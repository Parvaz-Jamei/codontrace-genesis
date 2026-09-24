"""Phase C dynamic / fluctuating environment substrate.

Opt-in peer-compatible resource dynamics for GENESIS: chemostat pools
(``RESOURCE`` initial/inflow/outflow), periodic/seasonal schedules,
fluctuating regimes, and spatial patches with deterministic diffusion/decay
hooks. Disabled by default so asexual and sexual research digests stay stable.

Literature grounding (software capability only, not an Avida replacement):

- Ofria & Wilke 2004, *Artificial Life* 10(2): environment = resources +
  reactions; a resource has initial quantity (optionally infinite), inflow
  per update, and outflow as the fraction of unused resource removed.
- Cooper & Ofria limited-resource ecosystems; Avida chemostat experiments
  commonly use ~1% unused-resource outflow.
- Avida-ED resource modes: unlimited / limited / chemostat / periodic
  (period < 1 ⇒ non-periodic), including inflow/cell and outflow fraction.
- Phenotypic-plasticity studies in Avida contrast static vs fluctuating
  environments (e.g. Lalejini et al. 2021 Frontiers; Clune/Ofria/Adami
  sensory-plasticity work). This module supplies the *environment
  substrate* for those designs. It does not claim that plasticity evolved.

Claim ceiling: runtime_observation only.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from enum import StrEnum
from typing import cast

from codontrace._types import JsonValue
from codontrace.errors import ConfigurationError
from codontrace.genesis.canonical import canonical_digest, require_finite_float
from codontrace.trace import (
    WORLD_EVENT_ENVIRONMENT_HAZARD_CHANGED,
    WORLD_EVENT_ENVIRONMENT_INFLOW,
    WORLD_EVENT_ENVIRONMENT_OUTFLOW,
    WORLD_EVENT_ENVIRONMENT_PERIODIC_TOGGLE,
    WORLD_EVENT_ENVIRONMENT_REGIME_SWITCH,
    Trace,
    WorldEvent,
)
from codontrace.world import World2D

_SPATIAL_MODES = frozenset({"global_pool", "local_patches", "global_and_local"})
_SCHEDULE_KINDS = frozenset({"static", "periodic", "seeded_events"})
_PATCH_UPDATE_MODES = frozenset({"replace", "inflow"})
_ENV_CLAIM_CEILING = "runtime_observation"


class SpatialResourceMode(StrEnum):
    """Where resource mass lives: well-mixed pool, local patches, or both."""

    GLOBAL_POOL = "global_pool"
    LOCAL_PATCHES = "local_patches"
    GLOBAL_AND_LOCAL = "global_and_local"


class ScheduleKind(StrEnum):
    """How regimes advance. ``periodic`` follows Avida-ED (period < 1 = static)."""

    STATIC = "static"
    PERIODIC = "periodic"
    SEEDED_EVENTS = "seeded_events"


def apply_chemostat_step(
    amount: float,
    *,
    inflow: float,
    outflow: float,
    consumed: float = 0.0,
    unlimited: bool = False,
) -> tuple[float, float, float]:
    """Apply one Avida ``RESOURCE`` update.

    After consumption, ``outflow`` is the fraction of *unused* resource
    removed, then ``inflow`` is added (Ofria & Wilke 2004; Cooper/Ofria
    chemostat: typically outflow=0.01). Unlimited resources skip depletion
    and turnover and keep the current amount.

    Returns ``(new_amount, outflow_removed, inflow_added)``.
    """

    current = require_finite_float("chemostat_amount", amount, non_negative=True)
    inflow_v = require_finite_float("chemostat_inflow", inflow, non_negative=True)
    outflow_v = require_finite_float(
        "chemostat_outflow", outflow, non_negative=True, probability=True
    )
    consumed_v = require_finite_float("chemostat_consumed", consumed, non_negative=True)
    if unlimited:
        return round(current, 10), 0.0, 0.0
    remaining = max(0.0, current - consumed_v)
    removed = round(remaining * outflow_v, 10)
    added = round(inflow_v, 10)
    new_amount = round(remaining - removed + added, 10)
    return new_amount, removed, added


def diffuse_local_patches(
    amounts: Mapping[tuple[int, int], float],
    *,
    width: int,
    height: int,
    rate: float,
    walls: set[tuple[int, int]] | None = None,
) -> dict[tuple[int, int], float]:
    """Deterministic von Neumann diffusion matching ElementGrid neighbor geometry.

    Mass is conserved aside from rounding to 10 decimal places. ``rate`` is the
    fraction of each cell that moves to neighbors this tick.
    """

    move_rate = require_finite_float("diffusion_rate", rate, non_negative=True, probability=True)
    blocked = walls or set()
    next_amounts: dict[tuple[int, int], float] = {}
    cells = {(x, y) for y in range(height) for x in range(width) if (x, y) not in blocked}

    def _add(position: tuple[int, int], value: float) -> None:
        if value <= 0:
            return
        next_amounts[position] = round(next_amounts.get(position, 0.0) + value, 10)

    for position in sorted(cells):
        amount = float(amounts.get(position, 0.0))
        if amount <= 0:
            continue
        neighbors = _von_neumann_neighbors(position, width=width, height=height, blocked=blocked)
        movable = round(amount * move_rate, 10)
        kept = round(amount - movable, 10)
        _add(position, kept)
        if movable > 0 and neighbors:
            share = round(movable / len(neighbors), 10)
            remainder = round(movable - share * len(neighbors), 10)
            for neighbor in neighbors:
                _add(neighbor, share)
            _add(position, remainder)
        elif movable > 0:
            _add(position, movable)
    return {pos: value for pos, value in next_amounts.items() if value > 0}


def decay_local_patches(
    amounts: Mapping[tuple[int, int], float],
    *,
    rate: float,
) -> dict[tuple[int, int], float]:
    """Multiply every local patch by ``(1 - rate)``. Rate 0 is a no-op."""

    decay_rate = require_finite_float("decay_rate", rate, non_negative=True, probability=True)
    keep = 1.0 - decay_rate
    decayed: dict[tuple[int, int], float] = {}
    for position, amount in amounts.items():
        kept = round(float(amount) * keep, 10)
        if kept > 0:
            decayed[position] = kept
    return decayed


def _von_neumann_neighbors(
    position: tuple[int, int],
    *,
    width: int,
    height: int,
    blocked: set[tuple[int, int]],
) -> tuple[tuple[int, int], ...]:
    candidates = (
        (position[0] + 1, position[1]),
        (position[0] - 1, position[1]),
        (position[0], position[1] + 1),
        (position[0], position[1] - 1),
    )
    return tuple(
        item
        for item in candidates
        if 0 <= item[0] < width and 0 <= item[1] < height and item not in blocked
    )


@dataclass(frozen=True, slots=True)
class ResourceSpec:
    """One Avida ``RESOURCE name:initial=:inflow=:outflow=`` line.

    ``unlimited`` is the Avida-ED unlimited / non-depletable mode. ``cell_inflow``
    is the optional Avida-ED spatial Inflow/cell term used when restocking patches.
    """

    name: str
    initial: float = 0.0
    inflow: float = 0.0
    outflow: float = 0.0
    unlimited: bool = False
    cell_inflow: float = 0.0

    def __post_init__(self) -> None:
        if not self.name or any(char.isspace() for char in self.name):
            raise ConfigurationError("ResourceSpec.name must be a non-empty token.")
        _set_finite(self, "initial", self.initial)
        _set_finite(self, "inflow", self.inflow)
        _set_finite(self, "outflow", self.outflow, probability=True)
        _set_finite(self, "cell_inflow", self.cell_inflow)

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "name": self.name,
            "initial": self.initial,
            "inflow": self.inflow,
            "outflow": self.outflow,
            "unlimited": self.unlimited,
            "cell_inflow": self.cell_inflow,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, JsonValue]) -> ResourceSpec:
        return cls(
            name=_str(data, "name"),
            initial=_float(data, "initial", 0.0),
            inflow=_float(data, "inflow", 0.0),
            outflow=_float(data, "outflow", 0.0),
            unlimited=_bool(data, "unlimited", False),
            cell_inflow=_float(data, "cell_inflow", 0.0),
        )

    def digest(self) -> str:
        return canonical_digest(self.to_dict())


@dataclass(frozen=True, slots=True)
class EnvironmentRegime:
    """One named environmental state (high-food, low-food, or a niche map).

    ``niche_patches`` is an explicit per-cell reward/abundance map
    ``((x, y, amount), ...)``. Empty means "use schedule patch_cells × scales".
    This is a selectable regime for later plasticity experiments; selecting it
    does not claim that plasticity evolved.
    """

    name: str
    inflow_scale: float = 1.0
    outflow_scale: float = 1.0
    patch_amount_scale: float = 1.0
    hazard_intensity: float = 0.0
    resource_inflow: dict[str, float] = field(default_factory=dict)
    niche_patches: tuple[tuple[int, int, float], ...] = ()

    def __post_init__(self) -> None:
        if not self.name:
            raise ConfigurationError("EnvironmentRegime.name must not be empty.")
        _set_finite(self, "inflow_scale", self.inflow_scale)
        _set_finite(self, "outflow_scale", self.outflow_scale)
        _set_finite(self, "patch_amount_scale", self.patch_amount_scale)
        _set_finite(self, "hazard_intensity", self.hazard_intensity)
        normalized: dict[str, float] = {}
        for key, value in self.resource_inflow.items():
            if not key:
                raise ConfigurationError("resource_inflow keys must be non-empty.")
            normalized[str(key)] = require_finite_float(
                f"resource_inflow.{key}", value, non_negative=True
            )
        object.__setattr__(self, "resource_inflow", dict(sorted(normalized.items())))
        patches: list[tuple[int, int, float]] = []
        for item in self.niche_patches:
            if len(item) != 3:
                raise ConfigurationError("niche_patches entries must be (x, y, amount).")
            x, y, amount = item
            if (
                not isinstance(x, int)
                or not isinstance(y, int)
                or isinstance(x, bool)
                or isinstance(y, bool)
            ):
                raise ConfigurationError("niche_patches coordinates must be integers.")
            patches.append(
                (x, y, require_finite_float("niche_patch_amount", amount, non_negative=True))
            )
        object.__setattr__(self, "niche_patches", tuple(patches))

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "name": self.name,
            "inflow_scale": self.inflow_scale,
            "outflow_scale": self.outflow_scale,
            "patch_amount_scale": self.patch_amount_scale,
            "hazard_intensity": self.hazard_intensity,
            "resource_inflow": dict(self.resource_inflow),
            "niche_patches": [[x, y, amount] for x, y, amount in self.niche_patches],
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, JsonValue]) -> EnvironmentRegime:
        inflow_raw = data.get("resource_inflow", {})
        if inflow_raw is None:
            inflow_map: dict[str, float] = {}
        elif not isinstance(inflow_raw, Mapping):
            raise ConfigurationError("resource_inflow must be an object.")
        else:
            inflow_map = {
                str(key): _float(cast(Mapping[str, JsonValue], {str(key): value}), str(key), 0.0)
                for key, value in inflow_raw.items()
            }
        patches_raw = data.get("niche_patches", [])
        patches: list[tuple[int, int, float]] = []
        if patches_raw:
            if not isinstance(patches_raw, list):
                raise ConfigurationError("niche_patches must be a list.")
            for item in patches_raw:
                if not isinstance(item, list) or len(item) != 3:
                    raise ConfigurationError("niche_patches entries must be [x, y, amount].")
                x, y, amount = item
                if (
                    isinstance(x, bool)
                    or isinstance(y, bool)
                    or not isinstance(x, int)
                    or not isinstance(y, int)
                ):
                    raise ConfigurationError("niche_patches coordinates must be integers.")
                if isinstance(amount, bool) or not isinstance(amount, int | float):
                    raise ConfigurationError("niche_patches amount must be numeric.")
                patches.append((x, y, float(amount)))
        return cls(
            name=_str(data, "name"),
            inflow_scale=_float(data, "inflow_scale", 1.0),
            outflow_scale=_float(data, "outflow_scale", 1.0),
            patch_amount_scale=_float(data, "patch_amount_scale", 1.0),
            hazard_intensity=_float(data, "hazard_intensity", 0.0),
            resource_inflow=inflow_map,
            niche_patches=tuple(patches),
        )


@dataclass(frozen=True, slots=True)
class EnvironmentSchedule:
    """Deterministic regime schedule (Avida-ED periodic, or seeded events).

    Period < 1 (including 0) is non-periodic, matching Avida-ED
    ``period < 1 ==> non-periodic``. ``seeded_events`` advances the regime
    index at each listed tick. This object is digest-backed for replay.
    """

    kind: str = "static"
    period_ticks: int = 0
    phase_offset: int = 0
    regimes: tuple[EnvironmentRegime, ...] = ()
    switch_ticks: tuple[int, ...] = ()

    def __post_init__(self) -> None:
        if self.kind not in _SCHEDULE_KINDS:
            raise ConfigurationError(
                f"EnvironmentSchedule.kind must be one of {sorted(_SCHEDULE_KINDS)!r}."
            )
        if self.period_ticks < 0:
            raise ConfigurationError("period_ticks must be >= 0.")
        if self.phase_offset < 0:
            raise ConfigurationError("phase_offset must be >= 0.")
        if any(tick < 0 for tick in self.switch_ticks):
            raise ConfigurationError("switch_ticks must be non-negative.")
        object.__setattr__(self, "switch_ticks", tuple(sorted(self.switch_ticks)))
        if self.kind != "static" and len(self.regimes) < 1:
            raise ConfigurationError("non-static schedules require at least one regime.")

    @property
    def is_periodic(self) -> bool:
        return self.kind == "periodic" and self.period_ticks >= 1 and len(self.regimes) >= 2

    def regime_index_at(self, tick: int) -> int:
        """Return the deterministic regime index active at ``tick``."""

        n = len(self.regimes)
        if n == 0:
            return 0
        if self.kind == "static" or (self.kind == "periodic" and self.period_ticks < 1):
            return 0
        if self.kind == "periodic":
            phase = (max(0, tick) + self.phase_offset) // self.period_ticks
            return int(phase % n)
        index = 0
        for switch_tick in self.switch_ticks:
            if tick >= switch_tick:
                index += 1
            else:
                break
        return index % n

    def regime_at(self, tick: int) -> EnvironmentRegime | None:
        if not self.regimes:
            return None
        return self.regimes[self.regime_index_at(tick)]

    def is_switch_tick(self, tick: int) -> bool:
        if tick <= 0 or len(self.regimes) < 2:
            return False
        return self.regime_index_at(tick) != self.regime_index_at(tick - 1)

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "kind": self.kind,
            "period_ticks": self.period_ticks,
            "phase_offset": self.phase_offset,
            "regimes": [regime.to_dict() for regime in self.regimes],
            "switch_ticks": list(self.switch_ticks),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, JsonValue]) -> EnvironmentSchedule:
        regimes_raw = data.get("regimes", [])
        if not isinstance(regimes_raw, list):
            raise ConfigurationError("regimes must be a list.")
        switch_raw = data.get("switch_ticks", [])
        if not isinstance(switch_raw, list) or any(
            isinstance(item, bool) or not isinstance(item, int) for item in switch_raw
        ):
            raise ConfigurationError("switch_ticks must be a list of integers.")
        return cls(
            kind=_str(data, "kind", "static"),
            period_ticks=_int(data, "period_ticks", 0),
            phase_offset=_int(data, "phase_offset", 0),
            regimes=tuple(
                EnvironmentRegime.from_dict(item)
                for item in regimes_raw
                if isinstance(item, Mapping)
            ),
            switch_ticks=tuple(int(item) for item in switch_raw),
        )

    def digest(self) -> str:
        return canonical_digest(self.to_dict())


@dataclass(frozen=True, slots=True)
class EnvironmentConfig:
    """Opt-in dynamic environment controls. Default disabled (digest-stable)."""

    enabled: bool = False
    resources: tuple[ResourceSpec, ...] = ()
    spatial_mode: str = "global_and_local"
    schedule: EnvironmentSchedule = field(default_factory=EnvironmentSchedule)
    patch_cells: tuple[tuple[int, int], ...] = ()
    patch_update_mode: str = "replace"
    diffusion_rate: float = 0.0
    decay_rate: float = 0.0
    skip_legacy_respawn: bool = True
    consume_from_global_pool: bool = True
    hazard_atp_scale: float = 0.0
    use_element_grid_physics: bool = False

    def __post_init__(self) -> None:
        if self.spatial_mode not in _SPATIAL_MODES:
            raise ConfigurationError(
                f"spatial_mode must be one of {sorted(_SPATIAL_MODES)!r}."
            )
        if self.patch_update_mode not in _PATCH_UPDATE_MODES:
            raise ConfigurationError(
                f"patch_update_mode must be one of {sorted(_PATCH_UPDATE_MODES)!r}."
            )
        object.__setattr__(
            self,
            "diffusion_rate",
            require_finite_float(
                "diffusion_rate", self.diffusion_rate, non_negative=True, probability=True
            ),
        )
        object.__setattr__(
            self,
            "decay_rate",
            require_finite_float(
                "decay_rate", self.decay_rate, non_negative=True, probability=True
            ),
        )
        object.__setattr__(
            self,
            "hazard_atp_scale",
            require_finite_float("hazard_atp_scale", self.hazard_atp_scale, non_negative=True),
        )
        names = [item.name for item in self.resources]
        if len(names) != len(set(names)):
            raise ConfigurationError("ResourceSpec names must be unique.")
        cells: list[tuple[int, int]] = []
        for item in self.patch_cells:
            if len(item) != 2 or isinstance(item[0], bool) or isinstance(item[1], bool):
                raise ConfigurationError("patch_cells must be (x, y) integer pairs.")
            cells.append((int(item[0]), int(item[1])))
        object.__setattr__(self, "patch_cells", tuple(cells))

    @property
    def uses_global_pool(self) -> bool:
        return self.enabled and self.spatial_mode in {"global_pool", "global_and_local"}

    @property
    def uses_local_patches(self) -> bool:
        return self.enabled and self.spatial_mode in {"local_patches", "global_and_local"}

    @classmethod
    def fluctuating_chemostat(
        cls,
        *,
        initial: float,
        inflow: float,
        outflow: float = 0.01,
        period_ticks: int = 4,
        patch_cells: Sequence[tuple[int, int]] = (),
        resource_name: str = "lumen",
        spatial_mode: str = "global_and_local",
        schedule_kind: str = "periodic",
        switch_ticks: Sequence[int] = (),
        high_inflow_scale: float = 2.0,
        low_inflow_scale: float = 0.25,
        high_patch_scale: float = 1.0,
        low_patch_scale: float = 1.0,
        high_hazard: float = 0.0,
        low_hazard: float = 1.0,
        cell_inflow: float = 0.0,
        diffusion_rate: float = 0.0,
        decay_rate: float = 0.0,
        hazard_atp_scale: float = 0.0,
        niche_maps: bool = False,
    ) -> EnvironmentConfig:
        """Build a two-regime chemostat (high-food vs low-food, or two niche maps)."""

        if niche_maps:
            cells = tuple(patch_cells)
            if len(cells) < 2:
                raise ConfigurationError("niche_maps requires at least two patch_cells.")
            high = EnvironmentRegime(
                name="niche_a",
                inflow_scale=high_inflow_scale,
                patch_amount_scale=high_patch_scale,
                hazard_intensity=high_hazard,
                niche_patches=(
                    (cells[0][0], cells[0][1], initial * 0.8),
                    (cells[1][0], cells[1][1], initial * 0.2),
                ),
            )
            low = EnvironmentRegime(
                name="niche_b",
                inflow_scale=low_inflow_scale,
                patch_amount_scale=low_patch_scale,
                hazard_intensity=low_hazard,
                niche_patches=(
                    (cells[0][0], cells[0][1], initial * 0.2),
                    (cells[1][0], cells[1][1], initial * 0.8),
                ),
            )
        else:
            high = EnvironmentRegime(
                name="high_food",
                inflow_scale=high_inflow_scale,
                patch_amount_scale=high_patch_scale,
                hazard_intensity=high_hazard,
            )
            low = EnvironmentRegime(
                name="low_food",
                inflow_scale=low_inflow_scale,
                patch_amount_scale=low_patch_scale,
                hazard_intensity=low_hazard,
            )
        kind = schedule_kind if schedule_kind in _SCHEDULE_KINDS else "periodic"
        schedule = EnvironmentSchedule(
            kind=kind,
            period_ticks=period_ticks,
            regimes=(high, low),
            switch_ticks=tuple(switch_ticks),
        )
        return cls(
            enabled=True,
            resources=(
                ResourceSpec(
                    name=resource_name,
                    initial=initial,
                    inflow=inflow,
                    outflow=outflow,
                    cell_inflow=cell_inflow,
                ),
            ),
            spatial_mode=spatial_mode,
            schedule=schedule,
            patch_cells=tuple(patch_cells),
            diffusion_rate=diffusion_rate,
            decay_rate=decay_rate,
            hazard_atp_scale=hazard_atp_scale,
        )

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "enabled": self.enabled,
            "resources": [item.to_dict() for item in self.resources],
            "spatial_mode": self.spatial_mode,
            "schedule": self.schedule.to_dict(),
            "patch_cells": [[x, y] for x, y in self.patch_cells],
            "patch_update_mode": self.patch_update_mode,
            "diffusion_rate": self.diffusion_rate,
            "decay_rate": self.decay_rate,
            "skip_legacy_respawn": self.skip_legacy_respawn,
            "consume_from_global_pool": self.consume_from_global_pool,
            "hazard_atp_scale": self.hazard_atp_scale,
            "use_element_grid_physics": self.use_element_grid_physics,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, JsonValue]) -> EnvironmentConfig:
        resources_raw = data.get("resources", [])
        if not isinstance(resources_raw, list):
            raise ConfigurationError("resources must be a list.")
        cells_raw = data.get("patch_cells", [])
        cells: list[tuple[int, int]] = []
        if cells_raw:
            if not isinstance(cells_raw, list):
                raise ConfigurationError("patch_cells must be a list.")
            for item in cells_raw:
                if not isinstance(item, list) or len(item) != 2:
                    raise ConfigurationError("patch_cells entries must be [x, y].")
                x, y = item
                if (
                    isinstance(x, bool)
                    or isinstance(y, bool)
                    or not isinstance(x, int)
                    or not isinstance(y, int)
                ):
                    raise ConfigurationError("patch_cells coordinates must be integers.")
                cells.append((x, y))
        schedule_raw = data.get("schedule", {})
        return cls(
            enabled=_bool(data, "enabled", False),
            resources=tuple(
                ResourceSpec.from_dict(item) for item in resources_raw if isinstance(item, Mapping)
            ),
            spatial_mode=_str(data, "spatial_mode", "global_and_local"),
            schedule=EnvironmentSchedule.from_dict(schedule_raw)
            if isinstance(schedule_raw, Mapping)
            else EnvironmentSchedule(),
            patch_cells=tuple(cells),
            patch_update_mode=_str(data, "patch_update_mode", "replace"),
            diffusion_rate=_float(data, "diffusion_rate", 0.0),
            decay_rate=_float(data, "decay_rate", 0.0),
            skip_legacy_respawn=_bool(data, "skip_legacy_respawn", True),
            consume_from_global_pool=_bool(data, "consume_from_global_pool", True),
            hazard_atp_scale=_float(data, "hazard_atp_scale", 0.0),
            use_element_grid_physics=_bool(data, "use_element_grid_physics", False),
        )

    def digest(self) -> str:
        return canonical_digest(self.to_dict())


@dataclass(frozen=True, slots=True)
class EnvironmentState:
    """Runtime chemostat / schedule state carried on ``PopulationState``."""

    tick: int = 0
    pools: dict[str, float] = field(default_factory=dict)
    active_regime: str = ""
    hazard_intensity: float = 0.0
    last_switch_tick: int | None = None
    cumulative_inflow: dict[str, float] = field(default_factory=dict)
    cumulative_outflow: dict[str, float] = field(default_factory=dict)
    cumulative_consumed: dict[str, float] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.tick < 0:
            raise ConfigurationError("EnvironmentState.tick must be non-negative.")
        object.__setattr__(self, "pools", _finite_amount_map(self.pools, "pools"))
        object.__setattr__(
            self,
            "hazard_intensity",
            require_finite_float("hazard_intensity", self.hazard_intensity, non_negative=True),
        )
        object.__setattr__(
            self,
            "cumulative_inflow",
            _finite_amount_map(self.cumulative_inflow, "cumulative_inflow"),
        )
        object.__setattr__(
            self,
            "cumulative_outflow",
            _finite_amount_map(self.cumulative_outflow, "cumulative_outflow"),
        )
        object.__setattr__(
            self,
            "cumulative_consumed",
            _finite_amount_map(self.cumulative_consumed, "cumulative_consumed"),
        )

    @classmethod
    def initialize(cls, config: EnvironmentConfig, *, tick: int = 0) -> EnvironmentState:
        regime = config.schedule.regime_at(tick)
        pools = {spec.name: spec.initial for spec in config.resources}
        return cls(
            tick=tick,
            pools=pools,
            active_regime="" if regime is None else regime.name,
            hazard_intensity=0.0 if regime is None else regime.hazard_intensity,
            last_switch_tick=None,
            cumulative_inflow={spec.name: 0.0 for spec in config.resources},
            cumulative_outflow={spec.name: 0.0 for spec in config.resources},
            cumulative_consumed={spec.name: 0.0 for spec in config.resources},
        )

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "tick": self.tick,
            "pools": dict(sorted(self.pools.items())),
            "active_regime": self.active_regime,
            "hazard_intensity": self.hazard_intensity,
            "last_switch_tick": self.last_switch_tick,
            "cumulative_inflow": dict(sorted(self.cumulative_inflow.items())),
            "cumulative_outflow": dict(sorted(self.cumulative_outflow.items())),
            "cumulative_consumed": dict(sorted(self.cumulative_consumed.items())),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, JsonValue]) -> EnvironmentState:
        switch_raw = data.get("last_switch_tick")
        last_switch = None if switch_raw is None else _int(data, "last_switch_tick", 0)
        return cls(
            tick=_int(data, "tick", 0),
            pools=_float_map(data, "pools"),
            active_regime=_str(data, "active_regime", ""),
            hazard_intensity=_float(data, "hazard_intensity", 0.0),
            last_switch_tick=last_switch,
            cumulative_inflow=_float_map(data, "cumulative_inflow"),
            cumulative_outflow=_float_map(data, "cumulative_outflow"),
            cumulative_consumed=_float_map(data, "cumulative_consumed"),
        )

    def digest(self) -> str:
        return canonical_digest(self.to_dict())


@dataclass(frozen=True, slots=True)
class EnvironmentEvent:
    """Digest-backed record for one environment mutation this tick."""

    tick: int
    event_type: str
    resource: str | None = None
    amount: float = 0.0
    regime_before: str | None = None
    regime_after: str | None = None
    position: tuple[int, int] | None = None
    status: str = "measured"
    metadata: dict[str, JsonValue] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.event_type:
            raise ConfigurationError("EnvironmentEvent.event_type must not be empty.")
        _set_finite(self, "amount", self.amount, name="EnvironmentEvent.amount")

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "schema_version": "environment_event_v1",
            "tick": self.tick,
            "event_type": self.event_type,
            "resource": self.resource,
            "amount": self.amount,
            "regime_before": self.regime_before,
            "regime_after": self.regime_after,
            "position": None if self.position is None else [self.position[0], self.position[1]],
            "status": self.status,
            "metadata": dict(sorted(self.metadata.items())),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, JsonValue]) -> EnvironmentEvent:
        raw_pos = data.get("position")
        pos = None
        if isinstance(raw_pos, list) and len(raw_pos) == 2:
            pos = (int(raw_pos[0]), int(raw_pos[1]))
        meta_raw = data.get("metadata", {})
        metadata = dict(meta_raw) if isinstance(meta_raw, Mapping) else {}
        resource_raw = data.get("resource")
        return cls(
            tick=_int(data, "tick", 0),
            event_type=_str(data, "event_type", "unknown"),
            resource=None if resource_raw is None else str(resource_raw),
            amount=_float(data, "amount", 0.0),
            regime_before=_optional_str(data, "regime_before"),
            regime_after=_optional_str(data, "regime_after"),
            position=pos,
            status=_str(data, "status", "measured"),
            metadata={str(key): value for key, value in metadata.items()},
        )

    def digest(self) -> str:
        return canonical_digest(self.to_dict())


@dataclass(frozen=True, slots=True)
class EnvironmentSnapshot:
    """Per-tick resource levels for trajectory digests and replay checks."""

    tick: int
    pools: dict[str, float]
    patch_total: float
    patch_cells: int
    active_regime: str
    hazard_intensity: float
    inflow_applied: dict[str, float] = field(default_factory=dict)
    outflow_removed: dict[str, float] = field(default_factory=dict)
    consumed: dict[str, float] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "pools", _finite_amount_map(self.pools, "pools"))
        object.__setattr__(
            self,
            "patch_total",
            require_finite_float("patch_total", self.patch_total, non_negative=True),
        )
        object.__setattr__(
            self,
            "hazard_intensity",
            require_finite_float("hazard_intensity", self.hazard_intensity, non_negative=True),
        )

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "schema_version": "environment_snapshot_v1",
            "tick": self.tick,
            "pools": dict(sorted(self.pools.items())),
            "patch_total": self.patch_total,
            "patch_cells": self.patch_cells,
            "active_regime": self.active_regime,
            "hazard_intensity": self.hazard_intensity,
            "inflow_applied": dict(sorted(self.inflow_applied.items())),
            "outflow_removed": dict(sorted(self.outflow_removed.items())),
            "consumed": dict(sorted(self.consumed.items())),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, JsonValue]) -> EnvironmentSnapshot:
        return cls(
            tick=_int(data, "tick", 0),
            pools=_float_map(data, "pools"),
            patch_total=_float(data, "patch_total", 0.0),
            patch_cells=_int(data, "patch_cells", 0),
            active_regime=_str(data, "active_regime", ""),
            hazard_intensity=_float(data, "hazard_intensity", 0.0),
            inflow_applied=_float_map(data, "inflow_applied"),
            outflow_removed=_float_map(data, "outflow_removed"),
            consumed=_float_map(data, "consumed"),
        )

    def digest(self) -> str:
        return canonical_digest(self.to_dict())


@dataclass(frozen=True, slots=True)
class EnvironmentStepResult:
    """World, state, evidence records, and WorldEvents from one env tick."""

    world: World2D
    state: EnvironmentState
    events: tuple[EnvironmentEvent, ...]
    snapshot: EnvironmentSnapshot
    world_events: tuple[WorldEvent, ...]


@dataclass(frozen=True, slots=True)
class EnvironmentReplayVerification:
    """Replay check for an environment trajectory digest."""

    matched: bool
    expected_digest: str
    observed_digest: str
    snapshot_count: int
    claim_ceiling: str = _ENV_CLAIM_CEILING

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "matched": self.matched,
            "expected_digest": self.expected_digest,
            "observed_digest": self.observed_digest,
            "snapshot_count": self.snapshot_count,
            "claim_ceiling": self.claim_ceiling,
        }


@dataclass(frozen=True, slots=True)
class DynamicEnvironmentObservation:
    """Runtime observation of one dynamic-environment run. Not a plasticity claim."""

    environment_config_digest: str
    trajectory_digest: str
    ticks: int
    regime_switches: int
    environment_events: int
    unique_regimes: tuple[str, ...]
    pool_series: dict[str, tuple[float, ...]]
    patch_total_series: tuple[float, ...]
    hazard_series: tuple[float, ...]
    pool_range: dict[str, tuple[float, float]]
    claim_ceiling: str = _ENV_CLAIM_CEILING
    plasticity_evolved: bool = False

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "environment_config_digest": self.environment_config_digest,
            "trajectory_digest": self.trajectory_digest,
            "ticks": self.ticks,
            "regime_switches": self.regime_switches,
            "environment_events": self.environment_events,
            "unique_regimes": list(self.unique_regimes),
            "pool_series": {key: list(values) for key, values in sorted(self.pool_series.items())},
            "patch_total_series": list(self.patch_total_series),
            "hazard_series": list(self.hazard_series),
            "pool_range": {
                key: [lo, hi] for key, (lo, hi) in sorted(self.pool_range.items())
            },
            "claim_ceiling": self.claim_ceiling,
            "plasticity_evolved": self.plasticity_evolved,
        }


def environment_trajectory_digest(snapshots: Sequence[EnvironmentSnapshot]) -> str:
    """Return a replayable digest of an ordered environment trajectory."""

    return canonical_digest({"snapshots": [item.to_dict() for item in snapshots]})


def verify_environment_trajectory_replay(
    expected: Sequence[EnvironmentSnapshot],
    observed: Sequence[EnvironmentSnapshot],
) -> EnvironmentReplayVerification:
    """Compare two env trajectories by digest (CodonTrace replay advantage)."""

    expected_digest = environment_trajectory_digest(expected)
    observed_digest = environment_trajectory_digest(observed)
    return EnvironmentReplayVerification(
        matched=expected_digest == observed_digest and len(expected) == len(observed),
        expected_digest=expected_digest,
        observed_digest=observed_digest,
        snapshot_count=len(observed),
    )


def snapshots_from_generation_results(results: Sequence[object]) -> tuple[EnvironmentSnapshot, ...]:
    """Extract environment snapshots from generation/engine tick results."""

    snapshots: list[EnvironmentSnapshot] = []
    for item in results:
        snapshot = getattr(item, "environment_snapshot", None)
        if snapshot is None:
            generation = getattr(item, "generation_result", None)
            snapshot = None
            if generation is not None:
                snapshot = getattr(generation, "environment_snapshot", None)
        if isinstance(snapshot, EnvironmentSnapshot):
            snapshots.append(snapshot)
    return tuple(snapshots)


def summarize_dynamic_environment_observation(
    result: object,
    *,
    config: EnvironmentConfig | None = None,
) -> DynamicEnvironmentObservation:
    """Summarize per-tick pools, patches, regimes, and env events from a run."""

    if result is None:
        raise TypeError("summarize_dynamic_environment_observation requires a run result, not None.")
    if not hasattr(result, "ticks"):
        raise TypeError(
            "summarize_dynamic_environment_observation expected an object with a ticks collection."
        )
    ticks = result.ticks
    snapshots = snapshots_from_generation_results(ticks)
    events: list[EnvironmentEvent] = []
    for tick in ticks:
        generation = getattr(tick, "generation_result", None)
        records = ()
        if generation is not None:
            records = getattr(generation, "environment_records", ()) or ()
        else:
            records = getattr(tick, "environment_records", ()) or ()
        for record in records:
            if isinstance(record, EnvironmentEvent):
                events.append(record)
    pool_series: dict[str, list[float]] = {}
    patch_series: list[float] = []
    hazard_series: list[float] = []
    regimes: list[str] = []
    for snapshot in snapshots:
        patch_series.append(snapshot.patch_total)
        hazard_series.append(snapshot.hazard_intensity)
        if snapshot.active_regime:
            regimes.append(snapshot.active_regime)
        for name, amount in snapshot.pools.items():
            pool_series.setdefault(name, []).append(amount)
    pool_range = {
        name: (min(values), max(values)) for name, values in pool_series.items() if values
    }
    switches = sum(
        1 for event in events if event.event_type in {"regime_switch", "periodic_toggle"}
    )
    config_digest = config.digest() if config is not None else ""
    if not config_digest:
        spec = getattr(result, "spec", None)
        population_configs = None if spec is None else getattr(spec, "population_configs", None)
        env = None
        if population_configs is not None:
            env = getattr(population_configs, "environment", None)
        if env is not None and getattr(env, "enabled", False):
            config_digest = env.digest()
    return DynamicEnvironmentObservation(
        environment_config_digest=config_digest,
        trajectory_digest=environment_trajectory_digest(snapshots),
        ticks=len(snapshots),
        regime_switches=switches,
        environment_events=len(events),
        unique_regimes=tuple(dict.fromkeys(regimes)),
        pool_series={key: tuple(values) for key, values in pool_series.items()},
        patch_total_series=tuple(patch_series),
        hazard_series=tuple(hazard_series),
        pool_range=pool_range,
    )


def step_environment(
    world: World2D,
    state: EnvironmentState,
    config: EnvironmentConfig,
    *,
    tick: int,
    consumed: Mapping[str, float] | None = None,
    occupied_positions: set[tuple[int, int]] | None = None,
) -> EnvironmentStepResult:
    """Advance chemostat, schedule, and spatial hooks one deterministic tick.

    Order follows Avida updates: organisms have already consumed; unused
    fraction flows out; inflow is added; then spatial restock / diffusion /
    decay. Does not mutate the caller's world (clones first).
    """

    working = world.clone()
    env_trace = Trace()
    events: list[EnvironmentEvent] = []
    consumed_map = {key: float(value) for key, value in dict(consumed or {}).items()}
    regime = config.schedule.regime_at(tick)
    previous_regime = state.active_regime
    switched = config.schedule.is_switch_tick(tick)
    hazard = 0.0 if regime is None else regime.hazard_intensity
    pools = dict(state.pools)
    inflow_applied: dict[str, float] = {}
    outflow_removed: dict[str, float] = {}
    cumulative_inflow = dict(state.cumulative_inflow)
    cumulative_outflow = dict(state.cumulative_outflow)
    cumulative_consumed = dict(state.cumulative_consumed)

    if config.uses_global_pool or config.resources:
        for spec in config.resources:
            used = consumed_map.get(spec.name, 0.0)
            if spec.unlimited or not config.consume_from_global_pool:
                used = 0.0
            inflow = _effective_inflow(spec, regime)
            outflow = _effective_outflow(spec, regime)
            new_amount, removed, added = apply_chemostat_step(
                pools.get(spec.name, spec.initial),
                inflow=inflow,
                outflow=outflow,
                consumed=used,
                unlimited=spec.unlimited,
            )
            pools[spec.name] = new_amount
            inflow_applied[spec.name] = added
            outflow_removed[spec.name] = removed
            cumulative_inflow[spec.name] = round(cumulative_inflow.get(spec.name, 0.0) + added, 10)
            cumulative_outflow[spec.name] = round(
                cumulative_outflow.get(spec.name, 0.0) + removed, 10
            )
            cumulative_consumed[spec.name] = round(
                cumulative_consumed.get(spec.name, 0.0) + consumed_map.get(spec.name, 0.0), 10
            )
            events.append(
                EnvironmentEvent(
                    tick=tick,
                    event_type="chemostat_update",
                    resource=spec.name,
                    amount=new_amount,
                    metadata={
                        "inflow": added,
                        "outflow_removed": removed,
                        "consumed": consumed_map.get(spec.name, 0.0),
                        "unlimited": spec.unlimited,
                    },
                )
            )
            if added > 0:
                env_trace.append_world_event(
                    _world_event(
                        WORLD_EVENT_ENVIRONMENT_INFLOW,
                        tick=tick,
                        sequence=env_trace.next_sequence(),
                        amount=added,
                        reason="chemostat_inflow",
                        metadata={"resource": spec.name},
                    )
                )
            if removed > 0:
                env_trace.append_world_event(
                    _world_event(
                        WORLD_EVENT_ENVIRONMENT_OUTFLOW,
                        tick=tick,
                        sequence=env_trace.next_sequence(),
                        amount=removed,
                        reason="chemostat_outflow",
                        metadata={"resource": spec.name},
                    )
                )

    if switched and regime is not None:
        event_type = "periodic_toggle" if config.schedule.is_periodic else "regime_switch"
        events.append(
            EnvironmentEvent(
                tick=tick,
                event_type=event_type,
                amount=0.0,
                regime_before=previous_regime or None,
                regime_after=regime.name,
                metadata={
                    "schedule_kind": config.schedule.kind,
                    "period_ticks": config.schedule.period_ticks,
                },
            )
        )
        world_type = (
            WORLD_EVENT_ENVIRONMENT_PERIODIC_TOGGLE
            if event_type == "periodic_toggle"
            else WORLD_EVENT_ENVIRONMENT_REGIME_SWITCH
        )
        env_trace.append_world_event(
            _world_event(
                world_type,
                tick=tick,
                sequence=env_trace.next_sequence(),
                reason=event_type,
                metadata={"regime_before": previous_regime, "regime_after": regime.name},
            )
        )
        if hazard != state.hazard_intensity:
            events.append(
                EnvironmentEvent(
                    tick=tick,
                    event_type="hazard_changed",
                    amount=hazard,
                    regime_before=previous_regime or None,
                    regime_after=regime.name,
                )
            )
            env_trace.append_world_event(
                _world_event(
                    WORLD_EVENT_ENVIRONMENT_HAZARD_CHANGED,
                    tick=tick,
                    sequence=env_trace.next_sequence(),
                    amount=hazard,
                    reason="hazard_changed",
                    metadata={"regime": "" if regime is None else regime.name},
                )
            )

    if config.uses_local_patches:
        working, patch_events, patch_world_events = _apply_spatial_patches(
            working,
            config=config,
            regime=regime,
            pools=pools,
            tick=tick,
            occupied=occupied_positions or set(),
            env_trace=env_trace,
        )
        events.extend(patch_events)
        # patch helpers already appended WorldEvents onto env_trace
        del patch_world_events

    patch_total = round(sum(working.resources.values()), 10)
    snapshot = EnvironmentSnapshot(
        tick=tick,
        pools=dict(sorted(pools.items())),
        patch_total=patch_total,
        patch_cells=len(working.resources),
        active_regime="" if regime is None else regime.name,
        hazard_intensity=hazard,
        inflow_applied=inflow_applied,
        outflow_removed=outflow_removed,
        consumed=dict(sorted(consumed_map.items())),
    )
    new_state = EnvironmentState(
        tick=tick,
        pools=pools,
        active_regime="" if regime is None else regime.name,
        hazard_intensity=hazard,
        last_switch_tick=tick if switched else state.last_switch_tick,
        cumulative_inflow=cumulative_inflow,
        cumulative_outflow=cumulative_outflow,
        cumulative_consumed=cumulative_consumed,
    )
    return EnvironmentStepResult(
        world=working,
        state=new_state,
        events=tuple(events),
        snapshot=snapshot,
        world_events=env_trace.world_events,
    )


def local_resource_consumed(
    before: Mapping[tuple[int, int], float],
    after: Mapping[tuple[int, int], float],
) -> float:
    """Return positive mass removed from local patches between two snapshots."""

    consumed = 0.0
    for position, amount in before.items():
        leftover = float(after.get(position, 0.0))
        if leftover < amount:
            consumed += float(amount) - leftover
    return round(consumed, 10)


def _effective_inflow(spec: ResourceSpec, regime: EnvironmentRegime | None) -> float:
    if spec.unlimited:
        return 0.0
    if regime is None:
        return spec.inflow
    if spec.name in regime.resource_inflow:
        return regime.resource_inflow[spec.name]
    return round(spec.inflow * regime.inflow_scale, 10)


def _effective_outflow(spec: ResourceSpec, regime: EnvironmentRegime | None) -> float:
    if spec.unlimited or regime is None:
        return spec.outflow
    return min(1.0, round(spec.outflow * regime.outflow_scale, 10))


def _apply_spatial_patches(
    world: World2D,
    *,
    config: EnvironmentConfig,
    regime: EnvironmentRegime | None,
    pools: dict[str, float],
    tick: int,
    occupied: set[tuple[int, int]],
    env_trace: Trace,
) -> tuple[World2D, list[EnvironmentEvent], tuple[WorldEvent, ...]]:
    events: list[EnvironmentEvent] = []
    primary = config.resources[0].name if config.resources else "lumen"
    spec = config.resources[0] if config.resources else ResourceSpec(name=primary)
    scale = 1.0 if regime is None else regime.patch_amount_scale
    targets = _patch_targets(config, regime, spec, scale, pools)
    if config.decay_rate > 0 and world.resources:
        decayed = decay_local_patches(world.resources, rate=config.decay_rate)
        _replace_resources(world, decayed)
        events.append(
            EnvironmentEvent(
                tick=tick,
                event_type="decay",
                resource=primary,
                amount=round(sum(decayed.values()), 10),
                metadata={"rate": config.decay_rate},
            )
        )
    for (x, y), amount in targets.items():
        position = (x, y)
        if not world.in_bounds(position) or position in world.walls:
            continue
        current = world.resource_amount(position)
        target = amount if config.patch_update_mode == "replace" else round(current + amount, 10)
        debit_pool = (
            config.patch_update_mode == "inflow"
            and config.uses_global_pool
            and config.consume_from_global_pool
            and not spec.unlimited
        )
        if debit_pool:
            available = pools.get(spec.name, 0.0)
            needed = max(0.0, target - current)
            take = min(needed, available)
            pools[spec.name] = round(available - take, 10)
            target = round(current + take, 10)
        if abs(target - current) <= 1e-12:
            continue
        if target > 0:
            world.place_resource_event(
                position,
                target,
                trace=env_trace,
                step=tick,
                source="environment",
                reason="environment_patch_restock",
                metadata={"resource": primary, "regime": "" if regime is None else regime.name},
            )
        elif current > 0:
            world.remove_resource_event(
                position,
                trace=env_trace,
                step=tick,
                source="environment",
                reason="environment_patch_cleared",
                metadata={"resource": primary},
            )
        events.append(
            EnvironmentEvent(
                tick=tick,
                event_type="patch_restock",
                resource=primary,
                amount=max(target, 0.0),
                position=position,
            )
        )
    if config.diffusion_rate > 0 and world.resources:
        diffused = diffuse_local_patches(
            world.resources,
            width=world.width,
            height=world.height,
            rate=config.diffusion_rate,
            walls=set(world.walls),
        )
        _replace_resources(world, diffused)
        events.append(
            EnvironmentEvent(
                tick=tick,
                event_type="diffusion",
                resource=primary,
                amount=round(sum(diffused.values()), 10),
                metadata={"rate": config.diffusion_rate, "occupied_ignored": len(occupied)},
            )
        )
    return world, events, env_trace.world_events


def _patch_targets(
    config: EnvironmentConfig,
    regime: EnvironmentRegime | None,
    spec: ResourceSpec,
    scale: float,
    pools: Mapping[str, float],
) -> dict[tuple[int, int], float]:
    if regime is not None and regime.niche_patches:
        return {
            (x, y): round(amount * scale, 10)
            for x, y, amount in regime.niche_patches
            if amount * scale > 0
        }
    cells = config.patch_cells
    if not cells:
        return {}
    if spec.unlimited:
        per_cell = spec.initial / len(cells) if spec.initial > 0 else spec.cell_inflow
    elif config.patch_update_mode == "replace" and spec.name in pools:
        per_cell = pools[spec.name] / len(cells) * scale
    elif spec.cell_inflow > 0:
        per_cell = spec.cell_inflow * scale
    else:
        per_cell = spec.initial / len(cells) * scale if spec.initial > 0 else scale
    return {cell: round(per_cell, 10) for cell in cells if per_cell > 0}


def _replace_resources(world: World2D, amounts: Mapping[tuple[int, int], float]) -> None:
    world.resources.clear()
    for position, amount in amounts.items():
        if amount > 0 and world.in_bounds(position) and position not in world.walls:
            world.resources[position] = amount


def _world_event(
    event_type: str,
    *,
    tick: int,
    sequence: int,
    amount: float = 0.0,
    reason: str = "",
    metadata: dict[str, JsonValue] | None = None,
) -> WorldEvent:
    return WorldEvent(
        schema_version=1,
        step=tick,
        sequence=sequence,
        event_type=event_type,
        position=None,
        source="environment",
        reason=reason,
        amount=amount,
        metadata=dict(metadata or {}),
    )


def _set_finite(
    obj: object,
    field: str,
    value: float,
    *,
    probability: bool = False,
    name: str | None = None,
) -> None:
    object.__setattr__(
        obj,
        field,
        require_finite_float(
            name or field, value, non_negative=True, probability=probability
        ),
    )


def _finite_amount_map(values: Mapping[str, float], name: str) -> dict[str, float]:
    normalized: dict[str, float] = {}
    for key, value in values.items():
        if not key:
            raise ConfigurationError(f"{name} keys must be non-empty.")
        normalized[str(key)] = require_finite_float(f"{name}.{key}", value, non_negative=True)
    return dict(sorted(normalized.items()))


def _float_map(data: Mapping[str, JsonValue], key: str) -> dict[str, float]:
    raw = data.get(key, {})
    if raw is None:
        return {}
    if not isinstance(raw, Mapping):
        raise ConfigurationError(f"{key} must be an object.")
    out: dict[str, float] = {}
    for item_key, value in raw.items():
        if isinstance(value, bool) or not isinstance(value, int | float):
            raise ConfigurationError(f"{key} values must be numeric.")
        out[str(item_key)] = require_finite_float(
            f"{key}.{item_key}", float(value), non_negative=True
        )
    return out


def _bool(data: Mapping[str, JsonValue], key: str, default: bool) -> bool:
    value = data.get(key, default)
    if not isinstance(value, bool):
        raise ConfigurationError(f"{key} must be a boolean.")
    return value


def _float(data: Mapping[str, JsonValue], key: str, default: float) -> float:
    value = data.get(key, default)
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise ConfigurationError(f"{key} must be numeric.")
    return require_finite_float(key, value, non_negative=True)


def _int(data: Mapping[str, JsonValue], key: str, default: int) -> int:
    value = data.get(key, default)
    if isinstance(value, bool) or not isinstance(value, int):
        raise ConfigurationError(f"{key} must be an integer.")
    return int(value)


def _str(data: Mapping[str, JsonValue], key: str, default: str | None = None) -> str:
    value = data.get(key, default)
    if not isinstance(value, str):
        raise ConfigurationError(f"{key} must be a string.")
    return value


def _optional_str(data: Mapping[str, JsonValue], key: str) -> str | None:
    value = data.get(key)
    if value is None:
        return None
    if not isinstance(value, str):
        raise ConfigurationError(f"{key} must be a string or null.")
    return value
