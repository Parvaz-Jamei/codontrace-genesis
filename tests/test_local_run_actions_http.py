"""Real two-process HTTP tests for per-card lifecycle and PID isolation."""

from __future__ import annotations

import hashlib
import json
import os
import threading
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor

import pytest

from codontrace.console import runs, server


def test_two_real_cards_pause_resume_stop_restart_and_remove_are_isolated(tmp_path, monkeypatch):
    monkeypatch.setenv("CODONTRACE_RUNS_DIR", str(tmp_path / "runs"))
    httpd = server.make_server("127.0.0.1", 0)
    serving = threading.Thread(target=httpd.serve_forever, daemon=True)
    serving.start()
    base = f"http://127.0.0.1:{httpd.server_port}"
    created = []

    def request(path, body=None):
        req = urllib.request.Request(
            base + path,
            data=None if body is None else json.dumps(body).encode(),
            headers={"Content-Type": "application/json"},
        )
        try:
            response = urllib.request.urlopen(req, timeout=5)
        except urllib.error.HTTPError as exc:
            response = exc
        with response:
            return response.status, json.load(response)

    def detail(run_id):
        code, data = request(f"/api/runs/{run_id}")
        assert code == 200
        return data

    def until(run_id, predicate):
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline:
            value = detail(run_id)
            if predicate(value):
                return value
            time.sleep(0.02)
        pytest.fail(f"Timed out: {value}")

    def action(run_id, act):
        return request("/api/runs/action", {"runId": run_id, "action": act})

    try:
        for seed in (301, 302):
            code, launched = request(
                "/api/runs/launch",
                {
                    "scriptName": "genesis_long_board_campaign.py",
                    "experiment": "T02",
                    "generations": 10000,
                    "population": 64,
                    "seeds": [seed],
                    "workers": 1,
                    "budget": 120,
                    "title": "identical_title",
                },
            )
            assert code == 200 and launched["ok"], launched
            created.append(launched["runId"])
        first, second = created
        assert first != second
        a = until(first, lambda d: d["snapshot"]["progress"]["done"] >= 2)
        b = until(second, lambda d: d["snapshot"]["progress"]["done"] >= 2)
        assert a["statusData"]["pid"] != b["statusData"]["pid"]
        code, rejected = action(second, "delete")
        assert code == 409 and not rejected["ok"]
        assert action(first, "pause")[1]["ok"]
        paused = until(first, lambda d: d["status"] == "PAUSED")
        paused_done = paused["snapshot"]["progress"]["done"]
        b_done = detail(second)["snapshot"]["progress"]["done"]
        until(second, lambda d: d["snapshot"]["progress"]["done"] > b_done + 2)
        assert detail(first)["snapshot"]["progress"]["done"] == paused_done
        assert action(first, "resume")[1]["ok"]
        until(first, lambda d: d["status"] == "RUNNING" and d["snapshot"]["progress"]["done"] > paused_done)
        assert action(first, "stop")[1]["ok"]
        until(first, lambda d: d["status"] == "STOPPED")
        until(first, lambda d: not runs.is_pid_alive(d["statusData"]["pid"]))
        assert detail(second)["status"] == "RUNNING"
        # Raw history from the stopped run is preserved by fresh replay restart.
        stopped_metrics = runs.get_safe_run_dir(first) / "metrics.jsonl"
        digest = hashlib.sha256(stopped_metrics.read_bytes()).hexdigest()
        def keyed_restart(_):
            return request("/api/runs/action", {"runId": first, "action": "restart", "requestId": "same-restart-attempt"})
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(keyed_restart, (0, 1)))
        assert all(code == 200 and data["ok"] for code, data in results), results
        code, restarted = results[0]
        assert results[1][1]["runId"] == restarted["runId"]
        assert any(data.get("idempotent_replay") is True for _, data in results)
        new_id = restarted["runId"]
        created.append(new_id)
        assert new_id not in (first, second)
        until(new_id, lambda d: d["snapshot"]["progress"]["done"] >= 1)
        assert hashlib.sha256(stopped_metrics.read_bytes()).hexdigest() == digest
        parent = json.loads((runs.get_safe_run_dir(new_id) / "restart_provenance.json").read_text())
        assert parent["parentRunId"] == first
        assert action(first, "remove")[1]["ok"]
        assert runs.get_safe_run_dir(first, must_exist=True) is None
        assert detail(second)["status"] == "RUNNING"
        assert detail(new_id)["status"] == "RUNNING"
    finally:
        for run_id in created:
            if runs.get_safe_run_dir(run_id, must_exist=True) is not None:
                action(run_id, "stop")
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            with runs._RUN_LOCK:
                alive = [runs._RUN_PROCESSES.get(run_id) for run_id in created]
            if not any(p is not None and p.poll() is None for p in alive):
                break
            time.sleep(0.02)
        httpd.shutdown()
        httpd.server_close()
        serving.join(5)


