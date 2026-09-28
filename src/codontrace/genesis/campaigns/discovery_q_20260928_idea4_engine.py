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
from codontrace.life_loop.engine_ledger_coupler import (
    EngineCoupledLedgerObserver,
    engine_pop_path_digest_from_ecology,
    population_path_fingerprint,
    pre_intervene_pop_digest_from_ecology,
)
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


def _lineage_after_checkpoint(
    census_history: list[list[dict[str, str]]],
    *,
    t_intervene: int,
) -> dict[str, Any]:
    """Births and new genome digests after the checkpoint census.

    The rare ledger tag is not an innovation. A birth is an organism id that
    was absent at the checkpoint. An innovation is a birth whose genome digest
    was also absent at the checkpoint.
    """

    idx = int(t_intervene) - 1
    if idx < 0 or idx >= len(census_history):
        return {
            "lineage_branching_real": False,
            "innovation_observable": False,
            "n_births_after_checkpoint": 0,
            "n_novel_genomes_after_checkpoint": 0,
            "n_regained_genomes": 0,
            "lost_then_regained": False,
            "checkpoint_organism_ids": [],
            "checkpoint_genome_digests": [],
        }
    checkpoint = census_history[idx]
    ck_ids = {row["id"] for row in checkpoint}
    ck_genomes = {row["genome"] for row in checkpoint}
    birth_ids: set[str] = set()
    novel_genomes: set[str] = set()
    missing: set[str] = set()
    regained: set[str] = set()
    for later in census_history[idx + 1 :]:
        present = {row["genome"] for row in later}
        for genome in ck_genomes:
            if genome not in present:
                missing.add(genome)
            elif genome in missing:
                regained.add(genome)
        for row in later:
            if row["id"] in ck_ids:
                continue
            birth_ids.add(row["id"])
            if row["genome"] not in ck_genomes:
                novel_genomes.add(row["genome"])
    # A new genome is ordinary reproduction. Recovery is a checkpoint genome
    # that disappears and is present again later. Background births do not open
    # the window gate.
    return {
        "lineage_branching_real": bool(birth_ids),
        "innovation_observable": bool(novel_genomes),
        "lost_then_regained": bool(regained),
        "n_births_after_checkpoint": len(birth_ids),
        "n_novel_genomes_after_checkpoint": len(novel_genomes),
        "n_regained_genomes": len(regained),
        "checkpoint_organism_ids": sorted(ck_ids),
        "checkpoint_genome_digests": sorted(ck_genomes),
    }


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
    cell_holder: dict[str, Any] = {"cell": None, "ckpt": None}

    def _ckpt_and_cell(led: Any, generation_index: int) -> dict[str, Any]:
        del generation_index
        ckpt = led.relocate_recovery_token(
            RECOVERY_TOKEN_KEY, remove=False, new_payload="relocated_engine"
        )
        cell = _apply_ops_cell(led, ops_cell)
        cell_holder["ckpt"] = ckpt
        cell_holder["cell"] = cell
        return {"ckpt": ckpt, "cell": cell}

    schedule = {t_int: [_ckpt_and_cell]}
    observer = EngineCoupledLedgerObserver(
        engine_holder=holder,
        ledger=ledger,
        schedule=schedule,
        harvest_fn=harvest_rare_class_yield,
        auto_advance=True,
        feedback_enabled=True,
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
    recover_lineage = _lineage_after_checkpoint(
        observer.census_history, t_intervene=t_int
    )
    # Rare-class yield rebound is not recovery of a genotype innovation.
    rare_yield_rebound = _score_recover(
        baseline_mean=baseline_mean, post_yields=post_yields
    )
    recover = bool(recover_lineage["lost_then_regained"])
    tt = t_tilde_of(t_int, t_horizon=t_hor)

    eco_tail = observer.ecology_history[-5:] if observer.ecology_history else []
    n_alive_series = [float(e["n_alive"]) for e in observer.ecology_history]
    mean_atp_series = [float(e["mean_atp"]) for e in observer.ecology_history]

    pre_pop = pre_intervene_pop_digest_from_ecology(
        observer.ecology_history, t_intervene=t_int
    )
    eng_pop = engine_pop_path_digest_from_ecology(
        observer.ecology_history, t_intervene=t_int
    )
    pop_fp = population_path_fingerprint(engine)
    feedback_applied = any(
        bool(h.get("effect_applied")) for h in observer.feedback_history
    )
    # Per-cell coupler flag: feedback ran. Paired PASS still requires different
    # engine_pop_path_digest across arms (see paired test).
    coupler_affects_engine = bool(feedback_applied)
    ledger_only_warn = not coupler_affects_engine

    cell_result = cell_holder.get("cell") or {}
    match_report = None
    match_exact = None
    exclude_from_combo_e = None
    if str(ops_cell) == "cut_matched_random" and isinstance(cell_result, dict):
        match_report = cell_result.get("match_report")
        match_exact = bool(cell_result.get("match_exact", False))
        exclude_from_combo_e = bool(
            cell_result.get("exclude_from_combo_e", not match_exact)
        )
    elif str(ops_cell) == "cut_named_scaffold" and isinstance(cell_result, dict):
        # Scaffold arm: record cut stats; match_exact is only defined vs matched.
        match_report = {
            "scaffold_cut_edge_ids": list(cell_result.get("cut_edge_ids", [])),
            "n_edges_cut_scaffold": int(cell_result.get("n_edges_cut", 0)),
            "degree_sum_scaffold": int(cell_result.get("degree_sum", 0)),
            "contact_weight_sum_scaffold": float(
                cell_result.get("contact_weight_sum", 0.0)
            ),
            "atp_lost_scaffold": float(cell_result.get("atp_lost", 0.0)),
        }

    # P4: pre-placed rare/scaffold markers are not genotype innovation; no real
    # lineage branch checkpoint yet → opportunity meters stay false on the cell.
    # Aggregate sets control_recover_rate / window_test_valid from the cohort.
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
        "rare_yield_rebound": bool(rare_yield_rebound),
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
            "GenesisEngine life-loop with ledger→engine contact-energy feedback. "
            "Not sealed recovery-window evidence; hypothesis_supported stays false. "
            "Volume ≠ discovery. Distinct from harness jsonl_campaign."
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
        "pre_intervene_pop_digest": pre_pop,
        "engine_pop_path_digest": eng_pop,
        "population_path_fingerprint": pop_fp,
        "coupler_affects_engine": coupler_affects_engine,
        "ledger_only_warn": ledger_only_warn,
        "match_report": match_report,
        "match_exact": match_exact,
        "exclude_from_combo_e": exclude_from_combo_e,
        "n_edges_cut": (
            int(cell_result.get("n_edges_cut"))
            if isinstance(cell_result, dict) and "n_edges_cut" in cell_result
            else None
        ),
        "cut_edge_ids": (
            list(cell_result.get("cut_edge_ids", []))
            if isinstance(cell_result, dict) and "cut_edge_ids" in cell_result
            else None
        ),
        "control_recover_rate": None,
        "window_test_valid": False,
        "window_law_tested": False,
        "lineage_branching_real": bool(recover_lineage["lineage_branching_real"]),
        "innovation_observable": bool(recover_lineage["innovation_observable"]),
        "n_births_after_checkpoint": int(recover_lineage["n_births_after_checkpoint"]),
        "n_novel_genomes_after_checkpoint": int(
            recover_lineage["n_novel_genomes_after_checkpoint"]
        ),
        "n_regained_genomes": int(recover_lineage["n_regained_genomes"]),
        "lost_then_regained": bool(recover_lineage["lost_then_regained"]),
        "checkpoint_organism_ids": list(recover_lineage["checkpoint_organism_ids"]),
        "checkpoint_genome_digests": list(recover_lineage["checkpoint_genome_digests"]),
        "feedback_event_count": sum(
            1 for h in observer.feedback_history if h.get("effect_applied")
        ),
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
    inexact_cells = {
        str(rec.get("ops_cell"))
        for rec in records
        if rec.get("match_exact") is False
    }
    for (cell, tt), vals in buckets.items():
        if cell == "control" or cell in inexact_cells or tt not in control_rates or not vals:
            continue
        rate = float(sum(1 for v in vals if v) / len(vals))
        delta_p[f"{cell}|t_tilde={tt:.4f}"] = abs(rate - control_rates[tt])

    # P4 recovery-opportunity preflight (diagnostic; not a window law claim).
    control_vals = [
        bool(rec["recover"])
        for rec in records
        if int(rec.get("idea_id", -1)) == 4 and str(rec.get("ops_cell")) == "control"
    ]
    control_recover_rate = (
        float(sum(1 for v in control_vals if v) / len(control_vals))
        if control_vals
        else 0.0
    )
    lineage_branching_real = any(
        bool(rec.get("lineage_branching_real"))
        for rec in records
        if int(rec.get("idea_id", -1)) == 4
    )
    innovation_observable = any(
        bool(rec.get("innovation_observable"))
        for rec in records
        if int(rec.get("idea_id", -1)) == 4
    )
    # recover=0 everywhere (including control) ⇒ window_test_valid=false.
    window_test_valid = bool(
        control_recover_rate > 0.0 and lineage_branching_real and innovation_observable
    )

    return {
        "p_recover_given_t_cell": p_recover,
        "slope_by_cell": slopes,
        "abs_delta_p_vs_control": delta_p,
        "slope_threshold": SLOPE_THRESHOLD,
        "delta_p_threshold": DELTA_P_THRESHOLD,
        "hypothesis_supported": False,
        "control_recover_rate": float(control_recover_rate),
        "window_test_valid": bool(window_test_valid),
        "window_law_tested": False,
        "inexact_match_cells_excluded": sorted(inexact_cells),
        "lineage_branching_real": bool(lineage_branching_real),
        "innovation_observable": bool(innovation_observable),
        "note": (
            "Aggregates are descriptive under phase2_design only. "
            "Soft-pass near 0.15 slope remains FAIL; no discovery claim. "
            "window_test_valid=false when control recover rate is 0 or "
            "lineage/innovation opportunity is absent (preflight diagnostic)."
        ),
    }
