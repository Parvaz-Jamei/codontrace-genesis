"""Deterministic diagnostic records for library-as-tool GENESIS runs.

These value objects intentionally do not make success claims. They expose costs,
rewards, blocked reasons, reproduction gates, baseline comparisons, and digest
stability so runners can build scientific protocols without reading private
engine internals.
"""

from __future__ import annotations

import csv
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from codontrace._types import JsonValue, Position
from codontrace.errors import ConfigurationError


def _digest(payload: dict[str, JsonValue]) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


FeatureStatus = Literal[
    "measured",
    "empty_but_available",
    "unavailable",
    "disabled_by_config",
    "not_applicable",
    "provisional",
]

_FEATURE_STATUSES = {
    "measured",
    "empty_but_available",
    "unavailable",
    "disabled_by_config",
    "not_applicable",
    "provisional",
}
_DEATH_ATTRIBUTION_LEVELS = {
    "none",
    "alive_gate_warning",
    "policy_fatal",
    "event_level",
    "generation_level",
    "not_applicable",
}


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _non_negative(value: int | float, field_name: str) -> None:
    if value < 0:
        raise ValueError(f"{field_name} must be non-negative.")


@dataclass(frozen=True, slots=True)
class ExportEnvelope:
    """Schema wrapper for empty/non-empty public exports."""

    schema_version: str
    feature_status: FeatureStatus
    status_reason: str
    records: tuple[JsonValue, ...] = ()

    def __post_init__(self) -> None:
        _require(bool(self.schema_version), "schema_version is required.")
        _require(self.feature_status in _FEATURE_STATUSES, "invalid feature_status.")
        _require(bool(self.status_reason), "status_reason is required.")
        if self.feature_status == "measured":
            _require(bool(self.records), "measured export envelopes require records.")

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "schema_version": self.schema_version,
            "feature_status": self.feature_status,
            "status_reason": self.status_reason,
            "records": list(self.records),
        }

    def digest(self) -> str:
        return _digest(self.to_dict())


