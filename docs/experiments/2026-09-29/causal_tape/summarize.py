"""Compact read-out of results/benchmark_results.json."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

RESULTS = Path(__file__).resolve().parent / "results" / "benchmark_results.json"
data = json.loads(RESULTS.read_text(encoding="utf-8"))

print("=" * 92)
print("CausalTape-1 — verdicts")
print("=" * 92)
for key, value in data["verdicts"].items():
    flag = value.get("passed")
    mark = {True: "PASS", False: "FAIL", None: "--"}[flag]
    print(f"[{mark}] {key}")
    for field, item in value.items():
        if field == "passed":
            continue
        if isinstance(item, list) and len(item) > 8:
            continue
        print(f"        {field}: {item}")

print()
print("=" * 92)
print("G = 40 sweep")
print("=" * 92)
header = f"{'eps':>5} {'innov':>6} {'ATT_med':>8} {'sd(ATT)':>9} {'sel_bias':>9} {'spec_bias':>10} {'|tau_epi|':>10} {'nullband':>9}"
print(header)
for eps in (0.0, 0.05, 0.1, 0.2, 0.4, 0.8):
    cfg = data["configs"][f"eps{eps}_G40"]
    rows = cfg["per_mutation"]
    att = np.array([r["att_fitness"] for r in rows])
    sd = np.array([r["att_fitness_sd"] for r in rows])
    sel = np.array([r["selection_bias_fitness"] for r in rows])
    spec = np.array([r["specification_bias_fitness"] for r in rows])
    epi = np.array([r["tau_epi_fitness"] for r in rows])
    print(
        f"{eps:>5} {cfg['innovation_rate']:>6.3f} {np.median(att):>8.4f} {np.median(sd):>9.2e} "
        f"{np.median(sel):>9.4f} {np.median(np.abs(spec)):>10.4f} {np.median(np.abs(epi)):>10.4f} "
        f"{cfg['null_band_across_loci_p95']:>9.4f}"
    )

print()
print("=" * 92)
print("depth sweep at eps = 0.8")
print("=" * 92)
print(f"{'G':>4} {'innov':>6} {'sd(ATT)':>9} {'|spec_bias|':>11} {'|tau_epi|':>10} {'nullband':>9}")
for depth in (20, 40, 80):
    cfg = data["configs"][f"eps0.8_G{depth}"]
    rows = cfg["per_mutation"]
    print(
        f"{depth:>4} {cfg['innovation_rate']:>6.3f} "
        f"{np.median([r['att_fitness_sd'] for r in rows]):>9.4f} "
        f"{np.median([abs(r['specification_bias_fitness']) for r in rows]):>11.4f} "
        f"{np.median([abs(r['tau_epi_fitness']) for r in rows]):>10.4f} "
        f"{cfg['null_band_across_loci_p95']:>9.4f}"
    )

print()
print("=" * 92)
print("per-mutation detail, eps = 0.0 / G = 40")
print("=" * 92)
print(f"{'mutation':>10} {'freq':>5} {'ATT':>10} {'sd(ATT)':>10} {'naive':>9} {'sel_bias':>9} {'adj':>9} {'spec_bias':>11}")
for row in data["configs"]["eps0.0_G40"]["per_mutation"]:
    print(
        f"{row['mutation']:>10} {row['frequency']:>5.2f} {row['att_fitness']:>10.6f} "
        f"{row['att_fitness_sd']:>10.2e} {row['naive_fitness']:>9.4f} {row['selection_bias_fitness']:>9.4f} "
        f"{row['adjusted_fitness']:>9.6f} {row['specification_bias_fitness']:>11.2e}"
    )

print()
print("=" * 92)
print("per-mutation detail, eps = 0.8 / G = 40")
print("=" * 92)
print(f"{'mutation':>10} {'freq':>5} {'ATT':>9} {'sd(ATT)':>8} {'tau_dir':>8} {'tau_epi':>9} {'naive':>9} {'sel_bias':>9} {'adj':>9} {'spec_bias':>9}")
for row in data["configs"]["eps0.8_G40"]["per_mutation"]:
    print(
        f"{row['mutation']:>10} {row['frequency']:>5.2f} {row['att_fitness']:>9.4f} {row['att_fitness_sd']:>8.4f} "
        f"{row['tau_direct_fitness']:>8.4f} {row['tau_epi_fitness']:>9.4f} {row['naive_fitness']:>9.4f} "
        f"{row['selection_bias_fitness']:>9.4f} {row['adjusted_fitness']:>9.4f} {row['specification_bias_fitness']:>9.4f}"
    )

print()
print("=" * 92)
print("tightest zero-variance check at eps = 0 (exact additivity)")
print("=" * 92)
all_sd = [
    row["att_fitness_sd"]
    for eps in (0.0,)
    for depth in (20, 40, 80)
    for row in data["configs"][f"eps{eps}_G{depth}"]["per_mutation"]
]
print(f"max sd(ATT) over {len(all_sd)} focal mutations at eps=0 : {max(all_sd):.3e}")
print(f"max |identity residual| naive - (ATT + sel_bias)         : "
      f"{max(row['identity_residual_fitness'] for cfg in data['configs'].values() for row in cfg['per_mutation']):.3e}")

print()
print("=" * 92)
print("engine-native substrate A (agent / closed ATP ledger)")
print("=" * 92)
agent = data["agent_instance"]
print(f"outcome: {agent['outcome']}, seeds={agent['n_seeds']}, depth={agent['depth']}, "
      f"mean={agent['fitness_mean']:.4f}, sd={agent['fitness_sd']:.4f}")
print(f"{'mutation':>10} {'freq':>5} {'ATT':>9} {'sd(ATT)':>9} {'naive':>9} {'sel_bias':>9} {'adj':>9} {'spec_bias':>9}")
for row in agent["per_mutation"]:
    print(
        f"{row['mutation']:>10} {row['frequency']:>5.2f} {row['att']:>9.4f} {row['att_sd']:>9.4f} "
        f"{row['naive']:>9.4f} {row['selection_bias']:>9.4f} {row['adjusted']:>9.4f} {row['specification_bias']:>9.4f}"
    )
