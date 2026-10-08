"""Test suite for Phase 1 contract, schema, lifecycle errors, and progress invariants.

Covers:
- L01: False positive pause prevention on dead/completed/failed/stopped runs (HTTP 409).
- L02: Import completeness along discovery & runner execution paths.
- L03: Resume restrictions on stopped/dead processes (HTTP 409) vs restart capability.
- Section 3 & P02: RunSnapshot v2 schema validation, snapshot construction, and list/detail parity.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from codontrace.console import runs
from codontrace.errors import ConfigurationError
from codontrace.genesis import snapshot

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_dead_completed_run_cannot_be_paused(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """L01: An inactive completed run without living process must reject pause with 409."""
    runs_dir = tmp_path / "runs"
    runs_dir.mkdir(parents=True)
    monkeypatch.setenv("CODONTRACE_RUNS_DIR", str(runs_dir))

    run_id = "run_completed_dead_001"
    run_entry = runs_dir / run_id
    run_entry.mkdir()

    status_data = {
        "schemaVersion": 1,
        "runId": run_id,
        "status": "COMPLETED",
        "title": "Completed Run",
        "pct": 100.0,
        "pid": 99999999,  # Non-existent/dead PID
    }
    (run_entry / "status.json").write_text(json.dumps(status_data), encoding="utf-8")

    # Attempt pause
    res = runs.manage_run_action(run_id, "pause")
    assert res["ok"] is False
    assert res["status_code"] == 409
    assert res.get("error_code") == "INVALID_STATE"

    # Invariant: No PAUSE marker file must be created
    assert not (run_entry / "PAUSE").exists()

    # Invariant: Status must remain COMPLETED, not overwritten to PAUSED
    refreshed_status = json.loads((run_entry / "status.json").read_text(encoding="utf-8"))
    assert refreshed_status["status"] == "COMPLETED"


def test_stopped_run_cannot_be_resumed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """L03: A STOPPED run cannot be resumed with a simple signal toggle; must return 409."""
    runs_dir = tmp_path / "runs"
    runs_dir.mkdir(parents=True)
    monkeypatch.setenv("CODONTRACE_RUNS_DIR", str(runs_dir))

    run_id = "run_stopped_dead_002"
    run_entry = runs_dir / run_id
    run_entry.mkdir()

    status_data = {
        "schemaVersion": 1,
        "runId": run_id,
        "status": "STOPPED",
        "title": "Stopped Run",
        "pct": 45.0,
        "pid": 99999998,
    }
    (run_entry / "status.json").write_text(json.dumps(status_data), encoding="utf-8")

    res = runs.manage_run_action(run_id, "resume")
    assert res["ok"] is False
    assert res["status_code"] == 409
    assert res.get("error_code") == "INVALID_STATE"

    # Status must remain STOPPED
    refreshed = json.loads((run_entry / "status.json").read_text(encoding="utf-8"))
    assert refreshed["status"] == "STOPPED"


def test_unsupported_runner_pause_rejected(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """L02 & Frontier: Runners without pause support must reject pause with 409."""
    runs_dir = tmp_path / "runs"
    runs_dir.mkdir(parents=True)
    monkeypatch.setenv("CODONTRACE_RUNS_DIR", str(runs_dir))

    run_id = "run_frontier_unsupported_003"
    run_entry = runs_dir / run_id
    run_entry.mkdir()

    manifest_data = {
        "schemaVersion": 1,
        "runId": run_id,
        "capabilities": {"pause": False, "resume": False, "checkpoint_continue": False},
        "executionBoundary": {"isFrontierReference": True},
    }
    (run_entry / "run_manifest.json").write_text(json.dumps(manifest_data), encoding="utf-8")

    status_data = {
        "schemaVersion": 1,
        "runId": run_id,
        "status": "RUNNING",
        "capabilities": {"pause": False, "resume": False, "checkpoint_continue": False},
        "pid": 99999997,
    }
    (run_entry / "status.json").write_text(json.dumps(status_data), encoding="utf-8")

    res = runs.manage_run_action(run_id, "pause")
    assert res["ok"] is False
    assert res["status_code"] == 409
    assert res.get("error_code") == "UNSUPPORTED_CAPABILITY"
    assert not (run_entry / "PAUSE").exists()


def test_run_snapshot_v2_validation_invariants() -> None:
    """Section 3: Strict validation of RunSnapshot v2 schema and invariants."""
    valid_snap = snapshot.create_run_snapshot(
        run_id="run_test",
        session_id="sess_123",
        revision=42,
        state="PAUSED",
        supports_pause=True,
        supports_resume=True,
        workers_expected=4,
        workers_paused=4,
        done=347,
        total=1000,
        pct=34.7,
        active_elapsed=120.0,
        wall_elapsed=130.0,
    )
    assert valid_snap["schema_version"] == "run_snapshot_v2"
    assert valid_snap["state"] == "PAUSED"
    assert valid_snap["progress"]["pct"] == 34.7

    # Reject non-finite numbers
    bad_snap = dict(valid_snap)
    bad_snap["progress"] = dict(valid_snap["progress"], pct=float("nan"))
    with pytest.raises(ConfigurationError):
        snapshot.validate_run_snapshot(bad_snap)

    bad_snap["progress"] = dict(valid_snap["progress"], pct=float("inf"))
    with pytest.raises(ConfigurationError):
        snapshot.validate_run_snapshot(bad_snap)

    # Reject invalid state
    bad_state = dict(valid_snap)
    bad_state["state"] = "INVALID_STATE_XYZ"
    with pytest.raises(ConfigurationError):
        snapshot.validate_run_snapshot(bad_state)

    # Reject negative timing
    bad_time = dict(valid_snap)
    bad_time["active_elapsed_seconds"] = -10.0
    with pytest.raises(ConfigurationError):
        snapshot.validate_run_snapshot(bad_time)


def test_list_and_details_pct_and_snapshot_parity(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """P02: list_simulation_runs and get_run_details must return matching top-level pct and RunSnapshot."""
    runs_dir = tmp_path / "runs"
    runs_dir.mkdir(parents=True)
    monkeypatch.setenv("CODONTRACE_RUNS_DIR", str(runs_dir))

    run_id = "run_parity_004"
    run_entry = runs_dir / run_id
    run_entry.mkdir()

    status_data = {
        "schemaVersion": 1,
        "runId": run_id,
        "status": "RUNNING",
        "title": "Parity Run",
        "pct": 34.7,
        "completedSeeds": 1,
        "totalSeeds": 4,
        "startedAt": 1000.0,
    }
    (run_entry / "status.json").write_text(json.dumps(status_data), encoding="utf-8")

    all_runs = runs.list_simulation_runs()
    assert len(all_runs) == 1
    list_item = all_runs[0]

    details = runs.get_run_details(run_id)
    assert details is not None

    # Parity assertions
    assert list_item["pct"] == 34.7
    assert details["pct"] == 34.7
    assert "snapshot" in list_item
    assert "snapshot" in details
    assert list_item["snapshot"]["schema_version"] == "run_snapshot_v2"
    assert details["snapshot"]["schema_version"] == "run_snapshot_v2"
    assert list_item["snapshot"]["progress"]["pct"] == 34.7
    assert details["snapshot"]["progress"]["pct"] == 34.7


def test_discovery_clis_import_and_help() -> None:
    """L02: Discovery CLIs must have clean imports without missing os or syntax errors."""
    clis = [
        "scripts/run_discovery_q_20260928_jsonl_smoke.py",
        "scripts/run_discovery_q_20260928_jsonl_track_c.py",
        "scripts/run_discovery_q_20260928_jsonl_campaign.py",
        "scripts/run_discovery_q_20260928_jsonl_engine.py",
    ]
    for cli in clis:
        cli_path = REPO_ROOT / cli
        assert cli_path.is_file(), f"CLI {cli} not found"
        proc = subprocess.run(
            [sys.executable, str(cli_path), "--help"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        assert proc.returncode == 0, f"CLI {cli} failed --help: {proc.stderr}"
        assert "usage:" in proc.stdout.lower()
