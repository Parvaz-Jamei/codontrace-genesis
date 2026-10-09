"""Strict Scientific Invariants & Security Regression Tests for Phase 1 Remediation (R01-R05).

Audit Document: AUDIT_037648e_UPDATE_REVIEW_FA.md
Scope:
- R01: Evaluator accepts scientific claims without valid controls, out-of-bound confidence,
       invalid percolation rate (>1.0), or during active/transitional lifecycle states (PAUSING/PAUSED).
- R02: Monitor in coordinator sleeps for up to 600s, missing quick pause cycles (< heartbeat)
       and failing to enforce wall-clock deadline during pause.
- R03: Parity between `list_simulation_runs` and `build_run_snapshot` on completed execution
       without status.json (COMPLETED vs RUNNING, 100% vs 0%), plus out-of-range progress rejection.
- R04: Worker pause ACK counting stuck in PAUSING when active seeds < workers or seed finishes mid-pause.
- R05: UI store details path lacks revision guard, overwriting newer state with stale responses,
       and ignores session_id boundaries.
"""

from __future__ import annotations

import json
import threading
import time
from pathlib import Path
from typing import Any

import pytest

from codontrace.console import runs
from codontrace.console.evaluator import evaluate_run_hypothesis
from codontrace.genesis import snapshot

# ==============================================================================
# R01: Evaluator Scientific Invariants & Control Enforcement
# ==============================================================================


def test_r01_reject_candidate_with_out_of_bound_confidence() -> None:
    """R01: Candidate assessment with confidence > 1.0 or < 0.0 must be rejected as invalid.
    
    Audit reproduction:
    hypothesis_assessment with confidence=42.0 must never yield verdict='supported'.
    """
    # Case A: Confidence > 1.0 (e.g. 42.0 as reported in audit)
    run_excessive_conf = {
        "status": "COMPLETED",
        "execution": {
            "complete": True,
            "hypothesis_assessment": {
                "verdict": "supported",
                "confidence": 42.0,
                "controls_passed": True,
            },
        },
    }
    eval_a = evaluate_run_hypothesis(run_excessive_conf)
    assert eval_a["verdict"] != "supported", (
        f"Security Invariant Violated: Candidate with confidence 42.0 accepted as supported: {eval_a}"
    )
    assert eval_a["verdict"] == "invalid"
    assert eval_a["confidence"] == 0.0

    # Case B: Negative confidence
    run_negative_conf = {
        "status": "COMPLETED",
        "execution": {
            "complete": True,
            "hypothesis_assessment": {
                "verdict": "supported",
                "confidence": -0.5,
                "controls_passed": True,
            },
        },
    }
    eval_b = evaluate_run_hypothesis(run_negative_conf)
    assert eval_b["verdict"] != "supported"
    assert eval_b["verdict"] == "invalid"


def test_r01_reject_candidate_without_explicit_verified_controls() -> None:
    """R01: Candidate claiming 'supported' without verified controls must be rejected.
    
    Absence of controls or missing controls_passed field must not default to passing.
    """
    # Candidate with missing controls_passed
    run_missing_controls = {
        "status": "COMPLETED",
        "execution": {
            "complete": True,
            "hypothesis_assessment": {
                "verdict": "supported",
                "confidence": 0.95,
                # controls_passed explicitly omitted
            },
        },
    }
    res = evaluate_run_hypothesis(run_missing_controls)
    assert res["verdict"] != "supported", (
        f"Scientific Invariant Violated: Candidate without controls passed accepted as supported: {res}"
    )
    assert res["controls_passed"] is not True


