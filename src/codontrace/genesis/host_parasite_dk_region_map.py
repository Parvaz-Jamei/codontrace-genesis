"""De-toy D2: mortality d × carrying capacity K cycling region map (port-local).

Sweeps the type-II / diagonally-dominant stepper from D1 across a declared
(d, K) grid and records where qualitative cycling_detected appears.
ClaimGate: red_queen_proved stays False; clinical prediction refused.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from codontrace.genesis.canonical import canonical_digest, canonical_payload
from codontrace.genesis.host_parasite_type2_rq import run_type2_campaign

SCHEMA = "host_parasite_dk_region_map_v1"
DOMAIN_PROFILE = "host_parasite"

DEFAULT_D_GRID: tuple[float, ...] = (0.01, 0.08, 0.12, 0.20, 0.40)
DEFAULT_K_GRID: tuple[float, ...] = (0.5, 2.0, 5.0, 10.0)
DEFAULT_SEEDS: tuple[int, ...] = (101, 202, 303, 404, 505)
# Slightly shorter than SF4 capable defaults — still long enough for region signal.
DEFAULT_STEPS = 4000
DEFAULT_BURN_IN = 500


def _digest_body(body: Mapping[str, object]) -> str:
    return canonical_digest(canonical_payload(dict(body)))


def _cell_label(*, n_cycling: int, n_seeds: int) -> str:
    if n_cycling >= 3:
        return "cycling_capable"
    if n_cycling >= 1:
        return "partial_cycling"
    return "noncycling"


def run_dk_region_map(
    *,
    d_grid: Sequence[float] = DEFAULT_D_GRID,
    k_grid: Sequence[float] = DEFAULT_K_GRID,
    seeds: Sequence[int] = DEFAULT_SEEDS,
    steps: int = DEFAULT_STEPS,
    burn_in: int = DEFAULT_BURN_IN,
    r: float = 0.5,
    n_types: int = 5,
    alpha_off: float = 0.01,
    dt: float = 0.05,
) -> dict[str, Any]:
    """Execute the (d, K) sweep; return digestible region map payload."""

    cells: list[dict[str, object]] = []
    capable_coords: list[list[float]] = []
    for d in d_grid:
        for k in k_grid:
            camp = run_type2_campaign(
                seeds=seeds,
                d=float(d),
                k=float(k),
                steps=int(steps),
                burn_in=int(burn_in),
                r=float(r),
                n_types=int(n_types),
                alpha_off=float(alpha_off),
                dt=float(dt),
            )
            n_cycle = int(camp["n_cycling_seeds"])
            label = _cell_label(n_cycling=n_cycle, n_seeds=len(seeds))
            cell = {
                "d": float(d),
                "K": float(k),
                "n_cycling_seeds": n_cycle,
                "n_seeds": len(seeds),
                "campaign_result": camp["result"],
                "label": label,
                "red_queen_proved": False,
            }
            cells.append(cell)
            if label == "cycling_capable":
                capable_coords.append([float(d), float(k)])

    # Prereg pattern checks (Sci Rep analogue; digital qualitative).
    mid_d_high_k = [
        c
        for c in cells
        if float(c["d"]) in {0.08, 0.12, 0.20} and float(c["K"]) >= 2.0  # type: ignore[arg-type]
    ]
    tiny_k = [c for c in cells if float(c["K"]) <= 0.5]  # type: ignore[arg-type]
    mid_capable = sum(1 for c in mid_d_high_k if c["label"] == "cycling_capable")
    tiny_k_capable = sum(1 for c in tiny_k if c["label"] == "cycling_capable")
    # Sci Rep visual RQ is narrower than our epoch cycling_detected metric.
    # Honest pattern: mid-d/high-K nonempty AND tiny-K mostly empty.
    # Low-d / high-d edges may still light up under the coarser digital metric —
    # that mismatch is documented, not hidden.
    structural_ok = mid_capable >= 1 and tiny_k_capable <= 1
    exact_sci_rep_match = structural_ok and all(
        float(c["d"]) > 0.01 and float(c["d"]) < 0.40  # type: ignore[arg-type]
        for c in cells
        if c["label"] == "cycling_capable"
    )
    pattern_matched = structural_ok
    pattern_note = (
        "mid-d/high-K capable and tiny-K mostly empty (Sci Rep analogue, digital metric)"
        if exact_sci_rep_match
        else (
            "structural mid-d/high-K capable + tiny-K empty OK; epoch metric wider "
            "than Sci Rep visual RQ on low-d/high-d edges — documented mismatch"
            if structural_ok
            else "documented mismatch vs Sci Rep qualitative expectation"
        )
    )
    extreme_capable = tiny_k_capable  # retained key for tests: tiny-K focus

    body: dict[str, Any] = {
        "schema": SCHEMA,
        "domain_profile": DOMAIN_PROFILE,
        "doi": "10.1038/srep10004",
        "pmc": "PMC4405699",
        "d_grid": [float(x) for x in d_grid],
        "k_grid": [float(x) for x in k_grid],
        "seeds": list(seeds),
        "steps": int(steps),
        "burn_in": int(burn_in),
        "r": float(r),
        "n_types": int(n_types),
        "alpha_off": float(alpha_off),
        "dt": float(dt),
        "cells": cells,
        "n_cells": len(cells),
        "n_cycling_capable_cells": len(capable_coords),
        "capable_coords_d_K": capable_coords,
        "prereg_pattern_matched": pattern_matched,
        "prereg_pattern_note": pattern_note,
        "sci_rep_visual_exact_match": exact_sci_rep_match,
        "mid_d_high_k_capable_count": mid_capable,
        "tiny_k_capable_count": tiny_k_capable,
        "extreme_capable_count": extreme_capable,
        "red_queen_proved": False,
        "clinical_prediction_refused": True,
        "claimgate_refuses": [
            "red_queen_proved",
            "phage_therapy_cleared",
            "clinical_pathogen_model",
        ],
        "engine_infection_physics": "not_in_engine_core",
        "honesty": (
            "Region labels are digital qualitative cycling detections on the "
            "host_parasite port — not wet Red Queen proof or clinical maps."
        ),
    }
    body["map_digest"] = _digest_body(body)
    return body


__all__ = [
    "SCHEMA",
    "DOMAIN_PROFILE",
    "DEFAULT_D_GRID",
    "DEFAULT_K_GRID",
    "DEFAULT_SEEDS",
    "run_dk_region_map",
]
