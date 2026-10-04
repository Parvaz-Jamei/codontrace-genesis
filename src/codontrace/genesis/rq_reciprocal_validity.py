"""Reciprocal-validity assay. Validity gates first.

A positive result is not the end condition. ``red_queen_proved`` is not a
caller argument and is not read from a row. Literature, prediction, control,
estimand, and limit are in ``runs/rq-reciprocal-validity/LITERATURE.md``.
No confirmatory number is computed in this module's constants.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence

from codontrace.errors import ConfigurationError
from codontrace.genesis.rq_mechanism_v2_phase5 import (
    VERDICT_BLOCKED,
    _binary_verdict,
    assert_measurement_floor,
    direction_reversal,
    lineage_relative_fitness,
    wilson_interval,
)

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
