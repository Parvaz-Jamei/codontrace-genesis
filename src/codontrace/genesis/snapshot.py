"""RunSnapshot v2 schema, data models, and runtime validation.

Single source of truth for simulation run telemetry and lifecycle state
across the engine, coordinator, control API, and web console.
Complies with AUDIT_P01_L05_PHASES1_4 section 3 contract.
"""

from __future__ import annotations

import datetime
import math
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from codontrace.errors import ConfigurationError

SCHEMA_VERSION = "run_snapshot_v2"

VALID_STATES: tuple[str, ...] = (
    "QUEUED",
    "STARTING",
    "RUNNING",
    "PAUSING",
    "PAUSED",
    "RESUMING",
    "STOPPING",
    "STOPPED",
    "COMPLETED",
    "FAILED",
)

VALID_PROGRESS_KINDS: tuple[str, ...] = (
    "work_units",
    "generations",
    "seeds",
    "time_budget",
    "indeterminate",
)


@dataclass(frozen=True, slots=True)
class CapabilitiesV2:
    pause: bool = True
    resume: bool = True
    checkpoint_continue: bool = False

    def to_dict(self) -> dict[str, bool]:
        return {
            "pause": bool(self.pause),
            "resume": bool(self.resume),
            "checkpoint_continue": bool(self.checkpoint_continue),
        }


@dataclass(frozen=True, slots=True)
class ProgressV2:
    kind: str = "work_units"
    stage: str = "simulation"
    done: float = 0.0
    total: float = 100.0
    pct: float | None = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "stage": self.stage,
            "done": self.done,
            "total": self.total,
            "pct": self.pct,
        }


@dataclass(frozen=True, slots=True)
class RunSnapshotV2:
    run_id: str
    session_id: str
    revision: int = 1
    state: str = "STARTING"
    requested_state: str | None = None
    capabilities: CapabilitiesV2 = CapabilitiesV2()
    workers_expected: int = 1
    workers_paused: int = 0
    progress: ProgressV2 = ProgressV2()
    active_elapsed_seconds: float = 0.0
    paused_seconds: float = 0.0
    wall_elapsed_seconds: float = 0.0
    heartbeat_at: str = ""
    pending_command_id: str | None = None
    schema_version: str = SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "run_id": self.run_id,
            "session_id": self.session_id,
            "revision": self.revision,
            "state": self.state,
            "requested_state": self.requested_state,
            "capabilities": self.capabilities.to_dict(),
            "workers_expected": self.workers_expected,
            "workers_paused": self.workers_paused,
            "progress": self.progress.to_dict(),
            "active_elapsed_seconds": self.active_elapsed_seconds,
            "paused_seconds": self.paused_seconds,
            "wall_elapsed_seconds": self.wall_elapsed_seconds,
            "heartbeat_at": self.heartbeat_at,
            "pending_command_id": self.pending_command_id,
        }