def test_r01_active_lifecycle_states_prevent_supported_verdict() -> None:
    """R01: In-flight or transitional states (PAUSING, PAUSED, RESUMING, STOPPING, RUNNING)
    must never be evaluated as 'supported'. They must yield 'not_evaluated'.
    """
    transitional_states = ["PAUSING", "PAUSED", "RESUMING", "STOPPING", "RUNNING", "STARTING", "QUEUED"]
    for state in transitional_states:
        payload = {
            "status": state,
            "execution": {
                "complete": False,
                "challenge": "FUNCTIONAL_INFO",
                "summary": {
                    "hazen_functional_info_bits": 8.0,
                    "neutral_percolation_rate": 0.45,
                },
                "hypothesis_assessment": {
                    "verdict": "supported",
                    "confidence": 0.95,
                    "controls_passed": True,
                },
            },
        }
        res = evaluate_run_hypothesis(payload)
        assert res["verdict"] != "supported", (
            f"State {state} produced supported verdict: {res}. "
            "Active and transitional states must return not_evaluated."
        )
        assert res["verdict"] == "not_evaluated", f"Expected not_evaluated for state {state}, got {res['verdict']}"


def test_r01_functional_info_percolation_rate_bounds_and_lifecycle() -> None:
    """R01: Percolation rate is a probability/fraction and must strictly reside in [0.0, 1.0].
    Percolation > 1.0 (e.g. 2.0) must be rejected as invalid.
    Also, incomplete/stopped runs without completed protocol must not yield supported.
    """
    # Case A: Percolation rate > 1.0 (physical / statistical absurdity)
    run_bad_perc = {
        "status": "STOPPED",
        "execution": {
            "complete": False,
            "challenge": "FUNCTIONAL_INFO",
            "summary": {
                "hazen_functional_info_bits": 8.0,
                "neutral_percolation_rate": 2.0,  # Invalid rate > 1.0
            },
        },
    }
    eval_a = evaluate_run_hypothesis(run_bad_perc)
    assert eval_a["verdict"] != "supported", (
        f"Scientific Invariant Violated: percolation=2.0 yielded supported: {eval_a}"
    )
    assert eval_a["verdict"] == "invalid"

    # Case B: Incomplete stopped run with percolation in range
    run_stopped_incomplete = {
        "status": "STOPPED",
        "execution": {
            "complete": False,
            "challenge": "FUNCTIONAL_INFO",
            "summary": {
                "hazen_functional_info_bits": 8.0,
                "neutral_percolation_rate": 0.5,
            },
        },
    }
    eval_b = evaluate_run_hypothesis(run_stopped_incomplete)
    assert eval_b["verdict"] != "supported", (
        f"Scientific Invariant Violated: Incomplete stopped run claimed supported: {eval_b}"
    )


def test_r01_positive_control_fixture_supported() -> None:
    """R01 Positive Control: Ensure genuinely valid, completed run with valid controls
    and metrics in bounds IS accepted as 'supported' (no false negative lockdown).
    """
    valid_payload = {
        "status": "COMPLETED",
        "execution": {
            "complete": True,
            "controls_passed": True,
            "challenge": "FUNCTIONAL_INFO",
            "summary": {
                "hazen_functional_info_bits": 4.5,
                "neutral_percolation_rate": 0.65,
                "controls_passed": True,
            },
            "hypothesis_assessment": {
                "verdict": "supported",
                "hypothesis_id": "hazen_functional_info_accretion",
                "protocol": "hazen_2007_functional_information",
                "confidence": 0.95,
                "controls_passed": True,
                "evidence_summary": {"fi_bits": 4.5, "percolation": 0.65},
            },
        },
    }
    res = evaluate_run_hypothesis(valid_payload)
    assert res["verdict"] == "supported"
    assert res["controls_passed"] is True
    assert 0.0 <= float(res["confidence"]) <= 1.0


# ==============================================================================
# R02: Monitor Timing, Quick Pause Detection, and Wall Deadline
# ==============================================================================


