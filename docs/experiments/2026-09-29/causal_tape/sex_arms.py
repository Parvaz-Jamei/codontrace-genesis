"""CausalTape-5b -- two-fold cost of sex with an audited irreversible dissipation.

Design changes forced by the literature audit:

* The repository already ships ``two_fold_cost_sex`` as demographic
  fecundity-halving (``genesis/population.py``). Charging ``c_sex = 2c`` inside a
  conserved ledger is algebraically the same rule, so it would earn nothing.
  The ledger is therefore made to do independent work by charging an
  **irreversible per-mating dissipation** ``delta``: ``c_sex = 2c(1 + delta)``,
  where the ``2c*delta`` part appears in no offspring and is audited as a
  first-class, individually counted flow. ``delta = 0`` must reproduce the
  classical null.

* At carrying capacity, realised per-capita fitness converges between the two
  modes (Yasui & Hasegawa), so the primary estimand is **sexual genotype
  frequency / extinction time / biomass share**, never equilibrium fitness.

* The parasite must impose *differential* pressure. In the first build it
  infected 100% of hosts, which is a uniform slowdown, not frequency-dependent
  selection; the pool is therefore small and matching is strict.

Estimands per run: final sexual frequency, time to sexual extinction, area under
the sexual-frequency curve, infected fraction, saturation index rho, ledger
residual, and the mating-dissipation audit.
"""

from __future__ import annotations

import json
import math
import time
from concurrent.futures import ProcessPoolExecutor
from functools import partial
from pathlib import Path

import numpy as np

import sys

REPO_SRC = Path(__file__).resolve().parents[1] / "codontrace-genesis" / "src"
if str(REPO_SRC) not in sys.path:
    sys.path.insert(0, str(REPO_SRC))

from codontrace.rng import RNGManager  # noqa: E402

HERE = Path(__file__).resolve().parent
RESULTS = HERE / "results"
RESULTS.mkdir(exist_ok=True)

WORKERS = 4
LOCI = 6
HOST_CAP = 400
PARASITE_CAP = 16
PARASITE_POOL = 2
INITIAL_HOSTS = 200
INVADERS = 100
GENERATIONS = 400
INTAKE = 2.0
METABOLISM = 1.0
INFECTION_COST = 0.4
BIRTH_COST = 4.0
START_ENERGY = 2.0
MATCH_TOLERANCE = 1
MUTATION_RATE = 0.02
PARASITE_MUTATION_RATE = 0.08
MORTALITY = 0.10
SEEDS = tuple(range(6000, 6100))


class Ledger:
    """Cumulative energy ledger; every flow is counted and the identity asserted."""

    def __init__(self, initial: float) -> None:
        self.initial = initial
        self.intake = 0.0
        self.metabolism = 0.0
        self.infection = 0.0
        self.births = 0.0
        self.offspring = 0.0
        self.deaths = 0.0
        self.mating_dissipation = 0.0
        self.mating_dissipation_expected = 0.0
        self.max_residual = 0.0
        self.max_dissipation_error = 0.0

    def check(self, total_now: float) -> float:
        expected = (
            self.initial
            + self.intake
            - self.metabolism
            - self.infection
            - self.births
            + self.offspring
            - self.deaths
        )
        residual = abs(expected - total_now)
        self.max_residual = max(self.max_residual, residual)
        self.max_dissipation_error = max(
            self.max_dissipation_error, abs(self.mating_dissipation - self.mating_dissipation_expected)
        )
        return residual


def _mutate(genomes: np.ndarray, stream: RNGManager, index: np.ndarray, rate: float) -> np.ndarray:
    if index.size == 0:
        return genomes
    draws = np.array([[stream.random() for _ in range(genomes.shape[1])] for _ in index])
    genomes[np.ix_(index, np.arange(genomes.shape[1]))] ^= (draws < rate).astype(genomes.dtype)
    return genomes


