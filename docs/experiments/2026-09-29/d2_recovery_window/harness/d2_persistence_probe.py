"""D-2 evidence for patch 2: does a persistence-safe soft ecology keep the control arm alive?

Compares the standing idea-4 engine spec against the patched spec (patch 2) for one
development seed at the early checkpoint, horizon 40, and reports whether the
control arm keeps a positive census long enough to have a recovery opportunity.

No repository edit: the patched spec is built with dataclasses.replace.
"""

from __future__ import annotations

import json
import sys
from dataclasses import replace
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "codontrace-genesis" / "src"))

from codontrace.engine_runtime import GenesisEngine  # noqa: E402
from codontrace.genesis.campaigns.discovery_q_20260928_idea4 import harvest_rare_class_yield  # noqa: E402
from codontrace.genesis.campaigns.discovery_q_20260928_idea4_engine import (  # noqa: E402
    SOFT_FOOD_CELLS,
    build_idea4_engine_spec,
)
from codontrace.genesis.population import MetabolicConfig, RuntimeResourcePolicy  # noqa: E402
from codontrace.genesis.substrate import world2d_to_element_grid  # noqa: E402
from codontrace.life_loop.contact_atp_ledger import build_engine_scaffold_ledger  # noqa: E402
from codontrace.life_loop.engine_ledger_coupler import (  # noqa: E402
    EngineCoupledLedgerObserver,
    population_path_fingerprint,
)
from codontrace.world import World2D  # noqa: E402

SEED = 5501
T_INT = 10
HORIZON = 40
# Patch 2: a persistence-safe soft ecology that creates a recovery opportunity.
PERSIST_FOOD_CELLS = SOFT_FOOD_CELLS + ((2, 2), (3, 0), (0, 1), (1, 1), (4, 1), (5, 2), (0, 2), (2, 1))


def patched_spec(*, seed: int, tick_count: int, population: int = 8) -> Any:
    """Standing idea-4 spec with the patch-2 ecology values."""

    from codontrace.genesis.runtime_profiles import GenesisRuntimeProfile

    base = GenesisRuntimeProfile.life_loop_world(seed=seed, tick_count=tick_count, population=population)
    world = World2D(base.world_width, base.world_height)
    for pos in PERSIST_FOOD_CELLS:
        if 0 <= pos[0] < world.width and 0 <= pos[1] < world.height:
            world.place_resource(pos, 12.0)
    cfg = base.population_configs
    rrp = RuntimeResourcePolicy(respawn_enabled=True, respawn_rate=1.0, max_resources=24, amount=12.0)
    metab = cfg.metabolism if cfg.metabolism is not None else MetabolicConfig()
    return replace(
        base,
        element_grid=world2d_to_element_grid(world),
        initial_runtime_atp=24.0,
        population_configs=replace(
            cfg,
            runtime_resource_policy=rrp,
            metabolism=replace(metab, basal_runtime_atp_cost=0.15),
            mutation=replace(cfg.mutation, bit_flip_rate=0.06),
            reproduction=replace(cfg.reproduction, min_runtime_atp=3.0, parent_atp_cost=0.5),
        ),
        metadata={**dict(base.metadata), "d2_patch2_persistence_safe_ecology": True},
    )


def run(*, seed: int, spec_builder: Any, label: str) -> dict[str, Any]:
    holder: dict[str, Any] = {"engine": None}
    rows: list[dict[str, Any]] = []
    ledger = build_engine_scaffold_ledger(seed=seed)
    observer = EngineCoupledLedgerObserver(
        engine_holder=holder,
        ledger=ledger,
        schedule={},
        harvest_fn=harvest_rare_class_yield,
        auto_advance=True,
        feedback_enabled=True,
        feedback_allocation="incident_endpoints_realised",
    )

    class _Rec:
        def __call__(self, *, generation_index: int) -> None:
            engine = holder["engine"]
            pop = engine.runner.population
            rows.append(
                {
                    "generation": int(generation_index),
                    "n_alive": len(list(pop.organisms)),
                    "path": population_path_fingerprint(engine),
                }
            )

    spec = spec_builder(seed=seed, tick_count=T_INT + HORIZON, population=8)
    engine = GenesisEngine.from_spec(spec, generation_boundary_observers=(observer, _Rec()))
    holder["engine"] = engine
    engine.run_ticks()
    alive_after_ckpt = [r["n_alive"] for r in rows if r["generation"] >= T_INT]
    return {
        "label": label,
        "n_generations": len(rows),
        "final_n_alive": rows[-1]["n_alive"],
        "min_n_alive_after_checkpoint": min(alive_after_ckpt) if alive_after_ckpt else 0,
        "n_zero_generations_after_checkpoint": sum(1 for v in alive_after_ckpt if v == 0),
        "positive_census_through_horizon": bool(alive_after_ckpt and min(alive_after_ckpt) > 0),
        "alive_series_after_checkpoint": alive_after_ckpt,
    }


def main() -> int:
    out = {
        "probe": "d2_patch2_persistence_opportunity",
        "seed": SEED,
        "t_intervene": T_INT,
        "horizon": HORIZON,
        "standing_ecology": run(seed=SEED, spec_builder=build_idea4_engine_spec, label="standing"),
        "patched_ecology": run(seed=SEED, spec_builder=patched_spec, label="patch2_persistence_safe"),
    }
    path = Path(__file__).resolve().parents[1] / "patch2_evidence.json"
    path.write_text(json.dumps(out, indent=2, sort_keys=True, default=str), encoding="utf-8")
    print(json.dumps({k: (v if not isinstance(v, dict) else {kk: vv for kk, vv in v.items() if kk != "alive_series_after_checkpoint"}) for k, v in out.items()}, indent=1, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
