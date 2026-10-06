"""Cross-platform discovery and monitoring of simulation runs for the console.

Standard library only. Does not import the evolution engine.
Works on Windows, Linux, and macOS.
"""

from __future__ import annotations

import json
import os
import signal
import sys
import time
from pathlib import Path
from typing import Any


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
    """Retrieve full details and recent logs of a specific run."""
    root = runs_directory()
    entry = root / run_id
    if not entry.is_dir():
        return None

    status_file = entry / "status.json"
    status_info = {}
    if status_file.is_file():
        try:
            status_info = json.loads(status_file.read_text(encoding="utf-8"))
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
    """Send SIGSTOP or SIGCONT to run processes on POSIX systems."""
    if sys.platform == "win32":
        return False

    sig = signal.SIGSTOP if sig_name.upper() == "STOP" else signal.SIGCONT

    # Find matching processes via /proc or pgrep
    try:
        import subprocess
        out = subprocess.check_output(["pgrep", "-f", run_id], text=True, timeout=5)
        pids = [int(p.strip()) for p in out.splitlines() if p.strip()]
        for pid in pids:
            try:
                os.kill(pid, sig)
            except OSError:
                pass
        return bool(pids)
    except (subprocess.SubprocessError, OSError):
        return False


def get_run_zip(run_id: str) -> bytes | None:
    """Create an in-memory zip archive of a simulation run directory."""
    root = runs_directory()
    entry = root / run_id
    if not entry.is_dir():
        return None

    import io
    import zipfile

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for file_path in entry.rglob("*"):
            if file_path.is_file():
                if file_path.stat().st_size < 25 * 1024 * 1024:
                    arcname = file_path.relative_to(entry)
                    zf.write(file_path, str(arcname))
    buf.seek(0)
    return buf.getvalue()


def manage_run_action(run_id: str, action: str) -> dict[str, Any]:
    """Execute lifecycle action on a simulation run."""
    act = action.lower().strip()
    root = runs_directory()
    entry = root / run_id
    if not entry.is_dir():
        return {"ok": False, "error": f"Run '{run_id}' not found"}

    if act == "pause":
        ok = send_signal_to_run(run_id, "STOP")
        return {"ok": ok, "action": "pause", "run_id": run_id}
    elif act == "resume":
        ok = send_signal_to_run(run_id, "CONT")
        return {"ok": ok, "action": "resume", "run_id": run_id}
    elif act == "stop":
        if sys.platform == "win32":
            import subprocess
            try:
                subprocess.run(["taskkill", "/F", "/FI", f"WINDOWTITLE eq *{run_id}*"], capture_output=True, timeout=5)
            except Exception:
                pass
        else:
            import subprocess
            try:
                subprocess.run(["pkill", "-f", run_id], capture_output=True, timeout=5)
            except Exception:
                pass
        return {"ok": True, "action": "stop", "run_id": run_id}
    elif act == "delete":
        import shutil
        try:
            shutil.rmtree(entry)
            return {"ok": True, "action": "delete", "run_id": run_id}
        except OSError as e:
            return {"ok": False, "error": str(e)}

    return {"ok": False, "error": f"Unknown action '{action}'"}


def launch_simulation_run(params: dict[str, Any]) -> dict[str, Any]:
    """Launch a simulation run in the background."""
    title = str(params.get("title") or "custom_run").strip()
    clean_title = "".join(c if c.isalnum() or c in ("-", "_") else "_" for c in title).lower()
    ts = time.strftime("%Y%m%d_%H%M%S")
    run_id = f"run_{clean_title}_{ts}"
    out_dir = runs_directory() / run_id
    out_dir.mkdir(parents=True, exist_ok=True)

    status_file = out_dir / "status.json"
    status_info = {
        "status": "RUNNING",
        "title": title,
        "startedAt": time.time(),
        "params": params,
    }
    status_file.write_text(json.dumps(status_info, indent=2), encoding="utf-8")

    script_name = params.get("scriptName")
    generations = int(params.get("generations") or 10)
    workers = int(params.get("workers") or 2)

    import subprocess
    repo_root = Path(__file__).resolve().parents[3]

    cmd = [sys.executable]
    if script_name:
        script_path = repo_root / "scripts" / script_name
        if not script_path.is_file():
            script_path = repo_root / "custom_tests" / script_name
        if script_path.is_file():
            cmd.extend([str(script_path), "--output", str(out_dir)])
        else:
            return {"ok": False, "error": f"Script {script_name} not found"}
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

    return {
        "ok": True,
        "runId": run_id,
        "pid": proc.pid,
        "path": str(out_dir),
    }

