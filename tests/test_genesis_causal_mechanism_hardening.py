from __future__ import annotations

import pytest

import codontrace.genesis as genesis
from codontrace.genesis.canonical import canonical_digest
from codontrace.genesis.capsule_validation import (
    CapsuleAblationPolicy,
    CapsuleOutcomeWindow,
    CapsuleDelayedOutcomeRecord,
    PacketAblationPolicy,
    PacketOutcomeWindow,
)
from codontrace.genesis.memory import SignalMemoryCausalLinkRecord, SourceReputationMemory
from codontrace.genesis.birth import SkillCompressionAblationPolicy, ChildOutcomeAuditRecord
from codontrace.genesis.role import RoleMechanicsPolicy, TerritoryMechanicsConfig, TerritoryDefenseRecord
from codontrace.genesis.collective_intelligence import (
    CollectiveTaskSpec,
    CollectiveTaskNode,
    RoleDependencyEdge,
    CollectiveTaskGraph,
    JointTaskProgressRecord,
    RoleAblationProtocol,
)
from codontrace.genesis.generalization import HeldoutPartnerEvaluationProtocol, HeldoutPartnerEvaluationRecord
from codontrace.genesis.contribution_ledger import MultiAgentContributionRecord, MultiAgentContributionLedger, MultiAgentCreditLedger
from codontrace.genesis.intervention import CounterfactualReplayProtocol, CounterfactualReplayIntervention, CounterfactualReplayResult
from codontrace.genesis.open_endedness import OEEExtendedMetrics, OpenEndednessMetrics
from codontrace.genesis.replay_integrity import replay_digest_class_policies


def d(name: str) -> str:
    return canonical_digest({"name": name})


def test_capsule_ablation_policy_uses_capsule_canonical_runtime_not_parallel_packet() -> None:
    policy = CapsuleAblationPolicy(
        enable_capsule_transfer=True,
        enable_capsule_utility_scoring=False,
        enable_source_fitness_weighting=False,
        enable_signal_memory_link=True,
        enable_capsule_behavior_update=False,
    )
    assert PacketAblationPolicy is CapsuleAblationPolicy
    assert genesis.PacketAblationPolicy is genesis.CapsuleAblationPolicy
    assert policy.enable_packet_utility is False
    assert policy.enable_packet_source_fitness is False
    assert policy.enable_packet_behavior_update is False
    assert policy.disabled_controls == (
        "disable_capsule_utility_scoring",
        "disable_source_fitness_weighting",
        "disable_capsule_behavior_update",
    )
    assert policy.digest().startswith("capsule_ablation_policy:")
    assert policy.claim_eligible is False


def test_capsule_outcome_window_records_delayed_utility_with_control() -> None:
    window = CapsuleOutcomeWindow(window_ticks=7)
    assert PacketOutcomeWindow is CapsuleOutcomeWindow
    record = CapsuleDelayedOutcomeRecord(
        capsule_id="cap-1",
        target_organism_id="org-2",
        signal_seen_tick=3,
        outcome_start_tick=3,
        outcome_end_tick=10,
        window_digest=window.digest(),
        policy_digest=CapsuleAblationPolicy().digest(),
        fitness_delta=0.2,
        memory_reuse_delta=1.0,
        compared_control_digest=d("control"),
    )
    assert record.claim_eligible is True
    assert record.to_dict()["record_digest"] == record.digest()
    with pytest.raises(ValueError):
        CapsuleOutcomeWindow(window_ticks=0)


