"""Dependency-free public API audit objects for GENESIS modules.

The helpers in this module return Python objects only. They do not write files,
run a CLI, generate reports, or freeze a public API contract prematurely.
"""

from __future__ import annotations

import hashlib
import inspect
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, is_dataclass
from enum import Enum
from types import ModuleType
from typing import Any

from codontrace._types import JsonValue
from codontrace.errors import ConfigurationError


class APIStabilityLevel(str, Enum):
    EXPERIMENTAL = "experimental"
    ALPHA = "alpha"
    STABLE_CANDIDATE = "stable_candidate"
    DEPRECATED = "deprecated"


@dataclass(frozen=True, slots=True)
class PublicAPISymbol:
    """One public API symbol with lightweight stability metadata."""

    name: str
    module: str
    kind: str
    stability: str = APIStabilityLevel.ALPHA.value
    added_in: str = "0.3.0a1"
    notes: str = ""
    module_path: str = ""
    object_qualname: str = ""

    def __post_init__(self) -> None:
        if not self.name or not self.module or not self.kind:
            msg = "PublicAPISymbol name, module, and kind must not be empty."
            raise ConfigurationError(msg)
        try:
            APIStabilityLevel(str(self.stability))
        except ValueError as exc:
            msg = (
                "PublicAPISymbol.stability must be experimental, alpha, "
                "stable_candidate, or deprecated."
            )
            raise ConfigurationError(msg) from exc
        if not self.module_path:
            object.__setattr__(self, "module_path", self.module)
        if not self.object_qualname:
            object.__setattr__(self, "object_qualname", self.name)

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "name": self.name,
            "module": self.module,
            "kind": self.kind,
            "stability": self.stability,
            "added_in": self.added_in,
            "notes": self.notes,
            "module_path": self.module_path,
            "object_qualname": self.object_qualname,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, JsonValue]) -> PublicAPISymbol:
        return cls(
            name=_str(data, "name"),
            module=_str(data, "module"),
            kind=_str(data, "kind"),
            stability=_str(data, "stability", APIStabilityLevel.ALPHA.value),
            added_in=_str(data, "added_in", "unknown"),
            notes=_str(data, "notes", ""),
            module_path=_str(data, "module_path", ""),
            object_qualname=_str(data, "object_qualname", ""),
        )

    def digest(self) -> str:
        return _digest(self.to_dict())


@dataclass(frozen=True, slots=True)
class DeprecatedAPISymbol:
    name: str
    module: str
    deprecated_in: str
    removal_not_before: str
    replacement: str
    reason: str = ""

    def __post_init__(self) -> None:
        if not self.name or not self.module or not self.deprecated_in:
            msg = "DeprecatedAPISymbol name/module/deprecated_in must not be empty."
            raise ConfigurationError(msg)

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "name": self.name,
            "module": self.module,
            "deprecated_in": self.deprecated_in,
            "removal_not_before": self.removal_not_before,
            "replacement": self.replacement,
            "reason": self.reason,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, JsonValue]) -> DeprecatedAPISymbol:
        return cls(
            name=_str(data, "name"),
            module=_str(data, "module"),
            deprecated_in=_str(data, "deprecated_in"),
            removal_not_before=_str(data, "removal_not_before"),
            replacement=_str(data, "replacement", ""),
            reason=_str(data, "reason", ""),
        )

    def digest(self) -> str:
        return _digest(self.to_dict())


