from __future__ import annotations

from codontrace import World2D, WorldObject


def test_world_object_is_cloned_and_included_in_digest() -> None:
    world = World2D(3, 3)
    before = world.digest()
    world.add_object((1, 1), WorldObject(kind="FOOD", amount=3.0, metadata={"color": "blue"}))
    clone = world.clone()

    assert clone.objects_at((1, 1))[0].kind == "FOOD"
    assert world.digest() != before
    assert clone.digest() == world.digest()


def test_world_object_export_roundtrip() -> None:
    world = World2D(3, 3)
    world.add_object((2, 2), WorldObject(kind="BEACON", amount=1.0))
    restored = World2D.from_dict(world.to_dict())

    assert restored.objects_at((2, 2))[0].kind == "BEACON"
    assert restored.digest() == world.digest()
