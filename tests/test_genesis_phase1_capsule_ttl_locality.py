from __future__ import annotations

import pytest

from codontrace.genesis import CapsuleStore, CausalCapsule, NexusStigmergyLayer


def _capsule(cid: str, *, position=None, tick: int = 0, ttl: int = 32) -> CausalCapsule:
    metadata = {} if position is None else {"position": [position[0], position[1]]}
    return CausalCapsule(cid, "src", 1.0, "graph", ("p",), "outcome", 0.9, tick, ttl, metadata)


def test_capsule_decay_does_not_shorten_absolute_ttl() -> None:
    store = CapsuleStore((_capsule("a", tick=0, ttl=32),))

    store.decay(10)

    assert store.active_at(31)[0].capsule_id == "a"
    assert store.active_at(32) == ()


def test_nexus_layer_decay_preserves_signal_until_absolute_expiry() -> None:
    layer = NexusStigmergyLayer()
    layer.deposit(_capsule("a", tick=0, ttl=32), position=(0, 0))

    layer.decay(10)

    assert len(layer.active_signals(31)) == 1
    assert layer.active_signals(32) == ()


def test_capsule_nearby_uses_manhattan_locality_and_radius() -> None:
    store = CapsuleStore()
    store.deposit(_capsule("near", position=(1, 1)))
    store.deposit(_capsule("far", position=(4, 4)))
    store.deposit(_capsule("global"))

    assert [c.capsule_id for c in store.nearby((1, 1), 0, tick=0)] == ["near"]
    assert [c.capsule_id for c in store.nearby((0, 1), 1, tick=0)] == ["near"]
    assert [c.capsule_id for c in store.nearby((1, 1), 10, tick=33)] == []
    assert [c.capsule_id for c in store.nearby(None, 10, tick=0)] == ["global"]
    assert set(c.capsule_id for c in store.nearby((1, 1), 0, tick=0, include_global=True)) == {
        "near",
        "global",
    }


def test_capsule_nearby_rejects_negative_radius() -> None:
    with pytest.raises(ValueError):
        CapsuleStore().nearby((0, 0), -1)
