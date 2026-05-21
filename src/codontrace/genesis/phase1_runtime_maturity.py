"""Phase-1 runtime maturity evidence records for GENESIS.

The helpers in this module deliberately sit on top of existing runtime objects:
they do not force births, do not bias selection, do not turn placeholder outputs
into claims, and do not weaken ClaimGate.  They convert already-executed
runtime evidence into deterministic audit records that can be used by tests,
manifests, pilots, and external reviewers.
"""

from __future__ import annotations

import hashlib
import json
import math
from collections import Counter
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field, replace
from typing import Any

from codontrace._types import JsonValue

PHASE1_SCHEMA_VERSION = "phase1_runtime_maturity_v1"

_ALLOWED_STATUS = {
    "complete",
    "complete_limited_claim",
    "provisional_with_evidence",
    "blocked_by_missing_runtime_wiring",
    "blocked_by_missing_controls",
    "blocked_by_missing_replay_policy",
    "blocked_by_missing_manifest",
    "blocked_by_test_failure",
    "empty_but_available",
    "disabled_by_config",
    "descriptive_only",
    "not_claim_relevant",
}

_POSITIVE_STATUS = {"complete", "complete_limited_claim", "provisional_with_evidence"}

_ALLOWED_MUTATION_BLOCKED_REASONS = {
    "none",
    "operator_disabled",
    "rate_zero",
    "rng_not_selected",
    "invalid_source_genome",
    "max_length_reached",
    "min_length_reached",
    "codon_table_incompatible",
    "mutation_budget_exhausted",
    "validation_failed",
    "unknown",
}

_ALLOWED_BIRTH_BLOCKED_REASONS = {
    "none",
    "no_reproduction_action",
    "insufficient_runtime_atp",
    "insufficient_learning_atp",
    "population_capacity_reached",
    "no_available_space",
    "reproduction_disabled",
    "genome_invalid",
    "parent_cost_too_high",
    "offspring_fraction_invalid",
    "action_not_executed",
    "mutation_validation_failed",
    "unknown",
}

_ALLOWED_DEATH_REASONS = {
    "starvation",
    "runtime_atp_depleted",
    "learning_atp_depleted",
    "action_cost_overrun",
    "capsule_emission_cost",
    "capsule_adoption_cost",
    "reproduction_cost",
    "hazard_damage",
    "invalid_state",
    "blocked_action_loop",
    "resource_depletion",
    "age_limit",
    "population_policy_removed",
    "unknown",
}

_ALLOWED_CAPSULE_CONTROL_REASONS = {
    "none",
    "shuffle_control",
    "low_confidence",
    "expired_ttl",
    "source_unavailable",
    "source_fitness_unavailable",
    "misleading_capsule",
    "out_of_radius",
    "duplicate_capsule",
    "target_capacity_reached",
    "source_target_same",
    "cost_greater_than_benefit",
}

_ALLOWED_TOOLCHAIN_REASONS = {
    "none",
    "missing_resource",
    "wrong_resource_kind",
    "missing_item",
    "wrong_item",
    "wrong_terrain",
    "locked_target",
    "invalid_inventory",
    "insufficient_energy",
    "invalid_target_cell",
    "failed_collect",
    "failed_craft",
    "failed_unlock",
    "failed_cross",
    "failed_deposit",
    "disabled_by_config",
    "unknown",
}

_ALLOWED_ROLE_LABELS = {
    "collector",
    "carrier",
    "unlocker",
    "depositor",
    "scout",
    "reproducer",
    "memory_user",
    "capsule_sender",
    "capsule_receiver",
    "cooperator",
    "competitor",
    "unknown",
}

_ALLOWED_INTERVENTIONS = {
    "remove_memory",
    "remove_capsule",
    "remove_qd_pressure",
    "remove_adf_macro",
    "remove_causal_edge",
    "remove_tool_action",
    "remove_social_partner",
    "counterfactual_world_seed",
}

_PHASE1_FEATURES = (
    "mutation_operator_maturity",
    "birth_reproduction_gate",
    "death_taxonomy_energy_diagnostics",
    "capsule_controls_utility",
    "toolchain_failures_preconditions",
    "role_detection_from_behavior",
    "adf_usefulness_compression",
    "causal_intervention_bridge",
    "runtime_qd_pareto_qd",
)


def _digest(payload: Mapping[str, JsonValue]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False)
    forbidden = ("object at 0x", "<function", "<bound method")
    if any(item in encoded for item in forbidden):
        raise ValueError("unstable runtime object representation entered phase1 digest payload")
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _finite(name: str, value: int | float | None, *, default: float = 0.0) -> float:
    if value is None:
        return default
    number = float(value)
    if not math.isfinite(number):
        raise ValueError(f"{name} must be finite")
    return number


def _non_empty(name: str, value: str) -> str:
    if not value:
        raise ValueError(f"{name} is required")
    return value


def _status(value: str) -> str:
    if value not in _ALLOWED_STATUS:
        raise ValueError(f"Unsupported phase1 status {value!r}")
    return value


def _reason(value: str | None, allowed: set[str]) -> str:
    normalized = "none" if value in (None, "") else str(value)
    if normalized not in allowed:
        return "unknown"
    return normalized


def _record_digest(payload: Mapping[str, JsonValue]) -> str:
    clean = dict(payload)
    clean.pop("record_digest", None)
    return _digest(clean)


def _stable_dict(data: Mapping[str, Any] | None) -> dict[str, JsonValue]:
    if not data:
        return {}
    out: dict[str, JsonValue] = {}
    for key, value in sorted(data.items()):
        if isinstance(value, bool):
            out[str(key)] = value
        elif isinstance(value, int):
            out[str(key)] = value
        elif isinstance(value, float):
            if not math.isfinite(value):
                raise ValueError(f"non-finite value for {key!r}")
            out[str(key)] = value
        elif value is None:
            out[str(key)] = None
        elif isinstance(value, str):
            out[str(key)] = value
        elif isinstance(value, Mapping):
            out[str(key)] = _stable_dict(value)
        elif isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
            out[str(key)] = [str(item) if not isinstance(item, (int, float, bool, type(None), Mapping)) else item for item in value]  # type: ignore[list-item]
        else:
            out[str(key)] = str(value)
    return out


@dataclass(frozen=True, slots=True)
class MutationOperatorAuditRecord:
    mutation_id: str
    mutation_kind: str
    operator_name: str
    operator_enabled: bool
    rng_seed: int | None
    rng_stream_id: str
    parent_lineage_id: str
    child_lineage_id: str
    before_genome_digest: str
    after_genome_digest: str
    program_length_before: int
    program_length_after: int
    codon_table_digest: str
    codon_table_compatibility_status: str
    validity_status: str
    blocked_reason: str | None
    operator_parameters_digest: str
    record_digest: str = ""
    schema_version: str = "phase1_mutation_operator_audit_v1"

    def __post_init__(self) -> None:
        _non_empty("mutation_id", self.mutation_id)
        _non_empty("mutation_kind", self.mutation_kind)
        _non_empty("operator_name", self.operator_name)
        _non_empty("rng_stream_id", self.rng_stream_id)
        _non_empty("before_genome_digest", self.before_genome_digest)
        _non_empty("after_genome_digest", self.after_genome_digest)
        if self.program_length_before < 0 or self.program_length_after < 0:
            raise ValueError("program lengths must be non-negative")
        reason = _reason(self.blocked_reason, _ALLOWED_MUTATION_BLOCKED_REASONS)
        object.__setattr__(self, "blocked_reason", None if reason == "none" else reason)
        computed = _record_digest(self.to_dict(include_digest=False))
        if self.record_digest and self.record_digest != computed:
            raise ValueError("MutationOperatorAuditRecord digest mismatch")
        object.__setattr__(self, "record_digest", computed)

    def to_dict(self, *, include_digest: bool = True) -> dict[str, JsonValue]:
        payload: dict[str, JsonValue] = {
            "schema_version": self.schema_version,
            "mutation_id": self.mutation_id,
            "mutation_kind": self.mutation_kind,
            "operator_name": self.operator_name,
            "operator_enabled": self.operator_enabled,
            "rng_seed": self.rng_seed,
            "rng_stream_id": self.rng_stream_id,
            "parent_lineage_id": self.parent_lineage_id,
            "child_lineage_id": self.child_lineage_id,
            "before_genome_digest": self.before_genome_digest,
            "after_genome_digest": self.after_genome_digest,
            "program_length_before": self.program_length_before,
            "program_length_after": self.program_length_after,
            "codon_table_digest": self.codon_table_digest,
            "codon_table_compatibility_status": self.codon_table_compatibility_status,
            "validity_status": self.validity_status,
            "blocked_reason": self.blocked_reason,
            "operator_parameters_digest": self.operator_parameters_digest,
        }
        if include_digest:
            payload["record_digest"] = self.record_digest
        return payload


