from __future__ import annotations

from codontrace.genesis import ElementGrid, ElementRegistry, SubstratePhysicsConfig


def test_quantitative_decay_caps_diffusion_and_toxicity_audit() -> None:
    registry = ElementRegistry.genesis_v0().define(
        symbol="Pl",
        name="Plasma",
        origin="emergent",
        layer="energy",
        properties={
            "decay_rate": 0.25,
            "diffusion_rate": 0.5,
            "max_concentration": 10.0,
            "toxicity": 2.0,
        },
    )
    grid = ElementGrid.from_cells(
        2,
        1,
        {(0, 0): {"Pl": 20.0}, (1, 0): {"Ae": 1.0}},
        registry=registry,
        physics_config=SubstratePhysicsConfig(enable_decay=True, enable_diffusion=True),
    )
    result = grid.step()
    assert grid.amount((0, 0), "Pl") <= 10.0
    assert grid.amount((1, 0), "Pl") > 0
    assert result.toxicity_audit["Pl"] > 0
