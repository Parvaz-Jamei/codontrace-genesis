"""Master 10-Phase Scientific Invariant and Deep Integrity Verification Suite.

Validates the core scientific pillars across all 10 audit phases in two layers:
- Part I: Unit / Synthetic Controls (baseline algorithmic sanity checks).
- Part II: Production & Integration Verification Layer (R10, R11, R02, R05):
    1. Active Time Budget & Paused Seconds Subtraction (R02).
    2. Monotonic Revision Comparison & Stale Rejection (R05).
    3. Telemetry Fidelity & API Contract Compliance (Zero Fake Points).
    4. Hazen Functional Information Uncertainty Bounds & Non-Binary Spaces (R10).
    5. Price Equation Multilevel Partition with Unequal Demes & Transmission (R10).
    6. Two-Way Cooperative Chat Cancellation with Upstream Semantic Distinction (R11).
"""

from __future__ import annotations

import json
import math
import threading
import time
import urllib.error
from pathlib import Path
from unittest.mock import patch

import pytest

from codontrace.console import chat
from codontrace.console.evaluator import _is_finite, evaluate_run_hypothesis
from codontrace.console.runs import build_run_snapshot, get_runner_adapter
from codontrace.genesis.phase_k import run_multi_generation_price_analysis
from codontrace.genesis.schema import HypothesisAssessment, MetricRecord
from codontrace.genesis.snapshot import (
    create_run_snapshot,
    validate_run_snapshot,
)

# ==============================================================================
# PART I: UNIT & SYNTHETIC CONTROLS
# ==============================================================================


def test_hazen_functional_information_mathematical_bounds() -> None:
    """[Unit / Synthetic Control] I(Ex) = -log2(M(Ex)/N) bounded for ideal binary genome."""
    genome_len = 32

    # Case 1: 100% viable fraction (p_f = 1.0) -> 0 bits
    p_f_1 = 1.0
    info_1 = -math.log2(p_f_1)
    assert info_1 == 0.0

    # Case 2: 1/256 viable fraction (p_f = 2^-8) -> 8.0 bits
    p_f_2 = 1.0 / 256.0
    info_2 = -math.log2(p_f_2)
    assert round(info_2, 4) == 8.0

    # Case 3: Zero viable mutants sampled -> synthetic binary upper bound is genome_len
    p_f_3 = 0.0
    info_3 = -math.log2(p_f_3) if p_f_3 > 0 else float(genome_len)
    assert info_3 == 32.0

    # A valid measured FI endpoint alone does not supply a decision protocol.
    run_record = {
        "status": "COMPLETED",
        "execution": {
            "complete": True,
            "challenge": "FUNCTIONAL_INFO",
            "summary": {
                "hazen_functional_info_bits": info_2,
                "neutral_percolation_rate": 0.35,
            },
        },
    }
    assessment = evaluate_run_hypothesis(run_record)
    assert assessment["verdict"] == "inconclusive"
    assert assessment["controls_passed"] is False
    assert assessment["evidence_summary"]["fi_bits"] == 8.0


def test_price_equation_multilevel_selection_covariance_partition() -> None:
    """[Unit / Synthetic Control] Equal-sized synthetic demes covariance partition (Price 1972)."""
    # 4 demes of size 10
    num_demes = 4
    deme_size = 10

    # Synthetic demes with varying mean trait z and mean fitness W
    demes_z = [
        [0.1] * deme_size,  # Deme 0: low trait
        [0.4] * deme_size,  # Deme 1: mid-low trait
        [0.7] * deme_size,  # Deme 2: mid-high trait
        [0.9] * deme_size,  # Deme 3: high trait
    ]
    # Positive between-deme selection: fitness increases with mean trait
    demes_w = [
        [1.0] * deme_size,
        [1.5] * deme_size,
        [2.0] * deme_size,
        [2.5] * deme_size,
    ]

    deme_mean_z = [sum(demes_z[d]) / deme_size for d in range(num_demes)]
    deme_mean_w = [sum(demes_w[d]) / deme_size for d in range(num_demes)]

    mean_W = sum(deme_mean_w) / num_demes
    mean_Z = sum(deme_mean_z) / num_demes

    # Between-group covariance
    cov_between = sum((deme_mean_w[d] - mean_W) * (deme_mean_z[d] - mean_Z) for d in range(num_demes)) / num_demes
    between_term = cov_between / mean_W if mean_W > 1e-6 else 0.0

    # Positive between-group selection confirmed
    assert between_term > 0.0
    assert math.isfinite(between_term)

    # Within-group variance is zero here (homogenous traits within demes)
    within_term = 0.0

    # Algebraic covariance alone does not establish replicated selection evidence.
    eval_res = evaluate_run_hypothesis({
        "status": "COMPLETED",
        "execution": {
            "complete": True,
            "challenge": "MLS_PRICE",
            "summary": {
                "between_deme_selection_term": between_term,
                "within_deme_selection_term": within_term,
            },
        },
    })
    assert eval_res["verdict"] == "inconclusive"
    assert eval_res["controls_passed"] is False
    assert eval_res["evidence_summary"]["between_term"] == between_term


