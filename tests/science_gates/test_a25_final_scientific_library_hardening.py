from __future__ import annotations

from pathlib import Path

import pytest

from codontrace.actions import ActionContext, ActionResult, default_action_registry
from codontrace.errors import ConfigurationError
from codontrace.genesis.artifacts import compute_source_digest
from codontrace.genesis.benchmark_suite import benchmark_v2_specs
from codontrace.genesis.claim_gate import (
    ClaimRequest,
    ScientificClaimGate,
    default_claim_gate_policy,
    normalize_claim_label,
)
from codontrace.genesis.engine import GenesisEngine, GenesisEngineConfig, GenesisExperimentSpec
from codontrace.genesis.event_graph import EventGraphEdge
from codontrace.genesis.qd_search import QDCandidate, QDSchedulerState
from codontrace.genesis.review import ForbiddenClaimPolicy
from codontrace.genesis.rules import (
    ApprovalStatus,
    ApprovedRuleSet,
    HumanApprovalRecord,
    RuleProposal,
    RuleProposalSource,
    RuleSetDiff,
    RuleValidator,
)
from codontrace.genesis.statistical_protocol import build_oee_metrics_report
from codontrace.genesis.structural_mutation import (
    StructuralMutationConfig,
    build_genome_program,
    mutate_genome_program,
)
from codontrace.genesis.translation_profile import (
    TranslationPolicy,
    TranslationUpdateRecord,
    TranslationWeight,
    build_translation_profile,
    resolve_translation_action,
)
from codontrace.rng import RNGManager


def test_claim_gate_rejects_aliases_and_unknown_claims() -> None:
    gate = ScientificClaimGate()
    for claim in (
        "true causal discovery",
        "unbounded-open-endedness-proved",
        "solved_artificial_life",
        "proved semantic closure",
        "benchmark_superiority",
    ):
        decision = gate.decide(ClaimRequest(claim, {}))
        assert not decision.allowed
        assert decision.decision == "rejected_overclaim_alias"
        assert decision.policy_version == default_claim_gate_policy().version
        assert decision.digest
    unknown = gate.decide(ClaimRequest("totally_new_grand_claim", {}))
    assert not unknown.allowed
    assert unknown.decision == "rejected_unknown_claim"
    assert normalize_claim_label("Full-GENESIS Engine!") == "full_genesis_engine"


def test_manifest_claim_comes_from_claim_gate_not_raw_config() -> None:
    spec = GenesisExperimentSpec(
        tick_count=1,
        engine_config=GenesisEngineConfig(claim_level="proved_semantic_closure"),
    )
    result = GenesisEngine.from_spec(spec).run_ticks()
    manifest = result.manifest
    assert manifest.requested_claim_level == "proved_semantic_closure"
    assert manifest.final_claim_level != "proved_semantic_closure"
    assert manifest.claim_level == manifest.final_claim_level
    assert manifest.claim_gate_decision == "rejected_overclaim_alias"
    assert manifest.claim_gate_decision_digest
    assert "overclaim_alias_forbidden" in manifest.failed_reasons


def test_approved_rule_set_binds_proposal_validation_approval_digest_chain() -> None:
    proposal = RuleProposal(
        "p",
        RuleProposalSource.HUMAN,
        RuleSetDiff(add=({"target": "metadata", "key": "x", "value": True},)),
    )
    validation = RuleValidator().validate(proposal)
    good_approval = HumanApprovalRecord(
        proposal_digest=proposal.digest(),
        approver="reviewer",
        status=ApprovalStatus.APPROVED,
        reason="ok",
        validation_digest=validation.digest(),
    )
    approved = ApprovedRuleSet(proposal, validation, good_approval)
    assert approved.digest()
    bad_approval = HumanApprovalRecord(
        proposal_digest=proposal.digest(),
        approver="reviewer",
        status=ApprovalStatus.APPROVED,
        reason="fake",
        validation_digest="fake",
    )
    with pytest.raises(ConfigurationError):
        ApprovedRuleSet(proposal, validation, bad_approval)


