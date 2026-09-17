"""Post-phase-3 wave status. Does not create tags or bump PyPI."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from codontrace._version import package_version
from codontrace.genesis.he03_status import he03_phase2_status


def wave_status() -> dict[str, Any]:
    helper = Path(__file__).with_name("he02_contrasts.py")
    runner = Path(__file__).with_name("hard_experiment_02.py")
    src = runner.read_text(encoding="utf-8") if runner.is_file() else ""
    he03 = he03_phase2_status()
    return {
        "product": "CodonTrace Genesis",
        "package_identity": package_version(),
        "pypi_cut": True,
        "proposed_tag": "v0.3.0b4.dev0-he02-v1b",
        "tag_created_in_this_wave": False,
        "phase1_wrapper_present": helper.is_file()
        and "run_hard_experiment_02_v1b" in helper.read_text(encoding="utf-8"),
        "phase1_runner_source_wired": "contrasts_from_seed_dicts" in src
        and "paired_effect_size(lefts, rights)" not in src,
        "phase2_he03_research_present": he03["research_results_present"],
        "claim_ceiling": "runtime_observation",
        "intervention_supported": False,
        "next": "do not recut PyPI 0.3.0b4; next public cut is 0.3.0b5",
    }


def main() -> dict[str, Any]:
    return wave_status()
