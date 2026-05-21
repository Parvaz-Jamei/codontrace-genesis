from codontrace.genesis import GenesisEngine
from codontrace.genesis.runtime_profiles import GenesisRuntimeProfile
from codontrace.genesis.replay_integrity import replay_digest_class_policies


def _run():
    return GenesisEngine.from_spec(GenesisRuntimeProfile.toolchain_pilot_world(seed=3, tick_count=2)).run_ticks()


def test_phase_b_report_is_runtime_wired_to_result_dict_exports_and_manifest():
    result = _run()
    report = result.phase_b_scientific_maturity_report
    payload = result.to_dict()
    assert payload["phase_b_scientific_maturity_report"]["record_digest"] == report.digest()
    assert payload["phase_b_scientific_maturity_matrix"]
    exports = result.export_envelopes_by_name
    assert exports["phase_b_scientific_maturity_report"].feature_status == "measured"
    assert exports["phase_b_discovery_events"].records
    manifest = result.evidence_manifest
    assert manifest.artifact_digest_map["phase_b_scientific_maturity_report"] == report.digest()
    assert manifest.feature_status["phase_b_scientific_maturity_report"] == "measured"


def test_phase_b_report_consumes_phase_a_runtime_digest_and_downgrades_strong_claims():
    result = _run()
    phase1_digest = result.phase1_runtime_maturity_report.record_digest
    report = result.phase_b_scientific_maturity_report
    assert report.phase1_runtime_maturity_digest == phase1_digest
    assert report.discovery_events[0].blocked_reason == "single_seed_runtime_discovery_descriptive_only"
    assert report.oee_results[0].blocked_reason == "single_seed_oee_descriptive_only"
    assert not report.release_packs[0].claim_ready


def test_phase_b_replay_policy_registry_covers_public_runtime_records():
    policies = {item.class_path for item in replay_digest_class_policies()}
    required = {
        "codontrace.genesis.phase_b_scientific_maturity.PhaseBScientificMaturityReport",
        "codontrace.genesis.phase_b_scientific_maturity.DiscoveryEvent",
        "codontrace.genesis.phase_b_scientific_maturity.AblationWitness",
        "codontrace.genesis.phase_b_scientific_maturity.HeldoutEvaluationResult",
        "codontrace.genesis.phase_b_scientific_maturity.OEEClaimEligibilityResult",
        "codontrace.genesis.phase_b_scientific_maturity.PluginValidationResult",
    }
    assert required <= policies
