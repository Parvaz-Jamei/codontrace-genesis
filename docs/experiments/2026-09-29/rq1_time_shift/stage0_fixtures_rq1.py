"""RQ-1 stage-0 fixture assay (instrument only, never a live result).

Reads the repository's own classifier and rotation helper, reproduces the four
pre-registered time-shift fixtures, and adds the quantity RQ-1 names as primary:
the host-time x antagonist-time **interaction contrast** of the pressure matrix.

Writes ``raw/stage0_fixtures.json`` and ``raw/stage0_fixture_events.jsonl``.
No live population is involved and no decision flag is raised.
"""

from __future__ import annotations

import hashlib
import itertools
import json
import sys
import time
from pathlib import Path

REPO = Path(r"E:\مقاله پزشکی شبیه سازی ویروس\codontrace-genesis")
SRC = REPO / "src"
OUT = Path(__file__).resolve().parent
RAW = OUT / "raw"
RAW.mkdir(parents=True, exist_ok=True)
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from codontrace.genesis.campaigns.discovery_program_20260929_stage0 import (  # noqa: E402
    classify_time_shift_matrix,
    example_flat_affinity,
    example_histogram_blind,
    example_truncation,
    rotate_antagonist_labels,
    rq1_hand_instrument,
    rq3_hand_channel,
)

TIMES = ("past", "now", "future")

# Pre-registered in design.md before any confirmatory seed. These are the
# program's own stage-0 fixtures, copied verbatim from
# codontrace-genesis/src/codontrace/genesis/campaigns/
# discovery_program_20260929_stage0.py, whose sha256 is recorded below.
FIXTURES: dict[str, dict[str, dict[str, float]]] = {
    "coevolve_contemporary": {
        "past": {"past": 0.70, "now": 0.20, "future": 0.15},
        "now": {"past": 0.25, "now": 0.80, "future": 0.30},
        "future": {"past": 0.20, "now": 0.35, "future": 0.60},
    },
    "lagged": {
        "past": {"past": 0.20, "now": 0.30, "future": 0.15},
        "now": {"past": 0.70, "now": 0.25, "future": 0.20},
        "future": {"past": 0.30, "now": 0.75, "future": 0.55},
    },
    "directional_arms_race": {
        "past": {"past": 0.20, "now": 0.40, "future": 0.60},
        "now": {"past": 0.30, "now": 0.50, "future": 0.70},
        "future": {"past": 0.40, "now": 0.60, "future": 0.90},
    },
    "frozen_flat": {h: {"past": 0.40, "now": 0.40, "future": 0.40} for h in TIMES},
    "host_only_zero": {h: {"past": 0.0, "now": 0.0, "future": 0.0} for h in TIMES},
}

SUPPORT_LABELS = {"contemporary_match", "lagged_match"}
CONTEMP_CELLS = (("now", "now"),)
LAG_CELLS = (("now", "past"), ("future", "now"))


def interaction_contrast(matrix: dict[str, dict[str, float]]) -> dict:
    cells = [matrix[h][a] for h in TIMES for a in TIMES]
    grand = sum(cells) / len(cells)
    row_mean = {h: sum(matrix[h][a] for a in TIMES) / 3.0 for h in TIMES}
    col_mean = {a: sum(matrix[h][a] for h in TIMES) / 3.0 for a in TIMES}
    inter = {
        h: {a: matrix[h][a] - row_mean[h] - col_mean[a] + grand for a in TIMES}
        for h in TIMES
    }
    flat = [(h, a, inter[h][a]) for h in TIMES for a in TIMES]
    i_max_h, i_max_a, i_max = max(flat, key=lambda t: t[2])
    i_min_h, i_min_a, i_min = min(flat, key=lambda t: t[2])
    n_positive = sum(1 for _, _, v in flat if v > 1e-12)
    n_negative = sum(1 for _, _, v in flat if v < -1e-12)
    i_contemp = sum(inter[h][a] for h, a in CONTEMP_CELLS) / len(CONTEMP_CELLS)
    i_lag = sum(inter[h][a] for h, a in LAG_CELLS) / len(LAG_CELLS)
    return {
        "grand_mean": round(grand, 10),
        "row_mean": {h: round(row_mean[h], 10) for h in TIMES},
        "col_mean": {a: round(col_mean[a], 10) for a in TIMES},
        "interaction": {h: {a: round(inter[h][a], 10) for a in TIMES} for h in TIMES},
        "i_contemp": round(i_contemp, 10),
        "i_lag": round(i_lag, 10),
        "i_max": {"cell": [i_max_h, i_max_a], "value": round(i_max, 10)},
        "i_min": {"cell": [i_min_h, i_min_a], "value": round(i_min, 10)},
        "n_positive_cells": n_positive,
        "n_negative_cells": n_negative,
        "uniform_increase": bool(n_negative == 0 and n_positive > 0),
    }


