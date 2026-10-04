"""Reciprocal-validity assay. Validity gates first.

A positive result is not the end condition. ``red_queen_proved`` is not a
caller argument and is not read from a row. Literature, prediction, control,
estimand, and limit are in ``runs/rq-reciprocal-validity/LITERATURE.md``.
No confirmatory number is computed in this module's constants.
"""

from __future__ import annotations

import hashlib
import json
import math
import threading
import time
from collections.abc import Mapping, Sequence
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import replace
from pathlib import Path

from codontrace.errors import ConfigurationError
from codontrace.genesis.closed_loop_hp_arm01 import _window
from codontrace.genesis.closed_loop_hp_arm01_structural_rq import STRUCT_SOFT_K
from codontrace.genesis.closed_loop_pearl_spc import PASSAGE_ABSENT, PASSAGE_COEVOLVE
from codontrace.genesis.rq_bidirectional_timeshift import ARM_A, build_arm
from codontrace.genesis.rq_bidirectional_timeshift_confirm import infectivity
from codontrace.genesis.rq_mechanism_v2_phase4 import (
    GENOME_A,
    GENOME_B,
    WINDOW_A,
    WINDOW_B,
    _clone_parasites,
    enable_outcross_birth_chamber,
    equal_host_seats,
    install_equal_hosts,
    load_conditioned_parasites,
    population_from_parasite_rows,
)
from codontrace.genesis.rq_mechanism_v2_phase5 import (
    VERDICT_BLOCKED,
    _arm_rows,
    _binary_verdict,
    _people,
    _statistical_verdict,
    _worker,
    assert_measurement_floor,
    direction_reversal,
    genotype_frequency,
    lineage_relative_fitness,
    replay_phase5_archive,
    resolve_workers,
    run_phase5_history,
    sampling_interval,
    wilson_interval,
)
from codontrace.genesis.rq_mechanism_v2_phase6 import replacement_time

TARGET_QUANTITY = "paired_infectivity_margin"


def _json_ready(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)


def _generation_body(row: Mapping[str, object]) -> dict[str, object]:
    """Scientific fields of one generation. Identity keys are not part of the body."""

    skipped = {"history_id", "seed", "evidence_id"}
    return {str(key): row[key] for key in sorted(row) if key not in skipped}


def _content_digest(generations: Sequence[Mapping[str, object]]) -> str:
    payload = [_generation_body(row) for row in generations]
    return hashlib.sha256(_json_ready(payload).encode("utf-8")).hexdigest()


def _as_generations(history: Mapping[str, object]) -> list[Mapping[str, object]]:
    raw = history.get("generations")
    if not isinstance(raw, list) or not raw:
        raise ConfigurationError("a history needs generation rows")
    rows: list[Mapping[str, object]] = []
    seen: set[int] = set()
    for item in raw:
        if not isinstance(item, Mapping):
            raise ConfigurationError("a generation row must be a mapping")
        if "generation" not in item:
            raise ConfigurationError("a generation row needs a generation")
        generation = item["generation"]
        if isinstance(generation, bool) or not isinstance(generation, int):
            raise ConfigurationError("generation must be an integer")
        if generation in seen:
            raise ConfigurationError("duplicate generations")
        seen.add(generation)
        rows.append(item)
    return rows


def extract_fitness_witness(history: Mapping[str, object]) -> dict[str, object]:
    """Lineage fitness from generation rows. A boolean label is not a witness.

    The keys ``fitness_measured`` and ``reversal`` are ignored on purpose.
    """

    generations = _as_generations(history)
    last = generations[-1]
    births = last.get("host_births")
    deaths = last.get("host_deaths")
    windows = last.get("start_windows")
    if not isinstance(births, list) or not isinstance(deaths, list) or not isinstance(windows, list):
        return {"measured": False, "relative": None, "source": "archive", "used_boolean_label": False}
    relative = lineage_relative_fitness([str(item) for item in windows], births, deaths)
    return {
        "measured": bool(relative["measured"]),
        "relative": relative,
        "source": "archive",
        "used_boolean_label": False,
    }


def extract_reversal_witness(history: Mapping[str, object]) -> dict[str, object]:
    """A sign change of archived gaps. A boolean ``reversal`` label is not read."""

    generations = _as_generations(history)
    gaps: list[float | None] = []
    for row in generations:
        raw = row.get("selection_gap")
        if raw is None:
            gaps.append(None)
            continue
        if isinstance(raw, bool) or not isinstance(raw, (int, float)):
            return {"measured": False, "reversal": None, "source": "archive", "used_boolean_label": False}
        gaps.append(float(raw))
    present = [gap for gap in gaps if gap is not None]
    if len(present) < 2:
        return {"measured": False, "reversal": None, "source": "archive", "used_boolean_label": False}
    changed = direction_reversal(present[-1], present[0])
    if changed is None:
        return {"measured": False, "reversal": None, "source": "archive", "used_boolean_label": False}
    return {
        "measured": True,
        "reversal": bool(changed),
        "source": "archive",
        "used_boolean_label": False,
    }


