"""Orchestrator for Genesis Long Board Campaign.

Manages execution, logging, CPU affinity, and directory structure.
"""

from __future__ import annotations

import json
import logging
import os
import platform
import subprocess
from pathlib import Path
from typing import Any

from codontrace.experiments.models import (
    AssessmentStatus,
    CompletionSummary,
    ExecutionTrack,
    ExperimentManifest,
)


class CampaignOrchestrator:
    def __init__(self, base_dir: Path, campaign_id: str) -> None:
        self.base_dir = base_dir
        self.campaign_id = campaign_id
        self.campaign_dir = self.base_dir / self.campaign_id
        self.campaign_dir.mkdir(parents=True, exist_ok=True)

    def _setup_run_dir(self, experiment_id: str, seed: int, arm: str) -> Path:
        run_dir = self.campaign_dir / "runs" / experiment_id / f"seed_{seed}" / f"arm_{arm}"
        run_dir.mkdir(parents=True, exist_ok=True)
        return run_dir

    def get_allowed_cpus(self) -> list[int]:
        if platform.system() == "Linux":
            try:
                output = subprocess.check_output(["taskset", "-p", "-c", str(os.getpid())], text=True)
                # Parse output, e.g., "pid 1234's current affinity list: 0-3"
                if ":" in output:
                    cpus_str = output.split(":")[1].strip()
                    cpus: list[int] = []
                    for part in cpus_str.split(","):
                        if "-" in part:
                            start, end = map(int, part.split("-"))
                            cpus.extend(range(start, end + 1))
                        else:
                            cpus.append(int(part))
                    return cpus
            except Exception:
                pass
        return list(range(os.cpu_count() or 1))

    def run_experiment(self, runner: Any) -> CompletionSummary:
        exp_id = getattr(runner, "experiment_id", runner.__class__.__name__)
        arm = getattr(runner, "arm", "DEFAULT")
        seed = runner.seed
        
        run_dir = self._setup_run_dir(exp_id, seed, arm)

        # 1. Manifest
        manifest = ExperimentManifest(
            experiment_id=exp_id,
            track=getattr(runner, "track", ExecutionTrack.ENGINE),
            backend_class=runner.__class__.__name__,
            source_sha="UNKNOWN",
            seed=seed,
            generations=getattr(runner, "generations", 100),
            population_size=getattr(runner, "population_size", 96),
            worker_affinity=None,
            platform_info={"system": platform.system(), "release": platform.release()}
        )
        with open(run_dir / "manifest.json", "w", encoding="utf-8") as f:
            json.dump(manifest.to_dict(), f, indent=2)

        # 2. live.log
        log_file = run_dir / "live.log"
        logger = logging.getLogger(f"{exp_id}_{seed}_{arm}")
        logger.setLevel(logging.INFO)
        fh = logging.FileHandler(log_file)
        fh.setFormatter(logging.Formatter("%(asctime)s - %(message)s"))
        logger.addHandler(fh)

        # 3. status.json
        status = {"status": "RUNNING"}
        with open(run_dir / "status.json", "w", encoding="utf-8") as f:
            json.dump(status, f, indent=2)

        # 4. Run and metrics.jsonl
        logger.info("Starting run")
        metrics_file = run_dir / "metrics.jsonl"

        summary: CompletionSummary
        if hasattr(runner, "run"):
            raw_summary = runner.run()
            if isinstance(raw_summary, CompletionSummary):
                summary = raw_summary
            else:
                summary = CompletionSummary(
                    experiment_id=exp_id,
                    track=getattr(runner, "track", ExecutionTrack.ENGINE),
                    seed=seed,
                    completed_generations=getattr(runner, "generations", 100),
                    total_ticks=getattr(runner, "generations", 100) * 16,
                    status="COMPLETED",
                    stop_reason="HORIZON_REACHED",
                    scientific_assessment=AssessmentStatus.NOT_SUPPORTED,
                    primary_endpoint_value=0.0,
                    summary_metrics={"arm": arm},
                )
            with open(metrics_file, "w", encoding="utf-8") as f:
                if hasattr(runner, "metrics_history"):
                    for record in runner.metrics_history:
                        f.write(json.dumps(record.to_dict()) + "\n")
        else:
            total_gens = getattr(runner, "generations", 100)
            if hasattr(runner, "initialize_population"):
                runner.initialize_population()
            with open(metrics_file, "w", encoding="utf-8") as f:
                for gen in range(1, total_gens + 1):
                    if hasattr(runner, "step_generation"):
                        step_out = runner.step_generation(gen)
                        record = step_out[1] if isinstance(step_out, tuple) else step_out
                        f.write(json.dumps(record.to_dict()) + "\n")
            summary = CompletionSummary(
                experiment_id=exp_id,
                track=getattr(runner, "track", ExecutionTrack.ENGINE),
                seed=seed,
                completed_generations=total_gens,
                total_ticks=total_gens * 16,
                status="COMPLETED",
                stop_reason="HORIZON_REACHED",
                scientific_assessment=AssessmentStatus.NOT_SUPPORTED,
                primary_endpoint_value=0.0,
                summary_metrics={"arm": arm},
            )

        logger.info("Run complete")

        with open(run_dir / "completion.json", "w", encoding="utf-8") as f:
            json.dump(summary.to_dict(), f, indent=2)

        status["status"] = "COMPLETED"
        with open(run_dir / "status.json", "w", encoding="utf-8") as f:
            json.dump(status, f, indent=2)

        return summary
