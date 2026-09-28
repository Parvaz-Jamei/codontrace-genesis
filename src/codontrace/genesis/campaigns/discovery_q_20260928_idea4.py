"""Discovery questions 2026-09-28 — Idea 4 phase-2 harness smoke.

Branching-history recovery window under sealed phase-2 design digest.
Harness only: ledger ops + generation-boundary observer wiring.
Full T=40 campaigns are not authorised by this smoke pack.
Claim ceiling: phase2_design. red_queen_proved stays False.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from codontrace._types import JsonValue
from codontrace.errors import ConfigurationError
from codontrace.genesis.canonical import canonical_digest
from codontrace.life_loop.contact_atp_ledger import (
    CHECKPOINT_RELOCATE_RECOVERY,
    CONTACT_TAG_RARE,
    ContactAtpLedger,
    build_smoke_ledger,
)
from codontrace.life_loop.discovery_boundary_hooks import make_op, run_boundary_loop

SCHEMA = "discovery_q_20260928_idea4_harness_v1"
CLAIM_CEILING = "phase2_design"
COMPETENCE_ID = "FI-RARECLASS-CONTACT-YIELD-V1"
CHECKPOINT_ID = "CKPT-RELOCATE-RECOVERY-TOKEN-V1"
SCAFFOLD_ID = "SCAF-CONTACT-SRC-PATH-V1"
RECOVERY_TOKEN_KEY = "token:recovery:FI-RARECLASS-CONTACT-YIELD-V1"
PRED_FAIL_DIGEST_KEY = "digest:pred_fail:smoke_v1"
HORIZON_T = 40
SLOPE_THRESHOLD = 0.15
DELTA_P_THRESHOLD = 0.20
T_TILDE_GRID_MIN = 3
REJECTED_CHECKPOINT_ALIASES = (
    "CKPT-REMOVE-PREDFAIL-DIGEST-MID-V1",
    "CKPT-CUT-SCAF-MEMBERSHIP-FREEZE-V1",
)
CLAIMGATE_REFUSES = (
    "red_queen_proved",
    "discovery_claim",
    "first_claim",
)

SUCCESS_RULE = (
    "Within horizon T generation boundaries after the checkpoint intervention, "
    "the run recovers a rare-class contact yield advantage: mean ATP from contacts "
    "tagged class=rare (ledger tag only) is at least 1.25× the run’s own "
    "pre-checkpoint baseline for that label, sustained for ≥3 consecutive "
    "generation boundaries ending at or before T."
)


def _score_recover_rule_shape(ledger: ContactAtpLedger) -> dict[str, Any]:
    """API-shape scorer for the sealed recover rule (smoke horizons are short)."""

    rare_edges = ledger.edges_with_tag(CONTACT_TAG_RARE)
    present_rare = [
        eid for eid in rare_edges if ledger.edges[eid].present and not ledger.edges[eid].masked
    ]
    yield_sum = sum(ledger.edges[eid].atp_yield for eid in present_rare)
    token_present = RECOVERY_TOKEN_KEY in ledger.recovery_tokens
    return {
        "competence_id": COMPETENCE_ID,
        "horizon_T": HORIZON_T,
        "slope_threshold": SLOPE_THRESHOLD,
        "delta_p_threshold": DELTA_P_THRESHOLD,
        "t_tilde_grid_min": T_TILDE_GRID_MIN,
        "rare_edge_ids": rare_edges,
        "present_rare_edge_ids": present_rare,
        "rare_yield_sum": float(yield_sum),
        "recovery_token_present": token_present,
        "success_rule": SUCCESS_RULE,
        "note": (
            "Smoke scores recover-rule API shape only; full T=40 campaigns "
            "are not authorised by this harness smoke."
        ),
    }


def run_idea4_smoke(
    *,
    seed: int = 42,
    horizons: Sequence[int] | None = None,
) -> dict[str, JsonValue]:
    """Deterministic Idea4 harness smoke — not a discovery campaign run."""

    # Tiny horizons for smoke; API still exposes ≥3 t̃ points.
    use_horizons = tuple(horizons) if horizons is not None else (2, 3, 4)
    if len(use_horizons) < T_TILDE_GRID_MIN:
        use_horizons = tuple(list(use_horizons) + [2, 3, 4])[: max(T_TILDE_GRID_MIN, len(use_horizons))]

    ledger = build_smoke_ledger(seed=int(seed))
    # Intervention schedule on a short generation-boundary loop.
    # Apply scramble, named-scaffold cut, digest ablation, recovery relocate
    # at distinct boundaries so distinction locks are exercised.
    schedule = {
        0: [make_op("scramble_contacts", degree_preserving=True)],
        1: [make_op("cut_named_scaffold", scaffold_id=SCAFFOLD_ID)],
        2: [make_op("ablate_knowledge_digest", digest_key=PRED_FAIL_DIGEST_KEY)],
        3: [
            make_op(
                "relocate_recovery_token",
                token_key=RECOVERY_TOKEN_KEY,
                remove=False,
                new_payload="relocated_smoke",
            )
        ],
    }
    # Degree-matched random cut control on a separate ledger copy path.
    control = build_smoke_ledger(seed=int(seed))
    scaffold_deg = control.edge_degree("E0")
    control_schedule = {
        0: [make_op("scramble_contacts", degree_preserving=True)],
        1: [make_op("cut_matched_random", degree=scaffold_deg)],
    }

    history = run_boundary_loop(ledger, generations=max(use_horizons), schedule=schedule)
    control_history = run_boundary_loop(
        control, generations=max(use_horizons), schedule=control_schedule
    )

    recover_shape = _score_recover_rule_shape(ledger)
    # Relocate keeps key; verify digests ablated and scaffold cut applied.
    digests_ablated = PRED_FAIL_DIGEST_KEY not in ledger.failed_prediction_digests
    scaffold_cut = all(not ledger.edges[eid].present for eid in ("E0", "E1"))
    token_relocated = ledger.recovery_tokens.get(RECOVERY_TOKEN_KEY) == "relocated_smoke"
    engineering_green = bool(
        CHECKPOINT_ID == CHECKPOINT_RELOCATE_RECOVERY
        and digests_ablated
        and scaffold_cut
        and token_relocated
        and bool(history)
        and bool(control_history)
    )

    pack: dict[str, JsonValue] = {
        "schema": SCHEMA,
        "claim_ceiling": CLAIM_CEILING,
        "competence_id": COMPETENCE_ID,
        "checkpoint_id": CHECKPOINT_ID,
        "scaffold_id": SCAFFOLD_ID,
        "recovery_token_key": RECOVERY_TOKEN_KEY,
        "rejected_checkpoint_aliases": list(REJECTED_CHECKPOINT_ALIASES),
        "horizon_T": HORIZON_T,
        "slope_threshold": SLOPE_THRESHOLD,
        "delta_p_threshold": DELTA_P_THRESHOLD,
        "t_tilde_grid": list(use_horizons),
        "t_tilde_grid_min": T_TILDE_GRID_MIN,
        "engineering_green": engineering_green,
        "hypothesis_supported": False,
        "red_queen_proved": False,
        "claimgate_refuses": list(CLAIMGATE_REFUSES),
        "honesty": (
            "Harness smoke only under sealed phase-2 design digest. "
            "No discovery claim. Full campaigns remain off until owner allows."
        ),
        "recover_rule_shape": recover_shape,
        "ledger_digest": ledger.digest(),
        "control_ledger_digest": control.digest(),
        "history_len": len(history),
        "control_history_len": len(control_history),
        "distinction_locks": {
            "checkpoint_is_relocate_recovery_token": CHECKPOINT_ID
            == "CKPT-RELOCATE-RECOVERY-TOKEN-V1",
            "checkpoint_distinct_from_ablate_digest": digests_ablated
            and RECOVERY_TOKEN_KEY in ledger.recovery_tokens,
            "checkpoint_distinct_from_scaffold_cut": scaffold_cut
            and RECOVERY_TOKEN_KEY in ledger.recovery_tokens,
            "class_rare_is_ledger_tag_only": True,
        },
    }
    pack["pack_digest"] = canonical_digest(
        {k: v for k, v in pack.items() if k != "pack_digest"},
        prefix="idea4_smoke",
    )
    return pack


def idea4_constants() -> Mapping[str, Any]:
    return {
        "competence_id": COMPETENCE_ID,
        "checkpoint_id": CHECKPOINT_ID,
        "scaffold_id": SCAFFOLD_ID,
        "horizon_T": HORIZON_T,
        "slope_threshold": SLOPE_THRESHOLD,
        "delta_p_threshold": DELTA_P_THRESHOLD,
        "claim_ceiling": CLAIM_CEILING,
        "red_queen_proved": False,
        "rejected_checkpoint_aliases": list(REJECTED_CHECKPOINT_ALIASES),
    }


# ---------------------------------------------------------------------------
# Scored cell API (phase2_design meters; not a discovery claim)
# ---------------------------------------------------------------------------

# Mid-history intervention times on the T=40 series — NOT smoke horizons (2,3,4).
T_INTERVENE_GRID: tuple[int, ...] = (10, 20, 30)
OPS_CELLS: tuple[str, ...] = (
    "control",
    "scramble_contacts",
    "cut_named_scaffold",
    "cut_matched_random",
    "ablate_knowledge_digest",
)


def t_tilde_of(t_intervene: int, *, t_horizon: int = HORIZON_T) -> float:
    """Normalised intervention time t_intervene / T_horizon."""

    if t_horizon <= 0:
        raise ConfigurationError("t_horizon must be > 0.")
    return float(t_intervene) / float(t_horizon)


def harvest_rare_class_yield(ledger: ContactAtpLedger) -> float:
    """Per-boundary rare-class contact ATP (ledger tag only; never genotype)."""

    raw = 0.0
    for eid in ledger.edges_with_tag(CONTACT_TAG_RARE):
        edge = ledger.edges[eid]
        if edge.present and not edge.masked:
            raw += float(edge.atp_yield)
    token = ledger.recovery_tokens.get(RECOVERY_TOKEN_KEY)
    if token == "eligible":
        mult = 1.0
    elif token is None:
        mult = 0.35
    else:
        mult = 0.55  # relocated payload
    scaffold_key = f"scaffold_edges:{SCAFFOLD_ID}"
    members = ledger.scaffold_edge_sets.get(scaffold_key, set())
    if members:
        present_n = sum(
            1
            for eid in members
            if eid in ledger.edges and ledger.edges[eid].present
        )
        mult *= 0.4 + 0.6 * (present_n / len(members))
    if not ledger.failed_prediction_digests:
        mult *= 0.75
    return float(raw) * float(mult)


def _score_recover(
    *,
    baseline_mean: float,
    post_yields: Sequence[float],
) -> bool:
    """FI-RARECLASS-CONTACT-YIELD-V1: ≥1.25× baseline for ≥3 consecutive gens."""

    if baseline_mean <= 0.0:
        return False
    threshold = 1.25 * float(baseline_mean)
    streak = 0
    for y in post_yields:
        if float(y) >= threshold:
            streak += 1
            if streak >= 3:
                return True
        else:
            streak = 0
    return False


def _apply_ops_cell(ledger: ContactAtpLedger, ops_cell: str) -> dict[str, Any]:
    """Apply one factorial cell op (checkpoint relocate is applied separately)."""

    cell = str(ops_cell)
    if cell == "control":
        return {"op": "control", "applied": False}
    if cell == "scramble_contacts":
        return ledger.scramble_contacts(degree_preserving=True)
    if cell == "cut_named_scaffold":
        return ledger.cut_named_scaffold(SCAFFOLD_ID)
    if cell == "cut_matched_random":
        # Match n_edges / degree / ATP targets to what the named scaffold would cut.
        profile = ledger.scaffold_cut_profile(SCAFFOLD_ID)
        n_edges = int(profile["n_edges_cut"])
        if n_edges < 1:
            raise ConfigurationError("scaffold cut profile has no present edges to match.")
        deg = int(profile["per_edge_degree"])
        matched = ledger.cut_matched_random(
            deg,
            n_edges=n_edges,
            target_degree_sum=int(profile["degree_sum"]),
            target_atp_sum=float(profile["atp_lost"]),
            target_weight_sum=float(profile["contact_weight_sum"]),
        )
        report = ContactAtpLedger.build_cut_match_report(profile, matched)
        matched["match_report"] = report
        matched["match_exact"] = bool(report["match_exact"])
        matched["exclude_from_combo_e"] = bool(report["exclude_from_combo_e"])
        matched["scaffold_cut_edge_ids"] = list(profile["cut_edge_ids"])
        matched["n_edges_cut_scaffold"] = int(profile["n_edges_cut"])
        return matched
    if cell == "ablate_knowledge_digest":
        return ledger.ablate_knowledge_digest(PRED_FAIL_DIGEST_KEY)
    raise ConfigurationError(f"unknown Idea4 ops_cell {ops_cell!r}.")


def run_idea4_scored_cell(
    *,
    seed: int,
    ops_cell: str,
    t_intervene: int,
    t_horizon: int = HORIZON_T,
) -> dict[str, JsonValue]:
    """One N=run Idea4 scored cell under GenerationBoundaryObserver series.

    Always applies CKPT-RELOCATE-RECOVERY-TOKEN-V1 at t_intervene, then the
    factorial ops_cell (control = checkpoint only). Scores FI recover bool.
    hypothesis_supported stays False (volume ≠ discovery).
    """

    if ops_cell not in OPS_CELLS:
        raise ConfigurationError(f"unknown Idea4 ops_cell {ops_cell!r}.")
    if int(t_intervene) < 1:
        raise ConfigurationError("t_intervene must be >= 1.")
    if int(t_horizon) < T_TILDE_GRID_MIN:
        raise ConfigurationError(f"t_horizon must be >= {T_TILDE_GRID_MIN}.")
    # Refuse the smoke-only short grid as the scored campaign horizon.
    if int(t_horizon) <= 4:
        raise ConfigurationError(
            "scored Idea4 refuses smoke horizons (T<=4); use mid-history on T≈40."
        )

    t_int = int(t_intervene)
    t_hor = int(t_horizon)
    ledger = build_smoke_ledger(seed=int(seed))
    knowledge_capital = 0.0
    pre_yields: list[float] = []

    # Pre-checkpoint burn-in at generation boundaries (observer-compatible).
    for _g in range(t_int):
        if ledger.failed_prediction_digests:
            knowledge_capital += 0.05
        pre_yields.append(harvest_rare_class_yield(ledger))
        run_boundary_loop(ledger, generations=1, schedule={})

    baseline_mean = (
        float(sum(pre_yields) / len(pre_yields)) if pre_yields else 0.0
    )

    # Checkpoint event (distinct from ablate / scaffold cut).
    ckpt_result = ledger.relocate_recovery_token(
        RECOVERY_TOKEN_KEY, remove=False, new_payload="relocated_scored"
    )
    cell_result = _apply_ops_cell(ledger, ops_cell)

    post_yields: list[float] = []
    recovery_progress = 0.0
    scaffold_key = f"scaffold_edges:{SCAFFOLD_ID}"
    members = ledger.scaffold_edge_sets.get(scaffold_key, set())
    scaffold_ok = bool(members) and all(
        eid in ledger.edges and ledger.edges[eid].present for eid in members
    )
    for _ in range(t_hor):
        if ledger.failed_prediction_digests and RECOVERY_TOKEN_KEY in ledger.recovery_tokens:
            recovery_progress += (0.06 + 0.04 * knowledge_capital) * (
                1.0 if scaffold_ok else 0.35
            )
        elif ledger.failed_prediction_digests:
            recovery_progress += 0.015 * (1.0 + knowledge_capital)
        post_yields.append(
            float(harvest_rare_class_yield(ledger) * (1.0 + recovery_progress))
        )
        run_boundary_loop(ledger, generations=1, schedule={})

    recover = _score_recover(baseline_mean=baseline_mean, post_yields=post_yields)
    tt = t_tilde_of(t_int, t_horizon=t_hor)

    return {
        "schema": "discovery_q_20260928_idea4_scored_cell_v1",
        "idea_id": 4,
        "seed": int(seed),
        "run_id": f"idea4-s{int(seed)}-{ops_cell}-t{t_int}",
        "ops_cell": str(ops_cell),
        "t_intervene": t_int,
        "T_horizon": t_hor,
        "t_tilde": float(tt),
        "recover": bool(recover),
        "baseline_mean_rare_yield": float(baseline_mean),
        "post_rare_yield_tail": [float(y) for y in post_yields[-5:]],
        "n_post_obs": len(post_yields),
        "competence_id": COMPETENCE_ID,
        "checkpoint_id": CHECKPOINT_ID,
        "scaffold_id": SCAFFOLD_ID,
        "slope_threshold": SLOPE_THRESHOLD,
        "delta_p_threshold": DELTA_P_THRESHOLD,
        "claim_ceiling": CLAIM_CEILING,
        "hypothesis_supported": False,
        "red_queen_proved": False,
        "honesty": (
            "Scored Idea4 cell under phase2_design. "
            "Not sealed recovery-window evidence; hypothesis_supported stays false "
            "until Critic post-data seal. Volume ≠ discovery."
        ),
        "checkpoint_after": ckpt_result.get("after"),
        "cell_result_op": cell_result.get("op"),
        "knowledge_capital": float(knowledge_capital),
        "n_unit": "run",
    }


def idea4_scored_constants() -> Mapping[str, Any]:
    return {
        **idea4_constants(),
        "t_intervene_grid": list(T_INTERVENE_GRID),
        "ops_cells": list(OPS_CELLS),
        "t_tilde_grid": [t_tilde_of(t) for t in T_INTERVENE_GRID],
        "hypothesis_supported": False,
    }
