"""Audit HARD_EXPERIMENT_01 v2 with the standalone ClaimGate auditor.

Print-only. Uses the committed ``docs/hard_experiment_01/results_v2.json``
campaign artifact. Does not run the Genesis engine, write files, start a
UI, loosen ClaimGate, or claim intelligence, collective intelligence,
Tokyo Type 1 passed, or Avida replacement.
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

from codontrace.claimgate import audit_bundle  # noqa: E402
from codontrace.claimgate.adapters.codontrace import (  # noqa: E402
    bundle_from_hard_experiment_01,
    committed_results_v2_path,
)
from codontrace.genesis.claim_gate import ClaimRequest, ScientificClaimGate  # noqa: E402


def main() -> None:
    path = committed_results_v2_path()
    bundle = bundle_from_hard_experiment_01(path)
    report = audit_bundle(bundle)
    print("artifact", path)
    print("public_level", report.achieved_level)
    print("public_name", report.public_name)
    print("missing_for_next", ",".join(report.missing_for_next))
    print("digest", report.digest)
    print("warnings", ",".join(report.warnings))
    gate = ScientificClaimGate()
    print(
        "runtime_observation_allowed",
        gate.decide(ClaimRequest("runtime_observation", {})).allowed,
    )
    print(
        "collective_intelligence_allowed",
        gate.decide(ClaimRequest("collective_intelligence", {})).allowed,
    )
    print("tokyo_type1_passed_allowed", gate.decide(ClaimRequest("tokyo_type1_passed", {})).allowed)
    print("avida_replacement_allowed", gate.decide(ClaimRequest("avida_replacement", {})).allowed)


if __name__ == "__main__":
    main()