@dataclass(frozen=True, slots=True)
class EnergyAccountingRecord:
    organism_id: str
    tick: int
    action: str
    runtime_atp_before: float
    runtime_atp_after: float
    learning_atp_before: float | None = None
    learning_atp_after: float | None = None
    action_cost: float = 0.0
    action_reward: float = 0.0
    blocked: bool = False
    blocked_reason: str | None = None
    death_event: bool = False
    death_reason: str | None = None
    fitness_delta: float | None = None
    fitness_delta_status: str = "not_measured"
    fitness_delta_source: str | None = None
    energy_delta: float = 0.0
    organism_dead_after_generation: bool = False
    death_causing_event: bool = False
    death_attribution_level: str = "not_applicable"
    actual_death_removed_from_population: bool = False
    alive_gate_failed_after_generation: bool = False
    death_risk_after_generation: bool = False
    selected_out_by_evolution: bool = False
    death_policy_digest: str | None = None
    engine_tick: int | None = None
    population_tick: int | None = None
    event_step: int | None = None
    schema_version: str = "energy_accounting_record_v4"

    def __post_init__(self) -> None:
        _require(bool(self.organism_id), "organism_id is required.")
        _require(bool(self.action), "action is required.")
        _non_negative(self.tick, "tick")
        if self.engine_tick is not None:
            _non_negative(self.engine_tick, "engine_tick")
        if self.population_tick is not None:
            _non_negative(self.population_tick, "population_tick")
        if self.event_step is not None:
            _non_negative(self.event_step, "event_step")
        _non_negative(self.action_cost, "action_cost")
        _non_negative(self.action_reward, "action_reward")
        if not self.blocked:
            _require(self.blocked_reason is None, "unblocked records must not carry blocked_reason.")
        if self.blocked:
            _require(self.blocked_reason is not None, "blocked records require blocked_reason.")
        if self.fitness_delta_status not in {"measured", "not_measured", "not_applicable"}:
            raise ValueError("invalid fitness_delta_status.")
        if self.fitness_delta_status == "measured":
            _require(self.fitness_delta is not None, "measured fitness_delta requires a value.")
            _require(self.fitness_delta_source is not None, "measured fitness_delta requires source.")
        else:
            _require(self.fitness_delta is None, "unmeasured fitness_delta must be None.")
        if self.death_causing_event:
            _require(
                self.actual_death_removed_from_population,
                "death_causing_event requires actual_death_removed_from_population=True.",
            )
        if self.death_risk_after_generation:
            _require(
                self.alive_gate_failed_after_generation,
                "death_risk_after_generation requires alive_gate_failed_after_generation=True.",
            )
            _require(
                not self.actual_death_removed_from_population,
                "death_risk_after_generation is non-fatal and must not coincide with actual death.",
            )
        if self.actual_death_removed_from_population:
            _require(self.death_policy_digest is not None, "actual death requires death_policy_digest.")
            _require(self.death_reason is not None, "actual death requires death_reason.")
        if self.death_event:
            _require(
                self.actual_death_removed_from_population,
                "death_event is an alias of actual_death_removed_from_population.",
            )
        if self.organism_dead_after_generation:
            _require(
                self.actual_death_removed_from_population,
                "organism_dead_after_generation means actual removal from population.",
            )
        _require(
            self.death_attribution_level in _DEATH_ATTRIBUTION_LEVELS,
            "invalid death_attribution_level.",
        )

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "schema_version": self.schema_version,
            "organism_id": self.organism_id,
            "tick": self.tick,
            "action": self.action,
            "runtime_atp_before": self.runtime_atp_before,
            "runtime_atp_after": self.runtime_atp_after,
            "learning_atp_before": self.learning_atp_before,
            "learning_atp_after": self.learning_atp_after,
            "action_cost": self.action_cost,
            "action_reward": self.action_reward,
            "blocked": self.blocked,
            "blocked_reason": self.blocked_reason,
            "death_event": self.death_event,
            "death_reason": self.death_reason,
            "fitness_delta": self.fitness_delta,
            "fitness_delta_status": self.fitness_delta_status,
            "fitness_delta_source": self.fitness_delta_source,
            "energy_delta": self.energy_delta,
            "organism_dead_after_generation": self.organism_dead_after_generation,
            "death_causing_event": self.death_causing_event,
            "death_attribution_level": self.death_attribution_level,
            "actual_death_removed_from_population": self.actual_death_removed_from_population,
            "alive_gate_failed_after_generation": self.alive_gate_failed_after_generation,
            "death_risk_after_generation": self.death_risk_after_generation,
            "selected_out_by_evolution": self.selected_out_by_evolution,
            "death_policy_digest": self.death_policy_digest,
            "engine_tick": self.engine_tick if self.engine_tick is not None else self.tick,
            "population_tick": self.population_tick,
            "event_step": self.event_step,
        }

    def digest(self) -> str:
        return _digest(self.to_dict())


@dataclass(frozen=True, slots=True)
class ActionCostRecord:
    organism_id: str
    tick: int
    action: str
    action_cost: float
    blocked: bool
    blocked_reason: str | None = None
    schema_version: str = "action_cost_record_v1"

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "schema_version": self.schema_version,
            "organism_id": self.organism_id,
            "tick": self.tick,
            "action": self.action,
            "action_cost": self.action_cost,
            "blocked": self.blocked,
            "blocked_reason": self.blocked_reason,
        }

    def digest(self) -> str:
        return _digest(self.to_dict())


@dataclass(frozen=True, slots=True)
class ActionRewardRecord:
    organism_id: str
    tick: int
    action: str
    action_reward: float
    reward_reason: str | None = None
    schema_version: str = "action_reward_record_v1"

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "schema_version": self.schema_version,
            "organism_id": self.organism_id,
            "tick": self.tick,
            "action": self.action,
            "action_reward": self.action_reward,
            "reward_reason": self.reward_reason,
        }

    def digest(self) -> str:
        return _digest(self.to_dict())


