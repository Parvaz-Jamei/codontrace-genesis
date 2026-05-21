from pathlib import Path

from codontrace.genesis import (
    ClaimType,
    ComponentToggle,
    ComponentToggleMatrix,
    EvidenceBundle,
    EvidenceRecord,
    FailureModeRecord,
    LimitationRecord,
    LimitationSeverity,
    ReleaseCandidateChecklist,
    ReleaseGateRecord,
    ReleaseGateStatus,
    ScenarioSuite,
    SeedMatrix,
    SupplyChainAuditResult,
    SupplyChainCheck,
    ValidationMatrixConfig,
    ValidationScenario,
    audit_claim_text,
    audit_docs_claims,
    collect_genesis_public_api,
    evaluate_release_candidate,
    evaluate_validation_matrix,
    validate_citation_metadata,
    validate_evidence_bundle,
    validate_genesis_exports,
    validate_no_app_drift_project_metadata,
    validate_release_evidence_consistency,
    validate_scenario_suite,
)


def test_claim_audit_blocks_broad_overclaims_and_allows_safe_negation() -> None:
    assert not audit_claim_text("CodonTrace demonstrates artificial life.").succeeded
    assert not audit_claim_text("CodonTrace proves consciousness.").succeeded
    assert not audit_claim_text("This is state of the art.").succeeded
    assert not audit_claim_text("CodonTrace achieves open-ended discovery.").succeeded
    assert audit_claim_text("CodonTrace does not prove open-ended discovery.").succeeded
    assert audit_claim_text("CodonTrace is a library-first research scaffold.").succeeded
    docs = audit_docs_claims({"README.md": "CodonTrace proves consciousness."})
    assert not docs.succeeded
    assert "README.md" in docs.findings[0].text


def test_validate_genesis_exports_checks_real_symbols_and_kind_inference() -> None:
    assert not validate_genesis_exports(("DefinitelyMissingSymbol",)).succeeded
    assert validate_genesis_exports(("PublicAPISymbol", "validate_genesis_exports")).succeeded
    symbols = collect_genesis_public_api(("PublicAPISymbol", "validate_genesis_exports"))
    by_name = {item.name: item.kind for item in symbols}
    assert by_name["PublicAPISymbol"] == "dataclass"
    assert by_name["validate_genesis_exports"] == "function"


def test_no_app_drift_and_citation_validation(tmp_path: Path) -> None:
    root = tmp_path
    (root / "src" / "codontrace").mkdir(parents=True)
    (root / "src" / "codontrace" / "py.typed").write_text("", encoding="utf-8")
    (root / "pyproject.toml").write_text(
        '[project]\nname="codontrace"\nversion="0.3.0a1"\ndependencies=[]\n',
        encoding="utf-8",
    )
    (root / "CITATION.cff").write_text(
        'cff-version: "1.2.0"\ntitle: "CodonTrace"\nmessage: "Cite this software."\n'
        'version: "0.3.0a1"\nauthors:\n'
        '  - family-names: "Jamei"\nlicense: "MIT"\nrepository-code: "https://example.test"\n',
        encoding="utf-8",
    )
    assert validate_no_app_drift_project_metadata(root).succeeded
    assert validate_citation_metadata(root).succeeded
    (root / "pyproject.toml").write_text(
        '[project]\nname="codontrace"\nversion="0.3.0a1"\ndependencies=["fastapi"]\n'
        '[project.scripts]\nct="codontrace:main"\n',
        encoding="utf-8",
    )
    assert not validate_no_app_drift_project_metadata(root).succeeded


def test_release_evidence_consistency_rc_mode() -> None:
    result = validate_release_evidence_consistency(
        {
            "version": "0.3.0a0",
            "artifact": "codontrace-alpha-regression-fixture.zip",
            "hosted_ci": "NOT RUN",
            "wheel_smoke": "PASS",
        },
        release_candidate=True,
    )
    assert not result.succeeded
    assert any(issue.code == "rc_gate_required" for issue in result.issues)


def test_scenario_suite_detects_duplicate_seeds_and_roundtrips() -> None:
    scenario = ValidationScenario("s1", "demo", ("d0",), "cfg", ("trace",), ("no proof",))
    suite = ScenarioSuite(
        "suite",
        "demo",
        (scenario,),
        SeedMatrix((1, 1, 2), 3),
        ComponentToggleMatrix((ComponentToggle("d0", True),)),
        ("trace",),
        ("alpha limitations",),
    )
    result = validate_scenario_suite(suite)
    assert not result.succeeded
    assert result.duplicate_seeds == (1,)
    assert ScenarioSuite.from_dict(suite.to_dict()).digest() == suite.digest()


def test_evidence_bundle_requires_digests() -> None:
    record = EvidenceRecord("e1", "trace", "d0", 1, "", "", limitation_ids=())
    bundle = EvidenceBundle("b", "0.3.0a0", (record,), claim_limitations=("no proof",))
    result = validate_evidence_bundle(bundle)
    assert not result.succeeded
    assert result.missing_trace_digests == ("e1",)
    assert EvidenceBundle.from_dict(bundle.to_dict()).digest() == bundle.digest()


def test_limitation_and_failure_mode_roundtrip() -> None:
    limitation = LimitationRecord(
        "lim1",
        LimitationSeverity.CRITICAL,
        "qd",
        "incomplete",
        "blocks claims",
        blocks_claims=(ClaimType.OPEN_ENDED_DISCOVERY_PROOF,),
    )
    assert LimitationRecord.from_dict(limitation.to_dict()).digest() == limitation.digest()
    failure = FailureModeRecord("f1", "qd", "duplicate", "replaced", "audit", True, seed=3)
    assert FailureModeRecord.from_dict(failure.to_dict()).digest() == failure.digest()


def test_validation_matrix_conservative_claim_ceiling() -> None:
    record = EvidenceRecord(
        "e1",
        "trace",
        "d0",
        1,
        "cfg",
        "trace",
        replay_digest="replay",
        qd_archive_digest="qd",
        limitation_ids=("lim",),
    )
    bundle = EvidenceBundle("b", "0.3.0a0", (record,), claim_limitations=("no proof",))
    result = evaluate_validation_matrix(
        bundle, ValidationMatrixConfig(require_ablation=True, min_seed_count=3)
    )
    assert not result.succeeded
    assert result.claim_ceiling == "CANDIDATE"
    assert "ablation" in result.missing_components


def test_release_candidate_and_supply_chain_objects() -> None:
    gates = tuple(
        ReleaseGateRecord(name, ReleaseGateStatus.PASS)
        for name in (
            "compileall",
            "pytest",
            "ruff",
            "mypy",
            "build",
            "twine",
            "wheel_smoke",
            "claim_audit",
            "api_audit",
            "zip_hygiene",
        )
    )
    checklist = ReleaseCandidateChecklist(
        "0.3.0a0",
        "codontrace-alpha-regression-fixture.zip",
        gates,
        api_snapshot_digest="api",
        claim_audit_digest="claim",
    )
    decision = evaluate_release_candidate(checklist)
    assert decision.accepted_for_testpypi
    assert not decision.accepted_for_pypi
    assert ReleaseCandidateChecklist.from_dict(checklist.to_dict()).digest() == checklist.digest()
    audit = SupplyChainAuditResult(
        True, True, (SupplyChainCheck("hosted_ci", ReleaseGateStatus.NOT_RUN),)
    )
    assert SupplyChainAuditResult.from_dict(audit.to_dict()).digest() == audit.digest()
