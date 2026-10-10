"""Cross-platform discovery and monitoring of simulation runs for the console.

Standard library only. Does not import the evolution engine.
Works on Windows, Linux, and macOS.
"""

from __future__ import annotations

import datetime
import hashlib
import json
import math
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
_RUN_FINALIZERS: dict[str, threading.Event] = {}
_RUN_LOCK = threading.Lock()
_RUN_ACTION_LOCKS: dict[str, Any] = {}


def is_pid_alive(pid: int) -> bool:
    """Check if process with given PID is currently active across platforms."""
    if pid <= 0:
        return False
    if sys.platform == "win32":
        try:
            import ctypes

            loader: Any = getattr(ctypes, "windll", None)
            if loader is None:
                return True
            kernel32: Any = getattr(loader, "kernel32", None)
            if kernel32 is None:
                return True
            from ctypes import wintypes
            kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
            kernel32.OpenProcess.restype = wintypes.HANDLE
            kernel32.GetExitCodeProcess.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]
            kernel32.GetExitCodeProcess.restype = wintypes.BOOL
            kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
            kernel32.CloseHandle.restype = wintypes.BOOL
            process_query_limited_information = 0x1000
            synchronize = 0x00100000
            handle = kernel32.OpenProcess(process_query_limited_information | synchronize, False, pid)
            if not handle:
                return False
            exit_code = ctypes.c_ulong()
            kernel32.GetExitCodeProcess(handle, ctypes.byref(exit_code))
            kernel32.CloseHandle(handle)
            return bool(exit_code.value == 259)  # STILL_ACTIVE
        except Exception:
            return False
    else:
        try:
            os.kill(pid, 0)
            return True
        except OSError as err:
            import errno

            return err.errno == errno.EPERM


def get_allowed_cpu_ids() -> list[int]:
    """Return sorted list of CPU core IDs allowed for this process across platforms."""
    get_affinity = getattr(os, "sched_getaffinity", None)
    if callable(get_affinity):
        try:
            aff = get_affinity(0)
            if aff:
                return sorted(int(x) for x in aff)
        except OSError:
            pass
    if sys.platform == "win32":
        try:
            import ctypes

            loader: Any = getattr(ctypes, "windll", None)
            if loader is not None:
                kernel32: Any = getattr(loader, "kernel32", None)
                if kernel32 is not None:
                    process_mask = ctypes.c_uint64()
                    system_mask = ctypes.c_uint64()
                    cur_proc = kernel32.GetCurrentProcess()
                    if kernel32.GetProcessAffinityMask(cur_proc, ctypes.byref(process_mask), ctypes.byref(system_mask)):
                        mask_val = int(process_mask.value)
                        if mask_val > 0:
                            cpus = [i for i in range(64) if (mask_val & (1 << i))]
                            if cpus:
                                return cpus
        except Exception:
            pass
    count = os.cpu_count() or 1
    if count < 1:
        count = 1
    return list(range(count))


def apply_windows_affinity(proc_or_pid: Any, cores: list[int]) -> bool:
    """Apply 64-bit CPU affinity mask to a Windows process using SetProcessAffinityMask."""
    if not cores or sys.platform != "win32":
        return False
    try:
        import ctypes

        loader: Any = getattr(ctypes, "windll", None)
        if loader is None:
            return False
        kernel32: Any = getattr(loader, "kernel32", None)
        if kernel32 is None:
            return False
        mask = 0
        for c in cores:
            if 0 <= c < 64:
                mask |= (1 << c)
        if mask == 0:
            return False
        affinity_mask = ctypes.c_uint64(mask)
        kernel32.SetProcessAffinityMask.argtypes = [ctypes.c_void_p, ctypes.c_uint64]
        kernel32.SetProcessAffinityMask.restype = ctypes.c_int

        handle = getattr(proc_or_pid, "_handle", None)
        if handle is not None:
            return bool(kernel32.SetProcessAffinityMask(ctypes.c_void_p(int(handle)), affinity_mask))

        pid = getattr(proc_or_pid, "pid", proc_or_pid)
        if isinstance(pid, int) and pid > 0:
            process_set_information = 0x0200
            h = kernel32.OpenProcess(process_set_information, False, pid)
            if h:
                try:
                    return bool(kernel32.SetProcessAffinityMask(h, affinity_mask))
                finally:
                    kernel32.CloseHandle(h)
        return False
    except Exception:
        return False


def _process_identity(pid: int) -> dict[str, Any] | None:
    """Identify a process incarnation so a recycled PID cannot own an old card."""
    if pid <= 0:
        return None
    if sys.platform == "linux":
        try:
            stat = Path(f"/proc/{pid}/stat").read_text(encoding="utf-8")
            start_ticks = stat.rsplit(")", 1)[1].split()[19]
            boot_id = Path("/proc/sys/kernel/random/boot_id").read_text(encoding="utf-8").strip()
            return {"pid": pid, "start_ticks": start_ticks, "boot_id": boot_id}
        except (OSError, IndexError):
            return None
    if sys.platform == "win32":
        try:
            import ctypes
            from ctypes import wintypes
            loader: Any = getattr(ctypes, "windll", None)
            kernel32: Any = getattr(loader, "kernel32", None)
            if kernel32 is None:
                return None
            kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
            kernel32.OpenProcess.restype = wintypes.HANDLE
            kernel32.GetProcessTimes.argtypes = [wintypes.HANDLE, *([ctypes.POINTER(wintypes.FILETIME)] * 4)]
            kernel32.GetProcessTimes.restype = wintypes.BOOL
            kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
            kernel32.CloseHandle.restype = wintypes.BOOL
            handle = kernel32.OpenProcess(0x1000, False, pid)
            if not handle:
                return None
            creation, exit_time, kernel, user = (wintypes.FILETIME() for _ in range(4))
            try:
                if not kernel32.GetProcessTimes(handle, ctypes.byref(creation), ctypes.byref(exit_time), ctypes.byref(kernel), ctypes.byref(user)):
                    return None
                created = (int(creation.dwHighDateTime) << 32) | int(creation.dwLowDateTime)
                return {"pid": pid, "creation_time": created}
            finally:
                kernel32.CloseHandle(handle)
        except (OSError, AttributeError):
            return None
    return None


def _run_pid_alive(pid: int, entry: Path) -> bool:
    """Respect a recorded process incarnation when reconciling card liveness."""
    if not is_pid_alive(pid):
        return False
    identity_file = entry / "process_identity.json"
    if identity_file.is_file():
        try:
            recorded = json.loads(identity_file.read_text(encoding="utf-8"))
            current = _process_identity(pid)
            if isinstance(recorded, dict) and current is not None:
                return recorded == current
        except (OSError, ValueError):
            pass
    return True


def _native_process_is_owned(pid: int | None, status: dict[str, Any], manifest: dict[str, Any]) -> bool:
    if not isinstance(pid, int) or pid <= 0:
        return False
    recorded = status.get("process_identity") or manifest.get("process_identity")
    return isinstance(recorded, dict) and recorded == _process_identity(pid)


def parse_seeds(val: Any) -> list[int]:
    """Parse and validate seeds from a list, int, or string."""
    seeds: list[int] = []
    if isinstance(val, int) and not isinstance(val, bool):
        s = int(val)
        if s >= 0:
            return [s]
        raise ValueError("Seed must be non-negative")
    elif isinstance(val, list):
        for item in val:
            if isinstance(item, int) and not isinstance(item, bool):
                s = int(item)
                if s < 0:
                    raise ValueError(f"Seed {s} must be non-negative")
                seeds.append(s)
            elif isinstance(item, str) and item.strip().isdigit():
                seeds.append(int(item.strip()))
            else:
                raise ValueError(f"Invalid seed value: {item!r}")
    elif isinstance(val, str):
        val = val.strip()
        if ".." in val:
            parts = val.split("..", 1)
            if parts[0].strip().isdigit() and parts[1].strip().isdigit():
                start, end = int(parts[0].strip()), int(parts[1].strip())
                if end < start or (end - start) > 1000:
                    raise ValueError("Invalid seed range")
                seeds = list(range(start, end + 1))
            else:
                raise ValueError("Invalid seed range format")
        else:
            tokens = [t.strip() for t in re.split(r"[,;\s]+", val) if t.strip()]
            for token in tokens:
                if token.isdigit():
                    seeds.append(int(token))
                else:
                    raise ValueError(f"Invalid seed token: {token!r}")
    if not seeds:
        raise ValueError("No valid seeds provided")
    if len(seeds) != len(set(seeds)):
        raise ValueError("Duplicate seeds provided")
    return seeds


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
    try:
        temp_file.write_text(json.dumps(data, indent=2, allow_nan=False), encoding="utf-8")
        # On Windows, os.replace can fail momentarily if another reader has the target file open.
        for attempt in range(5):
            try:
                os.replace(temp_file, path)
                break
            except OSError:
                if attempt == 4:
                    raise
                time.sleep(0.05)
    finally:
        if temp_file.is_file():
            try:
                temp_file.unlink()
            except OSError:
                pass



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


def tail_file(path: Path, max_lines: int = 50, max_bytes: int = 65536) -> list[str]:
    """Read tail lines from a file efficiently using seek-from-end without loading entire file."""
    if not path.is_file():
        return []
    try:
        file_size = path.stat().st_size
        if file_size == 0:
            return []
        read_size = min(file_size, max_bytes)
        with path.open("rb") as f:
            f.seek(file_size - read_size)
            chunk = f.read(read_size)
        text = chunk.decode("utf-8", errors="replace")
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        return lines[-max_lines:]
    except OSError:
        return []



