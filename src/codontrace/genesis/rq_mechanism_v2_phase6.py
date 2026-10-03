"""Phase-6 assay. One estimand, separate effects, and a horizon from both sides.

The public flag stays false. A reanalysis of phase 5b is not a new confirmation.
The absent census 34/30 is the id-sort rule under the birth cap. It is not retuned.
"""

from __future__ import annotations

import json
import math
import statistics
from collections.abc import Mapping, Sequence
from pathlib import Path

from codontrace.errors import ConfigurationError
from codontrace.genesis.closed_loop_hp_arm01_structural_rq import STRUCT_SOFT_K
from codontrace.genesis.closed_loop_pearl_spc import PASSAGE_ABSENT
from codontrace.genesis.rq_bidirectional_timeshift_confirm import MEASUREMENT_FLOOR, infectivity
from codontrace.genesis.rq_mechanism_v2_phase4 import (
    PHASE4_CENSUS,
    PHASE4_PER_CLASS,
    WINDOW_A,
    WINDOW_B,
)
from codontrace.genesis.rq_mechanism_v2_phase5 import (
    ARM_COEVOLVE,
    MAX_WORKERS,
    NO_CONFIRMATORY_SENTENCE,
    assert_measurement_floor,
    assert_output_dir,
    replay_phase5_archive,
    resolve_workers,
    run_phase5_history,
    wilson_interval,
)

PHASE6_BUDGET = 16
PHASE6_PROBE_GENERATIONS = 12
PHASE6_PROBE_PARASITE = 9800
PHASE6_PROBE_HOST = 9801
PHASE6_PROBE_DELAY = 9802
PHASE6_SHORT_SEED = 9803
PHASE6_SEED_START = 9811
PHASE6_N = 12
PHASE6_OFFSPRING_PER_PAIR = 2
OUTPUT_PRELIM = Path("runs/rq-mechanism-v2/phase6-prelim")
OUTPUT_SHORT = Path("runs/rq-mechanism-v2/phase6-short")
OUTPUT_CONFIRM = Path("runs/rq-mechanism-v2/phase6-coevolution")
PHASE6_LOCK = Path("runs/rq-mechanism-v2/PHASE6_LOCK.md")
REANALYSIS_NOTE = Path("runs/rq-mechanism-v2/PHASE5B_REANALYSIS.md")
_PHASE5B_SUMMARY = Path("runs/rq-mechanism-v2/phase5b-coevolution/summary.json")
_USED_SEEDS = frozenset(
    {
        *range(9600, 9613),
        *range(9700, 9713),
        *range(9201, 9225),
        *range(9301, 9305),
        *range(9500, 9505),
        9099,
        9101,
        9102,
        9103,
        9104,
        9401,
    }
)


def assert_phase6_output_dir(root: Path) -> None:
    """Phase 6 does not write a previous tree."""

    assert_output_dir(root)
    resolved = root.resolve()
    for banned in (
        Path("runs/rq-mechanism-v2/phase5-coevolution"),
        Path("runs/rq-mechanism-v2/phase5-probe"),
        Path("runs/rq-mechanism-v2/phase5b-coevolution"),
        Path("runs/rq-mechanism-v2/phase4-fitness"),
        Path("runs/rq-mechanism-v2/phase4b-fitness"),
    ):
        banned_resolved = banned.resolve()
        if resolved == banned_resolved or banned_resolved in resolved.parents:
            raise ConfigurationError(f"phase-6 must not write into {banned}")


def locked_phase6_seeds() -> tuple[int, ...]:
    """Twelve unused histories. Phase-5 and phase-5b seeds are not reused."""

    count = int(PHASE6_N)
    floor = assert_measurement_floor()
    if count < floor:
        raise ConfigurationError("phase-6 history count is below MEASUREMENT_FLOOR")
    seeds = tuple(range(PHASE6_SEED_START, PHASE6_SEED_START + count))
    banned = set(_USED_SEEDS) | {
        PHASE6_PROBE_PARASITE,
        PHASE6_PROBE_HOST,
        PHASE6_PROBE_DELAY,
        PHASE6_SHORT_SEED,
    }
    if len(set(seeds)) != count or (set(seeds) & banned):
        raise ConfigurationError("phase-6 seeds overlap a used history")
    if seeds[0] != 9811 or seeds[-1] != 9822:
        raise ConfigurationError("phase-6 seeds are not 9811 through 9822")
    return seeds