def test_structural_mutation_identity_and_provenance_are_separate() -> None:
    parent = build_genome_program("000001", codon_width=3)
    child, record = mutate_genome_program(
        parent,
        StructuralMutationConfig(codon_insert_rate=1.0, bit_flip_rate=0.0),
        RNGManager(seed=3),
        kind="insert",
        payload_codon="111",
    )
    assert record.child_genome_digest == child.identity_digest == child.digest
    assert child.provenance_digest != child.identity_digest
    assert child.artifact_digest != child.identity_digest
    child_same_identity = build_genome_program(
        child.bits,
        codon_width=3,
        structural_mutation_digest="different_provenance",
        lineage_tags=("other",),
    )
    assert child_same_identity.identity_digest == child.identity_digest
    assert child_same_identity.provenance_digest != child.provenance_digest


def test_replay_critical_digest_spoofing_rejected() -> None:
    with pytest.raises(ConfigurationError):
        EventGraphEdge("a", "b", 1, 1, digest="fake")
    with pytest.raises(ConfigurationError):
        TranslationUpdateRecord("o", 1, "000", None, "WAIT", 0.0, 1.0, "test", 1.0, digest="fake")
    with pytest.raises(ConfigurationError):
        QDSchedulerState("a", "b", "c", 1, digest="fake")


def test_source_digest_ignores_generated_metadata(tmp_path: Path) -> None:
    src = tmp_path / "src" / "codontrace"
    src.mkdir(parents=True)
    py = src / "a.py"
    py.write_text("x = 1\n")
    before = compute_source_digest(str(tmp_path))
    egg = tmp_path / "src" / "codontrace.egg-info"
    egg.mkdir()
    (egg / "PKG-INFO").write_text("generated")
    (tmp_path / "dist").mkdir()
    (tmp_path / "dist" / "pkg.whl").write_bytes(b"generated")
    assert compute_source_digest(str(tmp_path)) == before
    py.write_text("x = 2\n")
    assert compute_source_digest(str(tmp_path)) != before


def test_qd_candidate_validates_inline_genome_digest_and_status() -> None:
    good = QDCandidate.from_genome_bits("000111")
    assert good.genome_reference_status == "verified_inline"
    with pytest.raises(ConfigurationError):
        QDCandidate(
            candidate_id="bad",
            genome_digest="fake",
            genome_bits="000111",
            genome_program_digest=None,
            macro_registry_digest=None,
            translation_profile_digest=None,
            parent_ids=(),
            mutation_record_digest=None,
            lineage_tags=(),
        )
    opaque = QDCandidate(
        candidate_id="opaque",
        genome_digest="external_digest",
        genome_bits=None,
        genome_program_digest=None,
        macro_registry_digest=None,
        translation_profile_digest=None,
        parent_ids=(),
        mutation_record_digest=None,
        lineage_tags=(),
    )
    assert opaque.genome_reference_status == "opaque_external_reference"


def test_not_run_protocol_status_does_not_count_as_evidence() -> None:
    spec = GenesisExperimentSpec(
        tick_count=1, engine_config=GenesisEngineConfig(claim_level="intervention_supported")
    )
    result = GenesisEngine.from_spec(spec).run_ticks()
    assert result.manifest.protocol_statuses["intervention_result_status"] == "not_run"
    assert result.manifest.manifest_schema_complete is True
    assert result.manifest.claim_gate_allowed is False
    assert result.manifest.claim_level == "event_association_only"


def test_active_qd_requires_parent_selection_feedback_or_downgrades() -> None:
    gate = ScientificClaimGate()
    passive = gate.decide(
        ClaimRequest(
            "active_qd_supported",
            {"qd_candidate_schema": True, "qd_ask_tell": True, "archive_feedback": True},
        )
    )
    assert not passive.allowed
    assert passive.final_claim == "qd_reporting_supported"
    active = gate.decide(
        ClaimRequest(
            "active_qd_supported",
            {
                "qd_candidate_schema": True,
                "qd_ask_tell": True,
                "archive_feedback": True,
                "parent_selection_feedback": True,
                "archive_digest": True,
                "parent_selection_feedback_digest": True,
                "qd_scheduler_digest": True,
            },
        )
    )
    assert active.allowed


