"""Phase-3 diagnostic frequency panel. Not a Red Queen claim.

Two locked host genomes are held at a fixed mix while a parasite population
either evolves or keeps its genotypic composition. The assay is the existing
replay contact path, on a copy, with evolution off. A positive D is a shift
in relative specialization. It is not Red Queen. ``red_queen_proved`` stays
false.

What was read before this file was added
----------------------------------------
``runs/rq-mechanism-v2/PHASE1.md`` records the copies that were opened.
Decaestecker et al. 2007 (KU Leuven Lirias letter) is the source for scoring
infectivity with no evolution during the score. Papkou et al. 2019 (PMC6338873)
is the source for not treating an antagonist pattern as proof by itself.
Zaman et al. 2014 (PMC4267771) is the source for the sentence that a frozen
genotype is not reciprocal coevolution. Hall et al. 2011 full text was not
legally available; this panel does not quote it and does not fit a model to
it. No sentence in this module is a new quotation from those papers.

The seat rule, debit, credit, and frozen passage are the structural engine
already in this tree. This module does not add a score for being common.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
from collections import Counter
from collections.abc import Mapping, Sequence
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import replace
from pathlib import Path
from typing import cast

from codontrace.dynvalues import same_int, same_iter
from codontrace.errors import ConfigurationError
from codontrace.genesis.closed_loop_hp_arm01 import (
    _tape,
    _window,
)
from codontrace.genesis.closed_loop_hp_arm01_structural_rq import (
    _DISTINCT_WINDOWS,
    STRUCT_BIRTH_ATP,
    STRUCT_KEEP_FRACTION,
    STRUCT_PARASITE_MUTATION,
    STRUCT_STEAL_FRACTION,
    STRUCT_VIRULENCE,
    StructuralRQArm,
)
from codontrace.genesis.closed_loop_pearl_spc import PASSAGE_COEVOLVE, PASSAGE_FROZEN
from codontrace.genesis.host_parasite_life_plugin import (
    OUTCROSS_OUT_BITS,
    ROLE_PRIMARY,
    ROLE_SECONDARY,
    ClosedLoopHPLifeConfig,
    outcross_runtime_cost,
    silence_outcross_locus,
)
from codontrace.genesis.measurements.antagonist_population import (
    AntagonistPopulation,
)
from codontrace.genesis.organism import GenesisOrganism
from codontrace.genesis.rq_bidirectional_timeshift import (
    ARM_A,
    build_arm,
    replay_archived_contact,
)
from codontrace.genesis.rq_bidirectional_timeshift_confirm import (
    MEASUREMENT_FLOOR,
    VERDICT_BLOCKED,
    infectivity,
)
from codontrace.genesis.rq_stream import ARM_STREAM_POLICY

# Diagnostic histories. 9500 is the selection seed and is not a history.
PHASE3_SEEDS: tuple[int, ...] = (9501, 9502, 9503, 9504)
PHASE3_SELECTION_SEED = 9500
PHASE3_FORBIDDEN_SEEDS: frozenset[int] = frozenset(
    {
        9099,
        9101,
        9102,
        9103,
        9104,
        *range(9201, 9225),
        *range(9301, 9305),
        9401,
        601,
        602,
        603,
        PHASE3_SELECTION_SEED,
    }
)
# 64 is not divisible by 5, so an exact 80/20 mix cannot seat every parasite
# on the structural census. 60 seats seat every parasite and are 48 + 12.
PHASE3_CENSUS = 60
PHASE3_COMMON_FRACTION = 0.8
PHASE3_RARE_FRACTION = 0.2
# Pre-declared before any probe result. Three replacement times, so the
# standing population is expected to have turned over more than once.
# Not chosen from the sign of D.
TURNOVER_MULTIPLE = 3
# Probe length for the turnover rate only. Not the conditioning horizon.
PROBE_GENERATIONS = 24
MAX_WORKERS = 7
STREAM_ROOT = "RQ-MECHANISM-V2-PHASE3"
BRANCH_COMMON_A = "common_a"
BRANCH_COMMON_B = "common_b"
BRANCH_LOCKED = "locked"
BRANCHES: tuple[str, ...] = (BRANCH_COMMON_A, BRANCH_COMMON_B, BRANCH_LOCKED)
ARCHIVE_SCHEMA = "rq-mechanism-v2-phase3/1"
VERDICT_NOT_DECLARED = "NOT_DECLARED"
NO_MEASUREMENT_D_SENTENCE = "No measurement D has been computed."
IMPORTANCE_RULE = (
    "Importance for this estimand is undeclared. SUPPORTED is forbidden. "
    "The minimum detectable effect is not the importance bound."
)
RED_QUEEN_PROVED = False

_OUTCROSS_COST_CONFIG = ClosedLoopHPLifeConfig(enabled=True, outcross_enabled=True)


def assert_phase3_seeds(seeds: Sequence[int], *, selection: bool = False) -> None:
    """Refuse forbidden seeds. Selection may use only 9500."""

    chosen = tuple(int(seed) for seed in seeds)
    if len(set(chosen)) != len(chosen):
        raise ConfigurationError("phase-3 seeds must be unique")
    if selection:
        if chosen != (PHASE3_SELECTION_SEED,):
            raise ConfigurationError("selection may use only seed 9500")
        return
    banned = sorted(set(chosen) & PHASE3_FORBIDDEN_SEEDS)
    if banned:
        raise ConfigurationError(f"phase-3 measurement seed is forbidden; overlap={banned}")
    if PHASE3_SELECTION_SEED in chosen:
        raise ConfigurationError("seed 9500 is selection only and is not a measurement history")


def resolve_workers(requested: int | None) -> int:
    """Cap at 7, one core below this machine. Reject 8 and above."""

    if requested is None:
        requested = MAX_WORKERS
    workers = int(requested)
    if workers < 1 or workers > MAX_WORKERS:
        raise ConfigurationError(
            f"phase-3 workers must be in 1..{MAX_WORKERS}, got {workers}"
        )
    return workers


def host_genome(window: str) -> str:
    """Full tape: shared program, shared outcross locus, this recognition window."""

    return _tape(OUTCROSS_OUT_BITS, str(window))


def _shared_background(genome_a: str, genome_b: str) -> str:
    prefix = os.path.commonprefix([genome_a, genome_b])
    return prefix


def mix_counts(census: int, common_fraction: float) -> tuple[int, int]:
    """Integer counts for an exact fraction. Unmeasurable if it is not exact."""

    if census < 5:
        raise ConfigurationError("census cannot express an exact 80/20 mix")
    common = float(common_fraction) * float(census)
    if abs(common - round(common)) > 1e-9:
        raise ConfigurationError("host fraction is not an integer count")
    common_n = int(round(common))
    rare_n = int(census) - common_n
    if common_n < 1 or rare_n < 1:
        raise ConfigurationError("both host genotypes must be present")
    return common_n, rare_n


def build_host_seats(
    window_a: str,
    window_b: str,
    *,
    common: str,
    census: int = PHASE3_CENSUS,
    common_fraction: float = PHASE3_COMMON_FRACTION,
) -> list[dict[str, str]]:
    """Interleave an exact mix. Index % 5 == 4 is the rare genome.

    ``common`` is "A" or "B". The seat stores the genome bit string and a
    real id (``host-A-001``). The letter is not a class label passed to contact.
    """

    if common not in {"A", "B"}:
        raise ConfigurationError("common host must be A or B")
    common_n, rare_n = mix_counts(census, common_fraction)
    window_by = {"A": str(window_a), "B": str(window_b)}
    genome_by = {letter: host_genome(window) for letter, window in window_by.items()}
    if genome_by["A"] == genome_by["B"]:
        raise ConfigurationError("host genotypes must differ")
    for letter, window in window_by.items():
        if not genome_by[letter].endswith(window) or len(genome_by[letter]) <= 6:
            raise ConfigurationError("recognition window is not the tape suffix")
    rare_letter = "B" if common == "A" else "A"
    seats: list[dict[str, str]] = []
    counts = {"A": 0, "B": 0}
    for index in range(int(census)):
        letter = rare_letter if index % 5 == 4 else common
        counts[letter] += 1
        seats.append(
            {
                "genome": genome_by[letter],
                "host_id": f"host-{letter}-{counts[letter]:03d}",
                "role_letter": letter,
                "window": window_by[letter],
            }
        )
    if counts[common] != common_n or counts[rare_letter] != rare_n:
        raise ConfigurationError("interleave did not hit the locked counts")
    return seats


def recognition_table(windows: Sequence[str] = _DISTINCT_WINDOWS) -> list[dict[str, object]]:
    """Engine infectivity of a parasite whose window equals the first host.

    One host, one parasite, birth ATP. This is the recognition instrument,
    not a measurement history and not D.
    """

    rows: list[dict[str, object]] = []
    for left in windows:
        for right in windows:
            if str(left) >= str(right):
                continue
            parasite = [
                {
                    "born_generation": 0,
                    "energy": 1.0,
                    "parent_id": None,
                    "unit_id": "recognition-parasite",
                    "window": str(left),
                }
            ]
            host_left = [{"id": "recognition-host-left", "runtime_atp": STRUCT_BIRTH_ATP, "window": str(left)}]
            host_right = [{"id": "recognition-host-right", "runtime_atp": STRUCT_BIRTH_ATP, "window": str(right)}]
            i_left = infectivity(host_left, parasite)
            i_right = infectivity(host_right, parasite)
            if i_left is None or i_right is None:
                gap = None
            else:
                gap = float(i_left) - float(i_right)
            genome_left = host_genome(str(left))
            genome_right = host_genome(str(right))
            cost_left = outcross_runtime_cost(genome_left, _OUTCROSS_COST_CONFIG)
            cost_right = outcross_runtime_cost(genome_right, _OUTCROSS_COST_CONFIG)
            rows.append(
                {
                    "engine_infectivity_on_first": i_left,
                    "engine_infectivity_on_second": i_right,
                    "genome_first": genome_left,
                    "genome_second": genome_right,
                    "outcross_cost_first": cost_left,
                    "outcross_cost_second": cost_right,
                    "recognition_gap": gap,
                    "shared_prefix": _shared_background(genome_left, genome_right),
                    "window_first": str(left),
                    "window_second": str(right),
                }
            )
    return rows


def choose_host_pair(rows: Sequence[Mapping[str, object]]) -> dict[str, object]:
    """Clearest engine recognition gap, costs equal, genomes not class labels.

    Ties break by lexicographic window pair. The sign of a later D is not an input.
    """

    best: Mapping[str, object] | None = None
    best_key: tuple[float, str, str] | None = None
    for row in rows:
        gap = row.get("recognition_gap")
        if gap is None or isinstance(gap, bool) or not isinstance(gap, (int, float)):
            continue
        if row.get("outcross_cost_first") != row.get("outcross_cost_second"):
            continue
        genome_first = str(row["genome_first"])
        genome_second = str(row["genome_second"])
        if genome_first == genome_second:
            continue
        if len(genome_first) <= 6 or genome_first == str(row["window_first"]):
            continue
        key = (-float(gap), str(row["window_first"]), str(row["window_second"]))
        if best_key is None or key < best_key:
            best_key = key
            best = row
    if best is None:
        raise ConfigurationError("no host pair had a measurable recognition gap")
    if float(best["recognition_gap"]) <= 0.0:  # type: ignore[arg-type]
        raise ConfigurationError("recognition gap is not positive; pair is not distinct")
    return dict(best)


def horizon_from_turnover(
    *,
    mean_newborns: float,
    census: int,
    measurable: bool,
) -> dict[str, object]:
    """Conditioning horizon from parasite replacement time, not from D.

    One engine generation is one parasite ``advance``. Replacement time is
    census / mean seated newborns. The horizon is ``TURNOVER_MULTIPLE``
    replacement times, rounded up. Unmeasurable turnover is not zero and
    does not become a horizon.
    """

    if not measurable:
        raise ConfigurationError("contact was unmeasurable; horizon is not set")
    if census < 1:
        raise ConfigurationError("parasite census must be positive")
    if not math.isfinite(float(mean_newborns)) or float(mean_newborns) <= 0.0:
        raise ConfigurationError("parasite turnover is unmeasurable; horizon is not 0")
    replacement_generations = float(census) / float(mean_newborns)
    horizon = int(math.ceil(float(TURNOVER_MULTIPLE) * replacement_generations))
    if horizon < 1:
        raise ConfigurationError("horizon collapsed below one parasite generation")
    return {
        "census": int(census),
        "conditioning_generations": horizon,
        "generation_time": "one antagonist advance per engine generation",
        "mean_seated_newborns": float(mean_newborns),
        "replacement_generations": replacement_generations,
        "turnover_multiple": TURNOVER_MULTIPLE,
    }


def estimand_d(
    i_a_common_a: float | None,
    i_b_common_a: float | None,
    i_a_common_b: float | None,
    i_b_common_b: float | None,
) -> float | None:
    """D from four assay infectivities. Any missing input stays missing, not zero."""

    values = (i_a_common_a, i_b_common_a, i_a_common_b, i_b_common_b)
    for value in values:
        if value is None:
            return None
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ConfigurationError("infectivity must be a finite number or null")
        if not math.isfinite(float(value)):
            return None
    gap_a = float(i_a_common_a) - float(i_b_common_a)  # type: ignore[arg-type]
    gap_b = float(i_a_common_b) - float(i_b_common_b)  # type: ignore[arg-type]
    return gap_a - gap_b


def control_gap(i_a: float | None, i_b: float | None) -> float | None:
    """Intrinsic gap of the non-evolving parasite. Not substituted for D."""

    if i_a is None or i_b is None:
        return None
    if not math.isfinite(float(i_a)) or not math.isfinite(float(i_b)):
        return None
    return float(i_a) - float(i_b)


def assess_phase3(
    by_seed: Mapping[int, Mapping[str, object]],
    locked_seeds: Sequence[int],
) -> dict[str, object]:
    """Incomplete locked seeds are BLOCKED_MEASUREMENT, not a negative.

    ``MEASUREMENT_FLOOR`` is not lowered and is not aliased to an importance
    bound. Importance is undeclared, so a complete sample is ``NOT_DECLARED``
    and never ``SUPPORTED``.
    """

    if int(MEASUREMENT_FLOOR) < 12:
        raise ConfigurationError("MEASUREMENT_FLOOR must not be lowered")
    locked = [int(seed) for seed in locked_seeds]
    dropped: list[int] = []
    used: list[int] = []
    per_seed: list[dict[str, object]] = []
    for seed in locked:
        row = by_seed.get(int(seed))
        if row is None:
            dropped.append(int(seed))
            per_seed.append({"D": None, "control_gap": None, "seed": int(seed), "status": "missing"})
            continue
        raw_d = row.get("D")
        if raw_d is None:
            dropped.append(int(seed))
            per_seed.append(
                {
                    "D": None,
                    "control_gap": row.get("control_gap"),
                    "seed": int(seed),
                    "status": "unmeasurable",
                }
            )
            continue
        if isinstance(raw_d, bool) or not isinstance(raw_d, (int, float)):
            raise ConfigurationError("D must be a finite number or null")
        if not math.isfinite(float(raw_d)):
            dropped.append(int(seed))
            per_seed.append({"D": None, "control_gap": row.get("control_gap"), "seed": int(seed), "status": "unmeasurable"})
            continue
        used.append(int(seed))
        per_seed.append(
            {
                "D": float(raw_d),
                "control_gap": row.get("control_gap"),
                "seed": int(seed),
                "status": "measured",
            }
        )
    n_locked = len(locked)
    n_used = len(used)
    blocked = n_used != n_locked or bool(dropped)
    mean: float | None = None
    if not blocked and used:
        # Reported only when every locked seed was measurable. Not a support call.
        total = 0.0
        for seed in used:
            total += float(by_seed[seed]["D"])  # type: ignore[arg-type]
        mean = total / float(n_used)
    verdict = VERDICT_BLOCKED if blocked else VERDICT_NOT_DECLARED
    return {
        "D_mean": mean,
        "dropped_seeds": dropped,
        "importance_bound": None,
        "importance_rule": IMPORTANCE_RULE,
        "mde_is_importance_bound": False,
        "measurement_floor": int(MEASUREMENT_FLOOR),
        "measurement_floor_lowered": False,
        "n_locked": n_locked,
        "n_used": n_used,
        "per_seed": per_seed,
        "red_queen_declared": False,
        "red_queen_proved": False,
        "supported_forbidden": True,
        "verdict": verdict,
    }


def _parasite_founders(census: int = PHASE3_CENSUS) -> AntagonistPopulation:
    windows = [_DISTINCT_WINDOWS[index % len(_DISTINCT_WINDOWS)] for index in range(int(census))]
    return AntagonistPopulation.founders(
        windows,
        keep_fraction=float(STRUCT_KEEP_FRACTION),
        mutation_rate=float(STRUCT_PARASITE_MUTATION),
    )


def _clone_population(pop: AntagonistPopulation) -> AntagonistPopulation:
    units = [replace(unit) for unit in pop.units]
    return AntagonistPopulation(
        units=units,
        seat_cap=int(pop.seat_cap),
        ancestral_windows=list(pop.ancestral_windows),
        keep_fraction=float(pop.keep_fraction),
        mutation_rate=float(pop.mutation_rate),
        fecundity=float(pop.fecundity),
        maintenance_cost=float(pop.maintenance_cost),
    )


def install_locked_hosts(arm: StructuralRQArm, seats: Sequence[Mapping[str, str]]) -> None:
    """Put the locked genomes back. Does not touch the parasite population.

    ATP is the structural birth reserve so contact energy is shared and a
    debit cannot delete a genotype before the next generation's contact.
    """

    if not seats:
        raise ConfigurationError("locked host mix is empty")
    patches = list(arm.food_patches)
    if not patches:
        raise ConfigurationError("host mix requires the shared food patches")
    organisms: list[GenesisOrganism] = []
    roles: dict[str, str] = {"parasite_stock": ROLE_SECONDARY}
    seen: set[str] = set()
    for index, seat in enumerate(seats):
        host_id = str(seat["host_id"])
        if host_id in seen:
            raise ConfigurationError(f"duplicate locked host id {host_id}")
        seen.add(host_id)
        genome = str(seat["genome"])
        if genome == str(seat["window"]) or len(genome) <= 6:
            raise ConfigurationError("locked host must be a genome, not a class label")
        organism = GenesisOrganism.from_bits(
            host_id,
            genome,
            initial_runtime_atp=float(STRUCT_BIRTH_ATP),
            position=patches[index % len(patches)],
        )
        if _window(organism) != str(seat["window"]):
            raise ConfigurationError("installed genome does not decode to its window")
        silence_outcross_locus(organism, arm.runner.configs.closed_loop_hp_life)
        organisms.append(organism)
        roles[host_id] = ROLE_PRIMARY
    arm.runner.population = replace(
        arm.runner.population,
        organisms=tuple(organisms),
    )
    arm.roles = roles


def build_phase3_arm(
    seed: int,
    branch: str,
    seats: Sequence[Mapping[str, str]],
    founders: AntagonistPopulation,
) -> StructuralRQArm:
    """One branch from the shared parasite founders. Host mix is held fixed."""

    key = str(branch)
    if key not in BRANCHES:
        raise ConfigurationError(f"unknown phase-3 branch {branch!r}")
    arm = build_arm(ARM_A, int(seed))
    arm.stream_root = STREAM_ROOT
    arm.stream_history = str(int(seed))
    arm.freeze_host_genotypic_inheritance()
    if key == BRANCH_LOCKED:
        arm.passage = PASSAGE_FROZEN
    else:
        arm.passage = PASSAGE_COEVOLVE
    if arm.passage == "shuffled_labels":
        raise ConfigurationError("phase-3 passage must not be shuffled_labels")
    pop = _clone_population(founders)
    if key == BRANCH_LOCKED:
        # Inheritance off: the frozen passage already forces mutation rate 0
        # inside ``advance``. The stored rate stays the shared value so the
        # control is the mode, not a second parameter.
        pop.mutation_rate = float(STRUCT_PARASITE_MUTATION)
    arm.antagonist_pop = pop
    arm.parasite_windows = pop.windows()
    captured = [dict(seat) for seat in seats]

    def _hold(target: StructuralRQArm) -> None:
        install_locked_hosts(target, captured)

    arm.host_composition_hold = _hold
    install_locked_hosts(arm, captured)
    return arm


def _parasite_rows(pop: AntagonistPopulation) -> list[dict[str, object]]:
    rows = [
        {
            "born_generation": int(unit.born_generation),
            "energy": float(unit.energy),
            "parent_id": unit.parent_id,
            "unit_id": unit.unit_id,
            "window": unit.window,
        }
        for unit in pop.units
    ]
    rows.sort(key=lambda row: str(row["unit_id"]))
    return cast(list[dict[str, object]], rows)


def _archive_line(arm: StructuralRQArm, *, seed: int, branch: str, generation: int) -> dict[str, object]:
    pop = arm.antagonist_pop
    if not isinstance(pop, AntagonistPopulation):
        raise ConfigurationError("phase-3 archive requires the antagonist population")
    ledger = pop.ledgers[-1]
    account = pop.energy_accounts[-1]
    if abs(account.residual()) > 1e-6:
        raise ConfigurationError(f"energy residual {account.residual()} at generation {generation}")
    windows = tuple(arm.last_contact_host_windows)
    return {
        "branch": str(branch),
        "contact_credit": float(account.contact_income),
        "contact_host_windows": list(windows),
        "contacts": int(ledger.contacts),
        "generation": int(generation),
        "host_inheritance": arm.host_inheritance,
        "mutation_events": int(ledger.mutation_events),
        "parasite_births_seated": len(ledger.newborns),
        "parasite_deaths": len(ledger.deaths),
        "parasites": _parasite_rows(pop),
        "passage": arm.passage,
        "red_queen_proved": False,
        "reproduction_cost": float(account.reproduction_cost),
        "schema": ARCHIVE_SCHEMA,
        "seed": int(seed),
    }


def _expected_counts(seats: Sequence[Mapping[str, str]]) -> Counter[str]:
    return Counter(str(seat["window"]) for seat in seats)


def run_branch(
    *,
    seed: int,
    branch: str,
    seats: Sequence[Mapping[str, str]],
    founders: AntagonistPopulation,
    generations: int,
    archive_path: Path,
) -> dict[str, object]:
    """Condition one branch. Stops on a mix or energy bug and keeps the file."""

    arm = build_phase3_arm(seed, branch, seats, founders)
    expected = _expected_counts(seats)
    archive_path.parent.mkdir(parents=True, exist_ok=True)
    handle = archive_path.open("a", encoding="utf-8")
    completed = 0
    reason: str | None = None
    try:
        for generation in range(1, int(generations) + 1):
            try:
                arm.run_generations(1)
                seen = Counter(arm.last_contact_host_windows)
                if seen != expected:
                    reason = (
                        f"host mix drifted at generation {generation}: "
                        f"seen={dict(seen)} expected={dict(expected)}"
                    )
                    break
                if branch == BRANCH_LOCKED:
                    pop = arm.antagonist_pop
                    assert isinstance(pop, AntagonistPopulation)
                    if int(pop.ledgers[-1].mutation_events) != 0:
                        reason = f"locked branch mutated at generation {generation}"
                        break
                    founder_counts = Counter(unit.window for unit in founders.units)
                    if Counter(pop.windows()) != founder_counts:
                        reason = f"locked genotype composition changed at generation {generation}"
                        break
                row = _archive_line(arm, seed=seed, branch=branch, generation=generation)
            except Exception as exc:
                reason = f"{type(exc).__name__}: {exc}"
                break
            handle.write(json.dumps(row, sort_keys=True, separators=(",", ":")))
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
            completed = generation
    finally:
        handle.close()
    pop = arm.antagonist_pop
    assert isinstance(pop, AntagonistPopulation)
    newborns = [len(ledger.newborns) for ledger in pop.ledgers]
    contacts = [int(ledger.contacts) for ledger in pop.ledgers]
    return {
        "branch": str(branch),
        "completed": completed,
        "contacts": contacts,
        "failed": reason,
        "newborns": newborns,
        "passage": arm.passage,
        "red_queen_proved": False,
    }


def pure_host_rows(window: str, genome: str, n: int, *, label: str) -> list[dict[str, object]]:
    """Assay hosts: one real genome, repeated, standard energy applied by infectivity."""

    if genome == window or len(genome) <= 6:
        raise ConfigurationError("assay host must be a genome, not a class label")
    if not genome.endswith(window):
        raise ConfigurationError("assay genome does not end in its window")
    rows: list[dict[str, object]] = []
    for index in range(int(n)):
        rows.append(
            {
                "genome": genome,
                "id": f"assay-{label}-{index:03d}",
                "runtime_atp": float(STRUCT_BIRTH_ATP),
                "window": window,
            }
        )
    return rows


def assay_parasites(
    parasites: Sequence[Mapping[str, object]],
    *,
    window_a: str,
    genome_a: str,
    window_b: str,
    genome_b: str,
) -> dict[str, object]:
    """Score the same parasites on A and on B through ``replay_archived_contact``.

    The input list is copied by ``infectivity``. Callers that pass a file's
    bytes must compare those bytes themselves; this function does not open them.
    """

    copied = [dict(row) for row in parasites]
    if not copied:
        return {
            "I_A": None,
            "I_B": None,
            "contacts_A": 0,
            "contacts_B": 0,
            "evolution": False,
            "red_queen_proved": False,
        }
    hosts_a = pure_host_rows(window_a, genome_a, len(copied), label="A")
    hosts_b = pure_host_rows(window_b, genome_b, len(copied), label="B")
    # infectivity uses atp override and the engine debit path.
    i_a = infectivity(hosts_a, copied)
    i_b = infectivity(hosts_b, copied)
    # A second call on fresh copies must not have needed the first call's objects.
    scored_a = replay_archived_contact(
        [dict(row) for row in hosts_a],
        [dict(row) for row in copied],
        atp_override=float(STRUCT_BIRTH_ATP),
        tick_index=0,
    )
    if scored_a["evolution"] or scored_a["reproduction"] or scored_a["mutation"]:
        raise ConfigurationError("assay left evolution on")
    if scored_a["archive_mutated"]:
        raise ConfigurationError("assay mutated its input copies")
    return {
        "I_A": i_a,
        "I_B": i_b,
        "contacts_A": same_int(scored_a["contacts"]) if i_a is not None else 0,
        "contacts_B": None if i_b is None else "measured",
        "credit_A": scored_a["credit"],
        "debit_A": scored_a["debit"],
        "evolution": False,
        "mutation": False,
        "red_queen_proved": False,
        "reproduction": False,
        "scale": float(STRUCT_VIRULENCE) * float(STRUCT_STEAL_FRACTION),
    }


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_last(path: Path) -> dict[str, object]:
    last: dict[str, object] | None = None
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                parsed = json.loads(line)
                if isinstance(parsed, dict):
                    last = parsed
    if last is None:
        raise ConfigurationError(f"archive is empty: {path}")
    return last


def assay_archive(
    archive_path: Path,
    *,
    window_a: str,
    genome_a: str,
    window_b: str,
    genome_b: str,
) -> dict[str, object]:
    """Assay the final archived parasites. The archive bytes stay put."""

    before = archive_path.read_bytes()
    last = _load_last(archive_path)
    parasites = last.get("parasites")
    if not isinstance(parasites, list):
        raise ConfigurationError("archive parasites are missing")
    scored = assay_parasites(
        parasites,
        window_a=window_a,
        genome_a=genome_a,
        window_b=window_b,
        genome_b=genome_b,
    )
    after = archive_path.read_bytes()
    if after != before:
        raise ConfigurationError("assay modified the conditioning archive")
    scored["archive_sha256"] = hashlib.sha256(before).hexdigest()
    scored["archive_unchanged"] = True
    return scored


def _write_json(path: Path, body: Mapping[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(body, sort_keys=True, indent=2) + "\n", encoding="utf-8")


def run_phase3_seed(
    seed: int,
    root: Path,
    *,
    generations: int,
    window_a: str,
    window_b: str,
    genome_a: str,
    genome_b: str,
) -> dict[str, object]:
    """Three branches from one parasite initial state. No D is computed here."""

    assert_phase3_seeds([int(seed)])
    if int(generations) < 1:
        raise ConfigurationError("generations must be >= 1")
    founders = _parasite_founders()
    seed_dir = root / "by_seed" / f"seed{int(seed)}"
    seed_dir.mkdir(parents=True, exist_ok=True)
    _write_json(
        seed_dir / "initial.json",
        {
            "genome_a": genome_a,
            "genome_b": genome_b,
            "parasites": _parasite_rows(founders),
            "red_queen_proved": False,
            "seed": int(seed),
            "window_a": window_a,
            "window_b": window_b,
        },
    )
    seats = {
        BRANCH_COMMON_A: build_host_seats(window_a, window_b, common="A"),
        BRANCH_COMMON_B: build_host_seats(window_a, window_b, common="B"),
        BRANCH_LOCKED: build_host_seats(window_a, window_b, common="A"),
    }
    branch_summaries: dict[str, object] = {}
    failed: str | None = None
    for branch in BRANCHES:
        archive = seed_dir / branch / "archive.jsonl"
        if archive.exists() and archive.stat().st_size > 0:
            # A restarted call must not destroy a partial archive.
            failed = f"archive already exists: {archive}"
            break
        summary = run_branch(
            seed=int(seed),
            branch=branch,
            seats=seats[branch],
            founders=founders,
            generations=int(generations),
            archive_path=archive,
        )
        branch_summaries[branch] = summary
        if summary["failed"] or same_int(summary["completed"]) != same_int(generations):
            failed = str(summary["failed"] or "incomplete")
            (seed_dir / "REASON.txt").write_text(
                f"seed={seed} branch={branch} completed={summary['completed']} reason={failed}\n",
                encoding="utf-8",
            )
            break
    if failed:
        return {
            "branches": branch_summaries,
            "failed": failed,
            "red_queen_proved": False,
            "seed": int(seed),
        }
    assays: dict[str, object] = {}
    for branch in BRANCHES:
        archive = seed_dir / branch / "archive.jsonl"
        scored = assay_archive(
            archive,
            window_a=window_a,
            genome_a=genome_a,
            window_b=window_b,
            genome_b=genome_b,
        )
        assays[branch] = scored
        _write_json(seed_dir / branch / "assay.json", scored)
    (seed_dir / "COMPLETE").write_text(
        f"generations={int(generations)} red_queen_proved=false\n",
        encoding="utf-8",
    )
    return {
        "assays": assays,
        "branches": branch_summaries,
        "failed": None,
        "red_queen_proved": False,
        "seed": int(seed),
    }


def _seed_estimand(seed_dir: Path) -> dict[str, object]:
    def _i(branch: str, key: str) -> float | None:
        path = seed_dir / branch / "assay.json"
        if not path.is_file():
            return None
        body = json.loads(path.read_text(encoding="utf-8"))
        value = body.get(key)
        if value is None:
            return None
        return float(value)

    i_a_ca = _i(BRANCH_COMMON_A, "I_A")
    i_b_ca = _i(BRANCH_COMMON_A, "I_B")
    i_a_cb = _i(BRANCH_COMMON_B, "I_A")
    i_b_cb = _i(BRANCH_COMMON_B, "I_B")
    i_a_locked = _i(BRANCH_LOCKED, "I_A")
    i_b_locked = _i(BRANCH_LOCKED, "I_B")
    return {
        "D": estimand_d(i_a_ca, i_b_ca, i_a_cb, i_b_cb),
        "I_A_common_a": i_a_ca,
        "I_A_common_b": i_a_cb,
        "I_A_locked": i_a_locked,
        "I_B_common_a": i_b_ca,
        "I_B_common_b": i_b_cb,
        "I_B_locked": i_b_locked,
        "control_gap": control_gap(i_a_locked, i_b_locked),
        "red_queen_proved": False,
    }


def analyze_phase3(root: Path, locked_seeds: Sequence[int] = PHASE3_SEEDS) -> dict[str, object]:
    """Read assay files. Missing archives are dropped, not filled with zero."""

    by_seed: dict[int, dict[str, object]] = {}
    present: list[int] = []
    for seed in locked_seeds:
        seed_dir = root / "by_seed" / f"seed{int(seed)}"
        if not (seed_dir / "COMPLETE").is_file():
            continue
        present.append(int(seed))
        by_seed[int(seed)] = _seed_estimand(seed_dir)
    # Seeds with no directory stay absent so assess marks them dropped.
    report = assess_phase3(by_seed, locked_seeds)
    report["by_seed"] = {str(seed): by_seed[seed] for seed in present}
    report["red_queen_proved"] = False
    _write_json(root / "summary.json", report)
    return report


def _worker(payload: dict[str, object]) -> dict[str, object]:
    return run_phase3_seed(
        same_int(payload["seed"]),
        Path(str(payload["root"])),
        generations=same_int(payload["generations"]),
        window_a=str(payload["window_a"]),
        window_b=str(payload["window_b"]),
        genome_a=str(payload["genome_a"]),
        genome_b=str(payload["genome_b"]),
    )


def execute_phase3(
    root: Path,
    *,
    generations: int,
    window_a: str,
    window_b: str,
    genome_a: str,
    genome_b: str,
    workers: int | None = None,
    seeds: Sequence[int] = PHASE3_SEEDS,
) -> dict[str, object]:
    """Run the locked histories. Workers are at most 4. Does not prove Red Queen."""

    assert_phase3_seeds(seeds)
    n_workers = resolve_workers(workers)
    root.mkdir(parents=True, exist_ok=True)
    payloads = [
        {
            "genome_a": genome_a,
            "genome_b": genome_b,
            "generations": int(generations),
            "root": str(root),
            "seed": int(seed),
            "window_a": window_a,
            "window_b": window_b,
        }
        for seed in seeds
    ]
    results: list[dict[str, object]] = []
    if n_workers == 1:
        for payload in payloads:
            results.append(_worker(payload))
    else:
        with ProcessPoolExecutor(max_workers=n_workers) as pool:
            futures = [pool.submit(_worker, payload) for payload in payloads]
            for future in as_completed(futures):
                results.append(future.result())
    report = analyze_phase3(root, seeds)
    report["results"] = results
    report["workers"] = n_workers
    report["red_queen_proved"] = False
    report["stream_policy"] = ARM_STREAM_POLICY["policy_id"]
    _write_json(root / "summary.json", {k: v for k, v in report.items() if k != "results"})
    if any(item.get("failed") for item in results):
        report["stopped"] = True
    return report


def run_selection(root: Path) -> dict[str, object]:
    """Seed 9500 only. Chooses genomes and the horizon. Does not compute measurement D."""

    assert_phase3_seeds([PHASE3_SELECTION_SEED], selection=True)
    rows = recognition_table()
    chosen = choose_host_pair(rows)
    window_a = str(chosen["window_first"])
    window_b = str(chosen["window_second"])
    genome_a = str(chosen["genome_first"])
    genome_b = str(chosen["genome_second"])
    seats = build_host_seats(window_a, window_b, common="A")
    founders = _parasite_founders()
    probe_dir = root / "probe" / BRANCH_COMMON_A
    archive = probe_dir / "archive.jsonl"
    if archive.exists():
        raise ConfigurationError("selection probe archive already exists; not deleting it")
    probe = run_branch(
        seed=PHASE3_SELECTION_SEED,
        branch=BRANCH_COMMON_A,
        seats=seats,
        founders=founders,
        generations=PROBE_GENERATIONS,
        archive_path=archive,
    )
    if probe["failed"]:
        body = {
            "failed": probe["failed"],
            "measurement_D": None,
            "measurement_histories_run": False,
            "red_queen_proved": False,
            "seed": PHASE3_SELECTION_SEED,
        }
        _write_json(root / "selection.json", body)
        raise ConfigurationError(f"selection probe stopped: {probe['failed']}")
    newborns = [same_int(value) for value in same_iter(probe["newborns"])]
    contacts = [same_int(value) for value in same_iter(probe["contacts"])]
    measurable = bool(contacts) and all(value > 0 for value in contacts) and bool(newborns)
    mean_newborns = float(sum(newborns) / len(newborns)) if newborns else 0.0
    horizon = horizon_from_turnover(
        mean_newborns=mean_newborns,
        census=PHASE3_CENSUS,
        measurable=measurable,
    )
    # Exemplar ids are the first seat of each genome, not class names.
    first_a = next(seat for seat in seats if seat["window"] == window_a)
    first_b = next(seat for seat in seats if seat["window"] == window_b)
    body = {
        "chosen_pair": {
            "exemplar_id_a": first_a["host_id"],
            "exemplar_id_b": first_b["host_id"],
            "genome_a": genome_a,
            "genome_b": genome_b,
            "outcross_cost_a": chosen["outcross_cost_first"],
            "outcross_cost_b": chosen["outcross_cost_second"],
            "recognition_gap": chosen["recognition_gap"],
            "shared_prefix": chosen["shared_prefix"],
            "window_a": window_a,
            "window_b": window_b,
        },
        "horizon": horizon,
        "measurement_D": None,
        "measurement_histories_run": False,
        "no_measurement_d_sentence": NO_MEASUREMENT_D_SENTENCE,
        "probe": {
            "contacts_per_generation": contacts,
            "generations": PROBE_GENERATIONS,
            "mean_seated_newborns": mean_newborns,
            "newborns_per_generation": newborns,
            "seed": PHASE3_SELECTION_SEED,
        },
        "recognition_rows": len(rows),
        "red_queen_proved": False,
        "seed": PHASE3_SELECTION_SEED,
        "workers_cap": MAX_WORKERS,
    }
    _write_json(root / "selection.json", body)
    _write_json(probe_dir / "probe_summary.json", probe)
    return body


def render_phase3_lock(selection: Mapping[str, object], *, code_commit: str) -> str:
    """Lock text. Refuses a measurement D if one was stuffed into the selection."""

    if selection.get("measurement_histories_run"):
        raise ConfigurationError("lock refuses a selection that already ran measurement histories")
    if selection.get("measurement_D") not in (None,):
        raise ConfigurationError("lock refuses a measurement D")
    chosen = selection["chosen_pair"]
    horizon = selection["horizon"]
    if not isinstance(chosen, dict) or not isinstance(horizon, dict):
        raise ConfigurationError("selection is missing the pair or the horizon")
    lines = [
        "# Phase-3 lock",
        "",
        NO_MEASUREMENT_D_SENTENCE,
        "No generation of seeds 9501, 9502, 9503, or 9504 has been run.",
        "This file is the lock, written before any phase-3 measurement history.",
        "`red_queen_proved` is false. This is not a Red Queen claim.",
        "A positive D would not be Red Queen.",
        "",
        f"Code commit: `{code_commit}` on branch `rq/mechanism-v2`.",
        "Nothing has been pushed, merged, or rebased.",
        "`runs/rq-bidirectional-timeshift-01` is untouched and is not part of this commit.",
        "",
        "## Genotypes",
        "",
        "Chosen from the seed-9500 selection experiment, not from a measurement D.",
        f"Window A: `{chosen['window_a']}`",
        f"Window B: `{chosen['window_b']}`",
        f"Exemplar id A: `{chosen['exemplar_id_a']}`",
        f"Exemplar id B: `{chosen['exemplar_id_b']}`",
        f"Genome A: `{chosen['genome_a']}`",
        f"Genome B: `{chosen['genome_b']}`",
        f"Shared prefix: `{chosen['shared_prefix']}`",
        f"Outcross cost A: {chosen['outcross_cost_a']}",
        f"Outcross cost B: {chosen['outcross_cost_b']}",
        f"Engine recognition gap (parasite window = A, one host): {chosen['recognition_gap']}",
        "That gap is the instrument difference, not D.",
        "",
        "## Horizon",
        "",
        f"Conditioning generations: {horizon['conditioning_generations']}",
        f"Replacement generations: {horizon['replacement_generations']}",
        f"Mean seated newborns on the 9500 probe: {horizon['mean_seated_newborns']}",
        f"Census: {horizon['census']}",
        f"Turnover multiple, pre-declared: {horizon['turnover_multiple']}",
        str(horizon["generation_time"]),
        "The horizon was not chosen from the sign of D.",
        "",
        "## Seeds and rules",
        "",
        "Measurement histories: 9501, 9502, 9503, 9504.",
        "Selection seed 9500 is not a measurement history and is not reused as one.",
        "Forbidden and not used: 9099, 9101-9104, 9201-9224, 9301-9304, 9401, structural pilot seeds 601, 602, 603.",
        IMPORTANCE_RULE,
        "SUPPORTED is forbidden.",
        f"`MEASUREMENT_FLOOR` stays {MEASUREMENT_FLOOR} and is not lowered. It is not the importance bound.",
        "If a locked seed is missing or unmeasurable, the verdict is BLOCKED_MEASUREMENT, not a negative on the reduced sample.",
        "Unmeasurable is missing, not zero.",
        "CPU workers at most 7.",
        "Output: `runs/rq-mechanism-v2/phase3-frequency/`.",
        "Raw archives are kept. A partial run is kept. The seed is not replaced.",
        "`red_queen_proved` stays false.",
        "",
        NO_MEASUREMENT_D_SENTENCE,
        "",
    ]
    text = "\n".join(lines)
    if "D =" in text or "D=" in text:
        raise ConfigurationError("lock text must not contain a D formula result")
    return text


def founder_window_counter(census: int = PHASE3_CENSUS) -> tuple[tuple[str, int], ...]:
    windows = [_DISTINCT_WINDOWS[index % len(_DISTINCT_WINDOWS)] for index in range(int(census))]
    return tuple(sorted(Counter(windows).items()))