def _positive(value: object) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ConfigurationError("a timescale must be a positive number")
    number = float(value)
    if not math.isfinite(number) or number <= 0.0:
        raise ConfigurationError("a timescale must be positive and finite")
    return number


def choose_phase6_horizon(
    *,
    parasite_replacement: float | None,
    host_replacement: float | None,
    fitness_delay: float | None,
    budget: int = PHASE6_BUDGET,
) -> dict[str, object]:
    """Horizon from both replacement times and, when measured, the fitness delay.

    The cycle period is not three times the parasite replacement time. A missing
    delay stays missing. The horizon is not shortened to fit a budget.
    """

    if int(budget) != PHASE6_BUDGET:
        raise ConfigurationError("phase-6 budget is the registered 16")
    parasite = _positive(parasite_replacement)
    host = _positive(host_replacement)
    delay: float | None
    if fitness_delay is None:
        delay = None
    else:
        delay = _positive(fitness_delay)
    horizon = max(math.ceil(parasite), math.ceil(host))
    if delay is not None:
        horizon = max(horizon, math.ceil(delay))
    lag = max(1, int(round(parasite)))
    if lag >= horizon:
        raise ConfigurationError("primary lag does not leave a past partner inside the horizon")
    if horizon > int(budget):
        raise ConfigurationError("horizon exceeds the registered budget; it is not shortened")
    cycle_start = horizon - 2 * lag
    return {
        "budget": int(budget),
        "cycle_times_measurable": cycle_start >= 1,
        "fitness_delay": delay,
        "fitness_delay_unmeasurable": delay is None,
        "horizon": int(horizon),
        "host_replacement": host,
        "not_three_times_parasite_replacement": True,
        "parasite_replacement": parasite,
        "primary_lag": int(lag),
        "turnover_multiple_used": False,
    }


def shared_paired_estimand(
    hosts_now: Sequence[Mapping[str, object]],
    hosts_past: Sequence[Mapping[str, object]],
    parasites_now: Sequence[Mapping[str, object]],
    parasites_past: Sequence[Mapping[str, object]],
) -> dict[str, object]:
    """One paired estimand. Host and parasite effects are the two pieces that add to it.

    The other host contrast, contemporary parasites against past hosts, is a
    diagnostic. It is not added into the paired contrast.
    """

    if not hosts_now or not hosts_past or not parasites_now or not parasites_past:
        return {
            "diagnostic_host_on_contemporary_parasites": None,
            "host_effect": None,
            "paired": None,
            "parasite_effect": None,
        }
    now_now = infectivity(hosts_now, parasites_now)
    now_past = infectivity(hosts_now, parasites_past)
    past_past = infectivity(hosts_past, parasites_past)
    past_now = infectivity(hosts_past, parasites_now)
    if None in (now_now, now_past, past_past, past_now):
        return {
            "diagnostic_host_on_contemporary_parasites": None,
            "host_effect": None,
            "paired": None,
            "parasite_effect": None,
        }
    parasite_effect = float(now_now) - float(now_past)
    host_effect = float(now_past) - float(past_past)
    paired = float(now_now) - float(past_past)
    diagnostic = float(now_now) - float(past_now)
    if not math.isclose(parasite_effect + host_effect, paired, abs_tol=1e-12):
        raise ConfigurationError("host and parasite effects do not add to the paired estimand")
    return {
        "diagnostic_host_on_contemporary_parasites": diagnostic,
        "diagnostic_mixed_into_paired": False,
        "host_effect": host_effect,
        "paired": paired,
        "parasite_effect": parasite_effect,
    }


def _sign(left: float | None, right: float | None) -> int | None:
    if left is None or right is None:
        return None
    if not math.isfinite(left) or not math.isfinite(right) or left == right:
        return None
    return 1 if left > right else -1


def selection_direction(
    *,
    ancestry_fitness_a: float | None,
    ancestry_fitness_b: float | None,
    contact: float | None,
    genotype_a_present: bool,
    genotype_b_present: bool,
    infectivity_gap: float | None = None,
) -> dict[str, object]:
    """A selection direction needs both genotypes and contact. Infectivity is not enough."""

    present = bool(genotype_a_present) and bool(genotype_b_present)
    contacted = contact is not None and math.isfinite(float(contact)) and float(contact) > 0.0
    direction = _sign(ancestry_fitness_a, ancestry_fitness_b) if present and contacted else None
    return {
        "contact_ok": contacted,
        "direction": direction,
        "genotypes_present": present,
        "infectivity_used_as_selection": False,
        "infectivity_gap": infectivity_gap,
    }