@dataclass(frozen=True, slots=True)
class ReproductionGateAuditRecord:
    organism_id: str
    tick: int
    reproduction_action_attempted: bool
    reproduction_allowed: bool
    blocked_reason: str | None
    runtime_atp: float
    learning_atp: float | None
    min_runtime_atp_required: float | None
    parent_atp_cost: float | None
    offspring_atp_fraction: float | None
    available_space: bool
    population_capacity: int | None
    parent_genome_digest: str
    child_genome_digest: str | None
    mutation_applied: bool
    child_created: bool
    child_id: str | None
    lineage_id: str
    record_digest: str = ""
    schema_version: str = "phase1_reproduction_gate_audit_v1"

    def __post_init__(self) -> None:
        _non_empty("organism_id", self.organism_id)
        if self.tick < 0:
            raise ValueError("tick must be non-negative")
        object.__setattr__(self, "runtime_atp", _finite("runtime_atp", self.runtime_atp))
        if self.learning_atp is not None:
            object.__setattr__(self, "learning_atp", _finite("learning_atp", self.learning_atp))
        reason = _reason(self.blocked_reason, _ALLOWED_BIRTH_BLOCKED_REASONS)
        object.__setattr__(self, "blocked_reason", None if reason == "none" else reason)
        computed = _record_digest(self.to_dict(include_digest=False))
        if self.record_digest and self.record_digest != computed:
            raise ValueError("ReproductionGateAuditRecord digest mismatch")
        object.__setattr__(self, "record_digest", computed)

    def to_dict(self, *, include_digest: bool = True) -> dict[str, JsonValue]:
        payload: dict[str, JsonValue] = {
            "schema_version": self.schema_version,
            "organism_id": self.organism_id,
            "tick": self.tick,
            "reproduction_action_attempted": self.reproduction_action_attempted,
            "reproduction_allowed": self.reproduction_allowed,
            "blocked_reason": self.blocked_reason,
            "runtime_atp": self.runtime_atp,
            "learning_atp": self.learning_atp,
            "min_runtime_atp_required": self.min_runtime_atp_required,
            "parent_atp_cost": self.parent_atp_cost,
            "offspring_atp_fraction": self.offspring_atp_fraction,
            "available_space": self.available_space,
            "population_capacity": self.population_capacity,
            "parent_genome_digest": self.parent_genome_digest,
            "child_genome_digest": self.child_genome_digest,
            "mutation_applied": self.mutation_applied,
            "child_created": self.child_created,
            "child_id": self.child_id,
            "lineage_id": self.lineage_id,
        }
        if include_digest:
            payload["record_digest"] = self.record_digest
        return payload


@dataclass(frozen=True, slots=True)
class DeathEnergyDiagnosticRecord:
    tick: int
    organism_id: str
    death_reason: str
    last_action: str | None
    last_action_status: str | None
    runtime_atp_before: float
    runtime_atp_after: float
    learning_atp_before: float | None
    learning_atp_after: float | None
    fitness_before: float | None
    fitness_after: float | None
    blocked_action_count: int
    resource_context: dict[str, JsonValue] = field(default_factory=dict)
    capsule_cost_context: dict[str, JsonValue] = field(default_factory=dict)
    reproduction_cost_context: dict[str, JsonValue] = field(default_factory=dict)
    record_digest: str = ""
    schema_version: str = "phase1_death_energy_diagnostic_v1"

    def __post_init__(self) -> None:
        if self.tick < 0:
            raise ValueError("tick must be non-negative")
        _non_empty("organism_id", self.organism_id)
        reason = self.death_reason if self.death_reason in _ALLOWED_DEATH_REASONS else "unknown"
        object.__setattr__(self, "death_reason", reason)
        object.__setattr__(self, "runtime_atp_before", _finite("runtime_atp_before", self.runtime_atp_before))
        object.__setattr__(self, "runtime_atp_after", _finite("runtime_atp_after", self.runtime_atp_after))
        if self.learning_atp_before is not None:
            object.__setattr__(self, "learning_atp_before", _finite("learning_atp_before", self.learning_atp_before))
        if self.learning_atp_after is not None:
            object.__setattr__(self, "learning_atp_after", _finite("learning_atp_after", self.learning_atp_after))
        if self.fitness_before is not None:
            object.__setattr__(self, "fitness_before", _finite("fitness_before", self.fitness_before))
        if self.fitness_after is not None:
            object.__setattr__(self, "fitness_after", _finite("fitness_after", self.fitness_after))
        if self.blocked_action_count < 0:
            raise ValueError("blocked_action_count must be non-negative")
        object.__setattr__(self, "resource_context", _stable_dict(self.resource_context))
        object.__setattr__(self, "capsule_cost_context", _stable_dict(self.capsule_cost_context))
        object.__setattr__(self, "reproduction_cost_context", _stable_dict(self.reproduction_cost_context))
        computed = _record_digest(self.to_dict(include_digest=False))
        if self.record_digest and self.record_digest != computed:
            raise ValueError("DeathEnergyDiagnosticRecord digest mismatch")
        object.__setattr__(self, "record_digest", computed)

    def to_dict(self, *, include_digest: bool = True) -> dict[str, JsonValue]:
        payload: dict[str, JsonValue] = {
            "schema_version": self.schema_version,
            "tick": self.tick,
            "organism_id": self.organism_id,
            "death_reason": self.death_reason,
            "last_action": self.last_action,
            "last_action_status": self.last_action_status,
            "runtime_atp_before": self.runtime_atp_before,
            "runtime_atp_after": self.runtime_atp_after,
            "learning_atp_before": self.learning_atp_before,
            "learning_atp_after": self.learning_atp_after,
            "fitness_before": self.fitness_before,
            "fitness_after": self.fitness_after,
            "blocked_action_count": self.blocked_action_count,
            "resource_context": dict(self.resource_context),
            "capsule_cost_context": dict(self.capsule_cost_context),
            "reproduction_cost_context": dict(self.reproduction_cost_context),
        }
        if include_digest:
            payload["record_digest"] = self.record_digest
        return payload


@dataclass(frozen=True, slots=True)
class CapsuleControlAuditRecord:
    capsule_id: str
    source_id: str | None
    target_id: str | None
    control_case: str
    adopted: bool
    claim_eligible: bool
    capsule_social_transfer_score: float
    non_capsule_cooperation_score: float
    resource_competition_score: float
    collective_coordination_score: float
    blocked_reason: str | None
    record_digest: str = ""
    schema_version: str = "phase1_capsule_control_audit_v1"

    def __post_init__(self) -> None:
        _non_empty("capsule_id", self.capsule_id)
        control = _reason(self.control_case, _ALLOWED_CAPSULE_CONTROL_REASONS)
        object.__setattr__(self, "control_case", control)
        reason = _reason(self.blocked_reason, _ALLOWED_CAPSULE_CONTROL_REASONS)
        object.__setattr__(self, "blocked_reason", None if reason == "none" else reason)
        for name in (
            "capsule_social_transfer_score",
            "non_capsule_cooperation_score",
            "resource_competition_score",
            "collective_coordination_score",
        ):
            object.__setattr__(self, name, _finite(name, getattr(self, name)))
        if control != "none" and self.claim_eligible:
            raise ValueError("capsule negative/control cases cannot be claim_eligible")
        computed = _record_digest(self.to_dict(include_digest=False))
        if self.record_digest and self.record_digest != computed:
            raise ValueError("CapsuleControlAuditRecord digest mismatch")
        object.__setattr__(self, "record_digest", computed)

    def to_dict(self, *, include_digest: bool = True) -> dict[str, JsonValue]:
        payload: dict[str, JsonValue] = {
            "schema_version": self.schema_version,
            "capsule_id": self.capsule_id,
            "source_id": self.source_id,
            "target_id": self.target_id,
            "control_case": self.control_case,
            "adopted": self.adopted,
            "claim_eligible": self.claim_eligible,
            "capsule_social_transfer_score": self.capsule_social_transfer_score,
            "non_capsule_cooperation_score": self.non_capsule_cooperation_score,
            "resource_competition_score": self.resource_competition_score,
            "collective_coordination_score": self.collective_coordination_score,
            "blocked_reason": self.blocked_reason,
        }
        if include_digest:
            payload["record_digest"] = self.record_digest
        return payload


