"""Discovery questions 2026-09-28 — ENGINE closed-loop JSONL campaign.

Real GenesisEngine + GenerationBoundaryObserver path for Ideas 4 and 2.
Output under outputs/.../jsonl_engine/ — distinct from harness jsonl_campaign/.
Claim ceiling phase2_design; hypothesis_supported=False; red_queen_proved=False.
Sealed seeds 801–816 refused. Volume ≠ discovery.
"""

from __future__ import annotations

import json
import os
import time
from collections.abc import Mapping, Sequence
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from typing import Any, Literal

from codontrace._types import JsonValue
from codontrace.dynvalues import same_float, same_int
from codontrace.errors import ConfigurationError
from codontrace.genesis.campaigns.discovery_q_20260928_idea2_engine import (
    IDEA2_ENGINE_CELLS,
    run_idea2_engine_cell,
)
from codontrace.genesis.campaigns.discovery_q_20260928_idea4 import (
    CLAIM_CEILING as IDEA4_CLAIM_CEILING,
)
from codontrace.genesis.campaigns.discovery_q_20260928_idea4 import (
    OPS_CELLS,
    T_INTERVENE_GRID,
)
from codontrace.genesis.campaigns.discovery_q_20260928_idea4_engine import (
    aggregate_idea4_engine_rates,
    run_idea4_engine_cell,
)
from codontrace.genesis.campaigns.discovery_q_20260928_measurement import (
    assert_record_not_a_discovery,
)

SCHEMA = "discovery_q_20260928_jsonl_engine_v1"
CLAIM_CEILING = "phase2_design"
# Pilot seeds: non-sealed, small N to prove observer fires + seed variance.
DEFAULT_PILOT_SEEDS: tuple[int, ...] = tuple(range(301, 313))  # 12 seeds
DEFAULT_FULL_SEEDS: tuple[int, ...] = tuple(range(301, 365))  # 64 seeds (301–364)
SEALED_SEED_LO = 801
SEALED_SEED_HI = 816
IDEA_IDS: tuple[Literal[4, 2], ...] = (4, 2)

# Pilot reduced factorial (still ≥3 t_tilde points on T=40).
PILOT_OPS_CELLS: tuple[str, ...] = (
    "control",
    "scramble_contacts",
    "cut_named_scaffold",
    "ablate_knowledge_digest",
)
PILOT_T_INTERVENE: tuple[int, ...] = (10, 20, 30)
PILOT_IDEA2_CELLS: tuple[str, ...] = ("baseline", "pi_deception")

HONESTY = (
    "Engine closed-loop JSONL under sealed Idea4+Idea2 phase-2 design meters. "
    "GenerationBoundaryObserver on GenesisEngine life-loop; not harness theater. "
    "Ledger skeleton via build_engine_scaffold_ledger / "
    "build_idea2_engine_scaffold_ledger (scaffold-only; no recovery_progress path). "
    "Volume ≠ discovery. claim_ceiling remains phase2_design; "
    "hypothesis_supported and red_queen_proved stay false. "
    "Distinct from outputs/.../jsonl_campaign/ (ecf7148 harness-only)."
)


def _assert_ceiling_locked() -> None:
    if CLAIM_CEILING != "phase2_design":
        raise ConfigurationError("engine campaign claim ceiling must stay phase2_design.")
    if IDEA4_CLAIM_CEILING != CLAIM_CEILING:
        raise ConfigurationError("idea4 engine ceiling must match phase2_design.")


def validate_engine_seeds(seeds: Sequence[int]) -> tuple[int, ...]:
    if not seeds:
        raise ConfigurationError("jsonl engine campaign requires at least one seed.")
    out: list[int] = []
    seen: set[int] = set()
    for raw in seeds:
        seed = int(raw)
        if SEALED_SEED_LO <= seed <= SEALED_SEED_HI:
            raise ConfigurationError(
                f"seed {seed} is in sealed campaign range "
                f"{SEALED_SEED_LO}–{SEALED_SEED_HI}; refuse."
            )
        if seed in seen:
            continue
        seen.add(seed)
        out.append(seed)
    return tuple(out)


