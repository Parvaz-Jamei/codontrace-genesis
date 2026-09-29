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
EXPLORATORY_RECOVER_ID = "GENOME-DIGEST-LOST-THEN-REGAINED-V1"
EXPLORATORY_RECOVER_DATE = "2026-09-29"
PREREG_ESTIMAND_ID = "FI-RARECLASS-CONTACT-YIELD-V1"
PREREG_ESTIMAND_DATE = "2026-09-28"
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
    feedback_allocation: str = "global_smear",
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
        feedback_allocation=str(feedback_allocation),
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
    intervention_rows = [
        row
        for row in observer.feedback_history
        if int(row.get("generation_index", -1)) == t_int and "burden" in row
    ]
    intervention_feedback = None
    if intervention_rows:
        row = intervention_rows[-1]
        intervention_feedback = {
            "burden": float(row["burden"]),
            "burden_lost_energy": float(row.get("burden_lost_energy", 0.0)),
            "burden_edge_changes": float(row.get("burden_edge_changes", 0.0)),
            "burden_digest": float(row.get("burden_digest", 0.0)),
            "burden_token": float(row.get("burden_token", 0.0)),
            "n_edge_changes": float(row.get("n_edge_changes", 0.0)),
            "digest_changed": float(row.get("digest_changed", 0.0)),
            "token_changed": float(row.get("token_changed", 0.0)),
            "effect_applied": bool(row.get("effect_applied")),
            "food_from_lost_energy": float(row.get("food_from_lost_energy", 0.0)),
            "food_from_edge_count": float(row.get("food_from_edge_count", 0.0)),
            "allocation": str(row.get("allocation", feedback_allocation)),
            "recipient_ids": [str(item) for item in row.get("recipient_ids", [])],
            "endpoints_enter_debit": bool(row.get("endpoints_enter_debit")),
            "food_follows_endpoints": bool(row.get("food_follows_endpoints")),
            "endpoint_map_is_contact_physics": bool(
                row.get("endpoint_map_is_contact_physics")
            ),
            "lineage_resource_transfer": bool(row.get("lineage_resource_transfer")),
            "pop_fingerprint": str(row.get("pop_fingerprint", "")),
        }
    match_is_planted_mirror = False
    independent_design = None
    design_failure = None
    if isinstance(cell_result, dict):
        raw_design = cell_result.get("independent_match_design")
        if isinstance(raw_design, dict):
            independent_design = raw_design
            design_failure = bool(cell_result.get("design_failure"))
    if isinstance(match_report, dict):
        scaffold_ids = [str(item) for item in match_report.get("scaffold_cut_edge_ids", [])]
        matched_ids = [str(item) for item in match_report.get("matched_cut_edge_ids", [])]
        match_is_planted_mirror = bool(
            scaffold_ids == ["E0", "E1"]
            and matched_ids == ["E6", "E7"]
            and ledger.match_mirrors.get("E0") == "E6"
            and ledger.match_mirrors.get("E1") == "E7"
        )
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
            "recover is the exploratory genome-digest return, not the "
            "preregistered rare-yield rule and not a lineage identity. "
            "The E6/E7 mirror is a code check, not an independent control. "
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
        "match_is_planted_mirror": bool(match_is_planted_mirror),
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
        "recovery_window_built": False,
        "recovery_window_missing": [
            "real_branching_checkpoint",
            "innovation_arising_in_lineage",
            "control_recovery_opportunity",
        ],
        "lineage_branching_real": bool(recover_lineage["lineage_branching_real"]),
        "innovation_observable": bool(recover_lineage["innovation_observable"]),
        "n_births_after_checkpoint": int(recover_lineage["n_births_after_checkpoint"]),
        "n_novel_genomes_after_checkpoint": int(
            recover_lineage["n_novel_genomes_after_checkpoint"]
        ),
        "n_regained_genomes": int(recover_lineage["n_regained_genomes"]),
        "lost_then_regained": bool(recover_lineage["lost_then_regained"]),
        "recover_definition_id": EXPLORATORY_RECOVER_ID,
        "recover_definition_date": EXPLORATORY_RECOVER_DATE,
        "recover_role": "exploratory",
        "primary_estimand_id": PREREG_ESTIMAND_ID,
        "primary_estimand_date": PREREG_ESTIMAND_DATE,
        "primary_estimand_value": bool(rare_yield_rebound),
        "lineage_recovery_established": False,
        "checkpoint_fork_complete": False,
        "parent_child_ids_recorded": False,
        "checkpoint_organism_ids": list(recover_lineage["checkpoint_organism_ids"]),
        "checkpoint_genome_digests": list(recover_lineage["checkpoint_genome_digests"]),
        "feedback_event_count": sum(
            1 for h in observer.feedback_history if h.get("effect_applied")
        ),
        "intervention_feedback": intervention_feedback,
        "feedback_allocation": str(feedback_allocation),
        "endpoints_enter_debit": bool(
            intervention_feedback and intervention_feedback.get("endpoints_enter_debit")
        ),
        "independent_control": False if match_is_planted_mirror else None,
        "independent_match_design": independent_design,
        "design_failure": design_failure,
        "scientific_contrast_eligible": False if match_is_planted_mirror else None,
        "endpoint_map_is_contact_physics": False,
        "lineage_resource_transfer": False,
        "contact_structure_effect_identified": False,
        "knowledge_effect_identified": False,
        "topology_effect_identified": False,
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