def run_arm(
    seed: int,
    *,
    mode: str,
    parasite: bool,
    cost_ratio: float = 2.0,
    delta: float = 0.0,
    recombine: bool = True,
    evolving_parasite: bool = True,
    leak: float = 0.0,
    generations: int = GENERATIONS,
    infection_cost: float = INFECTION_COST,
    host_mutation: float = MUTATION_RATE,
    tolerance: int = MATCH_TOLERANCE,
    parasite_pool: int = PARASITE_POOL,
    shock: bool = False,
    shock_period: int = 25,
    shock_factor: float = 4.0,
) -> dict:
    root = RNGManager(seed=seed).fork("sex-arms")
    # Separate streams: the parasite consumes ~16*6 extra draws per generation,
    # so a shared stream makes the host mutation sequence diverge between the
    # parasite-on and parasite-off arms and breaks the seed pairing.
    stream = root.fork("host")
    par_stream = root.fork("parasite")
    rng = np.random.default_rng(seed)

    host_genome = np.zeros((HOST_CAP, LOCI), dtype=np.int8)
    host_energy = np.zeros(HOST_CAP, dtype=float)
    host_sexual = np.zeros(HOST_CAP, dtype=bool)
    host_alive = np.zeros(HOST_CAP, dtype=bool)

    order = rng.permutation(HOST_CAP)
    host_alive[order[:INITIAL_HOSTS]] = True
    host_energy[host_alive] = BIRTH_COST * 0.6
    host_genome[host_alive] = rng.integers(0, 2, size=(INITIAL_HOSTS, LOCI)).astype(np.int8)
    if mode == "sex":
        for row in rng.choice(order[:INITIAL_HOSTS], size=INVADERS, replace=False):
            host_sexual[row] = True

    parasite_genome = rng.integers(0, 2, size=(PARASITE_CAP, LOCI)).astype(np.int8)
    parasite_alive = np.zeros(PARASITE_CAP, dtype=bool)
    parasite_alive[:parasite_pool] = True
    fixed_parasite = parasite_genome[:parasite_pool].copy()

    ledger = Ledger(float(host_energy[host_alive].sum()))
    sexual_freq: list[float] = []
    infected_frac: list[float] = []
    biomass_frac: list[float] = []
    host_types: list[frozenset] = []
    energy_available = 0.0
    births_total = 0.0
    extinction_generation = -1

    for generation in range(generations):
        alive_idx = np.flatnonzero(host_alive)
        if alive_idx.size == 0:
            sexual_freq.append(0.0)
            infected_frac.append(0.0)
            biomass_frac.append(0.0)
            host_types.append(frozenset())
            continue

        # Abiotic regime: a "Court Jester" bolus pulse of resource on a fixed clock
        intake_now = INTAKE * (shock_factor if (shock and generation % shock_period == 0) else 1.0)
        host_energy[host_alive] += intake_now
        ledger.intake += intake_now * alive_idx.size
        host_energy[host_alive] -= METABOLISM
        ledger.metabolism += METABOLISM * alive_idx.size
        energy_available += intake_now * alive_idx.size

        infected = np.zeros(HOST_CAP, dtype=bool)
        if parasite:
            par_idx = np.flatnonzero(parasite_alive)
            if par_idx.size:
                distances = (
                    host_genome[alive_idx, None, :] != parasite_genome[None, par_idx, :]
                ).sum(axis=2)
                matches = distances <= tolerance
                infected[alive_idx] = matches.any(axis=1)
                host_energy[infected] -= infection_cost
                ledger.infection += infection_cost * int(infected.sum())

        if mode == "sex":
            unit = np.where(host_sexual, BIRTH_COST * cost_ratio * (1.0 + delta), BIRTH_COST)
        else:
            unit = np.full(HOST_CAP, BIRTH_COST)
        eligible = host_alive & (host_energy >= unit)
        if eligible.any():
            eligible_idx = np.flatnonzero(eligible)
            ranked = eligible_idx[np.argsort(-host_energy[eligible_idx], kind="stable")]
            free_slots = np.flatnonzero(~host_alive)
            n_births = min(ranked.size, free_slots.size)
            parents = ranked[:n_births]
            slots = free_slots[:n_births]

            child_genome = host_genome[parents].copy()
            if mode == "sex":
                sexual_parents = parents[host_sexual[parents]]
                if recombine and sexual_parents.size:
                    for offset, parent in enumerate(parents):
                        if not host_sexual[parent]:
                            continue
                        mate = sexual_parents[int(stream.randrange(sexual_parents.size))]
                        picks = np.array([stream.randrange(2) for _ in range(LOCI)])
                        child_genome[offset] = np.where(picks == 0, host_genome[parent], host_genome[mate])
            child_genome = _mutate(child_genome, stream, np.arange(n_births), host_mutation)
            paid = unit[parents]
            host_energy[parents] -= paid
            ledger.births += float(paid.sum())
            if mode == "sex":
                sexual_births = int(host_sexual[parents].sum())
                ledger.mating_dissipation += float(
                    (BIRTH_COST * cost_ratio * delta) * sexual_births
                )
                ledger.mating_dissipation_expected += float(
                    (BIRTH_COST * cost_ratio * delta) * sexual_births
                )
            host_genome[slots] = child_genome
            host_energy[slots] = START_ENERGY
            if mode == "sex":
                host_sexual[slots] = host_sexual[parents]
            host_alive[slots] = True
            ledger.offspring += START_ENERGY * n_births
            births_total += n_births

        bankrupt = host_alive & (host_energy < 0.0)
        ledger.deaths += float(host_energy[bankrupt].sum())
        host_energy[bankrupt] = 0.0
        host_alive[bankrupt] = False

        # Baseline mortality: without it the population fills to capacity, no
        # slots ever free up, reproduction stops and the sexual frequency is
        # frozen at its initial value (the first build of this script did
        # exactly that and measured nothing).
        mortal = host_alive & (rng.random(HOST_CAP) < MORTALITY)
        ledger.deaths += float(host_energy[mortal].sum())
        host_energy[mortal] = 0.0
        host_alive[mortal] = False

        if leak:
            # deliberate audit probe: destroy energy with no ledger entry
            alive_leak = np.flatnonzero(host_alive)
            if alive_leak.size:
                host_energy[alive_leak] = np.maximum(host_energy[alive_leak] - leak, 0.0)

        ledger.check(float(host_energy[host_alive].sum()))

        if parasite:
            par_idx = np.flatnonzero(parasite_alive)
            # Census after mortality: reusing the pre-death index counted dead
            # hosts as successful hosts for the parasite.
            alive_after = np.flatnonzero(host_alive)
            if par_idx.size and alive_after.size:
                distances = (
                    host_genome[alive_after, None, :] != parasite_genome[None, par_idx, :]
                ).sum(axis=2)
                success = (distances <= tolerance).sum(axis=0)
                if not evolving_parasite:
                    parasite_genome[:parasite_pool] = fixed_parasite
                    parasite_alive[:] = False
                    parasite_alive[:parasite_pool] = True
                elif success.sum() == 0:
                    parasite_genome[par_idx] = _mutate(
                        parasite_genome[par_idx].copy(), par_stream, np.arange(par_idx.size), PARASITE_MUTATION_RATE
                    )
                else:
                    survivors = par_idx[success > 0]
                    children = np.tile(survivors, int(math.ceil(PARASITE_CAP / survivors.size)))[:PARASITE_CAP]
                    parasite_genome = _mutate(
                        parasite_genome[children].copy(), par_stream, np.arange(PARASITE_CAP), PARASITE_MUTATION_RATE
                    )
                    parasite_alive[:] = True

        alive_now = np.flatnonzero(host_alive)
        freq = float(host_sexual[alive_now].mean()) if alive_now.size else 0.0
        sexual_freq.append(freq)
        infected_frac.append(float(infected[alive_now].mean()) if alive_now.size else 0.0)
        if mode == "sex" and alive_now.size:
            biomass_frac.append(float(host_energy[alive_now][host_sexual[alive_now]].sum() / max(host_energy[alive_now].sum(), 1e-12)))
        else:
            biomass_frac.append(0.0)
        if mode == "sex" and extinction_generation < 0 and freq == 0.0:
            extinction_generation = generation
        if alive_now.size:
            host_types.append(frozenset(tuple(row) for row in host_genome[alive_now]))
        else:
            host_types.append(frozenset())

    tail = int(generations * 0.25)
    diversity = [len(types) for types in host_types]
    turnover = []
    window = 20
    for index in range(window, len(host_types)):
        before, after = host_types[index - window], host_types[index]
        union = len(before | after)
        turnover.append(1.0 - (len(before & after) / union) if union else 0.0)
    return {
        "seed": seed,
        "mode": mode,
        "parasite": parasite,
        "cost_ratio": cost_ratio,
        "delta": delta,
        "recombine": recombine,
        "evolving_parasite": evolving_parasite,
        "sexual_final": float(np.mean(sexual_freq[-tail:])),
        "sexual_auc": float(np.mean(sexual_freq)),
        "sexual_biomass_final": float(np.mean(biomass_frac[-tail:])),
        "extinction_generation": extinction_generation,
        "infected_mean": float(np.mean(infected_frac)),
        "diversity_mean": float(np.mean(diversity)),
        "diversity_final": float(np.mean(diversity[-tail:])),
        "turnover_mean": float(np.mean(turnover)) if turnover else 0.0,
        "rho": float(min(1.0, births_total / max(energy_available / BIRTH_COST, 1e-12))),
        "ledger_residual": ledger.max_residual,
        "dissipation_error": ledger.max_dissipation_error,
        "mating_dissipation": ledger.mating_dissipation,
    }


