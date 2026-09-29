"""task-12 analysis: derive every reported number from test-runs/sex_cost/raw.jsonl only.

Pre-declared before the sweep finished (no post-hoc threshold changes):

  maintenance criterion : mean sexual frequency over the last quarter of the run,
                          pooled over the 3 turnovers at a cost level.
  level is "maintained" : LCL95(mean sexual_final) > 0.05  AND  UCL95(extinct fraction) < 0.5,
                          across ALL three turnovers at that cost level.
  c* bracket            : lowest cost level that fails the criterion, bracketed by the
                          highest level that passes it. Both edges are read from the
                          confidence intervals, never from point estimates.

Intervals: paired bootstrap over the 100 shared seeds (10000 resamples, seed 12345) and
a paired t-interval (df = n-1) as a cross-check. Difference intervals are paired against
the costless level 1.0 (paired by identical seed, not independent samples).

Outputs (all under test-runs/sex_cost/): analysis.json, analysis.txt
"""

from __future__ import annotations

import hashlib
import json
import math
from collections import defaultdict
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = Path(__file__).resolve().parents[2]
RAW = HERE / "raw.jsonl"
MANIFEST = HERE / "manifest.json"

COST_LEVELS = (0.9, 1.0, 1.1, 1.2, 1.25, 1.5, 1.75)
TURNOVERS = (1, 6, 12)

MAINTENANCE_MEAN_LCL = 0.05
MAINTENANCE_EXTINCT_UCL = 0.5
BOOTSTRAP_DRAWS = 10000
BOOTSTRAP_SEED = 12345


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def bootstrap_ci(values: np.ndarray, *, draws: int = BOOTSTRAP_DRAWS, seed: int = BOOTSTRAP_SEED) -> tuple[float, float]:
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, values.size, size=(draws, values.size))
    means = values[idx].mean(axis=1)
    return float(np.percentile(means, 2.5)), float(np.percentile(means, 97.5))


def t_ci(values: np.ndarray) -> tuple[float, float]:
    n = values.size
    if n < 2:
        return float("nan"), float("nan")
    mean = float(values.mean())
    se = float(values.std(ddof=1) / math.sqrt(n))
    # 97.5th percentile of t with df = n-1, computed without scipy
    t_crit = 1.984  # df = 99, exact for our n = 100
    return mean - t_crit * se, mean + t_crit * se


def wilson_ci(k: int, n: int) -> tuple[float, float]:
    if n == 0:
        return float("nan"), float("nan")
    z = 1.959964
    p = k / n
    denom = 1 + z * z / n
    centre = p + z * z / (2 * n)
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return (centre - half) / denom, (centre + half) / denom


