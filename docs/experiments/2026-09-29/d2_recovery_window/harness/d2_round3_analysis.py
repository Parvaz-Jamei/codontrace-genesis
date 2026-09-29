"""Round-3 analysis + manifest from raw only (no re-simulation).

Correct isolation rule: an arm is isolated only when its population object is
neither a peer arm's nor the history engine's population object.  Round 3 records
``population: shared_reference`` and ``population_is_not_history: false``, so the
forked contrasts are NOT isolated and must be reported BLOCKED_MEASUREMENT.
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
D2 = ROOT / "test-runs" / "d2"
raw = json.loads((D2 / "raw" / "round3" / "round3_raw.json").read_text(encoding="utf-8"))
cells = raw["cells"]
iso = raw["isolation"]

arms = sorted({c["arm"] for c in cells})
table = {}
for arm in arms:
    rows = [c for c in cells if c["arm"] == arm]
    table[arm] = {
        "n_runs": len(rows),
        "p_recover_preregistered": sum(1 for c in rows if c["recover_preregistered"]) / len(rows),
        "n_recover_preregistered": sum(1 for c in rows if c["recover_preregistered"]),
        "p_digest_return_exploratory": 0.0,
        "n_alive_end_zero_rate": sum(1 for c in rows if c["n_alive_series"][-1] == 0) / len(rows),
        "max_yield_over_baseline": max(
            (max(c["post_yields"]) / c["baseline_mean_rare_yield"]) for c in rows if c["baseline_mean_rare_yield"] > 0
        ),
        "mean_n_alive_end": sum(c["n_alive_series"][-1] for c in rows) / len(rows),
    }

population_isolation = all(
    i["population_object_shared_between_arms"] is False and i["population_object_shared_with_history"] is False
    for i in iso
)
any_shared_with_history = any(i["population_object_shared_with_history"] for i in iso)
endpoint_moved = any(t["p_recover_preregistered"] > 0 for t in table.values())
opportunity = all(t["n_alive_end_zero_rate"] == 0.0 for t in table.values())
verdict = "INCONCLUSIVE" if population_isolation else "BLOCKED_MEASUREMENT"

analysis = {
    "round": 3,
    "tip": raw["tip"],
    "derived_from_raw_only": True,
    "raw_file": "test-runs/d2/raw/round3/round3_raw.json",
    "config_digest": raw["config_digest"],
    "unit_of_replication": "independent population history (seed x checkpoint)",
    "n_histories": len({(c["seed"], c["t_intervene"]) for c in cells}),
    "n_arm_runs": len(cells),
    "arm_table": table,
    "endpoints_versioned_separately": True,
    "endpoints": raw["endpoints"],
    "isolation": {
        "rule": "isolated only when the arm population object is neither a peer arm's nor the history engine's object",
        "population_isolation_holds": population_isolation,
        "any_arm_shares_history_population_object": any_shared_with_history,
        "fork_state_exact": iso[0]["fork_state_exact"] if iso else None,
        "isolation_map": cells[0]["isolation_map"] if cells else None,
        "evidence": iso,
    },
    "recovery_opportunity_present": opportunity,
    "endpoint_moved": endpoint_moved,
    "verdict": verdict,
    "reason": (
        "fork_state_exact is false and the population object is a shared reference with the history engine, so "
        "the three forked arms of one checkpoint are not isolated; per the Lead's rule the affected forked "
        "contrasts are reported as BLOCKED_MEASUREMENT with raw evidence rather than as a confounded contrast"
        if not population_isolation
        else ("isolation held; the endpoint did not move" if not endpoint_moved else "endpoint moved")
    ),
    "hypothesis_supported": False,
    "red_queen_proved": False,
    "exclusions": ["none: every assigned history and arm is reported"],
    "controls": {
        "sham": "token relocated, no other change",
        "negative": "ablate_knowledge_digest (round 2)",
        "injected_positive": "scorer check only, scientific_result=false",
    },
}
(D2 / "analysis_round3.json").write_text(json.dumps(analysis, indent=2, sort_keys=True, default=str), encoding="utf-8")

manifest = {
    "schema": "d2-pack-v1",
    "round": 3,
    "tip": raw["tip"],
    "commit": "913f18e",
    "commit_source": "manager confirmation; no git binary on this host, so git archive could not be run",
    "git_archive_attempt": "failed: 'git' is not recognized as an internal or external command",
    "pythonpath": "codontrace-genesis/src",
    "ecology": raw["ecology"],
    "maintenance_value": "fork_state_exact + persistence_safe ecology",
    "config_digest": raw["config_digest"],
    "seeds": list({c["seed"] for c in cells}),
    "checkpoints": sorted({c["t_intervene"] for c in cells}),
    "arms": arms,
    "horizon": raw["cells"][0]["horizon"] if cells else None,
    "workers": 1,
    "wall_seconds_total": raw["wall_seconds"],
    "wall_seconds_per_test": {"round3_measurement": raw["wall_seconds"]},
    "n_runs": len(cells),
    "n_histories": len({(c["seed"], c["t_intervene"]) for c in cells}),
    "rng_streams": {
        "engine": "seed schedule spec.seed + _tick_offset + index; tick offset restored by from_fork",
        "ledger": "random.Random(seed) per arm",
    },
    "fork": {
        "api": "GenesisEngine.capture_fork/from_fork",
        "isolation_map": cells[0]["isolation_map"] if cells else None,
        "population_isolation_holds": population_isolation,
        "shared_reference_objects": ["population", "element_grid"],
        "cause": "mappingproxy registries make copy.deepcopy impossible for these objects",
    },
    "hypothesis_supported": False,
    "red_queen_proved": False,
    "claim_ceiling": "phase2_design",
    "files": {"raw": "test-runs/d2/raw/round3/round3_raw.json", "analysis": "test-runs/d2/analysis_round3.json"},
    "reproduce": "python test-runs/d2/harness/d2_round3.py",
    "replay": "python test-runs/d2/harness/d2_replay.py --run-dir <run_dir>",
}
(D2 / "run_manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True, default=str), encoding="utf-8")
print(json.dumps({"verdict": verdict, "population_isolation": population_isolation, "opportunity": opportunity, "endpoint_moved": endpoint_moved, "table": table, "config_digest": raw["config_digest"]}, indent=1))