@dataclass(frozen=True, slots=True)
class APIDeprecationAuditResult:
    attempted: bool
    succeeded: bool
    deprecated_symbols: tuple[DeprecatedAPISymbol, ...]
    missing_replacements: tuple[str, ...] = ()
    unsafe_removals: tuple[str, ...] = ()
    reasons: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "attempted": self.attempted,
            "succeeded": self.succeeded,
            "deprecated_symbols": [item.to_dict() for item in self.deprecated_symbols],
            "missing_replacements": list(self.missing_replacements),
            "unsafe_removals": list(self.unsafe_removals),
            "reasons": list(self.reasons),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, JsonValue]) -> APIDeprecationAuditResult:
        raw = data.get("deprecated_symbols", [])
        if not isinstance(raw, list):
            msg = "deprecated_symbols must be a list."
            raise ConfigurationError(msg)
        return cls(
            attempted=_bool(data, "attempted", False),
            succeeded=_bool(data, "succeeded", False),
            deprecated_symbols=tuple(
                DeprecatedAPISymbol.from_dict(_mapping(item, "deprecated_symbol")) for item in raw
            ),
            missing_replacements=_str_tuple(data, "missing_replacements"),
            unsafe_removals=_str_tuple(data, "unsafe_removals"),
            reasons=_str_tuple(data, "reasons"),
        )

    def digest(self) -> str:
        return _digest(self.to_dict())


@dataclass(frozen=True, slots=True)
class APIAuditResult:
    """Result of public export validation; not a report writer."""

    attempted: bool
    succeeded: bool
    public_symbol_count: int
    missing_from_all: tuple[str, ...] = ()
    undocumented_symbols: tuple[str, ...] = ()
    deprecated_symbols: tuple[str, ...] = ()
    reasons: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "attempted": self.attempted,
            "succeeded": self.succeeded,
            "public_symbol_count": self.public_symbol_count,
            "missing_from_all": list(self.missing_from_all),
            "undocumented_symbols": list(self.undocumented_symbols),
            "deprecated_symbols": list(self.deprecated_symbols),
            "reasons": list(self.reasons),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, JsonValue]) -> APIAuditResult:
        return cls(
            attempted=_bool(data, "attempted", False),
            succeeded=_bool(data, "succeeded", False),
            public_symbol_count=_int(data, "public_symbol_count", 0),
            missing_from_all=_str_tuple(data, "missing_from_all"),
            undocumented_symbols=_str_tuple(data, "undocumented_symbols"),
            deprecated_symbols=_str_tuple(data, "deprecated_symbols"),
            reasons=_str_tuple(data, "reasons"),
        )

    def digest(self) -> str:
        return _digest(self.to_dict())


@dataclass(frozen=True, slots=True)
class CompatibilitySnapshot:
    """Small object snapshot for release-candidate compatibility audits."""

    version: str
    public_symbols: tuple[str, ...]
    examples: tuple[str, ...] = ()
    docs_sections: tuple[str, ...] = ()
    config_defaults_digest: str = ""
    metadata_digest: str = ""

    def __post_init__(self) -> None:
        if not self.version:
            msg = "CompatibilitySnapshot.version must not be empty."
            raise ConfigurationError(msg)
        object.__setattr__(self, "public_symbols", tuple(sorted(self.public_symbols)))
        object.__setattr__(self, "examples", tuple(sorted(self.examples)))
        object.__setattr__(self, "docs_sections", tuple(sorted(self.docs_sections)))

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "version": self.version,
            "public_symbols": list(self.public_symbols),
            "examples": list(self.examples),
            "docs_sections": list(self.docs_sections),
            "config_defaults_digest": self.config_defaults_digest,
            "metadata_digest": self.metadata_digest,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, JsonValue]) -> CompatibilitySnapshot:
        return cls(
            version=_str(data, "version"),
            public_symbols=_str_tuple(data, "public_symbols"),
            examples=_str_tuple(data, "examples"),
            docs_sections=_str_tuple(data, "docs_sections"),
            config_defaults_digest=_str(data, "config_defaults_digest", ""),
            metadata_digest=_str(data, "metadata_digest", ""),
        )

    def digest(self) -> str:
        return _digest(self.to_dict())


