"""Follow-ups from the V4 review: watcher finalization, run-control auth, run trash."""

from __future__ import annotations

import json
import threading
import urllib.error
import urllib.request
from pathlib import Path

import pytest

from codontrace.console import runs, server

# ---------------------------------------------------------------------------
# Watcher: an unexpected exception must still terminalize and release the run.
# ---------------------------------------------------------------------------


class _ExitedProc:
    def __init__(self, code: int = 0) -> None:
        self.code = code

    def wait(self) -> int:
        return self.code

    def poll(self) -> int:
        return self.code


def _watched_run(tmp_path: Path, run_id: str) -> tuple[Path, Path, threading.Event]:
    run_dir = tmp_path / run_id
    engine_dir = run_dir / "output"
    engine_dir.mkdir(parents=True)
    (run_dir / "status.json").write_text(json.dumps({"status": "RUNNING", "pid": 0}), encoding="utf-8")
    event = threading.Event()
    with runs._RUN_LOCK:
        runs._RUN_PROCESSES[run_id] = _ExitedProc()
        runs._RUN_FINALIZERS[run_id] = event
    return run_dir, engine_dir, event


def test_watcher_exception_marks_failed_and_sets_finalizer(tmp_path, monkeypatch):
    run_id = "run_watcher_exc_once"
    run_dir, engine_dir, event = _watched_run(tmp_path, run_id)
    real_write = runs.write_atomic_json
    calls = {"n": 0}

    def flaky_write(path, data):
        calls["n"] += 1
        if calls["n"] == 1:
            raise RuntimeError("disk exploded")
        real_write(path, data)

    monkeypatch.setattr(runs, "write_atomic_json", flaky_write)
    runs._watch_run_process(run_id, _ExitedProc(0), run_dir, engine_dir)

    assert event.is_set()
    assert run_id not in runs._RUN_PROCESSES
    assert run_id not in runs._RUN_FINALIZERS
    status = json.loads((run_dir / "status.json").read_text(encoding="utf-8"))
    assert status["status"] == "FAILED"
    assert "RuntimeError" in status["errorReason"] and "disk exploded" in status["errorReason"]


def test_watcher_releases_run_even_if_status_cannot_be_written(tmp_path, monkeypatch):
    run_id = "run_watcher_exc_always"
    run_dir, engine_dir, event = _watched_run(tmp_path, run_id)

    def broken_write(path, data):
        raise OSError("read-only filesystem")

    monkeypatch.setattr(runs, "write_atomic_json", broken_write)
    runs._watch_run_process(run_id, _ExitedProc(0), run_dir, engine_dir)  # must not raise

    assert event.is_set()
    assert run_id not in runs._RUN_PROCESSES
    assert run_id not in runs._RUN_FINALIZERS


# ---------------------------------------------------------------------------
# Run-mutating endpoints require CODONTRACE_API_TOKEN or a direct loopback caller.
# ---------------------------------------------------------------------------


@pytest.fixture
def console(monkeypatch, tmp_path):
    monkeypatch.setenv("CODONTRACE_RUNS_DIR", str(tmp_path / "runs"))
    monkeypatch.delenv("CODONTRACE_API_TOKEN", raising=False)
    calls: list[tuple[str, object]] = []

    def fake_launch(params):
        calls.append(("launch", params))
        return {"ok": True, "runId": "run_fake"}

    def fake_action(run_id, action, request_id=None):
        calls.append((action, run_id))
        return {"ok": True, "action": action, "run_id": run_id}

    def fake_run_script(name):
        calls.append(("script", name))
        return {"ok": True}

    monkeypatch.setattr(server, "launch_simulation_run", fake_launch)
    monkeypatch.setattr(server, "manage_run_action", fake_action)
    monkeypatch.setattr(server, "run_script", fake_run_script)
    httpd = server.make_server("127.0.0.1", 0)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{httpd.server_port}"

    def request(path, body=None, headers=None):
        req = urllib.request.Request(
            base + path,
            data=None if body is None else json.dumps(body).encode(),
            headers={"Content-Type": "application/json", **(headers or {})},
        )
        try:
            response = urllib.request.urlopen(req, timeout=5)
        except urllib.error.HTTPError as exc:
            response = exc
        with response:
            return response.status, json.load(response)

    try:
        yield request, calls
    finally:
        httpd.shutdown()
        httpd.server_close()


MUTATING = [
    ("/api/runs/launch", {"experiment": "T02"}),
    ("/api/runs/action", {"runId": "run_x", "action": "stop"}),
    ("/api/runs/action", {"runId": "run_x", "action": "delete"}),
    ("/api/runs/run_x/pause", {}),
    ("/api/runs/run_x/resume", {}),
    ("/api/scripts/run", {"name": "x.py"}),
]


@pytest.mark.parametrize("path,body", MUTATING)
def test_remote_run_mutation_without_token_is_forbidden(console, monkeypatch, path, body):
    request, calls = console
    monkeypatch.setattr(server, "_from_this_machine", lambda address: False)
    code, data = request(path, body)
    assert code == 403 and data["ok"] is False
    assert "CODONTRACE_API_TOKEN" in data["error"]
    assert calls == []


