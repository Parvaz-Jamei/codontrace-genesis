from codontrace.genesis import (
    CapsuleEmissionConfig,
    CapsuleEmissionResult,
    CausalCapsule,
    NexusSignal,
)


def test_causal_capsule_roundtrip_digest():
    capsule = CausalCapsule("cap", "org", 1.0, "graph", ("WAIT",), "executed", 0.8, 1, 32)
    restored = CausalCapsule.from_dict(capsule.to_dict())
    assert restored.digest() == capsule.digest()


def test_capsule_config_default_disabled_and_result_serializes():
    config = CapsuleEmissionConfig()
    assert config.enabled is False
    assert CapsuleEmissionConfig.from_dict(config.to_dict()).enabled is False
    result = CapsuleEmissionResult(
        False, False, "capsule_emission_disabled", None, 0.0, 0.0, None, None
    )
    assert (
        CapsuleEmissionResult.from_dict(result.to_dict()).blocked_reason
        == "capsule_emission_disabled"
    )


def test_nexus_signal_roundtrip():
    signal = NexusSignal((1, 2), "cap", 1, 31, "digest")
    assert NexusSignal.from_dict(signal.to_dict()).position == (1, 2)