def _idea4_record(rec: Mapping[str, Any]) -> bool:
    return int(rec.get("idea_id", -1)) == 4


def _exploratory_recover_record(rec: Mapping[str, Any]) -> bool:
    return bool(
        rec.get("recover_definition_id") == EXPLORATORY_RECOVER_ID
        and str(rec.get("recover_definition_date")) == EXPLORATORY_RECOVER_DATE
        and rec.get("recover_role") == "exploratory"
    )


def _preregistered_estimand_record(rec: Mapping[str, Any]) -> bool:
    return bool(
        rec.get("primary_estimand_id") == PREREG_ESTIMAND_ID
        and str(rec.get("primary_estimand_date")) == PREREG_ESTIMAND_DATE
        and ("primary_estimand_value" in rec or "rare_yield_rebound" in rec)
    )


def _inexact_match(rec: Mapping[str, Any]) -> bool:
    return rec.get("match_exact") is False


def _nonindependent_match(rec: Mapping[str, Any]) -> bool:
    """Exact-looking arms that are still not an independent control.

    An inexact row is counted on its own. It is not also called a mirror.
    """

    if _inexact_match(rec):
        return False
    if rec.get("match_is_planted_mirror") is True:
        return True
    if rec.get("independent_control") is False:
        return True
    if rec.get("scientific_contrast_eligible") is False:
        return True
    if rec.get("design_failure") is True:
        return True
    if (
        str(rec.get("ops_cell")) == "cut_matched_random"
        and rec.get("independent_control") is not True
    ):
        return True
    return False


def _blocked_from_contrast(rec: Mapping[str, Any]) -> bool:
    return _inexact_match(rec) or _nonindependent_match(rec)


def _tt_label(rec: Mapping[str, Any]) -> str:
    return f"{float(rec['t_tilde']):.4f}"


def _rate_table(
    rows: Sequence[Mapping[str, Any]],
    value_of: Any,
) -> tuple[dict[str, float], dict[str, float], dict[str, float]]:
    buckets: dict[tuple[str, float], list[bool]] = {}
    for rec in rows:
        if _blocked_from_contrast(rec):
            continue
        key = (str(rec["ops_cell"]), float(rec["t_tilde"]))
        buckets.setdefault(key, []).append(bool(value_of(rec)))
    rates: dict[str, float] = {}
    by_cell: dict[str, list[tuple[float, float]]] = {}
    for (cell, tt), vals in sorted(buckets.items()):
        rate = float(sum(1 for v in vals if v) / len(vals)) if vals else 0.0
        rates[f"{cell}|t_tilde={tt:.4f}"] = rate
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
    control_rates = {
        tt: float(sum(1 for v in vals if v) / len(vals))
        for (cell, tt), vals in buckets.items()
        if cell == "control" and vals
    }
    delta_p: dict[str, float] = {}
    for (cell, tt), vals in buckets.items():
        if cell == "control" or tt not in control_rates or not vals:
            continue
        rate = float(sum(1 for v in vals if v) / len(vals))
        delta_p[f"{cell}|t_tilde={tt:.4f}"] = abs(rate - control_rates[tt])
    return rates, slopes, delta_p


