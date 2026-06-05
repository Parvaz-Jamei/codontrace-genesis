import pytest

from codontrace.genesis import EvidenceManifest
from codontrace.genesis.evidence import canonical_digest


def test_evidence_manifest_has_claim_ready_schema_and_stable_aggregate_digest():
    left = EvidenceManifest(
        schema_version="evidence_manifest_v2",
        producer_version="phase1",
        library_version="0.3.0b1",
        config_digest="cfg",
        source_digest="src",
        protocol_digest="proto",
        artifact_digests=("b", "a"),
        artifact_digest_map={"z": "2", "a": "1"},
        feature_status={"qd": "measured", "capsule": "empty_but_available"},
    )
    right = EvidenceManifest(
        schema_version="evidence_manifest_v2",
        producer_version="phase1",
        library_version="0.3.0b1",
        config_digest="cfg",
        source_digest="src",
        protocol_digest="proto",
        artifact_digests=("a", "b"),
        artifact_digest_map={"a": "1", "z": "2"},
        feature_status={"capsule": "empty_but_available", "qd": "measured"},
    )
    assert left.validate_claim_ready_schema() == ()
    assert left.artifact_digest == right.artifact_digest
    assert left.digest() == right.digest()
    assert left.to_dict()["determinism_policy"] == "canonical_json_sha256_no_time_no_object_id"


def test_evidence_manifest_rejects_invalid_status_and_unstable_digest_payload():
    with pytest.raises(ValueError):
        EvidenceManifest("v", "p", "l", "c", "s", "proto", feature_status={"qd": "dummy"})
    with pytest.raises(ValueError):
        canonical_digest({"bad": object()})
