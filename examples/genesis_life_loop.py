"""Phase A Darwinian life-loop smoke.

This example runs the explicit ``life_loop_world`` ecology preset and prints
runtime observations only: eat, survive, asexual COPY_SELF, parent→child
relatedness, optional resource respawn, and a replay digest. It does not write
files, start a UI, or claim life, intelligence, cooperation, or instinct
evolution.
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
from codontrace.genesis.runtime_profiles import (
    GenesisRuntimeProfile,
    summarize_life_loop_observation,
)


def main() -> None:
    spec = GenesisRuntimeProfile.life_loop_world(seed=7, tick_count=12, population=6)
    result = GenesisEngine.from_spec(spec).run_ticks()
    replay = GenesisEngine.from_spec(spec).run_ticks()
    observation = summarize_life_loop_observation(result)

    print("runtime_profile", spec.metadata["runtime_profile"])
    print("offspring_placement", spec.metadata["offspring_placement"])
    print("claim_ceiling", spec.metadata["claim_ceiling"])
    print("phase_d_instinct_metrics", spec.metadata["phase_d_instinct_claim_metrics"])
    print("lumen_eaten_events", observation.lumen_eaten_events)
    print("births", observation.births)
    print("deaths", observation.deaths)
    print("resource_respawn_events", observation.resource_respawn_events)
    print("parent_child_pairs", observation.parent_child_pairs)
    print("heritable_asexual_pairs", observation.heritable_asexual_pairs)
    print("replay_digest_stable", result.digest() == replay.digest())
    print("genesis_alive_full", observation.genesis_alive_full)


if __name__ == "__main__":
    main()