def registered_oscillation(
    directions: Sequence[Mapping[str, object]],
    *,
    horizon: int,
    lag: int,
) -> dict[str, object]:
    """The locked times only. One sign change is not a continuing cycle.

    Times are horizon, horizon-lag, and horizon-2*lag when that generation
    exists. A scan of every generation is not this function.
    """

    if int(lag) < 1 or int(horizon) <= int(lag):
        raise ConfigurationError("oscillation lag is outside the horizon")
    needed = [int(horizon) - 2 * int(lag), int(horizon) - int(lag), int(horizon)]
    by_gen = {int(row["generation"]): row for row in directions}
    if len(by_gen) != len(list(directions)):
        raise ConfigurationError("duplicate generations")
    if needed[0] < 1:
        return {
            "continuing_cycle": False,
            "direction_changes": [],
            "exploratory": False,
            "one_sign_change_is_not_a_cycle": False,
            "times": needed,
            "unmeasurable": True,
        }
    signs: list[int | None] = []
    for generation in needed:
        row = by_gen.get(generation)
        if row is None or row.get("direction") is None:
            return {
                "continuing_cycle": False,
                "direction_changes": [],
                "exploratory": False,
                "one_sign_change_is_not_a_cycle": False,
                "times": needed,
                "unmeasurable": True,
            }
        if row.get("genotypes_present") is not True or row.get("contact_ok") is not True:
            return {
                "continuing_cycle": False,
                "direction_changes": [],
                "exploratory": False,
                "one_sign_change_is_not_a_cycle": False,
                "times": needed,
                "unmeasurable": True,
            }
        signs.append(int(row["direction"]))
    changes = [needed[index] for index in (1, 2) if signs[index] != signs[index - 1]]
    continuing = len(changes) >= 2 and signs[0] == signs[2] and signs[1] != signs[0]
    return {
        "continuing_cycle": continuing,
        "direction_changes": changes,
        "exploratory": False,
        "one_sign_change_is_not_a_cycle": len(changes) == 1,
        "signs": signs,
        "times": needed,
        "unmeasurable": False,
    }


def exploratory_direction_scan(directions: Sequence[int | None]) -> dict[str, object]:
    """Every current time. This cannot confirm a cycle."""

    changes = 0
    previous: int | None = None
    for direction in directions:
        if direction is None:
            continue
        if previous is not None and direction != previous:
            changes += 1
        previous = direction
    return {"confirmatory": False, "direction_changes": changes, "exploratory": True}


def absent_baseline_rule(host_ids: Sequence[str]) -> dict[str, object]:
    """Which rule produces alive 34 and 30 when names sort A before B.

    Founders are 30 and 30. The life-loop steps organisms in id order.
    ``two_fold_cost_sex`` is false, so a chamber pair places two offspring.
    The seat cap is 64, so two pairs fill the four open seats and later ids
    are not reached. Food headcount is not this rule.
    """

    if len(host_ids) != PHASE4_CENSUS:
        raise ConfigurationError("absent baseline uses the locked census of 60")
    ordered = sorted(str(item) for item in host_ids)
    room = int(STRUCT_SOFT_K) - int(PHASE4_CENSUS)
    births = {"A": 0, "B": 0}
    index = 0
    while room >= PHASE6_OFFSPRING_PER_PAIR and index + 1 < len(ordered):
        for parent in ordered[index : index + PHASE6_OFFSPRING_PER_PAIR]:
            if "-A-" in parent:
                births["A"] += 1
            elif "-B-" in parent:
                births["B"] += 1
            else:
                raise ConfigurationError("baseline id is neither host A nor host B")
        room -= PHASE6_OFFSPRING_PER_PAIR
        index += PHASE6_OFFSPRING_PER_PAIR
    return {
        "alive_A": PHASE4_PER_CLASS + births["A"],
        "alive_B": PHASE4_PER_CLASS + births["B"],
        "births_A": births["A"],
        "births_B": births["B"],
        "cap": int(STRUCT_SOFT_K),
        "founders_A": PHASE4_PER_CLASS,
        "founders_B": PHASE4_PER_CLASS,
        "offspring_per_pair": PHASE6_OFFSPRING_PER_PAIR,
        "open_seats": int(STRUCT_SOFT_K) - int(PHASE4_CENSUS),
        "order": "sorted host id",
        "rule": "id-sort chamber pairs fill the four open seats before the later name",
    }


