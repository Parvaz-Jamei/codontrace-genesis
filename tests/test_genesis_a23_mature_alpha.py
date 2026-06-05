import pytest

from codontrace.errors import ConfigurationError
from codontrace.genesis import (
    APIAuditResult,
    APIStabilityMap,
    ClaimType,
    CompatibilityPolicy,
    D0EvidenceSummary,
    DocsConsistencyConfig,
    DocumentationAuditResult,
    EvidenceBundle,
    EvidenceDependency,
    EvidenceLineageGraph,
    LimitationRecord,
    LimitationSeverity,
    QDEvidenceSummary,
    ReleaseCandidateChecklist,
    ReleaseGateRecord,
    ReleaseGateStatus,
    ReleaseReadinessProfile,
    ScientificEvidencePack,
    ScientificEvidenceProfile,
    SecurityEvidenceRecord,
    WitnessEvidenceSummary,
    audit_claim_text,
    audit_documentation_sections,
    build_api_stability_map,
    evaluate_docs_consistency,
    evaluate_mature_alpha_readiness,
    evaluate_release_candidate,
    score_evidence_completeness,
    score_evidence_quality,
    summarize_reproducibility,
    validate_api_stability_map,
    validate_evidence_lineage,
    validate_scientific_evidence_pack,
)
from codontrace.genesis.evidence_bundle import EvidenceRecord
from codontrace.genesis.release_candidate import ReleaseGateException


def _complete_gates(profile: ReleaseReadinessProfile) -> tuple[ReleaseGateRecord, ...]:
    return tuple(ReleaseGateRecord(name, ReleaseGateStatus.PASS) for name in profile.required_gates)


def test_claim_audit_safe_negation_does_not_suppress_separate_claim() -> None:
    assert audit_claim_text("CodonTrace does not prove artificial life.").succeeded
    assert not audit_claim_text(
        "CodonTrace does not prove artificial life but is state of the art."
    ).succeeded
    assert not audit_claim_text(
        "Not proof of knowledge transfer; knowledge transfer is demonstrated."
    ).succeeded
    assert not audit_claim_text("No benchmark claim, but benchmark-leading.").succeeded


def test_claim_audit_blocks_mature_alpha_overclaims() -> None:
    blocked = (
        "CodonTrace achieves superintelligence.",
        "CodonTrace is an artificial life system.",
        "CodonTrace creates emergent life.",
        "CodonTrace is a breakthrough autonomous agent.",
        "CodonTrace is the best framework for open-ended AI.",
        "CodonTrace proves life-like intelligence.",
    )
    for text in blocked:
        assert not audit_claim_text(text).succeeded
    assert audit_claim_text("No superintelligence claim; research scaffold only.").succeeded


def test_release_candidate_mature_alpha_decision_and_pypi_exception_path() -> None:
    mature = ReleaseReadinessProfile.mature_alpha()
    checklist = ReleaseCandidateChecklist(
        "0.3.0a1",
        "artifact.zip",
        _complete_gates(mature),
        api_snapshot_digest="api",
        claim_audit_digest="claim",
        validation_bundle_digest="validation",
        citation_digest="citation",
        limitations_digest="limits",
    )
    decision = evaluate_release_candidate(checklist, mature)
    assert decision.accepted_for_mature_alpha
    assert decision.profile_name == "mature_alpha"

    pypi = ReleaseReadinessProfile.pypi()
    gates = tuple(
        ReleaseGateRecord(
            name, ReleaseGateStatus.NOT_COMPLETED if name == "pip_audit" else ReleaseGateStatus.PASS
        )
        for name in pypi.required_gates
    )
    exception_checklist = ReleaseCandidateChecklist(
        "0.3.0a1",
        "artifact.zip",
        gates,
        api_snapshot_digest="api",
        claim_audit_digest="claim",
        citation_digest="citation",
        limitations_digest="limits",
        gate_exceptions=(ReleaseGateException("pip_audit", True, "sandbox timeout"),),
    )
    exception_decision = evaluate_release_candidate(exception_checklist, pypi)
    assert not exception_decision.accepted_for_pypi
    assert exception_decision.accepted_for_pypi_with_exception
    assert exception_decision.accepted_with_exceptions


def test_qd_evidence_summary_rejects_invalid_coverage() -> None:
    with pytest.raises(ConfigurationError):
        QDEvidenceSummary("qd", 10, 5, 2.0, 1.0, 1.0, 0, "schema")
    with pytest.raises(ConfigurationError):
        QDEvidenceSummary("qd", 2, 4, 0.75, 1.0, 1.0, 0, "schema")
    assert QDEvidenceSummary("qd", 2, 4, 0.5, 1.0, 1.0, 0, "schema").digest()


def test_evidence_completeness_rejects_duplicates_and_unknown_profiles() -> None:
    pack = ScientificEvidencePack("pack", "0.3.0a1", claim_audit_digest="claim")
    with pytest.raises(ConfigurationError):
        score_evidence_completeness(pack, ("claim_audit", "claim_audit"))
    with pytest.raises(ConfigurationError):
        score_evidence_completeness(pack, "unknown")
    score = score_evidence_completeness(pack, "prepublic")
    assert "completeness_only_not_truth_or_proof" in score.warnings


