import math
import subprocess
import sys
from pathlib import Path

import pytest

from codontrace.errors import ConfigurationError
from codontrace.genesis import RELEASE_LABEL, canonical_digest
from codontrace.genesis.campaign import (
    Phase3CampaignManifest,
    Phase3CampaignResult,
    Phase3CampaignSpec,
    Phase3ControlPlan,
    Phase3ExperimentLedger,
    Phase3MetricSpec,
    Phase3RunRecord,
    Phase3ScenarioSpec,
    Phase3SeedPlan,
)
from codontrace.genesis.final_release_manifest import (
    FinalClaimManifest,
    ReleaseEvidencePack,
    validate_final_claim_manifest,
)
from codontrace.genesis.statistical_protocol import (
    PairedComparisonResult,
    PreregisteredMetric,
    StatisticalTestPolicy,
    validate_statistical_claim_inputs,
)


def D(name: str) -> str:
    return canonical_digest({"phase3_acceptance": name})


def _spec() -> Phase3CampaignSpec:
    return Phase3CampaignSpec(
        "camp",
        RELEASE_LABEL,
        Phase3SeedPlan((1, 2, 3)),
        Phase3ControlPlan(("positive",), ("negative",)),
        (Phase3ScenarioSpec("family", "scenario", D("cfg"), D("world")),),
        (Phase3MetricSpec("score", "task score"),),
    )


def test_measured_phase3_campaign_rejects_not_run_claim_manifest_digest():
    record = Phase3RunRecord("r", "scenario", 1, D("manifest"), D("replay"))
    with pytest.raises(ConfigurationError):
        Phase3CampaignResult(
            _spec(),
            (record,),
            status="measured",
            claim_manifest_digest="not_run:claim_manifest",
            replay_bundle_digest=D("replay_bundle"),
        )


def test_measured_phase3_campaign_rejects_not_run_replay_bundle_digest():
    record = Phase3RunRecord("r", "scenario", 1, D("manifest"), D("replay"))
    with pytest.raises(ConfigurationError):
        Phase3CampaignResult(
            _spec(),
            (record,),
            status="measured",
            claim_manifest_digest=D("claim_manifest"),
            replay_bundle_digest="not_run:replay_bundle",
        )


def test_provisional_phase3_campaign_may_report_missing_replay_with_non_claim_status():
    result = Phase3CampaignResult(_spec(), status="provisional")
    assert result.manifest.status == "provisional"
    assert "non_claimable_final_digest_placeholder" in result.rejection_reasons


def test_phase3_run_record_measured_rejects_not_run_manifest_and_replay_digest():
    with pytest.raises(ConfigurationError):
        Phase3RunRecord("r", "s", 1, "not_run:manifest", "not_run:replay")


def test_phase3_campaign_manifest_rejects_not_run_final_digests_for_final_status():
    with pytest.raises(ConfigurationError):
        Phase3CampaignManifest(
            D("spec"),
            D("runs"),
            D("summary"),
            "not_run:claim_manifest",
            "not_run:replay_bundle",
            RELEASE_LABEL,
            status="claim_ready",
        )


def test_phase3_experiment_ledger_rejects_fake_placeholder_and_not_run_digests():
    with pytest.raises(ConfigurationError):
        Phase3ExperimentLedger("fake", (D("run"),), "placeholder", "not_run:claim")


def test_final_claim_manifest_computes_missing_evidence_from_required_minus_available():
    manifest = FinalClaimManifest(
        claim_id="collective_coordination_candidate",
        claim_text="collective claim",
        claim_level="claim_ready",
        allowed=True,
        required_evidence=("replay_bundle", "heldout_partner", "ablation"),
        available_evidence=("replay_bundle",),
        missing_evidence=(),
        replay_bundle_digest=D("replay_bundle"),
        claim_gate_decision_digest=D("claim_gate"),
        evidence_lineage_path=(D("config"), D("run"), D("claim")),
    )
    assert not manifest.allowed
    assert manifest.missing_evidence == ("ablation", "heldout_partner")
    assert "missing_required_evidence" in manifest.validation_reasons


