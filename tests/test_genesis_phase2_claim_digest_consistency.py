from codontrace.genesis import GenesisEngine, GenesisExperimentSpec


def test_runtime_claim_gate_digest_matches_manifest_claim_gate_digest():
    result = GenesisEngine.from_spec(GenesisExperimentSpec(tick_count=1, seed=123)).run_ticks()
    assert result.manifest.claim_gate_decision_digest
    assert result.manifest.runtime_hashes["claim_gate_decision_digest"] == result.manifest.claim_gate_decision_digest
    assert result.manifest.runtime_hashes["phase2_claim_decision_digest"] == result.manifest.claim_gate_decision_digest