def rotate(matrix, source: dict[str, str]) -> dict[str, dict[str, float]]:
    return {h: {a: float(matrix[h][source[a]]) for a in TIMES} for h in TIMES}


def main() -> int:
    started = time.perf_counter()
    src_file = (
        REPO
        / "src"
        / "codontrace"
        / "genesis"
        / "campaigns"
        / "discovery_program_20260929_stage0.py"
    )
    fixture_source_sha = hashlib.sha256(src_file.read_bytes()).hexdigest()

    rows: list[dict] = []
    events: list[dict] = []
    for name, matrix in FIXTURES.items():
        contrast = interaction_contrast(matrix)
        label = classify_time_shift_matrix(matrix)
        rec = {
            "fixture": name,
            "matrix": matrix,
            "repo_label": label,
            "is_support_label": label in SUPPORT_LABELS,
            "contrast": contrast,
            "supports_fluctuating_selection": bool(
                label in SUPPORT_LABELS
                and (contrast["i_contemp"] > 0.0 or contrast["i_lag"] > 0.0)
                and not contrast["uniform_increase"]
            ),
        }
        rows.append(rec)
        events.append(
            {
                "schema_version": "rq1_stage0_fixture_v1",
                "record_role": "instrument_fixture_not_a_live_result",
                "fixture": name,
                "repo_label": label,
                "i_contemp": contrast["i_contemp"],
                "i_lag": contrast["i_lag"],
                "i_max_cell": contrast["i_max"]["cell"],
                "i_max_value": contrast["i_max"]["value"],
                "n_positive_cells": contrast["n_positive_cells"],
                "n_negative_cells": contrast["n_negative_cells"],
                "uniform_increase": contrast["uniform_increase"],
            }
        )

    # Controls: one deterministic label rotation as the repo implements it, and
    # the full 6-element permutation distribution of the antagonist time labels
    # on the coevolve fixture (the random time-label rotation control).
    rotated = rotate_antagonist_labels(FIXTURES["coevolve_contemporary"])
    rotation_control = {
        "repo_rotated_label": classify_time_shift_matrix(rotated),
        "repo_rotated_contrast": interaction_contrast(rotated),
    }
    perm_dist: list[dict] = []
    for perm in itertools.permutations(TIMES):
        source = {slot: perm[i] for i, slot in enumerate(TIMES)}
        m = rotate(FIXTURES["coevolve_contemporary"], source)
        lab = classify_time_shift_matrix(m)
        c = interaction_contrast(m)
        perm_dist.append(
            {
                "permutation": list(perm),
                "label": lab,
                "is_support_label": lab in SUPPORT_LABELS,
                "i_contemp": c["i_contemp"],
                "i_lag": c["i_lag"],
            }
        )
    n_support_perm = sum(1 for p in perm_dist if p["is_support_label"])
    randomisation = {
        "n_permutations": len(perm_dist),
        "n_support_label": n_support_perm,
        "fraction_support_label": round(n_support_perm / len(perm_dist), 10),
        "identity_permutation_label": next(
            p["label"] for p in perm_dist if p["permutation"] == list(TIMES)
        ),
        "distribution": perm_dist,
        "note": (
            "The randomisation control is over the 6 time-label permutations of "
            "one pre-registered fixture. It has no seed-level unit because no "
            "live population history exists to replicate; it is a label null, "
            "not a cluster interval."
        ),
    }

    payload = {
        "schema_version": "rq1_stage0_fixtures_v1",
        "fixture_source_path": str(src_file.relative_to(REPO)),
        "fixture_source_sha256": fixture_source_sha,
        "support_labels": sorted(SUPPORT_LABELS),
        "primary_scalars": {
            "i_contemp": "(now,now) interaction contrast",
            "i_lag": "mean of (now,past) and (future,now) interaction contrasts",
        },
        "fixtures": rows,
        "rotation_control": rotation_control,
        "randomisation_control": randomisation,
        "repo_stage0": {
            "rq1_hand_instrument": rq1_hand_instrument(),
            "rq3_hand_channel": rq3_hand_channel(),
            "example_histogram_blind": example_histogram_blind(),
            "example_flat_affinity": example_flat_affinity(),
            "example_truncation": example_truncation(),
        },
        "population_run": False,
        "hypothesis_supported": False,
        "red_queen_proved": False,
    }
    (RAW / "stage0_fixtures.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    with (RAW / "stage0_fixture_events.jsonl").open("w", encoding="utf-8") as handle:
        for row in events:
            handle.write(json.dumps(row, sort_keys=True) + "\n")
        handle.flush()
    print(
        json.dumps(
            {
                "fixtures": {r["fixture"]: r["repo_label"] for r in rows},
                "randomisation_n_support_label": n_support_perm,
                "hypothesis_supported": False,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
