"""The console must not write a stale progress copy back over status.json."""

from __future__ import annotations

import json
from pathlib import Path

from codontrace.console.runs import _write_status_transition


def test_transition_keeps_worker_progress(tmp_path: Path) -> None:
    status_file = tmp_path / "status.json"
    # The worker persisted generation 257 after the console read 256.
    status_file.write_text(json.dumps({"status": "RUNNING", "work_done": 257, "revision": 9}), encoding="utf-8")
    stale = {"status": "RUNNING", "work_done": 256, "revision": 7}
    _write_status_transition(status_file, stale, "PAUSED")
    fresh = json.loads(status_file.read_text(encoding="utf-8"))
    assert fresh["status"] == "PAUSED"
    assert fresh["work_done"] == 257
    assert fresh["revision"] == 10


def test_transition_falls_back_when_status_unreadable(tmp_path: Path) -> None:
    status_file = tmp_path / "status.json"
    status_file.write_text("{not json", encoding="utf-8")
    _write_status_transition(status_file, {"work_done": 3, "revision": 2}, "PAUSING")
    fresh = json.loads(status_file.read_text(encoding="utf-8"))
    assert fresh == {"work_done": 3, "revision": 3, "status": "PAUSING"}
