"""Experimental substrate runtime bridge between World2D and ElementGrid."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass
from typing import cast

from codontrace._types import JsonValue
from codontrace.genesis.substrate import (
    ElementGrid,
    element_grid_to_world2d,
    world2d_to_element_grid,
)
from codontrace.world import World2D


@dataclass(frozen=True, slots=True)
class SubstrateRuntimeConfig:
    source_of_truth: str = "world2d"
    enable_resource_bridge: bool = True
    enable_nexus_bridge: bool = True
    enable_hazard_bridge: bool = True
    feature_status: str = "provisional_audit_only"
    evidence_bearing: bool = False
    claim_allowed: bool = False

    def __post_init__(self) -> None:
        if self.source_of_truth not in {"world2d", "element_grid", "dual_bridge_experimental"}:
            raise ValueError(
                "source_of_truth must be world2d, element_grid, or dual_bridge_experimental."
            )

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "source_of_truth": self.source_of_truth,
            "enable_resource_bridge": self.enable_resource_bridge,
            "enable_nexus_bridge": self.enable_nexus_bridge,
            "enable_hazard_bridge": self.enable_hazard_bridge,
            "feature_status": self.feature_status,
            "evidence_bearing": self.evidence_bearing,
            "claim_allowed": self.claim_allowed,
        }


@dataclass(frozen=True, slots=True)
class GenesisWorldState:
    world: World2D
    element_grid: ElementGrid | None = None
    source_of_truth: str = "world2d"

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "world_digest": self.world.digest(),
            "element_grid_digest": None
            if self.element_grid is None
            else self.element_grid.digest(),
            "source_of_truth": self.source_of_truth,
        }

    def digest(self) -> str:
        return _digest(self.to_dict())


@dataclass(frozen=True, slots=True)
class ElementGridWorldState:
    element_grid: ElementGrid
    world_mirror: World2D | None = None
    source_of_truth: str = "element_grid"

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "element_grid_digest": self.element_grid.digest(),
            "world_mirror_digest": None
            if self.world_mirror is None
            else self.world_mirror.digest(),
            "source_of_truth": self.source_of_truth,
        }


@dataclass(frozen=True, slots=True)
class World2DAdapter:
    def to_element_grid(self, world: World2D) -> ElementGrid:
        return world2d_to_element_grid(world)


@dataclass(frozen=True, slots=True)
class ElementGridAdapter:
    def to_world2d(self, grid: ElementGrid) -> World2D:
        return cast(World2D, element_grid_to_world2d(grid))


@dataclass(frozen=True, slots=True)
class SubstrateActionBridge:
    config: SubstrateRuntimeConfig = SubstrateRuntimeConfig()

    def apply_action(
        self, state: GenesisWorldState, action: str, position: tuple[int, int]
    ) -> tuple[GenesisWorldState, dict[str, JsonValue]]:
        grid = state.element_grid or world2d_to_element_grid(state.world)
        audit: dict[str, JsonValue] = {
            "action": action,
            "position": [position[0], position[1]],
            "source_of_truth": state.source_of_truth,
            "feature_status": self.config.feature_status,
            "evidence_bearing": self.config.evidence_bearing,
            "claim_allowed": self.config.claim_allowed,
        }
        # ElementGrid APIs are intentionally wrapped conservatively because the alpha
        # grid is still a bridge, not the primary hot-loop substrate.
        if action == "EAT_LUMEN" and self.config.enable_resource_bridge:
            audit["Lu_consumption_attempted"] = True
            audit["resource_bridge_status"] = "audit_only_not_integrated"
        elif action == "EMIT_NEXUS" and self.config.enable_nexus_bridge:
            audit["Nx_deposit_attempted"] = True
            audit["nexus_bridge_status"] = "audit_only_not_integrated"
        elif action == "UMBRA_HAZARD" and self.config.enable_hazard_bridge:
            audit["Um_hazard_attempted"] = True
            audit["hazard_bridge_status"] = "audit_only_not_integrated"
        else:
            audit["bridge_status"] = "no_mapped_effect"
        new_world = (
            cast(World2D, element_grid_to_world2d(grid))
            if self.config.source_of_truth == "element_grid"
            else state.world
        )
        return GenesisWorldState(new_world, grid, self.config.source_of_truth), audit


def _digest(payload: Mapping[str, JsonValue]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()