def test_forwarded_request_via_loopback_proxy_is_not_treated_as_local(console):
    request, calls = console
    code, _ = request("/api/runs/launch", {"experiment": "T02"}, headers={"X-Forwarded-For": "203.0.113.9"})
    assert code == 403 and calls == []


@pytest.mark.parametrize("path,body", MUTATING)
def test_loopback_run_mutation_is_allowed(console, path, body):
    request, calls = console
    code, data = request(path, body)
    assert code == 200 and data["ok"] is True
    assert len(calls) == 1


def test_remote_with_correct_token_is_allowed_and_wrong_token_rejected(console, monkeypatch):
    request, calls = console
    monkeypatch.setattr(server, "_from_this_machine", lambda address: False)
    monkeypatch.setenv("CODONTRACE_API_TOKEN", "s3cret-usage-token")
    code, _ = request("/api/runs/launch", {"experiment": "T02"}, headers={"Authorization": "Bearer wrong"})
    assert code == 403 and calls == []
    code, data = request("/api/runs/launch", {"experiment": "T02"}, headers={"Authorization": "Bearer s3cret-usage-token"})
    assert code == 200 and data["ok"] is True
    code, data = request(
        "/api/runs/action", {"runId": "run_x", "action": "pause"}, headers={"Authorization": "Bearer s3cret-usage-token"}
    )
    assert code == 200 and data["ok"] is True
    assert [c[0] for c in calls] == ["launch", "pause"]


def test_read_only_run_list_stays_open_to_remote(console, monkeypatch):
    request, _ = console
    monkeypatch.setattr(server, "_from_this_machine", lambda address: False)
    code, data = request("/api/runs")
    assert code == 200 and isinstance(data, list)


# ---------------------------------------------------------------------------
# Delete moves the run to <runs root>/_trash instead of removing it.
# ---------------------------------------------------------------------------


def _finished_run(root: Path, run_id: str) -> Path:
    run_dir = root / run_id
    (run_dir / "output").mkdir(parents=True)
    (run_dir / "status.json").write_text(json.dumps({"status": "COMPLETED", "exitCode": 0}), encoding="utf-8")
    (run_dir / "manifest.json").write_text(json.dumps({"run_id": run_id}), encoding="utf-8")
    (run_dir / "output" / "archive.json").write_text('{"kept": true}', encoding="utf-8")
    return run_dir


def test_delete_moves_run_to_trash_and_hides_it_from_list(tmp_path, monkeypatch):
    root = tmp_path / "runs"
    root.mkdir()
    monkeypatch.setenv("CODONTRACE_RUNS_DIR", str(root))
    run_id = "run_trash_me_1"
    _finished_run(root, run_id)
    assert run_id in {r["id"] for r in runs.list_simulation_runs()}

    result = runs.manage_run_action(run_id, "delete")
    assert result["ok"] is True, result

    listed = {r["id"] for r in runs.list_simulation_runs()}
    assert run_id not in listed and runs.RUN_TRASH_DIRNAME not in listed
    assert not (root / run_id).exists()
    trashed = Path(result["trashPath"])
    assert trashed.parent == root / runs.RUN_TRASH_DIRNAME
    assert trashed.name.startswith(f"{run_id}-")
    assert json.loads((trashed / "output" / "archive.json").read_text(encoding="utf-8")) == {"kept": True}
    info = json.loads((trashed.parent / f"{trashed.name}.trashinfo.json").read_text(encoding="utf-8"))
    assert info["runId"] == run_id

    # The trash folder is not addressable as a run.
    assert runs.validate_run_id(runs.RUN_TRASH_DIRNAME) is None
    assert runs.get_safe_run_dir(runs.RUN_TRASH_DIRNAME) is None

    # Deleting a re-created run with the same id never overwrites the earlier copy.
    _finished_run(root, run_id)
    second = runs.manage_run_action(run_id, "delete")
    assert second["ok"] is True and second["trashPath"] != result["trashPath"]
    assert (trashed / "output" / "archive.json").is_file()
    assert Path(second["trashPath"]).is_dir()


def test_delete_still_refuses_actively_running_run(tmp_path, monkeypatch):
    root = tmp_path / "runs"
    root.mkdir()
    monkeypatch.setenv("CODONTRACE_RUNS_DIR", str(root))
    run_id = "run_trash_busy"
    _finished_run(root, run_id)
    with runs._RUN_LOCK:
        runs._RUN_PROCESSES[run_id] = _ExitedProc()
    try:
        result = runs.manage_run_action(run_id, "delete")
    finally:
        with runs._RUN_LOCK:
            runs._RUN_PROCESSES.pop(run_id, None)
    assert result["status_code"] == 409
    assert (root / run_id).is_dir()
    assert not (root / runs.RUN_TRASH_DIRNAME).exists()
