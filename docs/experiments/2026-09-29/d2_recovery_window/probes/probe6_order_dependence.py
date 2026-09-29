"""D-2 probe 6: is a cell's result independent of which cells ran before it?

Runs the same cell (same seed, same t, same arm) after different prefix cells in
the same process. If the result moves, the arms are not independent population
histories, which the common protocol requires.
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from typing import Any

sys.path.insert(0, r"E:\مقاله پزشکی شبیه سازی ویروس\codontrace-genesis\src")

from codontrace.engine_runtime import GenesisEngine
from codontrace.genesis.campaigns.discovery_q_20260928_idea4 import (
    RECOVERY_TOKEN_KEY,
    SCAFFOLD_ID,
    _apply_ops_cell,
    harvest_rare_class_yield,
)
from codontrace.genesis.campaigns.discovery_q_20260928_idea4_engine import build_idea4_engine_spec
from codontrace.life_loop.contact_atp_ledger import build_engine_scaffold_ledger
from codontrace.life_loop.engine_ledger_coupler import (
    EngineCoupledLedgerObserver,
    population_path_fingerprint,
)

OUT = Path(r"E:\مقاله پزشکی شبیه سازی ویروس\test-runs\d2\logs")
SEED = 301
T_INT = 10
TICKS = 16


def run_cell(arm: str) -> dict[str, Any]:
    ledger = build_engine_scaffold_ledger(seed=SEED)
    holder: dict[str, Any] = {"engine": None}
    detail: list[dict[str, Any]] = []

    def _op(led: Any, generation_index: int) -> dict[str, Any]:
        del generation_index
        ckpt = led.relocate_recovery_token(RECOVERY_TOKEN_KEY, remove=False, new_payload="relocated_engine")
        if arm == "cut_matched_random":
            profile = led.scaffold_cut_profile(SCAFFOLD_ID)
            design = led.independent_match_design(SCAFFOLD_ID)
            cel = _apply_ops_cell(led, arm)
            detail.append(
                {
                    "profile_cut_edge_ids": list(profile["cut_edge_ids"]),
                    "matched_cut_edge_ids": cel.get("cut_edge_ids"),
                    "design_failure": design.get("design_failure"),
                    "match_exact": cel.get("match_exact"),
                    "independent_control": cel.get("independent_control"),
                }
            )
        else:
            cel = _apply_ops_cell(led, arm)
            detail.append({"cell": cel.get("op")})
        return {"ckpt": ckpt, "cell": cel}

    observer = EngineCoupledLedgerObserver(
        engine_holder=holder,
        ledger=ledger,
        schedule={T_INT: [_op]},
        harvest_fn=harvest_rare_class_yield,
        auto_advance=True,
        feedback_enabled=True,
        feedback_allocation="global_smear",
    )
    spec = build_idea4_engine_spec(seed=SEED, tick_count=TICKS, population=8)
    engine = GenesisEngine.from_spec(spec, generation_boundary_observers=(observer,))
    holder["engine"] = engine
    engine.run_ticks()
    fb = observer.feedback_history[T_INT - 1]
    return {
        "arm": arm,
        "final_path": population_path_fingerprint(engine),
        "final_n": len(list(engine.runner.population.organisms)),
        "burden": round(float(fb.get("burden", -1.0)), 9),
        "detail": detail,
    }


PREFIXES = {
    "none": (),
    "scramble_first": ("scramble_contacts",),
    "named_first": ("cut_named_scaffold",),
    "ablate_first": ("ablate_knowledge_digest",),
    "control_first": ("control",),
    "scramble_then_named": ("scramble_contacts", "cut_named_scaffold"),
}

report: dict[str, Any] = {"probe": "cross_run_order_dependence", "seed": SEED, "t": T_INT, "cells": {}}
t0 = time.perf_counter()
for label, prefix in PREFIXES.items():
    for arm in prefix:
        run_cell(arm)
    target = run_cell("cut_matched_random")
    report["cells"][label] = {
        "prefix": list(prefix),
        "target_final_path": target["final_path"],
        "target_burden": target["burden"],
        "target_final_n": target["final_n"],
        "target_detail": target["detail"],
    }
    print(f"{label:22s} matched final={target['final_path'][-16:]} burden={target['burden']} detail={target['detail']}")
report["seconds"] = round(time.perf_counter() - t0, 2)

paths = {v["target_final_path"] for v in report["cells"].values()}
report["n_distinct_matched_paths"] = len(paths)
report["order_dependent"] = len(paths) > 1
print("distinct matched paths:", len(paths), "order_dependent:", report["order_dependent"])

(OUT / "probe6_order_dependence.json").write_text(
    json.dumps(report, indent=2, sort_keys=True, default=str), encoding="utf-8"
)
