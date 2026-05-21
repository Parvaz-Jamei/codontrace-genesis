"""Small deterministic 2D world for Core Kernel tests and examples."""

from __future__ import annotations

import hashlib
import json
import textwrap
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, ClassVar, cast

from codontrace._types import JsonValue, Position
from codontrace.errors import ConfigurationError, PlacementError
from codontrace.topology import TopologyProtocol, topology_from_name

if TYPE_CHECKING:
    from codontrace.agent import WhiteBoxAgent
    from codontrace.trace import TimelineFrame, Trace, TraceEvent, WorldEvent


@dataclass(frozen=True, slots=True)
class WorldObject:
    """Extensible object placed on a world cell.

    Objects are metadata-rich extension hooks for custom actions: food, hazards,
    beacons, nests, light, or any domain-specific object can be represented
    without changing the core grid/wall/resource API.
    """

    __hash__: ClassVar[None] = None  # type: ignore[assignment]

    kind: str
    amount: float = 0.0
    metadata: dict[str, JsonValue] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.kind:
            msg = "WorldObject.kind must not be empty."
            raise ConfigurationError(msg)

    def to_dict(self) -> dict[str, JsonValue]:
        """Return a JSON-friendly object dictionary."""

        return {
            "kind": self.kind,
            "amount": self.amount,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: dict[str, JsonValue]) -> WorldObject:
        """Restore a WorldObject from ``to_dict()`` output."""

        kind = data.get("kind")
        amount = data.get("amount", 0.0)
        metadata = data.get("metadata", {})
        if not isinstance(kind, str):
            msg = "WorldObject data requires a string kind."
            raise ConfigurationError(msg)
        if not isinstance(amount, int | float):
            msg = "WorldObject data requires numeric amount."
            raise ConfigurationError(msg)
        if not isinstance(metadata, dict):
            msg = "WorldObject data requires object metadata."
            raise ConfigurationError(msg)
        return cls(kind=kind, amount=float(amount), metadata=metadata)