def test_final_claim_manifest_normalizes_evidence_sets_and_recomputes_missing():
    manifest = FinalClaimManifest(
        "c",
        "claim",
        "level",
        False,
        ("b", "a", "a"),
        ("b",),
        ("caller_wrong",),
        D("replay"),
        D("gate"),
        (D("cfg"),),
    )
    assert manifest.required_evidence == ("a", "b")
    assert manifest.available_evidence == ("b",)
    assert manifest.missing_evidence == ("a",)


def test_final_claim_manifest_rejects_ci_low_greater_than_ci_high():
    with pytest.raises(ConfigurationError):
        FinalClaimManifest("c", "t", "level", False, (), (), (), D("r"), D("g"), (), 0.0, 2.0, 1.0)


def test_final_claim_manifest_rejects_empty_claim_gate_decision_digest_when_allowed():
    manifest = FinalClaimManifest("c", "t", "level", True, ("e",), ("e",), (), D("r"), "", (D("cfg"),))
    assert not manifest.allowed
    assert "missing_claim_gate_decision_digest" in manifest.validation_reasons


def test_final_claim_manifest_rejects_not_run_replay_digest_when_allowed():
    manifest = FinalClaimManifest("c", "t", "level", True, ("e",), ("e",), (), "not_run:replay_bundle", D("g"), (D("cfg"),))
    assert not manifest.allowed
    assert "missing_replay_bundle_digest" in manifest.validation_reasons


def test_final_claim_manifest_allowed_requires_evidence_lineage_and_real_replay_digest():
    manifest = FinalClaimManifest("c", "t", "level", True, ("e",), ("e",), (), "not_run:replay", D("g"), ())
    result = validate_final_claim_manifest(manifest)
    assert not result.passed
    assert "missing_replay_bundle_digest" in result.reasons
    assert "missing_evidence_lineage_path" in result.reasons


@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf")])
def test_statistical_claim_inputs_reject_non_finite_effect_size(value):
    ok, reason = validate_statistical_claim_inputs(
        p_value=0.5,
        effect_size=value,
        confidence_interval=(0.1, 1.0),
        replay_artifact_digest=D("replay"),
        protocol_digest=D("protocol"),
        claim_gate_decision_digest=D("gate"),
    )
    assert not ok
    assert reason == "non_finite_effect_size"


@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf")])
def test_statistical_claim_inputs_reject_non_finite_ci(value):
    ok, reason = validate_statistical_claim_inputs(
        p_value=0.5,
        effect_size=1.0,
        confidence_interval=(value, 1.0),
        replay_artifact_digest=D("replay"),
        protocol_digest=D("protocol"),
        claim_gate_decision_digest=D("gate"),
    )
    assert not ok
    assert reason == "non_finite_confidence_interval"


def test_statistical_claim_inputs_reject_p_value_outside_zero_one():
    ok, reason = validate_statistical_claim_inputs(
        p_value=1.5,
        effect_size=1.0,
        confidence_interval=(0.1, 1.0),
        replay_artifact_digest=D("replay"),
        protocol_digest=D("protocol"),
        claim_gate_decision_digest=D("gate"),
    )
    assert not ok
    assert reason == "p_value_out_of_range"


def test_statistical_test_policy_rejects_non_monotonic_thresholds():
    with pytest.raises(ConfigurationError):
        StatisticalTestPolicy(min_descriptive_n=8, min_exploratory_n=4)


def test_paired_comparison_result_rejects_inverted_ci():
    metric = PreregisteredMetric("score", "task")
    with pytest.raises(ConfigurationError):
        PairedComparisonResult(metric, D("b"), D("t"), D("seed"), 1.0, 3, 2.0, 1.0)


def test_paired_comparison_result_rejects_fake_digests_for_claim_grade():
    metric = PreregisteredMetric("score", "task")
    with pytest.raises(ConfigurationError):
        PairedComparisonResult(metric, "fake", D("t"), D("seed"), 1.0, 3, 0.1, 1.0)


def test_phase3_validation_smoke_runs_from_clean_checkout(tmp_path):
    repo_root = Path(__file__).resolve().parents[2]
    completed = subprocess.run(
        [sys.executable, "examples/genesis_phase3_validation_smoke.py"],
        cwd=repo_root,
        text=True,
        capture_output=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