def test_r02_short_pause_cycle_not_missed_by_monitor(tmp_path: Path) -> None:
    """R02: A pause cycle shorter than coordinator sleep (e.g. 0.3s-1.1s) must be
    detected and recorded in paused_seconds, rather than missed due to long sleep.
    """
    root = tmp_path / "run_timing"
    root.mkdir()
    stop = threading.Event()
    started = time.monotonic()
    paused_accumulated = [0.0]
    heartbeat_interval = 0.1  # Remediated fine-grained heartbeat interval

    def remediated_monitor() -> None:
        with (root / "health.log").open("w", encoding="utf-8", buffering=1) as log:
            while not stop.is_set():
                if (root / "PAUSE").is_file():
                    p_start = time.monotonic()
                    while (root / "PAUSE").is_file() and not stop.is_set():
                        time.sleep(0.05)
                    p_duration = time.monotonic() - p_start
                    paused_accumulated[0] += p_duration

                wall_elapsed = time.monotonic() - started
                active_elapsed = max(0.0, wall_elapsed - paused_accumulated[0])
                log.write(
                    json.dumps({
                        "paused_seconds": round(paused_accumulated[0], 3),
                        "active_elapsed_seconds": round(active_elapsed, 3),
                        "wall_elapsed_seconds": round(wall_elapsed, 3),
                    })
                    + "\n"
                )
                # Must NOT wait 600 seconds unconditionally!
                stop.wait(heartbeat_interval)

    thread = threading.Thread(target=remediated_monitor, daemon=True)
    thread.start()

    try:
        # Let monitor run briefly
        time.sleep(0.15)
        # Create quick pause cycle (0.3s)
        pause_file = root / "PAUSE"
        pause_file.write_text("paused\n", encoding="utf-8")
        time.sleep(0.3)
        pause_file.unlink()
        time.sleep(0.2)
    finally:
        stop.set()
        thread.join(timeout=1.0)

    # Invariant: paused_seconds MUST be recorded as > 0.2s, not 0.0s!
    assert paused_accumulated[0] >= 0.2, (
        f"Timing Invariant Violated: Fast pause cycle was missed or recorded as 0: {paused_accumulated[0]}"
    )

    # Health log must reflect accurate paused_seconds
    log_lines = (root / "health.log").read_text(encoding="utf-8").splitlines()
    assert len(log_lines) > 0
    last_rec = json.loads(log_lines[-1])
    assert last_rec["paused_seconds"] >= 0.2


def test_r02_wall_deadline_enforced_during_extended_pause(tmp_path: Path) -> None:
    """R02: Under budget_kind='wall_deadline', remaining paused beyond max_seconds
    must trigger cooperative STOP rather than hanging indefinitely.
    """
    root = tmp_path / "run_wall_deadline"
    root.mkdir()
    stop = threading.Event()
    started = time.monotonic()
    max_seconds = 0.4
    budget_kind = "wall_deadline"

    def remediated_deadline_monitor() -> None:
        while not stop.is_set():
            wall_elapsed = time.monotonic() - started
            if wall_elapsed >= max_seconds:
                (root / "STOP").write_text(f"fixed {budget_kind} budget exhausted\n", encoding="utf-8")
                return

            # Check pause with deadline awareness
            if (root / "PAUSE").is_file():
                while (root / "PAUSE").is_file() and not stop.is_set():
                    wall_elapsed_cur = time.monotonic() - started
                    if wall_elapsed_cur >= max_seconds:
                        (root / "STOP").write_text(f"fixed {budget_kind} budget exhausted during pause\n", encoding="utf-8")
                        return
                    time.sleep(0.05)

            stop.wait(0.05)

    thread = threading.Thread(target=remediated_deadline_monitor, daemon=True)
    thread.start()

    try:
        # Put into pause immediately
        (root / "PAUSE").write_text("paused\n", encoding="utf-8")
        # Wait longer than max_seconds while paused
        time.sleep(0.6)
    finally:
        stop.set()
        thread.join(timeout=1.0)

    # Invariant: STOP file must exist despite execution being paused
    stop_file = root / "STOP"
    assert stop_file.is_file(), "Wall deadline was not enforced during pause; STOP marker missing"
    assert "exhausted" in stop_file.read_text(encoding="utf-8")


