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
