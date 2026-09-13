"""E6 Morris elementary-effects screen for the HE01 overlay.

Exploratory only. Qualitatively ranks four post-Amendment-03-safe knobs
on held-out seeds. Does not raise ClaimGate, does not rewrite Amd 01/02/03,
and must never consume analysis seeds 11-40 or pilot seeds 1000-1009.

Default executable scale is smoke (8 ticks x 8 pop) for CI cost.
Research-scale cost is documented in docs/hard_experiment_01/morris_e6_design.md.
"""

from __future__ import annotations

import hashlib
import json
import math
import statistics
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, replace
from typing import Literal

from codontrace._types import JsonValue
from codontrace.errors import ConfigurationError
from codontrace.genesis.canonical import canonical_digest
from codontrace.genesis.claim_gate import ClaimDecision, ClaimRequest, ScientificClaimGate
from codontrace.genesis.engine import GenesisEngine, GenesisExperimentSpec
from codontrace.genesis.hard_experiment_01 import (
    CALIBRATION_BASAL_COST,
    CALIBRATION_RESOURCE_AMOUNT,
    CLAIM_CEILING,
    DEFAULT_POPULATION,
    DEFAULT_TICK_COUNT,
    MIN_SOURCE_FITNESS_TREATMENT,
    PRIMARY_OUTCOME,
    RESEARCH_POPULATION,
    RESEARCH_TICK_COUNT,
    SMOKE_POPULATION,
    SMOKE_TICK_COUNT,
    _genome_roles,
    _receiver_mean_terminal_atp,
    build_hard_experiment_01_spec,
)
from codontrace.genesis.population import MetabolicConfig
from codontrace.genesis.substrate import world2d_to_element_grid
from codontrace.rng import RNGManager
from codontrace.world import World2D

ScaleName = Literal["smoke", "research"]
OutcomeFn = Callable[[Mapping[str, float], int], float]

MORRIS_TIER = "exploratory_only"
MORRIS_NAMESPACE = "hard_experiment_01/morris"
MORRIS_ARM = "source_bias_on"
DEFAULT_DESIGN_SEED = 20260912
DEFAULT_TRAJECTORIES = 10
GRID_LEVELS = 4
# Morris 1991 / Saltelli Primer: Delta = p / [2(p-1)] on the unit cube.
MORRIS_DELTA = GRID_LEVELS / (2 * (GRID_LEVELS - 1))
LEVEL_STEP = 2
UNIT_GRID: tuple[float, ...] = (0.0, 1.0 / 3.0, 2.0 / 3.0, 1.0)

# Held-out exploratory world seeds. Never 11-40 or 1000-1009.
EXPLORATORY_SEEDS: tuple[int, ...] = tuple(range(2000, 2010))
# Smoke default uses one held-out seed so CI / local smoke stays cheap.
DEFAULT_SMOKE_SEEDS: tuple[int, ...] = (2000,)

ANALYSIS_SEEDS = frozenset(range(11, 41))
PILOT_SEEDS = frozenset(range(1000, 1010))

# Primary k=4. Coverage and respawn_draws stay Amd 03 frozen.
FACTOR_LEVELS: dict[str, tuple[float, ...]] = {
    "read_radius": (1.0, 3.0, 6.0, 10.0),
    "min_source_fitness": (0.0, 1.0, 1.5, 3.0),
    "basal_runtime_atp_cost": (0.2, 0.4, 0.6, 0.8),
    "resource_amount": (1.0, 2.0, 3.0, 4.0),
}
FACTOR_NAMES: tuple[str, ...] = tuple(FACTOR_LEVELS)
FROZEN_OVERLAY: dict[str, JsonValue] = {
    "food_coverage": 1.0,
    "food_layout": "every_cell",
    "respawn_draws_per_tick": "max(1, population_size)",
    "role_layout": "seed_permuted_v3_multiset",
}

_FORBIDDEN_CLAIMS = frozenset(
    {
        "collective_intelligence",
        "proved_collective_intelligence",
        "intelligence",
        "agi",
        "tokyo_type1_passed",
        "avida_replacement",
        "intervention_supported",
    }
)


@dataclass(frozen=True, slots=True)
class MorrisFactorPoint:
    """One design point: unit-cube coordinates plus physical knobs."""

    trajectory: int
    step: int
    unit: tuple[float, ...]
    knobs: dict[str, float]

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "trajectory": self.trajectory,
            "step": self.step,
            "unit": list(self.unit),
            "knobs": {name: self.knobs[name] for name in FACTOR_NAMES},
        }


