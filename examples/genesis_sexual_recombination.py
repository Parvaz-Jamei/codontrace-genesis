"""Phase B sexual recombination smoke.

This example enables the explicit two-parent crossover path on the life-loop
preset. Population runs use an Avida-style birth chamber (pairing queue) and
positional continuous corresponding crossover, then mutation. It prints
runtime observations only: recombinant births, two-parent lineage records,
and a replay digest. Research defaults stay asexual. It does not write files,
start a UI, or claim life, intelligence, sexual selection, instinct
evolution, diploid meiosis, or Avida-replacement status.
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
from codontrace.genesis.engine import GenesisEngine
from codontrace.genesis.runtime_profiles import (
    GenesisRuntimeProfile,
    summarize_life_loop_observation,
)


def main() -> None:
    spec = GenesisRuntimeProfile.life_loop_world(
        seed=7,
        tick_count=12,
        population=6,
        reproduction_mode=ReproductionMode.SEXUAL_CROSSOVER,
    )
    result = GenesisEngine.from_spec(spec).run_ticks()
    replay = GenesisEngine.from_spec(spec).run_ticks()
    observation = summarize_life_loop_observation(result)

    print("runtime_profile", spec.metadata["runtime_profile"])
    print("reproduction_mode", spec.metadata["reproduction_mode"])
    print("sexual_pairing", spec.metadata["sexual_pairing"])
    print("phase_b_sexual_crossover", spec.metadata["phase_b_sexual_crossover"])
    print("phase_b1_diploid_meiosis", spec.metadata["phase_b1_diploid_meiosis"])
    print("claim_ceiling", spec.metadata["claim_ceiling"])
    print("phase_c_fluctuating_environment", spec.metadata["phase_c_fluctuating_environment"])
    print("phase_d_instinct_metrics", spec.metadata["phase_d_instinct_claim_metrics"])
    print("births", observation.births)
    print("two_parent_lineage_records", observation.two_parent_lineage_records)
    print("heritable_sexual_pairs", observation.heritable_sexual_pairs)
    print("recombinant_child_pairs", observation.recombinant_child_pairs)
    print("heritable_asexual_pairs", observation.heritable_asexual_pairs)
    print("replay_digest_stable", result.digest() == replay.digest())
    print("genesis_alive_full", observation.genesis_alive_full)


if __name__ == "__main__":
    main()