@dataclass(slots=True)
class World2D:
    """A deterministic grid world with walls, resources, custom cells, objects, and one marker."""

    width: int
    height: int
    walls: set[Position] = field(default_factory=set)
    resources: dict[Position, float] = field(default_factory=dict)
    agent_position: Position | None = None
    custom_cells: dict[Position, str] = field(default_factory=dict)
    objects: dict[Position, tuple[WorldObject, ...]] = field(default_factory=dict)
    boundary: str = "closed"
    topology: TopologyProtocol | None = None

    EMPTY: ClassVar[str] = "."
    WALL: ClassVar[str] = "#"
    RESOURCE: ClassVar[str] = "*"
    AGENT: ClassVar[str] = "A"

    def __post_init__(self) -> None:
        if self.width <= 0 or self.height <= 0:
            msg = "World dimensions must be positive."
            raise ConfigurationError(msg)
        all_positions = (
            self.walls | set(self.resources) | set(self.custom_cells) | set(self.objects)
        )
        for position in all_positions:
            if not self.in_bounds(position):
                msg = f"Position {position!r} is outside the world."
                raise PlacementError(msg)
        if self.agent_position is not None and not self.in_bounds(self.agent_position):
            msg = f"Agent position {self.agent_position!r} is outside the world."
            raise PlacementError(msg)
        if self.boundary not in {"closed", "open", "wrap"}:
            msg = "World boundary must be 'closed', 'open', or 'wrap'."
            raise ConfigurationError(msg)
        if self.topology is not None and not (
            hasattr(self.topology, "normalize") and hasattr(self.topology, "neighbors")
        ):
            msg = "World2D.topology must satisfy TopologyProtocol."
            raise ConfigurationError(msg)
        self.objects = {position: tuple(objects) for position, objects in self.objects.items()}

    @classmethod
    def from_ascii(cls, ascii_map: str, *, allow_custom_cells: bool = False) -> World2D:
        """Create a world from ASCII rows.

        Built-in symbols are '.', '#', '*'/'F', and 'A'. Unknown symbols fail by
        default. With ``allow_custom_cells=True``, unknown non-whitespace symbols
        are stored as custom cell metadata markers that custom action handlers
        can inspect.
        """

        normalized = textwrap.dedent(ascii_map).strip("\n")
        rows = [line.rstrip() for line in normalized.splitlines()]
        while rows and not rows[0].strip():
            rows.pop(0)
        while rows and not rows[-1].strip():
            rows.pop()
        if not rows:
            msg = "ASCII map must contain at least one row."
            raise ConfigurationError(msg)
        width = len(rows[0])
        if any(len(row) != width for row in rows):
            msg = "All ASCII map rows must have the same width."
            raise ConfigurationError(msg)
        walls: set[Position] = set()
        resources: dict[Position, float] = {}
        custom_cells: dict[Position, str] = {}
        agent_position: Position | None = None
        for y, row in enumerate(rows):
            for x, char in enumerate(row):
                position = (x, y)
                if char == cls.WALL:
                    walls.add(position)
                elif char in {cls.RESOURCE, "F"}:
                    resources[position] = 2.0
                elif char == cls.AGENT:
                    if agent_position is not None:
                        msg = "ASCII map supports only one tracked agent."
                        raise ConfigurationError(msg)
                    agent_position = position
                elif char == cls.EMPTY:
                    continue
                elif allow_custom_cells:
                    custom_cells[position] = char
                else:
                    msg = f"Unsupported ASCII map symbol {char!r}."
                    raise ConfigurationError(msg)
        return cls(
            width=width,
            height=len(rows),
            walls=walls,
            resources=resources,
            agent_position=agent_position,
            custom_cells=custom_cells,
        )

    @classmethod
    def from_dict(cls, data: dict[str, JsonValue]) -> World2D:
        """Restore a world from ``to_dict()`` output."""

        width = data.get("width")
        height = data.get("height")
        if not _is_int_not_bool(width) or not _is_int_not_bool(height):
            msg = "World data requires integer width and height."
            raise ConfigurationError(msg)
        walls = {_position(item) for item in _list(data.get("walls", []), "walls")}
        resources: dict[Position, float] = {}
        for item in _list(data.get("resources", []), "resources"):
            if not isinstance(item, list) or len(item) != 2 or not isinstance(item[1], int | float):
                msg = "World resources must be [position, amount] pairs."
                raise ConfigurationError(msg)
            resources[_position(item[0])] = float(item[1])
        custom_cells: dict[Position, str] = {}
        for item in _list(data.get("custom_cells", []), "custom_cells"):
            if not isinstance(item, list) or len(item) != 2 or not isinstance(item[1], str):
                msg = "World custom_cells must be [position, marker] pairs."
                raise ConfigurationError(msg)
            custom_cells[_position(item[0])] = item[1]
        objects: dict[Position, tuple[WorldObject, ...]] = {}
        for item in _list(data.get("objects", []), "objects"):
            if not isinstance(item, list) or len(item) != 2 or not isinstance(item[1], list):
                msg = "World objects must be [position, objects] pairs."
                raise ConfigurationError(msg)
            object_items = []
            for raw_object in item[1]:
                if not isinstance(raw_object, dict):
                    msg = "World object entry must be a dictionary."
                    raise ConfigurationError(msg)
                object_items.append(WorldObject.from_dict(raw_object))
            objects[_position(item[0])] = tuple(object_items)
        raw_agent = data.get("agent_position")
        agent_position = None if raw_agent is None else _position(raw_agent)
        raw_boundary = data.get("boundary", "closed")
        boundary: str = raw_boundary if isinstance(raw_boundary, str) else "closed"
        raw_topology = data.get("topology")
        topology = topology_from_name(raw_topology) if isinstance(raw_topology, str) else None
        return cls(
            width=cast(int, width),
            height=cast(int, height),
            walls=walls,
            resources=resources,
            agent_position=agent_position,
            custom_cells=custom_cells,
            objects=objects,
            boundary=boundary,
            topology=topology,
        )

    def clone(self) -> World2D:
        """Return a deterministic clone for replay and perturbation tests."""

        return World2D(
            width=self.width,
            height=self.height,
            walls=set(self.walls),
            resources=dict(self.resources),
            agent_position=self.agent_position,
            custom_cells=dict(self.custom_cells),
            objects={position: tuple(objects) for position, objects in self.objects.items()},
            boundary=self.boundary,
            topology=self.topology,
        )

    def in_bounds(self, position: Position) -> bool:
        """Return whether ``position`` is inside the grid."""

        x, y = position
        return 0 <= x < self.width and 0 <= y < self.height

    def is_wall(self, position: Position) -> bool:
        """Return whether ``position`` contains a wall."""

        return position in self.walls

    def get_cell(self, position: Position) -> str:
        """Return the visible cell symbol at ``position``."""

        if not self.in_bounds(position):
            msg = f"Position {position!r} is outside the world."
            raise PlacementError(msg)
        if self.agent_position == position:
            return self.AGENT
        if position in self.walls:
            return self.WALL
        if position in self.resources:
            return self.RESOURCE
        custom = self.custom_cells.get(position)
        if custom is not None:
            return custom
        return self.EMPTY

    def set_cell(self, position: Position, value: str) -> None:
        """Set a cell to '.', '#', '*'/'F', or 'A'."""

        if not self.in_bounds(position):
            msg = f"Position {position!r} is outside the world."
            raise PlacementError(msg)
        self.walls.discard(position)
        self.resources.pop(position, None)
        self.custom_cells.pop(position, None)
        if self.agent_position == position:
            self.agent_position = None
        if value == self.WALL:
            self.walls.add(position)
        elif value in {self.RESOURCE, "F"}:
            self.resources[position] = 2.0
        elif value == self.AGENT:
            self.agent_position = position
        elif value != self.EMPTY:
            msg = f"Unsupported cell value {value!r}. Use set_custom_cell() for metadata markers."
            raise ConfigurationError(msg)

    def set_custom_cell(self, position: Position, marker: str) -> None:
        """Store a custom metadata marker at ``position``.

        Custom cells are metadata only. They are not walls, resources, or ATP.
        Custom action handlers may read them through get_custom_cell().
        """

        if len(marker) != 1 or marker in {self.EMPTY, self.WALL, self.RESOURCE, "F", self.AGENT}:
            msg = "Custom cell marker must be one non-built-in character."
            raise ConfigurationError(msg)
        if not self.in_bounds(position):
            msg = f"Position {position!r} is outside the world."
            raise PlacementError(msg)
        self.walls.discard(position)
        self.resources.pop(position, None)
        if self.agent_position == position:
            self.agent_position = None
        self.custom_cells[position] = marker

    def get_custom_cell(self, position: Position) -> str | None:
        """Return a custom cell marker, if present."""

        if not self.in_bounds(position):
            msg = f"Position {position!r} is outside the world."
            raise PlacementError(msg)
        return self.custom_cells.get(position)

    def add_object(self, position: Position, obj: WorldObject) -> None:
        """Add a WorldObject to ``position``."""

        if not self.in_bounds(position):
            msg = f"Position {position!r} is outside the world."
            raise PlacementError(msg)
        current = self.objects.get(position, ())
        self.objects[position] = (*current, obj)

    def objects_at(self, position: Position) -> tuple[WorldObject, ...]:
        """Return objects at ``position`` in insertion order."""

        if not self.in_bounds(position):
            msg = f"Position {position!r} is outside the world."
            raise PlacementError(msg)
        return self.objects.get(position, ())

    def remove_objects(
        self, position: Position, *, kind: str | None = None
    ) -> tuple[WorldObject, ...]:
        """Remove and return objects at ``position``, optionally filtered by kind."""

        if not self.in_bounds(position):
            msg = f"Position {position!r} is outside the world."
            raise PlacementError(msg)
        existing = self.objects.get(position, ())
        if kind is None:
            self.objects.pop(position, None)
            return existing
        removed = tuple(obj for obj in existing if obj.kind == kind)
        kept = tuple(obj for obj in existing if obj.kind != kind)
        if kept:
            self.objects[position] = kept
        else:
            self.objects.pop(position, None)
        return removed

    def move_agent(self, start: Position, delta: Position) -> tuple[Position, str]:
        """Attempt to move an agent and return ``(new_position, reason)``."""

        target = (start[0] + delta[0], start[1] + delta[1])
        if self.topology is not None:
            normalized = self.topology.normalize(target, self.width, self.height)
            if normalized is None:
                return start, "out_of_bounds"
            target = normalized
        elif not self.in_bounds(target):
            if self.boundary == "wrap":
                target = (target[0] % self.width, target[1] % self.height)
            else:
                return start, "out_of_bounds"
        if target in self.walls:
            return start, "wall_blocked"
        self.agent_position = target
        return target, "moved"

    def place_resource(self, position: Position, amount: float = 2.0) -> None:
        """Place a resource at ``position``."""

        if amount <= 0:
            msg = "Resource amount must be positive."
            raise ConfigurationError(msg)
        if not self.in_bounds(position):
            msg = f"Position {position!r} is outside the world."
            raise PlacementError(msg)
        if position in self.walls:
            msg = "Cannot place a resource inside a wall."
            raise PlacementError(msg)
        self.custom_cells.pop(position, None)
        self.resources[position] = amount

    def resource_amount(self, position: Position) -> float:
        """Return resource ATP at ``position`` without mutating the world."""

        return self.resources.get(position, 0.0)

    def collect_resource(self, position: Position) -> float:
        """Collect and remove a resource. Return collected ATP, or zero."""

        return self.resources.pop(position, 0.0)

    def nearby_resource(self, position: Position) -> bool:
        """Return whether a resource exists in the Moore neighborhood."""

        return any(resource in self._neighbors(position) for resource in self.resources)

    def nearby_wall(self, position: Position) -> bool:
        """Return whether a wall exists in the Moore neighborhood."""

        return any(wall in self._neighbors(position) for wall in self.walls)

    def render_ascii(self) -> str:
        """Render the world as ASCII."""

        rows: list[str] = []
        for y in range(self.height):
            chars: list[str] = []
            for x in range(self.width):
                chars.append(self.get_cell((x, y)))
            rows.append("".join(chars))
        return "\n".join(rows)

    def to_dict(self) -> dict[str, JsonValue]:
        """Return a deterministic JSON-friendly world representation."""

        walls: list[JsonValue] = [_position_to_json(position) for position in sorted(self.walls)]
        resources: list[JsonValue] = [
            [_position_to_json(position), amount]
            for position, amount in sorted(self.resources.items())
        ]
        custom_cells: list[JsonValue] = [
            [_position_to_json(position), marker]
            for position, marker in sorted(self.custom_cells.items())
        ]
        objects_json: list[JsonValue] = []
        for position, objects in sorted(self.objects.items()):
            object_items: list[JsonValue] = [obj.to_dict() for obj in objects]
            objects_json.append([_position_to_json(position), object_items])
        agent_position: JsonValue = (
            _position_to_json(self.agent_position) if self.agent_position is not None else None
        )
        return {
            "width": self.width,
            "height": self.height,
            "boundary": self.boundary,
            "topology": None if self.topology is None else self.topology.name,
            "walls": walls,
            "resources": resources,
            "custom_cells": custom_cells,
            "objects": objects_json,
            "agent_position": agent_position,
        }

    def digest(self) -> str:
        """Return a stable hash of world state."""

        return hashlib.sha256(
            json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()

    @staticmethod
    def movement_delta(name: str) -> Position:
        """Return a movement delta for a movement action name."""

        deltas: dict[str, Position] = {
            "MOVE_NORTH": (0, -1),
            "MOVE_SOUTH": (0, 1),
            "MOVE_EAST": (1, 0),
            "MOVE_WEST": (-1, 0),
        }
        try:
            return deltas[name]
        except KeyError:
            expected = ", ".join(sorted(deltas))
            msg = f"Unknown movement action {name!r}. Expected one of: {expected}."
            raise ConfigurationError(msg) from None

    def place_resource_event(
        self,
        position: Position,
        amount: float,
        *,
        trace: Trace,
        step: int,
        source: str = "environment",
        reason: str = "resource placement",
        metadata: dict[str, JsonValue] | None = None,
    ) -> WorldEvent:
        """Place a resource and append a WorldEvent to ``trace``."""

        from codontrace.trace import (
            WORLD_EVENT_RESOURCE_CHANGED,
            WORLD_EVENT_RESOURCE_PLACED,
            WorldEvent,
        )

        before_amount = self.resource_amount(position)
        self.place_resource(position, amount)
        after_amount = self.resource_amount(position)
        event = WorldEvent(
            schema_version=1,
            step=step,
            sequence=trace.next_sequence(),
            event_type=(
                WORLD_EVENT_RESOURCE_PLACED if before_amount == 0 else WORLD_EVENT_RESOURCE_CHANGED
            ),
            position=position,
            amount=amount,
            source=source,
            reason=reason,
            before={"resource": before_amount},
            after={"resource": after_amount},
            delta={"resource_delta": after_amount - before_amount},
            metadata=dict(metadata or {}),
        )
        trace.append_world_event(event)
        return event

    def remove_resource_event(
        self,
        position: Position,
        *,
        trace: Trace,
        step: int,
        source: str = "environment",
        reason: str = "resource removal",
        metadata: dict[str, JsonValue] | None = None,
    ) -> WorldEvent:
        """Remove a resource and append a WorldEvent to ``trace``."""

        from codontrace.trace import WORLD_EVENT_RESOURCE_REMOVED, WorldEvent

        if not self.in_bounds(position):
            msg = f"Position {position!r} is outside the world."
            raise PlacementError(msg)
        before_amount = self.resource_amount(position)
        self.resources.pop(position, None)
        event = WorldEvent(
            schema_version=1,
            step=step,
            sequence=trace.next_sequence(),
            event_type=WORLD_EVENT_RESOURCE_REMOVED,
            position=position,
            amount=before_amount,
            source=source,
            reason=reason,
            before={"resource": before_amount},
            after={"resource": 0.0},
            delta={"resource_delta": -before_amount},
            metadata=dict(metadata or {}),
        )
        trace.append_world_event(event)
        return event

    def add_wall_event(
        self,
        position: Position,
        *,
        trace: Trace,
        step: int,
        source: str = "environment",
        reason: str = "wall added",
        metadata: dict[str, JsonValue] | None = None,
    ) -> WorldEvent:
        """Add a wall and append a WorldEvent to ``trace``."""

        from codontrace.trace import WORLD_EVENT_WALL_ADDED, WorldEvent

        before_wall = self.is_wall(position)
        self.set_cell(position, self.WALL)
        event = WorldEvent(
            schema_version=1,
            step=step,
            sequence=trace.next_sequence(),
            event_type=WORLD_EVENT_WALL_ADDED,
            position=position,
            source=source,
            reason=reason,
            before={"wall": before_wall},
            after={"wall": True},
            delta={"wall_added": not before_wall},
            metadata=dict(metadata or {}),
        )
        trace.append_world_event(event)
        return event

    def remove_wall_event(
        self,
        position: Position,
        *,
        trace: Trace,
        step: int,
        source: str = "environment",
        reason: str = "wall removed",
        metadata: dict[str, JsonValue] | None = None,
    ) -> WorldEvent:
        """Remove a wall and append a WorldEvent to ``trace``."""

        from codontrace.trace import WORLD_EVENT_WALL_REMOVED, WorldEvent

        if not self.in_bounds(position):
            msg = f"Position {position!r} is outside the world."
            raise PlacementError(msg)
        before_wall = self.is_wall(position)
        self.walls.discard(position)
        event = WorldEvent(
            schema_version=1,
            step=step,
            sequence=trace.next_sequence(),
            event_type=WORLD_EVENT_WALL_REMOVED,
            position=position,
            source=source,
            reason=reason,
            before={"wall": before_wall},
            after={"wall": False},
            delta={"wall_removed": before_wall},
            metadata=dict(metadata or {}),
        )
        trace.append_world_event(event)
        return event

    def set_custom_cell_event(
        self,
        position: Position,
        marker: str,
        *,
        trace: Trace,
        step: int,
        source: str = "environment",
        reason: str = "custom cell set",
        metadata: dict[str, JsonValue] | None = None,
    ) -> WorldEvent:
        """Set a custom cell and append a WorldEvent to ``trace``."""

        from codontrace.trace import WORLD_EVENT_CUSTOM_CELL_SET, WorldEvent

        before_marker = self.get_custom_cell(position)
        self.set_custom_cell(position, marker)
        event = WorldEvent(
            schema_version=1,
            step=step,
            sequence=trace.next_sequence(),
            event_type=WORLD_EVENT_CUSTOM_CELL_SET,
            position=position,
            source=source,
            reason=reason,
            before={"marker": before_marker},
            after={"marker": marker},
            delta={"marker_changed": before_marker != marker},
            metadata=dict(metadata or {}),
        )
        trace.append_world_event(event)
        return event

    def clear_custom_cell_event(
        self,
        position: Position,
        *,
        trace: Trace,
        step: int,
        source: str = "environment",
        reason: str = "custom cell cleared",
        metadata: dict[str, JsonValue] | None = None,
    ) -> WorldEvent:
        """Clear a custom cell and append a WorldEvent to ``trace``."""

        from codontrace.trace import WORLD_EVENT_CUSTOM_CELL_CLEARED, WorldEvent

        if not self.in_bounds(position):
            msg = f"Position {position!r} is outside the world."
            raise PlacementError(msg)
        before_marker = self.custom_cells.pop(position, None)
        event = WorldEvent(
            schema_version=1,
            step=step,
            sequence=trace.next_sequence(),
            event_type=WORLD_EVENT_CUSTOM_CELL_CLEARED,
            position=position,
            source=source,
            reason=reason,
            before={"marker": before_marker},
            after={"marker": None},
            delta={"marker_cleared": before_marker is not None},
            metadata=dict(metadata or {}),
        )
        trace.append_world_event(event)
        return event

    def add_object_event(
        self,
        position: Position,
        obj: WorldObject,
        *,
        trace: Trace,
        step: int,
        source: str = "environment",
        reason: str = "object added",
        metadata: dict[str, JsonValue] | None = None,
    ) -> WorldEvent:
        """Add a WorldObject and append a WorldEvent to ``trace``."""

        from codontrace.trace import WORLD_EVENT_OBJECT_ADDED, WorldEvent

        before_count = len(self.objects_at(position))
        self.add_object(position, obj)
        after_count = len(self.objects_at(position))
        event_metadata: dict[str, JsonValue] = dict(metadata or {})
        event_metadata["object"] = obj.to_dict()
        event_metadata["kind"] = obj.kind
        event = WorldEvent(
            schema_version=1,
            step=step,
            sequence=trace.next_sequence(),
            event_type=WORLD_EVENT_OBJECT_ADDED,
            position=position,
            source=source,
            reason=reason,
            amount=obj.amount,
            before={"object_count": before_count},
            after={"object_count": after_count},
            delta={"object_delta": after_count - before_count},
            metadata=event_metadata,
        )
        trace.append_world_event(event)
        return event

    def remove_object_event(
        self,
        position: Position,
        *,
        trace: Trace,
        step: int,
        kind: str | None = None,
        source: str = "environment",
        reason: str = "object removed",
        metadata: dict[str, JsonValue] | None = None,
    ) -> WorldEvent:
        """Remove WorldObject entries and append a WorldEvent to ``trace``."""

        from codontrace.trace import WORLD_EVENT_OBJECT_REMOVED, WorldEvent

        before_count = len(self.objects_at(position))
        removed = self.remove_objects(position, kind=kind)
        after_count = len(self.objects_at(position))
        event_metadata: dict[str, JsonValue] = dict(metadata or {})
        event_metadata["kind"] = kind
        event_metadata["removed"] = [obj.to_dict() for obj in removed]
        event = WorldEvent(
            schema_version=1,
            step=step,
            sequence=trace.next_sequence(),
            event_type=WORLD_EVENT_OBJECT_REMOVED,
            position=position,
            source=source,
            reason=reason,
            amount=float(len(removed)),
            before={"object_count": before_count},
            after={"object_count": after_count},
            delta={"object_delta": after_count - before_count},
            metadata=event_metadata,
        )
        trace.append_world_event(event)
        return event

    def apply_world_event(self, event: WorldEvent) -> None:
        """Apply one WorldEvent to this world without appending to a trace."""

        from codontrace.trace import (
            WORLD_EVENT_AGENT_MOVED,
            WORLD_EVENT_AGENT_REGISTERED,
            WORLD_EVENT_AGENT_REMOVED,
            WORLD_EVENT_CUSTOM_CELL_CLEARED,
            WORLD_EVENT_CUSTOM_CELL_SET,
            WORLD_EVENT_EXTERNAL_REPLENISHMENT,
            WORLD_EVENT_OBJECT_ADDED,
            WORLD_EVENT_OBJECT_REMOVED,
            WORLD_EVENT_RESOURCE_CHANGED,
            WORLD_EVENT_RESOURCE_PLACED,
            WORLD_EVENT_RESOURCE_REMOVED,
            WORLD_EVENT_SNAPSHOT_MARKER,
            WORLD_EVENT_WALL_ADDED,
            WORLD_EVENT_WALL_REMOVED,
        )

        if event.event_type in {
            WORLD_EVENT_AGENT_REGISTERED,
            WORLD_EVENT_AGENT_MOVED,
            WORLD_EVENT_AGENT_REMOVED,
            WORLD_EVENT_SNAPSHOT_MARKER,
        }:
            return
        if event.position is None:
            return
        position = event.position
        if not self.in_bounds(position):
            msg = f"Position {position!r} is outside the world."
            raise PlacementError(msg)
        if event.event_type in {
            WORLD_EVENT_RESOURCE_PLACED,
            WORLD_EVENT_RESOURCE_CHANGED,
            WORLD_EVENT_EXTERNAL_REPLENISHMENT,
        }:
            amount = _numeric_dict_value(event.after, "resource", event.amount)
            if amount > 0:
                self.place_resource(position, amount)
            else:
                self.resources.pop(position, None)
        elif event.event_type == WORLD_EVENT_RESOURCE_REMOVED:
            self.resources.pop(position, None)
        elif event.event_type == WORLD_EVENT_WALL_ADDED:
            self.set_cell(position, self.WALL)
        elif event.event_type == WORLD_EVENT_WALL_REMOVED:
            self.walls.discard(position)
        elif event.event_type == WORLD_EVENT_CUSTOM_CELL_SET:
            marker = event.after.get("marker", event.metadata.get("marker"))
            if not isinstance(marker, str):
                msg = "custom_cell_set event requires a string marker in after or metadata."
                raise ConfigurationError(msg)
            self.set_custom_cell(position, marker)
        elif event.event_type == WORLD_EVENT_CUSTOM_CELL_CLEARED:
            self.custom_cells.pop(position, None)
        elif event.event_type == WORLD_EVENT_OBJECT_ADDED:
            raw_object = event.metadata.get("object")
            if not isinstance(raw_object, dict):
                msg = "object_added event requires metadata['object']."
                raise ConfigurationError(msg)
            obj = WorldObject.from_dict(raw_object)
            current = self.objects_at(position)
            if obj not in current:
                self.add_object(position, obj)
        elif event.event_type == WORLD_EVENT_OBJECT_REMOVED:
            kind_value = event.metadata.get("kind")
            kind = kind_value if isinstance(kind_value, str) else None
            self.remove_objects(position, kind=kind)
        else:
            msg = f"Unsupported WorldEvent type {event.event_type!r}."
            raise ConfigurationError(msg)

    def to_view_state(
        self,
        *,
        agents: Sequence[WhiteBoxAgent] = (),
        step: int = 0,
        events: Sequence[TraceEvent | WorldEvent] = (),
        metrics: dict[str, JsonValue] | None = None,
    ) -> dict[str, JsonValue]:
        """Return a plain JSON-friendly view state for UI/replay tooling."""

        walls: list[JsonValue] = [_position_to_json(position) for position in sorted(self.walls)]
        resources: list[JsonValue] = [
            {"position": _position_to_json(position), "amount": amount}
            for position, amount in sorted(self.resources.items())
        ]
        custom_cells: list[JsonValue] = [
            {"position": _position_to_json(position), "marker": marker}
            for position, marker in sorted(self.custom_cells.items())
        ]
        objects: list[JsonValue] = []
        for position, object_items in sorted(self.objects.items()):
            for obj in object_items:
                objects.append({"position": _position_to_json(position), **obj.to_dict()})
        agent_items: list[JsonValue] = []
        for agent in agents:
            item: dict[str, JsonValue] = {
                "id": agent.id,
                "position": _position_to_json(agent.position),
                "atp": agent.atp_account.current_atp,
            }
            if agent.profile is not None:
                item["profile"] = agent.profile
            agent_items.append(item)
        event_items: list[JsonValue] = [event.to_dict() for event in events]
        return {
            "schema_version": 1,
            "step": step,
            "world": {"width": self.width, "height": self.height},
            "layers": {
                "walls": walls,
                "resources": resources,
                "custom_cells": custom_cells,
                "objects": objects,
            },
            "agents": agent_items,
            "events": event_items,
            "metrics": dict(metrics or {}),
        }

    def to_timeline_frame(
        self,
        *,
        agents: Sequence[WhiteBoxAgent] = (),
        step: int = 0,
        events: Sequence[TraceEvent | WorldEvent] = (),
        metrics: dict[str, JsonValue] | None = None,
    ) -> TimelineFrame:
        """Return a typed TimelineFrame for UI/replay tooling."""

        from codontrace.trace import TimelineFrame

        agent_items: list[dict[str, JsonValue]] = []
        for agent in agents:
            item: dict[str, JsonValue] = {
                "id": agent.id,
                "position": _position_to_json(agent.position),
                "atp": agent.atp_account.current_atp,
            }
            if agent.profile is not None:
                item["profile"] = agent.profile
            agent_items.append(item)
        resources: list[dict[str, JsonValue]] = [
            {"position": _position_to_json(position), "amount": amount}
            for position, amount in sorted(self.resources.items())
        ]
        objects: list[dict[str, JsonValue]] = []
        for position, object_items in sorted(self.objects.items()):
            for obj in object_items:
                objects.append({"position": _position_to_json(position), **obj.to_dict()})
        return TimelineFrame(
            schema_version=1,
            step=step,
            world_size=(self.width, self.height),
            agents=tuple(agent_items),
            resources=tuple(resources),
            walls=tuple([point[0], point[1]] for point in sorted(self.walls)),
            objects=tuple(objects),
            events=tuple(event.to_dict() for event in events),
            metrics=dict(metrics or {}),
        )

    def _neighbors(self, position: Position) -> set[Position]:
        if self.topology is not None:
            return set(self.topology.neighbors(position, self.width, self.height))
        x, y = position
        neighbors: set[Position] = set()
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                if dx == 0 and dy == 0:
                    continue
                candidate = (x + dx, y + dy)
                if self.in_bounds(candidate):
                    neighbors.add(candidate)
        return neighbors


def _list(value: JsonValue, name: str) -> list[JsonValue]:
    if not isinstance(value, list):
        msg = f"World data field {name!r} must be a list."
        raise ConfigurationError(msg)
    return value


def _position_to_json(position: Position) -> list[JsonValue]:
    return [position[0], position[1]]


def _is_int_not_bool(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _position(value: JsonValue) -> Position:
    if (
        not isinstance(value, list)
        or len(value) != 2
        or not _is_int_not_bool(value[0])
        or not _is_int_not_bool(value[1])
    ):
        msg = "Position data must be [x, y] integer coordinates; bool is not accepted."
        raise ConfigurationError(msg)
    return (cast(int, value[0]), cast(int, value[1]))


def _numeric_dict_value(data: dict[str, JsonValue], key: str, default: float) -> float:
    value = data.get(key, default)
    if not isinstance(value, int | float):
        msg = f"Expected numeric value for {key!r}."
        raise ConfigurationError(msg)
    return float(value)
