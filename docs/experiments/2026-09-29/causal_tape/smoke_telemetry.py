"""Smoke test for the telemetry layer: live log, snapshots, manifest, resume."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

from telemetry import Telemetry, completed_keys, config_digest, iter_missing

ROOT = Path(__file__).resolve().parent / "runs_smoke"
if ROOT.exists():
    shutil.rmtree(ROOT)

cfg = {"test": "smoke", "seed": 1, "generations": 20}

tele = Telemetry(ROOT, "smoke", "run-1", cfg, snapshot_every=5)
for generation in range(1, 21):
    tele.event(event="generation", generation=generation, fitness=float(generation) * 0.5)
    tele.snapshot(generation, {"fitness": float(generation) * 0.5, "census": 100 + generation})
tele.close({"final": 10.0})

assert tele.log_path.exists(), "log missing"
lines = tele.log_path.read_text(encoding="utf-8").strip().splitlines()
assert len(lines) == 20, f"expected 20 live log lines, got {len(lines)}"
assert json.loads(lines[0])["generation"] == 1

manifest = json.loads(tele.manifest_path.read_text(encoding="utf-8"))
assert manifest["status"] == "done" and manifest["config_digest"] == config_digest(cfg)

import numpy as np

with np.load(tele.snap_path, allow_pickle=True) as data:
    gens = data["generation"]
assert list(gens) == [5, 10, 15, 20], f"decimation wrong: {list(gens)}"

done = completed_keys(ROOT, "smoke")
assert done == {"run-1"}, done
todo = iter_missing(["run-1", "run-2"], done)
assert todo == ["run-2"], todo

print("logs:", tele.log_path.name, len(lines), "lines")
print("snapshots:", list(gens))
print("manifest:", manifest["status"], manifest["config_digest"][:12])
print("resume:", sorted(done), "->", todo)
print("TELEMETRY_OK")
