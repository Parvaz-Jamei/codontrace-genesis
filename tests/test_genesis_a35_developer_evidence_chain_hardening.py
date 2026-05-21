from __future__ import annotations

from codontrace.genesis.engine import GenesisEngine, GenesisEngineConfig, GenesisExperimentSpec


def _result():
    spec = GenesisExperimentSpec(
        tick_count=1,
        engine_config=GenesisEngineConfig(qd_mode="off"),
    )
    return GenesisEngine.from_spec(spec).run_ticks()


def test_evidence_manifest_covers_every_public_export_envelope() -> None:
    result = _result()
    export_names = {item.schema_version.removesuffix("_export_v1") for item in result.export_status_records}
    manifest_names = set(result.evidence_manifest.artifact_digest_map)

    missing = export_names - manifest_names
    assert missing == set()
    assert set(result.evidence_manifest.feature_status) >= export_names


def test_result_to_dict_contains_claim_ready_public_evidence_surfaces() -> None:
    result = _result()
    payload = result.to_dict()

    assert "evidence_manifest" in payload
    assert "export_status_records" in payload
    assert "output_completeness_records" in payload
    assert payload["evidence_manifest"]["artifact_digest_map"]
    assert len(payload["export_status_records"]) == len(result.export_status_records)


def test_manifest_and_result_payload_remain_deterministic_after_export_chain_hardening() -> None:
    first = _result()
    second = _result()

    assert first.digest() == second.digest()
    assert first.evidence_manifest.digest() == second.evidence_manifest.digest()
    assert first.to_dict()["evidence_manifest"] == second.to_dict()["evidence_manifest"]


def test_active_qd_search_objects_are_star_import_public_exports() -> None:
    import codontrace.genesis as genesis

    expected = {
        "QDSearchConfig",
        "QDSearchRunner",
        "QDSearchRunResult",
        "QDSearchStepResult",
        "QDSearchArchive",
        "QDSearchCandidate",
        "QDParentSelection",
        "QDEmitter",
        "MutationEmitter",
        "RandomEmitter",
        "ArchiveSamplingEmitter",
        "NoveltyBiasedEmitter",
        "qd_candidate_from_dict",
    }
    missing = {name for name in expected if name not in genesis.__all__}
    assert missing == set()
