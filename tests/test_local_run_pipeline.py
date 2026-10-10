"""Behavioral contracts for local pilots, streaming, collisions and console state."""

from __future__ import annotations

import json
import subprocess
import sys
import threading
import time
from pathlib import Path

import pytest

from codontrace.console.runs import (
    build_run_snapshot,
    get_run_details,
    launch_simulation_run,
    list_simulation_runs,
    manage_run_action,
)
from codontrace.experiments.models import AssessmentStatus, CompletionSummary, ExecutionTrack, MetricRecord
from codontrace.experiments.orchestrator import CampaignOrchestrator


class ObservableRunner:
    experiment_id = "T01"
    arm = "NO_SELECTION"
    track = ExecutionTrack.REFERENCE
    population_size = 4
    generations = 4

    def __init__(self, seed=7, fail=False, boundary=None):
        self.seed = seed
        self.fail = fail
        self.boundary = boundary
        self.metrics_history = []

    def run(self, on_generation=None):
        for gen in range(1, self.generations + 1):
            if self.boundary:
                self.boundary(gen)
            if self.fail and gen == 2:
                raise RuntimeError("intentional measurement failure")
            record = MetricRecord(gen, 0, 4, "value", float(gen), {})
            self.metrics_history.append(record)
            on_generation(record)
        return CompletionSummary(
            "T01", self.track, self.seed, 4, 0, "COMPLETED", "HORIZON_REACHED", AssessmentStatus.INCONCLUSIVE, 4.0, {}
        )


@pytest.fixture
def env(tmp_path, monkeypatch):
    root = tmp_path / "simulation_runs"
    monkeypatch.setenv("CODONTRACE_RUNS_DIR", str(root))
    return root


def test_publish_live_before_finish_and_consistent_work(env, tmp_path):
    observed = []

    def inspect_boundary(gen):
        runs = list_simulation_runs()
        assert len(runs) == 1
        detail = get_run_details(runs[0]["id"])
        assert detail["status"] == "RUNNING"
        progress = detail["snapshot"]["progress"]
        assert progress["done"] == gen - 1
        assert progress["pct"] == 100 * (gen - 1) / 4
        assert detail["executionBoundary"]["isGenesisEngine"] is False
        assert len(detail["telemetry"]) == gen - 1
        observed.append(gen)

    orchestrator = CampaignOrchestrator(tmp_path / "campaign", "live")
    orchestrator.run_experiment(ObservableRunner(boundary=inspect_boundary))
    assert observed == [1, 2, 3, 4]
    detail = get_run_details(orchestrator.last_run_dir.name)
    assert detail["snapshot"]["progress"] == {
        "kind": "work_units",
        "stage": "simulation",
        "done": 4.0,
        "total": 4.0,
        "pct": 100.0,
    }
    assert detail["scientificAssessment"] == "INCONCLUSIVE"
    manifest = detail["manifest"]
    assert manifest["source_sha"] != "UNKNOWN"
    assert manifest["params"]["seeds"] == [7]
    assert manifest["params"]["generations"] == 4


def test_sessions_seeds_and_arms_never_overwrite(env, tmp_path):
    first = None
    for campaign in ("one", "two"):
        for seed in (7, 8):
            for arm in ("A", "B"):
                runner = ObservableRunner(seed)
                runner.arm = arm
                orchestrator = CampaignOrchestrator(tmp_path / "campaign", campaign)
                orchestrator.run_experiment(runner)
                if first is None:
                    first = (orchestrator.last_run_dir, (orchestrator.last_run_dir / "metrics.jsonl").read_bytes())
    assert len(list_simulation_runs()) == 8
    assert (first[0] / "metrics.jsonl").read_bytes() == first[1]


def test_exception_keeps_partial_data_and_failed_state(env, tmp_path):
    orchestrator = CampaignOrchestrator(tmp_path / "campaign", "failed")
    with pytest.raises(RuntimeError):
        orchestrator.run_experiment(ObservableRunner(fail=True))
    directory = orchestrator.last_run_dir
    detail = get_run_details(directory.name)
    assert detail["status"] == "FAILED"
    assert len(detail["telemetry"]) == 1
    assert detail["pct"] == 25
    assert not (directory / "COMPLETE").exists()


def test_stub_never_complete(env, tmp_path):
    from codontrace.experiments import T06CausalLedgerRunner

    orchestrator = CampaignOrchestrator(tmp_path / "campaign", "stub")
    summary = orchestrator.run_experiment(T06CausalLedgerRunner(seed=7, generations=4, population_size=4))
    assert summary.status == "FAILED"
    detail = get_run_details(orchestrator.last_run_dir.name)
    assert detail["status"] == "FAILED"
    assert detail["pct"] == 0
    assert not (orchestrator.last_run_dir / "COMPLETE").exists()


