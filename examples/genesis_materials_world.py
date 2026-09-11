"""Phase G named-materials / chemistry-effect substrate smoke.

This example enables the opt-in MaterialsWorld overlay on the life-loop
preset and prints runtime observations only: named-material chemostat
pools, uptake/toxin events, optional autocatalytic extent, trajectory
replay, and blocked realistic-chemistry claims. It does not write files,
start a UI, or claim wet-lab equivalence, KEGG/BiGG solving, intelligence,
or Avida-replacement status.
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
from codontrace.genesis.materials import (
    build_materials_evidence_pack,
    evaluate_materials_claim,
    materials_snapshots_from_generation_results,
    summarize_materials_observation,
    verify_materials_trajectory_replay,
)
from codontrace.genesis.runtime_profiles import (
    GenesisRuntimeProfile,
    summarize_life_loop_observation,
)


def main() -> None:
    spec = GenesisRuntimeProfile.materials_world(seed=7, tick_count=8, population=6)
    result = GenesisEngine.from_spec(spec).run_ticks()
    replay = GenesisEngine.from_spec(spec).run_ticks()
    observation = summarize_materials_observation(
        result,
        config=(
            spec.population_configs.materials if spec.population_configs else None
        ),
    )
    life = summarize_life_loop_observation(result)
    pack = build_materials_evidence_pack(result)
    snapshots = materials_snapshots_from_generation_results(result.ticks)
    replay_snapshots = materials_snapshots_from_generation_results(replay.ticks)
    verified = verify_materials_trajectory_replay(snapshots, replay_snapshots)
    gate = evaluate_materials_claim(pack)
    blocked_chem = ScientificClaimGate().decide(ClaimRequest("realistic_chemistry_proved", {}))
    blocked_wet = ScientificClaimGate().decide(ClaimRequest("wet_lab_equivalent", {}))

    cycle_spec = GenesisRuntimeProfile.materials_world(
        seed=7, tick_count=6, population=4, autocatalytic=True
    )
    cycle = GenesisEngine.from_spec(cycle_spec).run_ticks()
    cycle_obs = summarize_materials_observation(
        cycle,
        config=(
            cycle_spec.population_configs.materials if cycle_spec.population_configs else None
        ),
    )

    print("runtime_profile", spec.metadata["runtime_profile"])
    print("phase_g_materials", spec.metadata["phase_g_materials"])
    print("claim_ceiling", spec.metadata["claim_ceiling"])
    print("biological_accuracy_claimed", spec.metadata["biological_accuracy_claimed"])
    print("materials", spec.metadata["materials"])
    print("materials_config_digest", observation.materials_config_digest[:16])
    print("trajectory_digest", observation.trajectory_digest[:16])
    print("uptake_events", observation.uptake_events)
    print("toxin_drain_events", observation.toxin_drain_events)
    print("lumen_eaten_events", life.lumen_eaten_events)
    print("replay_digest_stable", result.digest() == replay.digest())
    print("materials_trajectory_replay_matched", verified.matched)
    print("pack_digest", pack.digest[:16])
    print("materials_gate_final", gate.final_claim)
    print("realistic_chemistry_proved_allowed", blocked_chem.allowed)
    print("wet_lab_equivalent_allowed", blocked_wet.allowed)
    print("binding_gem_solver", pack.binding_schema.gem_solver_implemented)
    print("autocatalytic_extent_total", cycle_obs.autocatalytic_extent_total)
    print(
        "spatial_ace_evolved",
        False
        if cycle_obs.spatial_coexistence is None
        else cycle_obs.spatial_coexistence.spatial_ace_evolved,
    )


if __name__ == "__main__":
    main()