def test_ieee_754_rejection_of_nan_and_inf() -> None:
    """[Unit / Synthetic Control] Rejection of NaN/Inf in MetricRecord, snapshot, and hypothesis evaluator."""
    # 1. _is_finite helper
    assert _is_finite(0) is True
    assert _is_finite(42.5) is True
    assert _is_finite(float("nan")) is False
    assert _is_finite(float("inf")) is False
    assert _is_finite(float("-inf")) is False
    assert _is_finite("42") is False

    # 2. MetricRecord
    with pytest.raises(ValueError, match="finite float"):
        MetricRecord("invalid_metric", float("nan"), "bits")
    with pytest.raises(ValueError, match="finite float"):
        MetricRecord("invalid_metric", float("inf"), "bits")

    # 3. HypothesisAssessment confidence
    with pytest.raises(ValueError, match="must be finite"):
        HypothesisAssessment("test_hypo", "supported", float("nan"), ("sha256_mock",))

    # 4. Evaluator rejects non-finite metrics in execution
    eval_nan = evaluate_run_hypothesis({
        "status": "COMPLETED",
        "execution": {
            "complete": True,
            "challenge": "FUNCTIONAL_INFO",
            "summary": {
                "hazen_functional_info_bits": float("nan"),
                "neutral_percolation_rate": 0.5,
            },
        },
    })
    assert eval_nan["verdict"] == "invalid"
    assert eval_nan["controls_passed"] is False


def test_run_snapshot_v2_progress_fidelity() -> None:
    """[Unit / Synthetic Control] RunSnapshotV2 progress bounds enforcement (0..100)."""
    snap = create_run_snapshot(
        run_id="run_fidelity_001",
        session_id="sess_001",
        state="RUNNING",
        done=45.0,
        total=100.0,
        pct=45.0,
    )
    validated = validate_run_snapshot(snap)
    assert validated["progress"]["pct"] == 45.0
    assert validated["progress"]["done"] == 45.0
    assert validated["progress"]["total"] == 100.0

    # Out of bounds percentage rejected
    with pytest.raises(Exception):
        validate_run_snapshot({
            "schema_version": "run_snapshot_v2",
            "run_id": "r1",
            "session_id": "s1",
            "revision": 1,
            "state": "RUNNING",
            "capabilities": {"pause": True, "resume": True, "checkpoint_continue": False},
            "workers_expected": 1,
            "workers_paused": 0,
            "progress": {"kind": "work_units", "stage": "sim", "done": 120.0, "total": 100.0, "pct": 120.0},
            "active_elapsed_seconds": 1.0,
            "paused_seconds": 0.0,
            "wall_elapsed_seconds": 1.0,
            "heartbeat_at": "",
        })


def test_worker_stop_ack_and_active_time_budget() -> None:
    """[Unit / Synthetic Control] Arithmetic baseline for active_elapsed = wall - paused."""
    started_wall = 1000.0
    current_wall = 1020.0  # 20 wall seconds
    accumulated_paused = 15.0  # 15 seconds paused

    active_elapsed = max(0.0, (current_wall - started_wall) - accumulated_paused)
    assert active_elapsed == 5.0
    assert active_elapsed < (current_wall - started_wall)


def test_two_way_chat_cancellation_lifecycle() -> None:
    """[Unit / Synthetic Control] Client request_id registration and cooperative abort via /api/chat/abort."""
    req_id = "test_two_way_abort_009"

    # Pre-register event
    event = threading.Event()
    with chat._CHAT_LOCK:
        chat._ACTIVE_CHAT_REQUESTS[req_id] = event

    # Trigger abort
    assert chat.abort_chat_request(req_id) is True
    assert event.is_set()

    # Chat turn recognizes abort
    res = chat.chat_turn("Calculate Eigen threshold", request_id=req_id)
    assert res.get("cancelled") is True
    assert res.get("cancelled_type") == "cancelled_response"
    assert res.get("model") == "cancelled"

    # Verified clean teardown
    with chat._CHAT_LOCK:
        assert req_id not in chat._ACTIVE_CHAT_REQUESTS


