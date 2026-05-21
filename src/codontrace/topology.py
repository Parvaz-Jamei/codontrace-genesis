"""Grid topology protocols and built-in deterministic topology presets."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from codontrace._types import Position


@runtime_checkable
class TopologyProtocol(Protocol):
    """Structural topology contract for World2D movement and neighborhoods."""

    @property
    def name(self) -> str:
        """Stable topology name for built-in serialization when available."""
        ...

    def normalize(self, position: Position, width: int, height: int) -> Position | None:
        """Return a valid position or ``None`` when movement leaves the topology."""

    def neighbors(self, position: Position, width: int, height: int) -> tuple[Position, ...]:
        """Return neighboring positions in deterministic order."""


@dataclass(frozen=True, slots=True)
class ClosedTopology:
    name: str = "closed"

    def normalize(self, position: Position, width: int, height: int) -> Position | None:
        return position if _in_bounds(position, width, height) else None

    def neighbors(self, position: Position, width: int, height: int) -> tuple[Position, ...]:
        return _bounded_neighbors(position, width, height)


@dataclass(frozen=True, slots=True)
class OpenTopology:
    name: str = "open"

    def normalize(self, position: Position, width: int, height: int) -> Position | None:
        return position if _in_bounds(position, width, height) else None

    def neighbors(self, position: Position, width: int, height: int) -> tuple[Position, ...]:
        return _bounded_neighbors(position, width, height)


@dataclass(frozen=True, slots=True)
class WrapTopology:
    name: str = "wrap"

    def normalize(self, position: Position, width: int, height: int) -> Position | None:
        return (position[0] % width, position[1] % height)

    def neighbors(self, position: Position, width: int, height: int) -> tuple[Position, ...]:
        return _wrapped_neighbors(position, width, height, wrap_x=True, wrap_y=True)


@dataclass(frozen=True, slots=True)
class TorusTopology(WrapTopology):
    name: str = "torus"


@dataclass(frozen=True, slots=True)
class CylinderTopology:
    """Wrap one axis and keep the other closed."""

    axis: str = "x"
    name: str = "cylinder"

    def __post_init__(self) -> None:
        if self.axis not in {"x", "y"}:
            msg = "CylinderTopology.axis must be 'x' or 'y'."
            raise ValueError(msg)

    def normalize(self, position: Position, width: int, height: int) -> Position | None:
        x, y = position
        candidate = (x % width, y) if self.axis == "x" else (x, y % height)
        return candidate if _in_bounds(candidate, width, height) else None

    def neighbors(self, position: Position, width: int, height: int) -> tuple[Position, ...]:
        return _wrapped_neighbors(
            position,
            width,
            height,
            wrap_x=self.axis == "x",
            wrap_y=self.axis == "y",
        )


@dataclass(frozen=True, slots=True)
class MobiusTopology:
    """Reserved simple x-wrap with y-reflection topology."""

    name: str = "mobius"

    def normalize(self, position: Position, width: int, height: int) -> Position | None:
        x, y = position
        wraps, wrapped_x = divmod(x, width)
        if wraps % 2 != 0:
            y = height - 1 - y
        candidate = (wrapped_x, y)
        return candidate if _in_bounds(candidate, width, height) else None

    def neighbors(self, position: Position, width: int, height: int) -> tuple[Position, ...]:
        candidates = []
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                if dx == 0 and dy == 0:
                    continue
                normalized = self.normalize((position[0] + dx, position[1] + dy), width, height)
                if normalized is not None:
                    candidates.append(normalized)
        return tuple(sorted(set(candidates)))


def topology_from_name(name: str) -> TopologyProtocol:
    if name == "closed":
        return ClosedTopology()
    if name == "open":
        return OpenTopology()
    if name == "wrap":
        return WrapTopology()
    if name == "torus":
        return TorusTopology()
    if name == "cylinder":
        return CylinderTopology()
    if name == "mobius":
        return MobiusTopology()
    msg = f"Unsupported topology {name!r}."
    raise ValueError(msg)


def _in_bounds(position: Position, width: int, height: int) -> bool:
    return 0 <= position[0] < width and 0 <= position[1] < height


def _bounded_neighbors(position: Position, width: int, height: int) -> tuple[Position, ...]:
    candidates = []
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            if dx == 0 and dy == 0:
                continue
            candidate = (position[0] + dx, position[1] + dy)
            if _in_bounds(candidate, width, height):
                candidates.append(candidate)
    return tuple(candidates)


def _wrapped_neighbors(
    position: Position,
    width: int,
    height: int,
    *,
    wrap_x: bool,
    wrap_y: bool,
) -> tuple[Position, ...]:
    candidates = []
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            if dx == 0 and dy == 0:
                continue
            x = position[0] + dx
            y = position[1] + dy
            if wrap_x:
                x %= width
            if wrap_y:
                y %= height
            candidate = (x, y)
            if _in_bounds(candidate, width, height):
                candidates.append(candidate)
    return tuple(sorted(set(candidates)))
