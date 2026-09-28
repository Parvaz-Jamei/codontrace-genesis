"""Discovery questions 2026-09-28 — Idea 4 phase-2 harness smoke.

Branching-history recovery window under sealed phase-2 design digest.
Harness only: ledger ops + generation-boundary observer wiring.
Full T=40 campaigns are not authorised by this smoke pack.
Claim ceiling: phase2_harness. red_queen_proved stays False.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from codontrace._types import JsonValue
from codontrace.genesis.canonical import canonical_digest
from codontrace.life_loop.contact_atp_ledger import (
    CHECKPOINT_RELOCATE_RECOVERY,
    CONTACT_TAG_RARE,
    ContactAtpLedger,
    build_smoke_ledger,
)
from codontrace.life_loop.discovery_boundary_hooks import make_op, run_boundary_loop

SCHEMA = "discovery_q_20260928_idea4_harness_v1"
CLAIM_CEILING = "phase2_harness"
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