@dataclass(frozen=True, slots=True)
class MorrisTrajectory:
    """One OAT trajectory of length k+1."""

    index: int
    points: tuple[MorrisFactorPoint, ...]
    stepped_factors: tuple[str, ...]

    def __post_init__(self) -> None:
        if len(self.points) != len(FACTOR_NAMES) + 1:
            raise ConfigurationError("Morris trajectory must have k+1 points.")
        if len(self.stepped_factors) != len(FACTOR_NAMES):
            raise ConfigurationError("Morris trajectory must step each factor once.")

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "index": self.index,
            "points": [point.to_dict() for point in self.points],
            "stepped_factors": list(self.stepped_factors),
        }


@dataclass(frozen=True, slots=True)
class MorrisScreeningRow:
    factor: str
    mu_star: float
    mu: float
    sigma: float | None
    n_effects: int

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "factor": self.factor,
            "mu_star": self.mu_star,
            "mu": self.mu,
            "sigma": self.sigma,
            "n_effects": self.n_effects,
        }


@dataclass(frozen=True, slots=True)
class MorrisE6Result:
    """Exploratory Morris screen. Ceiling stays runtime_observation."""

    trajectories: tuple[MorrisTrajectory, ...]
    screening: tuple[MorrisScreeningRow, ...]
    outcomes: tuple[float | None, ...]
    seeds: tuple[int, ...]
    design_seed: int
    r: int
    k: int
    scale: ScaleName
    tick_count: int
    population: int
    claim_ceiling: str = CLAIM_CEILING
    tier: str = MORRIS_TIER

    @property
    def n_evaluations(self) -> int:
        return self.r * (self.k + 1)

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "schema": "hard_experiment_01_morris_e6",
            "tier": self.tier,
            "claim_ceiling": self.claim_ceiling,
            "claim_gate_unchanged": True,
            "collective_intelligence": False,
            "intelligence": False,
            "agi": False,
            "tokyo_type1_passed": False,
            "avida_replacement": False,
            "k": self.k,
            "r": self.r,
            "n_evaluations": self.n_evaluations,
            "p": GRID_LEVELS,
            "delta": MORRIS_DELTA,
            "scale": self.scale,
            "tick_count": self.tick_count,
            "population": self.population,
            "seeds": list(self.seeds),
            "design_seed": self.design_seed,
            "outcome": PRIMARY_OUTCOME,
            "arm": MORRIS_ARM,
            "rng_namespace": MORRIS_NAMESPACE,
            "factors": {name: list(levels) for name, levels in FACTOR_LEVELS.items()},
            "frozen": dict(FROZEN_OVERLAY),
            "screening": [row.to_dict() for row in self.screening],
            "outcomes": list(self.outcomes),
            "trajectories": [item.to_dict() for item in self.trajectories],
            "note": (
                "exploratory_only Morris mu* screen; not Holm/BCa; not a "
                "ClaimGate input; Amd 03 coverage/respawn frozen"
            ),
        }

    def digest(self) -> str:
        return canonical_digest(self.to_dict())


def refuse_confirmatory_seeds(seeds: Sequence[int]) -> None:
    """Refuse HE01 analysis (11-40) and pilot (1000-1009) seeds."""

    bad = sorted(
        {int(seed) for seed in seeds if int(seed) in ANALYSIS_SEEDS or int(seed) in PILOT_SEEDS}
    )
    if bad:
        raise ConfigurationError(
            f"E6 Morris must not use analysis seeds 11-40 or pilot seeds 1000-1009; got {bad}."
        )


def evaluate_morris_e6_claim(
    payload: Mapping[str, JsonValue] | MorrisE6Result | None = None,
) -> ClaimDecision:
    """Always return runtime_observation. Refuse any ceiling raise."""

    data: Mapping[str, JsonValue]
    if isinstance(payload, MorrisE6Result):
        data = payload.to_dict()
    elif isinstance(payload, Mapping):
        data = payload
    else:
        data = {}
    requested = str(data.get("claim_ceiling") or CLAIM_CEILING)
    if requested in _FORBIDDEN_CLAIMS and requested != "intelligence":
        raise ConfigurationError(f"E6 Morris must not request {requested}.")
    if requested != CLAIM_CEILING:
        raise ConfigurationError(
            f"E6 Morris claim ceiling must stay {CLAIM_CEILING}; got {requested}."
        )
    for label in _FORBIDDEN_CLAIMS:
        if data.get(label) is True:
            raise ConfigurationError(f"E6 Morris must not set {label} True.")
    gate = ScientificClaimGate()
    decision = gate.decide(ClaimRequest(CLAIM_CEILING, {}))
    for label in (
        "collective_intelligence",
        "intelligence",
        "agi",
        "tokyo_type1_passed",
        "avida_replacement",
    ):
        blocked = gate.decide(ClaimRequest(label, {}))
        if blocked.allowed:
            raise ConfigurationError(f"{label} must remain blocked.")
    return decision