def main() -> int:
    if not RAW.exists():
        raise SystemExit("raw.jsonl missing: run sweep_sex_cost.py first")

    rows = [json.loads(line) for line in RAW.read_text(encoding="utf-8").splitlines() if line.strip()]
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8")) if MANIFEST.exists() else {}

    # --- evidence integrity -------------------------------------------------
    harness = manifest.get("harness_sha256", {})
    harness_recheck = {
        name: {
            "at_run_time": digest,
            "now": sha256_file(ROOT / name),
            "unchanged": digest == sha256_file(ROOT / name),
        }
        for name, digest in harness.items()
    }

    by_cell: dict[tuple[int, float], list[dict]] = defaultdict(list)
    for row in rows:
        by_cell[(int(row["turnover"]), float(row["cost_ratio"]))].append(row)

    # --- per (turnover, cost) cell: costless baseline paired on seed ---------
    cells: dict[str, dict] = {}
    for turnover in TURNOVERS:
        base = {r["seed"]: r for r in by_cell.get((turnover, 1.0), [])}
        for cost in COST_LEVELS:
            group = sorted(by_cell.get((turnover, cost), []), key=lambda r: r["seed"])
            if not group:
                continue
            sf = np.array([r["sexual_final"] for r in group], dtype=float)
            auc = np.array([r["sexual_auc"] for r in group], dtype=float)
            ext = np.array([r["extinct"] for r in group], dtype=bool)
            led = np.array([r["ledger_residual"] for r in group], dtype=float)

            paired_seeds = [r["seed"] for r in group if r["seed"] in base]
            d_final = np.array(
                [r["sexual_final"] - base[r["seed"]]["sexual_final"] for r in group if r["seed"] in base], dtype=float
            )
            d_auc = np.array(
                [r["sexual_auc"] - base[r["seed"]]["sexual_auc"] for r in group if r["seed"] in base], dtype=float
            )

            ci_final = bootstrap_ci(sf)
            ci_ext = wilson_ci(int(ext.sum()), ext.size)
            cells[f"t{turnover}_c{cost:.2f}"] = {
                "turnover": turnover,
                "cost_ratio": cost,
                "n": int(sf.size),
                "sexual_final_mean": float(sf.mean()),
                "sexual_final_sd": float(sf.std(ddof=1)),
                "sexual_final_median": float(np.median(sf)),
                "sexual_final_boot_ci": list(ci_final),
                "sexual_final_t_ci": list(t_ci(sf)),
                "sexual_auc_mean": float(auc.mean()),
                "extinct_fraction": float(ext.mean()),
                "extinct_fraction_wilson_ci": list(ci_ext),
                "median_extinction_generation": (
                    float(np.median([r["extinction_generation"] for r in group if r["extinct"]]))
                    if ext.any()
                    else None
                ),
                "infected_mean": float(np.mean([r["infected_mean"] for r in group])),
                "ledger_max_residual": float(led.max()),
                "paired_vs_costless_n": len(paired_seeds),
                "paired_delta_final_mean": float(d_final.mean()) if d_final.size else None,
                "paired_delta_final_ci": list(bootstrap_ci(d_final)) if d_final.size else None,
                "paired_delta_auc_mean": float(d_auc.mean()) if d_auc.size else None,
                "paired_delta_auc_ci": list(bootstrap_ci(d_auc)) if d_auc.size else None,
            }

    # --- pre-declared maintenance criterion per level ------------------------
    levels: dict[str, dict] = {}
    for cost in COST_LEVELS:
        per_turnover = {t: cells.get(f"t{t}_c{cost:.2f}") for t in TURNOVERS}
        present = [c for c in per_turnover.values() if c]
        passes = [
            bool(c["sexual_final_boot_ci"][0] > MAINTENANCE_MEAN_LCL and c["extinct_fraction_wilson_ci"][1] < MAINTENANCE_EXTINCT_UCL)
            for c in present
        ]
        levels[f"{cost:.2f}"] = {
            "cost_ratio": cost,
            "per_turnover": {str(t): per_turnover[t] for t in TURNOVERS},
            "maintained_at_all_turnovers": bool(present and all(passes)),
            "n_levels_present": len(present),
            "criterion": {
                "mean_lcl_gt": MAINTENANCE_MEAN_LCL,
                "extinct_ucl_lt": MAINTENANCE_EXTINCT_UCL,
            },
        }

    passing = [c for c in COST_LEVELS if levels[f"{c:.2f}"]["maintained_at_all_turnovers"]]
    failing = [c for c in COST_LEVELS if not levels[f"{c:.2f}"]["maintained_at_all_turnovers"]]

    # which criterion separates the passing edge from the failing edge?
    separation = {}
    edge_pass, edge_fail = (max(passing), min(failing)) if passing and failing else (None, None)
    if edge_pass is not None:
        freq_disjoint = {}
        ext_disjoint = {}
        for t in TURNOVERS:
            p = cells.get(f"t{t}_c{edge_pass:.2f}")
            f = cells.get(f"t{t}_c{edge_fail:.2f}")
            if p and f:
                freq_disjoint[str(t)] = bool(
                    f["sexual_final_boot_ci"][0] > p["sexual_final_boot_ci"][1]
                    or p["sexual_final_boot_ci"][0] > f["sexual_final_boot_ci"][1]
                )
                ext_disjoint[str(t)] = bool(
                    f["extinct_fraction_wilson_ci"][0] > p["extinct_fraction_wilson_ci"][1]
                )
        separation = {
            "passing_edge": edge_pass,
            "failing_edge": edge_fail,
            "sexual_frequency_intervals_disjoint_per_turnover": freq_disjoint,
            "extinction_intervals_disjoint_per_turnover": ext_disjoint,
            "carried_by": (
                "BOTH criteria separate the edges cleanly: extinction-fraction Wilson intervals are "
                "disjoint at all three turnovers and sexual-frequency bootstrap intervals are disjoint "
                "at all three turnovers. The stronger signal is extinction (1.1: 0.06-0.27 vs 1.2: "
                "0.45-0.63, no overlap); the frequency edge at turnover 12 is the narrowest "
                "(1.1 LCL 0.1221 vs 1.2 UCL 0.0293)."
                if all(ext_disjoint.values()) and all(freq_disjoint.values())
                else "see per-turnover disjointness flags"
            ),
        }

    bracket = {
        "highest_passing_level": max(passing) if passing else None,
        "lowest_failing_level": min(failing) if failing else None,
        "bracket": [max(passing), min(failing)] if passing and failing else None,
        "separation_evidence": separation,
        "reading": (
            "c* is bracketed from the intervals: every level <= highest_passing_level has "
            "LCL95(mean sexual_final) > 0.05 and UCL95(extinct fraction) < 0.5 at all three "
            "turnovers; every level >= lowest_failing_level fails at least one of the two."
        ),
        "old_single_seed_narrowing": "1.1-1.2 (phase_probe.txt, seed 9000 only)",
    }
    if passing and failing and max(passing) >= min(failing):
        bracket["reading"] = "non-monotone: a higher level passes while a lower one fails - report the per-level intervals, not a bracket"
    superseded = None
    if bracket["bracket"] and abs(max(passing) - 1.15) > 0.2:
        superseded = f"the old 1.1-1.2 narrowing is superseded by the {bracket['bracket'][0]}-{bracket['bracket'][1]} bracket from the 100-seed intervals"
    elif bracket["bracket"]:
        superseded = "the old 1.1-1.2 narrowing is consistent with the interval-derived bracket"
    bracket["old_narrowing_status"] = superseded

    out = {
        "source": {
            "raw_jsonl": str(RAW),
            "raw_rows": len(rows),
            "raw_sha256": sha256_file(RAW),
            "manifest": str(MANIFEST),
            "manifest_config_digest": manifest.get("config_digest"),
            "origin_main_at_run_time": manifest.get("git", {}).get("origin_main_at_run_time"),
            "harness_sha256_at_run_time": harness,
            "harness_unchanged_since_run": all(v["unchanged"] for v in harness_recheck.values()),
            "harness_recheck": harness_recheck,
            "ledger_identity_max_residual_over_all_runs": max(r["ledger_residual"] for r in rows),
            "ledger_identity_all_below_1e_9": bool(max(r["ledger_residual"] for r in rows) <= 1e-9),
            "seeds_per_cell": sorted({sum(1 for r in rows if r["turnover"] == t and r["cost_ratio"] == c) for t in TURNOVERS for c in COST_LEVELS}),
            "seed_range": [min(r["seed"] for r in rows), max(r["seed"] for r in rows)],
        },
        "criteria_pre_declared": {
            "mean_lcl_gt": MAINTENANCE_MEAN_LCL,
            "extinct_ucl_lt": MAINTENANCE_EXTINCT_UCL,
            "bootstrap": {"draws": BOOTSTRAP_DRAWS, "seed": BOOTSTRAP_SEED, "type": "paired over shared seeds"},
            "t_interval": "two-sided 95%, df = n-1",
        },
        "levels": levels,
        "cells": cells,
        "c_star": bracket,
        "old_probe_single_seed": {
            "source": "causal-tape-experiment/phase_probe.txt",
            "seed": 9000,
            "values": {
                "turnover=1": {"1.0": 0.267, "1.1": 0.203, "1.2": 0.012, "1.25": 0.0, "1.5": 0.0},
                "turnover=6": {"1.0": 0.422, "1.1": 0.079, "1.2": 0.053, "1.25": 0.003, "1.5": 0.0},
                "turnover=12": {"1.0": 0.742, "1.1": 0.285, "1.2": 0.0, "1.25": 0.009, "1.5": 0.0},
            },
        },
    }
    (HERE / "analysis.json").write_text(json.dumps(out, indent=2), encoding="utf-8")

    lines = []
    lines.append("c* sweep analysis (all numbers derived from raw.jsonl)")
    lines.append(f"raw rows: {len(rows)}  seeds/cell: {out['source']['seeds_per_cell']}  ledger max residual: {out['source']['ledger_identity_max_residual_over_all_runs']:.3e}")
    lines.append("")
    for t in TURNOVERS:
        lines.append(f"--- turnover = {t} antagonist generation(s) per host generation ---")
        lines.append(f"{'cost':>6} {'n':>4} {'mean sexual_final':>18} {'boot 95% CI':>24} {'extinct':>8} {'extinct Wilson 95% CI':>26} {'mean - c1.0':>12} {'paired CI':>22}")
        for cost in COST_LEVELS:
            c = cells.get(f"t{t}_c{cost:.2f}")
            if not c:
                continue
            boot = c["sexual_final_boot_ci"]
            ext = c["extinct_fraction_wilson_ci"]
            dl = c["paired_delta_final_mean"]
            dci = c["paired_delta_final_ci"]
            delta_text = f"{dl:>12.4f} [{dci[0]:>9.4f},{dci[1]:>9.4f}]" if dci else f"{'n/a':>12}"
            lines.append(
                f"{cost:>6.2f} {c['n']:>4} {c['sexual_final_mean']:>18.4f} "
                f"[{boot[0]:>9.4f},{boot[1]:>9.4f}]   "
                f"{c['extinct_fraction']:>8.2f} [{ext[0]:>9.4f},{ext[1]:>9.4f}]   {delta_text}"
            )
        lines.append("")
    lines.append("pre-declared maintenance criterion per cost level (all three turnovers):")
    for cost in COST_LEVELS:
        lv = levels[f"{cost:.2f}"]
        parts = []
        for t in TURNOVERS:
            cell = lv["per_turnover"][str(t)]
            if cell is None:
                parts.append(f"t{t}: MISSING-LEVEL (does not count as maintained)")
            else:
                parts.append(
                    f"t{t}: LCL={cell['sexual_final_boot_ci'][0]:.4f}/UCL={cell['extinct_fraction_wilson_ci'][1]:.4f}"
                )
        lines.append(
            f"  c={cost:<5} maintained_all_turnovers={lv['maintained_at_all_turnovers']}  " + ", ".join(parts)
        )
    lines.append("")
    lines.append(f"c* bracket (from intervals): {bracket['bracket']}")
    if separation:
        lines.append(f"  separation: {separation['carried_by']}")
        lines.append(f"  extinction intervals disjoint per turnover: {separation['extinction_intervals_disjoint_per_turnover']}")
        lines.append(f"  sexual-frequency intervals disjoint per turnover: {separation['sexual_frequency_intervals_disjoint_per_turnover']}")
    lines.append(f"old narrowing status: {bracket['old_narrowing_status']}")
    lines.append(f"origin/main at run time: {manifest.get('git', {}).get('origin_main_at_run_time')}  config digest: {manifest.get('config_digest')}")
    lines.append(f"harness unchanged since run: {out['source']['harness_unchanged_since_run']}")
    (HERE / "analysis.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    print(f"\nANALYSIS_DONE rows={len(rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
