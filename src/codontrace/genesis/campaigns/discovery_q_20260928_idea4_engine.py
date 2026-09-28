"""Discovery questions 2026-09-28 — Idea 4 ENGINE closed-loop cells.

Runs GenesisEngine life-loop with GenerationBoundaryObserver coupling a
ContactAtpLedger. Distinct from harness scored cells (jsonl_campaign): FI
recover uses real rare-class ATP from ecology-coupled yields — NO
recovery_progress multiplier. Claim ceiling remains phase2_design.
hypothesis_supported=False; red_queen_proved=False.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import replace
from typing import Any

from codontrace._types import JsonValue
from codontrace.errors import ConfigurationError
from codontrace.genesis.campaigns.discovery_q_20260928_idea4 import (
    CHECKPOINT_ID,
    CLAIM_CEILING,
    COMPETENCE_ID,
    DELTA_P_THRESHOLD,
    HORIZON_T,
    OPS_CELLS,
    RECOVERY_TOKEN_KEY,
    SCAFFOLD_ID,
    SLOPE_THRESHOLD,
    T_INTERVENE_GRID,
    T_TILDE_GRID_MIN,
    _apply_ops_cell,
    _score_recover,
    harvest_rare_class_yield,
    t_tilde_of,
)
from codontrace.genesis.engine import GenesisEngine
from codontrace.genesis.population import MetabolicConfig, RuntimeResourcePolicy
from codontrace.genesis.runtime_profiles import GenesisRuntimeProfile
from codontrace.genesis.substrate import world2d_to_element_grid
from codontrace.life_loop.contact_atp_ledger import build_engine_scaffold_ledger
from codontrace.life_loop.engine_ledger_coupler import EngineCoupledLedgerObserver
from codontrace.world import World2D

SCHEMA = "discovery_q_20260928_idea4_engine_cell_v1"
ENGINE_PATH = "genesis_life_loop_observer_coupled"
SOFT_FOOD_CELLS: tuple[tuple[int, int], ...] = (
    (0, 0),
    (1, 0),
    (2, 0),
    (3, 1),
    (4, 2),
    (5, 1),
    (1, 2),
    (0, 3),
)


def build_idea4_engine_spec(
    *,
    seed: int,
    tick_count: int,
    population: int = 8,
) -> Any:
    """Softened life_loop spec so ecology can persist across T≈40 post-checkpoint."""

    if int(tick_count) < 1:
        raise ConfigurationError("tick_count must be >= 1.")
    base = GenesisRuntimeProfile.life_loop_world(
        seed=int(seed),
        tick_count=int(tick_count),
        population=int(population),
    )
    world = World2D(base.world_width, base.world_height)
    for pos in SOFT_FOOD_CELLS:
        if 0 <= pos[0] < world.width and 0 <= pos[1] < world.height:
            world.place_resource(pos, 8.0)
    cfg = base.population_configs
    if cfg is None:
        raise ConfigurationError("life_loop_world must supply population_configs.")
    new_rrp = RuntimeResourcePolicy(
        respawn_enabled=True, respawn_rate=1.0, max_resources=12, amount=8.0
    )
    metab = cfg.metabolism if cfg.metabolism is not None else MetabolicConfig()
    new_metab = replace(metab, basal_runtime_atp_cost=0.4)
    return replace(
        base,
        element_grid=world2d_to_element_grid(world),
        initial_runtime_atp=20.0,
        population_configs=replace(
            cfg,
            runtime_resource_policy=new_rrp,
            metabolism=new_metab,
            mutation=replace(cfg.mutation, bit_flip_rate=0.06),
            reproduction=replace(
                cfg.reproduction, min_runtime_atp=4.0, parent_atp_cost=0.5
            ),
        ),
        metadata={
            **dict(base.metadata),
            "discovery_engine_soft_ecology": True,
            "claim_ceiling": CLAIM_CEILING,
            "engine_path": ENGINE_PATH,
            "hypothesis_supported": False,
            "red_queen_proved": False,
        },
    )


def run_idea4_engine_cell(
    *,
    seed: int,
    ops_cell: str,
    t_intervene: int,
    t_horizon: int = HORIZON_T,
    population: int = 8,
) -> dict[str, JsonValue]:
    """One N=run Idea4 cell on real GenesisEngine + GenerationBoundaryObserver.

    Checkpoint CKPT-RELOCATE-RECOVERY-TOKEN-V1 fires at generation_index ==
    t_intervene, then the factorial ops_cell. FI recover is scored from
    ecology-coupled rare-class ATP only (no recovery_progress multiplier).
    """

    if ops_cell not in OPS_CELLS:
        raise ConfigurationError(f"unknown Idea4 ops_cell {ops_cell!r}.")
    if int(t_intervene) < 1:
        raise ConfigurationError("t_intervene must be >= 1.")
    if int(t_horizon) < T_TILDE_GRID_MIN:
        raise ConfigurationError(f"t_horizon must be >= {T_TILDE_GRID_MIN}.")
    if int(t_horizon) <= 4:
        raise ConfigurationError(
            "engine Idea4 refuses smoke horizons (T<=4); use mid-history on T≈40."
        )

    t_int = int(t_intervene)
    t_hor = int(t_horizon)
    tick_count = t_int + t_hor
    ledger = build_engine_scaffold_ledger(seed=int(seed))
    holder: dict[str, Any] = {"engine": None}

    def _ckpt_and_cell(led: Any, generation_index: int) -> dict[str, Any]:
        del generation_index
        ckpt = led.relocate_recovery_token(
            RECOVERY_TOKEN_KEY, remove=False, new_payload="relocated_engine"
        )
        cell = _apply_ops_cell(led, ops_cell)
        return {"ckpt": ckpt, "cell": cell}

    schedule = {t_int: [_ckpt_and_cell]}
    observer = EngineCoupledLedgerObserver(
        engine_holder=holder,
        ledger=ledger,
        schedule=schedule,
        harvest_fn=harvest_rare_class_yield,
        auto_advance=True,
    )
    spec = build_idea4_engine_spec(
        seed=int(seed), tick_count=tick_count, population=int(population)
    )
    engine = GenesisEngine.from_spec(spec, generation_boundary_observers=(observer,))
    holder["engine"] = engine
    result = engine.run_ticks()

    fires = int(observer.observer_fire_count)
    if fires != tick_count:
        raise ConfigurationError(
            f"observer fire count {fires} != tick_count {tick_count}."
        )
    yields = list(observer.yield_history)
    # Engine generation_index starts at 1 after first completed generation.
    # schedule key t_int matches observer generation_index.
    # Pre: generations 1..t_int-1 (indices 0..t_int-2 in yields)
    # At t_int (index t_int-1): checkpoint+ops already applied before harvest.
    # Post: generations t_int .. t_int+t_hor-1 → yields[t_int-1 : t_int-1+t_hor]
    if t_int <= 1:
        pre_yields: list[float] = []
    else:
        pre_yields = [float(y) for y in yields[: t_int - 1]]
    post_start = t_int - 1
    post_end = post_start + t_hor
    post_yields = [float(y) for y in yields[post_start:post_end]]
    baseline_mean = (
        float(sum(pre_yields) / len(pre_yields)) if pre_yields else 0.0
    )
    recover = _score_recover(baseline_mean=baseline_mean, post_yields=post_yields)
    tt = t_tilde_of(t_int, t_horizon=t_hor)

    eco_tail = observer.ecology_history[-5:] if observer.ecology_history else []
    n_alive_series = [float(e["n_alive"]) for e in observer.ecology_history]
    mean_atp_series = [float(e["mean_atp"]) for e in observer.ecology_history]

    return {
        "schema": SCHEMA,
        "idea_id": 4,
        "engine_path": ENGINE_PATH,
        "seed": int(seed),
        "run_id": f"idea4-engine-s{int(seed)}-{ops_cell}-t{t_int}",
        "ops_cell": str(ops_cell),
        "t_intervene": t_int,
        "T_horizon": t_hor,
        "t_tilde": float(tt),
        "recover": bool(recover),
        "baseline_mean_rare_yield": float(baseline_mean),
        "post_rare_yield_tail": [float(y) for y in post_yields[-5:]],
        "n_post_obs": len(post_yields),
        "observer_fire_count": fires,
        "tick_count": tick_count,
        "competence_id": COMPETENCE_ID,
        "checkpoint_id": CHECKPOINT_ID,
        "scaffold_id": SCAFFOLD_ID,
        "slope_threshold": SLOPE_THRESHOLD,
        "delta_p_threshold": DELTA_P_THRESHOLD,
        "claim_ceiling": CLAIM_CEILING,
        "hypothesis_supported": False,
        "red_queen_proved": False,
        "honesty": (
            "Engine closed-loop Idea4 cell under phase2_design. "
            "GenerationBoundaryObserver coupled to ContactAtpLedger on "
            "GenesisEngine life-loop. Not sealed recovery-window evidence; "
            "hypothesis_supported stays false. Volume ≠ discovery. "
            "Distinct from harness jsonl_campaign."
        ),
        "n_unit": "run",
        "engine_result_digest": result.snapshot.digest(),
        "ledger_digest": ledger.digest(),
        "n_alive_end": float(n_alive_series[-1]) if n_alive_series else 0.0,
        "mean_atp_end": float(mean_atp_series[-1]) if mean_atp_series else 0.0,
        "n_alive_mean": (
            float(sum(n_alive_series) / len(n_alive_series)) if n_alive_series else 0.0
        ),
        "ecology_tail": eco_tail,
        "recovery_progress_multiplier_used": False,
    }


def idea4_engine_constants() -> Mapping[str, Any]:
    return {
        "schema": SCHEMA,
        "engine_path": ENGINE_PATH,
        "claim_ceiling": CLAIM_CEILING,
        "hypothesis_supported": False,
        "red_queen_proved": False,
        "horizon_T": HORIZON_T,
        "t_intervene_grid": list(T_INTERVENE_GRID),
        "ops_cells": list(OPS_CELLS),
        "t_tilde_grid": [t_tilde_of(t) for t in T_INTERVENE_GRID],
        "slope_threshold": SLOPE_THRESHOLD,
        "delta_p_threshold": DELTA_P_THRESHOLD,
        "competence_id": COMPETENCE_ID,
        "checkpoint_id": CHECKPOINT_ID,
        "scaffold_id": SCAFFOLD_ID,
    }


def aggregate_idea4_engine_rates(
    records: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Emit P(recover|t_tilde,cell), per-cell slopes, and |ΔP| vs control."""

    buckets: dict[tuple[str, float], list[bool]] = {}
    for rec in records:
        if int(rec.get("idea_id", -1)) != 4:
            continue
        key = (str(rec["ops_cell"]), float(rec["t_tilde"]))
        buckets.setdefault(key, []).append(bool(rec["recover"]))

    p_recover: dict[str, float] = {}
    for (cell, tt), vals in sorted(buckets.items()):
        rate = float(sum(1 for v in vals if v) / len(vals)) if vals else 0.0
        p_recover[f"{cell}|t_tilde={tt:.4f}"] = rate

    # Slope of P vs t_tilde per cell (simple least-squares).
    by_cell: dict[str, list[tuple[float, float]]] = {}
    for (cell, tt), vals in buckets.items():
        rate = float(sum(1 for v in vals if v) / len(vals)) if vals else 0.0
        by_cell.setdefault(cell, []).append((float(tt), rate))
    slopes: dict[str, float] = {}
    for cell, pts in by_cell.items():
        if len(pts) < 2:
            slopes[cell] = 0.0
            continue
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        xbar = sum(xs) / len(xs)
        ybar = sum(ys) / len(ys)
        num = sum((x - xbar) * (y - ybar) for x, y in zip(xs, ys, strict=True))
        den = sum((x - xbar) ** 2 for x in xs)
        slopes[cell] = float(num / den) if den else 0.0

    # |ΔP| vs control at each shared t_tilde.
    delta_p: dict[str, float] = {}
    control_rates = {
        tt: float(sum(1 for v in vals if v) / len(vals))
        for (cell, tt), vals in buckets.items()
        if cell == "control" and vals
    }
    for (cell, tt), vals in buckets.items():
        if cell == "control" or tt not in control_rates or not vals:
            continue
        rate = float(sum(1 for v in vals if v) / len(vals))
        delta_p[f"{cell}|t_tilde={tt:.4f}"] = abs(rate - control_rates[tt])

    return {
        "p_recover_given_t_cell": p_recover,
        "slope_by_cell": slopes,
        "abs_delta_p_vs_control": delta_p,
        "slope_threshold": SLOPE_THRESHOLD,
        "delta_p_threshold": DELTA_P_THRESHOLD,
        "hypothesis_supported": False,
        "note": (
            "Aggregates are descriptive under phase2_design only. "
            "Soft-pass near 0.15 slope remains FAIL; no discovery claim."
        ),
    }