@dataclass(frozen=True, slots=True)
class DeathReasonRecord:
    organism_id: str
    tick: int
    death_event: bool
    death_reason: str
    alive_gate_reasons: tuple[str, ...] = ()
    runtime_atp_after: float = 0.0
    blocked_actions: int = 0
    actual_death_removed_from_population: bool = False
    alive_gate_failure_event: bool = False
    death_risk_event: bool = False
    death_causing_event: bool = False
    death_attribution_level: str = "none"
    runtime_atp_before: float | None = None
    fatal_policy_matched: bool = False
    fatal_policy_reason: str | None = None
    death_policy_digest: str = ""
    engine_tick: int | None = None
    population_tick: int | None = None
    event_step: int | None = None
    schema_version: str = "death_reason_record_v3"

    def __post_init__(self) -> None:
        _require(bool(self.organism_id), "organism_id is required.")
        _non_negative(self.tick, "tick")
        if self.engine_tick is not None:
            _non_negative(self.engine_tick, "engine_tick")
        if self.population_tick is not None:
            _non_negative(self.population_tick, "population_tick")
        if self.event_step is not None:
            _non_negative(self.event_step, "event_step")
        _non_negative(self.blocked_actions, "blocked_actions")
        _require(
            self.death_event == self.actual_death_removed_from_population,
            "death_event must equal actual_death_removed_from_population.",
        )
        if self.actual_death_removed_from_population:
            _require(self.death_reason != "not_applicable", "actual death requires a death_reason.")
            _require(self.fatal_policy_matched, "actual death requires fatal_policy_matched=True.")
            _require(self.fatal_policy_reason is not None, "actual death requires fatal_policy_reason.")
        else:
            _require(
                self.death_reason in {
                    "not_applicable",
                    "alive_gate_failure_nonfatal",
                    "capacity_block_nonfatal",
                    "death_risk_nonfatal",
                },
                "non-death records must use not_applicable or a risk-only reason.",
            )
        if self.death_causing_event:
            _require(self.actual_death_removed_from_population, "death_causing_event requires actual death.")
        if self.death_risk_event:
            _require(self.alive_gate_failure_event, "death_risk_event requires alive_gate_failure_event.")
            _require(not self.actual_death_removed_from_population, "death risk is non-fatal.")
        _require(bool(self.death_policy_digest), "death_policy_digest is required.")
        _require(self.death_attribution_level in _DEATH_ATTRIBUTION_LEVELS, "invalid death_attribution_level.")

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "schema_version": self.schema_version,
            "organism_id": self.organism_id,
            "tick": self.tick,
            "death_event": self.death_event,
            "death_reason": self.death_reason,
            "alive_gate_reasons": list(self.alive_gate_reasons),
            "runtime_atp_before": self.runtime_atp_before,
            "runtime_atp_after": self.runtime_atp_after,
            "blocked_actions": self.blocked_actions,
            "actual_death_removed_from_population": self.actual_death_removed_from_population,
            "alive_gate_failure_event": self.alive_gate_failure_event,
            "death_risk_event": self.death_risk_event,
            "death_causing_event": self.death_causing_event,
            "death_attribution_level": self.death_attribution_level,
            "fatal_policy_matched": self.fatal_policy_matched,
            "fatal_policy_reason": self.fatal_policy_reason,
            "death_policy_digest": self.death_policy_digest,
            "engine_tick": self.engine_tick if self.engine_tick is not None else self.tick,
            "population_tick": self.population_tick,
            "event_step": self.event_step,
        }

    def digest(self) -> str:
        return _digest(self.to_dict())


