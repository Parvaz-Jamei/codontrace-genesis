from codontrace.genesis import (
    MultiAgentCreditLedger,
    OpenEndednessMetrics,
    PacketAblationPolicy,
    PacketOutcomeWindow,
    canonical_digest,
)
from codontrace.genesis.birth import SkillCompressionAblationPolicy
from codontrace.genesis.capsule_validation import CapsuleAblationPolicy, CapsuleOutcomeWindow
from codontrace.genesis.collective_intelligence import (
    CollectiveTaskGraph,
    CollectiveTaskNode,
    CollectiveTaskSpec,
    RoleAblationProtocol,
    RoleDependencyEdge,
)
from codontrace.genesis.contribution_ledger import MultiAgentContributionLedger
from codontrace.genesis.engine import GenesisEngine, GenesisExperimentSpec
from codontrace.genesis.generalization import HeldoutPartnerEvaluationProtocol
from codontrace.genesis.intervention import CounterfactualReplayIntervention, CounterfactualReplayProtocol
from codontrace.genesis.memory import SourceReputationMemory
from codontrace.genesis.open_endedness import OEEExtendedMetrics
from codontrace.genesis.role import RoleMechanicsPolicy, TerritoryMechanicsConfig


def test_causal_mechanism_specs_are_canonical_aliases_not_parallel_runtime() -> None:
    assert PacketAblationPolicy is CapsuleAblationPolicy
    assert PacketOutcomeWindow is CapsuleOutcomeWindow
    assert MultiAgentCreditLedger is MultiAgentContributionLedger
    assert CounterfactualReplayIntervention is CounterfactualReplayProtocol
    assert OpenEndednessMetrics is OEEExtendedMetrics


def test_causal_mechanism_configs_are_manifest_visible_and_claim_safe() -> None:
    task_spec = CollectiveTaskSpec(
        task_id="guarded_resource_transport",
        requires_multiple_agents=True,
        required_roles=("scout", "guard"),
    )
    collective_graph = CollectiveTaskGraph(
        task_spec=task_spec,
        nodes=(
            CollectiveTaskNode("scout_node", "scout"),
            CollectiveTaskNode("guard_node", "guard"),
        ),
        edges=(RoleDependencyEdge("scout_node", "guard_node", "signal"),),
        single_agent_baseline_digest=canonical_digest({"baseline": "single_agent"}),
    )
    assert collective_graph.supports_collective_claim

    spec = GenesisExperimentSpec(
        seed=7,
        tick_count=2,
        population_max=3,
        capsule_ablation_policy=CapsuleAblationPolicy(enable_capsule_utility_scoring=False),
        capsule_outcome_window=CapsuleOutcomeWindow(window_ticks=3),
        skill_compression_ablation_policy=SkillCompressionAblationPolicy(mode="capacity_only"),
        role_mechanics_policy=RoleMechanicsPolicy(max_bias_strength=0.1),
        territory_mechanics_config=TerritoryMechanicsConfig(enabled=True, home_cells=("0:0",)),
        heldout_partner_protocol=HeldoutPartnerEvaluationProtocol(train_partner_pool="A", test_partner_pool="B"),
        source_reputation_memory=SourceReputationMemory((("sender", 0.2),)),
        collective_task_graph=collective_graph,
        role_ablation_protocol=RoleAblationProtocol(("guard",)),
        multi_agent_contribution_ledger=MultiAgentContributionLedger(()),
        counterfactual_replay_protocol=CounterfactualReplayProtocol(
            base_replay_digest=canonical_digest({"base": 1}),
            intervention_type="disable_capsule_utility",
            target_tick=2,
        ),
        oee_extended_metrics=OEEExtendedMetrics(
            novelty_accumulation=0.3,
            complexity_growth=0.2,
            adaptive_success_accumulation=0.1,
            lineage_persistence=0.4,
            behavior_space_expansion=0.5,
            learnability=0.2,
            seed_count=2,
        ),
    )

    result = GenesisEngine.from_spec(spec).run_ticks()
    required_runtime_hashes = (
        "capsule_ablation_policy_digest",
        "capsule_outcome_window_digest",
        "skill_compression_ablation_policy_digest",
        "role_mechanics_policy_digest",
        "territory_mechanics_config_digest",
        "heldout_partner_protocol_digest",
        "source_reputation_memory_digest",
        "collective_task_graph_digest",
        "role_ablation_protocol_digest",
        "multi_agent_contribution_ledger_digest",
        "counterfactual_replay_protocol_digest",
        "oee_extended_metrics_digest",
    )
    missing = [name for name in required_runtime_hashes if not result.manifest.runtime_hashes.get(name)]
    assert missing == []

    for name in required_runtime_hashes:
        status = result.manifest.protocol_statuses.get(f"phase2.{name}.status")
        assert status in {"configured_digest_only", "candidate_evidence"}

    # The public evidence manifest must agree with the canonical run manifest,
    # so downstream reports cannot silently ignore the new engine-level knobs.
    assert result.evidence_manifest.to_dict()["config_digest"] == result.manifest.config_hash
