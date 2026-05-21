import codontrace.genesis as g
import codontrace.genesis.phase_b_scientific_maturity as pb
from codontrace.genesis.public_api_manifest import validate_public_api_manifest


def test_phase_b_conflicting_names_have_explicit_unambiguous_public_aliases():
    assert g.PhaseBDiscoveryWitness is pb.DiscoveryWitness
    assert g.PhaseBDiscoveryCandidate is pb.DiscoveryCandidate
    assert g.PhaseBDistanceToD0Result is pb.DistanceToD0Result
    assert g.PhaseBInterventionResult is pb.InterventionResult
    assert g.PhaseBHeldoutEvaluationResult is pb.HeldoutEvaluationResult
    assert g.PhaseBScaleBenchmarkReport is pb.ScaleBenchmarkReport
    assert g.PhaseBPluginValidationResult is pb.PluginValidationResult
    assert g.PhaseBReleaseEvidencePack is pb.ReleaseEvidencePack
    assert g.PhaseBFinalClaimManifest is pb.FinalClaimManifest
    assert g.PhaseBEvidenceLineageDAG is pb.EvidenceLineageDAG
    assert g.FinalClaimManifestSample is pb.FinalClaimManifest
    assert g.EvidenceLineageDAGSample is pb.EvidenceLineageDAG


def test_legacy_runtime_names_are_explicit_compatibility_aliases_not_hidden_overwrites():
    assert g.LegacyDiscoveryWitness is g.DiscoveryWitness
    assert g.LegacyDistanceToD0Result is g.DistanceToD0Result
    assert g.LegacyInterventionResult is g.InterventionResult
    assert g.LegacyTaskGeneratorSpec is g.TaskGeneratorSpec
    assert g.LegacyEnvironmentMutationSpec is g.EnvironmentMutationSpec
    assert g.LegacyHeldoutEvaluationResult is g.HeldoutEvaluationResult
    assert g.LegacyScaleBenchmarkReport is g.ScaleBenchmarkReport
    assert g.LegacyPluginValidationResult is g.PluginValidationResult
    assert g.LegacyFinalClaimManifest is g.FinalClaimManifest
    assert g.LegacyReleaseEvidencePack is g.ReleaseEvidencePack
    assert g.LegacyEvidenceLineageDAG is g.EvidenceLineageDAG


def test_phase_b_records_have_record_kind_for_digest_distinctness_and_schema_audits():
    checked = [
        pb.DiscoveryEvent,
        pb.DiscoveryWitness,
        pb.AblationWitness,
        pb.HeldoutEvaluationResult,
        pb.CollectiveSwarmEvidenceLadder,
        pb.OEEClaimEligibilityResult,
        pb.CurriculumEnvironmentRecord,
        pb.ScaleBenchmarkReport,
        pb.PluginValidationResult,
        pb.ReleaseEvidencePackSample,
    ]
    for cls in checked:
        field_names = getattr(cls, "__dataclass_fields__")
        assert "record_kind" in field_names
        assert field_names["record_kind"].default


def test_integration_public_api_manifest_documents_unified_alias_policy():
    payload = validate_public_api_manifest()
    assert payload["passed"] is True
    symbols = {row["symbol_name"]: row for row in payload["symbols"]}
    for name in (
        "PhaseBDiscoveryWitness",
        "PhaseBScaleBenchmarkReport",
        "PhaseBPluginValidationResult",
        "FinalClaimManifestSample",
        "EvidenceLineageDAGSample",
        "LegacyDiscoveryWitness",
        "LegacyHeldoutEvaluationResult",
        "LegacyScaleBenchmarkReport",
        "LegacyPluginValidationResult",
        "LegacyFinalClaimManifest",
        "LegacyReleaseEvidencePack",
        "LegacyEvidenceLineageDAG",
    ):
        assert name in symbols
    assert symbols["PhaseBDiscoveryWitness"]["stability_status"] == "stable"
    assert symbols["LegacyDiscoveryWitness"]["claim_ready_allowed"] is False
    assert symbols["LegacyFinalClaimManifest"]["claim_ready_allowed"] is False
