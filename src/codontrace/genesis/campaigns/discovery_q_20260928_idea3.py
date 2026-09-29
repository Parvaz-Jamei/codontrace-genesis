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
    REV_HIGH_NOISE_BLIND_ACCEPT,
    UNREACH_L_SINGLE_LIFETIME,
    build_idea3_scaffold_ledger,
)
from codontrace.life_loop.discovery_boundary_hooks import make_op, run_boundary_loop

SCHEMA = "discovery_q_20260928_idea3_harness_v1"
CLAIM_CEILING = "phase2_design"
LAW_ID = LAW_CONTACT_ATP_PARENT
UNREACH_ID = UNREACH_L_SINGLE_LIFETIME
PACKAGE_SCHEMA_ID = PKG_REASON_FAIL_BOUND
REVERSAL_CELL_ID = REV_HIGH_NOISE_BLIND_ACCEPT
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

    ledger = build_idea3_scaffold_ledger(seed=int(seed))
    law = _require_nonempty(ledger.law_id, "law_id")
    unreach = _require_nonempty(ledger.unreach_id, "unreach_id")
    if law != LAW_ID:
        raise ConfigurationError(f"law_id must be {LAW_ID!r}.")
    if unreach != UNREACH_ID:
        raise ConfigurationError(f"unreach_id must be {UNREACH_ID!r}.")
    reversal = _require_nonempty(ledger.reversal_cell_id, "reversal_cell_id")
    if reversal != REVERSAL_CELL_ID:
        raise ConfigurationError(f"reversal_cell_id must be {REVERSAL_CELL_ID!r}.")

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
    ids_nonempty = (
        bool(law) and bool(unreach) and bool(reversal)
        and all(bool(op) for op in OPS)
    )
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
        "reversal_cell_id": reversal,
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
            "cut_failed_and_bounds, unreachability criterion, and REV-HIGH-NOISE-BLIND-ACCEPT-V1 required every run."
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
            "reversal_cell_identity_present": bool(reversal),
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
        "reversal_cell_id": REVERSAL_CELL_ID,
        "ops": list(OPS),
        "discovery_margin": DISCOVERY_MARGIN,
        "claim_ceiling": CLAIM_CEILING,
        "hypothesis_supported": False,
        "red_queen_proved": False,
        "n_unit": "run",
    }


# ---------------------------------------------------------------------------
# Scored cell API (phase2_design meters; not a discovery claim)
# ---------------------------------------------------------------------------

IDEA3_SCORED_CELLS: tuple[str, ...] = (
    "transmit",
    "pool",
    "imitate",
    "cut",
    "reversal",
)
SCORED_HORIZON_T = 24


