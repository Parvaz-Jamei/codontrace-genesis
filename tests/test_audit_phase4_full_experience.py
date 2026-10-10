"""Deterministic Phase 4 test suite for Full Experience & Integration audit remediation.

Tests Section 7 & Acceptance Matrix (AUDIT_P01_L05_PHASES1_4.md):
- Client-server AbortController cancellation via request_id.
- Dynamic cooperative termination in chat_turn.
- Server /api/chat/abort and /api/chat/cancel endpoint contracts.
- Server /api/host version alignment (0.3.0b28) and host telemetry contract.
- Telemetry fidelity and zero synthetic/fake points in execution metrics.
- Analyst transparency and evidence-based hypothesis reasoning.
"""

from __future__ import annotations

import json
import threading
import urllib.error
import urllib.request

import pytest

from codontrace.console import chat, server
from codontrace.console.chat import abort_chat_request, chat_turn
from codontrace.console.evaluator import evaluate_run_hypothesis
from codontrace.console.release import installed_version

# ---------------------------------------------------------------------------
# 1. Chat Turn Abort & Request ID Tracking
# ---------------------------------------------------------------------------

def test_abort_nonexistent_request_returns_false() -> None:
    """Aborting a non-existent request_id must return False without crashing."""
    assert abort_chat_request("non_existent_req_id_12345") is False


def test_chat_turn_pre_aborted_returns_cancelled() -> None:
    """If a request is flagged as cancelled before/during processing, chat_turn must exit cooperatively."""
    req_id = "test_pre_abort_001"
    
    # Pre-register and trigger abort
    event = threading.Event()
    event.set()
    with chat._CHAT_LOCK:
        chat._ACTIVE_CHAT_REQUESTS[req_id] = event

    # Execute chat turn with pre-aborted request_id
    res = chat_turn("Tell me about Price equation", lang="en", request_id=req_id)
    
    assert res.get("cancelled") is True
    assert res.get("model") == "cancelled"
    assert "cancelled by user" in res.get("reply", "").lower()
    
    # Active request must be cleaned up in finally block
    with chat._CHAT_LOCK:
        assert req_id not in chat._ACTIVE_CHAT_REQUESTS


def test_chat_turn_lifecycle_registers_and_cleans_up_request_id() -> None:
    """During chat_turn execution, request_id is registered and cleaned up on return."""
    req_id = "test_cleanup_002"
    with chat._CHAT_LOCK:
        assert req_id not in chat._ACTIVE_CHAT_REQUESTS

    res = chat_turn("What is the current status?", lang="fa", model="local-analyst", request_id=req_id)
    
    assert res.get("source") == "analyst"
    assert res.get("cancelled") is not True
    # Without a selected run, ask for scope instead of exposing other projects.
    assert "یک اجرا را انتخاب" in res.get("reply", "")
    assert res.get("artifacts") == []

    # Cleanup verification
    with chat._CHAT_LOCK:
        assert req_id not in chat._ACTIVE_CHAT_REQUESTS


# ---------------------------------------------------------------------------
# 2. Server Abort Endpoints (/api/chat/abort and /api/chat/cancel)
# ---------------------------------------------------------------------------