def _knobs_from_indices(indices: Sequence[int]) -> dict[str, float]:
    if len(indices) != len(FACTOR_NAMES):
        raise ConfigurationError("Morris index vector length must equal k.")
    knobs: dict[str, float] = {}
    for name, index in zip(FACTOR_NAMES, indices, strict=True):
        levels = FACTOR_LEVELS[name]
        if index < 0 or index >= len(levels):
            raise ConfigurationError(f"Morris level index out of range for {name}.")
        knobs[name] = float(levels[index])
    return knobs


def _unit_from_indices(indices: Sequence[int]) -> tuple[float, ...]:
    return tuple(UNIT_GRID[index] for index in indices)


def build_morris_trajectories(
    *,
    r: int = DEFAULT_TRAJECTORIES,
    design_seed: int = DEFAULT_DESIGN_SEED,
) -> tuple[MorrisTrajectory, ...]:
    """Build r trajectories of length k+1 (N = r(k+1) points)."""

    count = int(r)
    if count < 1:
        raise ConfigurationError("Morris r must be >= 1.")
    rng = RNGManager(seed=int(design_seed), namespace=MORRIS_NAMESPACE)
    k = len(FACTOR_NAMES)
    trajectories: list[MorrisTrajectory] = []
    for traj_index in range(count):
        starts: list[int] = []
        directions: list[int] = []
        for _ in range(k):
            base = rng.randrange(2)
            sign = 1 if rng.randrange(2) == 0 else -1
            starts.append(base if sign > 0 else base + LEVEL_STEP)
            directions.append(sign)
        order = list(range(k))
        for idx in range(k - 1, 0, -1):
            swap = rng.randrange(idx + 1)
            order[idx], order[swap] = order[swap], order[idx]
        current = list(starts)
        points = [
            MorrisFactorPoint(
                trajectory=traj_index,
                step=0,
                unit=_unit_from_indices(current),
                knobs=_knobs_from_indices(current),
            )
        ]
        stepped: list[str] = []
        for step_no, factor_i in enumerate(order, start=1):
            current = list(current)
            current[factor_i] = current[factor_i] + directions[factor_i] * LEVEL_STEP
            if current[factor_i] < 0 or current[factor_i] >= GRID_LEVELS:
                raise ConfigurationError("Morris trajectory left the p-level grid.")
            points.append(
                MorrisFactorPoint(
                    trajectory=traj_index,
                    step=step_no,
                    unit=_unit_from_indices(current),
                    knobs=_knobs_from_indices(current),
                )
            )
            stepped.append(FACTOR_NAMES[factor_i])
        trajectories.append(
            MorrisTrajectory(
                index=traj_index,
                points=tuple(points),
                stepped_factors=tuple(stepped),
            )
        )
    return tuple(trajectories)


def flatten_morris_points(
    trajectories: Sequence[MorrisTrajectory],
) -> tuple[MorrisFactorPoint, ...]:
    points = tuple(point for item in trajectories for point in item.points)
    expected = len(trajectories) * (len(FACTOR_NAMES) + 1)
    if len(points) != expected:
        raise ConfigurationError(f"Morris design must have N=r(k+1)={expected} points.")
    return points


def _mean(values: Sequence[float]) -> float:
    if not values:
        raise ConfigurationError("Morris mean of an empty series is undefined.")
    return float(math.fsum(values) / len(values))


def compute_morris_screening(
    trajectories: Sequence[MorrisTrajectory],
    outcomes: Sequence[float | None],
) -> tuple[MorrisScreeningRow, ...]:
    """Compute mu*, mu, sigma from elementary effects (Campolongo 2007)."""

    points = flatten_morris_points(trajectories)
    if len(outcomes) != len(points):
        raise ConfigurationError("Morris outcomes length must equal N=r(k+1).")
    effects: dict[str, list[float]] = {name: [] for name in FACTOR_NAMES}
    offset = 0
    for trajectory in trajectories:
        local = list(outcomes[offset : offset + len(trajectory.points)])
        offset += len(trajectory.points)
        for step_i, factor in enumerate(trajectory.stepped_factors):
            before = local[step_i]
            after = local[step_i + 1]
            if before is None or after is None:
                continue
            effects[factor].append((float(after) - float(before)) / MORRIS_DELTA)
    rows: list[MorrisScreeningRow] = []
    for name in FACTOR_NAMES:
        series = effects[name]
        if not series:
            rows.append(
                MorrisScreeningRow(factor=name, mu_star=0.0, mu=0.0, sigma=None, n_effects=0)
            )
            continue
        mu = _mean(series)
        mu_star = _mean([abs(item) for item in series])
        sigma = statistics.stdev(series) if len(series) >= 2 else None
        rows.append(
            MorrisScreeningRow(
                factor=name,
                mu_star=mu_star,
                mu=mu,
                sigma=sigma,
                n_effects=len(series),
            )
        )
    return tuple(rows)


