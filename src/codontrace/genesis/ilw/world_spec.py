"""Shared ILW WorldSpec: digest-stable world configuration (ILW-1).

Claim ceiling stays ``runtime_observation``. This is scaffolding for an
``integrated eco-evolutionary runtime``, not an intelligence claim.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from codontrace._types import JsonValue
from codontrace.errors import ConfigurationError
from codontrace.genesis.canonical import canonical_digest
from codontrace.genesis.ilw.dag import CLAIM_CEILING, SCIENTIFIC_NAME

WORLD_SPEC_SCHEMA = "ilw_world_spec_v1"


class WorldSpecError(ConfigurationError):
    """Raised when an ILW WorldSpec is invalid."""


@dataclass(frozen=True, slots=True)
class WorldSpec:
    """Deterministic shared world configuration for one ILW run family.

    Digests are stable under key reordering and equivalent construction.
    ``seed`` is the base seed; per-subsystem streams come from
    :class:`~codontrace.genesis.ilw.seed_namespace.SeedNamespace`.
    """

    width: int
    height: int
    seed: int
    tick_horizon: int
    resource_kinds: tuple[str, ...] = ("lumen", "vitae")
    niche_count: int = 2
    population_cap: int = 16
    schema: str = WORLD_SPEC_SCHEMA
    claim_ceiling: str = CLAIM_CEILING
    scientific_name: str = SCIENTIFIC_NAME
    scale_label: str = "S0"

    def __post_init__(self) -> None:
        if isinstance(self.width, bool) or not isinstance(self.width, int) or self.width <= 0:
            raise WorldSpecError("WorldSpec.width must be a positive integer.")
        if isinstance(self.height, bool) or not isinstance(self.height, int) or self.height <= 0:
            raise WorldSpecError("WorldSpec.height must be a positive integer.")
        if isinstance(self.seed, bool) or not isinstance(self.seed, int):
            raise WorldSpecError("WorldSpec.seed must be an integer (bool rejected).")
        if (
            isinstance(self.tick_horizon, bool)
            or not isinstance(self.tick_horizon, int)
            or self.tick_horizon < 0
        ):
            raise WorldSpecError("WorldSpec.tick_horizon must be a non-negative integer.")
        if (
            isinstance(self.niche_count, bool)
            or not isinstance(self.niche_count, int)
            or self.niche_count < 1
        ):
            raise WorldSpecError("WorldSpec.niche_count must be a positive integer.")
        if (
            isinstance(self.population_cap, bool)
            or not isinstance(self.population_cap, int)
            or self.population_cap < 1
        ):
            raise WorldSpecError("WorldSpec.population_cap must be a positive integer.")
        if not self.resource_kinds or any(not str(item).strip() for item in self.resource_kinds):
            raise WorldSpecError("WorldSpec.resource_kinds must be non-empty strings.")
        if len(set(self.resource_kinds)) != len(self.resource_kinds):
            raise WorldSpecError("WorldSpec.resource_kinds must be unique.")
        if self.claim_ceiling != CLAIM_CEILING:
            raise WorldSpecError(
                f"WorldSpec.claim_ceiling must remain {CLAIM_CEILING!r}; "
                f"got {self.claim_ceiling!r}."
            )
        if self.scientific_name != SCIENTIFIC_NAME:
            raise WorldSpecError(
                f"WorldSpec.scientific_name must be {SCIENTIFIC_NAME!r}; "
                f"got {self.scientific_name!r}."
            )
        if not str(self.schema).strip():
            raise WorldSpecError("WorldSpec.schema must be non-empty.")
        if not str(self.scale_label).strip():
            raise WorldSpecError("WorldSpec.scale_label must be non-empty.")

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "schema": self.schema,
            "width": self.width,
            "height": self.height,
            "seed": self.seed,
            "tick_horizon": self.tick_horizon,
            "resource_kinds": list(self.resource_kinds),
            "niche_count": self.niche_count,
            "population_cap": self.population_cap,
            "claim_ceiling": self.claim_ceiling,
            "scientific_name": self.scientific_name,
            "scale_label": self.scale_label,
        }

    def digest(self) -> str:
        return canonical_digest(self.to_dict(), prefix="ilw_world_spec")

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> WorldSpec:
        kinds_raw = data.get("resource_kinds", ("lumen", "vitae"))
        if isinstance(kinds_raw, Sequence) and not isinstance(kinds_raw, (str, bytes)):
            kinds = tuple(str(item) for item in kinds_raw)
        else:
            raise WorldSpecError("WorldSpec.resource_kinds must be a sequence of strings.")
        return cls(
            width=int(data["width"]),
            height=int(data["height"]),
            seed=int(data["seed"]),
            tick_horizon=int(data["tick_horizon"]),
            resource_kinds=kinds,
            niche_count=int(data.get("niche_count", 2)),
            population_cap=int(data.get("population_cap", 16)),
            schema=str(data.get("schema", WORLD_SPEC_SCHEMA)),
            claim_ceiling=str(data.get("claim_ceiling", CLAIM_CEILING)),
            scientific_name=str(data.get("scientific_name", SCIENTIFIC_NAME)),
            scale_label=str(data.get("scale_label", "S0")),
        )

    @classmethod
    def s0_unit(cls, *, seed: int = 0) -> WorldSpec:
        """Minimal S0 unit-scale spec (4×4 / 6 tick) for scaffolding tests."""

        return cls(
            width=4,
            height=4,
            seed=seed,
            tick_horizon=6,
            resource_kinds=("lumen", "vitae"),
            niche_count=2,
            population_cap=8,
            scale_label="S0",
        )

    @classmethod
    def s1_smoke(cls, *, seed: int = 1) -> WorldSpec:
        """Integrated-smoke S1 scale (16×16 / 32 tick); larger than S0 unit."""

        return cls(
            width=16,
            height=16,
            seed=seed,
            tick_horizon=32,
            resource_kinds=("lumen", "vitae"),
            niche_count=4,
            population_cap=24,
            scale_label="S1",
        )
