"""Experiment spec, engine config, and generation-boundary observer protocol.

Extracted from ``codontrace.engine`` so configuration and domain-free observer
seams have a named module boundary. Digests go through
``codontrace.engine_digest`` and must remain byte-stable.
See ``docs/ENGINE_REPLAY_CONTRACT.md``.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Protocol


from codontrace._types import JsonValue
from codontrace.actions import (
    ActionRegistry,
    ActionRuntimeConfig,
)
from codontrace.codon import CodonTable
from codontrace.engine_digest import (
    _action_registry_hash,
    _codon_table_hash,
    _digest,
    _genome_spec_hash,
    _object_hash,
    _ribosome_hash,
    _status_registry_digest,
)
from codontrace.genesis.adf_runtime import (
    ADFExecutionPolicy,
    ADFMacroRegistry,
)
from codontrace.genesis.birth import SkillCompressionAblationPolicy
from codontrace.genesis.capsule import CapsuleTransferConfig
from codontrace.genesis.capsule_validation import (
    CapsuleAblationPolicy,
    CapsuleOutcomeWindow,
)
from codontrace.genesis.causal_graph import CausalGraphConfig
from codontrace.genesis.collective_intelligence import (
    CollectiveTaskGraph,
    RoleAblationProtocol,
)
from codontrace.genesis.contribution_ledger import MultiAgentContributionLedger
from codontrace.genesis.evidence_validation import EvidenceValidationContext
from codontrace.genesis.generalization import HeldoutPartnerEvaluationProtocol
from codontrace.genesis.intervention import CounterfactualReplayProtocol
from codontrace.genesis.memory import (
    EpisodicMemoryConfig,
    SourceReputationMemory,
)
from codontrace.genesis.open_endedness import OEEExtendedMetrics
from codontrace.genesis.population import (
    MutationConfig,
    PopulationConfigs,
    ReproductionConfig,
)
from codontrace.genesis.quality_diversity import QDArchiveConfig
from codontrace.genesis.ribosome import Ribosome
from codontrace.genesis.role import (
    RoleMechanicsPolicy,
    TerritoryMechanicsConfig,
)
from codontrace.genesis.rules import ApprovedRuleSet
from codontrace.genesis.selection import EvolutionConfig
from codontrace.genesis.structural_mutation import StructuralMutationConfig
from codontrace.genesis.substrate import ElementGrid
from codontrace.genesis.translation_profile import (
    TranslationPolicy,
    TranslationProfile,
)
from codontrace.specs import GenomeSpec


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


class GenerationBoundaryObserver(Protocol):
    """Domain-free hook: one call per completed generation after ATP/bolus boundary.

    Signature is generation_index only. Keep domain-specific payload out of the
    general engine kernel; attach domain measurements in env/plugin callers.
    """

    def __call__(self, *, generation_index: int) -> None: ...


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


__all__ = [
    "GenesisEngineConfig",
    "GenerationBoundaryObserver",
    "GenesisExperimentSpec",
]