@dataclass(frozen=True, slots=True)
class SurvivalBaselineRecord:
    baseline_type: str
    tick: int
    survived_ticks: int
    final_runtime_atp: float
    action_cost_total: float
    explanation: str
    schema_version: str = "survival_baseline_record_v1"

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "schema_version": self.schema_version,
            "baseline_type": self.baseline_type,
            "tick": self.tick,
            "survived_ticks": self.survived_ticks,
            "final_runtime_atp": self.final_runtime_atp,
            "action_cost_total": self.action_cost_total,
            "explanation": self.explanation,
        }

    def digest(self) -> str:
        return _digest(self.to_dict())


@dataclass(frozen=True, slots=True)
class BaselineComparisonRecord:
    baseline_type: str
    survival_advantage: float
    energy_advantage: float
    action_cost_advantage: float
    task_score_advantage: float
    explanation: str
    schema_version: str = "baseline_comparison_record_v1"

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "schema_version": self.schema_version,
            "baseline_type": self.baseline_type,
            "survival_advantage": self.survival_advantage,
            "energy_advantage": self.energy_advantage,
            "action_cost_advantage": self.action_cost_advantage,
            "task_score_advantage": self.task_score_advantage,
            "explanation": self.explanation,
        }

    def digest(self) -> str:
        return _digest(self.to_dict())


@dataclass(frozen=True, slots=True)
class ReproductionAttemptRecord:
    organism_id: str
    tick: int
    reproduction_action_attempted: bool
    reproduction_allowed: bool
    blocked_reason: str
    runtime_atp: float
    min_runtime_atp_required: float | None = None
    parent_atp_cost: float | None = None
    offspring_atp_fraction: float | None = None
    available_space: bool | None = None
    population_capacity: int | None = None
    mutation_applied: bool = False
    child_created: bool = False
    child_id: str | None = None
    lineage_id: str | None = None
    schema_version: str = "reproduction_attempt_record_v1"

    def __post_init__(self) -> None:
        _require(bool(self.organism_id), "organism_id is required.")
        _non_negative(self.tick, "tick")
        _non_negative(self.runtime_atp, "runtime_atp")
        if self.child_created:
            _require(self.child_id is not None, "child_created requires child_id.")
            _require(self.lineage_id is not None, "child_created requires lineage_id.")
        if self.reproduction_allowed and not self.child_created:
            _require(
                self.blocked_reason not in {"", "none"},
                "allowed reproduction without child requires a post-gate blocked_reason.",
            )
        if not self.reproduction_allowed:
            _require(
                self.blocked_reason not in {"", "none"},
                "blocked reproduction requires a concrete blocked_reason.",
            )

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "schema_version": self.schema_version,
            "organism_id": self.organism_id,
            "tick": self.tick,
            "reproduction_action_attempted": self.reproduction_action_attempted,
            "reproduction_allowed": self.reproduction_allowed,
            "blocked_reason": self.blocked_reason,
            "runtime_atp": self.runtime_atp,
            "min_runtime_atp_required": self.min_runtime_atp_required,
            "parent_atp_cost": self.parent_atp_cost,
            "offspring_atp_fraction": self.offspring_atp_fraction,
            "available_space": self.available_space,
            "population_capacity": self.population_capacity,
            "mutation_applied": self.mutation_applied,
            "child_created": self.child_created,
            "child_id": self.child_id,
            "lineage_id": self.lineage_id,
        }

    def digest(self) -> str:
        return _digest(self.to_dict())


@dataclass(frozen=True, slots=True)
class ReproductionGateRecord:
    organism_id: str
    tick: int
    allowed: bool
    blocked_reason: str
    runtime_atp: float
    min_runtime_atp_required: float | None = None
    parent_atp_cost: float | None = None
    offspring_atp_fraction: float | None = None
    population_capacity: int | None = None
    available_space: bool | None = None
    schema_version: str = "reproduction_gate_record_v1"

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "schema_version": self.schema_version,
            "organism_id": self.organism_id,
            "tick": self.tick,
            "allowed": self.allowed,
            "blocked_reason": self.blocked_reason,
            "runtime_atp": self.runtime_atp,
            "min_runtime_atp_required": self.min_runtime_atp_required,
            "parent_atp_cost": self.parent_atp_cost,
            "offspring_atp_fraction": self.offspring_atp_fraction,
            "population_capacity": self.population_capacity,
            "available_space": self.available_space,
        }

    def digest(self) -> str:
        return _digest(self.to_dict())