def assess_independent_histories(
    histories: Sequence[Mapping[str, object]],
    locked_seeds: Sequence[int],
    *,
    importance_bound: float | None,
) -> dict[str, object]:
    """n counts independent valid histories. Repeated rows cannot make n = 12.

    Duplicate seeds, duplicate ``history_id`` values, duplicate generation
    rows, and two histories with the same generation body are errors.
    Fitness and reversal come from ``extract_fitness_witness`` and
    ``extract_reversal_witness``. ``red_queen_proved`` is false.
    """

    floor = assert_measurement_floor()
    locked = tuple(int(seed) for seed in locked_seeds)
    if len(locked) != len(set(locked)):
        raise ConfigurationError("duplicate seeds")
    if len(locked) < floor:
        raise ConfigurationError("locked history count is below MEASUREMENT_FLOOR")
    by_seed: dict[int, Mapping[str, object]] = {}
    seen_ids: dict[str, int] = {}
    seen_body: dict[str, int] = {}
    for history in histories:
        if "seed" not in history or "history_id" not in history:
            raise ConfigurationError("a history needs a seed and a history_id")
        seed = history["seed"]
        history_id = history["history_id"]
        if isinstance(seed, bool) or not isinstance(seed, int):
            raise ConfigurationError("seed must be an integer")
        if not isinstance(history_id, str) or not history_id:
            raise ConfigurationError("history_id must be a non-empty string")
        generations = _as_generations(history)
        if history_id in seen_ids:
            raise ConfigurationError("duplicate history_id")
        seen_ids[history_id] = seed
        digest = _content_digest(generations)
        if digest in seen_body:
            raise ConfigurationError("duplicate history")
        seen_body[digest] = seed
        if seed in by_seed:
            raise ConfigurationError("duplicate seeds")
        by_seed[seed] = history
    valid: list[int] = []
    fitness_true = 0
    reversal_true = 0
    dropped: list[int] = []
    for seed in locked:
        history = by_seed.get(seed)
        if history is None:
            dropped.append(seed)
            continue
        fitness = extract_fitness_witness(history)
        reversal = extract_reversal_witness(history)
        if not fitness["measured"] or not reversal["measured"]:
            dropped.append(seed)
            continue
        valid.append(seed)
        if bool(fitness["relative"]["measured"]):  # type: ignore[index]
            fitness_true += 1
        if reversal["reversal"] is True:
            reversal_true += 1
    n_independent = len(valid)
    # Two copies never reach this count: they raise above. A short valid set
    # is not padded to the measurement floor.
    if n_independent > len(locked):
        raise ConfigurationError("independent histories exceed the locked seeds")
    interval = None
    verdict = VERDICT_BLOCKED
    if n_independent == len(locked) and n_independent >= floor:
        interval = wilson_interval(reversal_true, n_independent)
        verdict = _binary_verdict(interval, importance_bound)
    return {
        "dropped_seeds": dropped,
        "fitness_witness_n": fitness_true if n_independent else 0,
        "importance_bound": None if importance_bound is None else float(importance_bound),
        "interval": interval,
        "measurement_floor": floor,
        "n_independent": n_independent,
        "n_locked": len(locked),
        "red_queen_proved": False,
        "reversal_true_n": reversal_true if n_independent == len(locked) else None,
        "supported_forbidden": importance_bound is None,
        "target_quantity": TARGET_QUANTITY,
        "used_boolean_label": False,
        "verdict": verdict,
    }


PHASE3_PARASITE_SOURCE = "runs/rq-mechanism-v2/phase3-frequency/by_seed/seed9501/common_a/archive.jsonl"
PHASE3_SWAP_SEED = 9883
PHASE3_SERIES_ABSENT = 9881
PHASE3_SERIES_PRESSURE = 9882
SWAP_NAMES = (
    "baseline",
    "processing_order",
    "ids",
    "position",
    "food_access",
    "genome_background",
)


def selection_direction(births_a: int, births_b: int, deaths_a: int, deaths_b: int) -> dict[str, object]:
    """Signs of reproduction and survival. A tie is null, not a zero effect."""

    def _sign(left: int, right: int) -> int | None:
        if int(left) == int(right):
            return None
        return 1 if int(left) > int(right) else -1

    return {
        "birth_sign_a_minus_b": _sign(births_a, births_b),
        "death_sign_a_minus_b": _sign(deaths_a, deaths_b),
    }


