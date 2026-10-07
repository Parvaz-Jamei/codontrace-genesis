"""Discovery questions 2026-09-28 — scored JSONL Track C (Ideas 1, 3, 5, 6).

Genuine multi-cell N=run campaign under claim ceiling phase2_design.
Structurally separate from the Idea4+Idea2 jsonl_campaign. Volume ≠ discovery:
every record keeps hypothesis_supported=False and red_queen_proved=False.
Soft-pass forbidden. Sealed seeds 801–816 refused. Default seeds 401–464
avoid 201–264 and 301–364. Scaffold builders only (not smoke aliases).
"""

from __future__ import annotations

import json
import os
import time
from collections.abc import Mapping, Sequence
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, Literal

from codontrace._types import JsonValue
from codontrace.dynvalues import same_int
from codontrace.errors import ConfigurationError
from codontrace.genesis.campaigns.discovery_q_20260928_idea1 import (
    CLAIM_CEILING as IDEA1_CLAIM_CEILING,
)
from codontrace.genesis.campaigns.discovery_q_20260928_idea1 import (
    IDEA1_SCORED_CELLS,
    run_idea1_scored_cell,
)
from codontrace.genesis.campaigns.discovery_q_20260928_idea3 import (
    CLAIM_CEILING as IDEA3_CLAIM_CEILING,
)
from codontrace.genesis.campaigns.discovery_q_20260928_idea3 import (
    IDEA3_SCORED_CELLS,
    REVERSAL_CELL_ID,
    run_idea3_scored_cell,
)
from codontrace.genesis.campaigns.discovery_q_20260928_idea5 import (
    CLAIM_CEILING as IDEA5_CLAIM_CEILING,
)
from codontrace.genesis.campaigns.discovery_q_20260928_idea5 import (
    IDEA5_SCORED_CELLS,
    THETA,
    run_idea5_scored_cell,
)
from codontrace.genesis.campaigns.discovery_q_20260928_idea6 import (
    CLAIM_CEILING as IDEA6_CLAIM_CEILING,
)
from codontrace.genesis.campaigns.discovery_q_20260928_idea6 import (
    EVIDENCE_MEASURE_ID,
    IDEA6_SCORED_CELLS,
    USTAR_ID,
    run_idea6_scored_cell,
)
from codontrace.genesis.campaigns.discovery_q_20260928_measurement import (
    assert_record_not_a_discovery,
)

SCHEMA = "discovery_q_20260928_jsonl_track_c_v1"
CLAIM_CEILING = "phase2_design"
DEFAULT_CAMPAIGN_SEEDS: tuple[int, ...] = tuple(range(401, 465))  # 64 seeds
SEALED_SEED_LO = 801
SEALED_SEED_HI = 816
# Avoid overlap with Idea4+Idea2 campaign (201–264) and engine (301–364).
AVOID_SEED_RANGES: tuple[tuple[int, int], ...] = (
    (201, 264),
    (301, 364),
    (SEALED_SEED_LO, SEALED_SEED_HI),
)
IDEA_IDS: tuple[Literal[1, 3, 5, 6], ...] = (1, 3, 5, 6)

HONESTY = (
    "Scored JSONL Track C campaign under sealed Idea1/3/5/6 phase-2 design "
    "meters. Volume ≠ discovery. claim_ceiling remains phase2_design; "
    "hypothesis_supported and red_queen_proved stay false until Critic "
    "post-data seal. Soft-pass forbidden. Sealed seeds 801–816 untouched. "
    "Scaffold builders only (build_idea{N}_scaffold_ledger)."
)

SCAFFOLD_BUILDERS = {
    1: "build_idea1_scaffold_ledger",
    3: "build_idea3_scaffold_ledger",
    5: "build_idea5_scaffold_ledger",
    6: "build_idea6_scaffold_ledger",
}


def _assert_ceiling_locked() -> None:
    if CLAIM_CEILING != "phase2_design":
        raise ConfigurationError("track_c claim ceiling must stay phase2_design.")
    for ceiling in (
        IDEA1_CLAIM_CEILING,
        IDEA3_CLAIM_CEILING,
        IDEA5_CLAIM_CEILING,
        IDEA6_CLAIM_CEILING,
    ):
        if ceiling != CLAIM_CEILING:
            raise ConfigurationError("idea harness ceilings must match phase2_design.")


def validate_campaign_seeds(seeds: Sequence[int]) -> tuple[int, ...]:
    """Refuse empty lists and sealed / reserved campaign seed ranges."""

    if not seeds:
        raise ConfigurationError("jsonl track_c requires at least one seed.")
    out: list[int] = []
    seen: set[int] = set()
    for raw in seeds:
        seed = int(raw)
        for lo, hi in AVOID_SEED_RANGES:
            if lo <= seed <= hi:
                raise ConfigurationError(
                    f"seed {seed} is in refused range {lo}–{hi}; refuse."
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
        root
        / "outputs"
        / "campaigns"
        / "discovery_questions_20260928"
        / "jsonl_track_c"
    )


