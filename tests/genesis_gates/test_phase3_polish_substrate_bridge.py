from __future__ import annotations

from codontrace.genesis.engine import GenesisEngine, GenesisExperimentSpec
from codontrace.genesis.substrate import ElementGrid, ElementKind


def test_engine_exposes_element_grid_bridge_digest() -> None:
    grid = ElementGrid(width=3, height=3, cells={(1, 1): {ElementKind.LUMEN: 2.0}})
    spec = GenesisExperimentSpec(
        genome_bits=("000",),
        tick_count=1,
        element_grid=grid,
        substrate_bridge_mode="element_grid_source",
    )
    result = GenesisEngine.from_spec(spec).run_ticks()

    assert result.snapshot.element_grid_digest
    assert result.snapshot.substrate_bridge_mode == "element_grid_source"
    assert result.manifest.config_hash == spec.digest()
