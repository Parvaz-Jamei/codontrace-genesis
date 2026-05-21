"""GENESIS element vocabulary and open element registry contracts.

This module keeps the stable GENESIS v0 ``ElementKind`` enum for backward
compatibility while adding an open ``ElementRegistry`` for research extensions.
Custom elements are JSON-safe symbol definitions, not claims of fully endogenous
chemical emergence.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from enum import Enum
from types import MappingProxyType
from typing import Final

from codontrace._types import JsonValue
from codontrace.errors import ConfigurationError


class ElementKind(str, Enum):
    """Stable GENESIS v0 element symbols."""

    IGNIS = "Ig"
    AETHER = "Ae"
    TERRA = "Tr"
    AQUA = "Aq"
    LUMEN = "Lu"
    VITAE = "Vi"
    UMBRA = "Um"
    NEXUS = "Nx"


class ElementOrigin(str, Enum):
    """Whether an element is a primordial seed or an emergent label."""

    PRIMORDIAL = "primordial"
    EMERGENT = "emergent"


@dataclass(frozen=True, slots=True)
class ElementDefinition:
    """Open JSON-safe definition for one research element symbol."""

    symbol: str
    name: str
    origin: str
    layer: str
    description: str = ""
    properties: dict[str, JsonValue] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _validate_symbol(self.symbol)
        if not self.name or not self.origin or not self.layer:
            msg = "ElementDefinition name, origin, and layer must be non-empty strings."
            raise ConfigurationError(msg)
        _validate_json_object(self.properties, "ElementDefinition.properties")

    def to_dict(self) -> dict[str, JsonValue]:
        """Return a deterministic JSON-friendly definition."""

        return {
            "symbol": self.symbol,
            "name": self.name,
            "origin": self.origin,
            "layer": self.layer,
            "description": self.description,
            "properties": dict(sorted(self.properties.items())),
        }

    @classmethod
    def from_dict(cls, data: dict[str, JsonValue]) -> ElementDefinition:
        """Restore an element definition from ``to_dict()`` output."""

        symbol = data.get("symbol")
        name = data.get("name")
        origin = data.get("origin")
        layer = data.get("layer")
        description = data.get("description", "")
        properties = data.get("properties", {})
        if not isinstance(symbol, str):
            msg = "ElementDefinition.symbol must be a string."
            raise ConfigurationError(msg)
        if not isinstance(name, str):
            msg = "ElementDefinition.name must be a string."
            raise ConfigurationError(msg)
        if not isinstance(origin, str):
            msg = "ElementDefinition.origin must be a string."
            raise ConfigurationError(msg)
        if not isinstance(layer, str):
            msg = "ElementDefinition.layer must be a string."
            raise ConfigurationError(msg)
        if not isinstance(description, str):
            msg = "ElementDefinition.description must be a string."
            raise ConfigurationError(msg)
        if not isinstance(properties, dict):
            msg = "ElementDefinition.properties must be an object."
            raise ConfigurationError(msg)
        return cls(
            symbol=symbol,
            name=name,
            origin=origin,
            layer=layer,
            description=description,
            properties={str(key): value for key, value in properties.items()},
        )

    def digest(self) -> str:
        """Return a stable digest for this definition."""

        payload = json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class ElementSpec:
    """Backward-compatible JSON-safe descriptor for one GENESIS v0 element."""

    kind: ElementKind
    origin: ElementOrigin
    layer: str
    description: str

    def __post_init__(self) -> None:
        if not self.layer:
            msg = "ElementSpec.layer must not be empty."
            raise ValueError(msg)
        if not self.description:
            msg = "ElementSpec.description must not be empty."
            raise ValueError(msg)

    def to_definition(self) -> ElementDefinition:
        """Return the open registry definition equivalent for this v0 element."""

        return ElementDefinition(
            symbol=self.kind.value,
            name=self.kind.name.title(),
            origin=self.origin.value,
            layer=self.layer,
            description=self.description,
            properties={},
        )

    def to_dict(self) -> dict[str, JsonValue]:
        """Return a JSON-friendly descriptor."""

        return {
            "kind": self.kind.value,
            "name": self.kind.name,
            "origin": self.origin.value,
            "layer": self.layer,
            "description": self.description,
        }

    @classmethod
    def from_dict(cls, data: dict[str, JsonValue]) -> ElementSpec:
        """Restore an element descriptor from ``to_dict()`` output."""

        raw_kind = data.get("kind")
        raw_origin = data.get("origin")
        raw_layer = data.get("layer")
        raw_description = data.get("description")
        if not isinstance(raw_kind, str):
            msg = "ElementSpec.kind must be a string."
            raise ValueError(msg)
        if not isinstance(raw_origin, str):
            msg = "ElementSpec.origin must be a string."
            raise ValueError(msg)
        if not isinstance(raw_layer, str) or not isinstance(raw_description, str):
            msg = "ElementSpec.layer and description must be strings."
            raise ValueError(msg)
        return cls(
            kind=ElementKind(raw_kind),
            origin=ElementOrigin(raw_origin),
            layer=raw_layer,
            description=raw_description,
        )


class ElementRegistry:
    """Open deterministic registry for GENESIS substrate elements."""

    def __init__(self, definitions: tuple[ElementDefinition, ...] = ()) -> None:
        mapping: dict[str, ElementDefinition] = {}
        for definition in definitions:
            if definition.symbol in mapping:
                msg = f"Duplicate element symbol {definition.symbol!r}."
                raise ConfigurationError(msg)
            mapping[definition.symbol] = definition
        self._definitions = MappingProxyType(mapping)

    @classmethod
    def empty(cls) -> ElementRegistry:
        """Return an empty registry."""

        return cls(())

    @classmethod
    def genesis_v0(cls) -> ElementRegistry:
        """Return the GENESIS v0 preset registry."""

        return cls(tuple(spec.to_definition() for spec in ELEMENT_SPECS))

    def define(
        self,
        *,
        symbol: str,
        name: str,
        origin: str,
        layer: str,
        description: str = "",
        properties: dict[str, JsonValue] | None = None,
    ) -> ElementRegistry:
        """Return a new registry with one additional element definition."""

        definition = ElementDefinition(
            symbol=symbol,
            name=name,
            origin=origin,
            layer=layer,
            description=description,
            properties={} if properties is None else dict(properties),
        )
        if definition.symbol in self._definitions:
            msg = f"Element symbol {definition.symbol!r} is already defined."
            raise ConfigurationError(msg)
        return ElementRegistry((*self._definitions.values(), definition))

    def get(self, symbol: ElementKind | str) -> ElementDefinition | None:
        """Return a definition or ``None`` for an unknown symbol."""

        return self._definitions.get(_symbol(symbol))

    def require(self, symbol: ElementKind | str) -> ElementDefinition:
        """Return a definition or fail clearly for an unknown symbol."""

        key = _symbol(symbol)
        try:
            return self._definitions[key]
        except KeyError as exc:
            msg = f"Unknown element symbol {key!r}."
            raise ConfigurationError(msg) from exc

    def symbols(self) -> tuple[str, ...]:
        """Return registered symbols in deterministic order."""

        return tuple(sorted(self._definitions))

    def to_dict(self) -> dict[str, JsonValue]:
        """Return a JSON-friendly registry payload."""

        return {
            "definitions": [
                self._definitions[symbol].to_dict() for symbol in sorted(self._definitions)
            ]
        }

    @classmethod
    def from_dict(cls, data: dict[str, JsonValue]) -> ElementRegistry:
        """Restore a registry from ``to_dict()`` output."""

        raw = data.get("definitions")
        if not isinstance(raw, list):
            msg = "ElementRegistry.definitions must be a list."
            raise ConfigurationError(msg)
        definitions = []
        for item in raw:
            if not isinstance(item, dict):
                msg = "ElementRegistry definition entries must be objects."
                raise ConfigurationError(msg)
            definitions.append(ElementDefinition.from_dict(item))
        return cls(tuple(definitions))

    def digest(self) -> str:
        """Return a stable digest for registry content."""

        payload = json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()


ELEMENT_SPECS: Final[tuple[ElementSpec, ...]] = (
    ElementSpec(ElementKind.IGNIS, ElementOrigin.PRIMORDIAL, "energy", "Reactive heat/drive seed."),
    ElementSpec(ElementKind.AETHER, ElementOrigin.PRIMORDIAL, "space", "Empty carrier substrate."),
    ElementSpec(
        ElementKind.TERRA, ElementOrigin.PRIMORDIAL, "matter", "Solid boundary/support seed."
    ),
    ElementSpec(ElementKind.AQUA, ElementOrigin.EMERGENT, "medium", "Designed fluid/flow label."),
    ElementSpec(
        ElementKind.LUMEN, ElementOrigin.EMERGENT, "energy", "Consumable runtime energy label."
    ),
    ElementSpec(
        ElementKind.VITAE, ElementOrigin.EMERGENT, "organism", "Deferred life-support store label."
    ),
    ElementSpec(ElementKind.UMBRA, ElementOrigin.EMERGENT, "shadow", "Hazard/memory-shadow label."),
    ElementSpec(
        ElementKind.NEXUS, ElementOrigin.EMERGENT, "signal", "Information/signal carrier label."
    ),
)

ELEMENT_BY_KIND: Final[dict[ElementKind, ElementSpec]] = {spec.kind: spec for spec in ELEMENT_SPECS}
ELEMENT_BY_SYMBOL: Final[dict[str, ElementSpec]] = {spec.kind.value: spec for spec in ELEMENT_SPECS}


def get_element_spec(kind: ElementKind | str) -> ElementSpec:
    """Return the canonical GENESIS v0 descriptor for an element kind or symbol."""

    resolved = kind if isinstance(kind, ElementKind) else ElementKind(kind)
    return ELEMENT_BY_KIND[resolved]


def elements_to_dicts() -> list[dict[str, JsonValue]]:
    """Return all canonical GENESIS v0 element descriptors in stable order."""

    return [spec.to_dict() for spec in ELEMENT_SPECS]


def _symbol(symbol: ElementKind | str) -> str:
    return symbol.value if isinstance(symbol, ElementKind) else symbol


def _validate_symbol(symbol: str) -> None:
    if not symbol or any(char.isspace() for char in symbol):
        msg = "Element symbols must be non-empty and contain no whitespace."
        raise ConfigurationError(msg)


def _validate_json_object(value: dict[str, JsonValue], name: str) -> None:
    try:
        json.dumps(value, sort_keys=True)
    except (TypeError, ValueError) as exc:
        msg = f"{name} must be JSON-safe."
        raise ConfigurationError(msg) from exc