def which_swap_moves(baseline: Mapping[str, int], swapped: Mapping[str, Mapping[str, int]]) -> dict[str, object]:
    """A swap moves the effect when an id-letter birth count changes."""

    moved = []
    for name, counts in swapped.items():
        if int(counts["births_A"]) != int(baseline["births_A"]) or int(counts["births_B"]) != int(baseline["births_B"]):
            moved.append(str(name))
    return {"baseline_births_A": int(baseline["births_A"]), "baseline_births_B": int(baseline["births_B"]), "moved": moved}


def _id_letter(host_id: str) -> str:
    if "-A-" in host_id:
        return "A"
    if "-B-" in host_id:
        return "B"
    return "other"


def swapped_seats(name: str, seats: Sequence[Mapping[str, str]]) -> list[dict[str, str]]:
    """One factor. Food access reassigns patch index. It does not rename ids."""

    rows = [dict(seat) for seat in seats]
    if name in {"baseline", "processing_order", "position"}:
        return rows
    if name == "ids":
        counts = {"A": 0, "B": 0}
        renamed = []
        for seat in rows:
            letter = str(seat["role_letter"])
            other = "B" if letter == "A" else "A"
            counts[other] += 1
            renamed.append(
                {
                    "genome": str(seat["genome"]),
                    "host_id": f"host-{other}-{counts[other]:03d}",
                    "role_letter": letter,
                    "window": str(seat["window"]),
                }
            )
        return renamed
    if name == "food_access":
        class_a = [seat for seat in rows if seat["role_letter"] == "A"]
        class_b = [seat for seat in rows if seat["role_letter"] == "B"]
        mixed: list[dict[str, str]] = []
        for left, right in zip(class_b, class_a, strict=True):
            mixed.append(dict(left))
            mixed.append(dict(right))
        return mixed
    if name == "genome_background":
        flipped = []
        for seat in rows:
            letter = str(seat["role_letter"])
            other = "B" if letter == "A" else "A"
            flipped.append(
                {
                    "genome": GENOME_B if letter == "A" else GENOME_A,
                    "host_id": str(seat["host_id"]),
                    "role_letter": letter,
                    "window": WINDOW_B if letter == "A" else WINDOW_A,
                }
            )
        return flipped
    raise ConfigurationError(f"unknown swap {name}")


def build_swap_arm(seed: int, seats: Sequence[Mapping[str, str]], parasites: object, *, passage: str):
    """Absent or pressured arm. Does not use the phase-4 seed gate."""

    if int(seed) in {9501, 9502, 9503, 9504}:
        raise ConfigurationError("phase-3 diagnostic must not reuse a phase-4 measurement seed")
    arm = build_arm(ARM_A, int(seed))
    arm.stream_root = "RQ-RECIPROCAL-VALIDITY"
    arm.stream_history = str(int(seed))
    arm.host_composition_hold = None
    configs = arm.runner.configs
    arm.runner.configs = replace(configs, mutation=replace(configs.mutation, bit_flip_rate=0.0))
    if str(passage) == PASSAGE_ABSENT:
        arm.passage = PASSAGE_ABSENT
    elif str(passage) == PASSAGE_COEVOLVE:
        arm.passage = PASSAGE_COEVOLVE
    else:
        raise ConfigurationError("phase-3 passage is absent or coevolve")
    pop = _clone_parasites(parasites)  # type: ignore[arg-type]
    arm.antagonist_pop = pop
    arm.parasite_windows = pop.windows()
    install_equal_hosts(arm, seats)
    enable_outcross_birth_chamber(arm)
    return arm


def _tally_generation(arm: object) -> dict[str, object]:
    start = {str(org.id): _window(org) for org in arm._hosts()}  # type: ignore[attr-defined]
    before = {rec.organism_id for rec in arm.runner.population.lineage}  # type: ignore[attr-defined]
    arm.run_generations(1)  # type: ignore[attr-defined]
    births_id = {"A": 0, "B": 0, "other": 0}
    births_window: dict[str, int] = {}
    parent_ids: list[str] = []
    for rec in arm.runner.population.lineage:  # type: ignore[attr-defined]
        if rec.organism_id in before or not rec.parent_id or int(rec.generation) == 0:
            continue
        parent_ids.append(str(rec.parent_id))
        births_id[_id_letter(str(rec.parent_id))] += 1
        parent_window = start.get(str(rec.parent_id))
        if parent_window is None:
            births_window["unresolved"] = births_window.get("unresolved", 0) + 1
        else:
            births_window[parent_window] = births_window.get(parent_window, 0) + 1
    end_ids = {str(org.id) for org in arm._hosts()}  # type: ignore[attr-defined]
    deaths = [host_id for host_id in start if host_id not in end_ids]
    deaths_id = {"A": 0, "B": 0, "other": 0}
    for host_id in deaths:
        deaths_id[_id_letter(host_id)] += 1
    living_windows: dict[str, int] = {}
    for org in arm._hosts():  # type: ignore[attr-defined]
        window = _window(org)
        living_windows[window] = living_windows.get(window, 0) + 1
    contacts = int(arm.graded_contact_count[-1]) if arm.graded_contact_count else 0  # type: ignore[attr-defined]
    return {
        "births_A": births_id["A"],
        "births_B": births_id["B"],
        "births_by_id": births_id,
        "births_by_parent_window": births_window,
        "contacts": contacts,
        "parent_ids": parent_ids,
        "deaths_A": deaths_id["A"],
        "deaths_B": deaths_id["B"],
        "direction": selection_direction(births_id["A"], births_id["B"], deaths_id["A"], deaths_id["B"]),
        "living_windows": living_windows,
    }


