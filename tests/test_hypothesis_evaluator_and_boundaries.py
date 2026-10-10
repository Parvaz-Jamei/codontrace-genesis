"""Deterministic tests for evidence evaluator, chat hypothesis integration, and execution boundaries.

Tests Issue R01:
- Dynamic evidence evaluator (supported, not_supported, inconclusive, invalid, not_evaluated).
- Integration in console chat and analyst replies without permanent boolean locking.

Tests Issue R09:
- Clarified boundaries between frontier reference models and GenesisEngine in manifests and scripts.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from codontrace.console.chat import _generate_analyst_reply
from codontrace.console.evaluator import evaluate_run_hypothesis


def test_evaluator_unstarted_and_missing() -> None:
    # None run
    res = evaluate_run_hypothesis(None)
    assert res["verdict"] == "not_evaluated"

    # Active running run
    res_running = evaluate_run_hypothesis({"status": "RUNNING", "title": "live_run"})
    assert res_running["verdict"] == "not_evaluated"
    assert "active" in res_running["rationale"]

    # Failed run without execution data
    res_failed = evaluate_run_hypothesis({"status": "FAILED", "title": "aborted"})
    assert res_failed["verdict"] == "invalid"


def test_evaluator_invalid_due_to_failures_or_replays() -> None:
    # Exception stop reason
    res_exc = evaluate_run_hypothesis({
        "status": "FAILED",
        "execution": {
            "complete": False,
            "stop_reason": "EXCEPTION",
            "validation_failures": ["corrupt_archive_checksum"],
        },
    })
    assert res_exc["verdict"] == "invalid"
    assert not res_exc["controls_passed"]

    # Replay mismatch
    res_replay = evaluate_run_hypothesis({
        "status": "STOPPED",
        "execution": {
            "complete": False,
            "replays": [{"seed": 101, "matched": False}],
        },
    })
    assert res_replay["verdict"] == "invalid"


def test_evaluator_oee_novelty_metrics_are_exploratory() -> None:
    # OEE novelty with slope >= 0.1
    res_supp = evaluate_run_hypothesis({
        "status": "COMPLETED",
        "execution": {
            "complete": True,
            "challenge": "OEE_NOVELTY",
            "total_generations": 5000,
            "summary": {
                "activity_slope": 0.245,
                "total_generations": 5000,
            },
        },
    })
    assert res_supp["verdict"] == "inconclusive"
    assert res_supp["confidence"] is None
    assert res_supp["controls_passed"] is False

    # OEE novelty with slope < 0.1 (bounded cycling)
    res_not_supp = evaluate_run_hypothesis({
        "status": "COMPLETED",
        "execution": {
            "complete": True,
            "challenge": "OEE_NOVELTY",
            "total_generations": 5000,
            "summary": {
                "activity_slope": 0.042,
                "total_generations": 5000,
            },
        },
    })
    assert res_not_supp["verdict"] == "inconclusive"

    # OEE novelty premature halt
    res_inconclusive = evaluate_run_hypothesis({
        "status": "STOPPED",
        "execution": {
            "complete": False,
            "challenge": "OEE_NOVELTY",
            "total_generations": 200,
            "summary": {
                "activity_slope": 0.15,
                "total_generations": 200,
            },
        },
    })
    assert res_inconclusive["verdict"] == "inconclusive"


def test_evaluator_mls_price_coefficient_is_descriptive() -> None:
    res_mls = evaluate_run_hypothesis({
        "status": "COMPLETED",
        "execution": {
            "complete": True,
            "challenge": "MLS_PRICE",
            "summary": {
                "between_deme_selection_term": 0.1875,
                "within_deme_selection_term": 0.05,
            },
        },
    })
    assert res_mls["verdict"] == "inconclusive"
    assert res_mls["confidence"] is None


def test_evaluator_functional_information_point_estimate_is_descriptive() -> None:
    res_fi = evaluate_run_hypothesis({
        "status": "COMPLETED",
        "execution": {
            "complete": True,
            "challenge": "FUNCTIONAL_INFO",
            "summary": {
                "hazen_functional_info_bits": 8.42,
                "neutral_percolation_rate": 0.35,
            },
        },
    })
    assert res_fi["verdict"] == "inconclusive"
    assert res_fi["confidence"] is None


def test_evaluator_red_queen_timeshift() -> None:
    # Incomplete diagnostics
    res_diag_inc = evaluate_run_hypothesis({
        "status": "STOPPED",
        "diagnostics": {"by_seed": []},
        "execution": {"complete": False, "diagnostics_complete": False},
    })
    assert res_diag_inc["verdict"] == "inconclusive"

    # Completed diagnostics with positive signals
    res_diag_supp = evaluate_run_hypothesis({
        "status": "COMPLETED",
        "diagnostics": {
            "by_seed": [
                {"seed": 1, "matrices": [{"mean_contrast": 0.15}]},
                {"seed": 2, "matrices": [{"mean_contrast": 0.12}]},
            ],
        },
        "execution": {"complete": True, "diagnostics_complete": True},
    })
    assert res_diag_supp["verdict"] == "inconclusive"
    assert res_diag_supp["confidence"] is None

    # Completed diagnostics with negative signals
    res_diag_neg = evaluate_run_hypothesis({
        "status": "COMPLETED",
        "diagnostics": {
            "by_seed": [
                {"seed": 1, "matrices": [{"mean_contrast": -0.10}]},
                {"seed": 2, "matrices": [{"mean_contrast": -0.08}]},
            ],
        },
        "execution": {"complete": True, "diagnostics_complete": True},
    })
    assert res_diag_neg["verdict"] == "inconclusive"


def test_chat_analyst_reply_evaluates_dynamically() -> None:
    # Query without run context
    rep_en = _generate_analyst_reply("Is the Red Queen hypothesis proved?", lang="en", job_context=None, job_id=None)
    assert "not_evaluated" in rep_en
    assert "strictly locked to false" not in rep_en.lower()

    # Query with Persian language
    rep_fa = _generate_analyst_reply("آیا ملکه سرخ اثبات شده است؟", lang="fa", job_context=None, job_id=None)
    assert "ارزیابی شواهد فرضیه" in rep_fa
    assert "به طور قطعی false است" not in rep_fa.lower()

    # Query with completed supported run context
    supp_context = {
        "status": "COMPLETED",
        "execution": {
            "complete": True,
            "challenge": "OEE_NOVELTY",
            "total_generations": 10000,
            "summary": {"activity_slope": 0.25, "total_generations": 10000},
            "hypothesis_assessment": {"verdict": "supported", "controls_passed": True, "confidence": None, "protocol": "verified_external_protocol"},
        },
    }
    rep_supp = _generate_analyst_reply("What is the hypothesis verdict for this run?", lang="en", job_context=supp_context, job_id=None)
    assert "Verdict is 'supported'" in rep_supp


def test_manifest_boundary_classification(tmp_path: Path, monkeypatch: Any) -> None:
    monkeypatch.setenv("CODONTRACE_RUNS_DIR", str(tmp_path / "runs"))
    from codontrace.console.runs import get_run_details, launch_simulation_run

    # 1. Launch default run (should be genesis_engine)
    res_engine = launch_simulation_run({
        "generations": 2,
        "workers": 1,
        "seeds": [16001],
        "title": "engine_test",
    })
    assert res_engine["ok"] is True
    details_engine = get_run_details(res_engine["runId"])
    assert details_engine is not None
    manifest = details_engine["manifest"]
    assert "executionBoundary" in manifest
    assert manifest["executionBoundary"]["engineBackend"] == "genesis_engine"
    assert manifest["executionBoundary"]["isGenesisEngine"] is True
    assert manifest["executionBoundary"]["isFrontierReference"] is False
    assert details_engine["statusData"]["engineBackend"] == "genesis_engine"

    # 2. Launch frontier challenge run (should be frontier_reference_model)
    res_frontier = launch_simulation_run({
        "generations": 2,
        "workers": 1,
        "seeds": [16001],
        "title": "frontier_test",
        "scriptName": "grand_frontier_4challenge_campaign.py",
    })
    assert res_frontier["ok"] is True
    details_frontier = get_run_details(res_frontier["runId"])
    assert details_frontier is not None
    manifest_f = details_frontier["manifest"]
    assert manifest_f["executionBoundary"]["engineBackend"] == "frontier_reference_model"
    assert manifest_f["executionBoundary"]["isFrontierReference"] is True
    assert manifest_f["executionBoundary"]["isGenesisEngine"] is False
    assert details_frontier["statusData"]["engineBackend"] == "frontier_reference_model"


@pytest.mark.parametrize("contrast", [1.0, -1.0, 0.0])
def test_raw_time_shift_sign_cannot_create_confirmatory_verdict(contrast: float) -> None:
    assessment = evaluate_run_hypothesis({"status": "COMPLETED", "execution": {"complete": True, "diagnostics_complete": True},
        "diagnostics": {"by_seed": [{"seed": 1, "matrices": [{"mean_contrast": contrast}]}, {"seed": 1, "matrices": [{"mean_contrast": contrast}]}]}})
    assert assessment["verdict"] == "inconclusive"
    assert assessment["confidence"] is None
    assert assessment["controls_passed"] is False
    assert assessment["evidence_summary"]["independent_seeds"] == 1


@pytest.mark.parametrize("verdict", ["supported", "not_supported"])
def test_valid_precomputed_confirmatory_assessment_is_accepted(verdict: str) -> None:
    payload = {"status": "COMPLETED", "execution": {"complete": True, "hypothesis_assessment": {
        "verdict": verdict, "confidence": None, "controls_passed": True, "protocol": "registered_seed_level_analysis",
        "evidence_summary": {"protocol_sha256": "example_fixture", "scope": "synthetic_control"}}}}
    assert evaluate_run_hypothesis(payload)["verdict"] == verdict
    payload["execution"]["validation_failures"] = ["archive_hash_mismatch"]
    assert evaluate_run_hypothesis(payload)["verdict"] == "invalid"


@pytest.mark.parametrize("invalid_contrast", [float("nan"), float("inf"), True, "0.1"])
def test_time_shift_nonfinite_and_nonnumeric_measurements_are_invalid(invalid_contrast: Any) -> None:
    result = evaluate_run_hypothesis({"status": "COMPLETED", "execution": {"complete": True},
        "diagnostics": {"by_seed": [{"seed": 1, "matrices": [{"mean_contrast": invalid_contrast}]}]}})
    assert result["verdict"] == "invalid"
    assert result["confidence"] is None


def test_missing_metrics_are_not_synthesized_as_zero() -> None:
    result = evaluate_run_hypothesis({"status": "COMPLETED", "execution": {"complete": True, "challenge": "MLS_PRICE", "summary": {}}})
    assert result["verdict"] == "inconclusive"
    assert result["evidence_summary"]["between_term"] is None
    assert result["confidence"] is None


def test_completion_string_cannot_accept_confirmatory_assessment() -> None:
    result = evaluate_run_hypothesis({"status": "COMPLETED", "execution": {"complete": "false", "hypothesis_assessment": {"verdict": "supported", "controls_passed": True}}})
    assert result["verdict"] == "invalid"