def _place_every_cell_food(width: int, height: int, amount: float) -> World2D:
    world = World2D(width, height)
    for y in range(height):
        for x in range(width):
            world.place_resource((x, y), float(amount))
    return world


def build_morris_treatment_spec(
    *,
    seed: int,
    knobs: Mapping[str, float],
    tick_count: int = DEFAULT_TICK_COUNT,
    population: int = DEFAULT_POPULATION,
) -> GenesisExperimentSpec:
    """Treatment-arm overlay with E6 knobs. Coverage/respawn stay Amd 03 frozen."""

    refuse_confirmatory_seeds((seed,))
    missing = [name for name in FACTOR_NAMES if name not in knobs]
    if missing:
        raise ConfigurationError(f"Morris knobs missing {missing}.")
    spec = build_hard_experiment_01_spec(
        seed=int(seed),
        arm="source_bias_on",
        tick_count=int(tick_count),
        population=int(population),
    )
    capsule = spec.capsule_transfer_config
    if capsule is None:
        raise ConfigurationError("Morris treatment spec is missing capsule_transfer_config.")
    configs = spec.population_configs
    if configs is None:
        raise ConfigurationError("Morris treatment spec is missing population_configs.")
    read_radius = int(round(float(knobs["read_radius"])))
    min_source = float(knobs["min_source_fitness"])
    basal = float(knobs["basal_runtime_atp_cost"])
    amount = float(knobs["resource_amount"])
    if read_radius < 0 or basal < 0 or amount <= 0 or min_source < 0:
        raise ConfigurationError("Morris knobs must be non-negative; resource_amount > 0.")
    capsule = replace(capsule, read_radius=read_radius, min_source_fitness=min_source)
    population_size = len(spec.genome_bits)
    resource_policy = replace(
        configs.runtime_resource_policy,
        amount=amount,
        respawn_draws_per_tick=max(1, population_size),
    )
    configs = replace(
        configs,
        capsule_transfer=capsule,
        metabolism=MetabolicConfig(enabled=True, basal_runtime_atp_cost=basal),
        runtime_resource_policy=resource_policy,
    )
    width = int(spec.world_width)
    height = int(spec.world_height)
    world = _place_every_cell_food(width, height, amount)
    food_cells = [(x, y) for y in range(height) for x in range(width)]
    metadata: dict[str, JsonValue] = {
        **spec.metadata,
        "morris_e6": True,
        "morris_e6_tier": MORRIS_TIER,
        "morris_e6_knobs": {name: float(knobs[name]) for name in FACTOR_NAMES},
        "resource_amount": amount,
        "basal_runtime_atp_cost": basal,
        "food_coverage": 1.0,
        "food_layout": "every_cell",
        "food_cells": [list(cell) for cell in food_cells],
        "claim_ceiling": CLAIM_CEILING,
    }
    return replace(
        spec,
        capsule_transfer_config=capsule,
        population_configs=configs,
        element_grid=world2d_to_element_grid(world),
        metadata=metadata,
    )


def evaluate_morris_treatment_outcome(
    *,
    seed: int,
    knobs: Mapping[str, float],
    tick_count: int,
    population: int,
) -> float:
    """Run source_bias_on at one design point; return primary outcome."""

    spec = build_morris_treatment_spec(
        seed=seed, knobs=knobs, tick_count=tick_count, population=population
    )
    result = GenesisEngine.from_spec(spec).run_ticks()
    outcome = _receiver_mean_terminal_atp(result, _genome_roles(spec))
    if outcome is None:
        raise ConfigurationError(
            "E6 Morris outcome missing (no surviving receivers) at "
            f"seed={seed} knobs={dict(knobs)}."
        )
    return float(outcome)


