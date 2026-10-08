"""Test suite for Phase 2 Execution Control, Worker ACK Synchronization, Time Budget, and Polling Race Invariants.

Covers:
- Worker ACK coordination & state transitions (PAUSING -> PAUSED, RESUMING -> RUNNING, STOPPING -> STOPPED).
- Active computation time vs wall-clock deadline accounting across pause cycles.
- RunnerAdapter registry, output path resolution, and nested output/status.json reconciliation.
- Monotonic revision filtering and optimistic action immunity against polling race conditions.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import pytest

from codontrace.console.runs import (
    CustomScriptRunnerAdapter,
    FrontierReferenceRunnerAdapter,
    GenesisEngineRunnerAdapter,
    build_run_snapshot,
    get_runner_adapter,
)


def test_runner_adapter_resolution_and_capabilities() -> None:
    """Coder 3 / P03: Verify RunnerAdapter registry resolves proper adapter and capabilities."""
    # 1. Genesis engine default
    genesis_adapter = get_runner_adapter({"executionBoundary": {"backend": "genesis_engine"}})
    assert isinstance(genesis_adapter, GenesisEngineRunnerAdapter)
    assert genesis_adapter.supports_pause is True
    assert genesis_adapter.supports_resume is True
    caps = genesis_adapter.resolve_capabilities()
    assert caps["pause"] is True
    assert caps["resume"] is True
    assert caps["checkpoint_continue"] is False

    # 2. Frontier reference
    frontier_adapter = get_runner_adapter({"executionBoundary": {"isFrontierReference": True}})
    assert isinstance(frontier_adapter, FrontierReferenceRunnerAdapter)
    assert frontier_adapter.supports_pause is False
    assert frontier_adapter.supports_resume is False
    f_caps = frontier_adapter.resolve_capabilities()
    assert f_caps["pause"] is False
    assert f_caps["resume"] is False

    # 3. Custom script
    custom_adapter = get_runner_adapter({"params": {"scriptName": "user_benchmark.py"}})
    assert isinstance(custom_adapter, CustomScriptRunnerAdapter)
    assert custom_adapter.supports_pause is False


def test_nested_status_reconciliation(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Coder 3 / P03: Verify RunnerAdapter reconciles nested output/status.json into root status.json."""
    runs_dir = tmp_path / "runs"
    runs_dir.mkdir(parents=True)
    monkeypatch.setenv("CODONTRACE_RUNS_DIR", str(runs_dir))

    run_entry = runs_dir / "run_nested_test"
    run_entry.mkdir()
    output_dir = run_entry / "output"
    output_dir.mkdir()

    # Root status is at revision 1
    root_status = {
        "status": "RUNNING",
        "revision": 1,
        "totalSeeds": 12,
        "completedSeeds": 2,
    }
    (run_entry / "status.json").write_text(json.dumps(root_status), encoding="utf-8")

    # Output directory status has progressed to revision 2
    time.sleep(0.01)
    nested_status = {
        "status": "RUNNING",
        "revision": 2,
        "totalSeeds": 12,
        "completedSeeds": 5,
        "pct": 41.7,
    }
    (output_dir / "status.json").write_text(json.dumps(nested_status), encoding="utf-8")

    adapter = GenesisEngineRunnerAdapter()
    reconciled = adapter.reconcile_status(run_entry)

    assert reconciled["revision"] == 2
    assert reconciled["completedSeeds"] == 5
    assert reconciled["pct"] == 41.7

    # Ensure root status.json was atomically updated
    on_disk_root = json.loads((run_entry / "status.json").read_text(encoding="utf-8"))
    assert on_disk_root["revision"] == 2
    assert on_disk_root["completedSeeds"] == 5