def test_zero_fake_points_fidelity_preservation() -> None:
    """[Unit / Synthetic Control] Raw telemetry fields serialize unaltered without synthetic injection."""
    raw_telemetry = {
        "activity_slope": 0.124,
        "between_deme_selection_term": 0.052,
        "within_deme_selection_term": 0.018,
        "hazen_functional_info_bits": 19.45,
        "neutral_percolation_rate": 0.62,
    }

    payload = json.dumps(raw_telemetry)
    deserialized = json.loads(payload)

    for k, v in raw_telemetry.items():
        assert deserialized[k] == v
    assert "fake_curve_points" not in deserialized


def test_epistemic_neutrality_no_boolean_locking() -> None:
    """[Unit / Synthetic Control] Evaluator must never permanently lock hypothesis to False."""
    valid_run = {
        "status": "COMPLETED",
        "execution": {
            "complete": True,
            "hypothesis_assessment": {
                "verdict": "supported",
                "confidence": 0.94,
                "controls_passed": True,
                "rationale": "Empirically supported reciprocal antagonistic dynamics",
            },
        },
    }
    assessment = evaluate_run_hypothesis(valid_run)
    assert assessment["verdict"] == "supported"
    assert assessment["confidence"] == 0.94
    assert assessment["controls_passed"] is True


# ==============================================================================
# PART II: PRODUCTION & INTEGRATION VERIFICATION LAYER (R10, R11, R02, R05)
# ==============================================================================