def run_idea3_scored_cell(
    *,
    seed: int,
    cell: str,
    generations: int = SCORED_HORIZON_T,
) -> dict[str, JsonValue]:
    """Score one Idea3 transmission/control cell under scaffold ledger; N=run.

    Cells: transmit / pool / imitate / cut / reversal. Unreachability and
    REV-HIGH-NOISE-BLIND-ACCEPT-V1 identities required every run. Empty cut
    reopens the freeze. Uses build_idea3_scaffold_ledger (not smoke alias).
    hypothesis_supported stays False. Soft-pass forbidden.
    """

    if cell not in IDEA3_SCORED_CELLS:
        raise ConfigurationError(f"unknown Idea3 cell {cell!r}.")
    if int(generations) < 4:
        raise ConfigurationError("scored Idea3 generations must be >= 4.")

    from codontrace.rng import StdlibSeedRNG

    rng = StdlibSeedRNG(seed=int(seed) * 1009 + sum(ord(c) for c in cell))
    ledger = build_idea3_scaffold_ledger(seed=int(seed))
    law = _require_nonempty(ledger.law_id, "law_id")
    unreach = _require_nonempty(ledger.unreach_id, "unreach_id")
    reversal = _require_nonempty(ledger.reversal_cell_id, "reversal_cell_id")
    if law != LAW_ID:
        raise ConfigurationError(f"law_id must be {LAW_ID!r}.")
    if unreach != UNREACH_ID:
        raise ConfigurationError(f"unreach_id must be {UNREACH_ID!r}.")
    if reversal != REVERSAL_CELL_ID:
        raise ConfigurationError(f"reversal_cell_id must be {REVERSAL_CELL_ID!r}.")

    discovered = False
    cut_applied = False
    package_id = f"pkg-s{int(seed)}"

    if cell == "transmit":
        ledger.transmit_package(
            package_id=package_id,
            interventional_claim="intervene_on_E0_raises_rare_atp",
            failed_intervention="intervene_on_E2_no_effect",
            validity_bounds="horizon_L_lt_single_lifetime_sample",
        )
    elif cell == "pool":
        ledger.pool_raw_only(
            pool_key=f"pool-s{int(seed)}",
            observations={"n": 4, "mean_atp": 0.55 + 0.1 * rng.random()},
        )
    elif cell == "imitate":
        ledger.imitate_success_only(act_id="act-high-payoff", payoff=1.0 + 0.3 * rng.random())
    elif cell == "cut":
        ledger.transmit_package(
            package_id=package_id,
            interventional_claim="intervene_on_E0_raises_rare_atp",
            failed_intervention="intervene_on_E2_no_effect",
            validity_bounds="horizon_L_lt_single_lifetime_sample",
        )
        cut_result = ledger.cut_failed_and_bounds(package_id=package_id)
        cut_applied = bool(cut_result.get("cut_applied"))
        pkg = ledger.causal_packages[package_id]
        if pkg.get("failed_intervention") != "" or pkg.get("validity_bounds") != "":
            raise ConfigurationError("cut must empty failed_intervention and validity_bounds.")
        if not cut_applied:
            raise ConfigurationError("empty cut reopens Idea3 freeze.")
    else:  # reversal — high-noise blind-accept regime
        # Transmit with revision disabled; elevated noise on claim fidelity.
        ledger.transmit_package(
            package_id=package_id,
            interventional_claim="noisy_blind_accept_claim",
            failed_intervention="stripped_by_noise",
            validity_bounds="bounds_ignored",
            revision_rule="blind_accept",
        )
        # Noise: corrupt package claim fidelity without removing identity IDs.
        pkg = dict(ledger.causal_packages[package_id])
        pkg["noise"] = 0.85 + 0.1 * rng.random()
        pkg["blind_accept"] = True
        pkg["reversal_cell_id"] = reversal
        ledger.causal_packages[package_id] = pkg

    discovery_score = 0.0
    for _g in range(int(generations)):
        # Lifetime-alone cannot clear unreachability; package fields help transmit.
        if cell == "transmit" and package_id in ledger.causal_packages:
            pkg = ledger.causal_packages[package_id]
            has_fail = bool(pkg.get("failed_intervention"))
            has_bounds = bool(pkg.get("validity_bounds"))
            discovery_score += 0.06 if (has_fail and has_bounds) else 0.01
        elif cell == "pool":
            discovery_score += 0.02 + 0.01 * len(ledger.raw_pool)
        elif cell == "imitate":
            discovery_score += 0.025 * max(1, len(ledger.imitation_buffer))
        elif cell == "cut":
            # Cut removes H2 margin pathway — score stays low.
            discovery_score += 0.015
        else:  # reversal underperforms
            discovery_score += 0.01 * (1.0 - float(ledger.causal_packages[package_id].get("noise", 0.5)))
        run_boundary_loop(ledger, generations=1, schedule={})

    # Held-out interventional assay proxy (scaffold meters only).
    threshold = 0.55
    if cell == "transmit":
        discovered = discovery_score >= threshold
    elif cell == "reversal":
        discovered = False  # blind-accept regime fails assay by design
    else:
        discovered = discovery_score >= (threshold + 0.25)

    discovery_share_proxy = 1.0 if discovered else max(0.0, min(1.0, discovery_score / max(threshold, 1e-9)))

    return {
        "schema": "discovery_q_20260928_idea3_scored_cell_v1",
        "idea_id": 3,
        "seed": int(seed),
        "run_id": f"idea3-s{int(seed)}-{cell}",
        "cell": str(cell),
        "discovered": bool(discovered),
        "discovery_share_proxy": float(discovery_share_proxy),
        "discovery_score": float(discovery_score),
        "law_id": law,
        "unreach_id": unreach,
        "package_schema_id": PACKAGE_SCHEMA_ID,
        "reversal_cell_id": reversal,
        "discovery_margin_threshold": DISCOVERY_MARGIN,
        "estimand": "discovery_share",
        "cut_applied": bool(cut_applied) if cell == "cut" else False,
        "package_cut_applied": bool(ledger.package_cut_applied),
        "T_horizon": int(generations),
        "claim_ceiling": CLAIM_CEILING,
        "hypothesis_supported": False,
        "red_queen_proved": False,
        "soft_pass_claimed": False,
        "soft_pass": False,
        "claimgate_refuses": list(CLAIMGATE_REFUSES),
        "honesty": (
            "Scored Idea3 cell under phase2_design. "
            "Not sealed collective-causal evidence; hypothesis_supported stays false "
            "until Critic post-data seal. Volume ≠ discovery. "
            "cut_failed_and_bounds, unreachability, and REV-HIGH-NOISE-BLIND-ACCEPT-V1 "
            "required; empty cut reopens. Scaffold builder build_idea3_scaffold_ledger."
        ),
        "n_unit": "run",
        "ledger_digest": ledger.digest(),
        "distinction_locks": {
            "cut_failed_and_bounds_required": cell != "cut" or cut_applied,
            "unreachability_criterion_in_run": bool(unreach),
            "reversal_cell_identity_present": reversal == REVERSAL_CELL_ID,
            "empty_cut_reopens": True,
            "scaffold_builder": "build_idea3_scaffold_ledger",
        },
    }


def idea3_scored_constants() -> Mapping[str, Any]:
    return {
        **idea3_constants(),
        "scored_cells": list(IDEA3_SCORED_CELLS),
        "scored_horizon_T": SCORED_HORIZON_T,
        "hypothesis_supported": False,
        "soft_pass": False,
        "scaffold_builder": "build_idea3_scaffold_ledger",
        "reversal_cell_id": REVERSAL_CELL_ID,
    }
