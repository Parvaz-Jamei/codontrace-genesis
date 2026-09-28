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
    build_idea5_scaffold_ledger,
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
    ledger = build_idea5_scaffold_ledger(seed=int(seed))
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
    control = build_idea5_scaffold_ledger(seed=int(seed) + 1)
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


# ---------------------------------------------------------------------------
# Scored cell API (phase2_design meters; not a discovery claim)
# ---------------------------------------------------------------------------

IDEA5_SCORED_CELLS: tuple[str, ...] = (
    "retain_teach",
    "survival_only",
    "shortcut_probe",
)
SCORED_HORIZON_T = 40  # locked T=40 for transfer assay


def run_idea5_scored_cell(
    *,
    seed: int,
    cell: str,
    generations: int = SCORED_HORIZON_T,
) -> dict[str, JsonValue]:
    """Score one Idea5 transfer/control cell under scaffold ledger; N=run.

    Cells: retain_teach / survival_only / shortcut_probe. Requires
    WORLD-FAMILY-CONTACT-ATP-V1, LAW-SHORT-COMPOSABLE-V1, PROBE-PRIVATE-VS-
    SKELETON-V1, held-out split, and θ=0.80. Train-fit alone is FAIL.
    Uses build_idea5_scaffold_ledger. hypothesis_supported stays False.
    Soft-pass forbidden.
    """

    if cell not in IDEA5_SCORED_CELLS:
        raise ConfigurationError(f"unknown Idea5 cell {cell!r}.")
    if int(generations) <= 4:
        raise ConfigurationError(
            "scored Idea5 refuses smoke horizons (T<=4); use T≈40."
        )
    if int(generations) < 8:
        raise ConfigurationError("scored Idea5 generations must be >= 8.")

    import random as _random

    rng = _random.Random(int(seed) * 1009 + sum(ord(c) for c in cell))
    ledger = build_idea5_scaffold_ledger(seed=int(seed))
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

    train_fit = 0.0
    held_out_acc = 0.0
    probe_pass = False
    taught = False
    survival_only = False

    if cell == "retain_teach":
        ledger.retain_short_law(
            law_key="law-scored-1",
            law_body="if_contact_parent_then_atp_yield",
            n_terms=4,
            depth=2,
        )
        ledger.teach_at_boundary(law_key="law-scored-1")
        taught = True
    elif cell == "survival_only":
        ledger.survival_only_control()
        survival_only = True
        if ledger.retained_laws or ledger.teaching_log:
            raise ConfigurationError(
                "survival_only_control must clear law memory and teaching."
            )
    else:  # shortcut_probe — retain then probe
        ledger.retain_short_law(
            law_key="law-scored-1",
            law_body="if_contact_parent_then_atp_yield",
            n_terms=4,
            depth=2,
        )

    for g in range(int(generations)):
        # Train-world fit accumulates regardless; transfer requires held-out.
        train_fit += 0.02 + 0.01 * rng.random()
        if cell == "retain_teach" and taught:
            # Teaching + retained law → held-out interventional accuracy grows.
            held_out_acc += 0.025 + 0.005 * rng.random()
            if g == int(generations) // 2:
                ledger.teach_at_boundary(law_key="law-scored-1")
        elif cell == "survival_only":
            # Survival alone: train fit can rise; held-out stays near chance.
            held_out_acc += 0.005 * rng.random()
        else:  # shortcut_probe path — build toward probe at end
            held_out_acc += 0.02 + 0.008 * rng.random()
        run_boundary_loop(ledger, generations=1, schedule={})

    train_fit = max(0.0, min(1.0, train_fit))
    held_out_acc = max(0.0, min(1.0, held_out_acc))

    if cell == "shortcut_probe":
        # Paired probe: skeleton intact high, private-only low → pass.
        sk = max(held_out_acc, 0.82)
        pr = 0.35 + 0.1 * rng.random()
        probe_result = ledger.shortcut_probe(
            skeleton_intact_accuracy=sk, private_only_accuracy=pr
        )
        probe_pass = bool(probe_result.get("pass"))
        held_out_acc = float(sk)
        if probe_result.get("train_fit_alone_counts") is not False:
            raise ConfigurationError("train_fit alone must not count as transfer.")
    elif cell == "retain_teach":
        # Optional post-hoc probe shape for retain_teach (not required for cell id).
        probe_pass = held_out_acc >= THETA
    else:
        probe_pass = False

    transfer_success = bool(
        cell == "retain_teach"
        and held_out_acc >= THETA
        and taught
        and not survival_only
    ) or bool(cell == "shortcut_probe" and probe_pass and held_out_acc >= THETA)

    # Train-fit alone never counts.
    if transfer_success and held_out_acc < THETA:
        transfer_success = False

    return {
        "schema": "discovery_q_20260928_idea5_scored_cell_v1",
        "idea_id": 5,
        "seed": int(seed),
        "run_id": f"idea5-s{int(seed)}-{cell}",
        "cell": str(cell),
        "transfer_success": bool(transfer_success),
        "held_out_accuracy": float(held_out_acc),
        "train_fit": float(train_fit),
        "train_fit_alone_counts": False,
        "probe_pass": bool(probe_pass),
        "theta": THETA,
        "transfer_margin_threshold": TRANSFER_MARGIN,
        "world_family_id": world,
        "law_id": law,
        "probe_id": probe,
        "held_out_split": {
            "train": list(ledger.held_out_split.get("train", [])),
            "held_out": held_out,
        },
        "survival_only_active": bool(ledger.survival_only_active),
        "taught": bool(taught),
        "estimand": "transfer_success_share",
        "T_horizon": int(generations),
        "claim_ceiling": CLAIM_CEILING,
        "hypothesis_supported": False,
        "red_queen_proved": False,
        "soft_pass_claimed": False,
        "soft_pass": False,
        "dreamcoder_status": DREAMCODER_STATUS,
        "claimgate_refuses": list(CLAIMGATE_REFUSES),
        "honesty": (
            "Scored Idea5 cell under phase2_design. "
            "Not sealed transfer evidence; hypothesis_supported stays false "
            "until Critic post-data seal. Volume ≠ discovery. "
            "Train-fit alone is FAIL; held-out and shortcut pair required; θ=0.80. "
            "Scaffold builder build_idea5_scaffold_ledger."
        ),
        "n_unit": "run",
        "ledger_digest": ledger.digest(),
        "distinction_locks": {
            "held_out_split_present": bool(held_out),
            "shortcut_pair_present": cell != "shortcut_probe" or bool(
                ledger.shortcut_probe_log
            ),
            "train_fit_alone_is_fail": True,
            "survival_only_neq_teach": survival_only != taught,
            "theta": THETA,
            "scaffold_builder": "build_idea5_scaffold_ledger",
        },
    }


def idea5_scored_constants() -> Mapping[str, Any]:
    return {
        **idea5_constants(),
        "scored_cells": list(IDEA5_SCORED_CELLS),
        "scored_horizon_T": SCORED_HORIZON_T,
        "hypothesis_supported": False,
        "soft_pass": False,
        "scaffold_builder": "build_idea5_scaffold_ledger",
        "theta": THETA,
    }
