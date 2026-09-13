"""Integrated Living World (ILW) scaffolding.

ILW-0: integration DAG, fail-first orphan subsystem checks, event consumer.
ILW-1: shared WorldSpec, run-scoped scheduler, append-only event ledger, and
deterministic seed namespace.
ILW-2: full genome→lineage causal chain in a dual-resource world under one
run_id / WorldSpec / scheduler / ledger.
ILW-3: integrated smoke with replay, conservation, 100% required-edge coverage;
no scientific claim / no ClaimGate ladder promotion.
ILW-4: locked preregistration (POM patterns, interactions, scale/horizon/seeds,
stop rules, Morris→DSD plan) + pilot harness stub (fail-first confirmatory block).
ILW-pilot / ILW-5: S2 pilot gates artifact; confirmatory campaign harness (smoke cells).
ILW-6: exploratory MODES-style phylogeny hooks, organism↔capsule genealogy join,
novelty + learnability probes (no ClaimGate promotion / no CCE / no intelligence).

Claim ceiling stays ``runtime_observation``; scientific name is
``integrated eco-evolutionary runtime`` (not intelligence / AGI / CI).
Adapters must not inject fixture outcomes.
"""

from __future__ import annotations

from codontrace.genesis.ilw.adapter_honesty import (
    FORBIDDEN_OUTCOME_INJECTION_KEYS,
    AdapterHonestyError,
    assert_claim_ceiling_runtime_observation,
    assert_no_fixture_outcome_injection,
)
from codontrace.genesis.ilw.chain_runtime import (
    CapsuleRecord,
    IlwChainError,
    IlwChainRuntime,
    IlwOrganism,
)
from codontrace.genesis.ilw.conservation import (
    ConservationReport,
    IlwConservationError,
    check_conservation,
)
from codontrace.genesis.ilw.dag import (
    CLAIM_CEILING,
    REQUIRED_TELEMETRY_FIELDS,
    SCIENTIFIC_NAME,
    IntegrationDAG,
    IntegrationDAGError,
    load_integration_dag,
)
from codontrace.genesis.ilw.dual_resource_world import DualResourceWorld, DualResourceWorldError
from codontrace.genesis.ilw.event_consumer import (
    OrphanEventError,
    RegisteredEventConsumer,
)
from codontrace.genesis.ilw.event_ledger import (
    LEDGER_CORE_REQUIRED_FIELDS,
    EventLedger,
    EventLedgerError,
    LedgerEvent,
)
from codontrace.genesis.ilw.integrated_smoke import (
    IlwSmokeError,
    IlwSmokeReport,
    run_integrated_smoke,
)
from codontrace.genesis.ilw.knockouts import IlwKnockoutError, KnockoutConfig
from codontrace.genesis.ilw.orphan import (
    OrphanSubsystemError,
    SubsystemRegistry,
)
from codontrace.genesis.ilw.prereg import (
    CONFIRMATORY_HELD_OUT_SEEDS,
    DOE_PLAN,
    EDGE_KNOCKOUTS,
    FORBIDDEN_CLAIM_LABELS,
    HORIZON_DEFINITIONS,
    INTERACTIONS_TO_ESTIMATE,
    MESOUDI_CCE_CRITERIA,
    PILOT_SEEDS,
    POM_ACCEPTANCE_PATTERNS,
    PREREG_RELATIVE_PATH,
    PREREG_VERSION,
    SCALE_LADDER,
    SHAM_YOKED_CONTROLS,
    SMOKE_SEEDS,
    STOP_RULES,
    IlwPreregError,
    PilotGateError,
    PilotGateStatus,
    PilotHarness,
    assert_no_forbidden_claims,
    assert_prereg_claim_ceiling,
    assert_seed_policy_disjoint,
    ilw_prereg_design_digest,
    ilw_prereg_document_digest,
    locked_design_dict,
    summarize_prereg,
)
from codontrace.genesis.ilw.scheduler import IlwScheduler, IlwSchedulerError
from codontrace.genesis.ilw.seed_namespace import SeedNamespace, SeedNamespaceError
from codontrace.genesis.ilw.world_spec import WORLD_SPEC_SCHEMA, WorldSpec, WorldSpecError


from codontrace.genesis.ilw.campaign import (
    CampaignCell,
    CampaignCellResult,
    IlwCampaignError,
    build_ablation_cells,
    build_interaction_screening_cells,
    build_s4_scale_cells,
    default_partial_artifact_path,
    default_smoke_artifact_path,
    enumerate_campaign_design,
    run_campaign_cell,
    run_ilw5_partial,
    run_ilw5_smoke,
    select_partial_campaign_cells,
)

from codontrace.genesis.ilw.pilot import (
    IlwPilotError,
    PilotCampaignReport,
    PomPatternRecord,
    SeedPilotResult,
    default_artifact_path,
    evaluate_pilot_gates,
    evaluate_pom_patterns,
    load_pilot_gates,
    run_s2_pilot,
    run_seed_pilot,
    unlock_harness_from_artifact,
    unlocked_harness_or_raise,
)


