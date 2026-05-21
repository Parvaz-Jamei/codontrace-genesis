"""Deterministic role-specialization records for GENESIS runtime evidence."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass
from enum import Enum

from codontrace._types import JsonValue


class RoleProfile(str, Enum):
    FORAGER = "forager"
    EXPLORER = "explorer"
    HAZARD_AVOIDER = "hazard_avoider"
    CAPSULE_EMITTER = "capsule_emitter"
    CAPSULE_READER = "capsule_reader"
    REPRODUCER = "reproducer"
    TOOL_BUILDER = "tool_builder"
    HOME_GUARD = "home_guard"
    COOPERATOR = "cooperator"
    FREE_RIDER = "free_rider"
    UNKNOWN = "unknown"


def _json_int(value: JsonValue | None, default: int = 0) -> int:
    return int(value) if isinstance(value, int) and not isinstance(value, bool) else default


def _json_float(value: JsonValue | None, default: float = 0.0) -> float:
    return (
        float(value) if isinstance(value, (int, float)) and not isinstance(value, bool) else default
    )


@dataclass(frozen=True, slots=True)
class RoleAssignment:
    organism_id: str
    tick: int
    role: RoleProfile | str = RoleProfile.UNKNOWN
    role_confidence: float = 0.0
    action_distribution_digest: str = ""
    codon_usage_signature: str = ""
    role_switch_count: int = 0
    role_persistence: float = 0.0
    contribution_to_group_score: float = 0.0
    schema_version: str = "role_assignment_v1"

    def __post_init__(self) -> None:
        object.__setattr__(self, "role", _role(self.role))

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "schema_version": self.schema_version,
            "organism_id": self.organism_id,
            "tick": self.tick,
            "role": _role(self.role).value,
            "role_confidence": self.role_confidence,
            "action_distribution_digest": self.action_distribution_digest,
            "codon_usage_signature": self.codon_usage_signature,
            "role_switch_count": self.role_switch_count,
            "role_persistence": self.role_persistence,
            "contribution_to_group_score": self.contribution_to_group_score,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, JsonValue]) -> RoleAssignment:
        return cls(
            organism_id=str(data.get("organism_id", "")),
            tick=_json_int(data.get("tick")),
            role=str(data.get("role", RoleProfile.UNKNOWN.value)),
            role_confidence=_json_float(data.get("role_confidence")),
            action_distribution_digest=str(data.get("action_distribution_digest", "")),
            codon_usage_signature=str(data.get("codon_usage_signature", "")),
            role_switch_count=_json_int(data.get("role_switch_count")),
            role_persistence=_json_float(data.get("role_persistence")),
            contribution_to_group_score=_json_float(data.get("contribution_to_group_score")),
        )

    def digest(self) -> str:
        return _digest(self.to_dict())


@dataclass(frozen=True, slots=True)
class RoleTimeline:
    organism_id: str
    assignments: tuple[RoleAssignment, ...]
    schema_version: str = "role_timeline_v1"

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "schema_version": self.schema_version,
            "organism_id": self.organism_id,
            "assignments": [item.to_dict() for item in self.assignments],
        }

    def digest(self) -> str:
        return _digest(self.to_dict())


@dataclass(frozen=True, slots=True)
class RoleContribution:
    organism_id: str
    role: RoleProfile | str
    contribution_to_group_score: float = 0.0
    role_persistence: float = 0.0
    evidence_digest: str = ""
    schema_version: str = "role_contribution_v1"

    def __post_init__(self) -> None:
        object.__setattr__(self, "role", _role(self.role))

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "schema_version": self.schema_version,
            "organism_id": self.organism_id,
            "role": _role(self.role).value,
            "contribution_to_group_score": self.contribution_to_group_score,
            "role_persistence": self.role_persistence,
            "evidence_digest": self.evidence_digest,
        }

    def digest(self) -> str:
        return _digest(self.to_dict())


def infer_role_from_record(record: object, tick: int) -> RoleAssignment:
    descriptor = getattr(record, "behavior_descriptor", None)
    role = getattr(descriptor, "role_signature", "unknown") if descriptor is not None else "unknown"
    social_events = tuple(getattr(record, "social_interaction_records", ()) or ())
    tool_stage = (
        int(getattr(descriptor, "tool_chain_stage", 0) or 0) if descriptor is not None else 0
    )
    if tool_stage >= 3:
        role = RoleProfile.TOOL_BUILDER.value
    elif any(
        getattr(event, "interaction_type", "") == "cooperative_task_progress"
        for event in social_events
    ):
        role = RoleProfile.COOPERATOR.value
    elif any(getattr(event, "interaction_type", "") == "free_riding" for event in social_events):
        role = RoleProfile.FREE_RIDER.value
    if role not in {item.value for item in RoleProfile}:
        role = "unknown"
    evidence_count = (
        float(getattr(record, "capsule_adoption_successes", 0))
        + float(getattr(record, "capsule_emit_count", 0))
        + float(len(social_events))
        + float(tool_stage)
    )
    confidence = 0.0 if role == "unknown" else min(1.0, 0.45 + evidence_count * 0.05)
    persistence = (
        0.0
        if role == "unknown"
        else min(
            1.0,
            0.5
            + float(getattr(descriptor, "survival_ticks", 0) if descriptor is not None else 0)
            * 0.1,
        )
    )
    return RoleAssignment(
        organism_id=str(getattr(record, "organism_id", "")),
        tick=tick,
        role=role,
        role_confidence=round(confidence, 10),
        action_distribution_digest=str(getattr(record, "trace_digest", "")),
        codon_usage_signature=str(getattr(descriptor, "digest", lambda: "")())
        if descriptor is not None
        else "",
        role_switch_count=0,
        role_persistence=round(persistence, 10),
        contribution_to_group_score=round(evidence_count, 10),
    )


def _role(value: RoleProfile | str) -> RoleProfile:
    if isinstance(value, RoleProfile):
        return value
    try:
        return RoleProfile(str(value))
    except ValueError:
        return RoleProfile.UNKNOWN


def _digest(payload: Mapping[str, JsonValue]) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()

# ---------------------------------------------------------------------------
# Runtime role mechanics and territory primitives (P1)
# ---------------------------------------------------------------------------
from codontrace.genesis.canonical import canonical_digest as _role_canonical_digest, require_finite_float as _role_require_finite_float


@dataclass(frozen=True, slots=True)
class RoleMechanicsPolicy:
    """Soft role-bias policy derived from behavior, not scenario labels."""

    enable_role_bias: bool = True
    enable_role_persistence: bool = True
    enable_role_switch_cost: bool = True
    enable_role_task_bonus: bool = False
    role_inheritance_mode: str = "weak_bias"
    max_bias_strength: float = 0.25
    schema_version: str = "role_mechanics_policy_v1"

    def __post_init__(self) -> None:
        if self.role_inheritance_mode not in {"none", "weak_bias", "lineage_prior"}:
            raise ValueError("role_inheritance_mode must be none, weak_bias, or lineage_prior")
        object.__setattr__(self, "max_bias_strength", _role_require_finite_float("max_bias_strength", self.max_bias_strength, non_negative=True))
        if self.max_bias_strength > 1.0:
            raise ValueError("max_bias_strength must be <= 1.0")

    @property
    def hard_codes_success(self) -> bool:
        return bool(self.enable_role_task_bonus)

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "schema_version": self.schema_version,
            "enable_role_bias": self.enable_role_bias,
            "enable_role_persistence": self.enable_role_persistence,
            "enable_role_switch_cost": self.enable_role_switch_cost,
            "enable_role_task_bonus": self.enable_role_task_bonus,
            "role_inheritance_mode": self.role_inheritance_mode,
            "max_bias_strength": self.max_bias_strength,
            "hard_codes_success": self.hard_codes_success,
        }

    def digest(self) -> str:
        return _role_canonical_digest(self.to_dict(), prefix="role_mechanics")


@dataclass(frozen=True, slots=True)
class TerritoryMechanicsConfig:
    """Optional substrate extension for home-base/territory evidence."""

    enabled: bool = False
    home_cells: tuple[str, ...] = ()
    defendable_resources: bool = True
    hazard_pressure: bool = True
    intrusion_events: bool = True
    schema_version: str = "territory_mechanics_config_v1"

    def __post_init__(self) -> None:
        object.__setattr__(self, "home_cells", tuple(sorted(str(cell) for cell in self.home_cells)))
        if self.enabled and not self.home_cells:
            raise ValueError("enabled territory mechanics require at least one home cell")

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "schema_version": self.schema_version,
            "enabled": self.enabled,
            "home_cells": list(self.home_cells),
            "defendable_resources": self.defendable_resources,
            "hazard_pressure": self.hazard_pressure,
            "intrusion_events": self.intrusion_events,
        }

    def digest(self) -> str:
        return _role_canonical_digest(self.to_dict(), prefix="territory_mechanics")


@dataclass(frozen=True, slots=True)
class TerritoryDefenseRecord:
    organism_id: str
    role_label: str
    tick: int
    home_cell: str
    hazard_blocked: bool = False
    resource_defended: bool = False
    intrusion_response: bool = False
    group_loss_delta_without_guard: float = 0.0
    evidence_digest: str | None = None
    schema_version: str = "territory_defense_record_v1"
    record_digest: str = ""

    def __post_init__(self) -> None:
        if not self.organism_id or not self.home_cell:
            raise ValueError("organism_id and home_cell are required")
        if self.tick < 0:
            raise ValueError("tick must be non-negative")
        object.__setattr__(self, "group_loss_delta_without_guard", round(_role_require_finite_float("group_loss_delta_without_guard", self.group_loss_delta_without_guard), 10))
        if not self.record_digest:
            object.__setattr__(self, "record_digest", _role_canonical_digest(self._payload(), prefix="territory_defense"))

    @property
    def claim_eligible(self) -> bool:
        return bool(self.evidence_digest) and (self.hazard_blocked or self.resource_defended or self.intrusion_response) and self.group_loss_delta_without_guard > 0.0

    def _payload(self) -> dict[str, JsonValue]:
        return {
            "schema_version": self.schema_version,
            "organism_id": self.organism_id,
            "role_label": self.role_label,
            "tick": self.tick,
            "home_cell": self.home_cell,
            "hazard_blocked": self.hazard_blocked,
            "resource_defended": self.resource_defended,
            "intrusion_response": self.intrusion_response,
            "group_loss_delta_without_guard": self.group_loss_delta_without_guard,
            "evidence_digest": self.evidence_digest,
            "claim_eligible": self.claim_eligible,
        }

    def to_dict(self) -> dict[str, JsonValue]:
        return {**self._payload(), "record_digest": self.record_digest}

    def digest(self) -> str:
        return self.record_digest
