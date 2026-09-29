"""Mechanism check for the confirmatory runner. Does NOT run a confirmatory seed."""
from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location(
    "conf_mod", HERE / "confirmatory_rq1.py"
)
mod = importlib.util.module_from_spec(spec)
sys.modules["conf_mod"] = mod
spec.loader.exec_module(mod)

from codontrace.genesis.closed_loop_hp_arm01_structural_rq import StructuralRQArm  # noqa: E402

out = {}
mod.RAW = Path(tempfile.mkdtemp(prefix="rq1_smoke_"))
arm = StructuralRQArm.boot_structural(arm="copassaged", seed=1)
arm.collect_realised_host_pressure = True
em = mod._Emitter(1, "copassaged", "coevolve")
em.RAW = mod.RAW


def bridge(*, generation_index: int) -> None:
    em(generation_index=generation_index, arm=arm)


arm.generation_boundary_observer = bridge
arm.run_generations(3)
em.close()
loaded = (mod.RAW / "events_seed1.jsonl").read_text(encoding="utf-8").strip().splitlines()
snaps = {s: arm.window_snapshot(mod.SLOTS[s]) for s in mod.TIMES}
mat = {}
for ti in mod.TIMES:
    mat[ti] = {}
    hf = {str(k): float(v) for k, v in snaps[ti]["joint_freq"].items()}
    for tj in mod.TIMES:
        mat[ti][tj] = round(
            mod.pressure_cell(hf, [str(k) for k in snaps[tj]["parasite_class_hist"]]), 10
        )
m = mod.contrast(mat)
print(
    json.dumps(
        {
            "events_written": len(loaded),
            "first_event_keys": sorted(json.loads(loaded[0]).keys())[:8],
            "config_digest": mod.CONFIG_DIGEST,
            "slots": mod.SLOTS,
            "matrix_3gen": mat,
            "contrast": m,
            "paired_interval_two": mod._paired_interval([1.0, 3.0]),
        },
        indent=2,
    )
)