def food_seat_symmetry(census: int = PHASE4_CENSUS, n_patches: int = 16) -> dict[str, object]:
    """Even seats are A and odd seats are B. Patch headcount is still 30 and 30."""

    if int(census) != PHASE4_CENSUS or int(n_patches) != 16:
        raise ConfigurationError("food symmetry uses the locked 60 hosts and 16 patches")
    counts = {"A": 0, "B": 0}
    per_patch = {"A": [0] * n_patches, "B": [0] * n_patches}
    for index in range(int(census)):
        letter = "A" if index % 2 == 0 else "B"
        counts[letter] += 1
        per_patch[letter][index % n_patches] += 1
    return {
        "class_counts": counts,
        "even_patches_are_only_A": all(per_patch["B"][patch] == 0 for patch in range(0, n_patches, 2)),
        "headcount_equal": counts["A"] == counts["B"] == PHASE4_PER_CLASS,
        "odd_patches_are_only_B": all(per_patch["A"][patch] == 0 for patch in range(1, n_patches, 2)),
        "patch_occupancy_A": per_patch["A"],
        "patch_occupancy_B": per_patch["B"],
    }


def fitness_kinds(
    *,
    ancestry_a: float | None,
    ancestry_b: float | None,
    current_a: float | None,
    current_b: float | None,
) -> dict[str, object]:
    """Founder-class fitness and living-window fitness stay separate."""

    ancestry = None if ancestry_a is None or ancestry_b is None else float(ancestry_a) - float(ancestry_b)
    current = None if current_a is None or current_b is None else float(current_a) - float(current_b)
    return {
        "ancestry_gap": ancestry,
        "current_genotype_gap": current,
        "current_substituted_for_ancestry": False,
    }


def pressure_contrast(
    *,
    absent_contacts: int,
    absent_births: Mapping[str, int],
    absent_deaths: Mapping[str, int],
    pressured_contacts: int,
    pressured_births: Mapping[str, int],
    pressured_deaths: Mapping[str, int],
) -> dict[str, object]:
    """Parasite pressure is the contrast against the no-parasite baseline. It is not the baseline itself."""

    return {
        "absent_contacts": int(absent_contacts),
        "baseline_is_pressure": False,
        "births_differ": dict(absent_births) != dict(pressured_births),
        "deaths_differ": dict(absent_deaths) != dict(pressured_deaths),
        "pressured_contacts": int(pressured_contacts),
    }


def reanalyze_phase5b_reversals(summary_path: Path | None = None) -> dict[str, object]:
    """Wilson interval for the archived  phase-5b reversal count. Seeds are not opened again."""

    path = _PHASE5B_SUMMARY if summary_path is None else summary_path
    payload = json.loads(path.read_text(encoding="utf-8"))
    report = payload["report"]
    claim_b = report["claim_b"]
    successes = int(claim_b["reversal_true_n"])
    n = int(claim_b["n_used"])
    if int(payload["horizon"]) != 10 or list(payload["seeds"]) != list(range(9701, 9713)):
        raise ConfigurationError("phase-5b reanalysis file is not the archived run")
    if n != 12 or successes != int(claim_b["reversal_true_n"]):
        raise ConfigurationError("phase-5b reversal count is not the archived count")
    interval = wilson_interval(successes, n)
    mean_a = report["claim_a"]["mean"]
    return {
        "analysis": "REANALYSIS",
        "claim_a_mean_archived": mean_a,
        "claim_a_verdict_archived": report["claim_a"]["verdict"],
        "fresh_confirmation": False,
        "horizon": int(payload["horizon"]),
        "n_used": n,
        "red_queen_proved": False,
        "reversal_interval": interval,
        "reversal_true_n": successes,
        "seeds": list(payload["seeds"]),
        "seeds_rerun": False,
        "source_summary": str(path),
        "wald_p_was_null": claim_b.get("interval", {}).get("p_one_sided") is None,
    }