def _load_phase3_parasites():
    rows, digest, generation = load_conditioned_parasites(Path(PHASE3_PARASITE_SOURCE))
    return population_from_parasite_rows(rows), digest, generation


def run_swap_factorial(root: Path, *, seed: int = PHASE3_SWAP_SEED) -> dict[str, object]:
    """One generation of each swap on the absent passage. The source archive is only read."""

    parasites, digest, generation = _load_phase3_parasites()
    base_seats = equal_host_seats()
    results: dict[str, object] = {}
    for name in SWAP_NAMES:
        seats = swapped_seats(name, base_seats)
        arm = build_swap_arm(seed, seats, parasites, passage=PASSAGE_ABSENT)
        if name == "processing_order":
            arm.runner.population = replace(
                arm.runner.population,
                organisms=tuple(reversed(arm.runner.population.organisms)),
            )
        if name == "position":
            hosts = list(arm._hosts())
            by_suffix: dict[str, list] = {}
            for org in hosts:
                suffix = str(org.id).split("-")[-1]
                by_suffix.setdefault(suffix, []).append(org)
            for group in by_suffix.values():
                if len(group) == 2:
                    group[0].position, group[1].position = group[1].position, group[0].position
        tally = _tally_generation(arm)
        tally["swap"] = name
        results[name] = tally
    baseline = results["baseline"]
    assert isinstance(baseline, Mapping)
    moved = which_swap_moves(
        {"births_A": int(baseline["births_A"]), "births_B": int(baseline["births_B"])},
        {
            name: {"births_A": int(results[name]["births_A"]), "births_B": int(results[name]["births_B"])}  # type: ignore[index]
            for name in SWAP_NAMES
            if name != "baseline"
        },
    )
    # Pressure on the unswapped seats. Contact is recorded and is not the direction.
    pressured = build_swap_arm(seed, base_seats, parasites, passage=PASSAGE_COEVOLVE)
    pressure_tally = _tally_generation(pressured)
    absent_direction = baseline["direction"]
    pressure_direction = pressure_tally["direction"]
    direction_changed = absent_direction != pressure_direction
    payload = {
        "direction_changed_by_parasites": bool(direction_changed),
        "parasite_source_generation": int(generation),
        "parasite_source_sha256": digest,
        "pressure": pressure_tally,
        "red_queen_proved": False,
        "seed": int(seed),
        "source_archive_rewritten": False,
        "swaps": results,
        "which_swap_moves_id_births": moved,
    }
    root.mkdir(parents=True, exist_ok=True)
    (root / "swaps.json").write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return payload



def summarize_selection_rows(rows: Sequence[Mapping[str, object]]) -> list[dict[str, object]]:
    """Frequency, pressure, survival, and both fitnesses. Contact is not the direction."""

    series: list[dict[str, object]] = []
    for row in rows:
        births = row.get("host_births")
        deaths = row.get("host_deaths")
        hosts = row.get("hosts")
        start = row.get("start_windows")
        if not isinstance(births, list) or not isinstance(deaths, list) or not isinstance(hosts, list):
            series.append({"generation": row.get("generation"), "measured": False})
            continue
        births_a = sum(1 for item in births if isinstance(item, Mapping) and _id_letter(str(item.get("parent_id"))) == "A")
        births_b = sum(1 for item in births if isinstance(item, Mapping) and _id_letter(str(item.get("parent_id"))) == "B")
        deaths_a = sum(1 for item in deaths if _id_letter(str(item)) == "A")
        deaths_b = sum(1 for item in deaths if _id_letter(str(item)) == "B")
        windows = [str(item["window"]) for item in hosts if isinstance(item, Mapping) and "window" in item]
        current = genotype_frequency(windows)
        founder = lineage_relative_fitness(
            [str(item) for item in start] if isinstance(start, list) else None,
            births,
            deaths,
        )
        # Founder-lineage fitness uses the id letter, not the living window.
        start_hosts = row.get("start_hosts")
        founder_counts = {"A": 0, "B": 0}
        if isinstance(start_hosts, list):
            for item in start_hosts:
                if isinstance(item, Mapping):
                    founder_counts[_id_letter(str(item.get("id")))] = founder_counts.get(_id_letter(str(item.get("id"))), 0) + 1
        founder_fitness = {}
        birth_total = births_a + births_b
        for letter, count in founder_counts.items():
            if letter not in {"A", "B"} or count <= 0:
                continue
            if birth_total == 0:
                founder_fitness = None
                break
            births_letter = births_a if letter == "A" else births_b
            founder_fitness[letter] = (births_letter / birth_total) / (count / float(sum(founder_counts[k] for k in ("A", "B"))))
        series.append(
            {
                "contacts": row.get("contacts"),
                "current_genotype_frequency": current,
                "current_genotype_fitness": founder["by_window"] if founder["measured"] else None,
                "direction": selection_direction(births_a, births_b, deaths_a, deaths_b),
                "founder_lineage_fitness": founder_fitness,
                "generation": row.get("generation"),
                "measured": True,
            }
        )
    return series