def test_signal_memory_causal_link_requires_ordered_chain_and_behavior_change() -> None:
    link = SignalMemoryCausalLinkRecord(
        signal_id="sig-1",
        capsule_id="cap-1",
        target_organism_id="org-1",
        signal_seen_tick=1,
        memory_write_tick=2,
        memory_read_tick=5,
        action_after_memory="move_to_resource",
        behavior_digest_before=d("before"),
        behavior_digest_after=d("after"),
        reward_delta=0.5,
        selection_delta=0.1,
        memory_record_digest=d("memory"),
        action_record_digest=d("action"),
        control_digest=d("control"),
    )
    assert link.behavior_changed is True
    assert link.claim_eligible is True
    assert link.digest().startswith("signal_memory_link:")
    with pytest.raises(ValueError):
        SignalMemoryCausalLinkRecord(
            signal_id="sig-1", capsule_id="cap-1", target_organism_id="org-1",
            signal_seen_tick=5, memory_write_tick=4, memory_read_tick=6,
            action_after_memory="a", behavior_digest_before=d("b"), behavior_digest_after=d("c"), reward_delta=0.0,
        )


def test_skill_compression_policy_and_child_outcome_audit_are_claim_gated() -> None:
    policy = SkillCompressionAblationPolicy(mode="shuffle_compressed_skill")
    assert policy.negative_control is True
    assert policy.claim_eligible is False
    audit = ChildOutcomeAuditRecord(
        child_id="child",
        parent_id="parent",
        compression_digest=d("compression"),
        inherited_skill_count=2,
        inherited_adf_count=1,
        child_survival_ticks=10,
        child_fitness_delta=0.4,
        child_memory_reuse_count=2,
        child_reproduction_success=False,
        compared_to_uncompressed_control=True,
        control_digest=d("uncompressed_sibling"),
    )
    assert audit.claim_eligible is True
    assert audit.digest().startswith("child_outcome:")
    with pytest.raises(ValueError):
        SkillCompressionAblationPolicy(enabled=False, mode="full_compression")


def test_role_mechanics_and_territory_are_soft_policy_not_success_forcers() -> None:
    role_policy = RoleMechanicsPolicy()
    assert role_policy.enable_role_task_bonus is False
    assert role_policy.hard_codes_success is False
    territory = TerritoryMechanicsConfig(enabled=True, home_cells=("2:3", "1:1"))
    assert territory.home_cells == ("1:1", "2:3")
    record = TerritoryDefenseRecord(
        organism_id="guard",
        role_label="home_guard",
        tick=8,
        home_cell="1:1",
        hazard_blocked=True,
        group_loss_delta_without_guard=0.3,
        evidence_digest=d("defense"),
    )
    assert record.claim_eligible is True


def test_collective_task_graph_and_role_ablation_protocol_require_multi_agent_dependencies() -> None:
    spec = CollectiveTaskSpec(
        task_id="guarded_resource_transport",
        requires_multiple_agents=True,
        required_roles=("scout", "carrier", "guard"),
    )
    scout = CollectiveTaskNode("find_path", "scout")
    carrier = CollectiveTaskNode("carry_resource", "carrier")
    graph = CollectiveTaskGraph(
        task_spec=spec,
        nodes=(carrier, scout),
        edges=(RoleDependencyEdge("find_path", "carry_resource"),),
        single_agent_baseline_digest=d("single_agent"),
    )
    assert graph.supports_collective_claim is True
    progress = JointTaskProgressRecord(
        graph_digest=graph.digest(),
        tick=11,
        contributing_agents=("a", "b"),
        completed_node_ids=("find_path", "carry_resource"),
        progress_delta=1.0,
        evidence_digest=d("joint"),
    )
    assert progress.claim_eligible is True
    assert RoleAblationProtocol(("guard",)).digest().startswith("role_ablation_protocol:")


def test_heldout_partner_protocol_detects_familiar_unfamiliar_generalization_without_leakage() -> None:
    protocol = HeldoutPartnerEvaluationProtocol(train_partner_pool="A", test_partner_pool="B")
    record = HeldoutPartnerEvaluationRecord(
        protocol_digest=protocol.digest(),
        familiar_partner_digest=d("fam"),
        unfamiliar_partner_digest=d("unfam"),
        familiar_score=0.6,
        unfamiliar_score=0.55,
    )
    assert protocol.claim_eligible_by_design is True
    assert record.claim_eligible is True
    assert record.generalization_delta == -0.05
    with pytest.raises(ValueError):
        HeldoutPartnerEvaluationProtocol(train_partner_pool="A", test_partner_pool="A")


