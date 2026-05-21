"""Deterministic configurable GENESIS element substrate scaffolding.

The substrate remains a small dependency-free research primitive. GENESIS v0
rules are available as defaults, while custom element registries, rule configs,
and simple quantitative physics settings can be supplied as Python objects.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import TypeAlias, cast

from codontrace._types import JsonValue, Position
from codontrace.errors import ConfigurationError, PlacementError
from codontrace.genesis.elements import ElementKind, ElementRegistry

ElementSymbol: TypeAlias = ElementKind | str


@dataclass(frozen=True, slots=True)
class ElementCell:
    """Immutable view of element amounts at one position."""

    position: Position
    amounts: Mapping[ElementSymbol, float]

    def __post_init__(self) -> None:
        _validate_position(self.position)
        normalized: dict[ElementSymbol, float] = {}
        for raw_kind, raw_amount in self.amounts.items():
            kind = _display_symbol(raw_kind)
            amount = float(raw_amount)
            if amount < 0:
                msg = "Element amounts cannot be negative."
                raise ConfigurationError(msg)
            if amount > 0:
                normalized[kind] = amount
        object.__setattr__(self, "amounts", MappingProxyType(normalized))

    def to_dict(self) -> dict[str, JsonValue]:
        """Return a JSON-friendly cell representation."""

        return {
            "position": [self.position[0], self.position[1]],
            "amounts": {
                _symbol(kind): amount
                for kind, amount in sorted(self.amounts.items(), key=lambda item: _symbol(item[0]))
            },
        }

    @classmethod
    def from_dict(cls, data: dict[str, JsonValue]) -> ElementCell:
        """Restore a cell from ``to_dict()`` output."""

        position_raw = data.get("position")
        amounts_raw = data.get("amounts")
        if not isinstance(position_raw, list) or len(position_raw) != 2:
            msg = "ElementCell.position must be [x, y]."
            raise ConfigurationError(msg)
        if not all(
            isinstance(value, int) and not isinstance(value, bool) for value in position_raw
        ):
            msg = "ElementCell.position must contain integer coordinates."
            raise ConfigurationError(msg)
        if not isinstance(amounts_raw, dict):
            msg = "ElementCell.amounts must be a dictionary."
            raise ConfigurationError(msg)
        amounts: dict[ElementSymbol, float] = {}
        for raw_symbol, raw_amount in amounts_raw.items():
            if not isinstance(raw_symbol, str) or not isinstance(raw_amount, int | float):
                msg = "ElementCell.amount entries must be symbol -> number."
                raise ConfigurationError(msg)
            amounts[_display_symbol(raw_symbol)] = float(raw_amount)
        return cls(
            position=(cast(int, position_raw[0]), cast(int, position_raw[1])),
            amounts=amounts,
        )


@dataclass(frozen=True, slots=True)
class ElementRuleConfig:
    """Backward-compatible high-level switch for deterministic substrate rules."""

    conservation_tolerance: float = 1e-9
    enable_basic_emergence: bool = True

    def __post_init__(self) -> None:
        if self.conservation_tolerance < 0:
            msg = "conservation_tolerance cannot be negative."
            raise ConfigurationError(msg)

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "conservation_tolerance": self.conservation_tolerance,
            "enable_basic_emergence": self.enable_basic_emergence,
        }

    @classmethod
    def from_dict(cls, data: dict[str, JsonValue]) -> ElementRuleConfig:
        tolerance = data.get("conservation_tolerance", 1e-9)
        enabled = data.get("enable_basic_emergence", True)
        if not isinstance(tolerance, int | float) or isinstance(tolerance, bool):
            msg = "conservation_tolerance must be numeric."
            raise ConfigurationError(msg)
        if not isinstance(enabled, bool):
            msg = "enable_basic_emergence must be boolean."
            raise ConfigurationError(msg)
        return cls(conservation_tolerance=float(tolerance), enable_basic_emergence=enabled)


@dataclass(frozen=True, slots=True)
class SubstrateRule:
    """One deterministic substrate conversion rule."""

    inputs: tuple[str, ...]
    output: str
    threshold: float = 0.0
    efficiency: float = 1.0
    reversible: bool = False
    metadata: dict[str, JsonValue] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.inputs or not self.output:
            msg = "SubstrateRule requires at least one input and one output."
            raise ConfigurationError(msg)
        if any(not symbol or any(char.isspace() for char in symbol) for symbol in self.inputs):
            msg = "SubstrateRule inputs must be non-empty symbols without whitespace."
            raise ConfigurationError(msg)
        if any(char.isspace() for char in self.output):
            msg = "SubstrateRule output must contain no whitespace."
            raise ConfigurationError(msg)
        if self.threshold < 0 or self.efficiency < 0:
            msg = "SubstrateRule threshold and efficiency must be non-negative."
            raise ConfigurationError(msg)
        _validate_json_safe(self.metadata, "SubstrateRule.metadata")

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "inputs": list(self.inputs),
            "output": self.output,
            "threshold": self.threshold,
            "efficiency": self.efficiency,
            "reversible": self.reversible,
            "metadata": dict(sorted(self.metadata.items())),
        }

    @classmethod
    def from_dict(cls, data: dict[str, JsonValue]) -> SubstrateRule:
        inputs = data.get("inputs")
        output = data.get("output")
        threshold = data.get("threshold", 0.0)
        efficiency = data.get("efficiency", 1.0)
        reversible = data.get("reversible", False)
        metadata = data.get("metadata", {})
        if not isinstance(inputs, list) or not all(isinstance(item, str) for item in inputs):
            msg = "SubstrateRule.inputs must be a list of strings."
            raise ConfigurationError(msg)
        if not isinstance(output, str):
            msg = "SubstrateRule.output must be a string."
            raise ConfigurationError(msg)
        if isinstance(threshold, bool) or not isinstance(threshold, int | float):
            msg = "SubstrateRule.threshold must be numeric."
            raise ConfigurationError(msg)
        if isinstance(efficiency, bool) or not isinstance(efficiency, int | float):
            msg = "SubstrateRule.efficiency must be numeric."
            raise ConfigurationError(msg)
        if not isinstance(reversible, bool):
            msg = "SubstrateRule.reversible must be boolean."
            raise ConfigurationError(msg)
        if not isinstance(metadata, dict):
            msg = "SubstrateRule.metadata must be an object."
            raise ConfigurationError(msg)
        input_symbols = tuple(str(item) for item in inputs)
        return cls(
            inputs=input_symbols,
            output=output,
            threshold=float(threshold),
            efficiency=float(efficiency),
            reversible=reversible,
            metadata={str(key): value for key, value in metadata.items()},
        )


class SubstrateRuleConfig:
    """Immutable collection of substrate rules."""

    def __init__(self, rules: tuple[SubstrateRule, ...] = ()) -> None:
        self._rules = tuple(rules)

    @classmethod
    def empty(cls) -> SubstrateRuleConfig:
        return cls(())

    @classmethod
    def genesis_v0(cls) -> SubstrateRuleConfig:
        return cls(
            (
                SubstrateRule(("Ig", "Ae"), "Lu"),
                SubstrateRule(("Ig", "Ae", "Tr"), "Aq"),
                SubstrateRule(("Tr", "Aq"), "Um"),
                SubstrateRule(("Aq", "Lu", "Tr"), "Vi"),
                SubstrateRule(("Vi", "Um"), "Nx"),
            )
        )

    def add(
        self,
        *,
        inputs: tuple[ElementSymbol, ...] | list[ElementSymbol],
        output: ElementSymbol,
        threshold: float = 0.0,
        efficiency: float = 1.0,
        reversible: bool = False,
        metadata: dict[str, JsonValue] | None = None,
    ) -> SubstrateRuleConfig:
        rule = SubstrateRule(
            inputs=tuple(_symbol(item) for item in inputs),
            output=_symbol(output),
            threshold=threshold,
            efficiency=efficiency,
            reversible=reversible,
            metadata={} if metadata is None else dict(metadata),
        )
        return SubstrateRuleConfig((*self._rules, rule))

    @property
    def rules(self) -> tuple[SubstrateRule, ...]:
        return self._rules

    def to_dict(self) -> dict[str, JsonValue]:
        return {"rules": [rule.to_dict() for rule in self._rules]}

    @classmethod
    def from_dict(cls, data: dict[str, JsonValue]) -> SubstrateRuleConfig:
        raw = data.get("rules")
        if not isinstance(raw, list):
            msg = "SubstrateRuleConfig.rules must be a list."
            raise ConfigurationError(msg)
        rules = []
        for item in raw:
            if not isinstance(item, dict):
                msg = "SubstrateRuleConfig rule entries must be objects."
                raise ConfigurationError(msg)
            rules.append(SubstrateRule.from_dict(item))
        return cls(tuple(rules))

    def digest(self) -> str:
        payload = json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class SubstratePhysicsConfig:
    """Small quantitative substrate behavior switches."""

    enable_decay: bool = False
    enable_diffusion: bool = False
    enable_concentration_caps: bool = True
    enable_toxicity_audit: bool = True

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "enable_decay": self.enable_decay,
            "enable_diffusion": self.enable_diffusion,
            "enable_concentration_caps": self.enable_concentration_caps,
            "enable_toxicity_audit": self.enable_toxicity_audit,
        }

    @classmethod
    def from_dict(cls, data: dict[str, JsonValue]) -> SubstratePhysicsConfig:
        return cls(
            enable_decay=_bool(data, "enable_decay", False),
            enable_diffusion=_bool(data, "enable_diffusion", False),
            enable_concentration_caps=_bool(data, "enable_concentration_caps", True),
            enable_toxicity_audit=_bool(data, "enable_toxicity_audit", True),
        )


@dataclass(frozen=True, slots=True)
class ElementGridConfig:
    """Configuration for ElementGrid defaults that must be explicit and validated."""

    background_symbol: str = "Ae"

    def __post_init__(self) -> None:
        if not isinstance(self.background_symbol, str) or not self.background_symbol:
            msg = "ElementGridConfig.background_symbol must be a non-empty string."
            raise ConfigurationError(msg)
        if any(char.isspace() for char in self.background_symbol):
            msg = "ElementGridConfig.background_symbol must contain no whitespace."
            raise ConfigurationError(msg)

    def to_dict(self) -> dict[str, JsonValue]:
        return {"background_symbol": self.background_symbol}

    @classmethod
    def from_dict(cls, data: dict[str, JsonValue]) -> ElementGridConfig:
        raw = data.get("background_symbol", "Ae")
        if not isinstance(raw, str):
            msg = "ElementGridConfig.background_symbol must be a string."
            raise ConfigurationError(msg)
        return cls(background_symbol=raw)


@dataclass(frozen=True, slots=True)
class AppliedSubstrateRuleRecord:
    """Auditable record for one applied substrate conversion rule."""

    rule_id: str
    position: Position
    inputs: tuple[str, ...]
    output: str
    input_amounts_before: dict[str, float]
    consumed_amounts: dict[str, float]
    produced_amount: float
    threshold: float
    efficiency: float
    reversible: bool
    tick: int

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "rule_id": self.rule_id,
            "position": [self.position[0], self.position[1]],
            "inputs": list(self.inputs),
            "output": self.output,
            "input_amounts_before": dict(sorted(self.input_amounts_before.items())),
            "consumed_amounts": dict(sorted(self.consumed_amounts.items())),
            "produced_amount": self.produced_amount,
            "threshold": self.threshold,
            "efficiency": self.efficiency,
            "reversible": self.reversible,
            "tick": self.tick,
        }

    @classmethod
    def from_dict(cls, data: dict[str, JsonValue]) -> AppliedSubstrateRuleRecord:
        raw_position = data.get("position")
        raw_inputs = data.get("inputs")
        if not isinstance(raw_position, list) or len(raw_position) != 2:
            msg = "AppliedSubstrateRuleRecord.position must be [x, y]."
            raise ConfigurationError(msg)
        if not all(_is_int_not_bool(item) for item in raw_position):
            msg = "AppliedSubstrateRuleRecord.position must contain integer coordinates."
            raise ConfigurationError(msg)
        if not isinstance(raw_inputs, list) or not all(
            isinstance(item, str) for item in raw_inputs
        ):
            msg = "AppliedSubstrateRuleRecord.inputs must be a list of strings."
            raise ConfigurationError(msg)
        before = _float_map(data.get("input_amounts_before"), "input_amounts_before")
        consumed = _float_map(data.get("consumed_amounts"), "consumed_amounts")
        return cls(
            rule_id=_required_str(data, "rule_id"),
            position=(cast(int, raw_position[0]), cast(int, raw_position[1])),
            inputs=tuple(str(item) for item in raw_inputs),
            output=_required_str(data, "output"),
            input_amounts_before=before,
            consumed_amounts=consumed,
            produced_amount=_required_float(data, "produced_amount"),
            threshold=_required_float(data, "threshold"),
            efficiency=_required_float(data, "efficiency"),
            reversible=_bool(data, "reversible", False),
            tick=_required_int(data, "tick"),
        )


@dataclass(frozen=True, slots=True)
class ElementStepResult:
    """Summary emitted by one deterministic substrate step."""

    tick: int
    changed_cells: int
    total_energy_before: float
    total_energy_after: float
    element_counts: dict[str, int]
    conversion_gain: float = 0.0
    conversion_loss: float = 0.0
    toxicity_audit: dict[str, float] = field(default_factory=dict)
    applied_rules: tuple[AppliedSubstrateRuleRecord, ...] = ()

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "tick": self.tick,
            "changed_cells": self.changed_cells,
            "total_energy_before": self.total_energy_before,
            "total_energy_after": self.total_energy_after,
            "element_counts": dict(sorted(self.element_counts.items())),
            "conversion_gain": self.conversion_gain,
            "conversion_loss": self.conversion_loss,
            "toxicity_audit": dict(sorted(self.toxicity_audit.items())),
            "applied_rules": [record.to_dict() for record in self.applied_rules],
        }

    @classmethod
    def from_dict(cls, data: dict[str, JsonValue]) -> ElementStepResult:
        raw_rules = data.get("applied_rules", [])
        if not isinstance(raw_rules, list):
            msg = "ElementStepResult.applied_rules must be a list."
            raise ConfigurationError(msg)
        records = []
        for item in raw_rules:
            if not isinstance(item, dict):
                msg = "ElementStepResult.applied_rules entries must be objects."
                raise ConfigurationError(msg)
            records.append(AppliedSubstrateRuleRecord.from_dict(item))
        counts_raw = data.get("element_counts", {})
        if not isinstance(counts_raw, dict):
            msg = "ElementStepResult.element_counts must be an object."
            raise ConfigurationError(msg)
        return cls(
            tick=_required_int(data, "tick"),
            changed_cells=_required_int(data, "changed_cells"),
            total_energy_before=_required_float(data, "total_energy_before"),
            total_energy_after=_required_float(data, "total_energy_after"),
            element_counts={str(k): _int_value(v, "element_counts") for k, v in counts_raw.items()},
            conversion_gain=_required_float(data, "conversion_gain"),
            conversion_loss=_required_float(data, "conversion_loss"),
            toxicity_audit=_float_map(data.get("toxicity_audit", {}), "toxicity_audit"),
            applied_rules=tuple(records),
        )


@dataclass(slots=True)
class ElementGrid:
    """Small deterministic configurable element grid for GENESIS experiments."""

    width: int
    height: int
    cells: dict[Position, dict[ElementSymbol, float]] = field(default_factory=dict)
    rule_config: ElementRuleConfig = field(default_factory=ElementRuleConfig)
    tick: int = 0
    registry: ElementRegistry = field(default_factory=ElementRegistry.genesis_v0)
    rules: SubstrateRuleConfig = field(default_factory=SubstrateRuleConfig.genesis_v0)
    physics_config: SubstratePhysicsConfig = field(default_factory=SubstratePhysicsConfig)
    grid_config: ElementGridConfig = field(default_factory=ElementGridConfig)

    def __post_init__(self) -> None:
        if not _is_int_not_bool(self.width) or not _is_int_not_bool(self.height):
            msg = "ElementGrid width and height must be integers; bool is not accepted."
            raise ConfigurationError(msg)
        if self.width <= 0 or self.height <= 0:
            msg = "ElementGrid dimensions must be positive."
            raise ConfigurationError(msg)
        if not _is_int_not_bool(self.tick) or self.tick < 0:
            msg = "ElementGrid tick must be a non-negative integer; bool is not accepted."
            raise ConfigurationError(msg)
        try:
            self.registry.require(self.grid_config.background_symbol)
        except ConfigurationError as exc:
            msg = (
                "ElementGrid background_symbol "
                f"{self.grid_config.background_symbol!r} is not defined in the registry."
            )
            raise ConfigurationError(msg) from exc
        background = self._background_element()
        normalized: dict[Position, dict[ElementSymbol, float]] = {}
        for y in range(self.height):
            for x in range(self.width):
                normalized[(x, y)] = {background: 1.0}
        for position, amounts in self.cells.items():
            self._ensure_in_bounds(position)
            clean: dict[ElementSymbol, float] = {}
            for raw_kind, raw_amount in amounts.items():
                kind = _display_symbol(raw_kind)
                self.registry.require(_symbol(kind))
                amount = float(raw_amount)
                if amount < 0:
                    msg = "ElementGrid amounts cannot be negative."
                    raise ConfigurationError(msg)
                if amount > 0:
                    clean[kind] = amount
            if clean:
                normalized[position] = self._apply_caps(clean)
        self.cells = normalized

    @classmethod
    def from_cells(
        cls,
        width: int,
        height: int,
        cells: Mapping[Position, Mapping[ElementSymbol, float]],
        *,
        rule_config: ElementRuleConfig | None = None,
        tick: int = 0,
        registry: ElementRegistry | None = None,
        rules: SubstrateRuleConfig | None = None,
        physics_config: SubstratePhysicsConfig | None = None,
        grid_config: ElementGridConfig | None = None,
    ) -> ElementGrid:
        return cls(
            width=width,
            height=height,
            cells={pos: dict(amounts) for pos, amounts in cells.items()},
            rule_config=rule_config or ElementRuleConfig(),
            tick=tick,
            registry=registry or ElementRegistry.genesis_v0(),
            rules=rules or SubstrateRuleConfig.genesis_v0(),
            physics_config=physics_config or SubstratePhysicsConfig(),
            grid_config=grid_config or ElementGridConfig(),
        )

    def cell(self, position: Position) -> ElementCell:
        self._ensure_in_bounds(position)
        return ElementCell(position=position, amounts=self.cells[position])

    def amount(self, position: Position, kind: ElementSymbol) -> float:
        self._ensure_in_bounds(position)
        return self.cells[position].get(_display_symbol(kind), 0.0)

    def set_amount(self, position: Position, kind: ElementSymbol, amount: float) -> None:
        self._ensure_in_bounds(position)
        display_kind = _display_symbol(kind)
        self.registry.require(_symbol(display_kind))
        if amount < 0:
            msg = "Element amount cannot be negative."
            raise ConfigurationError(msg)
        if amount == 0:
            self.cells[position].pop(display_kind, None)
        else:
            self.cells[position][display_kind] = float(amount)
            self.cells[position] = self._apply_caps(self.cells[position])
        if not self.cells[position]:
            self.cells[position][self._background_element()] = 1.0

    def total_energy(self) -> float:
        return round(
            sum(amount for amounts in self.cells.values() for amount in amounts.values()),
            10,
        )

    def step(self) -> ElementStepResult:
        """Apply one deterministic substrate step."""

        before = self.total_energy()
        next_cells = {position: dict(amounts) for position, amounts in self.cells.items()}
        changed_positions: set[Position] = set()
        applied_rules: list[AppliedSubstrateRuleRecord] = []
        if self.physics_config.enable_decay:
            for position, amounts in list(next_cells.items()):
                next_cells[position] = self._apply_decay(amounts)
                if next_cells[position] != amounts:
                    changed_positions.add(position)
        if self.physics_config.enable_diffusion:
            next_cells, diffusion_changed = self._apply_diffusion(next_cells)
            changed_positions.update(diffusion_changed)
        if self.rule_config.enable_basic_emergence:
            for position, amounts in sorted(next_cells.items()):
                updated = dict(amounts)
                for rule in self.rules.rules:
                    if updated.get(_display_symbol(rule.output), 0.0) > 0:
                        continue
                    input_amounts = [
                        updated.get(_display_symbol(kind), 0.0) for kind in rule.inputs
                    ]
                    required = rule.threshold if rule.threshold > 0 else 0.0
                    if all(
                        amount >= required if rule.threshold > 0 else amount > 0
                        for amount in input_amounts
                    ):
                        input_before = {
                            _symbol(kind): updated.get(_display_symbol(kind), 0.0)
                            for kind in rule.inputs
                        }
                        transfer = round(min(input_amounts) / len(rule.inputs), 10)
                        if transfer <= 0:
                            continue
                        for raw_kind in rule.inputs:
                            kind = _display_symbol(raw_kind)
                            updated[kind] = round(updated.get(kind, 0.0) - transfer, 10)
                            if updated[kind] <= 0:
                                updated.pop(kind, None)
                        output = _display_symbol(rule.output)
                        produced = round(transfer * len(rule.inputs) * rule.efficiency, 10)
                        updated[output] = round(updated.get(output, 0.0) + produced, 10)
                        applied_rules.append(
                            AppliedSubstrateRuleRecord(
                                rule_id=_rule_digest(rule),
                                position=position,
                                inputs=tuple(_symbol(kind) for kind in rule.inputs),
                                output=_symbol(rule.output),
                                input_amounts_before=input_before,
                                consumed_amounts={_symbol(kind): transfer for kind in rule.inputs},
                                produced_amount=produced,
                                threshold=rule.threshold,
                                efficiency=rule.efficiency,
                                reversible=rule.reversible,
                                tick=self.tick + 1,
                            )
                        )
                        changed_positions.add(position)
                next_cells[position] = self._apply_caps(updated) or {
                    self._background_element(): 1.0
                }
        self.cells = next_cells
        self.tick += 1
        after = self.total_energy()
        delta = round(after - before, 10)
        if (
            abs(delta) > self.rule_config.conservation_tolerance
            and not self.physics_config.enable_decay
            and not self.physics_config.enable_diffusion
            and all(rule.efficiency == 1.0 for rule in self.rules.rules)
        ):
            msg = "ElementGrid conservation metric exceeded tolerance."
            raise ConfigurationError(msg)
        return ElementStepResult(
            tick=self.tick,
            changed_cells=len(changed_positions),
            total_energy_before=before,
            total_energy_after=after,
            element_counts=self.element_counts(),
            conversion_gain=max(delta, 0.0),
            conversion_loss=max(-delta, 0.0),
            toxicity_audit=self._toxicity_audit(),
            applied_rules=tuple(applied_rules),
        )

    def element_counts(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for amounts in self.cells.values():
            for kind, amount in amounts.items():
                if amount > 0:
                    symbol = _symbol(kind)
                    counts[symbol] = counts.get(symbol, 0) + 1
        return dict(sorted(counts.items()))

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "width": self.width,
            "height": self.height,
            "tick": self.tick,
            "rule_config": self.rule_config.to_dict(),
            "registry": self.registry.to_dict(),
            "rules": self.rules.to_dict(),
            "physics_config": self.physics_config.to_dict(),
            "grid_config": self.grid_config.to_dict(),
            "cells": [self.cell(position).to_dict() for position in sorted(self.cells)],
        }

    @classmethod
    def from_dict(cls, data: dict[str, JsonValue]) -> ElementGrid:
        width = data.get("width")
        height = data.get("height")
        tick = data.get("tick", 0)
        raw_config = data.get("rule_config", {})
        raw_registry = data.get("registry")
        raw_rules = data.get("rules")
        raw_physics = data.get("physics_config")
        raw_grid_config = data.get("grid_config")
        raw_cells = data.get("cells", [])
        if not _is_int_not_bool(width) or not _is_int_not_bool(height):
            msg = "ElementGrid data requires integer width and height."
            raise ConfigurationError(msg)
        if not _is_int_not_bool(tick):
            msg = "ElementGrid.tick must be an integer."
            raise ConfigurationError(msg)
        if not isinstance(raw_config, dict) or not isinstance(raw_cells, list):
            msg = "ElementGrid data requires rule_config dictionary and cells list."
            raise ConfigurationError(msg)
        registry = (
            ElementRegistry.from_dict(raw_registry)
            if isinstance(raw_registry, dict)
            else ElementRegistry.genesis_v0()
        )
        rules = (
            SubstrateRuleConfig.from_dict(raw_rules)
            if isinstance(raw_rules, dict)
            else SubstrateRuleConfig.genesis_v0()
        )
        physics_config = (
            SubstratePhysicsConfig.from_dict(raw_physics)
            if isinstance(raw_physics, dict)
            else SubstratePhysicsConfig()
        )
        grid_config = (
            ElementGridConfig.from_dict(raw_grid_config)
            if isinstance(raw_grid_config, dict)
            else ElementGridConfig()
        )
        cells: dict[Position, dict[ElementSymbol, float]] = {}
        for item in raw_cells:
            if not isinstance(item, dict):
                msg = "ElementGrid cells must be dictionaries."
                raise ConfigurationError(msg)
            cell = ElementCell.from_dict(item)
            cells[cell.position] = dict(cell.amounts)
        return cls(
            width=cast(int, width),
            height=cast(int, height),
            cells=cells,
            rule_config=ElementRuleConfig.from_dict(raw_config),
            tick=cast(int, tick),
            registry=registry,
            rules=rules,
            physics_config=physics_config,
            grid_config=grid_config,
        )

    def digest(self) -> str:
        payload = json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def _background_element(self) -> ElementSymbol:
        return _display_symbol(self.grid_config.background_symbol)

    def _ensure_in_bounds(self, position: Position) -> None:
        _validate_position(position)
        if not (0 <= position[0] < self.width and 0 <= position[1] < self.height):
            msg = f"Position {position!r} is outside the ElementGrid."
            raise PlacementError(msg)

    def _apply_caps(self, amounts: Mapping[ElementSymbol, float]) -> dict[ElementSymbol, float]:
        capped: dict[ElementSymbol, float] = {}
        for kind, amount in amounts.items():
            definition = self.registry.require(_symbol(kind))
            cap = definition.properties.get("max_concentration")
            if self.physics_config.enable_concentration_caps and isinstance(cap, int | float):
                capped[_display_symbol(kind)] = min(float(amount), float(cap))
            else:
                capped[_display_symbol(kind)] = float(amount)
        return {kind: value for kind, value in capped.items() if value > 0}

    def _apply_decay(self, amounts: Mapping[ElementSymbol, float]) -> dict[ElementSymbol, float]:
        decayed: dict[ElementSymbol, float] = {}
        for kind, amount in amounts.items():
            definition = self.registry.require(_symbol(kind))
            raw_rate = definition.properties.get("decay_rate", 0.0)
            rate = float(raw_rate) if isinstance(raw_rate, int | float) else 0.0
            kept = round(float(amount) * max(0.0, 1.0 - rate), 10)
            if kept > 0:
                decayed[_display_symbol(kind)] = kept
        return decayed or {self._background_element(): 1.0}

    def _apply_diffusion(
        self, cells: dict[Position, dict[ElementSymbol, float]]
    ) -> tuple[dict[Position, dict[ElementSymbol, float]], set[Position]]:
        next_cells: dict[Position, dict[ElementSymbol, float]] = {
            position: {} for position in cells
        }
        changed: set[Position] = set()
        for position, amounts in cells.items():
            for kind, amount in amounts.items():
                definition = self.registry.require(_symbol(kind))
                raw_rate = definition.properties.get("diffusion_rate", 0.0)
                rate = float(raw_rate) if isinstance(raw_rate, int | float) else 0.0
                neighbors = self._neighbors(position)
                movable = round(amount * max(0.0, min(rate, 1.0)), 10)
                kept = round(amount - movable, 10)
                _add_amount(next_cells[position], kind, kept)
                if movable > 0 and neighbors:
                    share = round(movable / len(neighbors), 10)
                    for neighbor in neighbors:
                        _add_amount(next_cells[neighbor], kind, share)
                    changed.add(position)
                    changed.update(neighbors)
                elif movable > 0:
                    _add_amount(next_cells[position], kind, movable)
        return (
            {
                position: self._apply_caps(amounts) or {self._background_element(): 1.0}
                for position, amounts in next_cells.items()
            },
            changed,
        )

    def _neighbors(self, position: Position) -> tuple[Position, ...]:
        candidates = (
            (position[0] + 1, position[1]),
            (position[0] - 1, position[1]),
            (position[0], position[1] + 1),
            (position[0], position[1] - 1),
        )
        return tuple(
            item for item in candidates if 0 <= item[0] < self.width and 0 <= item[1] < self.height
        )

    def _toxicity_audit(self) -> dict[str, float]:
        if not self.physics_config.enable_toxicity_audit:
            return {}
        audit: dict[str, float] = {}
        for amounts in self.cells.values():
            for kind, amount in amounts.items():
                definition = self.registry.require(_symbol(kind))
                toxicity = definition.properties.get("toxicity", 0.0)
                if isinstance(toxicity, int | float) and toxicity > 0:
                    symbol = _symbol(kind)
                    audit[symbol] = round(
                        audit.get(symbol, 0.0) + float(amount) * float(toxicity), 10
                    )
        return dict(sorted(audit.items()))


def world2d_to_element_grid(world: object) -> ElementGrid:
    """Map a World2D instance to a GENESIS ElementGrid."""

    from codontrace.world import World2D

    if not isinstance(world, World2D):
        msg = "world2d_to_element_grid expects a World2D instance."
        raise ConfigurationError(msg)
    cells: dict[Position, dict[ElementSymbol, float]] = {}
    marker_map = {
        "I": ElementKind.IGNIS,
        "V": ElementKind.VITAE,
        "U": ElementKind.UMBRA,
        "N": ElementKind.NEXUS,
    }
    for y in range(world.height):
        for x in range(world.width):
            position = (x, y)
            if position in world.walls:
                cells[position] = {ElementKind.TERRA: 1.0}
            elif position in world.resources:
                cells[position] = {ElementKind.LUMEN: world.resources[position]}
            elif position in world.custom_cells:
                marker = world.custom_cells[position]
                try:
                    cells[position] = {marker_map[marker]: 1.0}
                except KeyError as exc:
                    msg = f"Unsupported GENESIS custom marker {marker!r}."
                    raise ConfigurationError(msg) from exc
            else:
                cells[position] = {ElementKind.AETHER: 1.0}
    return ElementGrid(width=world.width, height=world.height, cells=cells)


def element_grid_to_world2d(grid: ElementGrid) -> object:
    """Map supported ElementGrid cells back to a World2D instance."""

    from codontrace.world import World2D

    world = World2D(grid.width, grid.height)
    reverse_markers = {
        "Ig": "I",
        "Vi": "V",
        "Um": "U",
        "Nx": "N",
    }
    for position, amounts in sorted(grid.cells.items()):
        dominant = _symbol(_dominant_element(amounts))
        if dominant == ElementKind.AETHER.value:
            continue
        if dominant == ElementKind.TERRA.value:
            world.set_cell(position, World2D.WALL)
        elif dominant == ElementKind.LUMEN.value:
            world.place_resource(position, max(0.0000000001, amounts[_display_symbol(dominant)]))
        elif dominant in reverse_markers:
            world.set_custom_cell(position, reverse_markers[dominant])
        else:
            msg = f"Element {dominant!r} has no supported World2D marker."
            raise ConfigurationError(msg)
    return world


def _dominant_element(amounts: Mapping[ElementSymbol, float]) -> ElementSymbol:
    if not amounts:
        return ElementKind.AETHER
    return sorted(amounts.items(), key=lambda item: (-item[1], _symbol(item[0])))[0][0]


def _display_symbol(symbol: ElementSymbol) -> ElementSymbol:
    if isinstance(symbol, ElementKind):
        return symbol
    try:
        return ElementKind(symbol)
    except ValueError:
        return symbol


def _symbol(symbol: ElementSymbol) -> str:
    return symbol.value if isinstance(symbol, ElementKind) else symbol


def _add_amount(amounts: dict[ElementSymbol, float], kind: ElementSymbol, amount: float) -> None:
    if amount <= 0:
        return
    display = _display_symbol(kind)
    amounts[display] = round(amounts.get(display, 0.0) + amount, 10)


def _validate_position(position: Position) -> None:
    if (
        not isinstance(position, tuple)
        or len(position) != 2
        or not _is_int_not_bool(position[0])
        or not _is_int_not_bool(position[1])
    ):
        msg = "Position must be an (x, y) integer tuple; bool is not accepted."
        raise ConfigurationError(msg)


def _is_int_not_bool(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _rule_digest(rule: SubstrateRule) -> str:
    payload = json.dumps(rule.to_dict(), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _required_str(data: dict[str, JsonValue], key: str) -> str:
    value = data.get(key)
    if not isinstance(value, str):
        msg = f"{key} must be a string."
        raise ConfigurationError(msg)
    return value


def _required_int(data: dict[str, JsonValue], key: str) -> int:
    return _int_value(data.get(key), key)


def _int_value(value: object, key: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        msg = f"{key} must be an integer."
        raise ConfigurationError(msg)
    return value


def _required_float(data: dict[str, JsonValue], key: str) -> float:
    value = data.get(key)
    if isinstance(value, bool) or not isinstance(value, int | float):
        msg = f"{key} must be numeric."
        raise ConfigurationError(msg)
    return float(value)


def _float_map(value: object, name: str) -> dict[str, float]:
    if not isinstance(value, dict):
        msg = f"{name} must be an object."
        raise ConfigurationError(msg)
    out: dict[str, float] = {}
    for key, raw in value.items():
        if not isinstance(key, str) or isinstance(raw, bool) or not isinstance(raw, int | float):
            msg = f"{name} entries must be string -> numeric."
            raise ConfigurationError(msg)
        out[key] = float(raw)
    return out


def _bool(data: dict[str, JsonValue], key: str, default: bool) -> bool:
    value = data.get(key, default)
    if not isinstance(value, bool):
        msg = f"{key} must be a boolean."
        raise ConfigurationError(msg)
    return value


def _validate_json_safe(value: dict[str, JsonValue], name: str) -> None:
    try:
        json.dumps(value, sort_keys=True)
    except (TypeError, ValueError) as exc:
        msg = f"{name} must be JSON-safe."
        raise ConfigurationError(msg) from exc
