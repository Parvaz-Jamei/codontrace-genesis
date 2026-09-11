"""Phase E capsule/memory/role/deme substrate smoke.

This example runs the opt-in Phase E substrate (associative capsule memory
with a real subsequent action effect, optional role/deme hooks) and prints
digest-backed observations. It does not write files, start a UI, or claim
learning, evolved plasticity, collective intelligence, or Avida-replacement
status.
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

from dataclasses import replace

from codontrace.genesis.claim_gate import ClaimRequest, ScientificClaimGate
from codontrace.genesis.engine import GenesisEngine
from codontrace.genesis.multi_generation import build_multi_generation_evidence_pack
from codontrace.genesis.phase_e import (
    AvidaParityProtocolSpec,
    GHALAMBOR_CLUNE_CONDITIONS,
    build_phase_e_evidence_pack,
    evaluate_phase_e_claim,
)
from codontrace.genesis.runtime_profiles import GenesisRuntimeProfile


def main() -> None:
    spec = GenesisRuntimeProfile.phase_e_substrate_world(
        seed=7,
        tick_count=8,
        population=4,
        enable_capsule_memory=True,
        enable_roles=True,
        enable_demes=True,
        seed_preferred_action="EAT_LUMEN",
    )
    # WAIT-only genomes at food cells make the capsule action-bias visible.
    spec = replace(spec, genome_bits=("000000000", "000000000", "000000000", "000000000"))
    result = GenesisEngine.from_spec(spec).run_ticks()
    replay = GenesisEngine.from_spec(spec).run_ticks()
    off_spec = GenesisRuntimeProfile.phase_e_substrate_world(
        seed=7,
        tick_count=8,
        population=4,
        enable_capsule_memory=False,
        seed_preferred_action="",
    )
    off_spec = replace(off_spec, genome_bits=spec.genome_bits)
    off_result = GenesisEngine.from_spec(off_spec).run_ticks()
    pack = build_phase_e_evidence_pack(result)
    d_pack = build_multi_generation_evidence_pack(result, spec=spec)
    gate = evaluate_phase_e_claim(pack)
    blocked = ScientificClaimGate().decide(ClaimRequest("collective_intelligence", {}))
    protocol = AvidaParityProtocolSpec(include_deme_messaging=True)

    print("runtime_profile", spec.metadata["runtime_profile"])
    print("claim_ceiling", pack.claim_ceiling)
    print("capsule_substitutions", pack.observation.capsule_substitutions)
    print("capsule_writes", pack.observation.capsule_writes)
    print("messages_sent", pack.observation.messages_sent)
    print("phase_d_observes_phase_e", d_pack.claim_ceiling)
    print("ablation_digest_differs", result.digest() != off_result.digest())
    print("replay_digest_stable", result.digest() == replay.digest())
    print("pack_digest", pack.digest[:16])
    print("phase_e_gate_final", gate.final_claim)
    print("collective_intelligence_allowed", blocked.allowed)
    print("plasticity_evolved", pack.observation.plasticity_evolved)
    print("ghalambor_clune_conditions", len(GHALAMBOR_CLUNE_CONDITIONS))
    print("avida_parity_superiority_claimed", protocol.to_dict()["superiority_claimed"])
    print("json_bytes", len(pack.to_json()))


if __name__ == "__main__":
    main()