def collect_genesis_public_api(symbols: Sequence[str] | None = None) -> tuple[PublicAPISymbol, ...]:
    """Collect public GENESIS symbols from ``codontrace.genesis.__all__``.

    When ``symbols`` is provided, the function returns metadata for the selected
    names and labels missing names as ``kind='missing'``. Use
    ``validate_genesis_exports`` to fail on missing names.
    """

    from codontrace import genesis

    requested = (
        tuple(str(item) for item in symbols)
        if symbols is not None
        else tuple(getattr(genesis, "__all__", ()))
    )
    return tuple(_symbol_for_name(genesis, name) for name in sorted(requested))


def validate_genesis_exports(symbols: Sequence[str] | None = None) -> APIAuditResult:
    """Validate real public exports on ``codontrace.genesis``."""

    from codontrace import genesis

    all_raw = getattr(genesis, "__all__", None)
    reasons: list[str] = []
    missing: list[str] = []
    if not isinstance(all_raw, list):
        reasons.append("missing_or_invalid___all__")
        all_names: tuple[str, ...] = ()
    else:
        all_names = tuple(str(item) for item in all_raw)
    duplicates = tuple(sorted({name for name in all_names if all_names.count(name) > 1}))
    if duplicates:
        reasons.extend(f"duplicate:{name}" for name in duplicates)
    for name in all_names:
        if not hasattr(genesis, name):
            missing.append(name)
            reasons.append(f"missing_attribute:{name}")
    if symbols is not None:
        for name in tuple(str(item) for item in symbols):
            if name not in all_names:
                missing.append(name)
                reasons.append(f"missing_from___all__:{name}")
            if not hasattr(genesis, name) and f"missing_attribute:{name}" not in reasons:
                reasons.append(f"missing_attribute:{name}")
    return APIAuditResult(
        attempted=True,
        succeeded=not reasons,
        public_symbol_count=len(all_names),
        missing_from_all=tuple(sorted(set(missing))),
        undocumented_symbols=(),
        deprecated_symbols=(),
        reasons=tuple(reasons) if reasons else ("exports_validated",),
    )


def audit_deprecations(
    deprecated_symbols: Sequence[DeprecatedAPISymbol], *, current_symbols: Sequence[str]
) -> APIDeprecationAuditResult:
    """Validate deprecation records without removing APIs silently."""

    current = set(current_symbols)
    missing_replacements: list[str] = []
    unsafe_removals: list[str] = []
    for symbol in deprecated_symbols:
        if symbol.replacement and symbol.replacement not in current:
            missing_replacements.append(symbol.name)
        if symbol.name not in current:
            unsafe_removals.append(symbol.name)
    reasons: list[str] = []
    if missing_replacements:
        reasons.append("missing_replacement")
    if unsafe_removals:
        reasons.append("unsafe_removal")
    return APIDeprecationAuditResult(
        attempted=True,
        succeeded=not reasons,
        deprecated_symbols=tuple(deprecated_symbols),
        missing_replacements=tuple(sorted(missing_replacements)),
        unsafe_removals=tuple(sorted(unsafe_removals)),
        reasons=tuple(reasons) if reasons else ("deprecations_validated",),
    )


def build_compatibility_snapshot(
    *,
    version: str,
    public_symbols: Sequence[str],
    examples: Sequence[str] = (),
    docs_sections: Sequence[str] = (),
    config_defaults: Mapping[str, JsonValue] | None = None,
    metadata: Mapping[str, JsonValue] | None = None,
) -> CompatibilitySnapshot:
    """Build a digestible compatibility snapshot from caller-provided data."""

    return CompatibilitySnapshot(
        version=version,
        public_symbols=tuple(str(item) for item in public_symbols),
        examples=tuple(str(item) for item in examples),
        docs_sections=tuple(str(item) for item in docs_sections),
        config_defaults_digest=_digest(dict(config_defaults or {})),
        metadata_digest=_digest(dict(metadata or {})),
    )



