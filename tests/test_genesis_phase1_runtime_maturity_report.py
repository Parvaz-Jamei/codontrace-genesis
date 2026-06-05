from __future__ import annotations

import pytest

from codontrace.genesis.engine import GenesisEngine, GenesisEngineConfig, GenesisExperimentSpec
from codontrace.genesis.evidence import EvidenceManifest
from codontrace.genesis.phase1_runtime_maturity import (
    adf_usefulness_audit,
    attach_phase1_report_to_manifest,
    build_phase1_runtime_maturity_report,
    capsule_control_audit,
    causal_intervention_audit,
    phase1_public_api_entries,
)
from codontrace.genesis.population import MutationConfig, ReproductionConfig
from codontrace.genesis.replay_integrity import replay_digest_class_policies


def _birth_run() -> object:
    spec = GenesisExperimentSpec(
        genome_bits=("111",),
        seed=44,
        tick_count=1,
        population_max=4,
        initial_runtime_atp=20.0,
        reproduction_config=ReproductionConfig(max_population=4, min_runtime_atp=1.0),
        mutation_config=MutationConfig(bit_flip_rate=1.0),
        engine_config=GenesisEngineConfig(enable_qd=True, qd_mode="archive_only"),
    )
    return GenesisEngine.from_spec(spec).run_ticks()


def test_engine_result_exposes_phase1_runtime_maturity_report() -> None:
    result = _birth_run()
    report = result.phase1_runtime_maturity_report
    assert report.record_digest
    assert report.reproduction_records
    assert any(item.feature == "birth_reproduction_gate" for item in report.feature_statuses)
    matrix = result.phase1_runtime_maturity_matrix
    assert matrix
    assert {row["feature"] for row in matrix} >= {
        "mutation_operator_maturity",
        "birth_reproduction_gate",
        "runtime_qd_pareto_qd",
    }


def test_phase1_report_can_be_attached_to_evidence_manifest_without_mutation() -> None:
    report = build_phase1_runtime_maturity_report(_birth_run())
    manifest = EvidenceManifest(
        schema_version="test_manifest_v1",
        producer_version="pytest",
        library_version="0.3.0b1",
        config_digest="config",
        source_digest="source",
        protocol_digest="protocol",
        feature_status={},
    )
    updated = attach_phase1_report_to_manifest(manifest, report)
    assert updated is not manifest
    assert updated.artifact_digest_map["phase1_runtime_maturity_report"] == report.record_digest
    assert updated.feature_status["birth_reproduction_gate"] in {"measured", "provisional"}
    assert updated.validate_claim_ready_schema() == ()


def test_capsule_controls_keep_negative_cases_claim_ineligible() -> None:
    record = capsule_control_audit(
        capsule_id="cap-1",
        source_id="s",
        target_id="t",
        control_case="misleading_capsule",
        adopted=True,
        benefit=-1.0,
        cost=0.5,
    )
    assert record.claim_eligible is False
    assert record.capsule_social_transfer_score < 0.0
    with pytest.raises(ValueError):
        record.__class__(**{**record.to_dict(), "claim_eligible": True})


def test_adf_single_action_and_metadata_only_causal_evidence_are_rejected() -> None:
    with pytest.raises(ValueError):
        adf_usefulness_audit(
            macro_id="m1",
            source_trace_digest="trace",
            source_map_digest="map",
            expanded_actions=("WAIT",),
            reuse_count=2,
            compression_ratio=2.0,
            task_delta=1.0,
        ).__class__(**{
            **adf_usefulness_audit(
                macro_id="m1",
                source_trace_digest="trace",
                source_map_digest="map",
                expanded_actions=("WAIT",),
                reuse_count=2,
                compression_ratio=2.0,
                task_delta=1.0,
            ).to_dict(),
            "claim_eligible": True,
        })
    with pytest.raises(ValueError):
        causal_intervention_audit(
            intervention_id="i1",
            intervention_type="remove_memory",
            target_id="memory",
            baseline_digest="same",
            treatment_digest="same",
            outcome_before=1.0,
            outcome_after=2.0,
            event_graph_digest="event",
            causal_graph_digest="graph",
            confidence_status="validated",
        )


def test_phase1_public_api_entries_and_replay_policies_cover_new_symbols() -> None:
    entries = phase1_public_api_entries()
    assert any(item["symbol"] == "Phase1RuntimeMaturityReport" for item in entries)
    policy_paths = {item.class_path for item in replay_digest_class_policies()}
    assert "codontrace.genesis.phase1_runtime_maturity.Phase1RuntimeMaturityReport" in policy_paths


def test_phase1_report_is_wired_into_to_dict_exports_and_manifest() -> None:
    result = _birth_run()
    payload = result.to_dict()
    report = result.phase1_runtime_maturity_report
    assert payload["phase1_runtime_maturity_report"]["record_digest"] == report.record_digest
    export_names = {
        item["schema_version"].removesuffix("_export_v1")
        for item in payload["export_status_records"]
    }
    assert "phase1_runtime_maturity_report" in export_names
    assert "phase1_runtime_maturity_matrix" in export_names
    manifest = payload["evidence_manifest"]
    assert manifest["artifact_digest_map"]["phase1_runtime_maturity_report"] == report.record_digest
    assert manifest["feature_status"]["phase1_runtime_maturity_report"] == "measured"
    assert manifest["feature_status"]["birth_reproduction_gate"] in {"measured", "provisional"}


def test_phase1_report_consumes_existing_engine_toolchain_surface() -> None:
    result = _birth_run()
    # A zero-toolchain run must still expose the official engine surface as an
    # explicit empty_but_available Phase-1 toolchain status rather than silently
    # bypassing the old tool_chain_records path.
    assert isinstance(result.tool_chain_records, tuple)
    report = result.phase1_runtime_maturity_report
    status = {item.feature: item for item in report.feature_statuses}
    assert status["toolchain_failures_preconditions"].status in {
        "empty_but_available",
        "complete_limited_claim",
    }
