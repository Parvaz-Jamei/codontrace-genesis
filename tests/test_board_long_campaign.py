"""T11 calibration is real. The other eleven experiments are not relabelled."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from codontrace.campaigns.analyst import analyse, control_assessment
from codontrace.campaigns.board_runner import CampaignRejected, resume, run_uninterrupted
from codontrace.campaigns.readiness import assessments_are_distinct, inventory, render_readiness_markdown

ROOT = Path(__file__).resolve().parents[1]


def test_not_supported_is_not_falsified() -> None:
    assert assessments_are_distinct("NOT_SUPPORTED", "FALSIFIED_IN_MODEL")
    assert assessments_are_distinct("INCONCLUSIVE", "NOT_SUPPORTED")
    assert assessments_are_distinct("INVALID_MEASUREMENT", "FALSIFIED_IN_MODEL")


def test_only_the_pilot_is_runnable() -> None:
    rows = {row["experiment_id"]: row for row in inventory()["experiments"]}
    assert set(rows) == {f"T{number:02d}" for number in range(1, 13)}
    assert rows["T11"]["status"] == "آمادهٔ پایلوت"
    assert rows["T11"]["run_enabled"] is False
    assert rows["T11"]["backend"] == "ENGINE"
    assert all(row["run_enabled"] is False for row in rows.values())
    assert rows["T05"]["status"] == "نیازمند اتصال"
    text = (ROOT / "docs" / "campaigns" / "T01_T12_READINESS.md").read_text(encoding="utf-8")
    assert text == render_readiness_markdown()


def test_positive_control_is_visible_and_excluded() -> None:
    assert (
        control_assessment(
            {
                "synthetic": True,
                "kind": "positive",
                "experiment_id": "T11",
                "predicted": "digest",
                "observed": "digest",
                "matched": True,
            }
        )
        == "SUPPORTED_IN_THIS_MODEL"
    )
    assert control_assessment({"synthetic": True, "kind": "positive", "matched": False}) == "INVALID_MEASUREMENT"


def test_refuses_an_unready_experiment(tmp_path: Path) -> None:
    from codontrace.campaigns.board_runner import main

    code = main(
        [
            "run",
            "--experiment",
            "T01",
            "--seed",
            "7",
            "--arm",
            "uninterrupted",
            "--ticks",
            "4",
            "--population",
            "6",
            "--output",
            str(tmp_path),
        ]
    )
    assert code == 2


def test_workers_follow_the_machine_not_a_fixed_four(tmp_path: Path) -> None:
    with pytest.raises(CampaignRejected, match="allowed CPUs"):
        run_uninterrupted(output=tmp_path, seed=7, ticks=4, population=6, workers=10_000)


def test_calibration_resume_matches_and_a_forged_hash_is_rejected(tmp_path: Path) -> None:
    run_uninterrupted(output=tmp_path, seed=7, ticks=2, population=4, workers=1)
    checkpoint = tmp_path / "runs" / "T11" / "seed_7" / "arm_uninterrupted" / "checkpoints" / "mid.bin"
    resume(output=tmp_path, checkpoint=checkpoint, seed=7, ticks=2, population=4, workers=1)
    (tmp_path / "SYNTHETIC_CONTROL").mkdir()
    (tmp_path / "SYNTHETIC_CONTROL" / "positive.json").write_text(
        json.dumps(
            {
                "synthetic": True,
                "kind": "positive",
                "experiment_id": "T11",
                "predicted": "same-digest",
                "observed": "same-digest",
                "matched": True,
            }
        ),
        encoding="utf-8",
    )
    # A flattering flag in the runner file must not become the scientific result.
    completion = tmp_path / "runs" / "T11" / "seed_7" / "arm_resume" / "completion.json"
    payload = json.loads(completion.read_text(encoding="utf-8"))
    payload["scientific_status"] = "SUPPORTED_IN_THIS_MODEL"
    completion.write_text(json.dumps(payload), encoding="utf-8")
    report = analyse(tmp_path)
    assert report["resume_matched"] is True
    assert report["engineering_status"] == "COMPLETE"
    assert report["scientific_status"] == "UNASSESSED"
    assert report["control_assessment"] == "SUPPORTED_IN_THIS_MODEL"
    assert report["synthetic_excluded"] is True

    broken = tmp_path / "broken"
    broken.mkdir()
    # Reuse the good tree's metric, then lie about its hash.
    source = tmp_path / "runs"
    target = broken / "runs"
    target.parent.mkdir(exist_ok=True)
    import shutil

    shutil.copytree(source, target)
    (broken / "manifest.json").write_text((tmp_path / "manifest.json").read_text(encoding="utf-8"), encoding="utf-8")
    metric = broken / "runs" / "T11" / "seed_7" / "arm_resume" / "metrics.jsonl"
    metric.write_text(metric.read_text(encoding="utf-8").replace("ENGINE", "REFERENCE"), encoding="utf-8")
    forged = analyse(broken)
    assert forged["scientific_status"] == "INVALID_MEASUREMENT"
    assert any("hash" in problem or "digest" in problem for problem in forged["problems"])


def test_incomplete_checkpoint_is_rejected(tmp_path: Path) -> None:
    checkpoint = tmp_path / "empty.bin"
    checkpoint.write_bytes(b"")
    with pytest.raises(CampaignRejected, match="incomplete checkpoint"):
        resume(output=tmp_path, checkpoint=checkpoint, seed=7, ticks=2, population=4)
    checkpoint.write_bytes(b'{"record_role":"nope"}')
    with pytest.raises(CampaignRejected, match="incompatible or incomplete checkpoint"):
        resume(output=tmp_path / "again", checkpoint=checkpoint, seed=7, ticks=2, population=4)
