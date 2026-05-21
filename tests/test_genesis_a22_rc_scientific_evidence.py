from codontrace.genesis import (
    ArtifactHygieneRecord,
    ClaimDowngradeResult,
    ClaimType,
    D0EvidenceSummary,
    EvidenceBundle,
    EvidenceRecord,
    LimitationRecord,
    LimitationSeverity,
    QDEvidenceSummary,
    ReleaseCandidateChecklist,
    ReleaseGateException,
    ReleaseGateRecord,
    ReleaseGateStatus,
    ReleaseReadinessProfile,
    ScientificEvidencePack,
    SupplyChainCheck,
    ValidationMatrixConfig,
    WitnessEvidenceSummary,
    apply_claim_downgrade_rules,
    audit_claim_text,
    evaluate_artifact_hygiene,
    evaluate_docs_consistency,
    evaluate_release_candidate,
    evaluate_supply_chain_checks,
    evaluate_validation_matrix,
    score_evidence_completeness,
    validate_evidence_bundle,
)
from codontrace.genesis.scientific_evidence import EvidenceCompletenessScore


def _record(
    evidence_type: str,
    source_component: str,
    *,
    evidence_id: str = "e1",
    seed: int = 1,
    config_digest: str = "cfg",
    trace_digest: str = "trace",
    replay_digest: str = "",
    qd_archive_digest: str = "",
    limitation_ids: tuple[str, ...] = ("lim",),
) -> EvidenceRecord:
    return EvidenceRecord(
        evidence_id,
        evidence_type,
        source_component,
        seed,
        config_digest,
        trace_digest,
        replay_digest=replay_digest,
        qd_archive_digest=qd_archive_digest,
        limitation_ids=limitation_ids,
    )


def test_validation_matrix_does_not_count_config_digest_as_d0() -> None:
    bundle = EvidenceBundle(
        "b",
        "0.3.0a0",
        (_record("trace", "trace", config_digest="cfg"),),
        claim_limitations=("lim",),
    )
    result = evaluate_validation_matrix(
        bundle,
        ValidationMatrixConfig(
            require_d0=True,
            require_qd=False,
            require_ablation=False,
            require_replay=False,
            require_multi_seed=False,
        ),
    )
    assert not result.succeeded
    assert "d0" in result.missing_components
    assert result.claim_ceiling == "CANDIDATE"


def test_validation_matrix_counts_explicit_evidence_types() -> None:
    bundle = EvidenceBundle(
        "b",
        "0.3.0a0",
        (
            _record("d0_baseline", "d0_baseline", evidence_id="d0", seed=1),
            _record("trace", "trace", evidence_id="qd", seed=2, qd_archive_digest="qd"),
            _record("replay", "trace", evidence_id="replay", seed=3, replay_digest="replay"),
            _record("ablation_comparison", "ablation", evidence_id="ab", seed=4),
        ),
        claim_limitations=("lim",),
    )
    result = evaluate_validation_matrix(bundle, ValidationMatrixConfig(min_seed_count=3))
    assert result.succeeded
    assert result.claim_ceiling == "EVIDENCE_SUPPORTED"


def test_claim_audit_blocks_a22_overclaims_and_allows_safe_context() -> None:
    assert not audit_claim_text("CodonTrace achieves open-endedness.").succeeded
    assert not audit_claim_text("This is proof of causal learning.").succeeded
    assert not audit_claim_text("Knowledge transfer is demonstrated.").succeeded
    assert not audit_claim_text("This library is benchmark-leading.").succeeded
    assert audit_claim_text("CodonTrace does not achieve open-endedness.").succeeded
    assert audit_claim_text("This is not proof of knowledge transfer.").succeeded
    assert audit_claim_text("Evidence scaffold only.").succeeded


def test_supply_chain_fail_forces_succeeded_false() -> None:
    result = evaluate_supply_chain_checks(
        (SupplyChainCheck("hosted_ci", ReleaseGateStatus.FAIL),), strict=False
    )
    assert not result.succeeded
    assert result.blocker_count == 1
    constructed = type(result)(True, True, result.checks)
    assert not constructed.succeeded


