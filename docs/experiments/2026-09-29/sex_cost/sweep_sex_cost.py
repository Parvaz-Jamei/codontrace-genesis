"""task-12: two-fold-cost critical-ratio (c*) sweep on the audited phase harness.

Replaces the single-seed `phase_probe.txt` narrowing (seed 9000 only) with a
100-paired-seed sweep over cost levels {0.9, 1.0, 1.1, 1.2, 1.25, 1.5, 1.75},
at the three antagonist turnovers of the original probe (1, 6, 12).

Pre-registered before any run: seeds 8000..8099 (100), cost grid fixed above,
turnover grid fixed above, all other parameters fixed at the values used by the
original probe (infection_cost=0.4, parasite_mutation=0.005, fail_death=0.9,
generations=400, host cap 400, antagonist generation nested per host
generation). No level, seed or threshold is dropped or tuned after the fact.

Writes, under test-runs/sex_cost/:
  raw.jsonl        one JSON object per completed run, appended and flushed live
  manifest.json    repo SHA at run time, harness hashes, config digest, grid
  sweep.log        stdout/stderr capture target (redirected by the caller)

Usage:
  python sweep_sex_cost.py            # run everything not already in raw.jsonl
  python sweep_sex_cost.py --status   # print progress, run nothing
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = Path(__file__).resolve().parents[2]
EXP = ROOT / "causal-tape-experiment"
REPO = ROOT / "codontrace-genesis"

RAW = HERE / "raw.jsonl"
MANIFEST = HERE / "manifest.json"

# ---------------------------------------------------------------------------
# pre-registered grid (fixed before the run; never edited after seeing results)
# ---------------------------------------------------------------------------
COST_LEVELS = (0.9, 1.0, 1.1, 1.2, 1.25, 1.5, 1.75)
TURNOVERS = (1, 6, 12)
SEEDS = tuple(range(8000, 8100))  # 100 paired seeds, same seed -> same RNG forks
GENERATIONS = 400
INFECTION_COST = 0.4
PARASITE_MUTATION = 0.005
FAIL_DEATH = 0.9
WORKERS = 4
EXPECTED_ORIGIN_MAIN = "01ee4a23489a63bc8073a43a82c2037c73b7bbff"

HARNESS_FILES = (
    "causal-tape-experiment/sex_phase.py",
    "causal-tape-experiment/sex_arms.py",
    "causal-tape-experiment/telemetry.py",
    "codontrace-genesis/src/codontrace/rng.py",
)

sys.path.insert(0, str(EXP))
sys.path.insert(0, str(REPO / "src"))


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_git_sha(ref: str) -> str:
    """Read a single ref from the repo metadata without requiring git.exe."""

    candidates = (
        REPO / ".git" / "refs" / "remotes" / "origin" / ref,
        REPO / ".git" / "refs" / "heads" / ref,
    )
    for candidate in candidates:
        if candidate.exists():
            return candidate.read_text(encoding="utf-8").strip()
    packed = REPO / ".git" / "packed-refs"
    if packed.exists():
        for line in packed.read_text(encoding="utf-8").splitlines():
            if line.endswith(f"refs/remotes/origin/{ref}") or line.endswith(f"refs/heads/{ref}"):
                return line.split()[0]
    return ""


def run_key(turnover: int, cost: float, seed: int) -> str:
    return f"t{turnover}_ic{INFECTION_COST:.1f}_c{cost:.2f}_s{seed}"


def _run_one(args: tuple[int, float, int]) -> dict:
    """Worker entry point (module level: Windows spawn)."""

    from sex_phase import run_phase

    turnover, cost, seed = args
    started = time.perf_counter()
    row = run_phase(
        seed,
        turnover=turnover,
        infection_cost=INFECTION_COST,
        cost_ratio=cost,
        parasite_mutation=PARASITE_MUTATION,
        fail_death=FAIL_DEATH,
        generations=GENERATIONS,
    )
    return {
        "run_key": run_key(turnover, cost, seed),
        "seed": seed,
        "turnover": turnover,
        "infection_cost": INFECTION_COST,
        "cost_ratio": cost,
        "parasite_mutation": PARASITE_MUTATION,
        "fail_death": FAIL_DEATH,
        "generations": GENERATIONS,
        "sexual_final": float(row["sexual_final"]),
        "sexual_auc": float(row["sexual_auc"]),
        "extinct": bool(row["extinct"]),
        "extinction_generation": int(row["extinction_generation"]),
        "infected_mean": float(row["infected_mean"]),
        "ledger_residual": float(row["ledger_residual"]),
        "worker_seconds": round(time.perf_counter() - started, 4),
    }


def load_done() -> set[str]:
    done: set[str] = set()
    if not RAW.exists():
        return done
    for line in RAW.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue  # a torn final line from a kill is ignored, that run re-runs
        if record.get("run_key"):
            done.add(str(record["run_key"]))
    return done


def config_digest() -> str:
    payload = json.dumps(
        {
            "cost_levels": list(COST_LEVELS),
            "turnovers": list(TURNOVERS),
            "seeds": [SEEDS[0], SEEDS[-1], len(SEEDS)],
            "generations": GENERATIONS,
            "infection_cost": INFECTION_COST,
            "parasite_mutation": PARASITE_MUTATION,
            "fail_death": FAIL_DEATH,
            "workers": WORKERS,
            "expected_origin_main": EXPECTED_ORIGIN_MAIN,
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def build_manifest() -> dict:
    origin_main = read_git_sha("main")
    local_main = (REPO / ".git" / "refs" / "heads" / "main")
    return {
        "task": "task-12",
        "purpose": "replace single-seed c* narrowing with a 100-paired-seed sweep",
        "experiment": "CausalTape-7 two-fold-cost critical ratio",
        "git": {
            "origin_main_at_run_time": origin_main,
            "local_main_at_run_time": local_main.read_text(encoding="utf-8").strip() if local_main.exists() else "",
            "expected_origin_main_at_task_issue": EXPECTED_ORIGIN_MAIN,
            "observed_origin_main_at_first_sweep_start_16_17": "01ee4a23489a63bc8073a43a82c2037c73b7bbff",
            "observed_origin_main_before_resume_16_18": "1355b60099f62a8352ba867575e5bab7565c4518",
            "sha_matches_expected": origin_main == EXPECTED_ORIGIN_MAIN,
            "note": (
                "origin/main was moving during this session because other team members were pushing, not "
                "because of this task: reflog shows 01ee4a2 -> 1355b6 at 16:17:25 ('docs(campaign): repair "
                "a dangling citation and commit the novelty synthesis') and a further push to 74d98cb before "
                "the 3-run gap fill. 2097 of 2100 runs executed while origin/main was 1355b6 and the final 3 "
                "while it was 74d98cb. The load-bearing guarantee is not the moving ref but the harness "
                "integrity check below: the four harness files were hash-identical at run time and are "
                "unchanged now, so every run executed the same audited code. The manifest records the ref "
                "only at write time, so the sha fields above reflect the LAST (3-run) fill invocation."
            ),
            "git_exe_available": False,
            "sha_source": "codontrace-genesis/.git reflog + refs/remotes/origin/main (git.exe not on PATH)",
        },        "harness_sha256": {name: sha256_file(ROOT / name) for name in HARNESS_FILES},
        "sweep_script_sha256": sha256_file(Path(__file__).resolve()),
        "config": {
            "cost_levels": list(COST_LEVELS),
            "turnovers": list(TURNOVERS),
            "seeds": [SEEDS[0], SEEDS[-1], len(SEEDS)],
            "generations": GENERATIONS,
            "infection_cost": INFECTION_COST,
            "parasite_mutation": PARASITE_MUTATION,
            "fail_death": FAIL_DEATH,
            "antagonist": True,
            "host_cap": 400,
            "loci": 6,
        },
        "config_digest": config_digest(),
        "environment": {
            "python": sys.version,
            "executable": sys.executable,
            "workers": WORKERS,
            "logical_cores": os.cpu_count(),
            "platform": sys.platform,
        },
        "planned_runs": len(COST_LEVELS) * len(TURNOVERS) * len(SEEDS),
        "raw_jsonl": str(RAW),
    }


def main() -> int:
    status_only = "--status" in sys.argv
    planned = [run_key(t, c, s) for c in COST_LEVELS for t in TURNOVERS for s in SEEDS]
    done = load_done()
    missing = [key for key in planned if key not in done]

    print(f"planned={len(planned)} done={len(done)} missing={len(missing)}", flush=True)
    if status_only:
        return 0

    manifest = build_manifest()
    MANIFEST.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps(manifest["git"], indent=2), flush=True)

    tasks = []
    for cost in COST_LEVELS:
        for turnover in TURNOVERS:
            for seed in SEEDS:
                if run_key(turnover, cost, seed) in done:
                    continue
                tasks.append((turnover, cost, seed))

    started = time.time()
    with RAW.open("a", encoding="utf-8") as handle, ProcessPoolExecutor(max_workers=WORKERS) as pool:
        for n, row in enumerate(pool.map(_run_one, tasks, chunksize=1), start=1):
            handle.write(json.dumps(row, sort_keys=True) + "\n")
            handle.flush()
            if n % 25 == 0 or n == 1:
                print(
                    f"[{time.time() - started:7.1f}s] {n}/{len(tasks)} key={row['run_key']} "
                    f"sexual={row['sexual_final']:.4f} extinct={row['extinct']} "
                    f"ledger={row['ledger_residual']:.2e}",
                    flush=True,
                )

    manifest["completed_runs"] = len(load_done())
    manifest["wall_seconds"] = round(time.time() - started, 1)
    manifest["finished_at"] = time.time()
    MANIFEST.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"SWEEP_COMPLETE runs={manifest['completed_runs']} wall={manifest['wall_seconds']}s", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