def _resolve_scale(scale: ScaleName) -> tuple[int, int]:
    if scale == "smoke":
        return SMOKE_TICK_COUNT, SMOKE_POPULATION
    if scale == "research":
        return RESEARCH_TICK_COUNT, RESEARCH_POPULATION
    raise ConfigurationError(f"unknown Morris scale: {scale!r}")


def run_morris_e6(
    *,
    r: int = DEFAULT_TRAJECTORIES,
    design_seed: int = DEFAULT_DESIGN_SEED,
    seeds: Sequence[int] | None = None,
    scale: ScaleName = "smoke",
    tick_count: int | None = None,
    population: int | None = None,
    outcome_fn: OutcomeFn | None = None,
    evaluate: bool = True,
) -> MorrisE6Result:
    """Build (and optionally evaluate) the E6 Morris screen.

    Default scale is smoke (8 x 8). ``outcome_fn(knobs, seed)`` may replace
    the engine for deterministic unit tests. ``evaluate=False`` returns the
    design with empty outcomes.
    """

    default_seeds = DEFAULT_SMOKE_SEEDS if seeds is None else seeds
    resolved_seeds = tuple(int(item) for item in default_seeds)
    if not resolved_seeds:
        raise ConfigurationError("E6 Morris requires at least one held-out seed.")
    refuse_confirmatory_seeds(resolved_seeds)
    resolved_ticks, resolved_pop = _resolve_scale(scale)
    if tick_count is not None:
        resolved_ticks = int(tick_count)
    if population is not None:
        resolved_pop = int(population)
    trajectories = build_morris_trajectories(r=r, design_seed=design_seed)
    points = flatten_morris_points(trajectories)
    outcomes: list[float | None] = [None] * len(points)
    if evaluate:
        for index, point in enumerate(points):
            per_seed: list[float] = []
            for seed in resolved_seeds:
                if outcome_fn is not None:
                    per_seed.append(float(outcome_fn(point.knobs, seed)))
                else:
                    per_seed.append(
                        evaluate_morris_treatment_outcome(
                            seed=seed,
                            knobs=point.knobs,
                            tick_count=resolved_ticks,
                            population=resolved_pop,
                        )
                    )
            outcomes[index] = _mean(per_seed)
    screening = compute_morris_screening(trajectories, outcomes) if evaluate else ()
    result = MorrisE6Result(
        trajectories=trajectories,
        screening=screening,
        outcomes=tuple(outcomes),
        seeds=resolved_seeds,
        design_seed=int(design_seed),
        r=int(r),
        k=len(FACTOR_NAMES),
        scale=scale,
        tick_count=resolved_ticks,
        population=resolved_pop,
    )
    evaluate_morris_e6_claim(result)
    return result


def morris_e6_smoke_payload(result: MorrisE6Result) -> dict[str, JsonValue]:
    """Compact JSON object for docs/hard_experiment_01/morris_e6_smoke.json."""

    payload = result.to_dict()
    # Smoke artifact keeps ranks + design identity; drop bulky trajectory bodies
    # when they are reconstructible from design_seed.
    payload["trajectories"] = [
        {
            "index": item.index,
            "stepped_factors": list(item.stepped_factors),
            "n_points": len(item.points),
        }
        for item in result.trajectories
    ]
    payload["bytes_sha256"] = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return payload


def calibration_anchor_knobs() -> dict[str, float]:
    """Amd 03 / HE01 treatment defaults inside the E6 level sets."""

    return {
        "read_radius": 6.0,
        "min_source_fitness": float(MIN_SOURCE_FITNESS_TREATMENT),
        "basal_runtime_atp_cost": float(CALIBRATION_BASAL_COST),
        "resource_amount": float(CALIBRATION_RESOURCE_AMOUNT),
    }


__all__ = [
    "DEFAULT_DESIGN_SEED",
    "DEFAULT_SMOKE_SEEDS",
    "EXPLORATORY_SEEDS",
    "FACTOR_LEVELS",
    "FACTOR_NAMES",
    "FROZEN_OVERLAY",
    "MORRIS_DELTA",
    "MORRIS_TIER",
    "MorrisE6Result",
    "MorrisFactorPoint",
    "MorrisScreeningRow",
    "MorrisTrajectory",
    "build_morris_trajectories",
    "build_morris_treatment_spec",
    "calibration_anchor_knobs",
    "compute_morris_screening",
    "evaluate_morris_e6_claim",
    "evaluate_morris_treatment_outcome",
    "flatten_morris_points",
    "morris_e6_smoke_payload",
    "refuse_confirmatory_seeds",
    "run_morris_e6",
]
