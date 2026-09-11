"""CodonTrace Genesis hard experiment 01 — capsule source-bias measurement.

Print-only. Runs the 12-seed paired campaign (source-bias on vs source-bias
off vs capsules off) and shows ClaimGate still blocking intelligence claims.
Does not write files, start a UI, set ClaimGate flags, or claim intelligence,
collective intelligence, Tokyo Type 1 passed, or Avida replacement.
"""

from __future__ import annotations

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
    format_hard_experiment_01_summary,
    run_hard_experiment_01,
)


def main() -> None:
    campaign = run_hard_experiment_01()
    print(format_hard_experiment_01_summary(campaign))
    gate = ScientificClaimGate()
    payload = campaign.to_dict()
    print(
        "runtime_observation_allowed",
        gate.decide(ClaimRequest("runtime_observation", payload)).allowed,
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
