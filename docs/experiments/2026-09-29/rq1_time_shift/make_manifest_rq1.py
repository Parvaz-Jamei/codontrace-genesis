"""Build run_manifest.json for the RQ-1 pack from the raw artifacts.

The manifest records commit, design/config hashes, schema versions, seeds and
RNG stream names, wall/CPU/RAM, the stop code, the parent snapshot id, the
parameters and the arm names, plus a checksum for every artifact.
"""

from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path

OUT = Path(__file__).resolve().parent
RAW = OUT / "raw"


def sha256(path: Path) -> str | None:
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else None


def main() -> int:
    run = json.loads((RAW / "probe_run.json").read_text(encoding="utf-8"))
    analysis = json.loads((OUT / "analysis.json").read_text(encoding="utf-8"))
    fixtures = json.loads((RAW / "stage0_fixtures.json").read_text(encoding="utf-8"))
    live_analysis_path = OUT / "analysis_live.json"
    live_analysis = (
        json.loads(live_analysis_path.read_text(encoding="utf-8"))
        if live_analysis_path.exists()
        else None
    )
    live_run_path = RAW / "live_run.json"
    live_run = (
        json.loads(live_run_path.read_text(encoding="utf-8"))
        if live_run_path.exists()
        else None
    )

    scripts = [
        "probe_rq1.py",
        "stage0_fixtures_rq1.py",
        "analysis_rq1.py",
        "verify_patch_rq1.py",
        "replay_rq1.py",
        "make_manifest_rq1.py",
        "design.md",
        "PROPOSED_CHANGE.patch",
    ]
    config_hashes = {name: sha256(OUT / name) for name in scripts}

    artifacts = {}
    tracked = list(RAW.iterdir()) + [
        OUT / "analysis.json",
        OUT / "effect_table.json",
        OUT / "design.md",
        OUT / "prior_art.md",
        OUT / "decision.md",
        OUT / "EXCLUSIONS.md",
        OUT / "NOTES.md",
        OUT / "PROPOSED_CHANGE.patch",
        OUT / "PROPOSED_CHANGE_NOTES.md",
        OUT / "analysis_live.json",
        OUT / "live_summary.json",
    ]
    for path in sorted(tracked):
        if path.is_file():
            artifacts[path.name] = {
                "sha256": sha256(path),
                "bytes": path.stat().st_size,
            }

    step_walls = {
        name: step.get("wall_s") for name, step in (run.get("steps") or {}).items()
    }
    manifest = {
        "schema_version": "rq1_run_manifest_v1",
        "pack_id": "RQ1-TIME-SHIFT-20260929",
        "test_id": "RQ-1",
        "created_utc_date": "2026-09-29",
        "commit": (run.get("repo_head") or {}).get("commit"),
        "dirty_flag": (run.get("repo_head") or {}).get("dirty_flag"),
        "dirty_flag_reason": (run.get("repo_head") or {}).get("dirty_flag_reason"),
        "working_tree_note": (
            "The git executable is not on PATH, so the dirty flag is null. The "
            "working tree was observed to change during this session (the manager "
            "is the single writer): host_parasite_world.py moved from sha256 "
            "88f5acf41832d8e5fb4f837d7695187d3ed3d0bec956e5bf08ae86de189027bb to "
            "17e3ffbd397a7e9dbea04568c07d039b9d9a872c2935aa96ee28f257309320a8. "
            "PROPOSED_CHANGE.patch was rebased onto the newer file and re-verified "
            "(logs/patch_verify.txt = PATCH_OK). Source hashes below are the ones "
            "recorded by the probe run."
        ),
        "repo_head": run.get("repo_head"),
        "config_hashes": config_hashes,
        "design_hash": config_hashes.get("design.md"),
        "design_locked_before_confirmatory_seed": True,
        "schema_versions": {
            "probe": "rq1_probe_v1",
            "stage0_fixtures": "rq1_stage0_fixtures_v1",
            "analysis": "rq1_analysis_v1",
            "run_manifest": "rq1_run_manifest_v1",
            "events": "rq1_probe_v1",
            "population": "rq1_probe_v1",
        },
        "seeds": {
            "live_probe_seeds": [301, 302],
            "host_parasite_history_seeds": [11, 22],
            "randomisation_seed": 20260929,
            "cluster_bootstrap_seed": 20260928,
            "confirmatory_seeds_reserved_unseen": [
                901,
                902,
                903,
                904,
                905,
                906,
                907,
                908,
            ],
        },
        "rng_streams": {
            "engine": "GenesisEngine RNG derived from the built spec seed (one stream per seed)",
            "host_parasite_world": (
                "RNGManager(seed=profile.seed) with labelled forks "
                "contact/<tick>, mutate/<role>/<mid>/<tick>, birth/<role>/<tick>"
            ),
            "arms": None,
            "arms_null_reason": (
                "no frozen / host-only / shuffled arm was launched: no fork point "
                "and no antagonist genotype population exist"
            ),
        },
        "budget": {
            "cap_wall_s_per_test": 480,
            "cap_wall_s_first_pack": 2700,
            "target_memory_bytes": 4 * 1024**3,
            "soft_stop_memory_bytes": int(3.5 * 1024**3),
            "pack_wall_s": run.get("wall_s"),
            "pack_cpu_s": run.get("cpu_s"),
            "peak_rss_bytes": run.get("peak_rss_bytes"),
            "step_walls": step_walls,
            "fixture_wall_s": fixtures.get("wall_s"),
            "within_budget": bool(
                (run.get("wall_s") or 0) <= 480
                and (run.get("peak_rss_bytes") or 0) <= 4 * 1024**3
            ),
        },
        "stop_code": (
            (live_analysis or {}).get("decision", {}).get("verdict")
            or analysis.get("decision")
        ),
        "stop_reason": (
            (live_analysis or {}).get("decision", {}).get("reason")
            or analysis.get("decision_reason")
        ),
        "round": 2,
        "live_route": {
            "route": (live_run or {}).get("route"),
            "design": (live_run or {}).get("design"),
            "wall_s": (live_run or {}).get("wall_s"),
            "calibration_gate_ok": (live_run or {}).get("calibration_gate_ok"),
            "pilot_gate_ok": (live_run or {}).get("pilot_gate_ok"),
            "n_seeds_completed": sum(
                1 for r in (live_run or {}).get("seeds", []) if not r.get("skipped")
            ),
            "summary": (live_analysis or {}).get("summary", {}).get("arms"),
            "rotation_control": (live_analysis or {}).get("summary", {}).get(
                "rotation_control"
            ),
            "integrity": (live_analysis or {}).get("summary", {}).get("integrity"),
            "verdict": (live_analysis or {}).get("decision", {}).get("verdict"),
        },
        "parent_snapshot_id": None,
        "parent_snapshot_null_reason": (
            "no full-state fork exists; RunCheckpoint carries digests only "
            "(run_id, tick, manifest_digest, snapshot_digest, rng_state_digest)"
        ),
        "parameters": {
            "live_probe_generations": 8,
            "live_probe_population": 4,
            "host_parasite_ticks": 30,
            "host_parasite_lag": 10,
            "host_parasite_time_slots": {"past": 10, "now": 20, "future": 30},
            "contact_rule": "reference_graded_affinity, 3 sub-loci x 2 bits",
            "kappa": 1.2,
            "virulence": 8.0,
            "steal_fraction": 0.15,
            "locked_thresholds_not_used_for_rq1": [0.20, -0.148],
        },
        "arms": [
            {"arm": "copassaged", "passage": "coevolve", "status": "ran", "is_rq1_arm": True},
            {"arm": "fixed", "passage": "frozen", "status": "ran", "is_rq1_arm": False},
            {"arm": "avirulent", "passage": "absent", "status": "ran", "is_rq1_arm": False},
            {
                "arm": "shuffled_time_labels",
                "status": "ran_as_matrix_control",
                "is_rq1_arm": False,
            },
            {
                "arm": "live_generation_probe",
                "status": "ran_as_precondition_probe",
                "is_rq1_arm": False,
            },
        ],
        "live_parameters": {
            "route": "StructuralRQArm",
            "generations": 40,
            "slots": {"past": 20, "now": 30, "future": 40},
            "lag": 10,
            "kappa": 1.2,
            "contact_mode": "full_matrix",
            "arms": {"copassaged": "coevolve", "fixed": "frozen", "avirulent": "absent"},
            "seeds": {
                "calibration": [5501, 5502],
                "pilot": [5601, 5602, 5603, 5604],
                "reserved_not_drawn": [5701, 5702, 5703, 5704, 5705, 5706, 5707, 5708],
            },
            "pack_wall_s": (live_run or {}).get("wall_s"),
        },
        "events_jsonl_fields": [
            "run_id",
            "seed",
            "arm",
            "generation",
            "event_id",
            "organism_id",
            "parent_id",
            "genotype_digest",
            "antagonist_digest",
            "contact_edge_id",
            "opportunity",
            "matched",
            "intended_debit",
            "realised_debit",
            "atp_before",
            "atp_after",
            "birth",
            "death",
            "mutation",
            "intervention_id",
        ],
        "events_jsonl_null_reasons_present": True,
        "analysis_digest": analysis.get("analysis_digest"),
        "decision": (
            (live_analysis or {}).get("decision", {}).get("verdict")
            or analysis.get("decision")
        ),
        "instrument_decision_after_precondition_probe": analysis.get("decision"),
        "artifacts": artifacts,
        "replay_command": (
            "C:\\Users\\parvaz\\AppData\\Local\\Programs\\Python\\Python314\\python.exe "
            "replay_rq1.py --from-manifest run_manifest.json"
        ),
        "manifest_created_wall_s": round(time.perf_counter(), 6),
    }
    (OUT / "run_manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "manifest": "run_manifest.json",
                "commit": manifest["commit"],
                "stop_code": manifest["stop_code"],
                "decision": manifest["decision"],
                "n_artifacts": len(artifacts),
                "within_budget": manifest["budget"]["within_budget"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