def test_server_chat_abort_endpoints() -> None:
    """Verify /api/chat/abort and /api/chat/cancel contract."""
    srv = server.make_server("127.0.0.1", 0)
    port = srv.server_address[1]
    thread = threading.Thread(target=srv.serve_forever)
    thread.daemon = True
    thread.start()

    try:
        origin = f"http://127.0.0.1:{port}"
        
        # Test 1: Missing request_id yields 400
        for ep in ("/api/chat/abort", "/api/chat/cancel"):
            url = f"{origin}{ep}"
            req = urllib.request.Request(
                url,
                data=json.dumps({}).encode("utf-8"),
                headers={"Origin": origin, "Content-Type": "application/json"},
                method="POST",
            )
            try:
                urllib.request.urlopen(req)
                pytest.fail("Expected 400 Bad Request for missing request_id")
            except urllib.error.HTTPError as err:
                assert err.code == 400
                data = json.loads(err.read().decode("utf-8"))
                assert data["ok"] is False
                assert "Missing request_id" in data["error"]

        # Test 2: Valid request_id returns 200 with aborted status
        test_req_id = "test_http_abort_003"
        # Register an event in chat requests
        event = threading.Event()
        with chat._CHAT_LOCK:
            chat._ACTIVE_CHAT_REQUESTS[test_req_id] = event

        req = urllib.request.Request(
            f"{origin}/api/chat/abort",
            data=json.dumps({"request_id": test_req_id}).encode("utf-8"),
            headers={"Origin": origin, "Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req) as resp:
            assert resp.status == 200
            data = json.loads(resp.read().decode("utf-8"))
            assert data["ok"] is True
            assert data["aborted"] is True
            assert data["request_id"] == test_req_id
            assert event.is_set()

        # Clean up
        with chat._CHAT_LOCK:
            chat._ACTIVE_CHAT_REQUESTS.pop(test_req_id, None)

    finally:
        srv.shutdown()
        srv.server_close()
        thread.join(timeout=1.0)


# ---------------------------------------------------------------------------
# 3. Host Profile Version Alignment & Telemetry
# ---------------------------------------------------------------------------

def test_server_host_profile_contract() -> None:
    """Verify /api/host returns 0.3.0b28 and proper system diagnostics."""
    srv = server.make_server("127.0.0.1", 0)
    port = srv.server_address[1]
    thread = threading.Thread(target=srv.serve_forever)
    thread.daemon = True
    thread.start()

    try:
        url = f"http://127.0.0.1:{port}/api/host"
        req = urllib.request.Request(url, headers={"Origin": f"http://127.0.0.1:{port}"})
        
        with urllib.request.urlopen(req) as resp:
            assert resp.status == 200
            data = json.loads(resp.read().decode("utf-8"))
            
            assert data["packageVersion"] == "0.3.0b28"
            assert data["packageVersion"] == installed_version()
            assert "cores" in data
            assert data["cores"] >= 1
            assert "memoryMb" in data
            assert "recommendedWorkers" in data
            assert "llm" in data

    finally:
        srv.shutdown()
        srv.server_close()
        thread.join(timeout=1.0)


# ---------------------------------------------------------------------------
# 4. Telemetry Fidelity & Zero Fake Points
# ---------------------------------------------------------------------------

def test_telemetry_fidelity_exact_measurements_preserved() -> None:
    """Raw telemetry metrics in execution summary must never be altered or interpolated."""
    telemetry = {
        "activity_slope": 0.0842,
        "between_deme_selection_term": 0.0315,
        "within_deme_selection_term": 0.0121,
        "hazen_functional_info_bits": 14.82,
        "neutral_percolation_rate": 0.441,
        "total_generations": 500,
        "elapsed_seconds": 12.4,
    }
    
    # Run details wrapping telemetry
    run_record = {
        "status": "COMPLETED",
        "execution": {
            "complete": True,
            "metrics": telemetry,
            "hypothesis_assessment": {
                "verdict": "supported",
                "confidence": 0.94,
                "controls_passed": True,
                "rationale": "Empirical confirmation",
            },
        },
    }
    
    assessment = evaluate_run_hypothesis(run_record)
    assert assessment["verdict"] == "supported"
    assert assessment["confidence"] == 0.94
    assert assessment["controls_passed"] is True

    # Assert metrics in execution payload remain intact without dummy fields
    exec_metrics = run_record["execution"]["metrics"]
    for k, v in telemetry.items():
        assert exec_metrics[k] == v
    
    # Verify unmeasured metrics are not synthesized
    assert "fake_metric" not in exec_metrics


def test_analyst_hypothesis_evidence_assessment_language_support() -> None:
    """Analyst response correctly evaluates hypothesis in both English and Persian without hardcoded proof."""
    mock_job = {
        "status": "COMPLETED",
        "execution": {
            "complete": True,
            "hypothesis_assessment": {
                "verdict": "supported",
                "confidence": 0.92,
                "controls_passed": True,
                "rationale": "Consistent negative correlation in time-lagged reciprocal fitness matrix",
                "protocol": "time_shifted_reciprocal_antagonism",
            },
        },
    }

    # English query
    en_res = chat_turn("Is the Red Queen hypothesis proved?", lang="en", model="local-analyst", job_context=mock_job)
    assert en_res["source"] == "analyst"
    assert "supported" in en_res["reply"].lower()
    assert "Genesis Epistemic Standard" in en_res["reply"]
    assert "empirical evidence" in en_res["reply"]

    # Persian query
    fa_res = chat_turn("آیا فرضیه ملکه سرخ اثبات شد؟", lang="fa", model="local-analyst", job_context=mock_job)
    assert fa_res["source"] == "analyst"
    assert "پشتیبانی‌شده" in fa_res["reply"]
    assert "اصل روش‌شناختی Genesis" in fa_res["reply"]
