"""Locked RQ-1 constants and the pure interaction contrast.

The pressure cell and the classifiers are imported only after the three meter
files match the blobs shared by ``6187ff4`` and ``a1d97e9``. A mismatch stops
the derived analysis. This module does not put a machine path on ``sys.path``
and it does not run a simulation.
"""

from __future__ import annotations

import hashlib
import sys
from pathlib import Path

COMMIT = "6187ff4"
SEEDS = (5701, 5702, 5703, 5704, 5705, 5706, 5707, 5708)
GENERATIONS = 200
TIMES = ("past", "now", "future")
SLOTS = {"past": 90, "now": 100, "future": 110}
REGIMES = {"copassaged": "coevolve", "fixed": "frozen"}
KAPPA = 1.2
SUPPORT_LABELS = {"contemporary_match", "lagged_match"}
CONFIG_DIGEST = (
    "rq1_confirmatory:d44a70140eeef5876ea68c838ca442de38f5e05cfeaeabd71bab2be38479c807"
)
LOCKED_CONFIG = {
    "test": "RQ-1",
    "commit": COMMIT,
    "seeds": list(SEEDS),
    "generations": GENERATIONS,
    "times": list(TIMES),
    "slots": SLOTS,
    "regimes": REGIMES,
    "kappa": KAPPA,
    "contact_mode": "full_matrix",
    "arms": ["contemporary", "lagged", "frozen"],
    "estimator": "host_time_x_antagonist_time_interaction_contrast",
    "controls": ["frozen_exactly_zero", "shuffled_time_labels_6_permutations"],
    "interval": "causal_validation._paired_interval (95% paired t)",
    "flags_locked_false": ["hypothesis_supported", "red_queen_proved"],
}

# SHA-256 of LF bytes. Identical at 6187ff4 and a1d97e9.
METER_PINS = {
    "src/codontrace/genesis/measurements/rq_frequency_clocks.py": (
        "00b84f0ca638ba9796a9c5d0c899aedd61df4713e78a171ecd123e937a240324"
    ),
    "src/codontrace/genesis/causal_validation.py": (
        "395f23a52d1ec15c93722428746a6149ae45acb01fb107803523ab12eba2832c"
    ),
    "src/codontrace/genesis/campaigns/discovery_program_20260929_stage0.py": (
        "beeb2c4dc3ed077d5fdb942d2453653e8c8cd9b98f42a0c96043db93c1c20476"
    ),
}

_paired_interval = None
classify_time_shift_matrix = None
pressure_cell = None


def repo_root_from(start: Path) -> Path:
    for candidate in (start, *start.parents):
        if (candidate / "src" / "codontrace").is_dir():
            return candidate
    raise SystemExit(f"no repository root above {start}")


def assert_meter_pins(root: Path) -> None:
    for rel, expected in METER_PINS.items():
        path = root / rel
        if not path.is_file():
            raise SystemExit(f"meter pin missing: {rel}")
        data = path.read_bytes().replace(b"\r\n", b"\n").replace(b"\r", b"\n")
        got = hashlib.sha256(data).hexdigest()
        if got != expected:
            raise SystemExit(f"meter pin mismatch for {rel}: got {got}")


def bind_meter(root: Path) -> None:
    """Import the pinned meters. Stops if the checkout is not the pinned blobs."""

    global _paired_interval, classify_time_shift_matrix, pressure_cell
    assert_meter_pins(root)
    src = str(root / "src")
    if src not in sys.path:
        sys.path.insert(0, src)
    from codontrace.genesis.campaigns.discovery_program_20260929_stage0 import (
        classify_time_shift_matrix as _classify,
    )
    from codontrace.genesis.causal_validation import _paired_interval as _interval
    from codontrace.genesis.measurements.rq_frequency_clocks import (
        realised_conditional_host_pressure,
    )

    def _pressure(host_freq: dict, ant_classes: list) -> float:
        if not host_freq or not ant_classes:
            return 0.0
        windows = {c: str(c).replace("|", "") for c in set(host_freq) | set(ant_classes)}
        res = realised_conditional_host_pressure(
            {c: windows[c] for c in host_freq},
            {c: windows[c] for c in ant_classes},
            contact_mode="full_matrix",
            virulence=8.0,
            steal_fraction=0.15,
        )
        pressure = res["pressure"]
        return float(sum(w * float(pressure[c]) for c, w in host_freq.items()))

    _paired_interval = _interval
    classify_time_shift_matrix = _classify
    pressure_cell = _pressure


def contrast(matrix):
    cells = [float(matrix[h][a]) for h in TIMES for a in TIMES]
    grand = sum(cells) / len(cells)
    row = {h: sum(float(matrix[h][a]) for a in TIMES) / 3.0 for h in TIMES}
    col = {a: sum(float(matrix[h][a]) for h in TIMES) / 3.0 for a in TIMES}
    inter = {
        h: {a: float(matrix[h][a]) - row[h] - col[a] + grand for a in TIMES} for h in TIMES
    }
    best = max(((h, a) for h in TIMES for a in TIMES), key=lambda c: inter[c[0]][c[1]])
    vals = [inter[h][a] for h in TIMES for a in TIMES]
    npos = sum(1 for v in vals if v > 1e-15)
    nneg = sum(1 for v in vals if v < -1e-15)
    return {
        "i_contemp": round(inter["now"]["now"], 10),
        "i_lag": round((inter["now"]["past"] + inter["future"]["now"]) / 2.0, 10),
        "i_max_cell": list(best),
        "i_max": round(inter[best[0]][best[1]], 10),
        "n_positive_cells": npos,
        "n_negative_cells": nneg,
        "uniform_increase": bool(npos > 0 and nneg == 0),
    }


def archive_inventory(raw: Path) -> list[dict[str, object]]:
    from codontrace.genesis.archive_io import resolve_jsonl

    rows = []
    for seed in SEEDS:
        def _has(name: str) -> bool:
            try:
                resolve_jsonl(raw / name)
            except FileNotFoundError:
                return False
            return True

        seed_json = raw / f"seed_{seed}.json"
        rows.append(
            {
                "seed": seed,
                "events": _has(f"events_seed{seed}.jsonl"),
                "population": _has(f"population_seed{seed}.jsonl"),
                "summary": _has(f"summary_seed{seed}.jsonl"),
                "seed_json": seed_json.is_file(),
            }
        )
    return rows
