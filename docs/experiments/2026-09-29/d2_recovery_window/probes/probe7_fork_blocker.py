"""D-2 probe 7: find the exact object that blocks deepcopy, and test state round-trips.

Evidence for the smallest unblocking change to the full-fork precondition.
"""

from __future__ import annotations

import copy
import json
import sys
from pathlib import Path
from types import MappingProxyType
from typing import Any

sys.path.insert(0, r"E:\مقاله پزشکی شبیه سازی ویروس\codontrace-genesis\src")

from codontrace.engine_runtime import GenesisEngine  # noqa: E402
from codontrace.genesis.campaigns.discovery_q_20260928_idea4 import harvest_rare_class_yield  # noqa: E402
from codontrace.genesis.campaigns.discovery_q_20260928_idea4_engine import build_idea4_engine_spec  # noqa: E402
from codontrace.life_loop.contact_atp_ledger import build_engine_scaffold_ledger  # noqa: E402
from codontrace.life_loop.engine_ledger_coupler import EngineCoupledLedgerObserver  # noqa: E402

OUT = Path(r"E:\مقاله پزشکی شبیه سازی ویروس\test-runs\d2\logs")
report: dict[str, Any] = {}

holder: dict[str, Any] = {"engine": None}
observer = EngineCoupledLedgerObserver(
    engine_holder=holder,
    ledger=build_engine_scaffold_ledger(seed=301),
    schedule={},
    harvest_fn=harvest_rare_class_yield,
    auto_advance=True,
    feedback_enabled=True,
)
spec = build_idea4_engine_spec(seed=301, tick_count=6, population=8)
engine = GenesisEngine.from_spec(spec, generation_boundary_observers=(observer,))
holder["engine"] = engine
engine.run_ticks()

report["engine_type"] = f"{type(engine).__module__}.{type(engine).__name__}"
report["runner_type"] = f"{type(engine.runner).__module__}.{type(engine.runner).__name__}"


def attr_names(obj: Any) -> list[str]:
    names: set[str] = set()
    for klass in type(obj).__mro__:
        for slot in getattr(klass, "__slots__", ()) or ():
            names.add(str(slot))
    names.update(n for n in dir(obj) if not n.startswith("__"))
    return sorted(names)


# --- locate mappingproxy instances in the reachable graph --------------------
found: list[str] = []
seen: set[int] = set()


def walk(obj: Any, path: str, depth: int = 0) -> None:
    if depth > 6 or len(found) >= 25:
        return
    if id(obj) in seen:
        return
    seen.add(id(obj))
    if isinstance(obj, MappingProxyType):
        found.append(f"{path} :: mappingproxy of {list(obj)[:4]}")
        return
    if isinstance(obj, dict):
        for k, v in list(obj.items())[:40]:
            walk(v, f"{path}[{k!r}]", depth + 1)
        return
    if isinstance(obj, (list, tuple, set, frozenset)):
        for i, v in enumerate(list(obj)[:40]):
            walk(v, f"{path}[{i}]", depth + 1)
        return
    if isinstance(obj, (str, bytes, int, float, bool, type(None))):
        return
    for name in attr_names(obj):
        if name.startswith("__"):
            continue
        try:
            value = getattr(obj, name)
        except Exception:  # noqa: BLE001
            continue
        if callable(value):
            continue
        walk(value, f"{path}.{name}", depth + 1)


for name in ("spec", "runner", "run", "_last_result", "element_grid", "qd_archive"):
    try:
        walk(getattr(engine, name, None), name)
    except Exception as exc:  # noqa: BLE001
        found.append(f"walk({name}) failed: {exc}")
report["mappingproxy_paths"] = found

# Which top-level attribute actually blocks deepcopy?
blockers: dict[str, str] = {}
for name in ("spec", "runner", "run", "_last_result", "element_grid", "qd_archive", "review_status"):
    try:
        value = getattr(engine, name, None)
        copy.deepcopy(value)
        blockers[name] = "ok"
    except Exception as exc:  # noqa: BLE001
        blockers[name] = f"{type(exc).__name__}: {exc}"
report["deepcopy_per_attribute"] = blockers

# --- population round-trip ---------------------------------------------------
population = engine.runner.population
report["population_type"] = f"{type(population).__module__}.{type(population).__name__}"
try:
    payload = population.to_dict()
    restored = type(population).from_dict(payload)
    report["population_roundtrip"] = {
        "ok": True,
        "n_before": len(list(population.organisms)),
        "n_after": len(list(restored.organisms)),
        "generation_before": int(getattr(population, "generation", -1)),
        "generation_after": int(getattr(restored, "generation", -1)),
        "ids_equal": [str(o.id) for o in population.organisms] == [str(o.id) for o in restored.organisms],
        "payload_keys": sorted(payload.keys())[:20],
    }
except Exception as exc:  # noqa: BLE001
    report["population_roundtrip"] = {"ok": False, "error": f"{type(exc).__name__}: {exc}"}

# --- world round-trip --------------------------------------------------------
world = engine.runner.world
report["world_type"] = f"{type(world).__module__}.{type(world).__name__}"
report["world_serializers"] = [n for n in dir(world) if "dict" in n.lower() or "snapshot" in n.lower()]
report["world_resources_len"] = len(dict(getattr(world, "resources", {}) or {}))

# --- runner surface ----------------------------------------------------------
report["runner_attrs"] = attr_names(engine.runner)
report["engine_mutables"] = sorted(set(attr_names(engine)) & {"_tick_results", "_snapshots", "_last_result", "element_grid", "qd_archive", "review_status"})
report["tick_results_len"] = len(getattr(engine, "_tick_results", []))
report["snapshots_len"] = len(getattr(engine, "_snapshots", []))

# --- is atp debit observable per organism? -----------------------------------
try:
    org = list(population.organisms)[0]
    report["organism_attrs"] = attr_names(org)[:40]
    report["atp_state_attrs"] = attr_names(org.atp_state)[:25]
except Exception as exc:  # noqa: BLE001
    report["organism_attrs"] = f"error: {exc}"

(OUT / "probe7_fork_blocker.json").write_text(json.dumps(report, indent=2, sort_keys=True, default=str), encoding="utf-8")
print(json.dumps({k: v for k, v in report.items() if k not in ("runner_attrs", "organism_attrs", "atp_state_attrs")}, indent=2, default=str)[:4000])
