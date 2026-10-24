"""Concurrent status.json writers keep progress and revision monotonic.

A run's heartbeat (``orchestrator._persist_locked``) and the console's
pause/resume handlers both read-modify-write ``status.json``. Without a shared
lock the console can write back a copy it read before the last heartbeat,
moving ``work_done`` and ``revision`` backwards (CI run 39689564062,
tests/test_local_run_actions_http.py:86, ``257.0 == 256.0``). These tests run
both kinds of writer at once, in threads and in separate processes, while a
monitor checks that neither value ever decreases.
"""

from __future__ import annotations

import json
import multiprocessing as mp
import sys
import threading
import time
from pathlib import Path
from typing import Any

import pytest

from codontrace.console.runs import write_status_json

_TESTS_DIR = Path(__file__).resolve().parent


@pytest.fixture
def spawn_safe_path(monkeypatch: pytest.MonkeyPatch) -> None:
    """Put the tests directory after the standard library for spawned children.

    A spawned child receives a copy of the parent's sys.path. pytest puts
    tests/ first, and tests/platform would then shadow the stdlib platform
    module that uuid imports. Moving tests/ to the end keeps this module
    importable by name while the stdlib wins.
    """

    def under_tests(entry: str) -> bool:
        try:
            return Path(entry or ".").resolve() == _TESTS_DIR
        except OSError:
            return False

    head = [e for e in sys.path if not under_tests(e)]
    tail = [e for e in sys.path if under_tests(e)]
    monkeypatch.setattr(sys, "path", head + tail)


HEARTBEATS = 400


def _read(path: Path) -> dict[str, Any] | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) else None


def _heartbeat(path: str) -> None:
    status: dict[str, Any] = {"status": "RUNNING", "revision": 0, "work_done": 0, "work_total": HEARTBEATS, "pct": 0.0}
    for done in range(1, HEARTBEATS + 1):
        status["revision"] += 1
        status["work_done"] = done
        status["pct"] = 100.0 * done / HEARTBEATS
        write_status_json(Path(path), status)


def _console(path: str) -> None:
    target = Path(path)
    stop_file = target.with_name("STOP_CONSOLES")
    flip = 0
    while not stop_file.exists():
        snapshot = _read(target)
        if snapshot is None:
            continue
        time.sleep(0.0005)  # the window in which a heartbeat lands
        flip ^= 1
        snapshot["status"] = "PAUSED" if flip else "RUNNING"
        snapshot["revision"] = int(snapshot.get("revision", 0)) + 1
        write_status_json(target, snapshot)


def _monitor(path: Path, stop: threading.Event, seen: list[tuple[int, float]]) -> None:
    while not stop.is_set():
        data = _read(path)
        if data is not None:
            seen.append((int(data["revision"]), float(data["work_done"])))


def _assert_monotonic(seen: list[tuple[int, float]], path: Path) -> None:
    assert seen, "monitor saw no status"
    revs = [r for r, _ in seen]
    done = [d for _, d in seen]
    rev_drops = sum(1 for a, b in zip(revs, revs[1:]) if b < a)
    done_drops = sum(1 for a, b in zip(done, done[1:]) if b < a)
    assert (rev_drops, done_drops) == (0, 0), f"revision fell {rev_drops}x, work_done fell {done_drops}x"
    final = _read(path)
    assert final is not None and final["work_done"] == HEARTBEATS


def _run(tmp_path: Path, start: Any) -> None:
    path = tmp_path / "status.json"
    write_status_json(path, {"status": "RUNNING", "revision": 1, "work_done": 0, "work_total": HEARTBEATS, "pct": 0.0})
    stop = threading.Event()
    seen: list[tuple[int, float]] = []
    mon = threading.Thread(target=_monitor, args=(path, stop, seen))
    mon.start()
    try:
        start(str(path))
    finally:
        stop.set()
        mon.join()
    _assert_monotonic(seen, path)


def _drive(path: str, workers: list[Any], heartbeat: Any) -> None:
    for w in workers:
        w.start()
    heartbeat.start()
    heartbeat.join(timeout=120)
    time.sleep(0.2)  # a few more console writes after the last heartbeat
    Path(path).with_name("STOP_CONSOLES").touch()
    for w in workers:
        w.join(timeout=30)


def test_threads_never_move_status_backwards(tmp_path: Path) -> None:
    def start(path: str) -> None:
        consoles = [threading.Thread(target=_console, args=(path,)) for _ in range(3)]
        _drive(path, consoles, threading.Thread(target=_heartbeat, args=(path,)))

    _run(tmp_path, start)


def test_processes_never_move_status_backwards(tmp_path: Path, spawn_safe_path: None) -> None:
    ctx = mp.get_context("spawn")

    def start(path: str) -> None:
        consoles = [ctx.Process(target=_console, args=(path,)) for _ in range(3)]
        hb = ctx.Process(target=_heartbeat, args=(path,))
        _drive(path, consoles, hb)
        assert hb.exitcode == 0
        assert all(p.exitcode == 0 for p in consoles)

    _run(tmp_path, start)


