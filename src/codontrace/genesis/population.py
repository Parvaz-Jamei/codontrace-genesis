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

from codontrace._numeric import finite_float, finite_json_dumps
from codontrace._types import JsonValue
from codontrace.errors import ConfigurationError
from codontrace.genesis.atp import GenesisATPState
from codontrace.genesis.behavior import BehaviorDescriptor, describe_behavior
from codontrace.genesis.birth import (
    ADFInheritanceMode,
    ADFInheritanceRecord,
    AIBirthInterventionRecord,
    BirthChamberState,
    BirthEvent,
    BirthIntent,
    BirthRequest,
    ChildAdmissionResult,
    ChildGenomeResult,
    IncipientOffspring,
    InheritancePolicy,
    LearningInheritanceRecord,
    MutationAuditResult,
    MutationOperator,
    MutationPlan,
    RecombinationRecord,
    ReproductionGateResult,
    ReproductionMode,
    SexualRecombinationConfig,
    SkillCompressionRecord,
    SkillInheritanceMode,
    build_mutation_plan,
    coerce_reproduction_mode,
    make_policy_digest,
    recombine_positional_segment,
    recombine_positional_segment_pair,
    reduce_incipient_to_haploid_gamete,
    select_chamber_pair,
    timed_out_chamber_slots,
)
from codontrace.genesis.canonical import canonical_digest
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
from codontrace.genesis.deme_selection import DemeSelectionConfig
from codontrace.genesis.environment import (
    EnvironmentConfig,
    EnvironmentEvent,
    EnvironmentSnapshot,
    EnvironmentState,
    local_resource_consumed,
    step_environment,
)
from codontrace.genesis.fitness import (
    FitnessBreakdown,
    FitnessSignalRegistry,
    SelectionFitnessScore,
    evaluate_task_sensitive_fitness,
    task_sensitive_raw_metrics,
)
from codontrace.genesis.food_patch_signal import (
    MOVE_TOWARD_CAPSULE_TARGET,
    FoodPatchSignalConfig,
    FoodPatchSignalRecord,
    FoodPatchState,
    decode_patch_payload,
    encode_patch_payload,
    spawn_patches_for_tick,
)
from codontrace.genesis.learning import LearningATPConfig
from codontrace.genesis.liveness import AliveGateConfig, AliveGateResult, evaluate_alive
from codontrace.genesis.logic9 import (
    LOGIC9_TASKS,
    Logic9ReactionConfig,
    Logic9ReactionEvent,
    apply_logic9_runtime_bonus,
    logic9_resource_name,
)
from codontrace.genesis.materials import (
    MaterialEvent,
    MaterialsConfig,
    MaterialsOrganismState,
    MaterialsSnapshot,
    MaterialsState,
    apply_organism_material_coupling,
    attach_materials_to_organisms,
    copy_materials_organism_state,
    inherit_materials_organism_state,
    step_materials,
)
from codontrace.genesis.memory import EpisodicMemory, EpisodicMemoryConfig
from codontrace.genesis.organism import GenesisOrganism
from codontrace.genesis.host_parasite_life_plugin import (
    ClosedLoopHPLifeConfig,
    apply_closed_loop_hp_life,
    charge_outcross_runtime,
    outcross_mates_compatible,
    outcross_runtime_cost,
    resolve_copy_self_mode,
    silence_outcross_locus,
)
from codontrace.genesis.phase_e import (
    DemeMessage,
    DemeState,
    PhaseESubstrateConfig,
    apply_deme_messaging_after_event,
    attach_phase_e_to_organisms,
    build_deme_state,
    copy_phase_e_state,
    inherit_phase_e_state,
    maybe_replicate_demes,
    refresh_phase_e_sensory,
)
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
from codontrace.genesis.stepping_stone_reward import (
    SteppingStoneRewardConfig,
)
from codontrace.genesis.structural_mutation import (
    StructuralMutationConfig,
    build_genome_program,
    mutate_genome_program,
)
from codontrace.genesis.task_switch_cost import (
    TaskSwitchCostConfig,
    TaskSwitchCostRecord,
    apply_task_switch_cost,
)
from codontrace.genesis.toolchain import evaluate_tool_chain_state
from codontrace.genesis.translation_profile import inherit_translation_profile
from codontrace.genome import SemanticGenome
from codontrace.rng import RNGManager
from codontrace.trace import Trace, TraceEvent, WorldEvent
from codontrace.world import World2D


class OffspringPlacementPolicy(str, Enum):
    """Explicit child placement policy for controlled reproduction."""

    SAME_CELL = "same_cell"
    ADJACENT_FREE = "adjacent_free"
    BLOCKED_IF_NO_SPACE = "blocked_if_no_space"
    REPLACE_OCCUPIED = "replace_occupied"


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
    reproduction_mode: ReproductionMode = ReproductionMode.ASEXUAL

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
        try:
            object.__setattr__(self, "reproduction_mode", coerce_reproduction_mode(self.reproduction_mode))
        except ValueError as exc:
            raise ConfigurationError(str(exc)) from exc
        except TypeError as exc:
            raise ConfigurationError(str(exc)) from exc
        object.__setattr__(self, "offspring_placement", _placement_policy(self.offspring_placement))

    def to_dict(self) -> dict[str, JsonValue]:
        payload: dict[str, JsonValue] = {
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
        if self.reproduction_mode is not ReproductionMode.ASEXUAL:
            payload["reproduction_mode"] = self.reproduction_mode.value
        return payload

    @property
    def is_sexual(self) -> bool:
        return self.reproduction_mode is ReproductionMode.SEXUAL_CROSSOVER

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
            reproduction_mode=_reproduction_mode(data.get("reproduction_mode")),
        )


@dataclass(frozen=True, slots=True)
class MetabolicConfig:
    """Opt-in basal / maintenance energy drain.

    Default is disabled so existing research presets and their digests stay
    unchanged. Life-loop ecology enables this explicitly (JaxLife / EEDx-style
    energy budgets): organisms pay ATP every tick for remaining alive, not only
    for executed actions.
    """

    enabled: bool = False
    basal_runtime_atp_cost: float = 0.0
    action_name: str = "BASAL_METABOLISM"
    reason: str = "basal_metabolism"

    def __post_init__(self) -> None:
        _validate_non_negative(self.basal_runtime_atp_cost, "basal_runtime_atp_cost")
        if not self.action_name:
            raise ConfigurationError("MetabolicConfig.action_name must not be empty.")
        if not self.reason:
            raise ConfigurationError("MetabolicConfig.reason must not be empty.")

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "enabled": self.enabled,
            "basal_runtime_atp_cost": self.basal_runtime_atp_cost,
            "action_name": self.action_name,
            "reason": self.reason,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, JsonValue]) -> MetabolicConfig:
        return cls(
            enabled=_bool(data, "enabled", False),
            basal_runtime_atp_cost=_float(data, "basal_runtime_atp_cost", 0.0),
            action_name=_str(data, "action_name", "BASAL_METABOLISM"),
            reason=_str(data, "reason", "basal_metabolism"),
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
    second_parent_id: str | None = None
    recombination_start_index: int | None = None
    recombination_end_index: int | None = None
    recombination_digest: str | None = None
    recombination_window_differed: bool | None = None

    @property
    def id(self) -> str | None:
        """Backward-compatible lineage identifier alias."""

        return self.reproduction_event_id

    @property
    def parent_ids(self) -> tuple[str, ...]:
        """Named genetic parents. Asexual records keep a single parent_id."""

        if self.parent_id is None:
            return ()
        if self.second_parent_id:
            return (self.parent_id, self.second_parent_id)
        return (self.parent_id,)

    def to_dict(self) -> dict[str, JsonValue]:
        payload: dict[str, JsonValue] = {
            "organism_id": self.organism_id,
            "parent_id": self.parent_id,
            "generation": self.generation,
            "genome_digest": self.genome_digest,
            "mutation_count": self.mutation_count,
            "birth_tick": self.birth_tick,
            "death_tick": self.death_tick,
            "reproduction_event_id": self.reproduction_event_id,
        }
        if self.second_parent_id:
            payload["second_parent_id"] = self.second_parent_id
            payload["parent_ids"] = list(self.parent_ids)
            if self.recombination_start_index is not None:
                payload["recombination_start_index"] = self.recombination_start_index
            if self.recombination_end_index is not None:
                payload["recombination_end_index"] = self.recombination_end_index
            if self.recombination_digest:
                payload["recombination_digest"] = self.recombination_digest
            if self.recombination_window_differed:
                payload["recombination_window_differed"] = True
        return payload

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
            second_parent_id=_optional_str(data, "second_parent_id"),
            recombination_start_index=None
            if data.get("recombination_start_index") is None
            else _int(data, "recombination_start_index", 0),
            recombination_end_index=None
            if data.get("recombination_end_index") is None
            else _int(data, "recombination_end_index", 0),
            recombination_digest=_optional_str(data, "recombination_digest"),
            recombination_window_differed=_optional_bool(data, "recombination_window_differed"),
        )


@dataclass(frozen=True, slots=True)
class BirthPlacementRecord:
    """Birth-time parent/child cells. Observation-only; not an intelligence metric."""

    parent_id: str
    child_id: str
    parent_position: tuple[int, int]
    placement_cell: tuple[int, int]

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "parent_id": self.parent_id,
            "child_id": self.child_id,
            "parent_position": [self.parent_position[0], self.parent_position[1]],
            "placement_cell": [self.placement_cell[0], self.placement_cell[1]],
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, JsonValue]) -> BirthPlacementRecord:
        parent_raw = data.get("parent_position", [0, 0])
        child_raw = data.get("placement_cell", [0, 0])
        if not isinstance(parent_raw, list) or len(parent_raw) != 2:
            raise ConfigurationError("BirthPlacementRecord.parent_position must be an [x, y] pair.")
        if not isinstance(child_raw, list) or len(child_raw) != 2:
            raise ConfigurationError("BirthPlacementRecord.placement_cell must be an [x, y] pair.")
        return cls(
            parent_id=_str(data, "parent_id"),
            child_id=_str(data, "child_id"),
            parent_position=(int(parent_raw[0]), int(parent_raw[1])),
            placement_cell=(int(child_raw[0]), int(child_raw[1])),
        )


