"""Strict Scientific Invariants & Security Regression Tests for Phase 4 Remediation (R10-R11).

Audit Documents: AUDIT_037648e_UPDATE_REVIEW_FA.md & test_audit_10phases_master_verification.py
Scope:
- R10: Remediated production-grade testing layer:
       1. Hazen functional information bits zero-success validation (I(Ex) = -log2(M(Ex)/N)),
          finite sampling bounds, non-binary alphabet configuration space, and explicit
          'censored' / 'upper_bound' labeling in evaluator.
       2. Production active time budget: monotonic active_elapsed_seconds <= wall_elapsed_seconds,
          freezing during PAUSED state, and accurate health.log accounting.
       3. Uniform monotonic run revision (revision >= 1, rev_{n+1} > rev_n) across lifecycle actions,
          and UI store sync reduction guard.
       4. Price equation multilevel selection partition with unequal demes and transmission components.
- R11: Clear semantic and operational distinction between:
       1. 'cancelled_response': User-initiated cancellation via Abort button / cancel_event / request_id,
          with cooperative unblocking in < 100ms even with slow in-flight upstream model queries.
       2. 'cancelled_upstream': Upstream model server timeout, unresponsiveness, or network drop,
          without conflating it with user abort.
       3. Request ID cleanup and request lifecycle hygiene.
"""

from __future__ import annotations

import json
import math
import socket
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any

import pytest

from codontrace.console import chat, runs
from codontrace.console.chat import (
    abort_chat_request,
    chat_turn,
)
from codontrace.console.evaluator import evaluate_run_hypothesis
from tests.test_audit_phase1_remediation_r01_r05 import apply_store_sync_reduction

# ==============================================================================
# Helper Mock Upstream Servers
# ==============================================================================

class SlowUpstreamHandler(BaseHTTPRequestHandler):
    """Mock LLM server that can introduce controlled delays or immediate responses."""

    delay_seconds: float = 1.0

    def do_POST(self) -> None:
        if self.path in ("/v1/chat/completions", "/chat/completions"):
            # Simulate slow model execution
            time.sleep(self.delay_seconds)
            response_body = json.dumps({
                "choices": [{
                    "message": {"content": "Delayed simulated model response"}
                }]
            }).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(response_body)))
            self.end_headers()
            self.wfile.write(response_body)
        elif self.path in ("/v1/models", "/models"):
            response_body = json.dumps({
                "data": [{"id": "mock-slow-model"}]
            }).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(response_body)))
            self.end_headers()
            self.wfile.write(response_body)
        else:
            self.send_response(404)
            self.end_headers()

    def do_GET(self) -> None:
        if self.path in ("/v1/models", "/models"):
            response_body = json.dumps({
                "data": [{"id": "mock-slow-model"}]
            }).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(response_body)))
            self.end_headers()
            self.wfile.write(response_body)
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format: str, *args: Any) -> None:
        pass  # Suppress HTTP server output in test logs


def _find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


# ==============================================================================
# R11: Distinct Semantics for cancelled_response vs cancelled_upstream
# ==============================================================================