def test_multi_agent_contribution_ledger_tracks_indirect_packet_guard_and_memory_credit() -> None:
    assert MultiAgentCreditLedger is MultiAgentContributionLedger
    ledger = MultiAgentContributionLedger((
        MultiAgentContributionRecord("guard", 1, guard_credit=0.4, indirect_reward=0.2),
        MultiAgentContributionRecord("sender", 1, packet_credit=0.3, memory_credit=0.1),
    ))
    assert ledger.aggregate_by_agent == (("guard", 0.6), ("sender", 0.4))
    assert ledger.digest().startswith("multi_agent_ledger:")


def test_counterfactual_replay_protocol_is_rng_preserving_and_claim_gated() -> None:
    protocol = CounterfactualReplayProtocol(
        base_replay_digest=d("base_replay"),
        intervention_type="disable_capsule_utility",
        target_tick=12,
    )
    assert CounterfactualReplayIntervention is CounterfactualReplayProtocol
    result = CounterfactualReplayResult(
        protocol_digest=protocol.digest(),
        base_replay_digest=d("base_replay"),
        counterfactual_replay_digest=d("counterfactual"),
        outcome_delta=-0.25,
        rng_stream_preserved=True,
        intervention_manifest_digest=d("manifest"),
    )
    assert result.claim_eligible is True
    with pytest.raises(ValueError):
        CounterfactualReplayProtocol(base_replay_digest=d("base"), intervention_type="unknown", target_tick=1)


def test_oee_extended_metrics_requires_more_than_novelty_for_claims() -> None:
    weak = OEEExtendedMetrics(
        novelty_accumulation=1.0,
        complexity_growth=0.0,
        adaptive_success_accumulation=0.0,
        lineage_persistence=1.0,
        behavior_space_expansion=1.0,
        seed_count=2,
    )
    assert weak.claim_eligible is False
    assert weak.evidence_level == "descriptive_only"
    strong = OpenEndednessMetrics(
        novelty_accumulation=1.0,
        complexity_growth=0.4,
        adaptive_success_accumulation=0.3,
        lineage_persistence=0.5,
        behavior_space_expansion=0.7,
        learnability=0.2,
        seed_count=10,
        baseline_digest=d("baseline"),
        negative_control_digest=d("negative"),
    )
    assert strong.claim_eligible is True
    assert strong.digest().startswith("oee_extended:")


def test_new_mechanism_public_exports_and_replay_policy_are_registered() -> None:
    required = {
        "CapsuleAblationPolicy",
        "PacketAblationPolicy",
        "SignalMemoryCausalLinkRecord",
        "SkillCompressionAblationPolicy",
        "ChildOutcomeAuditRecord",
        "RoleMechanicsPolicy",
        "CollectiveTaskGraph",
        "HeldoutPartnerEvaluationProtocol",
        "MultiAgentContributionLedger",
        "CounterfactualReplayProtocol",
        "OEEExtendedMetrics",
    }
    for name in required:
        assert hasattr(genesis, name), name
        assert name in genesis.__all__, name
    policies = {policy.class_path for policy in replay_digest_class_policies()}
    for path in (
        "codontrace.genesis.capsule_validation.CapsuleDelayedOutcomeRecord",
        "codontrace.genesis.memory.SignalMemoryCausalLinkRecord",
        "codontrace.genesis.birth.ChildOutcomeAuditRecord",
        "codontrace.genesis.collective_intelligence.CollectiveTaskGraph",
        "codontrace.genesis.intervention.CounterfactualReplayResult",
        "codontrace.genesis.open_endedness.OEEExtendedMetrics",
    ):
        assert path in policies