def test_execution_source_digest_changes_when_source_records_exist() -> None:
    base = GenesisExperimentSpec(tick_count=1, enable_execution_source=False)
    traced = GenesisExperimentSpec(tick_count=1, enable_execution_source=True)
    r0 = GenesisEngine.from_spec(base).run_ticks()
    r1 = GenesisEngine.from_spec(traced).run_ticks()
    assert r0.manifest.execution_source_digest != r1.manifest.execution_source_digest
    assert r1.evidence_pack.contribution_ledgers


def test_action_registry_digest_changes_when_handler_changes() -> None:
    def a(ctx: ActionContext) -> ActionResult:
        return ActionResult.executed(reason="a", position_after=ctx.position)

    def b(ctx: ActionContext) -> ActionResult:
        return ActionResult.executed(reason="b", position_after=ctx.position)

    spec_a = GenesisExperimentSpec(
        action_registry=default_action_registry().extend("CUSTOM_A", a), tick_count=0
    )
    spec_b = GenesisExperimentSpec(
        action_registry=default_action_registry().extend("CUSTOM_A", b), tick_count=0
    )
    assert spec_a.to_dict()["action_registry_hash"] != spec_b.to_dict()["action_registry_hash"]


def test_genesis_experiment_spec_validates_plain_string_and_metadata() -> None:
    spec = GenesisExperimentSpec(genome_bits="000001")  # type: ignore[arg-type]
    assert spec.genome_bits == ("000001",)
    with pytest.raises(ValueError):
        GenesisExperimentSpec(metadata={"bad": object()})  # type: ignore[arg-type]


def test_translation_profile_safety_gates() -> None:
    profile = build_translation_profile(
        "p", "spec", [TranslationWeight("000", "MOVE_EAST", 2.0, 1, 0)]
    )
    assert resolve_translation_action("000", "WAIT", profile, TranslationPolicy()) == "MOVE_EAST"
    with pytest.raises(ConfigurationError):
        resolve_translation_action(
            "000", "WAIT", profile, TranslationPolicy(weight_upper_bound=1.0)
        )
    with pytest.raises(ConfigurationError):
        resolve_translation_action(
            "000", "WAIT", profile, TranslationPolicy(approved_actions=("WAIT",))
        )


def test_forbidden_claim_policy_derives_from_claim_gate() -> None:
    policy = ForbiddenClaimPolicy()
    assert set(policy.forbidden_terms or ()) == set(default_claim_gate_policy().forbidden_aliases)
    assert policy.check_text("This proves semantic closure")


def test_known_capsule_transfer_world_exists_with_protocol_metadata() -> None:
    specs = {item.scenario_id: item for item in benchmark_v2_specs()}
    scenario = specs["known_capsule_transfer_world"]
    assert scenario.treatment_config_digest is not None
    assert scenario.claim_ceiling == "intervention_supported"
    assert "effect_size" in scenario.required_metrics


def test_oee_persistence_window_below_threshold_downgrades_claim() -> None:
    metrics = {
        "archive_coverage_slope": 1.0,
        "persistent_novelty_rate": 1.0,
        "lineage_persistence": 1.0,
        "behavior_entropy": 1.0,
    }
    ci = {key: (0.0, 1.0) for key in metrics}
    report = build_oee_metrics_report(
        30,
        1000,
        metrics,
        confidence_intervals=ci,
        shadow_adjusted=True,
        persistence_window_observed=1,
    )
    assert report.claim_level == "measurement_only"
    ok = build_oee_metrics_report(
        30,
        1000,
        metrics,
        confidence_intervals=ci,
        shadow_adjusted=True,
        persistence_window_observed=10,
    )
    assert ok.claim_level == "oee_candidate"