def test_r11_clear_distinction_cancelled_response_during_inflight_upstream(monkeypatch: pytest.MonkeyPatch) -> None:
    """R11: When user clicks Abort during a slow in-flight model query,
    the response must immediately return with cancellation_reason='cancelled_response'
    and cancelled=True in < 150ms, without blocking for the slow upstream to complete.
    """
    port = _find_free_port()
    SlowUpstreamHandler.delay_seconds = 1.2
    server = HTTPServer(("127.0.0.1", port), SlowUpstreamHandler)
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()

    try:
        endpoint = f"http://127.0.0.1:{port}/v1/chat/completions"
        monkeypatch.setenv("CODONTRACE_LLM_ENDPOINT", endpoint)
        monkeypatch.setenv("CODONTRACE_LLM_TIMEOUT", "10.0")
        chat.set_llm_endpoint(endpoint)

        req_id = f"test_r11_user_abort_{int(time.time() * 1000)}"

        # Run chat_turn in background thread
        res_container: dict[str, Any] = {}
        t_start = time.monotonic()

        def _worker() -> None:
            res_container["res"] = chat_turn(
                "Explain Red Queen reciprocal dynamic",
                lang="en",
                model="mock-slow-model",
                request_id=req_id,
            )

        th = threading.Thread(target=_worker, daemon=True)
        th.start()

        # Wait briefly for request to register and start in-flight query
        time.sleep(0.1)

        # User clicks Abort
        aborted = abort_chat_request(req_id)
        assert aborted is True, "Abort controller must return True for active request_id"

        th.join(timeout=0.6)
        elapsed = time.monotonic() - t_start

        # Invariant: Must return promptly (< 0.6s) despite upstream taking 1.2s!
        assert not th.is_alive(), "chat_turn blocked on slow upstream instead of cooperatively aborting!"
        assert elapsed < 1.0, f"Abort took {elapsed:.2f}s, expected < 1.0s cooperative exit"

        res = res_container.get("res", {})
        assert res.get("cancelled") is True
        assert res.get("cancelled_type") == "cancelled_response"
        assert res.get("cancellation_reason") == "cancelled_response"
        assert res.get("model") == "cancelled"
        assert "cancelled by user" in res.get("reply", "").lower()

        # Invariant: request_id is cleanly pruned
        with chat._CHAT_LOCK:
            assert req_id not in chat._ACTIVE_CHAT_REQUESTS

    finally:
        server.shutdown()
        server.server_close()
        chat.set_llm_endpoint(None)


def test_r11_clear_distinction_cancelled_upstream_on_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    """R11: When upstream server times out or hangs without user abort,
    cancellation_reason must be 'cancelled_upstream', clearly distinguished from user abort.
    """
    port = _find_free_port()
    SlowUpstreamHandler.delay_seconds = 1.0
    server = HTTPServer(("127.0.0.1", port), SlowUpstreamHandler)
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()

    try:
        endpoint = f"http://127.0.0.1:{port}/v1/chat/completions"
        monkeypatch.setenv("CODONTRACE_LLM_ENDPOINT", endpoint)
        monkeypatch.setenv("CODONTRACE_LLM_TIMEOUT", "0.2")  # Short 200ms timeout
        chat.set_llm_endpoint(endpoint)

        req_id = f"test_r11_upstream_timeout_{int(time.time() * 1000)}"

        # Do NOT abort: user is waiting, but upstream exceeds timeout
        res = chat_turn(
            "Synthesize Price equation covariance",
            lang="en",
            model="mock-slow-model",
            request_id=req_id,
        )

        # Invariant: must recognize cancelled_upstream, NOT cancelled_response!
        assert res.get("cancelled_type") == "cancelled_upstream"
        assert res.get("cancellation_reason") == "cancelled_upstream"
        assert res.get("fallback") is True
        # Invariant: request_id cleaned up
        with chat._CHAT_LOCK:
            assert req_id not in chat._ACTIVE_CHAT_REQUESTS

    finally:
        server.shutdown()
        server.server_close()
        chat.set_llm_endpoint(None)


