"""Discovery questions 2026-09-28 — Idea 3 phase-2 harness smoke.

Collective causal knowledge via package transmission vs pooling / imitation,
with cut_failed_and_bounds and L-unreachability on the contact/ATP ledger
(sealed phase-2 design digest). Harness only. Full campaigns are not
authorised by this smoke pack. Claim ceiling: phase2_design.
red_queen_proved stays False.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from codontrace._types import JsonValue
from codontrace.errors import ConfigurationError
from codontrace.genesis.canonical import canonical_digest
from codontrace.life_loop.contact_atp_ledger import (
    LAW_CONTACT_ATP_PARENT,
    PKG_REASON_FAIL_BOUND,
    UNREACH_L_SINGLE_LIFETIME,
    build_idea3_smoke_ledger,
)
from codontrace.life_loop.discovery_boundary_hooks import make_op, run_boundary_loop

SCHEMA = "discovery_q_20260928_idea3_harness_v1"
CLAIM_CEILING = "phase2_design"
LAW_ID = LAW_CONTACT_ATP_PARENT
UNREACH_ID = UNREACH_L_SINGLE_LIFETIME
PACKAGE_SCHEMA_ID = PKG_REASON_FAIL_BOUND
DISCOVERY_MARGIN = 0.15
OPS = (
    "transmit_package",
    "pool_raw_only",
    "imitate_success_only",
    "cut_failed_and_bounds",
)
CLAIMGATE_REFUSES = (
    "red_queen_proved",
    "discovery_claim",
    "first_claim",
    "soft_pass",
)


def _require_nonempty(value: str, name: str) -> str:
    text = str(value).strip()
    if not text:
        raise ConfigurationError(f"empty {name} reopens Idea3 freeze.")
    return text


def run_idea3_smoke(
    *,
    seed: int = 42,
    generations: int = 4,
) -> dict[str, JsonValue]:
    """Deterministic Idea3 harness smoke — not a discovery campaign run."""

    ledger = build_idea3_smoke_ledger(seed=int(seed))
    law = _require_nonempty(ledger.law_id, "law_id")
    unreach = _require_nonempty(ledger.unreach_id, "unreach_id")
    if law != LAW_ID:
        raise ConfigurationError(f"law_id must be {LAW_ID!r}.")
    if unreach != UNREACH_ID:
        raise ConfigurationError(f"unreach_id must be {UNREACH_ID!r}.")

    schedule = {
        0: [
            make_op(
                "transmit_package",
                package_id="pkg-smoke-1",
                interventional_claim="intervene_on_E0_raises_rare_atp",
                failed_intervention="intervene_on_E2_no_effect",
                validity_bounds="horizon_L_lt_single_lifetime_sample",
            )
        ],
        1: [
            make_op(
                "pool_raw_only",
                pool_key="pool-smoke",
                observations={"n": 3, "mean_atp": 0.6},
            )
        ],
        2: [make_op("imitate_success_only", act_id="act-high-payoff", payoff=1.2)],
        3: [make_op("cut_failed_and_bounds", package_id="pkg-smoke-1")],
    }
    history = run_boundary_loop(ledger, generations=int(generations), schedule=schedule)

    cut_ok = bool(ledger.package_cut_applied) and "pkg-smoke-1" in ledger.causal_packages
    pkg = ledger.causal_packages.get("pkg-smoke-1", {})
    cut_emptied_fields = (
        pkg.get("failed_intervention") == "" and pkg.get("validity_bounds") == ""
    )
    unreach_in_every_run = bool(unreach)  # criterion identity present in this run pack
    ids_nonempty = bool(law) and bool(unreach) and all(bool(op) for op in OPS)
    engineering_green = bool(
        history
        and cut_ok
        and cut_emptied_fields
        and bool(ledger.raw_pool)
        and bool(ledger.imitation_buffer)
        and unreach_in_every_run
        and ids_nonempty
    )
    freeze_reopen = not ids_nonempty or not cut_ok

    pack: dict[str, JsonValue] = {
        "schema": SCHEMA,
        "claim_ceiling": CLAIM_CEILING,
        "law_id": law,
        "unreach_id": unreach,
        "package_schema_id": PACKAGE_SCHEMA_ID,
        "ops": list(OPS),
        "discovery_margin": DISCOVERY_MARGIN,
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
            "cut_failed_and_bounds and unreachability criterion required every run."
        ),
        "ledger_digest": ledger.digest(),
        "history_len": len(history),
        "package_cut_applied": bool(ledger.package_cut_applied),
        "raw_pool_keys": sorted(ledger.raw_pool),
        "imitation_buffer_len": len(ledger.imitation_buffer),
        "distinction_locks": {
            "cut_failed_and_bounds_required": cut_ok,
            "unreachability_criterion_in_run": unreach_in_every_run,
            "pooling_without_reasons": True,
            "imitation_without_negatives": True,
            "identity_ids_nonempty": ids_nonempty,
            "empty_cut_reopens": True,
        },
    }
    pack["pack_digest"] = canonical_digest(
        {k: v for k, v in pack.items() if k != "pack_digest"},
        prefix="idea3_smoke",
    )
    return pack


def idea3_constants() -> Mapping[str, Any]:
    return {
        "law_id": LAW_ID,
        "unreach_id": UNREACH_ID,
        "package_schema_id": PACKAGE_SCHEMA_ID,
        "ops": list(OPS),
        "discovery_margin": DISCOVERY_MARGIN,
        "claim_ceiling": CLAIM_CEILING,
        "hypothesis_supported": False,
        "red_queen_proved": False,
        "n_unit": "run",
    }
