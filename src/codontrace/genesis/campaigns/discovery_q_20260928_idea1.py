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
    build_idea1_smoke_ledger,
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

    ledger = build_idea1_smoke_ledger(seed=int(seed))
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
