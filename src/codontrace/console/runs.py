"""Cross-platform discovery and monitoring of simulation runs for the console.

Standard library only. Does not import the evolution engine.
Works on Windows, Linux, and macOS.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import signal
import subprocess
import sys
import threading
import time
import uuid
from pathlib import Path
from typing import Any

_RUN_PROCESSES: dict[str, subprocess.Popen[Any]] = {}
_RUN_LOCK = threading.Lock()


def validate_run_id(run_id: str) -> str | None:
    """Validate run identifier to prevent path traversal and unsafe characters."""
    if not isinstance(run_id, str):
        return None
    clean = run_id.strip()
    if not clean or len(clean) > 128:
        return None
    if not re.fullmatch(r"^[a-zA-Z0-9_\-]+$", clean):
        return None
    if ".." in clean or "/" in clean or "\\" in clean:
        return None
    return clean


def get_safe_run_dir(run_id: str, must_exist: bool = False) -> Path | None:
    """Resolve and enforce that the target run directory stays strictly within runs_directory()."""
    valid_id = validate_run_id(run_id)
    if not valid_id:
        return None
    root = runs_directory().resolve()
    target = (root / valid_id).resolve()
    try:
        target.relative_to(root)
    except ValueError:
        return None
    if must_exist and not target.is_dir():
        return None
    return target


def write_atomic_json(path: Path, data: dict[str, Any]) -> None:
    """Safely write JSON using an atomic replace to avoid partial/corrupt files."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_file = path.with_name(f"{path.name}.tmp.{uuid.uuid4().hex[:6]}")
    temp_file.write_text(json.dumps(data, indent=2, allow_nan=False), encoding="utf-8")
    os.replace(temp_file, path)


def runs_directory() -> Path:
    """Find the simulation runs directory across different environments."""
    custom = os.environ.get("CODONTRACE_RUNS_DIR", "").strip()
    if custom:
        p = Path(custom).expanduser()
        p.mkdir(parents=True, exist_ok=True)
        return p

    # Local project directory
    local = Path("simulation_runs").resolve()
    if local.is_dir():
        return local

    # User home directory (typical on Linux SBC / desktop)
    home_runs = Path.home() / "simulation_runs"
    if home_runs.is_dir():
        return home_runs

    # Fallback to local
    local.mkdir(parents=True, exist_ok=True)
    return local


def tail_file(path: Path, max_lines: int = 50) -> list[str]:
    """Read tail lines from a file efficiently."""
    if not path.is_file():
        return []
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        return lines[-max_lines:]
    except OSError:
        return []