class RunnerAdapter:
    """Base adapter for simulation runners, providing output resolution and status reconciliation."""
    backend: str = "custom_script"
    primary_output_dir: str = "output"
    supports_pause: bool = False
    supports_resume: bool = False
    supports_checkpoint: bool = False

    def resolve_status_file(self, run_dir: Path) -> Path:
        return run_dir / "status.json"

    def resolve_capabilities(self, run_dir: Path | None = None) -> dict[str, bool]:
        return {
            "pause": self.supports_pause,
            "resume": self.supports_resume,
            "checkpoint_continue": self.supports_checkpoint,
        }

    def reconcile_status(self, run_dir: Path) -> dict[str, Any]:
        """Reconcile nested output/status.json into root status.json atomically if newer."""
        root_status_file = run_dir / "status.json"
        nested_status_file = run_dir / self.primary_output_dir / "status.json"
        root_data: dict[str, Any] = {}
        nested_data: dict[str, Any] = {}

        if root_status_file.is_file():
            try:
                loaded = json.loads(root_status_file.read_text(encoding="utf-8"))
                if isinstance(loaded, dict):
                    root_data = loaded
            except (OSError, ValueError):
                pass

        if nested_status_file.is_file():
            try:
                loaded = json.loads(nested_status_file.read_text(encoding="utf-8"))
                if isinstance(loaded, dict):
                    nested_data = loaded
            except (OSError, ValueError):
                pass

        if nested_data:
            nested_rev = int(nested_data.get("revision", 0))
            root_rev = int(root_data.get("revision", 0))
            nested_mtime = nested_status_file.stat().st_mtime
            root_mtime = root_status_file.stat().st_mtime if root_status_file.is_file() else 0.0

            if nested_rev > root_rev or (nested_rev == root_rev and nested_mtime > root_mtime) or not root_data:
                merged = {**root_data, **nested_data}
                merged["revision"] = max(nested_rev, root_rev)
                try:
                    write_atomic_json(root_status_file, merged)
                except Exception:
                    pass
                return merged

        return root_data

    def resolve_status_data(self, run_dir: Path) -> dict[str, Any]:
        """Resolve and reconcile authoritative status data for run_dir."""
        return self.reconcile_status(run_dir)

    def resolve_execution_data(self, run_dir: Path) -> dict[str, Any] | None:
        exec_path = run_dir / self.primary_output_dir / "execution.json"
        if not exec_path.is_file():
            exec_path = run_dir / "execution.json"
        if exec_path.is_file():
            try:
                data = json.loads(exec_path.read_text(encoding="utf-8"))
                if isinstance(data, dict):
                    return data
            except Exception:
                pass
        return None


class GenesisEngineRunnerAdapter(RunnerAdapter):
    backend: str = "genesis_engine"
    primary_output_dir: str = "output"
    supports_pause: bool = True
    supports_resume: bool = True
    supports_checkpoint: bool = False


class FrontierReferenceRunnerAdapter(RunnerAdapter):
    backend: str = "frontier_reference_model"
    primary_output_dir: str = "output"
    supports_pause: bool = False
    supports_resume: bool = False
    supports_checkpoint: bool = False


class ReferenceExperimentRunnerAdapter(RunnerAdapter):
    backend: str = "reference_experiment"
    primary_output_dir: str = "."
    supports_pause: bool = True
    supports_resume: bool = True


class CustomScriptRunnerAdapter(RunnerAdapter):
    backend: str = "custom_script"
    primary_output_dir: str = "output"
    supports_pause: bool = False
    supports_resume: bool = False
    supports_checkpoint: bool = False


def get_runner_adapter(manifest: dict[str, Any] | None = None, script_name: str | None = None) -> RunnerAdapter:
    """Resolve the appropriate RunnerAdapter for a simulation run."""
    manifest = manifest or {}
    boundary = manifest.get("executionBoundary") or {}
    backend = boundary.get("backend") or boundary.get("engineBackend") or manifest.get("engine_backend") or ""
    is_frontier = bool(boundary.get("isFrontierReference"))
    script = script_name or manifest.get("params", {}).get("scriptName") or ""
    s_lower = str(script).lower()

    if is_frontier or "frontier" in s_lower or "challenge" in s_lower or backend == "frontier_reference_model":
        return FrontierReferenceRunnerAdapter()
    if s_lower == "genesis_long_board_campaign.py" or backend == "reference_experiment":
        return ReferenceExperimentRunnerAdapter()
    if backend == "genesis_engine" or "rq_full_engine" in s_lower:
        return GenesisEngineRunnerAdapter()
    return CustomScriptRunnerAdapter()


