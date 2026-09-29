import json

from run_benchmark import run_config

for eps, depth in ((0.0, 20), (0.8, 20)):
    cfg = run_config(eps, depth)
    rows = cfg["per_mutation"]
    if rows:
        row = rows[0]
        print(
            "  first mutation:",
            row["mutation"],
            "freq=%.2f" % row["frequency"],
            "ATT=%.6f" % row["att_fitness"],
            "ATT_sd=%.6f" % row["att_fitness_sd"],
            "naive=%.4f" % row["naive_fitness"],
            "adj=%.4f" % row["adjusted_fitness"],
            "sel_bias=%.4f" % row["selection_bias_fitness"],
            "spec_bias=%.6f" % row["specification_bias_fitness"],
            "identity_res=%.2e" % row["identity_residual_fitness"],
            flush=True,
        )
    else:
        print("  NO MUTATIONS SELECTED", flush=True)

print("SMOKE_BENCHMARK_DONE", flush=True)