def run_selection_series(root: Path, *, generations: int = 8) -> dict[str, object]:
    """Absent versus coevolve. A negative direction change stays negative."""

    absent_root = root / "absent"
    pressure_root = root / "pressure"
    absent = run_phase5_history(
        PHASE3_SERIES_ABSENT,
        str(absent_root),
        int(generations),
        arms=("coevolve",),
        compare_one_shot=False,
        passage_override=PASSAGE_ABSENT,
    )
    pressure = run_phase5_history(
        PHASE3_SERIES_PRESSURE,
        str(pressure_root),
        int(generations),
        arms=("coevolve",),
        compare_one_shot=False,
    )
    absent_rows = []
    pressure_rows = []
    for line in (absent_root / "by_seed" / f"seed{PHASE3_SERIES_ABSENT}" / "archive.jsonl").read_text().splitlines():
        if line.strip():
            absent_rows.append(json.loads(line))
    pressure_path = pressure_root / "by_seed" / f"seed{PHASE3_SERIES_PRESSURE}" / "archive.jsonl"
    for line in pressure_path.read_text().splitlines():
        if line.strip():
            pressure_rows.append(json.loads(line))
    absent_series = summarize_selection_rows(absent_rows)
    pressure_series = summarize_selection_rows(pressure_rows)
    changed = []
    for left, right in zip(absent_series, pressure_series, strict=False):
        if left.get("measured") and right.get("measured") and left.get("direction") != right.get("direction"):
            changed.append(left.get("generation"))
    payload = {
        "absent": absent,
        "absent_series": absent_series,
        "direction_changed_generations": changed,
        "generations": int(generations),
        "pressure": pressure,
        "pressure_series": pressure_series,
        "red_queen_proved": False,
    }
    (root / "series.json").write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return payload



PILOT_SEEDS = (9901, 9902, 9903)
SHORT_SEED = 9904
CONFIRM_SEEDS = tuple(range(9911, 9923))
# One bit of affinity is 1/6. One such seat among STRUCT_SOFT_K contact seats.
IMPORTANCE_BOUND = (1.0 / 6.0) / float(STRUCT_SOFT_K)
MATRIX_TIMES = ("past", "present", "future")
NO_CONFIRMATORY_SENTENCE = "No confirmatory number has been computed."


def _roster_windows(people: Sequence[Mapping[str, object]] | None) -> tuple[str, ...] | None:
    if not people:
        return None
    return tuple(sorted(str(person["window"]) for person in people))


def response_diversity_fixation(rows: Sequence[Mapping[str, object]]) -> dict[str, object]:
    """Response time, diversity, and fixation. A side that never changes stays missing."""

    if not rows:
        raise ConfigurationError("pilot rows are empty")
    ordered = sorted(rows, key=lambda row: int(row["generation"]))
    first_hosts = _roster_windows(_people(ordered[0], "hosts"))
    first_parasites = _roster_windows(_people(ordered[0], "parasites"))
    host_response = None
    parasite_response = None
    for row in ordered:
        if host_response is None and _roster_windows(_people(row, "hosts")) != first_hosts:
            host_response = int(row["generation"])
        if parasite_response is None and _roster_windows(_people(row, "parasites")) != first_parasites:
            parasite_response = int(row["generation"])
    last_hosts = _people(ordered[-1], "hosts") or []
    last_parasites = _people(ordered[-1], "parasites") or []
    host_windows = [str(person["window"]) for person in last_hosts]
    parasite_windows = [str(person["window"]) for person in last_parasites]
    def _fixed(windows: list[str]) -> bool | None:
        if not windows:
            return None
        return len(set(windows)) == 1

    return {
        "host_diversity": len(set(host_windows)) if host_windows else None,
        "host_fixed": _fixed(host_windows),
        "host_response_generation": host_response,
        "parasite_diversity": len(set(parasite_windows)) if parasite_windows else None,
        "parasite_fixed": _fixed(parasite_windows),
        "parasite_response_generation": parasite_response,
    }


