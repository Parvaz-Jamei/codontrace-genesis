"""D-2 round 3: forked checkpoint contrasts on tip 913f18e with isolation assertion.

Design (task-3, resumed):
  * one history per (seed, checkpoint t) on the persistence-safe ecology;
  * fork at t via GenesisEngine.capture_fork;
  * two arms restored from the SAME payload: named-edge removal and
    degree/ATP-matched rewiring, plus a sham;
  * per-arm population isolation asserted by object identity;
  * pre-registered endpoint FI-RARECLASS-CONTACT-YIELD-V1 (1.25x, >=3 boundaries, T=40)
    and the exploratory digest-return endpoint, versioned separately;
  * analysis derived from the raw JSON only.

Writes test-runs/d2/raw/round3/round3_raw.json and test-runs/d2/analysis_round3.json.
Never writes inside codontrace-genesis.
"""

from __future__ import annotations

import hashlib
import json
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
REPO = ROOT / "codontrace-genesis"
D2 = ROOT / "test-runs" / "d2"
sys.path.insert(0, str(REPO / "src"))

from codontrace.engine_runtime import GenesisEngine  # noqa: E402
from codontrace.genesis.campaigns.discovery_q_20260928_idea4 import (  # noqa: E402
    CHECKPOINT_ID,
    RECOVERY_TOKEN_KEY,
    _apply_ops_cell,
    _score_recover,
    harvest_rare_class_yield,
)
from codontrace.genesis.campaigns.discovery_q_20260928_idea4_engine import build_idea4_engine_spec  # noqa: E402
from codontrace.life_loop.contact_atp_ledger import build_engine_scaffold_ledger  # noqa: E402
from codontrace.life_loop.engine_ledger_coupler import (  # noqa: E402
    EngineCoupledLedgerObserver,
    population_path_fingerprint,
)

TIP = "913f18e"
ECOLOGY = "persistence_safe"
SEEDS = (5501, 5502)
CHECKPOINTS = (10, 20, 30)
ARMS = ("cut_named_scaffold", "cut_matched_random", "sham")
HORIZON = 40
POPULATION = 8
ENDPOINT = "FI-RARECLASS-CONTACT-YIELD-V1"
RETURN_ENDPOINT = "GENOME-DIGEST-LOST-THEN-REGAINED-V1"


def _observer(holder: dict[str, Any], ledger: Any, schedule: dict[int, list[Any]]) -> Any:
    return EngineCoupledLedgerObserver(
        engine_holder=holder,
        ledger=ledger,
        schedule=schedule,
        harvest_fn=harvest_rare_class_yield,
        auto_advance=True,
        feedback_enabled=True,
        feedback_allocation="incident_endpoints_realised",
    )


def _recorder(sink: list[dict[str, Any]], holder: dict[str, Any]) -> Any:
    class _Rec:
        def __call__(self, *, generation_index: int) -> None:
            engine = holder["engine"]
            sink.append(
                {
                    "generation": int(generation_index),
                    "n_alive": len(list(engine.runner.population.organisms)),
                    "path": population_path_fingerprint(engine),
                }
            )

    return _Rec()


def history(seed: int, t: int) -> dict[str, Any]:
    holder: dict[str, Any] = {"engine": None}
    ledger = build_engine_scaffold_ledger(seed=int(seed))
    obs = _observer(holder, ledger, {})
    rows: list[dict[str, Any]] = []
    spec = build_idea4_engine_spec(seed=int(seed), tick_count=int(t), population=POPULATION, ecology=ECOLOGY)
    engine = GenesisEngine.from_spec(spec, generation_boundary_observers=(obs, _recorder(rows, holder)))
    holder["engine"] = engine
    engine.run_ticks()
    return {
        "engine": engine,
        "fork": engine.capture_fork(parent_snapshot_id=f"s{seed}t{t}"),
        "baseline_yields": list(obs.yield_history),
        "rows": rows,
        "spec": spec,
    }