def _birth_placement_record(
    parent: GenesisOrganism, child: GenesisOrganism
) -> BirthPlacementRecord:
    return BirthPlacementRecord(
        parent_id=parent.id,
        child_id=child.id,
        parent_position=parent.position,
        placement_cell=child.position,
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
    recombination_record: RecombinationRecord | None = None

    def to_dict(self) -> dict[str, JsonValue]:
        payload: dict[str, JsonValue] = {
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
        if self.recombination_record is not None:
            payload["recombination_record"] = self.recombination_record.to_dict()
        return payload

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
            recombination_record=_recombination_record_from_optional(
                data.get("recombination_record")
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
    birth_chamber: BirthChamberState = field(default_factory=BirthChamberState)
    environment: EnvironmentState | None = None
    deme: DemeState | None = None
    materials: MaterialsState | None = None

    def __post_init__(self) -> None:
        if self.generation < 0 or self.tick < 0:
            msg = "Population generation and tick must be non-negative."
            raise ConfigurationError(msg)
        ids = [organism.id for organism in self.organisms]
        if len(ids) != len(set(ids)):
            msg = "Population organism ids must be unique."
            raise ConfigurationError(msg)

    def to_dict(self) -> dict[str, JsonValue]:
        payload: dict[str, JsonValue] = {
            "generation": self.generation,
            "tick": self.tick,
            "organisms": [_organism_summary(organism) for organism in self.organisms],
            "lineage": [record.to_dict() for record in self.lineage],
            "fitness": [item.to_dict() for item in self.fitness],
        }
        if not self.birth_chamber.is_empty:
            payload["birth_chamber"] = self.birth_chamber.to_dict()
        if self.environment is not None:
            payload["environment"] = self.environment.to_dict()
        if self.deme is not None:
            payload["deme"] = self.deme.to_dict()
        if self.materials is not None:
            payload["materials"] = self.materials.to_dict()
        return payload

    @classmethod
    def from_dict(cls, data: Mapping[str, JsonValue]) -> PopulationState:
        organisms_raw = _list(data, "organisms")
        lineage_raw = _list(data, "lineage")
        fitness_raw = _list(data, "fitness")
        chamber_raw = data.get("birth_chamber")
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
            birth_chamber=BirthChamberState.from_dict(chamber_raw)
            if isinstance(chamber_raw, Mapping)
            else BirthChamberState(),
            environment=EnvironmentState.from_dict(env_raw)
            if isinstance((env_raw := data.get("environment")), Mapping)
            else None,
            deme=DemeState.from_dict(deme_raw)
            if isinstance((deme_raw := data.get("deme")), Mapping)
            else None,
            materials=MaterialsState.from_dict(mat_raw)
            if isinstance((mat_raw := data.get("materials")), Mapping)
            else None,
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
    # Wave 1c renewable-food knobs. Defaults reproduce the legacy behaviour
    # (one draw per tick, never under an organism) and are omitted from
    # ``to_dict`` so existing policy/spec digests stay byte-stable.
    respawn_under_organisms: bool = False
    respawn_draws_per_tick: int = 1

    def __post_init__(self) -> None:
        if not isinstance(self.respawn_enabled, bool):
            raise ConfigurationError("RuntimeResourcePolicy.respawn_enabled must be a bool.")
        if not isinstance(self.respawn_under_organisms, bool):
            raise ConfigurationError("RuntimeResourcePolicy.respawn_under_organisms must be a bool.")
        if self.respawn_draws_per_tick < 1:
            raise ConfigurationError("RuntimeResourcePolicy.respawn_draws_per_tick must be >= 1.")
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
        payload: dict[str, JsonValue] = {
            "respawn_enabled": self.respawn_enabled,
            "respawn_rate": self.respawn_rate,
            "max_resources": self.max_resources,
            "resource_kinds": list(self.resource_kinds),
            "amount": self.amount,
            "seed_namespace": self.seed_namespace,
            "status": self.status,
            "claim_allowed": self.respawn_enabled and self.status.startswith("runtime_effective"),
        }
        if self.respawn_under_organisms:
            payload["respawn_under_organisms"] = True
        if self.respawn_draws_per_tick != 1:
            payload["respawn_draws_per_tick"] = self.respawn_draws_per_tick
        return payload

    @classmethod
    def from_dict(cls, data: Mapping[str, JsonValue]) -> RuntimeResourcePolicy:
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
            respawn_under_organisms=_bool(data, "respawn_under_organisms", False),
            respawn_draws_per_tick=_int(data, "respawn_draws_per_tick", 1),
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
    def from_dict(cls, data: Mapping[str, JsonValue]) -> RuntimeResourceEvent:
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
    environment_records: tuple[EnvironmentEvent, ...] = ()
    environment_snapshot: EnvironmentSnapshot | None = None
    environment_world_events: tuple[WorldEvent, ...] = ()
    phase_e_messages: tuple[DemeMessage, ...] = ()
    deme_state: DemeState | None = None
    birth_placement_records: tuple[BirthPlacementRecord, ...] = ()
    logic9_events: tuple[Logic9ReactionEvent, ...] = ()
    materials_records: tuple[MaterialEvent, ...] = ()
    materials_snapshot: MaterialsSnapshot | None = None
    materials_world_events: tuple[WorldEvent, ...] = ()
    food_patch_signal_records: tuple[FoodPatchSignalRecord, ...] = ()
    task_switch_cost_records: tuple[TaskSwitchCostRecord, ...] = ()

    def to_dict(self) -> dict[str, JsonValue]:
        payload: dict[str, JsonValue] = {
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
        if self.environment_records:
            payload["environment_records"] = [item.to_dict() for item in self.environment_records]
        if self.environment_snapshot is not None:
            payload["environment_snapshot"] = self.environment_snapshot.to_dict()
        if self.environment_world_events:
            payload["environment_world_events"] = [
                item.to_dict() for item in self.environment_world_events
            ]
        if self.phase_e_messages:
            payload["phase_e_messages"] = [item.to_dict() for item in self.phase_e_messages]
        if self.deme_state is not None:
            payload["deme_state"] = self.deme_state.to_dict()
        if self.birth_placement_records:
            payload["birth_placement_records"] = [
                item.to_dict() for item in self.birth_placement_records
            ]
        if self.logic9_events:
            payload["logic9_events"] = [item.to_dict() for item in self.logic9_events]
        if self.materials_records:
            payload["materials_records"] = [item.to_dict() for item in self.materials_records]
        if self.materials_snapshot is not None:
            payload["materials_snapshot"] = self.materials_snapshot.to_dict()
        if self.materials_world_events:
            payload["materials_world_events"] = [
                item.to_dict() for item in self.materials_world_events
            ]
        if self.food_patch_signal_records:
            payload["food_patch_signal_records"] = [
                item.to_dict() for item in self.food_patch_signal_records
            ]
        if self.task_switch_cost_records:
            payload["task_switch_cost_records"] = [
                item.to_dict() for item in self.task_switch_cost_records
            ]
        return payload

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
            environment_records=tuple(
                EnvironmentEvent.from_dict(item)
                for item in _list(data, "environment_records")
                if isinstance(item, Mapping)
            ),
            environment_snapshot=EnvironmentSnapshot.from_dict(snapshot_raw)
            if isinstance((snapshot_raw := data.get("environment_snapshot")), Mapping)
            else None,
            environment_world_events=tuple(
                WorldEvent.from_dict(cast(dict[str, JsonValue], dict(item)))
                for item in _list(data, "environment_world_events")
                if isinstance(item, Mapping)
            ),
            phase_e_messages=tuple(
                DemeMessage.from_dict(item)
                for item in _list(data, "phase_e_messages")
                if isinstance(item, Mapping)
            ),
            deme_state=DemeState.from_dict(deme_state_raw)
            if isinstance((deme_state_raw := data.get("deme_state")), Mapping)
            else None,
            birth_placement_records=tuple(
                BirthPlacementRecord.from_dict(item)
                for item in _list(data, "birth_placement_records")
                if isinstance(item, Mapping)
            ),
            logic9_events=tuple(
                Logic9ReactionEvent(
                    tick=int(item.get("tick", 0) or 0),
                    organism_id=str(item.get("organism_id", "")),
                    task=str(item.get("task", "NAND")),
                    resource_name=str(item.get("resource_name", "resNAND")),
                    consumed=float(item.get("consumed", 0.0) or 0.0),
                    atp_bonus=float(item.get("atp_bonus", 0.0) or 0.0),
                    blocked_reason=str(item.get("blocked_reason", "")),
                    genome_digest=str(item.get("genome_digest", "")),
                )
                for item in _list(data, "logic9_events")
                if isinstance(item, Mapping)
            ),
            materials_records=tuple(
                MaterialEvent.from_dict(item)
                for item in _list(data, "materials_records")
                if isinstance(item, Mapping)
            ),
            materials_snapshot=MaterialsSnapshot.from_dict(mat_snap_raw)
            if isinstance((mat_snap_raw := data.get("materials_snapshot")), Mapping)
            else None,
            materials_world_events=tuple(
                WorldEvent.from_dict(cast(dict[str, JsonValue], dict(item)))
                for item in _list(data, "materials_world_events")
                if isinstance(item, Mapping)
            ),
            food_patch_signal_records=tuple(
                FoodPatchSignalRecord.from_dict(item)
                for item in _list(data, "food_patch_signal_records")
                if isinstance(item, Mapping)
            ),
            task_switch_cost_records=tuple(
                TaskSwitchCostRecord.from_dict(item)
                for item in _list(data, "task_switch_cost_records")
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
    metabolism: MetabolicConfig = field(default_factory=MetabolicConfig)
    sexual_recombination: SexualRecombinationConfig = field(
        default_factory=SexualRecombinationConfig
    )
    environment: EnvironmentConfig = field(default_factory=EnvironmentConfig)
    phase_e: PhaseESubstrateConfig = field(default_factory=PhaseESubstrateConfig)
    logic9: Logic9ReactionConfig = field(default_factory=Logic9ReactionConfig)
    materials: MaterialsConfig = field(default_factory=MaterialsConfig)
    closed_loop_hp_life: ClosedLoopHPLifeConfig = field(
        default_factory=ClosedLoopHPLifeConfig
    )
    food_patch_signal: FoodPatchSignalConfig = field(default_factory=FoodPatchSignalConfig)
    deme_selection: DemeSelectionConfig = field(default_factory=DemeSelectionConfig)
    stepping_stone_reward: SteppingStoneRewardConfig = field(
        default_factory=SteppingStoneRewardConfig
    )
    task_switch_cost: TaskSwitchCostConfig = field(default_factory=TaskSwitchCostConfig)

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

    @property
    def effective_sexual_config(self) -> SexualRecombinationConfig:
        """Return chamber/crossover knobs, enabling Avida defaults when sexual."""

        if self.sexual_recombination.enabled:
            return self.sexual_recombination
        if self.reproduction.is_sexual:
            return replace(self.sexual_recombination, enabled=True)
        return self.sexual_recombination

    def to_dict(self) -> dict[str, JsonValue]:
        payload: dict[str, JsonValue] = {
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
        if self.metabolism.enabled or self.metabolism.basal_runtime_atp_cost > 0:
            payload["metabolism"] = self.metabolism.to_dict()
        if self.sexual_recombination.enabled or self.reproduction.is_sexual:
            payload["sexual_recombination"] = self.effective_sexual_config.to_dict()
        if self.environment.enabled:
            payload["environment"] = self.environment.to_dict()
        if self.phase_e.enabled:
            payload["phase_e"] = self.phase_e.to_dict()
        if self.logic9.enabled:
            payload["logic9"] = self.logic9.to_dict()
        if self.materials.enabled:
            payload["materials"] = self.materials.to_dict()
        if self.closed_loop_hp_life.enabled:
            payload["closed_loop_hp_life"] = self.closed_loop_hp_life.to_dict()
        if self.food_patch_signal.enabled:
            payload["food_patch_signal"] = self.food_patch_signal.to_dict()
        if self.deme_selection.enabled:
            payload["deme_selection"] = self.deme_selection.to_dict()
        if self.stepping_stone_reward.enabled:
            payload["stepping_stone_reward"] = self.stepping_stone_reward.to_dict()
        if self.task_switch_cost.enabled:
            payload["task_switch_cost"] = self.task_switch_cost.to_dict()
        return payload

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
        metabolism_raw = data.get("metabolism")
        sexual_raw = data.get("sexual_recombination")
        environment_raw = data.get("environment")
        phase_e_raw = data.get("phase_e")
        logic9_raw = data.get("logic9")
        materials_raw = data.get("materials")
        closed_loop_hp_life_raw = data.get("closed_loop_hp_life")
        food_patch_signal_raw = data.get("food_patch_signal")
        deme_selection_raw = data.get("deme_selection")
        stepping_stone_reward_raw = data.get("stepping_stone_reward")
        task_switch_cost_raw = data.get("task_switch_cost")
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
            metabolism=MetabolicConfig.from_dict(metabolism_raw)
            if isinstance(metabolism_raw, Mapping)
            else MetabolicConfig(),
            sexual_recombination=SexualRecombinationConfig.from_dict(sexual_raw)
            if isinstance(sexual_raw, Mapping)
            else SexualRecombinationConfig(),
            environment=EnvironmentConfig.from_dict(environment_raw)
            if isinstance(environment_raw, Mapping)
            else EnvironmentConfig(),
            phase_e=PhaseESubstrateConfig.from_dict(phase_e_raw)
            if isinstance(phase_e_raw, Mapping)
            else PhaseESubstrateConfig(),
            logic9=Logic9ReactionConfig.from_dict(logic9_raw)
            if isinstance(logic9_raw, Mapping)
            else Logic9ReactionConfig(),
            materials=MaterialsConfig.from_dict(materials_raw)
            if isinstance(materials_raw, Mapping)
            else MaterialsConfig(),
            closed_loop_hp_life=ClosedLoopHPLifeConfig.from_dict(closed_loop_hp_life_raw)
            if isinstance(closed_loop_hp_life_raw, Mapping)
            else ClosedLoopHPLifeConfig(),
            food_patch_signal=FoodPatchSignalConfig.from_dict(food_patch_signal_raw)
            if isinstance(food_patch_signal_raw, Mapping)
            else FoodPatchSignalConfig(),
            deme_selection=DemeSelectionConfig.from_dict(deme_selection_raw)
            if isinstance(deme_selection_raw, Mapping)
            else DemeSelectionConfig(),
            stepping_stone_reward=SteppingStoneRewardConfig.from_dict(stepping_stone_reward_raw)
            if isinstance(stepping_stone_reward_raw, Mapping)
            else SteppingStoneRewardConfig(),
            task_switch_cost=TaskSwitchCostConfig.from_dict(task_switch_cost_raw)
            if isinstance(task_switch_cost_raw, Mapping)
            else TaskSwitchCostConfig(),
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
    # Block zero-endowment live births (Iy<=0): fraction→0 or residual×fraction rounds to 0.
    if organism.atp_state.runtime_available >= config.parent_atp_cost:
        remaining_after_cost = organism.atp_state.runtime_available - config.parent_atp_cost
        projected_iy = round(remaining_after_cost * config.offspring_atp_fraction, 10)
        if projected_iy <= 0:
            reasons.append("offspring_atp_zero")
    phase_e_state = getattr(organism, "phase_e_state", None)
    if (
        phase_e_state is not None
        and getattr(phase_e_state, "gate_reproduction", False)
        and not getattr(getattr(phase_e_state, "role", None), "propagule_eligible", True)
    ):
        reasons.append("not_propagule_eligible")
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
    mate: GenesisOrganism | None = None,
    sexual: SexualRecombinationConfig | None = None,
    skip_parent_costs: bool = False,
    recombination_record: RecombinationRecord | None = None,
    offspring_runtime_atp_override: float | None = None,
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
    if skip_parent_costs:
        decision = ReproductionDecision(True, ())
    else:
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
        min_runtime_atp_met=(
            True
            if skip_parent_costs
            else parent.atp_state.runtime_available >= config.min_runtime_atp
        ),
        parent_cost_payable=(
            True
            if skip_parent_costs
            else parent.atp_state.runtime_available >= config.parent_atp_cost
        ),
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
    sexual_cfg = sexual if sexual is not None else (
        SexualRecombinationConfig(enabled=True) if config.is_sexual else SexualRecombinationConfig()
    )
    if config.is_sexual and recombination_record is None and not skip_parent_costs:
        mate_reason = _sexual_mate_block_reason(parent, mate, config)
        if mate_reason is not None:
            return _blocked_reproduction_result(
                parent=parent,
                config=config,
                alive_result=alive_result,
                birth_tick=birth_tick,
                generation=generation,
                reason=mate_reason,
                capacity_available=True,
            )
        if (
            mate is not None
            and sexual_cfg.same_length_only
            and len(parent.genome.to_compact()) != len(mate.genome.to_compact())
        ):
            return _blocked_reproduction_result(
                parent=parent,
                config=config,
                alive_result=alive_result,
                birth_tick=birth_tick,
                generation=generation,
                reason="same_length_sex_not_met",
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
    if skip_parent_costs:
        offspring_atp = (
            offspring_runtime_atp_override
            if offspring_runtime_atp_override is not None
            else round(parent_after.atp_state.runtime_available * config.offspring_atp_fraction, 10)
        )
    else:
        # Ip = runtime after basal settle (caller) and after parent_atp_cost;
        # Iy = Ip * offspring_atp_fraction. Refuse zero-endowment live births.
        available_before_cost = parent_after.atp_state.runtime_available
        remaining_after_cost = available_before_cost - config.parent_atp_cost
        offspring_atp = round(remaining_after_cost * config.offspring_atp_fraction, 10)
        if config.parent_atp_cost > 0 and available_before_cost < config.parent_atp_cost:
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
        if offspring_atp <= 0:
            blocked = ReproductionDecision(False, ("offspring_atp_zero",))
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
    recombination = recombination_record
    source_genome = parent.genome
    if recombination is not None:
        source_genome = SemanticGenome.from_compact(
            recombination.child_genome_bits, spec=parent.genome.spec
        )
    elif config.is_sexual and not skip_parent_costs:
        if mate is None:
            return _blocked_reproduction_result(
                parent=parent,
                config=config,
                alive_result=alive_result,
                birth_tick=birth_tick,
                generation=generation,
                reason="no_viable_mate",
                capacity_available=True,
            )
        do_recombine = True
        if sexual_cfg.recombination_prob <= 0.0:
            do_recombine = False
        elif sexual_cfg.recombination_prob < 1.0:
            do_recombine = stream.fork("birth_chamber").random() < sexual_cfg.recombination_prob
        if do_recombine:
            try:
                recombination = recombine_positional_segment(
                    parent_a_id=parent.id,
                    parent_b_id=mate.id,
                    parent_a_bits=parent.genome.to_compact(),
                    parent_b_bits=mate.genome.to_compact(),
                    parent_a_genome_digest=parent.genome.digest(),
                    parent_b_genome_digest=mate.genome.digest(),
                    rng=stream.fork("recombination"),
                    codon_width=parent.genome.spec.codon_width,
                    spec=parent.genome.spec,
                )
            except ValueError:
                return _blocked_reproduction_result(
                    parent=parent,
                    config=config,
                    alive_result=alive_result,
                    birth_tick=birth_tick,
                    generation=generation,
                    reason="recombination_no_overlapping_codon",
                    capacity_available=True,
                )
            source_genome = SemanticGenome.from_compact(
                recombination.child_genome_bits, spec=parent.genome.spec
            )
    mutation_plan = build_mutation_plan(
        plan_id=_reproduction_event_id(
            parent.id, "mutation_plan", birth_tick, stream.state_digest()
        ),
        parent_genome_digest=source_genome.digest(),
        bit_flip_rate=mutation_config.bit_flip_rate,
        insertion_rate=mutation_config.insertion_rate,
        deletion_rate=mutation_config.deletion_rate,
        rng_state_digest_before=stream.state_digest(),
    )
    if recombination is not None:
        mutation_plan = replace(
            mutation_plan,
            operator_sequence=(
                MutationOperator.RECOMBINE_WITH_PARTNER.value,
                *mutation_plan.operator_sequence,
            ),
            mutation_budget=max(
                mutation_plan.mutation_budget, len(mutation_plan.operator_sequence) + 1
            ),
        )
    if structural_mutation_config is not None:
        program = build_genome_program(
            source_genome.to_compact(),
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
            original_genome=source_genome,
            mutated_genome=mutated_genome,
            mutation_count=1,
            operations=(f"structural:{structural_record.kind}:{structural_record.digest}",),
            rng_digest=structural_record.rng_state_digest_after,
        )
    else:
        mutation = mutate_genome(source_genome, mutation_config, rng=stream.fork("mutation"))
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
        phase_e_state=inherit_phase_e_state(
            getattr(parent, "phase_e_state", None), child_id=resolved_child_id
        ),
        materials_state=inherit_materials_organism_state(
            getattr(parent, "materials_state", None)
            if isinstance(getattr(parent, "materials_state", None), MaterialsOrganismState)
            else None,
            child_id=resolved_child_id,
            inherit_intracellular=False,
            default_permeability=(
                getattr(parent.materials_state, "membrane_permeability", 1.0)
                if getattr(parent, "materials_state", None) is not None
                else 1.0
            ),
        ),
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
        second_parent_id=None if recombination is None else recombination.parent_b_id,
        recombination_start_index=None if recombination is None else recombination.start_index,
        recombination_end_index=None if recombination is None else recombination.end_index,
        recombination_digest=None if recombination is None else recombination.digest(),
        recombination_window_differed=None
        if recombination is None
        else (
            recombination.parent_a_bits[recombination.start_index : recombination.end_index]
            != recombination.parent_b_bits[recombination.start_index : recombination.end_index]
        ),
    )
    child_genome_result = ChildGenomeResult(
        child_id=resolved_child_id,
        parent_id=parent.id,
        parent_genome_digest=parent.genome.digest(),
        child_genome_digest=child.genome.digest(),
        mutation_digest=mutation.digest(),
        mutation_count=mutation.mutation_count,
        genome_bits=child.genome.to_compact(),
        second_parent_id=None if recombination is None else recombination.parent_b_id,
        second_parent_genome_digest=(
            None if recombination is None else recombination.parent_b_genome_digest
        ),
        recombination_digest=None if recombination is None else recombination.digest(),
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
        second_parent_id=None if recombination is None else recombination.parent_b_id,
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
        recombination_record=recombination,
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
    resources_before = dict(working_world.resources)
    env_cfg = configs.environment
    env_tick = population.generation
    env_state = population.environment
    if env_cfg.enabled and env_state is None:
        env_state = EnvironmentState.initialize(env_cfg, tick=env_tick)
    mat_cfg = configs.materials
    mat_state = population.materials
    if mat_cfg.enabled and mat_state is None:
        mat_state = MaterialsState.initialize(mat_cfg, tick=env_tick)
    working_mat_pools: dict[str, float] = dict(mat_state.pools) if mat_state is not None else {}
    working_mat_grids: dict[str, dict[tuple[int, int], float]] = (
        {name: dict(cells) for name, cells in mat_state.grids.items()} if mat_state is not None else {}
    )
    materials_coupling_events: list[MaterialEvent] = []
    materials_consumed: dict[str, float] = {}
    hazard_cost = 0.0
    if env_cfg.enabled and env_state is not None and env_cfg.hazard_atp_scale > 0:
        hazard_cost = round(env_cfg.hazard_atp_scale * env_state.hazard_intensity, 10)
    before_count = len(population.organisms)
    lineage = _ensure_lineage(population)
    lineage_by_id = {record.organism_id: record for record in lineage}
    last_known_fitness_by_id = {record.organism_id: record.score for record in population.fitness}
    organism_clones = [_clone_organism(organism) for organism in population.organisms]
    if configs.phase_e.enabled:
        organism_clones = list(attach_phase_e_to_organisms(organism_clones, configs.phase_e))
    if configs.materials.enabled:
        organism_clones = list(attach_materials_to_organisms(organism_clones, configs.materials))
    working_deme_state = (
        DemeState.from_dict(population.deme.to_dict())
        if population.deme is not None
        else (build_deme_state(organism_clones) if configs.phase_e.enabled and configs.phase_e.demes.enabled else None)
    )
    if working_deme_state is not None and not working_deme_state.demes and configs.phase_e.demes.enabled:
        working_deme_state = build_deme_state(organism_clones)
    phase_e_messages: list[DemeMessage] = []
    logic9_events: list[Logic9ReactionEvent] = []
    logic9_pool = {logic9_resource_name(task): 8.0 for task in LOGIC9_TASKS}
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
    sexual_cfg = configs.effective_sexual_config
    waiting: list[IncipientOffspring] = list(population.birth_chamber.waiting)
    birth_placements: list[BirthPlacementRecord] = []
    chamber_rng = stream.fork("birth_chamber") if sexual_cfg.uses_birth_chamber else None
    if sexual_cfg.uses_birth_chamber and chamber_rng is not None:
        waiting, lineage, births, deaths, _, _ = _drain_chamber_pairs(
            waiting=waiting,
            configs=configs,
            sexual_cfg=sexual_cfg,
            stream=stream,
            chamber_rng=chamber_rng,
            working_world=working_world,
            live_positions=live_positions,
            survivors=survivors,
            pending=organism_clones,
            children=children,
            lineage=lineage,
            births=births,
            deaths=deaths,
            current_tick=current_tick,
            current_organism=None,
            alive_result=None,
            placements=birth_placements,
        )
    stigmergy_enabled = configs.enable_nexus_stigmergy or (
        configs.capsule_transfer is not None and configs.capsule_transfer.enabled
    )
    working_nexus_layer = (
        NexusStigmergyLayer.from_dict(nexus_layer.to_dict())
        if nexus_layer is not None
        else (NexusStigmergyLayer() if stigmergy_enabled else None)
    )
    # Wave 1e / Amd 04 activity-matched yoke: run-wide successful-accept budget
    # (cap-down). Copied onto the working nexus layer; excluded from nexus digest.
    adoption_budget_box: list[int] | None = None
    if working_nexus_layer is not None:
        prior = (
            None
            if nexus_layer is None
            else nexus_layer.adoption_budget_remaining
        )
        if isinstance(prior, list) and prior:
            working_nexus_layer.adoption_budget_remaining = prior
            adoption_budget_box = prior
        elif (
            configs.capsule_transfer is not None
            and configs.capsule_transfer.max_successful_adoptions is not None
        ):
            adoption_budget_box = [int(configs.capsule_transfer.max_successful_adoptions)]
            working_nexus_layer.adoption_budget_remaining = adoption_budget_box

    active_food_patches: tuple[FoodPatchState, ...] = ()
    food_patch_signal_records: list[FoodPatchSignalRecord] = []
    task_switch_cost_records: list[TaskSwitchCostRecord] = []
    last_task_by_organism: dict[str, str] = {}
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
        capsule_action_coupling = (
            configs.capsule_transfer
            if configs.capsule_transfer is not None
            and configs.capsule_transfer.enabled
            and configs.capsule_transfer.adoption_effect_action
            else None
        )
        nexus_signal_count_before = (
            0 if working_nexus_layer is None else len(working_nexus_layer.signals)
        )
        capsule_store_digest_before = (
            None if working_nexus_layer is None else working_nexus_layer.digest()
        )
        for _ in range(configs.ticks_per_generation):
            world_width = int(getattr(world, "width", getattr(world, "cols", 0)) or 0)
            world_height = int(getattr(world, "height", getattr(world, "rows", 0)) or 0)
            active_food_patches = _he02_sync_food_patches(
                tick=current_tick,
                width=world_width,
                height=world_height,
                config=configs.food_patch_signal,
                active=active_food_patches,
                seed_key=f"he02|{current_tick}|{len(population.organisms)}",
            )
            if configs.food_patch_signal.enabled:
                _he02_place_patch_resources(
                    world,
                    active_food_patches,
                    amount=float(configs.food_patch_signal.patch_atp),
                )
            if configs.metabolism.enabled and configs.metabolism.basal_runtime_atp_cost > 0:
                payable = min(
                    organism.atp_state.runtime_available,
                    configs.metabolism.basal_runtime_atp_cost,
                )
                if payable > 0:
                    organism.atp_state.debit_runtime(
                        payable,
                        tick=current_tick,
                        organism_id=organism.id,
                        codon="000",
                        action=configs.metabolism.action_name,
                        reason=configs.metabolism.reason,
                    )
            if hazard_cost > 0:
                payable_hazard = min(organism.atp_state.runtime_available, hazard_cost)
                if payable_hazard > 0:
                    organism.atp_state.debit_runtime(
                        payable_hazard,
                        tick=current_tick,
                        organism_id=organism.id,
                        codon="000",
                        action="ENVIRONMENT_HAZARD",
                        reason="environment_hazard",
                    )
            # Closed-loop P1: post-ATP settle / pre-birth (before nexus + reproduce).
            # Forks the live generation stream; never a parallel RNG tree.
            if configs.closed_loop_hp_life.enabled:
                mutated = apply_closed_loop_hp_life(
                    [organism],
                    config=configs.closed_loop_hp_life,
                    stream=stream,
                    mutation_config=configs.mutation,
                    tick=current_tick,
                )
                organism = mutated[0]
                if configs.closed_loop_hp_life.outcross_enabled:
                    silence_outcross_locus(organism, configs.closed_loop_hp_life)
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
                        if adoption_budget_box is not None and adoption_budget_box[0] <= 0:
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
                                    blocked_reason=(
                                        CapsuleAdoptionBlockedReason.ACTIVITY_MATCH_BUDGET_EXHAUSTED.value
                                    ),
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
                            if adoption_budget_box is not None:
                                adoption_budget_box[0] = max(0, adoption_budget_box[0] - 1)
                            if capsule_action_coupling is not None:
                                _apply_capsule_action_bias(
                                    organism, capsule, capsule_action_coupling
                                )
                            if (
                                configs.food_patch_signal.enabled
                                and active_food_patches
                                and configs.capsule_transfer is not None
                                and str(
                                    getattr(
                                        configs.capsule_transfer.shuffle_mode,
                                        "value",
                                        configs.capsule_transfer.shuffle_mode,
                                    )
                                )
                                == "off"
                            ):
                                payload_token = capsule_payload_action(capsule)
                                true_xy = _he02_true_patch_xy(active_food_patches)
                                if payload_token is not None and true_xy is not None:
                                    food_patch_signal_records.append(
                                        FoodPatchSignalRecord(
                                            tick=int(current_tick),
                                            emitter_id=str(capsule.source_organism_id),
                                            receiver_id=str(organism.id),
                                            payload_digest=canonical_digest(
                                                {"payload": str(payload_token)}
                                            ),
                                            target_true=true_xy,
                                            moved=(
                                                getattr(organism, "capsule_action_bias", None)
                                                == MOVE_TOWARD_CAPSULE_TARGET
                                            ),
                                            ate_at_target=False,
                                            payload_token=str(payload_token),
                                        )
                                    )
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
            if configs.phase_e.enabled:
                refresh_phase_e_sensory(
                    organism,
                    world=working_world,
                    environment=env_state,
                    tick=current_tick,
                )
            event = organism.step(working_world, trace, blocked_positions=blocked_positions)
            live_positions[organism.id] = organism.position
            if configs.food_patch_signal.enabled and active_food_patches:
                _he02_try_harvest_at_nav_target(
                    organism,
                    working_world,
                    patches=active_food_patches,
                    config=configs.food_patch_signal,
                    tick=int(current_tick),
                    records=food_patch_signal_records,
                )
            if configs.task_switch_cost.enabled:
                prev_task = getattr(organism, "last_task_class", None)
                if prev_task is None:
                    prev_task = last_task_by_organism.get(str(organism.id))
                current_task, switch_record = apply_task_switch_cost(
                    tick=int(current_tick),
                    organism_id=str(organism.id),
                    action=str(event.action),
                    previous_task=prev_task,
                    config=configs.task_switch_cost,
                    atp_state=organism.atp_state,
                )
                if current_task is not None:
                    last_task_by_organism[str(organism.id)] = current_task
                    organism.last_task_class = current_task
                if switch_record is not None:
                    task_switch_cost_records.append(switch_record)
            if capsule_action_coupling is not None:
                _track_capsule_payload_action(organism, event, capsule_action_coupling)
            if configs.logic9.enabled:
                logic9_events.extend(
                    apply_logic9_runtime_bonus(
                        organism,
                        tick=current_tick,
                        config=configs.logic9,
                        pool=logic9_pool,
                    )
                )
            if configs.materials.enabled:
                did_eat = bool(event.world_delta.get("lumen_interaction")) or (
                    event.action == "EAT_LUMEN" and event.reason == "lumen_consumed"
                )
                coupling = apply_organism_material_coupling(
                    organism,
                    working_mat_pools,
                    working_mat_grids,
                    configs.materials,
                    tick=current_tick,
                    did_eat=did_eat,
                )
                materials_coupling_events.extend(coupling)
                for item in coupling:
                    if item.event_type == "uptake" and item.material:
                        materials_consumed[item.material] = round(
                            materials_consumed.get(item.material, 0.0) + item.amount, 10
                        )
            if configs.phase_e.enabled and working_deme_state is not None:
                phase_e_messages.extend(
                    apply_deme_messaging_after_event(
                        organism,
                        event,
                        working_deme_state,
                        configs.phase_e.demes,
                        tick=current_tick,
                    )
                )
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
                        payload_action=_he02_payload_action(
                        organism,
                        configs.food_patch_signal,
                        active_food_patches,
                        capsule_action_coupling,
                    ),
                    )
                    working_nexus_layer.deposit(capsule, position=organism.position)
                    capsule_emit_count += 1
                    if (
                        configs.food_patch_signal.enabled
                        and active_food_patches
                        and configs.capsule_transfer is not None
                        and configs.capsule_transfer.enabled
                        and str(getattr(configs.capsule_transfer.shuffle_mode, "value", configs.capsule_transfer.shuffle_mode))
                        == "off"
                    ):
                        payload_token = capsule_payload_action(capsule)
                        true_xy = _he02_true_patch_xy(active_food_patches)
                        if payload_token is not None and true_xy is not None:
                            food_patch_signal_records.append(
                                FoodPatchSignalRecord(
                                    tick=int(current_tick),
                                    emitter_id=str(organism.id),
                                    receiver_id=str(organism.id),
                                    payload_digest=canonical_digest(
                                        {"payload": str(payload_token)}
                                    ),
                                    target_true=true_xy,
                                    moved=False,
                                    ate_at_target=False,
                                    payload_token=str(payload_token),
                                )
                            )
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
                life = configs.closed_loop_hp_life
                copy_mode = resolve_copy_self_mode(organism.genome.to_compact(), life)
                codon_ran = (
                    event.world_delta.get("reproduction") == "population_lifecycle_required"
                )
                enters_chamber = copy_mode == "chamber" or (
                    copy_mode != "asexual" and sexual_cfg.uses_birth_chamber
                )
                if enters_chamber and not codon_ran:
                    continue
                attempts += 1
                if copy_mode == "chamber" and not sexual_cfg.uses_birth_chamber:
                    blocked_reproduction += 1
                    reproduction_result = _blocked_reproduction_result(
                        parent=organism,
                        config=configs.reproduction,
                        alive_result=alive_result,
                        birth_tick=current_tick,
                        generation=population.generation,
                        reason="outcross_chamber_required",
                        capacity_available=True,
                    )
                    _replace_last_event(
                        trace,
                        _with_reproduction_delta(
                            event,
                            parent_after=organism,
                            reproduction_result=reproduction_result,
                            succeeded=False,
                            reason="outcross_chamber_required",
                            parent_id=organism.id,
                            child_id=None,
                            event_id=reproduction_result.event_id,
                        ),
                    )
                    continue
                if copy_mode != "asexual" and sexual_cfg.uses_birth_chamber:
                    (
                        organism,
                        reproduction_result,
                        waiting,
                        lineage,
                        births,
                        deaths,
                        blocked_reproduction,
                        queued_event,
                    ) = _handle_chamber_copy_self(
                        organism=organism,
                        event=event,
                        configs=configs,
                        sexual_cfg=sexual_cfg,
                        alive_result=alive_result,
                        generation=population.generation,
                        birth_tick=current_tick,
                        stream=stream,
                        chamber_rng=chamber_rng,
                        waiting=waiting,
                        working_world=working_world,
                        live_positions=live_positions,
                        survivors=survivors,
                        pending=organism_clones,
                        children=children,
                        lineage=lineage,
                        births=births,
                        deaths=deaths,
                        blocked_reproduction=blocked_reproduction,
                        placements=birth_placements,
                    )
                    _replace_last_event(trace, queued_event)
                    continue
                mate = None
                repro = configs.reproduction
                if copy_mode == "asexual":
                    repro = replace(
                        configs.reproduction,
                        reproduction_mode=ReproductionMode.ASEXUAL,
                    )
                elif configs.reproduction.is_sexual:
                    mate = _select_viable_mate(
                        parent=organism,
                        candidates=_live_mate_candidates(
                            parent_id=organism.id,
                            stepped=survivors,
                            pending=organism_clones,
                            children=children,
                            live_positions=live_positions,
                        ),
                        min_runtime_atp=configs.reproduction.min_runtime_atp,
                    )
                    if mate is None:
                        blocked_reproduction += 1
                        reproduction_result = _blocked_reproduction_result(
                            parent=organism,
                            config=configs.reproduction,
                            alive_result=alive_result,
                            birth_tick=current_tick,
                            generation=population.generation,
                            reason="no_viable_mate",
                            capacity_available=True,
                        )
                        _replace_last_event(
                            trace,
                            _with_reproduction_delta(
                                event,
                                parent_after=organism,
                                reproduction_result=reproduction_result,
                                succeeded=False,
                                reason="no_viable_mate",
                                parent_id=organism.id,
                                child_id=None,
                                event_id=reproduction_result.event_id,
                            ),
                        )
                        continue
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
                    repro,
                    configs.mutation,
                    alive_result=alive_result,
                    generation=population.generation,
                    birth_tick=current_tick,
                    rng=stream.fork(f"reproduce/{organism.id}/{current_tick}"),
                    structural_mutation_config=configs.structural_mutation,
                    world=working_world,
                    live_positions=live_positions,
                    mate=mate,
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
                    if (
                        configs.reproduction.offspring_placement
                        is OffspringPlacementPolicy.REPLACE_OCCUPIED
                    ):
                        occupant_id = next(
                            (
                                oid
                                for oid, pos in live_positions.items()
                                if pos == placement and oid not in {organism.id, child.id}
                            ),
                            None,
                        )
                        if occupant_id is not None:
                            live_positions.pop(occupant_id, None)
                            survivors[:] = [item for item in survivors if item.id != occupant_id]
                            deaths += 1
                            lineage = _mark_death(lineage, occupant_id, current_tick)
                    reproduction_result = _finalize_reproduction_placement(
                        reproduction_result,
                        placement=placement,
                        policy=configs.reproduction.offspring_placement,
                    )
                    child = reproduction_result.child
                    if child is None:
                        raise RuntimeError("finalized reproduction unexpectedly lost child")
                    children.append(child)
                    if configs.closed_loop_hp_life.outcross_enabled:
                        silence_outcross_locus(child, configs.closed_loop_hp_life)
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
        starvation_floor = configs.death_monitoring.starvation_floor
        if (
            starvation_floor is not None
            and organism.atp_state.runtime_available <= starvation_floor
        ):
            organism._low_energy_ticks += 1
        else:
            organism._low_energy_ticks = 0
        death_classification = classify_death(
            organism_id=organism.id,
            tick=current_tick,
            runtime_atp_before=runtime_before,
            runtime_atp_after=organism.atp_state.runtime_available,
            alive_result=alive_result,
            birth_tick=None if lineage_record is None else lineage_record.birth_tick,
            config=configs.death_monitoring,
            blocked_action_reasons=blocked_action_reasons,
            low_energy_ticks=organism._low_energy_ticks,
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

    if sexual_cfg.uses_birth_chamber and chamber_rng is not None:
        waiting, lineage, births, deaths, blocked_reproduction = _expire_chamber_waiters(
            waiting=waiting,
            configs=configs,
            sexual_cfg=sexual_cfg,
            stream=stream,
            working_world=working_world,
            live_positions=live_positions,
            survivors=survivors,
            pending=organism_clones,
            children=children,
            lineage=lineage,
            births=births,
            deaths=deaths,
            blocked_reproduction=blocked_reproduction,
            current_tick=current_tick,
            placements=birth_placements,
        )
        waiting, lineage, births, deaths, _, _ = _drain_chamber_pairs(
            waiting=waiting,
            configs=configs,
            sexual_cfg=sexual_cfg,
            stream=stream,
            chamber_rng=chamber_rng,
            working_world=working_world,
            live_positions=live_positions,
            survivors=survivors,
            pending=organism_clones,
            children=children,
            lineage=lineage,
            births=births,
            deaths=deaths,
            current_tick=current_tick,
            current_organism=None,
            alive_result=None,
            placements=birth_placements,
        )

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
    environment_records: tuple[EnvironmentEvent, ...] = ()
    environment_snapshot: EnvironmentSnapshot | None = None
    environment_world_events: tuple[WorldEvent, ...] = ()
    if env_cfg.enabled:
        consumed_total = local_resource_consumed(resources_before, working_world.resources)
        primary = env_cfg.resources[0].name if env_cfg.resources else "lumen"
        env_result = step_environment(
            working_world,
            env_state or EnvironmentState.initialize(env_cfg, tick=env_tick),
            env_cfg,
            tick=env_tick,
            consumed={primary: consumed_total},
            occupied_positions={item.position for item in next_organisms},
        )
        working_world = env_result.world
        env_state = env_result.state
        environment_records = env_result.events
        environment_snapshot = env_result.snapshot
        environment_world_events = env_result.world_events
        if traces:
            for event in environment_world_events:
                traces[0].append_world_event(replace(event, sequence=traces[0].next_sequence()))
    materials_records: tuple[MaterialEvent, ...] = ()
    materials_snapshot: MaterialsSnapshot | None = None
    materials_world_events: tuple[WorldEvent, ...] = ()
    if mat_cfg.enabled:
        coupling_state = MaterialsState(
            tick=env_tick,
            pools=working_mat_pools,
            grids=working_mat_grids,
            cumulative_inflow=dict(mat_state.cumulative_inflow) if mat_state is not None else {},
            cumulative_outflow=dict(mat_state.cumulative_outflow) if mat_state is not None else {},
            cumulative_consumed=dict(mat_state.cumulative_consumed) if mat_state is not None else {},
            cumulative_reacted=dict(mat_state.cumulative_reacted) if mat_state is not None else {},
        )
        mat_result = step_materials(
            coupling_state,
            mat_cfg,
            tick=env_tick,
            consumed=materials_consumed,
            organisms=next_organisms,
            world=working_world,
        )
        mat_state = mat_result.state
        materials_records = tuple((*materials_coupling_events, *mat_result.events))
        materials_snapshot = mat_result.snapshot
        materials_world_events = mat_result.world_events
        if traces:
            for event in materials_world_events:
                traces[0].append_world_event(replace(event, sequence=traces[0].next_sequence()))
    skip_legacy = env_cfg.enabled and env_cfg.skip_legacy_respawn
    if not skip_legacy:
        respawn_ns = configs.runtime_resource_policy.seed_namespace
        respawn_rng = stream.fork(f"{respawn_ns}/tick-{current_tick}")
        working_world, resource_events = _apply_runtime_resource_policy(
            working_world,
            configs.runtime_resource_policy,
            tick=current_tick,
            rng=respawn_rng,
            occupied_positions={item.position for item in next_organisms},
        )
        for _extra_draw in range(configs.runtime_resource_policy.respawn_draws_per_tick - 1):
            working_world, extra_events = _apply_runtime_resource_policy(
                working_world,
                configs.runtime_resource_policy,
                tick=current_tick,
                rng=respawn_rng,
                occupied_positions={item.position for item in next_organisms},
            )
            resource_events = (*resource_events, *extra_events)
    if configs.phase_e.enabled and working_deme_state is not None:
        fitness_by_id = {item.organism_id: item.score for item in fitness_results}
        working_deme_state, _repl = maybe_replicate_demes(
            working_deme_state,
            next_organisms,
            fitness_by_id,
            configs.phase_e.demes,
            tick=current_tick,
        )
        refreshed = build_deme_state(next_organisms)
        generation_by_id = {item.deme_id: item.generation for item in working_deme_state.demes}
        refreshed.demes = tuple(
            replace(item, generation=generation_by_id.get(item.deme_id, item.generation))
            for item in refreshed.demes
        )
        extra_demes = tuple(
            item
            for item in working_deme_state.demes
            if item.deme_id not in {deme.deme_id for deme in refreshed.demes}
        )
        if extra_demes:
            refreshed.demes = tuple((*refreshed.demes, *extra_demes))
        refreshed.inbox = working_deme_state.inbox
        refreshed.replication_events = working_deme_state.replication_events
        working_deme_state = refreshed
    next_population = PopulationState(
        generation=population.generation + 1,
        tick=current_tick,
        organisms=next_organisms,
        lineage=lineage,
        fitness=tuple(sorted(fitness_results, key=lambda item: item.organism_id)),
        birth_chamber=BirthChamberState(waiting=tuple(waiting)),
        environment=env_state if env_cfg.enabled else None,
        deme=working_deme_state if configs.phase_e.enabled and configs.phase_e.demes.enabled else None,
        materials=mat_state if mat_cfg.enabled else None,
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
        environment_records=environment_records,
        environment_snapshot=environment_snapshot,
        environment_world_events=environment_world_events,
        phase_e_messages=tuple(phase_e_messages),
        deme_state=working_deme_state
        if configs.phase_e.enabled and configs.phase_e.demes.enabled
        else None,
        birth_placement_records=tuple(birth_placements),
        logic9_events=tuple(logic9_events),
        materials_records=materials_records,
        materials_snapshot=materials_snapshot,
        materials_world_events=materials_world_events,
        food_patch_signal_records=tuple(food_patch_signal_records),
        task_switch_cost_records=tuple(task_switch_cost_records),
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
        and ((x, y) not in occupied_positions or policy.respawn_under_organisms)
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


def _he02_true_patch_xy(
    patches: tuple[FoodPatchState, ...],
    position: tuple[int, int] | None = None,
) -> tuple[int, int] | None:
    """Return canonical active-patch coordinates for payload↔patch MI.

    Uses lexicographic first patch so Y is environment ground truth, not
    receiver-local nearest (which would desynchronize from emitter encoding).
    ``position`` is accepted for call-site compatibility and ignored.
    """

    if not patches:
        return None
    _ = position
    patch = min(patches, key=lambda item: (int(item.x), int(item.y), str(item.patch_id)))
    return (int(patch.x), int(patch.y))


def _he02_payload_action(
    organism: GenesisOrganism,
    food_cfg: FoodPatchSignalConfig,
    patches: tuple[FoodPatchState, ...],
    capsule_action_coupling: CapsuleTransferConfig | None,
) -> str | None:
    """Prefer food-patch coordinate payloads when E1 is enabled and visible."""

    if food_cfg.enabled and patches:
        pos = organism.position
        for patch in patches:
            dx = abs(int(pos[0]) - int(patch.x))
            dy = abs(int(pos[1]) - int(patch.y))
            if max(dx, dy) <= int(food_cfg.visibility_radius):
                return encode_patch_payload(patch.x, patch.y)
    if capsule_action_coupling is None:
        return None
    return organism.capsule_last_executed_action


def _he02_sync_food_patches(
    *,
    tick: int,
    width: int,
    height: int,
    config: FoodPatchSignalConfig,
    active: tuple[FoodPatchState, ...],
    seed_key: str,
) -> tuple[FoodPatchState, ...]:
    """Deterministic spawn/expiry using a tick-scoped hash stream."""

    if not config.enabled:
        return ()
    needed = max(2, int(config.patch_count) * 2)
    draws: list[float] = []
    # Local deterministic stream; does not touch global RNG.
    material = f"{seed_key}|food_patch|{tick}|{width}x{height}".encode()
    digest = hashlib.sha256(material).digest()
    cursor = 0
    while len(draws) < needed:
        if cursor + 4 > len(digest):
            digest = hashlib.sha256(digest + material).digest()
            cursor = 0
        chunk = int.from_bytes(digest[cursor : cursor + 4], "big")
        cursor += 4
        draws.append((chunk % 10_000_000) / 10_000_000.0)
    return spawn_patches_for_tick(
        tick=tick,
        width=width,
        height=height,
        config=config,
        rng_draw=draws,
        active=active,
    )


def _he02_place_patch_resources(
    world: object,
    patches: tuple[FoodPatchState, ...],
    *,
    amount: float,
) -> None:
    """Deposit patch ATP/resources onto the world grid when API allows."""

    place = getattr(world, "place_resource", None)
    if not callable(place):
        return
    for patch in patches:
        try:
            place((int(patch.x), int(patch.y)), float(amount))
        except Exception:
            # World APIs vary; HE02 records still capture signal MI without placement.
            continue


def _he02_try_harvest_at_nav_target(
    organism: GenesisOrganism,
    world: object,
    *,
    patches: tuple[FoodPatchState, ...],
    config: FoodPatchSignalConfig,
    tick: int,
    records: list[FoodPatchSignalRecord],
) -> bool:
    """Credit patch ATP when a guided organism occupies the signaled patch.

    Completes E1 wiring: MOVE_TOWARD_CAPSULE_TARGET previously never harvested,
    so receiver terminal ATP could not discriminate arms (oracle_gt_channel_off
    stayed false despite healthy MI). Selective value requires an *active* patch
    matching ``capsule_nav_target``.
    """

    _ = world
    target = getattr(organism, "capsule_nav_target", None)
    if target is None:
        return False
    pos = organism.position
    if (int(pos[0]), int(pos[1])) != (int(target[0]), int(target[1])):
        return False
    on_patch = any(
        (int(patch.x), int(patch.y)) == (int(target[0]), int(target[1]))
        for patch in patches
    )
    if not on_patch:
        return False
    credit = float(config.patch_atp)
    if credit <= 0.0:
        return False
    organism.atp_state.credit_runtime(
        credit,
        tick=int(tick),
        organism_id=str(organism.id),
        codon="000",
        action=MOVE_TOWARD_CAPSULE_TARGET,
        reason="he02_ate_at_signaled_patch",
    )
    receiver_id = str(organism.id)
    for index in range(len(records) - 1, -1, -1):
        record = records[index]
        if record.receiver_id != receiver_id or record.ate_at_target:
            continue
        records[index] = FoodPatchSignalRecord(
            tick=record.tick,
            emitter_id=record.emitter_id,
            receiver_id=record.receiver_id,
            payload_digest=record.payload_digest,
            target_true=record.target_true,
            moved=True,
            ate_at_target=True,
            payload_token=record.payload_token,
        )
        break
    return True


def _track_capsule_payload_action(
    organism: GenesisOrganism, event: TraceEvent, config: CapsuleTransferConfig
) -> None:
    """Remember the emitter's latest executed, non-signalling action.

    Only active under ``adoption_effect_action``; the value becomes the capsule
    payload (``event_pattern[1]``) on the next EMIT_NEXUS.
    """

    if event.action == "EMIT_NEXUS" or event.action in config.adoption_substitutable_actions:
        return
    if organism.action_runtime_config.counts_as_executed(event.status):
        organism.capsule_last_executed_action = event.action


def capsule_payload_action(capsule: CausalCapsule) -> str | None:
    """Behavioural payload carried by a capsule (``None`` for legacy capsules)."""

    for item in capsule.event_pattern:
        if item != "EMIT_NEXUS":
            return str(item)
    return None


def _apply_capsule_action_bias(
    organism: GenesisOrganism, capsule: CausalCapsule, config: CapsuleTransferConfig
) -> bool:
    """Install the adopted capsule's payload as the organism's action bias.

    Returns ``True`` when a bias was (re)installed. Unknown payloads are
    ignored so a scrambled control cannot inject unregistered actions.
    HE02 food-patch payloads (``PATCH:x:y``) install MOVE_TOWARD_CAPSULE_TARGET
    plus ``capsule_nav_target``.
    """

    action = capsule_payload_action(capsule)
    patch = decode_patch_payload(action)
    if patch is not None:
        if organism.action_registry.get(MOVE_TOWARD_CAPSULE_TARGET) is None:
            return False
        organism.capsule_action_bias = MOVE_TOWARD_CAPSULE_TARGET
        organism.capsule_action_bias_capsule_id = capsule.capsule_id
        organism.capsule_action_bias_substitutable = tuple(config.adoption_substitutable_actions)
        organism.capsule_nav_target = (int(patch[0]), int(patch[1]))
        return True
    # metadata fallback for HE02 emitters that stash coords without pattern rewrite
    meta = getattr(capsule, "metadata", None)
    if isinstance(meta, dict):
        raw = meta.get("food_patch")
        if isinstance(raw, (list, tuple)) and len(raw) == 2:
            try:
                target = (int(raw[0]), int(raw[1]))
            except (TypeError, ValueError):
                target = None
            if target is not None and organism.action_registry.get(MOVE_TOWARD_CAPSULE_TARGET) is not None:
                organism.capsule_action_bias = MOVE_TOWARD_CAPSULE_TARGET
                organism.capsule_action_bias_capsule_id = capsule.capsule_id
                organism.capsule_action_bias_substitutable = tuple(
                    config.adoption_substitutable_actions
                )
                organism.capsule_nav_target = target
                return True
    if action is None or organism.action_registry.get(action) is None:
        return False
    organism.capsule_action_bias = action
    organism.capsule_action_bias_capsule_id = capsule.capsule_id
    organism.capsule_action_bias_substitutable = tuple(config.adoption_substitutable_actions)
    return True


def _capsule_from_nexus_event(
    organism: GenesisOrganism,
    event: TraceEvent,
    tick: int,
    *,
    ttl: int,
    source_fitness: float | None = None,
    source_fitness_status: SourceFitnessStatus = SourceFitnessStatus.UNAVAILABLE,
    payload_action: str | None = None,
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
        event_pattern=(event.action,) if payload_action is None else (event.action, payload_action),
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
        phase_e_state=copy_phase_e_state(getattr(organism, "phase_e_state", None)),
        capsule_action_bias=organism.capsule_action_bias,
        capsule_action_bias_capsule_id=organism.capsule_action_bias_capsule_id,
        capsule_action_bias_substitutable=organism.capsule_action_bias_substitutable,
        capsule_last_executed_action=organism.capsule_last_executed_action,
        capsule_nav_target=organism.capsule_nav_target,
        last_task_class=getattr(organism, "last_task_class", None),
        materials_state=copy_materials_organism_state(
            getattr(organism, "materials_state", None)
            if isinstance(getattr(organism, "materials_state", None), MaterialsOrganismState)
            else None
        ),
    )
    clone._cursor = organism._cursor
    clone._step_index = organism._step_index
    clone._low_energy_ticks = organism._low_energy_ticks
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
    extra_delta: Mapping[str, JsonValue] | None = None,
    force_executed: bool = False,
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
    if (
        reproduction_result is not None
        and reproduction_result.recombination_record is not None
    ):
        record = reproduction_result.recombination_record
        delta["second_parent_id"] = record.parent_b_id
        delta["parent_ids"] = list(record.parent_ids)
        delta["recombination_digest"] = record.digest()
        delta["recombination_start_index"] = record.start_index
        delta["recombination_end_index"] = record.end_index
    if extra_delta:
        delta.update(dict(extra_delta))
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
        status="executed" if succeeded or force_executed else "blocked",
        reason=reason,
        ledger_entry_ids=tuple(event.ledger_entry_ids + reproduction_ledger_ids),
        genome_digest=event.genome_digest,
        world_digest_before=event.world_digest_before,
        cause_refs=event.cause_refs,
        config_hash=event.config_hash,
    )


def _organism_summary(organism: GenesisOrganism) -> dict[str, JsonValue]:
    payload: dict[str, JsonValue] = {
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
    phase_e_state = getattr(organism, "phase_e_state", None)
    if phase_e_state is not None and hasattr(phase_e_state, "to_dict"):
        payload["phase_e_state"] = phase_e_state.to_dict()
    materials_state = getattr(organism, "materials_state", None)
    if materials_state is not None and hasattr(materials_state, "to_dict"):
        payload["materials_state"] = materials_state.to_dict()
    return payload


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
    phase_e_raw = data.get("phase_e_state")
    if isinstance(phase_e_raw, Mapping):
        from codontrace.genesis.phase_e import PhaseEOrganismState

        organism.phase_e_state = PhaseEOrganismState.from_dict(phase_e_raw)
    materials_raw = data.get("materials_state")
    if isinstance(materials_raw, Mapping):
        organism.materials_state = MaterialsOrganismState.from_dict(materials_raw)
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
        second_parent_id=_optional_str(value, "second_parent_id"),
        second_parent_genome_digest=_optional_str(value, "second_parent_genome_digest"),
        recombination_digest=_optional_str(value, "recombination_digest"),
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
        second_parent_id=_optional_str(value, "second_parent_id"),
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


def _apply_parent_reproduction_costs(
    organism: GenesisOrganism,
    config: ReproductionConfig,
    birth_tick: int,
) -> tuple[list[int], float, str | None]:
    ledger_ids: list[int] = []
    available_before_cost = organism.atp_state.runtime_available
    if config.parent_atp_cost > 0 and available_before_cost < config.parent_atp_cost:
        return [], 0.0, "parent_atp_cost_not_payable"
    remaining_after_cost = available_before_cost - config.parent_atp_cost
    offspring_atp = round(remaining_after_cost * config.offspring_atp_fraction, 10)
    if offspring_atp <= 0:
        return [], 0.0, "offspring_atp_zero"
    debit_id = organism.atp_state.debit_runtime(
        config.parent_atp_cost,
        tick=birth_tick,
        organism_id=organism.id,
        codon="111",
        action="COPY_SELF",
        reason="parent_reproduction_cost",
    )
    if debit_id is None and config.parent_atp_cost > 0:
        return [], 0.0, "parent_atp_cost_not_payable"
    if debit_id is not None:
        ledger_ids.append(debit_id)
    transfer_id = organism.atp_state.debit_runtime(
        offspring_atp,
        tick=birth_tick,
        organism_id=organism.id,
        codon="111",
        action="COPY_SELF",
        reason="offspring_runtime_atp_transfer",
    )
    if transfer_id is not None:
        ledger_ids.append(transfer_id)
    return ledger_ids, offspring_atp, None


def _lookup_step_organism(
    organism_id: str,
    *,
    current: GenesisOrganism | None,
    survivors: Sequence[GenesisOrganism],
    pending: Sequence[GenesisOrganism],
    children: Sequence[GenesisOrganism],
) -> GenesisOrganism | None:
    if current is not None and current.id == organism_id:
        return current
    for group in (survivors, pending, children):
        for item in group:
            if item.id == organism_id:
                return item
    return None


def _reconstruct_parent(slot: IncipientOffspring, template: GenesisOrganism) -> GenesisOrganism:
    reconstructed = GenesisOrganism.from_bits(
        slot.parent_id,
        slot.genome_bits,
        initial_runtime_atp=0.0,
        position=slot.parent_position,
        ribosome=template.ribosome,
        action_registry=template.action_registry,
        action_runtime_config=template.action_runtime_config,
        memory_config=template.memory_config,
        execution_source_enabled=template.execution_source_enabled,
        adf_macro_registry=template.adf_macro_registry,
        adf_execution_policy=template.adf_execution_policy,
        translation_profile=template.translation_profile,
        translation_policy=template.translation_policy,
    )
    return reconstructed


def _commit_newborn(
    reproduction_result: ReproductionResult,
    *,
    parent: GenesisOrganism,
    configs: PopulationConfigs,
    working_world: World2D,
    live_positions: dict[str, tuple[int, int]],
    survivors: list[GenesisOrganism],
    children: list[GenesisOrganism],
    lineage: tuple[LineageRecord, ...],
    deaths: int,
    current_tick: int,
    placements: list[BirthPlacementRecord],
) -> tuple[bool, ReproductionResult, tuple[LineageRecord, ...], int]:
    if not reproduction_result.succeeded or reproduction_result.child is None:
        return False, reproduction_result, lineage, deaths
    child = reproduction_result.child
    placement = _resolve_offspring_position(
        parent_position=parent.position,
        child_id=child.id,
        policy=configs.reproduction.offspring_placement,
        world=working_world,
        live_positions=live_positions,
    )
    if placement is None:
        blocked = _mark_reproduction_placement_blocked(
            reproduction_result,
            reason="offspring_no_free_space",
            policy=configs.reproduction.offspring_placement,
        )
        return False, blocked, lineage, deaths
    child.position = placement
    if configs.reproduction.offspring_placement is OffspringPlacementPolicy.REPLACE_OCCUPIED:
        occupant_id = next(
            (
                oid
                for oid, pos in live_positions.items()
                if pos == placement and oid not in {parent.id, child.id}
            ),
            None,
        )
        if occupant_id is not None:
            live_positions.pop(occupant_id, None)
            survivors[:] = [item for item in survivors if item.id != occupant_id]
            deaths += 1
            lineage = _mark_death(lineage, occupant_id, current_tick)
    reproduction_result = _finalize_reproduction_placement(
        reproduction_result,
        placement=placement,
        policy=configs.reproduction.offspring_placement,
    )
    child = reproduction_result.child
    if child is None:
        raise RuntimeError("finalized reproduction unexpectedly lost child")
    children.append(child)
    if configs.closed_loop_hp_life.outcross_enabled:
        silence_outcross_locus(child, configs.closed_loop_hp_life)
    live_positions[child.id] = child.position
    placements.append(_birth_placement_record(parent, child))
    if reproduction_result.lineage is not None:
        lineage += (reproduction_result.lineage,)
    return True, reproduction_result, lineage, deaths


def _drain_chamber_pairs(
    *,
    waiting: list[IncipientOffspring],
    configs: PopulationConfigs,
    sexual_cfg: SexualRecombinationConfig,
    stream: RNGManager,
    chamber_rng: RNGManager,
    working_world: World2D,
    live_positions: dict[str, tuple[int, int]],
    survivors: list[GenesisOrganism],
    pending: Sequence[GenesisOrganism],
    children: list[GenesisOrganism],
    lineage: tuple[LineageRecord, ...],
    births: int,
    deaths: int,
    current_tick: int,
    current_organism: GenesisOrganism | None,
    alive_result: AliveGateResult | None,
    placements: list[BirthPlacementRecord],
) -> tuple[list[IncipientOffspring], tuple[LineageRecord, ...], int, int, ReproductionResult | None, list[str]]:
    last_result: ReproductionResult | None = None
    placed_ids: list[str] = []
    template = current_organism or (survivors[0] if survivors else None) or (
        pending[0] if pending else None
    )
    while True:
        life = configs.closed_loop_hp_life
        compatible = None
        if life.outcross_enabled and life.outcross_same_role_only:
            compatible = lambda first, second, _life=life: outcross_mates_compatible(
                first.parent_id, second.parent_id, _life
            )
        pair = select_chamber_pair(
            waiting,
            same_length_only=sexual_cfg.same_length_only,
            compatible=compatible,
        )
        if pair is None:
            break
        needed = 1 if sexual_cfg.two_fold_cost_sex else 2
        if len(live_positions) + needed > configs.reproduction.max_population:
            break
        first = waiting[pair[0]]
        second = waiting[pair[1]]
        for index in sorted(pair, reverse=True):
            del waiting[index]
        if sexual_cfg.diploid_meiosis:
            first = reduce_incipient_to_haploid_gamete(
                first, stream.fork(f"meiosis/{first.slot_id}")
            )
            second = reduce_incipient_to_haploid_gamete(
                second, stream.fork(f"meiosis/{second.slot_id}")
            )
        do_recombine = True
        if sexual_cfg.recombination_prob <= 0.0:
            do_recombine = False
        elif sexual_cfg.recombination_prob < 1.0:
            do_recombine = chamber_rng.random() < sexual_cfg.recombination_prob
        record_a: RecombinationRecord | None = None
        record_b: RecombinationRecord | None = None
        if do_recombine:
            try:
                record_a, record_b = recombine_positional_segment_pair(
                    parent_a_id=first.parent_id,
                    parent_b_id=second.parent_id,
                    parent_a_bits=first.genome_bits,
                    parent_b_bits=second.genome_bits,
                    parent_a_genome_digest=first.genome_digest,
                    parent_b_genome_digest=second.genome_digest,
                    rng=stream.fork(f"recombination/{first.slot_id}/{second.slot_id}"),
                    codon_width=first.codon_width,
                )
            except ValueError:
                record_a, record_b = None, None
        products: list[tuple[IncipientOffspring, RecombinationRecord | None]] = [
            (first, record_a),
            (second, record_b),
        ]
        if sexual_cfg.two_fold_cost_sex:
            deferred_second = products[1]
            products = products[:1]
        else:
            deferred_second = None
        placed_this_pair = 0
        for slot, record in products:
            parent = _lookup_step_organism(
                slot.parent_id,
                current=current_organism,
                survivors=survivors,
                pending=pending,
                children=children,
            )
            if parent is None:
                if template is None:
                    waiting.insert(0, slot)
                    if placed_this_pair == 0:
                        waiting.insert(0, second if slot is first else first)
                    break
                parent = _reconstruct_parent(slot, template)
            gate_alive = alive_result or AliveGateResult(
                passed=True,
                survived_ticks=0,
                executed_actions=0,
                blocked_actions=0,
                blocked_ratio=0.0,
                final_runtime_atp=parent.atp_state.runtime_available,
                lumen_interactions=0,
                reproduction_events=0,
                reasons=("birth_chamber_completion",),
            )
            birth_config = (
                configs.reproduction
                if record is not None
                else replace(configs.reproduction, reproduction_mode=ReproductionMode.ASEXUAL)
            )
            result = reproduce(
                parent,
                birth_config,
                configs.mutation,
                alive_result=gate_alive,
                generation=slot.parent_generation,
                birth_tick=current_tick,
                rng=stream.fork(f"reproduce/{slot.parent_id}/{current_tick}/{slot.slot_id}"),
                structural_mutation_config=configs.structural_mutation,
                world=working_world,
                live_positions=live_positions,
                sexual=sexual_cfg,
                skip_parent_costs=True,
                recombination_record=record,
                offspring_runtime_atp_override=slot.offspring_runtime_atp,
            )
            admitted, result, lineage, deaths = _commit_newborn(
                result,
                parent=parent,
                configs=configs,
                working_world=working_world,
                live_positions=live_positions,
                survivors=survivors,
                children=children,
                lineage=lineage,
                deaths=deaths,
                current_tick=current_tick,
                placements=placements,
            )
            if not admitted or result.child is None:
                waiting.insert(0, slot)
                if placed_this_pair == 0:
                    waiting.insert(0, second if slot.slot_id == first.slot_id else first)
                    if deferred_second is not None:
                        waiting.insert(0, deferred_second[0])
                break
            placed_ids.append(result.child.id)
            last_result = result
            births += 1
            placed_this_pair += 1
        else:
            continue
        break
    return waiting, lineage, births, deaths, last_result, placed_ids


def _expire_chamber_waiters(
    *,
    waiting: list[IncipientOffspring],
    configs: PopulationConfigs,
    sexual_cfg: SexualRecombinationConfig,
    stream: RNGManager,
    working_world: World2D,
    live_positions: dict[str, tuple[int, int]],
    survivors: list[GenesisOrganism],
    pending: Sequence[GenesisOrganism],
    children: list[GenesisOrganism],
    lineage: tuple[LineageRecord, ...],
    births: int,
    deaths: int,
    blocked_reproduction: int,
    current_tick: int,
    placements: list[BirthPlacementRecord],
) -> tuple[list[IncipientOffspring], tuple[LineageRecord, ...], int, int, int]:
    timeout_indexes = timed_out_chamber_slots(
        waiting,
        now_tick=current_tick,
        max_birth_wait_ticks=sexual_cfg.max_birth_wait_ticks,
    )
    if not timeout_indexes:
        return waiting, lineage, births, deaths, blocked_reproduction
    expired = [waiting[index] for index in timeout_indexes]
    keep = [item for index, item in enumerate(waiting) if index not in set(timeout_indexes)]
    waiting = keep
    template = (survivors[0] if survivors else None) or (pending[0] if pending else None)
    asexual_config = replace(configs.reproduction, reproduction_mode=ReproductionMode.ASEXUAL)
    for slot in expired:
        if sexual_cfg.timeout_policy == "fail":
            blocked_reproduction += 1
            continue
        if len(live_positions) >= configs.reproduction.max_population:
            waiting.append(slot)
            continue
        parent = _lookup_step_organism(
            slot.parent_id,
            current=None,
            survivors=survivors,
            pending=pending,
            children=children,
        )
        if parent is None:
            if template is None:
                waiting.append(slot)
                continue
            parent = _reconstruct_parent(slot, template)
        result = reproduce(
            parent,
            asexual_config,
            configs.mutation,
            alive_result=AliveGateResult(
                passed=True,
                survived_ticks=0,
                executed_actions=0,
                blocked_actions=0,
                blocked_ratio=0.0,
                final_runtime_atp=parent.atp_state.runtime_available,
                lumen_interactions=0,
                reproduction_events=0,
                reasons=("birth_chamber_timeout_asexual_fallback",),
            ),
            generation=slot.parent_generation,
            birth_tick=current_tick,
            rng=stream.fork(f"reproduce/{slot.parent_id}/{current_tick}/timeout/{slot.slot_id}"),
            structural_mutation_config=configs.structural_mutation,
            world=working_world,
            live_positions=live_positions,
            skip_parent_costs=True,
            offspring_runtime_atp_override=slot.offspring_runtime_atp,
        )
        admitted, result, lineage, deaths = _commit_newborn(
            result,
            parent=parent,
            configs=configs,
            working_world=working_world,
            live_positions=live_positions,
            survivors=survivors,
            children=children,
            lineage=lineage,
            deaths=deaths,
            current_tick=current_tick,
            placements=placements,
        )
        if admitted:
            births += 1
        else:
            waiting.append(slot)
            blocked_reproduction += 1
    return waiting, lineage, births, deaths, blocked_reproduction


def _handle_chamber_copy_self(
    *,
    organism: GenesisOrganism,
    event: TraceEvent,
    configs: PopulationConfigs,
    sexual_cfg: SexualRecombinationConfig,
    alive_result: AliveGateResult,
    generation: int,
    birth_tick: int,
    stream: RNGManager,
    chamber_rng: RNGManager | None,
    waiting: list[IncipientOffspring],
    working_world: World2D,
    live_positions: dict[str, tuple[int, int]],
    survivors: list[GenesisOrganism],
    pending: Sequence[GenesisOrganism],
    children: list[GenesisOrganism],
    lineage: tuple[LineageRecord, ...],
    births: int,
    deaths: int,
    blocked_reproduction: int,
    placements: list[BirthPlacementRecord],
) -> tuple[
    GenesisOrganism,
    ReproductionResult | None,
    list[IncipientOffspring],
    tuple[LineageRecord, ...],
    int,
    int,
    int,
    TraceEvent,
]:
    if chamber_rng is None:
        raise RuntimeError("birth chamber pairing requires a chamber RNG namespace")
    decision = can_reproduce(organism, alive_result, configs.reproduction)
    if not decision.allowed:
        blocked_reproduction += 1
        reproduction_result = _blocked_reproduction_result(
            parent=organism,
            config=configs.reproduction,
            alive_result=alive_result,
            birth_tick=birth_tick,
            generation=generation,
            reason=decision.reasons[0] if decision.reasons else "reproduction_blocked",
            capacity_available=True,
        )
        return (
            organism,
            reproduction_result,
            waiting,
            lineage,
            births,
            deaths,
            blocked_reproduction,
            _with_reproduction_delta(
                event,
                parent_after=organism,
                reproduction_result=reproduction_result,
                succeeded=False,
                reason=reproduction_result.decision.reasons[0],
                parent_id=organism.id,
                child_id=None,
                event_id=reproduction_result.event_id,
            ),
        )
    if len(live_positions) >= configs.reproduction.max_population:
        blocked_reproduction += 1
        reproduction_result = _blocked_reproduction_result(
            parent=organism,
            config=configs.reproduction,
            alive_result=alive_result,
            birth_tick=birth_tick,
            generation=generation,
            reason="max_population_reached",
            capacity_available=False,
        )
        return (
            organism,
            reproduction_result,
            waiting,
            lineage,
            births,
            deaths,
            blocked_reproduction,
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
    if len(waiting) >= sexual_cfg.chamber_capacity:
        blocked_reproduction += 1
        reproduction_result = _blocked_reproduction_result(
            parent=organism,
            config=configs.reproduction,
            alive_result=alive_result,
            birth_tick=birth_tick,
            generation=generation,
            reason="birth_chamber_full",
            capacity_available=True,
        )
        return (
            organism,
            reproduction_result,
            waiting,
            lineage,
            births,
            deaths,
            blocked_reproduction,
            _with_reproduction_delta(
                event,
                parent_after=organism,
                reproduction_result=reproduction_result,
                succeeded=False,
                reason="birth_chamber_full",
                parent_id=organism.id,
                child_id=None,
                event_id=reproduction_result.event_id,
            ),
        )
    life = configs.closed_loop_hp_life
    fee = 0.0
    if resolve_copy_self_mode(organism.genome.to_compact(), life) == "chamber":
        fee = outcross_runtime_cost(organism.genome.to_compact(), life)
        available = float(organism.atp_state.runtime_available)
        parent_cost = float(configs.reproduction.parent_atp_cost)
        remaining = available - parent_cost
        projected_iy = round(remaining * float(configs.reproduction.offspring_atp_fraction), 10)
        if fee > 0.0 and (projected_iy <= 0.0 or remaining - projected_iy + 1e-12 < fee):
            blocked_reproduction += 1
            reproduction_result = _blocked_reproduction_result(
                parent=organism,
                config=configs.reproduction,
                alive_result=alive_result,
                birth_tick=birth_tick,
                generation=generation,
                reason="outcross_runtime_cost_not_payable",
                capacity_available=True,
            )
            return (
                organism,
                reproduction_result,
                waiting,
                lineage,
                births,
                deaths,
                blocked_reproduction,
                _with_reproduction_delta(
                    event,
                    parent_after=organism,
                    reproduction_result=reproduction_result,
                    succeeded=False,
                    reason="outcross_runtime_cost_not_payable",
                    parent_id=organism.id,
                    child_id=None,
                    event_id=reproduction_result.event_id,
                ),
            )
    ledger_ids, offspring_atp, cost_reason = _apply_parent_reproduction_costs(
        organism, configs.reproduction, birth_tick
    )
    if cost_reason is not None:
        blocked_reproduction += 1
        reproduction_result = _blocked_reproduction_result(
            parent=organism,
            config=configs.reproduction,
            alive_result=alive_result,
            birth_tick=birth_tick,
            generation=generation,
            reason=cost_reason,
            capacity_available=True,
        )
        return (
            organism,
            reproduction_result,
            waiting,
            lineage,
            births,
            deaths,
            blocked_reproduction,
            _with_reproduction_delta(
                event,
                parent_after=organism,
                reproduction_result=reproduction_result,
                succeeded=False,
                reason=cost_reason,
                parent_id=organism.id,
                child_id=None,
                event_id=reproduction_result.event_id,
            ),
        )
    if fee > 0.0 and not charge_outcross_runtime(organism, config=life, tick=birth_tick):
        if configs.reproduction.parent_atp_cost > 0.0:
            organism.atp_state.credit_runtime(
                configs.reproduction.parent_atp_cost,
                tick=birth_tick,
                organism_id=organism.id,
                codon="111",
                action="COPY_SELF",
                reason="outcross_cost_reversal",
            )
        if offspring_atp > 0.0:
            organism.atp_state.credit_runtime(
                offspring_atp,
                tick=birth_tick,
                organism_id=organism.id,
                codon="111",
                action="COPY_SELF",
                reason="outcross_cost_reversal",
            )
        blocked_reproduction += 1
        reproduction_result = _blocked_reproduction_result(
            parent=organism,
            config=configs.reproduction,
            alive_result=alive_result,
            birth_tick=birth_tick,
            generation=generation,
            reason="outcross_runtime_cost_not_payable",
            capacity_available=True,
        )
        return (
            organism,
            reproduction_result,
            waiting,
            lineage,
            births,
            deaths,
            blocked_reproduction,
            _with_reproduction_delta(
                event,
                parent_after=organism,
                reproduction_result=reproduction_result,
                succeeded=False,
                reason="outcross_runtime_cost_not_payable",
                parent_id=organism.id,
                child_id=None,
                event_id=reproduction_result.event_id,
            ),
        )
    slot = IncipientOffspring(
        slot_id=f"chamber-{birth_tick}-{organism.id}-{len(waiting)}",
        parent_id=organism.id,
        genome_bits=organism.genome.to_compact(),
        genome_digest=organism.genome.digest(),
        entered_tick=birth_tick,
        parent_position=organism.position,
        offspring_runtime_atp=offspring_atp,
        parent_generation=generation,
        codon_width=organism.genome.spec.codon_width,
        ledger_entry_ids=tuple(ledger_ids),
    )
    waiting.append(slot)
    waiting, lineage, births, deaths, pair_result, placed_ids = _drain_chamber_pairs(
        waiting=waiting,
        configs=configs,
        sexual_cfg=sexual_cfg,
        stream=stream,
        chamber_rng=chamber_rng,
        working_world=working_world,
        live_positions=live_positions,
        survivors=survivors,
        pending=pending,
        children=children,
        lineage=lineage,
        births=births,
        deaths=deaths,
        current_tick=birth_tick,
        current_organism=organism,
        alive_result=alive_result,
        placements=placements,
    )
    extra: dict[str, JsonValue] = {
        "birth_chamber_queued": True,
        "birth_chamber_slot_id": slot.slot_id,
        "birth_chamber_size": len(waiting),
        "birth_chamber_placed_ids": list(placed_ids),
    }
    if pair_result is not None and pair_result.child is not None:
        return (
            organism,
            pair_result,
            waiting,
            lineage,
            births,
            deaths,
            blocked_reproduction,
            _with_reproduction_delta(
                event,
                parent_after=organism,
                reproduction_result=pair_result,
                succeeded=True,
                reason="reproduction_succeeded",
                parent_id=organism.id,
                child_id=pair_result.child.id,
                event_id=pair_result.event_id,
                extra_delta=extra,
            ),
        )
    queued = ReproductionResult(
        attempted=True,
        succeeded=False,
        parent_before_id=organism.id,
        parent_after=organism,
        child=None,
        mutation=None,
        lineage=None,
        decision=ReproductionDecision(True, ("birth_chamber_queued",)),
        event_id=_reproduction_event_id(organism.id, "chamber_queued", birth_tick, slot.slot_id),
        ledger_entry_ids=tuple(ledger_ids),
    )
    return (
        organism,
        queued,
        waiting,
        lineage,
        births,
        deaths,
        blocked_reproduction,
        _with_reproduction_delta(
            event,
            parent_after=organism,
            reproduction_result=queued,
            succeeded=False,
            reason="birth_chamber_queued",
            parent_id=organism.id,
            child_id=None,
            event_id=queued.event_id,
            extra_delta=extra,
            force_executed=True,
        ),
    )


def _reproduction_mode(value: JsonValue | None) -> ReproductionMode:
    try:
        return coerce_reproduction_mode(value)  # type: ignore[arg-type]
    except (ValueError, TypeError) as exc:
        raise ConfigurationError(str(exc)) from exc


def _sexual_mate_block_reason(
    parent: GenesisOrganism,
    mate: GenesisOrganism | None,
    config: ReproductionConfig,
) -> str | None:
    if mate is None:
        return "no_viable_mate"
    if mate.id == parent.id:
        return "mate_is_self"
    if mate.atp_state.runtime_available < config.min_runtime_atp:
        return "mate_min_runtime_atp_not_met"
    return None


def _live_mate_candidates(
    *,
    parent_id: str,
    stepped: Sequence[GenesisOrganism],
    pending: Sequence[GenesisOrganism],
    children: Sequence[GenesisOrganism],
    live_positions: Mapping[str, tuple[int, int]],
) -> tuple[GenesisOrganism, ...]:
    by_id: dict[str, GenesisOrganism] = {}
    for organism in (*pending, *stepped, *children):
        if organism.id == parent_id or organism.id not in live_positions:
            continue
        by_id[organism.id] = organism
    return tuple(by_id.values())


def _select_viable_mate(
    *,
    parent: GenesisOrganism,
    candidates: Sequence[GenesisOrganism],
    min_runtime_atp: float,
) -> GenesisOrganism | None:
    """Pick the nearest live mate; ties break by organism id (no extra RNG)."""

    viable: list[tuple[int, str, GenesisOrganism]] = []
    for other in candidates:
        if other.id == parent.id:
            continue
        if other.atp_state.runtime_available < min_runtime_atp:
            continue
        distance = abs(other.position[0] - parent.position[0]) + abs(
            other.position[1] - parent.position[1]
        )
        viable.append((distance, other.id, other))
    if not viable:
        return None
    viable.sort(key=lambda item: (item[0], item[1]))
    return viable[0][2]


def _recombination_record_from_optional(
    value: JsonValue | None,
) -> RecombinationRecord | None:
    if not isinstance(value, Mapping):
        return None
    return RecombinationRecord(
        parent_a_id=_str(value, "parent_a_id"),
        parent_b_id=_str(value, "parent_b_id"),
        parent_a_genome_digest=_str(value, "parent_a_genome_digest"),
        parent_b_genome_digest=_str(value, "parent_b_genome_digest"),
        parent_a_bits=_str(value, "parent_a_bits"),
        parent_b_bits=_str(value, "parent_b_bits"),
        child_genome_bits=_str(value, "child_genome_bits"),
        child_genome_digest=_str(value, "child_genome_digest"),
        start_index=_int(value, "start_index", 0),
        end_index=_int(value, "end_index", 0),
        codon_width=_int(value, "codon_width", 3),
        rng_digest=_str(value, "rng_digest"),
        operator=_str(value, "operator", MutationOperator.RECOMBINE_WITH_PARTNER.value),
        mechanism=_str(value, "mechanism", "positional_segment_swap"),
        schema_version=_str(value, "schema_version", "recombination_record_v1"),
    )


def _placement_policy(value: JsonValue | OffspringPlacementPolicy | None) -> OffspringPlacementPolicy:
    if value is None:
        return OffspringPlacementPolicy.SAME_CELL
    if isinstance(value, OffspringPlacementPolicy):
        return value
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
    if policy is OffspringPlacementPolicy.REPLACE_OCCUPIED:
        for position in adjacent:
            if (
                world.in_bounds(position)
                and not world.is_wall(position)
                and position != parent_position
                and position in occupied
            ):
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
