from __future__ import annotations

from codontrace import TorusTopology, World2D


def test_topology_object_overrides_boundary_and_serializes() -> None:
    world = World2D(3, 1, topology=TorusTopology())
    assert world.move_agent((0, 0), (-1, 0))[0] == (2, 0)
    restored = World2D.from_dict(world.to_dict())
    assert restored.topology is not None
    assert restored.topology.name == "torus"
