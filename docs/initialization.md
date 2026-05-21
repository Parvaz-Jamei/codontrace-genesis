# Agent initialization

`codontrace v0.3.0a1` supports deterministic manual and automatic agent initialization for experiments.

Agent initialization is not a runtime population-evolution system. CodonTrace now provides a separate controlled population lifecycle under `codontrace.genesis.population`, including bounded reproduction, mutation, lineage, fitness scoring, and generation stepping. This does not claim open-ended evolution, biological life, or discovery.

## Runtime boundary

`v0.3.0a1` does not make `World2D` itself a multi-agent rendering surface. `World2D` still tracks one active rendered agent marker for simple ASCII workflows.

Multi-agent experiments are supported through `Simulation.run()`, which executes multiple agents over a shared world state and returns a `SimulationResult`. Separately, the GENESIS namespace provides controlled population lifecycle objects for bounded reproduction, mutation, lineage, fitness scoring, and generation stepping. Neither path claims open-ended evolution, biological life, or discovery.

## Manual creation

Use `AgentFactory.from_specs()` when you want exact control over agent ID, genome, ATP, position, profile, lineage metadata, and generation.

```python
from codontrace import AgentFactory, AgentSpec, SemanticGenome

agents = AgentFactory.from_specs([
    AgentSpec(
        agent_id="explorer-1",
        genome=SemanticGenome.from_codons(["101", "001"]),
        initial_atp=4.0,
        position=(1, 1),
        profile="explorer",
    )
])
```

## Automatic creation


```python
from codontrace import AgentFactory, InitializationConfig, World2D

world = World2D(width=10, height=6)
agents = AgentFactory.create_many(
    world=world,
    config=InitializationConfig(count=10, seed=42),
)
```

## Profile-based generation

Profiles let you describe prominent initialization traits without changing the library source code.

```python
from codontrace import AgentFactory, AgentProfile, InitializationConfig, World2D

world = World2D(width=12, height=8)
agents = AgentFactory.create_many(
    world=world,
    config=InitializationConfig(
        count=12,
        seed=42,
        genome_strategy="profiled_random",
        placement_strategy="poisson_disk",
        min_distance=2,
        profiles=(
            AgentProfile(
                name="explorer",
                count=4,
                genome_length=8,
                initial_atp=4.0,
                preferred_codons=("101", "011"),
            ),
            AgentProfile(
                name="collector",
                count=4,
                genome_length=6,
                initial_atp=6.0,
                preferred_codons=("111", "001"),
            ),
        ),
    ),
)
```


## Placement strategies

- `grid`: deterministic top-left to bottom-right filling; useful for debugging.
- `uniform_random`: deterministic seeded shuffle of valid free cells.
- `poisson_disk`: deterministic seeded placement that enforces a minimum Chebyshev distance between selected positions.


`placement_zone=(x1, y1, x2, y2)` is inclusive. Both corners must be inside the world.

## Lineage-seeded initialization

`lineage_seeded` creates initialization metadata inspired by parent/child lineages. It creates ancestors and derives later agents through controlled mutation, storing `lineage_id`, `parent_id`, and `generation` on agents. `LineageConfig` controls `ancestor_count`, allowed `mutation_operations`, and `mutation_steps`.

This is still initialization only. It is not a runtime reproduction loop and does not imply selection or biological evolution.

## Latin hypercube approximation

`latin_hypercube_lite` is implemented as a pure-Python, dependency-free approximation for broader parameter coverage. It stratifies sampled dimensions, but it is not a full SciPy QMC replacement. In `v0.3.0a1`, it supports exactly one profile; multi-profile LHS is deferred.


`latin_hypercube` remains a backward-compatible alias, but new code should use `latin_hypercube_lite` for naming honesty.
