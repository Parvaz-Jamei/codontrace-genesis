from codontrace.genesis import GenesisEngine
from codontrace.genesis.runtime_profiles import GenesisRuntimeProfile
from codontrace.genesis.evidence_consistency import audit_result_evidence_consistency
from codontrace.genesis.runtime_wiring_audit import integration_feature_catalog


def _run():
    return GenesisEngine.from_spec(GenesisRuntimeProfile.toolchain_pilot_world(seed=29, tick_count=2)).run_ticks()


def test_evidence_consistency_passes_on_real_phase_a_b_result():
    result = _run()
    required = tuple(item.record_class_path for item in integration_feature_catalog())
    out = audit_result_evidence_consistency(result, required_class_paths=required)
    assert out["passed"], out["issues"]


def test_evidence_consistency_rejects_positive_not_run_claim():
    out = audit_result_evidence_consistency(claims=[{"status":"allowed", "required_evidence":["not_run:claim"]}])
    assert not out["passed"]
    assert any(i["code"] == "positive_claim_with_non_real_digest" for i in out["issues"])


def test_evidence_consistency_rejects_positive_claim_without_evidence():
    out = audit_result_evidence_consistency(claims=[{"status":"allowed", "required_evidence":[]}])
    assert not out["passed"]
