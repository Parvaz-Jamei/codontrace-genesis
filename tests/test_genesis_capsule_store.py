import pytest

from codontrace.errors import ConfigurationError
from codontrace.genesis import CapsuleStore, CausalCapsule


def _capsule(cid="cap", tick=0, ttl=4):
    return CausalCapsule(cid, "src", 2.0, "graph", ("predicts_local",), "outcome:x", 0.8, tick, ttl)


def test_capsule_store_deposit_active_decay_roundtrip_digest():
    store = CapsuleStore()
    store.deposit(_capsule("a", tick=1, ttl=4))
    store.deposit(_capsule("b", tick=2, ttl=2))
    assert [c.capsule_id for c in store.active_at(2)] == ["a", "b"]
    before = store.digest()
    restored = CapsuleStore.from_dict(store.to_dict())
    assert restored.digest() == before
    store.decay(3)
    assert all(c.ttl >= 0 for c in store.capsules)
    store.expire(100)
    assert store.capsules == ()


def test_duplicate_capsule_rejected_unless_replace():
    store = CapsuleStore()
    store.deposit(_capsule("a"))
    with pytest.raises(ConfigurationError):
        store.deposit(_capsule("a"))
    store.deposit(_capsule("a", ttl=9), replace_existing=True)
    assert store.capsules[0].ttl == 9