ARMS: tuple[dict, ...] = (
    {"name": "A1_asex_noparasite", "mode": "asex", "parasite": False},
    {"name": "A2_sex_cost_noparasite", "mode": "sex", "parasite": False},
    {"name": "A3_sex_cost_parasite", "mode": "sex", "parasite": True},
    {"name": "A3b_sex_cost_ledger_parasite", "mode": "sex", "parasite": True, "delta": 0.5},
    {"name": "A4_asex_parasite", "mode": "asex", "parasite": True},
    {"name": "A5_sex_costless_parasite", "mode": "sex", "parasite": True, "cost_ratio": 1.0},
    {"name": "A6_sex_cost_norecomb_parasite", "mode": "sex", "parasite": True, "recombine": False},
    {"name": "A7_sex_cost_fixedparasite", "mode": "sex", "parasite": True, "evolving_parasite": False},
    {"name": "A8a_sex_cost1.0_parasite", "mode": "sex", "parasite": True, "cost_ratio": 1.0},
    {"name": "A8b_sex_cost1.5_parasite", "mode": "sex", "parasite": True, "cost_ratio": 1.5},
    {"name": "A8c_sex_cost3.0_parasite", "mode": "sex", "parasite": True, "cost_ratio": 3.0},
)


def _task(spec: dict, seed: int) -> dict:
    kwargs = {key: value for key, value in spec.items() if key != "name"}
    return run_arm(seed, **kwargs)


