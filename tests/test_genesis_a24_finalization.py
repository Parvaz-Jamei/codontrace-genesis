import pytest

from codontrace.errors import ConfigurationError
from codontrace.genesis import (
    APIStabilityLevel,
    BenchmarkScenario,
    DocumentationAuditConfig,
    FinalExamplesMatrix,
    FinalExamplesMatrixSummary,
    FinalGateSummary,
    FinalNonClaimStatement,
    FinalReleaseManifest,
    QDEvidenceSummary,
    ScientificEvidencePack,
    ScientificEvidenceProfile,
    WitnessEvidenceSummary,
    audit_claim_text,
    audit_docs_claims,
    audit_documentation_sections,
    build_api_stability_map,
    score_evidence_completeness,
    validate_api_stability_map_against_exports,
    validate_scientific_evidence_pack,
)
from codontrace.genesis.claim_audit import ClaimAuditContext
from codontrace.genesis.scientific_evidence import AblationEvidenceSummary, D0EvidenceSummary


def test_claim_audit_safe_negation_does_not_suppress_separate_claim() -> None:
    result = audit_claim_text("CodonTrace does not prove artificial life but is state of the art.")
    assert not result.succeeded
    assert any(item.claim_type.value == "state_of_the_art" for item in result.blocked_claims)


def test_claim_audit_docs_safe_history_not_blocker() -> None:
    result = audit_docs_claims(
        {
            "CHANGELOG.md": (
                "No AGI, consciousness, artificial-life proof, or benchmark superiority claim."
            )
        },
        {"CHANGELOG.md": ClaimAuditContext("CHANGELOG.md", "changelog")},
    )
    assert result.succeeded


def test_claim_audit_safe_non_claim_list_scope() -> None:
    safe = audit_claim_text(
        "No AGI, consciousness, artificial-life proof, or open-ended discovery proof is claimed."
    )
    assert safe.succeeded

    unsafe = audit_claim_text("No AGI, but proves consciousness.")
    assert not unsafe.succeeded
    assert any(item.claim_type.value == "consciousness" for item in unsafe.blocked_claims)

    benchmark = audit_claim_text("No benchmark claim, but benchmark-leading.")
    assert not benchmark.succeeded
    assert any(
        item.claim_type.value == "benchmark_superiority" for item in benchmark.blocked_claims
    )


def test_qd_evidence_summary_validates_bins_and_coverage() -> None:
    with pytest.raises(ConfigurationError):
        QDEvidenceSummary("a", 10, 5, 2.0, 0.0, None, 0, "schema")
    valid = QDEvidenceSummary("a", 2, 4, 0.5, 1.0, 1.0, 0, "schema", seed_count=3)
    assert valid.seed_count == 3


def test_scientific_evidence_seed_policy_per_component() -> None:
    pack = ScientificEvidencePack(
        pack_id="pack",
        version="0.3.0a1",
        d0_summary=D0EvidenceSummary("d0", 3, 1, ("novelty",), "normalized_l1", "threshold"),
        qd_summary=QDEvidenceSummary("qd", 1, 2, 0.5, 1.0, 1.0, 0, "schema", seed_count=3),
        ablation_summary=AblationEvidenceSummary("ab", "baseline", ("no_adf",), 3, {}, {}),
        witness_summary=WitnessEvidenceSummary(
            "w", "EVIDENCE_SUPPORTED", "ok", "d0", "trace", "replay", "ab", 3
        ),
        validation_matrix_digest="matrix",
        claim_audit_digest="claims",
        limitation_ids=("limits",),
    )
    result = validate_scientific_evidence_pack(pack, ScientificEvidenceProfile.mature_alpha())
    assert not result.succeeded
    assert "d0_multi_seed" in result.missing_items


def test_paper_ready_replay_completeness() -> None:
    pack = ScientificEvidencePack(
        pack_id="pack",
        version="0.3.0a1",
        witness_summary=WitnessEvidenceSummary(
            "w", "CANDIDATE", "ok", "d0", "trace", "replay", "ab", 5
        ),
        replay_digest="replay",
    )
    score = score_evidence_completeness(pack, "paper_ready")
    assert "replay" in score.present_items
    with pytest.raises(ConfigurationError):
        score_evidence_completeness(pack, ("claim_audit", "claim_audit"))


def test_documentation_audit_required_sections() -> None:
    docs = {
        "README.md": (
            "Installation\n"
            "Quickstart\n"
            "GENESIS alignment\n"
            "Non-goals\n"
            "Claim limitations\n"
            "API overview\n"
            "Examples\n"
            "Release evidence\n"
            "Citation\n"
            "Limitations"
        )
    }
    result = audit_documentation_sections(docs, config=DocumentationAuditConfig.mature_alpha())
    assert not result.succeeded
    assert "security" in result.missing_sections


def test_documentation_audit_accepts_mature_alpha_aliases() -> None:
    docs = {
        "README.md": (
            "Install\n"
            "Quick start\n"
            "GENESIS Foundation Kernel status\n"
            "Limitations and non-claims\n"
            "Core API\n"
            "Examples\n"
            "Release checklist\n"
            "Citation / references\n"
        ),
        "docs/api.md": "Core API",
        "docs/non_goals.md": "Limitations and non-claims",
        "docs/release_checklist.md": "Release checklist",
        "SECURITY.md": "Security policy",
    }
    result = audit_documentation_sections(docs, config=DocumentationAuditConfig.mature_alpha())
    assert result.succeeded
    assert result.missing_sections == ()


def test_api_stability_map_full_export_coverage() -> None:
    stability = build_api_stability_map("0.3.0a1", ("A",), default_level=APIStabilityLevel.ALPHA)
    assert validate_api_stability_map_against_exports(stability, ("A", "B")) == (
        "missing_export:B",
    )

    unknown = build_api_stability_map("0.3.0a1", ("A", "C"), default_level=APIStabilityLevel.ALPHA)
    assert validate_api_stability_map_against_exports(unknown, ("A",)) == ("unknown_symbol:C",)

    duplicate = build_api_stability_map("0.3.0a1", ("A",), default_level=APIStabilityLevel.ALPHA)
    duplicate = type(duplicate)("0.3.0a1", alpha_symbols=("A",), stable_candidate_symbols=("A",))
    assert validate_api_stability_map_against_exports(duplicate, ("A",)) == ("duplicate_symbol:A",)


def test_final_objects_roundtrip_digest() -> None:
    manifest = FinalReleaseManifest("0.3.0a1", "artifact.zip", "source")
    assert FinalReleaseManifest.from_dict(manifest.to_dict()).digest() == manifest.digest()
    gate = FinalGateSummary(
        "0.3.0a1", True, True, True, True, True, False, True, True, ("external gates pending",)
    )
    assert FinalGateSummary.from_dict(gate.to_dict()).digest() == gate.digest()
    examples = FinalExamplesMatrixSummary(
        (FinalExamplesMatrix("ex.py", "mature_alpha", smoke_status="PASS"),)
    )
    assert examples.passed_examples == 1
    statement = FinalNonClaimStatement.mature_alpha("unknown")
    assert "AGI" in statement.prohibited_claims


def test_optional_paper_companion_objects() -> None:
    scenario = BenchmarkScenario(
        benchmark_id="b",
        description="object only",
        baseline_method="baseline",
        controlled_variables=("seed",),
        metrics=("coverage",),
        non_claims=("No superiority claim.",),
    )
    assert scenario.digest() == BenchmarkScenario.from_dict(scenario.to_dict()).digest()