@dataclass(frozen=True, slots=True)
class ActionWiringRecord:
    """Claim-safe public audit row for one action/codon/runtime connection.

    The record is intentionally declarative: it does not claim a behavior is
    useful.  It states whether an action is registered, reachable from a codon
    table, world-effecting by contract, energy-costed, and which blocked
    reasons can appear in trace evidence.
    """

    action_name: str
    action_id: str
    registered: bool
    codon_reachable: bool
    profile_name: str
    world_effecting: bool
    changes_position: bool = False
    changes_inventory: bool = False
    changes_energy: bool = False
    changes_memory: bool = False
    changes_capsule_state: bool = False
    changes_toolchain_state: bool = False
    changes_fitness_component: bool = False
    cost_policy: str = "unknown"
    blocked_reasons: tuple[str, ...] = ()
    claim_relevance: str = "instrumentation"
    codons: tuple[str, ...] = ()
    handler_stable_id: str = ""
    effect_source: str = "contract"
    runtime_validated: bool = False
    runtime_validation_digest: str | None = None
    schema_version: str = "action_wiring_record_v1"

    def __post_init__(self) -> None:
        if not self.action_name or not self.action_id:
            msg = "ActionWiringRecord action_name/action_id must not be empty."
            raise ConfigurationError(msg)
        object.__setattr__(self, "blocked_reasons", tuple(sorted(str(x) for x in self.blocked_reasons)))
        object.__setattr__(self, "codons", tuple(sorted(str(x) for x in self.codons)))
        if self.effect_source not in {"contract", "runtime_smoke", "pilot_trace"}:
            raise ConfigurationError("ActionWiringRecord.effect_source is not recognized.")
        if self.runtime_validated and not self.runtime_validation_digest:
            raise ConfigurationError("runtime_validated action wiring requires runtime_validation_digest.")

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "schema_version": self.schema_version,
            "action_name": self.action_name,
            "action_id": self.action_id,
            "registered": self.registered,
            "codon_reachable": self.codon_reachable,
            "profile_name": self.profile_name,
            "world_effecting": self.world_effecting,
            "changes_position": self.changes_position,
            "changes_inventory": self.changes_inventory,
            "changes_energy": self.changes_energy,
            "changes_memory": self.changes_memory,
            "changes_capsule_state": self.changes_capsule_state,
            "changes_toolchain_state": self.changes_toolchain_state,
            "changes_fitness_component": self.changes_fitness_component,
            "cost_policy": self.cost_policy,
            "blocked_reasons": list(self.blocked_reasons),
            "claim_relevance": self.claim_relevance,
            "codons": list(self.codons),
            "handler_stable_id": self.handler_stable_id,
            "effect_source": self.effect_source,
            "runtime_validated": self.runtime_validated,
            "runtime_validation_digest": self.runtime_validation_digest,
        }

    def digest(self) -> str:
        return _digest(self.to_dict())


@dataclass(frozen=True, slots=True)
class ActionWiringMatrix:
    """Digestible public matrix for action reachability and effect contracts."""

    profile_name: str
    records: tuple[ActionWiringRecord, ...]
    schema_version: str = "action_wiring_matrix_v1"

    def __post_init__(self) -> None:
        if not self.profile_name:
            msg = "ActionWiringMatrix.profile_name must not be empty."
            raise ConfigurationError(msg)
        object.__setattr__(
            self,
            "records",
            tuple(sorted(self.records, key=lambda item: (item.action_name, item.action_id))),
        )

    @property
    def registered_count(self) -> int:
        return sum(1 for item in self.records if item.registered)

    @property
    def codon_reachable_count(self) -> int:
        return sum(1 for item in self.records if item.codon_reachable)

    @property
    def world_effecting_count(self) -> int:
        return sum(1 for item in self.records if item.world_effecting)

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "schema_version": self.schema_version,
            "profile_name": self.profile_name,
            "registered_count": self.registered_count,
            "codon_reachable_count": self.codon_reachable_count,
            "world_effecting_count": self.world_effecting_count,
            "records": [item.to_dict() for item in self.records],
        }

    def digest(self) -> str:
        return _digest(self.to_dict())


