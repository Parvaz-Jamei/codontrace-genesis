"""Engine-coupled GenerationBoundaryObserver for discovery phase-2 ledgers.

Attaches to GenesisEngine.run_ticks so each completed generation samples live
population / world ecology and updates a ContactAtpLedger outside engine.py.
No infection physics; no second population engine.
"""

from __future__ import annotations

import math
from collections.abc import Callable, Mapping, MutableMapping, Sequence
from dataclasses import dataclass, field
from typing import Any

from codontrace.errors import ConfigurationError
from codontrace.life_loop.contact_atp_ledger import CONTACT_TAG_RARE, ContactAtpLedger

BoundaryOp = Callable[[ContactAtpLedger, int], Any]


def sample_ecology(engine: Any) -> dict[str, float]:
    """Sample domain-free ecology meters from a live GenesisEngine."""

    population = engine.runner.population
    organisms = tuple(population.organisms)
    atps = [float(o.atp_state.runtime_available) for o in organisms]
    n_alive = float(len(organisms))
    mean_atp = float(sum(atps) / n_alive) if n_alive > 0.0 else 0.0
    sum_atp = float(sum(atps))
    resources = dict(getattr(engine.runner.world, "resources", {}) or {})
    n_resources = float(len(resources))
    resource_mass = float(sum(float(v) for v in resources.values()))
    loc_fp = 0.0
    for (x, y), amt in resources.items():
        loc_fp += float(x + 1) * float(y + 1) * float(amt)
    return {
        "n_alive": n_alive,
        "mean_atp": mean_atp,
        "sum_atp": sum_atp,
        "n_resources": n_resources,
        "resource_mass": resource_mass,
        "resource_loc_fp": loc_fp,
        "generation": float(getattr(population, "generation", 0)),
    }


def ecology_scale(eco: Mapping[str, float]) -> float:
    """Map ecology meters to a positive rare-yield scale factor."""

    mean_atp = float(eco.get("mean_atp", 0.0))
    n_alive = float(eco.get("n_alive", 0.0))
    resource_mass = float(eco.get("resource_mass", 0.0))
    loc_fp = float(eco.get("resource_loc_fp", 0.0))
    alive_term = 0.35 + 0.65 * math.tanh(n_alive / 4.0)
    atp_term = 0.40 + 0.60 * math.tanh(mean_atp / 8.0)
    food_term = 0.55 + 0.45 * math.tanh(resource_mass / 24.0)
    # Location fingerprint breaks ties when mass is saturated but layout differs.
    loc_term = 0.90 + 0.10 * math.sin(loc_fp / 17.0)
    return float(max(0.05, alive_term * atp_term * food_term * loc_term))


@dataclass(slots=True)
class EngineCoupledLedgerObserver:
    """GenerationBoundaryObserver: couple engine ecology into ledger yields + ops."""

    engine_holder: MutableMapping[str, Any]
    ledger: ContactAtpLedger
    schedule: Mapping[int, Sequence[BoundaryOp]] = field(default_factory=dict)
    base_rare_yields: dict[str, float] = field(default_factory=dict)
    yield_history: list[float] = field(default_factory=list)
    ecology_history: list[dict[str, float]] = field(default_factory=list)
    observer_fire_count: int = 0
    auto_advance: bool = True
    harvest_fn: Callable[[ContactAtpLedger], float] | None = None

    def __post_init__(self) -> None:
        if not self.base_rare_yields:
            for eid in self.ledger.edges_with_tag(CONTACT_TAG_RARE):
                self.base_rare_yields[eid] = float(self.ledger.edges[eid].atp_yield)

    def __call__(self, *, generation_index: int) -> None:
        if not isinstance(generation_index, int) or isinstance(generation_index, bool):
            raise ConfigurationError("generation_index must be an integer.")
        engine = self.engine_holder.get("engine")
        if engine is None:
            raise ConfigurationError(
                "EngineCoupledLedgerObserver requires engine_holder['engine'] "
                "before run_ticks()."
            )
        g = int(generation_index)
        eco = sample_ecology(engine)
        self.ecology_history.append(dict(eco))
        scale = ecology_scale(eco)
        # Update rare-class edge yields from live ecology (closed-loop variance).
        for eid, base in self.base_rare_yields.items():
            edge = self.ledger.edges.get(eid)
            if edge is None:
                continue
            edge.atp_yield = float(base) * float(scale)
        # Refresh tag aggregate.
        rare_sum = 0.0
        for eid in self.ledger.edges_with_tag(CONTACT_TAG_RARE):
            e = self.ledger.edges[eid]
            if e.present and not e.masked:
                rare_sum += float(e.atp_yield)
        self.ledger.atp_yield_by_tag[CONTACT_TAG_RARE] = float(rare_sum)

        ops = self.schedule.get(g, ())
        for op in ops:
            op(self.ledger, g)

        if self.harvest_fn is not None:
            harvested = float(self.harvest_fn(self.ledger))
        else:
            harvested = float(rare_sum)
        self.yield_history.append(harvested)
        self.observer_fire_count += 1

        if self.auto_advance:
            if self.ledger.generation_index < g:
                self.ledger.generation_index = g
            self.ledger.advance_generation()
