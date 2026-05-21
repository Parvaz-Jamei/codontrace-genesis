"""Birth, mutation, inheritance, and intervention primitives for GENESIS.

This module is deliberately library-as-tool: it defines deterministic records,
policies, and small helpers for reproduction evidence. It does not force
organisms to survive, does not improve fitness, and does not make intelligence
claims.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from enum import Enum

from codontrace._types import JsonValue, Position
from codontrace._numeric import finite_float, finite_json_dumps


def _digest(payload: dict[str, JsonValue]) -> str:
    return hashlib.sha256(
        finite_json_dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def _enum_value(value: Enum | str) -> str:
    return value.value if isinstance(value, Enum) else str(value)


def _validate_enum_value(value: str, enum_type: type[Enum], field_name: str) -> None:
    valid = {item.value for item in enum_type}
    if value not in valid:
        raise ValueError(
            f"Invalid {field_name}: {value!r}; expected one of {sorted(valid)!r}."
        )


def _validate_non_negative(value: int | float, field_name: str) -> None:
    finite_float(field_name, value, non_negative=True)


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


_SKILL_VALIDATION_STATUSES = {"not_requested", "rejected", "validated"}
_INHERITANCE_TYPES = {
    "genetic_only",
    "baldwinian_selection_pressure",
    "lamarckian_compressed",
}
_INTERVENTION_EVENTS = {
    "before_birth_gate",
    "before_mutation_plan",
    "after_mutation_plan",
    "before_child_admission",
    "after_birth_event",
}
_PLACEMENT_POLICIES = {"same_cell", "adjacent_free", "blocked_if_no_space"}
_PLACEMENT_RESOLUTION_STAGES = {"gate", "admission", "not_applicable"}


class MutationOperator(str, Enum):
    POINT_FLIP = "point_flip"
    POINT_SUBSTITUTION = "point_substitution"
    INSERT_CODON = "insert_codon"
    DELETE_CODON = "delete_codon"
    DUPLICATE_SEGMENT = "duplicate_segment"
    DELETE_SEGMENT = "delete_segment"
    TRANSPOSE_SEGMENT = "transpose_segment"
    INVERT_SEGMENT = "invert_segment"
    COPY_SEGMENT = "copy_segment"
    RECOMBINE_WITH_CAPSULE = "recombine_with_capsule"
    RECOMBINE_WITH_PARTNER = "recombine_with_partner"
    REPAIR_INVALID_REGION = "repair_invalid_region"
    MACRO_MUTATION = "macro_mutation"
    SEMANTIC_MUTATION = "semantic_mutation"
    NEUTRAL_DRIFT_MUTATION = "neutral_drift_mutation"


class MutationPolicy(str, Enum):
    RANDOM_BASELINE = "random_baseline"
    FITNESS_WEIGHTED = "fitness_weighted"
    NOVELTY_WEIGHTED = "novelty_weighted"
    BEHAVIOR_PRESERVING = "behavior_preserving"
    LEARNING_GUIDED = "learning_guided"
    AI_GUIDED_EXTERNAL = "ai_guided_external"


class InheritancePolicy(str, Enum):
    DARWINIAN_GENETIC_ONLY = "darwinian_genetic_only"
    BALDWINIAN = "baldwinian"
    LAMARCKIAN_COMPRESSED_LEARNING = "lamarckian_compressed_learning"


class SkillInheritanceMode(str, Enum):
    NONE = "none"
    CAPACITY_ONLY = "capacity_only"
    COMPRESSED_SKILL = "compressed_skill"
    GENOME_ASSIMILATED_SKILL = "genome_assimilated_skill"


class ADFInheritanceMode(str, Enum):
    RESET = "reset"
    INHERIT_CAPACITY = "inherit_capacity"
    INHERIT_MACROS = "inherit_macros"
    MUTATE_MACROS = "mutate_macros"
    COMPRESS_SUCCESSFUL_BEHAVIOR_TO_ADF = "compress_successful_behavior_to_adf"


class InterventionScope(str, Enum):
    CHILD_ONLY = "child_only"
    LINEAGE_ONLY = "lineage_only"
    NEXT_GENERATION = "next_generation"
    NEXT_WORLD = "next_world"
    NEW_EXPERIMENT_ONLY = "new_experiment_only"


@dataclass(frozen=True, slots=True)
class BirthIntent:
    organism_id: str
    tick: int
    action: str = "COPY_SELF"
    detected: bool = True
    counts_as_reproduction_attempt: bool = True
    counts_as_blocked_for_reproduction: bool = False
    status: str = "deferred_to_population_lifecycle"
    schema_version: str = "birth_intent_v1"

    def __post_init__(self) -> None:
        _require(bool(self.organism_id), "organism_id is required.")
        _validate_non_negative(self.tick, "tick")
        _require(bool(self.action), "action is required.")
        _require(bool(self.status), "status is required.")

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "schema_version": self.schema_version,
            "organism_id": self.organism_id,
            "tick": self.tick,
            "action": self.action,
            "detected": self.detected,
            "counts_as_reproduction_attempt": self.counts_as_reproduction_attempt,
            "counts_as_blocked_for_reproduction": self.counts_as_blocked_for_reproduction,
            "status": self.status,
        }

    def digest(self) -> str:
        return _digest(self.to_dict())


@dataclass(frozen=True, slots=True)
class BirthRequest:
    request_id: str
    parent_id: str
    tick: int
    parent_genome_digest: str
    policy_digest: str
    intent_digest: str
    schema_version: str = "birth_request_v1"

    def __post_init__(self) -> None:
        _require(bool(self.request_id), "request_id is required.")
        _require(bool(self.parent_id), "parent_id is required.")
        _validate_non_negative(self.tick, "tick")
        _require(bool(self.parent_genome_digest), "parent_genome_digest is required.")
        _require(bool(self.policy_digest), "policy_digest is required.")
        _require(bool(self.intent_digest), "intent_digest is required.")

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "schema_version": self.schema_version,
            "request_id": self.request_id,
            "parent_id": self.parent_id,
            "tick": self.tick,
            "parent_genome_digest": self.parent_genome_digest,
            "policy_digest": self.policy_digest,
            "intent_digest": self.intent_digest,
        }

    def digest(self) -> str:
        return _digest(self.to_dict())


@dataclass(frozen=True, slots=True)
class ReproductionGateResult:
    parent_id: str
    tick: int
    allowed: bool
    reasons: tuple[str, ...]
    parent_alive_before_copy_self: bool
    parent_runtime_atp_before_copy_self: float
    parent_learning_atp_before_copy_self: float | None
    capacity_available: bool
    copy_self_action_detected: bool
    reproduction_enabled: bool
    min_runtime_atp_met: bool
    parent_cost_payable: bool
    offspring_fraction_valid: bool
    min_runtime_atp_required: float | None = None
    parent_atp_cost: float | None = None
    offspring_atp_fraction: float | None = None
    population_capacity: int | None = None
    child_placement_available: bool | None = None
    placement_gate_evaluated: bool = False
    placement_resolution_stage: str = "admission"
    placement_policy: str = "same_cell"
    schema_version: str = "reproduction_gate_result_v1"

    def __post_init__(self) -> None:
        _validate_non_negative(self.tick, "tick")
        _validate_non_negative(
            self.parent_runtime_atp_before_copy_self,
            "parent_runtime_atp_before_copy_self",
        )
        if self.parent_learning_atp_before_copy_self is not None:
            _validate_non_negative(
                self.parent_learning_atp_before_copy_self,
                "parent_learning_atp_before_copy_self",
            )
        for value, name in (
            (self.min_runtime_atp_required, "min_runtime_atp_required"),
            (self.parent_atp_cost, "parent_atp_cost"),
            (self.offspring_atp_fraction, "offspring_atp_fraction"),
        ):
            if value is not None:
                _validate_non_negative(value, name)
        if self.offspring_atp_fraction is not None:
            _require(
                0.0 <= self.offspring_atp_fraction <= 1.0,
                "offspring_atp_fraction must be between 0 and 1.",
            )
        if self.population_capacity is not None:
            _require(self.population_capacity >= 0, "population_capacity must be non-negative.")
        _require(
            self.placement_resolution_stage in _PLACEMENT_RESOLUTION_STAGES,
            f"placement_resolution_stage must be one of {sorted(_PLACEMENT_RESOLUTION_STAGES)!r}.",
        )
        _require(
            self.placement_policy in _PLACEMENT_POLICIES,
            f"placement_policy must be one of {sorted(_PLACEMENT_POLICIES)!r}.",
        )
        if self.allowed:
            _require(not self.reasons, "allowed reproduction gate must not carry block reasons.")
            required_flags = {
                "parent_alive_before_copy_self": self.parent_alive_before_copy_self,
                "capacity_available": self.capacity_available,
                "copy_self_action_detected": self.copy_self_action_detected,
                "reproduction_enabled": self.reproduction_enabled,
                "min_runtime_atp_met": self.min_runtime_atp_met,
                "parent_cost_payable": self.parent_cost_payable,
                "offspring_fraction_valid": self.offspring_fraction_valid,
            }
            missing = tuple(name for name, value in required_flags.items() if not value)
            _require(not missing, f"allowed reproduction gate has failed flags: {missing!r}.")
            _require(
                self.child_placement_available is not None
                or self.placement_resolution_stage == "admission",
                "allowed reproduction gate requires known placement or admission-stage resolution.",
            )
            if self.placement_resolution_stage == "gate":
                _require(
                    self.placement_gate_evaluated,
                    "gate-stage placement requires placement_gate_evaluated=True.",
                )
                _require(
                    self.child_placement_available is not None,
                    "gate-stage placement requires child_placement_available to be known.",
                )
        else:
            _require(self.reasons, "blocked reproduction gate must carry at least one reason.")

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "schema_version": self.schema_version,
            "parent_id": self.parent_id,
            "tick": self.tick,
            "allowed": self.allowed,
            "reasons": list(self.reasons),
            "parent_alive_before_copy_self": self.parent_alive_before_copy_self,
            "parent_runtime_atp_before_copy_self": self.parent_runtime_atp_before_copy_self,
            "parent_learning_atp_before_copy_self": self.parent_learning_atp_before_copy_self,
            "capacity_available": self.capacity_available,
            "copy_self_action_detected": self.copy_self_action_detected,
            "reproduction_enabled": self.reproduction_enabled,
            "min_runtime_atp_met": self.min_runtime_atp_met,
            "parent_cost_payable": self.parent_cost_payable,
            "offspring_fraction_valid": self.offspring_fraction_valid,
            "min_runtime_atp_required": self.min_runtime_atp_required,
            "parent_atp_cost": self.parent_atp_cost,
            "offspring_atp_fraction": self.offspring_atp_fraction,
            "population_capacity": self.population_capacity,
            "child_placement_available": self.child_placement_available,
            "placement_gate_evaluated": self.placement_gate_evaluated,
            "placement_resolution_stage": self.placement_resolution_stage,
            "placement_policy": self.placement_policy,
        }

    def digest(self) -> str:
        return _digest(self.to_dict())


@dataclass(frozen=True, slots=True)
class MutationPlan:
    plan_id: str
    parent_genome_digest: str
    operator_sequence: tuple[str, ...]
    mutation_budget: int
    protected_regions: tuple[str, ...] = ()
    hotspot_regions: tuple[str, ...] = ()
    allowed_codons: tuple[str, ...] = ()
    forbidden_codons: tuple[str, ...] = ()
    expected_effect: str = "variation"
    rng_state_digest_before: str = ""
    controller_digest: str | None = None
    policy: str = MutationPolicy.RANDOM_BASELINE.value
    schema_version: str = "mutation_plan_v1"

    def __post_init__(self) -> None:
        _validate_enum_value(self.policy, MutationPolicy, "policy")
        for operator in self.operator_sequence:
            _validate_enum_value(operator, MutationOperator, "operator_sequence")
        _validate_non_negative(self.mutation_budget, "mutation_budget")
        _require(
            self.mutation_budget >= len(self.operator_sequence),
            "mutation_budget must cover all planned operator classes.",
        )

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "schema_version": self.schema_version,
            "plan_id": self.plan_id,
            "parent_genome_digest": self.parent_genome_digest,
            "operator_sequence": list(self.operator_sequence),
            "mutation_budget": self.mutation_budget,
            "protected_regions": list(self.protected_regions),
            "hotspot_regions": list(self.hotspot_regions),
            "allowed_codons": list(self.allowed_codons),
            "forbidden_codons": list(self.forbidden_codons),
            "expected_effect": self.expected_effect,
            "rng_state_digest_before": self.rng_state_digest_before,
            "controller_digest": self.controller_digest,
            "policy": self.policy,
        }

    def digest(self) -> str:
        return _digest(self.to_dict())


@dataclass(frozen=True, slots=True)
class MutationAuditResult:
    plan_id: str
    child_genome_digest: str
    applied_mutations: tuple[str, ...]
    rejected_mutations: tuple[str, ...] = ()
    mutation_count: int = 0
    mutation_digest: str = ""
    rng_state_digest_after: str = ""
    validity_status: str = "valid"
    repair_applied: bool = False
    schema_version: str = "mutation_result_record_v1"

    def __post_init__(self) -> None:
        _validate_non_negative(self.mutation_count, "mutation_count")
        _require(
            self.mutation_count == len(self.applied_mutations),
            "mutation_count must equal the number of applied_mutations.",
        )
        if self.mutation_count > 0:
            _require(bool(self.mutation_digest), "mutation_digest is required when mutations exist.")
        _require(self.validity_status in {"valid", "invalid", "repaired"}, "invalid validity_status.")

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "schema_version": self.schema_version,
            "plan_id": self.plan_id,
            "child_genome_digest": self.child_genome_digest,
            "applied_mutations": list(self.applied_mutations),
            "rejected_mutations": list(self.rejected_mutations),
            "mutation_count": self.mutation_count,
            "mutation_digest": self.mutation_digest,
            "rng_state_digest_after": self.rng_state_digest_after,
            "validity_status": self.validity_status,
            "repair_applied": self.repair_applied,
        }

    def digest(self) -> str:
        return _digest(self.to_dict())


@dataclass(frozen=True, slots=True)
class ChildGenomeResult:
    child_id: str
    parent_id: str
    parent_genome_digest: str
    child_genome_digest: str
    mutation_digest: str
    mutation_count: int
    genome_bits: str
    validity_status: str = "valid"
    schema_version: str = "child_genome_result_v1"

    def __post_init__(self) -> None:
        _validate_non_negative(self.mutation_count, "mutation_count")
        _require(bool(self.child_id), "child_id is required.")
        _require(bool(self.parent_id), "parent_id is required.")
        _require(bool(self.parent_genome_digest), "parent_genome_digest is required.")
        _require(bool(self.child_genome_digest), "child_genome_digest is required.")
        if self.mutation_count > 0:
            _require(bool(self.mutation_digest), "mutation_digest is required when mutations exist.")
        _require(bool(self.genome_bits), "genome_bits is required.")
        _require(self.validity_status in {"valid", "invalid", "repaired"}, "invalid validity_status.")

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "schema_version": self.schema_version,
            "child_id": self.child_id,
            "parent_id": self.parent_id,
            "parent_genome_digest": self.parent_genome_digest,
            "child_genome_digest": self.child_genome_digest,
            "mutation_digest": self.mutation_digest,
            "mutation_count": self.mutation_count,
            "genome_bits": self.genome_bits,
            "validity_status": self.validity_status,
        }

    def digest(self) -> str:
        return _digest(self.to_dict())


@dataclass(frozen=True, slots=True)
class ChildAdmissionResult:
    child_id: str
    admitted: bool
    placement_cell: Position | None
    blocked_reason: str | None = None
    schema_version: str = "child_admission_result_v1"

    def __post_init__(self) -> None:
        _require(bool(self.child_id), "child_id is required.")
        if self.admitted:
            _require(self.placement_cell is not None, "admitted child requires placement_cell.")
            _require(self.blocked_reason is None, "admitted child must not carry blocked_reason.")
        else:
            _require(self.blocked_reason is not None, "blocked child admission requires blocked_reason.")

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "schema_version": self.schema_version,
            "child_id": self.child_id,
            "admitted": self.admitted,
            "placement_cell": None if self.placement_cell is None else list(self.placement_cell),
            "blocked_reason": self.blocked_reason,
        }

    def digest(self) -> str:
        return _digest(self.to_dict())


@dataclass(frozen=True, slots=True)
class LearningInheritanceRecord:
    parent_id: str
    child_id: str | None
    tick: int
    inheritance_policy: str
    learning_capacity_inherited: bool
    learned_content_inherited: bool
    inheritance_type: str
    source_lifetime_evidence_digest: str | None = None
    compressed_skill_digest: str | None = None
    child_received_skill_digest: str | None = None
    learning_success_score: float | None = None
    learning_efficiency_score: float | None = None
    memory_use_score: float | None = None
    delayed_reward_score: float | None = None
    baldwinian_selection_pressure: bool = False
    schema_version: str = "learning_inheritance_record_v1"

    def __post_init__(self) -> None:
        _validate_enum_value(self.inheritance_policy, InheritancePolicy, "inheritance_policy")
        _require(
            self.inheritance_type in _INHERITANCE_TYPES,
            f"inheritance_type must be one of {sorted(_INHERITANCE_TYPES)!r}.",
        )
        if self.inheritance_policy == InheritancePolicy.DARWINIAN_GENETIC_ONLY.value:
            _require(
                not self.learned_content_inherited,
                "Darwinian genetic-only inheritance cannot inherit learned content.",
            )
            _require(
                self.child_received_skill_digest is None,
                "Darwinian genetic-only inheritance cannot give child skill digest.",
            )
        if self.inheritance_policy == InheritancePolicy.BALDWINIAN.value:
            _require(
                not self.learned_content_inherited,
                "Baldwinian inheritance cannot directly inherit learned content.",
            )
            _require(
                self.baldwinian_selection_pressure,
                "Baldwinian inheritance must mark selection pressure evidence.",
            )
        if not self.learned_content_inherited:
            _require(
                self.child_received_skill_digest is None,
                "non-inherited learning records must not carry child_received_skill_digest.",
            )
        if self.child_received_skill_digest is not None:
            _require(
                self.learned_content_inherited,
                "child_received_skill_digest requires learned_content_inherited=True.",
            )
        if (
            self.inheritance_type != "lamarckian_compressed"
            and self.inheritance_policy
            != InheritancePolicy.LAMARCKIAN_COMPRESSED_LEARNING.value
        ):
            _require(
                self.compressed_skill_digest is None,
                "non-lamarckian inheritance must not carry compressed_skill_digest.",
            )
        if self.learned_content_inherited:
            _require(
                self.inheritance_type == "lamarckian_compressed",
                "learned content inheritance must use lamarckian_compressed type.",
            )
            _require(
                self.inheritance_policy
                == InheritancePolicy.LAMARCKIAN_COMPRESSED_LEARNING.value,
                "learned content inheritance requires lamarckian_compressed_learning policy.",
            )
            _require(
                self.compressed_skill_digest is not None,
                "learned content inheritance requires compressed_skill_digest.",
            )
            _require(
                self.child_received_skill_digest is not None,
                "learned content inheritance requires child_received_skill_digest.",
            )
            _require(
                self.source_lifetime_evidence_digest is not None,
                "learned content inheritance requires source_lifetime_evidence_digest.",
            )

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "schema_version": self.schema_version,
            "parent_id": self.parent_id,
            "child_id": self.child_id,
            "tick": self.tick,
            "inheritance_policy": self.inheritance_policy,
            "learning_capacity_inherited": self.learning_capacity_inherited,
            "learned_content_inherited": self.learned_content_inherited,
            "inheritance_type": self.inheritance_type,
            "source_lifetime_evidence_digest": self.source_lifetime_evidence_digest,
            "compressed_skill_digest": self.compressed_skill_digest,
            "child_received_skill_digest": self.child_received_skill_digest,
            "learning_success_score": self.learning_success_score,
            "learning_efficiency_score": self.learning_efficiency_score,
            "memory_use_score": self.memory_use_score,
            "delayed_reward_score": self.delayed_reward_score,
            "baldwinian_selection_pressure": self.baldwinian_selection_pressure,
        }

    def digest(self) -> str:
        return _digest(self.to_dict())


@dataclass(frozen=True, slots=True)
class SkillCompressionRecord:
    parent_id: str
    child_id: str | None
    tick: int
    mode: str
    successful_behavior_trace_digest: str | None = None
    compressed_skill_digest: str | None = None
    validation_status: str = "not_requested"
    fitness_delta_positive: bool = False
    energy_efficiency_positive: bool = False
    replay_successful: bool = False
    inherited: bool = False
    rejected_reason: str | None = None
    schema_version: str = "skill_compression_record_v1"

    def __post_init__(self) -> None:
        _validate_enum_value(self.mode, SkillInheritanceMode, "mode")
        _require(
            self.validation_status in _SKILL_VALIDATION_STATUSES,
            f"validation_status must be one of {sorted(_SKILL_VALIDATION_STATUSES)!r}.",
        )
        if self.inherited:
            _require(
                self.validation_status == "validated",
                "inherited skill compression requires validation_status='validated'.",
            )
        if self.validation_status == "validated":
            _require(
                self.compressed_skill_digest is not None,
                "validated skill compression requires compressed_skill_digest.",
            )
            _require(
                self.successful_behavior_trace_digest is not None,
                "validated skill compression requires successful_behavior_trace_digest.",
            )
            _require(
                self.fitness_delta_positive,
                "validated skill compression requires fitness_delta_positive=True.",
            )
            _require(
                self.energy_efficiency_positive,
                "validated skill compression requires energy_efficiency_positive=True.",
            )
            _require(
                self.replay_successful,
                "validated skill compression requires replay_successful=True.",
            )
            _require(
                self.rejected_reason is None,
                "validated skill compression must not carry rejected_reason.",
            )
        elif self.validation_status == "rejected":
            _require(not self.inherited, "rejected skill compression cannot be inherited.")
            _require(
                self.rejected_reason is not None,
                "rejected skill compression requires rejected_reason.",
            )
        else:
            _require(not self.inherited, "not_requested skill compression cannot be inherited.")
            _require(
                self.compressed_skill_digest is None,
                "not_requested skill compression must not carry compressed_skill_digest.",
            )
            _require(
                self.successful_behavior_trace_digest is None,
                "not_requested skill compression must not carry successful_behavior_trace_digest.",
            )
            _require(
                self.rejected_reason is None,
                "not_requested skill compression must not carry rejected_reason.",
            )

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "schema_version": self.schema_version,
            "parent_id": self.parent_id,
            "child_id": self.child_id,
            "tick": self.tick,
            "mode": self.mode,
            "successful_behavior_trace_digest": self.successful_behavior_trace_digest,
            "compressed_skill_digest": self.compressed_skill_digest,
            "validation_status": self.validation_status,
            "fitness_delta_positive": self.fitness_delta_positive,
            "energy_efficiency_positive": self.energy_efficiency_positive,
            "replay_successful": self.replay_successful,
            "inherited": self.inherited,
            "rejected_reason": self.rejected_reason,
        }

    def digest(self) -> str:
        return _digest(self.to_dict())


@dataclass(frozen=True, slots=True)
class ADFInheritanceRecord:
    parent_id: str
    child_id: str | None
    tick: int
    parent_adf_digest: str | None
    child_adf_digest: str | None
    adf_inheritance_mode: str
    adf_macro_count_parent: int = 0
    adf_macro_count_child: int = 0
    adf_mutation_applied: bool = False
    adf_skill_imported: bool = False
    schema_version: str = "adf_inheritance_record_v1"

    def __post_init__(self) -> None:
        _validate_enum_value(self.adf_inheritance_mode, ADFInheritanceMode, "adf_inheritance_mode")
        _validate_non_negative(self.adf_macro_count_parent, "adf_macro_count_parent")
        _validate_non_negative(self.adf_macro_count_child, "adf_macro_count_child")
        if self.adf_skill_imported:
            _require(
                self.adf_inheritance_mode
                in {
                    ADFInheritanceMode.COMPRESS_SUCCESSFUL_BEHAVIOR_TO_ADF.value,
                    ADFInheritanceMode.INHERIT_MACROS.value,
                    ADFInheritanceMode.MUTATE_MACROS.value,
                },
                "adf_skill_imported is not allowed for reset/capacity-only modes.",
            )
            _require(
                self.child_adf_digest is not None,
                "adf_skill_imported requires child_adf_digest.",
            )
            _require(
                self.parent_adf_digest is not None,
                "adf_skill_imported requires parent_adf_digest until source skill digest is recorded.",
            )

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "schema_version": self.schema_version,
            "parent_id": self.parent_id,
            "child_id": self.child_id,
            "tick": self.tick,
            "parent_adf_digest": self.parent_adf_digest,
            "child_adf_digest": self.child_adf_digest,
            "adf_inheritance_mode": self.adf_inheritance_mode,
            "adf_macro_count_parent": self.adf_macro_count_parent,
            "adf_macro_count_child": self.adf_macro_count_child,
            "adf_mutation_applied": self.adf_mutation_applied,
            "adf_skill_imported": self.adf_skill_imported,
        }

    def digest(self) -> str:
        return _digest(self.to_dict())


@dataclass(frozen=True, slots=True)
class AIBirthInterventionRecord:
    intervention_id: str
    controller_name: str
    controller_version: str
    input_evidence_digest: str
    decision_digest: str
    applied: bool
    rejected_reason: str | None
    scope: str
    event: str
    schema_version: str = "ai_birth_intervention_record_v1"

    def __post_init__(self) -> None:
        _require(bool(self.intervention_id), "intervention_id is required.")
        _require(bool(self.controller_name), "controller_name is required.")
        _require(bool(self.controller_version), "controller_version is required.")
        _require(bool(self.input_evidence_digest), "input_evidence_digest is required.")
        _require(bool(self.decision_digest), "decision_digest is required.")
        _validate_enum_value(self.scope, InterventionScope, "scope")
        _require(self.event in _INTERVENTION_EVENTS, "event is not an allowed birth intervention event.")
        if self.applied:
            _require(self.rejected_reason is None, "applied intervention must not carry rejected_reason.")
        else:
            _require(self.rejected_reason is not None, "rejected/no-op intervention requires rejected_reason.")

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "schema_version": self.schema_version,
            "intervention_id": self.intervention_id,
            "controller_name": self.controller_name,
            "controller_version": self.controller_version,
            "input_evidence_digest": self.input_evidence_digest,
            "decision_digest": self.decision_digest,
            "applied": self.applied,
            "rejected_reason": self.rejected_reason,
            "scope": self.scope,
            "event": self.event,
        }

    def digest(self) -> str:
        return _digest(self.to_dict())


@dataclass(frozen=True, slots=True)
class BirthEvent:
    birth_event_id: str
    tick: int
    parent_id: str
    child_id: str | None
    parent_lineage_id: str | None
    child_lineage_id: str | None
    parent_generation: int
    child_generation: int | None
    parent_genome_digest: str
    child_genome_digest: str | None
    mutation_digest: str | None
    mutation_count: int
    mutation_operator_names: tuple[str, ...]
    birth_cost_runtime_atp: float
    birth_cost_learning_atp: float
    child_initial_runtime_atp: float | None
    child_initial_learning_atp: float | None
    placement_cell: Position | None
    birth_policy_digest: str
    reproduction_gate_digest: str
    reproduction_attempted: bool = True
    child_created: bool = False
    blocked_reason: str | None = None
    schema_version: str = "birth_event_v1"

    def __post_init__(self) -> None:
        _validate_non_negative(self.tick, "tick")
        _validate_non_negative(self.parent_generation, "parent_generation")
        _validate_non_negative(self.mutation_count, "mutation_count")
        _validate_non_negative(self.birth_cost_runtime_atp, "birth_cost_runtime_atp")
        _validate_non_negative(self.birth_cost_learning_atp, "birth_cost_learning_atp")
        if self.child_initial_runtime_atp is not None:
            _validate_non_negative(self.child_initial_runtime_atp, "child_initial_runtime_atp")
        if self.child_initial_learning_atp is not None:
            _validate_non_negative(self.child_initial_learning_atp, "child_initial_learning_atp")
        if not self.child_created:
            _require(self.child_id is None, "blocked BirthEvent must not expose child_id.")
            _require(
                self.child_lineage_id is None,
                "blocked BirthEvent must not expose child_lineage_id.",
            )
            _require(
                self.child_generation is None,
                "blocked BirthEvent must not expose child_generation.",
            )
            _require(
                self.child_genome_digest is None,
                "blocked BirthEvent must not expose child_genome_digest.",
            )
            _require(self.mutation_digest is None, "blocked BirthEvent must not expose mutation_digest.")
            _require(self.mutation_count == 0, "blocked BirthEvent mutation_count must be 0.")
            _require(
                not self.mutation_operator_names,
                "blocked BirthEvent must not expose mutation_operator_names.",
            )
            _require(
                self.child_initial_runtime_atp is None,
                "blocked BirthEvent must not expose child_initial_runtime_atp.",
            )
            _require(
                self.child_initial_learning_atp is None,
                "blocked BirthEvent must not expose child_initial_learning_atp.",
            )
            _require(self.placement_cell is None, "blocked BirthEvent must not expose placement_cell.")
            _require(self.blocked_reason is not None, "blocked BirthEvent requires blocked_reason.")
        else:
            _require(self.child_id is not None, "successful BirthEvent requires child_id.")
            _require(
                self.child_lineage_id is not None,
                "successful BirthEvent requires child_lineage_id.",
            )
            _require(
                self.child_generation is not None,
                "successful BirthEvent requires child_generation.",
            )
            _require(
                self.child_genome_digest is not None,
                "successful BirthEvent requires child_genome_digest.",
            )
            _require(self.mutation_digest is not None, "successful BirthEvent requires mutation_digest.")
            _require(
                self.child_initial_runtime_atp is not None,
                "successful BirthEvent requires child_initial_runtime_atp.",
            )
            _require(
                self.child_initial_learning_atp is not None,
                "successful BirthEvent requires child_initial_learning_atp.",
            )
            _require(self.placement_cell is not None, "successful BirthEvent requires placement_cell.")
            _require(self.blocked_reason is None, "successful BirthEvent must not carry blocked_reason.")

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "schema_version": self.schema_version,
            "birth_event_id": self.birth_event_id,
            "tick": self.tick,
            "parent_id": self.parent_id,
            "child_id": self.child_id,
            "parent_lineage_id": self.parent_lineage_id,
            "child_lineage_id": self.child_lineage_id,
            "parent_generation": self.parent_generation,
            "child_generation": self.child_generation,
            "parent_genome_digest": self.parent_genome_digest,
            "child_genome_digest": self.child_genome_digest,
            "mutation_digest": self.mutation_digest,
            "mutation_count": self.mutation_count,
            "mutation_operator_names": list(self.mutation_operator_names),
            "birth_cost_runtime_atp": self.birth_cost_runtime_atp,
            "birth_cost_learning_atp": self.birth_cost_learning_atp,
            "child_initial_runtime_atp": self.child_initial_runtime_atp,
            "child_initial_learning_atp": self.child_initial_learning_atp,
            "placement_cell": None if self.placement_cell is None else list(self.placement_cell),
            "birth_policy_digest": self.birth_policy_digest,
            "reproduction_gate_digest": self.reproduction_gate_digest,
            "reproduction_attempted": self.reproduction_attempted,
            "child_created": self.child_created,
            "blocked_reason": self.blocked_reason,
        }

    def digest(self) -> str:
        return _digest(self.to_dict())


@dataclass(frozen=True, slots=True)
class WorldLawPatch:
    old_digest: str
    new_digest: str
    scope: str
    activation_tick_or_world: str
    reason: str
    controller_digest: str | None = None
    claim_eligible: bool = False
    claim_gate_decision_digest: str | None = None
    schema_version: str = "world_law_patch_v1"

    def __post_init__(self) -> None:
        _validate_enum_value(self.scope, InterventionScope, "scope")
        if self.claim_eligible:
            _require(
                self.claim_gate_decision_digest is not None,
                "claim_eligible WorldLawPatch requires claim_gate_decision_digest.",
            )

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "schema_version": self.schema_version,
            "old_digest": self.old_digest,
            "new_digest": self.new_digest,
            "scope": self.scope,
            "activation_tick_or_world": self.activation_tick_or_world,
            "reason": self.reason,
            "controller_digest": self.controller_digest,
            "claim_eligible": self.claim_eligible,
            "claim_gate_decision_digest": self.claim_gate_decision_digest,
        }

    def digest(self) -> str:
        return _digest(self.to_dict())


MaterialSemanticsPatch = WorldLawPatch
PhysicsPatch = WorldLawPatch
GenomeGrammarPatch = WorldLawPatch


@dataclass(frozen=True, slots=True)
class ExternalBirthInterventionAPI:
    enabled: bool = False
    controller_name: str = "none"
    controller_version: str = "0"
    allowed_events: tuple[str, ...] = (
        "before_birth_gate",
        "before_mutation_plan",
        "after_mutation_plan",
        "before_child_admission",
        "after_birth_event",
    )
    allowed_scopes: tuple[str, ...] = tuple(item.value for item in InterventionScope)
    schema_version: str = "external_birth_intervention_api_v1"

    def __post_init__(self) -> None:
        forbidden_events = tuple(event for event in self.allowed_events if event not in _INTERVENTION_EVENTS)
        _require(not forbidden_events, f"unsupported birth intervention events: {forbidden_events!r}.")
        valid_scopes = {item.value for item in InterventionScope}
        forbidden_scopes = tuple(scope for scope in self.allowed_scopes if scope not in valid_scopes)
        _require(not forbidden_scopes, f"unsupported intervention scopes: {forbidden_scopes!r}.")

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "schema_version": self.schema_version,
            "enabled": self.enabled,
            "controller_name": self.controller_name,
            "controller_version": self.controller_version,
            "allowed_events": list(self.allowed_events),
            "allowed_scopes": list(self.allowed_scopes),
        }

    def digest(self) -> str:
        return _digest(self.to_dict())


def make_policy_digest(payload: dict[str, JsonValue]) -> str:
    return _digest(payload)


def build_mutation_plan(
    *,
    plan_id: str,
    parent_genome_digest: str,
    bit_flip_rate: float,
    insertion_rate: float,
    deletion_rate: float,
    rng_state_digest_before: str,
    policy: MutationPolicy = MutationPolicy.RANDOM_BASELINE,
) -> MutationPlan:
    bit_flip_rate = finite_float("bit_flip_rate", bit_flip_rate, probability=True)
    insertion_rate = finite_float("insertion_rate", insertion_rate, probability=True)
    deletion_rate = finite_float("deletion_rate", deletion_rate, probability=True)
    operators: list[str] = []
    if bit_flip_rate > 0:
        operators.append(MutationOperator.POINT_FLIP.value)
    if insertion_rate > 0:
        operators.append(MutationOperator.INSERT_CODON.value)
    if deletion_rate > 0:
        operators.append(MutationOperator.DELETE_CODON.value)
    if not operators:
        operators.append(MutationOperator.NEUTRAL_DRIFT_MUTATION.value)
    return MutationPlan(
        plan_id=plan_id,
        parent_genome_digest=parent_genome_digest,
        operator_sequence=tuple(operators),
        mutation_budget=len(operators),
        rng_state_digest_before=rng_state_digest_before,
        policy=policy.value,
    )


__all__ = [
    "ADFInheritanceMode",
    "ADFInheritanceRecord",
    "AIBirthInterventionRecord",
    "BirthEvent",
    "BirthIntent",
    "BirthRequest",
    "ChildAdmissionResult",
    "ChildGenomeResult",
    "ExternalBirthInterventionAPI",
    "GenomeGrammarPatch",
    "InheritancePolicy",
    "InterventionScope",
    "LearningInheritanceRecord",
    "MaterialSemanticsPatch",
    "MutationAuditResult",
    "MutationOperator",
    "MutationPlan",
    "MutationPolicy",
    "PhysicsPatch",
    "ReproductionGateResult",
    "SkillCompressionRecord",
    "SkillInheritanceMode",
    "WorldLawPatch",
    "build_mutation_plan",
    "make_policy_digest",
]

# ---------------------------------------------------------------------------
# Skill-compression causal controls and child outcome audits (P0)
# ---------------------------------------------------------------------------
from codontrace.genesis.canonical import canonical_digest as _birth_canonical_digest, require_finite_float as _birth_require_finite_float

_SKILL_COMPRESSION_ABLATION_MODES = {
    "full_compression",
    "disabled",
    "capacity_only",
    "shuffle_compressed_skill",
    "null_compression",
}


@dataclass(frozen=True, slots=True)
class SkillCompressionAblationPolicy:
    """Engine-level controls for learning/skill compression inheritance."""

    enabled: bool = True
    mode: str = "full_compression"
    child_outcome_window_ticks: int = 10
    compare_against_uncompressed_sibling: bool = True
    policy_id: str = "skill_compression_ablation_policy"
    schema_version: str = "skill_compression_ablation_policy_v1"

    def __post_init__(self) -> None:
        if self.mode not in _SKILL_COMPRESSION_ABLATION_MODES:
            raise ValueError(f"mode must be one of {sorted(_SKILL_COMPRESSION_ABLATION_MODES)!r}")
        if self.child_outcome_window_ticks <= 0:
            raise ValueError("child_outcome_window_ticks must be positive")
        if not self.enabled and self.mode != "disabled":
            raise ValueError("disabled policy must use mode='disabled'")

    @property
    def active_compression(self) -> bool:
        return self.enabled and self.mode == "full_compression"

    @property
    def negative_control(self) -> bool:
        return self.mode in {"shuffle_compressed_skill", "null_compression", "disabled"}

    @property
    def claim_eligible(self) -> bool:
        # Policy alone is experimental design metadata, not positive evidence.
        return False

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "schema_version": self.schema_version,
            "policy_id": self.policy_id,
            "enabled": self.enabled,
            "mode": self.mode,
            "child_outcome_window_ticks": self.child_outcome_window_ticks,
            "compare_against_uncompressed_sibling": self.compare_against_uncompressed_sibling,
            "active_compression": self.active_compression,
            "negative_control": self.negative_control,
            "claim_eligible": self.claim_eligible,
        }

    def digest(self) -> str:
        return _birth_canonical_digest(self.to_dict(), prefix="skill_compression_policy")


@dataclass(frozen=True, slots=True)
class ChildOutcomeAuditRecord:
    """Post-birth outcome audit for inherited skill/ADF compression."""

    child_id: str
    parent_id: str
    compression_digest: str | None
    inherited_skill_count: int
    inherited_adf_count: int
    child_survival_ticks: int
    child_fitness_delta: float
    child_memory_reuse_count: int
    child_reproduction_success: bool
    compared_to_uncompressed_control: bool
    control_digest: str | None = None
    blocked_reason: str | None = None
    schema_version: str = "child_outcome_audit_record_v1"
    record_digest: str = ""

    def __post_init__(self) -> None:
        if not self.child_id or not self.parent_id:
            raise ValueError("child_id and parent_id are required")
        for attr in ("inherited_skill_count", "inherited_adf_count", "child_survival_ticks", "child_memory_reuse_count"):
            if int(getattr(self, attr)) < 0:
                raise ValueError(f"{attr} must be non-negative")
        object.__setattr__(self, "child_fitness_delta", round(_birth_require_finite_float("child_fitness_delta", self.child_fitness_delta), 10))
        if not self.record_digest:
            object.__setattr__(self, "record_digest", _birth_canonical_digest(self._payload(), prefix="child_outcome"))

    @property
    def claim_eligible(self) -> bool:
        return (
            not self.blocked_reason
            and bool(self.compression_digest)
            and self.compared_to_uncompressed_control
            and bool(self.control_digest)
            and (
                self.child_fitness_delta > 0.0
                or self.child_reproduction_success
                or self.child_memory_reuse_count > 0
            )
        )

    def _payload(self) -> dict[str, JsonValue]:
        return {
            "schema_version": self.schema_version,
            "child_id": self.child_id,
            "parent_id": self.parent_id,
            "compression_digest": self.compression_digest,
            "inherited_skill_count": self.inherited_skill_count,
            "inherited_adf_count": self.inherited_adf_count,
            "child_survival_ticks": self.child_survival_ticks,
            "child_fitness_delta": self.child_fitness_delta,
            "child_memory_reuse_count": self.child_memory_reuse_count,
            "child_reproduction_success": self.child_reproduction_success,
            "compared_to_uncompressed_control": self.compared_to_uncompressed_control,
            "control_digest": self.control_digest,
            "blocked_reason": self.blocked_reason,
            "claim_eligible": self.claim_eligible,
        }

    def to_dict(self) -> dict[str, JsonValue]:
        return {**self._payload(), "record_digest": self.record_digest}

    def digest(self) -> str:
        return self.record_digest
