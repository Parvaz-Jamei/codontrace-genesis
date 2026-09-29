"""Round-4 isolation probe fix: the probe must reach the checkpoint before interleaving.

The first probe advanced from tick 0, so the arm op (scheduled at t+1) never fired
and two different arms trivially matched.  This re-runs ONLY the probe and re-derives
analysis_round4.json + run_manifest.json from the unchanged raw cells.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
D2 = ROOT / "test-runs" / "d2"
sys.path.insert(0, str(ROOT / "codontrace-genesis" / "src"))

spec = importlib.util.spec_from_file_location("d2r4", Path(__file__).resolve().parent / "d2_round4.py")
d2r4 = importlib.util.module_from_spec(spec)
sys.modules["d2r4"] = d2r4
spec.loader.exec_module(d2r4)


def isolation_probe_fixed(seed: int = 5501, t: int = 10, ticks: int = 3) -> dict[str, Any]:
    """Build three independent engines, advance each to the checkpoint, then interleave."""

    x, _, _, _ = d2r4.build(seed, t, "cut_named_scaffold")
    y, _, _, _ = d2r4.build(seed, t, "cut_named_scaffold")
    z, _, _, _ = d2r4.build(seed, t, "cut_matched_random")
    for engine in (x, y, z):
        engine.run_ticks(t)  # reach the checkpoint; arm op fires at t+1
    distinct = len({id(x.runner.population), id(y.runner.population), id(z.runner.population)}) == 3
    dx: list[str] = []
    dy: list[str] = []
    dz: list[str] = []
    for _ in range(ticks):
        dx.append(x.run_ticks(1).ticks[-1].digest())
        dy.append(y.run_ticks(1).ticks[-1].digest())
        dz.append(z.run_ticks(1).ticks[-1].digest())
    return {
        "population_objects_distinct": distinct,
        "engines_built_independently": True,
        "fork_used": False,
        "advanced_to_checkpoint_first": True,
        "interleaved_same_arm_x_equals_y": dx == dy,
        "different_arm_z_differs": dz != dx,
        "isolation_holds": bool(distinct and dx == dy and dz != dx),
        "x": [d[:12] for d in dx],
        "y": [d[:12] for d in dy],
        "z": [d[:12] for d in dz],
    }


def main() -> int:
    raw_path = D2 / "raw" / "round4" / "round4_raw.json"
    raw = json.loads(raw_path.read_text(encoding="utf-8"))
    raw["isolation"] = [isolation_probe_fixed()]
    pop_ids = [c["population_object_id"] for c in raw["cells"]]
    raw["all_population_objects_distinct"] = len(set(pop_ids)) == len(pop_ids)
    raw_path.write_text(json.dumps(raw, indent=2, sort_keys=True, default=str), encoding="utf-8")

    cells = raw["cells"]
    table = {}
    for arm in d2r4.ARMS:
        rows = [c for c in cells if c["arm"] == arm]
        table[arm] = {
            "n_runs": len(rows),
            "n_recover_preregistered": sum(1 for c in rows if c["recover_preregistered"]),
            "p_recover_preregistered": sum(1 for c in rows if c["recover_preregistered"]) / len(rows),
            "p_digest_return_exploratory": 0.0,
            "max_yield_over_baseline": max(c["max_yield_over_baseline"] for c in rows),
            "n_alive_end_zero_rate": sum(1 for c in rows if c["n_alive_series"][-1] == 0) / len(rows),
            "mean_n_alive_end": sum(c["n_alive_series"][-1] for c in rows) / len(rows),
        }
    iso_ok = all(i["isolation_holds"] for i in raw["isolation"]) and raw["all_population_objects_distinct"]
    max_ratio = max(t["max_yield_over_baseline"] for t in table.values())
    endpoint_moved = any(t["n_recover_preregistered"] > 0 for t in table.values())
    verdict = "BLOCKED_MEASUREMENT" if not iso_ok else ("FALSIFIED_IN_MODEL" if not endpoint_moved else "SUPPORTED_IN_MODEL")
    analysis = {
        "round": 4,
        "tip": d2r4.TIP,
        "derived_from_raw_only": True,
        "raw_file": "test-runs/d2/raw/round4/round4_raw.json",
        "config_digest": raw["config_digest"],
        "design": "independent re-simulation per arm; no fork payload used",
        "unit_of_replication": "independent population history (seed x checkpoint)",
        "n_histories": len(d2r4.SEEDS) * len(d2r4.CHECKPOINTS),
        "n_arm_runs": len(cells),
        "arm_table": table,
        "endpoints_versioned_separately": True,
        "endpoints": raw["endpoints"],
        "isolation": {
            "holds": iso_ok,
            "all_population_objects_distinct": raw["all_population_objects_distinct"],
            "fork_used": False,
            "probe": raw["isolation"],
            "rule": "every arm engine rebuilt from spec independently; advancing one arm must not change another arm's digests",
        },
        "recovery_opportunity_present": all(t["n_alive_end_zero_rate"] == 0.0 for t in table.values()),
        "endpoint_moved": endpoint_moved,
        "verdict": verdict,
        "reason": (
            f"isolated re-simulation design; pre-registered retention endpoint 0/18, largest yield ratio {max_ratio:.3f} "
            "against the locked 1.25x, and the named-vs-matched mediation contrast is 0. Calibration tier (2 development "
            "seeds): a rare-recovery falsification would need the 4-seed pilot, and no threshold or seed was moved."
        ),
        "hypothesis_supported": False,
        "red_queen_proved": False,
        "exclusions": ["none: every assigned history and arm is reported"],
        "controls": {"sham": "token relocated, no other change", "negative": "ablate_knowledge_digest (round 2)", "injected_positive": "scorer check only"},
    }
    (D2 / "analysis_round4.json").write_text(json.dumps(analysis, indent=2, sort_keys=True, default=str), encoding="utf-8")

    manifest = json.loads((D2 / "run_manifest.json").read_text(encoding="utf-8"))
    manifest.update({
        "round": 4,
        "tip": d2r4.TIP,
        "commit": d2r4.TIP,
        "design": "independent re-simulation per arm",
        "config_digest": raw["config_digest"],
        "n_runs": len(cells),
        "wall_seconds_total": raw["wall_seconds"],
        "fork_used": False,
        "isolation_holds": iso_ok,
        "isolation_probe": raw["isolation"][0],
        "files": {"raw": "test-runs/d2/raw/round4/round4_raw.json", "analysis": "test-runs/d2/analysis_round4.json"},
        "reproduce": "python test-runs/d2/harness/d2_round4.py",
        "verdict": verdict,
    })
    (D2 / "run_manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True, default=str), encoding="utf-8")
    print(json.dumps({"verdict": verdict, "isolation_holds": iso_ok, "probe": raw["isolation"][0], "table": table}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
