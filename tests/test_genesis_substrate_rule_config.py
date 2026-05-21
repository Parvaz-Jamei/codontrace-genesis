from __future__ import annotations

from codontrace.genesis import ElementGrid, ElementRegistry, SubstrateRuleConfig


def test_custom_substrate_rule_and_threshold_efficiency() -> None:
    registry = (
        ElementRegistry.genesis_v0()
        .define(symbol="Pl", name="Plasma", origin="emergent", layer="energy")
        .define(symbol="St", name="Steam", origin="emergent", layer="medium")
    )
    rules = SubstrateRuleConfig.empty().add(
        inputs=("Pl", "Aq"), output="St", threshold=1.0, efficiency=0.5
    )
    grid = ElementGrid.from_cells(
        1,
        1,
        {(0, 0): {"Pl": 4.0, "Aq": 4.0}},
        registry=registry,
        rules=rules,
    )
    result = grid.step()
    assert grid.amount((0, 0), "St") == 2.0
    assert result.conversion_loss == 2.0
    assert SubstrateRuleConfig.from_dict(rules.to_dict()).digest() == rules.digest()