@dataclass(frozen=True, slots=True)
class LineageGrowthRecord:
    tick: int
    births: int
    deaths: int
    before_count: int
    after_count: int
    lineage_growth_delta: int
    schema_version: str = "lineage_growth_record_v1"

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "schema_version": self.schema_version,
            "tick": self.tick,
            "births": self.births,
            "deaths": self.deaths,
            "before_count": self.before_count,
            "after_count": self.after_count,
            "lineage_growth_delta": self.lineage_growth_delta,
        }

    def digest(self) -> str:
        return _digest(self.to_dict())


@dataclass(frozen=True, slots=True)
class CapsuleCostRecord:
    capsule_id: str
    source_organism_id: str
    target_organism_id: str
    emission_runtime_cost: float = 0.0
    emission_learning_cost: float = 0.0
    adoption_runtime_cost: float = 0.0
    adoption_learning_cost: float = 0.0
    schema_version: str = "capsule_cost_record_v1"

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "schema_version": self.schema_version,
            "capsule_id": self.capsule_id,
            "source_organism_id": self.source_organism_id,
            "target_organism_id": self.target_organism_id,
            "emission_runtime_cost": self.emission_runtime_cost,
            "emission_learning_cost": self.emission_learning_cost,
            "adoption_runtime_cost": self.adoption_runtime_cost,
            "adoption_learning_cost": self.adoption_learning_cost,
        }

    def digest(self) -> str:
        return _digest(self.to_dict())


@dataclass(frozen=True, slots=True)
class CapsuleUtilityRecord:
    capsule_id: str
    source_organism_id: str
    target_organism_id: str
    source_fitness: float
    source_fitness_status: str
    confidence: float
    emitted_tick: int
    read_tick: int
    adoption_tick: int
    adoption_success: bool
    blocked_reason: str | None
    source_fitness_status_original: str | None = None
    target_fitness_before: float | None = None
    target_fitness_after: float | None = None
    utility_delta: float | None = None
    target_behavior_digest_before: str | None = None
    target_behavior_digest_after: str | None = None
    state_changed: bool = False
    adoption_semantics: str = "record_only"
    claim_eligible: bool = False
    capsule_status: str = "transferred_not_useful"
    target_selection_fitness_before: float | None = None
    target_selection_fitness_after: float | None = None
    utility_selection_delta: float | None = None
    utility_raw_fitness_delta: float | None = None
    utility_task_delta: float | None = None
    utility_status: str = "not_evidence_bearing"
    utility_protocol_digest: str | None = None
    schema_version: str = "capsule_utility_record_v2"

    def _payload(self) -> dict[str, JsonValue]:
        return {
            "schema_version": self.schema_version,
            "capsule_id": self.capsule_id,
            "source_organism_id": self.source_organism_id,
            "target_organism_id": self.target_organism_id,
            "source_fitness": self.source_fitness,
            "source_fitness_status": self.source_fitness_status,
            "source_fitness_status_original": self.source_fitness_status_original,
            "confidence": self.confidence,
            "emitted_tick": self.emitted_tick,
            "read_tick": self.read_tick,
            "adoption_tick": self.adoption_tick,
            "adoption_success": self.adoption_success,
            "blocked_reason": self.blocked_reason,
            "target_fitness_before": self.target_fitness_before,
            "target_fitness_after": self.target_fitness_after,
            "target_selection_fitness_before": self.target_selection_fitness_before,
            "target_selection_fitness_after": self.target_selection_fitness_after,
            "utility_delta": self.utility_delta,
            "utility_selection_delta": self.utility_selection_delta,
            "utility_raw_fitness_delta": self.utility_raw_fitness_delta,
            "utility_task_delta": self.utility_task_delta,
            "target_behavior_digest_before": self.target_behavior_digest_before,
            "target_behavior_digest_after": self.target_behavior_digest_after,
            "behavior_digest_before": self.target_behavior_digest_before,
            "behavior_digest_after": self.target_behavior_digest_after,
            "state_changed": self.state_changed,
            "adoption_semantics": self.adoption_semantics,
            "utility_status": self.utility_status,
            "utility_protocol_digest": self.utility_protocol_digest,
            "claim_eligible": self.claim_eligible,
            "capsule_status": self.capsule_status,
        }

    def to_dict(self) -> dict[str, JsonValue]:
        payload = self._payload()
        payload["record_digest"] = self.digest()
        return payload

    def digest(self) -> str:
        return _digest(self._payload())