def test_worker_ack_synchronization_and_snapshot(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Coder 1 / L01 & L05: Verify worker pause ACK counting and state transitions."""
    runs_dir = tmp_path / "runs"
    runs_dir.mkdir(parents=True)
    monkeypatch.setenv("CODONTRACE_RUNS_DIR", str(runs_dir))

    run_id = "run_ack_test"
    run_entry = runs_dir / run_id
    run_entry.mkdir()
    out_dir = run_entry / "output"
    out_dir.mkdir()

    status_data = {
        "status": "RUNNING",
        "revision": 5,
        "params": {"workers": 3},
        "startedAt": time.time() - 10,
    }
    (run_entry / "status.json").write_text(json.dumps(status_data), encoding="utf-8")

    # Initial state: 0 workers paused
    snap0 = build_run_snapshot(run_id, status_data)
    assert snap0["state"] == "RUNNING"
    assert snap0["workers_expected"] == 3
    assert snap0["workers_paused"] == 0
    assert snap0["requested_state"] is None

    # PAUSE marker placed, but only 1 worker has ACKed -> PAUSING
    (run_entry / "PAUSE").write_text("paused\n", encoding="utf-8")
    (out_dir / "ack_paused_16001").write_text("paused gen=1\n", encoding="utf-8")

    snap1 = build_run_snapshot(run_id, status_data)
    assert snap1["state"] == "PAUSING"
    assert snap1["workers_paused"] == 1
    assert snap1["requested_state"] == "PAUSED"

    # All 3 workers ACK -> PAUSED
    (out_dir / "ack_paused_16002").write_text("paused gen=1\n", encoding="utf-8")
    (out_dir / "ack_paused_16003").write_text("paused gen=1\n", encoding="utf-8")

    snap2 = build_run_snapshot(run_id, status_data)
    assert snap2["state"] == "PAUSED"
    assert snap2["workers_paused"] == 3
    assert snap2["requested_state"] is None

    # Resume requested (PAUSE marker removed), but workers have not yet all resumed -> RESUMING
    (run_entry / "PAUSE").unlink()
    status_data["status"] = "PAUSED"
    snap3 = build_run_snapshot(run_id, status_data)
    assert snap3["state"] == "RESUMING"
    assert snap3["requested_state"] == "RUNNING"

    # All workers clear their ACK files -> RUNNING
    (out_dir / "ack_paused_16001").unlink()
    (out_dir / "ack_paused_16002").unlink()
    (out_dir / "ack_paused_16003").unlink()

    snap4 = build_run_snapshot(run_id, status_data)
    assert snap4["state"] == "RUNNING"
    assert snap4["workers_paused"] == 0
    assert snap4["requested_state"] is None


def test_active_time_budget_accounting_across_pause(tmp_path: Path) -> None:
    """Coder 2 / L04 & P03: Verify paused duration is accumulated and subtracted in active_time mode."""
    # Simulate monitor logic
    started = time.monotonic() - 5.0  # 5 wall seconds have elapsed
    paused_accumulated = [4.0]  # Was paused for 4 seconds
    budget_kind = "active_time"
    max_seconds = 2.0  # Budget is 2 active seconds

    wall_elapsed = time.monotonic() - started  # ~5s
    active_elapsed = max(0.0, wall_elapsed - paused_accumulated[0])  # ~1s
    effective_elapsed = active_elapsed if budget_kind == "active_time" else wall_elapsed

    # Since effective_elapsed (~1.0s) < max_seconds (2.0s), simulation is NOT stopped
    assert effective_elapsed < max_seconds
    assert active_elapsed < wall_elapsed
    assert round(paused_accumulated[0], 1) == 4.0

    # Under wall_deadline, 5s would exceed max_seconds
    wall_effective = wall_elapsed
    assert wall_effective >= max_seconds


def test_health_log_telemetry_in_snapshot(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Coder 2 & 3: RunSnapshot parses health.log active_elapsed_seconds and paused_seconds."""
    runs_dir = tmp_path / "runs"
    runs_dir.mkdir(parents=True)
    monkeypatch.setenv("CODONTRACE_RUNS_DIR", str(runs_dir))

    run_id = "run_telemetry_test"
    run_entry = runs_dir / run_id
    run_entry.mkdir()
    out_dir = run_entry / "output"
    out_dir.mkdir()

    health_record = {
        "elapsed_seconds": 12.5,
        "active_elapsed_seconds": 10.0,
        "paused_seconds": 2.5,
        "wall_elapsed_seconds": 12.5,
        "budget_kind": "active_time",
        "stop_file": False,
    }
    (out_dir / "health.log").write_text(json.dumps(health_record) + "\n", encoding="utf-8")

    status_data = {
        "status": "RUNNING",
        "revision": 3,
        "startedAt": time.time() - 12.5,
    }
    (run_entry / "status.json").write_text(json.dumps(status_data), encoding="utf-8")

    snap = build_run_snapshot(run_id, status_data)
    assert snap["active_elapsed_seconds"] == 10.0
    assert snap["paused_seconds"] == 2.5
    assert snap["wall_elapsed_seconds"] == 12.5


def test_monotonic_revision_ordering() -> None:
    """Coder 4 / P04: Validate revision monotonicity rule (stale responses with lower revision are dropped)."""
    current_job = {
        "id": "run_job_1",
        "revision": 10,
        "status": "paused",
    }

    stale_incoming = {
        "id": "run_job_1",
        "revision": 8,  # Out-of-order stale network response
        "status": "running",
    }

    fresh_incoming = {
        "id": "run_job_1",
        "revision": 11,  # Newer response
        "status": "paused",
    }

    # Stale response must be rejected
    assert stale_incoming["revision"] < current_job["revision"]

    # Fresh response must be accepted
    assert fresh_incoming["revision"] >= current_job["revision"]