def choose_reciprocal_horizon(
    *,
    parasite_replacement: float | None,
    host_replacement: float | None,
    fitness_delay: float | None,
) -> dict[str, object]:
    """Max of the measured times. A missing time stays missing. The horizon is not shortened."""

    if parasite_replacement is None or host_replacement is None:
        raise ConfigurationError("replacement time is missing; it is not filled with zero")
    parasite = float(parasite_replacement)
    host = float(host_replacement)
    if parasite <= 0.0 or host <= 0.0 or not math.isfinite(parasite) or not math.isfinite(host):
        raise ConfigurationError("replacement time must be positive and finite")
    delay = None if fitness_delay is None else float(fitness_delay)
    if delay is not None and (delay <= 0.0 or not math.isfinite(delay)):
        raise ConfigurationError("fitness delay must be positive or null")
    horizon = max(math.ceil(parasite), math.ceil(host))
    if delay is not None:
        horizon = max(horizon, math.ceil(delay))
    lag = max(1, int(round(parasite)))
    if lag >= horizon or horizon - 2 * lag < 1:
        raise ConfigurationError("lag does not leave past, present, and future inside the horizon")
    return {
        "budget": int(horizon),
        "fitness_delay": delay,
        "fitness_delay_unmeasurable": delay is None,
        "future_generation": int(horizon),
        "horizon": int(horizon),
        "host_replacement": host,
        "importance_bound": IMPORTANCE_BOUND,
        "parasite_replacement": parasite,
        "past_generation": int(horizon - 2 * lag),
        "present_generation": int(horizon - lag),
        "primary_lag": int(lag),
        "turnover_multiple_used": False,
    }


def matrix_cells(
    rows: Sequence[Mapping[str, object]],
    *,
    arm: str,
    past: int,
    present: int,
    future: int,
) -> dict[str, float | None]:
    """Past/present/future hosts by past/present/future parasites. Missing stays null."""

    mapped = _arm_rows(rows, arm)
    times = {"past": int(past), "present": int(present), "future": int(future)}
    cells: dict[str, float | None] = {}
    for host_name, host_gen in times.items():
        host_row = mapped.get(host_gen)
        hosts = None if host_row is None else _people(host_row, "hosts")
        for parasite_name, parasite_gen in times.items():
            parasite_row = mapped.get(parasite_gen)
            parasites = None if parasite_row is None else _people(parasite_row, "parasites")
            key = f"{host_name}_host__{parasite_name}_parasite"
            if not hosts or not parasites:
                cells[key] = None
            else:
                cells[key] = infectivity(hosts, parasites)
    return cells


def matrix_margins(cells: Mapping[str, float | None]) -> dict[str, float | None]:
    """Same trait on both sides. A missing cell makes that margin missing."""

    def _margin(focal: float | None, left: float | None, right: float | None) -> float | None:
        if focal is None or left is None or right is None:
            return None
        return float(focal) - (float(left) + float(right)) / 2.0

    focal = cells.get("present_host__present_parasite")
    return {
        "host_margin": _margin(
            focal,
            cells.get("present_host__past_parasite"),
            cells.get("present_host__future_parasite"),
        ),
        "parasite_margin": _margin(
            focal,
            cells.get("past_host__present_parasite"),
            cells.get("future_host__present_parasite"),
        ),
        "target_quantity": TARGET_QUANTITY,
    }


