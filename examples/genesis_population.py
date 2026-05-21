"""Focused deterministic GENESIS population lifecycle example.

This example is library-first: it creates objects, steps 2-3 generations, and
prints small summaries. It does not write files, plot, start a UI, or claim
artificial life/open-ended discovery.
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

from codontrace import (
    AliveGateConfig,
    FitnessConfig,
    GenesisOrganism,
    MutationConfig,
    PopulationConfigs,
    PopulationRunner,
    PopulationState,
    ReproductionConfig,
    World2D,
)


def main() -> None:
    world = World2D(5, 5)
    organism = GenesisOrganism.from_bits(
        "founder",
        "111000101",  # COPY_SELF, WAIT, EAT_LUMEN
        initial_runtime_atp=24.0,
        position=(2, 2),
    )
    population = PopulationState(
        generation=0, tick=0, organisms=(organism,), lineage=(), fitness=()
    )
    configs = PopulationConfigs(
        reproduction=ReproductionConfig(
            min_runtime_atp=1.0,
            parent_atp_cost=0.5,
            max_population=4,
            offspring_atp_fraction=0.2,
        ),
        mutation=MutationConfig(bit_flip_rate=0.0),
        fitness=FitnessConfig(),
        alive_gate=AliveGateConfig(
            min_ticks=1,
            min_executed_actions=0,
            max_blocked_ratio=1.0,
            require_positive_runtime_atp=False,
        ),
        ticks_per_generation=1,
    )
    runner = PopulationRunner(population=population, world=world, configs=configs)

    for seed in (101, 102, 103):
        result = runner.step_generation(seed=seed)
        print(
            "generation=",
            result.population.generation,
            "births=",
            result.births,
            "deaths=",
            result.deaths,
            "best_fitness=",
            result.best_fitness,
            "mean_fitness=",
            result.mean_fitness,
        )

    if runner.population.lineage:
        print("lineage_sample=", runner.population.lineage[-1].to_dict())


if __name__ == "__main__":
    main()