def render_phase5b_reanalysis(result: Mapping[str, object]) -> str:
    """Note for the archived reversals. This is not a confirmatory."""

    interval = result["reversal_interval"]
    assert isinstance(interval, Mapping)
    lines = [
        "# Phase-5b reversal reanalysis",
        "",
        "This is a registered REANALYSIS of `runs/rq-mechanism-v2/phase5b-coevolution/summary.json`.",
        "Seeds 9701 through 9712 were not run again. No confirmatory history was opened.",
        "`red_queen_proved` stays false. The archived claim A mean is not rescaled.",
        "",
        f"Archived claim A mean: {result['claim_a_mean_archived']}.",
        f"Archived claim A verdict: {result['claim_a_verdict_archived']}.",
        f"Reversal count: {result['reversal_true_n']} / {result['n_used']}.",
        "The archived Wald interval had a zero standard error, a null one-sided p-value, and a null bound.",
        "That null p-value was not a p-value of 0, and the boundary was not dropped.",
        "",
        "Pre-registered null for this reanalysis: reversal probability 0.5.",
        "Interval: two-sided Wilson 95 percent, the small-n interval in Brown, Cai, and DasGupta 2001, equation (4).",
        "Directional tail: one-sided exact binomial probability at the null.",
        f"Wilson interval: [{interval['lower']}, {interval['upper']}].",
        f"Two-sided exact p: {interval['p_two_sided']}.",
        f"One-sided exact p: {interval['p_one_sided']}.",
        f"`wald_se_zero`: {interval['wald_se_zero']}. `se_zero` on the Wilson record: {interval['se_zero']}.",
        (
            "The upper bound is below 0.5, so the reversal index is on the negative side of the null."
            if float(interval["upper"]) < 0.5
            else "The upper bound is not below 0.5."
        ),
        "The continuous claim A mean stays the archived number. It is not this index.",
        "",
        "`red_queen_proved` is false.",
        "",
    ]
    return "\n".join(lines)


def render_phase6_lock(design: Mapping[str, object], *, code_commit: str) -> str:
    """Lock text. The required sentence is the first sentence and the last sentence."""

    seeds = [int(seed) for seed in design["seeds"]]  # type: ignore[index]
    payload = {
        "budget": int(design["budget"]),
        "fitness_delay": design["fitness_delay"],
        "fitness_delay_unmeasurable": bool(design["fitness_delay_unmeasurable"]),
        "horizon": int(design["horizon"]),
        "host_replacement": design["host_replacement"],
        "importance_bound": None,
        "n": len(seeds),
        "parasite_replacement": design["parasite_replacement"],
        "primary_lag": int(design["primary_lag"]),
        "seeds": seeds,
        "supported_forbidden": True,
        "turnover_multiple_used": False,
        "workers": MAX_WORKERS,
    }
    block = json.dumps(payload, indent=2, sort_keys=True)
    lines = [
        "# Phase-6 lock",
        "",
        NO_CONFIRMATORY_SENTENCE,
        "",
        f"Code commit: `{code_commit}`.",
        "Nothing in this lock is a confirmatory claim mean.",
        "Phase-5b seeds 9701 through 9712 are not reused. Seeds 9601 through 9612 are not reused.",
        "",
        "## Estimand",
        "",
        "Every arm is scored with the same paired estimand:",
        "`I(hosts at the horizon, parasites at the horizon) - I(hosts at horizon - lag, parasites at horizon - lag)`.",
        "Host effect, parasites held at the past generation:",
        "`I(hosts at the horizon, parasites at horizon - lag) - I(hosts at horizon - lag, parasites at horizon - lag)`.",
        "Parasite effect, hosts held at the horizon:",
        "`I(hosts at the horizon, parasites at the horizon) - I(hosts at the horizon, parasites at horizon - lag)`.",
        "Those two effects add to the paired estimand. The diagnostic host contrast on contemporary parasites is not added in.",
        "",
        "## Oscillation",
        "",
        "A direction of selection is the sign of ancestry fitness of genotypes that are both present, on a generation with contact pressure.",
        "An infectivity gap alone is not that direction.",
        "The registered times are the horizon, one lag earlier, and two lags earlier, when two lags fit.",
        "One sign change is not a continuing cycle. A scan of every generation stays exploratory.",
        "`red_queen_proved` is not set from this criterion. Importance is undeclared.",
        "",
        "## Horizon",
        "",
        "The horizon is the maximum of the parasite replacement time, the host replacement time,",
        "and the fitness-response delay when that delay was measured.",
        "It is not three times the parasite replacement time.",
        f"Parasite replacement: {design['parasite_replacement']}.",
        f"Host replacement: {design['host_replacement']}.",
        f"Fitness delay: {design['fitness_delay']}. Unmeasurable: {design['fitness_delay_unmeasurable']}.",
        f"Primary lag: {design['primary_lag']}.",
        f"Horizon: {design['horizon']} generations. Budget: {design['budget']}. The horizon was not shortened.",
        f"n: {len(seeds)}.",
        f"Seeds: {seeds[0]} through {seeds[-1]} ({', '.join(str(seed) for seed in seeds)}).",
        "",
        "Importance for this estimand is undeclared. SUPPORTED is forbidden.",
        f"`MEASUREMENT_FLOOR` stays {int(MEASUREMENT_FLOOR)} and is not lowered.",
        "CPU workers at most 7.",
        f"Output: `{OUTPUT_CONFIRM}`.",
        "",
        "```json",
        block,
        "```",
        "",
        NO_CONFIRMATORY_SENTENCE,
        "",
    ]
    return "\n".join(lines)