from codontrace.genesis.ilw.exploratory import (
    ILW6_FORBIDDEN_PROMOTIONS,
    ILW6_LIMITATIONS,
    ILW6_SCHEMA,
    ILW6_STATUS,
    CapsuleGenealNode,
    Ilw6ExploratoryError,
    Ilw6ExploratoryReport,
    LearnabilityProbe,
    ModesStylePoint,
    OrganismPhyloNode,
    PhyloJoinRow,
    build_capsule_genealogy,
    build_organism_phylogeny,
    join_organism_capsule_phylogenies,
    learnability_probe,
    modes_style_novelty_probe,
    run_ilw6_exploratory,
    run_ilw6_exploratory_smoke,
)

__all__ = [
    "CLAIM_CEILING",
    "FORBIDDEN_OUTCOME_INJECTION_KEYS",
    "LEDGER_CORE_REQUIRED_FIELDS",
    "REQUIRED_TELEMETRY_FIELDS",
    "SCIENTIFIC_NAME",
    "WORLD_SPEC_SCHEMA",
    "AdapterHonestyError",
    "CapsuleRecord",
    "ConservationReport",
    "DualResourceWorld",
    "DualResourceWorldError",
    "EventLedger",
    "EventLedgerError",
    "IlwChainError",
    "IlwChainRuntime",
    "IlwConservationError",
    "IlwKnockoutError",
    "IlwOrganism",
    "IlwScheduler",
    "IlwSchedulerError",
    "IlwSmokeError",
    "IlwSmokeReport",
    "IntegrationDAG",
    "IntegrationDAGError",
    "KnockoutConfig",
    "LedgerEvent",
    "OrphanEventError",
    "OrphanSubsystemError",
    "PILOT_SEEDS",
    "POM_ACCEPTANCE_PATTERNS",
    "PREREG_RELATIVE_PATH",
    "PREREG_VERSION",
    "SCALE_LADDER",
    "SHAM_YOKED_CONTROLS",
    "SMOKE_SEEDS",
    "STOP_RULES",
    "CONFIRMATORY_HELD_OUT_SEEDS",
    "DOE_PLAN",
    "EDGE_KNOCKOUTS",
    "FORBIDDEN_CLAIM_LABELS",
    "HORIZON_DEFINITIONS",
    "INTERACTIONS_TO_ESTIMATE",
    "MESOUDI_CCE_CRITERIA",
    "IlwPreregError",
    "PilotGateError",
    "PilotGateStatus",
    "PilotHarness",
    "RegisteredEventConsumer",
    "SeedNamespace",
    "SeedNamespaceError",
    "SubsystemRegistry",
    "WorldSpec",
    "WorldSpecError",
    "assert_claim_ceiling_runtime_observation",
    "assert_no_fixture_outcome_injection",
    "assert_no_forbidden_claims",
    "assert_prereg_claim_ceiling",
    "assert_seed_policy_disjoint",
    "check_conservation",
    "ilw_prereg_design_digest",
    "ilw_prereg_document_digest",
    "load_integration_dag",
    "locked_design_dict",
    "run_integrated_smoke",
    "summarize_prereg",
    "IlwPilotError",
    "PilotCampaignReport",
    "PomPatternRecord",
    "SeedPilotResult",
    "default_artifact_path",
    "evaluate_pilot_gates",
    "evaluate_pom_patterns",
    "load_pilot_gates",
    "run_s2_pilot",
    "run_seed_pilot",
    "unlock_harness_from_artifact",
    "unlocked_harness_or_raise",
    "CampaignCell",
    "CampaignCellResult",
    "IlwCampaignError",
    "build_ablation_cells",
    "build_interaction_screening_cells",
    "build_s4_scale_cells",
    "default_smoke_artifact_path",
    "enumerate_campaign_design",
    "run_campaign_cell",
    "run_ilw5_partial",
    "run_ilw5_smoke",
    "select_partial_campaign_cells",
    "default_partial_artifact_path",
    "ILW6_FORBIDDEN_PROMOTIONS",
    "ILW6_LIMITATIONS",
    "ILW6_SCHEMA",
    "ILW6_STATUS",
    "CapsuleGenealNode",
    "Ilw6ExploratoryError",
    "Ilw6ExploratoryReport",
    "LearnabilityProbe",
    "ModesStylePoint",
    "OrganismPhyloNode",
    "PhyloJoinRow",
    "build_capsule_genealogy",
    "build_organism_phylogeny",
    "join_organism_capsule_phylogenies",
    "learnability_probe",
    "modes_style_novelty_probe",
    "run_ilw6_exploratory",
    "run_ilw6_exploratory_smoke",
]
