"""Pause handshake between the run process and the console snapshot.

The worker must commit PAUSED and its final progress before it publishes
the ack file, the snapshot must not report PAUSED with progress read
before that commit, and a lock timeout must not stop the heartbeat.
"""

from __future__ import annotations

import json
import pathlib
import threading
import time
from pathlib import Path
from typing import Any

import pytest

from codontrace.console import runs as R
from codontrace.experiments import orchestrator as O
from codontrace.experiments.models import AssessmentStatus, CompletionSummary, ExecutionTrack, MetricRecord


class _Runner:
    experiment_id = "T01"
    arm = "NO_SELECTION"
    track = ExecutionTrack.REFERENCE
    population_size = 4

    def __init__(self, generations: int, boundary: Any = None) -> None:
        self.seed = 7
        self.generations = generations
        self.boundary = boundary
        self.metrics_history: list[Any] = []

    def run(self, on_generation: Any = None) -> CompletionSummary:
        for gen in range(1, self.generations + 1):
            if self.boundary:
                self.boundary(gen)
            record = MetricRecord(gen, 0, 4, "value", float(gen), {})
            self.metrics_history.append(record)
            on_generation(record)
        return CompletionSummary(
            "T01",
            self.track,
            self.seed,
            self.generations,
            0,
            "COMPLETED",
            "HORIZON_REACHED",
            AssessmentStatus.INCONCLUSIVE,
            float(self.generations),
            {},
        )


@pytest.fixture
def env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    root = tmp_path / "simulation_runs"
    monkeypatch.setenv("CODONTRACE_RUNS_DIR", str(root))
    return root


def test_ack_is_published_only_after_paused_is_committed(
    env: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    seen: list[dict[str, Any]] = []
    orch = O.CampaignOrchestrator(tmp_path / "campaign", "handshake")
    real_write_text = pathlib.Path.write_text

    def spy_write_text(self: Path, *args: Any, **kwargs: Any) -> int:
        if self.name.startswith("ack_paused_"):
            # The instant before the ack becomes visible to the console.
            seen.append(json.loads((self.parent / "status.json").read_text(encoding="utf-8")))
            real_write_text(self.parent / "PAUSE.release", "x")
        return real_write_text(self, *args, **kwargs)

    monkeypatch.setattr(pathlib.Path, "write_text", spy_write_text)

    def boundary(gen: int) -> None:
        if gen == 3:
            run_dir = orch.last_run_dir
            assert run_dir is not None
            real_write_text(run_dir / "PAUSE", "paused\n")

            def release() -> None:
                deadline = time.monotonic() + 30
                while not (run_dir / "PAUSE.release").exists() and time.monotonic() < deadline:
                    time.sleep(0.01)
                (run_dir / "PAUSE").unlink(missing_ok=True)

            threading.Thread(target=release, daemon=True).start()

    orch.run_experiment(_Runner(5, boundary))
    assert len(seen) == 1
    assert seen[0]["status"] == "PAUSED", "ack published before PAUSED was committed"
    assert seen[0]["work_done"] == 3


def test_paused_snapshot_rereads_progress_committed_before_the_ack(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    run_dir = tmp_path / "run1"
    run_dir.mkdir()
    params = {"scriptName": "genesis_long_board_campaign.py", "workers": 1, "seeds": [7]}
    # What the worker committed just before publishing the ack.
    committed = {"status": "PAUSED", "revision": 6, "work_done": 6, "work_total": 10, "pct": 60.0, "params": params}
    (run_dir / "status.json").write_text(json.dumps(committed), encoding="utf-8")
    (run_dir / "PAUSE").write_text("x", encoding="utf-8")
    (run_dir / "ack_paused_1").write_text("s", encoding="utf-8")
    monkeypatch.setattr(R, "get_safe_run_dir", lambda run_id, must_exist=False: run_dir)
    # What the console read one tick earlier, before the ack existed.
    stale = {"status": "RUNNING", "revision": 5, "work_done": 5, "work_total": 10, "pct": 50.0, "params": params}
    snap = R.build_run_snapshot("run1", stale, {"params": params})
    assert snap["progress"]["done"] == 6.0, snap["progress"]


def test_heartbeat_survives_a_lock_timeout(env: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    calls = {"ok": 0, "timeouts": 0}
    real = O.write_status_json

    def flaky(path: Path, data: dict[str, Any], **kw: Any) -> dict[str, Any]:
        if threading.current_thread().name.startswith("heartbeat-"):
            if calls["timeouts"] < 2:
                calls["timeouts"] += 1
                raise R.StatusLockTimeout("forced")
            calls["ok"] += 1
        return real(path, data, **kw)

    monkeypatch.setattr(O, "write_status_json", flaky)
    orch = O.CampaignOrchestrator(tmp_path / "campaign", "heartbeat")
    orch.heartbeat_seconds = 0.02

    def boundary(gen: int) -> None:
        deadline = time.monotonic() + 5
        while gen == 2 and calls["ok"] < 2 and time.monotonic() < deadline:
            time.sleep(0.01)

    orch.run_experiment(_Runner(3, boundary))
    assert calls["timeouts"] == 2
    assert calls["ok"] >= 2, "heartbeat thread stopped after a lock timeout"
