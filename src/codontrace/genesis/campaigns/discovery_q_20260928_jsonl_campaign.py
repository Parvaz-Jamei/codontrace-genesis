"""Discovery questions 2026-09-28 — scored JSONL campaign (Ideas 4 and 2).

Genuine multi-cell N=run campaign under claim ceiling phase2_design.
Structurally distinct from jsonl_smoke (separate ops/cells, scored meters,
mid-history t_tilde on T=40 for Idea4). Volume ≠ discovery: every record
keeps hypothesis_supported=False and red_queen_proved=False. Sealed seeds
801–816 refused. Track C phase-2 digests are not invented here.
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
from codontrace.genesis.campaigns.discovery_q_20260928_idea2 import (
    CLAIM_CEILING as IDEA2_CLAIM_CEILING,
)
from codontrace.genesis.campaigns.discovery_q_20260928_idea2 import (
    IDEA2_SCORED_CELLS,
    run_idea2_scored_cell,
)
from codontrace.genesis.campaigns.discovery_q_20260928_idea4 import (
    CLAIM_CEILING as IDEA4_CLAIM_CEILING,
)
from codontrace.genesis.campaigns.discovery_q_20260928_idea4 import (
    HORIZON_T,
    OPS_CELLS,
    T_INTERVENE_GRID,
    run_idea4_scored_cell,
    t_tilde_of,
)
from codontrace.genesis.campaigns.discovery_q_20260928_measurement import (
    assert_record_not_a_discovery,
)

SCHEMA = "discovery_q_20260928_jsonl_campaign_v1"
CLAIM_CEILING = "phase2_design"
DEFAULT_CAMPAIGN_SEEDS: tuple[int, ...] = tuple(range(201, 265))  # 64 seeds
SEALED_SEED_LO = 801
SEALED_SEED_HI = 816
IDEA_IDS: tuple[Literal[4, 2], ...] = (4, 2)

HONESTY = (
    "Scored JSONL campaign under sealed Idea4+Idea2 phase-2 design meters. "
    "Volume ≠ discovery. Not sealed recovery-window evidence (Idea 4) and not "
    "G2/M0–M3 sealed evidence (Idea 2). claim_ceiling remains phase2_design; "
    "hypothesis_supported and red_queen_proved stay false until Critic "
    "post-data seal. Sealed seeds 801–816 untouched."
)


def _assert_ceiling_locked() -> None:
    if CLAIM_CEILING != "phase2_design":
        raise ConfigurationError("campaign claim ceiling must stay phase2_design.")
    if IDEA4_CLAIM_CEILING != CLAIM_CEILING or IDEA2_CLAIM_CEILING != CLAIM_CEILING:
        raise ConfigurationError("idea harness ceilings must match phase2_design.")


def validate_campaign_seeds(seeds: Sequence[int]) -> tuple[int, ...]:
    """Refuse empty lists and sealed campaign seeds 801–816."""

    if not seeds:
        raise ConfigurationError("jsonl campaign requires at least one seed.")
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
        root / "outputs" / "campaigns" / "discovery_questions_20260928" / "jsonl_campaign"
    )


def _jobs_idea4(seeds: Sequence[int]) -> list[tuple[str, int, str, int]]:
    # (kind, seed, ops_cell, t_intervene)
    jobs: list[tuple[str, int, str, int]] = []
    for seed in seeds:
        for cell in OPS_CELLS:
            for t_int in T_INTERVENE_GRID:
                jobs.append(("idea4", int(seed), str(cell), int(t_int)))
    return jobs


def _jobs_idea2(seeds: Sequence[int]) -> list[tuple[str, int, str]]:
    # (kind, seed, cell) — expands to 3 arm rows inside worker
    return [
        ("idea2", int(seed), str(cell))
        for seed in seeds
        for cell in IDEA2_SCORED_CELLS
    ]


def _run_job(job: tuple[Any, ...]) -> list[dict[str, JsonValue]]:
    kind = job[0]
    if kind == "idea4":
        _, seed, ops_cell, t_int = job
        rec = run_idea4_scored_cell(
            seed=int(seed),
            ops_cell=str(ops_cell),
            t_intervene=int(t_int),
            t_horizon=HORIZON_T,
        )
        return [rec]
    if kind == "idea2":
        _, seed, cell = job
        return list(run_idea2_scored_cell(seed=int(seed), cell=str(cell)))
    raise ConfigurationError(f"unknown job kind {kind!r}.")


def run_jsonl_campaign(
    *,
    seeds: Sequence[int] | None = None,
    idea_ids: Sequence[int] | None = None,
    out_dir: Path | None = None,
    max_workers: int | None = None,
    parallel: bool = True,
) -> dict[str, Any]:
    """Run scored Idea4+Idea2 multi-cell campaign; write JSONL + manifest."""

    _assert_ceiling_locked()
    use_seeds = validate_campaign_seeds(
        seeds if seeds is not None else DEFAULT_CAMPAIGN_SEEDS
    )
    use_ideas = tuple(int(i) for i in (idea_ids if idea_ids is not None else IDEA_IDS))
    for idea_id in use_ideas:
        if idea_id not in (4, 2):
            raise ConfigurationError(f"unsupported idea_id {idea_id!r}; only 4 or 2.")

    jobs: list[tuple[Any, ...]] = []
    if 4 in use_ideas:
        jobs.extend(_jobs_idea4(use_seeds))
    if 2 in use_ideas:
        jobs.extend(_jobs_idea2(use_seeds))

    n_jobs = len(jobs)
    reported = nproc_reported()
    if max_workers is None:
        workers = min(8, reported, n_jobs) if parallel else 1
    else:
        workers = max(1, min(int(max_workers), 8, n_jobs))

    t0 = time.perf_counter()
    if workers <= 1 or n_jobs <= 1:
        nested = [_run_job(job) for job in jobs]
    else:
        with ThreadPoolExecutor(max_workers=workers) as pool:
            nested = list(pool.map(_run_job, jobs))
    wall_s = float(time.perf_counter() - t0)

    records: list[dict[str, JsonValue]] = [rec for group in nested for rec in group]

    # Deterministic order: idea_id (4 then 2), seed, cell/ops, arm/t
    def _sort_key(r: Mapping[str, Any]) -> tuple[Any, ...]:
        idea = int(r.get("idea_id", 99))
        seed = int(r.get("seed", 0))
        if idea == 4:
            return (0, seed, str(r.get("ops_cell", "")), float(r.get("t_tilde", 0.0)))
        return (1, seed, str(r.get("cell", "")), str(r.get("arm", "")))

    records.sort(key=_sort_key)

    for rec in records:
        if rec.get("hypothesis_supported") is not False:
            raise ConfigurationError("campaign must keep hypothesis_supported=False.")
        if rec.get("red_queen_proved") is not False:
            raise ConfigurationError("campaign must keep red_queen_proved=False.")
        if rec.get("claim_ceiling") != CLAIM_CEILING:
            raise ConfigurationError("campaign must keep claim_ceiling=phase2_design.")
        if SEALED_SEED_LO <= same_int(rec["seed"]) <= SEALED_SEED_HI:
            raise ConfigurationError("sealed seed leaked into campaign records.")
        assert_record_not_a_discovery(rec)

    target = Path(out_dir) if out_dir is not None else default_output_dir()
    target.mkdir(parents=True, exist_ok=True)
    jsonl_path = target / "idea4_idea2_jsonl_campaign.jsonl"
    with jsonl_path.open("w", encoding="utf-8") as fh:
        for rec in records:
            fh.write(json.dumps(rec, sort_keys=True, separators=(",", ":")) + "\n")

    n_idea4 = sum(1 for r in records if same_int(r["idea_id"]) == 4)
    n_idea2 = sum(1 for r in records if same_int(r["idea_id"]) == 2)
    recover_rate = (
        sum(1 for r in records if same_int(r["idea_id"]) == 4 and r.get("recover") is True)
        / n_idea4
        if n_idea4
        else None
    )

    manifest: dict[str, Any] = {
        "schema": SCHEMA,
        "claim_ceiling": CLAIM_CEILING,
        "honesty": HONESTY,
        "hypothesis_supported": False,
        "red_queen_proved": False,
        "n_runs_seeds": len(use_seeds),
        "seeds": list(use_seeds),
        "seed_lo": min(use_seeds),
        "seed_hi": max(use_seeds),
        "idea_ids": list(use_ideas),
        "idea4_ops_cells": list(OPS_CELLS),
        "idea4_t_intervene_grid": list(T_INTERVENE_GRID),
        "idea4_t_tilde_grid": [t_tilde_of(t) for t in T_INTERVENE_GRID],
        "idea4_T_horizon": HORIZON_T,
        "idea2_cells": list(IDEA2_SCORED_CELLS),
        "idea2_arms": ["gene", "pattern", "causal"],
        "n_records": len(records),
        "n_records_idea4": n_idea4,
        "n_records_idea2": n_idea2,
        "idea4_recover_rate_observational": recover_rate,
        "note_recover_rate": (
            "Observational recover rate only; not a sealed window claim."
        ),
        "nproc_reported": reported,
        "max_workers": workers,
        "wall_time_s": wall_s,
        "jsonl_path": str(jsonl_path),
        "sealed_seeds_refused": [SEALED_SEED_LO, SEALED_SEED_HI],
        "track_c": "standby",
    }
    manifest_path = target / "manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    readme_path = target / "README.md"
    readme_path.write_text(
        "\n".join(
            [
                "# Discovery questions 2026-09-28 — scored JSONL campaign",
                "",
                "Scored multi-cell N=run campaign under claim ceiling `phase2_design`.",
                "",
                "- Every record has `hypothesis_supported=false` and "
                "`red_queen_proved=false`.",
                "- **Volume ≠ discovery.** Not a Critic-sealed recovery-window "
                "result (Idea 4) and not G2/M0–M3 sealed evidence (Idea 2).",
                "- Idea4: mid-history `t_tilde` on T=40 (intervene grid "
                f"{list(T_INTERVENE_GRID)}); factorial ops cells "
                f"{list(OPS_CELLS)}; FI recover bool scored.",
                "- Idea2: cells "
                f"{list(IDEA2_SCORED_CELLS)}; arms gene/pattern/causal; "
                "survival_to_T + margin_vs_best_rival; sham "
                "`SHAM-CUE-PREDPHASE-V1` ≠ NC-*.",
                "- Sealed campaign seeds `801–816` are not used.",
                "- Track C phase-2 digests are not invented here.",
                "",
                f"Default seeds ({len(DEFAULT_CAMPAIGN_SEEDS)}): "
                f"`{list(DEFAULT_CAMPAIGN_SEEDS)[:4]}…{list(DEFAULT_CAMPAIGN_SEEDS)[-1]}`.",
                f"Schema: `{SCHEMA}`.",
                "",
                f"This run: n_records={len(records)} "
                f"(idea4={n_idea4}, idea2={n_idea2}), "
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


def jsonl_campaign_constants() -> Mapping[str, Any]:
    return {
        "schema": SCHEMA,
        "claim_ceiling": CLAIM_CEILING,
        "default_campaign_seeds": list(DEFAULT_CAMPAIGN_SEEDS),
        "sealed_seed_lo": SEALED_SEED_LO,
        "sealed_seed_hi": SEALED_SEED_HI,
        "idea_ids": list(IDEA_IDS),
        "idea4_ops_cells": list(OPS_CELLS),
        "idea4_t_intervene_grid": list(T_INTERVENE_GRID),
        "idea2_cells": list(IDEA2_SCORED_CELLS),
        "hypothesis_supported": False,
        "red_queen_proved": False,
    }
