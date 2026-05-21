from codontrace.genesis import D0BaselineConfig, DiscoveryClaimLevel, DiscoveryWitnessStub


def test_discovery_hooks_are_serializable_and_claim_none_default_path():
    config = D0BaselineConfig(behavior_descriptor_bins={"survival_ticks": 4})
    assert config.enabled is False
    assert D0BaselineConfig.from_dict(config.to_dict()).digest() == config.digest()
    witness = DiscoveryWitnessStub(
        witness_id="w",
        claim_level=DiscoveryClaimLevel.NONE,
        behavior_digest="b",
        graph_digest="g",
        vocabulary_digest="v",
        capsule_store_digest="c",
        required_evidence=("d0_baseline",),
    )
    restored = DiscoveryWitnessStub.from_dict(witness.to_dict())
    assert restored.claim_level is DiscoveryClaimLevel.NONE
    assert restored.digest() == witness.digest()