def test_stale_execution_complete_cannot_override_failure(env):
    entry = env / "stale_complete"
    entry.mkdir(parents=True)
    (entry / "execution.json").write_text(json.dumps({"runId": entry.name, "complete": True}))
    snapshot = build_run_snapshot(
        entry.name, {"status": "FAILED", "pct": 20}, {"executionBoundary": {"engineBackend": "unknown"}}
    )
    assert snapshot["state"] == "FAILED"
    assert snapshot["capabilities"]["pause"] is False


def test_pause_ack_resume_stop_preserve_partial(env, tmp_path):
    gate = threading.Event()
    continued = threading.Event()

    def boundary(gen):
        if gen == 2:
            gate.set()
            continued.wait(5)

    orchestrator = CampaignOrchestrator(tmp_path / "campaign", "pause")
    results = []
    thread = threading.Thread(
        target=lambda: results.append(orchestrator.run_experiment(ObservableRunner(boundary=boundary)))
    )
    thread.start()
    assert gate.wait(5)
    run_id = orchestrator.last_run_dir.name
    assert manage_run_action(run_id, "pause")["ok"]
    continued.set()
    for _ in range(100):
        if get_run_details(run_id)["status"] == "PAUSED":
            break
        time.sleep(0.02)
    assert get_run_details(run_id)["status"] == "PAUSED"
    assert manage_run_action(run_id, "stop")["ok"]
    thread.join(5)
    assert not thread.is_alive()
    assert results[0].status == "STOPPED"
    assert get_run_details(run_id)["status"] == "STOPPED"
    assert not (orchestrator.last_run_dir / "COMPLETE").exists()


def test_readiness_reflects_reference_and_real_engine_routes():
    from codontrace.campaigns.readiness import inventory, render_readiness_markdown

    rows = {row["experiment_id"]: row for row in inventory()["experiments"]}
    for n in range(1, 6):
        row = rows[f"T{n:02}"]
        assert row["backend"] == "REFERENCE"
        assert row["run_enabled"] and not row["long_campaign_ready"]
    assert rows["T11"]["launch_params"]["scriptName"] == "board_long_campaign.py"
    assert all(not rows[f"T{n:02}"]["run_enabled"] for n in (6, 7, 8, 9, 10, 12))
    assert Path("docs/campaigns/T01_T12_READINESS.md").read_text() == render_readiness_markdown()


def test_launcher_validation_and_real_reference_process(env):
    assert (
        launch_simulation_run({"scriptName": "genesis_long_board_campaign.py", "experiment": "T06", "workers": 1})["ok"]
        is False
    )
    assert (
        launch_simulation_run({"scriptName": "genesis_long_board_campaign.py", "experiment": "T01", "workers": 2})["ok"]
        is False
    )
    response = launch_simulation_run(
        {
            "scriptName": "genesis_long_board_campaign.py",
            "experiment": "T02",
            "workers": 1,
            "population": 16,
            "generations": 3,
            "seeds": [19],
        }
    )
    assert response["ok"], response
    for _ in range(250):
        detail = get_run_details(response["runId"])
        if detail["status"] in ("COMPLETED", "FAILED", "STOPPED"):
            break
        time.sleep(0.02)
    assert detail["status"] == "COMPLETED", detail
    assert detail["snapshot"]["progress"]["done"] == 3
    assert len(list_simulation_runs()) == 1


def test_t11_launch_uses_actual_calibration(env):
    response = launch_simulation_run(
        {
            "scriptName": "board_long_campaign.py",
            "experiment": "T11",
            "ticks": 2,
            "population": 4,
            "workers": 1,
            "seeds": [7],
        }
    )
    assert response["ok"], response
    for _ in range(250):
        detail = get_run_details(response["runId"])
        if detail["status"] in ("COMPLETED", "FAILED", "STOPPED"):
            break
        time.sleep(0.02)
    assert detail["status"] == "COMPLETED", detail
    assert detail["executionBoundary"]["isGenesisEngine"] is True
    assert not detail["capabilities"]["pause"]
    assert detail["snapshot"]["progress"]["done"] == 2


def test_cli_rejects_unknown_and_stub():
    for experiment in ("INVALID", "T06"):
        proc = subprocess.run(
            [sys.executable, "scripts/genesis_long_board_campaign.py", "--experiment", experiment], capture_output=True
        )
        assert proc.returncode != 0


def test_reference_ensemble_extinction_is_valid_endpoint(env, tmp_path):
    from codontrace.experiments import T04ContingencyRunner

    runner = T04ContingencyRunner(seed=42, generations=10, population_size=8, replay_branches=2, replay_generations=3)
    orchestrator = CampaignOrchestrator(tmp_path / "campaign", "ensemble")
    result = orchestrator.run_experiment(runner)
    assert result.status == "COMPLETED"
    detail = get_run_details(orchestrator.last_run_dir.name)
    progress = detail["snapshot"]["progress"]
    assert progress["done"] == progress["total"] == result.completed_generations
    assert progress["pct"] == 100
    assert detail["manifest"]["params"]["generations"] == 10
    assert result.summary_metrics["exact_replay_passed"]
    assert len((orchestrator.last_run_dir / "metrics.jsonl").read_text().splitlines()) == result.completed_generations