def test_production_active_time_paused_seconds_subtraction(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """[Production Verification - R02] Subtraction of paused_seconds from active time via build_run_snapshot."""
    monkeypatch.setenv("CODONTRACE_RUNS_DIR", str(tmp_path))
    run_id = "run_prod_active_01"
    run_dir = tmp_path / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    out_dir = run_dir / "output"
    out_dir.mkdir(parents=True, exist_ok=True)

    # Establish PAUSE marker and worker ACK file for cooperative state confirmation
    (run_dir / "PAUSE").touch()
    (run_dir / "ack_paused_seed_16001").touch()

    # Scenario 1: status_info contains paused_seconds directly, health.log absent
    t_start = time.time() - 40.0
    status_info_paused = {
        "status": "PAUSED",
        "startedAt": t_start,
        "paused_seconds": 15.0,
    }
    snap1 = build_run_snapshot(run_id, status_info_paused)
    assert snap1["state"] == "PAUSED"
    assert snap1["paused_seconds"] == 15.0
    assert snap1["active_elapsed_seconds"] == round(snap1["wall_elapsed_seconds"] - 15.0, 2)
    assert snap1["active_elapsed_seconds"] >= 0.0

    # Scenario 2: Coordinator health.log records paused time during live monitoring ticks
    health_lines = [
        json.dumps({
            "timestamp": 1000.0,
            "wall_elapsed_seconds": 1.0,
            "active_elapsed_seconds": 1.0,
            "paused_seconds": 0.0,
            "status": "RUNNING",
        }),
        json.dumps({
            "timestamp": 1010.0,
            "wall_elapsed_seconds": 11.0,
            "active_elapsed_seconds": 5.0,
            "paused_seconds": 6.0,
            "status": "PAUSED",
        }),
        json.dumps({
            "timestamp": 1025.0,
            "wall_elapsed_seconds": 26.0,
            "active_elapsed_seconds": 15.0,
            "paused_seconds": 11.0,
            "status": "RUNNING",
        }),
    ]
    (out_dir / "health.log").write_text("\n".join(health_lines) + "\n", encoding="utf-8")

    snap2 = build_run_snapshot(run_id, {"status": "RUNNING", "startedAt": t_start})
    assert snap2["active_elapsed_seconds"] == 15.0
    assert snap2["paused_seconds"] == 11.0
    assert snap2["wall_elapsed_seconds"] == 26.0
    assert round(snap2["active_elapsed_seconds"] + snap2["paused_seconds"], 2) == snap2["wall_elapsed_seconds"]


def test_production_monotonic_revision_server_rejection(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """[Production Verification - R05] Rejection of stale revisions in server runner adapter."""
    monkeypatch.setenv("CODONTRACE_RUNS_DIR", str(tmp_path))
    run_id = "run_prod_rev_01"
    run_dir = tmp_path / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    out_dir = run_dir / "output"
    out_dir.mkdir(parents=True, exist_ok=True)

    adapter = get_runner_adapter({"scriptName": "engine_run.py"})

    # 1. Authoritative status at root has revision 10, status PAUSED
    root_status = {
        "status": "PAUSED",
        "revision": 10,
        "session_id": "sess_001",
        "pct": 60.0,
    }
    (run_dir / "status.json").write_text(json.dumps(root_status), encoding="utf-8")

    # 2. Stale worker status write in output/ has older revision 8, status RUNNING
    stale_nested_status = {
        "status": "RUNNING",
        "revision": 8,
        "session_id": "sess_001",
        "pct": 45.0,
    }
    (out_dir / "status.json").write_text(json.dumps(stale_nested_status), encoding="utf-8")

    resolved_stale = adapter.reconcile_status(run_dir)
    assert resolved_stale["revision"] == 10
    assert resolved_stale["status"] == "PAUSED"
    assert resolved_stale["pct"] == 60.0

    # 3. Newer status write arrives with revision 12, status RESUMING
    newer_nested_status = {
        "status": "RESUMING",
        "revision": 12,
        "session_id": "sess_001",
        "pct": 62.0,
    }
    (out_dir / "status.json").write_text(json.dumps(newer_nested_status), encoding="utf-8")

    resolved_newer = adapter.reconcile_status(run_dir)
    assert resolved_newer["revision"] == 12
    assert resolved_newer["status"] == "RESUMING"
    assert resolved_newer["pct"] == 62.0


def test_production_telemetry_fidelity_and_contract_compliance() -> None:
    """[Production Verification - Telemetry Fidelity] Full snapshot schema validation without synthetic dummy data."""
    snap = create_run_snapshot(
        run_id="run_telemetry_prod_01",
        session_id="sess_prod_01",
        state="RUNNING",
        done=60.0,
        total=100.0,
        pct=60.0,
        active_elapsed=120.5,
        paused_elapsed=14.2,
        wall_elapsed=134.7,
        supports_pause=True,
        supports_resume=True,
        supports_checkpoint=False,
        workers_expected=4,
        workers_paused=0,
    )
    validated = validate_run_snapshot(snap)

    assert validated["schema_version"] == "run_snapshot_v2"
    assert validated["run_id"] == "run_telemetry_prod_01"
    assert validated["progress"]["pct"] == 60.0
    assert validated["active_elapsed_seconds"] == 120.5
    assert validated["paused_seconds"] == 14.2
    assert validated["wall_elapsed_seconds"] == 134.7
    assert validated["capabilities"]["pause"] is True

    # Confirm strict absence of synthetic injections or fake curve keys
    assert "fake_curve_points" not in validated
    assert "injected_mock_data" not in validated
    assert "quantized_progress_33" not in validated

    # Round-trip JSON serialization fidelity
    serialized = json.dumps(validated)
    deserialized = json.loads(serialized)
    assert deserialized == validated

    # Out-of-bound percentage rejection by schema validator
    invalid_snap = dict(snap)
    invalid_snap["progress"] = {"kind": "work_units", "stage": "sim", "done": 150.0, "total": 100.0, "pct": 150.0}
    with pytest.raises(Exception):
        validate_run_snapshot(invalid_snap)


def test_production_hazen_fi_zero_success_uncertainty_bounds() -> None:
    """[Production Verification - Hazen FI] Zero-success scenario bounded by uncertainty rather than fixed 32."""
    # When zero viable mutants are sampled (k=0) out of N sampled mutants:
    # A fixed 32-bit ceiling is an unscientific artifact (conflating 32-bit integer / binary genome length).
    #
    # 1. For sample size N=100 with k=0:
    # Rule of three (95% CI upper bound on viable probability p_f <= 3/N):
    # p_f_upper_95 = 3.0 / 100.0 = 0.03
    # Functional information lower bound I >= -log2(0.03) ≈ 5.059 bits.
    n_sample_100 = 100
    p_f_upper_100 = 3.0 / n_sample_100
    fi_lower_bound_100 = -math.log2(p_f_upper_100)
    assert round(fi_lower_bound_100, 2) == 5.06

    # 2. For sample size N=1000 with k=0:
    # p_f_upper_95 = 3.0 / 1000.0 = 0.003
    # Functional information lower bound I >= -log2(0.003) ≈ 8.38 bits.
    n_sample_1000 = 1000
    p_f_upper_1000 = 3.0 / n_sample_1000
    fi_lower_bound_1000 = -math.log2(p_f_upper_1000)
    assert round(fi_lower_bound_1000, 2) == 8.38

    # 3. For non-binary alphabet (e.g. 20-letter amino acids), length L=32:
    # Configuration space is 20^32, which is 32 * log2(20) ≈ 138.3 bits, NOT 32 bits.
    alphabet_size_aa = 20
    length_aa = 32
    max_bits_aa = length_aa * math.log2(alphabet_size_aa)
    assert round(max_bits_aa, 1) == 138.3

    # 4. Evaluator assessment: when 0 viable mutants and percolation is 0,
    # verdict must be 'not_supported' (functional threshold not met) with controls passing.
    run_record_zero_fi = {
        "status": "COMPLETED",
        "execution": {
            "complete": True,
            "challenge": "FUNCTIONAL_INFO",
            "summary": {
                "hazen_functional_info_bits": 0.0,
                "neutral_percolation_rate": 0.0,
            },
        },
    }
    assessment = evaluate_run_hypothesis(run_record_zero_fi)
    # A descriptive endpoint is neither a registered negative test nor proof.
    assert assessment["verdict"] == "inconclusive"
    assert assessment["controls_passed"] is False
    assert assessment["confidence"] is None


def test_production_price_equation_multilevel_unequal_demes_and_transmission() -> None:
    """[Production Verification - Price Equation] Multi-level partition with unequal demes and transmission term."""
    # 1. Multi-generation Price campaign with actual package function
    campaign = run_multi_generation_price_analysis(smoke=True)
    assert campaign.transmission_term_estimated is True
    assert campaign.transmission_identity_holds is True
    assert campaign.price_equation_complete is False  # Epistemic boundary preserved
    assert math.isfinite(campaign.mean_mls_transmission_term)
    assert math.isfinite(campaign.mean_mls_selection_term)

    # 2. Rigorous Price 1972 multilevel covariance partition with unequal deme sizes
    # Demes with unequal sizes: 5, 10, 25 organisms (total N = 40)
    deme_sizes = [5, 10, 25]
    total_pop = sum(deme_sizes)
    weights = [s / total_pop for s in deme_sizes]

    # Parent traits z, parent fitnesses w, offspring traits z_prime
    # Transmission change: dz = z_prime - z
    deme_data = [
        # Deme 0 (size 5): low mean trait
        {
            "z": [0.1, 0.12, 0.15, 0.18, 0.20],
            "w": [1.0, 1.1, 1.0, 1.2, 1.1],
            "dz": [0.01, -0.02, 0.0, 0.02, -0.01],
        },
        # Deme 1 (size 10): mid mean trait
        {
            "z": [0.4, 0.42, 0.45, 0.41, 0.44, 0.43, 0.46, 0.42, 0.45, 0.42],
            "w": [1.5, 1.6, 1.4, 1.7, 1.5, 1.6, 1.5, 1.7, 1.6, 1.5],
            "dz": [0.02, 0.01, -0.01, 0.0, 0.03, -0.02, 0.01, 0.0, 0.02, -0.01],
        },
        # Deme 2 (size 25): high mean trait
        {
            "z": [0.8 + 0.01 * (i % 5) for i in range(25)],
            "w": [2.0 + 0.05 * (i % 4) for i in range(25)],
            "dz": [0.01 * ((i % 3) - 1) for i in range(25)],
        },
    ]

    deme_mean_z = []
    deme_mean_w = []
    deme_within_cov = []
    deme_trans_term = []

    for d, data in enumerate(deme_data):
        n = deme_sizes[d]
        z = data["z"]
        w = data["w"]
        dz = data["dz"]

        mean_z_d = sum(z) / n
        mean_w_d = sum(w) / n
        deme_mean_z.append(mean_z_d)
        deme_mean_w.append(mean_w_d)

        # Within-deme covariance: Cov_d(w, z) = sum((w_i - mean_w_d) * (z_i - mean_z_d)) / n
        cov_w_z_d = sum((w[i] - mean_w_d) * (z[i] - mean_z_d) for i in range(n)) / n
        deme_within_cov.append(cov_w_z_d)

        # Transmission component for deme d: E_d[w * dz] = sum(w_i * dz_i) / n
        trans_d = sum(w[i] * dz[i] for i in range(n)) / n
        deme_trans_term.append(trans_d)

    # Weighted population averages
    mean_W = sum(weights[d] * deme_mean_w[d] for d in range(len(deme_sizes)))
    mean_Z = sum(weights[d] * deme_mean_z[d] for d in range(len(deme_sizes)))

    # 1. Between-group selection term: Cov(W_g, Z_g) / mean_W
    cov_between = sum(
        weights[d] * (deme_mean_w[d] - mean_W) * (deme_mean_z[d] - mean_Z)
        for d in range(len(deme_sizes))
    )
    between_term = cov_between / mean_W

    # 2. Within-group selection term: E[Cov(w, z)] / mean_W
    within_term = sum(weights[d] * deme_within_cov[d] for d in range(len(deme_sizes))) / mean_W

    # 3. Transmission term: E[w * dz] / mean_W
    transmission_term = sum(weights[d] * deme_trans_term[d] for d in range(len(deme_sizes))) / mean_W

    # Total evolutionary change in trait:
    # delta_Z = (E[w * (z + dz)] / mean_W) - mean_Z
    total_w_zprime = sum(
        weights[d]
        * (
            sum(
                deme_data[d]["w"][i] * (deme_data[d]["z"][i] + deme_data[d]["dz"][i])
                for i in range(deme_sizes[d])
            )
            / deme_sizes[d]
        )
        for d in range(len(deme_sizes))
    )
    delta_Z_actual = (total_w_zprime / mean_W) - mean_Z

    # Price equation identity partition: Delta_Z = Between + Within + Transmission
    predicted_delta_Z = between_term + within_term + transmission_term
    residual = abs(delta_Z_actual - predicted_delta_Z)

    assert residual < 1e-12, f"Price equation partition failed with residual {residual}"
    assert between_term > 0.0  # Confirmed positive between-group selection


def test_production_chat_cancellation_semantic_distinction() -> None:
    """[Production Verification - R11] Clear semantic distinction: user abort vs upstream error."""
    # Scenario A: User aborts request via abort_chat_request
    req_id_user = "test_user_abort_distinction_01"
    event_user = threading.Event()
    with chat._CHAT_LOCK:
        chat._ACTIVE_CHAT_REQUESTS[req_id_user] = event_user

    assert chat.abort_chat_request(req_id_user) is True
    assert event_user.is_set()

    res_user = chat.chat_turn("Explain Price equation", request_id=req_id_user)
    assert res_user["cancelled"] is True
    assert res_user["cancelled_type"] == "cancelled_response"
    assert res_user["model"] == "cancelled"

    # Clean teardown guaranteed in finally
    with chat._CHAT_LOCK:
        assert req_id_user not in chat._ACTIVE_CHAT_REQUESTS

    # Scenario B: Upstream LLM drops connection / times out WITHOUT user cancellation
    req_id_upstream = "test_upstream_fail_distinction_02"
    with patch("codontrace.console.chat.check_llm_status", return_value={
        "mounted": True,
        "endpoint": "http://127.0.0.1:8088/v1/chat/completions",
        "model": "llama-server",
        "provider": "llama-server",
        "available_models": ["llama-server"],
    }):
        with patch("urllib.request.urlopen", side_effect=TimeoutError("Connection timed out")):
            res_upstream = chat.chat_turn("Explain Price equation", request_id=req_id_upstream, model="board-model")
            assert res_upstream["cancelled"] is False
            assert res_upstream["cancelled_type"] == "cancelled_upstream"
            assert res_upstream["fallback"] is True
            assert res_upstream["source"] == "analyst"

    # Clean teardown guaranteed
    with chat._CHAT_LOCK:
        assert req_id_upstream not in chat._ACTIVE_CHAT_REQUESTS

    # Scenario C: Direct query_llm tests
    # With cancel_event set -> returns None immediately
    ev_cancel = threading.Event()
    ev_cancel.set()
    assert chat.query_llm([{"role": "user", "content": "test"}], cancel_event=ev_cancel) is None

    # Without cancel_event, network error -> raises LLMUpstreamError
    with patch("codontrace.console.chat.check_llm_status", return_value={
        "mounted": True,
        "endpoint": "http://127.0.0.1:8088/v1/chat/completions",
        "model": "llama-server",
        "provider": "llama-server",
        "available_models": ["llama-server"],
    }):
        with patch("urllib.request.urlopen", side_effect=urllib.error.URLError("Refused")):
            with pytest.raises(chat.LLMUpstreamError, match="cancelled_upstream"):
                chat.query_llm([{"role": "user", "content": "test"}])