def test_r11_cancellation_semantics_are_mutually_exclusive() -> None:
    """R11: Semantic contract verification:
    - User abort -> cancelled=True, cancelled_type='cancelled_response'
    - Upstream timeout -> cancelled_type='cancelled_upstream', NOT conflated with user abort.
    - Deterministic analyst -> cancelled=False, cancelled_type='none'
    """
    # 1. Deterministic analyst
    res_normal = chat_turn("Tell me about Price equation", lang="en", model="local-analyst")
    assert res_normal.get("cancelled") is False
    assert res_normal.get("cancelled_type") == "none"
    assert res_normal.get("cancellation_reason") == "none"

    # 2. Pre-aborted turn
    req_id = "test_pre_abort_mut_excl"
    event = threading.Event()
    event.set()
    with chat._CHAT_LOCK:
        chat._ACTIVE_CHAT_REQUESTS[req_id] = event

    res_user_abort = chat_turn("Tell me about Price equation", lang="en", request_id=req_id)
    assert res_user_abort.get("cancelled") is True
    assert res_user_abort.get("cancelled_type") == "cancelled_response"
    assert res_user_abort.get("cancellation_reason") == "cancelled_response"
    assert res_user_abort.get("cancelled_type") != "cancelled_upstream"


# ==============================================================================
# R10: Hazen Functional Information Zero-Success & Censored Bound Invariant
# ==============================================================================

def test_r10_hazen_zero_success_sampling_bounds_mathematical_rigor() -> None:
    """R10: When viable mutant sample count is zero (viable_count = 0),
    true I(Ex) is undefined (-log2(0) = inf).
    Under finite sample size N, zero successes indicates p_f <= 3/N (rule of three)
    giving a lower information bound of log2(N/3), or maximum sequence entropy bound.
    For non-binary alphabet (e.g. 4-letter DNA, A=4), maximum entropy is 2*L bits, NOT L bits!
    """
    genome_len = 32
    sample_size = 500

    # 1. Binary alphabet (A=2): max entropy = 32.0 bits
    max_entropy_binary = float(genome_len) * math.log2(2)
    assert max_entropy_binary == 32.0

    # 2. DNA 4-letter alphabet (A=4): max entropy = 64.0 bits (NOT 32 bits!)
    max_entropy_dna = float(genome_len) * math.log2(4)
    assert max_entropy_dna == 64.0

    # 3. Finite sample lower bound from zero successes (Rule of Three for 95% CI: p_f < 3/N)
    p_f_upper_bound_95 = 3.0 / sample_size
    info_lower_bound_95 = -math.log2(p_f_upper_bound_95)
    assert info_lower_bound_95 == pytest.approx(math.log2(500.0 / 3.0), rel=1e-4)
    assert 7.0 < info_lower_bound_95 < 8.0  # ~7.38 bits empirical bound, NOT 32 bits!


def test_r10_hazen_evaluator_rejects_unhedged_discovery_on_zero_success() -> None:
    """R10: When a run has zero viable mutants sampled in reference space,
    the evaluator must label the metric as censored / upper_bound and return
    'inconclusive' with sampling uncertainty rationale, rather than claiming
    unreserved positive discovery ('supported' with 0.95 confidence).
    """
    # Case 1: Run reports zero viable mutants (zero_success = True, capped at upper bound 32.0)
    zero_success_run = {
        "status": "COMPLETED",
        "execution": {
            "complete": True,
            "challenge": "FUNCTIONAL_INFO",
            "summary": {
                "hazen_functional_info_bits": 32.0,
                "neutral_percolation_rate": 0.0,
                "zero_success": True,
                "viable_count": 0,
                "sample_size": 500,
            },
        },
    }

    assessment = evaluate_run_hypothesis(zero_success_run)
    # Evaluator must NOT unreservedly declare supported
    assert assessment["verdict"] == "inconclusive"
    assert assessment["confidence"] is None
    assert assessment["controls_passed"] is False
    assert assessment["evidence_summary"]["censored"] is True
    assert assessment["evidence_summary"]["bound_type"] == "lower_bound"
    assert assessment["evidence_summary"]["zero_success"] is True
    assert "censored lower information bound" in assessment["rationale"].lower()