def main() -> int:
    started = time.perf_counter()
    report: dict = {"experiment": "CausalTape-5b", "workers": WORKERS, "seeds": len(SEEDS), "arms": {}}
    with ProcessPoolExecutor(max_workers=WORKERS) as pool:
        for spec in ARMS:
            rows = list(pool.map(partial(_task, spec), SEEDS, chunksize=2))
            final = np.array([row["sexual_final"] for row in rows])
            report["arms"][spec["name"]] = {
                "spec": spec,
                "sexual_final_mean": float(final.mean()),
                "sexual_final_sd": float(final.std()),
                "sexual_final_median": float(np.median(final)),
                "extinct_fraction": float(np.mean([row["extinction_generation"] >= 0 for row in rows])),
                "median_extinction_generation": float(
                    np.median([row["extinction_generation"] for row in rows if row["extinction_generation"] >= 0] or [-1])
                ),
                "sexual_auc": float(np.mean([row["sexual_auc"] for row in rows])),
                "sexual_biomass_final": float(np.mean([row["sexual_biomass_final"] for row in rows])),
                "infected_mean": float(np.mean([row["infected_mean"] for row in rows])),
                "rho_mean": float(np.mean([row["rho"] for row in rows])),
                "ledger_max_residual": float(np.max([row["ledger_residual"] for row in rows])),
                "dissipation_error": float(np.max([row["dissipation_error"] for row in rows])),
                "per_seed": final.tolist(),
            }
            arm = report["arms"][spec["name"]]
            print(
                f"{spec['name']:<32} sexual_final={arm['sexual_final_mean']:.4f}"
                f"+-{arm['sexual_final_sd']:.4f} extinct={arm['extinct_fraction']:.2f} "
                f"infected={arm['infected_mean']:.2f} rho={arm['rho_mean']:.2f} "
                f"ledger={arm['ledger_max_residual']:.1e}",
                flush=True,
            )

    leak_probe = run_arm(999, mode="sex", parasite=False, leak=1e-3, generations=50)
    report["leak_probe"] = {
        "injected_leak": 1e-3,
        "detected_residual": leak_probe["ledger_residual"],
        "detected": bool(leak_probe["ledger_residual"] > 1e-6),
    }

    # ---- rescue sweep: is there ANY parameter regime where sex is not lost? ----
    settings = (
        {"tag": "S1_base", "infection_cost": 0.8, "host_mutation": 0.02, "tolerance": 1, "parasite_pool": 4},
        {"tag": "S2_strong", "infection_cost": 1.6, "host_mutation": 0.005, "tolerance": 1, "parasite_pool": 4},
        {"tag": "S3_strict", "infection_cost": 1.6, "host_mutation": 0.005, "tolerance": 0, "parasite_pool": 2},
        {"tag": "S4_very_strong", "infection_cost": 2.4, "host_mutation": 0.005, "tolerance": 0, "parasite_pool": 2},
    )
    report["rescue"] = {}
    with ProcessPoolExecutor(max_workers=WORKERS) as pool:
        for setting in settings:
            tag = setting["tag"]
            params = {key: value for key, value in setting.items() if key != "tag"}
            for mode_tag, cost_ratio in (("cost", 2.0), ("costless", 1.0)):
                spec = {"name": f"{tag}_{mode_tag}", "mode": "sex", "parasite": True, "cost_ratio": cost_ratio, **params}
                rows = list(pool.map(partial(_task, spec), SEEDS, chunksize=2))
                final = np.array([row["sexual_final"] for row in rows])
                report["rescue"][spec["name"]] = {
                    "sexual_final_mean": float(final.mean()),
                    "extinct_fraction": float(np.mean([row["extinction_generation"] >= 0 for row in rows])),
                    "median_extinction_generation": float(
                        np.median([row["extinction_generation"] for row in rows if row["extinction_generation"] >= 0] or [-1])
                    ),
                    "infected_mean": float(np.mean([row["infected_mean"] for row in rows])),
                    "per_seed": final.tolist(),
                }
                row = report["rescue"][spec["name"]]
                print(
                    f"{spec['name']:<24} sexual_final={row['sexual_final_mean']:.4f} "
                    f"extinct={row['extinct_fraction']:.2f} med_ext={row['median_extinction_generation']:.0f} "
                    f"infected={row['infected_mean']:.2f}",
                    flush=True,
                )

        # ---- Red Queen vs Court Jester: biotic x abiotic factorial ----
        report["rjcj"] = {}
        for parasite_on in (False, True):
            for shock_on in (False, True):
                spec = {
                    "name": f"rjcj_p{int(parasite_on)}_s{int(shock_on)}",
                    "mode": "asex",
                    "parasite": parasite_on,
                    "shock": shock_on,
                }
                rows = list(pool.map(partial(_task, spec), SEEDS, chunksize=2))
                report["rjcj"][spec["name"]] = {
                    "diversity_mean": float(np.mean([row["diversity_mean"] for row in rows])),
                    "diversity_final": float(np.mean([row["diversity_final"] for row in rows])),
                    "turnover_mean": float(np.mean([row["turnover_mean"] for row in rows])),
                    "infected_mean": float(np.mean([row["infected_mean"] for row in rows])),
                    "per_seed": [row["turnover_mean"] for row in rows],
                }
                row = report["rjcj"][spec["name"]]
                print(
                    f"{spec['name']:<24} diversity={row['diversity_mean']:.1f} "
                    f"turnover={row['turnover_mean']:.4f} infected={row['infected_mean']:.2f}",
                    flush=True,
                )

    def per_seed(name: str) -> np.ndarray:
        return np.array(report["arms"][name]["per_seed"])

    a2 = per_seed("A2_sex_cost_noparasite")
    a3 = per_seed("A3_sex_cost_parasite")
    a3b = per_seed("A3b_sex_cost_ledger_parasite")
    a5 = per_seed("A5_sex_costless_parasite")
    a6 = per_seed("A6_sex_cost_norecomb_parasite")

    rng = np.random.default_rng(13)

    def paired_ci(x: np.ndarray, y: np.ndarray) -> list[float]:
        diff = x - y
        idx = rng.integers(0, diff.size, size=(2000, diff.size))
        return [float(np.percentile(diff[idx].mean(axis=1), 2.5)), float(np.percentile(diff[idx].mean(axis=1), 97.5))]

    diff_classical = a3 - a2
    diff_ledger = a3b - a2
    report["verdicts"] = {
        "P1_ledger_identity": {
            "max_residual": float(max(arm["ledger_max_residual"] for arm in report["arms"].values())),
            "max_dissipation_error": float(max(arm["dissipation_error"] for arm in report["arms"].values())),
            "passed": bool(
                max(arm["ledger_max_residual"] for arm in report["arms"].values()) <= 1e-9
                and max(arm["dissipation_error"] for arm in report["arms"].values()) <= 1e-12
            ),
        },
        "P1b_audit_detects_injected_leak": report["leak_probe"],
        "P2_positive_control_costless_sex_survives": {
            "A5_mean": float(a5.mean()),
            "threshold": 0.30,
            "passed": bool(a5.mean() > 0.30),
        },
        "P3_negative_control_cost_without_parasite_loses_sex": {
            "A2_mean": float(a2.mean()),
            "threshold": 0.05,
            "passed": bool(a2.mean() < 0.05),
        },
        "P4_classical_twofold_cost_rescued_by_parasite": {
            "A3_mean": float(a3.mean()),
            "A2_mean": float(a2.mean()),
            "paired_diff": float(diff_classical.mean()),
            "paired_diff_ci": paired_ci(a3, a2),
            "passed": bool(
                diff_classical.mean() > 0.0 and paired_ci(a3, a2)[0] > 0.0
            ),
        },
        "P5_ledger_dissipation_arm_rescued": {
            "A3b_mean": float(a3b.mean()),
            "paired_diff_vs_A2": float(diff_ledger.mean()),
            "paired_diff_ci": paired_ci(a3b, a2),
            "passed": bool(diff_ledger.mean() > 0.0 and paired_ci(a3b, a2)[0] > 0.0),
        },
        "P6_mechanism_is_recombination": {
            "A6_mean": float(a6.mean()),
            "A6_not_better_than_A3": bool(a6.mean() <= a3.mean()),
        },
    }

    # ---- rescue sweep verdict: any regime where costless sex persists? ----
    rescue = report["rescue"]
    report["verdicts"]["P7_rescue_sweep"] = {
        "costless_arms": {
            name: {
                "sexual_final_mean": arm["sexual_final_mean"],
                "extinct_fraction": arm["extinct_fraction"],
            }
            for name, arm in rescue.items()
            if name.endswith("_costless")
        },
        "cost_arms": {
            name: {
                "sexual_final_mean": arm["sexual_final_mean"],
                "extinct_fraction": arm["extinct_fraction"],
            }
            for name, arm in rescue.items()
            if name.endswith("_cost")
        },
        "any_regime_with_costless_sex_persisting": bool(
            any(arm["sexual_final_mean"] > 0.05 for name, arm in rescue.items() if name.endswith("_costless"))
        ),
        "any_regime_with_costly_sex_persisting": bool(
            any(arm["sexual_final_mean"] > 0.05 for name, arm in rescue.items() if name.endswith("_cost"))
        ),
    }

    # ---- Red Queen vs Court Jester: 2x2 factorial main effects and interaction ----
    rj = report["rjcj"]

    def cell(p: int, s: int) -> np.ndarray:
        return np.array(rj[f"rjcj_p{p}_s{s}"]["per_seed"])

    d_biotic = 0.5 * (cell(1, 0) + cell(1, 1)) - 0.5 * (cell(0, 0) + cell(0, 1))
    d_abiotic = 0.5 * (cell(0, 1) + cell(1, 1)) - 0.5 * (cell(0, 0) + cell(1, 0))
    interaction = (cell(1, 1) - cell(1, 0)) - (cell(0, 1) - cell(0, 0))
    report["verdicts"]["P8_red_queen_vs_court_jester"] = {
        "biotic_main_effect_turnover": {
            "mean": float(d_biotic.mean()),
            "ci": paired_ci(d_biotic, np.zeros_like(d_biotic)),
        },
        "abiotic_main_effect_turnover": {
            "mean": float(d_abiotic.mean()),
            "ci": paired_ci(d_abiotic, np.zeros_like(d_abiotic)),
        },
        "interaction": {
            "mean": float(interaction.mean()),
            "ci": paired_ci(interaction, np.zeros_like(interaction)),
        },
        "biotic_exceeds_abiotic": bool(abs(d_biotic.mean()) > abs(d_abiotic.mean())),
    }
    report["elapsed_seconds"] = round(time.perf_counter() - started, 1)
    (RESULTS / "sex_arms_results.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report["verdicts"], indent=2), flush=True)
    print("SEX_ARMS_DONE", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


