"""Convenience recorder for CodonTrace world and agent timelines."""

from __future__ import annotations

from codontrace._types import JsonValue, Position
from codontrace.trace import Trace, WorldEvent
from codontrace.world import World2D, WorldObject


class RunRecorder:
    """Convenience recorder for agent/world events.

    RunRecorder is optional. Core objects still work directly with Trace, but
    this helper keeps world mutation logging concise for notebooks and future
    replay/viewer tooling.
    """

    def __init__(self, trace: Trace | None = None) -> None:
        self.trace = trace or Trace()

    def place_resource(
        self,
        world: World2D,
        position: Position,
        amount: float,
        *,
        step: int,
        reason: str = "replenishment",
        metadata: dict[str, JsonValue] | None = None,
    ) -> WorldEvent:
        """Place a resource and record the world mutation."""

        return world.place_resource_event(
            position,
            amount,
            trace=self.trace,
            step=step,
            source="recorder",
            reason=reason,
            metadata=metadata,
        )

    def remove_resource(
        self,
        world: World2D,
        position: Position,
        *,
        step: int,
        reason: str = "resource removal",
        metadata: dict[str, JsonValue] | None = None,
    ) -> WorldEvent:
        """Remove a resource and record the world mutation."""

        return world.remove_resource_event(
            position,
            trace=self.trace,
            step=step,
            source="recorder",
            reason=reason,
            metadata=metadata,
        )

    def add_wall(
        self,
        world: World2D,
        position: Position,
        *,
        step: int,
        reason: str = "wall added",
        metadata: dict[str, JsonValue] | None = None,
    ) -> WorldEvent:
        """Add a wall and record the world mutation."""

        return world.add_wall_event(
            position,
            trace=self.trace,
            step=step,
            source="recorder",
            reason=reason,
            metadata=metadata,
        )

    def remove_wall(
        self,
        world: World2D,
        position: Position,
        *,
        step: int,
        reason: str = "wall removed",
        metadata: dict[str, JsonValue] | None = None,
    ) -> WorldEvent:
        """Remove a wall and record the world mutation."""

        return world.remove_wall_event(
            position,
            trace=self.trace,
            step=step,
            source="recorder",
            reason=reason,
            metadata=metadata,
        )

    def set_custom_cell(
        self,
        world: World2D,
        position: Position,
        marker: str,
        *,
        step: int,
        reason: str = "custom cell set",
        metadata: dict[str, JsonValue] | None = None,
    ) -> WorldEvent:
        """Set a custom cell marker and record the world mutation."""

        return world.set_custom_cell_event(
            position,
            marker,
            trace=self.trace,
            step=step,
            source="recorder",
            reason=reason,
            metadata=metadata,
        )

    def clear_custom_cell(
        self,
        world: World2D,
        position: Position,
        *,
        step: int,
        reason: str = "custom cell cleared",
        metadata: dict[str, JsonValue] | None = None,
    ) -> WorldEvent:
        """Clear a custom cell marker and record the world mutation."""

        return world.clear_custom_cell_event(
            position,
            trace=self.trace,
            step=step,
            source="recorder",
            reason=reason,
            metadata=metadata,
        )

    def add_object(
        self,
        world: World2D,
        position: Position,
        obj: WorldObject,
        *,
        step: int,
        reason: str = "object added",
        metadata: dict[str, JsonValue] | None = None,
    ) -> WorldEvent:
        """Add a world object and record the world mutation."""

        return world.add_object_event(
            position,
            obj,
            trace=self.trace,
            step=step,
            source="recorder",
            reason=reason,
            metadata=metadata,
        )

    def remove_object(
        self,
        world: World2D,
        position: Position,
        *,
        step: int,
        kind: str | None = None,
        reason: str = "object removed",
        metadata: dict[str, JsonValue] | None = None,
    ) -> WorldEvent:
        """Remove world objects and record the world mutation."""

        return world.remove_object_event(
            position,
            trace=self.trace,
            step=step,
            kind=kind,
            source="recorder",
            reason=reason,
            metadata=metadata,
        )