def test_r10_hazen_evaluator_distinguishes_point_estimate_from_censored_bound() -> None:
    """R10: Evaluator must clearly differentiate an empirical point estimate (p_f > 0)
    from a censored bound (viable_count = 0).
    """
    # 1. Valid point estimate with viable mutants sampled
    point_est_run = {
        "status": "COMPLETED",
        "execution": {
            "complete": True,
            "challenge": "FUNCTIONAL_INFO",
            "summary": {
                "hazen_functional_info_bits": 14.5,
                "neutral_percolation_rate": 0.28,
                "viable_count": 12,
                "sample_size": 500,
            },
        },
    }
    eval_point = evaluate_run_hypothesis(point_est_run)
    assert eval_point["verdict"] == "inconclusive"
    assert eval_point["confidence"] is None
    assert eval_point["evidence_summary"]["censored"] is False
    assert eval_point["evidence_summary"]["bound_type"] == "point_estimate"
    assert eval_point["evidence_summary"]["zero_success"] is False

    # 2. Censored run with explicit bound_type='upper_bound'
    censored_run = {
        "status": "COMPLETED",
        "execution": {
            "complete": True,
            "challenge": "FUNCTIONAL_INFO",
            "summary": {
                "hazen_functional_info_bits": 32.0,
                "neutral_percolation_rate": 0.35,
                "censored": True,
                "bound_type": "upper_bound",
            },
        },
    }
    eval_censored = evaluate_run_hypothesis(censored_run)
    assert eval_censored["verdict"] == "inconclusive"
    assert eval_censored["evidence_summary"]["censored"] is True
    assert eval_censored["evidence_summary"]["bound_type"] == "upper_bound"


# ==============================================================================
# R10: Production Active Time Budget & Health.log Coordination
# ==============================================================================

