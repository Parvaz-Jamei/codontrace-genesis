"""Discovery questions 2026-09-28 — honest JSONL smoke for Ideas 4 and 2.

Thin multi-seed writer over the sealed phase-2 harness smokes. Claim ceiling
remains phase2_design. Every record keeps hypothesis_supported=False and
red_queen_proved=False. JSONL smoke is not a recovery-window measurement
(Idea 4) and not G2/M0–M3 evidence (Idea 2). Sealed campaign seeds 801–816
are refused. Track C phase-2 digests are not invented here.
"""

from __future__ import annotations

import json
import os
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
from codontrace.genesis.campaigns.discovery_q_20260928_idea2 import run_idea2_smoke
from codontrace.genesis.campaigns.discovery_q_20260928_idea4 import (
    CLAIM_CEILING as IDEA4_CLAIM_CEILING,
)
from codontrace.genesis.campaigns.discovery_q_20260928_idea4 import run_idea4_smoke

SCHEMA = "discovery_q_20260928_jsonl_smoke_v1"
CLAIM_CEILING = "phase2_design"
# Honest large JSONL smoke seeds (32–64 per idea). Sealed 801–816 refused.
DEFAULT_SMOKE_SEEDS: tuple[int, ...] = tuple(range(101, 149))  # 48 seeds
SEALED_SEED_LO = 801
SEALED_SEED_HI = 816
IDEA_IDS: tuple[Literal[4, 2], ...] = (4, 2)

HONESTY = (
    "JSONL smoke under sealed Idea4+Idea2 phase-2 harness only. "
    "Not a recovery-window measurement (Idea 4) and not G2/M0–M3 evidence "
    "(Idea 2). claim_ceiling remains phase2_design; hypothesis_supported "
    "and red_queen_proved stay false. Sealed seeds 801–816 untouched."
)


def _assert_ceiling_locked() -> None:
    if CLAIM_CEILING != "phase2_design":
        raise ConfigurationError("jsonl smoke claim ceiling must stay phase2_design.")
    if IDEA4_CLAIM_CEILING != CLAIM_CEILING or IDEA2_CLAIM_CEILING != CLAIM_CEILING:
        raise ConfigurationError("idea harness ceilings must match phase2_design.")


def validate_smoke_seeds(seeds: Sequence[int]) -> tuple[int, ...]:
    """Refuse empty lists and sealed campaign seeds 801–816."""

    if not seeds:
        raise ConfigurationError("jsonl smoke requires at least one seed.")
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
    """Report worker-visible core count (fallback 1)."""

    reported = os.cpu_count()
    return int(reported) if reported and reported > 0 else 1


def _run_one(idea_id: int, seed: int) -> dict[str, JsonValue]:
    """Build one honest JSONL record from an existing harness smoke pack."""

    _assert_ceiling_locked()
    if idea_id == 4:
        pack = run_idea4_smoke(seed=seed)
    elif idea_id == 2:
        pack = run_idea2_smoke(seed=seed)
    else:
        raise ConfigurationError(f"unsupported idea_id {idea_id!r}; only 4 or 2.")

    pack_digest = pack.get("pack_digest")
    if not isinstance(pack_digest, str) or not pack_digest:
        raise ConfigurationError("harness pack missing pack_digest.")

    record: dict[str, JsonValue] = {
        "schema": SCHEMA,
        "seed": int(seed),
        "idea_id": int(idea_id),
        "claim_ceiling": CLAIM_CEILING,
        "engineering_green": bool(pack.get("engineering_green")),
        "hypothesis_supported": False,
        "red_queen_proved": False,
        "honesty": HONESTY,
        "pack_digest": pack_digest,
        "nproc_reported": nproc_reported(),
        "harness_schema": pack.get("schema"),
    }
    return record


def _worker(args: tuple[int, int]) -> dict[str, JsonValue]:
    idea_id, seed = args
    return _run_one(idea_id, seed)


def default_output_dir(repo_root: Path | None = None) -> Path:
    root = repo_root if repo_root is not None else Path.cwd()
    return root / "outputs" / "campaigns" / "discovery_questions_20260928" / "jsonl_smoke"