def export_action_wiring_matrix(
    *,
    action_registry: object | None = None,
    codon_table: object | None = None,
    profile_name: str = "genesis_default",
) -> ActionWiringMatrix:
    """Return an action/codon/effect audit matrix without private engine hooks.

    The helper uses only public registry/table surfaces: ``names()``, ``get()``,
    and ``actions()``.  It intentionally avoids executing scenarios or mutating
    worlds.  Runtime smoke tests can then verify selected rows with real deltas.
    """

    from codontrace.actions import default_action_registry
    from codontrace.codon import CodonTable

    registry = action_registry or default_action_registry()
    table = codon_table or CodonTable.genesis_toolchain_v0()
    names = tuple(str(name) for name in getattr(registry, "names")())
    codons_by_action: dict[str, list[str]] = {}
    for codon in getattr(table, "actions")():
        action_name = str(getattr(codon, "action_name", getattr(codon, "action", "")))
        codons_by_action.setdefault(action_name, []).append(str(getattr(codon, "bits", "")))
    all_actions = tuple(sorted(set(names) | set(codons_by_action)))
    rows: list[ActionWiringRecord] = []
    for action_name in all_actions:
        handler = getattr(registry, "get")(action_name)
        contract = _action_effect_contract(action_name)
        codons = tuple(codons_by_action.get(action_name, ()))
        handler_stable_id = ""
        if handler is not None:
            handler_stable_id = f"{getattr(handler, '__module__', 'unknown')}:{getattr(handler, '__qualname__', action_name)}"
        rows.append(
            ActionWiringRecord(
                action_name=action_name,
                action_id=action_name.lower(),
                registered=handler is not None,
                codon_reachable=bool(codons),
                profile_name=profile_name,
                codons=codons,
                handler_stable_id=handler_stable_id,
                **contract,
            )
        )
    return ActionWiringMatrix(profile_name=profile_name, records=tuple(rows))


def _action_effect_contract(action_name: str) -> dict[str, Any]:
    action = action_name.upper()
    movement = action.startswith("MOVE_") or action in {"MOVE_TOWARD", "MOVE_AWAY"}
    sensing = action.startswith("SENSE_")
    resource = action in {"COLLECT_RESOURCE", "COLLECT_RESOURCE_OBJECT", "EAT_LUMEN"}
    capsule = action == "EMIT_NEXUS"
    reproduction = action == "COPY_SELF"
    toolchain = action in {
        "COLLECT_WOOD", "COLLECT_STONE", "CRAFT_TOOL", "COLLECT_KEY", "OPEN_DOOR",
        "CROSS_WATER", "COLLECT_FOOD", "RETURN_HOME", "CRAFT_ITEM", "USE_ITEM",
        "UNLOCK_CELL", "CROSS_TERRAIN", "DEPOSIT_RESOURCE", "RETURN_TO_TARGET",
    }
    blocked: tuple[str, ...]
    if movement:
        blocked = ("out_of_bounds", "wall_blocked", "occupied_blocked", "no_food_target", "no_danger_target", "no_open_step_toward_food", "no_open_step_away_from_danger")
    elif resource:
        blocked = ("no_resource", "no_lumen", "missing_resource")
    elif toolchain:
        blocked = ("tool_chain_prerequisite_missing", "missing_resource", "recipe_inputs_missing", "no_item_available", "unlock_item_missing", "terrain_requirement_missing", "target_missing")
    elif reproduction:
        blocked = ("reproduction_not_enabled", "insufficient_runtime_atp", "population_capacity_reached", "no_available_space", "genome_invalid", "parent_cost_too_high", "offspring_fraction_invalid")
    else:
        blocked = () if not sensing else ("sensor_unavailable",)
    return {
        "world_effecting": bool(movement or resource or capsule or toolchain or reproduction),
        "changes_position": bool(movement),
        "changes_inventory": bool(resource or toolchain),
        "changes_energy": bool(resource or toolchain or reproduction),
        "changes_memory": False,
        "changes_capsule_state": bool(capsule),
        "changes_toolchain_state": bool(toolchain),
        "changes_fitness_component": bool(toolchain or resource),
        "cost_policy": "codon_cost_plus_energy_effect" if not sensing else "codon_cost_sensor",
        "blocked_reasons": blocked,
        "claim_relevance": "world_transition" if (movement or resource or toolchain) else ("reproduction_gate" if reproduction else ("capsule_signal" if capsule else "instrumentation")),
        "effect_source": "contract",
        "runtime_validated": False,
        "runtime_validation_digest": None,
    }