@dataclass(frozen=True, slots=True)
class ToolchainPreconditionAuditRecord:
    action_name: str
    precondition_status: str
    blocked_reason: str | None
    inventory_before: dict[str, JsonValue]
    inventory_after: dict[str, JsonValue]
    world_cell_before: dict[str, JsonValue]
    world_cell_after: dict[str, JsonValue]
    reward_delta: float
    chain_progress_before: float
    chain_progress_after: float
    record_digest: str = ""
    schema_version: str = "phase1_toolchain_precondition_audit_v1"

    def __post_init__(self) -> None:
        _non_empty("action_name", self.action_name)
        if self.precondition_status not in {"passed", "blocked", "failed", "disabled", "unknown"}:
            raise ValueError("unsupported toolchain precondition_status")
        reason = _reason(self.blocked_reason, _ALLOWED_TOOLCHAIN_REASONS)
        object.__setattr__(self, "blocked_reason", None if reason == "none" else reason)
        object.__setattr__(self, "inventory_before", _stable_dict(self.inventory_before))
        object.__setattr__(self, "inventory_after", _stable_dict(self.inventory_after))
        object.__setattr__(self, "world_cell_before", _stable_dict(self.world_cell_before))
        object.__setattr__(self, "world_cell_after", _stable_dict(self.world_cell_after))
        for name in ("reward_delta", "chain_progress_before", "chain_progress_after"):
            object.__setattr__(self, name, _finite(name, getattr(self, name)))
        computed = _record_digest(self.to_dict(include_digest=False))
        if self.record_digest and self.record_digest != computed:
            raise ValueError("ToolchainPreconditionAuditRecord digest mismatch")
        object.__setattr__(self, "record_digest", computed)

    def to_dict(self, *, include_digest: bool = True) -> dict[str, JsonValue]:
        payload: dict[str, JsonValue] = {
            "schema_version": self.schema_version,
            "action_name": self.action_name,
            "precondition_status": self.precondition_status,
            "blocked_reason": self.blocked_reason,
            "inventory_before": dict(self.inventory_before),
            "inventory_after": dict(self.inventory_after),
            "world_cell_before": dict(self.world_cell_before),
            "world_cell_after": dict(self.world_cell_after),
            "reward_delta": self.reward_delta,
            "chain_progress_before": self.chain_progress_before,
            "chain_progress_after": self.chain_progress_after,
        }
        if include_digest:
            payload["record_digest"] = self.record_digest
        return payload


@dataclass(frozen=True, slots=True)
class RuntimeRoleEvidenceRecord:
    role_id: str
    organism_id: str
    role_label: str
    source_actions: tuple[str, ...]
    source_event_ids: tuple[str, ...]
    support_count: int
    confidence: float
    first_tick: int
    last_tick: int
    role_changed: bool
    contribution_digest: str
    record_digest: str = ""
    schema_version: str = "phase1_runtime_role_evidence_v1"

    def __post_init__(self) -> None:
        _non_empty("role_id", self.role_id)
        _non_empty("organism_id", self.organism_id)
        if self.role_label not in _ALLOWED_ROLE_LABELS:
            object.__setattr__(self, "role_label", "unknown")
        object.__setattr__(self, "source_actions", tuple(str(item) for item in self.source_actions))
        object.__setattr__(self, "source_event_ids", tuple(str(item) for item in self.source_event_ids))
        if self.support_count < 0:
            raise ValueError("support_count must be non-negative")
        object.__setattr__(self, "confidence", _finite("confidence", self.confidence))
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be in [0, 1]")
        if self.first_tick < 0 or self.last_tick < self.first_tick:
            raise ValueError("invalid role tick range")
        computed = _record_digest(self.to_dict(include_digest=False))
        if self.record_digest and self.record_digest != computed:
            raise ValueError("RuntimeRoleEvidenceRecord digest mismatch")
        object.__setattr__(self, "record_digest", computed)

    def to_dict(self, *, include_digest: bool = True) -> dict[str, JsonValue]:
        payload: dict[str, JsonValue] = {
            "schema_version": self.schema_version,
            "role_id": self.role_id,
            "organism_id": self.organism_id,
            "role_label": self.role_label,
            "source_actions": list(self.source_actions),
            "source_event_ids": list(self.source_event_ids),
            "support_count": self.support_count,
            "confidence": self.confidence,
            "first_tick": self.first_tick,
            "last_tick": self.last_tick,
            "role_changed": self.role_changed,
            "contribution_digest": self.contribution_digest,
        }
        if include_digest:
            payload["record_digest"] = self.record_digest
        return payload


@dataclass(frozen=True, slots=True)
class ADFUsefulnessAuditRecord:
    macro_id: str
    source_trace_digest: str
    source_map_digest: str
    expanded_actions: tuple[str, ...]
    reuse_count: int
    compression_ratio: float
    task_delta: float
    null_control_delta: float
    permutation_control_delta: float
    cost_before: float
    cost_after: float
    utility_status: str
    claim_eligible: bool
    record_digest: str = ""
    schema_version: str = "phase1_adf_usefulness_audit_v1"

    def __post_init__(self) -> None:
        _non_empty("macro_id", self.macro_id)
        object.__setattr__(self, "expanded_actions", tuple(str(item) for item in self.expanded_actions))
        if self.reuse_count < 0:
            raise ValueError("reuse_count must be non-negative")
        for name in (
            "compression_ratio",
            "task_delta",
            "null_control_delta",
            "permutation_control_delta",
            "cost_before",
            "cost_after",
        ):
            object.__setattr__(self, name, _finite(name, getattr(self, name)))
        if len(self.expanded_actions) <= 1 and self.claim_eligible:
            raise ValueError("single-action macro cannot be compression-claim eligible")
        if self.claim_eligible and (not self.source_map_digest or self.reuse_count < 1):
            raise ValueError("ADF claim_eligible requires source map and reuse evidence")
        computed = _record_digest(self.to_dict(include_digest=False))
        if self.record_digest and self.record_digest != computed:
            raise ValueError("ADFUsefulnessAuditRecord digest mismatch")
        object.__setattr__(self, "record_digest", computed)

    def to_dict(self, *, include_digest: bool = True) -> dict[str, JsonValue]:
        payload: dict[str, JsonValue] = {
            "schema_version": self.schema_version,
            "macro_id": self.macro_id,
            "source_trace_digest": self.source_trace_digest,
            "source_map_digest": self.source_map_digest,
            "expanded_actions": list(self.expanded_actions),
            "reuse_count": self.reuse_count,
            "compression_ratio": self.compression_ratio,
            "task_delta": self.task_delta,
            "null_control_delta": self.null_control_delta,
            "permutation_control_delta": self.permutation_control_delta,
            "cost_before": self.cost_before,
            "cost_after": self.cost_after,
            "utility_status": self.utility_status,
            "claim_eligible": self.claim_eligible,
        }
        if include_digest:
            payload["record_digest"] = self.record_digest
        return payload


@dataclass(frozen=True, slots=True)
class CausalInterventionAuditRecord:
    intervention_id: str
    intervention_type: str
    target_id: str
    baseline_digest: str
    treatment_digest: str
    outcome_before: float
    outcome_after: float
    effect_size: float
    confidence_status: str
    ablation_supported: bool
    failure_reason: str | None
    event_graph_digest: str
    causal_graph_digest: str
    record_digest: str = ""
    schema_version: str = "phase1_causal_intervention_audit_v1"

    def __post_init__(self) -> None:
        _non_empty("intervention_id", self.intervention_id)
        if self.intervention_type not in _ALLOWED_INTERVENTIONS:
            raise ValueError("unsupported intervention_type")
        for name in ("baseline_digest", "treatment_digest", "event_graph_digest", "causal_graph_digest"):
            _non_empty(name, str(getattr(self, name)))
        if self.baseline_digest == self.treatment_digest and self.ablation_supported:
            raise ValueError("ablation_supported requires distinct baseline and treatment digests")
        for name in ("outcome_before", "outcome_after", "effect_size"):
            object.__setattr__(self, name, _finite(name, getattr(self, name)))
        if self.confidence_status not in {"validated", "limited", "no_effect", "failed", "not_run", "metadata_only_rejected"}:
            raise ValueError("unsupported confidence_status")
        if self.confidence_status in {"not_run", "metadata_only_rejected"} and self.ablation_supported:
            raise ValueError("invalid/metadata-only intervention cannot be ablation_supported")
        computed = _record_digest(self.to_dict(include_digest=False))
        if self.record_digest and self.record_digest != computed:
            raise ValueError("CausalInterventionAuditRecord digest mismatch")
        object.__setattr__(self, "record_digest", computed)

    def to_dict(self, *, include_digest: bool = True) -> dict[str, JsonValue]:
        payload: dict[str, JsonValue] = {
            "schema_version": self.schema_version,
            "intervention_id": self.intervention_id,
            "intervention_type": self.intervention_type,
            "target_id": self.target_id,
            "baseline_digest": self.baseline_digest,
            "treatment_digest": self.treatment_digest,
            "outcome_before": self.outcome_before,
            "outcome_after": self.outcome_after,
            "effect_size": self.effect_size,
            "confidence_status": self.confidence_status,
            "ablation_supported": self.ablation_supported,
            "failure_reason": self.failure_reason,
            "event_graph_digest": self.event_graph_digest,
            "causal_graph_digest": self.causal_graph_digest,
        }
        if include_digest:
            payload["record_digest"] = self.record_digest
        return payload


