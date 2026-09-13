#!/usr/bin/env python3
"""Resume-safe JOSS evidence battery with per-task checkpointing on disk (Drive-friendly).

Saves after EVERY (family, variant, seed) cycle into a single project folder:
  <out>/CONFIG.json
  <out>/checkpoint.json
  <out>/run_records.jsonl
  <out>/progress.json
  <out>/DONE.txt          (only when all tasks finished)
  <out>/summary_partial.json (rewritten every N completions)

Does not claim collective_intelligence. ClaimGate remains authority.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
import traceback
from pathlib import Path
from typing import Any

# Reuse planner from the main runner
import importlib.util

ROOT = Path(__file__).resolve().parent
RUNNER = ROOT / "collective_joss_evidence_benchmark.py"


def _load_runner():
    spec = importlib.util.spec_from_file_location("joss_runner", RUNNER)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def _task_key(family: str, variant: str, seed: int, repeat: int) -> str:
    return f"{family}|{variant}|{seed}|{repeat}"


def _atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(path)


def _load_json(path: Path, default: Any) -> Any:
    if not path.is_file():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Drive/resume wrapper for JOSS evidence benchmark")
    ap.add_argument("--out", required=True, help="Single project folder (on Drive)")
    ap.add_argument("--profile", default="marathon", choices=["smoke", "quick", "standard", "strong", "extended", "stress", "publication", "marathon"])
    ap.add_argument("--seed-start", type=int, default=1)
    ap.add_argument("--seed-count", type=int, default=24)
    ap.add_argument("--ticks", type=int, default=80)
    ap.add_argument("--generations", type=int, default=None)
    ap.add_argument("--population", type=int, default=24)
    ap.add_argument("--per-run-timeout", type=int, default=900)
    ap.add_argument("--repeat-per-scenario", type=int, default=1)
    ap.add_argument("--src-dir", default="src")
    ap.add_argument("--max-new-runs", type=int, default=0, help="Optional cap of NEW tasks this session (0=all remaining)")
    ap.add_argument("--rebuild-every", type=int, default=10, help="Rewrite partial summary every N new completions")
    args = ap.parse_args(argv)

    if args.generations is not None:
        args.ticks = int(args.generations)

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    records_path = out / "run_records.jsonl"
    checkpoint_path = out / "checkpoint.json"
    config_path = out / "CONFIG.json"
    progress_path = out / "progress.json"
    seeds_path = out / "SEEDS.json"
    done_path = out / "DONE.txt"

    mod = _load_runner()
    plan = mod.make_plan(args.profile, args.seed_count)
    tasks = mod.build_tasks(plan, args.seed_start, args.seed_count, args.repeat_per_scenario)

    seeds = list(range(args.seed_start, args.seed_start + args.seed_count))
    config = {
        "profile": args.profile,
        "seed_start": args.seed_start,
        "seed_count": args.seed_count,
        "seeds": seeds,
        "ticks": args.ticks,
        "population": args.population,
        "per_run_timeout": args.per_run_timeout,
        "plan_len": len(plan),
        "total_tasks": len(tasks),
        "claim_boundary": "not a proof of collective intelligence; ClaimGate is authority",
        "runner": "collective_joss_drive_resume.py",
        "updated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    _atomic_write(config_path, json.dumps(config, indent=2) + "\n")
    _atomic_write(seeds_path, json.dumps({"seeds": seeds, "seed_start": args.seed_start, "seed_count": args.seed_count}, indent=2) + "\n")

    checkpoint = _load_json(checkpoint_path, {"completed": {}, "failed": {}, "version": 1})
    completed: dict[str, Any] = dict(checkpoint.get("completed") or {})
    failed: dict[str, Any] = dict(checkpoint.get("failed") or {})

    remaining = [t for t in tasks if _task_key(*t) not in completed]
    if args.max_new_runs and args.max_new_runs > 0:
        remaining = remaining[: int(args.max_new_runs)]

    print(f"[resume] total={len(tasks)} done={len(completed)} fail={len(failed)} remaining_this_session={len(remaining)}", flush=True)

    src_dir = str(Path(args.src_dir).resolve()) if args.src_dir else None
    new_done = 0
    session_start = time.time()

    for i, (family, variant, seed, repeat) in enumerate(remaining, start=1):
        key = _task_key(family, variant, seed, repeat)
        print(f"[resume] {i}/{len(remaining)} {key}", flush=True)
        cmd = [
            sys.executable,
            str(RUNNER),
            "--out",
            str(out),
            "--profile",
            args.profile,
            "--ticks",
            str(args.ticks),
            "--population",
            str(args.population),
            "--single-run-mode",
            "--single-family",
            family,
            "--single-variant",
            variant,
            "--single-seed",
            str(seed),
        ]
        if src_dir:
            cmd.extend(["--src-dir", src_dir])
        t0 = time.time()
        row: dict[str, Any]
        try:
            completed_proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=args.per_run_timeout,
                env=os.environ.copy(),
            )
            lines = (completed_proc.stdout or "").strip().splitlines()
            if not lines:
                raise RuntimeError(f"no JSON stdout rc={completed_proc.returncode} stderr={completed_proc.stderr[:500]}")
            row = json.loads(lines[-1])
            row["repeat_index"] = repeat
            row["wall_s"] = round(time.time() - t0, 3)
            row["task_key"] = key
            if completed_proc.returncode != 0 or row.get("status") == "error":
                row["status"] = "error"
                row["rc"] = completed_proc.returncode
        except subprocess.TimeoutExpired as exc:
            row = {
                "family": family,
                "variant": variant,
                "seed": seed,
                "repeat_index": repeat,
                "status": "timeout",
                "error": "TimeoutExpired",
                "message": str(exc),
                "wall_s": round(time.time() - t0, 3),
                "task_key": key,
            }
        except Exception as exc:
            row = {
                "family": family,
                "variant": variant,
                "seed": seed,
                "repeat_index": repeat,
                "status": "error",
                "error": type(exc).__name__,
                "message": str(exc),
                "traceback": traceback.format_exc(limit=6),
                "wall_s": round(time.time() - t0, 3),
                "task_key": key,
            }

        # Append record immediately (crash-safe enough for Colab)
        with records_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")

        if row.get("status") == "passed":
            completed[key] = {"status": "passed", "ts": time.time(), "wall_s": row.get("wall_s")}
            failed.pop(key, None)
        else:
            failed[key] = {"status": row.get("status"), "error": row.get("error"), "message": row.get("message"), "ts": time.time()}
            # still mark completed so resume skips unless --retry-failed later
            completed[key] = {"status": row.get("status"), "ts": time.time(), "wall_s": row.get("wall_s")}

        checkpoint = {"completed": completed, "failed": failed, "version": 1, "updated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
        _atomic_write(checkpoint_path, json.dumps(checkpoint, indent=2) + "\n")

        progress = {
            "total_tasks": len(tasks),
            "completed_count": len(completed),
            "failed_count": len(failed),
            "remaining": len(tasks) - len(completed),
            "session_new": new_done + 1,
            "session_elapsed_s": round(time.time() - session_start, 1),
            "last_key": key,
            "last_status": row.get("status"),
            "updated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }
        _atomic_write(progress_path, json.dumps(progress, indent=2) + "\n")
        new_done += 1

        if args.rebuild_every and new_done % int(args.rebuild_every) == 0:
            _write_partial_summary(out, tasks, completed, failed)

        print(f"[resume] saved {key} status={row.get('status')} progress={len(completed)}/{len(tasks)}", flush=True)

    _write_partial_summary(out, tasks, completed, failed)

    if len(completed) >= len(tasks):
        done_path.write_text(
            json.dumps(
                {
                    "done": True,
                    "total": len(tasks),
                    "failed": len(failed),
                    "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                    "claim_boundary": config["claim_boundary"],
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        print("[resume] ALL TASKS COMPLETE — wrote DONE.txt", flush=True)
    else:
        if done_path.is_file():
            done_path.unlink()
        print(f"[resume] session end; remaining={len(tasks) - len(completed)} (re-run same --out to continue)", flush=True)
    return 0


def _write_partial_summary(out: Path, tasks: list, completed: dict, failed: dict) -> None:
    by_status: dict[str, int] = {}
    for meta in completed.values():
        st = str(meta.get("status") or "unknown")
        by_status[st] = by_status.get(st, 0) + 1
    payload = {
        "total_tasks": len(tasks),
        "completed_count": len(completed),
        "failed_count": len(failed),
        "by_status": by_status,
        "updated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "collective_intelligence": False,
        "note": "partial/final progress summary from resume wrapper; not ClaimGate promotion",
    }
    _atomic_write(out / "summary_partial.json", json.dumps(payload, indent=2) + "\n")


if __name__ == "__main__":
    raise SystemExit(main())