def list_simulation_runs() -> list[dict[str, Any]]:
    """Enumerate discovered simulation runs."""
    root = runs_directory()
    if not root.is_dir():
        return []

    runs = []
    try:
        entries = sorted(root.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True)
    except OSError:
        return []

    for entry in entries:
        if not entry.is_dir():
            continue

        run_id = entry.name
        status_file = entry / "status.json"
        live_log = entry / "live.log"
        console_log = entry / "console.log"

        status_info: dict[str, Any] = {}
        if status_file.is_file():
            try:
                status_info = json.loads(status_file.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                pass

        # Determine status
        st = status_info.get("status")
        if not st:
            if (entry / "COMPLETE").is_file() or (entry / "REPORT.md").is_file():
                st = "COMPLETED"
            elif live_log.is_file() and (time.time() - live_log.stat().st_mtime < 120):
                st = "RUNNING"
            else:
                st = "INACTIVE"

        seeds_dir = entry / "by_seed"
        seed_count = len(list(seeds_dir.glob("seed*"))) if seeds_dir.is_dir() else 0

        logs = tail_file(live_log, 15) or tail_file(console_log, 15)

        runs.append({
            "id": run_id,
            "title": run_id.replace("_", " ").title(),
            "status": st,
            "path": str(entry),
            "pct": status_info.get("pct", 100.0 if st == "COMPLETED" else 0.0),
            "completedSeeds": status_info.get("completed_seeds", seed_count),
            "totalSeeds": status_info.get("total_seeds", max(12, seed_count)),
            "mtime": entry.stat().st_mtime,
            "recentLogs": logs,
        })

    return runs


def get_run_details(run_id: str) -> dict[str, Any] | None:
    """Retrieve full details and recent logs of a specific run with containment validation."""
    entry = get_safe_run_dir(run_id, must_exist=True)
    if entry is None:
        return None

    status_file = entry / "status.json"
    status_info: dict[str, Any] = {}
    if status_file.is_file():
        try:
            status_info = json.loads(status_file.read_text(encoding="utf-8"))
            if not isinstance(status_info, dict):
                status_info = {}
        except (OSError, ValueError):
            pass

    live_log = entry / "live.log"
    console_log = entry / "console.log"

    return {
        "id": run_id,
        "title": run_id.replace("_", " ").title(),
        "status": status_info.get("status", "UNKNOWN"),
        "statusData": status_info,
        "liveLogs": tail_file(live_log, 100),
        "consoleLogs": tail_file(console_log, 100),
    }


def send_signal_to_run(run_id: str, sig_name: str) -> bool:
    """Send pause/resume signal directly to the run's registered process."""
    entry = get_safe_run_dir(run_id, must_exist=True)
    if entry is None:
        return False

    with _RUN_LOCK:
        proc = _RUN_PROCESSES.get(run_id)

    pid: int | None = proc.pid if proc and proc.poll() is None else None
    if pid is None:
        pid_file = entry / "run.pid"
        if pid_file.is_file():
            try:
                pid = int(pid_file.read_text(encoding="utf-8").strip())
            except (ValueError, OSError):
                pid = None

    if pid is None:
        return False

    sig_upper = sig_name.upper()
    if sys.platform == "win32":
        if sig_upper == "STOP":
            (entry / "STOP").write_text("paused by console\n", encoding="utf-8")
            return True
        elif sig_upper == "CONT":
            stop_marker = entry / "STOP"
            if stop_marker.is_file():
                try:
                    stop_marker.unlink()
                except OSError:
                    pass
            return True
        return False

    sig = signal.SIGSTOP if sig_upper == "STOP" else signal.SIGCONT
    try:
        os.kill(pid, sig)
        return True
    except OSError:
        return False


def get_run_zip(run_id: str) -> bytes | None:
    """Create an in-memory zip archive of a simulation run directory with strict containment."""
    entry = get_safe_run_dir(run_id, must_exist=True)
    if entry is None:
        return None

    import io
    import zipfile

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for file_path in entry.rglob("*"):
            if file_path.is_file():
                try:
                    file_path.relative_to(entry)
                except ValueError:
                    continue
                if file_path.stat().st_size < 25 * 1024 * 1024:
                    arcname = file_path.relative_to(entry)
                    zf.write(file_path, str(arcname))
    buf.seek(0)
    return buf.getvalue()


def manage_run_action(run_id: str, action: str) -> dict[str, Any]:
    """Execute lifecycle action on a simulation run with containment and process ownership."""
    valid_id = validate_run_id(run_id)
    if not valid_id:
        return {"ok": False, "error": "Invalid run ID or path traversal attempt", "status_code": 400}

    entry = get_safe_run_dir(run_id, must_exist=True)
    if entry is None:
        return {"ok": False, "error": f"Run '{run_id}' not found", "status_code": 200}

    act = action.lower().strip()
    if act == "pause":
        ok = send_signal_to_run(run_id, "STOP")
        return {"ok": ok, "action": "pause", "run_id": run_id}
    elif act == "resume":
        ok = send_signal_to_run(run_id, "CONT")
        return {"ok": ok, "action": "resume", "run_id": run_id}
    elif act == "stop":
        (entry / "STOP").write_text("stopped by console\n", encoding="utf-8")
        with _RUN_LOCK:
            proc = _RUN_PROCESSES.get(run_id)
        stopped = False
        if proc and proc.poll() is None:
            try:
                proc.terminate()
                proc.wait(timeout=2.0)
            except (subprocess.TimeoutExpired, OSError):
                try:
                    proc.kill()
                except OSError:
                    pass
            stopped = True
        else:
            pid_file = entry / "run.pid"
            if pid_file.is_file():
                try:
                    pid = int(pid_file.read_text(encoding="utf-8").strip())
                    if sys.platform == "win32":
                        subprocess.run(["taskkill", "/F", "/PID", str(pid)], capture_output=True, timeout=5)
                    else:
                        os.kill(pid, signal.SIGTERM)
                    stopped = True
                except (ValueError, OSError, subprocess.SubprocessError):
                    pass

        status_file = entry / "status.json"
        if status_file.is_file():
            try:
                st_info = json.loads(status_file.read_text(encoding="utf-8"))
                if isinstance(st_info, dict):
                    st_info["status"] = "STOPPED"
                    st_info["stoppedAt"] = time.time()
                    write_atomic_json(status_file, st_info)
            except Exception:
                pass

        return {"ok": stopped, "action": "stop", "run_id": run_id}
    elif act == "delete":
        with _RUN_LOCK:
            proc = _RUN_PROCESSES.get(run_id)
            if proc and proc.poll() is None:
                return {
                    "ok": False,
                    "error": "Cannot delete an actively running simulation. Stop it first.",
                    "status_code": 409,
                }

        status_file = entry / "status.json"
        if status_file.is_file():
            try:
                raw_st = json.loads(status_file.read_text(encoding="utf-8"))
                if isinstance(raw_st, dict) and raw_st.get("status") == "RUNNING":
                    live_log = entry / "live.log"
                    if live_log.is_file() and (time.time() - live_log.stat().st_mtime < 30):
                        return {
                            "ok": False,
                            "error": "Simulation is actively running. Stop it before deleting.",
                            "status_code": 409,
                        }
            except Exception:
                pass

        try:
            shutil.rmtree(entry)
            with _RUN_LOCK:
                _RUN_PROCESSES.pop(run_id, None)
            return {"ok": True, "action": "delete", "run_id": run_id}
        except OSError as e:
            return {"ok": False, "error": str(e), "status_code": 500}

    return {"ok": False, "error": f"Unknown action '{action}'", "status_code": 400}


def launch_simulation_run(params: dict[str, Any]) -> dict[str, Any]:
    """Launch a simulation run in the background with validation and collision safety."""
    if not isinstance(params, dict):
        return {"ok": False, "error": "Invalid params: expected JSON object", "status_code": 400}

    raw_gen = params.get("generations", 10)
    try:
        generations = int(raw_gen)
        if generations < 1 or generations > 100000:
            return {"ok": False, "error": "generations must be an integer between 1 and 100000", "status_code": 400}
    except (TypeError, ValueError):
        return {"ok": False, "error": "generations must be a valid integer", "status_code": 400}

    raw_workers = params.get("workers", 2)
    try:
        workers = int(raw_workers)
        if workers < 1 or workers > 16:
            return {"ok": False, "error": "workers must be an integer between 1 and 16", "status_code": 400}
    except (TypeError, ValueError):
        return {"ok": False, "error": "workers must be a valid integer", "status_code": 400}

    title = str(params.get("title") or "custom_run").strip()[:40]
    clean_title = "".join(c if c.isalnum() or c in ("-", "_") else "_" for c in title).lower() or "run"
    ts = time.strftime("%Y%m%d_%H%M%S")
    uid = uuid.uuid4().hex[:8]
    run_id = f"run_{clean_title}_{ts}_{uid}"
    out_dir = runs_directory() / run_id
    out_dir.mkdir(parents=True, exist_ok=True)

    status_file = out_dir / "status.json"
    status_info = {
        "status": "RUNNING",
        "title": title,
        "startedAt": time.time(),
        "params": {
            "generations": generations,
            "workers": workers,
            "title": title,
        },
    }
    write_atomic_json(status_file, status_info)

    script_name = params.get("scriptName")
    repo_root = Path(__file__).resolve().parents[3]
    cmd = [sys.executable]

    if script_name:
        if not isinstance(script_name, str) or not script_name.endswith(".py") or Path(script_name).name != script_name:
            return {"ok": False, "error": "Invalid scriptName", "status_code": 400}
        script_path = repo_root / "scripts" / script_name
        if not script_path.is_file():
            script_path = repo_root / "custom_tests" / script_name
        if script_path.is_file():
            cmd.extend([str(script_path), "--output", str(out_dir)])
        else:
            return {"ok": False, "error": f"Script {script_name} not found", "status_code": 404}
    else:
        engine_script = repo_root / "scripts" / "rq_full_engine_parallel.py"
        if engine_script.is_file():
            cmd.extend([
                str(engine_script),
                "--output", str(out_dir),
                "--generations", str(generations),
                "--workers", str(workers),
            ])
        else:
            cmd.extend(["-m", "codontrace.console", "--help"])

    log_path = out_dir / "console.log"
    with open(log_path, "w", encoding="utf-8") as log_fp:
        proc = subprocess.Popen(cmd, stdout=log_fp, stderr=subprocess.STDOUT, cwd=str(repo_root))

    with _RUN_LOCK:
        _RUN_PROCESSES[run_id] = proc

    (out_dir / "run.pid").write_text(f"{proc.pid}\n", encoding="utf-8")

    return {
        "ok": True,
        "runId": run_id,
        "pid": proc.pid,
        "path": str(out_dir),
    }