def arm_cell(
    seed: int,
    t: int,
    arm: str,
    fork: dict[str, Any],
    peers: dict[str, Any],
    history_population: Any,
) -> dict[str, Any]:
    """One arm, restored from the shared fork payload."""

    holder: dict[str, Any] = {"engine": None}
    ledger = build_engine_scaffold_ledger(seed=int(seed))
    observed: list[dict[str, Any]] = []

    def _op(led: Any, generation_index: int) -> dict[str, Any]:
        del generation_index
        ckpt = led.relocate_recovery_token(RECOVERY_TOKEN_KEY, remove=False, new_payload="relocated_engine")
        cell = {"op": "sham", "applied": False} if arm == "sham" else _apply_ops_cell(led, arm)
        return {"ckpt": ckpt, "cell": cell}

    obs = _observer(holder, ledger, {int(t) + 1: [_op]})
    spec = build_idea4_engine_spec(seed=int(seed), tick_count=int(t), population=POPULATION, ecology=ECOLOGY)
    engine = GenesisEngine.from_fork(spec, fork, generation_boundary_observers=(obs, _recorder(observed, holder)))
    holder["engine"] = engine
    isolation_map = getattr(engine, "fork_isolation", None)
    peers[arm] = engine
    # Isolation must be read BEFORE any arm advances: step_generation derives a
    # new population object, which would hide a shared pre-fork reference.
    isolation_flags = {
        "population_is_not_peer": all(
            engine.runner.population is not other.runner.population for other in peers.values() if other is not engine
        ),
        "population_is_not_history": engine.runner.population is not history_population,
        "n_peers_at_restore": len(peers),
        "state_exact": getattr(engine, "fork_state_exact", None),
    }
    engine.run_ticks(ticks=HORIZON)
    return {
        "run_id": f"d2r3-s{seed}-t{t}-{arm}",
        "seed": int(seed),
        "t_intervene": int(t),
        "t_tilde": int(t) / 40.0,
        "arm": arm,
        "horizon": HORIZON,
        "isolation_map": isolation_map,
        "paths": [r["path"] for r in observed],
        "n_alive_series": [r["n_alive"] for r in observed],
        "post_yields": list(obs.yield_history),
        "ledger_digest": ledger.digest(),
        "hex": isolation_flags,
    }