def replacement_time(births: Sequence[int], censuses: Sequence[int]) -> dict[str, object]:
    """Census over mean births. A zero birth mean is unmeasurable, not a zero time."""

    if not births or not censuses or len(births) != len(censuses):
        raise ConfigurationError("replacement time needs paired birth and census rows")
    if any(int(item) < 0 for item in births) or any(int(item) < 0 for item in censuses):
        raise ConfigurationError("birth and census counts cannot be negative")
    mean_births = float(statistics.fmean(int(item) for item in births))
    mean_census = float(statistics.fmean(int(item) for item in censuses))
    if mean_births <= 0.0 or mean_census <= 0.0:
        return {"measurable": False, "mean_births": mean_births, "mean_census": mean_census, "replacement": None}
    return {
        "measurable": True,
        "mean_births": mean_births,
        "mean_census": mean_census,
        "replacement": mean_census / mean_births,
    }


def fitness_response_delay(
    absent_signs: Sequence[int | None],
    pressured_signs: Sequence[int | None],
) -> dict[str, object]:
    """First generation where parasite pressure changes the birth-rank sign. Missing stays missing."""

    if len(absent_signs) != len(pressured_signs) or not absent_signs:
        raise ConfigurationError("delay series must be paired and non-empty")
    for index, (base, pressed) in enumerate(zip(absent_signs, pressured_signs, strict=True), start=1):
        if base is None or pressed is None:
            continue
        if int(pressed) != int(base):
            return {"delay": index, "measurable": True}
    return {"delay": None, "measurable": False}


def phase6_worker_cap(requested: int | None) -> int:
    """Accept 7. Reject 8. The phase-2 cap is a different module."""

    return resolve_workers(requested)



def _birth_census(path: Path) -> dict[str, object]:
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    host_births = []
    host_census = []
    parasite_births = []
    parasite_census = []
    signs: list[int | None] = []
    for row in rows:
        births = row.get("host_births")
        host_births.append(len(births) if isinstance(births, list) else 0)
        hosts = row.get("hosts")
        host_census.append(len(hosts) if isinstance(hosts, list) else 0)
        parasite_births.append(int(row.get("parasite_births") or 0))
        parasite_census.append(int(row.get("parasite_census") or 0))
        if not isinstance(births, list):
            signs.append(None)
            continue
        a = 0
        b = 0
        for item in births:
            if not isinstance(item, dict):
                continue
            parent = str(item.get("parent_id") or "")
            if "-A-" in parent:
                a += 1
            elif "-B-" in parent:
                b += 1
        signs.append(None if a == b else (1 if a > b else -1))
    return {
        "host_births": host_births,
        "host_census": host_census,
        "parasite_births": parasite_births,
        "parasite_census": parasite_census,
        "signs": signs,
    }


