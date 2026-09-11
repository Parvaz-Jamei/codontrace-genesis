"""Phase D multi-generation evidence smoke.

This example runs the Phase A life-loop preset (optional flags for Phase B
sexual recombination and Phase C dynamic environment) and prints first-class
library metrics: per-generation fitness, instinct/behavior descriptors,
persistence-filtered MODES-style axes, Bedau activity, and a digest-backed
``MultiGenerationEvidencePack``. It does not write files, start a UI, or claim
OEE, intelligence, or instinct evolution proved.
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

from codontrace.genesis.birth import ReproductionMode
from codontrace.genesis.claim_gate import ClaimRequest, ScientificClaimGate
from codontrace.genesis.engine import GenesisEngine
from codontrace.genesis.multi_generation import (
    build_multi_generation_evidence_pack,
    evaluate_instinct_improvement_claim,
    evaluate_oee_measurement_claim,
)
from codontrace.genesis.runtime_profiles import (
    GenesisRuntimeProfile,
    summarize_life_loop_observation,
)


def main() -> None:
    spec = GenesisRuntimeProfile.life_loop_world(seed=7, tick_count=12, population=6)
    result = GenesisEngine.from_spec(spec).run_ticks()
    replay = GenesisEngine.from_spec(spec).run_ticks()
    observation = summarize_life_loop_observation(result)
    pack = build_multi_generation_evidence_pack(result, spec=spec)
    instinct = evaluate_instinct_improvement_claim(pack)
    oee = evaluate_oee_measurement_claim(pack)
    blocked = ScientificClaimGate().decide(ClaimRequest("open_ended_intelligence", {}))

    print("runtime_profile", spec.metadata["runtime_profile"])
    print("phase_d_spec_metadata", spec.metadata["phase_d_instinct_claim_metrics"])
    print("life_loop_hook", observation.phase_d_instinct_metrics)
    print("generations", len(pack.fitness_trajectory.points))
    print("mean_fitness_first", pack.fitness_trajectory.points[0].mean_fitness)
    print("mean_fitness_last", pack.fitness_trajectory.points[-1].mean_fitness)
    print("births_total", sum(point.births for point in pack.fitness_trajectory.points))
    if pack.cohort_comparison is not None:
        print("fitness_delta", pack.cohort_comparison.fitness_delta)
        print("descendant_outperforms", pack.cohort_comparison.descendant_outperforms_ancestors)
    if pack.modes_assessment is not None and pack.modes_assessment.points:
        last_modes = pack.modes_assessment.points[-1]
        print("modes_novelty", last_modes.novelty)
        print("modes_complexity", last_modes.complexity)
        print("modes_change", last_modes.change)
        print("modes_ecological_potential", last_modes.ecological_potential)
    if pack.bedau_surface is not None and pack.bedau_surface.points:
        last_bedau = pack.bedau_surface.points[-1]
        print("bedau_diversity", last_bedau.diversity)
        print("bedau_cumulative_activity", last_bedau.cumulative_activity)
    print("instinct_improved_status", pack.instinct_improved_status)
    print("claim_ceiling", pack.claim_ceiling)
    print("instinct_gate_final", instinct.final_claim)
    print("oee_gate_final", oee.final_claim)
    print("open_ended_intelligence_allowed", blocked.allowed)
    print("oee_proved", False)
    print("pack_digest", pack.digest[:16])
    print("json_bytes", len(pack.to_json()))
    print("replay_digest_stable", result.digest() == replay.digest())
    print("pack_replay_stable", pack.digest == build_multi_generation_evidence_pack(replay).digest)
    print("sexual_opt_in_available", ReproductionMode.SEXUAL_CROSSOVER.value)
    print("dynamic_env_opt_in_available", True)


if __name__ == "__main__":
    main()