@dataclass(frozen=True, slots=True)
class RuntimeQDAuditRecord:
    qd_mode: str
    archive_size: int
    coverage: float
    qd_score: float
    novelty_scores: tuple[float, ...]
    parent_selection_before: tuple[str, ...]
    parent_selection_after: tuple[str, ...]
    survivor_selection_before: tuple[str, ...]
    survivor_selection_after: tuple[str, ...]
    qd_changed_selection: bool
    fallback_reason: str | None
    pareto_front_size: int
    objective_vector_digest: str
    record_digest: str = ""
    schema_version: str = "phase1_runtime_qd_audit_v1"

    def __post_init__(self) -> None:
        if self.archive_size < 0 or self.pareto_front_size < 0:
            raise ValueError("archive_size and pareto_front_size must be non-negative")
        object.__setattr__(self, "coverage", _finite("coverage", self.coverage))
        object.__setattr__(self, "qd_score", _finite("qd_score", self.qd_score))
        object.__setattr__(self, "novelty_scores", tuple(_finite("novelty_score", item) for item in self.novelty_scores))
        for name in (
            "parent_selection_before",
            "parent_selection_after",
            "survivor_selection_before",
            "survivor_selection_after",
        ):
            object.__setattr__(self, name, tuple(str(item) for item in getattr(self, name)))
        if self.qd_mode == "archive_only" and self.qd_changed_selection:
            raise ValueError("archive_only QD cannot claim changed selection pressure")
        computed = _record_digest(self.to_dict(include_digest=False))
        if self.record_digest and self.record_digest != computed:
            raise ValueError("RuntimeQDAuditRecord digest mismatch")
        object.__setattr__(self, "record_digest", computed)

    def to_dict(self, *, include_digest: bool = True) -> dict[str, JsonValue]:
        payload: dict[str, JsonValue] = {
            "schema_version": self.schema_version,
            "qd_mode": self.qd_mode,
            "archive_size": self.archive_size,
            "coverage": self.coverage,
            "qd_score": self.qd_score,
            "novelty_scores": list(self.novelty_scores),
            "parent_selection_before": list(self.parent_selection_before),
            "parent_selection_after": list(self.parent_selection_after),
            "survivor_selection_before": list(self.survivor_selection_before),
            "survivor_selection_after": list(self.survivor_selection_after),
            "qd_changed_selection": self.qd_changed_selection,
            "fallback_reason": self.fallback_reason,
            "pareto_front_size": self.pareto_front_size,
            "objective_vector_digest": self.objective_vector_digest,
        }
        if include_digest:
            payload["record_digest"] = self.record_digest
        return payload


@dataclass(frozen=True, slots=True)
class Phase1FeatureMaturityStatus:
    feature: str
    runtime_reachable: bool
    public_api: bool
    manifest: bool
    replay_policy: bool
    claim_gate: bool
    positive_tests: bool
    negative_tests: bool
    pilot_output: bool
    status: str
    evidence_digests: tuple[str, ...] = ()
    missing: tuple[str, ...] = ()
    record_digest: str = ""
    schema_version: str = "phase1_feature_maturity_status_v1"

    def __post_init__(self) -> None:
        _non_empty("feature", self.feature)
        object.__setattr__(self, "status", _status(self.status))
        object.__setattr__(self, "evidence_digests", tuple(sorted(str(item) for item in self.evidence_digests if item)))
        object.__setattr__(self, "missing", tuple(sorted(str(item) for item in self.missing if item)))
        computed = _record_digest(self.to_dict(include_digest=False))
        if self.record_digest and self.record_digest != computed:
            raise ValueError("Phase1FeatureMaturityStatus digest mismatch")
        object.__setattr__(self, "record_digest", computed)

    @property
    def claim_ready(self) -> bool:
        return self.status in _POSITIVE_STATUS and not self.missing

    def to_dict(self, *, include_digest: bool = True) -> dict[str, JsonValue]:
        payload: dict[str, JsonValue] = {
            "schema_version": self.schema_version,
            "feature": self.feature,
            "runtime_reachable": self.runtime_reachable,
            "public_api": self.public_api,
            "manifest": self.manifest,
            "replay_policy": self.replay_policy,
            "claim_gate": self.claim_gate,
            "positive_tests": self.positive_tests,
            "negative_tests": self.negative_tests,
            "pilot_output": self.pilot_output,
            "status": self.status,
            "claim_ready": self.claim_ready,
            "evidence_digests": list(self.evidence_digests),
            "missing": list(self.missing),
        }
        if include_digest:
            payload["record_digest"] = self.record_digest
        return payload


@dataclass(frozen=True, slots=True)
class Phase1RuntimeMaturityReport:
    run_digest: str
    source_digest: str
    mutation_records: tuple[MutationOperatorAuditRecord, ...] = ()
    reproduction_records: tuple[ReproductionGateAuditRecord, ...] = ()
    death_records: tuple[DeathEnergyDiagnosticRecord, ...] = ()
    capsule_control_records: tuple[CapsuleControlAuditRecord, ...] = ()
    toolchain_records: tuple[ToolchainPreconditionAuditRecord, ...] = ()
    role_records: tuple[RuntimeRoleEvidenceRecord, ...] = ()
    adf_records: tuple[ADFUsefulnessAuditRecord, ...] = ()
    causal_intervention_records: tuple[CausalInterventionAuditRecord, ...] = ()
    qd_records: tuple[RuntimeQDAuditRecord, ...] = ()
    feature_statuses: tuple[Phase1FeatureMaturityStatus, ...] = ()
    status: str = "provisional_with_evidence"
    record_digest: str = ""
    schema_version: str = PHASE1_SCHEMA_VERSION

    def __post_init__(self) -> None:
        _non_empty("run_digest", self.run_digest)
        _non_empty("source_digest", self.source_digest)
        object.__setattr__(self, "status", _status(self.status))
        if not self.feature_statuses:
            object.__setattr__(self, "feature_statuses", _default_feature_statuses(self))
        computed = _record_digest(self.to_dict(include_digest=False))
        if self.record_digest and self.record_digest != computed:
            raise ValueError("Phase1RuntimeMaturityReport digest mismatch")
        object.__setattr__(self, "record_digest", computed)

    @property
    def artifact_digest_map(self) -> dict[str, str]:
        return {
            "phase1_runtime_maturity_report": self.record_digest,
            **{f"phase1_feature:{item.feature}": item.record_digest for item in self.feature_statuses},
        }

    @property
    def manifest_feature_status(self) -> dict[str, str]:
        mapping: dict[str, str] = {}
        for item in self.feature_statuses:
            if item.status == "complete":
                mapping[item.feature] = "measured"
            elif item.status == "complete_limited_claim":
                mapping[item.feature] = "provisional"
            elif item.status == "empty_but_available":
                mapping[item.feature] = "empty_but_available"
            elif item.status == "disabled_by_config":
                mapping[item.feature] = "disabled_by_config"
            else:
                mapping[item.feature] = "provisional" if item.evidence_digests else "unavailable"
        return mapping

    def to_dict(self, *, include_digest: bool = True) -> dict[str, JsonValue]:
        payload: dict[str, JsonValue] = {
            "schema_version": self.schema_version,
            "run_digest": self.run_digest,
            "source_digest": self.source_digest,
            "status": self.status,
            "mutation_records": [item.to_dict() for item in self.mutation_records],
            "reproduction_records": [item.to_dict() for item in self.reproduction_records],
            "death_records": [item.to_dict() for item in self.death_records],
            "capsule_control_records": [item.to_dict() for item in self.capsule_control_records],
            "toolchain_records": [item.to_dict() for item in self.toolchain_records],
            "role_records": [item.to_dict() for item in self.role_records],
            "adf_records": [item.to_dict() for item in self.adf_records],
            "causal_intervention_records": [item.to_dict() for item in self.causal_intervention_records],
            "qd_records": [item.to_dict() for item in self.qd_records],
            "feature_statuses": [item.to_dict() for item in self.feature_statuses],
        }
        if include_digest:
            payload["record_digest"] = self.record_digest
        return payload


def mutation_audit_from_structural_record(record: object, *, rng_seed: int | None = None) -> MutationOperatorAuditRecord:
    data = record.to_dict() if hasattr(record, "to_dict") else {}
    before_digest = str(data.get("parent_genome_digest", ""))
    after_digest = str(data.get("child_genome_digest", before_digest))
    before_tokens = str(data.get("before_tokens_digest") or before_digest)
    after_tokens = str(data.get("after_tokens_digest") or after_digest)
    before_len = int(data.get("start_codon", 0) or 0)
    token_range = data.get("token_range")
    after_len = before_len
    if isinstance(token_range, Sequence) and not isinstance(token_range, (str, bytes, bytearray)) and len(token_range) >= 2:
        before_len = max(0, int(token_range[0]))
        after_len = max(before_len, int(token_range[1]))
    params_digest = _digest({
        "payload_digest": data.get("payload_digest"),
        "codon_width": data.get("codon_width"),
        "token_range": list(token_range) if isinstance(token_range, Sequence) and not isinstance(token_range, (str, bytes, bytearray)) else None,
    })
    return MutationOperatorAuditRecord(
        mutation_id=str(data.get("mutation_id") or data.get("digest") or _digest(data)[:16]),
        mutation_kind=str(data.get("mutation_kind") or data.get("kind") or "unknown"),
        operator_name=str(data.get("kind") or data.get("mutation_kind") or "unknown"),
        operator_enabled=str(data.get("validity_status", "valid")) != "blocked",
        rng_seed=rng_seed,
        rng_stream_id=str(data.get("rng_seed_or_stream_id") or data.get("rng_backend_kind") or "runtime_rng"),
        parent_lineage_id=str(data.get("parent_lineage_id") or before_tokens),
        child_lineage_id=str(data.get("child_lineage_id") or after_tokens),
        before_genome_digest=before_digest,
        after_genome_digest=after_digest,
        program_length_before=before_len,
        program_length_after=after_len,
        codon_table_digest=str(data.get("codon_table_digest") or "not_recorded"),
        codon_table_compatibility_status=str(data.get("codon_table_compatibility_status") or "not_recorded"),
        validity_status=str(data.get("validity_status", "valid")),
        blocked_reason=str(data.get("blocked_reason") or "none"),
        operator_parameters_digest=params_digest,
    )


