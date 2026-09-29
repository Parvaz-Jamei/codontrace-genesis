import time

from sex_twofold import CELLS, run_cell

started = time.perf_counter()
for spec in CELLS:
    row = run_cell(7000, parasite=spec["parasite"], cost=spec["cost"], generations=300, debug=True)
    series = row["sexual_series"]
    inf = row["infected_series"]
    marks = [f"{series[i]:.3f}/{inf[i]:.2f}" for i in range(0, 300, 50)]
    print(
        f"p={int(spec['parasite'])} c={int(spec['cost'])} "
        f"final={row['sexual_final_mean']:.4f} auc={row['sexual_auc']:.4f} "
        f"div={row['diversity_final_mean']:.1f} ledger={row['ledger_max_residual']:.2e}",
        flush=True,
    )
    print("   sexual/infected every 50 gens:", " | ".join(marks), flush=True)
print(f"elapsed {time.perf_counter() - started:.1f}s", flush=True)
