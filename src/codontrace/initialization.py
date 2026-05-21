"""Deterministic manual and profiled agent initialization utilities."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Literal, NoReturn, Protocol, cast

from codontrace._types import JsonValue, Position
from codontrace.actions import ActionRegistry, default_action_registry
from codontrace.agent import WhiteBoxAgent
from codontrace.codon import CodonTable
from codontrace.energy import ATPAccount
from codontrace.errors import ConfigurationError, PlacementError
from codontrace.genome import SemanticGenome
from codontrace.mutation import Mutation
from codontrace.rng import RNGManager
from codontrace.world import World2D

GenomeStrategy = Literal[
    "manual",
    "uniform_random",
    "profiled_random",
    "lineage_seeded",
    "latin_hypercube_lite",
    "latin_hypercube",  # backward-compatible alias for older callers
]
PlacementStrategy = Literal[
    "manual",
    "uniform_random",
    "poisson_disk",
    "grid",
]


class GenomeStrategyHandler(Protocol):
    """Structural protocol for custom genome initialization strategies."""

    def __call__(
        self,
        *,
        profile: AgentProfile,
        table: CodonTable,
        rng: RNGManager,
    ) -> SemanticGenome: ...


@dataclass(frozen=True, slots=True)
class AgentProfile:
    """Profile used for deterministic profile-based initialization.

    Profiles are initialization metadata only. They do not imply biological
    evolution, selection, reproduction, fitness, or emergent ecology.
    """

    name: str
    count: int | None = None
    weight: float = 1.0
    genome_length: int = 6
    initial_atp: float = 5.0
    preferred_codons: tuple[str, ...] = ()
    preferred_codons_weight: float = 0.7
    placement_zone: tuple[int, int, int, int] | None = None
    min_distance: int | None = None
    lineage_id: str | None = None

    def to_dict(self) -> dict[str, JsonValue]:
        """Return a JSON-friendly profile dictionary."""

        return {
            "name": self.name,
            "count": self.count,
            "weight": self.weight,
            "genome_length": self.genome_length,
            "initial_atp": self.initial_atp,
            "preferred_codons": list(self.preferred_codons),
            "preferred_codons_weight": self.preferred_codons_weight,
            "placement_zone": list(self.placement_zone) if self.placement_zone else None,
            "min_distance": self.min_distance,
            "lineage_id": self.lineage_id,
        }

    @classmethod
    def from_dict(cls, data: dict[str, JsonValue]) -> AgentProfile:
        """Restore a profile from ``to_dict()`` output."""

        name = data.get("name")
        if not isinstance(name, str):
            msg = "AgentProfile data requires a string name."
            raise ConfigurationError(msg)
        preferred_raw = data.get("preferred_codons", [])
        if not isinstance(preferred_raw, list) or not all(
            isinstance(item, str) for item in preferred_raw
        ):
            msg = "AgentProfile.preferred_codons must be a list of strings."
            raise ConfigurationError(msg)
        zone_raw = data.get("placement_zone")
        zone = None if zone_raw is None else _zone_from_json(zone_raw)
        return cls(
            name=name,
            count=_optional_int(data.get("count"), "count"),
            weight=_float(data.get("weight", 1.0), "weight"),
            genome_length=_int(data.get("genome_length", 6), "genome_length"),
            initial_atp=_float(data.get("initial_atp", 5.0), "initial_atp"),
            preferred_codons=tuple(str(item) for item in preferred_raw),
            preferred_codons_weight=_float(
                data.get("preferred_codons_weight", 0.7), "preferred_codons_weight"
            ),
            placement_zone=zone,
            min_distance=_optional_int(data.get("min_distance"), "min_distance"),
            lineage_id=_optional_str(data.get("lineage_id"), "lineage_id"),
        )


@dataclass(frozen=True, slots=True)
class AgentSpec:
    """Fully specified agent initialization record."""

    agent_id: str
    genome: SemanticGenome
    initial_atp: float
    position: Position
    profile: str | None = None
    lineage_id: str | None = None
    parent_id: str | None = None
    generation: int = 0

    def to_dict(self) -> dict[str, JsonValue]:
        """Return a JSON-friendly initialization specification."""

        return {
            "agent_id": self.agent_id,
            "genome": list(self.genome.to_codons()),
            "initial_atp": self.initial_atp,
            "position": list(self.position),
            "profile": self.profile,
            "lineage_id": self.lineage_id,
            "parent_id": self.parent_id,
            "generation": self.generation,
        }

    @classmethod
    def from_dict(cls, data: dict[str, JsonValue]) -> AgentSpec:
        """Restore an AgentSpec from ``to_dict()`` output."""

        agent_id = data.get("agent_id")
        genome = data.get("genome")
        position = data.get("position")
        if not isinstance(agent_id, str):
            msg = "AgentSpec data requires a string agent_id."
            raise ConfigurationError(msg)
        if not isinstance(genome, list) or not all(isinstance(codon, str) for codon in genome):
            msg = "AgentSpec data requires genome as a list of codon strings."
            raise ConfigurationError(msg)
        return cls(
            agent_id=agent_id,
            genome=SemanticGenome.from_codons(tuple(str(codon) for codon in genome)),
            initial_atp=_float(data.get("initial_atp", 0.0), "initial_atp"),
            position=_position_from_json(position),
            profile=_optional_str(data.get("profile"), "profile"),
            lineage_id=_optional_str(data.get("lineage_id"), "lineage_id"),
            parent_id=_optional_str(data.get("parent_id"), "parent_id"),
            generation=_int(data.get("generation", 0), "generation"),
        )


@dataclass(frozen=True, slots=True)
class LineageConfig:
    """Configuration for lineage-seeded initialization.

    This config only affects initialization metadata. It does not implement
    runtime reproduction, selection, fitness, or population evolution.
    """

    ancestor_count: int = 1
    mutation_operations: tuple[str, ...] = ("point", "swap")
    mutation_steps: int = 1

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "ancestor_count": self.ancestor_count,
            "mutation_operations": list(self.mutation_operations),
            "mutation_steps": self.mutation_steps,
        }

    @classmethod
    def from_dict(cls, data: dict[str, JsonValue]) -> LineageConfig:
        operations = data.get("mutation_operations", ["point", "swap"])
        if not isinstance(operations, list) or not all(
            isinstance(item, str) for item in operations
        ):
            msg = "LineageConfig.mutation_operations must be a list of strings."
            raise ConfigurationError(msg)
        return cls(
            ancestor_count=_int(data.get("ancestor_count", 1), "ancestor_count"),
            mutation_operations=tuple(str(item) for item in operations),
            mutation_steps=_int(data.get("mutation_steps", 1), "mutation_steps"),
        )


@dataclass(frozen=True, slots=True)
class InitializationConfig:
    """Configuration for deterministic agent creation.

    ``latin_hypercube_lite`` is a pure-Python LHS-inspired approximation for parameter coverage;
    no NumPy or SciPy dependency is added to the core package.
    """

    count: int
    seed: int | None = None
    genome_strategy: GenomeStrategy = "uniform_random"
    placement_strategy: PlacementStrategy = "uniform_random"
    genome_length: int = 6
    initial_atp: float = 5.0
    profiles: tuple[AgentProfile, ...] = ()
    lineage_config: LineageConfig = field(default_factory=LineageConfig)
    avoid_walls: bool = True
    avoid_resources: bool = True
    avoid_overlap: bool = True
    min_distance: int = 1
    prefix: str = "agent"

    def to_dict(self) -> dict[str, JsonValue]:
        """Return a JSON-friendly initialization config."""

        return {
            "count": self.count,
            "seed": self.seed,
            "genome_strategy": self.genome_strategy,
            "placement_strategy": self.placement_strategy,
            "genome_length": self.genome_length,
            "initial_atp": self.initial_atp,
            "profiles": [profile.to_dict() for profile in self.profiles],
            "lineage_config": self.lineage_config.to_dict(),
            "avoid_walls": self.avoid_walls,
            "avoid_resources": self.avoid_resources,
            "avoid_overlap": self.avoid_overlap,
            "min_distance": self.min_distance,
            "prefix": self.prefix,
        }

    @classmethod
    def from_dict(cls, data: dict[str, JsonValue]) -> InitializationConfig:
        """Restore an InitializationConfig from ``to_dict()`` output."""

        profiles_raw = data.get("profiles", [])
        if not isinstance(profiles_raw, list):
            msg = "InitializationConfig.profiles must be a list."
            raise ConfigurationError(msg)
        profiles = []
        for raw_profile in profiles_raw:
            if not isinstance(raw_profile, dict):
                msg = "InitializationConfig.profiles entries must be dictionaries."
                raise ConfigurationError(msg)
            profiles.append(AgentProfile.from_dict(raw_profile))
        lineage_raw = data.get("lineage_config", {})
        if not isinstance(lineage_raw, dict):
            msg = "InitializationConfig.lineage_config must be a dictionary."
            raise ConfigurationError(msg)
        return cls(
            count=_int(data.get("count"), "count"),
            seed=_optional_int(data.get("seed"), "seed"),
            genome_strategy=cast(GenomeStrategy, data.get("genome_strategy", "uniform_random")),
            placement_strategy=cast(
                PlacementStrategy, data.get("placement_strategy", "uniform_random")
            ),
            genome_length=_int(data.get("genome_length", 6), "genome_length"),
            initial_atp=_float(data.get("initial_atp", 5.0), "initial_atp"),
            profiles=tuple(profiles),
            lineage_config=LineageConfig.from_dict(lineage_raw),
            avoid_walls=_bool(data.get("avoid_walls", True), "avoid_walls"),
            avoid_resources=_bool(data.get("avoid_resources", True), "avoid_resources"),
            avoid_overlap=_bool(data.get("avoid_overlap", True), "avoid_overlap"),
            min_distance=_int(data.get("min_distance", 1), "min_distance"),
            prefix=_str(data.get("prefix", "agent"), "prefix"),
        )


class AgentFactory:
    """Create one or many agents from manual specs or deterministic strategies."""

    @staticmethod
    def from_specs(
        specs: tuple[AgentSpec, ...] | list[AgentSpec],
        *,
        world: World2D | None = None,
        codon_table: CodonTable | None = None,
        action_registry: ActionRegistry | None = None,
    ) -> tuple[WhiteBoxAgent, ...]:
        """Create agents from exact manual specifications.

        If ``world`` is provided, positions are validated against world bounds
        and walls. This is still manual initialization; it does not schedule or
        run multiple agents.
        """

        table = codon_table or CodonTable.default_minimal()
        registry = action_registry or default_action_registry()
        normalized = tuple(specs)
        _validate_specs(normalized, table, world)
        return tuple(_agent_from_spec(spec, table, registry) for spec in normalized)

    @staticmethod
    def create_one(
        *,
        genome: SemanticGenome | list[str] | tuple[str, ...] | None = None,
        genome_length: int = 6,
        initial_atp: float = 5.0,
        position: Position = (0, 0),
        agent_id: str = "agent-1",
        codon_table: CodonTable | None = None,
        action_registry: ActionRegistry | None = None,
        seed: int | None = None,
    ) -> WhiteBoxAgent:
        """Create one deterministic agent with sensible defaults."""

        if genome_length <= 0:
            msg = "genome_length must be positive."
            raise ConfigurationError(msg)
        if initial_atp < 0:
            msg = "initial_atp cannot be negative."
            raise ConfigurationError(msg)
        table = codon_table or CodonTable.default_minimal()
        rng = RNGManager(seed=seed).fork("agent-factory-one")
        resolved_genome = _resolve_genome(genome, genome_length, table, rng)
        spec = AgentSpec(
            agent_id=agent_id,
            genome=resolved_genome,
            initial_atp=initial_atp,
            position=position,
        )
        return AgentFactory.from_specs([spec], codon_table=table, action_registry=action_registry)[
            0
        ]

    @staticmethod
    def create_many(
        *,
        world: World2D,
        config: InitializationConfig,
        codon_table: CodonTable | None = None,
        action_registry: ActionRegistry | None = None,
    ) -> tuple[WhiteBoxAgent, ...]:
        """Create many agents using deterministic initialization strategies."""

        table = codon_table or CodonTable.default_minimal()
        registry = action_registry or default_action_registry()
        specs = AgentFactory.create_specs(world=world, config=config, codon_table=table)
        return AgentFactory.from_specs(
            specs, world=world, codon_table=table, action_registry=registry
        )

    @staticmethod
    def create_specs(
        *,
        world: World2D,
        config: InitializationConfig,
        codon_table: CodonTable | None = None,
    ) -> tuple[AgentSpec, ...]:
        """Create a reproducible initialization plan without constructing agents."""

        table = codon_table or CodonTable.default_minimal()
        _validate_config(config)
        profiles = _profiles_for_config(config)
        _validate_profiles(profiles, config, table, world)
        placements = _select_positions(world, config, profiles)
        specs = _build_specs(config, profiles, placements, table)
        _validate_specs(specs, table, world)
        return specs

    @staticmethod
    def specs_to_json(specs: tuple[AgentSpec, ...] | list[AgentSpec]) -> str:
        """Serialize AgentSpec records to deterministic JSON."""

        return json.dumps(
            [spec.to_dict() for spec in specs],
            indent=2,
            sort_keys=True,
        )

    @staticmethod
    def specs_from_json(text: str) -> tuple[AgentSpec, ...]:
        """Restore AgentSpec records from ``specs_to_json()`` output."""

        value = json.loads(text)
        if not isinstance(value, list):
            msg = "Agent specs JSON must be a list."
            raise ConfigurationError(msg)
        specs: list[AgentSpec] = []
        for item in value:
            if not isinstance(item, dict):
                msg = "Agent specs JSON entries must be dictionaries."
                raise ConfigurationError(msg)
            specs.append(AgentSpec.from_dict(cast(dict[str, JsonValue], item)))
        return tuple(specs)


def _resolve_genome(
    genome: SemanticGenome | list[str] | tuple[str, ...] | None,
    genome_length: int,
    table: CodonTable,
    rng: RNGManager,
) -> SemanticGenome:
    if isinstance(genome, SemanticGenome):
        resolved = genome
    elif genome is not None:
        resolved = SemanticGenome.from_codons(tuple(genome))
    else:
        resolved = _uniform_genome(genome_length, table, rng)
    _validate_genome(resolved, table)
    return resolved


def _agent_from_spec(
    spec: AgentSpec,
    table: CodonTable,
    registry: ActionRegistry,
) -> WhiteBoxAgent:
    return WhiteBoxAgent(
        id=spec.agent_id,
        genome=spec.genome,
        codon_table=table,
        atp_account=ATPAccount(spec.initial_atp),
        position=spec.position,
        action_registry=registry,
        profile=spec.profile,
        lineage_id=spec.lineage_id,
        parent_id=spec.parent_id,
        generation=spec.generation,
    )


def _validate_specs(
    specs: tuple[AgentSpec, ...],
    table: CodonTable,
    world: World2D | None = None,
) -> None:
    ids: set[str] = set()
    for spec in specs:
        if not spec.agent_id:
            msg = "AgentSpec.agent_id must not be empty."
            raise ConfigurationError(msg)
        if spec.agent_id in ids:
            msg = f"Duplicate agent_id {spec.agent_id!r}."
            raise ConfigurationError(msg)
        ids.add(spec.agent_id)
        if spec.initial_atp < 0:
            msg = f"Agent {spec.agent_id!r} has negative initial_atp."
            raise ConfigurationError(msg)
        if spec.generation < 0:
            msg = f"Agent {spec.agent_id!r} has negative generation."
            raise ConfigurationError(msg)
        if world is not None:
            if not world.in_bounds(spec.position):
                msg = f"Agent {spec.agent_id!r} position {spec.position!r} is outside the world."
                raise ConfigurationError(msg)
            if world.is_wall(spec.position):
                msg = f"Agent {spec.agent_id!r} position {spec.position!r} is on a wall."
                raise ConfigurationError(msg)
        _validate_genome(spec.genome, table)


def _validate_genome(genome: SemanticGenome, table: CodonTable) -> None:
    invalid = [codon for codon in genome.to_codons() if not table.validate(codon)]
    if invalid:
        msg = f"Genome contains codons not present in CodonTable: {invalid!r}."
        raise ConfigurationError(msg)


def _canonical_genome_strategy(strategy: GenomeStrategy) -> str:
    if strategy == "latin_hypercube":
        return "latin_hypercube_lite"
    return strategy


def _validate_config(config: InitializationConfig) -> None:
    if config.count <= 0:
        msg = "InitializationConfig.count must be positive."
        raise ConfigurationError(msg)
    if config.genome_length <= 0:
        msg = "InitializationConfig.genome_length must be positive."
        raise ConfigurationError(msg)
    if config.initial_atp < 0:
        msg = "InitializationConfig.initial_atp cannot be negative."
        raise ConfigurationError(msg)
    if config.min_distance < 0:
        msg = "InitializationConfig.min_distance cannot be negative."
        raise ConfigurationError(msg)
    if not config.prefix:
        msg = "InitializationConfig.prefix must not be empty."
        raise ConfigurationError(msg)
    if not config.avoid_overlap:
        msg = (
            "InitializationConfig.avoid_overlap=False is not supported by the planner yet; "
            "use Simulation(collision_policy='allow_overlap') for runtime overlap debugging."
        )
        raise ConfigurationError(msg)
    if config.genome_strategy == "manual":
        msg = "Use AgentFactory.from_specs() for manual genome initialization."
        raise ConfigurationError(msg)
    if config.placement_strategy == "manual":
        msg = "Use AgentFactory.from_specs() for manual placement."
        raise ConfigurationError(msg)
    _validate_lineage_config(config.lineage_config)


def _validate_lineage_config(config: LineageConfig) -> None:
    if config.ancestor_count <= 0:
        msg = "LineageConfig.ancestor_count must be positive."
        raise ConfigurationError(msg)
    if config.mutation_steps <= 0:
        msg = "LineageConfig.mutation_steps must be positive."
        raise ConfigurationError(msg)
    if not config.mutation_operations:
        msg = "LineageConfig.mutation_operations must not be empty."
        raise ConfigurationError(msg)
    allowed = {"point", "insert", "delete", "swap"}
    invalid = sorted(set(config.mutation_operations) - allowed)
    if invalid:
        msg = (
            f"Invalid lineage mutation operations: {invalid!r}. Expected only {sorted(allowed)!r}."
        )
        raise ConfigurationError(msg)


def _profiles_for_config(config: InitializationConfig) -> tuple[AgentProfile, ...]:
    profiles = tuple(config.profiles)
    if profiles:
        return profiles
    return (
        AgentProfile(
            name="default",
            count=config.count,
            genome_length=config.genome_length,
            initial_atp=config.initial_atp,
            min_distance=config.min_distance,
        ),
    )


def _validate_profiles(
    profiles: tuple[AgentProfile, ...],
    config: InitializationConfig,
    table: CodonTable,
    world: World2D,
) -> None:
    names: set[str] = set()
    for profile in profiles:
        if not profile.name:
            msg = "AgentProfile.name must not be empty."
            raise ConfigurationError(msg)
        if profile.name in names:
            msg = f"Duplicate profile name {profile.name!r}."
            raise ConfigurationError(msg)
        names.add(profile.name)
        if profile.count is not None and profile.count < 0:
            msg = f"Profile {profile.name!r} count cannot be negative."
            raise ConfigurationError(msg)
        if profile.weight <= 0:
            msg = f"Profile {profile.name!r} weight must be positive."
            raise ConfigurationError(msg)
        if profile.genome_length <= 0:
            msg = f"Profile {profile.name!r} genome_length must be positive."
            raise ConfigurationError(msg)
        if profile.initial_atp < 0:
            msg = f"Profile {profile.name!r} initial_atp cannot be negative."
            raise ConfigurationError(msg)
        if not 0.0 <= profile.preferred_codons_weight <= 1.0:
            msg = f"Profile {profile.name!r} preferred_codons_weight must be between 0 and 1."
            raise ConfigurationError(msg)
        invalid = [codon for codon in profile.preferred_codons if not table.validate(codon)]
        if invalid:
            msg = f"Profile {profile.name!r} has invalid preferred codons: {invalid!r}."
            raise ConfigurationError(msg)
        if profile.placement_zone is not None:
            _validate_zone(profile.placement_zone, world, profile.name)
        if profile.min_distance is not None and profile.min_distance < 0:
            msg = f"Profile {profile.name!r} min_distance cannot be negative."
            raise ConfigurationError(msg)
    counts = _profile_counts(profiles, config.count)
    if sum(counts.values()) != config.count:
        msg = "Profile counts do not add up to InitializationConfig.count."
        raise ConfigurationError(msg)


def _validate_zone(zone: tuple[int, int, int, int], world: World2D, name: str) -> None:
    x1, y1, x2, y2 = zone
    if x1 > x2 or y1 > y2:
        msg = f"Profile {name!r} placement_zone must be (x1, y1, x2, y2) with x1<=x2 and y1<=y2."
        raise ConfigurationError(msg)
    if not world.in_bounds((x1, y1)) or not world.in_bounds((x2, y2)):
        msg = f"Profile {name!r} placement_zone is outside the world."
        raise ConfigurationError(msg)


def _profile_counts(profiles: tuple[AgentProfile, ...], total: int) -> dict[str, int]:
    fixed = sum(int(profile.count) for profile in profiles if profile.count is not None)
    if fixed > total:
        msg = f"Profile counts exceed requested count {total}."
        raise ConfigurationError(msg)
    unspecified = tuple(profile for profile in profiles if profile.count is None)
    if not unspecified:
        if fixed != total:
            msg = "Profile counts must equal total count when every profile has count set."
            raise ConfigurationError(msg)
        return {profile.name: int(profile.count or 0) for profile in profiles}

    remaining = total - fixed
    total_weight = sum(profile.weight for profile in unspecified)
    allocated: dict[str, int] = {profile.name: int(profile.count or 0) for profile in profiles}
    floors: list[tuple[float, str, int]] = []
    assigned = 0
    for profile in unspecified:
        exact = remaining * profile.weight / total_weight
        count = int(exact)
        allocated[profile.name] = count
        assigned += count
        floors.append((exact - count, profile.name, count))
    leftover = remaining - assigned
    for _, name, _ in sorted(floors, key=lambda item: (-item[0], item[1]))[:leftover]:
        allocated[name] += 1
    return allocated


def _select_positions(
    world: World2D,
    config: InitializationConfig,
    profiles: tuple[AgentProfile, ...],
) -> tuple[Position, ...]:
    rng = RNGManager(seed=config.seed).fork(f"placement/{config.placement_strategy}")
    counts = _profile_counts(profiles, config.count)
    selected: list[Position] = []
    for profile in profiles:
        count = counts[profile.name]
        if count == 0:
            continue
        distance = profile.min_distance if profile.min_distance is not None else config.min_distance
        zone_cells = _free_cells(world, config, profile.placement_zone)
        if config.placement_strategy == "grid":
            chosen = _grid_positions(zone_cells, count, selected, distance)
        elif config.placement_strategy == "uniform_random":
            chosen = _uniform_positions(
                zone_cells, count, selected, distance, rng.fork(profile.name)
            )
        elif config.placement_strategy == "poisson_disk":
            chosen = _poisson_positions(
                zone_cells, count, selected, distance, rng.fork(profile.name)
            )
        else:
            msg = f"Unsupported placement strategy {config.placement_strategy!r}."
            raise ConfigurationError(msg)
        selected.extend(chosen)
    return tuple(selected)


def _free_cells(
    world: World2D,
    config: InitializationConfig,
    zone: tuple[int, int, int, int] | None,
) -> tuple[Position, ...]:
    if zone is None:
        xs = range(world.width)
        ys = range(world.height)
    else:
        x1, y1, x2, y2 = zone
        xs = range(x1, x2 + 1)
        ys = range(y1, y2 + 1)
    cells: list[Position] = []
    occupied: set[Position] = {world.agent_position} if world.agent_position is not None else set()
    for y in ys:
        for x in xs:
            position = (x, y)
            if config.avoid_walls and position in world.walls:
                continue
            if config.avoid_resources and position in world.resources:
                continue
            if config.avoid_overlap and position in occupied:
                continue
            cells.append(position)
    return tuple(cells)


def _grid_positions(
    cells: tuple[Position, ...],
    count: int,
    selected: list[Position],
    min_distance: int,
) -> tuple[Position, ...]:
    chosen: list[Position] = []
    for cell in cells:
        if _respects_distance(cell, (*selected, *chosen), min_distance):
            chosen.append(cell)
            if len(chosen) == count:
                return tuple(chosen)
    _raise_capacity(count, len(chosen), len(cells), min_distance)


def _uniform_positions(
    cells: tuple[Position, ...],
    count: int,
    selected: list[Position],
    min_distance: int,
    rng: RNGManager,
) -> tuple[Position, ...]:
    shuffled = _shuffled(tuple(cells), rng)
    return _grid_positions(shuffled, count, selected, min_distance)


def _poisson_positions(
    cells: tuple[Position, ...],
    count: int,
    selected: list[Position],
    min_distance: int,
    rng: RNGManager,
) -> tuple[Position, ...]:
    shuffled = _shuffled(tuple(cells), rng)
    chosen: list[Position] = []
    for candidate in shuffled:
        if _respects_distance(candidate, (*selected, *chosen), min_distance):
            chosen.append(candidate)
            if len(chosen) == count:
                return tuple(chosen)
    _raise_capacity(count, len(chosen), len(cells), min_distance)


def _raise_capacity(requested: int, placed: int, candidates: int, min_distance: int) -> NoReturn:
    msg = (
        f"Cannot place {requested} agents with min_distance={min_distance}; "
        f"placed {placed}, candidate cells={candidates}."
    )
    raise PlacementError(msg)


def _respects_distance(
    position: Position,
    existing: tuple[Position, ...],
    min_distance: int,
) -> bool:
    return all(_chebyshev(position, other) >= min_distance for other in existing)


def _chebyshev(left: Position, right: Position) -> int:
    return max(abs(left[0] - right[0]), abs(left[1] - right[1]))


def _shuffled(values: tuple[Position, ...], rng: RNGManager) -> tuple[Position, ...]:
    items = list(values)
    for index in range(len(items) - 1, 0, -1):
        swap = rng.randrange(index + 1)
        items[index], items[swap] = items[swap], items[index]
    return tuple(items)


def _build_specs(
    config: InitializationConfig,
    profiles: tuple[AgentProfile, ...],
    placements: tuple[Position, ...],
    table: CodonTable,
) -> tuple[AgentSpec, ...]:
    counts = _profile_counts(profiles, config.count)
    placement_iter = iter(placements)
    genome_strategy = _canonical_genome_strategy(config.genome_strategy)
    rng = RNGManager(seed=config.seed).fork(f"genomes/{genome_strategy}")
    specs: list[AgentSpec] = []
    if config.genome_strategy == "lineage_seeded":
        return _lineage_seeded_specs(config, profiles, placements, table, rng)
    if config.genome_strategy in {"latin_hypercube_lite", "latin_hypercube"}:
        return _latin_hypercube_specs(config, profiles, placements, table, rng)
    for profile in profiles:
        for local_index in range(counts[profile.name]):
            position = next(placement_iter)
            genome = _profile_genome(
                profile,
                config.genome_strategy,
                table,
                rng.fork(f"{profile.name}-{local_index}"),
            )
            specs.append(
                AgentSpec(
                    agent_id=f"{config.prefix}-{len(specs) + 1}",
                    genome=genome,
                    initial_atp=profile.initial_atp,
                    position=position,
                    profile=profile.name,
                    lineage_id=profile.lineage_id,
                    generation=0,
                )
            )
    return tuple(specs)


def _profile_genome(
    profile: AgentProfile,
    strategy: GenomeStrategy,
    table: CodonTable,
    rng: RNGManager,
) -> SemanticGenome:
    if strategy == "uniform_random":
        return _uniform_genome(profile.genome_length, table, rng)
    if strategy == "profiled_random":
        return _profiled_genome(profile, table, rng)
    msg = f"Unsupported genome strategy {strategy!r} for profile generation."
    raise ConfigurationError(msg)


def _uniform_genome(length: int, table: CodonTable, rng: RNGManager) -> SemanticGenome:
    bits = tuple(codon.bits for codon in table.actions())
    codons = tuple(rng.choice(bits) for _ in range(length))
    return SemanticGenome.from_codons(codons)


def _profiled_genome(profile: AgentProfile, table: CodonTable, rng: RNGManager) -> SemanticGenome:
    all_codons = tuple(codon.bits for codon in table.actions())
    preferred = profile.preferred_codons or all_codons
    codons: list[str] = []
    for _ in range(profile.genome_length):
        if rng.random() < profile.preferred_codons_weight:
            codons.append(rng.choice(preferred))
        else:
            codons.append(rng.choice(all_codons))
    return SemanticGenome.from_codons(tuple(codons))


def _lineage_seeded_specs(
    config: InitializationConfig,
    profiles: tuple[AgentProfile, ...],
    placements: tuple[Position, ...],
    table: CodonTable,
    rng: RNGManager,
) -> tuple[AgentSpec, ...]:
    counts = _profile_counts(profiles, config.count)
    all_positions = iter(placements)
    specs: list[AgentSpec] = []
    lineage_config = config.lineage_config
    for profile in profiles:
        profile_rng = rng.fork(profile.name)
        ancestors: list[tuple[str, SemanticGenome]] = []
        profile_count = counts[profile.name]
        ancestor_limit = min(lineage_config.ancestor_count, profile_count)
        for local_index in range(profile_count):
            position = next(all_positions)
            lineage_id = profile.lineage_id or f"lineage-{profile.name}"
            agent_id = f"{config.prefix}-{len(specs) + 1}"
            if local_index < ancestor_limit:
                genome = _profiled_genome(
                    profile, table, profile_rng.fork(f"ancestor-{local_index}")
                )
                ancestors.append((agent_id, genome))
                parent_id = None
                generation = 0
            else:
                parent_id, parent_genome = ancestors[local_index % len(ancestors)]
                genome = parent_genome
                child_rng = profile_rng.fork(f"child-{local_index}")
                for step in range(lineage_config.mutation_steps):
                    operation = child_rng.choice(lineage_config.mutation_operations)
                    mutation = Mutation(
                        operation=operation,
                        rng=child_rng.fork(f"{operation}-{local_index}-{step}"),
                    )
                    genome = mutation.apply(
                        genome,
                        parent_id=parent_id,
                        generation=step + 1,
                        codon_table=table,
                    )
                generation = lineage_config.mutation_steps
            specs.append(
                AgentSpec(
                    agent_id=agent_id,
                    genome=genome,
                    initial_atp=profile.initial_atp,
                    position=position,
                    profile=profile.name,
                    lineage_id=lineage_id,
                    parent_id=parent_id,
                    generation=generation,
                )
            )
    return tuple(specs)


def _latin_hypercube_specs(
    config: InitializationConfig,
    profiles: tuple[AgentProfile, ...],
    placements: tuple[Position, ...],
    table: CodonTable,
    rng: RNGManager,
) -> tuple[AgentSpec, ...]:
    """Pure-Python LHS-inspired parameter coverage for initialization.

    This is intentionally a lightweight approximation: each sampled dimension is
    stratified into ``count`` bins, then bins are deterministically shuffled per
    dimension. It is not a full SciPy QMC replacement.
    """

    if len(profiles) != 1:
        msg = "latin_hypercube_lite currently supports exactly one profile."
        raise ConfigurationError(msg)
    positions = iter(placements)
    base_profile = profiles[0]
    dimensions = _lhs_dimensions(config.count, rng)
    specs: list[AgentSpec] = []
    for index, sample in enumerate(dimensions):
        genome_length = max(1, round(3 + sample[0] * max(config.genome_length, 1) * 2))
        atp = round(max(0.0, config.initial_atp * (0.5 + sample[1])), 3)
        preferred_weight = min(1.0, max(0.0, sample[2]))
        profile = AgentProfile(
            name=base_profile.name,
            genome_length=genome_length,
            initial_atp=atp,
            preferred_codons=base_profile.preferred_codons,
            preferred_codons_weight=preferred_weight,
            lineage_id=base_profile.lineage_id,
        )
        specs.append(
            AgentSpec(
                agent_id=f"{config.prefix}-{index + 1}",
                genome=_profiled_genome(profile, table, rng.fork(f"lhs-{index}")),
                initial_atp=atp,
                position=next(positions),
                profile=profile.name,
                lineage_id=profile.lineage_id,
            )
        )
    return tuple(specs)


def _lhs_dimensions(count: int, rng: RNGManager) -> tuple[tuple[float, float, float], ...]:
    columns: list[tuple[float, ...]] = []
    for dim in range(3):
        dim_rng = rng.fork(f"lhs-dim-{dim}")
        values = tuple((index + dim_rng.random()) / count for index in range(count))
        columns.append(values)
    shuffled_columns = tuple(
        _shuffle_float_column(column, rng.fork(f"lhs-shuffle-{i}"))
        for i, column in enumerate(columns)
    )
    rows: list[tuple[float, float, float]] = []
    for row in range(count):
        rows.append(
            cast(
                tuple[float, float, float],
                tuple(column[row] for column in shuffled_columns),
            )
        )
    return tuple(rows)


def _shuffle_float_column(values: tuple[float, ...], rng: RNGManager) -> tuple[float, ...]:
    items = list(values)
    for index in range(len(items) - 1, 0, -1):
        swap = rng.randrange(index + 1)
        items[index], items[swap] = items[swap], items[index]
    return tuple(items)


def _str(value: JsonValue, name: str) -> str:
    if not isinstance(value, str):
        msg = f"{name} must be a string."
        raise ConfigurationError(msg)
    return value


def _optional_str(value: JsonValue, name: str) -> str | None:
    if value is None:
        return None
    return _str(value, name)


def _int(value: JsonValue, name: str) -> int:
    if not isinstance(value, int):
        msg = f"{name} must be an integer."
        raise ConfigurationError(msg)
    return value


def _optional_int(value: JsonValue, name: str) -> int | None:
    if value is None:
        return None
    return _int(value, name)


def _float(value: JsonValue, name: str) -> float:
    if not isinstance(value, int | float):
        msg = f"{name} must be numeric."
        raise ConfigurationError(msg)
    return float(value)


def _bool(value: JsonValue, name: str) -> bool:
    if not isinstance(value, bool):
        msg = f"{name} must be a boolean."
        raise ConfigurationError(msg)
    return value


def _position_from_json(value: JsonValue) -> Position:
    if (
        not isinstance(value, list)
        or len(value) != 2
        or not isinstance(value[0], int)
        or not isinstance(value[1], int)
    ):
        msg = "position must be [x, y]."
        raise ConfigurationError(msg)
    return (value[0], value[1])


def _zone_from_json(value: JsonValue) -> tuple[int, int, int, int]:
    if (
        not isinstance(value, list)
        or len(value) != 4
        or not all(isinstance(item, int) for item in value)
    ):
        msg = "placement_zone must be [x1, y1, x2, y2]."
        raise ConfigurationError(msg)
    x1, y1, x2, y2 = value
    if (
        not isinstance(x1, int)
        or not isinstance(y1, int)
        or not isinstance(x2, int)
        or not isinstance(y2, int)
    ):
        msg = "placement_zone must be [x1, y1, x2, y2]."
        raise ConfigurationError(msg)
    return (x1, y1, x2, y2)
