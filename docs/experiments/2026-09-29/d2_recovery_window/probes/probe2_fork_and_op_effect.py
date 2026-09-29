"""D-2 probe 2: fork capability + does a ledger intervention move the engine path?

Read-only w.r.t. the repository. Answers two preconditions directly:

P1  Is there a *full fork* of a generation boundary (engine state + RNG +
    parent/child genealogy)?  Reports the snapshot surface and whether any
    restore entry point exists.
P2  Does the named-scaffold cut differ from the degree/ATP-matched random cut in
    the real engine population trajectory and in realised contacts, at fixed
    seed and fixed boundary?  This is the D-2 refusal test.

Writes one JSON report under test-runs/d2/logs/.
"""

from __future__ import annotations

import inspect
import json
import sys
import time
from pathlib import Path
from typing import Any

sys.path.insert(0, r"E:\مقاله پزشکی شبیه سازی ویروس\codontrace-genesis\src")

from codontrace.genesis.campaigns.discovery_q_20260928_idea4 import (
    RECOVERY_TOKEN_KEY,
    SCAFFOLD_ID,
    _apply_ops_cell,
    harvest_rare_class_yield,
)
from codontrace.genesis.campaigns.discovery_q_20260928_idea4_engine import (
    build_idea4_engine_spec,
)
from codontrace.engine_runtime import GenesisEngine
from codontrace.life_loop.contact_atp_ledger import build_engine_scaffold_ledger
from codontrace.life_loop.engine_ledger_coupler import (
    EngineCoupledLedgerObserver,
    population_path_fingerprint,
)

OUT = Path(r"E:\مقاله پزشکی شبیه سازی ویروس\test-runs\d2\logs")
OUT.mkdir(parents=True, exist_ok=True)

SEED = 301
T_INT = 10
T_HOR = 6
TICKS = T_INT + T_HOR
OPS = ("control", "scramble_contacts", "cut_named_scaffold", "cut_matched_random", "ablate_knowledge_digest")

report: dict[str, Any] = {"probe": "fork_and_op_effect", "seed": SEED, "t_intervene": T_INT, "t_horizon": T_HOR}


def emit(name: str, value: Any) -> None:
    print(f"[{name}] {json.dumps(value, default=str)[:600]}")


def attr_names(obj: Any) -> list[str]:
    """All attribute names, including slot-only classes with no __dict__."""

    names: set[str] = set()
    try:
        names.update(vars(obj))
    except TypeError:
        pass
    for klass in type(obj).__mro__:
        for slot in getattr(klass, "__slots__", ()) or ():
            names.add(str(slot))
    names.update(n for n in dir(obj) if not n.startswith("__"))
    return sorted(names)


# --- P1: snapshot surface and fork capability --------------------------------
snap_report: dict[str, Any] = {}
holder: dict[str, Any] = {"engine": None}


class _RecordObserver:
    def __init__(self) -> None:
        self.rows: list[dict[str, Any]] = []

    def __call__(self, *, generation_index: int) -> None:
        engine = holder["engine"]
        pop = engine.runner.population
        orgs = list(pop.organisms)
        self.rows.append(
            {
                "generation_index": int(generation_index),
                "population_generation": int(pop.generation),
                "n_alive": len(orgs),
                "path": population_path_fingerprint(engine),
            }
        )


rec = _RecordObserver()
spec = build_idea4_engine_spec(seed=SEED, tick_count=10, population=8)
engine = GenesisEngine.from_spec(spec, generation_boundary_observers=(rec,))
holder["engine"] = engine
engine.run_ticks()

snap = engine.snapshot()
snap_fields = sorted(getattr(type(snap), "__dataclass_fields__", {}).keys())
snap_report["snapshot_type"] = f"{type(snap).__module__}.{type(snap).__name__}"
snap_report["snapshot_fields"] = snap_fields
snap_report["engine_has_restore_entry"] = [
    n for n in dir(GenesisEngine) if any(k in n.lower() for k in ("restore", "fork", "load", "from_snapshot"))
]
snap_report["runner_attrs"] = attr_names(engine.runner)
snap_report["runner_rng_attrs"] = [n for n in attr_names(engine.runner) if "rng" in n.lower() or "random" in n.lower()]
snap_report["engine_rng_attrs"] = [n for n in attr_names(engine) if "rng" in n.lower() or "random" in n.lower()]
pop = engine.runner.population
snap_report["population_type"] = f"{type(pop).__module__}.{type(pop).__name__}"
snap_report["population_restore_entry"] = [
    n for n in dir(pop) if any(k in n.lower() for k in ("restore", "from_snapshot", "from_dict", "to_dict"))
]
try:
    snap_report["deepcopy_engine_error"] = _deepcopy_error = None
    import copy as _copy

    try:
        _copy.deepcopy(engine)
        snap_report["deepcopy_engine_ok"] = True
    except Exception as exc:  # noqa: BLE001
        snap_report["deepcopy_engine_ok"] = False
        snap_report["deepcopy_engine_error"] = f"{type(exc).__name__}: {exc}"
except Exception as exc:  # noqa: BLE001
    snap_report["deepcopy_engine_ok"] = False
    snap_report["deepcopy_engine_error"] = f"{type(exc).__name__}: {exc}"

try:
    snap_dict = snap.to_dict() if hasattr(snap, "to_dict") else None
except Exception as exc:  # noqa: BLE001
    snap_dict = f"error: {type(exc).__name__}: {exc}"
