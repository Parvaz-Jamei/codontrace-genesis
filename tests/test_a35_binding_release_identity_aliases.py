import math

import pytest

import codontrace.genesis as g
from codontrace.errors import ConfigurationError
from codontrace.genesis import canonical_digest
from codontrace.genesis.final_release_manifest import ReleaseEvidencePack
from codontrace.genesis.open_endedness import LearnabilityReport, NoveltyTrajectory, OEEArtifactSequence
from codontrace.genesis.replay_integrity import audit_replay_digest_policy_registry

CURRENT_ARTIFACT_NAME = "codontrace-0.3.0a1-release-bundle.zip"


def D(name: str) -> str:
    return canonical_digest({"a35_binding_release_fix": name})


def test_release_artifact_name_matches_current_reviewed_package():
    assert g.RELEASE_ARTIFACT_NAME == CURRENT_ARTIFACT_NAME
    assert g.CURRENT_PACKAGE_ARTIFACT_NAME == CURRENT_ARTIFACT_NAME
    assert g.CURRENT_PACKAGE_LABEL == g.RELEASE_LABEL
    assert g.BASE_RELEASE_LABEL != g.RELEASE_LABEL


def test_phase3_public_artifact_exports_are_not_release_pack_aliases():
    alias_names = [
        "Phase3ScientificSummary",
        "NegativeResultReport",
        "ReplayBundleIndex",
        "BenchmarkLeaderboardArtifact",
        "AblationMatrixArtifact",
        "ClaimDowngradeReport",
    ]
    offenders = [name for name in alias_names if getattr(g, name) is ReleaseEvidencePack]
    assert offenders == []


def test_phase3_public_artifacts_validate_digest_and_finite_contracts():
    replay_index = g.ReplayBundleIndex((D("replay1"), D("replay2")), ("s1", "s2"), (1, 2), D("seed_plan"), D("cfg"))
    assert replay_index.validate().passed
    leaderboard = g.BenchmarkLeaderboardArtifact("scenario", ("fitness",), 2, D("seed_policy"), "descending_mean", 1.0, 0.1, 2.0)
    assert leaderboard.validate().passed
    ablation = g.AblationMatrixArtifact(("capsule",), D("base"), D("treat"), "capsule", 0.5, 0.1, 0.9, (D("neg"),))
    assert ablation.validate().passed
    downgrade = g.ClaimDowngradeReport("social_intelligence", "social_interaction", ("heldout_partner",), "missing heldout", D("gate"))
    assert not downgrade.validate().claim_eligible
    negative = g.NegativeResultReport("social_intelligence", ("events",), ("heldout_partner",), "documents a rejected higher-order claim", D("gate2"), D("replay"))
    summary = g.Phase3ScientificSummary(g.RELEASE_LABEL, replay_index.digest(), leaderboard.digest(), ablation.digest(), ("auditable evidence infrastructure",), ("social_intelligence",), (negative.digest(),))
    assert summary.validate().claim_eligible
    with pytest.raises(ConfigurationError):
        g.BenchmarkLeaderboardArtifact("scenario", ("fitness",), 2, D("seed_policy"), "rank", math.nan, 0.1, 2.0)
    with pytest.raises(ConfigurationError):
        g.ReplayBundleIndex(("fake",), ("s1",), (1,), D("seed"), D("cfg"))


def test_oee_schema_collapsing_aliases_are_independent_dataclasses():
    assert g.PersistenceReport is not NoveltyTrajectory
    assert g.SteppingStoneTransferReport is not LearnabilityReport
    assert g.CurriculumCoEvolutionReport is not LearnabilityReport
    assert g.D0ShadowBaselineReport is not LearnabilityReport
    assert g.TaskGeneratorSpec is not OEEArtifactSequence
    assert g.EnvironmentMutationRecord is not OEEArtifactSequence


def test_replay_digest_policy_registry_covers_new_phase3_artifacts():
    assert audit_replay_digest_policy_registry() == ()


def test_phase3_public_artifact_schemas_are_distinct():
    artifacts = [
        g.ReplayBundleIndex((D("replay_schema"),), ("scenario",), (7,), D("seed_plan_schema"), D("config_schema")),
        g.BenchmarkLeaderboardArtifact("scenario", ("fitness",), 1, D("seed_policy_schema"), "descending_mean", 1.0, 0.1, 2.0),
        g.AblationMatrixArtifact(("memory",), D("baseline_schema"), D("treatment_schema"), "memory", 0.2, 0.01, 0.4, (D("negative_schema"),)),
        g.ClaimDowngradeReport("social_intelligence", "social_interaction", ("heldout_partner",), "missing heldout", D("claim_gate_schema")),
        g.NegativeResultReport("generalization", ("train_replay",), ("heldout_replay",), "negative result retained as evidence", D("gate_schema"), D("replay_schema_2")),
    ]
    summary = g.Phase3ScientificSummary(
        g.RELEASE_LABEL,
        artifacts[0].digest(),
        artifacts[1].digest(),
        artifacts[2].digest(),
        ("release evidence infrastructure",),
        ("social_intelligence",),
        (artifacts[4].digest(),),
    )
    artifacts.append(summary)
    class_names = [artifact.__class__.__name__ for artifact in artifacts]
    schema_versions = [artifact.schema_version for artifact in artifacts]
    assert len(class_names) == len(set(class_names))
    assert len(schema_versions) == len(set(schema_versions))


def test_stale_phase3_generated_helper_files_are_not_shipped():
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    assert not (root / ".phase3_patch.py").exists()
    assert not (root / ".phase3_exports_tests.py").exists()


def test_stepping_stone_placeholder_is_negative_evidence_not_constructor_crash():
    weak = g.SteppingStoneTransferReport(1.0, "placeholder", D("replay_placeholder_regression"))
    assert not weak.claim_eligible
    payload = weak.to_dict()
    assert payload["transfer_status"] == "invalid_evidence"
    assert "missing_source_environment_digest" in payload["rejection_reasons"]
    assert weak.digest()