def build_run_snapshot(
    run_id: str,
    status_info: dict[str, Any],
    manifest_data: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build unified RunSnapshot v2 dictionary for consistent list and details views."""
    manifest = manifest_data or {}
    session_id = str(status_info.get("session_id") or manifest.get("session_id") or f"sess_{run_id}")
    revision = int(status_info.get("revision", 1))

    entry = get_safe_run_dir(run_id)
    adapter = get_runner_adapter(manifest, script_name=status_info.get("params", {}).get("scriptName"))
    exec_data = adapter.resolve_execution_data(entry) if entry else None
    has_complete_exec = False
    if exec_data and exec_data.get("complete") is True:
        rep_id = exec_data.get("runId") or exec_data.get("run_id")
        if not rep_id or rep_id == run_id:
            if not exec_data.get("validation_failures") and not exec_data.get("errors") and not exec_data.get("failed"):
                has_complete_exec = True

    raw_status = str(status_info.get("status", "")).upper()
    if not raw_status or raw_status == "UNKNOWN":
        if has_complete_exec:
            raw_status = "COMPLETED"
        else:
            live_log = (entry / adapter.primary_output_dir / "live.log") if entry else None
            if live_log and not live_log.is_file():
                if entry is not None:
                    live_log = entry / "live.log"
            if live_log and live_log.is_file() and (time.time() - live_log.stat().st_mtime < 120):
                raw_status = "RUNNING"
            elif entry and ((entry / "STOP").is_file() or ((entry / adapter.primary_output_dir / "STOP").is_file())):
                raw_status = "STOPPED"
            else:
                raw_status = "STOPPED"

    state_map = {
        "STARTING": "STARTING",
        "RUNNING": "RUNNING",
        "PAUSING": "PAUSING",
        "PAUSED": "PAUSED",
        "RESUMING": "RESUMING",
        "STOPPING": "STOPPING",
        "STOPPED": "STOPPED",
        "COMPLETED": "COMPLETED",
        "FAILED": "FAILED",
        "QUEUED": "QUEUED",
        "STALE": "STOPPED",
        "CANCELLED": "STOPPED",
        "INACTIVE": "STOPPED",
    }
    state = state_map.get(raw_status, "STOPPED")
    if has_complete_exec and raw_status not in ("FAILED", "STOPPED", "CANCELLED", "STOPPING"):
        state = "COMPLETED"

    # A reader can observe the sealed report before the watcher flushes final status.
    # Use actual calibrated work, never done=total from a completion label alone.
    sealed_summary = (exec_data or {}).get("summary") or {}
    sealed_summary = sealed_summary if isinstance(sealed_summary, dict) else {}
    sealed_work = sealed_summary.get("summary_metrics") or {}
    sealed_work = sealed_work if isinstance(sealed_work, dict) else {}
    expected_ticks = (manifest.get("params") or status_info.get("params") or {}).get("ticks")
    if (
        has_complete_exec and state == "COMPLETED"
        and sealed_summary.get("experiment_id") == "T11"
        and sealed_summary.get("track") == "ENGINE"
        and sealed_work.get("validity") == "COMPLETE"
        and isinstance(expected_ticks, int) and not isinstance(expected_ticks, bool)
        and expected_ticks >= 2
        and sealed_work.get("finished_ticks") == expected_ticks
        and sealed_work.get("target_ticks") == expected_ticks
    ):
        status_info = dict(status_info)
        status_info["work_done"] = sealed_work["finished_ticks"]
        status_info["work_total"] = sealed_work["target_ticks"]

    caps = status_info.get("capabilities") or manifest.get("capabilities")
    if not isinstance(caps, dict):
        caps = adapter.resolve_capabilities()

    workers_expected = int(
        status_info.get("params", {}).get("workers")
        or manifest.get("params", {}).get("workers")
        or 1
    )
    manifest_seeds = manifest.get("params", {}).get("seeds")
    seeds_list_len = len(manifest_seeds) if isinstance(manifest_seeds, list) else 0

    explicit_total_seeds = (
        status_info.get("totalSeeds")
        or status_info.get("total_seeds")
        or manifest.get("params", {}).get("totalSeeds")
        or (seeds_list_len if seeds_list_len > 0 else None)
    )
    total_seeds = int(explicit_total_seeds) if explicit_total_seeds is not None else max(1, workers_expected)
    completed_seeds = int(
        status_info.get("completedSeeds")
        or status_info.get("completed_seeds")
        or 0
    )
    if state == "COMPLETED":
        completed_seeds = max(completed_seeds, total_seeds)

    remaining_seeds = max(0, total_seeds - completed_seeds)
    active_workers_expected = min(workers_expected, max(1, remaining_seeds)) if remaining_seeds > 0 else 0

    ack_files: set[str] = set()
    if entry and entry.is_dir():
        for p in entry.glob("ack_paused_*"):
            ack_files.add(p.name)
        out_dir = entry / adapter.primary_output_dir
        if out_dir.is_dir():
            for p in out_dir.glob("ack_paused_*"):
                ack_files.add(p.name)

    workers_paused = min(len(ack_files), max(workers_expected, 1))

    # Cooperative ACK-driven state refinement
    if entry and entry.is_dir():
        has_pause_file = (entry / "PAUSE").is_file() or ((entry / adapter.primary_output_dir / "PAUSE").is_file())
        if has_pause_file:
            if state in ("RUNNING", "STARTING", "PAUSING"):
                if (active_workers_expected > 0 and workers_paused >= active_workers_expected) or (active_workers_expected == 0 and remaining_seeds == 0):
                    state = "PAUSED"
                else:
                    state = "PAUSING"
        elif state == "PAUSED":
            if workers_paused > 0:
                state = "RESUMING"
            else:
                state = "RUNNING"

    requested_state: str | None = None
    if state == "PAUSING":
        requested_state = "PAUSED"
    elif state == "RESUMING":
        requested_state = "RUNNING"
    elif state == "STOPPING":
        requested_state = "STOPPED"

    pct_raw = status_info.get("pct")
    if pct_raw is None:
        pct_val = 100.0 if state == "COMPLETED" else 0.0
    else:
        try:
            pct_val = float(pct_raw)
            if not math.isfinite(pct_val):
                pct_val = 100.0 if state == "COMPLETED" else 0.0
        except (ValueError, TypeError):
            pct_val = 100.0 if state == "COMPLETED" else 0.0

    if "work_done" in status_info and "work_total" in status_info:
        try:
            work_done = float(status_info["work_done"])
            work_total = float(status_info["work_total"])
            if math.isfinite(work_done) and math.isfinite(work_total) and work_total > 0:
                pct_val = 100.0 * max(0.0, min(work_total, work_done)) / work_total
        except (TypeError, ValueError):
            pct_val = 0.0
    elif state == "COMPLETED":
        pct_val = 100.0
    pct_val = max(0.0, min(100.0, pct_val))

    started_at = float(status_info.get("startedAt", 0.0))
    wall_elapsed = max(0.0, time.time() - started_at) if started_at > 0 else 0.0
    paused_seconds = float(status_info.get("paused_seconds", 0.0))
    if "active_elapsed_seconds" in status_info:
        active_elapsed = float(status_info["active_elapsed_seconds"])
    else:
        active_elapsed = max(0.0, wall_elapsed - paused_seconds)

    if entry and entry.is_dir():
        hlog = entry / adapter.primary_output_dir / "health.log"
        if not hlog.is_file():
            hlog = entry / "health.log"
        if hlog.is_file():
            try:
                lines = hlog.read_text(encoding="utf-8").splitlines()
                if lines:
                    last_rec = json.loads(lines[-1])
                    if "active_elapsed_seconds" in last_rec:
                        active_elapsed = float(last_rec["active_elapsed_seconds"])
                    if "paused_seconds" in last_rec:
                        paused_seconds = float(last_rec["paused_seconds"])
                    if "wall_elapsed_seconds" in last_rec:
                        wall_elapsed = float(last_rec["wall_elapsed_seconds"])
            except Exception:
                pass

    snap_dict = {
        "schema_version": "run_snapshot_v2",
        "run_id": run_id,
        "session_id": session_id,
        "revision": revision,
        "state": state,
        "requested_state": requested_state,
        "capabilities": {
            "pause": bool(caps.get("pause", False)),
            "resume": bool(caps.get("resume", False)),
            "checkpoint_continue": bool(caps.get("checkpoint_continue", False)),
        },
        "workers_expected": workers_expected,
        "workers_paused": workers_paused,
        "progress": {
            "kind": "work_units",
            "stage": "simulation",
            "done": float(status_info.get("work_done", completed_seeds)),
            "total": float(status_info.get("work_total", total_seeds)),
            "pct": round(pct_val, 2),
        },
        "active_elapsed_seconds": round(active_elapsed, 2),
        "paused_seconds": round(paused_seconds, 2),
        "wall_elapsed_seconds": round(wall_elapsed, 2),
        "heartbeat_at": datetime.datetime.now(datetime.UTC).isoformat(),
        "pending_command_id": None,
    }
    from codontrace.genesis.snapshot import validate_run_snapshot

    return validate_run_snapshot(snap_dict)


def list_simulation_runs() -> list[dict[str, Any]]:
    """Enumerate discovered simulation runs with authoritative status verification."""
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
        manifest_file = entry / "manifest.json"
        if not manifest_file.is_file():
            manifest_file = entry / "run_manifest.json"
        manifest_data: dict[str, Any] = {}
        if manifest_file.is_file():
            try:
                manifest_data = json.loads(manifest_file.read_text(encoding="utf-8"))
            except Exception:
                pass

        adapter = get_runner_adapter(manifest_data)
        status_info = adapter.reconcile_status(entry)
        engine_dir = entry / adapter.primary_output_dir
        status_file = entry / "status.json"
        live_log = (engine_dir / "live.log") if (engine_dir / "live.log").is_file() else (entry / "live.log")
        console_log = (entry / "console.log") if (entry / "console.log").is_file() else (engine_dir / "console.log")

        # Authoritative status determination
        st = status_info.get("status")
        pid = status_info.get("pid")
        if not pid:
            pid_file = entry / "run.pid"
            if pid_file.is_file():
                try:
                    pid = int(pid_file.read_text(encoding="utf-8").strip())
                except (ValueError, OSError):
                    pid = None

        exec_data = adapter.resolve_execution_data(entry)
        has_complete_exec = False
        if exec_data and exec_data.get("complete") is True:
            rep_id = exec_data.get("runId") or exec_data.get("run_id")
            if not rep_id or rep_id == run_id:
                if not exec_data.get("validation_failures") and not exec_data.get("errors") and not exec_data.get("failed"):
                    has_complete_exec = True

        if st in ("RUNNING", "STARTING", "PAUSED", "PAUSING", "RESUMING", "STOPPING"):
            alive = False
            with _RUN_LOCK:
                proc = _RUN_PROCESSES.get(run_id)
                if proc and proc.poll() is None:
                    alive = True
            if not alive and pid:
                alive = _run_pid_alive(pid, entry)

            if not alive:
                orig_st = status_info.get("status")
                if (entry / "STOP").is_file() or (engine_dir / "STOP").is_file():
                    st = "STOPPED"
                elif has_complete_exec:
                    st = "COMPLETED"
                else:
                    st = "STALE"
                if st != orig_st:
                    status_info["status"] = st
                    write_atomic_json(status_file, status_info)
        elif not st:
            has_complete_marker = False
            complete_file = entry / "COMPLETE"
            if complete_file.is_file():
                try:
                    content = complete_file.read_text(encoding="utf-8").strip()
                    if not content or run_id in content:
                        has_complete_marker = True
                except OSError:
                    has_complete_marker = True
            if has_complete_exec or has_complete_marker:
                st = "COMPLETED"
            elif live_log.is_file() and (time.time() - live_log.stat().st_mtime < 120):
                st = "RUNNING"
            else:
                st = "INACTIVE"

        status_info["status"] = st
        if st == "COMPLETED":
            status_info["pct"] = 100.0

        seeds_dir = (engine_dir / "by_seed") if (engine_dir / "by_seed").is_dir() else (entry / "by_seed")
        seed_count = 0
        if seeds_dir.is_dir():
            for s_dir in seeds_dir.glob("seed*"):
                if (s_dir / "archive.jsonl").is_file() or s_dir.is_dir():
                    seed_count += 1

        logs = tail_file(live_log, 15) or tail_file(console_log, 15)
        snapshot = build_run_snapshot(run_id, status_info, manifest_data)
        pct_val = snapshot["progress"]["pct"] if (snapshot.get("progress") and snapshot["progress"].get("pct") is not None) else (100.0 if st == "COMPLETED" else 0.0)

        runs.append({
            "id": run_id,
            "title": status_info.get("title") or run_id.replace("_", " ").title(),
            "status": st if st == "STALE" else snapshot["state"],
            "path": str(entry),
            "pct": round(float(pct_val), 2),
            "completedSeeds": status_info.get("completed_seeds", status_info.get("completedSeeds", seed_count)),
            "totalSeeds": status_info.get("total_seeds", status_info.get("totalSeeds", max(12, seed_count))),
            "mtime": entry.stat().st_mtime,
            "recentLogs": logs,
            "snapshot": snapshot,
            "capabilities": snapshot["capabilities"],
        })

    return runs


def get_run_details(run_id: str) -> dict[str, Any] | None:
    """Retrieve full details and recent logs of a specific run with containment validation."""
    entry = get_safe_run_dir(run_id, must_exist=True)
    if entry is None:
        return None

    manifest_file = entry / "run_manifest.json"
    if not manifest_file.is_file():
        manifest_file = entry / "manifest.json"
    manifest_data: dict[str, Any] = {}
    if manifest_file.is_file():
        try:
            manifest_data = json.loads(manifest_file.read_text(encoding="utf-8"))
            if not isinstance(manifest_data, dict):
                manifest_data = {}
        except (OSError, ValueError):
            pass

    adapter = get_runner_adapter(manifest_data)
    status_info = adapter.reconcile_status(entry)
    engine_dir = entry / adapter.primary_output_dir
    status_file = entry / "status.json"

    st = status_info.get("status")
    pid = status_info.get("pid")
    if not pid:
        pid_file = entry / "run.pid"
        if pid_file.is_file():
            try:
                pid = int(pid_file.read_text(encoding="utf-8").strip())
            except (ValueError, OSError):
                pid = None

    if st in ("RUNNING", "STARTING", "PAUSED", "PAUSING", "RESUMING", "STOPPING"):
        alive = False
        with _RUN_LOCK:
            proc = _RUN_PROCESSES.get(run_id)
            if proc:
                p_code = proc.poll()
                if p_code is None:
                    alive = True
                else:
                    # The registered watcher still owns terminalization and seal
                    # validation. Process exit alone is not a finished report.
                    # Never persist STALE while that watcher is publishing T11.
                    alive = True
                    status_info.setdefault("exitCode", p_code)
        if not alive and pid:
            alive = _run_pid_alive(pid, entry)

        if not alive:
            orig_st = status_info.get("status")
            exec_data_val = adapter.resolve_execution_data(entry)
            if (entry / "STOP").is_file() or (engine_dir / "STOP").is_file():
                st = "STOPPED"
            elif exec_data_val:
                is_complete = exec_data_val.get("complete") is True
                rep_id = exec_data_val.get("runId") or exec_data_val.get("run_id")
                if rep_id and rep_id != run_id:
                    is_complete = False
                if exec_data_val.get("validation_failures") or exec_data_val.get("errors") or exec_data_val.get("failed"):
                    is_complete = False
                st = "COMPLETED" if is_complete else "FAILED"
            elif (entry / "STOP").is_file() or (engine_dir / "STOP").is_file():
                st = "STOPPED"
            else:
                st = "STALE"
            if st != orig_st:
                status_info["status"] = st
                if st == "COMPLETED":
                    status_info.setdefault("exitCode", 0)
                    status_info["pct"] = 100.0
                    status_info.setdefault("endedAt", time.time())
                elif st == "FAILED":
                    status_info.setdefault("exitCode", 1)
                    status_info.setdefault("endedAt", time.time())
                write_atomic_json(status_file, status_info)
        elif not st:
            live_log = (engine_dir / "live.log") if (engine_dir / "live.log").is_file() else (entry / "live.log")
            exec_data_val = adapter.resolve_execution_data(entry)
            has_complete_exec = False
            if exec_data_val and exec_data_val.get("complete") is True:
                rep_id = exec_data_val.get("runId") or exec_data_val.get("run_id")
                if not rep_id or rep_id == run_id:
                    if not exec_data_val.get("validation_failures") and not exec_data_val.get("errors") and not exec_data_val.get("failed"):
                        has_complete_exec = True
            complete_file = entry / "COMPLETE"
            if has_complete_exec or complete_file.is_file():
                st = "COMPLETED"
                status_info["status"] = "COMPLETED"
                status_info["pct"] = 100.0
                status_info.setdefault("exitCode", 0)
            elif live_log.is_file() and (time.time() - live_log.stat().st_mtime < 120):
                st = "RUNNING"
                status_info["status"] = "RUNNING"
            else:
                st = "STOPPED"
                status_info["status"] = "STOPPED"

    live_log = (engine_dir / "live.log") if (engine_dir / "live.log").is_file() else (entry / "live.log")
    console_log = (entry / "console.log") if (entry / "console.log").is_file() else (engine_dir / "console.log")

    exec_data: dict[str, Any] = {}
    for ej in (engine_dir / "execution.json", entry / "execution.json", engine_dir / "partial_execution.json"):
        if ej.is_file():
            try:
                raw_ej = json.loads(ej.read_text(encoding="utf-8"))
                if isinstance(raw_ej, dict):
                    exec_data = raw_ej
                    break
            except Exception:
                pass

    diagnostics_data: dict[str, Any] = {}
    for dj in (engine_dir / "time_shift_diagnostics.json", entry / "time_shift_diagnostics.json"):
        if dj.is_file():
            try:
                raw_dj = json.loads(dj.read_text(encoding="utf-8"))
                if isinstance(raw_dj, dict):
                    diagnostics_data = raw_dj
                    break
            except Exception:
                pass

    snapshot = build_run_snapshot(run_id, status_info, manifest_data)
    pct_val = snapshot["progress"]["pct"] if (snapshot.get("progress") and snapshot["progress"].get("pct") is not None) else (100.0 if status_info.get("status") == "COMPLETED" else 0.0)

    from codontrace.console.evaluator import evaluate_run_hypothesis

    assessment = evaluate_run_hypothesis({
        "status": snapshot["state"],
        "execution": exec_data,
        "diagnostics": diagnostics_data,
        "manifest": manifest_data,
    })
    boundary = manifest_data.get("executionBoundary") or {
        "engineBackend": status_info.get("engineBackend", "unknown"),
        "isGenesisEngine": status_info.get("engineBackend", "unknown") == "genesis_engine",
        "isFrontierReference": status_info.get("isFrontierReference", False),
        "modelScope": "full_digital_organism_simulation" if status_info.get("engineBackend") == "genesis_engine" else "unverified_execution",
        "modelBoundaryNotice": "Digital organism coevolution engine" if status_info.get("engineBackend") == "genesis_engine" else "Execution backend has not been established by this run manifest.",
    }
    if snapshot["state"] == "COMPLETED":
        status_info["pct"] = 100.0
        status_info.setdefault("exitCode", 0)

    return {
        "id": run_id,
        "title": status_info.get("title") or run_id.replace("_", " ").title(),
        "status": snapshot["state"],
        "pct": round(float(pct_val), 2),
        "statusData": status_info,
        "manifest": manifest_data,
        "execution": exec_data,
        "diagnostics": diagnostics_data,
        "liveLogs": tail_file(live_log, 100),
        "consoleLogs": tail_file(console_log, 100),
        "snapshot": snapshot,
        "capabilities": snapshot["capabilities"],
        "hypothesis_assessment": assessment,
        "scientificAssessment": (exec_data.get("summary") or {}).get("scientific_assessment", "UNASSESSED"),
        "telemetry": _read_metrics_tail(entry / "metrics.jsonl"),
        "executionBoundary": boundary,
    }


def _read_metrics_tail(path: Path) -> list[dict[str, Any]]:
    """Bounded latest telemetry; a concurrent partial JSONL line is ignored."""
    records = []
    for line in tail_file(path, max_lines=200, max_bytes=262144):
        try:
            row = json.loads(line)
            if isinstance(row, dict):
                records.append(row)
        except ValueError:
            continue
    return records


def _seal_t11_console_report(run_id: str, run_dir: Path, engine_dir: Path, status: dict[str, Any]) -> None:
    """Adapt the real calibrated pilot's sealed artifacts without claiming science."""
    seed = status.get("params", {}).get("seeds", [7])[0]
    arm = engine_dir / "runs" / "T11" / f"seed_{seed}" / "arm_uninterrupted"
    try:
        completion = json.loads((arm / "completion.json").read_text(encoding="utf-8"))
        manifest = json.loads((arm / "artifacts_manifest.json").read_text(encoding="utf-8"))
        valid = completion.get("validity") == "COMPLETE" and completion.get("finished_ticks") == completion.get("target_ticks") and completion.get("finished_ticks", 0) >= 2 and completion.get("target_ticks") == status.get("params", {}).get("ticks")
        for relative, digest in manifest.get("files", {}).items():
            artifact = (arm / relative).resolve()
            if not artifact.is_relative_to(arm.resolve()) or hashlib.sha256(artifact.read_bytes()).hexdigest() != digest:
                valid = False
        if not manifest.get("files"):
            valid = False
        if not valid:
            raise ValueError("T11 seal/horizon validation failed")
        summary = {"experiment_id": "T11", "track": "ENGINE", "scientific_assessment": "UNASSESSED", "summary_metrics": completion}
        # Preserve original raw files; publish a normalized observation for the
        # generic analysis UI rather than pretending ticks are generations.
        observations = _read_metrics_tail(arm / "metrics.jsonl")
        with (run_dir / "metrics.jsonl").open("w", encoding="utf-8") as metrics:
            for observation in observations:
                normalized = {"tick": observation.get("tick"), "population_size": observation.get("living"), "primary_metric_name": "living_organisms", "primary_metric_value": observation.get("living"), "secondary_metrics": {}, "details": observation}
                metrics.write(json.dumps(normalized, allow_nan=False) + "\n")
        write_atomic_json(run_dir / "execution.json", {"runId": run_id, "complete": True, "summary": summary})
        status["work_done"] = completion["finished_ticks"]
        status["work_total"] = completion["target_ticks"]
        status["completedSeeds"] = 1
        status["totalSeeds"] = 1
    except (OSError, ValueError, TypeError, KeyError) as exc:
        write_atomic_json(run_dir / "execution.json", {"runId": run_id, "complete": False, "failed": True, "error": str(exc)})


def send_signal_to_run(run_id: str, sig_name: str) -> bool:
    """Send cooperative pause/resume signal directly to the run's registered process."""
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

    proc_alive = False
    if proc and proc.poll() is None or pid and _run_pid_alive(pid, entry):
        proc_alive = True

    if (proc is not None or pid is not None) and not proc_alive:
        return False

    sig_upper = sig_name.upper()
    engine_dir = entry / "output"

    if sig_upper in ("PAUSE", "STOP"):
        # Cooperative pause: place PAUSE marker file (R17)
        (entry / "PAUSE").write_text("paused by console\n", encoding="utf-8")
        if engine_dir.is_dir():
            (engine_dir / "PAUSE").write_text("paused by console\n", encoding="utf-8")
        return True
    elif sig_upper == "CONT":
        # Cooperative resume: remove PAUSE marker file (R17)
        for marker in (entry / "PAUSE", engine_dir / "PAUSE"):
            if marker.is_file():
                try:
                    marker.unlink()
                except OSError:
                    pass
        return True

    return False


def generate_run_zip_file(run_id: str) -> tuple[Path | None, dict[str, Any] | None]:
    """Generate a temporary zip archive on disk with integrity manifest and no silent file drops."""
    entry = get_safe_run_dir(run_id, must_exist=True)
    if entry is None:
        return None, None

    import hashlib
    import tempfile
    import zipfile

    status_file = entry / "status.json"
    status_str = "UNKNOWN"
    if status_file.is_file():
        try:
            status_data = json.loads(status_file.read_text(encoding="utf-8"))
            if isinstance(status_data, dict):
                status_str = status_data.get("status", "UNKNOWN")
        except Exception:
            pass

    is_partial = status_str != "COMPLETED"

    tmp_fd, tmp_path_str = tempfile.mkstemp(suffix=".zip", prefix=f"run_export_{run_id}_")
    os.close(tmp_fd)
    tmp_path = Path(tmp_path_str)

    manifest_files: list[dict[str, Any]] = []
    omitted_files: list[dict[str, Any]] = []
    total_raw_bytes = 0

    entry_root = entry.resolve()
    try:
        with zipfile.ZipFile(tmp_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for file_path in sorted(entry.rglob("*")):
                if not file_path.is_file():
                    continue
                try:
                    rel_path = file_path.relative_to(entry)
                except ValueError:
                    continue

                if ".tmp." in file_path.name:
                    continue

                # Strict boundary containment check (prevent symlink path traversal - R05)
                if file_path.is_symlink():
                    omitted_files.append({
                        "path": str(rel_path).replace("\\", "/"),
                        "size": 0,
                        "reason": "Symlink traversal outside run boundary rejected",
                    })
                    continue

                try:
                    target_path = file_path.resolve(strict=True)
                    if not target_path.is_relative_to(entry_root):
                        omitted_files.append({
                            "path": str(rel_path).replace("\\", "/"),
                            "size": 0,
                            "reason": "Symlink traversal outside run boundary rejected",
                        })
                        continue
                    if target_path == tmp_path.resolve():
                        continue
                except (OSError, RuntimeError, ValueError) as exc:
                    omitted_files.append({
                        "path": str(rel_path).replace("\\", "/"),
                        "size": 0,
                        "reason": f"Path resolution error: {exc}",
                    })
                    continue

                file_size = file_path.stat().st_size
                hasher = hashlib.sha256()
                try:
                    # Hash the exact archived prefix, not a separate pre-export read
                    # of a JSONL stream that can grow between operations.
                    captured_bytes = 0
                    with file_path.open("rb") as f, zf.open(str(rel_path).replace("\\", "/"), "w") as archived:
                        remaining = file_size
                        while remaining > 0:
                            chunk = f.read(min(65536, remaining))
                            if not chunk:
                                break
                            archived.write(chunk)
                            hasher.update(chunk)
                            captured_bytes += len(chunk)
                            remaining -= len(chunk)
                    sha256_hex = hasher.hexdigest()
                    file_size = captured_bytes
                    manifest_files.append({
                        "path": str(rel_path).replace("\\", "/"),
                        "size": file_size,
                        "sha256": sha256_hex,
                    })
                    total_raw_bytes += file_size
                except (OSError, PermissionError) as exc:
                    omitted_files.append({
                        "path": str(rel_path).replace("\\", "/"),
                        "size": file_size,
                        "reason": f"Read error: {exc}",
                    })

            export_manifest = {
                "schemaVersion": 1,
                "runId": run_id,
                "exportedAt": time.time(),
                "snapshotStatus": status_str,
                "isPartialSnapshot": is_partial,
                "totalFiles": len(manifest_files),
                "totalRawBytes": total_raw_bytes,
                "files": manifest_files,
                "omittedFiles": omitted_files,
            }
            zf.writestr("export_manifest.json", json.dumps(export_manifest, indent=2))

        return tmp_path, export_manifest
    except Exception:
        if tmp_path.is_file():
            try:
                tmp_path.unlink()
            except OSError:
                pass
        raise


def get_run_zip(run_id: str) -> bytes | None:
    """Create a complete zip archive of a simulation run with integrity manifest."""
    tmp_path, _ = generate_run_zip_file(run_id)
    if tmp_path is None:
        return None
    try:
        return tmp_path.read_bytes()
    finally:
        try:
            tmp_path.unlink(missing_ok=True)
        except OSError:
            pass


def manage_run_action(run_id: str, action: str, *, request_id: str | None = None) -> dict[str, Any]:
    """Serialize one card's actions and make explicitly keyed restarts idempotent."""
    if request_id is not None and (not isinstance(request_id, str) or not re.fullmatch(r"[A-Za-z0-9_.-]{1,128}", request_id)):
        return {"ok": False, "error": "Invalid request_id", "status_code": 400}
    if validate_run_id(run_id) is None:
        return _manage_run_action_unlocked(run_id, action)
    with _RUN_LOCK:
        action_lock = _RUN_ACTION_LOCKS.setdefault(run_id, threading.RLock())
    with action_lock:
        entry = get_safe_run_dir(run_id, must_exist=True)
        cache: dict[str, Any] = {}
        cache_file = entry / "restart_requests.json" if entry else None
        cache_key = request_id if action.lower().strip() == "restart" else None
        if cache_file is not None and cache_key is not None:
            try:
                loaded = json.loads(cache_file.read_text(encoding="utf-8"))
                if isinstance(loaded, dict):
                    cache = loaded
            except (OSError, ValueError):
                pass
            if isinstance(cache.get(cache_key), dict):
                return dict(cache[cache_key], idempotent_replay=True)
        result = _manage_run_action_unlocked(run_id, action)
        if cache_file is not None and cache_key is not None and result.get("ok"):
            cache[cache_key] = result
            cache = dict(list(cache.items())[-64:])
            write_atomic_json(cache_file, cache)
        return result


def _manage_run_action_unlocked(run_id: str, action: str) -> dict[str, Any]:
    """Execute lifecycle action on a simulation run with containment and process ownership."""
    valid_id = validate_run_id(run_id)
    if not valid_id:
        return {"ok": False, "error": "Invalid run ID or path traversal attempt", "status_code": 400}

    entry = get_safe_run_dir(run_id, must_exist=True)
    if entry is None:
        return {"ok": False, "error": f"Run '{run_id}' not found", "status_code": 200}

    act = action.lower().strip()
    status_file = entry / "status.json"
    status_info: dict[str, Any] = {}
    if status_file.is_file():
        try:
            status_info = json.loads(status_file.read_text(encoding="utf-8"))
            if not isinstance(status_info, dict):
                status_info = {}
        except Exception:
            status_info = {}

    manifest_file = entry / "run_manifest.json"
    if not manifest_file.is_file():
        manifest_file = entry / "manifest.json"
    manifest_data: dict[str, Any] = {}
    if manifest_file.is_file():
        try:
            manifest_data = json.loads(manifest_file.read_text(encoding="utf-8"))
            if not isinstance(manifest_data, dict):
                manifest_data = {}
        except Exception:
            manifest_data = {}

    # Determine capabilities
    caps = status_info.get("capabilities") or manifest_data.get("capabilities")
    if not isinstance(caps, dict):
        adapter = get_runner_adapter(manifest_data, script_name=status_info.get("params", {}).get("scriptName"))
        caps = adapter.resolve_capabilities(entry)

    # Determine process ownership and liveness
    with _RUN_LOCK:
        proc = _RUN_PROCESSES.get(run_id)

    pid = status_info.get("pid")
    if not pid:
        pid_file = entry / "run.pid"
        if pid_file.is_file():
            try:
                pid = int(pid_file.read_text(encoding="utf-8").strip())
            except (ValueError, OSError):
                pid = None

    proc_alive = False
    if proc and proc.poll() is None or pid and _run_pid_alive(pid, entry):
        proc_alive = True

    current_status = str(status_info.get("status", "UNKNOWN")).upper()

    # State errors take precedence over missing/unknown runner capabilities.
    if act in ("pause", "resume") and current_status in ("COMPLETED", "FAILED", "STOPPED", "STALE"):
        return {"ok": False, "status_code": 409, "error_code": "INVALID_STATE",
                "error": f"Cannot {act} run in terminal state '{current_status}'. Use restart instead."}

    if act == "pause":
        if not caps.get("pause", False):
            return {
                "ok": False,
                "status_code": 409,
                "error_code": "UNSUPPORTED_CAPABILITY",
                "message": f"Run {run_id} does not support {action} capability.",
                "action": action,
                "run_id": run_id,
            }

        # Terminal and stale states are forbidden to pause (L01)
        if current_status in ("COMPLETED", "FAILED", "STOPPED", "STALE"):
            return {
                "ok": False,
                "error": f"Cannot pause a run in terminal or inactive state '{current_status}'",
                "error_code": "INVALID_STATE",
                "status_code": 409,
            }

        # Idempotent pause on already paused run
        if current_status == "PAUSED":
            return {
                "ok": True,
                "action": "pause",
                "run_id": run_id,
                "already_paused": True,
                "status_code": 200,
            }

        # Must have living process
        if (proc is not None or pid is not None) and not proc_alive:
            status_info["status"] = "FAILED"
            write_atomic_json(status_file, status_info)
            return {
                "ok": False,
                "error": "Cannot pause run: process is no longer active",
                "error_code": "PROCESS_NOT_ALIVE",
                "status_code": 409,
            }

        ok = send_signal_to_run(run_id, "PAUSE")
        if ok:
            ack_files = set()
            for f in entry.glob("ack_paused_*"):
                ack_files.add(f.name)
            for f in (entry / "output").glob("ack_paused_*"):
                ack_files.add(f.name)
            workers_param = status_info.get("params", {}).get("workers") or manifest_data.get("params", {}).get("workers")
            if workers_param is not None and int(workers_param) > 1:
                workers_expected = int(workers_param)
                manifest_seeds = manifest_data.get("params", {}).get("seeds")
                seeds_list_len = len(manifest_seeds) if isinstance(manifest_seeds, list) else 0
                total_seeds = int(
                    status_info.get("totalSeeds")
                    or status_info.get("total_seeds")
                    or manifest_data.get("params", {}).get("totalSeeds")
                    or (seeds_list_len if seeds_list_len > 0 else 0)
                    or 1
                )
                completed_seeds = int(status_info.get("completedSeeds") or status_info.get("completed_seeds") or 0)
                remaining_seeds = max(0, total_seeds - completed_seeds)
                active_expected = min(workers_expected, max(1, remaining_seeds)) if remaining_seeds > 0 else 0

                status_info["status"] = "PAUSED" if len(ack_files) >= active_expected and active_expected > 0 else "PAUSING"
            else:
                status_info["status"] = "PAUSED" if ack_files else "PAUSING"
            status_info["revision"] = int(status_info.get("revision", 1)) + 1
            write_atomic_json(status_file, status_info)
        return {"ok": ok, "action": "pause", "run_id": run_id, "status_code": 200 if ok else 500}

    elif act == "resume":
        if not caps.get("resume", False):
            return {
                "ok": False,
                "status_code": 409,
                "error_code": "UNSUPPORTED_CAPABILITY",
                "message": f"Run {run_id} does not support {action} capability.",
                "action": action,
                "run_id": run_id,
            }

        # Cannot resume terminal or stopped runs (L03)
        if current_status in ("COMPLETED", "FAILED", "STOPPED", "STALE"):
            return {
                "ok": False,
                "error": f"Cannot resume run in terminal state '{current_status}'. Use restart instead.",
                "error_code": "INVALID_STATE",
                "status_code": 409,
            }

        if current_status == "RUNNING":
            return {
                "ok": True,
                "action": "resume",
                "run_id": run_id,
                "already_running": True,
                "status_code": 200,
            }

        if current_status not in ("PAUSED", "PAUSING"):
            return {
                "ok": False,
                "error": f"Cannot resume run in state '{current_status}' (must be PAUSED)",
                "error_code": "INVALID_STATE",
                "status_code": 409,
            }

        if (proc is not None or pid is not None) and not proc_alive:
            status_info["status"] = "FAILED"
            write_atomic_json(status_file, status_info)
            return {
                "ok": False,
                "error": "Cannot resume run: process is dead. Use restart.",
                "error_code": "PROCESS_DEAD",
                "status_code": 409,
            }

        ok = send_signal_to_run(run_id, "CONT")
        if ok:
            ack_files = set()
            for f in entry.glob("ack_paused_*"):
                ack_files.add(f.name)
            for f in (entry / "output").glob("ack_paused_*"):
                ack_files.add(f.name)
            status_info["status"] = "RESUMING" if ack_files else "RUNNING"
            status_info["revision"] = int(status_info.get("revision", 1)) + 1
            write_atomic_json(status_file, status_info)
        return {"ok": ok, "action": "resume", "run_id": run_id, "status_code": 200 if ok else 500}

    elif act == "stop":
        if current_status == "STOPPED":
            return {"ok": True, "action": "stop", "run_id": run_id, "already_stopped": True, "status_code": 200}
        if current_status in ("COMPLETED", "FAILED"):
            return {"ok": True, "action": "stop", "run_id": run_id, "already_terminal": True, "status_code": 200}

        if proc is None and pid and proc_alive and not caps.get("cooperative_stop", False):
            identity_file = entry / "process_identity.json"
            if identity_file.is_file():
                try:
                    status_info["process_identity"] = json.loads(identity_file.read_text(encoding="utf-8"))
                except (OSError, ValueError):
                    pass
            if not _native_process_is_owned(pid, status_info, manifest_data):
                return {"ok": False, "error": "Process ownership is unverified; refused to signal a possibly reused PID", "error_code": "UNVERIFIED_PROCESS_IDENTITY", "status_code": 409}

        # Unlink any existing PAUSE markers so the process aborts cleanly
        for marker in (entry / "PAUSE", (entry / "output") / "PAUSE"):
            if marker.is_file():
                try:
                    marker.unlink()
                except OSError:
                    pass
        for ack in list(entry.glob("ack_paused_*")) + list((entry / "output").glob("ack_paused_*")):
            try:
                ack.unlink(missing_ok=True)
            except OSError:
                pass
        (entry / "STOP").write_text("stopped by console\n", encoding="utf-8")
        if (entry / "output").is_dir():
            ((entry / "output") / "STOP").write_text("stopped by console\n", encoding="utf-8")

        if caps.get("cooperative_stop", False) and proc_alive:
            status_info["status"] = "STOPPING"
            status_info["revision"] = int(status_info.get("revision", 1)) + 1
            write_atomic_json(status_file, status_info)
            return {"ok": True, "action": "stop", "run_id": run_id, "status_code": 200, "pending": True}

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
        elif pid and proc_alive:
            try:
                if sys.platform == "win32":
                    subprocess.run(["taskkill", "/F", "/PID", str(pid)], capture_output=True, timeout=5)
                else:
                    os.kill(pid, signal.SIGTERM)
                stopped = True
            except (ValueError, OSError, subprocess.SubprocessError):
                pass
        else:
            stopped = True

        still_alive = bool(proc is not None and proc.poll() is None or proc is None and pid and _run_pid_alive(pid, entry))
        status_info["status"] = "STOPPING" if still_alive else "STOPPED"
        status_info["stoppedAt"] = time.time()
        status_info["revision"] = int(status_info.get("revision", 1)) + 1
        write_atomic_json(status_file, status_info)

        return {"ok": stopped, "action": "stop", "run_id": run_id, "status_code": 200 if stopped else 500, "pending": still_alive}
    elif act == "restart":
        # Exit and sealed-report publication are separate events. Wait briefly
        # for an exited owned worker's finalizer, never for an active simulation.
        if proc is not None and proc.poll() is not None:
            with _RUN_LOCK:
                finalizer = _RUN_FINALIZERS.get(run_id)
            if finalizer is not None and finalizer.wait(timeout=2.0):
                with _RUN_LOCK:
                    proc = _RUN_PROCESSES.get(run_id)
                try:
                    status_info = json.loads(status_file.read_text(encoding="utf-8"))
                    current_status = str(status_info.get("status", "UNKNOWN")).upper()
                except (OSError, ValueError, AttributeError):
                    return {"ok": False, "error": "Final run status unavailable", "status_code": 409}
        if proc is not None:
            return {"ok": False, "error": "Run process or finalizer is still registered; wait for completion acknowledgement", "error_code": "INVALID_STATE", "status_code": 409}
        if proc_alive or current_status in ("STARTING", "QUEUED", "RUNNING", "PAUSING", "PAUSED", "RESUMING", "STOPPING"):
            return {"ok": False, "error": "Stop the active run and wait for its acknowledgement before restarting", "error_code": "INVALID_STATE", "status_code": 409}
        replay_params = manifest_data.get("params") or status_info.get("params")
        if not isinstance(replay_params, dict) or not replay_params:
            return {"ok": False, "error": "No reproducible launch parameters are available", "status_code": 409}
        result = launch_simulation_run(dict(replay_params))
        if result.get("ok"):
            new_dir = get_safe_run_dir(result["runId"], must_exist=True)
            if new_dir:
                write_atomic_json(new_dir / "restart_provenance.json", {"parentRunId": run_id, "parentConfigDigest": manifest_data.get("configDigest"), "restartedAt": time.time(), "mode": "fresh_replay"})
            result.update({"action": "restart", "parentRunId": run_id, "mode": "fresh_replay"})
        return result
    elif act in ("delete", "remove"):
        if proc_alive:
            return {"ok": False, "error": "Cannot delete an actively running simulation. Stop it first.", "status_code": 409}
        with _RUN_LOCK:
            proc = _RUN_PROCESSES.get(run_id)
            if proc is not None:
                return {
                    "ok": False,
                    "error": "Cannot delete an actively running or finalizing simulation. Stop it and wait first.",
                    "status_code": 409,
                }

        status_file = entry / "status.json"
        if status_file.is_file():
            try:
                raw_st = json.loads(status_file.read_text(encoding="utf-8"))
                if isinstance(raw_st, dict) and raw_st.get("status") == "RUNNING":
                    live_log = (entry / "output" / "live.log") if (entry / "output" / "live.log").is_file() else (entry / "live.log")
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


def _watch_run_process(run_id: str, proc: subprocess.Popen[Any], run_dir: Path, engine_dir: Path) -> None:
    """Monitor background simulation process, capture exit code and update status atomically."""
    try:
        ret = proc.wait()
    except Exception:
        ret = -1

    ended_at = time.time()
    status_file = run_dir / "status.json"
    status_info: dict[str, Any] = {}
    if status_file.is_file():
        try:
            status_info = json.loads(status_file.read_text(encoding="utf-8"))
            if not isinstance(status_info, dict):
                status_info = {}
        except Exception:
            status_info = {}

    if ret == 0 and status_info.get("params", {}).get("scriptName") == "board_long_campaign.py":
        _seal_t11_console_report(run_id, run_dir, engine_dir, status_info)
    stopped_marker = (run_dir / "STOP").is_file() or (engine_dir / "STOP").is_file()
    if stopped_marker or status_info.get("status") in ("STOPPED", "CANCELLED"):
        new_status = "STOPPED"
        error_reason = None
    elif status_info.get("status") == "FAILED":
        new_status = "FAILED"
        error_reason = status_info.get("errorReason") or "Run failed before process exit"
    elif ret == 0:
        exec_json = (engine_dir / "execution.json") if (engine_dir / "execution.json").is_file() else (run_dir / "execution.json")
        complete_marker = (run_dir / "COMPLETE").is_file() or (engine_dir / "COMPLETE").is_file()
        if exec_json.is_file():
            try:
                rep = json.loads(exec_json.read_text(encoding="utf-8"))
                if not isinstance(rep, dict):
                    new_status = "FAILED"
                    error_reason = "Corrupted execution report: root is not a JSON object"
                else:
                    is_complete = rep.get("complete") is True
                    rep_id = rep.get("runId") or rep.get("run_id")
                    if rep_id and rep_id != run_id:
                        is_complete = False

                    val_failures = rep.get("validation_failures") or rep.get("errors")
                    if rep.get("failed") or val_failures:
                        is_complete = False

                    if is_complete:
                        new_status = "COMPLETED"
                        error_reason = None
                    else:
                        new_status = "FAILED"
                        if rep.get("failed"):
                            error_reason = f"Execution failed: {rep.get('failed')}"
                        elif val_failures and isinstance(val_failures, list) and len(val_failures) > 0:
                            first = val_failures[0]
                            if isinstance(first, dict) and "reason" in first:
                                error_reason = f"Validation failure: {first['reason']}"
                            else:
                                error_reason = f"Validation failures: {val_failures}"
                        else:
                            error_reason = rep.get("error") or rep.get("reason") or "Run completed with failures in execution report"
            except Exception as exc:
                new_status = "FAILED"
                error_reason = f"Corrupted execution report (JSONDecodeError): {exc}"
        elif complete_marker:
            new_status = "COMPLETED"
            error_reason = None
        else:
            new_status = "FAILED"
            error_reason = "Run exited with 0 but produced no complete marker and no execution.json"
    else:
        new_status = "FAILED"
        console_log = run_dir / "console.log"
        last_lines = tail_file(console_log, 5)
        error_reason = last_lines[-1] if last_lines else f"Process exited with code {ret}"

    status_info["status"] = new_status
    status_info["exitCode"] = ret
    status_info["endedAt"] = ended_at
    if new_status == "COMPLETED":
        status_info["pct"] = 100.0
    if error_reason:
        status_info["errorReason"] = error_reason

    write_atomic_json(status_file, status_info)
    with _RUN_LOCK:
        _RUN_PROCESSES.pop(run_id, None)
        finalized = _RUN_FINALIZERS.pop(run_id, None)
        if finalized is not None:
            finalized.set()


def launch_simulation_run(params: dict[str, Any]) -> dict[str, Any]:
    """Launch a simulation run in the background with lifecycle separation, validation, and watcher."""
    if not isinstance(params, dict):
        return {"ok": False, "error": "Invalid params: expected JSON object", "status_code": 400}

    # Generations validation
    raw_gen = params.get("generations", 100)
    if isinstance(raw_gen, (bool, float)):
        return {"ok": False, "error": "generations must be an integer", "status_code": 400}
    try:
        generations = int(raw_gen)
        if generations < 1 or generations > 100000:
            return {"ok": False, "error": "generations must be an integer between 1 and 100000", "status_code": 400}
    except (TypeError, ValueError):
        return {"ok": False, "error": "generations must be a valid integer", "status_code": 400}

    # Workers validation
    raw_workers = params.get("workers", 2)
    if isinstance(raw_workers, bool) or isinstance(raw_workers, float):
        return {"ok": False, "error": "workers must be an integer >= 1", "status_code": 400}
    try:
        if isinstance(raw_workers, int):
            workers = raw_workers
        elif isinstance(raw_workers, str):
            s = raw_workers.strip()
            if not s.isdigit():
                return {"ok": False, "error": "workers must be a valid integer string >= 1", "status_code": 400}
            workers = int(s)
        else:
            return {"ok": False, "error": "workers must be an integer >= 1", "status_code": 400}
        if workers < 1:
            return {"ok": False, "error": "workers must be an integer >= 1", "status_code": 400}
    except (TypeError, ValueError):
        return {"ok": False, "error": "workers must be a valid integer", "status_code": 400}

    # Seeds validation
    raw_seeds = params.get("seeds") if "seeds" in params else params.get("seedsText")
    resolved_seeds: list[int] | None = None
    if raw_seeds is not None:
        try:
            resolved_seeds = parse_seeds(raw_seeds)
        except ValueError as exc:
            return {"ok": False, "error": f"Invalid seeds parameter: {exc}", "status_code": 400}

    # Budget / max_seconds validation
    raw_budget = params.get("budget") if "budget" in params else params.get("max_seconds", params.get("maxSeconds"))
    max_seconds = 1800.0
    if raw_budget is not None:
        try:
            max_seconds = float(raw_budget)
            if max_seconds <= 0 or math.isnan(max_seconds) or math.isinf(max_seconds):
                return {"ok": False, "error": "budget/max_seconds must be a positive number", "status_code": 400}
        except (TypeError, ValueError):
            return {"ok": False, "error": "budget/max_seconds must be a valid number", "status_code": 400}

    # Cores / affinity validation
    cores_val = params.get("cores")
    if cores_val is not None:
        if not isinstance(cores_val, list):
            return {"ok": False, "error": "cores must be a list of non-negative integer core IDs", "status_code": 400}
        if len(cores_val) == 0:
            return {"ok": False, "error": "cores list cannot be empty", "status_code": 400}
        for c in cores_val:
            if isinstance(c, bool) or not isinstance(c, int) or c < 0:
                return {"ok": False, "error": "cores must be a list of non-negative integer core IDs", "status_code": 400}
        if len(cores_val) != len(set(cores_val)):
            return {"ok": False, "error": "cores must not contain duplicate core IDs", "status_code": 400}
        allowed_cpus = set(get_allowed_cpu_ids())
        if not set(cores_val).issubset(allowed_cpus):
            return {"ok": False, "error": f"cores contains IDs not in allowed_cpu_ids: {sorted(set(cores_val) - allowed_cpus)}", "status_code": 400}
        cores_val = sorted(cores_val)

    track_val = str(params.get("track") or "reference").strip()
    title = str(params.get("title") or "custom_run").strip()[:40]
    clean_title = "".join(c if c.isalnum() or c in ("-", "_") else "_" for c in title).lower() or "run"
    ts = time.strftime("%Y%m%d_%H%M%S")
    uid = uuid.uuid4().hex[:8]
    run_id = f"run_{clean_title}_{ts}_{uid}"

    # Lifecycle parent directory
    run_dir = runs_directory() / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    # Scientific engine child directory (NOT pre-created!)
    engine_dir = run_dir / "output"

    repo_root = Path(__file__).resolve().parents[3]
    cmd = [sys.executable]

    script_name = params.get("scriptName") or params.get("script")
    if script_name:
        if not isinstance(script_name, str) or not script_name.endswith(".py") or Path(script_name).name != script_name:
            shutil.rmtree(run_dir, ignore_errors=True)
            return {"ok": False, "error": "Invalid scriptName", "status_code": 400}
        script_path = None
        custom_scripts_env = os.environ.get("CODONTRACE_SCRIPTS_DIR", "").strip()
        if custom_scripts_env:
            candidate = (Path(custom_scripts_env).expanduser() / script_name).resolve()
            if candidate.is_file():
                script_path = candidate
        if not script_path:
            for s_dir in (repo_root / "scripts", repo_root / "custom_tests", Path("custom_tests").resolve()):
                candidate = (s_dir / script_name).resolve()
                if candidate.is_file():
                    script_path = candidate
                    break
        if script_path and script_path.is_file():
            if script_name in ("genesis_long_board_campaign.py", "board_long_campaign.py"):
                if workers != 1 or (resolved_seeds is not None and len(resolved_seeds) != 1):
                    shutil.rmtree(run_dir, ignore_errors=True)
                    return {"ok": False, "error": "Pilot launcher uses one seed and one worker per run; launch separate cards for independent seeds", "status_code": 400}
                resolved_seeds = resolved_seeds or [42 if script_name == "genesis_long_board_campaign.py" else 7]
                exp = str(params.get("experiment", ""))
                try:
                    if isinstance(params.get("population"), (bool, float)):
                        raise ValueError("population must be an integer")
                    pop = int(params.get("population", 96 if script_name == "genesis_long_board_campaign.py" else 6))
                    if pop < 2 or pop > 100000:
                        raise ValueError("population must be between 2 and 100000")
                    from codontrace.campaigns.readiness import experiment
                    row = experiment(exp)
                    if not row["run_enabled"] or row["launch_params"]["scriptName"] != script_name:
                        raise ValueError("Experiment does not have a runnable adapter for this script")
                except (ValueError, TypeError, KeyError) as exc:
                    shutil.rmtree(run_dir, ignore_errors=True)
                    return {"ok": False, "error": str(exc), "status_code": 400}
                if script_name == "genesis_long_board_campaign.py":
                    if str(params.get("track", "REFERENCE")).upper() != "REFERENCE":
                        shutil.rmtree(run_dir, ignore_errors=True)
                        return {"ok": False, "error": "Implemented pilots have REFERENCE boundary only", "status_code": 400}
                    import runpy
                    cli_namespace = runpy.run_path(str(script_path))
                    arm = str(params.get("arm") or cli_namespace["ARMS"][exp][0])
                    if arm not in cli_namespace["ARMS"][exp]:
                        shutil.rmtree(run_dir, ignore_errors=True)
                        return {"ok": False, "error": "Invalid experiment arm", "status_code": 400}
                    recorded_config = params.get("runner_config") or {}
                    if not isinstance(recorded_config, dict):
                        shutil.rmtree(run_dir, ignore_errors=True)
                        return {"ok": False, "error": "runner_config must be an object", "status_code": 400}
                    pilot_config: dict[str, Any] = {}
                    extras: list[str] = []
                    try:
                        def config_value(name: str, default: Any) -> Any:
                            return params.get(name, recorded_config.get(name, default))
                        if exp == "T02":
                            num_demes = config_value("num_demes", 8)
                            if isinstance(num_demes, bool) or not isinstance(num_demes, int) or num_demes < 1 or pop % num_demes:
                                raise ValueError("population must be divisible by positive integer num_demes")
                            group_selection = config_value("group_selection", arm != "NO_GROUP_SELECTION")
                            high_migration = config_value("high_migration", arm == "HIGH_MIGRATION")
                            if not isinstance(group_selection, bool) or not isinstance(high_migration, bool):
                                raise ValueError("group_selection and high_migration must be booleans")
                            pilot_config = {"num_demes": num_demes, "deme_capacity": pop // num_demes, "group_selection": group_selection, "high_migration": high_migration}
                            extras = ["--num-demes", str(num_demes), "--group-selection" if group_selection else "--no-group-selection", "--high-migration" if high_migration else "--no-high-migration"]
                        elif exp == "T03":
                            rate = config_value("vertical_transmission_rate", {"VERTICAL": .75, "HORIZONTAL": 0.0, "LOW_VERTICAL": .25}[arm])
                            cost = config_value("cooperation_cost", .20)
                            if isinstance(rate, bool) or isinstance(cost, bool):
                                raise ValueError("transmission rate and cooperation cost must be numeric")
                            pilot_config = {"vertical_transmission_rate": float(rate), "cooperation_cost": float(cost)}
                            extras = ["--vertical-transmission-rate", str(rate), "--cooperation-cost", str(cost)]
                        elif exp == "T04":
                            pilot_config = {name: config_value(name, default) for name, default in (("history_count", 2), ("replay_branches", 8), ("replay_generations", None), ("snapshot_generations", None))}
                            if pilot_config["snapshot_generations"] is not None:
                                if not isinstance(pilot_config["snapshot_generations"], (list, tuple)):
                                    raise ValueError("snapshot_generations must be an integer list")
                                pilot_config["snapshot_generations"] = tuple(pilot_config["snapshot_generations"])
                            for name, value in pilot_config.items():
                                if value is not None:
                                    extras.extend(["--" + name.replace("_", "-"), ",".join(str(g) for g in value) if name == "snapshot_generations" else str(value)])
                        constructor = dict(pilot_config, seed=resolved_seeds[0], generations=generations)
                        if exp == "T02":
                            pass
                        else:
                            constructor["population_size"] = pop
                        if exp in ("T01", "T04", "T05"):
                            constructor["arm"] = arm
                        cli_namespace["RUNNERS"][exp](**constructor)
                    except (ValueError, TypeError) as exc:
                        shutil.rmtree(run_dir, ignore_errors=True)
                        return {"ok": False, "error": str(exc), "status_code": 400}
                    cmd.extend([str(script_path), "--experiment", exp, "--seed", str(resolved_seeds[0]), "--generations", str(generations), "--population", str(pop), "--arm", arm, "--console-run-id", run_id, "--base-dir", str(run_dir / "campaign_index"), *extras])
                    if "budget" in params and params["budget"] is None:
                        max_seconds = None
                    else:
                        cmd.extend(["--max-seconds", str(max_seconds)])
                else:
                    try:
                        if isinstance(params.get("ticks"), (bool, float)):
                            raise ValueError("ticks must be an integer")
                        ticks = int(params.get("ticks", 4))
                        if ticks < 2:
                            raise ValueError("ticks must be >= 2")
                    except (ValueError, TypeError) as exc:
                        shutil.rmtree(run_dir, ignore_errors=True)
                        return {"ok": False, "error": str(exc), "status_code": 400}
                    if str(params.get("arm", "uninterrupted")) != "uninterrupted":
                        shutil.rmtree(run_dir, ignore_errors=True)
                        return {"ok": False, "error": "T11 calibration launch supports uninterrupted only", "status_code": 400}
                    cmd.extend([str(script_path), "run", "--experiment", "T11", "--seed", str(resolved_seeds[0]), "--ticks", str(ticks), "--population", str(pop), "--workers", "1", "--arm", "uninterrupted", "--output", str(engine_dir)])
            else:
                cmd.extend([str(script_path), "--output", str(engine_dir)])
        else:
            shutil.rmtree(run_dir, ignore_errors=True)
            return {"ok": False, "error": f"Script '{script_name}' not found", "status_code": 404}
    else:
        engine_script = repo_root / "scripts" / "rq_full_engine_parallel.py"
        if not engine_script.is_file():
            shutil.rmtree(run_dir, ignore_errors=True)
            return {"ok": False, "error": "Simulation engine script 'rq_full_engine_parallel.py' not found", "status_code": 404}

        cmd.extend([
            str(engine_script),
            "--output", str(engine_dir),
            "--generations", str(generations),
            "--workers", str(workers),
            "--max-seconds", str(max_seconds),
        ])
        if resolved_seeds:
            cmd.extend([
                "--seeds", ",".join(str(s) for s in resolved_seeds),
                "--histories", str(len(resolved_seeds)),
                "--seed-start", str(min(resolved_seeds)),
            ])
            
        if track_val and track_val != "reference":
            cmd.extend(["--track", track_val])

    # Shared affinity command prefix for all runners (Linux taskset)
    if cores_val and (sys.platform == "linux" or shutil.which("taskset")):
        if shutil.which("taskset"):
            cmd = ["taskset", "-c", ",".join(map(str, cores_val))] + cmd

    started_at = time.time()
    if script_name:
        s_lower = script_name.lower()
        if s_lower == "genesis_long_board_campaign.py":
            engine_backend = "reference_experiment"
            model_scope = "standalone_reference_model"
            boundary_notice = "Standalone REFERENCE pilot, not GenesisEngine execution."
        elif s_lower == "board_long_campaign.py":
            engine_backend = "genesis_engine"
            model_scope = "engine_calibration"
            boundary_notice = "T11 GenesisEngine calibration; scientific campaign not assessed."
        elif "frontier" in s_lower or "challenge" in s_lower:
            engine_backend = "frontier_reference_model"
            model_scope = "frontier_reference_exploration"
            boundary_notice = "Isolated mathematical reference exploration model executing on dedicated CPU core; distinct from full GenesisEngine codon VM."
        else:
            engine_backend = "custom_script"
            model_scope = "script_execution"
            boundary_notice = f"Custom script execution: {script_name}."
    else:
        engine_backend = "genesis_engine"
        model_scope = "full_digital_organism_simulation"
        boundary_notice = "Full Genesis digital organism coevolution engine with codon translation, contact dynamics, and biological assays."

    execution_boundary = {
        "backend": engine_backend,
        "engineBackend": engine_backend,
        "modelScope": model_scope,
        "boundaryNotice": boundary_notice,
        "isFrontierReference": (engine_backend == "frontier_reference_model"),
        "isGenesisEngine": (engine_backend == "genesis_engine"),
    }

    adapter = get_runner_adapter(
        {"executionBoundary": execution_boundary, "params": {"scriptName": script_name}},
        script_name=script_name,
    )
    capabilities_dict = adapter.resolve_capabilities(run_dir)
    if script_name == "genesis_long_board_campaign.py":
        capabilities_dict["cooperative_stop"] = True
    elif script_name == "board_long_campaign.py":
        capabilities_dict = {"pause": False, "resume": False, "checkpoint_continue": False}

    effective_affinity = list(cores_val) if cores_val is not None else None

    param_record = {
        "generations": generations,
        "experiment": params.get("experiment"),
        "population": pop if script_name in ("genesis_long_board_campaign.py", "board_long_campaign.py") else params.get("population"),
        "runner_config": pilot_config if script_name == "genesis_long_board_campaign.py" else params.get("runner_config"),
        "ticks": ticks if script_name == "board_long_campaign.py" else params.get("ticks"),
        "arm": params.get("arm"),
        "workers": workers,
        "seeds": resolved_seeds,
        "budget": max_seconds,
        "track": track_val,
        "cores": cores_val,
        "effective_affinity": effective_affinity,
        "effectiveAffinity": effective_affinity,
        "title": title,
        "scriptName": script_name,
        "backend": engine_backend,
        "engineBackend": engine_backend,
        "modelScope": model_scope,
        "capabilities": capabilities_dict,
    }

    manifest_info = {
        "schemaVersion": 1,
        "runId": run_id,
        "title": title,
        "startedAt": started_at,
        "command": cmd,
        "params": param_record,
        "effective_affinity": effective_affinity,
        "effectiveAffinity": effective_affinity,
        "capabilities": capabilities_dict,
        "executionBoundary": execution_boundary,
        "configDigest": hashlib.sha256(json.dumps(param_record, sort_keys=True).encode("utf-8")).hexdigest()[:16],
    }
    try:
        manifest_info["source_sha"] = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo_root, text=True, stderr=subprocess.DEVNULL).strip()
        manifest_info["source_dirty"] = bool(subprocess.check_output(["git", "status", "--porcelain"], cwd=repo_root, text=True))
    except (OSError, subprocess.SubprocessError):
        manifest_info["source_sha"] = "UNKNOWN"
    write_atomic_json(run_dir / "run_manifest.json", manifest_info)

    status_info = {
        "schemaVersion": 1,
        "runId": run_id,
        "status": "STARTING",
        "title": title,
        "startedAt": started_at,
        "pct": 0.0,
        "completedSeeds": 0,
        "totalSeeds": len(resolved_seeds) if resolved_seeds else 12,
        "params": param_record,
        "effective_affinity": effective_affinity,
        "effectiveAffinity": effective_affinity,
        "capabilities": capabilities_dict,
        "backend": engine_backend,
        "engineBackend": engine_backend,
        "modelScope": model_scope,
    }
    write_atomic_json(run_dir / "status.json", status_info)

    log_path = run_dir / "console.log"
    child_env = dict(os.environ)
    child_env["CODONTRACE_RUNS_DIR"] = str(runs_directory().resolve())
    try:
        with open(log_path, "w", encoding="utf-8") as log_fp:
            proc = subprocess.Popen(cmd, stdout=log_fp, stderr=subprocess.STDOUT, cwd=str(repo_root), env=child_env)
    except OSError as exc:
        status_info.update({"status": "FAILED", "endedAt": time.time(), "errorReason": str(exc)})
        write_atomic_json(run_dir / "status.json", status_info)
        return {"ok": False, "error": f"Process launch failed: {exc}", "runId": run_id, "status_code": 500}

    if cores_val and sys.platform == "win32":
        apply_windows_affinity(proc, cores_val)

    with _RUN_LOCK:
        _RUN_PROCESSES[run_id] = proc
        _RUN_FINALIZERS[run_id] = threading.Event()

    (run_dir / "run.pid").write_text(f"{proc.pid}\n", encoding="utf-8")
    identity = _process_identity(proc.pid)
    if identity is not None:
        write_atomic_json(run_dir / "process_identity.json", identity)
        status_info["process_identity"] = identity

    try:
        current_child_status = json.loads((run_dir / "status.json").read_text(encoding="utf-8"))
        if current_child_status.get("revision", 0) > status_info.get("revision", 0):
            status_info = current_child_status
    except (OSError, ValueError):
        pass
    if status_info.get("status") == "STARTING":
        status_info["status"] = "RUNNING"
    status_info["pid"] = proc.pid
    write_atomic_json(run_dir / "status.json", status_info)

    watcher_thread = threading.Thread(
        target=_watch_run_process,
        args=(run_id, proc, run_dir, engine_dir),
        daemon=True,
    )
    watcher_thread.start()

    return {
        "ok": True,
        "runId": run_id,
        "pid": proc.pid,
        "path": str(run_dir),
    }