def assess_matrix_scores(
    scores: Sequence[Mapping[str, object]],
    locked_seeds: Sequence[int],
    *,
    importance_bound: float,
) -> dict[str, object]:
    """n is independent valid histories. A boolean label is not read."""

    floor = assert_measurement_floor()
    if abs(float(importance_bound) - IMPORTANCE_BOUND) > 1e-15:
        raise ConfigurationError("importance bound is the locked seat quantum")
    locked = tuple(int(seed) for seed in locked_seeds)
    if len(locked) != len(set(locked)):
        raise ConfigurationError("duplicate seeds")
    if len(locked) < floor:
        raise ConfigurationError("locked history count is below MEASUREMENT_FLOOR")
    by_seed: dict[int, Mapping[str, object]] = {}
    seen_ids: set[str] = set()
    seen_body: set[str] = set()
    for score in scores:
        seed = int(score["seed"])
        history_id = str(score["history_id"])
        if history_id in seen_ids:
            raise ConfigurationError("duplicate history_id")
        seen_ids.add(history_id)
        body = _content_digest([{"generation": 1, "margins": score.get("margins"), "matrix": score.get("matrix")}])
        if body in seen_body:
            raise ConfigurationError("duplicate history")
        seen_body.add(body)
        if seed in by_seed:
            raise ConfigurationError("duplicate seeds")
        by_seed[seed] = score
    host_values: list[float] = []
    parasite_values: list[float] = []
    both_positive = 0
    dropped: list[int] = []
    for seed in locked:
        score = by_seed.get(seed)
        if score is None:
            dropped.append(seed)
            continue
        margins = score.get("margins")
        if not isinstance(margins, Mapping):
            dropped.append(seed)
            continue
        host_margin = margins.get("host_margin")
        parasite_margin = margins.get("parasite_margin")
        if host_margin is None or parasite_margin is None:
            dropped.append(seed)
            continue
        host_values.append(float(host_margin))
        parasite_values.append(float(parasite_margin))
        if float(host_margin) > 0.0 and float(parasite_margin) > 0.0:
            both_positive += 1
    blocked = len(dropped) > 0 or len(host_values) != len(locked)
    report: dict[str, object] = {
        "binary_index": None,
        "dropped_seeds": dropped,
        "host_margin": None,
        "importance_bound": float(importance_bound),
        "measurement_floor": floor,
        "n_independent": 0 if blocked else len(host_values),
        "n_locked": len(locked),
        "parasite_margin": None,
        "red_queen_proved": False,
        "supported_forbidden": False,
        "target_quantity": TARGET_QUANTITY,
        "used_boolean_label": False,
        "verdict": VERDICT_BLOCKED,
    }
    if blocked:
        return report
    host_interval = sampling_interval(host_values)
    parasite_interval = sampling_interval(parasite_values)
    binary = wilson_interval(both_positive, len(locked))
    host_verdict = _statistical_verdict(host_interval, importance_bound)
    parasite_verdict = _statistical_verdict(parasite_interval, importance_bound)
    binary_verdict = _binary_verdict(binary, importance_bound)
    # Both continuous margins must clear the seat quantum. The rate is separate.
    if host_verdict == "NEGATIVE" or parasite_verdict == "NEGATIVE":
        verdict = "NEGATIVE"
    elif host_verdict == "SUPPORTED" and parasite_verdict == "SUPPORTED":
        verdict = "SUPPORTED"
    else:
        verdict = "INCONCLUSIVE"
    report.update(
        {
            "binary_index": {"interval": binary, "k": both_positive, "verdict": binary_verdict},
            "host_margin": {"interval": host_interval, "verdict": host_verdict},
            "n_independent": len(host_values),
            "parasite_margin": {"interval": parasite_interval, "verdict": parasite_verdict},
            "verdict": verdict,
        }
    )
    return report


def render_confirm_lock(design: Mapping[str, object], *, code_commit: str) -> str:
    """First sentence is the required sentence. No confirmatory mean is included."""

    lines = [
        NO_CONFIRMATORY_SENTENCE,
        "",
        f"Code commit: `{code_commit}`.",
        "This lock is not a confirmatory result.",
        "",
        "Primary estimand, same infectivity trait on both antagonists:",
        "`I(present hosts, present parasites) - mean(I(present hosts, past parasites), I(present hosts, future parasites))`",
        "and",
        "`I(present hosts, present parasites) - mean(I(past hosts, present parasites), I(future hosts, present parasites))`.",
        "A missing cell stays missing. The two margins are not added.",
        "Reversal of two fixed genotypes is not this estimand. The other matrix cells are exploratory.",
        "",
        f"Past generation: {design['past_generation']}. Present: {design['present_generation']}. Future: {design['future_generation']}.",
        f"Horizon: {design['horizon']}. Lag: {design['primary_lag']}. Budget: {design['budget']}. The horizon was not shortened.",
        f"Host replacement: {design['host_replacement']}. Parasite replacement: {design['parasite_replacement']}.",
        f"Fitness delay: {design['fitness_delay']}. Unmeasurable: {design['fitness_delay_unmeasurable']}.",
        f"Importance bound: {design['importance_bound']}. It is one bit of affinity (1/6) on one of {int(STRUCT_SOFT_K)} seats.",
        "It was not taken from a confirmatory mean. SUPPORTED requires both continuous lower bounds to clear it.",
        "The binary index is the count of histories where both margins are positive. Its interval is Wilson, equation (4) of Brown, Cai, and DasGupta 2001.",
        "The binary index is not the continuous margin. 0/n and n/n keep the endpoint.",
        f"`MEASUREMENT_FLOOR` stays {int(assert_measurement_floor())}. Workers at most 7.",
        f"Seeds: {CONFIRM_SEEDS[0]} through {CONFIRM_SEEDS[-1]}.",
        "Pilot seeds 9901-9903 and short seed 9904 are not in that list.",
        "`red_queen_proved` is not set from this criterion.",
        "",
        NO_CONFIRMATORY_SENTENCE,
        "",
    ]
    return "\n".join(lines)



