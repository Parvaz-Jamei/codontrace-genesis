from __future__ import annotations

from pathlib import Path

import pytest

from codontrace.errors import ConfigurationError
from codontrace.genesis import (
    AblationFactor,
    AblationRunRecord,
    APIAuditResult,
    BehaviorDescriptorSchema,
    ClaimType,
    PublicAPISymbol,
    QDArchive,
    QDArchiveBatchUpdateResult,
    QDArchiveConfig,
    QDArchiveItemUpdateRecord,
    QDElite,
    StatisticalProtocolConfig,
    ValidationBundle,
    ValidationIssue,
    ValidationResult,
    ValidationRunRecord,
    ValidationScenario,
    audit_claim_text,
    build_compatibility_snapshot,
    collect_genesis_public_api,
    compare_ablation_runs,
    update_qd_archive_many,
    validate_digest_stability,
    validate_genesis_exports,
    validate_no_app_drift_project_metadata,
    validate_roundtrip,
)
from codontrace.genesis.claim_audit import audit_docs_claims
from codontrace.genesis.example_smoke import ExampleSmokeCase, describe_example_smoke_cases


def _schema() -> BehaviorDescriptorSchema:
    return BehaviorDescriptorSchema(
        descriptor_names=("novelty", "complexity"),
        bins_per_descriptor={"novelty": 4, "complexity": 4},
        min_values={"novelty": 0.0, "complexity": 0.0},
        max_values={"novelty": 4.0, "complexity": 4.0},
    )


def _elite(name: str, fitness: float, novelty: float, complexity: float) -> QDElite:
    descriptor = {"novelty": novelty, "complexity": complexity}
    from codontrace.genesis import assign_behavior_bin

    return QDElite(
        organism_id=name,
        fitness=fitness,
        behavior_descriptor=descriptor,
        behavior_bin=assign_behavior_bin(descriptor, _schema()),
        genome_digest=f"genome:{name}",
        trace_digest=f"trace:{name}",
    )


def test_statistical_protocol_default_constructible_and_strict_mode() -> None:
    default = StatisticalProtocolConfig()
    assert not default.require_pre_registered_metrics
    assert StatisticalProtocolConfig.from_dict(default.to_dict()).digest() == default.digest()
    with pytest.raises(ConfigurationError):
        StatisticalProtocolConfig(require_pre_registered_metrics=True, metric_names=())
    strict = StatisticalProtocolConfig(
        require_pre_registered_metrics=True, metric_names=("fitness",)
    )
    assert strict.metric_names == ("fitness",)


def test_qd_keep_one_elite_false_fails_clearly() -> None:
    with pytest.raises(ConfigurationError, match="reserved"):
        QDArchiveConfig(schema=_schema(), keep_one_elite_per_bin=False)


def test_qd_batch_update_result_is_compact() -> None:
    archive = QDArchive.empty(QDArchiveConfig(schema=_schema()))
    candidates = tuple(
        _elite(f"elite-{i}", float(i), float(i % 4), float((i * 2) % 4)) for i in range(20)
    )
    batch = update_qd_archive_many(archive, candidates)
    payload = batch.to_dict()
    assert isinstance(batch, QDArchiveBatchUpdateResult)
    assert "update_records" in payload
    assert "update_results" not in payload
    assert all("archive" not in item for item in payload["update_records"])
    assert all(isinstance(item, QDArchiveItemUpdateRecord) for item in batch.update_records)
    assert QDArchiveBatchUpdateResult.from_dict(payload).digest() == batch.digest()


def test_ablation_factor_control_vs_intervention_and_duplicate_seeds() -> None:
    assert AblationFactor.control().factor_type == "control"
    with pytest.raises(ConfigurationError):
        AblationFactor("empty", "Empty", factor_type="mixed")
    assert AblationFactor(
        "no_adf", "No ADF", disabled_components=("adf",), factor_type="disable_component"
    )
    assert AblationFactor(
        "cfg",
        "Config override",
        config_overrides={"adf_enabled": False},
        factor_type="config_override",
    )
    baseline = (
        AblationRunRecord("b1", "baseline", 1, "cfg", "trace", "behavior", 1.0),
        AblationRunRecord("b2", "baseline", 1, "cfg", "trace", "behavior", 1.1),
    )
    treatment = (AblationRunRecord("t1", "no_adf", 1, "cfg", "trace", "behavior", 0.5),)
    result = compare_ablation_runs(baseline, treatment)
    assert not result.succeeded
    assert result.duplicate_baseline_seeds == (1,)
    assert "duplicate_seed" in result.reasons


