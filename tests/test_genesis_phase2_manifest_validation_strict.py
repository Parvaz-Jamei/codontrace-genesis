from codontrace.genesis.artifacts import (
    PHASE2_MANIFEST_FIELDS,
    manifest_from_parts,
    validate_phase2_manifest_fields,
)


def _manifest(runtime_hashes, protocol_statuses):
    return manifest_from_parts(
        run_id="r",
        seed=1,
        config={},
        codon_table_hash="ct",
        genome_spec_hash="gs",
        initial_population_hash="pop",
        tick_count=0,
        replay_digest="replay",
        runtime_hashes=runtime_hashes,
        protocol_statuses=protocol_statuses,
    )


def test_phase2_manifest_rejects_measured_status_without_hash():
    manifest = _manifest({}, {f"phase2.{name}.status": "measured" for name in PHASE2_MANIFEST_FIELDS})
    result = validate_phase2_manifest_fields(manifest)
    assert not result.passed
    assert "genome_program_digest" in result.missing_hashes


def test_phase2_manifest_rejects_placeholder_hash_for_measured_status():
    manifest = _manifest(
        {name: "placeholder" for name in PHASE2_MANIFEST_FIELDS},
        {f"phase2.{name}.status": "measured" for name in PHASE2_MANIFEST_FIELDS},
    )
    result = validate_phase2_manifest_fields(manifest)
    assert not result.passed
    assert "genome_program_digest" in result.placeholder_hashes


def test_phase2_manifest_not_run_is_not_claim_eligible():
    manifest = _manifest(
        {name: "not_run" for name in PHASE2_MANIFEST_FIELDS},
        {f"phase2.{name}.status": "not_run" for name in PHASE2_MANIFEST_FIELDS},
    )
    result = validate_phase2_manifest_fields(manifest)
    assert result.passed


def test_phase2_manifest_provisional_requires_reason_and_digest():
    hashes = {name: f"digest-{name}" for name in PHASE2_MANIFEST_FIELDS}
    statuses = {f"phase2.{name}.status": "provisional" for name in PHASE2_MANIFEST_FIELDS}
    missing_reason = validate_phase2_manifest_fields(_manifest(hashes, statuses))
    assert not missing_reason.passed
    assert "protocol_statuses.phase2.genome_program_digest.status_reason" in missing_reason.missing_hashes
    statuses.update({f"phase2.{name}.status_reason": "runtime_protocol_incomplete" for name in PHASE2_MANIFEST_FIELDS})
    assert validate_phase2_manifest_fields(_manifest(hashes, statuses)).passed
