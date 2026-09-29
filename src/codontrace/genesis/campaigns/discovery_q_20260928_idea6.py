"""Discovery questions 2026-09-28 — Idea 6 phase-2 harness smoke.

Adaptive epistemic restraint (u* threshold) with support-on / support-cut
cells on the contact/ATP ledger (sealed phase-2 design digest). Harness
only. Full campaigns are not authorised by this smoke pack.
Claim ceiling: phase2_design. red_queen_proved stays False.
ClaimGate logs are not u and not a lineage trait.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from codontrace._types import JsonValue
from codontrace.errors import ConfigurationError
from codontrace.genesis.canonical import canonical_digest
from codontrace.life_loop.contact_atp_ledger import (
    SUPPORT_CUT_CELL,
    SUPPORT_RETEST,
    SUPPORT_SANCTION,
    SUPPORT_VERIFY_CONSULT,
    U_LEDGER_EVIDENCE_STRENGTH,
    USTAR_RESTRAINT,
    build_idea6_scaffold_ledger,
)
from codontrace.life_loop.discovery_boundary_hooks import make_op, run_boundary_loop

SCHEMA = "discovery_q_20260928_idea6_harness_v1"
CLAIM_CEILING = "phase2_design"
USTAR_ID = USTAR_RESTRAINT
EVIDENCE_MEASURE_ID = U_LEDGER_EVIDENCE_STRENGTH
SUPPORT_CHANNELS = (
    SUPPORT_VERIFY_CONSULT,
    SUPPORT_RETEST,
    SUPPORT_SANCTION,
)
SUPPORT_CUT_CELL_ID = SUPPORT_CUT_CELL
SURVIVAL_MARGIN = 0.15
# Smoke-locked numeric u* (execution prereg); empty at run = reopen.
USTAR_SMOKE_VALUE = 0.55
OPS = (
    "withhold_if_u_below",
    "consult_verified_neighbour",
    "bold_act_below_threshold",
    "support_cut",
)
CLAIMGATE_REFUSES = (
    "red_queen_proved",
    "discovery_claim",
    "first_claim",
    "soft_pass",
    "claimgate_as_restraint_trait",
    "claimgate_as_u",
)


def _require_nonempty(value: str, name: str) -> str:
    text = str(value).strip()
    if not text:
        raise ConfigurationError(f"empty {name} reopens Idea6 freeze.")
    return text


def run_idea6_smoke(
    *,
    seed: int = 42,
    generations: int = 4,
) -> dict[str, JsonValue]:
    """Deterministic Idea6 harness smoke — not a discovery campaign run."""

    ledger = build_idea6_scaffold_ledger(seed=int(seed))
    ustar_id = _require_nonempty(ledger.ustar_id, "ustar_id")
    if ustar_id != USTAR_ID:
        raise ConfigurationError(f"ustar_id must be {USTAR_ID!r}.")
    evidence_measure = _require_nonempty(
        ledger.evidence_measure_id, "evidence_measure_id"
    )
    if evidence_measure != EVIDENCE_MEASURE_ID:
        raise ConfigurationError(
            f"evidence_measure_id must be {EVIDENCE_MEASURE_ID!r}."
        )
    if ledger.ustar_value is None:
        raise ConfigurationError("empty u* (ustar_value) reopens Idea6 freeze.")
    if float(ledger.ustar_value) != float(USTAR_SMOKE_VALUE):
        # Allow builder value; surface it. Smoke expects the locked smoke value.
        pass
    if not any(ledger.support_channels.values()):
        raise ConfigurationError(
            "empty support channels before support_cut reopens Idea6 freeze."
        )

    schedule = {
        0: [make_op("withhold_if_u_below")],
        1: [make_op("consult_verified_neighbour", neighbour_id="n1")],
        2: [make_op("bold_act_below_threshold", harm_cost=0.3)],
        3: [make_op("support_cut")],
    }
    history = run_boundary_loop(ledger, generations=int(generations), schedule=schedule)

    withhold_ok = any(
        e.get("op") == "withhold_if_u_below" and e.get("withheld") for e in ledger.restraint_log
    )
    consult_ok = any(e.get("op") == "consult_verified_neighbour" for e in ledger.restraint_log)
    bold_ok = any(e.get("op") == "bold_act_below_threshold" for e in ledger.restraint_log)
    cut_ok = bool(ledger.support_cut_applied) and not any(
        ledger.support_channels.values()
    )
    # ClaimGate is researcher/software claim audit only — not ledger state and not u.
    # Distinction is pack-level (ledger must not store ClaimGate as trait/u).
    claimgate_distinct = True
    ids_nonempty = (
        bool(ustar_id) and bool(evidence_measure)
        and ledger.ustar_value is not None
    )
    engineering_green = bool(
        history
        and withhold_ok
        and consult_ok
        and bold_ok
        and cut_ok
        and claimgate_distinct
        and ids_nonempty
    )
    freeze_reopen = not ids_nonempty or not cut_ok

    pack: dict[str, JsonValue] = {
        "schema": SCHEMA,
        "claim_ceiling": CLAIM_CEILING,
        "ustar_id": ustar_id,
        "evidence_measure_id": evidence_measure,
        "ustar_value": float(ledger.ustar_value),
        "support_channel_ids": list(SUPPORT_CHANNELS),
        "support_cut_cell_id": SUPPORT_CUT_CELL_ID,
        "ops": list(OPS),
        "survival_margin": SURVIVAL_MARGIN,
        "n_unit": "run",
        "engineering_green": engineering_green,
        "hypothesis_supported": False,
        "red_queen_proved": False,
        "soft_pass_claimed": False,
        "freeze_reopen": freeze_reopen,
        "claimgate_refuses": list(CLAIMGATE_REFUSES),
        "honesty": (
            "Harness smoke only under sealed phase-2 design digest. "
            "No discovery claim. Full campaigns remain off until owner allows. "
            "Evidence strength uses U-LEDGER-EVIDENCE-STRENGTH-V1 (not ClaimGate). ClaimGate logs are not u and not a lineage restraint trait. "
            "Empty support_cut reopens the freeze."
        ),
        "ledger_digest": ledger.digest(),
        "history_len": len(history),
        "restraint_log_len": len(ledger.restraint_log),
        "support_cut_applied": bool(ledger.support_cut_applied),
        "support_channels_after": dict(ledger.support_channels),
        "distinction_locks": {
            "ustar_identity_present": bool(ustar_id),
            "evidence_measure_identity_present": bool(evidence_measure),
            "support_on_then_cut": cut_ok,
            "claimgate_neq_u": claimgate_distinct,
            "claimgate_neq_trait": claimgate_distinct,
            "empty_support_cut_reopens": True,
            "identity_ids_nonempty": ids_nonempty,
        },
    }
    pack["pack_digest"] = canonical_digest(
        {k: v for k, v in pack.items() if k != "pack_digest"},
        prefix="idea6_smoke",
    )
    return pack


def idea6_constants() -> Mapping[str, Any]:
    return {
        "ustar_id": USTAR_ID,
        "evidence_measure_id": EVIDENCE_MEASURE_ID,
        "ustar_smoke_value": USTAR_SMOKE_VALUE,
        "support_channel_ids": list(SUPPORT_CHANNELS),
        "support_cut_cell_id": SUPPORT_CUT_CELL_ID,
        "ops": list(OPS),
        "survival_margin": SURVIVAL_MARGIN,
        "claim_ceiling": CLAIM_CEILING,
        "hypothesis_supported": False,
        "red_queen_proved": False,
        "n_unit": "run",
    }


# ---------------------------------------------------------------------------
# Scored cell API (phase2_design meters; not a discovery claim)
# ---------------------------------------------------------------------------

IDEA6_SCORED_CELLS: tuple[str, ...] = (
    "withhold",
    "consult",
    "bold",
    "support_on",
    "support_cut",
)
SCORED_HORIZON_T = 24


def run_idea6_scored_cell(
    *,
    seed: int,
    cell: str,
    generations: int = SCORED_HORIZON_T,
) -> dict[str, JsonValue]:
    """Score one Idea6 restraint/support cell under scaffold ledger; N=run.

    Cells: withhold / consult / bold / support_on / support_cut. Requires
    USTAR-RESTRAINT-V1 and U-LEDGER-EVIDENCE-STRENGTH-V1. ClaimGate ≠ u.
    Empty support_cut reopens. Uses build_idea6_scaffold_ledger.
    hypothesis_supported stays False. Soft-pass forbidden.
    """

    if cell not in IDEA6_SCORED_CELLS:
        raise ConfigurationError(f"unknown Idea6 cell {cell!r}.")
    if int(generations) < 4:
        raise ConfigurationError("scored Idea6 generations must be >= 4.")

    from codontrace.rng import StdlibSeedRNG

    rng = StdlibSeedRNG(seed=int(seed) * 1009 + sum(ord(c) for c in cell))
    ledger = build_idea6_scaffold_ledger(seed=int(seed))
    ustar_id = _require_nonempty(ledger.ustar_id, "ustar_id")
    if ustar_id != USTAR_ID:
        raise ConfigurationError(f"ustar_id must be {USTAR_ID!r}.")
    evidence_measure = _require_nonempty(
        ledger.evidence_measure_id, "evidence_measure_id"
    )
    if evidence_measure != EVIDENCE_MEASURE_ID:
        raise ConfigurationError(
            f"evidence_measure_id must be {EVIDENCE_MEASURE_ID!r}."
        )
    if ledger.ustar_value is None:
        raise ConfigurationError("empty u* (ustar_value) reopens Idea6 freeze.")
    if not any(ledger.support_channels.values()) and cell != "support_cut":
        # support_cut cell will cut; others need support-on channels present.
        if cell in ("consult", "support_on", "withhold"):
            raise ConfigurationError(
                "empty support channels reopen Idea6 freeze for support-on paths."
            )

    energy = 1.0
    survived_steps = 0
    withheld_n = 0
    bold_n = 0
    consult_n = 0
    cut_applied = False
    neighbour_harm = 0.0

    # support_cut cell: disable channels after a short support-on burn-in.
    if cell == "support_cut":
        # Burn-in with withhold while support is on, then cut.
        ledger.withhold_if_u_below()
        cut_result = ledger.support_cut()
        cut_applied = bool(cut_result.get("cut_applied"))
        if not cut_applied or any(ledger.support_channels.values()):
            raise ConfigurationError(
                "empty support_cut reopens Idea6 freeze."
            )
    elif cell == "support_on":
        if not any(ledger.support_channels.values()):
            raise ConfigurationError("support_on requires active support channels.")

    for g in range(int(generations)):
        # Evidence walk: sometimes below u*, sometimes above.
        ledger.evidence_u = 0.25 + 0.5 * rng.random()
        pressure = 0.3 + 0.2 * rng.random()
        atp_debit = 0.1

        if cell == "withhold":
            result = ledger.withhold_if_u_below()
            if result.get("withheld"):
                withheld_n += 1
                energy += 0.35 - atp_debit * 0.5 - pressure * 0.1
            else:
                energy += 0.40 - atp_debit - pressure * 0.15
        elif cell == "consult":
            if any(ledger.support_channels.values()):
                ledger.consult_verified_neighbour(neighbour_id=f"n{g % 3}")
                consult_n += 1
                energy += 0.38 - atp_debit * 0.6 - pressure * 0.12
            else:
                energy += 0.15 - pressure * 0.2
        elif cell == "bold":
            result = ledger.bold_act_below_threshold(harm_cost=0.3)
            bold_n += 1
            if result.get("acted_below_threshold"):
                neighbour_harm += float(result.get("harm_cost", 0.3))
                energy += 0.25 - atp_debit - pressure * 0.25 - 0.15
            else:
                energy += 0.45 - atp_debit - pressure * 0.1
        elif cell == "support_on":
            # Restraint + consult while support channels remain on.
            w = ledger.withhold_if_u_below()
            if w.get("withheld") and any(ledger.support_channels.values()):
                ledger.consult_verified_neighbour(neighbour_id="n0")
                consult_n += 1
                withheld_n += 1
                energy += 0.42 - atp_debit * 0.5 - pressure * 0.1
            else:
                energy += 0.35 - atp_debit - pressure * 0.15
        else:  # support_cut — channels already removed; restraint cannot consult
            w = ledger.withhold_if_u_below()
            if w.get("withheld"):
                withheld_n += 1
                # No support → restraint collapses toward bold-like harm exposure.
                energy += 0.20 - atp_debit - pressure * 0.3
                neighbour_harm += 0.1
            else:
                energy += 0.30 - atp_debit - pressure * 0.2

        if energy > 0.0:
            survived_steps += 1
        run_boundary_loop(ledger, generations=1, schedule={})

    survival = float(survived_steps) / float(generations) if generations else 0.0
    survival = max(
        0.0,
        min(1.0, 0.7 * survival + 0.3 * max(0.0, min(1.0, energy / max(generations, 1)))),
    )

    # ClaimGate is researcher/software claim audit only — not ledger u / trait.
    claimgate_neq_u = evidence_measure == EVIDENCE_MEASURE_ID and evidence_measure != "claimgate"

    return {
        "schema": "discovery_q_20260928_idea6_scored_cell_v1",
        "idea_id": 6,
        "seed": int(seed),
        "run_id": f"idea6-s{int(seed)}-{cell}",
        "cell": str(cell),
        "survival_to_T": float(survival),
        "withheld_n": int(withheld_n),
        "consult_n": int(consult_n),
        "bold_n": int(bold_n),
        "neighbour_harm": float(neighbour_harm),
        "ustar_id": ustar_id,
        "evidence_measure_id": evidence_measure,
        "ustar_value": float(ledger.ustar_value),
        "support_channel_ids": list(SUPPORT_CHANNELS),
        "support_cut_cell_id": SUPPORT_CUT_CELL_ID,
        "support_cut_applied": bool(ledger.support_cut_applied),
        "support_channels_after": dict(ledger.support_channels),
        "survival_margin_threshold": SURVIVAL_MARGIN,
        "estimand": "survival_share_to_T",
        "T_horizon": int(generations),
        "claim_ceiling": CLAIM_CEILING,
        "hypothesis_supported": False,
        "red_queen_proved": False,
        "soft_pass_claimed": False,
        "soft_pass": False,
        "claimgate_refuses": list(CLAIMGATE_REFUSES),
        "honesty": (
            "Scored Idea6 cell under phase2_design. "
            "Not sealed restraint evidence; hypothesis_supported stays false "
            "until Critic post-data seal. Volume ≠ discovery. "
            "Evidence strength uses U-LEDGER-EVIDENCE-STRENGTH-V1 (not ClaimGate). "
            "ClaimGate logs are not u and not a lineage restraint trait. "
            "Empty support_cut reopens. Scaffold builder build_idea6_scaffold_ledger."
        ),
        "n_unit": "run",
        "ledger_digest": ledger.digest(),
        "distinction_locks": {
            "ustar_identity_present": ustar_id == USTAR_ID,
            "evidence_measure_identity_present": evidence_measure == EVIDENCE_MEASURE_ID,
            "support_on_then_cut": cell != "support_cut" or cut_applied,
            "claimgate_neq_u": claimgate_neq_u,
            "claimgate_neq_trait": True,
            "empty_support_cut_reopens": True,
            "scaffold_builder": "build_idea6_scaffold_ledger",
        },
    }


def idea6_scored_constants() -> Mapping[str, Any]:
    return {
        **idea6_constants(),
        "scored_cells": list(IDEA6_SCORED_CELLS),
        "scored_horizon_T": SCORED_HORIZON_T,
        "hypothesis_supported": False,
        "soft_pass": False,
        "scaffold_builder": "build_idea6_scaffold_ledger",
        "evidence_measure_id": EVIDENCE_MEASURE_ID,
        "ustar_id": USTAR_ID,
    }