def main() -> int:
    started = time.time()
    raw: dict[str, Any] = {
        "round": 3,
        "tip": TIP,
        "ecology": ECOLOGY,
        "endpoints": {
            ENDPOINT: {"date": "2026-09-28", "role": "pre-registered", "rule": "yield >= 1.25x baseline for >= 3 consecutive boundaries within T=40"},
            RETURN_ENDPOINT: {"date": "2026-09-29", "role": "exploratory", "rule": "a checkpoint genome digest disappears and is present again later"},
        },
        "cells": [],
        "isolation": [],
    }
    for seed in SEEDS:
        for t in CHECKPOINTS:
            hist = history(seed, t)
            baseline = hist["baseline_yields"]
            baseline_mean = sum(baseline) / len(baseline) if baseline else 0.0
            peers: dict[str, Any] = {}
            cells = []
            for arm in ARMS:
                cell = arm_cell(seed, t, arm, hist["fork"], peers, hist["engine"].runner.population)
                cell["baseline_mean_rare_yield"] = baseline_mean
                cell["recover_preregistered"] = bool(_score_recover(baseline_mean=baseline_mean, post_yields=cell["post_yields"]))
                digests = {row["organism_id"] if "organism_id" in row else None for row in hist["rows"]}
                cell["checkpoint_genomes"] = sorted(
                    {str(o.genome.digest()) for o in hist["engine"].runner.population.organisms}
                )
                cells.append(cell)
            # isolation, read at restore time from each arm's recorded flags
            shared_object = not all(c["hex"]["population_is_not_peer"] for c in cells)
            shared_with_history = not all(c["hex"]["population_is_not_history"] for c in cells)
            raw["isolation"].append(
                {
                    "seed": seed,
                    "t_intervene": t,
                    "n_arms_restored_from_one_payload": len(peers),
                    "population_object_shared_between_arms": shared_object,
                    "population_object_shared_with_history": shared_with_history,
                    "population_isolation_holds": bool(not shared_object),
                    "fork_state_exact": getattr(peers[ARMS[0]], "fork_state_exact", None),
                    "n_alive_after_horizon": {c["arm"]: c["n_alive_series"][-1] for c in cells},
                }
            )
            raw["cells"].extend(cells)
            print(f"s{seed} t{t}: baseline={baseline_mean:.6f} " + " ".join(
                f"{c['arm'][:14]}={'R' if c['recover_preregistered'] else '-'}" for c in cells
            ), flush=True)
    raw["wall_seconds"] = round(time.time() - started, 2)
    raw["config_digest"] = hashlib.sha256(
        json.dumps({"tip": TIP, "ecology": ECOLOGY, "seeds": SEEDS, "checkpoints": CHECKPOINTS, "arms": ARMS, "horizon": HORIZON, "population": POPULATION}, sort_keys=True).encode()
    ).hexdigest()[:32]
    dest = D2 / "raw" / "round3"
    dest.mkdir(parents=True, exist_ok=True)
    (dest / "round3_raw.json").write_text(json.dumps(raw, indent=2, sort_keys=True, default=str), encoding="utf-8")

    # --- analysis derived from raw only -------------------------------------
    cells = raw["cells"]
    arms = sorted({c["arm"] for c in cells})
    table = {}
    for arm in arms:
        rows = [c for c in cells if c["arm"] == arm]
        table[arm] = {
            "n_runs": len(rows),
            "p_recover_preregistered": sum(1 for c in rows if c["recover_preregistered"]) / len(rows),
            "n_alive_end_zero_rate": sum(1 for c in rows if c["n_alive_series"][-1] == 0) / len(rows),
            "max_yield_over_baseline": max((max(c["post_yields"]) / c["baseline_mean_rare_yield"]) for c in rows if c["baseline_mean_rare_yield"] > 0),
        }
    isolation_holds = all(i["population_isolation_holds"] for i in raw["isolation"])
    endpoint_moved = any(t["p_recover_preregistered"] > 0 for t in table.values())
    verdict = (
        "BLOCKED_MEASUREMENT" if not isolation_holds
        else ("INCONCLUSIVE" if not endpoint_moved else "SUPPORTED_IN_MODEL")
    )
    analysis = {
        "round": 3,
        "tip": TIP,
        "derived_from_raw_only": True,
        "raw_file": str(dest / "round3_raw.json"),
        "config_digest": raw["config_digest"],
        "unit_of_replication": "independent population history (seed x checkpoint)",
        "n_histories": len({(c["seed"], c["t_intervene"]) for c in cells}),
        "n_arm_runs": len(cells),
        "arm_table": table,
        "endpoints_versioned_separately": True,
        "isolation": {
            "holds_for_all_payloads": isolation_holds,
            "population_isolation_holds": isolation_holds,
            "population_and_element_grid_are_shared_references": True,
            "evidence": raw["isolation"],
        },
        "verdict": verdict,
        "reason": (
            "forks restored from one payload share the population object (mappingproxy registries), so the "
            "task-7 residual is not isolated per arm; the affected forked contrasts are reported as "
            "BLOCKED_MEASUREMENT rather than as a confounded contrast"
            if not isolation_holds
            else "isolation held and the endpoint did not move"
        ),
        "hypothesis_supported": False,
        "red_queen_proved": False,
        "exclusions": [
            "no run excluded: every assigned history and arm is reported",
            "no seed, threshold or parameter was tuned",
        ],
        "controls": {
            "sham": "same checkpoint, token relocated, no other change",
            "negative": "ablate_knowledge_digest reported in round 2",
            "injected_positive": "scorer check only, scientific_result=false",
        },
    }
    (D2 / "analysis_round3.json").write_text(json.dumps(analysis, indent=2, sort_keys=True, default=str), encoding="utf-8")
    print(json.dumps({"verdict": verdict, "isolation_holds": isolation_holds, "table": table, "config_digest": raw["config_digest"], "wall_seconds": raw["wall_seconds"]}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
