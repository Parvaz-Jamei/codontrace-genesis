"""Phase C dynamic / fluctuating environment smoke.

This example enables the opt-in chemostat + periodic high-food / low-food
schedule on the life-loop preset. It prints runtime observations only:
environment config digest, per-tick pool trajectory, regime switches, and a
replay-verified env digest. Research defaults stay static Phase A ecology.
It does not write files, start a UI, or claim life, intelligence, evolved
plasticity, instinct, or Avida-replacement status.
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

from codontrace.genesis.engine import GenesisEngine
from codontrace.genesis.environment import (
    snapshots_from_generation_results,
    summarize_dynamic_environment_observation,
    verify_environment_trajectory_replay,
)
from codontrace.genesis.runtime_profiles import (
    GenesisRuntimeProfile,
    summarize_life_loop_observation,
)


def main() -> None:
    spec = GenesisRuntimeProfile.dynamic_environment_world(
        seed=7, tick_count=12, population=6, period_ticks=4
    )
    result = GenesisEngine.from_spec(spec).run_ticks()
    replay = GenesisEngine.from_spec(spec).run_ticks()
    env = summarize_dynamic_environment_observation(
        result,
        config=(
            spec.population_configs.environment if spec.population_configs else None
        ),
    )
    life = summarize_life_loop_observation(result)
    snapshots = snapshots_from_generation_results(result.ticks)
    replay_snapshots = snapshots_from_generation_results(replay.ticks)
    verified = verify_environment_trajectory_replay(snapshots, replay_snapshots)

    print("runtime_profile", spec.metadata["runtime_profile"])
    print("phase_c_fluctuating_environment", spec.metadata["phase_c_fluctuating_environment"])
    print("environment_schedule_kind", spec.metadata["environment_schedule_kind"])
    print("environment_period_ticks", spec.metadata["environment_period_ticks"])
    print("environment_regimes", spec.metadata["environment_regimes"])
    print("claim_ceiling", spec.metadata["claim_ceiling"])
    print("claim_allowed_for_plasticity", spec.metadata["claim_allowed_for_plasticity"])
    print("phase_d_instinct_metrics", spec.metadata["phase_d_instinct_claim_metrics"])
    print("environment_config_digest", env.environment_config_digest[:16])
    print("trajectory_digest", env.trajectory_digest[:16])
    print("regime_switches", env.regime_switches)
    print("unique_regimes", list(env.unique_regimes))
    print("environment_events", env.environment_events)
    print("lumen_pool_min", env.pool_range.get("lumen", (0.0, 0.0))[0])
    print("lumen_pool_max", env.pool_range.get("lumen", (0.0, 0.0))[1])
    print("lumen_eaten_events", life.lumen_eaten_events)
    print("births", life.births)
    print("replay_digest_stable", result.digest() == replay.digest())
    print("env_trajectory_replay_matched", verified.matched)
    print("plasticity_evolved", env.plasticity_evolved)
    print("genesis_alive_full", life.genesis_alive_full)


if __name__ == "__main__":
    main()
