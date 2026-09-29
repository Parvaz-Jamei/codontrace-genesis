"""RQ-1 feasibility probe: is the structural RQ arm a runnable dated route?

Read-only. Measures wall time per generation and reports what the dated
snapshots expose. No repo change, no seed tuning.
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

REPO = Path(r"E:\مقاله پزشکی شبیه سازی ویروس\codontrace-genesis")
if str(REPO / "src") not in sys.path:
    sys.path.insert(0, str(REPO / "src"))

from codontrace.genesis.closed_loop_hp_arm01_structural_rq import (  # noqa: E402
    ECOLOGY_ARMS,
    PASSAGE_ABSENT,
    PASSAGE_COEVOLVE,
    PASSAGE_FROZEN,
    StructuralRQArm,
)

OUT = Path(__file__).resolve().parent
RAW = OUT / "raw"
RAW.mkdir(parents=True, exist_ok=True)

report: dict[str, object] = {
    "schema_version": "rq1_feasibility_v1",
    "ecology_arms": list(ECOLOGY_ARMS),
    "passage_constants": {
        "coevolve": PASSAGE_COEVOLVE,
        "frozen": PASSAGE_FROZEN,
        "absent": PASSAGE_ABSENT,
    },
    "arms": [],
    "errors": [],
}

for arm_name in ECOLOGY_ARMS:
    t0 = time.perf_counter()
    try:
        arm = StructuralRQArm.boot_structural(arm=arm_name, seed=9001)
        boot_s = time.perf_counter() - t0
        arm.collect_realised_host_pressure = True
        t1 = time.perf_counter()
        arm.run_generations(10)
        run_s = time.perf_counter() - t1
        snap = arm.window_snapshot(5)
        report["arms"].append(
            {
                "arm": arm_name,
                "passage": arm.passage,
                "boot_s": round(boot_s, 3),
                "run_10_gens_s": round(run_s, 3),
                "s_per_generation": round(run_s / 10.0, 4),
                "parasite_windows_n": len(arm.parasite_windows),
                "host_sub_locus_series_len": len(arm.host_sub_locus_series),
                "host_joint_series_len": len(arm.host_joint_class_series),
                "parasite_class_hist_series_len": len(arm.parasite_class_hist_series),
                "host_realised_pressure_series_len": len(
                    arm.host_realised_pressure_series
                ),
                "snapshot_5_keys": sorted(snap.keys()),
                "snapshot_5_host_classes": len(snap["joint_freq"]),
                "snapshot_5_parasite_classes": len(snap["parasite_class_hist"]),
                "snapshot_5_host_pressure_classes": len(
                    snap["host_realised_pressure"]
                ),
                "snapshot_5_census": snap["census"],
                "snapshot_5_parasite_n": snap["parasite_n"],
                "sample_host_classes": list(snap["joint_freq"])[:5],
                "sample_parasite_classes": list(snap["parasite_class_hist"])[:5],
                "sample_host_pressure": dict(
                    list(snap["host_realised_pressure"].items())[:5]
                ),
            }
        )
    except Exception as exc:  # noqa: BLE001
        import traceback

        report["errors"].append(
            {"arm": arm_name, "error": type(exc).__name__, "traceback": traceback.format_exc()}
        )

(RAW / "feasibility_structural.json").write_text(
    json.dumps(report, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8"
)
print(json.dumps(report, indent=2, default=str))
