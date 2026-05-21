from types import SimpleNamespace

from codontrace.genesis import (
    CapsuleAdoptionPolicy,
    CapsuleTransferConfig,
    CausalCapsule,
    CausalGraph,
    GenesisATPState,
    NexusStigmergyLayer,
    adopt_causal_capsule,
    read_nexus_capsules,
)


def _capsule(confidence=0.8):
    return CausalCapsule(
        "cap", "src", 2.0, "graph", ("predicts_local",), "outcome:x", confidence, 0, 32
    )


def test_read_consumes_runtime_and_adoption_consumes_learning():
    layer = NexusStigmergyLayer()
    capsule = _capsule()
    layer.deposit(capsule)
    atp = GenesisATPState.from_runtime(5.0, learning_atp=5.0, learning_enabled=True)
    cfg = CapsuleTransferConfig(enabled=True, min_confidence=0.1)
    org = SimpleNamespace(id="target")
    read = read_nexus_capsules(org, layer, atp, cfg, tick=1)
    assert read.succeeded
    assert atp.runtime_available < 5.0
    graph = CausalGraph()
    adopt = adopt_causal_capsule(org, capsule, graph, None, atp, cfg, tick=1)
    assert adopt.succeeded
    assert adopt.adopted_edges == 1
    assert atp.learning_available < 5.0


def test_adoption_rejects_low_confidence_and_never_policy():
    org = SimpleNamespace(id="target")
    atp = GenesisATPState.from_runtime(5.0, learning_atp=5.0, learning_enabled=True)
    low = _capsule(confidence=0.1)
    cfg = CapsuleTransferConfig(enabled=True, min_confidence=0.5)
    assert (
        adopt_causal_capsule(org, low, CausalGraph(), None, atp, cfg, tick=1).blocked_reason
        == "confidence_below_threshold"
    )
    cfg2 = CapsuleTransferConfig(enabled=True, adoption_policy=CapsuleAdoptionPolicy.NEVER)
    assert (
        adopt_causal_capsule(org, _capsule(), CausalGraph(), None, atp, cfg2, tick=1).blocked_reason
        == "adoption_policy_never"
    )