snap_report["snapshot_has_rng"] = bool(
    isinstance(snap_dict, dict) and any("rng" in str(k).lower() for k in snap_dict)
)
snap_report["snapshot_field_names_flat"] = (
    sorted(snap_dict.keys()) if isinstance(snap_dict, dict) else snap_dict
)
for name in (
    "from_snapshot",
    "restore",
):
    snap_report[f"has_{name}"] = hasattr(GenesisEngine, name)
snap_report["rng_module_entry_points"] = [
    n for n in dir(__import__("codontrace.rng", fromlist=["*"])) if "RNGSnapshot" in n or "RNGManager" in n
]
report["P1_snapshot"] = snap_report

# --- P2: does the intervention move the engine path? -------------------------
cell_reports: dict[str, Any] = {}
def _run_cell(ops: str) -> dict[str, Any]:
    ledger = build_engine_scaffold_ledger(seed=SEED)
    holder2: dict[str, Any] = {"engine": None}
    per_cell: list[dict[str, Any]] = []

    def _op(led: Any, generation_index: int) -> dict[str, Any]:
        del generation_index
        ckpt = led.relocate_recovery_token(RECOVERY_TOKEN_KEY, remove=False, new_payload="relocated_engine")
        cell = _apply_ops_cell(led, ops)
        return {"ckpt": ckpt, "cell": cell}

    schedule = {T_INT: [_op]}
    coupled = EngineCoupledLedgerObserver(
        engine_holder=holder2,
        ledger=ledger,
        schedule=schedule,
        harvest_fn=harvest_rare_class_yield,
        auto_advance=True,
        feedback_enabled=True,
        feedback_allocation="global_smear",
    )

    class _Combined:
        """Record the engine path around the coupled observer's boundary action."""

        def __call__(self, *, generation_index: int) -> None:
            engine2 = holder2["engine"]
            pre = population_path_fingerprint(engine2)
            coupled(generation_index=generation_index)
            post = population_path_fingerprint(engine2)
            pop2 = engine2.runner.population
            per_cell.append(
                {
                    "generation_index": int(generation_index),
                    "n_alive": len(list(pop2.organisms)),
                    "path_pre": pre,
                    "path_post": post,
                    "rare_yield": round(float(harvest_rare_class_yield(ledger)), 9),
                    "rare_edges_present": sorted(
                        eid
                        for eid in ledger.edges_with_tag("class=rare")
                        if ledger.edges[eid].present and not ledger.edges[eid].masked
                    ),
                    "n_edges_present": sum(1 for e in ledger.edges.values() if e.present),
                    "n_edges_total": len(ledger.edges),
                }
            )

    combined = _Combined()
    spec2 = build_idea4_engine_spec(seed=SEED, tick_count=TICKS, population=8)
    t0 = time.perf_counter()
    engine2 = GenesisEngine.from_spec(spec2, generation_boundary_observers=(coupled, combined))
    holder2["engine"] = engine2
    engine2.run_ticks()
    return {
        "seconds": round(time.perf_counter() - t0, 3),
        "fires": int(coupled.observer_fire_count),
        "per_generation": per_cell,
        "final_path": population_path_fingerprint(engine2),
        "final_n_alive": len(list(engine2.runner.population.organisms)),
        "ledger_digest": ledger.digest(),
    }


for ops in OPS:
    cell_reports[ops] = _run_cell(ops)
    emit(f"P2.{ops}", cell_reports[ops]["final_path"])

report["P2_cells"] = cell_reports

# Comparison table: path fingerprints per generation across ops cells.
gens = sorted({row["generation_index"] for rows in (c["per_generation"] for c in cell_reports.values()) for row in rows})
compare: dict[str, Any] = {"generations": gens, "path_by_gen": {}, "path_post_by_gen": {}, "identical_ops_groups": {}}
for g in gens:
    mapping: dict[str, str | None] = {}
    mapping_post: dict[str, str | None] = {}
    for ops, cell in cell_reports.items():
        row = next((r for r in cell["per_generation"] if r["generation_index"] == g), None)
        mapping[ops] = None if row is None else row["path_post"]
        mapping_post[ops] = None if row is None else row["path_pre"]
    compare["path_by_gen"][str(g)] = mapping
    compare["path_post_by_gen"][str(g)] = mapping_post
# Which ops share the exact same full path sequence?
seqs: dict[str, tuple[Any, ...]] = {}
for ops, cell in cell_reports.items():
    seqs[ops] = tuple(r["path_post"] for r in cell["per_generation"])
for ops, seq in seqs.items():
    for other, oseq in seqs.items():
        if ops < other and seq == oseq:
            compare["identical_ops_groups"][f"{ops}|{other}"] = "identical"
# First generation at which each arm's path_post differs from the control arm.
control_paths = {r["generation_index"]: r["path_post"] for r in cell_reports["control"]["per_generation"]}
compare["first_divergence_from_control"] = {
    ops: next(
        (r["generation_index"] for r in cell["per_generation"] if r["path_post"] != control_paths.get(r["generation_index"])),
        None,
    )
    for ops, cell in cell_reports.items()
}
report["P2_path_identity"] = compare

# Rare-yield identity check across arms (realised contact numbers).
yield_cmp: dict[str, Any] = {}
for ops, cell in cell_reports.items():
    yield_cmp[ops] = [r["rare_yield"] for r in cell["per_generation"]]
report["P2_rare_yield_by_gen"] = yield_cmp

(OUT / "probe2_fork_and_op_effect.json").write_text(
    json.dumps(report, indent=2, sort_keys=True, default=str), encoding="utf-8"
)
print("WROTE probe2_fork_and_op_effect.json")
