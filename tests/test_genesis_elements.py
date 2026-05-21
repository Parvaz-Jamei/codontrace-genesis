from __future__ import annotations

from codontrace.genesis import ELEMENT_SPECS, ElementKind, ElementOrigin, ElementSpec


def test_all_8_elements_exist_with_stable_symbols() -> None:
    symbols = [spec.kind.value for spec in ELEMENT_SPECS]
    assert symbols == ["Ig", "Ae", "Tr", "Aq", "Lu", "Vi", "Um", "Nx"]
    assert len(set(symbols)) == 8


def test_primordial_and_emergent_classification() -> None:
    by_kind = {spec.kind: spec for spec in ELEMENT_SPECS}
    assert by_kind[ElementKind.IGNIS].origin is ElementOrigin.PRIMORDIAL
    assert by_kind[ElementKind.AETHER].origin is ElementOrigin.PRIMORDIAL
    assert by_kind[ElementKind.TERRA].origin is ElementOrigin.PRIMORDIAL
    assert by_kind[ElementKind.AQUA].origin is ElementOrigin.EMERGENT
    assert by_kind[ElementKind.LUMEN].origin is ElementOrigin.EMERGENT
    assert by_kind[ElementKind.VITAE].origin is ElementOrigin.EMERGENT
    assert by_kind[ElementKind.UMBRA].origin is ElementOrigin.EMERGENT
    assert by_kind[ElementKind.NEXUS].origin is ElementOrigin.EMERGENT


def test_element_serialization_roundtrip() -> None:
    spec = ELEMENT_SPECS[0]
    restored = ElementSpec.from_dict(spec.to_dict())
    assert restored == spec
