"""D-2 probe 1: engine API surface, wall time, and deepcopy-fork feasibility.

Read-only w.r.t. the repository. Writes only its stdout (redirected by the
caller) plus an optional JSON report under test-runs/d2/logs/.

Question: can a generation boundary produce a *full fork* of the live model
(state + RNG + population + genealogy) that replays the post-boundary path
byte-identically? If yes, D-2 can be wired without touching the repo. If no,
the missing precondition is recorded with raw evidence.
"""

from __future__ import annotations

import copy
import inspect
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, r"E:\مقاله پزشکی شبیه سازی ویروس\codontrace-genesis\src")

from codontrace.genesis.campaigns.discovery_q_20260928_idea4_engine import (
    build_idea4_engine_spec,
)
from codontrace.genesis.engine import GenesisEngine

OUT = Path(r"E:\مقاله پزشکی شبیه سازی ویروس\test-runs\d2\logs")
OUT.mkdir(parents=True, exist_ok=True)

report: dict[str, object] = {"probe": "engine_api_and_fork", "steps": []}


def step(name: str, value: object) -> None:
    report["steps"].append({name: value})  # type: ignore[arg-type]
    print(f"[{name}] {value}")


# --- API surface -------------------------------------------------------------
step("engine_module", GenesisEngine.__module__)
step("engine_public", sorted(n for n in dir(GenesisEngine) if not n.startswith("_")))
try:
    step("from_spec_sig", str(inspect.signature(GenesisEngine.from_spec)))
except (TypeError, ValueError) as exc:  # pragma: no cover
    step("from_spec_sig", f"unavailable: {exc}")
try:
    step("run_ticks_sig", str(inspect.signature(GenesisEngine.run_ticks)))
except (TypeError, ValueError) as exc:  # pragma: no cover
    step("run_ticks_sig", f"unavailable: {exc}")

# --- Build a short idea-4 spec ----------------------------------------------
SEED = 301
T_INT = 10
T_HOR = 6  # probe horizon only; D-2 protocol ceiling is T=40
TICKS = T_INT + T_HOR

t0 = time.perf_counter()
spec = build_idea4_engine_spec(seed=SEED, tick_count=TICKS, population=8)
build_s = time.perf_counter() - t0
step("spec_build_seconds", round(build_s, 4))

events: list[dict[str, object]] = []
forked: dict[str, object] = {}


class _ProbeObserver:
    """Records the boundary census and deep-copies the live engine at t_int."""

    def __init__(self) -> None:
        self.fires = 0

    def __call__(self, *, generation_index: int) -> None:
        self.fires += 1
        engine = holder["engine"]
        if engine is None:
            events.append({"gen": generation_index, "engine": None})
            return
        pop = engine.runner.population
        orgs = list(pop.organisms)
        events.append(
            {
                "gen": int(generation_index),
                "n_alive": len(orgs),
                "ids": [str(o.id) for o in orgs],
                "genomes": [str(o.genome.digest()) if hasattr(o.genome, "digest") else None for o in orgs],
                "atp": [round(float(o.atp_state.runtime_available), 6) for o in orgs],
                "tick": int(getattr(engine, "tick", -1)),
            }
        )
        if int(generation_index) == T_INT and not forked:
            t_copy = time.perf_counter()
            try:
                forked["engine"] = copy.deepcopy(engine)
                forked["deepcopy_ok"] = True
                forked["deepcopy_seconds"] = round(time.perf_counter() - t_copy, 4)
                forked["source_tick"] = int(getattr(engine, "tick", -1))
            except Exception as exc:  # noqa: BLE001 - probe records any failure
                forked["deepcopy_ok"] = False
                forked["deepcopy_error"] = f"{type(exc).__name__}: {exc}"


holder: dict[str, object] = {"engine": None}
observer = _ProbeObserver()
t0 = time.perf_counter()
engine = GenesisEngine.from_spec(spec, generation_boundary_observers=(observer,))
step("from_spec_seconds", round(time.perf_counter() - t0, 4))
holder["engine"] = engine

t0 = time.perf_counter()
result = engine.run_ticks()
run_s = time.perf_counter() - t0
step("run_ticks_seconds", round(run_s, 4))
step("observer_fires", observer.fires)
step("expected_ticks", TICKS)
step("result_type", type(result).__name__)
step("engine_attrs_after", sorted(n for n in vars(engine) if not n.startswith("_props")))

report["boundary_events"] = events
report["fork"] = forked
report["wall_seconds_ticks"] = run_s
report["wall_seconds_per_tick"] = round(run_s / max(1, TICKS), 6)

# --- Can the fork continue? --------------------------------------------------
if forked.get("deepcopy_ok"):
    fork_engine = forked["engine"]
    try:
        step("fork_run_ticks_sig", str(inspect.signature(fork_engine.run_ticks)))
        t0 = time.perf_counter()
        fork_result = fork_engine.run_ticks()
        fork_s = time.perf_counter() - t0
        report["fork"]["continue_seconds"] = round(fork_s, 4)
        report["fork"]["continue_ok"] = True
        report["fork"]["fork_result_type"] = type(fork_result).__name__
        pop_fork = fork_engine.runner.population
        report["fork"]["fork_final_n"] = len(list(pop_fork.organisms))
        report["fork"]["original_final_n"] = len(list(engine.runner.population.organisms))
    except Exception as exc:  # noqa: BLE001
        report["fork"]["continue_ok"] = False
        report["fork"]["continue_error"] = f"{type(exc).__name__}: {exc}"
        step("fork_continue_error", report["fork"]["continue_error"])

(OUT / "probe1_engine_api.json").write_text(
    json.dumps(report, indent=2, sort_keys=True, default=str), encoding="utf-8"
)
print("WROTE", OUT / "probe1_engine_api.json")