def _jobs_for_idea(idea_id: int, seeds: Sequence[int]) -> list[tuple[Any, ...]]:
    cells_map = {
        1: IDEA1_SCORED_CELLS,
        3: IDEA3_SCORED_CELLS,
        5: IDEA5_SCORED_CELLS,
        6: IDEA6_SCORED_CELLS,
    }
    cells = cells_map[idea_id]
    return [
        ("idea", int(idea_id), int(seed), str(cell))
        for seed in seeds
        for cell in cells
    ]


def _run_job(job: tuple[Any, ...]) -> list[dict[str, JsonValue]]:
    kind, idea_id, seed, cell = job
    if kind != "idea":
        raise ConfigurationError(f"unknown job kind {kind!r}.")
    idea = int(idea_id)
    if idea == 1:
        return [run_idea1_scored_cell(seed=int(seed), cell=str(cell))]
    if idea == 3:
        return [run_idea3_scored_cell(seed=int(seed), cell=str(cell))]
    if idea == 5:
        return [run_idea5_scored_cell(seed=int(seed), cell=str(cell))]
    if idea == 6:
        return [run_idea6_scored_cell(seed=int(seed), cell=str(cell))]
    raise ConfigurationError(f"unsupported idea_id {idea!r}; only 1, 3, 5, or 6.")