def nproc_reported() -> int:
    reported = os.cpu_count()
    return int(reported) if reported and reported > 0 else 1


def default_output_dir(repo_root: Path | None = None) -> Path:
    root = repo_root if repo_root is not None else Path.cwd()
    return (
        root / "outputs" / "campaigns" / "discovery_questions_20260928" / "jsonl_engine"
    )


def _jobs_idea4(
    seeds: Sequence[int],
    *,
    ops_cells: Sequence[str],
    t_intervene: Sequence[int],
) -> list[tuple[Any, ...]]:
    jobs: list[tuple[Any, ...]] = []
    for seed in seeds:
        for cell in ops_cells:
            for t_int in t_intervene:
                jobs.append(("idea4", int(seed), str(cell), int(t_int)))
    return jobs


def _jobs_idea2(
    seeds: Sequence[int],
    *,
    cells: Sequence[str],
) -> list[tuple[Any, ...]]:
    return [
        ("idea2", int(seed), str(cell))
        for seed in seeds
        for cell in cells
    ]


def _run_job(job: tuple[Any, ...]) -> list[dict[str, JsonValue]]:
    kind = job[0]
    if kind == "idea4":
        _, seed, ops_cell, t_int = job
        rec = run_idea4_engine_cell(
            seed=int(seed),
            ops_cell=str(ops_cell),
            t_intervene=int(t_int),
        )
        return [rec]
    if kind == "idea2":
        _, seed, cell = job
        return list(run_idea2_engine_cell(seed=int(seed), cell=str(cell)))
    raise ConfigurationError(f"unknown job kind {kind!r}.")



def _idea2_arm_cell_survival_stats(
    idea2_recs: list[dict[str, JsonValue]],
    *,
    cell: str,
    arm: str,
) -> dict[str, Any]:
    """Unique survival_to_T values for one (cell, arm); collapse when n_unique==1."""

    subset = [
        r
        for r in idea2_recs
        if str(r.get("cell")) == cell and str(r.get("arm")) == arm
    ]
    vals = sorted({round(same_float(r["survival_to_T"]), 8) for r in subset})
    return {
        "cell": cell,
        "arm": arm,
        "n_records": len(subset),
        "n_unique_survival_to_T": len(vals),
        "min_survival_to_T": vals[0] if vals else None,
        "max_survival_to_T": vals[-1] if vals else None,
        "collapse_unique_surv_eq_1": bool(vals) and len(vals) == 1,
        "soft_pass": False,  # never soft-pass a collapse
        "note": (
            "Honest collapse report under phase2_design; "
            "unique_surv==1 is FAIL evidence, not a soft-pass."
            if vals and len(vals) == 1
            else "Descriptive unique-survival stats only; not a discovery claim."
        ),
    }


def _idea4_alive_end_stats(idea4_recs: list[dict[str, JsonValue]]) -> dict[str, Any]:
    """Honest n_alive_end==0 rate (ecology extinction / empty end state)."""

    n = len(idea4_recs)
    if n == 0:
        return {
            "n_records": 0,
            "n_alive_end_eq_0": 0,
            "rate_alive_end_eq_0": None,
            "note": "no idea4 records",
        }
    n_zero = sum(1 for r in idea4_recs if same_float(r.get("n_alive_end", 0.0)) == 0.0)
    rate = float(n_zero) / float(n)
    return {
        "n_records": n,
        "n_alive_end_eq_0": n_zero,
        "rate_alive_end_eq_0": rate,
        "high_rate_warn": rate >= 0.5,
        "note": (
            "High n_alive_end==0 rate reported honestly under phase2_design; "
            "not soft-passed as recovery evidence."
            if rate >= 0.5
            else "Descriptive n_alive_end==0 rate only; not a discovery claim."
        ),
    }