def test_partial_export_hashes_match_exact_archived_bytes(env):
    import hashlib
    import zipfile

    from codontrace.console.runs import generate_run_zip_file

    entry = env / "paused_export"
    entry.mkdir(parents=True)
    (entry / "status.json").write_text(json.dumps({"status": "PAUSED"}))
    (entry / "metrics.jsonl").write_text('{"generation":1}\n')
    path, manifest = generate_run_zip_file(entry.name)
    try:
        assert manifest["isPartialSnapshot"]
        with zipfile.ZipFile(path) as archive:
            for record in manifest["files"]:
                content = archive.read(record["path"])
                assert hashlib.sha256(content).hexdigest() == record["sha256"]
                assert len(content) == record["size"]
    finally:
        path.unlink()


def test_fractional_and_boolean_configuration_is_rejected(env):
    from codontrace.console.runs import parse_seeds

    for values in ([1.5], True, 1.9):
        with pytest.raises(ValueError):
            parse_seeds(values)
    for generations in (True, 1.5):
        assert not launch_simulation_run({"generations": generations})["ok"]


def test_active_clock_freezes_during_acknowledged_pause_and_resumes(env, tmp_path):
    gate = threading.Event()
    continued = threading.Event()

    def boundary(gen):
        if gen == 2:
            gate.set()
            continued.wait(5)

    orchestrator = CampaignOrchestrator(tmp_path / "campaign", "pause_clock")
    orchestrator.heartbeat_seconds = 0.025
    results = []
    thread = threading.Thread(
        target=lambda: results.append(orchestrator.run_experiment(ObservableRunner(boundary=boundary)))
    )
    thread.start()
    assert gate.wait(5)
    run_id = orchestrator.last_run_dir.name
    assert manage_run_action(run_id, "pause")["ok"]
    continued.set()
    for _ in range(100):
        if get_run_details(run_id)["status"] == "PAUSED":
            break
        time.sleep(0.01)
    first = get_run_details(run_id)["snapshot"]
    assert first["state"] == "PAUSED"
    time.sleep(0.2)
    second = get_run_details(run_id)["snapshot"]
    assert second["state"] == "PAUSED"
    assert second["active_elapsed_seconds"] <= first["active_elapsed_seconds"] + 0.03
    assert second["paused_seconds"] >= first["paused_seconds"] + 0.15
    assert second["progress"] == first["progress"]
    assert manage_run_action(run_id, "resume")["ok"]
    thread.join(5)
    assert not thread.is_alive()
    assert results[0].status == "COMPLETED"
    assert get_run_details(run_id)["snapshot"]["paused_seconds"] >= 0.15


def test_active_time_budget_stops_at_boundary_without_false_completion(env, tmp_path):
    orchestrator = CampaignOrchestrator(tmp_path / "campaign", "budget", max_seconds=0.25)
    runner = ObservableRunner(boundary=lambda generation: time.sleep(0.30))
    summary = orchestrator.run_experiment(runner)
    assert summary.status == "STOPPED"
    assert summary.stop_reason == "TIME_BUDGET"
    assert summary.completed_generations == 1
    assert not (orchestrator.last_run_dir / "COMPLETE").exists()
    assert len(get_run_details(orchestrator.last_run_dir.name)["telemetry"]) == 1


def test_t11_sealed_completion_precedes_status_flush_without_progress_race(env):
    folder=env/'t11_sealing'
    folder.mkdir(parents=True)
    manifest={'params':{'scriptName':'board_long_campaign.py','ticks':2,'workers':1,'seeds':[7]},'engineBackend':'genesis_engine'}
    (folder/'run_manifest.json').write_text(json.dumps(manifest))
    report={'runId':'t11_sealing','complete':True,'summary':{'experiment_id':'T11','track':'ENGINE','summary_metrics':{'validity':'COMPLETE','finished_ticks':2,'target_ticks':2}}}
    (folder/'execution.json').write_text(json.dumps(report))
    old={'status':'RUNNING','params':manifest['params'],'work_done':1,'work_total':2}
    snapshot=build_run_snapshot('t11_sealing',old,manifest)
    assert snapshot['state']=='COMPLETED'
    assert snapshot['progress']['done']==2
    assert snapshot['progress']['pct']==100
    assert old['work_done']==1
    report['summary']['summary_metrics']['finished_ticks']=1
    (folder/'execution.json').write_text(json.dumps(report))
    invalid=build_run_snapshot('t11_sealing',old,manifest)
    assert invalid['progress']['done']==1