@dataclass(frozen=True, slots=True)
class PostCapsuleBehaviorRecord:
    capsule_id: str
    target_organism_id: str
    behavior_digest_before: str | None
    behavior_digest_after: str | None
    changed: bool
    schema_version: str = "post_capsule_behavior_record_v1"

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "schema_version": self.schema_version,
            "capsule_id": self.capsule_id,
            "target_organism_id": self.target_organism_id,
            "behavior_digest_before": self.behavior_digest_before,
            "behavior_digest_after": self.behavior_digest_after,
            "changed": self.changed,
        }

    def digest(self) -> str:
        return _digest(self.to_dict())


@dataclass(frozen=True, slots=True)
class EngineDigestAuditRecord:
    digest_name: str
    stable: bool
    mismatch_reason: str | None = None
    nondeterministic_field: str | None = None
    suggested_fix: str | None = None
    digest: str | None = None
    schema_version: str = "engine_digest_audit_record_v1"

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "schema_version": self.schema_version,
            "digest_name": self.digest_name,
            "stable": self.stable,
            "mismatch_reason": self.mismatch_reason,
            "nondeterministic_field": self.nondeterministic_field,
            "suggested_fix": self.suggested_fix,
            "digest": self.digest,
        }


@dataclass(frozen=True, slots=True)
class DigestInstabilityReason:
    digest_name: str
    stable: bool
    mismatch_reason: str | None
    nondeterministic_field: str | None
    suggested_fix: str | None
    schema_version: str = "digest_instability_reason_v1"

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "schema_version": self.schema_version,
            "digest_name": self.digest_name,
            "stable": self.stable,
            "mismatch_reason": self.mismatch_reason,
            "nondeterministic_field": self.nondeterministic_field,
            "suggested_fix": self.suggested_fix,
        }


@dataclass(frozen=True, slots=True)
class InventoryState:
    organism_id: str
    tick: int
    items: tuple[tuple[str, float], ...] = ()
    position: Position | None = None
    schema_version: str = "inventory_state_v1"

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "schema_version": self.schema_version,
            "organism_id": self.organism_id,
            "tick": self.tick,
            "items": [[name, amount] for name, amount in self.items],
            "position": None if self.position is None else list(self.position),
        }

    def digest(self) -> str:
        return _digest(self.to_dict())


@dataclass(frozen=True, slots=True)
class ActionPreconditionRecord:
    organism_id: str
    tick: int
    action: str
    allowed: bool
    missing_inputs: tuple[str, ...] = ()
    blocked_reason: str | None = None
    schema_version: str = "action_precondition_record_v1"

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "schema_version": self.schema_version,
            "organism_id": self.organism_id,
            "tick": self.tick,
            "action": self.action,
            "allowed": self.allowed,
            "missing_inputs": list(self.missing_inputs),
            "blocked_reason": self.blocked_reason,
        }

    def digest(self) -> str:
        return _digest(self.to_dict())


