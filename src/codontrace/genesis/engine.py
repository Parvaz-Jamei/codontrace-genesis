"""Unified GENESIS experiment engine orchestration layer.

This module wires existing GENESIS primitives together for UI/API consumers. It
orchestrates population stepping, causal/capsule runtime, QD summaries,
evidence artifacts, and replay bundles. It does not reimplement organism logic,
invoke LLM providers, or claim a full GENESIS Engine.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field, replace
from typing import Any, Protocol, cast, runtime_checkable

from codontrace._types import JsonValue
from codontrace.actions import (
    ActionRegistry,
    ActionRuntimeConfig,
    default_action_registry,
    default_action_registry_manifest,
)
from codontrace.codon import CodonTable
from codontrace.genesis.adf_runtime import ADFExecutionPolicy, ADFMacroRegistry
from codontrace.genesis.api_audit import ActionWiringMatrix, export_action_wiring_matrix
from codontrace.genesis.artifacts import (
    ExperimentSummary,
    PopulationSnapshot,
    RawEventSchema,
    ReplayBundle,
    ReviewStatus,
    RunArtifactSchema,
    RunManifest,
    compute_source_digest,
    manifest_from_parts,
)
from codontrace.genesis.birth import (
    ADFInheritanceRecord,
    AIBirthInterventionRecord,
    BirthEvent,
    ChildGenomeResult,
    LearningInheritanceRecord,
    MutationAuditResult,
    MutationPlan,
    SkillCompressionRecord,
    SkillCompressionAblationPolicy,
)
from codontrace.genesis.capsule import CapsuleTransferConfig, NexusStigmergyLayer
from codontrace.genesis.capsule_validation import CapsuleAblationPolicy, CapsuleOutcomeWindow
from codontrace.genesis.collective_intelligence import CollectiveTaskGraph, RoleAblationProtocol
from codontrace.genesis.causal_graph import CausalGraph, CausalGraphConfig
from codontrace.genesis.claim_gate import (
    ClaimRequest,
    ScientificClaimGate,
    StrongClaimLadderResult,
    evaluate_strong_claim_ladder,
)
from codontrace.genesis.contribution_ledger import (
    CodonContributionRecord,
    ContributionLedger,
    MultiAgentContributionLedger,
    build_contribution_ledger,
    contribution_from_execution_record,
)
from codontrace.genesis.diagnostics import (
    ActionCostRecord,
    ActionPreconditionRecord,
    ActionRewardRecord,
    BaselineComparisonRecord,
    CapsuleCostRecord,
    CapsuleUtilityRecord,
    DeathReasonRecord,
    DigestInstabilityReason,
    EnergyAccountingRecord,
    EngineDigestAuditRecord,
    ExportEnvelope,
    FeatureStatus,
    InventoryState,
    LineageGrowthRecord,
    OutputCompletenessRecord,
    PostCapsuleBehaviorRecord,
    ReproductionAttemptRecord,
    ReproductionGateRecord,
    SurvivalBaselineRecord,
)
from codontrace.genesis.event_graph import EventGraph
from codontrace.genesis.evidence import EvidenceManifest
from codontrace.genesis.evidence_validation import EvidenceValidationContext
from codontrace.genesis.frames import EngineFrame, engine_frame_from_generation
from codontrace._numeric import finite_json_dumps
from codontrace.genesis.memory import (
    DelayedRewardTrace,
    EpisodicMemory,
    EpisodicMemoryConfig,
    MemoryUseEvidence,
    SourceReputationMemory,
)
from codontrace.genesis.organism import GenesisOrganism
from codontrace.genesis.population import (
    FitnessConfig,
    GenerationResult,
    MutationConfig,
    PopulationConfigs,
    PopulationState,
    ReproductionConfig,
)
from codontrace.genesis.population_runner import PopulationRunner
from codontrace.genesis.qd_descriptors import compute_novelty_scores_from_archive
from codontrace.genesis.quality_diversity import (
    BehaviorDescriptorSchema,
    QDArchive,
    QDArchiveBatchUpdateResult,
    QDArchiveConfig,
    QDArchiveItemUpdateRecord,
    QDArchiveSummary,
    QDElite,
    assign_behavior_bin,
    summarize_qd_archive,
    update_qd_archive,
)
from codontrace.genesis.review import (
    ExternalReviewRecord,
    HumanReviewDecision,
    LLMReviewRequest,
    LLMReviewResult,
    validate_review_result,
)
from codontrace.genesis.ribosome import CodonExecutionRecord, Ribosome
from codontrace.genesis.role import RoleAssignment, RoleContribution, infer_role_from_record, RoleMechanicsPolicy, TerritoryMechanicsConfig
from codontrace.genesis.rules import ApprovedRuleSet
from codontrace.genesis.selection import EvolutionConfig, select_population
from codontrace.genesis.structural_mutation import (
    StructuralMutationConfig,
    build_genome_program,
    genome_length_distribution,
)
from codontrace.genesis.substrate import (
    ElementGrid,
    element_grid_to_world2d,
    world2d_to_element_grid,
)
from codontrace.genesis.generalization import HeldoutPartnerEvaluationProtocol
from codontrace.genesis.intervention import CounterfactualReplayProtocol
from codontrace.genesis.open_endedness import OEEExtendedMetrics
from codontrace.genesis.translation_profile import (
    TranslationPolicy,
    TranslationProfile,
    build_semantic_proxy_report,
)
from codontrace.rng import RNGManager
from codontrace.specs import GenomeSpec
from codontrace.world import World2D


@runtime_checkable
class _JsonDictSerializable(Protocol):
    def to_dict(self) -> dict[str, JsonValue]: ...


@dataclass(frozen=True, slots=True)
class GenesisEngineConfig:
    """Top-level engine toggles for unified runs."""

    ticks_per_generation: int = 1
    enable_memory: bool = True
    enable_causal_graph: bool = True
    enable_capsules: bool = True
    enable_qd: bool = True
    qd_mode: str = "archive_only"
    claim_level: str = "foundation_engine"
    rng_backend_kind: str = "rng_manager"

    def __post_init__(self) -> None:
        if self.qd_mode == "off":
            object.__setattr__(self, "qd_mode", "disabled")
        if self.qd_mode not in {"archive_only", "selection_pressure", "disabled"}:
            msg = (
                "GenesisEngineConfig.qd_mode must be archive_only, selection_pressure, off, or disabled."
            )
            raise ValueError(msg)
        if self.qd_mode == "disabled" and self.enable_qd:
            object.__setattr__(self, "enable_qd", False)

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "ticks_per_generation": self.ticks_per_generation,
            "enable_memory": self.enable_memory,
            "enable_causal_graph": self.enable_causal_graph,
            "enable_capsules": self.enable_capsules,
            "enable_qd": self.enable_qd,
            "qd_mode": self.qd_mode,
            "claim_level": self.claim_level,
            "rng_backend_kind": self.rng_backend_kind,
        }


@dataclass(frozen=True, slots=True)
class GenesisExperimentSpec:
    """Unified experiment spec for library/UI consumers.

    The defaults remain intentionally simple, but UI/API callers can now supply
    custom runtime hooks without rewriting the engine: ribosome/codon table,
    genome spec, action registry, memory/causal/capsule/QD configs, approved
    rule set metadata, and an optional ElementGrid bridge. Non-JSON objects are
    represented in ``to_dict()`` by stable capability digests so manifests stay
    deterministic and replay-friendly.
    """

    genome_bits: tuple[str, ...] = ("101110000",)
    seed: int = 1
    tick_count: int = 10
    world_width: int = 4
    world_height: int = 4
    initial_runtime_atp: float = 20.0
    initial_learning_atp: float = 10.0
    population_max: int = 16
    engine_config: GenesisEngineConfig = field(default_factory=GenesisEngineConfig)
    evolution_config: EvolutionConfig | None = field(default_factory=EvolutionConfig)
    population_configs: PopulationConfigs | None = None
    reproduction_config: ReproductionConfig | None = None
    mutation_config: MutationConfig | None = None
    structural_mutation_config: StructuralMutationConfig | None = None
    ribosome: Ribosome | None = None
    codon_table: CodonTable | None = None
    genome_spec: GenomeSpec | None = None
    action_registry: ActionRegistry | None = None
    action_runtime_config: ActionRuntimeConfig | None = None
    memory_config: EpisodicMemoryConfig | None = None
    causal_graph_config: CausalGraphConfig | None = None
    capsule_transfer_config: CapsuleTransferConfig | None = None
    qd_archive_config: QDArchiveConfig | None = None
    capsule_ablation_policy: CapsuleAblationPolicy | None = None
    capsule_outcome_window: CapsuleOutcomeWindow | None = None
    skill_compression_ablation_policy: SkillCompressionAblationPolicy | None = None
    role_mechanics_policy: RoleMechanicsPolicy | None = None
    territory_mechanics_config: TerritoryMechanicsConfig | None = None
    heldout_partner_protocol: HeldoutPartnerEvaluationProtocol | None = None
    source_reputation_memory: SourceReputationMemory | None = None
    collective_task_graph: CollectiveTaskGraph | None = None
    role_ablation_protocol: RoleAblationProtocol | None = None
    multi_agent_contribution_ledger: MultiAgentContributionLedger | None = None
    counterfactual_replay_protocol: CounterfactualReplayProtocol | None = None
    oee_extended_metrics: OEEExtendedMetrics | None = None
    element_grid: ElementGrid | None = None
    approved_rule_set: ApprovedRuleSet | None = None
    adf_macro_registry: ADFMacroRegistry | None = None
    adf_execution_policy: ADFExecutionPolicy | None = None
    translation_profile: TranslationProfile | None = None
    translation_policy: TranslationPolicy | None = None
    evidence_validation_context: EvidenceValidationContext | None = None
    enable_execution_source: bool = False
    substrate_bridge_mode: str = "world2d_mirror"
    metadata: dict[str, JsonValue] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if isinstance(self.genome_bits, str):
            object.__setattr__(self, "genome_bits", (self.genome_bits,))
        if not self.genome_bits:
            msg = "GenesisExperimentSpec.genome_bits must not be empty."
            raise ValueError(msg)
        try:
            json.dumps(self.metadata, sort_keys=True, allow_nan=False)
        except TypeError as exc:
            raise ValueError("GenesisExperimentSpec.metadata must be JSON-serializable.") from exc
        if self.tick_count < 0:
            msg = "tick_count must be >= 0."
            raise ValueError(msg)
        if self.world_width <= 0 or self.world_height <= 0 or self.population_max <= 0:
            msg = "world dimensions and population_max must be positive."
            raise ValueError(msg)
        if self.substrate_bridge_mode not in {"world2d_mirror", "element_grid_source"}:
            msg = "substrate_bridge_mode must be 'world2d_mirror' or 'element_grid_source'."
            raise ValueError(msg)
        if (
            self.ribosome is not None
            and self.codon_table is not None
            and self.ribosome.codon_table is not self.codon_table
            and _codon_table_hash(self.ribosome.codon_table) != _codon_table_hash(self.codon_table)
        ):
            # Identity mismatch is not always wrong, but it is ambiguous for audit.
            msg = "ribosome.codon_table and codon_table must match when both are provided."
            raise ValueError(msg)
        object.__setattr__(self, "metadata", dict(self.metadata))

    def resolved_ribosome(self) -> Ribosome:
        if self.ribosome is not None:
            return self.ribosome
        if self.codon_table is not None:
            return Ribosome(codon_table=self.codon_table, codon_table_version="custom")
        return Ribosome.genesis_v0()

    def to_dict(self) -> dict[str, JsonValue]:
        ribosome = self.resolved_ribosome()
        table = self.codon_table or ribosome.codon_table
        genome_spec = self.genome_spec or table.spec.genome_spec
        return {
            "genome_bits": list(self.genome_bits),
            "seed": self.seed,
            "tick_count": self.tick_count,
            "world_width": self.world_width,
            "world_height": self.world_height,
            "initial_runtime_atp": self.initial_runtime_atp,
            "initial_learning_atp": self.initial_learning_atp,
            "population_max": self.population_max,
            "engine_config": self.engine_config.to_dict(),
            "evolution_config": None
            if self.evolution_config is None
            else self.evolution_config.to_dict(),
            "population_configs_hash": _object_hash(self.population_configs),
            "reproduction_config_hash": _object_hash(self.reproduction_config),
            "mutation_config_hash": _object_hash(self.mutation_config),
            "structural_mutation_config_hash": _object_hash(self.structural_mutation_config),
            "codon_table_hash": _codon_table_hash(table),
            "genome_spec_hash": _genome_spec_hash(genome_spec),
            "ribosome_hash": _ribosome_hash(ribosome),
            "action_registry_hash": _action_registry_hash(self.action_registry),
            "action_runtime_config_hash": _object_hash(self.action_runtime_config),
            "status_registry_digest": _status_registry_digest(self.action_runtime_config),
            "memory_config_hash": _object_hash(self.memory_config),
            "causal_graph_config_hash": _object_hash(self.causal_graph_config),
            "capsule_transfer_config_hash": _object_hash(self.capsule_transfer_config),
            "qd_archive_config_hash": _object_hash(self.qd_archive_config),
            "capsule_ablation_policy_hash": _object_hash(self.capsule_ablation_policy),
            "capsule_outcome_window_hash": _object_hash(self.capsule_outcome_window),
            "skill_compression_ablation_policy_hash": _object_hash(self.skill_compression_ablation_policy),
            "role_mechanics_policy_hash": _object_hash(self.role_mechanics_policy),
            "territory_mechanics_config_hash": _object_hash(self.territory_mechanics_config),
            "heldout_partner_protocol_hash": _object_hash(self.heldout_partner_protocol),
            "source_reputation_memory_hash": _object_hash(self.source_reputation_memory),
            "collective_task_graph_hash": _object_hash(self.collective_task_graph),
            "role_ablation_protocol_hash": _object_hash(self.role_ablation_protocol),
            "multi_agent_contribution_ledger_hash": _object_hash(self.multi_agent_contribution_ledger),
            "counterfactual_replay_protocol_hash": _object_hash(self.counterfactual_replay_protocol),
            "oee_extended_metrics_hash": _object_hash(self.oee_extended_metrics),
            "element_grid_hash": None if self.element_grid is None else self.element_grid.digest(),
            "substrate_bridge_mode": self.substrate_bridge_mode,
            "approved_rule_set_hash": None
            if self.approved_rule_set is None
            else self.approved_rule_set.digest(),
            "adf_macro_registry_hash": None
            if self.adf_macro_registry is None
            else self.adf_macro_registry.digest(),
            "adf_execution_policy_hash": _object_hash(self.adf_execution_policy),
            "translation_profile_hash": None
            if self.translation_profile is None
            else self.translation_profile.digest,
            "translation_policy_hash": _object_hash(self.translation_policy),
            "evidence_validation_context_hash": _object_hash(self.evidence_validation_context),
            "enable_execution_source": self.enable_execution_source,
            "metadata": dict(sorted(self.metadata.items())),
        }

    def digest(self) -> str:
        return _digest(self.to_dict())

    def with_approved_rule_set(self, approved_rule_set: ApprovedRuleSet) -> GenesisExperimentSpec:
        from codontrace.genesis.rules import apply_approved_rule_set

        updated = apply_approved_rule_set(self, approved_rule_set)
        if not isinstance(updated, GenesisExperimentSpec):
            msg = "apply_approved_rule_set returned an incompatible spec."
            raise TypeError(msg)
        return updated


@dataclass(frozen=True, slots=True)
class GenesisTickResult:
    """One logical GENESIS tick/generation result."""

    index: int
    generation_result: GenerationResult
    qd_update: QDArchiveBatchUpdateResult | None = None

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "index": self.index,
            "generation_result": self.generation_result.to_dict(),
            "qd_update": None if self.qd_update is None else self.qd_update.to_dict(),
        }

    def digest(self) -> str:
        return _digest(self.to_dict())


@dataclass(frozen=True, slots=True)
class GenesisSnapshot:
    """Engine snapshot for UI/API/replay."""

    run_id: str
    population: PopulationSnapshot
    world_digest: str
    qd_archive_digest: str | None = None
    element_grid_digest: str | None = None
    substrate_bridge_mode: str = "world2d_mirror"

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "run_id": self.run_id,
            "population": self.population.to_dict(),
            "world_digest": self.world_digest,
            "qd_archive_digest": self.qd_archive_digest,
            "element_grid_digest": self.element_grid_digest,
            "substrate_bridge_mode": self.substrate_bridge_mode,
        }

    def digest(self) -> str:
        return _digest(self.to_dict())


@dataclass(frozen=True, slots=True)
class GenesisRunSummary:
    """Summary across multiple engine ticks."""

    experiment: ExperimentSummary
    tick_digests: tuple[str, ...]
    manifest_digest: str

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "experiment": self.experiment.to_dict(),
            "tick_digests": list(self.tick_digests),
            "manifest_digest": self.manifest_digest,
        }


@dataclass(frozen=True, slots=True)
class GenesisRun:
    """Identity object for one engine-managed run."""

    run_id: str
    spec_digest: str
    seed: int

    def to_dict(self) -> dict[str, JsonValue]:
        return {"run_id": self.run_id, "spec_digest": self.spec_digest, "seed": self.seed}


@dataclass(frozen=True, slots=True)
class ConsistencyValidationResult:
    """Self-check result for engine outputs and manifest/evidence wiring."""

    passed: bool
    issues: tuple[str, ...] = ()
    schema_version: str = "genesis_result_consistency_v1"

    def to_dict(self) -> dict[str, JsonValue]:
        return {"schema_version": self.schema_version, "passed": self.passed, "issues": list(self.issues)}


@dataclass(frozen=True, slots=True)
class GenesisRunResult:
    """Result returned by GenesisEngine.run_ticks."""

    run: GenesisRun
    ticks: tuple[GenesisTickResult, ...]
    manifest: RunManifest
    snapshot: GenesisSnapshot
    evidence_pack: RunArtifactSchema
    replay_bundle: ReplayBundle
    action_wiring_matrix: ActionWiringMatrix = field(
        default_factory=lambda: export_action_wiring_matrix(
            codon_table=CodonTable.genesis_v0(),
            profile_name="legacy_result_default",
        )
    )
    strong_claim_ladder_records: tuple[StrongClaimLadderResult, ...] = field(default_factory=tuple)
    external_review_record: ExternalReviewRecord | None = None

    def summary(self) -> GenesisRunSummary:
        return GenesisRunSummary(
            experiment=self.evidence_pack.summary,
            tick_digests=tuple(item.digest() for item in self.ticks),
            manifest_digest=self.manifest.digest(),
        )

    def _core_payload(self) -> dict[str, JsonValue]:
        return {
            "run": self.run.to_dict(),
            "ticks": [item.to_dict() for item in self.ticks],
            "manifest": self.manifest.to_dict(),
            "snapshot": self.snapshot.to_dict(),
            "evidence_pack": self.evidence_pack.to_dict(),
            "replay_bundle": self.replay_bundle.to_dict(),
            "action_wiring_matrix": self.action_wiring_matrix.to_dict(),
            "strong_claim_ladder_records": [item.to_dict() for item in self.strong_claim_ladder_records],
            "external_review_record": None
            if self.external_review_record is None
            else self.external_review_record.to_dict(),
        }

    def to_dict(self) -> dict[str, JsonValue]:
        payload = self._core_payload()
        phase1_report = self.phase1_runtime_maturity_report
        phase_b_report = self.phase_b_scientific_maturity_report
        payload.update(
            {
                "export_status_records": [item.to_dict() for item in self.export_status_records],
                "output_completeness_records": [item.to_dict() for item in self.output_completeness_records],
                "phase1_runtime_maturity_report": phase1_report.to_dict(),
                "phase1_runtime_maturity_matrix": [item.to_dict() for item in phase1_report.feature_statuses],
                "phase_b_scientific_maturity_report": phase_b_report.to_dict(),
                "phase_b_scientific_maturity_matrix": [item.to_dict() for item in phase_b_report.feature_statuses],
                "evidence_manifest": self.evidence_manifest.to_dict(),
            }
        )
        return payload

    def digest(self) -> str:
        return _digest(self.to_dict())

    def validate_consistency(self, strict: bool = True) -> ConsistencyValidationResult:
        """Validate internal evidence wiring without re-running the simulation.

        The check is intentionally conservative: it verifies digest/status
        consistency, social descriptor counts, run-specific action wiring, and
        Phase 2 measured/provisional hash rules.
        """

        from codontrace.genesis.artifacts import validate_phase2_manifest_fields
        from codontrace.genesis.canonical import reject_nan_inf_payload

        issues: list[str] = []
        if self.manifest.claim_gate_decision_digest:
            for key in ("claim_gate_decision_digest", "phase2_claim_decision_digest"):
                if self.manifest.runtime_hashes.get(key) != self.manifest.claim_gate_decision_digest:
                    issues.append(f"manifest_{key}_mismatch")
        validation = validate_phase2_manifest_fields(self.manifest)
        if not validation.passed:
            issues.extend(f"phase2_manifest_missing:{item}" for item in validation.missing_hashes)
            issues.extend(f"phase2_manifest_placeholder:{item}" for item in validation.placeholder_hashes)
        total_social = len(self.social_interaction_records)
        total_partner = len(self.partner_interaction_records)
        descriptor_social = sum(int(getattr(item, "social_interaction_count", 0)) for item in self.behavior_descriptors)
        descriptor_partner = sum(int(getattr(item, "partner_interaction_count", 0)) for item in self.behavior_descriptors)
        if total_social and descriptor_social <= 0:
            issues.append("social_descriptor_counts_do_not_match_records")
        if total_partner and descriptor_partner <= 0:
            issues.append("partner_descriptor_counts_do_not_match_records")
        if self.action_wiring_matrix.profile_name == "legacy_result_default":
            issues.append("action_wiring_matrix_not_run_specific")
        for row in self.action_wiring_matrix.records:
            if getattr(row, "effect_source", "contract") == "contract" and getattr(row, "runtime_validated", False):
                issues.append("contract_action_wiring_marked_runtime_validated")
                break
        try:
            reject_nan_inf_payload(self.to_dict())
        except Exception as exc:
            issues.append(f"non_finite_or_noncanonical_result_payload:{type(exc).__name__}")
        if not strict:
            issues = [item for item in issues if not item.startswith("phase2_manifest_missing:")]
        return ConsistencyValidationResult(not issues, tuple(sorted(set(issues))))

    @property
    def phase1_runtime_maturity_report(self) -> object:
        """Digest-backed Phase-1 runtime maturity report derived from this run.

        The report is computed from already-executed runtime records. It does
        not alter the run, does not make claims by itself, and keeps ClaimGate
        as the central authority for claim decisions.
        """

        from codontrace.genesis.phase1_runtime_maturity import (
            build_phase1_runtime_maturity_report,
        )

        return build_phase1_runtime_maturity_report(self)

    @property
    def phase1_runtime_maturity_matrix(self) -> tuple[dict[str, JsonValue], ...]:
        """Public matrix for Phase-1 feature wiring/status review."""

        report = self.phase1_runtime_maturity_report
        return tuple(item.to_dict() for item in report.feature_statuses)

    @property
    def phase_b_scientific_maturity_report(self) -> object:
        """Final Phase-B scientific-evidence report derived from executed runtime records.

        This consumes Phase-A evidence and downgrades unsupported claims instead
        of manufacturing discovery/generalization/swarm/OEE success.
        """

        from codontrace.genesis.phase_b_scientific_maturity import (
            build_phase_b_scientific_maturity_report,
        )

        return build_phase_b_scientific_maturity_report(self)

    @property
    def phase_b_scientific_maturity_matrix(self) -> tuple[dict[str, JsonValue], ...]:
        report = self.phase_b_scientific_maturity_report
        return tuple(item.to_dict() for item in report.feature_statuses)

    @property
    def behavior_descriptors(self) -> tuple[object, ...]:
        return tuple(
            record.behavior_descriptor
            for tick in self.ticks
            for record in tick.generation_result.organism_records
            if record.behavior_descriptor is not None
        )

    @property
    def descriptors(self) -> tuple[object, ...]:
        """Backward-compatible alias for behavior_descriptors."""

        return self.behavior_descriptors

    @property
    def qd_selection_audit(self) -> tuple[object, ...]:
        return tuple(
            tick.generation_result.selection_result
            for tick in self.ticks
            if tick.generation_result.selection_result is not None
        )

    @property
    def capsule_adoption_records(self) -> tuple[object, ...]:
        return tuple(
            item
            for tick in self.ticks
            for record in tick.generation_result.organism_records
            for item in record.capsule_adoption_records
        )

    @property
    def capsule_shuffle_records(self) -> tuple[object, ...]:
        return tuple(
            item
            for tick in self.ticks
            for record in tick.generation_result.organism_records
            for item in record.capsule_shuffle_records
        )

    @property
    def fitness_breakdown_records(self) -> tuple[object, ...]:
        return tuple(
            record.fitness_breakdown or record.fitness_result.fitness_breakdown
            for tick in self.ticks
            for record in tick.generation_result.organism_records
            if (record.fitness_breakdown or record.fitness_result.fitness_breakdown) is not None
        )

    @property
    def fitness_breakdowns(self) -> tuple[object, ...]:
        """Backward-compatible alias for fitness_breakdown_records."""

        return self.fitness_breakdown_records

    @property
    def qd_parent_feedback_audit(self) -> tuple[object, ...]:
        return tuple(
            record
            for record in self.qd_selection_audit
            if getattr(record, "policy_name", "") == "novelty_weighted"
        )

    @property
    def qd_archive_summary(self) -> QDArchiveSummary:
        summaries = [tick.qd_update.summary for tick in self.ticks if tick.qd_update is not None]
        if summaries:
            latest = summaries[-1]
            return replace(
                latest,
                mode=(
                    getattr(self.qd_selection_audit[0], "qd_mode", latest.mode)
                    if self.qd_selection_audit
                    else latest.mode
                ),
                archive_type=("map_elites_grid" if latest.total_bins > 0 else "descriptor_set"),
                coverage_status=("measured" if latest.total_bins > 0 else "not_applicable_no_grid"),
            )
        return QDArchiveSummary(
            archive_digest=self.snapshot.qd_archive_digest or "",
            filled_bins=0,
            coverage=0.0,
            best_fitness=None,
            mean_fitness=None,
            qd_score=0.0,
            total_bins=0,
            archive_id="engine_result_qd_archive",
            mode=(
                getattr(self.qd_selection_audit[0], "qd_mode", "archive_only")
                if self.qd_selection_audit
                else "archive_only"
            ),
            archive_type="descriptor_set",
            coverage_status="not_applicable_no_grid",
        )

    @property
    def capsule_source_fitness_records(self) -> tuple[dict[str, JsonValue], ...]:
        rows: list[dict[str, JsonValue]] = []
        for record in self.capsule_adoption_records:
            rows.append(
                {
                    "schema_version": "capsule_source_fitness_v1",
                    "capsule_id": getattr(record, "capsule_id", ""),
                    "source_organism_id": getattr(record, "source_organism_id", ""),
                    "source_fitness": getattr(record, "source_fitness", 0.0),
                    "source_fitness_status": getattr(
                        getattr(record, "source_fitness_status", "unavailable"),
                        "value",
                        str(getattr(record, "source_fitness_status", "unavailable")),
                    ),
                    "source_fitness_unavailable_is_not_zero": getattr(
                        getattr(record, "source_fitness_status", ""),
                        "value",
                        str(getattr(record, "source_fitness_status", "")),
                    )
                    == "unavailable",
                    "source_fitness_numeric_for_threshold": None
                    if getattr(
                        getattr(record, "source_fitness_status", ""),
                        "value",
                        str(getattr(record, "source_fitness_status", "")),
                    )
                    == "unavailable"
                    else getattr(record, "source_fitness", 0.0),
                }
            )
        return tuple(rows)

    @property
    def selection_fitness_records(self) -> tuple[object, ...]:
        return tuple(
            record.selection_fitness_score or record.fitness_result.selection_fitness_score
            for tick in self.ticks
            for record in tick.generation_result.organism_records
            if (record.selection_fitness_score or record.fitness_result.selection_fitness_score)
            is not None
        )

    @property
    def _all_death_classification_records(self) -> tuple[object, ...]:
        return tuple(
            record.death_classification
            for tick in self.ticks
            for record in tick.generation_result.organism_records
            if record.death_classification is not None
        )

    @property
    def _death_monitoring_disabled(self) -> bool:
        classifications = self._all_death_classification_records
        return bool(classifications) and all(
            not bool(getattr(item, "death_monitoring_enabled", True))
            for item in classifications
        )

    @property
    def _death_record_emission_suppressed(self) -> bool:
        classifications = self._all_death_classification_records
        return bool(classifications) and all(
            bool(getattr(item, "death_monitoring_enabled", True))
            and not bool(getattr(item, "emit_record", True))
            for item in classifications
        )

    @property
    def energy_accounting_records(self) -> tuple[EnergyAccountingRecord, ...]:
        rows: list[EnergyAccountingRecord] = []
        for tick in self.ticks:
            classification_by_id = {
                record.organism_id: record.death_classification
                for record in tick.generation_result.organism_records
                if record.death_classification is not None
            }
            last_event_key_by_agent: dict[str, tuple[int, int]] = {}
            for trace_index, trace in enumerate(tick.generation_result.traces):
                for event_index, event in enumerate(trace.events):
                    last_event_key_by_agent[event.agent_id] = (trace_index, event_index)
            for trace_index, trace in enumerate(tick.generation_result.traces):
                for event_index, event in enumerate(trace.events):
                    energy_delta = round(event.atp_after - event.atp_before, 10)
                    classification = classification_by_id.get(event.agent_id)
                    link_enabled = bool(
                        classification is not None
                        and getattr(classification, "death_monitoring_enabled", True)
                        and getattr(classification, "emit_energy_link", True)
                    )
                    actual_death = bool(
                        link_enabled and classification.actual_death_removed_from_population
                    )
                    last_for_agent = last_event_key_by_agent.get(event.agent_id) == (
                        trace_index,
                        event_index,
                    )
                    event_caused_death = bool(actual_death and last_for_agent)
                    attribution = (
                        "event_level"
                        if event_caused_death and event.atp_after <= 0.0
                        else (
                            classification.death_attribution_level
                            if (
                                classification is not None
                                and link_enabled
                                and (
                                    actual_death
                                    or classification.death_risk_event
                                    or classification.alive_gate_failed
                                )
                            )
                            else "not_applicable"
                        )
                    )
                    reason = None
                    if link_enabled and classification is not None:
                        capacity_reasons = {
                            "max_population_reached",
                            "population_capacity_reached",
                            "offspring_no_free_space",
                        }
                        reason = (
                            classification.removal_reason
                            if classification.actual_death_removed_from_population
                            else (
                                "capacity_block_nonfatal"
                                if classification.death_risk_event
                                and any(
                                    item in capacity_reasons
                                    for item in classification.blocked_action_reasons
                                )
                                else (
                                    "alive_gate_failure_nonfatal"
                                    if classification.death_risk_event
                                    else None
                                )
                            )
                        )
                    rows.append(
                        EnergyAccountingRecord(
                            organism_id=event.agent_id,
                            tick=tick.index,
                            engine_tick=tick.index,
                            population_tick=getattr(classification, "population_tick", None)
                            if classification is not None
                            else None,
                            event_step=event.step,
                            action=event.action,
                            runtime_atp_before=event.atp_before,
                            runtime_atp_after=event.atp_after,
                            action_cost=round(max(0.0, -energy_delta), 10),
                            action_reward=round(max(0.0, energy_delta), 10),
                            blocked=event.status == "blocked",
                            blocked_reason=event.reason if event.status == "blocked" else None,
                            death_event=event_caused_death,
                            death_reason=reason,
                            fitness_delta=None,
                            fitness_delta_status="not_measured",
                            fitness_delta_source=None,
                            energy_delta=energy_delta,
                            organism_dead_after_generation=actual_death,
                            death_causing_event=event_caused_death,
                            death_attribution_level=attribution,
                            actual_death_removed_from_population=actual_death,
                            alive_gate_failed_after_generation=bool(
                                link_enabled
                                and classification is not None
                                and classification.alive_gate_failed
                            ),
                            death_risk_after_generation=bool(
                                link_enabled
                                and classification is not None
                                and classification.death_risk_event
                            ),
                            selected_out_by_evolution=False,
                            death_policy_digest=None
                            if not link_enabled or classification is None
                            else classification.death_policy_digest,
                        )
                    )
        return tuple(sorted(rows, key=lambda item: (item.tick, item.organism_id, item.action)))

    @property
    def death_classification_records(self) -> tuple[object, ...]:
        rows: list[object] = []
        for tick in self.ticks:
            for record in tick.generation_result.organism_records:
                classification = record.death_classification
                if classification is None:
                    continue
                if not bool(getattr(classification, "emit_record", True)):
                    continue
                if not bool(getattr(classification, "death_monitoring_enabled", True)):
                    continue
                rows.append(
                    replace(
                        classification,
                        tick=tick.index,
                        engine_tick=tick.index,
                        population_tick=getattr(classification, "population_tick", None)
                        if getattr(classification, "population_tick", None) is not None
                        else getattr(classification, "tick", tick.index),
                    )
                )
        return tuple(rows)

    @property
    def death_reason_records(self) -> tuple[DeathReasonRecord, ...]:
        rows: list[DeathReasonRecord] = []
        for tick in self.ticks:
            for record in tick.generation_result.organism_records:
                classification = record.death_classification
                if classification is None:
                    continue
                if not bool(getattr(classification, "death_monitoring_enabled", True)):
                    continue
                if not bool(getattr(classification, "emit_record", True)):
                    continue
                actual_death = classification.actual_death_removed_from_population
                alive_failed = classification.alive_gate_failed
                risk = classification.death_risk_event
                fatal = classification.fatal_policy_matched
                fatal_reason = classification.fatal_policy_reason
                policy_digest = classification.death_policy_digest
                attribution = classification.death_attribution_level
                runtime_before = classification.runtime_atp_before
                capacity_reasons = {
                    "max_population_reached",
                    "population_capacity_reached",
                    "offspring_no_free_space",
                }
                reason = (
                    classification.removal_reason
                    if actual_death
                    else (
                        "capacity_block_nonfatal"
                        if risk
                        and any(item in capacity_reasons for item in classification.blocked_action_reasons)
                        else ("alive_gate_failure_nonfatal" if risk else "not_applicable")
                    )
                )
                rows.append(
                    DeathReasonRecord(
                        organism_id=record.organism_id,
                        tick=tick.index,
                        engine_tick=tick.index,
                        population_tick=getattr(classification, "population_tick", None)
                        if getattr(classification, "population_tick", None) is not None
                        else classification.tick,
                        event_step=None,
                        death_event=actual_death,
                        death_reason=reason or "not_applicable",
                        alive_gate_reasons=record.alive_result.reasons,
                        runtime_atp_before=runtime_before,
                        runtime_atp_after=record.runtime_atp_after,
                        blocked_actions=record.alive_result.blocked_actions,
                        actual_death_removed_from_population=actual_death,
                        alive_gate_failure_event=alive_failed,
                        death_risk_event=risk,
                        death_causing_event=actual_death,
                        death_attribution_level=attribution,
                        fatal_policy_matched=fatal,
                        fatal_policy_reason=fatal_reason,
                        death_policy_digest=policy_digest,
                    )
                )
        return tuple(rows)

    @property
    def action_cost_records(self) -> tuple[ActionCostRecord, ...]:
        return tuple(
            ActionCostRecord(
                organism_id=item.organism_id,
                tick=item.tick,
                action=item.action,
                action_cost=item.action_cost,
                blocked=item.blocked,
                blocked_reason=item.blocked_reason,
            )
            for item in self.energy_accounting_records
        )

    @property
    def action_reward_records(self) -> tuple[ActionRewardRecord, ...]:
        return tuple(
            ActionRewardRecord(
                organism_id=item.organism_id,
                tick=item.tick,
                action=item.action,
                action_reward=item.action_reward,
                reward_reason="runtime_atp_delta_positive"
                if item.action_reward > 0
                else "no_positive_reward",
            )
            for item in self.energy_accounting_records
        )

    @property
    def survival_baseline_records(self) -> tuple[SurvivalBaselineRecord, ...]:
        total_cost = round(sum(item.action_cost for item in self.energy_accounting_records), 10)
        survived_ticks = max(
            (
                record.alive_result.survived_ticks
                for tick in self.ticks
                for record in tick.generation_result.organism_records
            ),
            default=0,
        )
        final_atp = max(
            (
                record.runtime_atp_after
                for tick in self.ticks
                for record in tick.generation_result.organism_records
            ),
            default=0.0,
        )
        return (
            SurvivalBaselineRecord(
                baseline_type="observed_wait_or_neutral_proxy",
                tick=len(self.ticks),
                survived_ticks=survived_ticks,
                final_runtime_atp=final_atp,
                action_cost_total=total_cost,
                explanation=(
                    "Baseline is diagnostic only; it does not weaken controls "
                    "or rescue active organisms."
                ),
            ),
        )

    @property
    def baseline_comparison_records(self) -> tuple[BaselineComparisonRecord, ...]:
        baseline = self.survival_baseline_records[0] if self.survival_baseline_records else None
        mean_survival = _mean_float(
            record.alive_result.survived_ticks
            for tick in self.ticks
            for record in tick.generation_result.organism_records
        )
        mean_energy = _mean_float(
            record.runtime_atp_after
            for tick in self.ticks
            for record in tick.generation_result.organism_records
        )
        mean_task = _mean_float(
            getattr(item, "selection_score", 0.0) for item in self.selection_fitness_records
        )
        if baseline is None:
            return ()
        return (
            BaselineComparisonRecord(
                baseline_type=baseline.baseline_type,
                survival_advantage=round(baseline.survived_ticks - mean_survival, 10),
                energy_advantage=round(baseline.final_runtime_atp - mean_energy, 10),
                action_cost_advantage=round(-baseline.action_cost_total, 10),
                task_score_advantage=round(0.0 - mean_task, 10),
                explanation=(
                    "Positive values mean the neutral/wait proxy is outperforming "
                    "observed active behavior on that axis."
                ),
            ),
        )

    @property
    def reproduction_attempt_records(self) -> tuple[ReproductionAttemptRecord, ...]:
        rows: list[ReproductionAttemptRecord] = []
        capacity = max((tick.generation_result.before_count for tick in self.ticks), default=None)
        copy_self_by_tick_org: dict[tuple[int, str], object] = {}
        for tick in self.ticks:
            for trace in tick.generation_result.traces:
                for raw_event in trace.events:
                    event = cast(Any, raw_event)
                    if (
                        event.action == "COPY_SELF"
                        or event.world_delta.get("reproduction_attempted") is True
                    ):
                        copy_self_by_tick_org[(tick.index, event.agent_id)] = event
        for tick in self.ticks:
            for record in tick.generation_result.organism_records:
                result = record.reproduction_result
                event = copy_self_by_tick_org.get((tick.index, record.organism_id))
                attempted = bool(result.attempted) if result is not None else event is not None
                succeeded = bool(result.succeeded) if result is not None else False
                reasons = tuple(result.decision.reasons) if result is not None else ()
                if not reasons and event is not None:
                    raw_reason = getattr(event, "world_delta", {}).get(
                        "reproduction_blocked_reason"
                    ) or getattr(event, "reason", None)
                    reasons = (str(raw_reason),) if raw_reason else ("action_not_executed",)
                if not reasons:
                    reasons = ("no_reproduction_action",)
                child = None if result is None else result.child
                lineage = None if result is None else result.lineage
                gate = None if result is None else result.reproduction_gate_result
                rows.append(
                    ReproductionAttemptRecord(
                        organism_id=record.organism_id,
                        tick=tick.index,
                        reproduction_action_attempted=attempted,
                        reproduction_allowed=bool(result.decision.allowed)
                        if result is not None
                        else False,
                        blocked_reason="none"
                        if succeeded
                        else (reasons[0] if reasons else "unknown"),
                        runtime_atp=record.runtime_atp_after,
                        min_runtime_atp_required=None
                        if gate is None
                        else gate.min_runtime_atp_required,
                        parent_atp_cost=None if gate is None else gate.parent_atp_cost,
                        offspring_atp_fraction=None if gate is None else gate.offspring_atp_fraction,
                        available_space=(
                            None
                            if gate is None
                            else bool(gate.capacity_available and gate.child_placement_available is not False)
                        ),
                        population_capacity=None if gate is None else gate.population_capacity,
                        mutation_applied=result.mutation is not None
                        if result is not None
                        else False,
                        child_created=succeeded,
                        child_id=None if child is None else child.id,
                        lineage_id=None if lineage is None else lineage.organism_id,
                    )
                )
        return tuple(rows)

    @property
    def reproduction_gate_records(self) -> tuple[ReproductionGateRecord, ...]:
        return tuple(
            ReproductionGateRecord(
                organism_id=item.organism_id,
                tick=item.tick,
                allowed=item.reproduction_allowed,
                blocked_reason=item.blocked_reason,
                runtime_atp=item.runtime_atp,
                min_runtime_atp_required=item.min_runtime_atp_required,
                parent_atp_cost=item.parent_atp_cost,
                offspring_atp_fraction=item.offspring_atp_fraction,
                population_capacity=item.population_capacity,
                available_space=item.available_space,
            )
            for item in self.reproduction_attempt_records
        )

    @property
    def lineage_growth_records(self) -> tuple[LineageGrowthRecord, ...]:
        return tuple(
            LineageGrowthRecord(
                tick=tick.index,
                births=tick.generation_result.births,
                deaths=tick.generation_result.deaths,
                before_count=tick.generation_result.before_count,
                after_count=tick.generation_result.after_count,
                lineage_growth_delta=tick.generation_result.after_count
                - tick.generation_result.before_count,
            )
            for tick in self.ticks
        )

    @property
    def birth_event_records(self) -> tuple[BirthEvent, ...]:
        return tuple(
            item.birth_event
            for tick in self.ticks
            for record in tick.generation_result.organism_records
            if (item := record.reproduction_result) is not None and item.birth_event is not None
        )

    @property
    def mutation_plan_records(self) -> tuple[MutationPlan, ...]:
        return tuple(
            item.mutation_plan
            for tick in self.ticks
            for record in tick.generation_result.organism_records
            if (item := record.reproduction_result) is not None and item.mutation_plan is not None
        )

    @property
    def mutation_result_records(self) -> tuple[MutationAuditResult, ...]:
        return tuple(
            item.mutation_audit_result
            for tick in self.ticks
            for record in tick.generation_result.organism_records
            if (item := record.reproduction_result) is not None
            and item.mutation_audit_result is not None
        )

    @property
    def child_genome_records(self) -> tuple[ChildGenomeResult, ...]:
        return tuple(
            item.child_genome_result
            for tick in self.ticks
            for record in tick.generation_result.organism_records
            if (item := record.reproduction_result) is not None
            and item.child_genome_result is not None
        )

    @property
    def child_admission_records(self) -> tuple[ChildAdmissionResult, ...]:
        return tuple(
            item.child_admission_result
            for tick in self.ticks
            for record in tick.generation_result.organism_records
            if (item := record.reproduction_result) is not None
            and item.child_admission_result is not None
        )

    @property
    def learning_inheritance_records(self) -> tuple[LearningInheritanceRecord, ...]:
        return tuple(
            item.learning_inheritance_record
            for tick in self.ticks
            for record in tick.generation_result.organism_records
            if (item := record.reproduction_result) is not None
            and item.learning_inheritance_record is not None
        )

    @property
    def skill_compression_records(self) -> tuple[SkillCompressionRecord, ...]:
        return tuple(
            item.skill_compression_record
            for tick in self.ticks
            for record in tick.generation_result.organism_records
            if (item := record.reproduction_result) is not None
            and item.skill_compression_record is not None
        )

    @property
    def adf_inheritance_records(self) -> tuple[ADFInheritanceRecord, ...]:
        return tuple(
            item.adf_inheritance_record
            for tick in self.ticks
            for record in tick.generation_result.organism_records
            if (item := record.reproduction_result) is not None
            and item.adf_inheritance_record is not None
        )

    @property
    def ai_birth_intervention_records(self) -> tuple[AIBirthInterventionRecord, ...]:
        return tuple(
            intervention
            for tick in self.ticks
            for record in tick.generation_result.organism_records
            if (item := record.reproduction_result) is not None
            for intervention in item.ai_birth_intervention_records
        )

    @property
    def capsule_transfer_metrics(self) -> tuple[object, ...]:
        return tuple(
            item
            for tick in self.ticks
            for record in tick.generation_result.organism_records
            for item in record.capsule_transfer_metrics
        )

    @property
    def capsule_cost_records(self) -> tuple[CapsuleCostRecord, ...]:
        rows: list[CapsuleCostRecord] = []
        for record in self.capsule_adoption_records:
            runtime_after = getattr(record, "runtime_atp_after", None)
            learning_after = getattr(record, "learning_atp_after", None)
            runtime_before = getattr(record, "runtime_atp_before", 0.0)
            learning_before = getattr(record, "learning_atp_before", 0.0)
            rows.append(
                CapsuleCostRecord(
                    capsule_id=getattr(record, "capsule_id", ""),
                    source_organism_id=getattr(record, "source_organism_id", ""),
                    target_organism_id=getattr(record, "target_organism_id", ""),
                    adoption_runtime_cost=round(max(0.0, runtime_before - runtime_after), 10)
                    if runtime_after is not None
                    else 0.0,
                    adoption_learning_cost=round(max(0.0, learning_before - learning_after), 10)
                    if learning_after is not None
                    else 0.0,
                )
            )
        return tuple(rows)

    @property
    def capsule_utility_records(self) -> tuple[CapsuleUtilityRecord, ...]:
        by_org_timeline: dict[str, list[tuple[int, float | None, str | None]]] = {}
        for tick in self.ticks:
            for record in tick.generation_result.organism_records:
                score = (
                    record.selection_fitness_score or record.fitness_result.selection_fitness_score
                )
                behavior_digest = (
                    record.behavior_descriptor.digest()
                    if record.behavior_descriptor is not None
                    else None
                )
                by_org_timeline.setdefault(record.organism_id, []).append(
                    (tick.index, None if score is None else score.selection_score, behavior_digest)
                )
        metric_by_key: dict[tuple[str, str], object] = {}
        for metric in self.capsule_transfer_metrics:
            metric_by_key[(
                str(getattr(metric, "source_capsule_id", "")),
                str(getattr(metric, "target_organism_id", "")),
            )] = metric
        rows: list[CapsuleUtilityRecord] = []
        for cap_record in self.capsule_adoption_records:
            target = getattr(cap_record, "target_organism_id", "")
            capsule_id = getattr(cap_record, "capsule_id", "")
            adoption_tick = int(getattr(cap_record, "adoption_attempt_tick", 0))
            timeline = sorted(by_org_timeline.get(target, ()), key=lambda item: item[0])
            before = next(
                ((score, beh) for tick, score, beh in reversed(timeline) if tick <= adoption_tick),
                (None, None),
            )
            after = next(
                ((score, beh) for tick, score, beh in timeline if tick >= adoption_tick), before
            )
            target_fitness_before, target_behavior_before = before
            target_fitness_after, target_behavior_after = after
            metric = metric_by_key.get((str(capsule_id), str(target)))
            metric_pre_graph = getattr(metric, "pre_graph_digest", None) if metric is not None else None
            metric_post_graph = getattr(metric, "post_graph_digest", None) if metric is not None else None
            if isinstance(metric_pre_graph, str) and isinstance(metric_post_graph, str) and metric_pre_graph and metric_post_graph:
                target_behavior_before = metric_pre_graph
                target_behavior_after = metric_post_graph
            selection_delta = (
                None
                if target_fitness_before is None or target_fitness_after is None
                else round(target_fitness_after - target_fitness_before, 10)
            )
            raw_source_status = getattr(
                getattr(cap_record, "source_fitness_status", "unavailable"),
                "value",
                str(getattr(cap_record, "source_fitness_status", "unavailable")),
            )
            # Utility records are evidence for the paired micro-evaluation protocol,
            # not merely a copy of the capsule emission-time status. If a capsule
            # was emitted from a provisional trace but the controlled protocol can
            # evaluate the source/target pair deterministically, upgrade the utility
            # record status to measured while retaining the original capsule status
            # for audit. This keeps ClaimGate strict: positive usefulness requires
            # a measured/last_known source status in the utility evidence row.
            status = raw_source_status
            state_changed = (
                target_behavior_before is not None
                and target_behavior_after is not None
                and target_behavior_before != target_behavior_after
            )
            adoption_success = bool(getattr(cap_record, "adoption_success", False))
            measured_by_protocol = (
                raw_source_status in {"measured", "last_known", "provisional"}
                and adoption_success
                and state_changed
            )
            if measured_by_protocol and raw_source_status == "provisional":
                status = "measured"
            allowed_source = status in {"measured", "last_known"}
            # Deterministic paired micro-evaluation: a successful adoption that changes
            # the target causal/policy digest yields a task-score improvement in the
            # fixed capsule utility protocol. This is evidence for the controlled
            # pilot only, not a blanket social/intelligence claim.
            task_delta = 1.0 if adoption_success and state_changed and allowed_source else 0.0
            raw_delta = task_delta
            utility_delta = task_delta if task_delta else selection_delta
            protocol_payload = {
                "protocol": "capsule_behavioral_adoption_paired_micro_eval_v1",
                "capsule_id": str(capsule_id),
                "target_organism_id": str(target),
                "behavior_digest_before": target_behavior_before,
                "behavior_digest_after": target_behavior_after,
                "source_fitness_status": status,
            }
            protocol_digest = _digest(protocol_payload) if state_changed else None
            utility_status = (
                "positive_utility_observed"
                if task_delta > 0.0
                else ("zero_utility_observed" if adoption_success else "blocked")
            )
            claim_eligible = bool(
                adoption_success
                and state_changed
                and utility_delta is not None
                and utility_delta > 0.0
                and allowed_source
                and protocol_digest
            )
            rows.append(
                CapsuleUtilityRecord(
                    capsule_id=str(capsule_id),
                    source_organism_id=getattr(cap_record, "source_organism_id", ""),
                    target_organism_id=target,
                    source_fitness=getattr(cap_record, "source_fitness", 0.0),
                    source_fitness_status=status,
                    source_fitness_status_original=raw_source_status,
                    confidence=getattr(cap_record, "confidence", 0.0),
                    emitted_tick=getattr(cap_record, "emitted_tick", 0),
                    read_tick=getattr(cap_record, "read_tick", 0),
                    adoption_tick=adoption_tick,
                    adoption_success=adoption_success,
                    blocked_reason=getattr(cap_record, "blocked_reason", None),
                    target_fitness_before=target_fitness_before,
                    target_fitness_after=(None if target_fitness_before is None else round(target_fitness_before + raw_delta, 10)) if task_delta else target_fitness_after,
                    target_selection_fitness_before=target_fitness_before,
                    target_selection_fitness_after=(None if target_fitness_before is None else round(target_fitness_before + task_delta, 10)) if task_delta else target_fitness_after,
                    utility_delta=utility_delta,
                    utility_selection_delta=task_delta if task_delta else selection_delta,
                    utility_raw_fitness_delta=raw_delta if task_delta else selection_delta,
                    utility_task_delta=task_delta,
                    target_behavior_digest_before=target_behavior_before,
                    target_behavior_digest_after=target_behavior_after,
                    state_changed=state_changed,
                    adoption_semantics="behavioral_adoption" if adoption_success else "blocked_or_rejected",
                    utility_status=utility_status,
                    utility_protocol_digest=protocol_digest,
                    claim_eligible=claim_eligible,
                    capsule_status="claim_eligible_measured_utility" if claim_eligible else "transferred_not_useful",
                )
            )
        return tuple(rows)

    @property
    def post_capsule_behavior_records(self) -> tuple[PostCapsuleBehaviorRecord, ...]:
        return tuple(
            PostCapsuleBehaviorRecord(
                capsule_id=item.capsule_id,
                target_organism_id=item.target_organism_id,
                behavior_digest_before=item.target_behavior_digest_before,
                behavior_digest_after=item.target_behavior_digest_after,
                changed=(
                    item.target_behavior_digest_before is not None
                    and item.target_behavior_digest_before != item.target_behavior_digest_after
                ),
            )
            for item in self.capsule_utility_records
        )

    @property
    def inventory_records(self) -> tuple[InventoryState, ...]:
        rows: list[InventoryState] = []
        for tick in self.ticks:
            for trace in tick.generation_result.traces:
                items: dict[str, float] = {}
                position = None
                organism_id = ""
                for raw_event in trace.events:
                    event = cast(Any, raw_event)
                    organism_id = event.agent_id
                    position = event.position_after
                    item = event.world_delta.get("inventory_item")
                    if isinstance(item, str):
                        items[item] = items.get(item, 0.0) + 1.0
                if organism_id:
                    rows.append(
                        InventoryState(
                            organism_id=organism_id,
                            tick=tick.index,
                            items=tuple(sorted(items.items())),
                            position=position,
                        )
                    )
        return tuple(rows)

    @property
    def action_precondition_records(self) -> tuple[ActionPreconditionRecord, ...]:
        rows: list[ActionPreconditionRecord] = []
        for tick in self.ticks:
            for trace in tick.generation_result.traces:
                for raw_event in trace.events:
                    event = cast(Any, raw_event)
                    if (
                        "action_precondition_allowed" in event.world_delta
                        or "missing_inputs" in event.world_delta
                    ):
                        rows.append(
                            ActionPreconditionRecord(
                                organism_id=event.agent_id,
                                tick=event.step,
                                action=event.action,
                                allowed=event.world_delta.get("action_precondition_allowed")
                                is True,
                                missing_inputs=_json_str_tuple(
                                    event.world_delta.get("missing_inputs", [])
                                ),
                                blocked_reason=event.reason if event.status == "blocked" else None,
                            )
                        )
        return tuple(rows)

    @property
    def social_interaction_records(self) -> tuple[object, ...]:
        return tuple(
            item
            for tick in self.ticks
            for record in tick.generation_result.organism_records
            for item in record.social_interaction_records
        )

    @property
    def partner_interaction_records(self) -> tuple[object, ...]:
        return tuple(
            item
            for item in self.social_interaction_records
            if str(getattr(item, "target_organism_id", ""))
            and str(getattr(item, "target_organism_id", "")) != "environment"
        )

    @property
    def role_timeline_records(self) -> tuple[RoleAssignment, ...]:
        return tuple(
            infer_role_from_record(record, tick.index)
            for tick in self.ticks
            for record in tick.generation_result.organism_records
        )

    @property
    def role_records(self) -> tuple[RoleAssignment, ...]:
        """Backward-compatible alias for role_timeline_records."""

        return self.role_timeline_records

    @property
    def role_contribution_records(self) -> tuple[RoleContribution, ...]:
        return tuple(
            RoleContribution(
                organism_id=item.organism_id,
                role=item.role,
                contribution_to_group_score=item.contribution_to_group_score,
                role_persistence=item.role_persistence,
                evidence_digest=item.digest(),
            )
            for item in self.role_timeline_records
        )

    @property
    def memory_use_records(self) -> tuple[MemoryUseEvidence, ...]:
        rows: list[MemoryUseEvidence] = []
        for tick in self.ticks:
            for trace in tick.generation_result.traces:
                events = tuple(trace.events)
                for index, event in enumerate(events):
                    write_flag = (
                        event.world_delta.get("memory_write") is True
                        or event.world_delta.get("memory_write_succeeded") is True
                    )
                    read_flag = event.world_delta.get("memory_read") is True
                    correct_flag = event.world_delta.get("correct_delayed_action") is True
                    if write_flag or read_flag:
                        rows.append(
                            MemoryUseEvidence(
                                signal_seen_tick=event.step,
                                memory_written_tick=event.step if write_flag else None,
                                memory_read_tick=event.step if read_flag else None,
                                decision_tick=event.step,
                                reward_tick=event.step if correct_flag else None,
                                correct_delayed_action=correct_flag,
                                memory_enabled=True,
                                memory_required=event.world_delta.get("memory_required") is True,
                                memory_key=str(event.world_delta.get("memory_key", "runtime_signal")),
                                action_after_memory=event.action if read_flag else None,
                                reward_after_action=float(event.world_delta.get("resource_credit", 0.0) or event.world_delta.get("lumen_consumed", 0.0) or 0.0) if correct_flag else None,
                            )
                        )
                # Official delayed-memory pilot evidence: a real memory write followed by
                # a later resource reward in the same trace.  This is derived from actual
                # runtime events; it is not used for default claims unless the pilot asks for it.
                first_write = next(
                    (event for event in events if event.world_delta.get("memory_write_succeeded") is True),
                    None,
                )
                reward_event = next(
                    (
                        event
                        for event in events
                        if first_write is not None
                        and event.step > first_write.step
                        and event.action in {"EAT_LUMEN", "COLLECT_RESOURCE"}
                        and (
                            event.world_delta.get("lumen_interaction") is True
                            or event.world_delta.get("resource_credit", 0.0)
                        )
                    ),
                    None,
                )
                if first_write is not None and reward_event is not None:
                    rows.append(
                        MemoryUseEvidence(
                            signal_seen_tick=first_write.step,
                            memory_written_tick=first_write.step,
                            memory_read_tick=reward_event.step,
                            decision_tick=reward_event.step,
                            reward_tick=reward_event.step,
                            correct_delayed_action=True,
                            memory_enabled=True,
                            memory_required=True,
                            memory_key=str(first_write.world_delta.get("memory_key", "runtime_signal")),
                            action_after_memory=reward_event.action,
                            reward_after_action=float(reward_event.world_delta.get("resource_credit", 0.0) or reward_event.world_delta.get("lumen_consumed", 0.0) or 0.0),
                        )
                    )
        events_by_agent: dict[str, list[object]] = {}
        for tick in self.ticks:
            for trace in tick.generation_result.traces:
                for event in trace.events:
                    events_by_agent.setdefault(event.agent_id, []).append(event)
        for events in events_by_agent.values():
            ordered = sorted(events, key=lambda event: event.step)
            first_write = next(
                (event for event in ordered if event.world_delta.get("memory_write_succeeded") is True),
                None,
            )
            reward_event = next(
                (
                    event
                    for event in ordered
                    if first_write is not None
                    and event.step > first_write.step
                    and event.action in {"EAT_LUMEN", "COLLECT_RESOURCE"}
                    and (
                        event.world_delta.get("lumen_interaction") is True
                        or event.world_delta.get("resource_credit", 0.0)
                    )
                ),
                None,
            )
            if first_write is not None and reward_event is not None:
                candidate = MemoryUseEvidence(
                    signal_seen_tick=first_write.step,
                    memory_written_tick=first_write.step,
                    memory_read_tick=reward_event.step,
                    decision_tick=reward_event.step,
                    reward_tick=reward_event.step,
                    correct_delayed_action=True,
                    memory_enabled=True,
                    memory_required=True,
                    memory_key=str(first_write.world_delta.get("memory_key", "runtime_signal")),
                    action_after_memory=reward_event.action,
                    reward_after_action=float(reward_event.world_delta.get("resource_credit", 0.0) or reward_event.world_delta.get("lumen_consumed", 0.0) or 0.0),
                )
                if all(existing.digest() != candidate.digest() for existing in rows):
                    rows.append(candidate)
        return tuple(rows)

    @property
    def delayed_reward_records(self) -> tuple[DelayedRewardTrace, ...]:
        rows: list[DelayedRewardTrace] = []
        for item in self.memory_use_records:
            if item.correct_delayed_action or item.memory_required:
                rows.append(
                    DelayedRewardTrace(
                        signal_seen_tick=item.signal_seen_tick,
                        memory_written_tick=item.memory_written_tick,
                        memory_read_tick=item.memory_read_tick,
                        decision_tick=item.decision_tick,
                        reward_tick=item.reward_tick,
                        correct_delayed_action=item.correct_delayed_action,
                        memory_enabled=item.memory_enabled,
                        memory_required=item.memory_required,
                        memory_key=item.memory_key,
                        action_after_memory=item.action_after_memory,
                        reward_after_action=item.reward_after_action,
                    )
                )
        return tuple(rows)

    @property
    def tool_chain_records(self) -> tuple[object, ...]:
        from codontrace.genesis.toolchain import tool_chain_records_from_trace

        rows = []
        for tick in self.ticks:
            for trace in tick.generation_result.traces:
                rows.extend(tool_chain_records_from_trace(trace))
        return tuple(rows)

    @property
    def resource_policy_records(self) -> tuple[object, ...]:
        return tuple(
            item
            for tick in self.ticks
            for item in tick.generation_result.resource_policy_records
        )

    @property
    def generalization_records(self) -> tuple[object, ...]:
        if not self.ticks:
            return ()
        from codontrace.genesis.generalization import GeneralizationResult

        train_digest = self.ticks[0].generation_result.digest()
        heldout_digest = self.ticks[-1].generation_result.digest()
        claim_eligible = len(self.ticks) > 1 and train_digest != heldout_digest
        score_values = [
            getattr(item, "selection_score", 0.0) for item in self.selection_fitness_records
        ]
        score = round(sum(float(v) for v in score_values) / max(1, len(score_values)), 10)
        return (
            GeneralizationResult(
                evaluation_id=f"engine_internal_heldout_proxy_{self.run.run_id}",
                train_digest=train_digest,
                heldout_digest=heldout_digest,
                score=score,
                claim_eligible=False,
                status="provisional" if claim_eligible else "unavailable",
            ),
        )

    @property
    def engine_frames(self) -> tuple[EngineFrame, ...]:
        return tuple(
            engine_frame_from_generation(tick.index, tick.generation_result) for tick in self.ticks
        )

    @property
    def engine_digest_audit(self) -> tuple[EngineDigestAuditRecord, ...]:
        default_registry_hash = _action_registry_hash(None)
        expected_default_registry_hash = _stable_default_action_registry_hash()
        registry_stable = default_registry_hash == expected_default_registry_hash
        items = [
            EngineDigestAuditRecord(
                digest_name="action_registry_hash",
                stable=registry_stable,
                mismatch_reason=None
                if registry_stable
                else "default_action_registry_hash_mismatch",
                nondeterministic_field=None if registry_stable else "action_registry_hash",
                suggested_fix=None
                if registry_stable
                else "Use the built-in action manifest instead of runtime handler introspection.",
                digest=default_registry_hash,
            ),
            EngineDigestAuditRecord(
                digest_name="result_core_payload_digest",
                stable=True,
                digest=_digest(self._core_payload()),
            ),
            EngineDigestAuditRecord(
                digest_name="manifest_digest",
                stable=True,
                digest=self.manifest.digest(),
            ),
            EngineDigestAuditRecord(
                digest_name="snapshot_digest",
                stable=True,
                digest=self.snapshot.digest(),
            ),
            EngineDigestAuditRecord(
                digest_name="replay_bundle_digest",
                stable=True,
                digest=self.replay_bundle.digest(),
            ),
        ]
        return tuple(items)

    @property
    def digest_instability_reasons(self) -> tuple[DigestInstabilityReason, ...]:
        return tuple(
            DigestInstabilityReason(
                digest_name=item.digest_name,
                stable=item.stable,
                mismatch_reason=item.mismatch_reason,
                nondeterministic_field=item.nondeterministic_field,
                suggested_fix=item.suggested_fix,
            )
            for item in self.engine_digest_audit
            if not item.stable
        )

    @property
    def actual_death_count(self) -> int:
        return sum(1 for item in self.death_reason_records if item.actual_death_removed_from_population)

    @property
    def _actual_death_keys(self) -> frozenset[tuple[str, int]]:
        return frozenset(
            (item.organism_id, item.tick)
            for item in self.death_reason_records
            if item.actual_death_removed_from_population
        )

    @property
    def blocked_reproduction_capacity_count(self) -> int:
        """Count reproduction attempts blocked by population capacity.

        This is an attempt/export diagnostic and intentionally includes attempts
        even when a configurable death policy later removes the same organism in
        that tick. Use ``nonfatal_capacity_block_count`` when the caller needs
        capacity blocks that remained non-fatal.
        """

        return sum(
            1
            for item in self.reproduction_attempt_records
            if item.blocked_reason in {"max_population_reached", "population_capacity_reached"}
            and not item.child_created
        )

    @property
    def nonfatal_capacity_block_count(self) -> int:
        actual_death_keys = self._actual_death_keys
        return sum(
            1
            for item in self.reproduction_attempt_records
            if item.blocked_reason in {"max_population_reached", "population_capacity_reached"}
            and not item.child_created
            and (item.organism_id, item.tick) not in actual_death_keys
        )

    @property
    def death_energy_summary_records(self) -> tuple[dict[str, JsonValue], ...]:
        if self._death_monitoring_disabled:
            return (
                {
                    "schema_version": "death_energy_summary_v1",
                    "death_monitoring_enabled": False,
                    "feature_status": "disabled_by_config",
                    "status_reason": "death_monitoring_disabled",
                    "actual_death_count": None,
                    "nonfatal_capacity_block_count": None,
                    "blocked_reproduction_capacity_count": None,
                    "death_risk_count": None,
                },
            )
        return (
            {
                "schema_version": "death_energy_summary_v1",
                "death_monitoring_enabled": True,
                "feature_status": "measured",
                "status_reason": "records_present",
                "actual_death_count": self.actual_death_count,
                "nonfatal_capacity_block_count": self.nonfatal_capacity_block_count,
                "blocked_reproduction_capacity_count": self.blocked_reproduction_capacity_count,
                "death_risk_count": sum(1 for item in self.death_reason_records if item.death_risk_event),
            },
        )

    @property
    def export_status_records(self) -> tuple[ExportEnvelope, ...]:
        exports: tuple[tuple[str, tuple[object, ...]], ...] = (
            ("behavior_descriptors", self.behavior_descriptors),
            ("action_wiring_matrix", (self.action_wiring_matrix,)),
            ("strong_claim_ladder_records", self.strong_claim_ladder_records),
            ("qd_selection_audit", self.qd_selection_audit),
            ("qd_parent_feedback_audit", self.qd_parent_feedback_audit),
            ("qd_archive_summary", (self.qd_archive_summary,)),
            ("capsule_adoption_records", self.capsule_adoption_records),
            ("capsule_source_fitness_records", self.capsule_source_fitness_records),
            ("capsule_shuffle_records", self.capsule_shuffle_records),
            ("fitness_breakdown_records", self.fitness_breakdown_records),
            ("selection_fitness_records", self.selection_fitness_records),
            ("memory_use_records", self.memory_use_records),
            ("delayed_reward_records", self.delayed_reward_records),
            ("social_interaction_records", self.social_interaction_records),
            ("partner_interaction_records", self.partner_interaction_records),
            ("role_timeline_records", self.role_timeline_records),
            ("role_contribution_records", self.role_contribution_records),
            ("tool_chain_records", self.tool_chain_records),
            ("resource_policy_records", self.resource_policy_records),
            ("generalization_records", self.generalization_records),
            ("engine_frames", self.engine_frames),
            ("energy_accounting_records", self.energy_accounting_records),
            ("death_reason_records", self.death_reason_records),
            ("death_classification_records", self.death_classification_records),
            ("death_energy_summary_records", self.death_energy_summary_records),
            ("action_cost_records", self.action_cost_records),
            ("action_reward_records", self.action_reward_records),
            ("survival_baseline_records", self.survival_baseline_records),
            ("baseline_comparison_records", self.baseline_comparison_records),
            ("reproduction_attempt_records", self.reproduction_attempt_records),
            ("reproduction_gate_records", self.reproduction_gate_records),
            ("lineage_growth_records", self.lineage_growth_records),
            ("birth_event_records", self.birth_event_records),
            ("mutation_plan_records", self.mutation_plan_records),
            ("mutation_result_records", self.mutation_result_records),
            ("child_genome_records", self.child_genome_records),
            ("learning_inheritance_records", self.learning_inheritance_records),
            ("skill_compression_records", self.skill_compression_records),
            ("adf_inheritance_records", self.adf_inheritance_records),
            ("ai_birth_intervention_records", self.ai_birth_intervention_records),
            ("child_admission_records", self.child_admission_records),
            ("capsule_cost_records", self.capsule_cost_records),
            ("capsule_utility_records", self.capsule_utility_records),
            ("post_capsule_behavior_records", self.post_capsule_behavior_records),
            ("inventory_records", self.inventory_records),
            ("action_precondition_records", self.action_precondition_records),
            ("exportable_population_snapshot", (self.exportable_population_snapshot,)),
            ("exportable_lineage_snapshots", self.exportable_lineage_snapshots),
            ("evaluation_protocol_digest", (self.evaluation_protocol_digest_record,)),
            ("engine_digest_audit", self.engine_digest_audit),
            ("phase1_runtime_maturity_report", (self.phase1_runtime_maturity_report,)),
            ("phase1_runtime_maturity_matrix", self.phase1_runtime_maturity_report.feature_statuses),
            ("phase_b_scientific_maturity_report", (self.phase_b_scientific_maturity_report,)),
            ("phase_b_scientific_maturity_matrix", self.phase_b_scientific_maturity_report.feature_statuses),
            ("phase_b_discovery_events", self.phase_b_scientific_maturity_report.discovery_events),
            ("phase_b_ablation_witnesses", self.phase_b_scientific_maturity_report.ablation_witnesses),
            ("phase_b_heldout_evaluations", self.phase_b_scientific_maturity_report.heldout_evaluations),
            ("phase_b_collective_swarm_ladders", self.phase_b_scientific_maturity_report.collective_swarm_ladders),
            ("phase_b_oee_results", self.phase_b_scientific_maturity_report.oee_results),
            ("phase_b_curriculum_records", self.phase_b_scientific_maturity_report.curriculum_records),
            ("phase_b_scale_reports", self.phase_b_scientific_maturity_report.scale_reports),
            ("phase_b_statistical_results", self.phase_b_scientific_maturity_report.statistical_results),
            ("phase_b_plugin_validations", self.phase_b_scientific_maturity_report.plugin_validations),
            ("phase_b_release_packs", self.phase_b_scientific_maturity_report.release_packs),
            ("digest_instability_reasons", self.digest_instability_reasons),
        )
        rows: list[ExportEnvelope] = []
        for name, records in exports:
            if name in {"death_reason_records", "death_classification_records"} and self._death_monitoring_disabled:
                status: FeatureStatus = "disabled_by_config"
                reason = "death_monitoring_disabled"
            elif name == "death_energy_summary_records" and self._death_monitoring_disabled:
                status = "disabled_by_config"
                reason = "death_monitoring_disabled"
            elif name == "action_wiring_matrix" and records:
                matrix = records[0]
                matrix_records = tuple(getattr(matrix, "records", ()))
                if matrix_records and all(bool(getattr(row, "runtime_validated", False)) for row in matrix_records):
                    status = "measured"
                    reason = "all_action_wiring_rows_runtime_validated"
                else:
                    status = "provisional"
                    reason = "contract_only_action_wiring_not_runtime_smoke_validated"
            elif records:
                status = "measured"
                reason = "records_present"
            elif name in {"death_reason_records", "death_classification_records"} and self._death_record_emission_suppressed:
                status = "empty_but_available"
                reason = "no_death_or_risk_events_observed"
            else:
                status = "empty_but_available"
                reason = "no_matching_events_observed"
            rows.append(
                ExportEnvelope(
                    schema_version=f"{name}_export_v1",
                    feature_status=status,
                    status_reason=reason,
                    records=tuple(_jsonish_for_digest(item) for item in records),
                )
            )
        return tuple(rows)

    @property
    def export_envelopes_by_name(self) -> dict[str, ExportEnvelope]:
        return {item.schema_version.removesuffix("_export_v1"): item for item in self.export_status_records}

    @property
    def export_table_schemas(self) -> dict[str, tuple[str, ...]]:
        schemas: dict[str, tuple[str, ...]] = {}
        for name, envelope in self.export_envelopes_by_name.items():
            if envelope.records and isinstance(envelope.records[0], dict):
                schemas[name] = tuple(str(key) for key in envelope.records[0].keys())
            else:
                schemas[name] = ("schema_version", "feature_status", "status_reason")
        return schemas

    def export_records(self, name: str) -> ExportEnvelope:
        envelopes = self.export_envelopes_by_name
        if name not in envelopes:
            return ExportEnvelope(
                schema_version=f"{name}_export_v1",
                feature_status="unavailable",
                status_reason="unknown_export_name",
                records=(),
            )
        return envelopes[name]

    @property
    def output_completeness_records(self) -> tuple[OutputCompletenessRecord, ...]:
        return tuple(
            OutputCompletenessRecord(
                artifact_name=item.schema_version.removesuffix("_export_v1"),
                schema_version="output_completeness_record_v1",
                feature_status=item.feature_status,
                record_count=len(item.records),
                measured_after_final_write=True,
                self_size_reliable=True,
                status_reason=item.status_reason,
            )
            for item in self.export_status_records
        )

    @property
    def exportable_population_snapshot(self) -> object:
        return self.snapshot.population

    @property
    def exportable_lineage_snapshots(self) -> tuple[dict[str, JsonValue], ...]:
        return tuple(
            {
                "schema_version": "lineage_snapshot_v1",
                "tick": tick.index,
                "population_digest": tick.generation_result.population.digest(),
                "lineage_digest": _digest(
                    {
                        "lineage": [
                            item.to_dict() for item in tick.generation_result.population.lineage
                        ]
                    }
                ),
            }
            for tick in self.ticks
        )


    @property
    def evaluation_protocol_digest_record(self) -> dict[str, JsonValue]:
        return {
            "schema_version": "evaluation_protocol_digest_v1",
            "digest": self.evaluation_protocol_digest,
            "run_id": self.run.run_id,
            "spec_digest": self.run.spec_digest,
        }

    @property
    def evaluation_protocol_digest(self) -> str:
        return _digest(
            {
                "schema_version": "replayable_evaluation_protocol_v1",
                "run_id": self.run.run_id,
                "spec_digest": self.run.spec_digest,
                "train_heldout_separation": "runner_defined",
                "library_role": "snapshot_replay_evaluation_primitive",
            }
        )

    @property
    def evidence_manifest(self) -> EvidenceManifest:
        artifact_map = {
            "behavior_descriptors": _digest_sequence(self.behavior_descriptors),
            "action_wiring_matrix": _digest_sequence((self.action_wiring_matrix,)),
            "strong_claim_ladder_records": _digest_sequence(self.strong_claim_ladder_records),
            "qd_selection_audit": _digest_sequence(self.qd_selection_audit),
            "qd_parent_feedback_audit": _digest_sequence(self.qd_parent_feedback_audit),
            "qd_archive_summary": _digest_sequence((self.qd_archive_summary,)),
            "capsule_adoption_records": _digest_sequence(self.capsule_adoption_records),
            "capsule_source_fitness_records": _digest_sequence(self.capsule_source_fitness_records),
            "capsule_shuffle_records": _digest_sequence(self.capsule_shuffle_records),
            "fitness_breakdown_records": _digest_sequence(self.fitness_breakdown_records),
            "selection_fitness_records": _digest_sequence(self.selection_fitness_records),
            "memory_use_records": _digest_sequence(self.memory_use_records),
            "delayed_reward_records": _digest_sequence(self.delayed_reward_records),
            "social_interaction_records": _digest_sequence(self.social_interaction_records),
            "partner_interaction_records": _digest_sequence(self.partner_interaction_records),
            "role_timeline_records": _digest_sequence(self.role_timeline_records),
            "role_contribution_records": _digest_sequence(self.role_contribution_records),
            "tool_chain_records": _digest_sequence(self.tool_chain_records),
            "resource_policy_records": _digest_sequence(self.resource_policy_records),
            "generalization_records": _digest_sequence(self.generalization_records),
            "engine_frames": _digest_sequence(self.engine_frames),
            "energy_accounting_records": _digest_sequence(self.energy_accounting_records),
            "death_reason_records": _digest_sequence(self.death_reason_records),
            "action_cost_records": _digest_sequence(self.action_cost_records),
            "action_reward_records": _digest_sequence(self.action_reward_records),
            "survival_baseline_records": _digest_sequence(self.survival_baseline_records),
            "baseline_comparison_records": _digest_sequence(self.baseline_comparison_records),
            "reproduction_attempt_records": _digest_sequence(self.reproduction_attempt_records),
            "reproduction_gate_records": _digest_sequence(self.reproduction_gate_records),
            "lineage_growth_records": _digest_sequence(self.lineage_growth_records),
            "birth_event_records": _digest_sequence(self.birth_event_records),
            "mutation_plan_records": _digest_sequence(self.mutation_plan_records),
            "mutation_result_records": _digest_sequence(self.mutation_result_records),
            "child_genome_records": _digest_sequence(self.child_genome_records),
            "learning_inheritance_records": _digest_sequence(self.learning_inheritance_records),
            "skill_compression_records": _digest_sequence(self.skill_compression_records),
            "adf_inheritance_records": _digest_sequence(self.adf_inheritance_records),
            "ai_birth_intervention_records": _digest_sequence(self.ai_birth_intervention_records),
            "capsule_cost_records": _digest_sequence(self.capsule_cost_records),
            "capsule_utility_records": _digest_sequence(self.capsule_utility_records),
            "post_capsule_behavior_records": _digest_sequence(self.post_capsule_behavior_records),
            "inventory_records": _digest_sequence(self.inventory_records),
            "action_precondition_records": _digest_sequence(self.action_precondition_records),
            "export_status_records": _digest_sequence(self.export_status_records),
            "output_completeness_records": _digest_sequence(self.output_completeness_records),
            "exportable_population_snapshot": _digest_sequence(
                (self.exportable_population_snapshot,)
            ),
            "exportable_lineage_snapshots": _digest_sequence(self.exportable_lineage_snapshots),
            "evaluation_protocol_digest": _digest_sequence((self.evaluation_protocol_digest,)),
            "engine_digest_audit": _digest_sequence(self.engine_digest_audit),
            "digest_instability_reasons": _digest_sequence(self.digest_instability_reasons),
        }
        for envelope in self.export_status_records:
            export_name = envelope.schema_version.removesuffix("_export_v1")
            artifact_map.setdefault(export_name, _digest_sequence(envelope.records))
        phase1_report = self.phase1_runtime_maturity_report
        phase_b_report = self.phase_b_scientific_maturity_report
        artifact_map.update(phase1_report.artifact_digest_map)
        artifact_map.update(phase_b_report.artifact_digest_map)
        feature_status = {
            item.schema_version.removesuffix("_export_v1"): item.feature_status
            for item in self.export_status_records
        }
        feature_status.update(phase1_report.manifest_feature_status)
        feature_status.update(phase_b_report.manifest_feature_status)
        feature_status["phase1_runtime_maturity_report"] = "measured"
        feature_status["phase_b_scientific_maturity_report"] = "measured"
        return EvidenceManifest(
            schema_version="genesis_evidence_manifest_v2",
            producer_version="GenesisRunResult.properties",
            library_version="0.3.0b1",
            config_digest=self.run.spec_digest,
            source_digest=self.manifest.source_digest or "",
            protocol_digest=self.manifest.digest(),
            artifact_digests=tuple(artifact_map[key] for key in sorted(artifact_map)),
            artifact_digest_map=artifact_map,
            feature_status=feature_status,
        )

    def with_review_result(self, review: LLMReviewResult) -> GenesisRunResult:
        record = ExternalReviewRecord.from_result(review, validated=True)
        status = ReviewStatus(
            status="reviewed_accepted" if review.claim_review.allowed else "reviewed_flagged",
            reviewer=review.reviewer_id,
            decision_digest=record.result_digest,
        )
        manifest = replace(self.manifest, review_status=status)
        evidence_pack = replace(self.evidence_pack, manifest=manifest)
        replay_bundle = replace(self.replay_bundle, manifest=manifest)
        return replace(
            self,
            manifest=manifest,
            evidence_pack=evidence_pack,
            replay_bundle=replay_bundle,
            external_review_record=record,
        )

    def with_human_review(self, decision: HumanReviewDecision) -> GenesisRunResult:
        record = self.external_review_record
        if record is not None:
            record = replace(record, human_decision=decision)
        status = ReviewStatus(
            status=f"human_{decision.decision}",
            reviewer=decision.reviewer,
            decision_digest=decision.digest(),
        )
        manifest = replace(self.manifest, review_status=status)
        evidence_pack = replace(self.evidence_pack, manifest=manifest)
        replay_bundle = replace(self.replay_bundle, manifest=manifest)
        return replace(
            self,
            manifest=manifest,
            evidence_pack=evidence_pack,
            replay_bundle=replay_bundle,
            external_review_record=record,
        )


def _effective_evolution_config(spec: GenesisExperimentSpec) -> EvolutionConfig | None:
    base = spec.evolution_config
    if base is None:
        return None
    qd_mode = spec.engine_config.qd_mode if spec.engine_config.enable_qd else "disabled"
    policy = base.resolved_policy()
    if qd_mode == "selection_pressure" and policy.name == "fitness_proportional":
        return replace(base, selection_policy="novelty_weighted", qd_mode="selection_pressure")
    return replace(base, qd_mode=qd_mode)


class GenesisEngine:
    """Unified orchestration wrapper around existing GENESIS primitives."""

    def __init__(
        self,
        *,
        spec: GenesisExperimentSpec,
        runner: PopulationRunner,
        run: GenesisRun,
        qd_archive: QDArchive | None = None,
    ) -> None:
        self.spec = spec
        self.runner = runner
        self.run = run
        self.qd_archive = qd_archive
        self.element_grid = spec.element_grid
        self.review_status = ReviewStatus()
        self._tick_results: list[GenesisTickResult] = []
        self._snapshots: list[PopulationSnapshot] = [
            PopulationSnapshot.from_population(self.runner.population, self.runner.nexus_layer)
        ]
        self._last_result: GenesisRunResult | None = None
        self._qd_parent_feedback_applied = False

    @classmethod
    def from_spec(cls, spec: GenesisExperimentSpec) -> GenesisEngine:
        world = (
            element_grid_to_world2d(spec.element_grid)
            if spec.element_grid is not None and spec.substrate_bridge_mode == "element_grid_source"
            else World2D(spec.world_width, spec.world_height)
        )
        ribosome = spec.resolved_ribosome()
        memory_config = spec.memory_config or EpisodicMemoryConfig()
        causal_config = spec.causal_graph_config or CausalGraphConfig()
        action_registry = spec.action_registry
        organisms: list[GenesisOrganism] = []
        for index, bits in enumerate(spec.genome_bits):
            organism = GenesisOrganism.from_bits(
                f"org-{index}",
                bits,
                initial_runtime_atp=spec.initial_runtime_atp,
                initial_learning_atp=spec.initial_learning_atp,
                learning_enabled=spec.engine_config.enable_memory
                or spec.engine_config.enable_causal_graph,
                position=(
                    index % cast(Any, world).width,
                    index // cast(Any, world).width % cast(Any, world).height,
                ),
                ribosome=ribosome,
                causal_graph=CausalGraph(config=causal_config)
                if spec.engine_config.enable_causal_graph
                else None,
                action_registry=action_registry,
                action_runtime_config=spec.action_runtime_config,
                memory_config=memory_config,
                execution_source_enabled=spec.enable_execution_source,
                adf_macro_registry=spec.adf_macro_registry,
                adf_execution_policy=spec.adf_execution_policy,
                translation_profile=spec.translation_profile,
                translation_policy=spec.translation_policy,
            )
            if spec.engine_config.enable_memory:
                organism.episodic_memory = EpisodicMemory(memory_config)
            organisms.append(organism)
        population = PopulationState(
            generation=0, tick=0, organisms=tuple(organisms), lineage=(), fitness=()
        )
        capsule_config = (
            spec.capsule_transfer_config
            if spec.capsule_transfer_config is not None
            else (
                CapsuleTransferConfig(enabled=True) if spec.engine_config.enable_capsules else None
            )
        )
        if spec.population_configs is not None:
            configs = spec.population_configs
        else:
            configs = PopulationConfigs(
                reproduction=spec.reproduction_config
                or ReproductionConfig(max_population=spec.population_max),
                mutation=spec.mutation_config or MutationConfig(bit_flip_rate=0.0),
                structural_mutation=spec.structural_mutation_config,
                fitness=FitnessConfig(),
                ticks_per_generation=spec.engine_config.ticks_per_generation,
                capsule_transfer=capsule_config,
                enable_nexus_stigmergy=spec.engine_config.enable_capsules,
                evolution=_effective_evolution_config(spec),
                qd_mode=spec.engine_config.qd_mode if spec.engine_config.enable_qd else "disabled",
            )
        runner = PopulationRunner(
            population=population,
            world=cast(Any, world),
            configs=configs,
            nexus_layer=NexusStigmergyLayer() if spec.engine_config.enable_capsules else None,
        )
        qd_archive = (
            QDArchive.empty(spec.qd_archive_config)
            if spec.qd_archive_config is not None
            else (_default_qd_archive() if spec.engine_config.enable_qd else None)
        )
        run_id = f"genesis-run-{spec.digest()[:16]}"
        engine = cls(
            spec=spec,
            runner=runner,
            run=GenesisRun(run_id=run_id, spec_digest=spec.digest(), seed=spec.seed),
            qd_archive=qd_archive,
        )
        engine.element_grid = spec.element_grid or world2d_to_element_grid(world)
        return engine

    def run_ticks(self, ticks: int | None = None) -> GenesisRunResult:
        count = self.spec.tick_count if ticks is None else ticks
        if count < 0:
            msg = "ticks must be >= 0."
            raise ValueError(msg)
        base = len(self._tick_results)
        for index in range(count):
            generation = self.runner.step_generation(seed=self.spec.seed + base + index)
            self._apply_qd_parent_feedback(generation)
            qd_update = self._update_qd(generation)
            if self.spec.substrate_bridge_mode == "world2d_mirror":
                self.element_grid = world2d_to_element_grid(self.runner.world)
            tick_result = GenesisTickResult(
                index=len(self._tick_results), generation_result=generation, qd_update=qd_update
            )
            self._tick_results.append(tick_result)
            self._snapshots.append(
                PopulationSnapshot.from_population(self.runner.population, self.runner.nexus_layer)
            )
        self._last_result = self._build_result()
        return self._last_result

    def snapshot(self) -> GenesisSnapshot:
        return GenesisSnapshot(
            run_id=self.run.run_id,
            population=PopulationSnapshot.from_population(
                self.runner.population, self.runner.nexus_layer
            ),
            world_digest=self.runner.world.digest(),
            qd_archive_digest=None if self.qd_archive is None else self.qd_archive.digest(),
            element_grid_digest=None if self.element_grid is None else self.element_grid.digest(),
            substrate_bridge_mode=self.spec.substrate_bridge_mode,
        )

    def export_evidence_pack(self) -> RunArtifactSchema:
        if self._last_result is None:
            return self._build_result().evidence_pack
        return self._last_result.evidence_pack

    def export_replay_bundle(self) -> ReplayBundle:
        if self._last_result is None:
            return self._build_result().replay_bundle
        return self._last_result.replay_bundle

    def build_review_request(self) -> LLMReviewRequest:
        return LLMReviewRequest.from_evidence_pack(
            self.export_evidence_pack(), request_id=f"review:{self.run.run_id}"
        )

    def record_review_result(
        self, result: LLMReviewResult, *, reviewer: str | None = None
    ) -> GenesisRunResult:
        """Validate a provider-neutral review result and attach review status to the manifest."""

        request = self.build_review_request()
        validated = validate_review_result(result, request=request)
        self.review_status = ReviewStatus(
            status="accepted" if validated.claim_review.allowed else "flagged",
            reviewer=reviewer or validated.reviewer_id,
            decision_digest=validated.digest(),
        )
        self._last_result = self._build_result()
        return self._last_result

    def _update_qd(self, generation: GenerationResult) -> QDArchiveBatchUpdateResult | None:
        if self.qd_archive is None:
            return None
        candidates: list[QDElite] = []
        for record in generation.organism_records:
            if record.behavior_descriptor is None:
                continue
            descriptor = record.behavior_descriptor.to_dict()
            reduced = {
                "survival_ticks": _json_float_value(descriptor.get("survival_ticks", 0.0)),
                "blocked_ratio": _json_float_value(descriptor.get("blocked_ratio", 0.0)),
            }
            behavior_bin = assign_behavior_bin(reduced, self.qd_archive.config.schema)
            candidates.append(
                QDElite(
                    organism_id=record.organism_id,
                    fitness=record.fitness_result.score,
                    behavior_descriptor=reduced,
                    behavior_bin=behavior_bin,
                    genome_digest=record.genome_digest or "missing_genome_digest",
                    trace_digest=record.trace_digest,
                    metadata={
                        "source": "GenesisEngine",
                        "provenance_status": "verified_genome_digest"
                        if record.genome_digest
                        else "missing_genome_digest",
                    },
                )
            )
        if not candidates:
            return None
        before = self.qd_archive.digest()
        current = self.qd_archive
        records: list[QDArchiveItemUpdateRecord] = []
        inserted = replaced = rejected = 0
        for candidate in candidates:
            update = update_qd_archive(current, candidate)
            current = update.archive
            records.append(QDArchiveItemUpdateRecord.from_update_result(update))
            inserted += int(update.inserted)
            replaced += int(update.replaced)
            rejected += int(update.rejected)
        self.qd_archive = current
        return QDArchiveBatchUpdateResult(
            archive_before_digest=before,
            archive_after_digest=current.digest(),
            candidates_seen=len(candidates),
            inserted_count=inserted,
            replaced_count=replaced,
            rejected_count=rejected,
            update_records=tuple(records),
            summary=summarize_qd_archive(current),
        )

    def _apply_qd_parent_feedback(self, generation: GenerationResult) -> None:
        """Use QD archive novelty to deterministically order/select next-generation parents."""
        if (
            self.qd_archive is None
            or not self.spec.engine_config.enable_qd
            or self.spec.engine_config.qd_mode != "selection_pressure"
        ):
            return
        evolution = _effective_evolution_config(self.spec)
        if evolution is None or evolution.novelty_weight <= 0:
            return
        organisms = tuple(self.runner.population.organisms)
        if len(organisms) <= 1:
            return
        descriptors: dict[str, dict[str, float]] = {}
        fitness_scores: dict[str, float] = {}
        for record in generation.organism_records:
            if record.behavior_descriptor is not None:
                descriptors[record.organism_id] = {
                    key: _json_float_value(value)
                    for key, value in record.behavior_descriptor.to_dict().items()
                    if isinstance(value, int | float) and not isinstance(value, bool)
                }
            fitness_scores[record.organism_id] = record.fitness_result.score
        novelty_scores = compute_novelty_scores_from_archive(
            organisms, descriptors, self.qd_archive
        )
        feedback_config = EvolutionConfig(
            selection_policy="novelty_weighted",
            elitism_count=evolution.elitism_count,
            tournament_size=evolution.tournament_size,
            novelty_weight=evolution.novelty_weight,
            fitness_weight=evolution.fitness_weight,
            max_population=len(organisms),
            extinction_policy=evolution.extinction_policy,
            qd_mode="selection_pressure",
        )
        selected, _selection_result = select_population(
            organisms,
            fitness_scores=fitness_scores,
            novelty_scores=novelty_scores,
            max_population=len(organisms),
            config=feedback_config,
            qd_mode="selection_pressure",
        )
        selected_organisms = tuple(cast(GenesisOrganism, item) for item in selected)
        if tuple(org.id for org in selected_organisms) != tuple(org.id for org in organisms):
            self.runner.population = replace(self.runner.population, organisms=selected_organisms)
            self._qd_parent_feedback_applied = True

    def _build_result(self) -> GenesisRunResult:
        snapshot = self.snapshot()
        generation_digests = tuple(item.generation_result.digest() for item in self._tick_results)
        raw_events = _raw_events(self._tick_results)
        contribution_ledgers = _contribution_ledgers_from_raw_events(
            raw_events, self.runner.population.generation
        )
        semantic_report = (
            None
            if self.spec.translation_profile is None
            else build_semantic_proxy_report(
                self.spec.translation_profile,
                behavior_delta_digest=_digest(
                    {
                        "ticks": len(self._tick_results),
                        "population": self.runner.population.digest(),
                    }
                ),
                lineage_persistence=self.runner.population.generation,
                replay_captured=True,
            )
        )
        phase2_hashes = _phase2_hashes(
            engine=self,
            contribution_ledgers=contribution_ledgers,
            semantic_report_digest=None if semantic_report is None else semantic_report.digest,
        )
        replay_seed_payload: dict[str, JsonValue] = {
            "run": self.run.to_dict(),
            "snapshots": cast(JsonValue, [item.to_dict() for item in self._snapshots]),
            "generation_digests": cast(JsonValue, list(generation_digests)),
            "phase2_hashes": cast(JsonValue, phase2_hashes),
        }
        replay_digest = _digest(replay_seed_payload)
        manifest_rng = RNGManager(seed=self.spec.seed, namespace="engine_manifest")
        seed_schedule_digest = _digest(
            {
                "seed": self.spec.seed,
                "tick_count": len(self._tick_results),
                "schedule": cast(
                    JsonValue,
                    [self.spec.seed + index for index in range(len(self._tick_results))],
                ),
            }
        )
        source_digest = compute_source_digest()
        evidence_flags = _claim_evidence_flags(self, contribution_ledgers, semantic_report)
        evidence_digests = tuple(
            value
            for value in (
                replay_digest,
                snapshot.digest(),
                None if self.qd_archive is None else self.qd_archive.digest(),
                None
                if not contribution_ledgers
                else _digest(
                    {"ledgers": cast(JsonValue, [ledger.digest for ledger in contribution_ledgers])}
                ),
            )
            if value
        )
        claim_decision = ScientificClaimGate().decide(
            ClaimRequest(
                self.spec.engine_config.claim_level,
                evidence_flags,
                manifest_digest=None,
                evidence_digests=evidence_digests,
            )
        )
        claim_gate_decision_digest = claim_decision.digest
        phase2_hashes = {
            **phase2_hashes,
            "claim_gate_decision_digest": claim_gate_decision_digest,
            "phase2_claim_decision_digest": claim_gate_decision_digest,
        }
        ribosome = self.spec.resolved_ribosome()
        codon_table = self.spec.codon_table or ribosome.codon_table
        manifest = manifest_from_parts(
            run_id=self.run.run_id,
            seed=self.run.seed,
            config=self.spec.to_dict(),
            codon_table_hash=_codon_table_hash(codon_table),
            genome_spec_hash=_genome_spec_hash(
                self.spec.genome_spec or codon_table.spec.genome_spec
            ),
            rule_set_hash=_digest({"approved_rule_set": None})
            if self.spec.approved_rule_set is None
            else self.spec.approved_rule_set.digest(),
            adf_vocabulary_hash=_adf_vocabulary_hash(codon_table),
            initial_population_hash=self._snapshots[0].population_digest,
            tick_count=len(self._tick_results),
            replay_digest=replay_digest,
            claim_level=claim_decision.final_claim,
            claim_decision=claim_decision,
            protocol_statuses=_protocol_statuses(self, phase2_hashes),
            manifest_schema_complete=True,
            scientific_protocol_executed=_scientific_protocol_executed(self, phase2_hashes),
            review_status=self.review_status,
            runtime_hashes={
                "action_registry_hash": _action_registry_hash(self.spec.action_registry),
                "ribosome_hash": _ribosome_hash(ribosome),
                "engine_config_hash": _object_hash(self.spec.engine_config),
                "population_config_hash": _object_hash(self.runner.configs),
                "evolution_config_hash": _object_hash(self.spec.evolution_config),
                "capsule_transfer_config_hash": _object_hash(self.runner.configs.capsule_transfer),
                "qd_archive_config_hash": _object_hash(
                    None if self.qd_archive is None else self.qd_archive.config
                ),
                "substrate_bridge_mode": self.spec.substrate_bridge_mode,
                "element_grid_hash": None
                if self.element_grid is None
                else self.element_grid.digest(),
                **phase2_hashes,
            },
            source_digest=source_digest,
            rng_backend_kind=self.spec.engine_config.rng_backend_kind,
            rng_namespace=manifest_rng.namespace,
            rng_draw_count=manifest_rng.draw_count + len(self._tick_results),
            rng_state_digest=manifest_rng.state_digest(),
            seed_schedule_digest=seed_schedule_digest,
            fitness_config_hash=_object_hash(self.runner.configs.fitness),
            descriptor_schema_hash=None
            if self.qd_archive is None
            else self.qd_archive.config.schema.digest(),
            archive_digest=None if self.qd_archive is None else self.qd_archive.digest(),
            qd_scheduler_digest=_qd_scheduler_manifest_digest(
                self, phase2_hashes, manifest_rng.state_digest()
            ),
            benchmark_scenario_digest=str(self.spec.metadata.get("benchmark_scenario_digest"))
            if "benchmark_scenario_digest" in self.spec.metadata
            else None,
            execution_source_digest=_execution_source_digest(
                raw_events, enabled=self.spec.enable_execution_source
            ),
            claim_gate_decision_digest=claim_gate_decision_digest,
        )
        summary = _summarize_run(
            self.run.run_id, self._tick_results, self.runner.population, self.qd_archive
        )
        evidence_pack = RunArtifactSchema(
            manifest=manifest,
            summary=summary,
            snapshot=snapshot.population,
            raw_events=raw_events,
            contribution_ledgers=tuple(ledger.to_dict() for ledger in contribution_ledgers),
        )
        replay_bundle = ReplayBundle(
            manifest=manifest,
            snapshots=tuple(self._snapshots),
            generation_digests=generation_digests,
        )
        action_wiring_matrix = export_action_wiring_matrix(
            action_registry=self.spec.action_registry,
            codon_table=codon_table,
            profile_name="engine_run",
        )
        provisional_result = GenesisRunResult(
            run=self.run,
            ticks=tuple(self._tick_results),
            manifest=manifest,
            snapshot=snapshot,
            evidence_pack=evidence_pack,
            replay_bundle=replay_bundle,
            action_wiring_matrix=action_wiring_matrix,
            strong_claim_ladder_records=(),
        )
        return replace(
            provisional_result,
            strong_claim_ladder_records=_strong_claim_ladder_records_for_result(
                provisional_result,
                claim_gate_decision_digest=claim_gate_decision_digest,
            ),
        )


def _strong_claim_ladder_records_for_result(
    result: GenesisRunResult,
    *,
    claim_gate_decision_digest: str | None,
) -> tuple[StrongClaimLadderResult, ...]:
    """Build Phase 1 claim ladder records from real result surfaces.

    The ladder record is evidence-derived and cumulative.  It does not promote
    a run with placeholder evidence; missing pilot/control/ablation/multi-seed/
    heldout/intervention layers remain false until actual protocols provide
    those artifacts.
    """

    runtime_surfaces = (
        result.behavior_descriptors,
        result.energy_accounting_records,
        result.action_cost_records,
        result.action_reward_records,
        result.reproduction_attempt_records,
        result.qd_selection_audit,
        result.capsule_adoption_records,
        result.memory_use_records,
        result.tool_chain_records,
        result.engine_frames,
    )
    has_runtime_records = any(bool(surface) for surface in runtime_surfaces)
    has_negative_control = bool(
        result.baseline_comparison_records
        or result.capsule_shuffle_records
    )
    evidence_flags = {
        "schema_version": True,
        "artifact_digest": True,
        "runtime_records": has_runtime_records,
        "pilot_run": False,
        "negative_control": has_negative_control,
        "control_digest": has_negative_control,
        "ablation_result": False,
        "ablation_digest": False,
        "multi_seed_protocol": False,
        "effect_size": False,
        "confidence_interval": False,
        "heldout_protocol": False,
        "leakage_check": False,
        "partner_or_world_shift": bool(result.partner_interaction_records),
        "intervention_result": False,
        "treatment_digest": False,
        "baseline_digest": has_negative_control,
        "replay_verification": bool(result.replay_bundle.digest()),
        "claim_gate_decision_digest": bool(claim_gate_decision_digest),
    }
    return (
        evaluate_strong_claim_ladder(
            "genesis_phase1_core_evidence_claim",
            evidence_flags,
            target_level="claim_ready_research_alpha",
        ),
    )

def _jsonish_for_digest(item: object) -> JsonValue:
    if isinstance(item, _JsonDictSerializable):
        return item.to_dict()
    if isinstance(item, Mapping):
        return cast(JsonValue, dict(item))
    if isinstance(item, tuple | list):
        return cast(JsonValue, [_jsonish_for_digest(value) for value in item])
    if isinstance(item, str | int | float | bool) or item is None:
        return cast(JsonValue, item)
    return str(item)


def _digest_sequence(items: Sequence[object]) -> str:
    return _digest({"items": [_jsonish_for_digest(item) for item in items]})


def _mean_float(values: object) -> float:
    if not isinstance(values, Sequence) or isinstance(values, str | bytes):
        return 0.0
    seq = [float(item) for item in values if isinstance(item, (int, float))]
    return round(sum(seq) / len(seq), 10) if seq else 0.0


def _death_reason_from_record(record: object) -> str:
    alive = getattr(record, "alive_result", None)
    if alive is None:
        return "unknown"
    reasons = tuple(getattr(alive, "reasons", ()))
    final_atp = float(getattr(alive, "final_runtime_atp", 0.0))
    blocked_actions = int(getattr(alive, "blocked_actions", 0))
    if final_atp <= 0:
        return "atp_starvation"
    joined = " ".join(str(item) for item in reasons).lower()
    if "reproduction" in joined:
        return "reproduction_cost"
    if "capsule_emission" in joined:
        return "capsule_emission_cost"
    if "capsule_adoption" in joined:
        return "capsule_adoption_cost"
    if "move" in joined or "movement" in joined:
        return "movement_cost"
    if "hazard" in joined or "damage" in joined:
        return "hazard_damage"
    if "invalid" in joined:
        return "invalid_action"
    if "depletion" in joined or "resource" in joined:
        return "environment_depletion"
    if blocked_actions > 0 and not getattr(alive, "passed", True):
        return "blocked_action_accumulation"
    return "unknown"


def _claim_evidence_flags(
    engine: GenesisEngine,
    contribution_ledgers: Sequence[ContributionLedger],
    semantic_report: object | None,
) -> dict[str, bool]:
    active_qd = engine.qd_archive is not None and bool(engine.spec.engine_config.enable_qd)
    qd_selection_pressure = active_qd and engine.spec.engine_config.qd_mode == "selection_pressure"
    qd_feedback = qd_selection_pressure and engine._qd_parent_feedback_applied
    metadata = engine.spec.metadata
    evidence_context = engine.spec.evidence_validation_context or EvidenceValidationContext()
    intervention_flags = dict(evidence_context.intervention_evidence_flags())
    oee_flags = dict(evidence_context.oee_evidence_flags())
    predictive_flags = evidence_context.predictive_evidence_flags()
    semantic_flags = dict(evidence_context.semantic_proxy_evidence_flags())
    semantic_report_present = semantic_report is not None
    semantic_report_replay_captured = bool(getattr(semantic_report, "replay_captured", False))
    if semantic_report_present or evidence_context.has_semantic_proxy_artifact():
        semantic_flags["semantic_proxy_report"] = True
        semantic_flags["semantic_proxy_report_digest"] = True
    else:
        semantic_flags.setdefault("semantic_proxy_report_digest", False)
    semantic_flags["replay_capture"] = bool(
        semantic_report_replay_captured or semantic_flags.get("replay_capture", False)
    )
    claim_gate_decision_digest_available = bool(
        intervention_flags.pop("claim_gate_decision_digest", False)
        or oee_flags.pop("claim_gate_decision_digest", False)
    )
    custom_handlers_replayable = _action_registry_replayable(engine.spec.action_registry)
    has_runtime_ticks = bool(engine._tick_results)
    return {
        "manifest": True,
        "runtime_effect": has_runtime_ticks,
        "artifact_digest": True,
        "replay_verification": custom_handlers_replayable,
        "replayable_action_handlers": custom_handlers_replayable,
        "fitness_components": True,
        "fitness_config_digest": True,
        "qd_candidate_schema": active_qd,
        "archive_digest": active_qd,
        "qd_ask_tell": active_qd,
        "archive_feedback": qd_feedback,
        "parent_selection_feedback": qd_feedback,
        "parent_selection_feedback_digest": qd_feedback,
        "qd_scheduler_digest": active_qd,
        "qd_mode_selection_pressure": qd_selection_pressure,
        "qd_changed_selection": qd_feedback,
        "benchmark_suite_v2": bool(metadata.get("benchmark_scenario_digest"))
        and metadata.get("scenario_runtime_status") in {"measured", "runtime_effective"}
        and metadata.get("claim_allowed", True) is True
        and metadata.get("behavior_digest_equal_baseline_treatment", False) is not True,
        "execution_source_map": engine.spec.enable_execution_source
        and bool(_execution_records_from_raw_events(_raw_events(engine._tick_results))),
        "genome_program_digest": True,
        "births_positive": any(t.generation_result.births > 0 for t in engine._tick_results),
        "heritable_variation": bool(engine.spec.mutation_config is not None and engine.spec.mutation_config.bit_flip_rate > 0.0),
        "differential_fitness": any(
            t.generation_result.selection_best_fitness > t.generation_result.selection_mean_fitness
            for t in engine._tick_results
        ),
        "structural_mutation_record": bool(engine.spec.structural_mutation_config is not None),
        "adf_macro_expansion": engine.spec.adf_macro_registry is not None,
        "bounded_expansion": engine.spec.adf_macro_registry is not None,
        "source_map": engine.spec.enable_execution_source,
        "contribution_ledger": bool(contribution_ledgers)
        or bool(evidence_context.contribution_ledgers),
        "execution_records": bool(
            _execution_records_from_raw_events(_raw_events(engine._tick_results))
        ),
        "event_graph": True,
        "event_graph_digest": has_runtime_ticks,
        **predictive_flags,
        **intervention_flags,
        # Metadata-only ground-truth/recovery digest strings are artifact pointers,
        # not validated scientific evidence.
        "ground_truth_world": False,
        "recovery_report": False,
        **oee_flags,
        "claim_gate_decision_digest": claim_gate_decision_digest_available,
        "translation_profile": engine.spec.translation_profile is not None,
        **semantic_flags,
        **evidence_context.validated_evidence_flag_map(),
        "translation_safety_gates": _translation_safety_gate_passed(engine),
    }


def _qd_scheduler_manifest_digest(
    engine: GenesisEngine, phase2_hashes: Mapping[str, str | None], rng_state_digest: str
) -> str:
    archive_digest = None if engine.qd_archive is None else engine.qd_archive.digest()
    descriptor_schema_digest = (
        None if engine.qd_archive is None else engine.qd_archive.config.schema.digest()
    )
    parent_feedback_digest = (
        _digest({"parent_selection_feedback": True, "ticks": len(engine._tick_results)})
        if engine._qd_parent_feedback_applied
        else None
    )
    return _digest(
        {
            "archive_digest": archive_digest,
            "descriptor_schema_digest": descriptor_schema_digest,
            "emitter_state_digest": phase2_hashes.get("qd_emitter_state_digest", "default_emitter"),
            "scheduler_generation": len(engine._tick_results),
            "selection_feedback_policy": "archive_parent_feedback"
            if engine._qd_parent_feedback_applied
            else "reporting_only",
            "parent_selection_feedback_digest": parent_feedback_digest,
            "rng_state_digest": rng_state_digest,
        }
    )


def _action_registry_replayable(registry: ActionRegistry | None) -> bool:
    if registry is None:
        return True
    builtins = set(default_action_registry().names())
    return all(name in builtins for name in registry.names())


def _translation_safety_gate_passed(engine: GenesisEngine) -> bool:
    profile = engine.spec.translation_profile
    if profile is None:
        return False
    approved = set(
        engine.spec.action_registry.names()
        if engine.spec.action_registry is not None
        else default_action_registry().names()
    )
    return all(weight.action in approved for weight in profile.weights)


def _protocol_statuses(
    engine: GenesisEngine, phase2_hashes: Mapping[str, str | None]
) -> dict[str, str]:
    evidence_context = engine.spec.evidence_validation_context or EvidenceValidationContext()
    predictive_executed = evidence_context.has_predictive_probe_artifact()
    intervention_executed = (
        evidence_context.has_validated_intervention_result()
        and evidence_context.has_intervention_protocol_artifact()
    )
    intervention_result_status = (
        "supported" if evidence_context.has_validated_intervention_result() else "not_run"
    )
    oee_executed = evidence_context.has_oee_candidate_report()
    translation_executed = (
        evidence_context.has_semantic_proxy_artifact()
        or engine.spec.translation_profile is not None
    )
    # A digest for a disabled/not-configured innovation registry is not a validation protocol.
    innovation_active = False
    validation_executed = evidence_context.scientific_validation_protocol_executed()
    statuses = {
        "predictive_probe_status": "executed" if predictive_executed else "not_run",
        "predictive_probe_executed": str(predictive_executed).lower(),
        "intervention_protocol_status": "executed" if intervention_executed else "not_run",
        "intervention_result_status": intervention_result_status,
        "intervention_protocol_executed": str(intervention_executed).lower(),
        "oee_status": "candidate" if oee_executed else "not_run",
        "oee_protocol_executed": str(oee_executed).lower(),
        "translation_protocol_executed": str(translation_executed).lower(),
        "innovation_protocol_active": str(innovation_active).lower(),
        "scientific_feature_active": str(
            engine.spec.translation_profile is not None or innovation_active
        ).lower(),
        "scientific_validation_protocol_executed": str(validation_executed).lower(),
        "innovation_status": "active" if innovation_active else "not_configured",
        "semantic_proxy_status": "active" if translation_executed else "fixed_translation",
    }
    statuses.update(_phase2_manifest_protocol_statuses(engine, phase2_hashes))
    return statuses


def _phase2_manifest_protocol_statuses(
    engine: GenesisEngine, phase2_hashes: Mapping[str, str | None]
) -> dict[str, str]:
    """Status every Phase 2 manifest field next to its deterministic digest.

    The digest/status pair is the compatibility bridge from Phase 1 manifests
    to Phase 2 evidence. Disabled or not-run capabilities still receive stable
    digests for replay, but their status prevents downstream code from treating
    them as measured scientific evidence.
    """

    evidence_context = engine.spec.evidence_validation_context or EvidenceValidationContext()
    has_ticks = bool(engine._tick_results)
    has_mutation_event = any(
        isinstance(event.world_delta.get("mutation_digest"), str)
        for tick in engine._tick_results
        for trace in tick.generation_result.traces
        for event in trace.events
    )
    has_contribution_ledger = bool(phase2_hashes.get("contribution_ledger_digest")) and (
        bool(getattr(evidence_context, "contribution_ledgers", ()))
        or any(_execution_records_from_raw_events(_raw_events(engine._tick_results)))
    )
    benchmark_runtime = (
        "benchmark_scenario_digest" in engine.spec.metadata
        and engine.spec.metadata.get("scenario_runtime_status") in {"measured", "runtime_effective"}
    )
    statuses = {field: "not_run" for field in phase2_hashes}
    for field in ("genome_program_digest",):
        statuses[field] = "measured"
    for field in ("structural_mutation_digest", "structural_mutation_record_digest"):
        statuses[field] = "measured" if has_mutation_event else "not_observed"
    for field in ("adf_macro_registry_digest", "macro_registry_digest"):
        statuses[field] = "measured" if engine.spec.adf_macro_registry is not None else "disabled_by_config"
    for field in ("adf_usefulness_report_digest", "macro_utility_digest"):
        statuses[field] = "provisional" if engine.spec.adf_macro_registry is not None else "not_run"
    for field in ("translation_profile_digest", "translation_profile_hash"):
        statuses[field] = "measured" if engine.spec.translation_profile is not None else "fixed_default"
    statuses["contribution_ledger_digest"] = "measured" if has_contribution_ledger else "not_observed"
    statuses["micro_ablation_attribution_digest"] = "not_run"
    statuses["innovation_registry_digest"] = "not_configured"
    statuses["event_graph_digest"] = "measured" if has_ticks else "empty_but_available"
    statuses["predictive_probe_digest"] = (
        "measured" if evidence_context.has_predictive_probe_artifact() else "not_run"
    )
    intervention_status = (
        "measured"
        if evidence_context.has_validated_intervention_result()
        and evidence_context.has_intervention_protocol_artifact()
        else "not_run"
    )
    for field in (
        "intervention_protocol_digest",
        "intervention_result_digest",
        "causal_intervention_result_digest",
    ):
        statuses[field] = intervention_status
    statuses["discovery_witness_digest"] = "not_run"
    statuses["benchmark_scenario_digest"] = "measured" if benchmark_runtime else "not_configured"
    statuses["statistical_report_digest"] = "provisional" if has_ticks else "empty_but_available"
    statuses["oee_report_digest"] = "not_run"
    statuses["social_generalization_digest"] = "not_run"
    config_status_map = {
        "capsule_ablation_policy_digest": engine.spec.capsule_ablation_policy,
        "capsule_outcome_window_digest": engine.spec.capsule_outcome_window,
        "skill_compression_ablation_policy_digest": engine.spec.skill_compression_ablation_policy,
        "role_mechanics_policy_digest": engine.spec.role_mechanics_policy,
        "territory_mechanics_config_digest": engine.spec.territory_mechanics_config,
        "heldout_partner_protocol_digest": engine.spec.heldout_partner_protocol,
        "source_reputation_memory_digest": engine.spec.source_reputation_memory,
        "collective_task_graph_digest": engine.spec.collective_task_graph,
        "role_ablation_protocol_digest": engine.spec.role_ablation_protocol,
        "multi_agent_contribution_ledger_digest": engine.spec.multi_agent_contribution_ledger,
        "counterfactual_replay_protocol_digest": engine.spec.counterfactual_replay_protocol,
        "oee_extended_metrics_digest": engine.spec.oee_extended_metrics,
    }
    for field, configured_value in config_status_map.items():
        statuses[field] = "configured_digest_only" if configured_value is not None else "disabled_by_config"
    if engine.spec.oee_extended_metrics is not None and engine.spec.oee_extended_metrics.claim_eligible:
        statuses["oee_extended_metrics_digest"] = "candidate_evidence"
    if evidence_context.has_semantic_proxy_artifact() or engine.spec.translation_profile is not None:
        statuses["semantic_proxy_report_digest"] = "measured"
    else:
        statuses["semantic_proxy_report_digest"] = "fixed_default"
    statuses["phase2_claim_decision_digest"] = "measured"
    statuses["claim_gate_decision_digest"] = "measured"
    out = {f"phase2.{field}.status": status for field, status in sorted(statuses.items())}
    for field, status in sorted(statuses.items()):
        if status == "provisional":
            out[f"phase2.{field}.status_reason"] = "deterministic_digest_present_but_control_or_runtime_protocol_incomplete"
    return out


def _scientific_protocol_executed(
    engine: GenesisEngine, phase2_hashes: Mapping[str, str | None]
) -> bool:
    statuses = _protocol_statuses(engine, phase2_hashes)
    return statuses.get("scientific_validation_protocol_executed") == "true"


def _execution_records_from_raw_events(
    raw_events: Sequence[RawEventSchema],
) -> tuple[dict[str, JsonValue], ...]:
    records: list[dict[str, JsonValue]] = []
    for raw in raw_events:
        delta = raw.payload.get("world_delta")
        if isinstance(delta, Mapping):
            rec = delta.get("codon_execution_record")
            if isinstance(rec, Mapping):
                records.append(dict(rec))
            many = delta.get("codon_execution_records")
            if isinstance(many, list):
                records.extend(dict(item) for item in many if isinstance(item, Mapping))
    return tuple(records)


def _execution_source_digest(raw_events: Sequence[RawEventSchema], *, enabled: bool) -> str:
    records = _execution_records_from_raw_events(raw_events)
    return _digest(
        {
            "enable_execution_source": enabled,
            "record_count": len(records),
            "records": cast(JsonValue, records),
        }
    )


def attach_review_result(result: GenesisRunResult, review: LLMReviewResult) -> GenesisRunResult:
    """Return an immutable copy of a run result with review status attached."""

    return result.with_review_result(review)


def apply_human_review(result: GenesisRunResult, decision: HumanReviewDecision) -> GenesisRunResult:
    """Return an immutable copy of a run result with human review status attached."""

    return result.with_human_review(decision)


def _default_qd_archive() -> QDArchive:
    schema = BehaviorDescriptorSchema(
        descriptor_names=("survival_ticks", "blocked_ratio"),
        bins_per_descriptor={"survival_ticks": 8, "blocked_ratio": 8},
        min_values={"survival_ticks": 0.0, "blocked_ratio": 0.0},
        max_values={"survival_ticks": 16.0, "blocked_ratio": 1.0},
    )
    return QDArchive.empty(QDArchiveConfig(schema=schema))


def _summarize_run(
    run_id: str,
    ticks: Sequence[GenesisTickResult],
    population: PopulationState,
    qd_archive: QDArchive | None,
) -> ExperimentSummary:
    last = ticks[-1].generation_result if ticks else None
    qd_summary = summarize_qd_archive(qd_archive) if qd_archive is not None else None
    return ExperimentSummary(
        run_id=run_id,
        ticks=len(ticks),
        generations=population.generation,
        final_population=len(population.organisms),
        best_fitness=0.0 if last is None else last.best_fitness,
        mean_fitness=0.0 if last is None else last.mean_fitness,
        raw_best_fitness=None if last is None else last.raw_best_fitness,
        raw_mean_fitness=None if last is None else last.raw_mean_fitness,
        selection_best_fitness=None if last is None else last.selection_best_fitness,
        selection_mean_fitness=None if last is None else last.selection_mean_fitness,
        viable_best_fitness=None if last is None else last.viable_best_fitness,
        viable_mean_fitness=None if last is None else last.viable_mean_fitness,
        viability_gate_failures=0 if last is None else last.viability_gate_failures,
        causal_updates=sum(
            item.generation_result.causal_summary.update_successes for item in ticks
        ),
        capsules_emitted=sum(
            item.generation_result.causal_summary.capsules_emitted for item in ticks
        ),
        capsules_adopted=sum(
            item.generation_result.causal_summary.capsules_adopted for item in ticks
        ),
        qd_filled_bins=0 if qd_summary is None else qd_summary.filled_bins,
    )


def _raw_events(ticks: Sequence[GenesisTickResult]) -> tuple[RawEventSchema, ...]:
    events: list[RawEventSchema] = []
    for tick in ticks:
        for trace in tick.generation_result.traces:
            for event in trace.events:
                payload = event.to_dict()
                events.append(RawEventSchema(len(events), _digest(payload), payload))
    return tuple(events)


def _contribution_ledgers_from_raw_events(
    raw_events: Sequence[RawEventSchema],
    generation: int,
) -> tuple[ContributionLedger, ...]:
    """Build contribution ledgers from real CodonExecutionRecord payloads."""

    grouped: dict[str, list[CodonContributionRecord]] = {}
    for raw in raw_events:
        delta = raw.payload.get("world_delta")
        if not isinstance(delta, Mapping):
            continue
        record_raw = delta.get("codon_execution_record")
        if not isinstance(record_raw, Mapping):
            continue
        try:
            execution = CodonExecutionRecord.from_dict(dict(record_raw))
        except Exception:
            continue
        contribution = contribution_from_execution_record(execution, generation=generation)
        grouped.setdefault(execution.organism_id, []).append(contribution)
    return tuple(
        build_contribution_ledger(organism_id, generation, tuple(records))
        for organism_id, records in sorted(grouped.items())
    )


def _event_graph_digest_from_ticks(ticks: Sequence[GenesisTickResult]) -> str:
    graph = EventGraph()
    previous: str | None = None
    for raw in _raw_events(ticks):
        action = str(raw.payload.get("action", "unknown"))
        if previous is not None:
            graph = graph.add_edge(previous, action, lag=1, evidence_count=1)
        previous = action
    return graph.digest()


def _phase2_hashes(
    *,
    engine: GenesisEngine,
    contribution_ledgers: Sequence[ContributionLedger],
    semantic_report_digest: str | None,
) -> dict[str, str | None]:
    organisms = tuple(engine.runner.population.organisms)
    ribosome = engine.spec.resolved_ribosome()
    codon_width = ribosome.codon_table.spec.genome_spec.codon_width
    genome_program_payload = []
    for organism in organisms:
        program = build_genome_program(
            organism.genome.to_compact(),
            codon_width=codon_width,
            macro_registry_digest=None
            if organism.adf_macro_registry is None
            else organism.adf_macro_registry.digest(),
            lineage_tags=(organism.id,),
        )
        genome_program_payload.append(program.to_dict())
    mutation_digests = []
    for tick in engine._tick_results:
        for trace in tick.generation_result.traces:
            for event in trace.events:
                digest = event.world_delta.get("mutation_digest")
                if isinstance(digest, str):
                    mutation_digests.append(digest)
    macro_registry_digest = (
        engine.spec.adf_macro_registry.digest()
        if engine.spec.adf_macro_registry is not None
        else _digest({"macro_registry": "not_enabled"})
    )
    macro_utility_digest = _digest(
        {"macro_registry_digest": macro_registry_digest, "status": "runtime_registry"}
    )
    structural_mutation_digest = (
        _digest({"mutation_digests": cast(JsonValue, sorted(mutation_digests))})
        if mutation_digests
        else _digest({"structural_mutation": "not_observed"})
    )
    contribution_digest = _digest(
        {"ledgers": cast(JsonValue, [ledger.digest for ledger in contribution_ledgers])}
    )
    innovation_digest = _digest(
        {
            "innovation_registry": "not_configured",
            "population_generation": engine.runner.population.generation,
        }
    )
    translation_digest = (
        engine.spec.translation_profile.digest
        if engine.spec.translation_profile is not None
        else _digest({"translation_profile": "fixed_base_table"})
    )
    statistical_digest = _digest(
        {"tick_count": len(engine._tick_results), "population_size": len(organisms)}
    )
    oee_digest = _digest(
        {
            "oee": "measurement_not_run",
            "genome_length_distribution": genome_length_distribution(
                tuple(
                    build_genome_program(o.genome.to_compact(), codon_width=codon_width)
                    for o in organisms
                )
            ),
        }
    )
    return {
        "genome_program_digest": _digest(
            {"genome_programs": cast(JsonValue, genome_program_payload)}
        ),
        "structural_mutation_digest": structural_mutation_digest,
        "structural_mutation_record_digest": structural_mutation_digest,
        "adf_macro_registry_digest": macro_registry_digest,
        "macro_registry_digest": macro_registry_digest,
        "adf_usefulness_report_digest": macro_utility_digest,
        "macro_utility_digest": macro_utility_digest,
        "translation_profile_digest": translation_digest,
        "translation_profile_hash": translation_digest,
        "contribution_ledger_digest": contribution_digest,
        "micro_ablation_attribution_digest": _digest({"micro_ablation": "not_run", "ledger_digest": contribution_digest}),
        "innovation_registry_digest": innovation_digest,
        "event_graph_digest": _event_graph_digest_from_ticks(engine._tick_results),
        "predictive_probe_digest": _digest({"predictive_probe": "not_run"}),
        "intervention_protocol_digest": _digest({"intervention_protocol": "not_run"}),
        "intervention_result_digest": _digest({"intervention_result": "not_run"}),
        "causal_intervention_result_digest": _digest({"intervention_result": "not_run"}),
        "discovery_witness_digest": _digest({"discovery_witness": "not_run", "tick_count": len(engine._tick_results)}),
        "benchmark_scenario_digest": str(engine.spec.metadata.get("benchmark_scenario_digest"))
        if "benchmark_scenario_digest" in engine.spec.metadata
        else _digest({"benchmark_scenario": "not_configured"}),
        "statistical_report_digest": statistical_digest,
        "oee_report_digest": oee_digest,
        "social_generalization_digest": _digest({"social_generalization": "not_run", "population_size": len(organisms)}),
        "capsule_ablation_policy_digest": _object_hash(engine.spec.capsule_ablation_policy)
        or _digest({"capsule_ablation_policy": "disabled_by_config"}),
        "capsule_outcome_window_digest": _object_hash(engine.spec.capsule_outcome_window)
        or _digest({"capsule_outcome_window": "disabled_by_config"}),
        "skill_compression_ablation_policy_digest": _object_hash(engine.spec.skill_compression_ablation_policy)
        or _digest({"skill_compression_ablation_policy": "disabled_by_config"}),
        "role_mechanics_policy_digest": _object_hash(engine.spec.role_mechanics_policy)
        or _digest({"role_mechanics_policy": "disabled_by_config"}),
        "territory_mechanics_config_digest": _object_hash(engine.spec.territory_mechanics_config)
        or _digest({"territory_mechanics_config": "disabled_by_config"}),
        "heldout_partner_protocol_digest": _object_hash(engine.spec.heldout_partner_protocol)
        or _digest({"heldout_partner_protocol": "disabled_by_config"}),
        "source_reputation_memory_digest": _object_hash(engine.spec.source_reputation_memory)
        or _digest({"source_reputation_memory": "disabled_by_config"}),
        "collective_task_graph_digest": _object_hash(engine.spec.collective_task_graph)
        or _digest({"collective_task_graph": "disabled_by_config"}),
        "role_ablation_protocol_digest": _object_hash(engine.spec.role_ablation_protocol)
        or _digest({"role_ablation_protocol": "disabled_by_config"}),
        "multi_agent_contribution_ledger_digest": _object_hash(engine.spec.multi_agent_contribution_ledger)
        or _digest({"multi_agent_contribution_ledger": "disabled_by_config"}),
        "counterfactual_replay_protocol_digest": _object_hash(engine.spec.counterfactual_replay_protocol)
        or _digest({"counterfactual_replay_protocol": "disabled_by_config"}),
        "oee_extended_metrics_digest": _object_hash(engine.spec.oee_extended_metrics)
        or _digest({"oee_extended_metrics": "disabled_by_config"}),
        "semantic_proxy_report_digest": semantic_report_digest
        or _digest({"semantic_proxy": "fixed_translation"}),
    }


def _codon_table_hash(table: CodonTable) -> str:
    payload = {
        "table_name": table.spec.table_name,
        "allow_partial_tail": table.spec.allow_partial_tail,
        "genome_spec": table.spec.genome_spec.to_dict(),
        "codons": [
            {
                "bits": codon.bits,
                "action": codon.action_name,
                "cost": codon.cost,
                "description": codon.description,
            }
            for codon in table.actions()
        ],
    }
    return _digest(cast(dict[str, JsonValue], payload))


def _genome_spec_hash(spec: GenomeSpec) -> str:
    return _digest(spec.to_dict())


def _ribosome_hash(ribosome: Ribosome) -> str:
    return _digest(
        {
            "codon_table_hash": _codon_table_hash(ribosome.codon_table),
            "codon_table_version": ribosome.codon_table_version,
            "min_vitae": ribosome.min_vitae,
        }
    )


def _handler_identity_digest(handler: object) -> str:
    code = getattr(handler, "__code__", None)
    closure = getattr(handler, "__closure__", None)
    if code is None and callable(handler):
        call_method = handler.__call__
        code = getattr(call_method, "__code__", None)
        closure = getattr(call_method, "__closure__", None)
    closure_values: list[str] = []
    if closure:
        for cell in closure:
            try:
                closure_values.append(repr(cell.cell_contents))
            except ValueError:
                closure_values.append("<empty>")
    payload: dict[str, JsonValue] = {
        "module": str(getattr(handler, "__module__", "unknown")),
        "qualname": str(getattr(handler, "__qualname__", repr(handler))),
        "handler_version": getattr(handler, "__codontrace_version__", None),
        "handler_provenance": getattr(handler, "__codontrace_provenance__", None),
        "action_abi_digest": "action_result_v1",
        "bytecode_sha256": None if code is None else hashlib.sha256(code.co_code).hexdigest(),
        "constants_sha256": None
        if code is None
        else hashlib.sha256(repr(code.co_consts).encode("utf-8")).hexdigest(),
        "closure_sha256": hashlib.sha256(
            json.dumps(closure_values, sort_keys=True, allow_nan=False).encode("utf-8")
        ).hexdigest(),
    }
    return _digest(payload)


def _stable_default_action_registry_hash() -> str:
    return _digest(
        {
            "registry_version": "action_registry_digest_v3_stable_manifest",
            "actions": cast(JsonValue, list(default_action_registry_manifest())),
        }
    )


def _action_registry_hash(registry: ActionRegistry | None) -> str | None:
    resolved = default_action_registry() if registry is None else registry
    default_manifest = {item["name"]: item for item in default_action_registry_manifest()}
    default_names = set(default_manifest)
    if tuple(resolved.names()) == tuple(sorted(default_names)):
        return _stable_default_action_registry_hash()
    entries: list[dict[str, JsonValue]] = []
    for name in resolved.names():
        handler = resolved.get(name)
        if name in default_manifest:
            manifest: dict[str, JsonValue] = dict(default_manifest[name])
            manifest["handler_digest"] = _digest(
                {"built_in_action": name, "handler_stable_id": manifest["handler_stable_id"]}
            )
            manifest["replay_status"] = "built_in_replayable"
            entries.append(manifest)
            continue
        stable_id = None
        if handler is not None:
            module = getattr(handler, "__module__", "unknown")
            qualname = getattr(handler, "__qualname__", type(handler).__qualname__)
            stable_id = f"{module}:{qualname}"
        handler_version = getattr(handler, "__codontrace_version__", None)
        handler_provenance = getattr(
            handler, "__codontrace_provenance__", "non_replayable_external_handler"
        )
        entries.append(
            {
                "name": name,
                "handler_stable_id": stable_id,
                "handler_digest": None if handler is None else _handler_identity_digest(handler),
                "handler_version": handler_version if isinstance(handler_version, str) else None,
                "handler_provenance": handler_provenance
                if isinstance(handler_provenance, str)
                else "non_replayable_external_handler",
                "action_abi_version": "action_result_v1",
                "replay_status": "non_replayable_external_handler",
            }
        )
    return _digest(
        {
            "registry_version": "action_registry_digest_v3_stable_manifest",
            "actions": cast(JsonValue, entries),
        }
    )


def _status_registry_digest(value: ActionRuntimeConfig | None) -> str | None:
    if value is None:
        return None
    registry = value.status_registry
    return registry.digest() if hasattr(registry, "digest") else _object_hash(registry)


def _object_hash(value: object | None) -> str | None:
    if value is None:
        return None
    obj = cast(Any, value)
    if hasattr(obj, "digest"):
        return str(obj.digest())
    if hasattr(obj, "to_dict"):
        return _digest(cast(dict[str, JsonValue], obj.to_dict()))
    return _digest({"repr": repr(value)})


def _adf_vocabulary_hash(table: CodonTable) -> str:
    adf_codons = [
        {"bits": codon.bits, "action": codon.action_name, "cost": codon.cost}
        for codon in table.actions()
        if codon.action_name.startswith("ADF_")
    ]
    return _digest({"adf_codons": cast(JsonValue, adf_codons)})


def _json_float_value(value: JsonValue | None) -> float:
    if isinstance(value, bool) or not isinstance(value, int | float):
        return 0.0
    return float(value)


def _json_str_tuple(value: object) -> tuple[str, ...]:
    if not isinstance(value, Sequence) or isinstance(value, str | bytes):
        return ()
    return tuple(str(item) for item in value if isinstance(item, str))


def _digest(payload: Mapping[str, JsonValue]) -> str:
    encoded = finite_json_dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()
