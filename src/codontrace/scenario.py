"""Scenario configuration and deterministic factory helpers for CodonTrace."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Literal, cast

from codontrace._types import JsonValue, Position
from codontrace.agent import WhiteBoxAgent
from codontrace.codon import CodonTable
from codontrace.energy import ATPAccount
from codontrace.errors import (
    InvalidDensityError,
    InvalidWorldSizeError,
    PlacementError,
    ScenarioValidationError,
)
from codontrace.genome import SemanticGenome
from codontrace.rng import RNGManager
from codontrace.simulation import Simulation, SimulationConfig, SimulationResult
from codontrace.trace import Trace
from codontrace.world import World2D, WorldObject

WallPattern = Literal["none", "border", "uniform", "clusters", "rooms", "maze_lite"]
Distribution = Literal["none", "uniform", "clusters", "gradient", "patches"]
BoundaryMode = Literal["closed", "open", "wrap"]
GenomeStrategyName = Literal[
    "uniform_random", "profiled_random", "lineage_seeded", "latin_hypercube_lite"
]
ScenarioPlacementZone = Literal[
    "anywhere",
    "center",
    "edges",
    "quadrants",
    "near_resources",
    "far_from_hazards",
]


@dataclass(frozen=True, slots=True)
class ResourceConfig:
    """First-class resource generation configuration."""

    kind: str = "resource"
    density: float = 0.0
    amount_range: tuple[float, float] = (1.0, 2.0)
    distribution: Distribution = "none"
    respawn: bool = False
    respawn_rate: float = 0.0

    def __post_init__(self) -> None:
        if not self.kind:
            msg = "ResourceConfig.kind must not be empty."
            raise ScenarioValidationError(msg)
        _validate_density(self.density, "ResourceConfig.density")
        _validate_float_range(self.amount_range, "ResourceConfig.amount_range", positive=True)
        _validate_choice(
            self.distribution,
            {"none", "uniform", "clusters", "gradient", "patches"},
            "ResourceConfig.distribution",
        )
        if self.density > 0 and self.distribution == "none":
            msg = "ResourceConfig.density > 0 requires distribution != 'none'."
            raise InvalidDensityError(msg)
        if not isinstance(self.respawn, bool):
            msg = "ResourceConfig.respawn must be a bool."
            raise ScenarioValidationError(msg)
        _validate_density(self.respawn_rate, "ResourceConfig.respawn_rate")

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "kind": self.kind,
            "density": self.density,
            "amount_range": [self.amount_range[0], self.amount_range[1]],
            "distribution": self.distribution,
            "respawn": self.respawn,
            "respawn_rate": self.respawn_rate,
            "respawn_runtime_enabled": False,
            "respawn_status": "reserved_config_only" if self.respawn else "disabled_by_config",
            "respawn_claim_allowed": False,
        }

    @classmethod
    def from_dict(cls, data: dict[str, JsonValue]) -> ResourceConfig:
        kind = data.get("kind", "resource")
        respawn = data.get("respawn", False)
        if not isinstance(kind, str):
            msg = "ResourceConfig.kind must be a string."
            raise ScenarioValidationError(msg)
        if not isinstance(respawn, bool):
            msg = "ResourceConfig.respawn must be a bool."
            raise ScenarioValidationError(msg)
        amount_value = data.get("amount_range", data.get("amount", [1.0, 2.0]))
        if _is_number_not_bool(amount_value):
            amount_number = float(cast(int | float, amount_value))
            amount_range = (amount_number, amount_number)
        else:
            amount_range = _float_pair(amount_value, "ResourceConfig.amount_range")
        return cls(
            kind=kind,
            density=_float(data.get("density", 0.0), "ResourceConfig.density"),
            amount_range=amount_range,
            distribution=_distribution(
                data.get("distribution", "none"), "ResourceConfig.distribution"
            ),
            respawn=respawn,
            respawn_rate=_float(data.get("respawn_rate", 0.0), "ResourceConfig.respawn_rate"),
        )


@dataclass(frozen=True, slots=True)
class ObstacleConfig:
    """First-class obstacle/wall generation configuration."""

    density: float = 0.0
    pattern: WallPattern = "none"
    block_movement: bool = True
    block_sight: bool = True

    def __post_init__(self) -> None:
        _validate_density(self.density, "ObstacleConfig.density")
        _validate_choice(
            self.pattern,
            {"none", "border", "uniform", "clusters", "rooms", "maze_lite"},
            "ObstacleConfig.pattern",
        )
        if self.density > 0 and self.pattern == "none":
            msg = "ObstacleConfig.density > 0 requires pattern != 'none'."
            raise InvalidDensityError(msg)
        if not isinstance(self.block_movement, bool) or not isinstance(self.block_sight, bool):
            msg = "ObstacleConfig block flags must be bools."
            raise ScenarioValidationError(msg)

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "density": self.density,
            "pattern": self.pattern,
            "block_movement": self.block_movement,
            "block_sight": self.block_sight,
            "block_sight_runtime_enabled": False,
            "block_sight_status": "reserved_config_only" if self.block_sight else "disabled_by_config",
            "line_of_sight_claim_allowed": False,
        }

    @classmethod
    def from_dict(cls, data: dict[str, JsonValue]) -> ObstacleConfig:
        block_movement = data.get("block_movement", True)
        block_sight = data.get("block_sight", True)
        if not isinstance(block_movement, bool) or not isinstance(block_sight, bool):
            msg = "ObstacleConfig block flags must be bools."
            raise ScenarioValidationError(msg)
        return cls(
            density=_float(data.get("density", 0.0), "ObstacleConfig.density"),
            pattern=_wall_pattern(data.get("pattern", "none"), "ObstacleConfig.pattern"),
            block_movement=block_movement,
            block_sight=block_sight,
        )


@dataclass(frozen=True, slots=True, init=False)
class WorldConfig:
    """Deterministic world-generation configuration."""

    width: int
    height: int
    seed: int | None
    boundary: BoundaryMode
    wall_density: float
    wall_pattern: WallPattern
    resource_density: float
    resource_distribution: Distribution
    resource_amount_range: tuple[float, float]
    resource_kind: str
    resource_respawn: bool
    resource_respawn_rate: float
    hazard_density: float
    hazard_distribution: Distribution
    beacon_density: float
    beacon_distribution: Distribution
    allow_resource_on_wall: bool
    allow_agent_on_wall: bool
    allow_object_overlap: bool
    obstacle_block_movement: bool
    obstacle_block_sight: bool

    def __init__(
        self,
        width: int = 10,
        height: int = 10,
        seed: int | None = None,
        *,
        boundary: BoundaryMode | bool = "closed",
        wall_density: float = 0.0,
        wall_pattern: WallPattern = "none",
        resource_density: float = 0.0,
        resource_distribution: Distribution = "none",
        resource_amount_range: tuple[float, float] = (1.0, 2.0),
        resource_kind: str = "resource",
        resource_respawn: bool = False,
        resource_respawn_rate: float = 0.0,
        resource_amount: float | None = None,
        hazard_density: float = 0.0,
        hazard_distribution: Distribution = "none",
        beacon_density: float = 0.0,
        beacon_distribution: Distribution = "none",
        allow_resource_on_wall: bool = False,
        allow_agent_on_wall: bool = False,
        allow_object_overlap: bool = False,
        obstacle_block_movement: bool = True,
        obstacle_block_sight: bool = True,
        resource_config: ResourceConfig | None = None,
        obstacle_config: ObstacleConfig | None = None,
    ) -> None:
        if obstacle_config is not None:
            wall_density = obstacle_config.density
            wall_pattern = obstacle_config.pattern
            obstacle_block_movement = obstacle_config.block_movement
            obstacle_block_sight = obstacle_config.block_sight
        if resource_config is not None:
            resource_kind = resource_config.kind
            resource_density = resource_config.density
            resource_distribution = resource_config.distribution
            resource_amount_range = resource_config.amount_range
            resource_respawn = resource_config.respawn
            resource_respawn_rate = resource_config.respawn_rate
        if resource_amount is not None:
            resource_amount_range = (resource_amount, resource_amount)
        resolved_boundary: BoundaryMode
        if isinstance(boundary, bool):
            resolved_boundary = "closed" if boundary else "open"
        else:
            resolved_boundary = boundary
        object.__setattr__(self, "width", width)
        object.__setattr__(self, "height", height)
        object.__setattr__(self, "seed", seed)
        object.__setattr__(self, "boundary", resolved_boundary)
        object.__setattr__(self, "wall_density", wall_density)
        object.__setattr__(self, "wall_pattern", wall_pattern)
        object.__setattr__(self, "resource_density", resource_density)
        object.__setattr__(self, "resource_distribution", resource_distribution)
        object.__setattr__(self, "resource_amount_range", resource_amount_range)
        object.__setattr__(self, "resource_kind", resource_kind)
        object.__setattr__(self, "resource_respawn", resource_respawn)
        object.__setattr__(self, "resource_respawn_rate", resource_respawn_rate)
        object.__setattr__(self, "hazard_density", hazard_density)
        object.__setattr__(self, "hazard_distribution", hazard_distribution)
        object.__setattr__(self, "beacon_density", beacon_density)
        object.__setattr__(self, "beacon_distribution", beacon_distribution)
        object.__setattr__(self, "allow_resource_on_wall", allow_resource_on_wall)
        object.__setattr__(self, "allow_agent_on_wall", allow_agent_on_wall)
        object.__setattr__(self, "allow_object_overlap", allow_object_overlap)
        object.__setattr__(self, "obstacle_block_movement", obstacle_block_movement)
        object.__setattr__(self, "obstacle_block_sight", obstacle_block_sight)
        self.__post_init__()

    def __post_init__(self) -> None:
        _validate_positive_int(self.width, "WorldConfig.width")
        _validate_positive_int(self.height, "WorldConfig.height")
        if self.seed is not None and not _is_int_not_bool(self.seed):
            msg = "WorldConfig.seed must be an integer or null."
            raise ScenarioValidationError(msg)
        for value, name in (
            (self.wall_density, "WorldConfig.wall_density"),
            (self.resource_density, "WorldConfig.resource_density"),
            (self.hazard_density, "WorldConfig.hazard_density"),
            (self.beacon_density, "WorldConfig.beacon_density"),
        ):
            _validate_density(value, name)
        _validate_choice(self.boundary, {"closed", "open", "wrap"}, "WorldConfig.boundary")
        _validate_choice(
            self.wall_pattern,
            {"none", "border", "uniform", "clusters", "rooms", "maze_lite"},
            "WorldConfig.wall_pattern",
        )
        for dist_value, dist_name in (
            (self.resource_distribution, "WorldConfig.resource_distribution"),
            (self.hazard_distribution, "WorldConfig.hazard_distribution"),
            (self.beacon_distribution, "WorldConfig.beacon_distribution"),
        ):
            _validate_choice(
                dist_value, {"none", "uniform", "clusters", "gradient", "patches"}, dist_name
            )
        _validate_float_range(
            self.resource_amount_range, "WorldConfig.resource_amount_range", positive=True
        )
        if not isinstance(self.resource_kind, str) or not self.resource_kind:
            msg = "WorldConfig.resource_kind must be a non-empty string."
            raise ScenarioValidationError(msg)
        if not isinstance(self.resource_respawn, bool):
            msg = "WorldConfig.resource_respawn must be a bool."
            raise ScenarioValidationError(msg)
        _validate_density(self.resource_respawn_rate, "WorldConfig.resource_respawn_rate")
        for value, name in (
            (self.allow_resource_on_wall, "WorldConfig.allow_resource_on_wall"),
            (self.allow_agent_on_wall, "WorldConfig.allow_agent_on_wall"),
            (self.allow_object_overlap, "WorldConfig.allow_object_overlap"),
            (self.obstacle_block_movement, "WorldConfig.obstacle_block_movement"),
            (self.obstacle_block_sight, "WorldConfig.obstacle_block_sight"),
        ):
            if not isinstance(value, bool):
                msg = f"{name} must be a bool."
                raise ScenarioValidationError(msg)
        _reject_contradictions(self)

    @property
    def resource_config(self) -> ResourceConfig:
        """Return first-class ResourceConfig view used by WorldFactory."""

        return ResourceConfig(
            kind=self.resource_kind,
            density=self.resource_density,
            amount_range=self.resource_amount_range,
            distribution=self.resource_distribution,
            respawn=self.resource_respawn,
            respawn_rate=self.resource_respawn_rate,
        )

    @property
    def obstacle_config(self) -> ObstacleConfig:
        """Return first-class ObstacleConfig view used by WorldFactory."""

        return ObstacleConfig(
            density=self.wall_density,
            pattern=self.wall_pattern,
            block_movement=self.obstacle_block_movement,
            block_sight=self.obstacle_block_sight,
        )

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "width": self.width,
            "height": self.height,
            "seed": self.seed,
            "boundary": self.boundary,
            "wall_density": self.wall_density,
            "wall_pattern": self.wall_pattern,
            "resource_density": self.resource_density,
            "resource_distribution": self.resource_distribution,
            "resource_amount_range": [
                self.resource_amount_range[0],
                self.resource_amount_range[1],
            ],
            "resource_kind": self.resource_kind,
            "resource_respawn": self.resource_respawn,
            "resource_respawn_rate": self.resource_respawn_rate,
            "resource_respawn_runtime_enabled": False,
            "resource_respawn_status": "reserved_config_only" if self.resource_respawn else "disabled_by_config",
            "resource_respawn_claim_allowed": False,
            "resource_config": self.resource_config.to_dict(),
            "hazard_density": self.hazard_density,
            "hazard_distribution": self.hazard_distribution,
            "beacon_density": self.beacon_density,
            "beacon_distribution": self.beacon_distribution,
            "beacon_runtime_semantics": "extension_only" if self.beacon_density > 0 else "disabled_by_config",
            "beacon_claim_allowed": False,
            "allow_resource_on_wall": self.allow_resource_on_wall,
            "allow_agent_on_wall": self.allow_agent_on_wall,
            "allow_object_overlap": self.allow_object_overlap,
            "obstacle_block_movement": self.obstacle_block_movement,
            "obstacle_block_sight": self.obstacle_block_sight,
            "obstacle_block_sight_runtime_enabled": False,
            "obstacle_block_sight_status": "reserved_config_only" if self.obstacle_block_sight else "disabled_by_config",
            "line_of_sight_claim_allowed": False,
            "obstacle_config": self.obstacle_config.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, JsonValue]) -> WorldConfig:
        seed = data.get("seed")
        if seed is not None and not _is_int_not_bool(seed):
            msg = "WorldConfig.seed must be an integer or null."
            raise ScenarioValidationError(msg)
        resource_raw = data.get("resource_config")
        if resource_raw is not None and not isinstance(resource_raw, dict):
            msg = "WorldConfig.resource_config must be a dictionary."
            raise ScenarioValidationError(msg)
        obstacle_raw = data.get("obstacle_config")
        if obstacle_raw is not None and not isinstance(obstacle_raw, dict):
            msg = "WorldConfig.obstacle_config must be a dictionary."
            raise ScenarioValidationError(msg)

        if isinstance(resource_raw, dict):
            resource_config = ResourceConfig.from_dict(resource_raw)
            amount_range = resource_config.amount_range
        else:
            amount_value = data.get(
                "resource_amount_range", data.get("resource_amount", [1.0, 2.0])
            )
            if _is_number_not_bool(amount_value):
                amount_number = float(cast(int | float, amount_value))
                amount_range = (amount_number, amount_number)
            else:
                amount_range = _float_pair(amount_value, "WorldConfig.resource_amount_range")
            resource_config = ResourceConfig(
                kind=_str(data.get("resource_kind", "resource"), "WorldConfig.resource_kind"),
                density=_float(data.get("resource_density", 0.0), "WorldConfig.resource_density"),
                amount_range=amount_range,
                distribution=_distribution(
                    data.get("resource_distribution", "none"),
                    "WorldConfig.resource_distribution",
                ),
                respawn=_bool(data.get("resource_respawn", False), "WorldConfig.resource_respawn"),
                respawn_rate=_float(
                    data.get("resource_respawn_rate", 0.0),
                    "WorldConfig.resource_respawn_rate",
                ),
            )

        obstacle_config = (
            ObstacleConfig.from_dict(obstacle_raw)
            if isinstance(obstacle_raw, dict)
            else ObstacleConfig(
                density=_float(data.get("wall_density", 0.0), "WorldConfig.wall_density"),
                pattern=_wall_pattern(data.get("wall_pattern", "none"), "WorldConfig.wall_pattern"),
                block_movement=_bool(
                    data.get("obstacle_block_movement", True),
                    "WorldConfig.obstacle_block_movement",
                ),
                block_sight=_bool(
                    data.get("obstacle_block_sight", True),
                    "WorldConfig.obstacle_block_sight",
                ),
            )
        )
        return cls(
            width=_int(data.get("width", 10), "WorldConfig.width"),
            height=_int(data.get("height", 10), "WorldConfig.height"),
            seed=cast(int | None, seed),
            boundary=_boundary(data.get("boundary", "closed")),
            wall_density=obstacle_config.density,
            wall_pattern=obstacle_config.pattern,
            resource_density=resource_config.density,
            resource_distribution=resource_config.distribution,
            resource_amount_range=amount_range,
            resource_kind=resource_config.kind,
            resource_respawn=resource_config.respawn,
            resource_respawn_rate=resource_config.respawn_rate,
            hazard_density=_float(data.get("hazard_density", 0.0), "WorldConfig.hazard_density"),
            hazard_distribution=_distribution(
                data.get("hazard_distribution", "none"), "WorldConfig.hazard_distribution"
            ),
            beacon_density=_float(data.get("beacon_density", 0.0), "WorldConfig.beacon_density"),
            beacon_distribution=_distribution(
                data.get("beacon_distribution", "none"), "WorldConfig.beacon_distribution"
            ),
            allow_resource_on_wall=_bool(
                data.get("allow_resource_on_wall", False), "WorldConfig.allow_resource_on_wall"
            ),
            allow_agent_on_wall=_bool(
                data.get("allow_agent_on_wall", False), "WorldConfig.allow_agent_on_wall"
            ),
            allow_object_overlap=_bool(
                data.get("allow_object_overlap", False), "WorldConfig.allow_object_overlap"
            ),
            obstacle_block_movement=obstacle_config.block_movement,
            obstacle_block_sight=obstacle_config.block_sight,
        )


@dataclass(frozen=True, slots=True)
class ScenarioAgentProfile:
    """Scenario-level agent profile for reproducible scenario factories."""

    name: str
    count: int = 1
    genome_strategy: GenomeStrategyName = "uniform_random"
    genome_length_range: tuple[int, int] = (3, 6)
    atp_range: tuple[float, float] = (5.0, 5.0)
    codon_bias: dict[str, float] = field(default_factory=dict)
    placement_zone: ScenarioPlacementZone = "anywhere"
    min_distance: int = 1

    def __post_init__(self) -> None:
        if not self.name:
            msg = "ScenarioAgentProfile.name must not be empty."
            raise ScenarioValidationError(msg)
        _validate_positive_int(self.count, "ScenarioAgentProfile.count")
        _validate_choice(
            self.genome_strategy,
            {"uniform_random", "profiled_random", "lineage_seeded", "latin_hypercube_lite"},
            "ScenarioAgentProfile.genome_strategy",
        )
        low, high = self.genome_length_range
        _validate_positive_int(low, "ScenarioAgentProfile.genome_length_range[0]")
        _validate_positive_int(high, "ScenarioAgentProfile.genome_length_range[1]")
        if low > high:
            msg = "ScenarioAgentProfile.genome_length_range must be (min, max)."
            raise ScenarioValidationError(msg)
        atp_low, atp_high = self.atp_range
        _validate_nonnegative_number(atp_low, "ScenarioAgentProfile.atp_range[0]")
        _validate_nonnegative_number(atp_high, "ScenarioAgentProfile.atp_range[1]")
        if atp_low > atp_high:
            msg = "ScenarioAgentProfile.atp_range must be (min, max)."
            raise ScenarioValidationError(msg)
        _validate_choice(
            self.placement_zone,
            {"anywhere", "center", "edges", "quadrants", "near_resources", "far_from_hazards"},
            "ScenarioAgentProfile.placement_zone",
        )
        _validate_nonnegative_int(self.min_distance, "ScenarioAgentProfile.min_distance")
        for codon, weight in self.codon_bias.items():
            if len(codon) != 3 or any(bit not in {"0", "1"} for bit in codon):
                msg = f"Invalid codon_bias codon {codon!r}."
                raise ScenarioValidationError(msg)
            _validate_nonnegative_number(weight, f"codon_bias[{codon!r}]")

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "name": self.name,
            "count": self.count,
            "genome_strategy": self.genome_strategy,
            "genome_length_range": [self.genome_length_range[0], self.genome_length_range[1]],
            "atp_range": [self.atp_range[0], self.atp_range[1]],
            "codon_bias": dict(sorted(self.codon_bias.items())),
            "placement_zone": self.placement_zone,
            "min_distance": self.min_distance,
        }

    @classmethod
    def from_dict(cls, data: dict[str, JsonValue]) -> ScenarioAgentProfile:
        name = data.get("name")
        if not isinstance(name, str):
            msg = "ScenarioAgentProfile.name must be a string."
            raise ScenarioValidationError(msg)
        codon_bias_raw = data.get("codon_bias", {})
        if not isinstance(codon_bias_raw, dict):
            msg = "ScenarioAgentProfile.codon_bias must be a dictionary."
            raise ScenarioValidationError(msg)
        codon_bias: dict[str, float] = {}
        for codon, weight in codon_bias_raw.items():
            if not isinstance(codon, str):
                msg = "ScenarioAgentProfile.codon_bias keys must be strings."
                raise ScenarioValidationError(msg)
            codon_bias[codon] = _float(weight, f"codon_bias[{codon!r}]")
        return cls(
            name=name,
            count=_int(data.get("count", 1), "ScenarioAgentProfile.count"),
            genome_strategy=_genome_strategy(data.get("genome_strategy", "uniform_random")),
            genome_length_range=_int_pair(
                data.get("genome_length_range", [3, 6]), "genome_length_range"
            ),
            atp_range=_float_pair(data.get("atp_range", [5.0, 5.0]), "atp_range"),
            codon_bias=codon_bias,
            placement_zone=_placement_zone(data.get("placement_zone", "anywhere")),
            min_distance=_int(data.get("min_distance", 1), "ScenarioAgentProfile.min_distance"),
        )


@dataclass(frozen=True, slots=True, init=False)
class ScenarioConfig:
    """Complete deterministic scenario-generation configuration."""

    name: str
    seed: int | None
    world: WorldConfig
    agents: tuple[ScenarioAgentProfile, ...]
    max_steps: int
    trace_enabled: bool
    replay_enabled: bool
    metadata: dict[str, str]

    def __init__(
        self,
        name: str = "scenario",
        seed: int | None = None,
        world: WorldConfig | None = None,
        agents: tuple[ScenarioAgentProfile, ...] | list[ScenarioAgentProfile] | None = None,
        *,
        profiles: tuple[ScenarioAgentProfile, ...] | list[ScenarioAgentProfile] | None = None,
        max_steps: int = 100,
        steps: int | None = None,
        trace_enabled: bool = True,
        replay_enabled: bool = True,
        metadata: dict[str, str] | None = None,
    ) -> None:
        resolved_agents = agents if agents is not None else profiles
        if resolved_agents is None:
            resolved_agents = (ScenarioAgentProfile(name="default", count=1),)
        if steps is not None:
            max_steps = steps
        object.__setattr__(self, "name", name)
        object.__setattr__(self, "seed", seed)
        object.__setattr__(self, "world", world or WorldConfig())
        object.__setattr__(self, "agents", tuple(resolved_agents))
        object.__setattr__(self, "max_steps", max_steps)
        object.__setattr__(self, "trace_enabled", trace_enabled)
        object.__setattr__(self, "replay_enabled", replay_enabled)
        object.__setattr__(self, "metadata", dict(metadata or {}))
        self.__post_init__()

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not self.name:
            msg = "ScenarioConfig.name must be a non-empty string."
            raise ScenarioValidationError(msg)
        if self.seed is not None and not _is_int_not_bool(self.seed):
            msg = "ScenarioConfig.seed must be an integer or null."
            raise ScenarioValidationError(msg)
        if not isinstance(self.world, WorldConfig):
            msg = "ScenarioConfig.world must be a WorldConfig."
            raise ScenarioValidationError(msg)
        _validate_positive_int(self.max_steps, "ScenarioConfig.max_steps")
        if not isinstance(self.trace_enabled, bool) or not isinstance(self.replay_enabled, bool):
            msg = "ScenarioConfig trace_enabled and replay_enabled must be bools."
            raise ScenarioValidationError(msg)
        if not self.agents:
            msg = "ScenarioConfig.agents must not be empty."
            raise ScenarioValidationError(msg)
        names: set[str] = set()
        for profile in self.agents:
            if not isinstance(profile, ScenarioAgentProfile):
                msg = "ScenarioConfig.agents must contain ScenarioAgentProfile values."
                raise ScenarioValidationError(msg)
            if profile.name in names:
                msg = f"Duplicate ScenarioAgentProfile name {profile.name!r}."
                raise ScenarioValidationError(msg)
            names.add(profile.name)
        if not all(isinstance(k, str) and isinstance(v, str) for k, v in self.metadata.items()):
            msg = "ScenarioConfig.metadata must be dict[str, str]."
            raise ScenarioValidationError(msg)

    @property
    def profiles(self) -> tuple[ScenarioAgentProfile, ...]:
        """Backward-compatible alias for ``agents``."""

        return self.agents

    @property
    def steps(self) -> int:
        """Backward-compatible alias for ``max_steps``."""

        return self.max_steps

    @property
    def config_hash(self) -> str:
        payload = json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "name": self.name,
            "seed": self.seed,
            "world": self.world.to_dict(),
            "agents": [profile.to_dict() for profile in self.agents],
            "max_steps": self.max_steps,
            "trace_enabled": self.trace_enabled,
            "replay_enabled": self.replay_enabled,
            "metadata": dict(sorted(self.metadata.items())),
        }

    @classmethod
    def from_dict(cls, data: dict[str, JsonValue]) -> ScenarioConfig:
        name = data.get("name", "scenario")
        if not isinstance(name, str):
            msg = "ScenarioConfig.name must be a string."
            raise ScenarioValidationError(msg)
        seed = data.get("seed")
        if seed is not None and not _is_int_not_bool(seed):
            msg = "ScenarioConfig.seed must be an integer or null."
            raise ScenarioValidationError(msg)
        world_raw = data.get("world", {})
        agents_raw = data.get("agents", data.get("profiles", []))
        if not isinstance(world_raw, dict):
            msg = "ScenarioConfig.world must be a dictionary."
            raise ScenarioValidationError(msg)
        if not isinstance(agents_raw, list):
            msg = "ScenarioConfig.agents must be a list."
            raise ScenarioValidationError(msg)
        agents = []
        for item in agents_raw:
            if not isinstance(item, dict):
                msg = "ScenarioConfig.agents entries must be dictionaries."
                raise ScenarioValidationError(msg)
            agents.append(ScenarioAgentProfile.from_dict(item))
        metadata_raw = data.get("metadata", {})
        if not isinstance(metadata_raw, dict) or not all(
            isinstance(k, str) and isinstance(v, str) for k, v in metadata_raw.items()
        ):
            msg = "ScenarioConfig.metadata must be dict[str, str]."
            raise ScenarioValidationError(msg)
        return cls(
            name=name,
            seed=cast(int | None, seed),
            world=WorldConfig.from_dict(world_raw),
            agents=tuple(agents),
            max_steps=_int(
                data.get("max_steps", data.get("steps", 100)),
                "ScenarioConfig.max_steps",
            ),
            trace_enabled=_bool(data.get("trace_enabled", True), "ScenarioConfig.trace_enabled"),
            replay_enabled=_bool(data.get("replay_enabled", True), "ScenarioConfig.replay_enabled"),
            metadata=cast(dict[str, str], metadata_raw),
        )

    def to_json(self, *, indent: int | None = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, sort_keys=True)

    @classmethod
    def from_json(cls, text: str) -> ScenarioConfig:
        value = json.loads(text)
        if not isinstance(value, dict):
            msg = "ScenarioConfig JSON must be an object."
            raise ScenarioValidationError(msg)
        return cls.from_dict(cast(dict[str, JsonValue], value))


@dataclass(frozen=True, slots=True)
class Scenario:
    """A generated scenario bundle before runtime execution."""

    config: ScenarioConfig
    world: World2D
    agents: tuple[WhiteBoxAgent, ...]
    config_hash: str
    initial_world_digest: str
    initial_agent_digest: str

    def run(self, *, steps: int | None = None) -> ScenarioResult:
        """Run this scenario and return a scenario-aware result.

        Scenario-level runs propagate ``config_hash`` into TraceEvent objects.
        If ``trace_enabled`` is false, the returned result contains an empty
        Trace while still returning the final world and agent states.
        ``replay_enabled`` is recorded in scenario metadata; scenario runs do not
        perform automatic replay validation during the run.
        """

        simulation_config = SimulationConfig(
            steps=self.config.max_steps if steps is None else steps,
            seed=self.config.seed,
            allow_agent_on_wall=self.config.world.allow_agent_on_wall,
        )
        runtime_agents = tuple(_clone_agent(agent) for agent in self.agents)
        result = Simulation.run(
            world=self.world,
            agents=runtime_agents,
            config=simulation_config,
        )
        trace = (
            _trace_with_config_hash(result.trace, self.config_hash)
            if self.config.trace_enabled
            else Trace()
        )
        scenario_result = SimulationResult(
            trace=trace,
            final_world=result.final_world,
            agent_states=result.agent_states,
            world_digest=result.world_digest,
            trace_digest=trace.digest(),
        )
        return ScenarioResult(scenario=self, simulation=scenario_result)

    def to_summary(self) -> dict[str, JsonValue]:
        return {
            "name": self.config.name,
            "config_hash": self.config_hash,
            "initial_world_digest": self.initial_world_digest,
            "initial_agent_digest": self.initial_agent_digest,
            "agent_count": len(self.agents),
            "world": self.world.to_dict(),
            "max_steps": self.config.max_steps,
            "trace_enabled": self.config.trace_enabled,
            "replay_enabled": self.config.replay_enabled,
            "metadata": dict(self.config.metadata),
        }


@dataclass(frozen=True, slots=True)
class ScenarioResult:
    """Scenario-level run result with reproducibility metadata."""

    scenario: Scenario
    simulation: SimulationResult

    @property
    def trace(self) -> Trace:
        return self.simulation.trace

    @property
    def final_world(self) -> World2D:
        return self.simulation.final_world

    @property
    def final_world_digest(self) -> str:
        return self.simulation.world_digest

    @property
    def world_digest(self) -> str:
        """Alias for ``final_world_digest`` for result-level convenience."""

        return self.final_world_digest

    @property
    def trace_digest(self) -> str:
        return self.simulation.trace_digest

    @property
    def agent_states(self) -> tuple[dict[str, JsonValue], ...]:
        return tuple(dict(state) for state in self.simulation.agent_states)

    @property
    def config_hash(self) -> str:
        return self.scenario.config_hash

    def to_viewer_bundle(self) -> dict[str, JsonValue]:
        bundle = self.simulation.to_viewer_bundle()
        bundle["scenario"] = self.scenario.to_summary()
        bundle["config_hash"] = self.config_hash
        bundle["initial_world_digest"] = self.scenario.initial_world_digest
        bundle["initial_agent_digest"] = self.scenario.initial_agent_digest
        bundle["final_world_digest"] = self.final_world_digest
        return bundle


class WorldFactory:
    """Factory for deterministic World2D generation from WorldConfig."""

    @staticmethod
    def from_config(config: WorldConfig) -> World2D:
        world = World2D(config.width, config.height, boundary=config.boundary)
        rng = RNGManager(seed=config.seed).fork("world-factory")
        _place_walls(world, config, rng.fork("walls"))
        _place_resources(world, config, rng.fork("resources"))
        _place_objects(
            world,
            config,
            kind="hazard",
            density=config.hazard_density,
            distribution=config.hazard_distribution,
            rng=rng.fork("hazards"),
        )
        _place_objects(
            world,
            config,
            kind="beacon",
            density=config.beacon_density,
            distribution=config.beacon_distribution,
            rng=rng.fork("beacons"),
        )
        return world


class ScenarioFactory:
    """Factory for reproducible scenario worlds and initial agents."""

    @staticmethod
    def from_config(
        config: ScenarioConfig,
        *,
        codon_table: CodonTable | None = None,
    ) -> Scenario:
        table = codon_table or CodonTable.default_minimal()
        world = WorldFactory.from_config(config.world)
        agents = _create_scenario_agents(config, world, table)
        return Scenario(
            config=config,
            world=world,
            agents=agents,
            config_hash=config.config_hash,
            initial_world_digest=world.digest(),
            initial_agent_digest=_agent_digest(agents),
        )

    @staticmethod
    def run(
        config: ScenarioConfig,
        *,
        codon_table: CodonTable | None = None,
        steps: int | None = None,
    ) -> ScenarioResult:
        """Create and run a scenario while propagating scenario config refs."""

        return ScenarioFactory.from_config(config, codon_table=codon_table).run(steps=steps)


def _clone_agent(agent: WhiteBoxAgent) -> WhiteBoxAgent:
    clone = WhiteBoxAgent(
        id=agent.id,
        genome=agent.genome,
        codon_table=agent.codon_table,
        atp_account=ATPAccount.from_dict(agent.atp_account.to_dict()),
        position=agent.position,
        action_registry=agent.action_registry,
        profile=agent.profile,
        lineage_id=agent.lineage_id,
        parent_id=agent.parent_id,
        generation=agent.generation,
    )
    clone.restore_runtime_state(cursor=agent.cursor, step_index=agent.step_index)
    return clone


def _trace_with_config_hash(trace: Trace, config_hash: str) -> Trace:
    bundle = trace.to_bundle()
    agent_events = bundle.get("agent_events", [])
    if not isinstance(agent_events, list):
        msg = "Trace bundle agent_events must be a list."
        raise ScenarioValidationError(msg)
    updated_events: list[JsonValue] = []
    for event in agent_events:
        if not isinstance(event, dict):
            msg = "Trace bundle agent_events must contain dictionaries."
            raise ScenarioValidationError(msg)
        updated = dict(event)
        updated["config_hash"] = config_hash
        updated_events.append(updated)
    bundle["agent_events"] = updated_events
    return Trace.from_bundle(bundle)


# ---------------- deterministic generation helpers ----------------


def _place_walls(world: World2D, config: WorldConfig, rng: RNGManager) -> None:
    if config.boundary == "closed" or config.wall_pattern == "border":
        for x in range(world.width):
            world.walls.add((x, 0))
            world.walls.add((x, world.height - 1))
        for y in range(world.height):
            world.walls.add((0, y))
            world.walls.add((world.width - 1, y))
    if config.wall_pattern == "none" or config.wall_density == 0:
        return
    if config.wall_pattern == "maze_lite":
        for x in range(2, world.width - 1, 4):
            gap_y = 1 + (x * 3) % max(1, world.height - 2)
            for y in range(1, world.height - 1):
                if y != gap_y:
                    world.walls.add((x, y))
        return
    if config.wall_pattern == "rooms":
        _place_room_walls(world)
        return
    cells = _candidate_cells(world, allow_walls=True)
    count = _density_count(cells, config.wall_density)
    if config.wall_pattern == "clusters":
        for position in _cluster_positions(cells, count, rng):
            world.walls.add(position)
    else:
        for position in _sample_positions(cells, count, rng):
            world.walls.add(position)


def _place_room_walls(world: World2D) -> None:
    if world.width < 5 or world.height < 5:
        return
    vertical = world.width // 2
    horizontal = world.height // 2
    door_x = max(1, world.width // 4)
    door_y = max(1, world.height // 4)
    for y in range(1, world.height - 1):
        if y != door_y and y != world.height - 1 - door_y:
            world.walls.add((vertical, y))
    for x in range(1, world.width - 1):
        if x != door_x and x != world.width - 1 - door_x:
            world.walls.add((x, horizontal))


def _place_resources(world: World2D, config: WorldConfig, rng: RNGManager) -> None:
    resource_config = config.resource_config
    if resource_config.distribution == "none" or resource_config.density == 0:
        return
    cells = _candidate_cells(world, allow_walls=config.allow_resource_on_wall)
    count = _density_count(cells, resource_config.density)
    for position in _positions_for_distribution(cells, count, resource_config.distribution, rng):
        if config.allow_resource_on_wall or not world.is_wall(position):
            world.resources[position] = _range_float(resource_config.amount_range, rng)


def _place_objects(
    world: World2D,
    config: WorldConfig,
    *,
    kind: str,
    density: float,
    distribution: Distribution,
    rng: RNGManager,
) -> None:
    if distribution == "none" or density == 0:
        return
    cells = [
        cell
        for cell in _candidate_cells(world, allow_walls=config.allow_resource_on_wall)
        if config.allow_object_overlap or cell not in world.objects
    ]
    count = _density_count(cells, density)
    for position in _positions_for_distribution(cells, count, distribution, rng):
        if config.allow_resource_on_wall or not world.is_wall(position):
            world.add_object(
                position, WorldObject(kind=kind, amount=1.0, metadata={"source": "WorldFactory"})
            )


def _create_scenario_agents(
    config: ScenarioConfig,
    world: World2D,
    table: CodonTable,
) -> tuple[WhiteBoxAgent, ...]:
    rng = RNGManager(seed=config.seed).fork("scenario-agents")
    used: list[Position] = []
    agents: list[WhiteBoxAgent] = []
    for profile in config.agents:
        founder = _founder_genome(profile, table, rng.fork(f"{profile.name}-founder"))
        for index in range(profile.count):
            stream = rng.fork(f"{profile.name}-{index}")
            genome = _scenario_genome(profile, table, stream.fork("genome"), index, founder)
            atp = _range_float(profile.atp_range, stream.fork("atp"))
            position = _choose_agent_position(
                world, profile, used, stream.fork("placement"), config
            )
            used.append(position)
            lineage_id = profile.name if profile.genome_strategy == "lineage_seeded" else None
            parent_id = (
                f"{profile.name}-000"
                if profile.genome_strategy == "lineage_seeded" and index > 0
                else None
            )
            generation = 1 if profile.genome_strategy == "lineage_seeded" and index > 0 else 0
            agents.append(
                WhiteBoxAgent(
                    id=f"{profile.name}-{index:03d}",
                    genome=genome,
                    codon_table=table,
                    atp_account=ATPAccount(atp),
                    position=position,
                    profile=profile.name,
                    lineage_id=lineage_id,
                    parent_id=parent_id,
                    generation=generation,
                )
            )
    return tuple(agents)


def _founder_genome(
    profile: ScenarioAgentProfile,
    table: CodonTable,
    rng: RNGManager,
) -> SemanticGenome:
    if profile.genome_strategy != "lineage_seeded":
        return SemanticGenome.from_codons(("000",))
    return _profiled_genome(profile, table, rng, use_bias=True)


def _scenario_genome(
    profile: ScenarioAgentProfile,
    table: CodonTable,
    rng: RNGManager,
    index: int,
    founder: SemanticGenome,
) -> SemanticGenome:
    if profile.genome_strategy == "uniform_random":
        return _uniform_genome(profile, table, rng)
    if profile.genome_strategy == "profiled_random":
        return _profiled_genome(profile, table, rng, use_bias=True)
    if profile.genome_strategy == "lineage_seeded":
        if index == 0:
            return founder
        return _lineage_variant(founder, table, index)
    if profile.genome_strategy == "latin_hypercube_lite":
        return _latin_hypercube_genome(profile, table, index)
    return _uniform_genome(profile, table, rng)


def _uniform_genome(
    profile: ScenarioAgentProfile, table: CodonTable, rng: RNGManager
) -> SemanticGenome:
    length = _range_int(profile.genome_length_range, rng)
    codons = tuple(codon.bits for codon in table.actions())
    selected = tuple(rng.choice(codons) for _ in range(length))
    return SemanticGenome.from_codons(selected)


def _profiled_genome(
    profile: ScenarioAgentProfile,
    table: CodonTable,
    rng: RNGManager,
    *,
    use_bias: bool,
) -> SemanticGenome:
    length = _range_int(profile.genome_length_range, rng)
    codons = tuple(codon.bits for codon in table.actions())
    weights = [
        max(profile.codon_bias.get(codon, 1.0 if use_bias else 1.0), 0.0) for codon in codons
    ]
    if not any(weight > 0 for weight in weights):
        msg = f"ScenarioAgentProfile {profile.name!r} has no positive codon weights."
        raise ScenarioValidationError(msg)
    selected = tuple(_weighted_choice(codons, weights, rng) for _ in range(length))
    return SemanticGenome.from_codons(selected)


def _lineage_variant(founder: SemanticGenome, table: CodonTable, index: int) -> SemanticGenome:
    codons = list(founder.to_codons())
    vocabulary = tuple(codon.bits for codon in table.actions())
    position = (index - 1) % len(codons)
    current = codons[position]
    current_index = vocabulary.index(current) if current in vocabulary else 0
    codons[position] = vocabulary[(current_index + index) % len(vocabulary)]
    return SemanticGenome.from_codons(tuple(codons))


def _latin_hypercube_genome(
    profile: ScenarioAgentProfile, table: CodonTable, index: int
) -> SemanticGenome:
    low, high = profile.genome_length_range
    span = max(1, high - low + 1)
    length = low + (index % span)
    codons = tuple(codon.bits for codon in table.actions())
    selected = tuple(
        codons[(index + j * max(1, profile.count)) % len(codons)] for j in range(length)
    )
    return SemanticGenome.from_codons(selected)


def _choose_agent_position(
    world: World2D,
    profile: ScenarioAgentProfile,
    used: list[Position],
    rng: RNGManager,
    config: ScenarioConfig,
) -> Position:
    candidates = _profile_cells(
        world,
        profile.placement_zone,
        allow_walls=config.world.allow_agent_on_wall,
    )
    candidates = [cell for cell in candidates if cell not in used]
    if not config.world.allow_agent_on_wall:
        candidates = [cell for cell in candidates if not world.is_wall(cell)]
    if profile.min_distance > 0:
        candidates = [
            cell
            for cell in candidates
            if all(_manhattan(cell, other) >= profile.min_distance for other in used)
        ]
    if not candidates:
        msg = f"No valid position for scenario profile {profile.name!r}."
        raise PlacementError(msg)
    return rng.choice(sorted(candidates))


def _profile_cells(
    world: World2D,
    zone: ScenarioPlacementZone,
    *,
    allow_walls: bool,
) -> list[Position]:
    cells = _candidate_cells(world, allow_walls=allow_walls)
    if zone == "anywhere":
        return cells
    if zone == "center":
        x1 = world.width // 4
        x2 = max(x1, (world.width * 3) // 4)
        y1 = world.height // 4
        y2 = max(y1, (world.height * 3) // 4)
        return [cell for cell in cells if x1 <= cell[0] <= x2 and y1 <= cell[1] <= y2]
    if zone == "edges":
        return [
            cell
            for cell in cells
            if cell[0] in {0, world.width - 1} or cell[1] in {0, world.height - 1}
        ]
    if zone == "quadrants":
        return [
            cell for cell in cells if cell[0] < world.width // 2 and cell[1] < world.height // 2
        ]
    if zone == "near_resources":
        return [
            cell
            for cell in cells
            if any(_manhattan(cell, resource) <= 2 for resource in world.resources)
        ] or cells
    if zone == "far_from_hazards":
        hazards = [
            position
            for position, objects in world.objects.items()
            if any(obj.kind == "hazard" for obj in objects)
        ]
        return [
            cell for cell in cells if all(_manhattan(cell, hazard) >= 3 for hazard in hazards)
        ] or cells
    return cells


def _candidate_cells(world: World2D, *, allow_walls: bool) -> list[Position]:
    return [
        (x, y)
        for y in range(world.height)
        for x in range(world.width)
        if allow_walls or (x, y) not in world.walls
    ]


def _positions_for_distribution(
    cells: list[Position],
    count: int,
    distribution: Distribution,
    rng: RNGManager,
) -> list[Position]:
    if count <= 0:
        return []
    if distribution == "clusters":
        return _cluster_positions(cells, count, rng)
    if distribution == "gradient":
        ranked = sorted(cells, key=lambda item: (item[0] + item[1], item[1], item[0]))
        return ranked[:count]
    if distribution == "patches":
        return _cluster_positions(cells, count, rng, radius=2)
    return _sample_positions(cells, count, rng)


def _sample_positions(cells: list[Position], count: int, rng: RNGManager) -> list[Position]:
    pool = list(cells)
    selected: list[Position] = []
    for _ in range(min(count, len(pool))):
        index = rng.randrange(len(pool))
        selected.append(pool.pop(index))
    return selected


def _cluster_positions(
    cells: list[Position],
    count: int,
    rng: RNGManager,
    *,
    radius: int = 1,
) -> list[Position]:
    if not cells or count <= 0:
        return []
    centers = _sample_positions(cells, max(1, min(count, max(1, count // 4))), rng)
    selected: list[Position] = []
    remaining = set(cells)
    for center in centers:
        cluster = sorted(
            cell
            for cell in remaining
            if abs(cell[0] - center[0]) <= radius and abs(cell[1] - center[1]) <= radius
        )
        for cell in cluster:
            if len(selected) >= count:
                return selected
            if cell in remaining:
                selected.append(cell)
                remaining.remove(cell)
    if len(selected) < count:
        selected.extend(_sample_positions(sorted(remaining), count - len(selected), rng))
    return selected


def _density_count(cells: list[Position], density: float) -> int:
    return min(len(cells), int(round(len(cells) * density)))


def _agent_digest(agents: tuple[WhiteBoxAgent, ...]) -> str:
    payload = [
        {
            "id": agent.id,
            "genome": list(agent.genome.to_codons()),
            "position": [agent.position[0], agent.position[1]],
            "atp": agent.atp_account.current_atp,
            "profile": agent.profile,
            "lineage_id": agent.lineage_id,
            "parent_id": agent.parent_id,
            "generation": agent.generation,
        }
        for agent in sorted(agents, key=lambda item: item.id)
    ]
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def _weighted_choice(values: tuple[str, ...], weights: list[float], rng: RNGManager) -> str:
    total = sum(weights)
    threshold = rng.random() * total
    running = 0.0
    for value, weight in zip(values, weights, strict=True):
        running += weight
        if threshold <= running:
            return value
    return values[-1]


def _range_int(values: tuple[int, int], rng: RNGManager) -> int:
    low, high = values
    if low == high:
        return low
    return rng.randrange(low, high + 1)


def _range_float(values: tuple[float, float], rng: RNGManager) -> float:
    low, high = values
    if low == high:
        return low
    return low + (high - low) * rng.random()


def _manhattan(a: Position, b: Position) -> int:
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def _reject_contradictions(config: WorldConfig) -> None:
    if config.wall_density > 0 and config.wall_pattern == "none":
        msg = "WorldConfig.wall_density > 0 requires wall_pattern != 'none'."
        raise InvalidDensityError(msg)
    if config.resource_density > 0 and config.resource_distribution == "none":
        msg = "WorldConfig.resource_density > 0 requires resource_distribution != 'none'."
        raise InvalidDensityError(msg)
    if config.hazard_density > 0 and config.hazard_distribution == "none":
        msg = "WorldConfig.hazard_density > 0 requires hazard_distribution != 'none'."
        raise InvalidDensityError(msg)
    if config.beacon_density > 0 and config.beacon_distribution == "none":
        msg = "WorldConfig.beacon_density > 0 requires beacon_distribution != 'none'."
        raise InvalidDensityError(msg)


def _int(value: JsonValue, name: str) -> int:
    if not _is_int_not_bool(value):
        msg = f"{name} must be an integer."
        raise ScenarioValidationError(msg)
    return cast(int, value)


def _str(value: JsonValue, name: str) -> str:
    if not isinstance(value, str) or not value:
        msg = f"{name} must be a non-empty string."
        raise ScenarioValidationError(msg)
    return value


def _float(value: JsonValue, name: str) -> float:
    if not _is_number_not_bool(value):
        msg = f"{name} must be numeric."
        raise ScenarioValidationError(msg)
    return float(cast(int | float, value))


def _bool(value: JsonValue, name: str) -> bool:
    if not isinstance(value, bool):
        msg = f"{name} must be a bool."
        raise ScenarioValidationError(msg)
    return value


def _int_pair(value: JsonValue, name: str) -> tuple[int, int]:
    if not isinstance(value, list) or len(value) != 2:
        msg = f"{name} must be [min, max]."
        raise ScenarioValidationError(msg)
    return (_int(value[0], f"{name}[0]"), _int(value[1], f"{name}[1]"))


def _float_pair(value: JsonValue, name: str) -> tuple[float, float]:
    if not isinstance(value, list) or len(value) != 2:
        msg = f"{name} must be [min, max]."
        raise ScenarioValidationError(msg)
    return (_float(value[0], f"{name}[0]"), _float(value[1], f"{name}[1]"))


def _wall_pattern(value: JsonValue, name: str) -> WallPattern:
    _validate_choice(value, {"none", "border", "uniform", "clusters", "rooms", "maze_lite"}, name)
    return cast(WallPattern, value)


def _distribution(value: JsonValue, name: str) -> Distribution:
    _validate_choice(value, {"none", "uniform", "clusters", "gradient", "patches"}, name)
    return cast(Distribution, value)


def _boundary(value: JsonValue | bool) -> BoundaryMode:
    if isinstance(value, bool):
        return "closed" if value else "open"
    _validate_choice(value, {"closed", "open", "wrap"}, "WorldConfig.boundary")
    return cast(BoundaryMode, value)


def _genome_strategy(value: JsonValue) -> GenomeStrategyName:
    _validate_choice(
        value,
        {"uniform_random", "profiled_random", "lineage_seeded", "latin_hypercube_lite"},
        "ScenarioAgentProfile.genome_strategy",
    )
    return cast(GenomeStrategyName, value)


def _placement_zone(value: JsonValue) -> ScenarioPlacementZone:
    _validate_choice(
        value,
        {"anywhere", "center", "edges", "quadrants", "near_resources", "far_from_hazards"},
        "ScenarioAgentProfile.placement_zone",
    )
    return cast(ScenarioPlacementZone, value)


def _validate_choice(value: object, allowed: set[str], name: str) -> None:
    if not isinstance(value, str) or value not in allowed:
        msg = f"{name} must be one of {sorted(allowed)!r}."
        raise ScenarioValidationError(msg)


def _validate_positive_int(value: int, name: str) -> None:
    if not _is_int_not_bool(value) or value <= 0:
        msg = f"{name} must be a positive integer."
        if "width" in name or "height" in name:
            raise InvalidWorldSizeError(msg)
        raise ScenarioValidationError(msg)


def _validate_nonnegative_int(value: int, name: str) -> None:
    if not _is_int_not_bool(value) or value < 0:
        msg = f"{name} must be a non-negative integer."
        raise ScenarioValidationError(msg)


def _validate_float_range(
    value: tuple[float, float],
    name: str,
    *,
    positive: bool = False,
) -> None:
    if (
        not isinstance(value, tuple)
        or len(value) != 2
        or not _is_number_not_bool(value[0])
        or not _is_number_not_bool(value[1])
    ):
        msg = f"{name} must be a numeric (min, max) tuple."
        raise ScenarioValidationError(msg)
    low, high = value
    if low > high:
        msg = f"{name} must be ordered as (min, max)."
        raise ScenarioValidationError(msg)
    if positive and low <= 0:
        msg = f"{name} values must be positive."
        raise ScenarioValidationError(msg)


def _validate_nonnegative_number(value: float, name: str) -> None:
    if not _is_number_not_bool(value) or value < 0:
        msg = f"{name} must be non-negative."
        raise ScenarioValidationError(msg)


def _validate_density(value: float, name: str) -> None:
    if not _is_number_not_bool(value) or not 0.0 <= float(value) <= 1.0:
        msg = f"{name} must be between 0 and 1."
        raise InvalidDensityError(msg)


def _is_int_not_bool(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _is_number_not_bool(value: object) -> bool:
    return isinstance(value, int | float) and not isinstance(value, bool)
