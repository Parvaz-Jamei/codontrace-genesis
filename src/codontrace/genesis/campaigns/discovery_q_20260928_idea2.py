"""Discovery questions 2026-09-28 — Idea 2 phase-2 harness smoke.

Gene / pattern / causal competition under coevolving antagonist pressure
on the contact/ATP ledger (sealed phase-2 design digest). Harness only:
ledger do-ops + SHAM-CUE-PREDPHASE-V1 wiring. Full campaigns are not
authorised by this smoke pack. Claim ceiling: phase2_design.
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
    build_idea2_smoke_ledger,
)
from codontrace.life_loop.discovery_boundary_hooks import make_op, run_boundary_loop

SCHEMA = "discovery_q_20260928_idea2_harness_v1"
CLAIM_CEILING = "phase2_design"
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


# ---------------------------------------------------------------------------
# Scored cell API (phase2_design meters; not a discovery claim)
# ---------------------------------------------------------------------------

IDEA2_SCORED_CELLS: tuple[str, ...] = (
    "baseline",
    "pi_deception",
    "do_ablation",
    "sham_predphase",
)
MECHANISM_COMPETITORS: tuple[str, ...] = ("M0", "M1", "M2", "M3")
SCORED_HORIZON_T = 24


def _arm_survival_series(
    *,
    seed: int,
    cell: str,
    arm: str,
    generations: int,
    kappa: float,
) -> dict[str, Any]:
    """Simulate one arm under a scored cell; return survival_to_T and flags."""

    import random as _random

    rng = _random.Random(int(seed) * 1009 + sum(ord(c) for c in cell + arm))
    ledger = build_idea2_smoke_ledger(seed=int(seed))
    realised = 0.25
    predicted = realised
    if cell == "pi_deception":
        predicted = realised + DECEPTION_PHASE
    ledger.realised_pressure_phase = float(realised)
    ledger.predicted_pressure_phase = float(predicted)

    # Arm state
    gene_match = 0.0
    pattern_memory = float(predicted)
    causal_do_enabled = cell != "do_ablation"
    do_on_nc = False
    energy = 1.0
    survived_steps = 0

    for g in range(int(generations)):
        # Shared realised pressure walk
        realised = (realised + 0.35 + 0.05 * rng.random()) % (2.0 * math.pi)
        if cell == "pi_deception":
            predicted = realised + DECEPTION_PHASE
        elif cell == "sham_predphase":
            # Sham retargets predicted phase only (never NC-*).
            ledger.sham_cue_predphase(offset=DECEPTION_PHASE)
            predicted = float(ledger.predicted_pressure_phase)
            realised = (realised + 0.0) % (2.0 * math.pi)
        else:
            predicted = realised + 0.05 * (rng.random() - 0.5)
        ledger.realised_pressure_phase = float(realised)
        ledger.predicted_pressure_phase = float(predicted)

        pressure = 0.5 + 0.5 * abs(math.sin(realised))
        atp_debit = float(DECISION_BUDGET) * float(kappa)

        if arm == "gene":
            # Slow genotype tracking of realised pressure.
            gene_match += 0.08 * (math.sin(realised) - gene_match)
            fit = max(0.0, 1.0 - abs(gene_match - math.sin(realised)))
            energy += fit * 0.35 - atp_debit * 0.15 - pressure * 0.2
        elif arm == "pattern":
            pattern_memory = 0.7 * pattern_memory + 0.3 * predicted
            # Pattern pays when predicted aligns with realised (fails under π).
            align = 1.0 - min(1.0, abs((predicted - realised + math.pi) % (2 * math.pi) - math.pi) / math.pi)
            energy += align * 0.45 - atp_debit * 0.15 - pressure * 0.25
        else:  # causal
            fit = 0.25
            if causal_do_enabled and g % 3 == 0:
                # Allowed do on NC-* parents of pressure (not sham).
                target = sorted(NAMED_CONTACT_SET)[g % len(NAMED_CONTACT_SET)]
                ledger.mask_named_contacts([target], one_generation=True)
                do_on_nc = True
                fit = 0.55 + 0.2 * (1.0 - abs(math.sin(realised)))
            elif cell == "sham_predphase":
                # Sham available but is cue-parent only → weak causal signal.
                fit = 0.22
            else:
                # do ablated: revision only, no ledger do.
                fit = 0.28
            energy += fit * 0.5 - atp_debit * 0.2 - pressure * 0.15

        # Harvest present unmasked NC ATP as weak survival buffer
        nc_atp = sum(
            ledger.edges[eid].atp_yield
            for eid in NAMED_CONTACT_SET
            if eid in ledger.edges and ledger.edges[eid].present and not ledger.edges[eid].masked
        )
        energy += 0.02 * nc_atp
        if energy > 0.0:
            survived_steps += 1
        run_boundary_loop(ledger, generations=1, schedule={})

    survival = float(survived_steps) / float(generations) if generations else 0.0
    # Soft clip with energy residual
    survival = max(0.0, min(1.0, 0.7 * survival + 0.3 * max(0.0, min(1.0, energy / generations))))
    return {
        "survival_to_T": float(survival),
        "do_on_NC": bool(do_on_nc),
        "energy_end": float(energy),
        "ledger_digest": ledger.digest(),
    }


def run_idea2_scored_cell(
    *,
    seed: int,
    cell: str,
    kappa: float | None = KAPPA_SMOKE,
    generations: int = SCORED_HORIZON_T,
) -> list[dict[str, JsonValue]]:
    """Score all three arms for one cell; N=run; one record per arm.

    Records margin_vs_best_rival and locked estimand threshold, but keeps
    hypothesis_supported=False (M0–M3 are labels only; no post-data seal).
    """

    k = require_kappa(kappa)
    if cell not in IDEA2_SCORED_CELLS:
        raise ConfigurationError(f"unknown Idea2 cell {cell!r}.")
    if int(generations) < 4:
        raise ConfigurationError("scored Idea2 generations must be >= 4.")

    arm_stats: dict[str, dict[str, Any]] = {}
    for arm in ARMS:
        arm_stats[arm] = _arm_survival_series(
            seed=int(seed), cell=str(cell), arm=arm, generations=int(generations), kappa=k
        )

    records: list[dict[str, JsonValue]] = []
    for arm in ARMS:
        surv = float(arm_stats[arm]["survival_to_T"])
        rivals = [float(arm_stats[a]["survival_to_T"]) for a in ARMS if a != arm]
        best_rival = max(rivals) if rivals else 0.0
        margin = float(surv - best_rival)
        rec: dict[str, JsonValue] = {
            "schema": "discovery_q_20260928_idea2_scored_cell_v1",
            "idea_id": 2,
            "seed": int(seed),
            "run_id": f"idea2-s{int(seed)}-{cell}-{arm}",
            "cell": str(cell),
            "arm": str(arm),
            "survival_to_T": surv,
            "margin_vs_best_rival": margin,
            "channel_margin_threshold": CHANNEL_MARGIN,
            "estimand": "observer_arm_score",
            "score_role": "observer_arm_score",
            "hypothesis_test_eligible": False,
            "sham_id": SHAM_ID,
            "do_on_NC": bool(arm_stats[arm]["do_on_NC"]),
            "decision_budget": DECISION_BUDGET,
            "kappa": k,
            "T_horizon": int(generations),
            "mechanism_competitors": list(MECHANISM_COMPETITORS),
            "mechanism_label_deferred": True,
            "claim_ceiling": CLAIM_CEILING,
            "hypothesis_supported": False,
            "red_queen_proved": False,
            "honesty": (
                "Scored Idea2 cell under phase2_design. "
                "survival_to_T is an observer-arm score: positive-energy steps "
                "blended 0.7/0.3 with residual energy. It is not an independent "
                "host population and not a host-parasite hypothesis test. "
                "Not G2/M0–M3 sealed evidence; hypothesis_supported stays false. "
                "Volume ≠ discovery. "
                "Sham is SHAM-CUE-PREDPHASE-V1 only (never NC-*)."
            ),
            "n_unit": "run",
            "ledger_digest": arm_stats[arm]["ledger_digest"],
        }
        # Distinction lock: sham cell must not set do_on_NC via sham path as NC mask claim
        if cell == "sham_predphase":
            rec["sham_targets_nc"] = False
        records.append(rec)
    return records


def idea2_scored_constants() -> Mapping[str, Any]:
    return {
        **idea2_constants(),
        "scored_cells": list(IDEA2_SCORED_CELLS),
        "arms": list(ARMS),
        "mechanism_competitors": list(MECHANISM_COMPETITORS),
        "scored_horizon_T": SCORED_HORIZON_T,
        "channel_margin": CHANNEL_MARGIN,
        "hypothesis_supported": False,
        "hypothesis_test_eligible": False,
        "score_role": "observer_arm_score",
    }