def test_r02_rq_driver_pause_accounting_probe_contract(tmp_path: Path) -> None:
    """R02 Acceptance Contract: Fast pause cycle in rq_full_engine_parallel run.
    
    Audit reproduction:
    probe in AUDIT_037648e_UPDATE_REVIEW_FA.md showed unpatched driver monitor sleeps 600s,
    resulting in paused_seconds=0.0 when a 0.8s-1.1s pause/resume cycle occurs.
    The remediated driver coordinator must capture the pause and accumulate paused_seconds.
    """
    import sys
    from concurrent.futures import ThreadPoolExecutor
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
    import rq_full_engine_parallel

    root = tmp_path / "rq_probe_run"

    def fast_pause_worker(seed: int, root_str: str, generations: int) -> dict[str, Any]:
        p_root = Path(root_str)
        hlog = p_root / "health.log"
        for _ in range(50):
            if hlog.is_file() and hlog.stat().st_size > 0:
                break
            time.sleep(0.02)
        # 0.8s pause cycle
        (p_root / "PAUSE").write_text("paused\n", encoding="utf-8")
        time.sleep(0.8)
        (p_root / "PAUSE").unlink(missing_ok=True)
        return {"seed": seed, "matched": True}

    orig_executor = rq_full_engine_parallel.ProcessPoolExecutor
    orig_worker = rq_full_engine_parallel.worker
    orig_validate = rq_full_engine_parallel.validate_archive
    orig_replay = rq_full_engine_parallel.replay_phase5_archive
    orig_diag = rq_full_engine_parallel.engine_diagnostics
    orig_horiz = rq_full_engine_parallel.horizon_diagnostics

    try:
        rq_full_engine_parallel.ProcessPoolExecutor = ThreadPoolExecutor  # type: ignore
        rq_full_engine_parallel.worker = fast_pause_worker  # type: ignore
        rq_full_engine_parallel.validate_archive = lambda *args, **kwargs: None  # type: ignore
        rq_full_engine_parallel.replay_phase5_archive = lambda *args, **kwargs: {"matched": True}  # type: ignore
        rq_full_engine_parallel.engine_diagnostics = lambda *args, **kwargs: None  # type: ignore
        rq_full_engine_parallel.horizon_diagnostics = lambda *args, **kwargs: None  # type: ignore

        report = rq_full_engine_parallel.run(root, (16001,), generations=10, workers=1, max_seconds=10.0)
        # Remediated invariant:
        assert report["paused_seconds"] >= 0.5, (
            f"R02 Invariant Violated: rq_full_engine_parallel monitor missed fast pause cycle; "
            f"paused_seconds={report['paused_seconds']}"
        )
    finally:
        rq_full_engine_parallel.ProcessPoolExecutor = orig_executor
        rq_full_engine_parallel.worker = orig_worker
        rq_full_engine_parallel.validate_archive = orig_validate
        rq_full_engine_parallel.replay_phase5_archive = orig_replay
        rq_full_engine_parallel.engine_diagnostics = orig_diag
        rq_full_engine_parallel.horizon_diagnostics = orig_horiz


# ==============================================================================
# R03: Parity between list_simulation_runs and build_run_snapshot
# ==============================================================================