def execute_phase6_prelim(root: Path | None = None) -> dict[str, object]:
    """Three unused probe seeds. No confirmatory seed and no claim mean."""

    target = OUTPUT_PRELIM if root is None else root
    assert_phase6_output_dir(target)
    if (target / "by_seed").exists():
        raise ConfigurationError("phase-6 prelim already exists; a seed is not replaced")
    jobs = (
        (PHASE6_PROBE_PARASITE, None, "parasite"),
        (PHASE6_PROBE_HOST, PASSAGE_ABSENT, "host"),
        (PHASE6_PROBE_DELAY, None, "delay"),
    )
    outcomes = []
    for seed, passage, _name in jobs:
        outcomes.append(
            run_phase5_history(
                seed,
                str(target),
                PHASE6_PROBE_GENERATIONS,
                arms=(ARM_COEVOLVE,),
                compare_one_shot=False,
                passage_override=passage,
            )
        )
    failed = [item for item in outcomes if item["failed"]]
    summary: dict[str, object] = {"failed": failed, "red_queen_proved": False, "seeds": [item[0] for item in jobs]}
    if not failed:
        parasite = _birth_census(target / "by_seed" / f"seed{PHASE6_PROBE_PARASITE}" / "archive.jsonl")
        host = _birth_census(target / "by_seed" / f"seed{PHASE6_PROBE_HOST}" / "archive.jsonl")
        delay_rows = _birth_census(target / "by_seed" / f"seed{PHASE6_PROBE_DELAY}" / "archive.jsonl")
        parasite_time = replacement_time(parasite["parasite_births"], parasite["parasite_census"])  # type: ignore[arg-type]
        host_time = replacement_time(host["host_births"], host["host_census"])  # type: ignore[arg-type]
        delay = fitness_response_delay(host["signs"], delay_rows["signs"])  # type: ignore[arg-type]
        summary["parasite_turnover"] = parasite_time
        summary["host_turnover"] = host_time
        summary["fitness_delay"] = delay
        if parasite_time["measurable"] and host_time["measurable"]:
            try:
                summary["design"] = choose_phase6_horizon(
                    parasite_replacement=parasite_time["replacement"],  # type: ignore[arg-type]
                    host_replacement=host_time["replacement"],  # type: ignore[arg-type]
                    fitness_delay=delay["delay"],  # type: ignore[arg-type]
                )
                summary["design_error"] = None
            except ConfigurationError as exc:
                summary["design"] = None
                summary["design_error"] = str(exc)
        else:
            summary["design"] = None
            summary["design_error"] = "a replacement time is unmeasurable"
    target.mkdir(parents=True, exist_ok=True)
    (target / "prelim_summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return summary


def execute_phase6_short(root: Path | None = None) -> dict[str, object]:
    """One unused seed, two generations, one-shot replay, then the archive replay."""

    target = OUTPUT_SHORT if root is None else root
    assert_phase6_output_dir(target)
    if (target / "by_seed").exists():
        raise ConfigurationError("phase-6 short run already exists; a seed is not replaced")
    outcome = run_phase5_history(
        PHASE6_SHORT_SEED,
        str(target),
        2,
        arms=(ARM_COEVOLVE, "adaptation_cut", "constant_parasite"),
        compare_one_shot=True,
    )
    replay = None
    if not outcome["failed"]:
        replay = replay_phase5_archive(target / "by_seed" / f"seed{PHASE6_SHORT_SEED}" / "archive.jsonl")
        if not replay["matched"]:
            outcome = dict(outcome)
            outcome["failed"] = "replay-mismatch"
            (target / "STOP").write_text("replay-mismatch\n", encoding="utf-8")
    summary = {"failed": outcome["failed"], "red_queen_proved": False, "replay": replay, "seed": PHASE6_SHORT_SEED}
    target.mkdir(parents=True, exist_ok=True)
    (target / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return summary



__all__ = [
    "MEASUREMENT_FLOOR",
    "OUTPUT_CONFIRM",
    "PHASE6_BUDGET",
    "PHASE6_LOCK",
    "PHASE6_N",
    "WINDOW_A",
    "WINDOW_B",
    "absent_baseline_rule",
    "assert_phase6_output_dir",
    "choose_phase6_horizon",
    "execute_phase6_prelim",
    "execute_phase6_short",
    "exploratory_direction_scan",
    "fitness_kinds",
    "fitness_response_delay",
    "food_seat_symmetry",
    "locked_phase6_seeds",
    "phase6_worker_cap",
    "pressure_contrast",
    "reanalyze_phase5b_reversals",
    "registered_oscillation",
    "render_phase5b_reanalysis",
    "render_phase6_lock",
    "replacement_time",
    "selection_direction",
    "shared_paired_estimand",
]
