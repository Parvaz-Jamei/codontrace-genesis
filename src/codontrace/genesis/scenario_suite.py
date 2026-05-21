"""Object-only validation scenario-suite records for GENESIS.

No experiment execution, file output, dashboards, reports, or random generation are
performed here. Callers provide scenarios and seeds explicitly.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass, field

from codontrace._types import JsonValue
from codontrace.errors import ConfigurationError
from codontrace.genesis.research_validation import ValidationScenario


@dataclass(frozen=True, slots=True)
class ScenarioComponentRequirement:
    component_name: str
    required: bool = True
    minimum_version: str = ""
    evidence_required: tuple[str, ...] = ()
    notes: str = ""

    def __post_init__(self) -> None:
        if not self.component_name:
            raise ConfigurationError(
                "ScenarioComponentRequirement.component_name must not be empty."
            )

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "component_name": self.component_name,
            "required": self.required,
            "minimum_version": self.minimum_version,
            "evidence_required": list(self.evidence_required),
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, JsonValue]) -> ScenarioComponentRequirement:
        return cls(
            _str(data, "component_name"),
            _bool(data, "required", True),
            _str(data, "minimum_version", ""),
            _str_tuple(data, "evidence_required"),
            _str(data, "notes", ""),
        )

    def digest(self) -> str:
        return _digest(self.to_dict())


@dataclass(frozen=True, slots=True)
class SeedMatrix:
    seeds: tuple[int, ...]
    min_seeds: int
    unique_required: bool = True

    def __post_init__(self) -> None:
        if isinstance(self.min_seeds, bool) or self.min_seeds <= 0:
            raise ConfigurationError("SeedMatrix.min_seeds must be a positive integer.")
        if any(isinstance(seed, bool) or not isinstance(seed, int) for seed in self.seeds):
            raise ConfigurationError("SeedMatrix.seeds must contain integers only.")

    @property
    def duplicate_seeds(self) -> tuple[int, ...]:
        return tuple(sorted({seed for seed in self.seeds if self.seeds.count(seed) > 1}))

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "seeds": list(self.seeds),
            "min_seeds": self.min_seeds,
            "unique_required": self.unique_required,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, JsonValue]) -> SeedMatrix:
        return cls(
            _int_tuple(data, "seeds"),
            _int(data, "min_seeds", 1),
            _bool(data, "unique_required", True),
        )

    def digest(self) -> str:
        return _digest(self.to_dict())


@dataclass(frozen=True, slots=True)
class ComponentToggle:
    component_name: str
    enabled: bool
    reason: str = ""
    expected_effect: str = ""
    metadata: dict[str, JsonValue] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.component_name:
            raise ConfigurationError("ComponentToggle.component_name must not be empty.")
        object.__setattr__(self, "metadata", dict(self.metadata))

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "component_name": self.component_name,
            "enabled": self.enabled,
            "reason": self.reason,
            "expected_effect": self.expected_effect,
            "metadata": dict(sorted(self.metadata.items())),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, JsonValue]) -> ComponentToggle:
        return cls(
            _str(data, "component_name"),
            _bool(data, "enabled", True),
            _str(data, "reason", ""),
            _str(data, "expected_effect", ""),
            _mapping_to_dict(data.get("metadata", {}), "metadata"),
        )

    def digest(self) -> str:
        return _digest(self.to_dict())


@dataclass(frozen=True, slots=True)
class ComponentToggleMatrix:
    toggles: tuple[ComponentToggle, ...] = ()

    def to_dict(self) -> dict[str, JsonValue]:
        return {"toggles": [item.to_dict() for item in self.toggles]}

    @classmethod
    def from_dict(cls, data: Mapping[str, JsonValue]) -> ComponentToggleMatrix:
        raw = data.get("toggles", [])
        if not isinstance(raw, list):
            raise ConfigurationError("ComponentToggleMatrix.toggles must be a list.")
        return cls(tuple(ComponentToggle.from_dict(_mapping(item, "toggle")) for item in raw))

    def digest(self) -> str:
        return _digest(self.to_dict())


@dataclass(frozen=True, slots=True)
class ScenarioSuite:
    suite_id: str
    description: str
    scenarios: tuple[ValidationScenario, ...]
    seed_matrix: SeedMatrix
    component_matrix: ComponentToggleMatrix = field(default_factory=ComponentToggleMatrix)
    required_evidence: tuple[str, ...] = ()
    limitations: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.suite_id:
            raise ConfigurationError("ScenarioSuite.suite_id must not be empty.")
        if not self.limitations:
            raise ConfigurationError("ScenarioSuite.limitations must list non-claims/limitations.")

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "suite_id": self.suite_id,
            "description": self.description,
            "scenarios": [item.to_dict() for item in self.scenarios],
            "seed_matrix": self.seed_matrix.to_dict(),
            "component_matrix": self.component_matrix.to_dict(),
            "required_evidence": list(self.required_evidence),
            "limitations": list(self.limitations),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, JsonValue]) -> ScenarioSuite:
        raw_scenarios = data.get("scenarios", [])
        if not isinstance(raw_scenarios, list):
            raise ConfigurationError("ScenarioSuite.scenarios must be a list.")
        return cls(
            _str(data, "suite_id"),
            _str(data, "description", ""),
            tuple(
                ValidationScenario.from_dict(_mapping(item, "scenario")) for item in raw_scenarios
            ),
            SeedMatrix.from_dict(_mapping(data.get("seed_matrix", {}), "seed_matrix")),
            ComponentToggleMatrix.from_dict(
                _mapping(data.get("component_matrix", {"toggles": []}), "component_matrix")
            ),
            _str_tuple(data, "required_evidence"),
            _str_tuple(data, "limitations"),
        )

    def digest(self) -> str:
        return _digest(self.to_dict())


@dataclass(frozen=True, slots=True)
class ScenarioSuiteValidationResult:
    attempted: bool
    succeeded: bool
    scenario_count: int
    seed_count: int
    unique_seed_count: int = 0
    duplicate_seed_count: int = 0
    missing_evidence: tuple[str, ...] = ()
    duplicate_seeds: tuple[int, ...] = ()
    reasons: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "attempted": self.attempted,
            "succeeded": self.succeeded,
            "scenario_count": self.scenario_count,
            "seed_count": self.seed_count,
            "unique_seed_count": self.unique_seed_count,
            "duplicate_seed_count": self.duplicate_seed_count,
            "missing_evidence": list(self.missing_evidence),
            "duplicate_seeds": list(self.duplicate_seeds),
            "reasons": list(self.reasons),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, JsonValue]) -> ScenarioSuiteValidationResult:
        return cls(
            _bool(data, "attempted", False),
            _bool(data, "succeeded", False),
            _int(data, "scenario_count", 0),
            _int(data, "seed_count", 0),
            _int(data, "unique_seed_count", 0),
            _int(data, "duplicate_seed_count", 0),
            _str_tuple(data, "missing_evidence"),
            _int_tuple(data, "duplicate_seeds"),
            _str_tuple(data, "reasons"),
        )

    def digest(self) -> str:
        return _digest(self.to_dict())


def validate_scenario_suite(suite: ScenarioSuite) -> ScenarioSuiteValidationResult:
    missing: list[str] = []
    for scenario in suite.scenarios:
        for evidence in suite.required_evidence:
            if evidence not in scenario.expected_evidence:
                missing.append(f"{scenario.scenario_id}:{evidence}")
    duplicate = suite.seed_matrix.duplicate_seeds if suite.seed_matrix.unique_required else ()
    reasons: list[str] = []
    if len(set(suite.seed_matrix.seeds)) < suite.seed_matrix.min_seeds:
        reasons.append("insufficient_unique_seeds")
    if duplicate:
        reasons.append("duplicate_seeds")
    if missing:
        reasons.append("missing_evidence")
    if not suite.limitations:
        reasons.append("missing_limitations")
    return ScenarioSuiteValidationResult(
        True,
        not reasons,
        len(suite.scenarios),
        len(suite.seed_matrix.seeds),
        len(set(suite.seed_matrix.seeds)),
        sum(1 for seed in set(suite.seed_matrix.seeds) if suite.seed_matrix.seeds.count(seed) > 1),
        tuple(sorted(missing)),
        duplicate,
        tuple(reasons) if reasons else ("scenario_suite_validated",),
    )


def _digest(payload: Mapping[str, JsonValue]) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def _mapping(value: object, name: str) -> Mapping[str, JsonValue]:
    if not isinstance(value, Mapping):
        raise ConfigurationError(f"{name} must be an object.")
    return value


def _mapping_to_dict(value: object, name: str) -> dict[str, JsonValue]:
    if not isinstance(value, Mapping):
        raise ConfigurationError(f"{name} must be an object.")
    return dict(value)


def _str(data: Mapping[str, JsonValue], key: str, default: str | None = None) -> str:
    value = data.get(key, default)
    if not isinstance(value, str):
        raise ConfigurationError(f"{key} must be a string.")
    return value


def _bool(data: Mapping[str, JsonValue], key: str, default: bool) -> bool:
    value = data.get(key, default)
    if not isinstance(value, bool):
        raise ConfigurationError(f"{key} must be a boolean.")
    return value


def _int(data: Mapping[str, JsonValue], key: str, default: int) -> int:
    value = data.get(key, default)
    if isinstance(value, bool) or not isinstance(value, int):
        raise ConfigurationError(f"{key} must be an integer.")
    return value


def _str_tuple(data: Mapping[str, JsonValue], key: str) -> tuple[str, ...]:
    raw = data.get(key, [])
    if not isinstance(raw, list) or not all(isinstance(item, str) for item in raw):
        raise ConfigurationError(f"{key} must be a list of strings.")
    return tuple(str(item) for item in raw)


def _int_tuple(data: Mapping[str, JsonValue], key: str) -> tuple[int, ...]:
    raw = data.get(key, [])
    if not isinstance(raw, list):
        raise ConfigurationError(f"{key} must be a list of integers.")
    checked: list[int] = []
    for item in raw:
        if isinstance(item, bool) or not isinstance(item, int):
            raise ConfigurationError(f"{key} must be a list of integers.")
        checked.append(item)
    return tuple(checked)