def test_docs_consistency_allows_changelog_history_and_flags_current_scope() -> None:
    docs = {
        "CHANGELOG.md": "v0.2.0a20 historical entry.",
        "README.md": "Current v0.3.0a1 release notes.",
    }
    result = evaluate_docs_consistency(docs, config=DocsConsistencyConfig("unknown"))
    assert result.passed
    stale = evaluate_docs_consistency({"README.md": "Current v0.2.0a20."}, "unknown")
    assert not stale.passed


def test_scientific_evidence_profile_mature_alpha_validation() -> None:
    empty = ScientificEvidencePack("pack", "0.3.0a1", claim_audit_digest="claim")
    assert validate_scientific_evidence_pack(empty, ScientificEvidenceProfile.prepublic()).succeeded
    assert not validate_scientific_evidence_pack(
        empty, ScientificEvidenceProfile.mature_alpha()
    ).succeeded
    complete = ScientificEvidencePack(
        "pack",
        "0.3.0a1",
        d0_summary=D0EvidenceSummary("d0", 3, 3, ("novelty",), "normalized_l1", "t"),
        qd_summary=QDEvidenceSummary("qd", 2, 4, 0.5, 2.0, 1.0, 0, "schema"),
        witness_summary=WitnessEvidenceSummary(
            "w", "EVIDENCE_SUPPORTED", "scaffold", "d0", "trace", "replay", "ab", 3
        ),
        validation_matrix_digest="vm",
        claim_audit_digest="claim",
        limitation_ids=("lim",),
    )
    # Missing ablation summary still blocks mature alpha.
    assert not validate_scientific_evidence_pack(
        complete, ScientificEvidenceProfile.mature_alpha()
    ).succeeded


def test_evidence_lineage_and_reproducibility_summary() -> None:
    graph = EvidenceLineageGraph(
        "g",
        (
            EvidenceDependency("d0", "witness", "supports"),
            EvidenceDependency("witness", "d0", "depends"),
        ),
        ("d0", "witness"),
    )
    result = validate_evidence_lineage(graph)
    assert not result.succeeded
    assert result.circular_dependencies
    missing = validate_evidence_lineage(
        EvidenceLineageGraph("g", (EvidenceDependency("a", "b", "supports"),), ("a",))
    )
    assert "b" in missing.missing_evidence_ids

    bundle = EvidenceBundle(
        "b",
        "0.3.0a1",
        (
            EvidenceRecord("e1", "trace", "trace", 1, "cfg", "trace"),
            EvidenceRecord("e2", "trace", "trace", 1, "cfg2", "trace2", replay_digest="r"),
        ),
        claim_limitations=("lim",),
    )
    summary = summarize_reproducibility(bundle)
    assert summary.duplicate_seed_count == 1
    assert summary.deterministic_replay_available


def test_evidence_quality_and_mature_alpha_readiness_blocks_claim_failure() -> None:
    pack = ScientificEvidencePack("pack", "0.3.0a1", claim_audit_digest="claim")
    bundle = EvidenceBundle("b", "0.3.0a1", (), claim_limitations=("lim",))
    limitation = LimitationRecord(
        "lim",
        LimitationSeverity.CRITICAL,
        "claim",
        "critical",
        "blocks claims",
        blocks_claims=(ClaimType.OPEN_ENDED_DISCOVERY_PROOF,),
    )
    claim_audit = audit_claim_text("CodonTrace achieves superintelligence.")
    quality = score_evidence_quality(pack, bundle, (limitation,), claim_audit)
    assert quality.score_0_to_1 < 1.0
    api_audit = APIAuditResult(True, True, 1)
    release_decision = evaluate_release_candidate(
        ReleaseCandidateChecklist(
            "0.3.0a1",
            "artifact.zip",
            _complete_gates(ReleaseReadinessProfile.mature_alpha()),
            api_snapshot_digest="api",
            claim_audit_digest="claim",
            validation_bundle_digest="validation",
            citation_digest="citation",
            limitations_digest="limits",
        ),
        ReleaseReadinessProfile.mature_alpha(),
    )
    readiness = evaluate_mature_alpha_readiness(
        "0.3.0a1",
        release_decision,
        validate_scientific_evidence_pack(pack, ScientificEvidenceProfile.mature_alpha()),
        quality,
        claim_audit,
        api_audit,
        (limitation,),
    )
    assert not readiness.accepted
    assert "claim_audit_blockers" in readiness.blocking_issues


def test_api_stability_policy_documentation_and_security_records() -> None:
    stability = build_api_stability_map("0.3.0a1", ("A", "B"))
    assert isinstance(stability, APIStabilityMap)
    assert validate_api_stability_map(stability, ("A", "B")) == ()
    assert validate_api_stability_map(stability, ("A", "C")) == ("C",)
    assert CompatibilityPolicy("0.3.0a1", ">=3.10", ("3.10",), "one alpha cycle").digest()
    doc_audit = audit_documentation_sections(
        {
            "README.md": (
                "installation quickstart GENESIS alignment non-goals claim limitations "
                "API overview examples release evidence citation security"
            )
        },
        (
            "installation",
            "quickstart",
            "GENESIS alignment",
            "non-goals",
            "claim limitations",
            "API overview",
            "examples",
            "release evidence",
            "citation",
            "security",
        ),
    )
    assert isinstance(doc_audit, DocumentationAuditResult)
    assert doc_audit.succeeded
    assert SecurityEvidenceRecord("pip-audit", "PASS", "pip-audit", "digest").digest()
