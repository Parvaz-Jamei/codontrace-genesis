from __future__ import annotations

from codontrace.actions import default_action_registry
from codontrace.genesis.capsule import CapsuleTransferConfig
from codontrace.genesis.causal_graph import CausalGraphConfig
from codontrace.genesis.engine import GenesisEngine, GenesisEngineConfig, GenesisExperimentSpec
from codontrace.genesis.memory import EpisodicMemoryConfig
from codontrace.genesis.quality_diversity import BehaviorDescriptorSchema, QDArchiveConfig
from codontrace.genesis.review import ClaimReview, LLMReviewResult
from codontrace.genesis.rules import (
    ApprovalStatus,
    ApprovedRuleSet,
    HumanApprovalRecord,
    RuleProposal,
    RuleProposalSource,
    RuleSetDiff,
    RuleValidator,
    apply_approved_rule_set,
)


def _approved_rule_set() -> ApprovedRuleSet:
    proposal = RuleProposal(
        proposal_id="rule-polish-1",
        source=RuleProposalSource.HUMAN,
        diff=RuleSetDiff(
            modify=(
                {"target": "metadata", "key": "rule_mode", "value": "approved"},
                {"target": "engine_config", "field": "enable_capsules", "value": False},
            )
        ),
    )
    validation = RuleValidator().validate(proposal)
    approval = HumanApprovalRecord(
        proposal_digest=proposal.digest(),
        approver="test-human",
        status=ApprovalStatus.APPROVED,
        reason="unit test",
        validation_digest=validation.digest(),
    )
    return ApprovedRuleSet(proposal=proposal, validation=validation, approval=approval)


def test_experiment_spec_accepts_custom_runtime_hooks() -> None:
    schema = BehaviorDescriptorSchema(
        descriptor_names=("survival_ticks", "blocked_ratio"),
        bins_per_descriptor={"survival_ticks": 4, "blocked_ratio": 4},
        min_values={"survival_ticks": 0.0, "blocked_ratio": 0.0},
        max_values={"survival_ticks": 8.0, "blocked_ratio": 1.0},
    )
    spec = GenesisExperimentSpec(
        tick_count=1,
        action_registry=default_action_registry(),
        memory_config=EpisodicMemoryConfig(capacity=8),
        causal_graph_config=CausalGraphConfig(update_cost=0.25),
        capsule_transfer_config=CapsuleTransferConfig(enabled=True, read_radius=2),
        qd_archive_config=QDArchiveConfig(schema=schema),
    )
    result = GenesisEngine.from_spec(spec).run_ticks()

    assert result.manifest.config_hash == spec.digest()
    assert result.manifest.codon_table_hash == spec.to_dict()["codon_table_hash"]
    assert result.manifest.genome_spec_hash == spec.to_dict()["genome_spec_hash"]


def test_apply_approved_rule_set_updates_spec_and_manifest_rule_hash() -> None:
    approved = _approved_rule_set()
    original = GenesisExperimentSpec(
        tick_count=1, engine_config=GenesisEngineConfig(enable_capsules=True)
    )
    updated = apply_approved_rule_set(original, approved)

    assert isinstance(updated, GenesisExperimentSpec)
    assert updated.approved_rule_set is approved
    assert updated.metadata["rule_mode"] == "approved"
    assert updated.engine_config.enable_capsules is False

    result = GenesisEngine.from_spec(updated).run_ticks()
    assert result.manifest.rule_set_hash == approved.digest()
    assert result.manifest.config_hash == updated.digest()


def test_review_result_can_update_manifest_review_status() -> None:
    engine = GenesisEngine.from_spec(GenesisExperimentSpec(tick_count=1))
    initial = engine.run_ticks()
    request = engine.build_review_request()
    review = LLMReviewResult(
        request_digest=request.digest(),
        reviewer_id="schema-reviewer",
        findings=(),
        claim_review=ClaimReview(allowed=True, reason="ok"),
    )

    reviewed = engine.record_review_result(review)

    assert initial.manifest.review_status.status == "not_reviewed"
    assert reviewed.manifest.review_status.status == "accepted"
    assert reviewed.manifest.review_status.reviewer == "schema-reviewer"
    assert reviewed.manifest.review_status.decision_digest == review.digest()
