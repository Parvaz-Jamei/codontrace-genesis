"""Throwaway independent verification of results/estimand_split.json.

Recomputes a sample of the reported numbers through a deliberately different code
path (explicit pair loops, lstsq on the full 3000-row design, no shared helpers)
and checks the identity, the aggregates, and bootstrap determinism.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

import estimand_split as es

HERE = Path(__file__).resolve().parent
REPORT = json.loads((HERE / "results" / "estimand_split.json").read_text(encoding="utf-8"))

failures: list[str] = []


def check(name: str, condition: bool, detail: str = "") -> None:
    print(f"[{'PASS' if condition else 'FAIL'}] {name} {detail}")
    if not condition:
        failures.append(name)


# ---------------------------------------------------------------- structure
required_top = {
    "notes",
    "reproduction_check",
    "per_config",
    "by_eps",
    "by_coupling_draw",
    "correlation",
    "bootstrap_reroute_share_eps_max",
    "verdict",
    "bootstrap",
}
check("json top-level keys", required_top <= set(REPORT), str(sorted(REPORT)))
check("18 configurations", len(REPORT["per_config"]) == 18)
check("16 mutations each", all(len(c["per_mutation"]) == 16 for c in REPORT["per_config"].values()))
check("no re-simulation claim in notes", any("no re-simulation" in n or "whole-tape effect" in n for n in REPORT["notes"]))
check(
    "model-based caveat present in notes",
    any("MODEL-BASED one-bit quantity, NOT an interventional one" in n for n in REPORT["notes"]),
)

# ------------------------------------------------- independent recomputation
worst = {"beta": 0.0, "whole": 0.0, "onebit": 0.0, "i": 0.0, "ii": 0.0, "tot": 0.0}
pairs = [(c["key"], c["env_seed"], c["eps"]) for c in REPORT["per_config"].values()]
for key, env_seed, eps in pairs:
    with np.load(HERE / "datasets" / f"{key}.npz") as data:
        y = data["fitness"].astype(float)
        X = data["bits"].astype(float)
        C = data["counterfactual"].astype(float)
        P = data["present"].astype(bool)
        muts = [str(m) for m in data["mutations"]]
    n = X.shape[0]
    A = np.hstack([np.ones((n, 1)), X])
    beta = np.linalg.lstsq(A, y, rcond=None)[0][1:]
    # independent quadratic construction: explicit python pair loop
    cols = [np.ones(n), *[X[:, i] for i in range(18)]]
    pair_index = {}
    for i in range(18):
        for j in range(i + 1, 18):
            pair_index[(i, j)] = len(cols)
            cols.append(X[:, i] * X[:, j])
    Q = np.column_stack(cols)
    coef = np.linalg.lstsq(Q, y, rcond=None)[0]
    rows = {m["mutation"]: m for m in REPORT["per_config"][key]["per_mutation"]}
    for j, mid in enumerate(muts):
        bit = int(mid.split(":")[0])
        exposed = P[:, j]
        att_whole = float(np.mean((y - C[:, j])[exposed]))
        # per-seed one-bit contrast, written out longhand
        per_seed = np.full(n, coef[1 + bit])
        for l in range(18):
            if l == bit:
                continue
            a, b = (bit, l) if bit < l else (l, bit)
            per_seed = per_seed + coef[pair_index[(a, b)]] * X[:, l]
        att_onebit = float(np.mean(per_seed[exposed]))
        row = rows[mid]
        worst["beta"] = max(worst["beta"], abs(beta[bit] - row["beta"]))
        worst["whole"] = max(worst["whole"], abs(att_whole - row["att_whole_tape"]))
        worst["onebit"] = max(worst["onebit"], abs(att_onebit - row["att_onebit_proxy_exposed"]))
        worst["i"] = max(worst["i"], abs((beta[bit] - att_onebit) - row["component_i_misspec"]))
        worst["ii"] = max(worst["ii"], abs((att_onebit - att_whole) - row["component_ii_reroute"]))
        worst["tot"] = max(worst["tot"], abs((beta[bit] - att_whole) - row["total_gap"]))

for name, value in worst.items():
    check(f"independent recomputation max |diff| ({name})", value < 1e-9, f"{value:.3e}")

# ------------------------------------------------------------------ identity
ident = max(
    abs(m["total_gap"] - m["component_i_misspec"] - m["component_ii_reroute"])
    for c in REPORT["per_config"].values()
    for m in c["per_mutation"]
)
check("per-mutation identity total = (i) + (ii)", ident < 1e-12, f"{ident:.3e}")

# ------------------------------------------------------- aggregates recompute
for cfg in REPORT["per_config"].values():
    ci = np.array([abs(m["component_i_misspec"]) for m in cfg["per_mutation"]])
    cii = np.array([abs(m["component_ii_reroute"]) for m in cfg["per_mutation"]])
    tot = np.array([abs(m["total_gap"]) for m in cfg["per_mutation"]])
    ok = (
        abs(np.median(ci) - cfg["median_abs_component_i_misspec"]) < 1e-12
        and abs(np.mean(ci) - cfg["mean_abs_component_i_misspec"]) < 1e-12
        and abs(np.median(cii) - cfg["median_abs_component_ii_reroute"]) < 1e-12
        and abs(np.mean(cii) - cfg["mean_abs_component_ii_reroute"]) < 1e-12
        and abs(np.median(tot) - cfg["median_abs_total_gap"]) < 1e-12
        and abs(np.mean(tot) - cfg["mean_abs_total_gap"]) < 1e-12
    )
    if not ok:
        check(f"aggregates for {cfg['key']}", False)
        break
else:
    check("per-config medians and means recomputed from per_mutation", True)

# ------------------------------------------------------- published comparison
published = json.loads((HERE / "results" / "heavy2_results.json").read_text(encoding="utf-8"))
worst_pub = 0.0
for key, cfg in REPORT["per_config"].items():
    rows = {r["mutation"]: r for r in published["configs"][key]["per_mutation"]}
    for m in cfg["per_mutation"]:
        worst_pub = max(worst_pub, abs(m["total_gap"] - rows[m["mutation"]]["specification_bias"]))
check("reproduces published specification_bias", worst_pub < 1e-9, f"{worst_pub:.3e}")

# ------------------------------------------------------------ bootstrap determinism
original_draws = es.BOOTSTRAP_DRAWS
es.BOOTSTRAP_DRAWS = 20
configs = es.load_configs()
top = [c for c in configs if c["eps"] == 0.8]
first = es.bootstrap(top)
second = es.bootstrap(top)
es.BOOTSTRAP_DRAWS = original_draws
same = json.dumps(first, sort_keys=True) == json.dumps(second, sort_keys=True)
check("bootstrap deterministic for a fixed seed", same)
value = REPORT["bootstrap_reroute_share_eps_max"]["pooled_share_of_total_ratio_of_medians"]
check(
    "bootstrap interval covers the point estimate",
    value["median"] > 0.5 and 0.0 < value["ci95"][0] < value["median"] < value["ci95"][1] < 1.1,
    str(value),
)
check("bootstrap used 500 draws", value["draws"] == 500)
check("bootstrap seed fixed", REPORT["bootstrap"]["rng_seed"] == 20261004)

# ---------------------------------------------------------------- verdict text
verdict = REPORT["verdict"]
check("verdict labels component ii as re-routing", "re-routing" in verdict["honest_labels"]["component_ii"])
check("verdict rejects the old label", "NOT 'specification bias'" in verdict["honest_labels"]["old_label"])
check(
    "eps0 components are numerically zero",
    verdict["eps0_median_abs_component_i"] < 1e-12 and verdict["eps0_median_abs_component_ii"] < 1e-12,
)
check(
    "rerouting share at eps_max in (0.5, 0.8)",
    0.5 < verdict["fraction_of_published_bias_that_is_rerouting"] < 0.8,
    f"{verdict['fraction_of_published_bias_that_is_rerouting']:.4f}",
)

print()
print("FAILURES:", failures if failures else "none")
