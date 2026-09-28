"""Discovery questions 2026-09-28 — Idea 2 phase-2 harness smoke.

Gene / pattern / causal competition under coevolving antagonist pressure
on the contact/ATP ledger (sealed phase-2 design digest). Harness only:
ledger do-ops + SHAM-CUE-PREDPHASE-V1 wiring. Full campaigns are not
authorised by this smoke pack. Claim ceiling: phase2_harness.
red_queen_proved stays False.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from typing import Any

from codontrace._types import JsonValue
from codontrace.errors import ConfigurationError
from codontrace.genesis.canonical import canonical_digest
from codontrace.life_loop.contact_atp_ledger import (
    NAMED_CONTACT_EDGE_IDS,
    SHAM_CUE_PREDPHASE,
    ContactAtpLedger,
    build_idea2_smoke_ledger,
)
from codontrace.life_loop.discovery_boundary_hooks import make_op, run_boundary_loop

SCHEMA = "discovery_q_20260928_idea2_harness_v1"
CLAIM_CEILING = "phase2_harness"
NAMED_CONTACT_SET = tuple(sorted(NAMED_CONTACT_EDGE_IDS))
DECISION_BUDGET = 1.0
CAUSAL_SPEND = (0.5, 0.5)  # revision + one do
DECEPTION_PHASE = math.pi
SHAM_ID = "SHAM-CUE-PREDPHASE-V1"
# Execution prereg κ (not a design-freeze invent): locked for smoke runs.
KAPPA_SMOKE = 1.0
CHANNEL_MARGIN = 0.15
CLAIMGATE_REFUSES = (
    "red_queen_proved",
    "discovery_claim",
    "first_claim",
)
ARMS = ("gene", "pattern", "causal")


def require_kappa(kappa: float | None) -> float:
    """κ must be required/non-empty before run (execution prereg lock)."""

    if kappa is None:
        raise ConfigurationError(
            "kappa is required before Idea2 execution; empty kappa reopens "
            "execution preregistration."
        )
    value = float(kappa)
    if not math.isfinite(value) or value <= 0.0:
        raise ConfigurationError("kappa must be a finite float > 0.")
    return value


def run_idea2_smoke(
    *,
    seed: int = 42,
    generations: int = 4,
    kappa: float | None = KAPPA_SMOKE,
    arms: Sequence[str] | None = None,
) -> dict[str, JsonValue]:
    """Deterministic Idea2 harness smoke — not a discovery campaign run."""

    k = require_kappa(kappa)
    use_arms = tuple(arms) if arms is not None else ARMS
    for arm in use_arms:
        if arm not in ARMS:
            raise ConfigurationError(f"unknown arm {arm!r}.")

    ledger = build_idea2_smoke_ledger(seed=int(seed))
    ledger.realised_pressure_phase = 0.25
    ledger.predicted_pressure_phase = float(ledger.realised_pressure_phase) + DECEPTION_PHASE

    # Three do ops only at generation boundary; sham ≠ mask_named_contacts.
    do_edge = "NC-H0-A0"
    schedule = {
        0: [make_op("mask_named_contacts", edge_ids=[do_edge], one_generation=True)],
        1: [
            make_op(
                "reallocate_contact_budget",
                class_blind=True,
                zero_sum=True,
                one_generation=True,
                budget=DECISION_BUDGET,
            )
        ],
        2: [make_op("cut_or_restore_named_contact_edge", edge_id="NC-H1-A0", restore=False)],
        3: [make_op("sham_cue_predphase", offset=DECEPTION_PHASE)],
    }
    history = run_boundary_loop(ledger, generations=int(generations), schedule=schedule)

    # Sham must leave NC-* presence/mask state intact relative to cuts already applied.
    # After gen0 mask (one-gen, cleared on advance) and gen2 cut of NC-H1-A0:
    nc_presence = {
        eid: (ledger.edges[eid].present if eid in ledger.edges else False)
        for eid in NAMED_CONTACT_SET
    }
    nc_masked = {
        eid: (ledger.edges[eid].masked if eid in ledger.edges else False)
        for eid in NAMED_CONTACT_SET
    }
    # Sham ran at gen 3; one-generation masks from gen0 already cleared.
    sham_ok = (
        SHAM_ID == SHAM_CUE_PREDPHASE
        and abs(
            float(ledger.predicted_pressure_phase)
            - (float(ledger.realised_pressure_phase) + DECEPTION_PHASE)
        )
        < 1e-12
        and nc_presence.get("NC-H1-A0") is False
        and all(nc_masked.get(eid) is False for eid in NAMED_CONTACT_SET)
    )

    arm_pack: dict[str, JsonValue] = {}
    for arm in use_arms:
        if arm == "gene":
            spend = {"decision_units": DECISION_BUDGET, "genotype_update": True, "do": False}
        elif arm == "pattern":
            spend = {
                "decision_units": DECISION_BUDGET,
                "correlational_memory_update": True,
                "do": False,
            }
        else:
            spend = {
                "decision_units": DECISION_BUDGET,
                "hypothesis_revision": CAUSAL_SPEND[0],
                "do": CAUSAL_SPEND[1],
                "do_ops": [
                    "mask_named_contacts",
                    "reallocate_contact_budget",
                    "cut_or_restore_named_contact_edge",
                ],
                "sham_control": SHAM_ID,
            }
        arm_pack[arm] = {
            "budget": DECISION_BUDGET,
            "kappa": k,
            "atp_debit": float(DECISION_BUDGET) * float(k),
            "spend": spend,
        }

    engineering_green = bool(
        history
        and sham_ok
        and set(NAMED_CONTACT_SET) == set(NAMED_CONTACT_EDGE_IDS)
        and k == KAPPA_SMOKE
    )

    pack: dict[str, JsonValue] = {
        "schema": SCHEMA,
        "claim_ceiling": CLAIM_CEILING,
        "named_contact_edge_ids": list(NAMED_CONTACT_SET),
        "decision_budget": DECISION_BUDGET,
        "causal_spend": list(CAUSAL_SPEND),
        "deception_phase": DECEPTION_PHASE,
        "kappa": k,
        "kappa_note": (
            "kappa=1.0 locked as execution prereg for harness smoke; "
            "not a design-freeze invent."
        ),
        "sham_id": SHAM_ID,
        "channel_margin": CHANNEL_MARGIN,
        "arms": arm_pack,
        "engineering_green": engineering_green,
        "hypothesis_supported": False,
        "red_queen_proved": False,
        "claimgate_refuses": list(CLAIMGATE_REFUSES),
        "honesty": (
            "Harness smoke only under sealed phase-2 design digest. "
            "No discovery claim. Full campaigns remain off until owner allows."
        ),
        "ledger_digest": ledger.digest(),
        "history_len": len(history),
        "nc_presence": nc_presence,
        "nc_masked": nc_masked,
        "predicted_pressure_phase": float(ledger.predicted_pressure_phase),
        "realised_pressure_phase": float(ledger.realised_pressure_phase),
        "distinction_locks": {
            "sham_is_predphase_only": sham_ok,
            "sham_id": SHAM_ID,
            "named_contact_is_edge_id": True,
            "kappa_required": True,
        },
    }
    pack["pack_digest"] = canonical_digest(
        {k_: v for k_, v in pack.items() if k_ != "pack_digest"},
        prefix="idea2_smoke",
    )
    return pack


def idea2_constants() -> Mapping[str, Any]:
    return {
        "named_contact_edge_ids": list(NAMED_CONTACT_SET),
        "decision_budget": DECISION_BUDGET,
        "causal_spend": list(CAUSAL_SPEND),
        "deception_phase": DECEPTION_PHASE,
        "kappa_smoke": KAPPA_SMOKE,
        "sham_id": SHAM_ID,
        "claim_ceiling": CLAIM_CEILING,
        "red_queen_proved": False,
        "channel_margin": CHANNEL_MARGIN,
    }
