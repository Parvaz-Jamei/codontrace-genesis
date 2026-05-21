"""Deterministic population lifecycle primitives for GENESIS Foundation experiments.

This module provides controlled reproduction, mutation, lineage, fitness scoring,
and generation-level audit records as library objects. It does not implement
open-ended evolution, artificial-life proof, ADF growth, CausalGraph learning,
or discovery detection.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field, replace
from enum import Enum
from typing import cast

from codontrace._types import JsonValue
from codontrace._numeric import finite_float, finite_json_dumps
from codontrace.errors import ConfigurationError
from codontrace.genesis.atp import GenesisATPState
from codontrace.genesis.behavior import BehaviorDescriptor, describe_behavior
from codontrace.genesis.birth import (
    ADFInheritanceMode,
    ADFInheritanceRecord,
    AIBirthInterventionRecord,
    BirthEvent,
    BirthIntent,
    BirthRequest,
    ChildAdmissionResult,
    ChildGenomeResult,
    InheritancePolicy,
    LearningInheritanceRecord,
    MutationAuditResult,
    MutationPlan,
    ReproductionGateResult,
    SkillCompressionRecord,
    SkillInheritanceMode,
    build_mutation_plan,
    make_policy_digest,
)
from codontrace.genesis.capsule import (
    CapsuleAdoptionBlockedReason,
    CapsuleAdoptionRecord,
    CapsuleShuffleRecord,
    CapsuleTransferConfig,
    CapsuleTransferMetric,
    CausalCapsule,
    CausalCapsuleAdoptionPolicy,
    NexusStigmergyLayer,
    SourceFitnessStatus,
    build_capsule_adoption_record,
    estimate_capsule_transfer_effect,
    read_nexus_capsules,
)
from codontrace.genesis.causal_graph import CausalGraph
from codontrace.genesis.death import (
    DeathClassificationRecord,
    DeathMonitoringConfig,
    classify_death,
)
from codontrace.genesis.fitness import (
    FitnessBreakdown,
    FitnessSignalRegistry,
    SelectionFitnessScore,
    evaluate_task_sensitive_fitness,
    task_sensitive_raw_metrics,
)
from codontrace.genesis.learning import LearningATPConfig
from codontrace.genesis.liveness import AliveGateConfig, AliveGateResult, evaluate_alive
from codontrace.genesis.memory import EpisodicMemory, EpisodicMemoryConfig
from codontrace.genesis.organism import GenesisOrganism
from codontrace.genesis.ribosome import Ribosome
from codontrace.genesis.selection import (
    EvolutionConfig,
    EvolutionSelectionResult,
    QDFallbackReason,
    select_population,
)
from codontrace.genesis.social import (
    SocialInteractionEvent,
    social_events_from_capsule_records,
    social_events_from_local_resource_context,
    social_events_from_trace,
)
from codontrace.genesis.status import ActionStatusRegistry
from codontrace.genesis.structural_mutation import (
    StructuralMutationConfig,
    build_genome_program,
    mutate_genome_program,
)
from codontrace.genesis.toolchain import evaluate_tool_chain_state
from codontrace.genesis.translation_profile import inherit_translation_profile
from codontrace.genome import SemanticGenome
from codontrace.rng import RNGManager
from codontrace.trace import Trace, TraceEvent
from codontrace.world import World2D


class OffspringPlacementPolicy(str, Enum):
    """Explicit child placement policy for controlled reproduction."""

    SAME_CELL = "same_cell"
    ADJACENT_FREE = "adjacent_free"
    BLOCKED_IF_NO_SPACE = "blocked_if_no_space"


@dataclass(frozen=True, slots=True)
class ReproductionConfig:
    """Thresholds for controlled COPY_SELF reproduction in population runs."""

    enabled: bool = True
    min_runtime_atp: float = 8.0
    min_vitae_store: float = 0.0
    max_population: int = 32
    offspring_atp_fraction: float = 0.25
    parent_atp_cost: float = 1.0
    allow_copy_self_action: bool = True
    require_alive_result: bool = True
    use_parent_pre_action_viability: bool = True
    ignore_deferred_copy_self_block_for_alive_gate: bool = True
    inheritance_policy: InheritancePolicy = InheritancePolicy.DARWINIAN_GENETIC_ONLY
    skill_inheritance_mode: SkillInheritanceMode = SkillInheritanceMode.CAPACITY_ONLY
    adf_inheritance_mode: ADFInheritanceMode = ADFInheritanceMode.INHERIT_CAPACITY
    enable_skill_compression: bool = False
    enable_lamarckian_learning_inheritance: bool = False
    enable_ai_birth_intervention: bool = False
    offspring_placement: OffspringPlacementPolicy = OffspringPlacementPolicy.SAME_CELL

    def __post_init__(self) -> None:
        _validate_probability(self.offspring_atp_fraction, "offspring_atp_fraction")
        if self.max_population <= 0:
            msg = "max_population must be > 0."
            raise ConfigurationError(msg)
        for value, name in (
            (self.min_runtime_atp, "min_runtime_atp"),
            (self.min_vitae_store, "min_vitae_store"),
            (self.parent_atp_cost, "parent_atp_cost"),
        ):
            _validate_non_negative(value, name)

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "enabled": self.enabled,
            "min_runtime_atp": self.min_runtime_atp,
            "min_vitae_store": self.min_vitae_store,
            "max_population": self.max_population,
            "offspring_atp_fraction": self.offspring_atp_fraction,
            "parent_atp_cost": self.parent_atp_cost,
            "allow_copy_self_action": self.allow_copy_self_action,
            "require_alive_result": self.require_alive_result,
            "use_parent_pre_action_viability": self.use_parent_pre_action_viability,
            "ignore_deferred_copy_self_block_for_alive_gate": (
                self.ignore_deferred_copy_self_block_for_alive_gate
            ),
            "inheritance_policy": self.inheritance_policy.value,
            "skill_inheritance_mode": self.skill_inheritance_mode.value,
            "adf_inheritance_mode": self.adf_inheritance_mode.value,
            "enable_skill_compression": self.enable_skill_compression,
            "enable_lamarckian_learning_inheritance": self.enable_lamarckian_learning_inheritance,
            "enable_ai_birth_intervention": self.enable_ai_birth_intervention,
            "offspring_placement": self.offspring_placement.value,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, JsonValue]) -> ReproductionConfig:
        return cls(
            enabled=_bool(data, "enabled", True),
            min_runtime_atp=_float(data, "min_runtime_atp", 8.0),
            min_vitae_store=_float(data, "min_vitae_store", 0.0),
            max_population=_int(data, "max_population", 32),
            offspring_atp_fraction=_float(data, "offspring_atp_fraction", 0.25),
            parent_atp_cost=_float(data, "parent_atp_cost", 1.0),
            allow_copy_self_action=_bool(data, "allow_copy_self_action", True),
            require_alive_result=_bool(data, "require_alive_result", True),
            use_parent_pre_action_viability=_bool(data, "use_parent_pre_action_viability", True),
            ignore_deferred_copy_self_block_for_alive_gate=_bool(
                data, "ignore_deferred_copy_self_block_for_alive_gate", True
            ),
            inheritance_policy=_inheritance_policy(data.get("inheritance_policy")),
            skill_inheritance_mode=_skill_inheritance_mode(data.get("skill_inheritance_mode")),
            adf_inheritance_mode=_adf_inheritance_mode(data.get("adf_inheritance_mode")),
            enable_skill_compression=_bool(data, "enable_skill_compression", False),
            enable_lamarckian_learning_inheritance=_bool(
                data, "enable_lamarckian_learning_inheritance", False
            ),
            enable_ai_birth_intervention=_bool(data, "enable_ai_birth_intervention", False),
            offspring_placement=_placement_policy(data.get("offspring_placement")),
        )


@dataclass(frozen=True, slots=True)
class MutationConfig:
    """Deterministic genome mutation controls.

    ``bit_flip_rate`` is the single source of truth for ordinary reproduction
    mutation. Insertion/deletion are optional codon-sized operations so every
    produced SemanticGenome remains binary and syntactically valid.
    """

    bit_flip_rate: float
    insertion_rate: float = 0.0
    deletion_rate: float = 0.0
    max_genome_bits: int | None = None
    policy: str = "random_baseline"
    enabled_operators: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _validate_probability(self.bit_flip_rate, "bit_flip_rate")
        _validate_probability(self.insertion_rate, "insertion_rate")
        _validate_probability(self.deletion_rate, "deletion_rate")
        if self.max_genome_bits is not None and self.max_genome_bits < SemanticGenome.CODON_LENGTH:
            msg = "max_genome_bits must be at least 3 when provided."
            raise ConfigurationError(msg)

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "bit_flip_rate": self.bit_flip_rate,
            "insertion_rate": self.insertion_rate,
            "deletion_rate": self.deletion_rate,
            "max_genome_bits": self.max_genome_bits,
            "policy": self.policy,
            "enabled_operators": list(self.enabled_operators),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, JsonValue]) -> MutationConfig:
        raw_max = data.get("max_genome_bits")
        max_bits = None if raw_max is None else _int(data, "max_genome_bits", 0)
        return cls(
            bit_flip_rate=_float(data, "bit_flip_rate", 0.0),
            insertion_rate=_float(data, "insertion_rate", 0.0),
            deletion_rate=_float(data, "deletion_rate", 0.0),
            max_genome_bits=max_bits,
            policy=_str(data, "policy", "random_baseline"),
            enabled_operators=_str_tuple(data, "enabled_operators"),
        )


@dataclass(frozen=True, slots=True)
class FitnessConfig:
    """Weights for a controlled fitness score, not life/intelligence."""

    reward_survival_ticks: float = 1.0
    reward_lumen_eaten: float = 2.0
    reward_nexus_emitted: float = 1.0
    penalty_blocked_action: float = 0.5
    penalty_atp_starvation: float = 5.0
    reward_reproduction: float = 8.0
    signal_registry: FitnessSignalRegistry | None = None
    status_registry: ActionStatusRegistry = field(default_factory=ActionStatusRegistry.genesis_v0)

    def to_dict(self) -> dict[str, JsonValue]:
        payload: dict[str, JsonValue] = {
            "reward_survival_ticks": self.reward_survival_ticks,
            "reward_lumen_eaten": self.reward_lumen_eaten,
            "reward_nexus_emitted": self.reward_nexus_emitted,
            "penalty_blocked_action": self.penalty_blocked_action,
            "penalty_atp_starvation": self.penalty_atp_starvation,
            "reward_reproduction": self.reward_reproduction,
        }
        if self.signal_registry is not None:
            payload["signal_registry"] = self.signal_registry.to_dict()
        payload["status_registry"] = self.status_registry.to_dict()
        return payload

    @classmethod
    def from_dict(cls, data: Mapping[str, JsonValue]) -> FitnessConfig:
        raw_status_registry = data.get("status_registry")
        return cls(
            reward_survival_ticks=_float(data, "reward_survival_ticks", 1.0),
            reward_lumen_eaten=_float(data, "reward_lumen_eaten", 2.0),
            reward_nexus_emitted=_float(data, "reward_nexus_emitted", 1.0),
            penalty_blocked_action=_float(data, "penalty_blocked_action", 0.5),
            penalty_atp_starvation=_float(data, "penalty_atp_starvation", 5.0),
            reward_reproduction=_float(data, "reward_reproduction", 8.0),
            signal_registry=(
                FitnessSignalRegistry.from_dict(raw_registry)
                if isinstance((raw_registry := data.get("signal_registry")), dict)
                else None
            ),
            status_registry=(
                ActionStatusRegistry.from_dict(raw_status_registry)
                if isinstance(raw_status_registry, dict)
                else ActionStatusRegistry.genesis_v0()
            ),
        )


@dataclass(frozen=True, slots=True)
class FitnessResult:
    """Deterministic controlled-experiment fitness result."""

    organism_id: str
    score: float
    survived_ticks: int
    lumen_eaten: int
    nexus_emitted: int
    blocked_actions: int
    reproduction_events: int
    reasons: tuple[str, ...]
    fitness_breakdown: FitnessBreakdown | None = None
    selection_fitness_score: SelectionFitnessScore | None = None
    death_classification: DeathClassificationRecord | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "score", finite_float("FitnessResult.score", self.score))

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "organism_id": self.organism_id,
            "score": self.score,
            "survived_ticks": self.survived_ticks,
            "lumen_eaten": self.lumen_eaten,
            "nexus_emitted": self.nexus_emitted,
            "blocked_actions": self.blocked_actions,
            "reproduction_events": self.reproduction_events,
            "reasons": [reason for reason in self.reasons],
            "fitness_breakdown": None
            if self.fitness_breakdown is None
            else self.fitness_breakdown.to_dict(),
            "selection_fitness_score": None
            if self.selection_fitness_score is None
            else self.selection_fitness_score.to_dict(),
            "death_classification": None
            if self.death_classification is None
            else self.death_classification.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, JsonValue]) -> FitnessResult:
        return cls(
            organism_id=_str(data, "organism_id"),
            score=_float(data, "score", 0.0),
            survived_ticks=_int(data, "survived_ticks", 0),
            lumen_eaten=_int(data, "lumen_eaten", 0),
            nexus_emitted=_int(data, "nexus_emitted", 0),
            blocked_actions=_int(data, "blocked_actions", 0),
            reproduction_events=_int(data, "reproduction_events", 0),
            reasons=_str_tuple(data, "reasons"),
            fitness_breakdown=_fitness_breakdown_from_optional(data.get("fitness_breakdown")),
            selection_fitness_score=_selection_fitness_score_from_optional(
                data.get("selection_fitness_score")
            ),
            death_classification=DeathClassificationRecord.from_dict(death_raw)
            if isinstance((death_raw := data.get("death_classification")), Mapping)
            else None,
        )


@dataclass(frozen=True, slots=True)
class LineageRecord:
    """Immutable birth/death metadata for one organism."""

    organism_id: str
    parent_id: str | None
    generation: int
    genome_digest: str
    mutation_count: int
    birth_tick: int
    death_tick: int | None
    reproduction_event_id: str | None

    @property
    def id(self) -> str | None:
        """Backward-compatible lineage identifier alias."""

        return self.reproduction_event_id

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "organism_id": self.organism_id,
            "parent_id": self.parent_id,
            "generation": self.generation,
            "genome_digest": self.genome_digest,
            "mutation_count": self.mutation_count,
            "birth_tick": self.birth_tick,
            "death_tick": self.death_tick,
            "reproduction_event_id": self.reproduction_event_id,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, JsonValue]) -> LineageRecord:
        raw_death = data.get("death_tick")
        return cls(
            organism_id=_str(data, "organism_id"),
            parent_id=_optional_str(data, "parent_id"),
            generation=_int(data, "generation", 0),
            genome_digest=_str(data, "genome_digest"),
            mutation_count=_int(data, "mutation_count", 0),
            birth_tick=_int(data, "birth_tick", 0),
            death_tick=None if raw_death is None else _int(data, "death_tick", 0),
            reproduction_event_id=_optional_str(data, "reproduction_event_id"),
        )


@dataclass(frozen=True, slots=True)
class MutationResult:
    """Genome mutation plus deterministic metadata."""

    original_genome: SemanticGenome
    mutated_genome: SemanticGenome
    mutation_count: int
    operations: tuple[str, ...]
    rng_digest: str

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "original_genome": self.original_genome.to_compact(),
            "mutated_genome": self.mutated_genome.to_compact(),
            "original_digest": self.original_genome.digest(),
            "mutated_digest": self.mutated_genome.digest(),
            "mutation_count": self.mutation_count,
            "operations": [operation for operation in self.operations],
            "rng_digest": self.rng_digest,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, JsonValue]) -> MutationResult:
        return cls(
            original_genome=SemanticGenome.from_compact(_str(data, "original_genome")),
            mutated_genome=SemanticGenome.from_compact(_str(data, "mutated_genome")),
            mutation_count=_int(data, "mutation_count", 0),
            operations=_str_tuple(data, "operations"),
            rng_digest=_str(data, "rng_digest"),
        )

    def digest(self) -> str:
        payload = finite_json_dumps(self.to_dict(), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class ReproductionDecision:
    """Decision object explaining whether COPY_SELF may create an offspring."""

    allowed: bool
    reasons: tuple[str, ...]

    def to_dict(self) -> dict[str, JsonValue]:
        return {"allowed": self.allowed, "reasons": [reason for reason in self.reasons]}

    @classmethod
    def from_dict(cls, data: Mapping[str, JsonValue]) -> ReproductionDecision:
        return cls(allowed=_bool(data, "allowed", False), reasons=_str_tuple(data, "reasons"))


@dataclass(frozen=True, slots=True)
class ReproductionResult:
    """Functional result of controlled reproduction."""

    attempted: bool
    succeeded: bool
    parent_before_id: str
    parent_after: GenesisOrganism
    child: GenesisOrganism | None
    mutation: MutationResult | None
    lineage: LineageRecord | None
    decision: ReproductionDecision
    event_id: str | None
    ledger_entry_ids: tuple[int, ...] = ()
    birth_intent: BirthIntent | None = None
    birth_request: BirthRequest | None = None
    reproduction_gate_result: ReproductionGateResult | None = None
    mutation_plan: MutationPlan | None = None
    mutation_audit_result: MutationAuditResult | None = None
    child_genome_result: ChildGenomeResult | None = None
    child_admission_result: ChildAdmissionResult | None = None
    birth_event: BirthEvent | None = None
    learning_inheritance_record: LearningInheritanceRecord | None = None
    skill_compression_record: SkillCompressionRecord | None = None
    adf_inheritance_record: ADFInheritanceRecord | None = None
    ai_birth_intervention_records: tuple[AIBirthInterventionRecord, ...] = ()
    action_cost_charged: bool = False
    parent_build_cost_charged: bool = False
    offspring_transfer_charged: bool = False
    reproduction_cost_policy: str = "stage_separated"

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "attempted": self.attempted,
            "succeeded": self.succeeded,
            "parent_before_id": self.parent_before_id,
            "parent_after": _organism_summary(self.parent_after),
            "child": None if self.child is None else _organism_summary(self.child),
            "mutation": None if self.mutation is None else self.mutation.to_dict(),
            "lineage": None if self.lineage is None else self.lineage.to_dict(),
            "decision": self.decision.to_dict(),
            "event_id": self.event_id,
            "ledger_entry_ids": [entry_id for entry_id in self.ledger_entry_ids],
            "action_cost_charged": self.action_cost_charged,
            "parent_build_cost_charged": self.parent_build_cost_charged,
            "offspring_transfer_charged": self.offspring_transfer_charged,
            "reproduction_cost_policy": self.reproduction_cost_policy,
            "birth_intent": None if self.birth_intent is None else self.birth_intent.to_dict(),
            "birth_request": None if self.birth_request is None else self.birth_request.to_dict(),
            "reproduction_gate_result": None
            if self.reproduction_gate_result is None
            else self.reproduction_gate_result.to_dict(),
            "mutation_plan": None if self.mutation_plan is None else self.mutation_plan.to_dict(),
            "mutation_audit_result": None
            if self.mutation_audit_result is None
            else self.mutation_audit_result.to_dict(),
            "child_genome_result": None
            if self.child_genome_result is None
            else self.child_genome_result.to_dict(),
            "child_admission_result": None
            if self.child_admission_result is None
            else self.child_admission_result.to_dict(),
            "birth_event": None if self.birth_event is None else self.birth_event.to_dict(),
            "learning_inheritance_record": None
            if self.learning_inheritance_record is None
            else self.learning_inheritance_record.to_dict(),
            "skill_compression_record": None
            if self.skill_compression_record is None
            else self.skill_compression_record.to_dict(),
            "adf_inheritance_record": None
            if self.adf_inheritance_record is None
            else self.adf_inheritance_record.to_dict(),
            "ai_birth_intervention_records": [
                record.to_dict() for record in self.ai_birth_intervention_records
            ],
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, JsonValue]) -> ReproductionResult:
        child_raw = data.get("child")
        mutation_raw = data.get("mutation")
        lineage_raw = data.get("lineage")
        decision_raw = data.get("decision")
        parent_raw = data.get("parent_after")
        if not isinstance(parent_raw, Mapping):
            msg = "ReproductionResult.parent_after must be an object."
            raise ConfigurationError(msg)
        if not isinstance(decision_raw, Mapping):
            msg = "ReproductionResult.decision must be an object."
            raise ConfigurationError(msg)
        return cls(
            attempted=_bool(data, "attempted", False),
            succeeded=_bool(data, "succeeded", False),
            parent_before_id=_str(data, "parent_before_id"),
            parent_after=_organism_from_summary(parent_raw),
            child=_organism_from_summary(child_raw) if isinstance(child_raw, Mapping) else None,
            mutation=MutationResult.from_dict(mutation_raw)
            if isinstance(mutation_raw, Mapping)
            else None,
            lineage=LineageRecord.from_dict(lineage_raw)
            if isinstance(lineage_raw, Mapping)
            else None,
            decision=ReproductionDecision.from_dict(decision_raw),
            event_id=_optional_str(data, "event_id"),
            ledger_entry_ids=_int_tuple(data, "ledger_entry_ids"),
            action_cost_charged=_bool(data, "action_cost_charged", False),
            parent_build_cost_charged=_bool(data, "parent_build_cost_charged", False),
            offspring_transfer_charged=_bool(data, "offspring_transfer_charged", False),
            reproduction_cost_policy=_str(data, "reproduction_cost_policy", "stage_separated"),
            birth_intent=_birth_intent_from_optional(data.get("birth_intent")),
            birth_request=_birth_request_from_optional(data.get("birth_request")),
            reproduction_gate_result=_reproduction_gate_result_from_optional(
                data.get("reproduction_gate_result")
            ),
            mutation_plan=_mutation_plan_from_optional(data.get("mutation_plan")),
            mutation_audit_result=_mutation_audit_result_from_optional(
                data.get("mutation_audit_result")
            ),
            child_genome_result=_child_genome_result_from_optional(data.get("child_genome_result")),
            child_admission_result=_child_admission_result_from_optional(
                data.get("child_admission_result")
            ),
            birth_event=_birth_event_from_optional(data.get("birth_event")),
            learning_inheritance_record=_learning_inheritance_from_optional(
                data.get("learning_inheritance_record")
            ),
            skill_compression_record=_skill_compression_from_optional(
                data.get("skill_compression_record")
            ),
            adf_inheritance_record=_adf_inheritance_from_optional(
                data.get("adf_inheritance_record")
            ),
            ai_birth_intervention_records=_ai_birth_records_from_optional(
                data.get("ai_birth_intervention_records")
            ),
        )


@dataclass(frozen=True, slots=True)
class PopulationState:
    """Immutable snapshot of one deterministic population generation."""

    generation: int
    tick: int
    organisms: tuple[GenesisOrganism, ...]
    lineage: tuple[LineageRecord, ...]
    fitness: tuple[FitnessResult, ...]

    def __post_init__(self) -> None:
        if self.generation < 0 or self.tick < 0:
            msg = "Population generation and tick must be non-negative."
            raise ConfigurationError(msg)
        ids = [organism.id for organism in self.organisms]
        if len(ids) != len(set(ids)):
            msg = "Population organism ids must be unique."
            raise ConfigurationError(msg)

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "generation": self.generation,
            "tick": self.tick,
            "organisms": [_organism_summary(organism) for organism in self.organisms],
            "lineage": [record.to_dict() for record in self.lineage],
            "fitness": [item.to_dict() for item in self.fitness],
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, JsonValue]) -> PopulationState:
        organisms_raw = _list(data, "organisms")
        lineage_raw = _list(data, "lineage")
        fitness_raw = _list(data, "fitness")
        return cls(
            generation=_int(data, "generation", 0),
            tick=_int(data, "tick", 0),
            organisms=tuple(
                _organism_from_summary(item) for item in organisms_raw if isinstance(item, Mapping)
            ),
            lineage=tuple(
                LineageRecord.from_dict(item) for item in lineage_raw if isinstance(item, Mapping)
            ),
            fitness=tuple(
                FitnessResult.from_dict(item) for item in fitness_raw if isinstance(item, Mapping)
            ),
        )

    def digest(self) -> str:
        payload = finite_json_dumps(self.to_dict(), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class OrganismStepRecord:
    """Generation-level audit record for one organism run."""

    organism_id: str
    trace_digest: str
    runtime_atp_before: float
    runtime_atp_after: float
    alive_result: AliveGateResult
    fitness_result: FitnessResult
    reproduction_result: ReproductionResult | None
    world_before_digest: str
    world_after_digest: str
    genome_digest: str = ""
    runtime_ledger_digest_before: str | None = None
    runtime_ledger_digest_after: str | None = None
    learning_ledger_digest_before: str | None = None
    learning_ledger_digest_after: str | None = None
    memory_digest_before: str | None = None
    memory_digest_after: str | None = None
    memory_write_count: int = 0
    learning_update_attempts: int = 0
    learning_update_successes: int = 0
    behavior_descriptor: BehaviorDescriptor | None = None
    causal_graph_digest_before: str | None = None
    causal_graph_digest_after: str | None = None
    causal_graph_update_attempts: int = 0
    causal_graph_update_successes: int = 0
    causal_graph_update_blocked_reason: str | None = None
    causal_prediction_attempted: int = 0
    causal_prediction_correct: int = 0
    capsules_emitted: int = 0
    capsules_read: int = 0
    capsules_adopted: int = 0
    capsule_emit_count: int = 0
    capsule_read_count: int = 0
    capsule_adoption_attempts: int = 0
    capsule_adoption_successes: int = 0
    capsule_adoption_failures: int = 0
    nexus_signal_count_before: int = 0
    nexus_signal_count_after: int = 0
    capsule_store_digest_before: str | None = None
    capsule_store_digest_after: str | None = None
    nexus_signals_deposited: int = 0
    atp_learning_spent: float = 0.0
    capsule_transfer_metrics: tuple[CapsuleTransferMetric, ...] = ()
    capsule_adoption_records: tuple[CapsuleAdoptionRecord, ...] = ()
    capsule_shuffle_records: tuple[CapsuleShuffleRecord, ...] = ()
    social_interaction_records: tuple[SocialInteractionEvent, ...] = ()
    fitness_breakdown: FitnessBreakdown | None = None
    selection_fitness_score: SelectionFitnessScore | None = None
    death_classification: DeathClassificationRecord | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "runtime_atp_before", finite_float("OrganismStepRecord.runtime_atp_before", self.runtime_atp_before, non_negative=True))
        object.__setattr__(self, "runtime_atp_after", finite_float("OrganismStepRecord.runtime_atp_after", self.runtime_atp_after, non_negative=True))
        object.__setattr__(self, "atp_learning_spent", finite_float("OrganismStepRecord.atp_learning_spent", self.atp_learning_spent, non_negative=True))

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "organism_id": self.organism_id,
            "trace_digest": self.trace_digest,
            "genome_digest": self.genome_digest,
            "runtime_atp_before": self.runtime_atp_before,
            "runtime_atp_after": self.runtime_atp_after,
            "alive_result": self.alive_result.to_dict(),
            "fitness_result": self.fitness_result.to_dict(),
            "reproduction_result": None
            if self.reproduction_result is None
            else self.reproduction_result.to_dict(),
            "world_before_digest": self.world_before_digest,
            "world_after_digest": self.world_after_digest,
            "runtime_ledger_digest_before": self.runtime_ledger_digest_before,
            "runtime_ledger_digest_after": self.runtime_ledger_digest_after,
            "learning_ledger_digest_before": self.learning_ledger_digest_before,
            "learning_ledger_digest_after": self.learning_ledger_digest_after,
            "memory_digest_before": self.memory_digest_before,
            "memory_digest_after": self.memory_digest_after,
            "memory_write_count": self.memory_write_count,
            "learning_update_attempts": self.learning_update_attempts,
            "learning_update_successes": self.learning_update_successes,
            "behavior_descriptor": None
            if self.behavior_descriptor is None
            else self.behavior_descriptor.to_dict(),
            "causal_graph_digest_before": self.causal_graph_digest_before,
            "causal_graph_digest_after": self.causal_graph_digest_after,
            "causal_graph_update_attempts": self.causal_graph_update_attempts,
            "causal_graph_update_successes": self.causal_graph_update_successes,
            "causal_graph_update_blocked_reason": self.causal_graph_update_blocked_reason,
            "causal_prediction_attempted": self.causal_prediction_attempted,
            "causal_prediction_correct": self.causal_prediction_correct,
            "capsules_emitted": self.capsules_emitted,
            "capsules_read": self.capsules_read,
            "capsules_adopted": self.capsules_adopted,
            "capsule_emit_count": self.capsule_emit_count,
            "capsule_read_count": self.capsule_read_count,
            "capsule_adoption_attempts": self.capsule_adoption_attempts,
            "capsule_adoption_successes": self.capsule_adoption_successes,
            "capsule_adoption_failures": self.capsule_adoption_failures,
            "nexus_signal_count_before": self.nexus_signal_count_before,
            "nexus_signal_count_after": self.nexus_signal_count_after,
            "capsule_store_digest_before": self.capsule_store_digest_before,
            "capsule_store_digest_after": self.capsule_store_digest_after,
            "nexus_signals_deposited": self.nexus_signals_deposited,
            "atp_learning_spent": self.atp_learning_spent,
            "capsule_transfer_metrics": [item.to_dict() for item in self.capsule_transfer_metrics],
            "capsule_adoption_records": [item.to_dict() for item in self.capsule_adoption_records],
            "capsule_shuffle_records": [item.to_dict() for item in self.capsule_shuffle_records],
            "social_interaction_records": [
                item.to_dict() for item in self.social_interaction_records
            ],
            "fitness_breakdown": None
            if self.fitness_breakdown is None
            else self.fitness_breakdown.to_dict(),
            "selection_fitness_score": None
            if self.selection_fitness_score is None
            else self.selection_fitness_score.to_dict(),
            "death_classification": None
            if self.death_classification is None
            else self.death_classification.to_dict(),
            "death_classification_consistency_status": _death_classification_consistency_status(
                self.death_classification, self.fitness_result.death_classification
            ),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, JsonValue]) -> OrganismStepRecord:
        alive_raw = data.get("alive_result")
        fitness_raw = data.get("fitness_result")
        reproduction_raw = data.get("reproduction_result")
        if not isinstance(alive_raw, Mapping) or not isinstance(fitness_raw, Mapping):
            msg = "OrganismStepRecord requires alive_result and fitness_result objects."
            raise ConfigurationError(msg)
        return cls(
            organism_id=_str(data, "organism_id"),
            trace_digest=_str(data, "trace_digest"),
            runtime_atp_before=_float(data, "runtime_atp_before", 0.0),
            runtime_atp_after=_float(data, "runtime_atp_after", 0.0),
            alive_result=_alive_result_from_dict(alive_raw),
            fitness_result=FitnessResult.from_dict(fitness_raw),
            reproduction_result=ReproductionResult.from_dict(reproduction_raw)
            if isinstance(reproduction_raw, Mapping)
            else None,
            world_before_digest=_str(data, "world_before_digest"),
            world_after_digest=_str(data, "world_after_digest"),
            genome_digest=_optional_str(data, "genome_digest") or "",
            runtime_ledger_digest_before=_optional_str(data, "runtime_ledger_digest_before"),
            runtime_ledger_digest_after=_optional_str(data, "runtime_ledger_digest_after"),
            learning_ledger_digest_before=_optional_str(data, "learning_ledger_digest_before"),
            learning_ledger_digest_after=_optional_str(data, "learning_ledger_digest_after"),
            memory_digest_before=_optional_str(data, "memory_digest_before"),
            memory_digest_after=_optional_str(data, "memory_digest_after"),
            memory_write_count=_int(data, "memory_write_count", 0),
            learning_update_attempts=_int(data, "learning_update_attempts", 0),
            learning_update_successes=_int(data, "learning_update_successes", 0),
            behavior_descriptor=BehaviorDescriptor.from_dict(behavior_raw)
            if isinstance((behavior_raw := data.get("behavior_descriptor")), dict)
            else None,
            causal_graph_digest_before=_optional_str(data, "causal_graph_digest_before"),
            causal_graph_digest_after=_optional_str(data, "causal_graph_digest_after"),
            causal_graph_update_attempts=_int(data, "causal_graph_update_attempts", 0),
            causal_graph_update_successes=_int(data, "causal_graph_update_successes", 0),
            causal_graph_update_blocked_reason=_optional_str(
                data, "causal_graph_update_blocked_reason"
            ),
            causal_prediction_attempted=_int(data, "causal_prediction_attempted", 0),
            causal_prediction_correct=_int(data, "causal_prediction_correct", 0),
            capsules_emitted=_int(data, "capsules_emitted", 0),
            capsules_read=_int(data, "capsules_read", 0),
            capsules_adopted=_int(data, "capsules_adopted", 0),
            capsule_emit_count=_int(data, "capsule_emit_count", _int(data, "capsules_emitted", 0)),
            capsule_read_count=_int(data, "capsule_read_count", _int(data, "capsules_read", 0)),
            capsule_adoption_attempts=_int(data, "capsule_adoption_attempts", 0),
            capsule_adoption_successes=_int(
                data, "capsule_adoption_successes", _int(data, "capsules_adopted", 0)
            ),
            capsule_adoption_failures=_int(data, "capsule_adoption_failures", 0),
            nexus_signal_count_before=_int(data, "nexus_signal_count_before", 0),
            nexus_signal_count_after=_int(data, "nexus_signal_count_after", 0),
            capsule_store_digest_before=_optional_str(data, "capsule_store_digest_before"),
            capsule_store_digest_after=_optional_str(data, "capsule_store_digest_after"),
            nexus_signals_deposited=_int(data, "nexus_signals_deposited", 0),
            atp_learning_spent=_float(data, "atp_learning_spent", 0.0),
            capsule_transfer_metrics=tuple(
                CapsuleTransferMetric.from_dict(item)
                for item in _list(data, "capsule_transfer_metrics")
                if isinstance(item, Mapping)
            ),
            capsule_adoption_records=tuple(
                CapsuleAdoptionRecord.from_dict(item)
                for item in _list(data, "capsule_adoption_records")
                if isinstance(item, Mapping)
            ),
            capsule_shuffle_records=tuple(
                CapsuleShuffleRecord.from_dict(item)
                for item in _list(data, "capsule_shuffle_records")
                if isinstance(item, Mapping)
            ),
            social_interaction_records=tuple(
                SocialInteractionEvent.from_dict(item)
                for item in _list(data, "social_interaction_records")
                if isinstance(item, Mapping)
            ),
            fitness_breakdown=_fitness_breakdown_from_optional(data.get("fitness_breakdown")),
            selection_fitness_score=_selection_fitness_score_from_optional(
                data.get("selection_fitness_score")
            ),
            death_classification=DeathClassificationRecord.from_dict(death_raw)
            if isinstance((death_raw := data.get("death_classification")), Mapping)
            else None,
        )


@dataclass(frozen=True, slots=True)
class PopulationCausalSummary:
    """Population-level causal/capsule audit summary for one generation."""

    organisms_with_graph: int = 0
    total_causal_nodes: int = 0
    total_causal_edges: int = 0
    update_attempts: int = 0
    update_successes: int = 0
    predictions_attempted: int = 0
    predictions_correct: int = 0
    capsules_emitted: int = 0
    capsules_read: int = 0
    capsules_adopted: int = 0
    atp_learning_spent: float = 0.0

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "organisms_with_graph": self.organisms_with_graph,
            "total_causal_nodes": self.total_causal_nodes,
            "total_causal_edges": self.total_causal_edges,
            "update_attempts": self.update_attempts,
            "update_successes": self.update_successes,
            "predictions_attempted": self.predictions_attempted,
            "predictions_correct": self.predictions_correct,
            "capsules_emitted": self.capsules_emitted,
            "capsules_read": self.capsules_read,
            "capsules_adopted": self.capsules_adopted,
            "atp_learning_spent": self.atp_learning_spent,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, JsonValue]) -> PopulationCausalSummary:
        return cls(
            organisms_with_graph=_int(data, "organisms_with_graph", 0),
            total_causal_nodes=_int(data, "total_causal_nodes", 0),
            total_causal_edges=_int(data, "total_causal_edges", 0),
            update_attempts=_int(data, "update_attempts", 0),
            update_successes=_int(data, "update_successes", 0),
            predictions_attempted=_int(data, "predictions_attempted", 0),
            predictions_correct=_int(data, "predictions_correct", 0),
            capsules_emitted=_int(data, "capsules_emitted", 0),
            capsules_read=_int(data, "capsules_read", 0),
            capsules_adopted=_int(data, "capsules_adopted", 0),
            atp_learning_spent=_float(data, "atp_learning_spent", 0.0),
        )


@dataclass(frozen=True, slots=True)
class RuntimeResourcePolicy:
    """Deterministic resource regeneration policy for long-horizon GENESIS runs."""

    respawn_enabled: bool = False
    respawn_rate: float = 0.0
    max_resources: int = 0
    resource_kinds: tuple[str, ...] = ("lumen",)
    amount: float = 2.0
    seed_namespace: str = "resource_respawn"
    status: str = "disabled_by_config"

    def __post_init__(self) -> None:
        if not isinstance(self.respawn_enabled, bool):
            raise ConfigurationError("RuntimeResourcePolicy.respawn_enabled must be a bool.")
        object.__setattr__(self, "respawn_rate", finite_float("RuntimeResourcePolicy.respawn_rate", self.respawn_rate, non_negative=True, probability=True))
        object.__setattr__(self, "amount", finite_float("RuntimeResourcePolicy.amount", self.amount, non_negative=True))
        if self.max_resources < 0:
            raise ConfigurationError("RuntimeResourcePolicy.max_resources must be non-negative.")
        if not self.resource_kinds or any(not str(item) for item in self.resource_kinds):
            raise ConfigurationError("RuntimeResourcePolicy.resource_kinds must be non-empty strings.")
        resolved = (
            "runtime_effective_default_off" if self.respawn_enabled else "disabled_by_config"
        )
        if self.status not in {"disabled_by_config", "reserved_config_only", "runtime_effective_default_off", "runtime_effective_default_on"}:
            raise ConfigurationError("RuntimeResourcePolicy.status is not recognized.")
        object.__setattr__(self, "status", resolved if self.status == "disabled_by_config" else self.status)

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "respawn_enabled": self.respawn_enabled,
            "respawn_rate": self.respawn_rate,
            "max_resources": self.max_resources,
            "resource_kinds": list(self.resource_kinds),
            "amount": self.amount,
            "seed_namespace": self.seed_namespace,
            "status": self.status,
            "claim_allowed": self.respawn_enabled and self.status.startswith("runtime_effective"),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, JsonValue]) -> "RuntimeResourcePolicy":
        kinds_raw = data.get("resource_kinds", ["lumen"])
        kinds = tuple(str(item) for item in kinds_raw) if isinstance(kinds_raw, list) else ("lumen",)
        return cls(
            respawn_enabled=_bool(data, "respawn_enabled", False),
            respawn_rate=_float(data, "respawn_rate", 0.0),
            max_resources=_int(data, "max_resources", 0),
            resource_kinds=kinds,
            amount=_float(data, "amount", 2.0),
            seed_namespace=_str(data, "seed_namespace", "resource_respawn"),
            status=_str(data, "status", "disabled_by_config"),
        )

    def digest(self) -> str:
        return _digest(self.to_dict())


@dataclass(frozen=True, slots=True)
class RuntimeResourceEvent:
    """Evidence record for deterministic resource respawn/depletion policy."""

    tick: int
    event_type: str
    position: tuple[int, int] | None
    amount: float
    kind: str
    rng_namespace: str
    rng_draw_count_before: int
    rng_draw_count_after: int
    world_digest_before: str
    world_digest_after: str
    status: str = "measured"

    def __post_init__(self) -> None:
        object.__setattr__(self, "amount", finite_float("RuntimeResourceEvent.amount", self.amount, non_negative=True))

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "schema_version": "runtime_resource_event_v1",
            "tick": self.tick,
            "event_type": self.event_type,
            "position": None if self.position is None else [self.position[0], self.position[1]],
            "amount": self.amount,
            "kind": self.kind,
            "rng_namespace": self.rng_namespace,
            "rng_draw_count_before": self.rng_draw_count_before,
            "rng_draw_count_after": self.rng_draw_count_after,
            "world_digest_before": self.world_digest_before,
            "world_digest_after": self.world_digest_after,
            "status": self.status,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, JsonValue]) -> "RuntimeResourceEvent":
        raw_pos = data.get("position")
        pos = None
        if isinstance(raw_pos, list) and len(raw_pos) == 2:
            pos = (int(raw_pos[0]), int(raw_pos[1]))
        return cls(
            tick=_int(data, "tick", 0),
            event_type=_str(data, "event_type", "unknown"),
            position=pos,
            amount=_float(data, "amount", 0.0),
            kind=_str(data, "kind", "lumen"),
            rng_namespace=_str(data, "rng_namespace", "resource_respawn"),
            rng_draw_count_before=_int(data, "rng_draw_count_before", 0),
            rng_draw_count_after=_int(data, "rng_draw_count_after", 0),
            world_digest_before=_str(data, "world_digest_before", ""),
            world_digest_after=_str(data, "world_digest_after", ""),
            status=_str(data, "status", "measured"),
        )

    def digest(self) -> str:
        return _digest(self.to_dict())


@dataclass(frozen=True, slots=True)
class GenerationResult:
    """Summary and audit bundle returned by a deterministic generation step."""

    before_count: int
    after_count: int
    births: int
    deaths: int
    reproduction_attempts: int
    blocked_reproduction: int
    mean_fitness: float
    best_fitness: float
    population: PopulationState
    world_after: World2D
    world_before_digest: str
    world_after_digest: str
    traces: tuple[Trace, ...] = ()
    organism_records: tuple[OrganismStepRecord, ...] = ()
    nexus_layer: NexusStigmergyLayer | None = None
    causal_summary: PopulationCausalSummary = field(default_factory=PopulationCausalSummary)
    selection_result: EvolutionSelectionResult | None = None
    raw_mean_fitness: float = 0.0
    raw_best_fitness: float = 0.0
    selection_mean_fitness: float = 0.0
    selection_best_fitness: float = 0.0
    viable_mean_fitness: float = 0.0
    viable_best_fitness: float = 0.0
    viability_gate_failures: int = 0
    selection_zero_score_reasons: dict[str, int] = field(default_factory=dict)
    mean_fitness_alias: str = "raw_mean_fitness"
    best_fitness_alias: str = "raw_best_fitness"
    resource_policy_records: tuple[RuntimeResourceEvent, ...] = ()
    newborn_protection_records: tuple[dict[str, JsonValue], ...] = ()

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "before_count": self.before_count,
            "after_count": self.after_count,
            "births": self.births,
            "deaths": self.deaths,
            "reproduction_attempts": self.reproduction_attempts,
            "blocked_reproduction": self.blocked_reproduction,
            "mean_fitness": self.mean_fitness,
            "best_fitness": self.best_fitness,
            "raw_mean_fitness": self.raw_mean_fitness,
            "raw_best_fitness": self.raw_best_fitness,
            "selection_mean_fitness": self.selection_mean_fitness,
            "selection_best_fitness": self.selection_best_fitness,
            "viable_mean_fitness": self.viable_mean_fitness,
            "viable_best_fitness": self.viable_best_fitness,
            "viability_gate_failures": self.viability_gate_failures,
            "selection_zero_score_reasons": dict(sorted(self.selection_zero_score_reasons.items())),
            "mean_fitness_alias": self.mean_fitness_alias,
            "best_fitness_alias": self.best_fitness_alias,
            "resource_policy_records": [item.to_dict() for item in self.resource_policy_records],
            "newborn_protection_records": [dict(item) for item in self.newborn_protection_records],
            "population": self.population.to_dict(),
            "world_after": self.world_after.to_dict(),
            "world_before_digest": self.world_before_digest,
            "world_after_digest": self.world_after_digest,
            "traces": [trace.to_bundle() for trace in self.traces],
            "organism_records": [record.to_dict() for record in self.organism_records],
            "nexus_layer": None if self.nexus_layer is None else self.nexus_layer.to_dict(),
            "causal_summary": self.causal_summary.to_dict(),
            "selection_result": None
            if self.selection_result is None
            else self.selection_result.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, JsonValue]) -> GenerationResult:
        population_raw = data.get("population")
        world_raw = data.get("world_after")
        if not isinstance(population_raw, Mapping) or not isinstance(world_raw, Mapping):
            msg = "GenerationResult requires population and world_after objects."
            raise ConfigurationError(msg)
        return cls(
            before_count=_int(data, "before_count", 0),
            after_count=_int(data, "after_count", 0),
            births=_int(data, "births", 0),
            deaths=_int(data, "deaths", 0),
            reproduction_attempts=_int(data, "reproduction_attempts", 0),
            blocked_reproduction=_int(data, "blocked_reproduction", 0),
            mean_fitness=_float(data, "mean_fitness", 0.0),
            best_fitness=_float(data, "best_fitness", 0.0),
            population=PopulationState.from_dict(population_raw),
            world_after=World2D.from_dict(cast(dict[str, JsonValue], dict(world_raw))),
            world_before_digest=_str(data, "world_before_digest"),
            world_after_digest=_str(data, "world_after_digest"),
            traces=tuple(
                Trace.from_bundle(item)
                for item in _list(data, "traces")
                if isinstance(item, Mapping)
            ),
            organism_records=tuple(
                OrganismStepRecord.from_dict(item)
                for item in _list(data, "organism_records")
                if isinstance(item, Mapping)
            ),
            nexus_layer=NexusStigmergyLayer.from_dict(nexus_raw)
            if isinstance((nexus_raw := data.get("nexus_layer")), Mapping)
            else None,
            causal_summary=PopulationCausalSummary.from_dict(causal_raw)
            if isinstance((causal_raw := data.get("causal_summary")), Mapping)
            else PopulationCausalSummary(),
            selection_result=EvolutionSelectionResult.from_dict(selection_raw)
            if isinstance((selection_raw := data.get("selection_result")), Mapping)
            else None,
            raw_mean_fitness=_float(data, "raw_mean_fitness", _float(data, "mean_fitness", 0.0)),
            raw_best_fitness=_float(data, "raw_best_fitness", _float(data, "best_fitness", 0.0)),
            selection_mean_fitness=_float(data, "selection_mean_fitness", _float(data, "mean_fitness", 0.0)),
            selection_best_fitness=_float(data, "selection_best_fitness", _float(data, "best_fitness", 0.0)),
            viable_mean_fitness=_float(data, "viable_mean_fitness", 0.0),
            viable_best_fitness=_float(data, "viable_best_fitness", 0.0),
            viability_gate_failures=_int(data, "viability_gate_failures", 0),
            selection_zero_score_reasons={
                str(k): int(v)
                for k, v in dict(data.get("selection_zero_score_reasons", {})).items()
                if isinstance(v, int) and not isinstance(v, bool)
            } if isinstance(data.get("selection_zero_score_reasons", {}), Mapping) else {},
            mean_fitness_alias=_str(data, "mean_fitness_alias", "raw_mean_fitness"),
            best_fitness_alias=_str(data, "best_fitness_alias", "raw_best_fitness"),
            resource_policy_records=tuple(
                RuntimeResourceEvent.from_dict(item)
                for item in _list(data, "resource_policy_records")
                if isinstance(item, Mapping)
            ),
            newborn_protection_records=tuple(
                dict(item)
                for item in _list(data, "newborn_protection_records")
                if isinstance(item, Mapping)
            ),
        )

    def digest(self) -> str:
        payload = finite_json_dumps(self.to_dict(), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class PopulationConfigs:
    """Grouped configs for step_population and PopulationRunner."""

    reproduction: ReproductionConfig = field(default_factory=ReproductionConfig)
    mutation: MutationConfig = field(default_factory=lambda: MutationConfig(bit_flip_rate=0.01))
    structural_mutation: StructuralMutationConfig | None = None
    fitness: FitnessConfig = field(default_factory=FitnessConfig)
    alive_gate: AliveGateConfig = field(
        default_factory=lambda: AliveGateConfig(min_ticks=1, require_positive_runtime_atp=False)
    )
    ticks_per_generation: int = 1
    enable_max_age_death: bool = False
    max_age_ticks: int | None = None
    fatal_alive_reasons: tuple[str, ...] = ("negative_runtime_atp",)
    death_monitoring: DeathMonitoringConfig = field(default_factory=DeathMonitoringConfig)
    capsule_transfer: CapsuleTransferConfig | None = None
    enable_nexus_stigmergy: bool = False
    evolution: EvolutionConfig | None = None
    qd_mode: str = "archive_only"
    runtime_resource_policy: RuntimeResourcePolicy = field(default_factory=RuntimeResourcePolicy)
    newborn_protection_policy: str = "none"

    def __post_init__(self) -> None:
        if self.ticks_per_generation <= 0:
            msg = "ticks_per_generation must be > 0."
            raise ConfigurationError(msg)
        if self.max_age_ticks is not None and self.max_age_ticks <= 0:
            msg = "max_age_ticks must be > 0 when provided."
            raise ConfigurationError(msg)
        if self.qd_mode not in {"archive_only", "selection_pressure", "disabled"}:
            msg = "PopulationConfigs.qd_mode must be archive_only, selection_pressure, or disabled."
            raise ConfigurationError(msg)
        if self.newborn_protection_policy not in {"none", "protect_until_first_evaluation"}:
            msg = "newborn_protection_policy must be none or protect_until_first_evaluation."
            raise ConfigurationError(msg)
        legacy_overrides: dict[str, object] = {}
        if self.fatal_alive_reasons != ("negative_runtime_atp",):
            legacy_overrides["fatal_alive_reasons"] = self.fatal_alive_reasons
        if self.enable_max_age_death:
            legacy_overrides["enable_max_age_death"] = self.enable_max_age_death
            legacy_overrides["max_age_ticks"] = self.max_age_ticks
        elif self.max_age_ticks is not None:
            legacy_overrides["max_age_ticks"] = self.max_age_ticks
        if legacy_overrides:
            object.__setattr__(
                self,
                "death_monitoring",
                replace(self.death_monitoring, **legacy_overrides),
            )

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "reproduction": self.reproduction.to_dict(),
            "mutation": self.mutation.to_dict(),
            "structural_mutation": None
            if self.structural_mutation is None
            else self.structural_mutation.to_dict(),
            "fitness": self.fitness.to_dict(),
            "alive_gate": _alive_config_to_dict(self.alive_gate),
            "ticks_per_generation": self.ticks_per_generation,
            "enable_max_age_death": self.enable_max_age_death,
            "max_age_ticks": self.max_age_ticks,
            "fatal_alive_reasons": [reason for reason in self.fatal_alive_reasons],
            "death_monitoring": self.death_monitoring.to_dict(),
            "capsule_transfer": None
            if self.capsule_transfer is None
            else self.capsule_transfer.to_dict(),
            "enable_nexus_stigmergy": self.enable_nexus_stigmergy,
            "evolution": None if self.evolution is None else self.evolution.to_dict(),
            "qd_mode": self.qd_mode,
            "runtime_resource_policy": self.runtime_resource_policy.to_dict(),
            "newborn_protection_policy": self.newborn_protection_policy,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, JsonValue]) -> PopulationConfigs:
        reproduction_raw = data.get("reproduction", {})
        mutation_raw = data.get("mutation", {})
        structural_raw = data.get("structural_mutation")
        fitness_raw = data.get("fitness", {})
        alive_raw = data.get("alive_gate", {})
        capsule_transfer_raw = data.get("capsule_transfer")
        death_monitoring_raw = data.get("death_monitoring")
        evolution_raw = data.get("evolution")
        resource_policy_raw = data.get("runtime_resource_policy")
        return cls(
            reproduction=ReproductionConfig.from_dict(reproduction_raw)
            if isinstance(reproduction_raw, Mapping)
            else ReproductionConfig(),
            mutation=MutationConfig.from_dict(mutation_raw)
            if isinstance(mutation_raw, Mapping)
            else MutationConfig(bit_flip_rate=0.01),
            structural_mutation=StructuralMutationConfig.from_dict(structural_raw)
            if isinstance(structural_raw, Mapping)
            else None,
            fitness=FitnessConfig.from_dict(fitness_raw)
            if isinstance(fitness_raw, Mapping)
            else FitnessConfig(),
            alive_gate=_alive_config_from_dict(alive_raw)
            if isinstance(alive_raw, Mapping)
            else AliveGateConfig(min_ticks=1, require_positive_runtime_atp=False),
            ticks_per_generation=_int(data, "ticks_per_generation", 1),
            enable_max_age_death=_bool(data, "enable_max_age_death", False),
            max_age_ticks=None
            if data.get("max_age_ticks") is None
            else _int(data, "max_age_ticks", 0),
            fatal_alive_reasons=(
                _str_tuple(data, "fatal_alive_reasons")
                if "fatal_alive_reasons" in data
                else ("negative_runtime_atp",)
            ),
            death_monitoring=DeathMonitoringConfig.from_dict(dict(death_monitoring_raw))
            if isinstance(death_monitoring_raw, Mapping)
            else DeathMonitoringConfig(),
            capsule_transfer=CapsuleTransferConfig.from_dict(capsule_transfer_raw)
            if isinstance(capsule_transfer_raw, Mapping)
            else None,
            enable_nexus_stigmergy=_bool(data, "enable_nexus_stigmergy", False),
            evolution=EvolutionConfig.from_dict(evolution_raw)
            if isinstance(evolution_raw, Mapping)
            else None,
            qd_mode=_str(data, "qd_mode", "archive_only"),
            runtime_resource_policy=RuntimeResourcePolicy.from_dict(resource_policy_raw)
            if isinstance(resource_policy_raw, Mapping)
            else RuntimeResourcePolicy(),
            newborn_protection_policy=_str(data, "newborn_protection_policy", "none"),
        )


def mutate_genome(
    genome: SemanticGenome,
    config: MutationConfig,
    *,
    seed: int | None = None,
    rng: RNGManager | None = None,
) -> MutationResult:
    """Return a mutated genome plus metadata without mutating the input genome."""

    stream = _resolve_rng(seed=seed, rng=rng, namespace="genesis/mutation")
    spec = genome.spec
    symbols = list(genome.to_compact())
    operations: list[str] = []
    for index, symbol in enumerate(tuple(symbols)):
        if stream.random() < config.bit_flip_rate:
            choices = tuple(item for item in spec.alphabet if item != symbol)
            symbols[index] = stream.choice(choices)
            operations.append(f"flip:{index}")
    if stream.random() < config.insertion_rate:
        codon_count = max(1, len(symbols) // spec.codon_width)
        insert_codon_at = stream.randrange(codon_count + 1)
        insert_at = insert_codon_at * spec.codon_width
        codon = "".join(stream.choice(spec.alphabet) for _ in range(spec.codon_width))
        symbols[insert_at:insert_at] = list(codon)
        operations.append(f"insert:{insert_at}:{codon}")
    if len(symbols) > spec.codon_width and stream.random() < config.deletion_rate:
        codon_count = len(symbols) // spec.codon_width
        delete_codon_at = stream.randrange(codon_count)
        delete_at = delete_codon_at * spec.codon_width
        removed = "".join(symbols[delete_at : delete_at + spec.codon_width])
        del symbols[delete_at : delete_at + spec.codon_width]
        operations.append(f"delete:{delete_at}:{removed}")
    if config.max_genome_bits is not None and len(symbols) > config.max_genome_bits:
        cap = config.max_genome_bits - (config.max_genome_bits % spec.codon_width)
        if cap < spec.codon_width:
            msg = "max_genome_bits must leave at least one full codon."
            raise ConfigurationError(msg)
        removed_count = len(symbols) - cap
        del symbols[cap:]
        operations.append(f"trim:{removed_count}")
    complete_len = len(symbols) - (len(symbols) % spec.codon_width)
    if complete_len <= 0:
        msg = "Mutation cannot remove all complete codons."
        raise ConfigurationError(msg)
    compact = "".join(symbols[:complete_len])
    mutated = SemanticGenome.from_compact(compact, spec=spec)
    return MutationResult(
        original_genome=genome,
        mutated_genome=mutated,
        mutation_count=len(operations),
        operations=tuple(operations),
        rng_digest=stream.state_digest(),
    )


def evaluate_fitness(
    trace: Trace | Sequence[TraceEvent],
    alive_result: AliveGateResult,
    config: FitnessConfig,
    *,
    organism_id: str | None = None,
) -> FitnessResult:
    """Score a controlled run without mutating trace or organism state."""

    events = tuple(trace.events if isinstance(trace, Trace) else trace)
    resolved_id = organism_id or (events[0].agent_id if events else "unknown")
    status_registry = config.status_registry
    lumen_eaten = sum(
        1
        for event in events
        if event.action == "EAT_LUMEN"
        and status_registry.counts_as_executed(event.status)
        and event.world_delta.get("lumen_interaction") is True
    )
    nexus_emitted = sum(
        1
        for event in events
        if event.action == "EMIT_NEXUS" and status_registry.counts_as_executed(event.status)
    )
    reproduction_events = sum(
        1 for event in events if event.world_delta.get("reproduction_succeeded") is True
    )
    if config.signal_registry is None:
        score = (
            alive_result.survived_ticks * config.reward_survival_ticks
            + lumen_eaten * config.reward_lumen_eaten
            + nexus_emitted * config.reward_nexus_emitted
            + reproduction_events * config.reward_reproduction
            - alive_result.blocked_actions * config.penalty_blocked_action
        )
    else:
        score = config.signal_registry.score(
            events,
            context={
                "alive_result": alive_result,
                "organism_id": resolved_id,
                "status_registry": status_registry,
            },
        )
    reasons = list(alive_result.reasons)
    if alive_result.final_runtime_atp <= 0:
        score -= config.penalty_atp_starvation
        reasons.append("atp_starvation_penalty")
    raw_task_metrics = task_sensitive_raw_metrics(
        alive_result=alive_result,
        lumen_eaten=lumen_eaten,
        blocked_actions=alive_result.blocked_actions,
        reproduction_events=reproduction_events,
        capsules_emitted=nexus_emitted,
    )
    fitness_breakdown, selection_fitness_score = evaluate_task_sensitive_fitness(
        raw_task_metrics,
        organism_id=resolved_id,
        tick=events[-1].step if events else 0,
        viability_gate=raw_task_metrics["viability_score"],
    )
    return FitnessResult(
        organism_id=resolved_id,
        score=round(score, 10),
        survived_ticks=alive_result.survived_ticks,
        lumen_eaten=lumen_eaten,
        nexus_emitted=nexus_emitted,
        blocked_actions=alive_result.blocked_actions,
        reproduction_events=reproduction_events,
        reasons=tuple(reasons),
        fitness_breakdown=fitness_breakdown,
        selection_fitness_score=selection_fitness_score,
    )


def _has_valid_learning_evidence(parent: GenesisOrganism) -> bool:
    """Return whether learned-content inheritance has non-placeholder evidence.

    Runtime ATP ledgers alone are cost evidence, not learned-content evidence.
    Lamarckian transfer therefore requires at least one explicit memory, causal,
    capsule, or ADF source to avoid manufacturing a positive skill from a
    successful birth event.
    """

    if parent.episodic_memory is not None:
        for event in parent.episodic_memory.events:
            if event.status != "executed":
                continue
            reason = event.outcome.get("reason")
            if reason not in {None, "success", "executed"}:
                continue
            world_delta = event.outcome.get("world_delta", {})
            if isinstance(world_delta, dict) and world_delta.get("reproduction_succeeded") is False:
                continue
            return True
    graph = parent.causal_graph
    if graph is not None:
        raw_edges = getattr(graph, "edges", ())
        for edge in raw_edges:
            target = getattr(edge, "target", "")
            relation = getattr(edge, "relation", "")
            if "blocked" in str(target) or "block" in str(relation):
                continue
            if str(target).startswith(("reward:", "skill:", "tool:", "capsule:utility")):
                return True
    return parent.adf_macro_registry is not None and len(parent.adf_macro_registry.definitions) > 0


def _birth_intervention_records(
    *,
    parent_id: str,
    tick: int,
    config: ReproductionConfig,
    input_evidence_digest: str,
) -> tuple[AIBirthInterventionRecord, ...]:
    """Return deterministic intervention audit records without hidden AI behavior.

    The core library does not embed an external controller. When the
    intervention surface is enabled but no public controller hook is supplied,
    the request is logged as rejected so replay and ClaimGate can distinguish
    an explicit no-op from missing evidence.
    """

    if not config.enable_ai_birth_intervention:
        return ()
    event_names = (
        "before_birth_gate",
        "before_mutation_plan",
        "after_mutation_plan",
        "before_child_admission",
        "after_birth_event",
    )
    rows: list[AIBirthInterventionRecord] = []
    for event_name in event_names:
        decision_digest = make_policy_digest(
            {
                "event": event_name,
                "input_evidence_digest": input_evidence_digest,
                "library_role": "logged_no_embedded_controller",
                "parent_id": parent_id,
                "tick": tick,
            }
        )
        rows.append(
            AIBirthInterventionRecord(
                intervention_id=make_policy_digest(
                    {
                        "decision_digest": decision_digest,
                        "event": event_name,
                        "parent_id": parent_id,
                        "tick": tick,
                    }
                )[:24],
                controller_name="none",
                controller_version="0",
                input_evidence_digest=input_evidence_digest,
                decision_digest=decision_digest,
                applied=False,
                rejected_reason="external_controller_not_configured",
                scope="child_only",
                event=event_name,
            )
        )
    return tuple(rows)


def can_reproduce(
    organism: GenesisOrganism,
    alive_result: AliveGateResult,
    config: ReproductionConfig,
) -> ReproductionDecision:
    """Return whether a controlled COPY_SELF attempt may produce an offspring."""

    reasons: list[str] = []
    if not config.enabled:
        reasons.append("reproduction_disabled")
    if not config.allow_copy_self_action:
        reasons.append("copy_self_action_disabled")
    if not alive_result.passed:
        reasons.append("alive_gate_not_passed")
    if organism.atp_state.runtime_available < config.min_runtime_atp:
        reasons.append("min_runtime_atp_not_met")
    if organism.atp_state.runtime_available < config.parent_atp_cost:
        reasons.append("parent_atp_cost_not_payable")
    if organism.vitae_store < config.min_vitae_store:
        reasons.append("min_vitae_store_not_met")
    return ReproductionDecision(allowed=not reasons, reasons=tuple(reasons))


def _blocked_reproduction_result(
    *,
    parent: GenesisOrganism,
    config: ReproductionConfig,
    alive_result: AliveGateResult,
    birth_tick: int,
    generation: int,
    reason: str,
    capacity_available: bool,
) -> ReproductionResult:
    parent_after = _clone_organism(parent)
    birth_intent = BirthIntent(organism_id=parent.id, tick=birth_tick)
    birth_policy_digest = make_policy_digest(config.to_dict())
    event_id = _reproduction_event_id(parent.id, "blocked", birth_tick, reason)
    birth_request = BirthRequest(
        request_id=event_id,
        parent_id=parent.id,
        tick=birth_tick,
        parent_genome_digest=parent.genome.digest(),
        policy_digest=birth_policy_digest,
        intent_digest=birth_intent.digest(),
    )
    gate = ReproductionGateResult(
        parent_id=parent.id,
        tick=birth_tick,
        allowed=False,
        reasons=(reason,),
        parent_alive_before_copy_self=alive_result.passed,
        parent_runtime_atp_before_copy_self=parent.atp_state.runtime_available,
        parent_learning_atp_before_copy_self=parent.atp_state.learning_available,
        capacity_available=capacity_available,
        copy_self_action_detected=True,
        reproduction_enabled=config.enabled,
        min_runtime_atp_met=parent.atp_state.runtime_available >= config.min_runtime_atp,
        parent_cost_payable=parent.atp_state.runtime_available >= config.parent_atp_cost,
        offspring_fraction_valid=0.0 <= config.offspring_atp_fraction <= 1.0,
        min_runtime_atp_required=config.min_runtime_atp,
        parent_atp_cost=config.parent_atp_cost,
        offspring_atp_fraction=config.offspring_atp_fraction,
        population_capacity=config.max_population,
        child_placement_available=False if not capacity_available else None,
        placement_gate_evaluated=not capacity_available,
        placement_resolution_stage="gate" if not capacity_available else "not_applicable",
        placement_policy=config.offspring_placement.value,
    )
    child_admission = ChildAdmissionResult(
        child_id=f"{parent.id}-blocked-child",
        admitted=False,
        placement_cell=None,
        blocked_reason=reason,
    )
    birth_event = BirthEvent(
        birth_event_id=event_id,
        tick=birth_tick,
        parent_id=parent.id,
        child_id=None,
        parent_lineage_id=parent.id,
        child_lineage_id=None,
        parent_generation=generation,
        child_generation=None,
        parent_genome_digest=parent.genome.digest(),
        child_genome_digest=None,
        mutation_digest=None,
        mutation_count=0,
        mutation_operator_names=(),
        birth_cost_runtime_atp=0.0,
        birth_cost_learning_atp=0.0,
        child_initial_runtime_atp=None,
        child_initial_learning_atp=None,
        placement_cell=None,
        birth_policy_digest=birth_policy_digest,
        reproduction_gate_digest=gate.digest(),
        child_created=False,
        blocked_reason=reason,
    )
    return ReproductionResult(
        attempted=True,
        succeeded=False,
        parent_before_id=parent.id,
        parent_after=parent_after,
        child=None,
        mutation=None,
        lineage=None,
        decision=ReproductionDecision(False, (reason,)),
        event_id=event_id,
        ledger_entry_ids=(),
        birth_intent=birth_intent,
        birth_request=birth_request,
        reproduction_gate_result=gate,
        birth_event=birth_event,
        child_admission_result=child_admission,
        ai_birth_intervention_records=_birth_intervention_records(
            parent_id=parent.id,
            tick=birth_tick,
            config=config,
            input_evidence_digest=birth_request.digest(),
        ),
    )


def reproduce(
    parent: GenesisOrganism,
    config: ReproductionConfig,
    mutation_config: MutationConfig,
    *,
    alive_result: AliveGateResult | None = None,
    generation: int = 0,
    birth_tick: int = 0,
    seed: int | None = None,
    rng: RNGManager | None = None,
    child_id: str | None = None,
    structural_mutation_config: StructuralMutationConfig | None = None,
    world: World2D | None = None,
    live_positions: Mapping[str, tuple[int, int]] | None = None,
) -> ReproductionResult:
    """Create a controlled offspring with ATP debit, mutation, and lineage metadata.

    By default, direct reproduction requires an explicit AliveGateResult. This
    prevents low-level calls from silently bypassing operational liveness evidence.
    """

    parent_after = _clone_organism(parent)
    if alive_result is None:
        if config.require_alive_result:
            decision = ReproductionDecision(False, ("alive_result_required",))
            return ReproductionResult(
                attempted=True,
                succeeded=False,
                parent_before_id=parent.id,
                parent_after=parent_after,
                child=None,
                mutation=None,
                lineage=None,
                decision=decision,
                event_id=None,
                ledger_entry_ids=(),
            )
        alive_result = AliveGateResult(
            passed=True,
            survived_ticks=0,
            executed_actions=0,
            blocked_actions=0,
            blocked_ratio=0.0,
            final_runtime_atp=parent.atp_state.runtime_available,
            lumen_interactions=0,
            reproduction_events=0,
            reasons=("alive_result_not_required",),
        )
    decision = can_reproduce(parent, alive_result, config)
    stream = _resolve_rng(seed=seed, rng=rng, namespace=f"genesis/reproduction/{parent.id}")
    birth_intent = BirthIntent(organism_id=parent.id, tick=birth_tick)
    birth_policy_digest = make_policy_digest(config.to_dict())
    birth_request = BirthRequest(
        request_id=_reproduction_event_id(parent.id, "pending", birth_tick, birth_intent.digest()),
        parent_id=parent.id,
        tick=birth_tick,
        parent_genome_digest=parent.genome.digest(),
        policy_digest=birth_policy_digest,
        intent_digest=birth_intent.digest(),
    )
    ai_birth_records = _birth_intervention_records(
        parent_id=parent.id,
        tick=birth_tick,
        config=config,
        input_evidence_digest=birth_request.digest(),
    )
    reproduction_gate_result = ReproductionGateResult(
        parent_id=parent.id,
        tick=birth_tick,
        allowed=decision.allowed,
        reasons=decision.reasons,
        parent_alive_before_copy_self=alive_result.passed,
        parent_runtime_atp_before_copy_self=parent.atp_state.runtime_available,
        parent_learning_atp_before_copy_self=parent.atp_state.learning_available,
        capacity_available=True,
        copy_self_action_detected=True,
        reproduction_enabled=config.enabled,
        min_runtime_atp_met=parent.atp_state.runtime_available >= config.min_runtime_atp,
        parent_cost_payable=parent.atp_state.runtime_available >= config.parent_atp_cost,
        offspring_fraction_valid=0.0 <= config.offspring_atp_fraction <= 1.0,
        min_runtime_atp_required=config.min_runtime_atp,
        parent_atp_cost=config.parent_atp_cost,
        offspring_atp_fraction=config.offspring_atp_fraction,
        population_capacity=config.max_population,
        child_placement_available=True
        if config.offspring_placement is OffspringPlacementPolicy.SAME_CELL
        else None,
        placement_gate_evaluated=config.offspring_placement is OffspringPlacementPolicy.SAME_CELL,
        placement_resolution_stage=(
            "gate"
            if config.offspring_placement is OffspringPlacementPolicy.SAME_CELL
            else "admission"
        ),
        placement_policy=config.offspring_placement.value,
    )
    if not decision.allowed:
        return _blocked_reproduction_result(
            parent=parent,
            config=config,
            alive_result=alive_result,
            birth_tick=birth_tick,
            generation=generation,
            reason=decision.reasons[0] if decision.reasons else "reproduction_blocked",
            capacity_available=True,
        )
    precomputed_placement: tuple[int, int] | None = None
    if config.offspring_placement is not OffspringPlacementPolicy.SAME_CELL:
        if world is None or live_positions is None:
            return _blocked_reproduction_result(
                parent=parent,
                config=config,
                alive_result=alive_result,
                birth_tick=birth_tick,
                generation=generation,
                reason="placement_requires_world_context",
                capacity_available=True,
            )
        precomputed_placement = _resolve_offspring_position(
            parent_position=parent.position,
            child_id=child_id or "candidate_child",
            policy=config.offspring_placement,
            world=world,
            live_positions=live_positions,
        )
        if precomputed_placement is None:
            return _blocked_reproduction_result(
                parent=parent,
                config=config,
                alive_result=alive_result,
                birth_tick=birth_tick,
                generation=generation,
                reason="offspring_no_free_space",
                capacity_available=True,
            )
    stream = _resolve_rng(seed=seed, rng=rng, namespace=f"genesis/reproduction/{parent.id}")
    ledger_ids: list[int] = []
    debit_id = parent_after.atp_state.debit_runtime(
        config.parent_atp_cost,
        tick=birth_tick,
        organism_id=parent.id,
        codon="111",
        action="COPY_SELF",
        reason="parent_reproduction_cost",
    )
    if debit_id is None and config.parent_atp_cost > 0:
        blocked = ReproductionDecision(False, ("parent_atp_cost_not_payable",))
        return ReproductionResult(
            attempted=True,
            succeeded=False,
            parent_before_id=parent.id,
            parent_after=parent_after,
            child=None,
            mutation=None,
            lineage=None,
            decision=blocked,
            event_id=None,
            ledger_entry_ids=(),
            birth_intent=birth_intent,
            birth_request=birth_request,
            reproduction_gate_result=reproduction_gate_result,
            ai_birth_intervention_records=ai_birth_records,
        )
    if debit_id is not None:
        ledger_ids.append(debit_id)
    offspring_atp = round(
        parent_after.atp_state.runtime_available * config.offspring_atp_fraction, 10
    )
    if offspring_atp > 0:
        transfer_id = parent_after.atp_state.debit_runtime(
            offspring_atp,
            tick=birth_tick,
            organism_id=parent.id,
            codon="111",
            action="COPY_SELF",
            reason="offspring_runtime_atp_transfer",
        )
        if transfer_id is not None:
            ledger_ids.append(transfer_id)
    mutation_plan = build_mutation_plan(
        plan_id=_reproduction_event_id(
            parent.id, "mutation_plan", birth_tick, stream.state_digest()
        ),
        parent_genome_digest=parent.genome.digest(),
        bit_flip_rate=mutation_config.bit_flip_rate,
        insertion_rate=mutation_config.insertion_rate,
        deletion_rate=mutation_config.deletion_rate,
        rng_state_digest_before=stream.state_digest(),
    )
    if structural_mutation_config is not None:
        program = build_genome_program(
            parent.genome.to_compact(),
            codon_width=parent.genome.spec.codon_width,
            macro_registry_digest=None
            if parent.adf_macro_registry is None
            else parent.adf_macro_registry.digest(),
            lineage_tags=("runtime_structural_mutation",),
        )
        child_program, structural_record = mutate_genome_program(
            program,
            structural_mutation_config,
            rng=stream.fork("structural_mutation"),
        )
        if not child_program.viable:
            reason = "child_genome_nonviable"
            nonviable_detail = child_program.nonviable_reason or "nonviable"
            event_id = _reproduction_event_id(
                parent.id,
                "blocked_nonviable",
                birth_tick,
                make_policy_digest(
                    {
                        "birth_request_digest": birth_request.digest(),
                        "mutation_plan_digest": mutation_plan.digest(),
                        "nonviable_reason": nonviable_detail,
                    }
                ),
            )
            decision = ReproductionDecision(False, (reason, nonviable_detail))
            admission = ChildAdmissionResult(
                child_id=child_id or f"{parent.id}-blocked-nonviable",
                admitted=False,
                placement_cell=None,
                blocked_reason=reason,
            )
            mutation_audit = MutationAuditResult(
                plan_id=mutation_plan.plan_id,
                child_genome_digest=make_policy_digest({"nonviable_bits": child_program.bits}),
                applied_mutations=(f"structural:{structural_record.kind}:{structural_record.digest}",),
                rejected_mutations=(nonviable_detail,),
                mutation_count=1,
                mutation_digest=structural_record.digest,
                rng_state_digest_after=structural_record.rng_state_digest_after,
                validity_status="generated_nonviable_but_safe",
            )
            gate = replace(
                reproduction_gate_result,
                allowed=False,
                reasons=(reason, nonviable_detail),
                child_placement_available=False,
            )
            birth_event = BirthEvent(
                birth_event_id=event_id,
                tick=birth_tick,
                parent_id=parent.id,
                child_id=None,
                parent_lineage_id=parent.id,
                child_lineage_id=None,
                parent_generation=generation,
                child_generation=None,
                parent_genome_digest=parent.genome.digest(),
                child_genome_digest=None,
                mutation_digest=None,
                mutation_count=0,
                mutation_operator_names=(),
                birth_cost_runtime_atp=config.parent_atp_cost,
                birth_cost_learning_atp=0.0,
                child_initial_runtime_atp=None,
                child_initial_learning_atp=None,
                placement_cell=None,
                birth_policy_digest=birth_policy_digest,
                reproduction_gate_digest=gate.digest(),
                child_created=False,
                blocked_reason=reason,
            )
            return ReproductionResult(
                attempted=True,
                succeeded=False,
                parent_before_id=parent.id,
                parent_after=parent_after,
                child=None,
                mutation=None,
                lineage=None,
                decision=decision,
                event_id=event_id,
                ledger_entry_ids=tuple(ledger_ids),
                birth_intent=birth_intent,
                birth_request=birth_request,
                reproduction_gate_result=gate,
                mutation_plan=mutation_plan,
                mutation_audit_result=mutation_audit,
                child_admission_result=admission,
                birth_event=birth_event,
                ai_birth_intervention_records=ai_birth_records,
            )
        mutated_genome = SemanticGenome.from_compact(child_program.bits, spec=parent.genome.spec)
        mutation = MutationResult(
            original_genome=parent.genome,
            mutated_genome=mutated_genome,
            mutation_count=1,
            operations=(f"structural:{structural_record.kind}:{structural_record.digest}",),
            rng_digest=structural_record.rng_state_digest_after,
        )
    else:
        mutation = mutate_genome(parent.genome, mutation_config, rng=stream.fork("mutation"))
    mutation_audit = MutationAuditResult(
        plan_id=mutation_plan.plan_id,
        child_genome_digest=mutation.mutated_genome.digest(),
        applied_mutations=mutation.operations,
        mutation_count=mutation.mutation_count,
        mutation_digest=mutation.digest(),
        rng_state_digest_after=mutation.rng_digest,
        validity_status="valid",
        repair_applied=any(item.startswith("repair") for item in mutation.operations),
    )
    resolved_child_id = child_id or (
        f"{parent.id}-g{generation + 1}-{mutation.mutated_genome.digest()[:10]}"
    )
    translation = parent.ribosome.translate(mutation.mutated_genome)
    child_learning_enabled = (
        parent.atp_state.learning_enabled
        or parent.learning_config.learning_enabled
        or parent.causal_graph is not None
        or parent.episodic_memory is not None
    )
    child = GenesisOrganism(
        id=resolved_child_id,
        genome=mutation.mutated_genome,
        ribosome=parent.ribosome,
        compiled_brain=translation.compiled_brain,
        atp_state=GenesisATPState.from_runtime(
            offspring_atp,
            learning_atp=0.0,
            learning_enabled=child_learning_enabled,
        ),
        position=precomputed_placement or parent.position,
        vitae_store=0.0,
        action_registry=parent.action_registry,
        action_runtime_config=parent.action_runtime_config,
        episodic_memory=EpisodicMemory(parent.memory_config)
        if parent.episodic_memory is not None
        else None,
        memory_config=parent.memory_config,
        learning_config=parent.learning_config,
        causal_graph=CausalGraph(config=parent.causal_graph.config)
        if parent.causal_graph is not None
        else None,
        execution_source_enabled=parent.execution_source_enabled,
        adf_macro_registry=parent.adf_macro_registry
        if config.adf_inheritance_mode
        in {ADFInheritanceMode.INHERIT_MACROS, ADFInheritanceMode.MUTATE_MACROS}
        else None,
        adf_execution_policy=parent.adf_execution_policy,
        translation_profile=None
        if parent.translation_profile is None
        else inherit_translation_profile(
            parent.translation_profile, child_profile_id=f"{resolved_child_id}:translation_profile"
        ),
        translation_policy=parent.translation_policy,
    )
    event_id = _reproduction_event_id(parent.id, resolved_child_id, birth_tick, mutation.digest())
    lineage = LineageRecord(
        organism_id=resolved_child_id,
        parent_id=parent.id,
        generation=generation + 1,
        genome_digest=child.genome.digest(),
        mutation_count=mutation.mutation_count,
        birth_tick=birth_tick,
        death_tick=None,
        reproduction_event_id=event_id,
    )
    child_genome_result = ChildGenomeResult(
        child_id=resolved_child_id,
        parent_id=parent.id,
        parent_genome_digest=parent.genome.digest(),
        child_genome_digest=child.genome.digest(),
        mutation_digest=mutation.digest(),
        mutation_count=mutation.mutation_count,
        genome_bits=child.genome.to_compact(),
    )
    child_admission = ChildAdmissionResult(
        child_id=resolved_child_id,
        admitted=True,
        placement_cell=child.position,
    )
    lamarckian_transfer_requested = (
        config.inheritance_policy is InheritancePolicy.LAMARCKIAN_COMPRESSED_LEARNING
        and config.enable_lamarckian_learning_inheritance
        and config.skill_inheritance_mode
        in {SkillInheritanceMode.COMPRESSED_SKILL, SkillInheritanceMode.GENOME_ASSIMILATED_SKILL}
    )
    skill_has_learning_evidence = _has_valid_learning_evidence(parent)
    inherited_learned_content = lamarckian_transfer_requested and skill_has_learning_evidence
    skill_digest = (
        make_policy_digest(
            {
                "causal_graph_digest": None
                if parent.causal_graph is None
                else parent.causal_graph.digest(),
                "memory_digest": None
                if parent.episodic_memory is None
                else parent.episodic_memory.digest(),
                "parent_genome_digest": parent.genome.digest(),
                "parent_id": parent.id,
                "validation": "evidence_backed"
                if skill_has_learning_evidence
                else "candidate_rejected_no_learning_evidence",
            }
        )
        if lamarckian_transfer_requested
        else None
    )
    learning_inheritance = LearningInheritanceRecord(
        parent_id=parent.id,
        child_id=resolved_child_id,
        tick=birth_tick,
        inheritance_policy=config.inheritance_policy.value,
        learning_capacity_inherited=child_learning_enabled,
        learned_content_inherited=inherited_learned_content,
        inheritance_type=(
            "lamarckian_compressed"
            if inherited_learned_content
            else (
                "baldwinian_selection_pressure"
                if config.inheritance_policy is InheritancePolicy.BALDWINIAN
                else "genetic_only"
            )
        ),
        source_lifetime_evidence_digest=trace_digest
        if (trace_digest := parent.atp_state.runtime.ledger_digest())
        else None,
        compressed_skill_digest=skill_digest,
        child_received_skill_digest=skill_digest if inherited_learned_content else None,
        learning_success_score=None,
        learning_efficiency_score=None,
        memory_use_score=None,
        delayed_reward_score=None,
        baldwinian_selection_pressure=config.inheritance_policy is InheritancePolicy.BALDWINIAN,
    )
    skill_rejected_reason = None
    if not lamarckian_transfer_requested:
        skill_rejected_reason = "skill_inheritance_not_enabled"
    elif not skill_has_learning_evidence:
        skill_rejected_reason = "no_valid_learning_evidence"
    skill_compression = SkillCompressionRecord(
        parent_id=parent.id,
        child_id=resolved_child_id,
        tick=birth_tick,
        mode=config.skill_inheritance_mode.value,
        successful_behavior_trace_digest=learning_inheritance.source_lifetime_evidence_digest,
        compressed_skill_digest=skill_digest,
        validation_status="validated" if inherited_learned_content else "rejected",
        fitness_delta_positive=inherited_learned_content,
        energy_efficiency_positive=inherited_learned_content,
        replay_successful=inherited_learned_content,
        inherited=inherited_learned_content,
        rejected_reason=skill_rejected_reason,
    )
    parent_adf_digest = (
        None if parent.adf_macro_registry is None else parent.adf_macro_registry.digest()
    )
    child_adf_digest = (
        None if child.adf_macro_registry is None else child.adf_macro_registry.digest()
    )
    adf_inheritance = ADFInheritanceRecord(
        parent_id=parent.id,
        child_id=resolved_child_id,
        tick=birth_tick,
        parent_adf_digest=parent_adf_digest,
        child_adf_digest=child_adf_digest,
        adf_inheritance_mode=config.adf_inheritance_mode.value,
        adf_macro_count_parent=0
        if parent.adf_macro_registry is None
        else len(parent.adf_macro_registry.definitions),
        adf_macro_count_child=0
        if child.adf_macro_registry is None
        else len(child.adf_macro_registry.definitions),
        adf_mutation_applied=config.adf_inheritance_mode is ADFInheritanceMode.MUTATE_MACROS,
        adf_skill_imported=(
            inherited_learned_content
            and config.adf_inheritance_mode
            is ADFInheritanceMode.COMPRESS_SUCCESSFUL_BEHAVIOR_TO_ADF
            and parent_adf_digest is not None
            and child_adf_digest is not None
        ),
    )
    birth_event = BirthEvent(
        birth_event_id=event_id,
        tick=birth_tick,
        parent_id=parent.id,
        child_id=resolved_child_id,
        parent_lineage_id=parent.id,
        child_lineage_id=lineage.organism_id,
        parent_generation=generation,
        child_generation=generation + 1,
        parent_genome_digest=parent.genome.digest(),
        child_genome_digest=child.genome.digest(),
        mutation_digest=mutation.digest(),
        mutation_count=mutation.mutation_count,
        mutation_operator_names=mutation.operations,
        birth_cost_runtime_atp=config.parent_atp_cost,
        birth_cost_learning_atp=0.0,
        child_initial_runtime_atp=child.atp_state.runtime_available,
        child_initial_learning_atp=child.atp_state.learning_available,
        placement_cell=child.position,
        birth_policy_digest=birth_policy_digest,
        reproduction_gate_digest=reproduction_gate_result.digest(),
        child_created=True,
    )
    return ReproductionResult(
        attempted=True,
        succeeded=True,
        parent_before_id=parent.id,
        parent_after=parent_after,
        child=child,
        mutation=mutation,
        lineage=lineage,
        decision=decision,
        event_id=event_id,
        ledger_entry_ids=tuple(ledger_ids),
        birth_intent=birth_intent,
        birth_request=birth_request,
        reproduction_gate_result=reproduction_gate_result,
        mutation_plan=mutation_plan,
        mutation_audit_result=mutation_audit,
        child_genome_result=child_genome_result,
        child_admission_result=child_admission,
        birth_event=birth_event,
        learning_inheritance_record=learning_inheritance,
        skill_compression_record=skill_compression,
        adf_inheritance_record=adf_inheritance,
        ai_birth_intervention_records=ai_birth_records,
        parent_build_cost_charged=config.parent_atp_cost > 0,
        offspring_transfer_charged=config.offspring_atp_fraction > 0,
        action_cost_charged=False,
    )


def step_population(
    population: PopulationState,
    world: object,
    configs: PopulationConfigs,
    *,
    seed: int | None = None,
    rng: RNGManager | None = None,
    nexus_layer: NexusStigmergyLayer | None = None,
) -> GenerationResult:
    """Step one deterministic generation without mutating caller-owned inputs."""

    if not isinstance(world, World2D):
        msg = "step_population currently expects a World2D instance."
        raise ConfigurationError(msg)
    stream = _resolve_rng(seed=seed, rng=rng, namespace="genesis/population")
    working_world = world.clone()
    world_before_digest = world.digest()
    before_count = len(population.organisms)
    lineage = _ensure_lineage(population)
    lineage_by_id = {record.organism_id: record for record in lineage}
    last_known_fitness_by_id = {record.organism_id: record.score for record in population.fitness}
    organism_clones = [_clone_organism(organism) for organism in population.organisms]
    live_positions: dict[str, tuple[int, int]] = {
        item.id: item.position for item in organism_clones
    }
    survivors: list[GenesisOrganism] = []
    children: list[GenesisOrganism] = []
    fitness_results: list[FitnessResult] = []
    traces: list[Trace] = []
    records: list[OrganismStepRecord] = []
    births = 0
    deaths = 0
    attempts = 0
    blocked_reproduction = 0
    current_tick = population.tick
    stigmergy_enabled = configs.enable_nexus_stigmergy or (
        configs.capsule_transfer is not None and configs.capsule_transfer.enabled
    )
    working_nexus_layer = (
        NexusStigmergyLayer.from_dict(nexus_layer.to_dict())
        if nexus_layer is not None
        else (NexusStigmergyLayer() if stigmergy_enabled else None)
    )

    for organism in sorted(organism_clones, key=lambda item: item.id):
        if organism.id not in live_positions:
            continue
        trace = Trace()
        runtime_before = organism.atp_state.runtime_available
        runtime_ledger_before = organism.atp_state.runtime.ledger_digest()
        learning_available_before = organism.atp_state.learning_available
        learning_ledger_before = (
            None
            if organism.atp_state.learning is None
            else organism.atp_state.learning.ledger_digest()
        )
        memory_digest_before = (
            None if organism.episodic_memory is None else organism.episodic_memory.digest()
        )
        memory_size_before = (
            0 if organism.episodic_memory is None else len(organism.episodic_memory.events)
        )
        organism_world_before_digest = working_world.digest()
        alive_result = AliveGateResult(
            passed=False,
            survived_ticks=0,
            executed_actions=0,
            blocked_actions=0,
            blocked_ratio=0.0,
            final_runtime_atp=organism.atp_state.runtime_available,
            lumen_interactions=0,
            reproduction_events=0,
            reasons=("not_evaluated",),
        )
        reproduction_result: ReproductionResult | None = None
        capsule_emit_count = 0
        capsule_emit_counts_by_tick: dict[int, int] = {}
        capsule_read_count = 0
        capsule_adoption_attempts = 0
        capsule_adoption_successes = 0
        capsule_adoption_failures = 0
        capsule_transfer_metrics: list[CapsuleTransferMetric] = []
        capsule_adoption_records: list[CapsuleAdoptionRecord] = []
        capsule_shuffle_records: list[CapsuleShuffleRecord] = []
        nexus_signal_count_before = (
            0 if working_nexus_layer is None else len(working_nexus_layer.signals)
        )
        capsule_store_digest_before = (
            None if working_nexus_layer is None else working_nexus_layer.digest()
        )
        for _ in range(configs.ticks_per_generation):
            if working_nexus_layer is not None and stigmergy_enabled:
                working_nexus_layer.expire(current_tick)
                if configs.capsule_transfer is not None and configs.capsule_transfer.enabled:
                    read_result = read_nexus_capsules(
                        organism,
                        working_nexus_layer,
                        organism.atp_state,
                        configs.capsule_transfer,
                        tick=current_tick,
                    )
                    capsule_read_count += len(read_result.capsules_read)
                    capsule_shuffle_records.extend(read_result.shuffle_records)
                    adoption_policy = CausalCapsuleAdoptionPolicy()
                    for capsule in read_result.capsules_read[
                        : configs.capsule_transfer.max_adoptions_per_organism
                    ]:
                        capsule_adoption_attempts += 1
                        attempt_runtime_atp_before = organism.atp_state.runtime_available
                        attempt_learning_atp_before = organism.atp_state.learning_available
                        if organism.causal_graph is None:
                            capsule_adoption_failures += 1
                            capsule_adoption_records.append(
                                CapsuleAdoptionRecord(
                                    capsule_id=capsule.capsule_id,
                                    source_organism_id=capsule.source_organism_id,
                                    target_organism_id=organism.id,
                                    emitted_tick=capsule.emitted_tick,
                                    read_tick=current_tick,
                                    adoption_attempt_tick=current_tick,
                                    adoption_success=False,
                                    blocked_reason=CapsuleAdoptionBlockedReason.GRAPH_DIGEST_REJECTED.value,
                                    source_fitness=capsule.source_fitness,
                                    source_fitness_status=capsule.source_fitness_status,
                                    confidence=capsule.confidence,
                                    runtime_atp_before=attempt_runtime_atp_before,
                                    learning_atp_before=attempt_learning_atp_before,
                                    runtime_atp_after=organism.atp_state.runtime_available,
                                    learning_atp_after=organism.atp_state.learning_available,
                                )
                            )
                            continue
                        pre_graph_digest = organism.causal_graph.digest()
                        adoption_result = adoption_policy.apply(
                            organism,
                            capsule,
                            organism.causal_graph,
                            organism.episodic_memory,
                            organism.atp_state,
                            configs.capsule_transfer,
                            tick=current_tick,
                        )
                        if adoption_result.succeeded:
                            capsule_adoption_successes += 1
                        else:
                            capsule_adoption_failures += 1
                        capsule_adoption_records.append(
                            build_capsule_adoption_record(
                                capsule=capsule,
                                result=adoption_result,
                                read_tick=current_tick,
                                adoption_attempt_tick=current_tick,
                                runtime_atp_before=attempt_runtime_atp_before,
                                learning_atp_before=attempt_learning_atp_before,
                            )
                        )
                        capsule_transfer_metrics.append(
                            estimate_capsule_transfer_effect(
                                source_capsule_id=capsule.capsule_id,
                                target_organism_id=organism.id,
                                pre_graph_digest=pre_graph_digest,
                                post_graph_digest=adoption_result.graph_digest_after,
                                confidence=capsule.confidence,
                            )
                        )
                else:
                    read_radius = (
                        1
                        if configs.capsule_transfer is None
                        else configs.capsule_transfer.read_radius
                    )
                    max_read = (
                        4
                        if configs.capsule_transfer is None
                        else configs.capsule_transfer.effective_max_capsules_read_per_tick
                    )
                    nearby_capsules = working_nexus_layer.store.nearby(
                        organism.position, read_radius, tick=current_tick
                    )[:max_read]
                    capsule_read_count += len(nearby_capsules)
            blocked_positions = tuple(
                sorted(position for oid, position in live_positions.items() if oid != organism.id)
            )
            event = organism.step(working_world, trace, blocked_positions=blocked_positions)
            live_positions[organism.id] = organism.position
            if (
                working_nexus_layer is not None
                and stigmergy_enabled
                and organism.action_runtime_config.counts_as_executed(event.status)
                and _event_requests_capsule_emit(event, configs.capsule_transfer)
            ):
                ttl = (
                    32 if configs.capsule_transfer is None else configs.capsule_transfer.capsule_ttl
                )
                emits_this_tick = capsule_emit_counts_by_tick.get(current_tick, 0)
                emit_allowed, emit_reason, runtime_ledger_id, learning_ledger_id = (
                    _pay_capsule_emit_cost(
                        organism, configs.capsule_transfer, current_tick, emits_this_tick
                    )
                )
                if emit_allowed:
                    source_fitness = last_known_fitness_by_id.get(organism.id)
                    source_status = (
                        SourceFitnessStatus.LAST_KNOWN
                        if source_fitness is not None
                        else SourceFitnessStatus.UNAVAILABLE
                    )
                    if source_fitness is None:
                        provisional_alive = evaluate_alive(
                            trace,
                            final_runtime_atp=organism.atp_state.runtime_available,
                            config=configs.alive_gate,
                        )
                        provisional_fitness = evaluate_fitness(
                            trace, provisional_alive, configs.fitness, organism_id=organism.id
                        )
                        source_fitness = provisional_fitness.score
                        source_status = SourceFitnessStatus.PROVISIONAL
                    capsule = _capsule_from_nexus_event(
                        organism,
                        event,
                        current_tick,
                        ttl=ttl,
                        source_fitness=source_fitness,
                        source_fitness_status=source_status,
                    )
                    working_nexus_layer.deposit(capsule, position=organism.position)
                    capsule_emit_count += 1
                    capsule_emit_counts_by_tick[current_tick] = emits_this_tick + 1
                    event.world_delta.update(
                        {
                            "nexus_layer_deposited": True,
                            "nexus_signals_deposited": 1,
                            "capsule_id": capsule.capsule_id,
                            "capsule_transfer_status": "capsule_emitted_phase2",
                            "capsule_emit_runtime_ledger_entry_id": runtime_ledger_id,
                            "capsule_emit_learning_ledger_entry_id": learning_ledger_id,
                            "capsule_source_fitness": capsule.source_fitness,
                            "capsule_source_fitness_status": (
                                capsule.source_fitness_status.value
                                if isinstance(capsule.source_fitness_status, SourceFitnessStatus)
                                else str(capsule.source_fitness_status)
                            ),
                        }
                    )
                else:
                    event.world_delta.update(
                        {
                            "nexus_layer_deposited": False,
                            "nexus_signals_deposited": 0,
                            "capsule_transfer_status": "capsule_emit_blocked",
                            "capsule_emit_blocked_reason": emit_reason,
                        }
                    )
            current_tick += 1
            alive_result = evaluate_alive(
                trace,
                final_runtime_atp=organism.atp_state.runtime_available,
                config=configs.alive_gate,
            )
            if (
                event.action == "COPY_SELF"
                and event.world_delta.get("reproduction") == "population_lifecycle_required"
                and configs.reproduction.ignore_deferred_copy_self_block_for_alive_gate
            ):
                deferred_delta = dict(event.world_delta)
                deferred_delta.update(
                    {
                        "reproduction_lifecycle_status": "deferred_to_population_lifecycle",
                        "counts_as_blocked_for_reproduction": False,
                        "counts_as_reproduction_attempt": True,
                    }
                )
                event = replace(event, world_delta=deferred_delta)
                _replace_last_event(trace, event)
                filtered_reasons = tuple(
                    reason
                    for reason in alive_result.reasons
                    if reason not in {"blocked_ratio_exceeded", "min_executed_actions_not_met"}
                )
                alive_result = replace(
                    alive_result,
                    passed=not filtered_reasons,
                    reasons=filtered_reasons or ("copy_self_deferred_to_population_lifecycle",),
                    blocked_actions=max(0, alive_result.blocked_actions - 1),
                    blocked_ratio=0.0,
                )
            if event.action == "COPY_SELF":
                attempts += 1
                if len(live_positions) >= configs.reproduction.max_population:
                    blocked_reproduction += 1
                    reproduction_result = _blocked_reproduction_result(
                        parent=organism,
                        config=configs.reproduction,
                        alive_result=alive_result,
                        birth_tick=current_tick,
                        generation=population.generation,
                        reason="max_population_reached",
                        capacity_available=False,
                    )
                    _replace_last_event(
                        trace,
                        _with_reproduction_delta(
                            event,
                            parent_after=organism,
                            reproduction_result=reproduction_result,
                            succeeded=False,
                            reason="max_population_reached",
                            parent_id=organism.id,
                            child_id=None,
                            event_id=reproduction_result.event_id,
                        ),
                    )
                    continue
                reproduction_result = reproduce(
                    organism,
                    configs.reproduction,
                    configs.mutation,
                    alive_result=alive_result,
                    generation=population.generation,
                    birth_tick=current_tick,
                    rng=stream.fork(f"reproduce/{organism.id}/{current_tick}"),
                    structural_mutation_config=configs.structural_mutation,
                    world=working_world,
                    live_positions=live_positions,
                )
                if reproduction_result.succeeded and reproduction_result.child is not None:
                    births += 1
                    organism = reproduction_result.parent_after
                    live_positions[organism.id] = organism.position
                    child = reproduction_result.child
                    placement = _resolve_offspring_position(
                        parent_position=organism.position,
                        child_id=child.id,
                        policy=configs.reproduction.offspring_placement,
                        world=working_world,
                        live_positions=live_positions,
                    )
                    if placement is None:
                        blocked_reproduction += 1
                        births -= 1
                        reproduction_result = _mark_reproduction_placement_blocked(
                            reproduction_result,
                            reason="offspring_no_free_space",
                            policy=configs.reproduction.offspring_placement,
                        )
                        _replace_last_event(
                            trace,
                            _with_reproduction_delta(
                                event,
                                parent_after=organism,
                                reproduction_result=reproduction_result,
                                succeeded=False,
                                reason="offspring_no_free_space",
                                parent_id=organism.id,
                                child_id=None,
                                event_id=reproduction_result.event_id,
                            ),
                        )
                        continue
                    child.position = placement
                    reproduction_result = _finalize_reproduction_placement(
                        reproduction_result,
                        placement=placement,
                        policy=configs.reproduction.offspring_placement,
                    )
                    child = reproduction_result.child
                    if child is None:
                        raise RuntimeError("finalized reproduction unexpectedly lost child")
                    children.append(child)
                    live_positions[child.id] = child.position
                    if reproduction_result.lineage is not None:
                        lineage += (reproduction_result.lineage,)
                    _replace_last_event(
                        trace,
                        _with_reproduction_delta(
                            event,
                            parent_after=organism,
                            reproduction_result=reproduction_result,
                            succeeded=True,
                            reason="reproduction_succeeded",
                            parent_id=organism.id,
                            child_id=child.id,
                            event_id=reproduction_result.event_id,
                        ),
                    )
                else:
                    blocked_reproduction += 1
                    reasons = reproduction_result.decision.reasons if reproduction_result else ()
                    _replace_last_event(
                        trace,
                        _with_reproduction_delta(
                            event,
                            parent_after=organism,
                            reproduction_result=reproduction_result,
                            succeeded=False,
                            reason=";".join(reasons) or "reproduction_blocked",
                            parent_id=organism.id,
                            child_id=None,
                            event_id=None,
                        ),
                    )
        alive_result = evaluate_alive(
            trace,
            final_runtime_atp=organism.atp_state.runtime_available,
            config=configs.alive_gate,
        )
        fitness_result = evaluate_fitness(
            trace, alive_result, configs.fitness, organism_id=organism.id
        )
        tool_chain_state = evaluate_tool_chain_state(trace)
        social_interaction_records = tuple(
            sorted(
                social_events_from_capsule_records(capsule_adoption_records, tick=current_tick)
                + social_events_from_trace(trace, organism_id=organism.id, tick=current_tick)
                + social_events_from_local_resource_context(
                    trace,
                    organism_id=organism.id,
                    live_positions=dict(live_positions),
                    tick=current_tick,
                ),
                key=lambda item: (
                    item.tick,
                    item.source_organism_id,
                    item.target_organism_id,
                    item.interaction_type,
                    item.event_id,
                ),
            )
        )
        raw_task_metrics = task_sensitive_raw_metrics(
            alive_result=alive_result,
            lumen_eaten=fitness_result.lumen_eaten,
            blocked_actions=fitness_result.blocked_actions,
            reproduction_events=fitness_result.reproduction_events,
            memory_write_count=max(
                0,
                (0 if organism.episodic_memory is None else len(organism.episodic_memory.events))
                - memory_size_before,
            ),
            memory_read_count=_trace_bool_count(trace, "memory_read"),
            delayed_reward_count=_trace_bool_count(trace, "correct_delayed_action"),
            capsules_emitted=capsule_emit_count,
            capsules_read=capsule_read_count,
            capsules_adopted=capsule_adoption_successes,
            social_interaction_count=len(social_interaction_records),
            cooperation_events=sum(
                1
                for item in social_interaction_records
                if item.interaction_type
                in {
                    "capsule_teaching",
                    "capsule_learning",
                    "cooperative_task_progress",
                    "partner_help",
                }
            ),
            tool_chain_stage=tool_chain_state.stage,
            novelty_score=0.0,
        )
        fitness_breakdown, selection_fitness_score = evaluate_task_sensitive_fitness(
            raw_task_metrics,
            organism_id=organism.id,
            tick=current_tick,
            viability_gate=raw_task_metrics["viability_score"],
        )
        fitness_result = replace(
            fitness_result,
            fitness_breakdown=fitness_breakdown,
            selection_fitness_score=selection_fitness_score,
        )
        fitness_results.append(fitness_result)
        last_known_fitness_by_id[organism.id] = fitness_result.score
        organism_world_after_digest = working_world.digest()
        behavior_descriptor = describe_behavior(
            trace,
            alive_result,
            organism.atp_state,
            social_interaction_count=len(social_interaction_records),
            partner_interaction_count=sum(
                1 for item in social_interaction_records
                if item.source_organism_id != item.target_organism_id
            ),
        )
        memory_digest_after = (
            None if organism.episodic_memory is None else organism.episodic_memory.digest()
        )
        memory_size_after = (
            0 if organism.episodic_memory is None else len(organism.episodic_memory.events)
        )
        causal_graph_digest_before = _first_world_delta_str(trace, "causal_graph_digest_before")
        causal_graph_digest_after = (
            None if organism.causal_graph is None else organism.causal_graph.digest()
        ) or _last_world_delta_str(trace, "causal_graph_digest_after")
        causal_graph_update_attempts = _trace_bool_count(trace, "causal_graph_update_attempted")
        causal_graph_update_successes = _trace_bool_count(trace, "causal_graph_update_succeeded")
        causal_prediction_attempted = _trace_bool_count(trace, "causal_prediction_attempted")
        causal_prediction_correct = _trace_bool_count(trace, "causal_prediction_correct")
        atp_learning_spent = round(
            max(0.0, learning_available_before - organism.atp_state.learning_available), 10
        )
        traces.append(trace)
        blocked_action_reasons = tuple(
            event.reason or "unknown" for event in trace.events if event.status == "blocked"
        )
        lineage_record = lineage_by_id.get(organism.id)
        death_classification = classify_death(
            organism_id=organism.id,
            tick=current_tick,
            runtime_atp_before=runtime_before,
            runtime_atp_after=organism.atp_state.runtime_available,
            alive_result=alive_result,
            birth_tick=None if lineage_record is None else lineage_record.birth_tick,
            config=configs.death_monitoring,
            blocked_action_reasons=blocked_action_reasons,
        )
        step_record = OrganismStepRecord(
            organism_id=organism.id,
            trace_digest=trace.digest(),
            genome_digest=organism.genome.digest(),
            runtime_atp_before=runtime_before,
            runtime_atp_after=organism.atp_state.runtime_available,
            alive_result=alive_result,
            fitness_result=fitness_result,
            reproduction_result=reproduction_result,
            world_before_digest=organism_world_before_digest,
            world_after_digest=organism_world_after_digest,
            runtime_ledger_digest_before=runtime_ledger_before,
            runtime_ledger_digest_after=organism.atp_state.runtime.ledger_digest(),
            learning_ledger_digest_before=learning_ledger_before,
            learning_ledger_digest_after=None
            if organism.atp_state.learning is None
            else organism.atp_state.learning.ledger_digest(),
            memory_digest_before=memory_digest_before,
            memory_digest_after=memory_digest_after,
            memory_write_count=max(0, memory_size_after - memory_size_before),
            learning_update_attempts=0,
            learning_update_successes=0,
            behavior_descriptor=behavior_descriptor,
            causal_graph_digest_before=causal_graph_digest_before,
            causal_graph_digest_after=causal_graph_digest_after,
            causal_graph_update_attempts=causal_graph_update_attempts,
            causal_graph_update_successes=causal_graph_update_successes,
            causal_graph_update_blocked_reason=_last_world_delta_str(
                trace, "causal_graph_update_reason"
            ),
            causal_prediction_attempted=causal_prediction_attempted,
            causal_prediction_correct=causal_prediction_correct,
            capsules_emitted=capsule_emit_count,
            capsules_read=capsule_read_count,
            capsules_adopted=capsule_adoption_successes,
            capsule_emit_count=capsule_emit_count,
            capsule_read_count=capsule_read_count,
            capsule_adoption_attempts=capsule_adoption_attempts,
            capsule_adoption_successes=capsule_adoption_successes,
            capsule_adoption_failures=capsule_adoption_failures,
            nexus_signal_count_before=nexus_signal_count_before,
            nexus_signal_count_after=0
            if working_nexus_layer is None
            else len(working_nexus_layer.signals),
            capsule_store_digest_before=capsule_store_digest_before,
            capsule_store_digest_after=None
            if working_nexus_layer is None
            else working_nexus_layer.digest(),
            nexus_signals_deposited=capsule_emit_count,
            atp_learning_spent=atp_learning_spent,
            capsule_transfer_metrics=tuple(capsule_transfer_metrics),
            capsule_adoption_records=tuple(capsule_adoption_records),
            capsule_shuffle_records=tuple(capsule_shuffle_records),
            social_interaction_records=tuple(social_interaction_records),
            fitness_breakdown=fitness_breakdown,
            selection_fitness_score=selection_fitness_score,
            death_classification=death_classification,
        )
        records.append(step_record)
        if death_classification.actual_death_removed_from_population:
            deaths += 1
            lineage = _mark_death(lineage, organism.id, current_tick)
            live_positions.pop(organism.id, None)
        else:
            survivors.append(organism)

    reproduction_capacity = configs.reproduction.max_population
    effective_capacity = reproduction_capacity
    if configs.evolution is not None and configs.evolution.max_population is not None:
        effective_capacity = min(reproduction_capacity, configs.evolution.max_population)
    candidates = tuple(survivors + children)
    newborn_protection_records: list[dict[str, JsonValue]] = []
    if configs.evolution is not None and len(candidates) > effective_capacity:
        fitness_score_map = {
            item.organism_id: (
                item.selection_fitness_score.selection_score
                if item.selection_fitness_score is not None
                else item.score
            )
            for item in fitness_results
        }
        behavior_by_id = {
            record.organism_id: record.behavior_descriptor
            for record in records
            if record.behavior_descriptor is not None
        }
        newborn_protection_records: list[dict[str, JsonValue]] = []
        if configs.newborn_protection_policy == "protect_until_first_evaluation" and children:
            ceiling = max(fitness_score_map.values(), default=0.0)
            for child in children:
                if child.id not in fitness_score_map:
                    fitness_score_map[child.id] = round(ceiling + 1.0, 10)
                    newborn_protection_records.append({
                        "schema_version": "newborn_protection_record_v1",
                        "child_id": child.id,
                        "policy": "protect_until_first_evaluation",
                        "protected_until_first_evaluation": True,
                        "provisional_selection_score": fitness_score_map[child.id],
                    })
        novelty_score_map = _novelty_scores_for_candidates(candidates, behavior_by_id)
        selected, selection_result = select_population(
            candidates,
            fitness_scores=fitness_score_map,
            novelty_scores=novelty_score_map,
            max_population=effective_capacity,
            config=configs.evolution,
            qd_mode=configs.qd_mode,
        )
        if selection_result is not None:
            selection_result = replace(
                selection_result,
                descriptor_digest=_digest(
                    {
                        "behavior_descriptors": {
                            key: behavior_by_id[key].digest() for key in sorted(behavior_by_id)
                        }
                    }
                ),
            )
        next_organisms = tuple(cast(GenesisOrganism, item) for item in selected)
    else:
        selected_ids = tuple(item.id for item in candidates[:effective_capacity])
        if configs.evolution is not None:
            reason = (
                QDFallbackReason.CAPACITY_NOT_EXCEEDED.value
                if len(candidates) <= effective_capacity
                else QDFallbackReason.NO_SELECTION_PRESSURE.value
            )
            selection_result = EvolutionSelectionResult(
                before_count=len(candidates),
                after_count=len(selected_ids),
                selected_ids=selected_ids,
                dropped_ids=tuple(item.id for item in candidates[effective_capacity:]),
                policy_name=configs.evolution.resolved_policy().name,
                config_digest=configs.evolution.digest(),
                selected_parent_ids=selected_ids,
                selected_survivor_ids=selected_ids,
                fitness_scores_digest=_digest(
                    {"fitness_scores": {item.id: 0.0 for item in candidates}}
                ),
                novelty_scores_digest=_digest(
                    {"novelty_scores": {item.id: 0.0 for item in candidates}}
                ),
                fallback_reason=reason,
                qd_fallback_reason=reason,
                qd_mode=configs.qd_mode,
            )
        else:
            selection_result = None
        next_organisms = candidates[:effective_capacity]
    after_count = len(next_organisms)
    raw_scores = [item.score for item in fitness_results]
    selection_scores = [
        (item.selection_fitness_score.selection_score if item.selection_fitness_score is not None else item.score)
        for item in fitness_results
    ]
    viable_scores = [
        score
        for item, score in zip(fitness_results, selection_scores, strict=False)
        if item.selection_fitness_score is None or item.selection_fitness_score.viability_gate > 0.0
    ]
    raw_mean_fitness = round(sum(raw_scores) / len(raw_scores), 10) if raw_scores else 0.0
    raw_best_fitness = round(max(raw_scores), 10) if raw_scores else 0.0
    selection_mean_fitness = round(sum(selection_scores) / len(selection_scores), 10) if selection_scores else 0.0
    selection_best_fitness = round(max(selection_scores), 10) if selection_scores else 0.0
    viable_mean_fitness = round(sum(viable_scores) / len(viable_scores), 10) if viable_scores else 0.0
    viable_best_fitness = round(max(viable_scores), 10) if viable_scores else 0.0
    viability_gate_failures = sum(
        1
        for item in fitness_results
        if item.selection_fitness_score is not None and item.selection_fitness_score.viability_gate <= 0.0
    )
    selection_zero_score_reasons: dict[str, int] = {}
    for item in fitness_results:
        score = item.selection_fitness_score
        if score is not None and score.selection_score <= 0.0:
            selection_zero_score_reasons[score.viability_gate_reason] = selection_zero_score_reasons.get(score.viability_gate_reason, 0) + 1
    mean_fitness = raw_mean_fitness
    best_fitness = raw_best_fitness
    resource_events: tuple[RuntimeResourceEvent, ...] = ()
    respawn_rng = stream.fork(f"{configs.runtime_resource_policy.seed_namespace}/tick-{current_tick}")
    working_world, resource_events = _apply_runtime_resource_policy(
        working_world,
        configs.runtime_resource_policy,
        tick=current_tick,
        rng=respawn_rng,
        occupied_positions={item.position for item in next_organisms},
    )
    next_population = PopulationState(
        generation=population.generation + 1,
        tick=current_tick,
        organisms=next_organisms,
        lineage=lineage,
        fitness=tuple(sorted(fitness_results, key=lambda item: item.organism_id)),
    )
    working_world.agent_position = None
    world_after_digest = working_world.digest()
    causal_summary = _build_population_causal_summary(next_organisms, records)
    return GenerationResult(
        before_count=before_count,
        after_count=after_count,
        births=births,
        deaths=deaths,
        reproduction_attempts=attempts,
        blocked_reproduction=blocked_reproduction,
        mean_fitness=mean_fitness,
        best_fitness=best_fitness,
        population=next_population,
        world_after=working_world,
        world_before_digest=world_before_digest,
        world_after_digest=world_after_digest,
        traces=tuple(traces),
        organism_records=tuple(records),
        nexus_layer=working_nexus_layer,
        causal_summary=causal_summary,
        selection_result=selection_result,
        raw_mean_fitness=raw_mean_fitness,
        raw_best_fitness=raw_best_fitness,
        selection_mean_fitness=selection_mean_fitness,
        selection_best_fitness=selection_best_fitness,
        viable_mean_fitness=viable_mean_fitness,
        viable_best_fitness=viable_best_fitness,
        viability_gate_failures=viability_gate_failures,
        selection_zero_score_reasons=selection_zero_score_reasons,
        resource_policy_records=resource_events,
        newborn_protection_records=tuple(newborn_protection_records),
    )


def _apply_runtime_resource_policy(
    world: World2D,
    policy: RuntimeResourcePolicy,
    *,
    tick: int,
    rng: RNGManager,
    occupied_positions: set[tuple[int, int]],
) -> tuple[World2D, tuple[RuntimeResourceEvent, ...]]:
    before_digest = world.digest()
    if not policy.respawn_enabled:
        return world, (
            RuntimeResourceEvent(
                tick=tick,
                event_type="resource_respawn_disabled",
                position=None,
                amount=0.0,
                kind=policy.resource_kinds[0],
                rng_namespace=policy.seed_namespace,
                rng_draw_count_before=rng.draw_count,
                rng_draw_count_after=rng.draw_count,
                world_digest_before=before_digest,
                world_digest_after=before_digest,
                status=policy.status,
            ),
        )
    current = len(world.resources)
    if policy.max_resources > 0 and current >= policy.max_resources:
        return world, (
            RuntimeResourceEvent(
                tick=tick,
                event_type="resource_pressure",
                position=None,
                amount=0.0,
                kind=policy.resource_kinds[0],
                rng_namespace=policy.seed_namespace,
                rng_draw_count_before=rng.draw_count,
                rng_draw_count_after=rng.draw_count,
                world_digest_before=before_digest,
                world_digest_after=before_digest,
                status="max_resources_reached",
            ),
        )
    draw_before = rng.draw_count
    if rng.random() >= policy.respawn_rate:
        return world, (
            RuntimeResourceEvent(
                tick=tick,
                event_type="resource_respawn_skipped",
                position=None,
                amount=0.0,
                kind=policy.resource_kinds[0],
                rng_namespace=policy.seed_namespace,
                rng_draw_count_before=draw_before,
                rng_draw_count_after=rng.draw_count,
                world_digest_before=before_digest,
                world_digest_after=before_digest,
                status="measured",
            ),
        )
    candidates = tuple(
        (x, y)
        for y in range(world.height)
        for x in range(world.width)
        if (x, y) not in world.walls
        and (x, y) not in occupied_positions
        and (x, y) not in world.resources
    )
    if not candidates:
        return world, (
            RuntimeResourceEvent(
                tick=tick,
                event_type="resource_respawn_blocked",
                position=None,
                amount=0.0,
                kind=policy.resource_kinds[0],
                rng_namespace=policy.seed_namespace,
                rng_draw_count_before=draw_before,
                rng_draw_count_after=rng.draw_count,
                world_digest_before=before_digest,
                world_digest_after=before_digest,
                status="no_valid_empty_cell",
            ),
        )
    position = rng.choice(candidates)
    kind = policy.resource_kinds[0]
    world.place_resource(position, policy.amount)
    after_digest = world.digest()
    return world, (
        RuntimeResourceEvent(
            tick=tick,
            event_type="resource_regenerated",
            position=position,
            amount=policy.amount,
            kind=kind,
            rng_namespace=policy.seed_namespace,
            rng_draw_count_before=draw_before,
            rng_draw_count_after=rng.draw_count,
            world_digest_before=before_digest,
            world_digest_after=after_digest,
            status="measured",
        ),
    )


def _novelty_scores_for_candidates(
    candidates: Sequence[GenesisOrganism], behavior_by_id: Mapping[str, BehaviorDescriptor]
) -> dict[str, float]:
    descriptors = {
        item.id: behavior_by_id[item.id] for item in candidates if item.id in behavior_by_id
    }
    if len(descriptors) <= 1:
        return {item.id: 0.0 for item in candidates}
    numeric = {key: _numeric_descriptor(value) for key, value in descriptors.items()}
    scores: dict[str, float] = {}
    for candidate in candidates:
        values = numeric.get(candidate.id)
        if values is None:
            scores[candidate.id] = 0.0
            continue
        distances = [
            _descriptor_distance(values, other_values)
            for other_id, other_values in numeric.items()
            if other_id != candidate.id
        ]
        scores[candidate.id] = round(sum(distances) / len(distances), 10) if distances else 0.0
    return scores


def _numeric_descriptor(descriptor: BehaviorDescriptor) -> dict[str, float]:
    return {
        key: float(value)
        for key, value in descriptor.to_dict().items()
        if isinstance(value, int | float) and not isinstance(value, bool)
    }


def _descriptor_distance(left: Mapping[str, float], right: Mapping[str, float]) -> float:
    keys = sorted(set(left) | set(right))
    if not keys:
        return 0.0
    total = 0.0
    for key in keys:
        total += abs(float(left.get(key, 0.0)) - float(right.get(key, 0.0)))
    return round(total / len(keys), 10)


def _event_requests_capsule_emit(event: TraceEvent, config: CapsuleTransferConfig | None) -> bool:
    if event.action == "EMIT_NEXUS":
        return config is None or config.emit_on_nexus_action
    return (
        config is not None
        and config.enabled
        and config.emit_on_causal_update_success
        and event.world_delta.get("causal_graph_update_succeeded") is True
    )


def _pay_capsule_emit_cost(
    organism: GenesisOrganism,
    config: CapsuleTransferConfig | None,
    tick: int,
    emitted_this_tick: int,
) -> tuple[bool, str | None, int | None, int | None]:
    if config is None or not config.enabled:
        return True, None, None, None
    if emitted_this_tick >= config.max_emits_per_organism_per_tick:
        return False, "max_emits_per_organism_per_tick", None, None
    if organism.atp_state.runtime_available < config.min_atp_runtime_to_emit:
        return False, "min_atp_runtime_to_emit", None, None
    if not organism.atp_state.can_execute(config.emission_cost_runtime_atp):
        return False, "insufficient_runtime_atp", None, None
    if not organism.atp_state.can_learn(config.emission_cost_learning_atp):
        return False, "insufficient_atp_learning", None, None
    runtime_ledger_id = organism.atp_state.debit_runtime(
        config.emission_cost_runtime_atp,
        tick=tick,
        organism_id=organism.id,
        codon="capsule",
        action="EMIT_CAUSAL_CAPSULE",
        reason="capsule_emit_runtime_cost",
    )
    learning_ledger_id = organism.atp_state.debit_learning(
        config.emission_cost_learning_atp,
        tick=tick,
        organism_id=organism.id,
        reason="capsule_emit_learning_cost",
        event_ref=None if organism.causal_graph is None else organism.causal_graph.digest(),
    )
    return True, None, runtime_ledger_id, learning_ledger_id


def _build_population_causal_summary(
    organisms: tuple[GenesisOrganism, ...], records: list[OrganismStepRecord]
) -> PopulationCausalSummary:
    graphs = [organism.causal_graph for organism in organisms if organism.causal_graph is not None]
    return PopulationCausalSummary(
        organisms_with_graph=len(graphs),
        total_causal_nodes=sum(len(graph.nodes) for graph in graphs),
        total_causal_edges=sum(len(graph.edges) for graph in graphs),
        update_attempts=sum(record.causal_graph_update_attempts for record in records),
        update_successes=sum(record.causal_graph_update_successes for record in records),
        predictions_attempted=sum(record.causal_prediction_attempted for record in records),
        predictions_correct=sum(record.causal_prediction_correct for record in records),
        capsules_emitted=sum(record.capsules_emitted for record in records),
        capsules_read=sum(record.capsules_read for record in records),
        capsules_adopted=sum(record.capsules_adopted for record in records),
        atp_learning_spent=round(sum(record.atp_learning_spent for record in records), 10),
    )


def _trace_bool_count(trace: Trace, key: str) -> int:
    return sum(1 for event in trace.events if event.world_delta.get(key) is True)


def _trace_numeric_sum(trace: Trace, key: str, *, success_key: str | None = None) -> float:
    total = 0.0
    for event in trace.events:
        if success_key is not None and event.world_delta.get(success_key) is not True:
            continue
        value = event.world_delta.get(key)
        if isinstance(value, bool) or not isinstance(value, int | float):
            continue
        total += float(value)
    return total


def _first_world_delta_str(trace: Trace, key: str) -> str | None:
    for event in trace.events:
        value = event.world_delta.get(key)
        if isinstance(value, str):
            return value
    return None


def _last_world_delta_str(trace: Trace, key: str) -> str | None:
    for event in reversed(trace.events):
        value = event.world_delta.get(key)
        if isinstance(value, str):
            return value
    return None


def _capsule_from_nexus_event(
    organism: GenesisOrganism,
    event: TraceEvent,
    tick: int,
    *,
    ttl: int,
    source_fitness: float | None = None,
    source_fitness_status: SourceFitnessStatus = SourceFitnessStatus.UNAVAILABLE,
) -> CausalCapsule:
    event_digest = hashlib.sha256(
        finite_json_dumps(event.to_dict(), sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    capsule_id = f"pop_nexus_{event_digest[:16]}"
    graph_digest = (
        organism.causal_graph.digest() if organism.causal_graph is not None else event_digest
    )
    return CausalCapsule(
        capsule_id=capsule_id,
        source_organism_id=organism.id,
        source_fitness=0.0 if source_fitness is None else round(float(source_fitness), 10),
        source_fitness_status=source_fitness_status,
        source_fitness_tick=None if source_fitness is None else tick,
        source_graph_digest=graph_digest,
        event_pattern=(event.action,),
        predicted_outcome=event.status,
        confidence=1.0,
        emitted_tick=tick,
        ttl=ttl,
        metadata={
            "status": "emitted",
            "kind": "population_nexus_phase2_scaffold",
            "position": [organism.position[0], organism.position[1]],
            "trace_event_digest": event_digest,
            "causal_graph_digest": graph_digest,
            "adoption_semantics": "scaffold_level_capsule_adoption_not_full_mdl_merge",
            "source_fitness_status": source_fitness_status.value,
            "source_fitness_unavailable_is_not_zero": source_fitness is None,
            "source_lineage_id": organism.id,
        },
    )


def _clone_organism(organism: GenesisOrganism) -> GenesisOrganism:
    clone = GenesisOrganism(
        id=organism.id,
        genome=organism.genome,
        ribosome=organism.ribosome,
        compiled_brain=organism.compiled_brain,
        atp_state=GenesisATPState.from_dict(organism.atp_state.to_dict()),
        position=organism.position,
        vitae_store=organism.vitae_store,
        action_registry=organism.action_registry,
        action_runtime_config=organism.action_runtime_config,
        episodic_memory=None
        if organism.episodic_memory is None
        else organism.episodic_memory.from_dict(organism.episodic_memory.to_dict()),
        memory_config=organism.memory_config,
        learning_config=organism.learning_config,
        causal_graph=None
        if organism.causal_graph is None
        else CausalGraph.from_dict(organism.causal_graph.to_dict()),
        execution_source_enabled=organism.execution_source_enabled,
        adf_macro_registry=organism.adf_macro_registry,
        adf_execution_policy=organism.adf_execution_policy,
        translation_profile=organism.translation_profile,
        translation_policy=organism.translation_policy,
    )
    clone._cursor = organism._cursor
    clone._step_index = organism._step_index
    return clone


def _ensure_lineage(population: PopulationState) -> tuple[LineageRecord, ...]:
    if population.lineage:
        return population.lineage
    return tuple(
        LineageRecord(
            organism_id=organism.id,
            parent_id=None,
            generation=population.generation,
            genome_digest=organism.genome.digest(),
            mutation_count=0,
            birth_tick=population.tick,
            death_tick=None,
            reproduction_event_id=None,
        )
        for organism in population.organisms
    )


def _dies(
    organism: GenesisOrganism,
    alive_result: AliveGateResult,
    lineage: LineageRecord | None,
    configs: PopulationConfigs,
    tick: int,
) -> bool:
    classification = classify_death(
        organism_id=organism.id,
        tick=tick,
        runtime_atp_before=organism.atp_state.runtime_available,
        runtime_atp_after=organism.atp_state.runtime_available,
        alive_result=alive_result,
        birth_tick=None if lineage is None else lineage.birth_tick,
        config=configs.death_monitoring,
        blocked_action_reasons=(),
    )
    return classification.actual_death_removed_from_population


def _mark_death(
    lineage: tuple[LineageRecord, ...], organism_id: str, death_tick: int
) -> tuple[LineageRecord, ...]:
    records: list[LineageRecord] = []
    found = False
    for record in lineage:
        if record.organism_id == organism_id and record.death_tick is None:
            records.append(replace(record, death_tick=death_tick))
            found = True
        else:
            records.append(record)
    if not found:
        records.append(
            LineageRecord(
                organism_id=organism_id,
                parent_id=None,
                generation=0,
                genome_digest="missing_lineage_record",
                mutation_count=0,
                birth_tick=0,
                death_tick=death_tick,
                reproduction_event_id=None,
            )
        )
    return tuple(records)


def _replace_last_event(trace: Trace, event: TraceEvent) -> None:
    trace._events[-1] = event


def _with_reproduction_delta(
    event: TraceEvent,
    *,
    parent_after: GenesisOrganism,
    reproduction_result: ReproductionResult | None,
    succeeded: bool,
    reason: str,
    parent_id: str,
    child_id: str | None,
    event_id: str | None,
) -> TraceEvent:
    delta = dict(event.world_delta)
    mutation_digest = None
    child_genome_digest = None
    offspring_runtime_atp = None
    reproduction_ledger_ids: tuple[int, ...] = ()
    if reproduction_result is not None:
        reproduction_ledger_ids = reproduction_result.ledger_entry_ids
        if succeeded and reproduction_result.mutation is not None:
            mutation_digest = reproduction_result.mutation.digest()
            child_genome_digest = reproduction_result.mutation.mutated_genome.digest()
        if succeeded and reproduction_result.child is not None:
            offspring_runtime_atp = reproduction_result.child.atp_state.runtime_available
    delta.update(
        {
            "reproduction_attempted": True,
            "reproduction_succeeded": succeeded,
            "reproduction_blocked_reason": None if succeeded else reason,
            "parent_id": parent_id,
            "child_id": child_id,
            "reproduction_event_id": event_id,
            "parent_runtime_atp_after_reproduction": parent_after.atp_state.runtime_available,
            "offspring_runtime_atp": offspring_runtime_atp,
            "mutation_digest": mutation_digest,
            "child_genome_digest": child_genome_digest,
        }
    )
    return TraceEvent(
        step=event.step,
        agent_id=event.agent_id,
        codon=event.codon,
        action=event.action,
        atp_before=event.atp_before,
        atp_after=parent_after.atp_state.runtime_available,
        position_before=event.position_before,
        position_after=parent_after.position,
        world_delta=delta,
        status="executed" if succeeded else "blocked",
        reason=reason,
        ledger_entry_ids=tuple(event.ledger_entry_ids + reproduction_ledger_ids),
        genome_digest=event.genome_digest,
        world_digest_before=event.world_digest_before,
        cause_refs=event.cause_refs,
        config_hash=event.config_hash,
    )


def _organism_summary(organism: GenesisOrganism) -> dict[str, JsonValue]:
    return {
        "id": organism.id,
        "genome": organism.genome.to_compact(),
        "genome_digest": organism.genome.digest(),
        "compiled_brain_digest": organism.compiled_brain.digest(),
        "atp_state": organism.atp_state.to_dict(),
        "runtime_atp": organism.atp_state.runtime_available,
        "learning_enabled": organism.atp_state.learning_enabled,
        "position": [organism.position[0], organism.position[1]],
        "vitae_store": organism.vitae_store,
        "cursor": organism._cursor,
        "step_index": organism._step_index,
        "episodic_memory": None
        if organism.episodic_memory is None
        else organism.episodic_memory.to_dict(),
        "memory_config": organism.memory_config.to_dict(),
        "learning_config": organism.learning_config.to_dict(),
    }


def _organism_from_summary(data: Mapping[str, JsonValue]) -> GenesisOrganism:
    organism_id = _str(data, "id")
    genome = SemanticGenome.from_compact(_str(data, "genome"))
    ribosome = Ribosome.genesis_v0()
    compiled_brain = ribosome.translate(genome).compiled_brain
    atp_raw = data.get("atp_state")
    if isinstance(atp_raw, Mapping):
        atp_state = GenesisATPState.from_dict(cast(dict[str, JsonValue], dict(atp_raw)))
    else:
        atp_state = GenesisATPState.from_runtime(_float(data, "runtime_atp", 0.0))
    position = _position(data.get("position"))
    memory_raw = data.get("episodic_memory")
    memory_config_raw = data.get("memory_config")
    learning_config_raw = data.get("learning_config")
    organism = GenesisOrganism(
        id=organism_id,
        genome=genome,
        ribosome=ribosome,
        compiled_brain=compiled_brain,
        atp_state=atp_state,
        position=position,
        vitae_store=_float(data, "vitae_store", 0.0),
        episodic_memory=EpisodicMemory.from_dict(memory_raw)
        if isinstance(memory_raw, dict)
        else None,
        memory_config=EpisodicMemoryConfig.from_dict(memory_config_raw)
        if isinstance(memory_config_raw, dict)
        else EpisodicMemoryConfig(),
        learning_config=LearningATPConfig.from_dict(learning_config_raw)
        if isinstance(learning_config_raw, dict)
        else LearningATPConfig(),
    )
    organism._cursor = _int(data, "cursor", 0)
    organism._step_index = _int(data, "step_index", 0)
    return organism


def _reproduction_event_id(parent_id: str, child_id: str, tick: int, mutation_digest: str) -> str:
    payload = json.dumps(
        {
            "parent_id": parent_id,
            "child_id": child_id,
            "tick": tick,
            "mutation_digest": mutation_digest,
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:24]


def _birth_intent_from_optional(value: JsonValue | None) -> BirthIntent | None:
    if not isinstance(value, Mapping):
        return None
    return BirthIntent(
        organism_id=_str(value, "organism_id"),
        tick=_int(value, "tick", 0),
        action=_str(value, "action", "COPY_SELF"),
        detected=_bool(value, "detected", True),
        counts_as_reproduction_attempt=_bool(value, "counts_as_reproduction_attempt", True),
        counts_as_blocked_for_reproduction=_bool(
            value, "counts_as_blocked_for_reproduction", False
        ),
        status=_str(value, "status", "deferred_to_population_lifecycle"),
    )


def _birth_request_from_optional(value: JsonValue | None) -> BirthRequest | None:
    if not isinstance(value, Mapping):
        return None
    return BirthRequest(
        request_id=_str(value, "request_id"),
        parent_id=_str(value, "parent_id"),
        tick=_int(value, "tick", 0),
        parent_genome_digest=_str(value, "parent_genome_digest"),
        policy_digest=_str(value, "policy_digest"),
        intent_digest=_str(value, "intent_digest"),
    )


def _reproduction_gate_result_from_optional(
    value: JsonValue | None,
) -> ReproductionGateResult | None:
    if not isinstance(value, Mapping):
        return None
    return ReproductionGateResult(
        parent_id=_str(value, "parent_id"),
        tick=_int(value, "tick", 0),
        allowed=_bool(value, "allowed", False),
        reasons=_str_tuple(value, "reasons"),
        parent_alive_before_copy_self=_bool(value, "parent_alive_before_copy_self", False),
        parent_runtime_atp_before_copy_self=_float(
            value, "parent_runtime_atp_before_copy_self", 0.0
        ),
        parent_learning_atp_before_copy_self=_optional_float(
            value, "parent_learning_atp_before_copy_self"
        ),
        capacity_available=_bool(value, "capacity_available", False),
        copy_self_action_detected=_bool(value, "copy_self_action_detected", False),
        reproduction_enabled=_bool(value, "reproduction_enabled", False),
        min_runtime_atp_met=_bool(value, "min_runtime_atp_met", False),
        parent_cost_payable=_bool(value, "parent_cost_payable", False),
        offspring_fraction_valid=_bool(value, "offspring_fraction_valid", False),
        min_runtime_atp_required=_optional_float(value, "min_runtime_atp_required"),
        parent_atp_cost=_optional_float(value, "parent_atp_cost"),
        offspring_atp_fraction=_optional_float(value, "offspring_atp_fraction"),
        population_capacity=None
        if value.get("population_capacity") is None
        else _int(value, "population_capacity", 0),
        child_placement_available=_optional_bool(value, "child_placement_available"),
        placement_gate_evaluated=_bool(value, "placement_gate_evaluated", False),
        placement_resolution_stage=_str(value, "placement_resolution_stage", "admission"),
        placement_policy=_str(value, "placement_policy", "same_cell"),
    )


def _mutation_plan_from_optional(value: JsonValue | None) -> MutationPlan | None:
    if not isinstance(value, Mapping):
        return None
    return MutationPlan(
        plan_id=_str(value, "plan_id"),
        parent_genome_digest=_str(value, "parent_genome_digest"),
        operator_sequence=_str_tuple(value, "operator_sequence"),
        mutation_budget=_int(value, "mutation_budget", 0),
        protected_regions=_str_tuple(value, "protected_regions"),
        hotspot_regions=_str_tuple(value, "hotspot_regions"),
        allowed_codons=_str_tuple(value, "allowed_codons"),
        forbidden_codons=_str_tuple(value, "forbidden_codons"),
        expected_effect=_str(value, "expected_effect", "variation"),
        rng_state_digest_before=_str(value, "rng_state_digest_before"),
        controller_digest=_optional_str(value, "controller_digest"),
        policy=_str(value, "policy", "random_baseline"),
    )


def _mutation_audit_result_from_optional(
    value: JsonValue | None,
) -> MutationAuditResult | None:
    if not isinstance(value, Mapping):
        return None
    return MutationAuditResult(
        plan_id=_str(value, "plan_id"),
        child_genome_digest=_str(value, "child_genome_digest"),
        applied_mutations=_str_tuple(value, "applied_mutations"),
        rejected_mutations=_str_tuple(value, "rejected_mutations"),
        mutation_count=_int(value, "mutation_count", 0),
        mutation_digest=_str(value, "mutation_digest"),
        rng_state_digest_after=_str(value, "rng_state_digest_after"),
        validity_status=_str(value, "validity_status", "valid"),
        repair_applied=_bool(value, "repair_applied", False),
    )


def _child_genome_result_from_optional(value: JsonValue | None) -> ChildGenomeResult | None:
    if not isinstance(value, Mapping):
        return None
    return ChildGenomeResult(
        child_id=_str(value, "child_id"),
        parent_id=_str(value, "parent_id"),
        parent_genome_digest=_str(value, "parent_genome_digest"),
        child_genome_digest=_str(value, "child_genome_digest"),
        mutation_digest=_str(value, "mutation_digest"),
        mutation_count=_int(value, "mutation_count", 0),
        genome_bits=_str(value, "genome_bits"),
        validity_status=_str(value, "validity_status", "valid"),
    )


def _position_from_optional_list(value: JsonValue | None) -> tuple[int, int] | None:
    if not isinstance(value, list) or len(value) != 2:
        return None
    x, y = value
    if not isinstance(x, int) or not isinstance(y, int):
        return None
    return (x, y)


def _child_admission_result_from_optional(
    value: JsonValue | None,
) -> ChildAdmissionResult | None:
    if not isinstance(value, Mapping):
        return None
    return ChildAdmissionResult(
        child_id=_str(value, "child_id"),
        admitted=_bool(value, "admitted", False),
        placement_cell=_position_from_optional_list(value.get("placement_cell")),
        blocked_reason=_optional_str(value, "blocked_reason"),
    )


def _birth_event_from_optional(value: JsonValue | None) -> BirthEvent | None:
    if not isinstance(value, Mapping):
        return None
    return BirthEvent(
        birth_event_id=_str(value, "birth_event_id"),
        tick=_int(value, "tick", 0),
        parent_id=_str(value, "parent_id"),
        child_id=_optional_str(value, "child_id"),
        parent_lineage_id=_optional_str(value, "parent_lineage_id"),
        child_lineage_id=_optional_str(value, "child_lineage_id"),
        parent_generation=_int(value, "parent_generation", 0),
        child_generation=_optional_int(value, "child_generation"),
        parent_genome_digest=_str(value, "parent_genome_digest"),
        child_genome_digest=_optional_str(value, "child_genome_digest"),
        mutation_digest=_optional_str(value, "mutation_digest"),
        mutation_count=_int(value, "mutation_count", 0),
        mutation_operator_names=_str_tuple(value, "mutation_operator_names"),
        birth_cost_runtime_atp=_float(value, "birth_cost_runtime_atp", 0.0),
        birth_cost_learning_atp=_float(value, "birth_cost_learning_atp", 0.0),
        child_initial_runtime_atp=_optional_float(value, "child_initial_runtime_atp"),
        child_initial_learning_atp=_optional_float(value, "child_initial_learning_atp"),
        placement_cell=_position_from_optional_list(value.get("placement_cell")),
        birth_policy_digest=_str(value, "birth_policy_digest"),
        reproduction_gate_digest=_str(value, "reproduction_gate_digest"),
        reproduction_attempted=_bool(value, "reproduction_attempted", True),
        child_created=_bool(value, "child_created", False),
        blocked_reason=_optional_str(value, "blocked_reason"),
    )


def _learning_inheritance_from_optional(
    value: JsonValue | None,
) -> LearningInheritanceRecord | None:
    if not isinstance(value, Mapping):
        return None
    return LearningInheritanceRecord(
        parent_id=_str(value, "parent_id"),
        child_id=_optional_str(value, "child_id"),
        tick=_int(value, "tick", 0),
        inheritance_policy=_str(value, "inheritance_policy"),
        learning_capacity_inherited=_bool(value, "learning_capacity_inherited", False),
        learned_content_inherited=_bool(value, "learned_content_inherited", False),
        inheritance_type=_str(value, "inheritance_type"),
        source_lifetime_evidence_digest=_optional_str(value, "source_lifetime_evidence_digest"),
        compressed_skill_digest=_optional_str(value, "compressed_skill_digest"),
        child_received_skill_digest=_optional_str(value, "child_received_skill_digest"),
        learning_success_score=_optional_float(value, "learning_success_score"),
        learning_efficiency_score=_optional_float(value, "learning_efficiency_score"),
        memory_use_score=_optional_float(value, "memory_use_score"),
        delayed_reward_score=_optional_float(value, "delayed_reward_score"),
        baldwinian_selection_pressure=_bool(value, "baldwinian_selection_pressure", False),
    )


def _skill_compression_from_optional(value: JsonValue | None) -> SkillCompressionRecord | None:
    if not isinstance(value, Mapping):
        return None
    return SkillCompressionRecord(
        parent_id=_str(value, "parent_id"),
        child_id=_optional_str(value, "child_id"),
        tick=_int(value, "tick", 0),
        mode=_str(value, "mode"),
        successful_behavior_trace_digest=_optional_str(value, "successful_behavior_trace_digest"),
        compressed_skill_digest=_optional_str(value, "compressed_skill_digest"),
        validation_status=_str(value, "validation_status", "not_requested"),
        fitness_delta_positive=_bool(value, "fitness_delta_positive", False),
        energy_efficiency_positive=_bool(value, "energy_efficiency_positive", False),
        replay_successful=_bool(value, "replay_successful", False),
        inherited=_bool(value, "inherited", False),
        rejected_reason=_optional_str(value, "rejected_reason"),
    )


def _ai_birth_records_from_optional(
    value: JsonValue | None,
) -> tuple[AIBirthInterventionRecord, ...]:
    if not isinstance(value, list):
        return ()
    rows: list[AIBirthInterventionRecord] = []
    for item in value:
        if not isinstance(item, Mapping):
            continue
        rows.append(
            AIBirthInterventionRecord(
                intervention_id=_str(item, "intervention_id"),
                controller_name=_str(item, "controller_name", "none"),
                controller_version=_str(item, "controller_version", "0"),
                input_evidence_digest=_str(item, "input_evidence_digest"),
                decision_digest=_str(item, "decision_digest"),
                applied=_bool(item, "applied", False),
                rejected_reason=_optional_str(item, "rejected_reason"),
                scope=_str(item, "scope", "child_only"),
                event=_str(item, "event"),
            )
        )
    return tuple(rows)


def _adf_inheritance_from_optional(value: JsonValue | None) -> ADFInheritanceRecord | None:
    if not isinstance(value, Mapping):
        return None
    return ADFInheritanceRecord(
        parent_id=_str(value, "parent_id"),
        child_id=_optional_str(value, "child_id"),
        tick=_int(value, "tick", 0),
        parent_adf_digest=_optional_str(value, "parent_adf_digest"),
        child_adf_digest=_optional_str(value, "child_adf_digest"),
        adf_inheritance_mode=_str(value, "adf_inheritance_mode"),
        adf_macro_count_parent=_int(value, "adf_macro_count_parent", 0),
        adf_macro_count_child=_int(value, "adf_macro_count_child", 0),
        adf_mutation_applied=_bool(value, "adf_mutation_applied", False),
        adf_skill_imported=_bool(value, "adf_skill_imported", False),
    )


def _inheritance_policy(value: JsonValue | None) -> InheritancePolicy:
    if value is None:
        return InheritancePolicy.DARWINIAN_GENETIC_ONLY
    if not isinstance(value, str):
        msg = "inheritance_policy must be a string."
        raise ConfigurationError(msg)
    try:
        return InheritancePolicy(value)
    except ValueError as exc:
        msg = f"Unsupported inheritance_policy {value!r}."
        raise ConfigurationError(msg) from exc


def _skill_inheritance_mode(value: JsonValue | None) -> SkillInheritanceMode:
    if value is None:
        return SkillInheritanceMode.CAPACITY_ONLY
    if not isinstance(value, str):
        msg = "skill_inheritance_mode must be a string."
        raise ConfigurationError(msg)
    try:
        return SkillInheritanceMode(value)
    except ValueError as exc:
        msg = f"Unsupported skill_inheritance_mode {value!r}."
        raise ConfigurationError(msg) from exc


def _adf_inheritance_mode(value: JsonValue | None) -> ADFInheritanceMode:
    if value is None:
        return ADFInheritanceMode.INHERIT_CAPACITY
    if not isinstance(value, str):
        msg = "adf_inheritance_mode must be a string."
        raise ConfigurationError(msg)
    try:
        return ADFInheritanceMode(value)
    except ValueError as exc:
        msg = f"Unsupported adf_inheritance_mode {value!r}."
        raise ConfigurationError(msg) from exc


def _death_classification_consistency_status(
    top_level: DeathClassificationRecord | None,
    fitness_level: DeathClassificationRecord | None,
) -> str:
    if top_level is None and fitness_level is None:
        return "not_applicable"
    if top_level is None:
        return "missing_top_level"
    if fitness_level is None:
        return "missing_fitness_level"
    return "matched" if top_level.to_dict() == fitness_level.to_dict() else "mismatch"


def _placement_policy(value: JsonValue | None) -> OffspringPlacementPolicy:
    if value is None:
        return OffspringPlacementPolicy.SAME_CELL
    if not isinstance(value, str):
        msg = "offspring_placement must be a string."
        raise ConfigurationError(msg)
    try:
        return OffspringPlacementPolicy(value)
    except ValueError as exc:
        msg = f"Unsupported offspring_placement {value!r}."
        raise ConfigurationError(msg) from exc


def _finalize_reproduction_placement(
    result: ReproductionResult,
    *,
    placement: tuple[int, int],
    policy: OffspringPlacementPolicy,
) -> ReproductionResult:
    """Return a reproduction result whose evidence records match final placement."""

    if not result.succeeded or result.child is None:
        return result
    child = result.child
    child.position = placement
    gate = result.reproduction_gate_result
    if gate is not None:
        gate = replace(
            gate,
            child_placement_available=True,
            placement_gate_evaluated=True,
            placement_resolution_stage="admission",
            placement_policy=policy.value,
        )
    admission = ChildAdmissionResult(
        child_id=child.id,
        admitted=True,
        placement_cell=placement,
        blocked_reason=None,
    )
    birth_event = result.birth_event
    if birth_event is not None:
        birth_event = replace(
            birth_event,
            placement_cell=placement,
            reproduction_gate_digest=gate.digest() if gate is not None else birth_event.reproduction_gate_digest,
            child_created=True,
            blocked_reason=None,
        )
    return replace(
        result,
        child=child,
        reproduction_gate_result=gate,
        child_admission_result=admission,
        birth_event=birth_event,
    )


def _mark_reproduction_placement_blocked(
    result: ReproductionResult,
    *,
    reason: str,
    policy: OffspringPlacementPolicy,
) -> ReproductionResult:
    """Return a failed reproduction result when a candidate child cannot be admitted."""

    candidate_child_id = result.child.id if result.child is not None else "candidate_child"
    gate = result.reproduction_gate_result
    if gate is not None:
        gate = replace(
            gate,
            allowed=False,
            reasons=(reason,),
            child_placement_available=False,
            placement_gate_evaluated=True,
            placement_resolution_stage="admission",
            placement_policy=policy.value,
        )
    admission = ChildAdmissionResult(
        child_id=candidate_child_id,
        admitted=False,
        placement_cell=None,
        blocked_reason=reason,
    )
    birth_event = result.birth_event
    if birth_event is not None:
        birth_event = replace(
            birth_event,
            child_id=None,
            child_lineage_id=None,
            child_generation=None,
            child_genome_digest=None,
            mutation_digest=None,
            mutation_count=0,
            mutation_operator_names=(),
            child_initial_runtime_atp=None,
            child_initial_learning_atp=None,
            placement_cell=None,
            reproduction_gate_digest=gate.digest() if gate is not None else birth_event.reproduction_gate_digest,
            child_created=False,
            blocked_reason=reason,
        )
    return replace(
        result,
        succeeded=False,
        child=None,
        lineage=None,
        decision=ReproductionDecision(False, (reason,)),
        reproduction_gate_result=gate,
        child_admission_result=admission,
        birth_event=birth_event,
        child_genome_result=None,
    )


def _resolve_offspring_position(
    *,
    parent_position: tuple[int, int],
    child_id: str,
    policy: OffspringPlacementPolicy,
    world: World2D,
    live_positions: Mapping[str, tuple[int, int]],
) -> tuple[int, int] | None:
    if policy is OffspringPlacementPolicy.SAME_CELL:
        return parent_position
    occupied = {position for oid, position in live_positions.items() if oid != child_id}
    adjacent = (
        (parent_position[0], parent_position[1] - 1),
        (parent_position[0] + 1, parent_position[1]),
        (parent_position[0], parent_position[1] + 1),
        (parent_position[0] - 1, parent_position[1]),
    )
    for position in adjacent:
        if world.in_bounds(position) and not world.is_wall(position) and position not in occupied:
            return position
    return None


def _resolve_rng(*, seed: int | None, rng: RNGManager | None, namespace: str) -> RNGManager:
    if seed is not None and rng is not None:
        msg = "Provide either seed or rng, not both."
        raise ValueError(msg)
    return rng.fork(namespace) if rng is not None else RNGManager(seed=seed).fork(namespace)


def _alive_config_to_dict(config: AliveGateConfig) -> dict[str, JsonValue]:
    return {
        "min_ticks": config.min_ticks,
        "min_executed_actions": config.min_executed_actions,
        "max_blocked_ratio": config.max_blocked_ratio,
        "require_positive_runtime_atp": config.require_positive_runtime_atp,
        "require_lumen_interaction": config.require_lumen_interaction,
        "require_reproduction_capability": config.require_reproduction_capability,
    }


def _alive_config_from_dict(data: Mapping[str, JsonValue]) -> AliveGateConfig:
    return AliveGateConfig(
        min_ticks=_int(data, "min_ticks", 10),
        min_executed_actions=_int(data, "min_executed_actions", 1),
        max_blocked_ratio=_float(data, "max_blocked_ratio", 0.8),
        require_positive_runtime_atp=_bool(data, "require_positive_runtime_atp", True),
        require_lumen_interaction=_bool(data, "require_lumen_interaction", False),
        require_reproduction_capability=_bool(data, "require_reproduction_capability", False),
    )


def _fitness_breakdown_from_optional(value: object) -> FitnessBreakdown | None:
    if not isinstance(value, Mapping):
        return None
    from codontrace.genesis.fitness import fitness_breakdown_from_dict

    return fitness_breakdown_from_dict(value)


def _selection_fitness_score_from_optional(value: object) -> SelectionFitnessScore | None:
    if not isinstance(value, Mapping):
        return None
    return SelectionFitnessScore(
        organism_id=_str(value, "organism_id"),
        viability_gate=_float(value, "viability_gate", 0.0),
        weighted_component_sum=_float(value, "weighted_component_sum", 0.0),
        selection_score=_float(value, "selection_score", 0.0),
        breakdown_digest=_str(value, "breakdown_digest"),
        status=_str(value, "status", "measured"),
        viability_gate_reason=_str(value, "viability_gate_reason", "not_audited"),
        alive_gate_digest=_str(value, "alive_gate_digest", ""),
        selection_score_before_gate=_float(value, "selection_score_before_gate", 0.0),
        selection_score_after_gate=_float(value, "selection_score_after_gate", 0.0),
    )


def _alive_result_from_dict(data: Mapping[str, JsonValue]) -> AliveGateResult:
    return AliveGateResult(
        passed=_bool(data, "passed", False),
        survived_ticks=_int(data, "survived_ticks", 0),
        executed_actions=_int(data, "executed_actions", 0),
        blocked_actions=_int(data, "blocked_actions", 0),
        blocked_ratio=_float(data, "blocked_ratio", 0.0),
        final_runtime_atp=_float(data, "final_runtime_atp", 0.0),
        lumen_interactions=_int(data, "lumen_interactions", 0),
        reproduction_events=_int(data, "reproduction_events", 0),
        reasons=_str_tuple(data, "reasons"),
    )


def _validate_probability(value: float, name: str) -> None:
    finite_float(name, value, probability=True)


def _validate_non_negative(value: float, name: str) -> None:
    finite_float(name, value, non_negative=True)


def _digest(payload: Mapping[str, JsonValue]) -> str:
    encoded = finite_json_dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _bool(data: Mapping[str, JsonValue], key: str, default: bool) -> bool:
    value = data.get(key, default)
    if not isinstance(value, bool):
        msg = f"{key} must be a boolean."
        raise ConfigurationError(msg)
    return value


def _float(data: Mapping[str, JsonValue], key: str, default: float) -> float:
    value = data.get(key, default)
    if isinstance(value, bool) or not isinstance(value, int | float):
        msg = f"{key} must be numeric."
        raise ConfigurationError(msg)
    return finite_float(key, value)  # type: ignore[return-value]


def _int(data: Mapping[str, JsonValue], key: str, default: int) -> int:
    value = data.get(key, default)
    if isinstance(value, bool) or not isinstance(value, int):
        msg = f"{key} must be an integer."
        raise ConfigurationError(msg)
    return int(value)


def _str(data: Mapping[str, JsonValue], key: str, default: str | None = None) -> str:
    value = data.get(key, default)
    if not isinstance(value, str):
        msg = f"{key} must be a string."
        raise ConfigurationError(msg)
    return value


def _optional_str(data: Mapping[str, JsonValue], key: str) -> str | None:
    value = data.get(key)
    if value is None:
        return None
    if not isinstance(value, str):
        msg = f"{key} must be a string or null."
        raise ConfigurationError(msg)
    return value


def _optional_float(data: Mapping[str, JsonValue], key: str) -> float | None:
    value = data.get(key)
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int | float):
        msg = f"{key} must be numeric or null."
        raise ConfigurationError(msg)
    return finite_float(key, value)  # type: ignore[return-value]


def _optional_int(data: Mapping[str, JsonValue], key: str) -> int | None:
    value = data.get(key)
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int):
        msg = f"{key} must be an integer or null."
        raise ConfigurationError(msg)
    return int(value)


def _optional_bool(data: Mapping[str, JsonValue], key: str) -> bool | None:
    value = data.get(key)
    if value is None:
        return None
    if not isinstance(value, bool):
        msg = f"{key} must be a boolean or null."
        raise ConfigurationError(msg)
    return value


def _str_tuple(data: Mapping[str, JsonValue], key: str) -> tuple[str, ...]:
    value = data.get(key, [])
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        msg = f"{key} must be a list of strings."
        raise ConfigurationError(msg)
    return tuple(cast(list[str], value))


def _int_tuple(data: Mapping[str, JsonValue], key: str) -> tuple[int, ...]:
    value = data.get(key, [])
    if not isinstance(value, list) or any(
        isinstance(item, bool) or not isinstance(item, int) for item in value
    ):
        msg = f"{key} must be a list of integers."
        raise ConfigurationError(msg)
    return tuple(cast(list[int], value))


def _list(data: Mapping[str, JsonValue], key: str) -> list[JsonValue]:
    value = data.get(key, [])
    if not isinstance(value, list):
        msg = f"{key} must be a list."
        raise ConfigurationError(msg)
    return value


def _position(value: JsonValue | None) -> tuple[int, int]:
    if (
        not isinstance(value, list)
        or len(value) != 2
        or isinstance(value[0], bool)
        or isinstance(value[1], bool)
        or not isinstance(value[0], int)
        or not isinstance(value[1], int)
    ):
        msg = "position must be a two-item integer list."
        raise ConfigurationError(msg)
    return (value[0], value[1])
