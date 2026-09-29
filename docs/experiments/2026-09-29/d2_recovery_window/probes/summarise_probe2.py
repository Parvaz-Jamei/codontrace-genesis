"""Summarise probe2 JSON: which arms share a path, when divergence starts."""

from __future__ import annotations

import json
from pathlib import Path

P = Path(r"E:\مقاله پزشکی شبیه سازی ویروس\test-runs\d2\logs\probe2_fork_and_op_effect.json")
r = json.loads(P.read_text(encoding="utf-8"))
cells = r["P2_cells"]
gens = r["P2_path_identity"]["generations"]
ops = list(cells)

print("P1: snapshot fields      :", r["P1_snapshot"]["snapshot_fields"])
print("P1: engine restore entry :", r["P1_snapshot"]["engine_has_restore_entry"])
print("P1: runner attrs (n)     :", len(r["P1_snapshot"]["runner_attrs"]))
print("P1: runner rng attrs     :", r["P1_snapshot"]["runner_rng_attrs"])
print("P1: engine rng attrs     :", r["P1_snapshot"]["engine_rng_attrs"])
print("P1: population type      :", r["P1_snapshot"]["population_type"])
print("P1: population restore   :", r["P1_snapshot"]["population_restore_entry"])
print("P1: snapshot has rng     :", r["P1_snapshot"]["snapshot_has_rng"])
print("P1: deepcopy engine ok   :", r["P1_snapshot"]["deepcopy_engine_ok"], r["P1_snapshot"]["deepcopy_engine_error"])
print()
print("P2: path identity groups :", r["P2_path_identity"]["identical_ops_groups"])
print()
print("gen | " + " | ".join(f"{o[:16]:16s}" for o in ops))
for g in gens:
    row = r["P2_path_identity"]["path_by_gen"][str(g)]
    print(f"{g:3d} | " + " | ".join((row[o] or "None")[-16:] for o in ops))
print()
print("first divergence generation per arm vs control:")
ctrl = {row["generation_index"]: row["path"] for row in cells["control"]["per_generation"]}
for o in ops:
    first = None
    for row in cells[o]["per_generation"]:
        if row["path"] != ctrl.get(row["generation_index"]):
            first = row["generation_index"]
            break
    print(f"  {o:24s} first_differs_at={first} final_n={cells[o]['final_n_alive']}")
print()
print("rare yield by generation (ledger arithmetic):")
print("gen | " + " | ".join(f"{o[:16]:16s}" for o in ops))
for g in gens:
    vals = []
    for o in ops:
        row = next((x for x in cells[o]["per_generation"] if x["generation_index"] == g), None)
        vals.append("None" if row is None else f"{row['rare_yield']:.6f}")
    print(f"{g:3d} | " + " | ".join(f"{v:16s}" for v in vals))
print()
print("n_edges_present at t+1 per arm:", {o: next(x["n_edges_present"] for x in cells[o]["per_generation"] if x["generation_index"] == 11) for o in ops})
print("rare_edges_present at t+1 per arm:", {o: next(x["rare_edges_present"] for x in cells[o]["per_generation"] if x["generation_index"] == 11) for o in ops})
print("seconds per cell:", {o: cells[o]["seconds"] for o in ops})
