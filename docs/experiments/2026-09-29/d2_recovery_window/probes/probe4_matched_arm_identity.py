"""D-2 probe 4: why do the matched and scrambled arms move?

Runs the same arm twice in one process and records the coupler's own feedback
records (burden components) plus the per-generation engine path, so the
"identical trajectory" refusal can be read off real numbers.
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path
from typing import Any

sys.path.insert(0, r"E:\مقاله پزشکی شبیه سازی ویروس\codontrace-genesis\src")

from codontrace.engine_runtime import GenesisEngine
from codontrace.genesis.campaigns.discovery_q_20260928_idea4 import (
    RECOVERY_TOKEN_KEY,
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
T_HOR = int(os.environ.get("D2_T_HOR", "3"))
TICKS = T_INT + T_HOR
ALL_ARMS = ("control", "cut_named_scaffold", "cut_matched_random", "scramble_contacts", "ablate_knowledge_digest")
ARMS = tuple(os.environ.get("D2_ARMS", "control,cut_named_scaffold,cut_matched_random,scramble_contacts").split(","))
# "simple" records one path per boundary; "combined" adds a second fingerprint and
# an extra harvest per boundary (the probe-2 recorder semantics).
RECORDER = os.environ.get("D2_RECORDER", "simple")


def run_arm(arm: str, allocation: str = "global_smear", feedback: bool = True) -> dict[str, Any]:
    ledger = build_engine_scaffold_ledger(seed=SEED)
    holder: dict[str, Any] = {"engine": None}
    paths: list[dict[str, Any]] = []

    def _op(led: Any, generation_index: int) -> dict[str, Any]:
        del generation_index
        ckpt = led.relocate_recovery_token(RECOVERY_TOKEN_KEY, remove=False, new_payload="relocated_engine")
        return {"ckpt": ckpt, "cell": _apply_ops_cell(led, arm)}

    observer = EngineCoupledLedgerObserver(
        engine_holder=holder,
        ledger=ledger,
        schedule={T_INT: [_op]},
        harvest_fn=harvest_rare_class_yield,
        auto_advance=True,
        feedback_enabled=feedback,
        feedback_allocation=allocation,
    )

    class _Rec:
        def __call__(self, *, generation_index: int) -> None:
            engine = holder["engine"]
            pre = population_path_fingerprint(engine)
            entry: dict[str, Any] = {
                "g": int(generation_index),
                "path": population_path_fingerprint(engine),
                "n_alive": len(list(engine.runner.population.organisms)),
            }
            if RECORDER == "combined":
                entry["path_pre"] = pre
                entry["rare_yield"] = round(float(harvest_rare_class_yield(ledger)), 9)
                entry["n_edges_present"] = sum(1 for e in ledger.edges.values() if e.present)
            paths.append(entry)

    rec = _Rec()
    spec = build_idea4_engine_spec(seed=SEED, tick_count=TICKS, population=8)
    t0 = time.perf_counter()
    engine = GenesisEngine.from_spec(spec, generation_boundary_observers=(observer, rec))
    holder["engine"] = engine
    engine.run_ticks()
    fb = observer.feedback_history[T_INT - 1] if len(observer.feedback_history) >= T_INT else {}
    return {
        "arm": arm,
        "allocation": allocation,
        "feedback": feedback,
        "seconds": round(time.perf_counter() - t0, 3),
        "paths": paths,
        "final_path": population_path_fingerprint(engine),
        "final_n": len(list(engine.runner.population.organisms)),
        "feedback_at_t": {
            k: fb.get(k)
            for k in (
                "pre_contact_energy",
                "post_contact_energy",
                "burden",
                "burden_lost_energy",
                "burden_edge_changes",
                "burden_digest",
                "burden_token",
                "total_debited",
                "food_removed",
                "n_edge_changes",
                "digest_changed",
                "token_changed",
                "n_alive_before",
                "n_alive_after_feedback",
                "allocation",
                "endpoints_enter_debit",
            )
        },
        "ledger_digest": ledger.digest(),
    }


report: dict[str, Any] = {
    "probe": "matched_arm_identity",
    "seed": SEED,
    "t": T_INT,
    "horizon": T_HOR,
    "recorder": RECORDER,
    "runs": [],
}
for arm in ARMS:
    a = run_arm(arm)
    b = run_arm(arm)
    a["repeat_identical_path"] = [p["path"] for p in a["paths"]] == [p["path"] for p in b["paths"]]
    a["repeat_identical_final"] = a["final_path"] == b["final_path"]
    report["runs"].append(a)
    print(f"{arm:24s} final={a['final_path'][-16:]} repeat_identical={a['repeat_identical_final']} burden={a['feedback_at_t']['burden']}")

# Cross-arm comparison of the *post-boundary* path from t onwards.
by_arm = {r["arm"]: r for r in report["runs"]}
report["path_from_t"] = {}
report["divergence"] = {}
base = [p["path"] for p in by_arm["control"]["paths"] if p["g"] >= T_INT]
for arm, r in by_arm.items():
    seq = [p["path"] for p in r["paths"] if p["g"] >= T_INT]
    report["path_from_t"][arm] = seq
    report["divergence"][arm] = {
        "identical_to_control_from_t": seq == base,
        "first_diff_gen": next((p["g"] for p, q in zip(r["paths"], by_arm["control"]["paths"], strict=False) if p["path"] != q["path"]), None),
    }

(OUT / "probe4_matched_arm_identity.json").write_text(
    json.dumps(report, indent=2, sort_keys=True, default=str), encoding="utf-8"
)
print(json.dumps(report["divergence"], indent=2))
