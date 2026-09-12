"""CodonTrace Genesis hard experiment 01 — capsule source-bias measurement.

Print-only. Default run is the 12-seed exploratory campaign (four arms:
source-bias on, source-bias off, capsules off, capsules shuffled) plus a
2-seed dose-ladder smoke. Pass --research-grade for the 30-seed path
(StatisticalTestPolicy research-grade language). Does not write files,
start a UI, set ClaimGate flags, or claim intelligence, collective
intelligence, Tokyo Type 1 passed, or Avida replacement.
"""

from __future__ import annotations

import argparse

try:
    from ._path_bootstrap import ensure_src_path
except ImportError:
    import sys as _sys
    from pathlib import Path as _Path

    _EXAMPLES_DIR = _Path(__file__).resolve().parent
    if str(_EXAMPLES_DIR) not in _sys.path:
        _sys.path.insert(0, str(_EXAMPLES_DIR))
    from _path_bootstrap import ensure_src_path

ensure_src_path()

from codontrace.genesis.claim_gate import ClaimRequest, ScientificClaimGate
from codontrace.genesis.hard_experiment_01 import (
    RESEARCH_GRADE_SEED_COUNT,
    format_hard_experiment_01_dose_summary,
    format_hard_experiment_01_summary,
    hard_experiment_01_dag,
    run_hard_experiment_01,
    run_hard_experiment_01_dose_response,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="CodonTrace Genesis HARD_EXPERIMENT_01")
    parser.add_argument(
        "--research-grade",
        action="store_true",
        help="run seed_count=30 (research-grade language). Default is 12-seed exploratory.",
    )
    args = parser.parse_args()
    seed_count = RESEARCH_GRADE_SEED_COUNT if args.research_grade else None
    campaign = run_hard_experiment_01(seed_count=seed_count)
    print(format_hard_experiment_01_summary(campaign))
    print("dag_digest", hard_experiment_01_dag().digest)
    dose = run_hard_experiment_01_dose_response(seed_count=2 if seed_count is None else seed_count)
    print(format_hard_experiment_01_dose_summary(dose))
    gate = ScientificClaimGate()
    payload = campaign.to_dict()
    print(
        "runtime_observation_allowed",
        gate.decide(ClaimRequest("runtime_observation", payload)).allowed,
    )
    print(
        "intervention_supported_allowed",
        gate.decide(ClaimRequest("intervention_supported", payload)).allowed,
    )
    print(
        "collective_intelligence_allowed",
        gate.decide(ClaimRequest("collective_intelligence", payload)).allowed,
    )
    print("intelligence_allowed", gate.decide(ClaimRequest("intelligence", payload)).allowed)
    print("agi_allowed", gate.decide(ClaimRequest("agi", payload)).allowed)
    print("tokyo_type1_passed_allowed", gate.decide(ClaimRequest("tokyo_type1_passed", payload)).allowed)
    print("avida_replacement_allowed", gate.decide(ClaimRequest("avida_replacement", payload)).allowed)


if __name__ == "__main__":
    main()
