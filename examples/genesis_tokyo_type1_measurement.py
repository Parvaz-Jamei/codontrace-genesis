"""Tokyo Type 1 *measurement* protocol smoke (Channon 2024 steps).

Prints Channon-2024 measurement-step labels from a Phase A life-loop run plus
a Phase D evidence pack. It does not write files, start a UI, or claim Tokyo
Type 1 passed, OEE, intelligence, AGI, or Avida replacement.
"""

from __future__ import annotations

try:
    from ._path_bootstrap import ensure_src_path
except ImportError:  # direct script or runpy execution outside the examples package
    import sys as _sys
    from pathlib import Path as _Path

    _EXAMPLES_DIR = _Path(__file__).resolve().parent
    if str(_EXAMPLES_DIR) not in _sys.path:
        _sys.path.insert(0, str(_EXAMPLES_DIR))
    from _path_bootstrap import ensure_src_path

ensure_src_path()

from codontrace.genesis.claim_gate import ClaimRequest, ScientificClaimGate
from codontrace.genesis.engine import GenesisEngine
from codontrace.genesis.multi_generation import build_multi_generation_evidence_pack
from codontrace.genesis.runtime_profiles import GenesisRuntimeProfile
from codontrace.genesis.tokyo_type1 import (
    build_tokyo_type1_measurement_protocol,
    evaluate_tokyo_type1_measurement_claim,
    evaluate_tokyo_type1_pass_claim,
)


def main() -> None:
    spec = GenesisRuntimeProfile.life_loop_world(seed=7, tick_count=12, population=6)
    result = GenesisEngine.from_spec(spec).run_ticks()
    pack = build_multi_generation_evidence_pack(result, spec=spec)
    protocol = build_tokyo_type1_measurement_protocol(pack)
    measured = evaluate_tokyo_type1_measurement_claim(protocol)
    blocked = evaluate_tokyo_type1_pass_claim(protocol)
    agi = ScientificClaimGate().decide(ClaimRequest("agi", {}))
    replacement = ScientificClaimGate().decide(ClaimRequest("avida_replacement", {}))

    print("runtime_profile", spec.metadata["runtime_profile"])
    print("persistence_window_t", protocol.persistence_window_t)
    print("seed_count", protocol.seed_count)
    print("measurement_status", protocol.measurement_status)
    print("claim_ceiling", protocol.claim_ceiling)
    print("tokyo_type1_passed", protocol.tokyo_type1_passed)
    print("measurement_gate_final", measured.final_claim)
    print("pass_claim_allowed", blocked.allowed)
    print("agi_allowed", agi.allowed)
    print("avida_replacement_allowed", replacement.allowed)
    print("empirical_systematics_shadow_run", protocol.empirical_systematics_shadow_run)
    print("shadow_normalization_status", protocol.shadow_normalization_status)
    for step in protocol.steps:
        print("step", step.step_id, step.status)
    print("protocol_digest", protocol.digest[:16])
    print("capacity_exceeds_population", spec.population_max > len(spec.genome_bits))


if __name__ == "__main__":
    main()