def _read_jsonl(path: Path) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            parsed = json.loads(line)
            if isinstance(parsed, dict):
                rows.append(parsed)
    return rows


def _coevolve_rows(path: Path) -> list[dict[str, object]]:
    return [row for row in _read_jsonl(path) if row.get("arm") == "coevolve"]


def run_pilot(root: Path, *, generations: int = 12) -> dict[str, object]:
    """Exploratory pilot. These seeds are not the confirmatory."""

    root.mkdir(parents=True, exist_ok=True)
    per_seed = []
    for seed in PILOT_SEEDS:
        outcome = run_phase5_history(
            seed,
            str(root),
            int(generations),
            arms=("coevolve",),
            compare_one_shot=False,
        )
        archive = root / "by_seed" / f"seed{seed}" / "archive.jsonl"
        rows = _coevolve_rows(archive)
        measured = response_diversity_fixation(rows)
        host_births = [len(row.get("host_births") or []) for row in rows]
        host_census = [len(row.get("hosts") or []) for row in rows]
        parasite_births = [int(row.get("parasite_births") or 0) for row in rows]
        parasite_census = [int(row.get("parasite_census") or 0) for row in rows]
        per_seed.append(
            {
                "failed": outcome["failed"],
                "host_replacement": replacement_time(host_births, host_census),
                "measured": measured,
                "parasite_replacement": replacement_time(parasite_births, parasite_census),
                "seed": seed,
            }
        )
    payload = {"exploratory": True, "generations": int(generations), "red_queen_proved": False, "seeds": per_seed}
    (root / "pilot_summary.json").write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return payload


def run_short(root: Path, *, generations: int = 4) -> dict[str, object]:
    """One-shot versus resume, then replay. Not a confirmatory."""

    outcome = run_phase5_history(
        SHORT_SEED,
        str(root),
        int(generations),
        arms=("coevolve", "adaptation_cut", "constant_parasite"),
        compare_one_shot=True,
    )
    archive = root / "by_seed" / f"seed{SHORT_SEED}" / "archive.jsonl"
    replay = replay_phase5_archive(archive) if archive.is_file() else {"matched": False, "reason": "missing archive"}
    payload = {"failed": outcome["failed"], "red_queen_proved": False, "replay": replay, "seed": SHORT_SEED}
    root.mkdir(parents=True, exist_ok=True)
    (root / "short_summary.json").write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return payload


def score_confirmatory_archives(root: Path, design: Mapping[str, object]) -> list[dict[str, object]]:
    """Matrix margins from archives. Controls use the same cells."""

    scores = []
    for seed in CONFIRM_SEEDS:
        archive = root / "by_seed" / f"seed{seed}" / "archive.jsonl"
        rows = _read_jsonl(archive)
        arms = {}
        for arm in ("coevolve", "adaptation_cut", "constant_parasite"):
            cells = matrix_cells(
                rows,
                arm=arm,
                past=int(design["past_generation"]),
                present=int(design["present_generation"]),
                future=int(design["future_generation"]),
            )
            arms[arm] = {"cells": cells, "margins": matrix_margins(cells)}
        primary = arms["coevolve"]["margins"]
        scores.append(
            {
                "arms": arms,
                "history_id": f"rq-reciprocal-{seed}",
                "margins": primary,
                "matrix": arms["coevolve"]["cells"],
                "seed": seed,
            }
        )
    return scores


def _health_loop(path: Path, stop: threading.Event) -> None:
    while not stop.wait(600):
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(f"health ts={time.time()} red_queen_proved=false\n")


def run_confirmatory(root: Path, *, generations: int, workers: int = 7) -> dict[str, object]:
    """Fresh seeds. Stops on a history failure. Does not retune."""

    if int(generations) < 1:
        raise ConfigurationError("confirmatory generations must be positive")
    workers_used = resolve_workers(workers)
    root.mkdir(parents=True, exist_ok=True)
    health = root / "health.log"
    stop = threading.Event()
    thread = threading.Thread(target=_health_loop, args=(health, stop), daemon=True)
    thread.start()
    jobs = [
        {
            "arms": ["coevolve", "adaptation_cut", "constant_parasite"],
            "compare_one_shot": True,
            "generations": int(generations),
            "passage_override": None,
            "root": str(root),
            "seed": seed,
        }
        for seed in CONFIRM_SEEDS
    ]
    failed = []
    try:
        with ProcessPoolExecutor(max_workers=workers_used) as pool:
            futures = [pool.submit(_worker, job) for job in jobs]
            for future in as_completed(futures):
                outcome = future.result()
                if outcome.get("failed"):
                    failed.append(outcome)
                    (root / "STOP").write_text(str(outcome["failed"]) + "\n", encoding="utf-8")
    finally:
        stop.set()
    return {"failed": failed, "red_queen_proved": False, "workers": workers_used}
