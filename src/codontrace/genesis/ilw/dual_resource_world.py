"""Minimal dual limited renewable resource world with niches (ILW-2).

Honest vertical slice: two resource kinds, spatial grid, niche preference
regions, harvest depletion, and per-tick renewal. No oracle fitness injection.
"""

from __future__ import annotations

from collections.abc import MutableMapping
from dataclasses import dataclass, field

from codontrace._types import JsonValue
from codontrace.errors import ConfigurationError
from codontrace.genesis.canonical import canonical_digest
from codontrace.genesis.ilw.world_spec import WorldSpec


class DualResourceWorldError(ConfigurationError):
    """Raised when the dual-resource world is misconfigured."""


@dataclass(slots=True)
class DualResourceWorld:
    """Spatial world with >=2 limited renewable resources and niches."""

    width: int
    height: int
    resource_kinds: tuple[str, ...]
    niche_count: int
    amounts: dict[tuple[int, int, str], float] = field(default_factory=dict)
    renewal_rate: float = 0.15
    capacity: float = 4.0
    harvest_take: float = 1.0

    def __post_init__(self) -> None:
        if self.width <= 0 or self.height <= 0:
            raise DualResourceWorldError("width/height must be positive.")
        if len(self.resource_kinds) < 2:
            raise DualResourceWorldError("Need at least two resource kinds.")
        if len(set(self.resource_kinds)) != len(self.resource_kinds):
            raise DualResourceWorldError("resource_kinds must be unique.")
        if self.niche_count < 1:
            raise DualResourceWorldError("niche_count must be >= 1.")
        if self.renewal_rate < 0 or self.capacity <= 0 or self.harvest_take <= 0:
            raise DualResourceWorldError("renewal/capacity/harvest must be positive/non-neg.")

    @classmethod
    def from_world_spec(cls, spec: WorldSpec, *, seed_amounts: float = 2.0) -> DualResourceWorld:
        world = cls(
            width=spec.width,
            height=spec.height,
            resource_kinds=tuple(spec.resource_kinds),
            niche_count=spec.niche_count,
        )
        world.seed_niches(base_amount=seed_amounts)
        return world

    def niche_id(self, x: int, y: int) -> int:
        # Partition columns into niche bands.
        band = max(1, self.width // self.niche_count)
        return min(self.niche_count - 1, x // band)

    def preferred_kind(self, niche: int) -> str:
        return self.resource_kinds[niche % len(self.resource_kinds)]

    def seed_niches(self, *, base_amount: float = 2.0) -> None:
        self.amounts.clear()
        for y in range(self.height):
            for x in range(self.width):
                niche = self.niche_id(x, y)
                preferred = self.preferred_kind(niche)
                for kind in self.resource_kinds:
                    amount = base_amount * (1.5 if kind == preferred else 0.5)
                    self.amounts[(x, y, kind)] = min(self.capacity, amount)

    def amount(self, x: int, y: int, kind: str) -> float:
        return float(self.amounts.get((x, y, kind), 0.0))

    def total_of(self, kind: str) -> float:
        return float(sum(v for (xx, yy, k), v in self.amounts.items() if k == kind))

    def totals(self) -> dict[str, float]:
        return {kind: self.total_of(kind) for kind in self.resource_kinds}

    def harvest(self, x: int, y: int, kind: str) -> float:
        if kind not in self.resource_kinds:
            raise DualResourceWorldError(f"Unknown resource kind {kind!r}.")
        if not (0 <= x < self.width and 0 <= y < self.height):
            return 0.0
        key = (x, y, kind)
        available = float(self.amounts.get(key, 0.0))
        taken = min(self.harvest_take, available)
        self.amounts[key] = available - taken
        return taken

    def renew(self, *, pressure: float = 1.0) -> dict[str, float]:
        """Renew resources; pressure < 1 slows renewal (ecological feedback)."""

        if pressure < 0:
            raise DualResourceWorldError("pressure must be non-negative.")
        before = self.totals()
        rate = self.renewal_rate * max(0.0, min(1.5, pressure))
        for y in range(self.height):
            for x in range(self.width):
                niche = self.niche_id(x, y)
                preferred = self.preferred_kind(niche)
                for kind in self.resource_kinds:
                    key = (x, y, kind)
                    current = float(self.amounts.get(key, 0.0))
                    boost = 1.25 if kind == preferred else 0.75
                    nxt = min(self.capacity, current + rate * boost)
                    self.amounts[key] = nxt
        after = self.totals()
        return {kind: after[kind] - before[kind] for kind in self.resource_kinds}

    def digest(self) -> str:
        payload: dict[str, JsonValue] = {
            "width": self.width,
            "height": self.height,
            "resource_kinds": list(self.resource_kinds),
            "niche_count": self.niche_count,
            "capacity": self.capacity,
            "renewal_rate": self.renewal_rate,
            "amounts": [
                {"x": x, "y": y, "kind": kind, "amount": amount}
                for (x, y, kind), amount in sorted(self.amounts.items())
            ],
        }
        return canonical_digest(payload, prefix="ilw_dual_resource_world")

    def snapshot(self) -> MutableMapping[str, JsonValue]:
        return {
            "digest": self.digest(),
            "totals": self.totals(),
            "niche_count": self.niche_count,
            "resource_kinds": list(self.resource_kinds),
        }