def test_digest_stability_after_input_dict_mutation() -> None:
    metadata = {"source": "before"}
    factor = AblationFactor(
        "cfg", "Config", config_overrides=metadata, factor_type="config_override"
    )
    before = factor.digest()
    metadata["source"] = "after"
    assert factor.digest() == before

    descriptor = {"novelty": 1.0, "complexity": 1.0}
    elite = QDElite("o", 1.0, descriptor, _elite("tmp", 1.0, 1.0, 1.0).behavior_bin, "g", "t")
    elite_digest = elite.digest()
    descriptor["novelty"] = 3.0
    assert elite.digest() == elite_digest


def test_api_audit_and_validation_helpers() -> None:
    symbols = collect_genesis_public_api(("PublicAPISymbol", "validate_genesis_exports"))
    assert all(isinstance(item, PublicAPISymbol) for item in symbols)
    assert {item.kind for item in symbols} >= {"dataclass", "function"}
    audit = validate_genesis_exports(("PublicAPISymbol", "validate_genesis_exports"))
    assert isinstance(audit, APIAuditResult)
    assert audit.succeeded
    assert not validate_genesis_exports(("DefinitelyMissingSymbol",)).succeeded
    snapshot = build_compatibility_snapshot(
        version="0.3.0a0",
        public_symbols=("A", "B"),
        examples=("examples/genesis_api_audit.py",),
        docs_sections=("api",),
    )
    assert snapshot.digest() == type(snapshot).from_dict(snapshot.to_dict()).digest()

    result = validate_roundtrip(QDArchiveConfig(schema=_schema()))
    assert isinstance(result, ValidationResult)
    assert result.succeeded
    assert validate_digest_stability(QDArchiveConfig(schema=_schema())).succeeded
    assert validate_no_app_drift_project_metadata(Path.cwd()).succeeded
    issue = ValidationIssue("x", "warning", "code", "message")
    assert issue.digest() == ValidationIssue.from_dict(issue.to_dict()).digest()


def test_research_validation_bundle_and_claim_audit() -> None:
    scenario = ValidationScenario(
        "s1",
        "D0/QD evidence smoke",
        required_components=("d0", "qd"),
        config_digest="cfg",
        expected_evidence=("trace",),
        non_claims=("no AGI",),
    )
    record = ValidationRunRecord("run1", "s1", 1, "trace", "behavior", qd_archive_digest="qd")
    bundle = ValidationBundle(
        "bundle",
        "0.3.0a0",
        scenarios=(scenario,),
        run_records=(record,),
        claim_limitations=("no proof",),
    )
    assert ValidationBundle.from_dict(bundle.to_dict()).digest() == bundle.digest()

    blocked = audit_claim_text("This proves open-ended discovery and AGI")
    assert not blocked.succeeded
    assert any(item.claim_type is ClaimType.AGI for item in blocked.blocked_claims)
    allowed = audit_claim_text("CodonTrace is a library feature scaffold")
    assert allowed.succeeded
    docs = audit_docs_claims({"README": "library feature scaffold"})
    assert docs.succeeded


def test_example_smoke_contracts_do_not_execute() -> None:
    case = ExampleSmokeCase("claim", "examples/genesis_claim_audit.py", ("codontrace.genesis",))
    result = describe_example_smoke_cases((case,))[0]
    assert not result.attempted
    assert not result.succeeded
    assert not result.executed
    assert result.execution_status == "contract_only_not_executed"
    assert result.success_status == "not_attempted"
    assert result.created_files_count == 0


def test_docs_no_a19_capsule_heading() -> None:
    docs = "\n".join(
        path.read_text(encoding="utf-8")
        for path in [
            Path("README.md"),
            Path("docs/api.md"),
            Path("docs/concepts.md"),
            Path("docs/non_goals.md"),
        ]
    )
    assert "legacy Causal Capsule + Nexus Stigmergy" not in docs