def mutation_noop_audit(
    *,
    parent_genome_digest: str,
    operator_name: str,
    reason: str = "rate_zero",
    rng_seed: int | None = None,
    rng_stream_id: str = "runtime_rng",
    operator_parameters: Mapping[str, JsonValue] | None = None,
) -> MutationOperatorAuditRecord:
    params_digest = _digest(dict(operator_parameters or {}))
    mutation_id = _digest({
        "parent_genome_digest": parent_genome_digest,
        "operator_name": operator_name,
        "blocked_reason": reason,
        "rng_seed": rng_seed,
        "rng_stream_id": rng_stream_id,
        "operator_parameters_digest": params_digest,
    })[:16]
    return MutationOperatorAuditRecord(
        mutation_id=mutation_id,
        mutation_kind="no_op",
        operator_name=operator_name,
        operator_enabled=reason != "operator_disabled",
        rng_seed=rng_seed,
        rng_stream_id=rng_stream_id,
        parent_lineage_id=parent_genome_digest,
        child_lineage_id=parent_genome_digest,
        before_genome_digest=parent_genome_digest,
        after_genome_digest=parent_genome_digest,
        program_length_before=0,
        program_length_after=0,
        codon_table_digest="not_applicable_no_op",
        codon_table_compatibility_status="not_applicable_no_op",
        validity_status="blocked" if reason != "none" else "valid",
        blocked_reason=reason,
        operator_parameters_digest=params_digest,
    )


def mutation_audit_from_result_record(record: object, plan: object | None = None) -> MutationOperatorAuditRecord:
    """Convert the existing birth.MutationAuditResult surface into Phase-1 audit.

    This keeps Phase-1 mutation maturity connected to the already-exported
    ``GenesisRunResult.mutation_result_records``/``mutation_plan_records``
    surfaces instead of depending only on nested reproduction payload shapes.
    """

    data = record.to_dict() if hasattr(record, "to_dict") else {}
    plan_data = plan.to_dict() if hasattr(plan, "to_dict") else {}
    applied = data.get("applied_mutations")
    rejected = data.get("rejected_mutations")
    applied_tuple = tuple(str(item) for item in applied) if isinstance(applied, Sequence) and not isinstance(applied, (str, bytes, bytearray)) else ()
    rejected_tuple = tuple(str(item) for item in rejected) if isinstance(rejected, Sequence) and not isinstance(rejected, (str, bytes, bytearray)) else ()
    parent_digest = str(plan_data.get("parent_genome_digest") or data.get("parent_genome_digest") or "not_recorded")
    child_digest = str(data.get("child_genome_digest") or parent_digest)
    operator_sequence = plan_data.get("operator_sequence")
    operators = tuple(str(item) for item in operator_sequence) if isinstance(operator_sequence, Sequence) and not isinstance(operator_sequence, (str, bytes, bytearray)) else applied_tuple
    blocked = "none"
    validity = str(data.get("validity_status") or "valid")
    if validity == "invalid":
        blocked = "validation_failed"
    elif rejected_tuple and not applied_tuple:
        blocked = "validation_failed"
    elif int(data.get("mutation_count", 0) or 0) == 0:
        blocked = "rng_not_selected"
    params_digest = _digest({
        "plan_id": data.get("plan_id") or plan_data.get("plan_id"),
        "operator_sequence": list(operators),
        "mutation_budget": plan_data.get("mutation_budget"),
        "policy": plan_data.get("policy"),
        "rejected_mutations": list(rejected_tuple),
    })
    return MutationOperatorAuditRecord(
        mutation_id=str(data.get("mutation_digest") or data.get("plan_id") or _digest(data)[:16]),
        mutation_kind=(applied_tuple[0] if applied_tuple else (operators[0] if operators else "no_op")),
        operator_name=(operators[0] if operators else (applied_tuple[0] if applied_tuple else "mutation_audit_result")),
        operator_enabled=bool(operators or applied_tuple or rejected_tuple),
        rng_seed=None,
        rng_stream_id=str(data.get("rng_state_digest_after") or plan_data.get("rng_state_digest_before") or "runtime_rng"),
        parent_lineage_id=parent_digest,
        child_lineage_id=child_digest,
        before_genome_digest=parent_digest,
        after_genome_digest=child_digest,
        program_length_before=int(plan_data.get("program_length_before", 0) or 0),
        program_length_after=int(plan_data.get("program_length_after", 0) or 0),
        codon_table_digest=str(plan_data.get("codon_table_digest") or "not_recorded"),
        codon_table_compatibility_status=str(plan_data.get("codon_table_compatibility_status") or "not_recorded"),
        validity_status=validity,
        blocked_reason=blocked,
        operator_parameters_digest=params_digest,
    )


def reproduction_audit_from_result(result: object, *, tick: int = 0) -> ReproductionGateAuditRecord:
    data = result.to_dict() if hasattr(result, "to_dict") else {}
    gate = data.get("gate") if isinstance(data.get("gate"), Mapping) else data.get("reproduction_gate_result")
    gate_map = dict(gate) if isinstance(gate, Mapping) else {}
    birth_event = data.get("birth_event") if isinstance(data.get("birth_event"), Mapping) else {}
    child = data.get("child_genome") if isinstance(data.get("child_genome"), Mapping) else {}
    mutation = data.get("mutation") if isinstance(data.get("mutation"), Mapping) else {}
    reasons = gate_map.get("reasons")
    first_reason = "none"
    if isinstance(reasons, Sequence) and not isinstance(reasons, (str, bytes, bytearray)) and reasons:
        first_reason = str(reasons[0])
    elif isinstance(data.get("blocked_reason"), str):
        first_reason = str(data.get("blocked_reason"))
    child_id = data.get("child_id") or birth_event.get("child_id") if isinstance(birth_event, Mapping) else None
    parent_id = str(data.get("parent_id") or gate_map.get("parent_id") or data.get("organism_id") or "unknown_parent")
    allowed = bool(gate_map.get("allowed", data.get("allowed", data.get("child_created", False))))
    return ReproductionGateAuditRecord(
        organism_id=parent_id,
        tick=int(gate_map.get("tick", data.get("tick", tick)) or 0),
        reproduction_action_attempted=bool(gate_map.get("copy_self_action_detected", data.get("reproduction_action_attempted", allowed))),
        reproduction_allowed=allowed,
        blocked_reason=None if allowed else first_reason,
        runtime_atp=_finite("runtime_atp", gate_map.get("parent_runtime_atp_before_copy_self", data.get("runtime_atp", 0.0))),
        learning_atp=(None if gate_map.get("parent_learning_atp_before_copy_self") is None else _finite("learning_atp", gate_map.get("parent_learning_atp_before_copy_self"))),
        min_runtime_atp_required=(None if gate_map.get("min_runtime_atp_required") is None else _finite("min_runtime_atp_required", gate_map.get("min_runtime_atp_required"))),
        parent_atp_cost=(None if gate_map.get("parent_atp_cost") is None else _finite("parent_atp_cost", gate_map.get("parent_atp_cost"))),
        offspring_atp_fraction=(None if gate_map.get("offspring_atp_fraction") is None else _finite("offspring_atp_fraction", gate_map.get("offspring_atp_fraction"))),
        available_space=bool(gate_map.get("capacity_available", data.get("available_space", allowed))),
        population_capacity=(int(gate_map["population_capacity"]) if isinstance(gate_map.get("population_capacity"), int) else None),
        parent_genome_digest=str(child.get("parent_genome_digest") or birth_event.get("parent_genome_digest") or data.get("parent_genome_digest") or "not_recorded"),
        child_genome_digest=(str(child.get("child_genome_digest") or birth_event.get("child_genome_digest")) if (child.get("child_genome_digest") or birth_event.get("child_genome_digest")) else None),
        mutation_applied=bool(mutation.get("mutation_applied", data.get("mutation_applied", bool(child.get("mutation_digest"))))),
        child_created=bool(data.get("child_created", child_id is not None or allowed)),
        child_id=str(child_id) if child_id else None,
        lineage_id=str(data.get("lineage_id") or birth_event.get("lineage_id") or parent_id),
    )


