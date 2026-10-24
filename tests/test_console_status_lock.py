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
import threading
import time
from pathlib import Path
from typing import Any

from codontrace.console.runs import write_status_json

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


def test_processes_never_move_status_backwards(tmp_path: Path) -> None:
    ctx = mp.get_context("spawn")

    def start(path: str) -> None:
        consoles = [ctx.Process(target=_console, args=(path,)) for _ in range(3)]
        hb = ctx.Process(target=_heartbeat, args=(path,))
        _drive(path, consoles, hb)
        assert hb.exitcode == 0
        assert all(p.exitcode == 0 for p in consoles)

    _run(tmp_path, start)