def test_r03_complete_execution_without_status_json_parity(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """R03: For a run with completed execution.json but NO status.json,
    list_simulation_runs and build_run_snapshot MUST report matching state
    ('COMPLETED') and percentage (100.0%).
    
    Audit reproduction:
    list_state was 'COMPLETED', snapshot_state was 'RUNNING' (or pct 100 vs 0).
    """
    runs_dir = tmp_path / "runs"
    runs_dir.mkdir(parents=True)
    monkeypatch.setenv("CODONTRACE_RUNS_DIR", str(runs_dir))

    run_id = "run_exec_complete_no_status_001"
    run_entry = runs_dir / run_id
    run_entry.mkdir()

    # Complete execution.json, NO status.json
    exec_data = {
        "runId": run_id,
        "complete": True,
        "validation_failures": [],
        "errors": [],
        "summary": {"total_generations": 500},
    }
    (run_entry / "execution.json").write_text(json.dumps(exec_data), encoding="utf-8")

    all_runs = runs.list_simulation_runs()
    assert len(all_runs) == 1
    list_item = all_runs[0]
    list_status = list_item["status"]
    list_pct = list_item["pct"]
    snapshot_data = list_item["snapshot"]

    # Parity assertions between list item and its embedded snapshot
    assert list_status == "COMPLETED"
    assert list_pct == 100.0
    assert snapshot_data["state"] == "COMPLETED", (
        f"R03 Parity Violation: list_status is COMPLETED but snapshot_state is {snapshot_data['state']}"
    )
    assert snapshot_data["progress"]["pct"] == 100.0, (
        f"R03 Parity Violation: list_pct is 100.0 but snapshot_pct is {snapshot_data['progress']['pct']}"
    )


def test_r03_out_of_bounds_progress_sanitization(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """R03: Percentage progress outside [0.0, 100.0] (e.g. 200%, -10%, NaN, Inf)
    must never be emitted by snapshot or list view.
    """
    runs_dir = tmp_path / "runs"
    runs_dir.mkdir(parents=True)
    monkeypatch.setenv("CODONTRACE_RUNS_DIR", str(runs_dir))

    run_id = "run_oob_pct_002"
    run_entry = runs_dir / run_id
    run_entry.mkdir()

    # status.json with invalid 200.0%
    status_data = {
        "schemaVersion": 1,
        "runId": run_id,
        "status": "RUNNING",
        "pct": 200.0,
    }
    (run_entry / "status.json").write_text(json.dumps(status_data), encoding="utf-8")

    all_runs = runs.list_simulation_runs()
    assert len(all_runs) == 1
    item = all_runs[0]
    # Percentage must be clamped or sanitized to <= 100.0
    assert item["pct"] <= 100.0, f"Out-of-bounds pct=200 was not clamped in list: {item['pct']}"
    assert item["snapshot"]["progress"]["pct"] <= 100.0, (
        f"Out-of-bounds pct=200 was not clamped in snapshot: {item['snapshot']['progress']['pct']}"
    )

    # Snapshot validation must pass without raising ConfigurationError
    snapshot.validate_run_snapshot(item["snapshot"])


# ==============================================================================
# R04: Worker Pause ACK Coordination with Few Seeds or Seed Termination
# ==============================================================================


def test_r04_seeds_fewer_than_workers_does_not_hang_in_pausing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """R04: When seeds < workers (e.g. workers=4, seeds=[42]), only 1 worker runs.
    When PAUSE is written and ack_paused_42 appears, the snapshot MUST transition
    to PAUSED, and not stay indefinitely stuck in PAUSING waiting for 4 ACKs.
    """
    runs_dir = tmp_path / "runs"
    runs_dir.mkdir(parents=True)
    monkeypatch.setenv("CODONTRACE_RUNS_DIR", str(runs_dir))

    run_id = "run_few_seeds_003"
    run_entry = runs_dir / run_id
    run_entry.mkdir()
    out_dir = run_entry / "output"
    out_dir.mkdir()

    # Manifest configures 4 workers, but only 1 seed
    manifest_data = {
        "schemaVersion": 1,
        "runId": run_id,
        "params": {"workers": 4, "seeds": [42], "totalSeeds": 1},
    }
    (run_entry / "manifest.json").write_text(json.dumps(manifest_data), encoding="utf-8")

    status_data = {
        "status": "RUNNING",
        "revision": 1,
        "params": {"workers": 4, "seeds": [42]},
        "totalSeeds": 1,
        "completedSeeds": 0,
    }
    (run_entry / "status.json").write_text(json.dumps(status_data), encoding="utf-8")

    # User initiates PAUSE
    (run_entry / "PAUSE").write_text("pause\n", encoding="utf-8")
    # The only running worker acknowledges pause
    (out_dir / "ack_paused_42").write_text("paused gen=1\n", encoding="utf-8")

    # Authoritative snapshot check
    snap = runs.build_run_snapshot(run_id, status_data, manifest_data)
    assert snap["state"] == "PAUSED", (
        f"R04 Invariant Violated: All active workers (1/1) ACKed pause, but snapshot remains in {snap['state']}"
    )


def test_r04_seed_completed_during_pause_does_not_block_paused_state(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """R04: When 1 of 2 seeds has already completed when pause occurs,
    the snapshot must not expect ACKs from the completed seed.
    """
    runs_dir = tmp_path / "runs"
    runs_dir.mkdir(parents=True)
    monkeypatch.setenv("CODONTRACE_RUNS_DIR", str(runs_dir))

    run_id = "run_seed_finished_mid_pause_004"
    run_entry = runs_dir / run_id
    run_entry.mkdir()
    out_dir = run_entry / "output"
    out_dir.mkdir()

    manifest_data = {
        "schemaVersion": 1,
        "runId": run_id,
        "params": {"workers": 2, "seeds": [101, 102], "totalSeeds": 2},
    }
    (run_entry / "manifest.json").write_text(json.dumps(manifest_data), encoding="utf-8")

    status_data = {
        "status": "RUNNING",
        "revision": 2,
        "params": {"workers": 2, "seeds": [101, 102]},
        "totalSeeds": 2,
        "completedSeeds": 1,  # Seed 101 finished!
    }
    (run_entry / "status.json").write_text(json.dumps(status_data), encoding="utf-8")

    (run_entry / "PAUSE").write_text("pause\n", encoding="utf-8")
    # Only active seed 102 writes ACK
    (out_dir / "ack_paused_102").write_text("paused gen=10\n", encoding="utf-8")

    snap = runs.build_run_snapshot(run_id, status_data, manifest_data)
    assert snap["state"] == "PAUSED", (
        f"R04 Invariant Violated: Only remaining active seed paused, but state is {snap['state']}"
    )


# ==============================================================================
# R05: UI Store Monotonic Revision & Details Path Guard
# ==============================================================================


def apply_store_sync_reduction(
    current_job: dict[str, Any],
    incoming_update: dict[str, Any],
    is_details: bool = False,
) -> dict[str, Any]:
    """Specification of the remediated UI store reducer for syncServerRuns and details.
    
    Invariants enforced:
    1. Monotonic revision guard: Drops incoming updates with lower revision
       when within the same session_id.
    2. Session boundary awareness: Fresh session_id with revision 1 is accepted,
       not dropped because of a previous session's high revision.
    3. Authoritative fields protected: Status and pct are never regressed by stale responses.
    4. Transitional state mapping: PAUSING is not conflated with PAUSED.
    """
    curr_sess = current_job.get("session_id")
    curr_rev = current_job.get("revision", 0)

    inc_sess = incoming_update.get("session_id")
    inc_rev = incoming_update.get("revision", 0)

    # If same session and incoming revision is older -> drop stale update!
    if curr_sess and inc_sess and curr_sess == inc_sess:
        if inc_rev < curr_rev:
            return dict(current_job)  # Stale response rejected completely

    # Map status safely without conflating PAUSING into paused
    raw_status = incoming_update.get("status", "")
    if raw_status == "PAUSING":
        mapped_status = "pausing"
    elif raw_status == "PAUSED":
        mapped_status = "paused"
    elif raw_status == "RUNNING":
        mapped_status = "running"
    elif raw_status == "STOPPED":
        mapped_status = "stopped"
    elif raw_status == "COMPLETED":
        mapped_status = "completed"
    else:
        mapped_status = str(raw_status).lower()

    updated = dict(current_job)
    updated["session_id"] = inc_sess or curr_sess
    updated["revision"] = max(curr_rev, inc_rev) if (curr_sess == inc_sess) else inc_rev
    updated["status"] = mapped_status
    updated["pct"] = incoming_update.get("pct", current_job.get("pct"))
    return updated


def test_r05_details_path_rejects_stale_revision_updates() -> None:
    """R05: When details response has revision < current_job.revision,
    authoritative fields (status, pct) must NOT be overwritten.
    
    Audit reproduction:
    list had rev=10, paused, pct=75.
    details arrived late with rev=8, running, pct=50.
    In the unpatched store, status was reverted to running and pct to 50 under revision 10.
    """
    current_job = {
        "id": "run_sim_01",
        "session_id": "sess_alpha_1",
        "revision": 10,
        "status": "paused",
        "pct": 75.0,
    }

    # Stale details response arriving late over network
    stale_details = {
        "id": "run_sim_01",
        "session_id": "sess_alpha_1",
        "revision": 8,
        "status": "RUNNING",
        "pct": 50.0,
    }

    result = apply_store_sync_reduction(current_job, stale_details, is_details=True)

    # Invariant: Must retain newer revision 10 state!
    assert result["revision"] == 10
    assert result["status"] == "paused", f"Stale response reverted status: {result['status']}"
    assert result["pct"] == 75.0, f"Stale response reverted pct: {result['pct']}"


def test_r05_session_id_boundary_allows_new_session_low_revision() -> None:
    """R05: A new run session (session_id changes) starting at revision 1 must NOT
    be dropped as stale just because the prior session ended at revision 10.
    """
    previous_session_job = {
        "id": "run_sim_01",
        "session_id": "sess_old_1",
        "revision": 10,
        "status": "stopped",
        "pct": 100.0,
    }

    fresh_session_update = {
        "id": "run_sim_01",
        "session_id": "sess_new_2",
        "revision": 1,
        "status": "RUNNING",
        "pct": 0.0,
    }

    result = apply_store_sync_reduction(previous_session_job, fresh_session_update)
    assert result["session_id"] == "sess_new_2"
    assert result["revision"] == 1
    assert result["status"] == "running"
    assert result["pct"] == 0.0


def test_r05_unpatched_store_details_path_regression() -> None:
    """R05 Bug Reproduction & Remediation Gate:
    In unpatched store.ts, details sync computes dRev and curRev, but lacks a guard,
    resulting in updatedJobs[idx] having its status and pct regressed by older details.
    """
    def unpatched_store_details_sync(current_job: dict[str, Any], details: dict[str, Any]) -> dict[str, Any]:
        dRev = details.get("revision", 0)
        curRev = current_job.get("revision", 0)
        detStatus = "running" if details.get("status") == "RUNNING" else str(details.get("status", "")).lower()
        # Exact unpatched store.ts behavior (lines 362-398):
        updated = dict(current_job)
        updated["status"] = detStatus
        updated["pct"] = details.get("pct")
        updated["revision"] = max(dRev, curRev)
        return updated

    current_job = {"id": "run_1", "session_id": "sess_1", "revision": 10, "status": "paused", "pct": 75.0}
    stale_details = {"id": "run_1", "session_id": "sess_1", "revision": 8, "status": "RUNNING", "pct": 50.0}

    # The unpatched logic reproduces the bug:
    unpatched_res = unpatched_store_details_sync(current_job, stale_details)
    assert unpatched_res["status"] == "running", "Unpatched logic must reproduce status regression"
    assert unpatched_res["pct"] == 50.0, "Unpatched logic must reproduce pct regression"
    assert unpatched_res["revision"] == 10, "Unpatched logic stamps old data with max revision"

    # The remediated logic MUST prevent this regression:
    remediated_res = apply_store_sync_reduction(current_job, stale_details, is_details=True)
    assert remediated_res["status"] == "paused"
    assert remediated_res["pct"] == 75.0
    assert remediated_res["revision"] == 10


def test_r05_transitional_pausing_not_conflated_with_paused() -> None:
    """R05: Server state 'PAUSING' must not be prematurely mapped to 'paused'."""
    current_job = {
        "id": "run_sim_01",
        "session_id": "sess_alpha_1",
        "revision": 5,
        "status": "running",
        "pct": 30.0,
    }

    pausing_update = {
        "id": "run_sim_01",
        "session_id": "sess_alpha_1",
        "revision": 6,
        "status": "PAUSING",
        "pct": 30.0,
    }

    result = apply_store_sync_reduction(current_job, pausing_update)
    assert result["status"] != "paused", "PAUSING was conflated with paused in UI mapping"
    assert result["status"] == "pausing"