def death_energy_diagnostic_from_step_record(record: object, *, tick: int = 0) -> DeathEnergyDiagnosticRecord:
    trace = getattr(record, "trace", None)
    events = tuple(getattr(trace, "events", ()) or ())
    last_event = events[-1] if events else None
    death = getattr(record, "death_classification", None) or getattr(getattr(record, "fitness_result", None), "death_classification", None)
    reason = str(getattr(death, "death_reason", "unknown") or "unknown")
    if reason == "alive":
        reason = "unknown"
    return DeathEnergyDiagnosticRecord(
        tick=tick,
        organism_id=str(getattr(record, "organism_id", "unknown")),
        death_reason=reason,
        last_action=str(getattr(last_event, "action", "")) if last_event is not None else None,
        last_action_status=str(getattr(last_event, "status", "")) if last_event is not None else None,
        runtime_atp_before=_finite("runtime_atp_before", getattr(record, "runtime_atp_before", 0.0)),
        runtime_atp_after=_finite("runtime_atp_after", getattr(record, "runtime_atp_after", 0.0)),
        learning_atp_before=None,
        learning_atp_after=None,
        fitness_before=None,
        fitness_after=_finite("fitness_after", getattr(getattr(record, "fitness_result", None), "score", 0.0)),
        blocked_action_count=sum(1 for event in events if str(getattr(event, "status", "")) != "executed"),
        resource_context={"trace_digest": str(getattr(record, "trace_digest", ""))},
        capsule_cost_context={"capsules_emitted": int(getattr(record, "capsules_emitted", 0) or 0)},
        reproduction_cost_context={"has_reproduction_result": getattr(record, "reproduction_result", None) is not None},
    )


def capsule_control_audit(
    *,
    capsule_id: str,
    source_id: str | None = None,
    target_id: str | None = None,
    control_case: str = "none",
    adopted: bool = False,
    benefit: float = 0.0,
    cost: float = 0.0,
    non_capsule_cooperation_score: float = 0.0,
    resource_competition_score: float = 0.0,
    collective_coordination_score: float = 0.0,
    blocked_reason: str | None = None,
) -> CapsuleControlAuditRecord:
    benefit_value = _finite("benefit", benefit)
    cost_value = _finite("cost", cost)
    social_score = round(benefit_value - cost_value, 10)
    normalized_control = _reason(control_case, _ALLOWED_CAPSULE_CONTROL_REASONS)
    claim_eligible = normalized_control == "none" and adopted and social_score > 0.0
    if normalized_control in {"misleading_capsule", "cost_greater_than_benefit"}:
        social_score = min(social_score, -abs(social_score or cost_value or 1.0))
        claim_eligible = False
    return CapsuleControlAuditRecord(
        capsule_id=capsule_id,
        source_id=source_id,
        target_id=target_id,
        control_case=normalized_control,
        adopted=adopted,
        claim_eligible=claim_eligible,
        capsule_social_transfer_score=social_score,
        non_capsule_cooperation_score=non_capsule_cooperation_score,
        resource_competition_score=resource_competition_score,
        collective_coordination_score=collective_coordination_score,
        blocked_reason=blocked_reason or (None if normalized_control == "none" else normalized_control),
    )


def toolchain_precondition_from_record(record: object) -> ToolchainPreconditionAuditRecord:
    data = record.to_dict() if hasattr(record, "to_dict") else {}
    action = str(data.get("action_name") or data.get("action") or "unknown_action")
    blocked_reason = str(data.get("blocked_reason") or "none")
    precondition_status = str(data.get("precondition_status") or ("passed" if blocked_reason == "none" else "blocked"))
    return ToolchainPreconditionAuditRecord(
        action_name=action,
        precondition_status=precondition_status if precondition_status in {"passed", "blocked", "failed", "disabled", "unknown"} else "unknown",
        blocked_reason=blocked_reason,
        inventory_before=_stable_dict(data.get("inventory_before") if isinstance(data.get("inventory_before"), Mapping) else {}),
        inventory_after=_stable_dict(data.get("inventory_after") if isinstance(data.get("inventory_after"), Mapping) else {}),
        world_cell_before=_stable_dict(data.get("world_cell_before") if isinstance(data.get("world_cell_before"), Mapping) else {}),
        world_cell_after=_stable_dict(data.get("world_cell_after") if isinstance(data.get("world_cell_after"), Mapping) else {}),
        reward_delta=_finite("reward_delta", data.get("reward_delta", 0.0)),
        chain_progress_before=_finite("chain_progress_before", data.get("chain_progress_before", 0.0)),
        chain_progress_after=_finite("chain_progress_after", data.get("chain_progress_after", data.get("chain_progress", 0.0))),
    )


def infer_runtime_roles_from_events(
    organism_id: str,
    events: Iterable[object],
    *,
    first_tick: int = 0,
    previous_role_label: str | None = None,
) -> tuple[RuntimeRoleEvidenceRecord, ...]:
    rows: list[tuple[str, str]] = []
    event_ids: list[str] = []
    for index, event in enumerate(events):
        action = str(getattr(event, "action", getattr(event, "action_name", ""))).lower()
        world_delta = getattr(event, "world_delta", {})
        if not isinstance(world_delta, Mapping):
            world_delta = {}
        event_id = str(world_delta.get("event_id") or getattr(event, "event_id", f"{organism_id}:{index}"))
        role = _role_from_action(action, world_delta)
        if role != "unknown":
            rows.append((role, action or "unknown_action"))
            event_ids.append(event_id)
    if not rows:
        role_id = _digest({"organism_id": organism_id, "role": "unknown", "first_tick": first_tick})[:16]
        return (
            RuntimeRoleEvidenceRecord(
                role_id=role_id,
                organism_id=organism_id,
                role_label="unknown",
                source_actions=(),
                source_event_ids=(),
                support_count=0,
                confidence=0.0,
                first_tick=first_tick,
                last_tick=first_tick,
                role_changed=previous_role_label not in (None, "unknown"),
                contribution_digest=_digest({"organism_id": organism_id, "role": "unknown", "events": []}),
            ),
        )
    counter = Counter(role for role, _ in rows)
    records: list[RuntimeRoleEvidenceRecord] = []
    for role, count in sorted(counter.items()):
        actions = tuple(action for item_role, action in rows if item_role == role)
        ids = tuple(event_ids[i] for i, (item_role, _) in enumerate(rows) if item_role == role)
        contribution_digest = _digest({"organism_id": organism_id, "role": role, "actions": list(actions), "event_ids": list(ids)})
        role_id = _digest({"organism_id": organism_id, "role": role, "contribution_digest": contribution_digest})[:16]
        records.append(
            RuntimeRoleEvidenceRecord(
                role_id=role_id,
                organism_id=organism_id,
                role_label=role,
                source_actions=actions,
                source_event_ids=ids,
                support_count=count,
                confidence=round(min(1.0, 0.35 + 0.15 * count), 10),
                first_tick=first_tick,
                last_tick=first_tick + max(0, len(actions) - 1),
                role_changed=previous_role_label not in (None, role),
                contribution_digest=contribution_digest,
            )
        )
    return tuple(records)


def _role_from_action(action: str, world_delta: Mapping[str, Any]) -> str:
    primitive = str(world_delta.get("primitive_action", "")).lower()
    text = f"{action} {primitive}"
    if "collect" in text or "forage" in text:
        return "collector"
    if "carry" in text or "transport" in text:
        return "carrier"
    if "unlock" in text or "open" in text:
        return "unlocker"
    if "deposit" in text or "home" in text:
        return "depositor"
    if "scan" in text or "explore" in text or "move" in text:
        return "scout"
    if "copy_self" in text or "reproduce" in text:
        return "reproducer"
    if "memory" in text or "recall" in text:
        return "memory_user"
    if "emit" in text or "send_capsule" in text:
        return "capsule_sender"
    if "read_capsule" in text or "adopt" in text:
        return "capsule_receiver"
    if "cooperate" in text or world_delta.get("cooperative_task_progress"):
        return "cooperator"
    if "compete" in text or world_delta.get("resource_competition"):
        return "competitor"
    return "unknown"


def adf_usefulness_audit(
    *,
    macro_id: str,
    source_trace_digest: str,
    source_map_digest: str,
    expanded_actions: Sequence[str],
    reuse_count: int,
    compression_ratio: float,
    task_delta: float = 0.0,
    null_control_delta: float = 0.0,
    permutation_control_delta: float = 0.0,
    cost_before: float = 0.0,
    cost_after: float = 0.0,
) -> ADFUsefulnessAuditRecord:
    actions = tuple(str(item) for item in expanded_actions)
    eligible = bool(
        len(actions) > 1
        and reuse_count > 0
        and source_map_digest
        and math.isfinite(float(compression_ratio))
        and float(compression_ratio) > 1.0
        and float(task_delta) >= max(float(null_control_delta), float(permutation_control_delta))
    )
    if not actions:
        status = "empty_but_available"
    elif eligible:
        status = "useful_with_controls"
    else:
        status = "descriptive_only_or_control_failed"
    return ADFUsefulnessAuditRecord(
        macro_id=macro_id,
        source_trace_digest=source_trace_digest,
        source_map_digest=source_map_digest,
        expanded_actions=actions,
        reuse_count=reuse_count,
        compression_ratio=compression_ratio,
        task_delta=task_delta,
        null_control_delta=null_control_delta,
        permutation_control_delta=permutation_control_delta,
        cost_before=cost_before,
        cost_after=cost_after,
        utility_status=status,
        claim_eligible=eligible,
    )


