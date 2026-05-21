from codontrace.genesis import CausalCapsule, NexusStigmergyLayer


def _capsule(cid, tick=0, ttl=4):
    return CausalCapsule(cid, "src", 2.0, "graph", ("p",), "outcome", 0.8, tick, ttl)


def test_stigmergy_layer_deposit_read_expire_roundtrip():
    layer = NexusStigmergyLayer()
    layer.deposit(_capsule("a"), position=(0, 0))
    layer.deposit(_capsule("b", tick=1, ttl=2), position=(1, 0))
    digest = layer.digest()
    assert len(layer.active_signals(1)) == 2
    restored = NexusStigmergyLayer.from_dict(layer.to_dict())
    assert restored.digest() == digest
    layer.expire(10)
    assert layer.active_signals(10) == ()
    assert layer.store.capsules == ()
