"""Discovery questions 2026-09-28 — Idea 5 phase-2 harness smoke.

Transferable short composable falsifiable causal laws on the contact/ATP
ledger (sealed phase-2 design digest). Harness only: retain / teach /
survival-only / shortcut-probe wiring. Full campaigns are not authorised
by this smoke pack. Claim ceiling: phase2_design.
red_queen_proved stays False.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from codontrace._types import JsonValue
from codontrace.errors import ConfigurationError
from codontrace.genesis.canonical import canonical_digest
from codontrace.life_loop.contact_atp_ledger import (
    LAW_SHORT_COMPOSABLE,
    PROBE_PRIVATE_VS_SKELETON,
    WORLD_FAMILY_CONTACT_ATP,
    build_idea5_smoke_ledger,
)
from codontrace.life_loop.discovery_boundary_hooks import make_op, run_boundary_loop

SCHEMA = "discovery_q_20260928_idea5_harness_v1"
CLAIM_CEILING = "phase2_design"
WORLD_FAMILY_ID = WORLD_FAMILY_CONTACT_ATP
LAW_ID = LAW_SHORT_COMPOSABLE
PROBE_ID = PROBE_PRIVATE_VS_SKELETON
THETA = 0.80
TRANSFER_MARGIN = 0.15
HORIZON_T = 40
OPS = (
    "retain_short_law",
    "teach_at_boundary",
    "survival_only_control",
    "shortcut_probe",
)
CLAIMGATE_REFUSES = (
    "red_queen_proved",
    "discovery_claim",
    "first_claim",
    "soft_pass",
)
DREAMCODER_STATUS = "DEFER"


def _require_nonempty(value: str, name: str) -> str:
    text = str(value).strip()
    if not text:
        raise ConfigurationError(f"empty {name} reopens Idea5 freeze.")
    return text


def run_idea5_smoke(
    *,
    seed: int = 42,
    generations: int = 4,
) -> dict[str, JsonValue]:
    """Deterministic Idea5 harness smoke — not a discovery campaign run."""

    # Primary path: retain + teach + shortcut probe (memory/teaching arm).
    ledger = build_idea5_smoke_ledger(seed=int(seed))
    world = _require_nonempty(ledger.world_family_id, "world_family_id")
    law = _require_nonempty(ledger.short_law_id, "short_law_id")
    probe = _require_nonempty(ledger.probe_id, "probe_id")
    if world != WORLD_FAMILY_ID:
        raise ConfigurationError(f"world_family_id must be {WORLD_FAMILY_ID!r}.")
    if law != LAW_ID:
        raise ConfigurationError(f"short_law_id must be {LAW_ID!r}.")
    if probe != PROBE_ID:
        raise ConfigurationError(f"probe_id must be {PROBE_ID!r}.")
    held_out = list(ledger.held_out_split.get("held_out", []))
    if not held_out:
        raise ConfigurationError("empty held-out split reopens Idea5 freeze.")

    schedule = {
        0: [
            make_op(
                "retain_short_law",
                law_key="law-smoke-1",
                law_body="if_contact_parent_then_atp_yield",
                n_terms=4,
                depth=2,
            )
        ],
        1: [make_op("teach_at_boundary", law_key="law-smoke-1")],
        2: [
            make_op(
                "shortcut_probe",
                skeleton_intact_accuracy=0.85,
                private_only_accuracy=0.40,
            )
        ],
        # Gen 3 left as no-op on primary ledger (probe already recorded).
    }
    history = run_boundary_loop(ledger, generations=int(generations), schedule=schedule)

    # Matched survival-only control on a separate ledger (H3 contrast wiring).
    control = build_idea5_smoke_ledger(seed=int(seed) + 1)
    control_schedule = {
        0: [make_op("survival_only_control")],
    }
    control_history = run_boundary_loop(
        control, generations=2, schedule=control_schedule
    )

    teach_ok = len(ledger.teaching_log) >= 1 and "law-smoke-1" in ledger.retained_laws
    probe_ok = (
        len(ledger.shortcut_probe_log) >= 1
        and ledger.shortcut_probe_log[-1].get("pass") is True
        and ledger.shortcut_probe_log[-1].get("train_fit_alone_counts") is False
    )
    survival_distinct = (
        control.survival_only_active
        and not control.retained_laws
        and not control.teaching_log
        and not ledger.survival_only_active
    )
    ids_nonempty = bool(world) and bool(law) and bool(probe) and bool(held_out)
    engineering_green = bool(
        history
        and control_history
        and teach_ok
        and probe_ok
        and survival_distinct
        and ids_nonempty
    )
    freeze_reopen = not ids_nonempty

    pack: dict[str, JsonValue] = {
        "schema": SCHEMA,
        "claim_ceiling": CLAIM_CEILING,
        "world_family_id": world,
        "law_id": law,
        "probe_id": probe,
        "held_out_split": {
            "train": list(ledger.held_out_split.get("train", [])),
            "held_out": held_out,
        },
        "ops": list(OPS),
        "theta": THETA,
        "transfer_margin": TRANSFER_MARGIN,
        "horizon_T": HORIZON_T,
        "n_unit": "run",
        "engineering_green": engineering_green,
        "hypothesis_supported": False,
        "red_queen_proved": False,
        "soft_pass_claimed": False,
        "freeze_reopen": freeze_reopen,
        "dreamcoder_status": DREAMCODER_STATUS,
        "claimgate_refuses": list(CLAIMGATE_REFUSES),
        "honesty": (
            "Harness smoke only under sealed phase-2 design digest. "
            "No discovery claim. Full campaigns remain off until owner allows. "
            "Train-fit alone is FAIL; held-out split and shortcut pair required."
        ),
        "ledger_digest": ledger.digest(),
        "control_ledger_digest": control.digest(),
        "history_len": len(history),
        "control_history_len": len(control_history),
        "teaching_log_len": len(ledger.teaching_log),
        "shortcut_probe_pass": bool(probe_ok),
        "distinction_locks": {
            "held_out_split_present": bool(held_out),
            "shortcut_pair_present": probe_ok,
            "train_fit_alone_is_fail": True,
            "survival_only_neq_teach": survival_distinct,
            "dreamcoder_deferred": DREAMCODER_STATUS == "DEFER",
            "identity_ids_nonempty": ids_nonempty,
        },
    }
    pack["pack_digest"] = canonical_digest(
        {k: v for k, v in pack.items() if k != "pack_digest"},
        prefix="idea5_smoke",
    )
    return pack


def idea5_constants() -> Mapping[str, Any]:
    return {
        "world_family_id": WORLD_FAMILY_ID,
        "law_id": LAW_ID,
        "probe_id": PROBE_ID,
        "ops": list(OPS),
        "theta": THETA,
        "transfer_margin": TRANSFER_MARGIN,
        "horizon_T": HORIZON_T,
        "claim_ceiling": CLAIM_CEILING,
        "hypothesis_supported": False,
        "red_queen_proved": False,
        "dreamcoder_status": DREAMCODER_STATUS,
        "n_unit": "run",
    }