def validate_run_snapshot(data: Mapping[str, Any]) -> dict[str, Any]:
    """Validate a RunSnapshot dictionary against schema_version run_snapshot_v2.

    Raises ConfigurationError if the snapshot violates invariants.
    Returns the validated dictionary.
    """
    if not isinstance(data, Mapping):
        raise ConfigurationError("RunSnapshot must be a dictionary/mapping")

    sv = data.get("schema_version")
    if sv != SCHEMA_VERSION:
        raise ConfigurationError(f"Invalid schema_version {sv!r}, expected {SCHEMA_VERSION!r}")

    run_id = data.get("run_id")
    if not isinstance(run_id, str) or not run_id.strip():
        raise ConfigurationError("RunSnapshot run_id must be a non-empty string")

    session_id = data.get("session_id")
    if not isinstance(session_id, str):
        raise ConfigurationError("RunSnapshot session_id must be a string")

    rev = data.get("revision")
    if type(rev) is not int or rev < 0:
        raise ConfigurationError(f"RunSnapshot revision must be non-negative int, got {rev!r}")

    state = data.get("state")
    if state not in VALID_STATES:
        raise ConfigurationError(f"RunSnapshot state {state!r} not in valid states: {VALID_STATES}")

    req_state = data.get("requested_state")
    if req_state is not None and req_state not in VALID_STATES:
        raise ConfigurationError(f"RunSnapshot requested_state {req_state!r} invalid")

    caps = data.get("capabilities")
    if not isinstance(caps, Mapping):
        raise ConfigurationError("RunSnapshot capabilities must be a mapping")
    for k in ("pause", "resume", "checkpoint_continue"):
        if k in caps and not isinstance(caps[k], bool):
            raise ConfigurationError(f"RunSnapshot capability {k} must be boolean")

    we = data.get("workers_expected", 0)
    if type(we) is not int or we < 0:
        raise ConfigurationError(f"RunSnapshot workers_expected must be non-negative int, got {we!r}")

    wp = data.get("workers_paused", 0)
    if type(wp) is not int or wp < 0 or wp > max(we, 1):
        raise ConfigurationError(f"RunSnapshot workers_paused {wp!r} out of bounds")

    prog = data.get("progress")
    if not isinstance(prog, Mapping):
        raise ConfigurationError("RunSnapshot progress must be a mapping")

    p_kind = prog.get("kind", "work_units")
    if p_kind not in VALID_PROGRESS_KINDS:
        raise ConfigurationError(f"RunSnapshot progress.kind {p_kind!r} invalid")

    p_stage = prog.get("stage", "simulation")
    if not isinstance(p_stage, str):
        raise ConfigurationError("RunSnapshot progress.stage must be string")

    done = prog.get("done", 0.0)
    if not isinstance(done, (int, float)) or not math.isfinite(done) or done < 0:
        raise ConfigurationError(f"RunSnapshot progress.done must be finite non-negative number, got {done!r}")

    total = prog.get("total", 0.0)
    if not isinstance(total, (int, float)) or not math.isfinite(total) or total < 0:
        raise ConfigurationError(f"RunSnapshot progress.total must be finite non-negative number, got {total!r}")

    pct = prog.get("pct")
    if pct is not None:
        if isinstance(pct, bool) or not isinstance(pct, (int, float)) or not math.isfinite(pct):
            raise ConfigurationError(f"RunSnapshot progress.pct must be finite number or None, got {pct!r}")
        if pct < 0.0 or pct > 100.0:
            raise ConfigurationError(f"RunSnapshot progress.pct out of 0..100 bounds: {pct!r}")

    for time_field in ("active_elapsed_seconds", "paused_seconds", "wall_elapsed_seconds"):
        val = data.get(time_field, 0.0)
        if isinstance(val, bool) or not isinstance(val, (int, float)) or not math.isfinite(val) or val < 0:
            raise ConfigurationError(f"RunSnapshot {time_field} must be finite non-negative number, got {val!r}")

    hb = data.get("heartbeat_at", "")
    if not isinstance(hb, str):
        raise ConfigurationError("RunSnapshot heartbeat_at must be string")

    return dict(data)


def create_run_snapshot(
    run_id: str,
    session_id: str,
    *,
    revision: int = 1,
    state: str = "RUNNING",
    requested_state: str | None = None,
    supports_pause: bool = True,
    supports_resume: bool = True,
    supports_checkpoint: bool = False,
    capabilities: Mapping[str, bool] | None = None,
    workers_expected: int = 1,
    workers_paused: int = 0,
    progress_kind: str = "work_units",
    progress_stage: str = "simulation",
    done: float = 0.0,
    total: float = 100.0,
    pct: float | None = None,
    active_elapsed: float = 0.0,
    active_elapsed_seconds: float | None = None,
    paused_elapsed: float = 0.0,
    paused_seconds: float | None = None,
    wall_elapsed: float = 0.0,
    wall_elapsed_seconds: float | None = None,
    heartbeat_at: str | None = None,
    pending_command_id: str | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    """Helper to construct and validate a RunSnapshot dictionary."""
    if capabilities is not None:
        supports_pause = bool(capabilities.get("pause", supports_pause))
        supports_resume = bool(capabilities.get("resume", supports_resume))
        supports_checkpoint = bool(capabilities.get("checkpoint_continue", supports_checkpoint))

    if active_elapsed_seconds is not None:
        active_elapsed = active_elapsed_seconds
    if paused_seconds is not None:
        paused_elapsed = paused_seconds
    if wall_elapsed_seconds is not None:
        wall_elapsed = wall_elapsed_seconds

    if pct is None and total > 0:
        raw_pct = (done / total) * 100.0
        pct = round(max(0.0, min(100.0, raw_pct)), 1)

    if heartbeat_at is None:
        heartbeat_at = datetime.datetime.now(datetime.UTC).isoformat()

    snapshot = RunSnapshotV2(
        run_id=run_id,
        session_id=session_id,
        revision=revision,
        state=state,
        requested_state=requested_state,
        capabilities=CapabilitiesV2(
            pause=supports_pause,
            resume=supports_resume,
            checkpoint_continue=supports_checkpoint,
        ),
        workers_expected=workers_expected,
        workers_paused=workers_paused,
        progress=ProgressV2(
            kind=progress_kind,
            stage=progress_stage,
            done=float(done),
            total=float(total),
            pct=pct,
        ),
        active_elapsed_seconds=float(active_elapsed),
        paused_seconds=float(paused_elapsed),
        wall_elapsed_seconds=float(wall_elapsed),
        heartbeat_at=heartbeat_at,
        pending_command_id=pending_command_id,
    )
    return validate_run_snapshot(snapshot.to_dict())
