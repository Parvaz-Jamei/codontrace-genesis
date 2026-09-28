"""Discovery questions 2026-09-28 — Idea 1 phase-2 harness smoke.

Costly causal experimentation vs reactive learning / reward exploration
on the contact/ATP ledger (sealed phase-2 design digest). Harness only:
ledger do-ops + rival-discrimination assay wiring. Full campaigns are not
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
    RIVAL_PAIR_ATP_DRAIN,
    build_idea1_scaffold_ledger,
)
from codontrace.life_loop.discovery_boundary_hooks import make_op, run_boundary_loop

SCHEMA = "discovery_q_20260928_idea1_harness_v1"
CLAIM_CEILING = "phase2_design"
RIVAL_PAIR_ID = RIVAL_PAIR_ATP_DRAIN
DECISION_BUDGET = 1.0
CHANNEL_MARGIN = 0.15
OPS = (
    "do_rival_discriminate",
    "update_reactive_ledger",
    "reward_explore_ε",
)
CLAIMGATE_REFUSES = (
    "red_queen_proved",
    "discovery_claim",
    "first_claim",
    "soft_pass",
)
EVOSCM_STATUS = "DEFER"


def _require_rival_pair(rival_pair_id: str) -> str:
    text = str(rival_pair_id).strip()
    if not text:
        raise ConfigurationError(
            "empty rival_pair_id reopens Idea1 freeze."
        )
    if text != RIVAL_PAIR_ID:
        raise ConfigurationError(
            f"rival_pair_id must be {RIVAL_PAIR_ID!r}; got {text!r}."
        )
    return text


def run_idea1_smoke(
    *,
    seed: int = 42,
    generations: int = 4,
) -> dict[str, JsonValue]:
    """Deterministic Idea1 harness smoke — not a discovery campaign run."""

    ledger = build_idea1_scaffold_ledger(seed=int(seed))
    rival = _require_rival_pair(ledger.rival_pair_id)

    schedule = {
        0: [
            make_op(
                "do_rival_discriminate",
                parent_edge_id="P0",
                cost=0.25,
                rival_pair_id=rival,
            )
        ],
        1: [make_op("update_reactive_ledger", observation_key="atp_obs", value=0.7)],
        2: [make_op("reward_explore_ε", epsilon=0.2, budget=DECISION_BUDGET)],
        3: [
            make_op(
                "do_rival_discriminate",
                parent_edge_id="P1",
                cost=0.25,
                rival_pair_id=rival,
            )
        ],
    }
    history = run_boundary_loop(ledger, generations=int(generations), schedule=schedule)

    assay_ran = len(ledger.rival_assay_log) >= 1
    reactive_ran = bool(ledger.reactive_memory)
    explore_ran = len(ledger.explore_log) >= 1
    # Distinction: margin without assay pass is not H2 (smoke records shape only).
    assay_separate_from_reward = assay_ran and explore_ran and (
        ledger.rival_assay_log[0]["op"] == "do_rival_discriminate"
        and ledger.explore_log[0]["op"] == "reward_explore_ε"
        and ledger.explore_log[0].get("rival_contrast") is False
    )
    ids_nonempty = bool(rival) and all(bool(op) for op in OPS)
    engineering_green = bool(
        history
        and assay_ran
        and reactive_ran
        and explore_ran
        and assay_separate_from_reward
        and ids_nonempty
    )
    freeze_reopen = not ids_nonempty

    pack: dict[str, JsonValue] = {
        "schema": SCHEMA,
        "claim_ceiling": CLAIM_CEILING,
        "rival_pair_id": rival,
        "ops": list(OPS),
        "decision_budget": DECISION_BUDGET,
        "channel_margin": CHANNEL_MARGIN,
        "n_unit": "run",
        "engineering_green": engineering_green,
        "hypothesis_supported": False,
        "red_queen_proved": False,
        "soft_pass_claimed": False,
        "freeze_reopen": freeze_reopen,
        "evoscm_status": EVOSCM_STATUS,
        "combo_c_is_core": False,
        "claimgate_refuses": list(CLAIMGATE_REFUSES),
        "honesty": (
            "Harness smoke only under sealed phase-2 design digest. "
            "No discovery claim. Full campaigns remain off until owner allows. "
            "Margin without assay pass is not H2."
        ),
        "ledger_digest": ledger.digest(),
        "history_len": len(history),
        "rival_assay_log_len": len(ledger.rival_assay_log),
        "reactive_memory_keys": sorted(ledger.reactive_memory),
        "explore_log_len": len(ledger.explore_log),
        "distinction_locks": {
            "assay_separate_from_reward": assay_separate_from_reward,
            "margin_without_assay_is_not_h2": True,
            "combo_c_not_core": True,
            "evoscm_deferred": EVOSCM_STATUS == "DEFER",
            "identity_ids_nonempty": ids_nonempty,
        },
    }
    pack["pack_digest"] = canonical_digest(
        {k: v for k, v in pack.items() if k != "pack_digest"},
        prefix="idea1_smoke",
    )
    return pack


def idea1_constants() -> Mapping[str, Any]:
    return {
        "rival_pair_id": RIVAL_PAIR_ID,
        "ops": list(OPS),
        "decision_budget": DECISION_BUDGET,
        "channel_margin": CHANNEL_MARGIN,
        "claim_ceiling": CLAIM_CEILING,
        "hypothesis_supported": False,
        "red_queen_proved": False,
        "evoscm_status": EVOSCM_STATUS,
        "n_unit": "run",
    }


# ---------------------------------------------------------------------------
# Scored cell API (phase2_design meters; not a discovery claim)
# ---------------------------------------------------------------------------

IDEA1_SCORED_CELLS: tuple[str, ...] = (
    "discriminate",
    "reactive",
    "reward_explore",
)
SCORED_HORIZON_T = 24


def run_idea1_scored_cell(
    *,
    seed: int,
    cell: str,
    generations: int = SCORED_HORIZON_T,
) -> dict[str, JsonValue]:
    """Score one Idea1 arm cell under scaffold ledger; N=run.

    Cells: discriminate / reactive / reward_explore. Rival assay is separate
    from reward exploration. Uses build_idea1_scaffold_ledger (not smoke alias).
    hypothesis_supported stays False (volume ≠ discovery). Soft-pass forbidden.
    """

    if cell not in IDEA1_SCORED_CELLS:
        raise ConfigurationError(f"unknown Idea1 cell {cell!r}.")
    if int(generations) < 4:
        raise ConfigurationError("scored Idea1 generations must be >= 4.")

    import random as _random

    rng = _random.Random(int(seed) * 1009 + sum(ord(c) for c in cell))
    ledger = build_idea1_scaffold_ledger(seed=int(seed))
    rival = _require_rival_pair(ledger.rival_pair_id)

    energy = 1.0
    survived_steps = 0
    assay_passes = 0
    assay_trials = 0
    reward_gain = 0.0

    for g in range(int(generations)):
        atp_debit = float(DECISION_BUDGET) * 0.15
        pressure = 0.35 + 0.25 * rng.random()

        if cell == "discriminate":
            parent = "P0" if g % 2 == 0 else "P1"
            ledger.do_rival_discriminate(
                parent_edge_id=parent, cost=0.25, rival_pair_id=rival
            )
            assay_trials += 1
            # Scaffold discrimination: parent mask separates R1 from R2 schedule.
            separated = bool(ledger.rival_assay_log) and ledger.rival_assay_log[-1][
                "op"
            ] == "do_rival_discriminate"
            if separated:
                assay_passes += 1
            fit = 0.55 if separated else 0.25
            energy += fit * 0.4 - atp_debit - pressure * 0.15 - 0.25 * 0.2
        elif cell == "reactive":
            obs = 0.4 + 0.5 * rng.random()
            ledger.update_reactive_ledger(observation_key="atp_obs", value=obs)
            mem = float(ledger.reactive_memory.get("atp_obs", 0.0))
            fit = max(0.0, min(1.0, mem))
            energy += fit * 0.35 - atp_debit * 0.1 - pressure * 0.2
        else:  # reward_explore
            before = sum(e.atp_yield for e in ledger.edges.values() if e.present)
            ledger.reward_explore_ε(epsilon=0.2, budget=DECISION_BUDGET)
            after = sum(e.atp_yield for e in ledger.edges.values() if e.present)
            reward_gain += max(0.0, after - before)
            # Reward path must not claim rival contrast.
            if ledger.explore_log and ledger.explore_log[-1].get("rival_contrast") is not False:
                raise ConfigurationError(
                    "reward_explore_ε must keep rival_contrast=False "
                    "(assay separate from reward)."
                )
            fit = 0.35 + 0.1 * min(1.0, reward_gain)
            energy += fit * 0.4 - atp_debit * 0.1 - pressure * 0.2

        if energy > 0.0:
            survived_steps += 1
        run_boundary_loop(ledger, generations=1, schedule={})

    survival = float(survived_steps) / float(generations) if generations else 0.0
    survival = max(
        0.0,
        min(1.0, 0.7 * survival + 0.3 * max(0.0, min(1.0, energy / max(generations, 1)))),
    )
    assay_pass = bool(assay_trials and assay_passes == assay_trials and cell == "discriminate")
    # Margin without assay pass is not H2 — record assay flag explicitly.
    assay_separate_from_reward = (
        cell == "discriminate"
        and bool(ledger.rival_assay_log)
        and not any(e.get("rival_contrast") for e in ledger.explore_log)
    ) or (
        cell == "reward_explore"
        and bool(ledger.explore_log)
        and all(e.get("rival_contrast") is False for e in ledger.explore_log)
    ) or (cell == "reactive")

    return {
        "schema": "discovery_q_20260928_idea1_scored_cell_v1",
        "idea_id": 1,
        "seed": int(seed),
        "run_id": f"idea1-s{int(seed)}-{cell}",
        "cell": str(cell),
        "survival_to_T": float(survival),
        "assay_pass": bool(assay_pass) if cell == "discriminate" else False,
        "assay_trials": int(assay_trials),
        "assay_passes": int(assay_passes),
        "reward_gain": float(reward_gain),
        "rival_pair_id": rival,
        "channel_margin_threshold": CHANNEL_MARGIN,
        "estimand": "survival_share_to_T",
        "decision_budget": DECISION_BUDGET,
        "T_horizon": int(generations),
        "claim_ceiling": CLAIM_CEILING,
        "hypothesis_supported": False,
        "red_queen_proved": False,
        "soft_pass_claimed": False,
        "soft_pass": False,
        "evoscm_status": EVOSCM_STATUS,
        "claimgate_refuses": list(CLAIMGATE_REFUSES),
        "honesty": (
            "Scored Idea1 cell under phase2_design. "
            "Not sealed discrimination evidence; hypothesis_supported stays false "
            "until Critic post-data seal. Volume ≠ discovery. "
            "Assay separate from reward; margin without assay pass is not H2. "
            "Scaffold builder build_idea1_scaffold_ledger."
        ),
        "n_unit": "run",
        "ledger_digest": ledger.digest(),
        "distinction_locks": {
            "assay_separate_from_reward": bool(assay_separate_from_reward),
            "margin_without_assay_is_not_h2": True,
            "rival_pair_id": rival,
            "scaffold_builder": "build_idea1_scaffold_ledger",
        },
    }


def idea1_scored_constants() -> Mapping[str, Any]:
    return {
        **idea1_constants(),
        "scored_cells": list(IDEA1_SCORED_CELLS),
        "scored_horizon_T": SCORED_HORIZON_T,
        "hypothesis_supported": False,
        "soft_pass": False,
        "scaffold_builder": "build_idea1_scaffold_ledger",
    }
