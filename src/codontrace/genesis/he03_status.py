"""HE03 phase-2 status. Research results_v1 is deferred; do not invent it."""

from __future__ import annotations

from pathlib import Path
from typing import Any

CLAIM_CEILING = "runtime_observation"
RESEARCH_RELATIVE = "docs/hard_experiment_03/results_v1.json"
PREREG_RELATIVE = "docs/HARD_EXPERIMENT_03_PREREG.md"


def _repo_root() -> Path:
    here = Path(__file__).resolve()
    if len(here.parents) >= 4:
        return here.parents[3]
    return Path.cwd()


def research_results_path() -> Path:
    root = _repo_root()
    candidate = root / RESEARCH_RELATIVE
    cwd = Path.cwd() / RESEARCH_RELATIVE
    if candidate.is_file():
        return candidate
    return cwd


def he03_phase2_status() -> dict[str, Any]:
    results = research_results_path()
    prereg = _repo_root() / PREREG_RELATIVE
    if not prereg.is_file():
        prereg = Path.cwd() / PREREG_RELATIVE
    return {
        "experiment_id": "hard_experiment_03_task_switch_dol",
        "research_results_present": results.is_file(),
        "research_results_path": str(results),
        "prereg_present": prereg.is_file(),
        "claim_ceiling": CLAIM_CEILING,
        "intervention_supported": False,
        "collective_intelligence": False,
        "fabricated": False,
        "note": "research results_v1 is deferred; smoke/pilot code exists",
    }


def main() -> dict[str, Any]:
    return he03_phase2_status()