def run_jsonl_engine_campaign(
    *,
    seeds: Sequence[int] | None = None,
    idea_ids: Sequence[int] | None = None,
    out_dir: Path | None = None,
    max_workers: int | None = None,
    parallel: bool = True,
    pilot: bool = True,
    ops_cells: Sequence[str] | None = None,
    t_intervene: Sequence[int] | None = None,
    idea2_cells: Sequence[str] | None = None,
) -> dict[str, Any]:
    """Run engine closed-loop Idea4(+Idea2) campaign; write JSONL + manifest."""

    _assert_ceiling_locked()
    use_seeds = validate_engine_seeds(
        seeds
        if seeds is not None
        else (DEFAULT_PILOT_SEEDS if pilot else DEFAULT_FULL_SEEDS)
    )
    use_ideas = tuple(int(i) for i in (idea_ids if idea_ids is not None else IDEA_IDS))
    for idea_id in use_ideas:
        if idea_id not in (4, 2):
            raise ConfigurationError(f"unsupported idea_id {idea_id!r}; only 4 or 2.")

    use_ops = tuple(
        ops_cells
        if ops_cells is not None
        else (PILOT_OPS_CELLS if pilot else OPS_CELLS)
    )
    use_t = tuple(
        t_intervene
        if t_intervene is not None
        else (PILOT_T_INTERVENE if pilot else T_INTERVENE_GRID)
    )
    if len(use_t) < 3:
        raise ConfigurationError("engine Idea4 requires >=3 t_intervene points.")
    use_i2 = tuple(
        idea2_cells
        if idea2_cells is not None
        else (PILOT_IDEA2_CELLS if pilot else IDEA2_ENGINE_CELLS)
    )

    jobs: list[tuple[Any, ...]] = []
    if 4 in use_ideas:
        jobs.extend(_jobs_idea4(use_seeds, ops_cells=use_ops, t_intervene=use_t))
    if 2 in use_ideas:
        jobs.extend(_jobs_idea2(use_seeds, cells=use_i2))

    workers = 1
    if parallel:
        import os
        cap = os.cpu_count() or 1
        workers = min(cap, int(max_workers) if max_workers else cap)
        workers = max(1, workers)

    t0 = time.perf_counter()
    records: list[dict[str, JsonValue]] = []
    if workers == 1 or not parallel:
        for job in jobs:
            records.extend(_run_job(job))
    else:
        # Process pool: GenesisEngine is CPU-bound under the GIL; threads do not
        # scale. _run_job is a top-level function so workers can receive it.
        with ProcessPoolExecutor(max_workers=workers) as pool:
            for batch in pool.map(_run_job, jobs, chunksize=1):
                records.extend(batch)
    wall = float(time.perf_counter() - t0)

    out = default_output_dir() if out_dir is None else Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    jsonl_path = out / "idea4_idea2_jsonl_engine.jsonl"
    with jsonl_path.open("w", encoding="utf-8") as fh:
        for rec in records:
            if rec.get("hypothesis_supported") is not False:
                raise ConfigurationError("hypothesis_supported must be False.")
            if rec.get("red_queen_proved") is not False:
                raise ConfigurationError("red_queen_proved must be False.")
            if rec.get("claim_ceiling") != CLAIM_CEILING:
                raise ConfigurationError("claim_ceiling must stay phase2_design.")
            assert_record_not_a_discovery(rec)
            fh.write(json.dumps(rec, sort_keys=True) + "\n")

    idea4_recs = [r for r in records if same_int(r.get("idea_id", -1)) == 4]
    idea2_recs = [r for r in records if same_int(r.get("idea_id", -1)) == 2]
    aggregates = aggregate_idea4_engine_rates(idea4_recs)

    # Seed variance proof on at least one metric (baseline_mean_rare_yield).
    variance_proof: dict[str, Any] = {"ok": False, "metric": None, "n_unique": 0}
    if idea4_recs:
        metric = "baseline_mean_rare_yield"
        # Fix cell+t for fair comparison across seeds.
        subset = [
            r
            for r in idea4_recs
            if r.get("ops_cell") == "control" and same_int(r.get("t_intervene", -1)) == 10
        ]
        vals = sorted({round(same_float(r[metric]), 8) for r in subset})
        variance_proof = {
            "ok": len(vals) >= 2,
            "metric": metric,
            "ops_cell": "control",
            "t_intervene": 10,
            "n_seeds_in_subset": len(subset),
            "n_unique": len(vals),
            "min": vals[0] if vals else None,
            "max": vals[-1] if vals else None,
            "observer_fires_min": min(same_int(r["observer_fire_count"]) for r in idea4_recs),
            "observer_fires_expected": same_int(idea4_recs[0]["tick_count"]),
        }

    pattern_pi_survival = _idea2_arm_cell_survival_stats(
        idea2_recs, cell="pi_deception", arm="pattern"
    )
    alive_end_stats = _idea4_alive_end_stats(idea4_recs)
    idea2_unique_surv_by_arm_cell: dict[str, Any] = {}
    for cell_name in use_i2 if 2 in use_ideas else ():
        for arm_name in ("gene", "pattern", "causal"):
            key = f"{cell_name}|{arm_name}"
            idea2_unique_surv_by_arm_cell[key] = _idea2_arm_cell_survival_stats(
                idea2_recs, cell=str(cell_name), arm=arm_name
            )

    manifest: dict[str, Any] = {
        "schema": SCHEMA,
        "claim_ceiling": CLAIM_CEILING,
        "hypothesis_supported": False,
        "red_queen_proved": False,
        "honesty": HONESTY,
        "pilot": bool(pilot),
        "seed_lo": use_seeds[0],
        "seed_hi": use_seeds[-1],
        "n_runs_seeds": len(use_seeds),
        "seeds": list(use_seeds),
        "idea_ids": list(use_ideas),
        "idea4_ops_cells": list(use_ops),
        "idea4_t_intervene": list(use_t),
        "idea2_cells": list(use_i2) if 2 in use_ideas else [],
        "n_records": len(records),
        "n_records_idea4": len(idea4_recs),
        "n_records_idea2": len(idea2_recs),
        "jsonl_path": str(jsonl_path),
        "nproc_reported": nproc_reported(),
        "max_workers": workers,
        "wall_time_s": wall,
        "aggregates_idea4": aggregates,
        "variance_proof": variance_proof,
        "idea2_pattern_pi_unique_survival": pattern_pi_survival,
        "idea2_unique_survival_by_arm_cell": idea2_unique_surv_by_arm_cell,
        "idea4_n_alive_end_stats": alive_end_stats,
        "ledger_builders": {
            "idea4": "build_engine_scaffold_ledger",
            "idea2": "build_idea2_engine_scaffold_ledger",
            "smoke_aliases_harness_only": True,
            "recovery_progress_multiplier_used": False,
        },
        "harness_jsonl_campaign_not_discovery": True,
        "output_subdir": "jsonl_engine",
    }
    manifest_path = out / "idea4_idea2_jsonl_engine_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    manifest["manifest_path"] = str(manifest_path)
    return manifest


def jsonl_engine_constants() -> Mapping[str, Any]:
    return {
        "schema": SCHEMA,
        "claim_ceiling": CLAIM_CEILING,
        "hypothesis_supported": False,
        "red_queen_proved": False,
        "default_pilot_seeds": list(DEFAULT_PILOT_SEEDS),
        "default_full_seeds": list(DEFAULT_FULL_SEEDS),
        "pilot_ops_cells": list(PILOT_OPS_CELLS),
        "pilot_t_intervene": list(PILOT_T_INTERVENE),
        "pilot_idea2_cells": list(PILOT_IDEA2_CELLS),
        "output_subdir": "jsonl_engine",
        "sealed_seed_range": [SEALED_SEED_LO, SEALED_SEED_HI],
    }
