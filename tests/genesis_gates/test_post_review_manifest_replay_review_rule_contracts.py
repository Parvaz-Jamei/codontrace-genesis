from __future__ import annotations

from codontrace.actions import ActionContext, ActionResult, default_action_registry
from codontrace.genesis import BehaviorDescriptorBuilder, BehaviorMetricRegistry
from codontrace.genesis.artifacts import ReplayBundle, verify_replay_bundle
from codontrace.genesis.engine import (
    GenesisEngine,
    GenesisEngineConfig,
    GenesisExperimentSpec,
    apply_human_review,
    attach_review_result,
)
from codontrace.genesis.review import ClaimReview, HumanReviewDecision, LLMReviewResult
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


def _approved() -> ApprovedRuleSet:
    proposal = RuleProposal(
        proposal_id="post-review-rule",
        source=RuleProposalSource.HUMAN,
        diff=RuleSetDiff(modify=({"target": "metadata", "key": "mode", "value": "approved"},)),
    )
    validation = RuleValidator().validate(proposal)
    approval = HumanApprovalRecord(
        proposal.digest(), "human", ApprovalStatus.APPROVED, "ok", validation.digest()
    )
    return ApprovedRuleSet(proposal, validation, approval)


def test_manifest_uses_engine_claim_level_and_real_runtime_hashes() -> None:
    spec = GenesisExperimentSpec(
        tick_count=1,
        engine_config=GenesisEngineConfig(claim_level="custom_claim"),
    )
    result = GenesisEngine.from_spec(spec).run_ticks()
    assert result.manifest.requested_claim_level == "custom_claim"
    assert result.manifest.claim_level == "not_claimed"
    assert result.manifest.claim_gate_decision == "rejected_unknown_claim"
    assert result.manifest.runtime_hashes["engine_config_hash"]
    assert result.manifest.runtime_hashes["ribosome_hash"]
    assert result.manifest.runtime_hashes["population_config_hash"]


def test_manifest_hashes_change_when_runtime_specs_change() -> None:
    def custom_handler(ctx: ActionContext) -> ActionResult:
        return ActionResult(status="executed", position=ctx.position)

    base = GenesisEngine.from_spec(GenesisExperimentSpec(tick_count=1)).run_ticks()
    registry = default_action_registry().extend("CUSTOM_UI_ACTION", custom_handler)
    changed = GenesisEngine.from_spec(
        GenesisExperimentSpec(tick_count=1, action_registry=registry)
    ).run_ticks()

    assert base.manifest.config_hash != changed.manifest.config_hash
    assert (
        base.manifest.runtime_hashes["action_registry_hash"]
        != changed.manifest.runtime_hashes["action_registry_hash"]
    )


def test_approved_rule_set_can_update_experiment_spec_and_manifest_rule_hash() -> None:
    approved = _approved()
    original = GenesisExperimentSpec(tick_count=1)
    updated = apply_approved_rule_set(original, approved)
    assert isinstance(updated, GenesisExperimentSpec)
    assert updated.metadata["mode"] == "approved"
    assert updated.digest() != original.digest()
    result = GenesisEngine.from_spec(updated).run_ticks()
    assert result.manifest.rule_set_hash == approved.digest()


def test_review_result_updates_manifest_review_status_immutably_and_human_decision() -> None:
    engine = GenesisEngine.from_spec(GenesisExperimentSpec(tick_count=1))
    result = engine.run_ticks()
    request = engine.build_review_request()
    review = LLMReviewResult(
        request_digest=request.digest(),
        reviewer_id="reviewer",
        findings=(),
        claim_review=ClaimReview(allowed=True, reason="ok"),
    )
    reviewed = attach_review_result(result, review)
    assert result.manifest.review_status.status == "not_reviewed"
    assert reviewed.manifest.review_status.status == "reviewed_accepted"
    assert reviewed.external_review_record is not None
    decision = HumanReviewDecision("lead", "approved", "ok", review.digest())
    human = apply_human_review(reviewed, decision)
    assert human.manifest.review_status.status == "human_approved"
    assert human.manifest.review_status.decision_digest == decision.digest()


def test_replay_bundle_verification_passes_and_tamper_fails() -> None:
    result = GenesisEngine.from_spec(GenesisExperimentSpec(tick_count=2, seed=11)).run_ticks()
    ok = verify_replay_bundle(result.replay_bundle, result)
    assert ok.passed
    tampered = ReplayBundle(
        manifest=result.replay_bundle.manifest,
        snapshots=result.replay_bundle.snapshots,
        generation_digests=("tampered",) + result.replay_bundle.generation_digests[1:],
    )
    bad = verify_replay_bundle(tampered, result)
    assert not bad.passed
    assert "generation_digests_mismatch" in bad.issues


def test_run_ticks_batch_seed_schedule_matches_single_steps() -> None:
    spec = GenesisExperimentSpec(tick_count=0, seed=22)
    batch = GenesisEngine.from_spec(spec).run_ticks(5)
    single_engine = GenesisEngine.from_spec(spec)
    for _ in range(5):
        single = single_engine.run_ticks(1)
    assert tuple(item.digest() for item in batch.ticks) == tuple(
        item.digest() for item in single.ticks
    )


def test_public_behavior_exports_are_available() -> None:
    assert BehaviorMetricRegistry.genesis_v1()
    assert BehaviorDescriptorBuilder(BehaviorMetricRegistry.genesis_v1())
