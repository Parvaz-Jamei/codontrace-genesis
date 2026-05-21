"""Public plugin/extension registry for GENESIS research use."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from codontrace._types import JsonValue
from codontrace.errors import PluginError
from codontrace.genesis.canonical import canonical_digest

_EXTENSION_POINTS = {
    "action_primitive", "world_rule", "mutation_operator", "fitness_component",
    "qd_descriptor", "selection_policy", "evidence_artifact",
    "claim_gate_evidence_provider", "benchmark_scenario",
}


@dataclass(frozen=True, slots=True)
class PluginSpec:
    plugin_id: str
    extension_point: str
    version: str
    digest_policy: str = "canonical_json_v1"
    schema_version: str = "plugin_spec_v1"

    def __post_init__(self) -> None:
        if not self.plugin_id:
            raise PluginError("plugin_id must not be empty")
        if self.extension_point not in _EXTENSION_POINTS:
            raise PluginError(f"Unsupported extension point: {self.extension_point}")

    def to_dict(self) -> dict[str, JsonValue]:
        return {"schema_version": self.schema_version, "plugin_id": self.plugin_id, "extension_point": self.extension_point, "version": self.version, "digest_policy": self.digest_policy}

    def digest(self) -> str:
        return canonical_digest(self.to_dict())


class PluginRegistry:
    def __init__(self, plugins: Iterable[PluginSpec] = ()) -> None:
        mapping: dict[tuple[str, str], PluginSpec] = {}
        for plugin in plugins:
            key = (plugin.extension_point, plugin.plugin_id)
            if key in mapping:
                raise PluginError(f"Duplicate plugin registration: {plugin.extension_point}:{plugin.plugin_id}")
            mapping[key] = plugin
        self._plugins = dict(sorted(mapping.items()))

    @classmethod
    def empty(cls) -> "PluginRegistry":
        return cls(())

    def register(self, plugin: PluginSpec) -> "PluginRegistry":
        return PluginRegistry((*self._plugins.values(), plugin))

    def by_extension_point(self, extension_point: str) -> tuple[PluginSpec, ...]:
        if extension_point not in _EXTENSION_POINTS:
            raise PluginError(f"Unsupported extension point: {extension_point}")
        return tuple(plugin for (point, _), plugin in self._plugins.items() if point == extension_point)

    def to_dict(self) -> dict[str, JsonValue]:
        return {"schema_version": "plugin_registry_v1", "plugins": [p.to_dict() for p in self._plugins.values()]}

    def digest(self) -> str:
        return canonical_digest(self.to_dict())

@dataclass(frozen=True, slots=True)
class GenesisPluginSpec:
    plugin_id: str
    extension_point: str
    version: str
    declared_capabilities: tuple[str, ...]
    sandbox_policy: str = "no_private_imports_digest_stable"
    schema_version: str = "genesis_plugin_spec_v1"
    def __post_init__(self) -> None:
        if not self.plugin_id or not self.version or not self.declared_capabilities:
            raise PluginError("GenesisPluginSpec requires id, version, and capabilities")
        if self.extension_point not in _EXTENSION_POINTS:
            raise PluginError(f"Unsupported extension point: {self.extension_point}")
        object.__setattr__(self, "declared_capabilities", tuple(sorted(self.declared_capabilities)))
    def to_dict(self) -> dict[str, JsonValue]:
        return {"schema_version": self.schema_version, "plugin_id": self.plugin_id, "extension_point": self.extension_point, "version": self.version, "declared_capabilities": list(self.declared_capabilities), "sandbox_policy": self.sandbox_policy}
    def digest(self) -> str:
        return canonical_digest(self.to_dict())

@dataclass(frozen=True, slots=True)
class PluginManifest:
    plugin_id: str
    extension_point: str
    version: str
    config_digest: str
    enabled: bool = True
    schema_version: str = "plugin_manifest_v1"

    def __post_init__(self) -> None:
        if not self.plugin_id or not self.version:
            raise PluginError("PluginManifest requires plugin_id/version")
        if self.extension_point not in _EXTENSION_POINTS:
            raise PluginError(f"Unsupported extension point: {self.extension_point}")
        if not self.enabled and not self.config_digest:
            object.__setattr__(self, "config_digest", "disabled_by_config")

    @property
    def status(self) -> str:
        return "enabled" if self.enabled else "disabled_by_config"

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "schema_version": self.schema_version,
            "plugin_id": self.plugin_id,
            "extension_point": self.extension_point,
            "version": self.version,
            "config_digest": self.config_digest,
            "enabled": self.enabled,
            "status": self.status,
        }

    def digest(self) -> str:
        return canonical_digest(self.to_dict())


def _plugin_spec_payload(plugin_id: str, extension_point: str, version: str, declared_capabilities: tuple[str, ...], sandbox_policy: str, schema_version: str) -> dict[str, JsonValue]:
    return {
        "schema_version": schema_version,
        "plugin_id": plugin_id,
        "extension_point": extension_point,
        "version": version,
        "declared_capabilities": list(sorted(declared_capabilities)),
        "sandbox_policy": sandbox_policy,
    }


@dataclass(frozen=True, slots=True)
class ActionPluginSpec:
    plugin_id: str
    version: str
    declared_capabilities: tuple[str, ...]
    sandbox_policy: str = "no_private_imports_digest_stable"
    schema_version: str = "action_plugin_spec_v1"

    def __post_init__(self) -> None:
        if not self.plugin_id or not self.version or not self.declared_capabilities:
            raise PluginError("ActionPluginSpec requires id, version, and capabilities")
        object.__setattr__(self, "declared_capabilities", tuple(sorted(self.declared_capabilities)))

    @property
    def extension_point(self) -> str:
        return "action_primitive"

    def to_dict(self) -> dict[str, JsonValue]:
        return _plugin_spec_payload(self.plugin_id, self.extension_point, self.version, self.declared_capabilities, self.sandbox_policy, self.schema_version)

    def digest(self) -> str:
        return canonical_digest(self.to_dict())


@dataclass(frozen=True, slots=True)
class WorldPluginSpec(ActionPluginSpec):
    schema_version: str = "world_plugin_spec_v1"

    @property
    def extension_point(self) -> str:
        return "world_rule"


@dataclass(frozen=True, slots=True)
class FitnessPluginSpec(ActionPluginSpec):
    schema_version: str = "fitness_plugin_spec_v1"

    @property
    def extension_point(self) -> str:
        return "fitness_component"


@dataclass(frozen=True, slots=True)
class MutationPluginSpec(ActionPluginSpec):
    schema_version: str = "mutation_plugin_spec_v1"

    @property
    def extension_point(self) -> str:
        return "mutation_operator"


@dataclass(frozen=True, slots=True)
class PolicyPluginSpec(ActionPluginSpec):
    schema_version: str = "policy_plugin_spec_v1"

    @property
    def extension_point(self) -> str:
        return "selection_policy"


# Backward-compatible short names keep the old public API while no longer being
# collapsed aliases for the release-facing *Spec classes above.
ActionPlugin = ActionPluginSpec
WorldPlugin = WorldPluginSpec
FitnessPlugin = FitnessPluginSpec
MutationPlugin = MutationPluginSpec
SelectionPolicyPlugin = PolicyPluginSpec
PluginSandboxPolicy = PluginManifest


@dataclass(frozen=True, slots=True)
class PluginValidationResult:
    plugin_digest: str
    passed: bool
    reasons: tuple[str, ...]
    status: str = "measured"
    schema_version: str = "plugin_validation_result_v1"

    def __post_init__(self) -> None:
        if not self.plugin_digest and self.passed:
            object.__setattr__(self, "passed", False)
            object.__setattr__(self, "status", "rejected")
        if self.status not in {"measured", "rejected", "disabled_by_config"}:
            raise PluginError("PluginValidationResult status is invalid")

    def to_dict(self) -> dict[str, JsonValue]:
        return {"schema_version": self.schema_version, "plugin_digest": self.plugin_digest, "passed": self.passed, "reasons": list(self.reasons), "status": self.status}

    def digest(self) -> str:
        return canonical_digest(self.to_dict())


@dataclass(frozen=True, slots=True)
class PluginValidationReport:
    plugin_digest: str
    passed: bool
    reasons: tuple[str, ...]
    schema_version: str = "plugin_validation_report_v1"
    def to_dict(self) -> dict[str, JsonValue]:
        return {"schema_version": self.schema_version, "plugin_digest": self.plugin_digest, "passed": self.passed, "reasons": list(self.reasons)}
    def digest(self) -> str:
        return canonical_digest(self.to_dict())
