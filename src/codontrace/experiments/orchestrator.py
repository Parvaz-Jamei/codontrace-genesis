"""Local, observable experiment execution with an explicit scientific boundary.

A completed computation is independent of scientific support. All artifacts are
published before the runner starts and append-only metrics survive interruption.
"""

from __future__ import annotations

import hashlib
import inspect
import json
import logging
import math
import os
import platform
import re
import subprocess
import sys
import threading
import time
import uuid
from dataclasses import replace
from pathlib import Path
from typing import Any

from codontrace.console.runs import get_allowed_cpu_ids, runs_directory, write_atomic_json
from codontrace.experiments.models import AssessmentStatus, CompletionSummary, ExecutionTrack


class RunStopped(Exception):
    """Cooperative stop acknowledged at a generation boundary."""


def _safe(value: Any) -> str:
    return re.sub(r"[^A-Za-z0-9_-]", "_", str(value))[:64] or "default"


class CampaignOrchestrator:
    def __init__(
        self, base_dir: Path, campaign_id: str, *, console_run_id: str | None = None, max_seconds: float | None = None
    ) -> None:
        self.base_dir = Path(base_dir)
        self.campaign_id = _safe(campaign_id)
        self.campaign_dir = self.base_dir / self.campaign_id
        self.campaign_dir.mkdir(parents=True, exist_ok=True)
        if max_seconds is not None and (not math.isfinite(max_seconds) or max_seconds <= 0):
            raise ValueError("max_seconds must be finite and positive")
        self.max_seconds = max_seconds
        self.console_run_id = console_run_id
        self.last_run_dir: Path | None = None
        self.heartbeat_seconds = 5.0

    def get_allowed_cpus(self) -> list[int]:
        return get_allowed_cpu_ids()

    def _resolve_console_runs_dir(self) -> Path:
        return runs_directory()

    def run_experiment(self, runner: Any) -> CompletionSummary:
        exp_id = str(getattr(runner, "experiment_id", runner.__class__.__name__))
        seed = int(runner.seed)
        arm = str(getattr(runner, "arm", "DEFAULT"))
        if arm == "DEFAULT" and exp_id.startswith("T02"):
            arm = (
                "HIGH_MIGRATION"
                if getattr(runner, "high_migration", False)
                else ("GROUP_SELECTION" if getattr(runner, "group_selection", True) else "NO_GROUP_SELECTION")
            )
        elif arm == "DEFAULT" and exp_id.startswith("T03"):
            rate = getattr(runner, "vertical_transmission_rate", 0.75)
            arm = "HORIZONTAL" if rate == 0 else "LOW_VERTICAL" if rate == 0.25 else "VERTICAL"
        requested_generations = int(getattr(runner, "generations", 0))
        horizon = int(getattr(runner, "planned_work_units", requested_generations))
        population = int(getattr(runner, "population_size", 0))
        if seed < 0:
            raise ValueError("seed must be nonnegative")
        if horizon < 1 or population < 1:
            raise ValueError("generations and population_size must be positive")
        track = getattr(runner, "track", ExecutionTrack.REFERENCE)
        if track != ExecutionTrack.REFERENCE:
            raise ValueError("These runners implement REFERENCE models; ENGINE requires its own connected runner")
        session_id = uuid.uuid4().hex
        seed_slug = str(seed) if len(str(seed)) <= 16 else hashlib.sha256(str(seed).encode()).hexdigest()[:16]
        run_id = (
            self.console_run_id
            or f"genesis_{self.campaign_id[:24]}_{_safe(exp_id)[:24]}_s{seed_slug}_{_safe(arm)[:24]}_{session_id[:12]}"
        )
        from codontrace.console.runs import validate_run_id

        if not validate_run_id(run_id):
            raise ValueError("invalid console run ID")
        run_dir = self._resolve_console_runs_dir() / run_id
        if run_dir.exists() and not self.console_run_id:
            raise FileExistsError(run_dir)
        if (run_dir / "run_manifest.json").exists() and self.console_run_id:
            existing = json.loads((run_dir / "run_manifest.json").read_text(encoding="utf-8"))
            if existing.get("session_id"):
                raise FileExistsError("refusing to reuse an existing execution session")
        if (run_dir / "execution.json").exists() or (run_dir / "COMPLETE").exists():
            raise FileExistsError("refusing to overwrite prior run artifacts")
        run_dir.mkdir(parents=True, exist_ok=True)
        self.last_run_dir = run_dir
        # Campaign index contains references, never a second competing artifact set.
        index = self.campaign_dir / "runs" / run_id
        index.mkdir(parents=True, exist_ok=False)
        write_atomic_json(index / "run_reference.json", {"runId": run_id, "path": str(run_dir.resolve())})
        root = Path(__file__).resolve().parents[3]
        try:
            source_sha = subprocess.check_output(
                ["git", "rev-parse", "HEAD"], cwd=root, text=True, stderr=subprocess.DEVNULL
            ).strip()
            dirty = bool(subprocess.check_output(["git", "status", "--porcelain"], cwd=root, text=True))
            source_diff = subprocess.check_output(["git", "diff", "HEAD"], cwd=root)
            source_diff_hash = hashlib.sha256(source_diff).hexdigest()
        except (OSError, subprocess.SubprocessError):
            source_sha, dirty, source_diff_hash = "UNKNOWN", None, None
        callback_supported = "on_generation" in inspect.signature(runner.run).parameters
        caps = {
            "pause": callback_supported,
            "resume": callback_supported,
            "checkpoint_continue": False,
            "cooperative_stop": callback_supported,
        }
        params = {
            "scriptName": "genesis_long_board_campaign.py",
            "experiment": exp_id[:3],
            "seed": seed,
            "seeds": [seed],
            "arm": arm,
            "generations": requested_generations,
            "planned_work_units": horizon,
            "population": population,
            "workers": 1,
            "track": "REFERENCE",
            "campaign_id": self.campaign_id,
            "base_dir": str(self.base_dir.resolve()),
            "budget": self.max_seconds,
        }
        runner_config = {}
        for field in inspect.signature(runner.__class__.__init__).parameters:
            value = getattr(runner, field, None)
            if field != "self" and (isinstance(value, (str, int, float, bool, tuple, list)) or value is None):
                runner_config[field] = value
        params["runner_config"] = runner_config
        config_digest = hashlib.sha256(json.dumps(params, sort_keys=True).encode()).hexdigest()
        started = time.time()
        started_monotonic = time.monotonic()
        boundary = {
            "engineBackend": "reference_experiment",
            "backend": "reference_experiment",
            "isGenesisEngine": False,
            "isFrontierReference": False,
            "modelScope": "standalone_reference_model",
            "modelBoundaryNotice": "Standalone REFERENCE pilot; no GenesisEngine VM execution is claimed.",
        }
        command = [
            sys.executable,
            str(root / "scripts/genesis_long_board_campaign.py"),
            "--experiment",
            exp_id[:3],
            "--seed",
            str(seed),
            "--arm",
            arm,
            "--generations",
            str(requested_generations),
            "--population",
            str(population),
            "--campaign-id",
            self.campaign_id,
            "--base-dir",
            str(self.base_dir.resolve()),
        ]
        if self.max_seconds is not None:
            command.extend(["--max-seconds", str(self.max_seconds)])
        if exp_id.startswith("T02"):
            command.extend(
                [
                    "--num-demes",
                    str(runner.num_demes),
                    "--group-selection" if runner.group_selection else "--no-group-selection",
                    "--high-migration" if runner.high_migration else "--no-high-migration",
                ]
            )
        elif exp_id.startswith("T04") and hasattr(runner, "replay_branches"):
            command.extend(
                [
                    "--replay-branches",
                    str(runner.replay_branches),
                    "--replay-generations",
                    str(runner.replay_generations),
                    "--history-count",
                    str(runner.history_count),
                    "--snapshot-generations",
                    ",".join(str(g) for g in runner.snapshot_generations),
                ]
            )
        elif exp_id.startswith("T03"):
            command.extend(
                [
                    "--vertical-transmission-rate",
                    str(runner.vertical_transmission_rate),
                    "--cooperation-cost",
                    str(runner.cooperation_cost),
                ]
            )
        manifest = {
            "schemaVersion": 2,
            "runId": run_id,
            "title": f"{exp_id} / seed {seed} / {arm}",
            "startedAt": started,
            "session_id": session_id,
            "params": params,
            "command": command,
            "source_sha": source_sha,
            "source_dirty": dirty,
            "source_diff_sha256": source_diff_hash,
            "configDigest": config_digest,
            "platform_info": {"system": platform.system(), "release": platform.release()},
            "allowed_cpu_ids": self.get_allowed_cpus(),
            "capabilities": caps,
            "executionBoundary": boundary,
        }
        write_atomic_json(run_dir / "run_manifest.json", manifest)
        (run_dir / "run.pid").write_text(f"{os.getpid()}\n", encoding="utf-8")
        status: dict[str, Any] = {
            "runId": run_id,
            "title": manifest["title"],
            "session_id": session_id,
            "status": "RUNNING",
            "startedAt": started,
            "pid": os.getpid(),
            "revision": 0,
            "params": params,
            "capabilities": caps,
            "engineBackend": "reference_experiment",
            "pct": 0.0,
            "completed_seeds": 0,
            "total_seeds": 1,
            "work_done": 0,
            "work_total": horizon,
            "paused_seconds": 0.0,
        }
        done, last_tick = 0, 0
        completed_paused_seconds = 0.0
        pause_started: float | None = None
        logger = logging.getLogger(f"genesis.run.{run_id}")
        logger.setLevel(logging.INFO)
        logger.propagate = False
        handler = logging.FileHandler(run_dir / "live.log", encoding="utf-8")
        handler.setFormatter(logging.Formatter("%(asctime)s %(message)s"))
        logger.addHandler(handler)

        state_lock = threading.RLock()

        def _persist_locked() -> None:
            # Read latest action revision so acknowledgements never travel backwards.
            try:
                previous = json.loads((run_dir / "status.json").read_text(encoding="utf-8"))
                status["revision"] = max(status["revision"], int(previous.get("revision", 0)))
            except (OSError, ValueError, TypeError):
                pass
            status["revision"] += 1
            status["heartbeat_at"] = time.time()
            status["work_done"] = done
            status["pct"] = min(100.0, 100.0 * done / max(1, status["work_total"]))
            ongoing_pause = max(0.0, time.monotonic() - pause_started) if pause_started is not None else 0.0
            status["paused_seconds"] = completed_paused_seconds + ongoing_pause
            status["active_elapsed_seconds"] = max(0.0, time.monotonic() - started_monotonic - status["paused_seconds"])
            write_atomic_json(run_dir / "status.json", status)

        def persist() -> None:
            with state_lock:
                _persist_locked()

        def cooperate() -> None:
            nonlocal completed_paused_seconds, pause_started
            if (run_dir / "STOP").exists():
                raise RunStopped("USER_REQUEST")
            if (
                self.max_seconds is not None
                and time.monotonic() - started_monotonic - completed_paused_seconds >= self.max_seconds
            ):
                raise RunStopped("TIME_BUDGET")
            if (run_dir / "PAUSE").exists():
                pause_started = time.monotonic()
                ack = run_dir / f"ack_paused_{os.getpid()}"
                ack.write_text(session_id, encoding="utf-8")
                status["status"] = "PAUSED"
                persist()
                try:
                    while (run_dir / "PAUSE").exists():
                        if (run_dir / "STOP").exists():
                            raise RunStopped("USER_REQUEST")
                        time.sleep(0.1)
                finally:
                    with state_lock:
                        completed_paused_seconds += time.monotonic() - pause_started
                        pause_started = None
                    ack.unlink(missing_ok=True)
                status["status"] = "RUNNING"
                persist()

        summary: CompletionSummary
        metrics_digest = hashlib.sha256()
        persist()
        logger.info("Starting %s seed=%s arm=%s boundary=REFERENCE", exp_id, seed, arm)
        heartbeat_stop = threading.Event()

        def heartbeat() -> None:
            while not heartbeat_stop.wait(self.heartbeat_seconds):
                persist()
                logger.info("heartbeat work=%s/%s state=%s", done, horizon, status["status"])

        heartbeat_thread = threading.Thread(target=heartbeat, daemon=True, name=f"heartbeat-{run_id}")
        heartbeat_thread.start()
        try:
            with (run_dir / "metrics.jsonl").open("a", encoding="utf-8", newline="\n") as metrics:

                def on_generation(record: Any) -> None:
                    nonlocal done, last_tick
                    payload = record.to_dict() if hasattr(record, "to_dict") else dict(record)
                    generation = int(payload["generation"])
                    if generation != done + 1 or generation > horizon:
                        raise ValueError("nonsequential/out-of-horizon generation record")
                    line = json.dumps(payload, allow_nan=False) + "\n"
                    metrics.write(line)
                    metrics_digest.update(line.encode("utf-8"))
                    metrics.flush()
                    done = generation
                    last_tick = int(payload.get("tick", 0))
                    logger.info(
                        "generation=%d/%d primary=%s value=%s",
                        done,
                        horizon,
                        payload.get("primary_metric_name"),
                        payload.get("primary_metric_value"),
                    )
                    persist()
                    history = getattr(runner, "metrics_history", None)
                    if isinstance(history, list) and callback_supported:
                        history.clear()
                    cooperate()

                cooperate()
                raw = runner.run(on_generation=on_generation) if callback_supported else runner.run()
                if not isinstance(raw, CompletionSummary):
                    raise TypeError("runner did not return a CompletionSummary")
                summary = raw
                if not callback_supported:
                    for record in getattr(runner, "metrics_history", []):
                        on_generation(record)
                extinction = summary.status == "EXTINCT" and summary.stop_reason == "EXTINCTION" and done > 0
                ensemble = False
                if (
                    exp_id.startswith("T04")
                    and summary.status == "COMPLETED"
                    and summary.stop_reason == "ENSEMBLE_FINISHED"
                ):
                    details = summary.summary_metrics
                    ensemble = (
                        details.get("replay_ensemble_implemented") is True
                        and details.get("planned_work_units") == horizon
                        and details.get("completed_work_units") == done
                        and summary.completed_generations == done
                        and len(details.get("history_hashes", [])) == getattr(runner, "history_count", 0)
                        and len(details.get("branches", []))
                        == len(details.get("snapshots", [])) * (getattr(runner, "replay_branches", 0) + 1)
                        and done
                        == sum(h.get("completed_generations", 0) for h in details.get("history_hashes", []))
                        + sum(b.get("completed_generations", 0) for b in details.get("branches", []))
                        and all(
                            h.get("completed_generations") == requested_generations
                            or h.get("stop_reason") == "EXTINCTION"
                            for h in details.get("history_hashes", [])
                        )
                        and all(
                            b.get("completed_generations") == getattr(runner, "replay_generations", 0)
                            or b.get("stop_reason") == "EXTINCTION"
                            for b in details.get("branches", [])
                        )
                    )
                complete = (
                    summary.status == "COMPLETED"
                    and summary.completed_generations == horizon
                    and done == horizon
                    or extinction
                    and summary.completed_generations == done
                    or ensemble
                ) and not summary.summary_metrics.get("stub")
                if (extinction or ensemble) and complete:
                    summary = replace(summary, status="COMPLETED")
                    status["planned_work_units"] = horizon
                    status["planned_generations"] = requested_generations
                    status["work_total"] = done
                if not complete:
                    summary = replace(
                        summary,
                        status="FAILED",
                        stop_reason="INCOMPLETE_OR_UNIMPLEMENTED",
                        scientific_assessment=AssessmentStatus.UNASSESSED,
                    )
        except RunStopped as exc:
            summary = CompletionSummary(
                exp_id,
                track,
                seed,
                done,
                last_tick,
                "STOPPED",
                str(exc) or "USER_REQUEST",
                AssessmentStatus.UNASSESSED,
                None,
                {"arm": arm, "partial": True},
            )
        except BaseException as exc:
            status["status"] = "FAILED"
            status["errorReason"] = f"{type(exc).__name__}: {exc}"
            status["endedAt"] = time.time()
            persist()
            write_atomic_json(
                run_dir / "execution.json",
                {
                    "runId": run_id,
                    "complete": False,
                    "failed": True,
                    "error": status["errorReason"],
                    "executionBoundary": boundary,
                },
            )
            logger.exception("Run failed")
            raise
        finally:
            heartbeat_stop.set()
            heartbeat_thread.join(timeout=1.0)
            logger.removeHandler(handler)
            handler.close()
        summary_data = summary.to_dict()
        status["status"] = summary.status
        status["completed_seeds"] = 1 if summary.status == "COMPLETED" else 0
        status["endedAt"] = time.time()
        status["summary"] = summary_data
        persist()
        write_atomic_json(run_dir / "completion.json", summary_data)
        write_atomic_json(
            run_dir / "execution.json",
            {
                "runId": run_id,
                "complete": summary.status == "COMPLETED",
                "failed": summary.status == "FAILED",
                "summary": summary_data,
                "executionBoundary": boundary,
                "engine_backend": "reference_experiment",
            },
        )
        hashes = {"metrics.jsonl": metrics_digest.hexdigest()}
        for artifact in ("run_manifest.json", "completion.json", "execution.json"):
            hashes[artifact] = hashlib.sha256((run_dir / artifact).read_bytes()).hexdigest()
        write_atomic_json(
            run_dir / "artifacts_manifest.json",
            {
                "schema_version": 1,
                "runId": run_id,
                "files": hashes,
                "metric_records": done,
                "partial": summary.status != "COMPLETED",
            },
        )
        if summary.status == "COMPLETED":
            (run_dir / "COMPLETE").write_text(run_id + "\n", encoding="utf-8")
        return summary
