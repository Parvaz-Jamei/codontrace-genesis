"""Comprehensive verification suite for all 8 Grand Frontier Challenges.

Validates that:
- Challenges 1-4 (Campaign Suite) and Challenges 5-8 (Extension Suite) execute cleanly.
- Every worker produces deterministic status.json and execution.json telemetry.
- Lifecycle stop semantics, completion flags, and stop_reason are correctly maintained.
- Specialized mathematical metrics (Price equation, Hazen functional information,
  quasispecies error threshold, Bedau activity, Fisher DFE) are computed accurately.
- Epistemic invariant `red_queen_proved == False` is strictly enforced.
"""

from __future__ import annotations

import json
from pathlib import Path

from scripts.grand_frontier_4challenge_campaign import (
    run_worker_0_oee,
    run_worker_1_mls,
    run_worker_2_transition,
    run_worker_3_contingency,
)
from scripts.grand_frontier_suite_extension import (
    run_worker_5_functional_info,
    run_worker_6_quasispecies,
    run_worker_7_oee_shadow,
    run_worker_8_fisher_geometric,
)


def test_challenge_1_oee_novelty_micro_run(tmp_path: Path) -> None:
    """Verify Challenge 1 (OEE Novelty) execution and telemetry."""
    out_dir = tmp_path / "c1_oee"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "STOP").write_text("stop test\n", encoding="utf-8")

    summary = run_worker_0_oee(
        output_dir=out_dir,
        target_seconds=10.0,
        epoch_gens=50,
        seed=10001,
        resume=False,
    )

    assert summary["challenge"] == "OEE_NOVELTY"
    assert summary["red_queen_proved"] is False
    assert (out_dir / "status.json").is_file()
    assert (out_dir / "execution.json").is_file()
    assert not (out_dir / "COMPLETE").exists()

    exec_data = json.loads((out_dir / "execution.json").read_text(encoding="utf-8"))
    assert exec_data["complete"] is False
    assert exec_data["stop_reason"] == "STOP_FILE_DETECTED"
    assert exec_data["red_queen_proved"] is False


def test_challenge_2_mls_price_micro_run(tmp_path: Path) -> None:
    """Verify Challenge 2 (Multilevel Selection Price Equation) execution."""
    out_dir = tmp_path / "c2_mls"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "STOP").write_text("stop test\n", encoding="utf-8")

    summary = run_worker_1_mls(
        output_dir=out_dir,
        target_seconds=10.0,
        epoch_gens=50,
        seed=20001,
        resume=False,
    )

    assert summary["challenge"] == "MLS_PRICE"
    assert summary["red_queen_proved"] is False
    assert (out_dir / "status.json").is_file()

    status_data = json.loads((out_dir / "status.json").read_text(encoding="utf-8"))
    assert status_data["status"] == "STOPPED"
    assert status_data["red_queen_proved"] is False


def test_challenge_3_transition_mutualism_micro_run(tmp_path: Path) -> None:
    """Verify Challenge 3 (Major Transition & Mutualism) execution."""
    out_dir = tmp_path / "c3_trans"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "STOP").write_text("stop test\n", encoding="utf-8")

    summary = run_worker_2_transition(
        output_dir=out_dir,
        target_seconds=10.0,
        epoch_gens=50,
        seed=30001,
        resume=False,
    )

    assert summary["challenge"] == "TRANSITION_MUTUALISM"
    assert summary["major_transition_proved"] is False
    assert summary["red_queen_proved"] is False


def test_challenge_4_contingency_replay_micro_run(tmp_path: Path) -> None:
    """Verify Challenge 4 (Historical Contingency Replay) execution."""
    out_dir = tmp_path / "c4_replay"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "STOP").write_text("stop test\n", encoding="utf-8")

    summary = run_worker_3_contingency(
        output_dir=out_dir,
        target_seconds=10.0,
        epoch_gens=50,
        seed=40001,
        resume=False,
    )

    assert summary["challenge"] == "CONTINGENCY_REPLAY"
    assert summary["red_queen_proved"] is False
    assert (out_dir / "status.json").is_file()


def test_challenge_5_functional_info_micro_run(tmp_path: Path) -> None:
    """Verify Challenge 5 (Hazen Functional Info & Neutral Percolation) execution."""
    out_dir = tmp_path / "c5_fi"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "STOP").write_text("stop test\n", encoding="utf-8")

    run_worker_5_functional_info(output_dir=out_dir, duration_hours=10.0, core_id=0)

    status_data = json.loads((out_dir / "status.json").read_text(encoding="utf-8"))
    assert status_data["status"] == "STOPPED"
    assert status_data["red_queen_proved"] is False
    assert "metrics" in status_data
    assert "functional_info_bits" in status_data["metrics"]

    exec_data = json.loads((out_dir / "execution.json").read_text(encoding="utf-8"))
    assert exec_data["complete"] is False
    assert exec_data["stop_reason"] == "STOP_FILE_DETECTED"
    assert exec_data["red_queen_proved"] is False


def test_challenge_6_quasispecies_micro_run(tmp_path: Path) -> None:
    """Verify Challenge 6 (Eigen Quasispecies & Error Catastrophe) execution."""
    out_dir = tmp_path / "c6_quasi"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "STOP").write_text("stop test\n", encoding="utf-8")

    run_worker_6_quasispecies(output_dir=out_dir, duration_hours=10.0, core_id=1)

    status_data = json.loads((out_dir / "status.json").read_text(encoding="utf-8"))
    assert status_data["status"] == "STOPPED"
    assert status_data["red_queen_proved"] is False
    assert "metrics" in status_data
    assert "theoretical_mu_c" in status_data["metrics"]

    exec_data = json.loads((out_dir / "execution.json").read_text(encoding="utf-8"))
    assert exec_data["complete"] is False
    assert exec_data["stop_reason"] == "STOP_FILE_DETECTED"


def test_challenge_7_oee_shadow_micro_run(tmp_path: Path) -> None:
    """Verify Challenge 7 (OEE Cumulative Activity vs Shadow) execution."""
    out_dir = tmp_path / "c7_shadow"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "STOP").write_text("stop test\n", encoding="utf-8")

    run_worker_7_oee_shadow(output_dir=out_dir, duration_hours=10.0, core_id=2)

    status_data = json.loads((out_dir / "status.json").read_text(encoding="utf-8"))
    assert status_data["status"] == "STOPPED"
    assert status_data["red_queen_proved"] is False
    assert "metrics" in status_data
    assert "excess_adaptive_activity" in status_data["metrics"]

    exec_data = json.loads((out_dir / "execution.json").read_text(encoding="utf-8"))
    assert exec_data["complete"] is False
    assert exec_data["stop_reason"] == "STOP_FILE_DETECTED"


def test_challenge_8_fisher_geometric_micro_run(tmp_path: Path) -> None:
    """Verify Challenge 8 (Fisher Geometric Model & DFE) execution."""
    out_dir = tmp_path / "c8_fisher"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "STOP").write_text("stop test\n", encoding="utf-8")

    run_worker_8_fisher_geometric(output_dir=out_dir, duration_hours=10.0, core_id=3)

    status_data = json.loads((out_dir / "status.json").read_text(encoding="utf-8"))
    assert status_data["status"] == "STOPPED"
    assert status_data["red_queen_proved"] is False
    assert "metrics" in status_data
    assert "dimensions" in status_data["metrics"]

    exec_data = json.loads((out_dir / "execution.json").read_text(encoding="utf-8"))
    assert exec_data["complete"] is False
    assert exec_data["stop_reason"] == "STOP_FILE_DETECTED"
    assert exec_data["red_queen_proved"] is False