def _lock_holder(lock: str, ready: str, release: str) -> None:
    from codontrace.console.runs import _status_file_lock

    with _status_file_lock(Path(lock)):
        Path(ready).touch()
        deadline = time.monotonic() + 30
        while not Path(release).exists() and time.monotonic() < deadline:
            time.sleep(0.01)


def test_lock_times_out_instead_of_hanging(tmp_path: Path, spawn_safe_path: None) -> None:
    from codontrace.console.runs import StatusLockTimeout, _status_file_lock

    lock, ready, release = tmp_path / "s.lock", tmp_path / "ready", tmp_path / "release"
    p = mp.get_context("spawn").Process(target=_lock_holder, args=(str(lock), str(ready), str(release)))
    p.start()
    try:
        deadline = time.monotonic() + 60
        while not ready.exists() and time.monotonic() < deadline:
            time.sleep(0.01)
        assert ready.exists()
        t0 = time.monotonic()
        with pytest.raises(StatusLockTimeout):
            with _status_file_lock(lock, timeout=0.3):
                pass
        assert time.monotonic() - t0 < 10
    finally:
        release.touch()
        p.join(timeout=30)
    with _status_file_lock(lock, timeout=5):
        pass


def test_reentrant_lock_raises(tmp_path: Path) -> None:
    from codontrace.console.runs import _status_file_lock

    lock = tmp_path / "s.lock"
    with _status_file_lock(lock):
        with pytest.raises(RuntimeError, match="re-entrant"):
            with _status_file_lock(lock, timeout=0.2):
                pass
    with _status_file_lock(lock, timeout=1):
        pass


def test_heartbeat_cannot_unpause_while_pause_marker_exists(tmp_path: Path) -> None:
    from codontrace.console.runs import CONSOLE_STATUS_FIELDS, write_status_json

    f = tmp_path / "status.json"
    write_status_json(f, {"status": "RUNNING", "revision": 1, "work_done": 5, "work_total": 10, "pct": 50.0})
    (tmp_path / "PAUSE").touch()
    stale = {"status": "PAUSED", "revision": 1, "work_done": 4, "work_total": 10, "pct": 40.0}
    write_status_json(f, stale, fields=CONSOLE_STATUS_FIELDS)
    on_disk = json.loads(f.read_text(encoding="utf-8"))
    assert on_disk["status"] == "PAUSED" and on_disk["work_done"] == 5 and on_disk["pct"] == 50.0
    write_status_json(f, {"status": "RUNNING", "revision": 2, "work_done": 5, "work_total": 10})
    assert json.loads(f.read_text(encoding="utf-8"))["status"] == "PAUSED"
    (tmp_path / "PAUSE").unlink()
    write_status_json(f, {"status": "RUNNING", "revision": 9, "work_done": 6, "work_total": 10})
    assert json.loads(f.read_text(encoding="utf-8"))["status"] == "RUNNING"


def test_reconcile_holds_root_lock(tmp_path: Path) -> None:
    """A reconcile must wait for (and not write past) another holder of the root lock."""
    from codontrace.console import runs as R

    (tmp_path / "output").mkdir()
    root = tmp_path / "status.json"
    root.write_text(json.dumps({"status": "RUNNING", "revision": 1, "work_done": 1}))
    (tmp_path / "output" / "status.json").write_text(json.dumps({"status": "PAUSED", "revision": 3, "work_done": 7}))
    adapter = R.CustomScriptRunnerAdapter()
    held, release = threading.Event(), threading.Event()

    def holder() -> None:
        with R._status_file_lock(R.status_lock_path(root)):
            held.set()
            release.wait(10)

    t = threading.Thread(target=holder)
    t.start()
    held.wait(10)
    old_timeout = R.STATUS_LOCK_TIMEOUT_S
    R.STATUS_LOCK_TIMEOUT_S = 0.3
    try:
        t0 = time.monotonic()
        adapter.reconcile_status(tmp_path)
        waited = time.monotonic() - t0
        before_release = json.loads(root.read_text())
    finally:
        R.STATUS_LOCK_TIMEOUT_S = old_timeout
        release.set()
        t.join(10)
    assert waited >= 0.25, "reconcile did not wait for the root lock"
    assert before_release["revision"] == 1 and before_release["work_done"] == 1, "reconcile wrote without the lock"
    merged = adapter.reconcile_status(tmp_path)
    assert merged["status"] == "PAUSED" and merged["work_done"] == 7


def test_stop_marker_keeps_stopping_and_stopped(tmp_path: Path) -> None:
    f = tmp_path / "status.json"
    for terminal in ("STOPPING", "STOPPED"):
        write_status_json(f, {"status": terminal, "revision": 1, "work_done": 3})
        (tmp_path / "STOP").touch()
        for live in ("RUNNING", "RESUMING", "PAUSING", "PAUSED"):
            write_status_json(f, {"status": live, "revision": 1, "work_done": 3})
            assert json.loads(f.read_text())["status"] == terminal, (terminal, live)
        write_status_json(f, {"status": "STOPPED", "revision": 1, "work_done": 3})
        assert json.loads(f.read_text())["status"] == "STOPPED"
        (tmp_path / "STOP").unlink()
        write_status_json(f, {"status": "RUNNING", "revision": 1, "work_done": 3})
        assert json.loads(f.read_text())["status"] == "RUNNING"
        f.unlink()


