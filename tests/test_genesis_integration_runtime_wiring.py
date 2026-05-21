from codontrace.genesis import GenesisEngine
from codontrace.genesis.runtime_profiles import GenesisRuntimeProfile
from codontrace.genesis.runtime_wiring_audit import audit_runtime_wiring, integration_feature_catalog


def _run():
    return GenesisEngine.from_spec(GenesisRuntimeProfile.toolchain_pilot_world(seed=23, tick_count=2)).run_ticks()


def test_integration_runtime_wiring_catalog_has_runtime_and_tests():
    catalog = integration_feature_catalog()
    assert catalog
    assert all(item.runtime_producer for item in catalog)
    assert all(item.positive_test and item.negative_test for item in catalog)


def test_integration_runtime_wiring_passes_against_real_result():
    result = _run()
    audit = audit_runtime_wiring(result)
    assert audit["passed"], audit["issues"]
    assert any(row["feature_name"] == "release_evidence_pack" for row in audit["features"])
