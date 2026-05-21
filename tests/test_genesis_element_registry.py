from __future__ import annotations

import pytest

from codontrace import ElementKind
from codontrace.errors import ConfigurationError
from codontrace.genesis import ElementRegistry


def test_genesis_v0_registry_contains_stable_symbols_and_digest() -> None:
    registry = ElementRegistry.genesis_v0()
    assert set(registry.symbols()) == {"Ig", "Ae", "Tr", "Aq", "Lu", "Vi", "Um", "Nx"}
    assert ElementRegistry.from_dict(registry.to_dict()).digest() == registry.digest()
    assert registry.require(ElementKind.LUMEN).symbol == "Lu"


def test_custom_element_properties_roundtrip_and_duplicates_fail() -> None:
    registry = ElementRegistry.genesis_v0().define(
        symbol="Pl",
        name="Plasma",
        origin="emergent",
        layer="energy",
        properties={"energy_density": 3.5, "toxic": True},
    )
    assert registry.require("Pl").properties == {"energy_density": 3.5, "toxic": True}
    restored = ElementRegistry.from_dict(registry.to_dict())
    assert restored.require("Pl").properties == registry.require("Pl").properties
    with pytest.raises(ConfigurationError):
        registry.define(symbol="Pl", name="Duplicate", origin="emergent", layer="energy")