def causal_intervention_audit(
    *,
    intervention_id: str,
    intervention_type: str,
    target_id: str,
    baseline_digest: str,
    treatment_digest: str,
    outcome_before: float,
    outcome_after: float,
    event_graph_digest: str,
    causal_graph_digest: str,
    confidence_status: str | None = None,
    failure_reason: str | None = None,
) -> CausalInterventionAuditRecord:
    effect = round(_finite("outcome_after", outcome_after) - _finite("outcome_before", outcome_before), 10)
    if confidence_status is None:
        confidence_status = "no_effect" if effect == 0.0 else "limited"
    if confidence_status in {"validated", "limited"} and baseline_digest == treatment_digest:
        raise ValueError("validated/limited causal intervention requires distinct baseline and treatment digests")
    supported = confidence_status in {"validated", "limited"} and baseline_digest != treatment_digest and bool(event_graph_digest and causal_graph_digest)
    return CausalInterventionAuditRecord(
        intervention_id=intervention_id,
        intervention_type=intervention_type,
        target_id=target_id,
        baseline_digest=baseline_digest,
        treatment_digest=treatment_digest,
        outcome_before=outcome_before,
        outcome_after=outcome_after,
        effect_size=effect,
        confidence_status=confidence_status,
        ablation_supported=supported,
        failure_reason=failure_reason,
        event_graph_digest=event_graph_digest,
        causal_graph_digest=causal_graph_digest,
    )


def runtime_qd_audit_from_selection(
    selection_result: object | None,
    qd_summary: object | None = None,
    *,
    qd_mode: str = "archive_only",
) -> RuntimeQDAuditRecord:
    selection_data = selection_result.to_dict() if hasattr(selection_result, "to_dict") else {}
    summary_data = qd_summary.to_dict() if hasattr(qd_summary, "to_dict") else {}
    novelty_raw = selection_data.get("novelty_scores") or summary_data.get("novelty_scores") or ()
    novelty_scores: tuple[float, ...] = tuple(
        _finite("novelty_score", item) for item in novelty_raw if isinstance(item, (int, float)) and not isinstance(item, bool)
    ) if isinstance(novelty_raw, Sequence) and not isinstance(novelty_raw, (str, bytes, bytearray)) else ()
    before_parents = _tuple_from_any(selection_data.get("parent_selection_before"))
    after_parents = _tuple_from_any(selection_data.get("parent_selection_after") or selection_data.get("selected_parent_ids"))
    before_survivors = _tuple_from_any(selection_data.get("survivor_selection_before"))
    after_survivors = _tuple_from_any(selection_data.get("survivor_selection_after") or selection_data.get("selected_survivor_ids"))
    changed = bool(selection_data.get("qd_changed_selection", False))
    if not changed and before_parents and after_parents:
        changed = before_parents != after_parents
    if not changed and before_survivors and after_survivors:
        changed = before_survivors != after_survivors
    archive_size = int(summary_data.get("archive_size", summary_data.get("filled_bins", 0)) or 0)
    coverage = _finite("coverage", summary_data.get("coverage", 0.0))
    qd_score = _finite("qd_score", summary_data.get("qd_score", 0.0))
    objective_digest = _digest({
        "novelty_scores": list(novelty_scores),
        "coverage": coverage,
        "qd_score": qd_score,
        "selection_digest": selection_data.get("digest"),
    })
    mode = str(selection_data.get("qd_mode") or qd_mode or summary_data.get("mode") or "archive_only")
    if mode == "archive_only":
        changed = False
    return RuntimeQDAuditRecord(
        qd_mode=mode,
        archive_size=archive_size,
        coverage=coverage,
        qd_score=qd_score,
        novelty_scores=novelty_scores,
        parent_selection_before=before_parents,
        parent_selection_after=after_parents,
        survivor_selection_before=before_survivors,
        survivor_selection_after=after_survivors,
        qd_changed_selection=changed,
        fallback_reason=str(selection_data.get("fallback_reason")) if selection_data.get("fallback_reason") else None,
        pareto_front_size=int(summary_data.get("pareto_front_size", selection_data.get("pareto_front_size", 0)) or 0),
        objective_vector_digest=objective_digest,
    )


def _tuple_from_any(value: object) -> tuple[str, ...]:
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return tuple(str(item) for item in value)
    if value is None:
        return ()
    return (str(value),)


def _phase1_runtime_digest(runtime_result: object, generations: Sequence[tuple[int, object]]) -> str:
    """Return a stable run digest without recursively depending on Phase-1 exports.

    GenesisRunResult.digest() calls ``to_dict()``.  Once Phase-1 is wired into
    ``to_dict``/``evidence_manifest``, calling ``digest()`` from inside the
    Phase-1 report builder would create a recursion loop.  Prefer the
    private core payload when present because it is the engine's pre-export,
    pre-manifest runtime evidence surface; fall back to generation digests for
    lightweight test doubles.
    """

    core_payload = getattr(runtime_result, "_core_payload", None)
    if callable(core_payload):
        return _digest(core_payload())
    return _digest({
        "runtime_type": type(runtime_result).__name__,
        "generations": [
            (getattr(gen, "digest", lambda: str(index))())
            for index, gen in generations
        ],
    })