def aggregate_idea4_engine_rates(
    records: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Separate the 2026-09-28 rare-yield rule from the 2026-09-29 digest return.

    Rows that do not carry the dated definition are excluded from that
    series. Planted-mirror and inexact matched arms are excluded from both
    contrasts. Their counts are reported. They are not dropped silently.
    """

    idea4_recs = [rec for rec in records if _idea4_record(rec)]
    exploratory_rows = [rec for rec in idea4_recs if _exploratory_recover_record(rec)]
    prereg_rows = [rec for rec in idea4_recs if _preregistered_estimand_record(rec)]
    n_excluded_recover_definition_mismatch = sum(
        1 for rec in idea4_recs if not _exploratory_recover_record(rec)
    )
    p_recover, slopes, delta_p = _rate_table(
        exploratory_rows, lambda rec: rec["recover"]
    )

    def _prereg_value(rec: Mapping[str, Any]) -> bool:
        if "primary_estimand_value" in rec:
            return bool(rec["primary_estimand_value"])
        return bool(rec["rare_yield_rebound"])

    rare_rates, rare_slopes, rare_delta = _rate_table(prereg_rows, _prereg_value)
    exploratory_controls = [
        bool(rec["recover"])
        for rec in exploratory_rows
        if str(rec.get("ops_cell")) == "control" and not _blocked_from_contrast(rec)
    ]
    control_recover_rate = (
        float(sum(1 for v in exploratory_controls if v) / len(exploratory_controls))
        if exploratory_controls
        else 0.0
    )
    prereg_controls = [
        _prereg_value(rec)
        for rec in prereg_rows
        if str(rec.get("ops_cell")) == "control" and not _blocked_from_contrast(rec)
    ]
    preregistered_control_rate = (
        float(sum(1 for v in prereg_controls if v) / len(prereg_controls))
        if prereg_controls
        else 0.0
    )
    inexact_cells = sorted(
        {str(rec.get("ops_cell")) for rec in idea4_recs if _inexact_match(rec)}
    )
    nonindependent_cells = sorted(
        {str(rec.get("ops_cell")) for rec in idea4_recs if _nonindependent_match(rec)}
    )
    inexact_by_t: dict[str, int] = {}
    nonindependent_by_t: dict[str, int] = {}
    for rec in idea4_recs:
        label = _tt_label(rec)
        if _inexact_match(rec):
            inexact_by_t[label] = inexact_by_t.get(label, 0) + 1
        if _nonindependent_match(rec):
            nonindependent_by_t[label] = nonindependent_by_t.get(label, 0) + 1

    qualifying_controls: list[Mapping[str, Any]] = []
    for rec in idea4_recs:
        if str(rec.get("ops_cell")) != "control":
            continue
        if not _exploratory_recover_record(rec) or _blocked_from_contrast(rec):
            continue
        if not (
            bool(rec.get("recover"))
            and bool(rec.get("lineage_branching_real"))
            and bool(rec.get("innovation_observable"))
        ):
            continue
        if rec.get("seed") is None:
            continue
        seed = rec.get("seed")
        label = _tt_label(rec)
        paired = any(
            other is not rec
            and _exploratory_recover_record(other)
            and other.get("seed") == seed
            and _tt_label(other) == label
            and str(other.get("ops_cell")) != "control"
            and not _blocked_from_contrast(other)
            for other in idea4_recs
        )
        if paired:
            qualifying_controls.append(rec)
    window_test_valid = bool(qualifying_controls)
    any_branch = any(bool(rec.get("lineage_branching_real")) for rec in idea4_recs)
    any_innov = any(bool(rec.get("innovation_observable")) for rec in idea4_recs)

    return {
        "p_recover_given_t_cell": p_recover,
        "slope_by_cell": slopes,
        "abs_delta_p_vs_control": delta_p,
        "p_rare_yield_rebound_given_t_cell": rare_rates,
        "rare_yield_slope_by_cell": rare_slopes,
        "rare_yield_abs_delta_p_vs_control": rare_delta,
        "slope_threshold": SLOPE_THRESHOLD,
        "delta_p_threshold": DELTA_P_THRESHOLD,
        "hypothesis_supported": False,
        "control_recover_rate": float(control_recover_rate),
        "preregistered_control_rare_yield_rate": float(preregistered_control_rate),
        "window_test_valid": bool(window_test_valid),
        "window_law_tested": False,
        "recovery_window_built": False,
        "lineage_recovery_established": False,
        "p_recover_definition": "exploratory_genome_digest_return",
        "p_recover_not_preregistered": True,
        "preregistered_estimand_id": PREREG_ESTIMAND_ID,
        "preregistered_estimand_date": PREREG_ESTIMAND_DATE,
        "recovery_window_missing": [
            "real_branching_checkpoint",
            "innovation_arising_in_lineage",
            "control_recovery_opportunity",
        ],
        "inexact_match_cells_excluded": inexact_cells,
        "nonindependent_cells_excluded": nonindependent_cells,
        "n_excluded_inexact_by_t": dict(sorted(inexact_by_t.items())),
        "n_excluded_nonindependent_by_t": dict(sorted(nonindependent_by_t.items())),
        "n_excluded_recover_definition_mismatch": int(
            n_excluded_recover_definition_mismatch
        ),
        "lineage_branching_real": bool(qualifying_controls),
        "innovation_observable": bool(qualifying_controls),
        "lineage_branching_real_any_row": bool(any_branch),
        "innovation_observable_any_row": bool(any_innov),
        "note": (
            "Aggregates are descriptive under phase2_design only. "
            "p_recover is only the exploratory genome-digest return dated "
            "2026-09-29. Rows without that definition are counted in "
            "n_excluded_recover_definition_mismatch and are not pooled into it. "
            "The 2026-09-28 rare-yield rule is p_rare_yield_rebound_given_t_cell. "
            "A planted mirror or an undeclared matched cut is excluded from both "
            "contrasts and counted by time. "
            "Soft-pass near 0.15 slope remains FAIL; no discovery claim. "
            "window_test_valid requires the dated exploratory recover, branching, "
            "and innovation on the same unblocked control row of one seed and "
            "t_tilde, plus a paired arm that carries the same dated exploratory "
            "definition and is not an inexact or non-independent match. "
            "It is not a window law and it is not lineage recovery."
        ),
    }
