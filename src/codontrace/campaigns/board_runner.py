"""Calibration runner for the one experiment that can actually run.

T11's long endurance campaign is not this module. This module runs a short
life-loop, writes a checkpoint, and can continue that checkpoint. It does not
set a scientific verdict.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

from codontrace.campaigns.readiness import experiment
from codontrace.engine_runtime import GenesisEngine, checkpoint_bytes, checkpoint_from_bytes
from codontrace.errors import ConfigurationError
from codontrace.genesis.runtime_profiles import GenesisRuntimeProfile

BASIS_SHA = "e90f9cd1d7287d2b51531cae82cd75dc0a18b2f1"


class CampaignRejected(ConfigurationError):
    """The request is not a runnable campaign. The process must not start it quietly."""


def allowed_cpu_ids() -> list[int]:
    get_affinity = getattr(os, "sched_getaffinity", None)
    if callable(get_affinity):
        try:
            aff = get_affinity(0)
            if aff:
                return sorted(int(item) for item in aff)
        except OSError:
            pass
    count = os.cpu_count() or 1
    return list(range(max(1, count)))


def _require_ready(experiment_id: str) -> dict[str, Any]:
    try:
        row = experiment(experiment_id)
    except KeyError as exc:
        raise CampaignRejected(str(exc)) from exc
    if row["status"] not in {"آمادهٔ پایلوت", "آمادهٔ کمپین"}:
        raise CampaignRejected(f"{experiment_id} is {row['status']}. {row['gap']} Refusing to relabel it as a run.")
    return row


def _positive_int(name: str, value: int, *, minimum: int = 1) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise CampaignRejected(f"{name} must be an integer >= {minimum}")
    return value


def _check_resources(*, workers: int, cores: list[int] | None) -> list[int]:
    allowed = allowed_cpu_ids()
    if workers > len(allowed):
        raise CampaignRejected(
            f"workers {workers} exceeds allowed CPUs {allowed}. There is no fixed cap of 4; the limit is the machine."
        )
    if cores is None:
        return allowed
    unknown = sorted(set(cores) - set(allowed))
    if unknown:
        raise CampaignRejected(f"cores {unknown} are not in allowed CPUs {allowed}")
    if len(cores) != len(set(cores)):
        raise CampaignRejected("cores must not contain duplicates")
    return allowed


def _git_state(root: Path) -> tuple[str, bool]:
    try:
        sha = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=root, text=True, stderr=subprocess.DEVNULL
        ).strip()
        dirty = bool(
            subprocess.check_output(
                ["git", "status", "--porcelain"], cwd=root, text=True, stderr=subprocess.DEVNULL
            ).strip()
        )
    except (OSError, subprocess.CalledProcessError):
        return "UNKNOWN", True
    return sha, dirty


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    digest.update(path.read_bytes())
    return digest.hexdigest()


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _append_jsonl(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, sort_keys=True) + "\n")


def _spec(seed: int, ticks: int, population: int) -> Any:
    return GenesisRuntimeProfile.life_loop_world(seed=seed, tick_count=ticks, population=population)


def _living(engine: GenesisEngine) -> int | None:
    population = getattr(engine.runner, "population", None)
    organisms = getattr(population, "organisms", None)
    if isinstance(organisms, (dict, list, tuple)):
        return len(organisms)
    return None


def _run_until(engine: GenesisEngine, ticks: int, events: Path) -> tuple[str, dict[str, Any]]:
    engine.run_ticks(ticks)
    for tick in engine._tick_results:
        _append_jsonl(events, {"kind": "tick", "tick": int(tick.index) + 1})
    fork = engine.capture_fork()
    digest = str(fork["state_digest"])
    _append_jsonl(events, {"kind": "checkpoint", "tick": int(fork["tick_index"]), "state_digest": digest})
    return digest, fork


def _arm_dir(output: Path, seed: int, arm: str) -> Path:
    return output / "runs" / "T11" / f"seed_{seed}" / f"arm_{arm}"


def _seal(
    arm_dir: Path, *, seed: int, arm: str, ticks: int, population: int, state_digest: str, living: int | None
) -> None:
    metrics = arm_dir / "metrics.jsonl"
    events = arm_dir / "events.jsonl"
    _append_jsonl(
        metrics,
        {
            "arm": arm,
            "backend": "ENGINE",
            "living": living,
            "population": population,
            "seed": seed,
            "state_digest": state_digest,
            "tick": ticks,
        },
    )
    assay = {"arm": arm, "seed": seed, "state_digest": state_digest, "tick": ticks}
    _write_json(arm_dir / "assays" / "state.json", assay)
    completion = {
        "exit_code": 0,
        "experiment_id": "T11",
        "finished_ticks": ticks,
        "missing": [],
        "stop_reason": "horizon_reached",
        "target_ticks": ticks,
        "validity": "COMPLETE",
    }
    _write_json(arm_dir / "completion.json", completion)
    _write_json(
        arm_dir / "status.json",
        {"arm": arm, "engineering_status": "COMPLETE", "scientific_status": "UNASSESSED", "seed": seed},
    )
    (arm_dir / "live.log").write_text(
        f"experiment=T11 seed={seed} arm={arm} tick={ticks} backend=ENGINE scientific_status=UNASSESSED\n",
        encoding="utf-8",
    )
    hashed = {
        "assays/state.json": _sha256(arm_dir / "assays" / "state.json"),
        "events.jsonl": _sha256(events),
        "metrics.jsonl": _sha256(metrics),
    }
    checkpoint = arm_dir / "checkpoints" / "end.bin"
    if checkpoint.is_file():
        hashed["checkpoints/end.bin"] = _sha256(checkpoint)
    mid = arm_dir / "checkpoints" / "mid.bin"
    if mid.is_file():
        hashed["checkpoints/mid.bin"] = _sha256(mid)
    _write_json(arm_dir / "artifacts_manifest.json", {"files": hashed, "schema_version": 1})
    _write_json(
        arm_dir / "manifest.json",
        {
            "arm": arm,
            "backend": "ENGINE",
            "experiment_id": "T11",
            "population": population,
            "profile": "CALIBRATION",
            "seed": seed,
            "ticks": ticks,
        },
    )


def _write_campaign_manifest(
    output: Path, *, seed: int, ticks: int, population: int, workers: int, cores: list[int] | None
) -> None:
    root = Path(__file__).resolve().parents[3]
    sha, dirty = _git_state(root)
    _write_json(
        output / "manifest.json",
        {
            "backend": "ENGINE",
            "basis_sha": BASIS_SHA,
            "board_rate_measured": False,
            "dirty": dirty,
            "experiment_id": "T11",
            "horizon_ticks": ticks,
            "population": population,
            "profile": "CALIBRATION",
            "scientific_status": "UNASSESSED",
            "seed": seed,
            "source_sha": sha,
            "workers": workers,
            "allowed_cpu_ids": allowed_cpu_ids(),
            "cores": cores,
        },
    )


def run_uninterrupted(
    *,
    output: Path,
    seed: int,
    ticks: int,
    population: int,
    workers: int = 1,
    cores: list[int] | None = None,
) -> Path:
    _require_ready("T11")
    seed = _positive_int("seed", seed, minimum=0)
    ticks = _positive_int("ticks", ticks, minimum=2)
    population = _positive_int("population", population)
    workers = _positive_int("workers", workers)
    _check_resources(workers=workers, cores=cores)
    arm_dir = _arm_dir(output, seed, "uninterrupted")
    if arm_dir.exists():
        raise CampaignRejected(f"{arm_dir} already exists; refusing a silent restart")
    events = arm_dir / "events.jsonl"
    spec = _spec(seed, ticks, population)
    engine = GenesisEngine.from_spec(spec)
    digest, end = _run_until(engine, ticks, events)
    (arm_dir / "checkpoints").mkdir(parents=True, exist_ok=True)
    (arm_dir / "checkpoints" / "end.bin").write_bytes(checkpoint_bytes(end))
    # A mid checkpoint is the resume point. It is taken from a second, identical prefix.
    prefix = GenesisEngine.from_spec(spec)
    prefix.run_ticks(ticks // 2)
    mid = prefix.capture_fork()
    if int(mid["tick_index"]) != ticks // 2:
        raise CampaignRejected("mid checkpoint tick does not match half the locked horizon")
    (arm_dir / "checkpoints" / "mid.bin").write_bytes(checkpoint_bytes(mid))
    _seal(
        arm_dir,
        seed=seed,
        arm="uninterrupted",
        ticks=ticks,
        population=population,
        state_digest=digest,
        living=_living(engine),
    )
    _write_campaign_manifest(output, seed=seed, ticks=ticks, population=population, workers=workers, cores=cores)
    return arm_dir


def resume(
    *,
    output: Path,
    checkpoint: Path,
    seed: int,
    ticks: int,
    population: int,
    workers: int = 1,
    cores: list[int] | None = None,
) -> Path:
    _require_ready("T11")
    seed = _positive_int("seed", seed, minimum=0)
    ticks = _positive_int("ticks", ticks, minimum=2)
    population = _positive_int("population", population)
    workers = _positive_int("workers", workers)
    _check_resources(workers=workers, cores=cores)
    if not checkpoint.is_file() or checkpoint.stat().st_size == 0:
        raise CampaignRejected(f"incomplete checkpoint: {checkpoint}")
    try:
        loaded = checkpoint_from_bytes(checkpoint.read_bytes())
    except (ConfigurationError, OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        raise CampaignRejected(f"incompatible or incomplete checkpoint: {exc}") from exc
    if int(loaded.get("seed", -1)) != seed:
        raise CampaignRejected("checkpoint seed does not match the requested seed")
    if int(loaded.get("tick_index", -1)) != ticks // 2:
        raise CampaignRejected(
            f"checkpoint tick {loaded.get('tick_index')} is not half of horizon {ticks}; refusing a quiet restart"
        )
    arm_dir = _arm_dir(output, seed, "resume")
    if (arm_dir / "completion.json").is_file():
        raise CampaignRejected(f"{arm_dir} is already complete; refusing a silent restart")
    spec = _spec(seed, ticks, population)
    try:
        restored = GenesisEngine.from_fork(spec, loaded)
    except (ConfigurationError, ValueError) as exc:
        raise CampaignRejected(f"incompatible checkpoint: {exc}") from exc
    events = arm_dir / "events.jsonl"
    restored.run_ticks(ticks - (ticks // 2))
    fork = restored.capture_fork()
    if int(fork["tick_index"]) != ticks:
        raise CampaignRejected("resumed engine did not reach the locked horizon")
    digest = str(fork["state_digest"])
    _append_jsonl(events, {"kind": "resume", "from_tick": ticks // 2, "tick": ticks, "state_digest": digest})
    (arm_dir / "checkpoints").mkdir(parents=True, exist_ok=True)
    (arm_dir / "checkpoints" / "mid.bin").write_bytes(checkpoint.read_bytes())
    (arm_dir / "checkpoints" / "end.bin").write_bytes(checkpoint_bytes(fork))
    _seal(
        arm_dir,
        seed=seed,
        arm="resume",
        ticks=ticks,
        population=population,
        state_digest=digest,
        living=_living(restored),
    )
    _write_campaign_manifest(output, seed=seed, ticks=ticks, population=population, workers=workers, cores=cores)
    return arm_dir


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(prog="board_long_campaign")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("inventory")
    run_parser = sub.add_parser("run")
    resume_parser = sub.add_parser("resume")
    for item in (run_parser, resume_parser):
        item.add_argument("--experiment", required=True)
        item.add_argument("--seed", type=int, required=True)
        item.add_argument("--ticks", type=int, required=True)
        item.add_argument("--population", type=int, required=True)
        item.add_argument("--workers", type=int, default=1)
        item.add_argument("--cores", default=None)
        item.add_argument("--output", type=Path, required=True)
    run_parser.add_argument("--arm", required=True)
    resume_parser.add_argument("--checkpoint", type=Path, required=True)
    args = parser.parse_args(argv)
    if args.command == "inventory":
        from codontrace.campaigns.readiness import inventory

        json.dump(inventory(), sys.stdout, indent=2, ensure_ascii=False)
        sys.stdout.write("\n")
        return 0
    cores = None
    if args.cores:
        cores = [int(part) for part in str(args.cores).split(",") if part != ""]
    try:
        if args.command == "run":
            if args.experiment != "T11" or args.arm != "uninterrupted":
                if args.experiment == "T11":
                    detail = "the calibration arm is uninterrupted"
                else:
                    try:
                        detail = experiment(args.experiment)["gap"]
                    except KeyError:
                        detail = "unknown experiment"
                raise CampaignRejected(f"refusing {args.experiment} arm {args.arm}. {detail}")
            run_uninterrupted(
                output=args.output,
                seed=args.seed,
                ticks=args.ticks,
                population=args.population,
                workers=args.workers,
                cores=cores,
            )
        else:
            if args.experiment != "T11":
                raise CampaignRejected(experiment(args.experiment)["gap"])
            resume(
                output=args.output,
                checkpoint=args.checkpoint,
                seed=args.seed,
                ticks=args.ticks,
                population=args.population,
                workers=args.workers,
                cores=cores,
            )
    except CampaignRejected as exc:
        sys.stderr.write(f"{exc}\n")
        return 2
    return 0