def run_jsonl_track_c(
    *,
    seeds: Sequence[int] | None = None,
    idea_ids: Sequence[int] | None = None,
    out_dir: Path | None = None,
    max_workers: int | None = None,
    parallel: bool = True,
) -> dict[str, Any]:
    """Run scored Idea1/3/5/6 multi-cell campaign; write JSONL + manifest."""

    _assert_ceiling_locked()
    use_seeds = validate_campaign_seeds(
        seeds if seeds is not None else DEFAULT_CAMPAIGN_SEEDS
    )
    use_ideas = tuple(int(i) for i in (idea_ids if idea_ids is not None else IDEA_IDS))
    for idea_id in use_ideas:
        if idea_id not in (1, 3, 5, 6):
            raise ConfigurationError(
                f"unsupported idea_id {idea_id!r}; only 1, 3, 5, or 6."
            )

    jobs: list[tuple[Any, ...]] = []
    for idea_id in use_ideas:
        jobs.extend(_jobs_for_idea(idea_id, use_seeds))

    n_jobs = len(jobs)
    reported = nproc_reported()
    if max_workers is None:
        import os
        workers = min(os.cpu_count() or 1, reported, n_jobs) if parallel else 1
    else:
        workers = max(1, min(int(max_workers), n_jobs))

    t0 = time.perf_counter()
    if workers <= 1 or n_jobs <= 1:
        nested = [_run_job(job) for job in jobs]
    else:
        with ThreadPoolExecutor(max_workers=workers) as pool:
            nested = list(pool.map(_run_job, jobs))
    wall_s = float(time.perf_counter() - t0)

    records: list[dict[str, JsonValue]] = [rec for group in nested for rec in group]

    def _sort_key(r: Mapping[str, Any]) -> tuple[Any, ...]:
        return (int(r.get("idea_id", 99)), int(r.get("seed", 0)), str(r.get("cell", "")))

    records.sort(key=_sort_key)

    for rec in records:
        rec["data_class"] = "scaffold"
        rec["scientific_result"] = False
        rec["closed_loop_unseen_worlds"] = False

    hyp_any = False
    for rec in records:
        if rec.get("hypothesis_supported") is not False:
            raise ConfigurationError("track_c must keep hypothesis_supported=False.")
        if rec.get("red_queen_proved") is not False:
            raise ConfigurationError("track_c must keep red_queen_proved=False.")
        if rec.get("claim_ceiling") != CLAIM_CEILING:
            raise ConfigurationError("track_c must keep claim_ceiling=phase2_design.")
        if rec.get("soft_pass") is True or rec.get("soft_pass_claimed") is True:
            raise ConfigurationError("track_c forbids soft-pass.")
        if SEALED_SEED_LO <= same_int(rec["seed"]) <= SEALED_SEED_HI:
            raise ConfigurationError("sealed seed leaked into track_c records.")
        assert_record_not_a_discovery(rec)
        if rec.get("hypothesis_supported") is True:
            hyp_any = True

    if hyp_any:
        raise ConfigurationError("hypothesis_supported_any must stay false.")

    target = Path(out_dir) if out_dir is not None else default_output_dir()
    target.mkdir(parents=True, exist_ok=True)
    jsonl_path = target / "idea1_3_5_6_jsonl_track_c.jsonl"
    with jsonl_path.open("w", encoding="utf-8") as fh:
        for rec in records:
            fh.write(json.dumps(rec, sort_keys=True, separators=(",", ":")) + "\n")

    counts = {i: sum(1 for r in records if same_int(r["idea_id"]) == i) for i in (1, 3, 5, 6)}

    manifest: dict[str, Any] = {
        "schema": SCHEMA,
        "claim_ceiling": CLAIM_CEILING,
        "honesty": HONESTY,
        "hypothesis_supported": False,
        "hypothesis_supported_any": False,
        "red_queen_proved": False,
        "soft_pass": False,
        "n_runs_seeds": len(use_seeds),
        "seeds": list(use_seeds),
        "seed_lo": min(use_seeds),
        "seed_hi": max(use_seeds),
        "idea_ids": list(use_ideas),
        "idea1_cells": list(IDEA1_SCORED_CELLS),
        "idea3_cells": list(IDEA3_SCORED_CELLS),
        "idea3_reversal_cell_id": REVERSAL_CELL_ID,
        "idea5_cells": list(IDEA5_SCORED_CELLS),
        "idea5_theta": THETA,
        "idea6_cells": list(IDEA6_SCORED_CELLS),
        "idea6_ustar_id": USTAR_ID,
        "idea6_evidence_measure_id": EVIDENCE_MEASURE_ID,
        "scaffold_builders": dict(SCAFFOLD_BUILDERS),
        "n_records": len(records),
        "n_records_idea1": counts[1],
        "n_records_idea3": counts[3],
        "n_records_idea5": counts[5],
        "n_records_idea6": counts[6],
        "nproc_reported": reported,
        "max_workers": workers,
        "wall_time_s": wall_s,
        "jsonl_path": str(jsonl_path),
        "sealed_seeds_refused": [SEALED_SEED_LO, SEALED_SEED_HI],
        "avoid_seed_ranges": [list(r) for r in AVOID_SEED_RANGES],
        "track": "C",
        "critic_post_data": "pending",
        "not_discovery": True,
        "data_class": "scaffold",
        "scientific_result": False,
        "closed_loop_unseen_worlds": False,
    }
    manifest_path = target / "manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    readme_path = target / "README.md"
    readme_path.write_text(
        "\n".join(
            [
                "# Discovery questions 2026-09-28 — scored JSONL Track C",
                "",
                "Scored multi-cell N=run campaign for Ideas 1 / 3 / 5 / 6 under "
                "claim ceiling `phase2_design`.",
                "",
                "- Every record has `hypothesis_supported=false` and "
                "`red_queen_proved=false`.",
                "- Soft-pass forbidden.",
                "- **Volume ≠ discovery.** Critic post-data seal pending.",
                "- Data class is scaffold. A fast JSONL file is not a closed-loop",
                "  result on unseen worlds, and it does not test the six questions.",
                "- Idea1: cells "
                f"{list(IDEA1_SCORED_CELLS)}; rival "
                "`RP-LEDGER-ATP-DRAIN-V1`; assay separate from reward.",
                "- Idea3: cells "
                f"{list(IDEA3_SCORED_CELLS)}; unreach + "
                f"`{REVERSAL_CELL_ID}`; empty cut reopens.",
                "- Idea5: cells "
                f"{list(IDEA5_SCORED_CELLS)}; θ={THETA}; held-out; "
                "train-fit alone is FAIL.",
                "- Idea6: cells "
                f"{list(IDEA6_SCORED_CELLS)}; "
                f"`{USTAR_ID}` + `{EVIDENCE_MEASURE_ID}`; "
                "ClaimGate ≠ u; support-on vs cut.",
                "- Scaffold builders only "
                "(`build_idea{N}_scaffold_ledger`); smoke aliases are not "
                "the evidence path.",
                "- Sealed campaign seeds `801–816` are not used.",
                "- Default seeds avoid 201–264 and 301–364.",
                "",
                f"Default seeds ({len(DEFAULT_CAMPAIGN_SEEDS)}): "
                f"`{list(DEFAULT_CAMPAIGN_SEEDS)[:4]}…{list(DEFAULT_CAMPAIGN_SEEDS)[-1]}`.",
                f"Schema: `{SCHEMA}`.",
                "",
                f"This run: n_records={len(records)} "
                f"(idea1={counts[1]}, idea3={counts[3]}, "
                f"idea5={counts[5]}, idea6={counts[6]}), "
                f"wall_time_s={wall_s:.2f}, max_workers={workers}.",
                "",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    return {
        **manifest,
        "readme_path": str(readme_path),
        "manifest_path": str(manifest_path),
        "records": records,
    }


def jsonl_track_c_constants() -> Mapping[str, Any]:
    return {
        "schema": SCHEMA,
        "claim_ceiling": CLAIM_CEILING,
        "default_campaign_seeds": list(DEFAULT_CAMPAIGN_SEEDS),
        "sealed_seed_lo": SEALED_SEED_LO,
        "sealed_seed_hi": SEALED_SEED_HI,
        "avoid_seed_ranges": [list(r) for r in AVOID_SEED_RANGES],
        "idea_ids": list(IDEA_IDS),
        "idea1_cells": list(IDEA1_SCORED_CELLS),
        "idea3_cells": list(IDEA3_SCORED_CELLS),
        "idea5_cells": list(IDEA5_SCORED_CELLS),
        "idea6_cells": list(IDEA6_SCORED_CELLS),
        "scaffold_builders": dict(SCAFFOLD_BUILDERS),
        "hypothesis_supported": False,
        "red_queen_proved": False,
        "soft_pass": False,
    }