@pytest.mark.parametrize("act", ["pause", "resume"])
def test_console_action_does_not_write_back_stale_progress(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, act: str
) -> None:
    """Forced interleaving: a heartbeat lands between the handler's read and its write."""
    from codontrace.console import runs as R

    d = tmp_path / "run1"
    d.mkdir()
    sf = d / "status.json"
    caps = {"pause": True, "resume": True, "stop": True}
    start = "PAUSED" if act == "resume" else "RUNNING"
    sf.write_text(
        json.dumps(
            {
                "status": start,
                "revision": 10,
                "work_done": 100,
                "work_total": 1000,
                "pct": 10.0,
                "pid": 1,
                "capabilities": caps,
            }
        )
    )
    if act == "resume":
        (d / "PAUSE").write_text("x")
    heartbeat = {
        "status": start,
        "revision": 50,
        "work_done": 200,
        "work_total": 1000,
        "pct": 20.0,
        "heartbeat_at": 123.0,
        "pid": 1,
        "capabilities": caps,
    }
    monkeypatch.setattr(R, "get_safe_run_dir", lambda run_id, must_exist=False: d)
    monkeypatch.setattr(R, "_run_pid_alive", lambda *a, **k: True)
    fired: list[int] = []
    orig_atomic, orig_ws = R.write_atomic_json, R.write_status_json

    def inject() -> None:
        if not fired:
            fired.append(1)
            orig_atomic(sf, heartbeat)

    def wrapped_ws(path: Path, data: dict[str, Any], **kw: Any) -> dict[str, Any]:
        if Path(path) == sf:
            inject()
        return orig_ws(path, data, **kw)

    monkeypatch.setattr(R, "write_status_json", wrapped_ws)
    R.manage_run_action("run1", act)
    final = json.loads(sf.read_text())
    assert fired
    assert final["work_done"] == 200 and final["pct"] == 20.0 and final["revision"] > 50
    assert final.get("heartbeat_at") == 123.0, "console wrote back fields it does not own"


def test_status_lock_timeout_in_console_write_is_not_fatal(tmp_path: Path) -> None:
    from codontrace.console import runs as R

    f = tmp_path / "status.json"
    write_status_json(f, {"status": "RUNNING", "revision": 1})
    old = R.STATUS_LOCK_TIMEOUT_S
    R.STATUS_LOCK_TIMEOUT_S = 0.2
    try:
        with R._status_file_lock(R.status_lock_path(f)):
            done = []
            t = threading.Thread(
                target=lambda: done.append(R.console_write_status(f, {"status": "PAUSING"}, R.CONSOLE_STATUS_FIELDS))
            )
            t.start()
            t.join(10)
    finally:
        R.STATUS_LOCK_TIMEOUT_S = old
    assert done == [False]
    assert json.loads(f.read_text())["status"] == "RUNNING"


def _report_platform(out: str) -> None:
    import platform

    Path(out).write_text(str(getattr(platform, "__file__", "")), encoding="utf-8")


def test_spawned_child_uses_stdlib_platform(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys, "path", [str(_TESTS_DIR), *sys.path])
    # Same fixture logic as spawn_safe_path, applied after tests/ was pushed first.
    head = [e for e in sys.path if Path(e or ".").resolve() != _TESTS_DIR]
    monkeypatch.setattr(sys, "path", head + [str(_TESTS_DIR)])
    out = tmp_path / "platform.txt"
    p = mp.get_context("spawn").Process(target=_report_platform, args=(str(out),))
    p.start()
    p.join(60)
    assert p.exitcode == 0
    assert _TESTS_DIR not in Path(out.read_text(encoding="utf-8")).resolve().parents


def test_replace_waits_out_a_busy_target_on_windows(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from codontrace.console import runs as R

    src, dst = tmp_path / "a", tmp_path / "b"
    attempts: list[int] = []

    def busy_then_ok(a: Any, b: Any) -> None:
        attempts.append(1)
        if len(attempts) <= 8:  # longer than the old 5 x 50 ms budget allowed
            raise PermissionError(13, "Access is denied")
        src.rename(dst)

    src.write_text("x")
    monkeypatch.setattr(R.os, "replace", busy_then_ok)
    monkeypatch.setattr(R.os, "name", "nt")
    R._replace_with_retry(src, dst)
    assert len(attempts) == 9 and dst.read_text() == "x"

    def denied(a: Any, b: Any) -> None:
        raise PermissionError(13, "Access is denied")

    monkeypatch.setattr(R.os, "replace", denied)
    monkeypatch.setattr(R, "ATOMIC_REPLACE_TIMEOUT_S", 0.1)
    with pytest.raises(PermissionError):
        R._replace_with_retry(src, dst)