@dataclass(frozen=True, slots=True)
class OutputCompletenessRecord:
    artifact_name: str
    schema_version: str
    feature_status: FeatureStatus
    record_count: int
    measured_after_final_write: bool
    self_size_reliable: bool
    status_reason: str = ""

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "artifact_name": self.artifact_name,
            "schema_version": self.schema_version,
            "feature_status": self.feature_status,
            "record_count": self.record_count,
            "measured_after_final_write": self.measured_after_final_write,
            "self_size_reliable": self.self_size_reliable,
            "status_reason": self.status_reason,
        }

    def digest(self) -> str:
        return _digest(self.to_dict())


@dataclass(frozen=True, slots=True)
class ExportWrittenFile:
    table_name: str
    path: str
    size_bytes: int
    row_count: int
    header_digest: str
    file_digest: str
    feature_status: FeatureStatus
    status_reason: str
    schema_version: str = "export_written_file_v1"

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "schema_version": self.schema_version,
            "table_name": self.table_name,
            "path": self.path,
            "size_bytes": self.size_bytes,
            "row_count": self.row_count,
            "header_digest": self.header_digest,
            "file_digest": self.file_digest,
            "feature_status": self.feature_status,
            "status_reason": self.status_reason,
        }

    def digest(self) -> str:
        return _digest(self.to_dict())


@dataclass(frozen=True, slots=True)
class ExportWriteManifest:
    output_dir: str
    files: tuple[ExportWrittenFile, ...]
    schema_version: str = "export_write_manifest_v1"

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "schema_version": self.schema_version,
            "output_dir": self.output_dir,
            "files": [item.to_dict() for item in self.files],
        }

    def digest(self) -> str:
        return _digest(self.to_dict())


def _csv_cell(value: Any) -> str | int | float | bool | None:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def write_export_csvs(
    result: object,
    output_dir: str | Path,
    *,
    include_empty: bool = True,
    include_status_rows: bool = True,
) -> ExportWriteManifest:
    """Write public result exports as schema-safe CSV files.

    This is a library-level writer: it does not build reports or scenarios. It
    only ensures every exported CSV has a header, optional status row for empty
    tables, and a digest manifest so runners do not need private hacks.
    """

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    envelopes = getattr(result, "export_envelopes_by_name")
    schemas = getattr(result, "export_table_schemas")
    files: list[ExportWrittenFile] = []
    for name in sorted(envelopes):
        envelope = envelopes[name]
        records = tuple(getattr(envelope, "records", ()))
        if not records and not include_empty:
            continue
        fieldnames = tuple(schemas.get(name, ())) or (
            "schema_version",
            "feature_status",
            "status_reason",
        )
        if records and not all(isinstance(row, dict) for row in records):
            raise ConfigurationError(
                f"Export {name!r} contains non-dict records; measured CSV export would be lossy."
            )
        if not records and include_status_rows:
            base = {key: None for key in fieldnames}
            base.update(
                {
                    "schema_version": envelope.schema_version,
                    "feature_status": envelope.feature_status,
                    "status_reason": envelope.status_reason,
                }
            )
            rows = (base,)
        else:
            rows = records
        path = out / f"{name}.csv"
        written_rows = 0
        with path.open("w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=list(fieldnames), extrasaction="ignore")
            writer.writeheader()
            for row in rows:
                if not isinstance(row, dict):
                    raise ConfigurationError(
                        f"Export {name!r} contains non-dict records; measured CSV export would be lossy."
                    )
                writer.writerow({key: _csv_cell(row.get(key)) for key in fieldnames})
                written_rows += 1
        data = path.read_bytes()
        header_digest = hashlib.sha256(
            json.dumps(list(fieldnames), sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
        files.append(
            ExportWrittenFile(
                table_name=name,
                path=str(path),
                size_bytes=len(data),
                row_count=written_rows,
                header_digest=header_digest,
                file_digest=hashlib.sha256(data).hexdigest(),
                feature_status=envelope.feature_status,
                status_reason=envelope.status_reason,
            )
        )
    return ExportWriteManifest(output_dir=str(out), files=tuple(files))