def run_jsonl_smoke(
    *,
    seeds: Sequence[int] | None = None,
    idea_ids: Sequence[int] | None = None,
    out_dir: Path | None = None,
    max_workers: int | None = None,
    parallel: bool = True,
) -> dict[str, Any]:
    """Run Idea4+Idea2 harness smokes for a small seed set; write JSONL.

    Records are ordered by (seed, idea_id) so digests and file order stay
    deterministic even when workers run in parallel.
    """

    _assert_ceiling_locked()
    use_seeds = validate_smoke_seeds(
        seeds if seeds is not None else DEFAULT_SMOKE_SEEDS
    )
    use_ideas = tuple(int(i) for i in (idea_ids if idea_ids is not None else IDEA_IDS))
    for idea_id in use_ideas:
        if idea_id not in (4, 2):
            raise ConfigurationError(f"unsupported idea_id {idea_id!r}; only 4 or 2.")

    jobs = [(idea_id, seed) for seed in sorted(use_seeds) for idea_id in use_ideas]
    n_jobs = len(jobs)
    reported = nproc_reported()
    if max_workers is None:
        import os
        workers = min(os.cpu_count() or 1, reported, n_jobs, len(use_seeds)) if parallel else 1
    else:
        workers = max(1, min(int(max_workers), n_jobs))

    if workers <= 1 or n_jobs <= 1:
        records = [_run_one(idea_id, seed) for idea_id, seed in jobs]
    else:
        with ThreadPoolExecutor(max_workers=workers) as pool:
            # map preserves input order → deterministic file order by seed.
            records = list(pool.map(_worker, jobs))

    # Defensive sort: seed then idea_id (4 before 2 follows IDEA_IDS order).
    idea_rank = {4: 0, 2: 1}
    records.sort(key=lambda r: (same_int(r["seed"]), idea_rank.get(same_int(r["idea_id"]), 99)))

    for rec in records:
        if rec.get("hypothesis_supported") is not False:
            raise ConfigurationError("jsonl smoke must keep hypothesis_supported=False.")
        if rec.get("red_queen_proved") is not False:
            raise ConfigurationError("jsonl smoke must keep red_queen_proved=False.")
        if rec.get("claim_ceiling") != CLAIM_CEILING:
            raise ConfigurationError("jsonl smoke must keep claim_ceiling=phase2_design.")

    target = Path(out_dir) if out_dir is not None else default_output_dir()
    target.mkdir(parents=True, exist_ok=True)
    jsonl_path = target / "idea4_idea2_jsonl_smoke.jsonl"
    with jsonl_path.open("w", encoding="utf-8") as fh:
        for rec in records:
            fh.write(json.dumps(rec, sort_keys=True, separators=(",", ":")) + "\n")

    readme_path = target / "README.md"
    readme_path.write_text(
        "\n".join(
            [
                "# Discovery questions 2026-09-28 — JSONL smoke (Ideas 4 and 2)",
                "",
                "Honest multi-seed harness wiring dump under claim ceiling "
                "`phase2_design`.",
                "",
                "- Every record has `hypothesis_supported=false` and "
                "`red_queen_proved=false`.",
                "- JSONL smoke is **not** a recovery-window measurement (Idea 4).",
                "- JSONL smoke is **not** G2 / M0–M3 evidence (Idea 2).",
                "- Sealed campaign seeds `801–816` are not used.",
                "- This path is not a full campaign and not measurement evidence.",
                "",
                f"Default seeds ({len(DEFAULT_SMOKE_SEEDS)}): `{list(DEFAULT_SMOKE_SEEDS)}`.",
                f"Schema: `{SCHEMA}`.",
                "",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    return {
        "schema": SCHEMA,
        "claim_ceiling": CLAIM_CEILING,
        "seeds": list(use_seeds),
        "idea_ids": list(use_ideas),
        "n_records": len(records),
        "jsonl_path": str(jsonl_path),
        "readme_path": str(readme_path),
        "nproc_reported": reported,
        "max_workers": workers,
        "hypothesis_supported": False,
        "red_queen_proved": False,
        "records": records,
    }


def jsonl_smoke_constants() -> Mapping[str, Any]:
    return {
        "schema": SCHEMA,
        "claim_ceiling": CLAIM_CEILING,
        "default_smoke_seeds": list(DEFAULT_SMOKE_SEEDS),
        "sealed_seed_lo": SEALED_SEED_LO,
        "sealed_seed_hi": SEALED_SEED_HI,
        "idea_ids": list(IDEA_IDS),
        "hypothesis_supported": False,
        "red_queen_proved": False,
    }