def test_release_candidate_duplicate_gates_and_pip_audit_exception() -> None:
    required = ReleaseReadinessProfile.pypi().required_gates
    gates = []
    for name in required:
        status = ReleaseGateStatus.NOT_COMPLETED if name == "pip_audit" else ReleaseGateStatus.PASS
        gates.append(ReleaseGateRecord(name, status))
    gates.append(ReleaseGateRecord("pytest", ReleaseGateStatus.FAIL))
    checklist = ReleaseCandidateChecklist(
        "0.3.0a0",
        "artifact.zip",
        tuple(gates),
        api_snapshot_digest="api",
        claim_audit_digest="claim",
        validation_bundle_digest="validation",
        citation_digest="citation",
        limitations_digest="limitations",
        gate_exceptions=(
            ReleaseGateException("pip_audit", True, "sandbox DNS unavailable", "maintainer"),
        ),
    )
    decision = evaluate_release_candidate(checklist, ReleaseReadinessProfile.pypi())
    assert "pytest" in decision.duplicate_gate_names
    assert not decision.accepted_for_pypi
    assert "approved_exception:pip_audit" in decision.warning_reasons


def test_pip_audit_exception_policy_without_duplicate_allows_warning_for_pypi() -> None:
    gates = tuple(
        ReleaseGateRecord(
            name, ReleaseGateStatus.NOT_COMPLETED if name == "pip_audit" else ReleaseGateStatus.PASS
        )
        for name in ReleaseReadinessProfile.pypi().required_gates
    )
    checklist = ReleaseCandidateChecklist(
        "0.3.0a0",
        "artifact.zip",
        gates,
        api_snapshot_digest="api",
        claim_audit_digest="claim",
        validation_bundle_digest="validation",
        citation_digest="citation",
        limitations_digest="limitations",
        gate_exceptions=(ReleaseGateException("pip_audit", True, "documented network issue"),),
    )
    decision = evaluate_release_candidate(checklist, ReleaseReadinessProfile.pypi())
    assert not decision.accepted_for_pypi
    assert decision.accepted_for_pypi_with_exception
    assert decision.accepted_with_exceptions
    assert "security_exception:pip_audit" in decision.warning_reasons


def test_evidence_bundle_unknown_limitation_id_fails() -> None:
    bundle = EvidenceBundle(
        "b",
        "0.3.0a0",
        (_record("trace", "trace", limitation_ids=("unknown",)),),
        claim_limitations=("lim",),
    )
    result = validate_evidence_bundle(bundle)
    assert not result.succeeded
    assert result.unknown_limitation_ids == ("unknown",)


def test_release_readiness_artifact_and_docs_consistency_objects() -> None:
    assert ReleaseReadinessProfile.prepublic().digest()
    hygiene = evaluate_artifact_hygiene(("src/codontrace/__init__.py", "dist/pkg.whl"), "pkg.zip")
    assert isinstance(hygiene, ArtifactHygieneRecord)
    assert not hygiene.passed
    docs = evaluate_docs_consistency(
        {"README.md": "CodonTrace v0.2.0a20: old label. It does not prove discovery."},
        "0.3.0a0",
    )
    assert not docs.passed
    assert docs.stale_version_mentions


def test_scientific_evidence_pack_and_claim_downgrade() -> None:
    pack = ScientificEvidencePack(
        "pack",
        "0.3.0a0",
        d0_summary=D0EvidenceSummary("d0", 3, 3, ("novelty",), "normalized_l1", "threshold"),
        qd_summary=QDEvidenceSummary("qd", 1, 4, 0.25, 1.5, 1.5, 0, "schema"),
        witness_summary=WitnessEvidenceSummary(
            "w", "EVIDENCE_SUPPORTED", "scaffold", "d0", "trace", "", "ab", 3
        ),
        claim_audit_digest="claim",
        limitation_ids=("lim",),
        claim_ceiling="EVIDENCE_SUPPORTED",
    )
    restored = ScientificEvidencePack.from_dict(pack.to_dict())
    assert restored.digest() == pack.digest()
    limitation = LimitationRecord(
        "lim",
        LimitationSeverity.CRITICAL,
        "d0",
        "missing replay",
        "blocks discovery claims",
        blocks_claims=(ClaimType.OPEN_ENDED_DISCOVERY_PROOF,),
    )
    result = apply_claim_downgrade_rules(pack, (limitation,))
    assert isinstance(result, ClaimDowngradeResult)
    assert result.final_ceiling in {"NONE", "CANDIDATE"}
    assert "PROOF" not in result.final_ceiling


def test_evidence_completeness_score_is_completeness_only() -> None:
    pack = ScientificEvidencePack(
        "pack", "0.3.0a0", claim_audit_digest="claim", limitation_ids=("lim",)
    )
    score = score_evidence_completeness(pack, "mature_alpha")
    assert isinstance(score, EvidenceCompletenessScore)
    assert 0.0 <= score.score_0_to_1 <= 1.0
    assert "completeness_only_not_truth_or_proof" in score.warnings