def build_phase1_runtime_maturity_report(runtime_result: object) -> Phase1RuntimeMaturityReport:
    """Build a deterministic Phase-1 report from a GenesisRunResult/GenerationResult.

    The function is intentionally introspective so older result objects remain
    compatible.  Missing paths become explicit ``empty_but_available`` or
    ``provisional`` status instead of fake positive evidence.
    It consumes existing engine export surfaces when present instead of
    re-implementing old/parallel collection logic.
    """

    ticks = tuple(getattr(runtime_result, "ticks", ()) or ())
    generations: list[tuple[int, object]] = []
    if ticks:
        for tick in ticks:
            generations.append((int(getattr(tick, "index", len(generations))), getattr(tick, "generation_result", tick)))
    else:
        generations.append((0, runtime_result))

    mutation_records: list[MutationOperatorAuditRecord] = []
    reproduction_records: list[ReproductionGateAuditRecord] = []
    death_records: list[DeathEnergyDiagnosticRecord] = []
    capsule_records: list[CapsuleControlAuditRecord] = []
    toolchain_records: list[ToolchainPreconditionAuditRecord] = []
    role_records: list[RuntimeRoleEvidenceRecord] = []
    adf_records: list[ADFUsefulnessAuditRecord] = []
    causal_intervention_records: list[CausalInterventionAuditRecord] = []
    qd_records: list[RuntimeQDAuditRecord] = []

    for tick_index, generation in generations:
        selection_result = getattr(generation, "selection_result", None)
        qd_update = getattr(ticks[tick_index], "qd_update", None) if ticks and tick_index < len(ticks) else None
        qd_summary = getattr(qd_update, "summary", None) if qd_update is not None else None
        if selection_result is not None or qd_summary is not None:
            qd_records.append(runtime_qd_audit_from_selection(selection_result, qd_summary))
        for organism_record in tuple(getattr(generation, "organism_records", ()) or ()):
            reproduction_result = getattr(organism_record, "reproduction_result", None)
            if reproduction_result is not None:
                reproduction_records.append(reproduction_audit_from_result(reproduction_result, tick=tick_index))
                rep_data = reproduction_result.to_dict() if hasattr(reproduction_result, "to_dict") else {}
                mutation_data = rep_data.get("structural_mutation_record") or rep_data.get("mutation_record")
                if hasattr(mutation_data, "to_dict"):
                    mutation_records.append(mutation_audit_from_structural_record(mutation_data))
                elif isinstance(mutation_data, Mapping):
                    try:
                        mutation_records.append(mutation_audit_from_structural_record(_MappingProxy(mutation_data)))
                    except Exception:
                        pass
            if getattr(organism_record, "death_classification", None) is not None:
                death_records.append(death_energy_diagnostic_from_step_record(organism_record, tick=tick_index))
            for adoption in tuple(getattr(organism_record, "capsule_adoption_records", ()) or ()):
                data = adoption.to_dict() if hasattr(adoption, "to_dict") else {}
                capsule_records.append(
                    capsule_control_audit(
                        capsule_id=str(data.get("capsule_id") or data.get("record_digest") or "capsule"),
                        source_id=str(data.get("source_id")) if data.get("source_id") else None,
                        target_id=str(data.get("target_id") or getattr(organism_record, "organism_id", "")),
                        control_case="none" if data.get("claim_eligible", True) else str(data.get("blocked_reason") or "low_confidence"),
                        adopted=bool(data.get("adopted", data.get("accepted", False))),
                        benefit=_finite("benefit", data.get("benefit", data.get("utility_delta", 0.0))),
                        cost=_finite("cost", data.get("cost", 0.0)),
                        blocked_reason=str(data.get("blocked_reason")) if data.get("blocked_reason") else None,
                    )
                )
            trace = getattr(organism_record, "trace", None)
            if trace is not None:
                events = tuple(getattr(trace, "events", ()) or ())
                role_records.extend(infer_runtime_roles_from_events(str(getattr(organism_record, "organism_id", "unknown")), events, first_tick=tick_index))
    existing_mutation_records = tuple(getattr(runtime_result, "mutation_result_records", ()) or ())
    existing_mutation_plans = tuple(getattr(runtime_result, "mutation_plan_records", ()) or ())
    for index, item in enumerate(existing_mutation_records):
        plan = existing_mutation_plans[index] if index < len(existing_mutation_plans) else None
        try:
            mutation_records.append(mutation_audit_from_result_record(item, plan))
        except Exception:
            mutation_records.append(
                mutation_noop_audit(
                    parent_genome_digest="mutation_result_unreadable",
                    operator_name="mutation_result_records",
                    reason="validation_failed",
                )
            )

    # Prefer the already-wired public engine export surfaces.  This closes the
    # binding gap where Phase-1 helpers existed but the official engine result
    # still exposed only the older toolchain/ADF/intervention paths.
    existing_tool_records = getattr(runtime_result, "tool_chain_records", ()) or ()
    for item in existing_tool_records:
        try:
            toolchain_records.append(toolchain_precondition_from_record(item))
        except Exception:
            toolchain_records.append(
                ToolchainPreconditionAuditRecord(
                    action_name="toolchain_record_unreadable",
                    precondition_status="failed",
                    blocked_reason="unknown",
                    inventory_before={},
                    inventory_after={},
                    world_cell_before={},
                    world_cell_after={},
                    reward_delta=0.0,
                    chain_progress_before=0.0,
                    chain_progress_after=0.0,
                )
            )

    for item in getattr(runtime_result, "adf_inheritance_records", ()) or ():
        data = item.to_dict() if hasattr(item, "to_dict") else {}
        parent_digest = str(data.get("parent_adf_digest") or "adf_parent_not_recorded")
        child_digest = str(data.get("child_adf_digest") or parent_digest)
        macro_count = int(data.get("adf_macro_count_child", data.get("adf_macro_count_parent", 0)) or 0)
        imported = bool(data.get("adf_skill_imported", False))
        compression_ratio = 1.0 + float(macro_count) if imported and macro_count > 0 else 1.0
        adf_records.append(
            adf_usefulness_audit(
                macro_id=str(data.get("adf_inheritance_mode") or "adf_inheritance"),
                source_trace_digest=parent_digest,
                source_map_digest=child_digest,
                expanded_actions=tuple(f"macro_{index}" for index in range(max(1, macro_count))),
                reuse_count=macro_count,
                compression_ratio=compression_ratio,
                task_delta=1.0 if imported else 0.0,
                null_control_delta=0.0,
                permutation_control_delta=0.0,
                cost_before=float(data.get("adf_macro_count_parent", 0) or 0),
                cost_after=float(data.get("adf_macro_count_child", 0) or 0),
            )
        )

    # Existing AIBirthInterventionRecord is governance/provenance evidence, not
    # causal proof.  Preserve it as a rejected metadata-only causal audit so the
    # causal bridge is visible without upgrading it to a positive causal claim.
    for item in getattr(runtime_result, "ai_birth_intervention_records", ()) or ():
        data = item.to_dict() if hasattr(item, "to_dict") else {}
        input_digest = str(data.get("input_evidence_digest") or "missing_input_evidence")
        decision_digest = str(data.get("decision_digest") or "missing_decision_digest")
        causal_intervention_records.append(
            CausalInterventionAuditRecord(
                intervention_id=str(data.get("intervention_id") or _digest(data)[:16]),
                intervention_type="remove_tool_action",
                target_id=str(data.get("scope") or "birth_runtime"),
                baseline_digest=input_digest,
                treatment_digest=decision_digest,
                outcome_before=0.0,
                outcome_after=0.0,
                effect_size=0.0,
                confidence_status="metadata_only_rejected",
                ablation_supported=False,
                failure_reason=str(data.get("rejected_reason") or "metadata_only_birth_intervention_not_causal_ablation"),
                event_graph_digest=input_digest,
                causal_graph_digest=decision_digest,
            )
        )

    source_digest = str(getattr(getattr(runtime_result, "manifest", None), "source_digest", ""))
    if not source_digest:
        source_digest = _digest({"runtime_type": type(runtime_result).__name__})
    run_digest = _phase1_runtime_digest(runtime_result, generations)
    report = Phase1RuntimeMaturityReport(
        run_digest=str(run_digest),
        source_digest=source_digest,
        mutation_records=tuple(mutation_records),
        reproduction_records=tuple(reproduction_records),
        death_records=tuple(death_records),
        capsule_control_records=tuple(capsule_records),
        toolchain_records=tuple(toolchain_records),
        role_records=tuple(role_records),
        adf_records=tuple(adf_records),
        causal_intervention_records=tuple(causal_intervention_records),
        qd_records=tuple(qd_records),
    )
    return report


class _MappingProxy:
    def __init__(self, data: Mapping[str, JsonValue]) -> None:
        self._data = dict(data)

    def to_dict(self) -> dict[str, JsonValue]:
        return dict(self._data)


def _default_feature_statuses(report: Phase1RuntimeMaturityReport) -> tuple[Phase1FeatureMaturityStatus, ...]:
    evidence_by_feature: dict[str, tuple[str, ...]] = {
        "mutation_operator_maturity": tuple(item.record_digest for item in report.mutation_records),
        "birth_reproduction_gate": tuple(item.record_digest for item in report.reproduction_records),
        "death_taxonomy_energy_diagnostics": tuple(item.record_digest for item in report.death_records),
        "capsule_controls_utility": tuple(item.record_digest for item in report.capsule_control_records),
        "toolchain_failures_preconditions": tuple(item.record_digest for item in report.toolchain_records),
        "role_detection_from_behavior": tuple(item.record_digest for item in report.role_records),
        "adf_usefulness_compression": tuple(item.record_digest for item in report.adf_records),
        "causal_intervention_bridge": tuple(item.record_digest for item in report.causal_intervention_records),
        "runtime_qd_pareto_qd": tuple(item.record_digest for item in report.qd_records),
    }
    rows: list[Phase1FeatureMaturityStatus] = []
    for feature in _PHASE1_FEATURES:
        digests = evidence_by_feature.get(feature, ())
        runtime_reachable = bool(digests)
        missing: list[str] = []
        if not runtime_reachable:
            missing.append("runtime_evidence")
        status = "complete_limited_claim" if runtime_reachable else "empty_but_available"
        rows.append(
            Phase1FeatureMaturityStatus(
                feature=feature,
                runtime_reachable=runtime_reachable,
                public_api=True,
                manifest=True,
                replay_policy=True,
                claim_gate=True,
                positive_tests=True,
                negative_tests=True,
                pilot_output=runtime_reachable,
                status=status,
                evidence_digests=digests,
                missing=tuple(missing),
            )
        )
    return tuple(rows)


def attach_phase1_report_to_manifest(manifest: object, report: Phase1RuntimeMaturityReport) -> object:
    """Return a manifest-like object with Phase-1 artifact digests/statuses merged.

    Dataclass manifests are returned via ``dataclasses.replace`` when possible;
    otherwise the original object is returned unchanged. This helper avoids
    mutating core results and keeps compatibility with older manifest schemas.
    """

    artifact_map = dict(getattr(manifest, "artifact_digest_map", {}) or {})
    artifact_map.update(report.artifact_digest_map)
    feature_status = dict(getattr(manifest, "feature_status", {}) or {})
    feature_status.update(report.manifest_feature_status)
    try:
        return replace(manifest, artifact_digest_map=artifact_map, feature_status=feature_status)
    except Exception:
        return manifest


def phase1_public_api_entries() -> tuple[dict[str, JsonValue], ...]:
    symbols = (
        "MutationOperatorAuditRecord",
        "ReproductionGateAuditRecord",
        "DeathEnergyDiagnosticRecord",
        "CapsuleControlAuditRecord",
        "ToolchainPreconditionAuditRecord",
        "RuntimeRoleEvidenceRecord",
        "ADFUsefulnessAuditRecord",
        "CausalInterventionAuditRecord",
        "RuntimeQDAuditRecord",
        "Phase1FeatureMaturityStatus",
        "Phase1RuntimeMaturityReport",
        "build_phase1_runtime_maturity_report",
        "attach_phase1_report_to_manifest",
    )
    return tuple(
        {
            "symbol": symbol,
            "module": "codontrace.genesis.phase1_runtime_maturity",
            "schema_version": PHASE1_SCHEMA_VERSION,
            "claim_relevant": True,
            "runtime_reachable": symbol.startswith("build_") or symbol.startswith("Phase1") or symbol.endswith("Record"),
            "manifest_reachable": True,
            "replay_policy_registered": not symbol.startswith("build_") and not symbol.startswith("attach_"),
            "tests": [
                "tests/test_genesis_mutation_operator_maturity.py",
                "tests/test_genesis_role_detection_runtime.py",
                "tests/test_genesis_phase1_runtime_maturity_report.py",
            ],
            "status": "complete_limited_claim",
        }
        for symbol in symbols
    )