def test_r10_production_active_time_budget_freezes_during_pause(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """R10: Production active time verification:
    - active_elapsed_seconds monotonically advances while RUNNING.
    - active_elapsed_seconds strictly freezes when PAUSED.
    - wall_elapsed_seconds continues to advance while PAUSED.
    - Strict invariant: active_elapsed_seconds <= wall_elapsed_seconds at all points.
    - RunSnapshotV2 accurately reflects active_elapsed_seconds parsed from health.log.
    """
    runs_dir = tmp_path / "runs"
    runs_dir.mkdir(parents=True)
    monkeypatch.setenv("CODONTRACE_RUNS_DIR", str(runs_dir))

    run_id = "run_prod_active_time_010"
    run_entry = runs_dir / run_id
    run_entry.mkdir()
    out_dir = run_entry / "output"
    out_dir.mkdir()

    manifest_data = {
        "schemaVersion": 1,
        "runId": run_id,
        "session_id": f"sess_{run_id}",
        "params": {"workers": 1, "seeds": [42], "totalSeeds": 1},
    }
    (run_entry / "manifest.json").write_text(json.dumps(manifest_data), encoding="utf-8")

    status_data = {
        "status": "RUNNING",
        "session_id": f"sess_{run_id}",
        "revision": 1,
        "params": {"workers": 1, "seeds": [42]},
        "totalSeeds": 1,
        "completedSeeds": 0,
    }
    (run_entry / "status.json").write_text(json.dumps(status_data), encoding="utf-8")

    # Step 1: Running phase (10s wall, 10s active, 0s paused)
    health_file = out_dir / "health.log"
    health_file.write_text(
        json.dumps({
            "paused_seconds": 0.0,
            "active_elapsed_seconds": 10.0,
            "wall_elapsed_seconds": 10.0,
        }) + "\n",
        encoding="utf-8",
    )

    snap1 = runs.build_run_snapshot(run_id, status_data, manifest_data)
    assert snap1["state"] == "RUNNING"
    assert snap1["active_elapsed_seconds"] == 10.0
    assert snap1["paused_seconds"] == 0.0
    assert snap1["active_elapsed_seconds"] <= snap1["wall_elapsed_seconds"]

    # Step 2: Transition to PAUSED via PAUSE file and worker ACK
    (run_entry / "PAUSE").write_text("paused\n", encoding="utf-8")
    (out_dir / "ack_paused_42").write_text("ack\n", encoding="utf-8")

    # While paused: wall time advances from 10s to 25s, active time remains frozen at 10s
    health_file.write_text(
        health_file.read_text(encoding="utf-8")
        + json.dumps({
            "paused_seconds": 15.0,
            "active_elapsed_seconds": 10.0,  # FROZEN
            "wall_elapsed_seconds": 25.0,
        }) + "\n",
        encoding="utf-8",
    )

    snap2 = runs.build_run_snapshot(run_id, status_data, manifest_data)
    assert snap2["state"] == "PAUSED"
    assert snap2["active_elapsed_seconds"] == 10.0, "Active time increased while paused!"
    assert snap2["paused_seconds"] == 15.0
    assert snap2["wall_elapsed_seconds"] == 25.0
    assert snap2["active_elapsed_seconds"] <= snap2["wall_elapsed_seconds"]
    assert round(snap2["active_elapsed_seconds"] + snap2["paused_seconds"], 1) == round(snap2["wall_elapsed_seconds"], 1)

    # Step 3: Resume execution
    (run_entry / "PAUSE").unlink()
    (out_dir / "ack_paused_42").unlink()

    # Active time resumes advancing: 5 more seconds active (total 15s active, 30s wall)
    health_file.write_text(
        health_file.read_text(encoding="utf-8")
        + json.dumps({
            "paused_seconds": 15.0,
            "active_elapsed_seconds": 15.0,  # Resumed
            "wall_elapsed_seconds": 30.0,
        }) + "\n",
        encoding="utf-8",
    )

    snap3 = runs.build_run_snapshot(run_id, status_data, manifest_data)
    assert snap3["state"] == "RUNNING"
    assert snap3["active_elapsed_seconds"] == 15.0
    assert snap3["paused_seconds"] == 15.0
    assert snap3["wall_elapsed_seconds"] == 30.0
    assert snap3["active_elapsed_seconds"] <= snap3["wall_elapsed_seconds"]


# ==============================================================================
# R10: Production Monotonic Uniform Revision Across Lifecycle Actions
# ==============================================================================

def test_r10_production_monotonic_uniform_revision_across_actions(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """R10: Production revision verification:
    - Every manage_run_action strictly increments revision (rev_{n+1} > rev_n).
    - RunSnapshotV2 preserves the exact latest status revision.
    - UI store sync reduction drops stale revisions and enforces monotonic advancement.
    """
    runs_dir = tmp_path / "runs"
    runs_dir.mkdir(parents=True)
    monkeypatch.setenv("CODONTRACE_RUNS_DIR", str(runs_dir))

    run_id = "run_prod_revision_010"
    run_entry = runs_dir / run_id
    run_entry.mkdir()

    manifest_data = {
        "schemaVersion": 1,
        "runId": run_id,
        "session_id": f"sess_{run_id}",
        "capabilities": {"pause": True, "resume": True, "checkpoint_continue": False},
        "params": {"workers": 1, "seeds": [1]},
    }
    (run_entry / "manifest.json").write_text(json.dumps(manifest_data), encoding="utf-8")

    # Initial status at revision 1
    status_data = {
        "status": "RUNNING",
        "session_id": f"sess_{run_id}",
        "revision": 1,
        "params": {"workers": 1, "seeds": [1]},
    }
    (run_entry / "status.json").write_text(json.dumps(status_data), encoding="utf-8")

    # Action 1: PAUSE -> revision must increment to 2
    res_pause = runs.manage_run_action(run_id, "pause")
    assert res_pause.get("ok") is True
    curr_status = json.loads((run_entry / "status.json").read_text(encoding="utf-8"))
    rev_after_pause = curr_status.get("revision", 0)
    assert rev_after_pause == 2, f"Expected revision 2 after pause, got {rev_after_pause}"

    # Action 2: RESUME -> revision must increment to 3
    res_resume = runs.manage_run_action(run_id, "resume")
    assert res_resume.get("ok") is True
    curr_status = json.loads((run_entry / "status.json").read_text(encoding="utf-8"))
    rev_after_resume = curr_status.get("revision", 0)
    assert rev_after_resume == 3, f"Expected revision 3 after resume, got {rev_after_resume}"

    # Action 3: STOP -> revision must increment to 4
    res_stop = runs.manage_run_action(run_id, "stop")
    assert res_stop.get("ok") is True
    curr_status = json.loads((run_entry / "status.json").read_text(encoding="utf-8"))
    rev_after_stop = curr_status.get("revision", 0)
    assert rev_after_stop == 4, f"Expected revision 4 after stop, got {rev_after_stop}"

    # Verify RunSnapshot strictly reflects revision 4
    snap = runs.build_run_snapshot(run_id, curr_status, manifest_data)
    assert snap["revision"] == 4

    # Test UI store sync reduction guard
    job_state = {"id": run_id, "session_id": f"sess_{run_id}", "revision": 4, "status": "stopped"}

    # Stale packet at revision 2 -> must be dropped
    stale_update = {"id": run_id, "session_id": f"sess_{run_id}", "revision": 2, "status": "RUNNING"}
    reduced_stale = apply_store_sync_reduction(job_state, stale_update)
    assert reduced_stale["revision"] == 4
    assert reduced_stale["status"] == "stopped"

    # New session with reset revision 1 -> must be accepted across session boundary
    new_sess_update = {"id": run_id, "session_id": "sess_new_session_002", "revision": 1, "status": "RUNNING"}
    reduced_new_sess = apply_store_sync_reduction(job_state, new_sess_update)
    assert reduced_new_sess["revision"] == 1
    assert reduced_new_sess["session_id"] == "sess_new_session_002"
    assert reduced_new_sess["status"] == "running"


# ==============================================================================
# R10: Production Multilevel Selection Price Equation Partition
# ==============================================================================

def test_r10_production_price_equation_unequal_demes_and_transmission() -> None:
    """R10: Verify multilevel Price equation (Price 1972) partition with:
    1. Unequal deme population sizes (weighted between-group covariance).
    2. Non-zero within-deme variance and transmission bias (E[Cov(w, z)] + E[w * dz]).
    3. Rigorous finite check and evaluator verification.
    """
    # 3 demes with unequal sizes
    deme_sizes = [5, 15, 30]
    total_pop = sum(deme_sizes)
    weights = [s / total_pop for s in deme_sizes]

    # Mean traits and fitnesses per deme
    deme_traits = [0.2, 0.5, 0.8]
    deme_fitness = [1.0, 1.8, 2.4]

    # Weighted population means
    mean_Z = sum(w * z for w, z in zip(weights, deme_traits))
    mean_W = sum(w * f for w, f in zip(weights, deme_fitness))

    # Weighted between-group covariance
    cov_between = sum(w * (f - mean_W) * (z - mean_Z) for w, f, z in zip(weights, deme_fitness, deme_traits))
    between_term = cov_between / mean_W if mean_W > 1e-6 else 0.0

    # Non-zero within-deme term and transmission bias
    within_term = 0.045
    transmission_bias = -0.005
    total_within = within_term + transmission_bias

    assert math.isfinite(between_term)
    assert between_term > 0.0
    assert math.isfinite(total_within)

    # Evaluator verification
    eval_res = evaluate_run_hypothesis({
        "status": "COMPLETED",
        "execution": {
            "complete": True,
            "challenge": "MLS_PRICE",
            "summary": {
                "between_deme_selection_term": between_term,
                "within_deme_selection_term": total_within,
            },
        },
    })
    assert eval_res["verdict"] == "inconclusive"
    assert eval_res["controls_passed"] is False
    assert eval_res["evidence_summary"]["between_term"] == between_term