def test_external_paused_pid_cannot_be_deleted_or_unverified_signal(tmp_path, monkeypatch):
    monkeypatch.setenv("CODONTRACE_RUNS_DIR", str(tmp_path / "runs"))
    entry = runs.runs_directory() / "external_paused"
    entry.mkdir()
    (entry / "status.json").write_text(
        json.dumps({"status": "PAUSED", "pid": os.getpid(), "capabilities": {"pause": True, "resume": True}})
    )
    assert runs.manage_run_action(entry.name, "delete")["status_code"] == 409
    result = runs.manage_run_action(entry.name, "stop")
    assert not result["ok"]
    assert result["error_code"] == "UNVERIFIED_PROCESS_IDENTITY"
    assert entry.exists() and runs.is_pid_alive(os.getpid())
    assert not (entry / "STOP").exists()


def test_recycled_pid_is_not_mistaken_for_the_old_run(tmp_path, monkeypatch):
    monkeypatch.setenv("CODONTRACE_RUNS_DIR", str(tmp_path / "runs"))
    entry = runs.runs_directory() / "recycled_pid"
    entry.mkdir()
    (entry / "status.json").write_text(json.dumps({"status": "RUNNING", "pid": os.getpid()}))
    (entry / "process_identity.json").write_text(
        json.dumps({"pid": os.getpid(), "start_ticks": "wrong", "boot_id": "wrong"})
    )
    if runs._process_identity(os.getpid()) is None:
        pytest.skip("OS does not provide a process incarnation token")
    assert not runs._run_pid_alive(os.getpid(), entry)
    assert runs.get_run_details(entry.name)["status"] == "STOPPED"
    assert runs.is_pid_alive(os.getpid())


@pytest.mark.parametrize(
    "experiment,population,configuration,arm",
    [
        ("T02", 16, {"num_demes": 4, "group_selection": False, "high_migration": True}, "HIGH_MIGRATION"),
        ("T03", 8, {"vertical_transmission_rate": 0.42, "cooperation_cost": 0.31}, "VERTICAL"),
        (
            "T04",
            8,
            {"replay_branches": 2, "replay_generations": 3, "history_count": 2, "snapshot_generations": [0, 2]},
            "CONTINGENCY_REPLAY",
        ),
    ],
)
def test_restart_preserves_model_configuration(tmp_path, monkeypatch, experiment, population, configuration, arm):
    monkeypatch.setenv("CODONTRACE_RUNS_DIR", str(tmp_path / "runs"))
    response = runs.launch_simulation_run(
        {
            "scriptName": "genesis_long_board_campaign.py",
            "experiment": experiment,
            "generations": 4,
            "population": population,
            "arm": arm,
            "seeds": [44],
            "workers": 1,
            "runner_config": configuration,
            "budget": None,
        }
    )
    assert response["ok"], response

    def wait_terminal(run_id):
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            detail = runs.get_run_details(run_id)
            with runs._RUN_LOCK:
                proc = runs._RUN_PROCESSES.get(run_id)
            if detail["status"] in ("COMPLETED", "FAILED", "STOPPED") and (proc is None or proc.poll() is not None):
                return detail
            time.sleep(0.02)
        pytest.fail(f"Not terminal: {detail}")

    original = wait_terminal(response["runId"])
    assert original["status"] == "COMPLETED", original
    restarted = runs.manage_run_action(response["runId"], "restart")
    assert restarted["ok"], restarted
    copied = wait_terminal(restarted["runId"])
    assert copied["status"] == "COMPLETED", copied
    for detail in (original, copied):
        params = detail["manifest"]["params"]
        assert params["population"] == population
        assert params["arm"] == arm
        assert params["generations"] == 4
        assert params["seeds"] == [44]
        assert params["budget"] is None
        for key, value in configuration.items():
            assert params["runner_config"][key] == value
    assert (
        original["execution"]["summary"]["primary_endpoint_value"]
        == copied["execution"]["summary"]["primary_endpoint_value"]
    )