def test_new_mechanism_policies_are_part_of_genesis_experiment_spec_digest_not_runner_only() -> None:
    base = genesis.GenesisExperimentSpec(seed=7, tick_count=1)
    heldout = HeldoutPartnerEvaluationProtocol(train_partner_pool="A", test_partner_pool="B")
    task_spec = CollectiveTaskSpec(
        task_id="guarded_transport",
        requires_multiple_agents=True,
        required_roles=("scout", "guard"),
        heldout_partner_protocol_digest=heldout.digest(),
    )
    graph = CollectiveTaskGraph(
        task_spec=task_spec,
        nodes=(
            CollectiveTaskNode("scan", "scout"),
            CollectiveTaskNode("protect", "guard"),
        ),
        edges=(RoleDependencyEdge("scan", "protect"),),
        single_agent_baseline_digest=d("single_agent_baseline"),
    )
    ledger = MultiAgentContributionLedger(
        (
            MultiAgentContributionRecord(
                organism_id="org-a",
                tick=1,
                direct_reward=1.0,
                indirect_reward=0.5,
                packet_credit=0.25,
                guard_credit=0.25,
                memory_credit=0.1,
            ),
        )
    )
    counterfactual = CounterfactualReplayProtocol(
        base_replay_digest=d("base_replay"),
        intervention_type="disable_capsule_utility",
        target_tick=1,
        preserve_rng_stream=True,
    )
    oee = OEEExtendedMetrics(
        novelty_accumulation=1.0,
        complexity_growth=1.0,
        adaptive_success_accumulation=1.0,
        lineage_persistence=1.0,
        behavior_space_expansion=1.0,
        learnability=1.0,
        seed_count=10,
        baseline_digest=d("oee_baseline"),
        negative_control_digest=d("oee_negative_control"),
    )
    hardened = genesis.GenesisExperimentSpec(
        seed=7,
        tick_count=1,
        capsule_ablation_policy=CapsuleAblationPolicy(enable_capsule_utility_scoring=False),
        capsule_outcome_window=CapsuleOutcomeWindow(window_ticks=3),
        skill_compression_ablation_policy=SkillCompressionAblationPolicy(mode="capacity_only"),
        role_mechanics_policy=RoleMechanicsPolicy(max_bias_strength=0.1),
        territory_mechanics_config=TerritoryMechanicsConfig(enabled=True, home_cells=("0:0",)),
        heldout_partner_protocol=heldout,
        source_reputation_memory=SourceReputationMemory((("sender", 0.2),)),
        collective_task_graph=graph,
        role_ablation_protocol=RoleAblationProtocol(("guard",)),
        multi_agent_contribution_ledger=ledger,
        counterfactual_replay_protocol=counterfactual,
        oee_extended_metrics=oee,
    )
    payload = hardened.to_dict()
    for key in (
        "capsule_ablation_policy_hash",
        "capsule_outcome_window_hash",
        "skill_compression_ablation_policy_hash",
        "role_mechanics_policy_hash",
        "territory_mechanics_config_hash",
        "heldout_partner_protocol_hash",
        "source_reputation_memory_hash",
        "collective_task_graph_hash",
        "role_ablation_protocol_hash",
        "multi_agent_contribution_ledger_hash",
        "counterfactual_replay_protocol_hash",
        "oee_extended_metrics_hash",
    ):
        assert payload[key] not in (None, "")
    result = genesis.GenesisEngine.from_spec(hardened).run_ticks()
    for key in (
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
    ):
        assert result.manifest.runtime_hashes[key] not in (None, "")
        assert result.manifest.protocol_statuses[f"phase2.{key}.status"] in {
            "configured_digest_only",
            "candidate_evidence",
        }
    assert result.manifest.protocol_statuses["phase2.oee_extended_metrics_digest.status"] == "candidate_evidence"
    assert base.digest() != hardened.digest()