def compare_public_api_snapshots(
    old: CompatibilitySnapshot, new: CompatibilitySnapshot
) -> APIAuditResult:
    """Compare two snapshots and return added/removed symbols as reasons."""

    old_symbols = set(old.public_symbols)
    new_symbols = set(new.public_symbols)
    removed = tuple(sorted(old_symbols - new_symbols))
    added = tuple(sorted(new_symbols - old_symbols))
    reasons: list[str] = []
    reasons.extend(f"removed:{name}" for name in removed)
    reasons.extend(f"added:{name}" for name in added)
    return APIAuditResult(
        attempted=True,
        succeeded=not removed,
        public_symbol_count=len(new_symbols),
        missing_from_all=removed,
        undocumented_symbols=added,
        deprecated_symbols=(),
        reasons=tuple(reasons) if reasons else ("snapshots_compatible",),
    )


def compare_compatibility_snapshots(
    old: CompatibilitySnapshot, new: CompatibilitySnapshot
) -> APIAuditResult:
    """Alias for compatibility snapshot comparison."""

    return compare_public_api_snapshots(old, new)


def _symbol_for_name(module: ModuleType, name: str) -> PublicAPISymbol:
    obj = getattr(module, name, None)
    kind = _infer_kind(obj) if obj is not None else "missing"
    object_module = (
        getattr(obj, "__module__", module.__name__) if obj is not None else module.__name__
    )
    qualname = getattr(obj, "__qualname__", name) if obj is not None else name
    return PublicAPISymbol(
        name=name,
        module=module.__name__,
        kind=kind,
        stability=APIStabilityLevel.ALPHA.value,
        added_in="0.3.0a1",
        module_path=str(object_module),
        object_qualname=str(qualname),
    )


def _infer_kind(obj: Any) -> str:
    if inspect.ismodule(obj):
        return "module_alias"
    if inspect.isfunction(obj):
        return "function"
    if inspect.isclass(obj):
        if getattr(obj, "_is_protocol", False):
            return "protocol"
        if is_dataclass(obj):
            return "dataclass"
        if issubclass(obj, Enum):
            return "enum"
        return "class"
    return "constant"


def _digest(payload: Mapping[str, JsonValue]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _mapping(value: object, name: str) -> Mapping[str, JsonValue]:
    if not isinstance(value, Mapping):
        msg = f"{name} must be an object."
        raise ConfigurationError(msg)
    return value


def _str(data: Mapping[str, JsonValue], key: str, default: str | None = None) -> str:
    value = data.get(key, default)
    if not isinstance(value, str):
        msg = f"{key} must be a string."
        raise ConfigurationError(msg)
    return value


def _bool(data: Mapping[str, JsonValue], key: str, default: bool) -> bool:
    value = data.get(key, default)
    if not isinstance(value, bool):
        msg = f"{key} must be a boolean."
        raise ConfigurationError(msg)
    return value


def _int(data: Mapping[str, JsonValue], key: str, default: int) -> int:
    value = data.get(key, default)
    if isinstance(value, bool) or not isinstance(value, int):
        msg = f"{key} must be an integer."
        raise ConfigurationError(msg)
    return value


def _str_tuple(data: Mapping[str, JsonValue], key: str) -> tuple[str, ...]:
    raw = data.get(key, [])
    if not isinstance(raw, list) or not all(isinstance(item, str) for item in raw):
        msg = f"{key} must be a list of strings."
        raise ConfigurationError(msg)
    return tuple(str(item) for item in raw)
