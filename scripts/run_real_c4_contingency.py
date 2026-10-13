#!/usr/bin/env python3
"""
run_real_c4_contingency.py - Challenge 4: Gouldian Historical Contingency & Replay Forks.

Rigorous implementation of Stephen Jay Gould's "Replaying Life's Tape" thought experiment
and Richard Lenski's LTEE Replay Methodology using the GenesisEngine virtual machine
and SimulationRecorder for the Simulation Atlas.

Theoretical Grounding:
- Stephen Jay Gould (1989): "Wonderful Life: The Burgess Shale and the Nature of History".
  If the tape of life is rewound to an ancestral checkpoint and replayed, do evolutionary
  trajectories arrive at convergent phenotypes (determinism) or radically diverge into
  novel states (historical contingency)?
- Richard E. Lenski & Zachary D. Blount et al. (2008, PNAS):
  Historical contingency in the E. coli long-term evolution experiment (LTEE Cit+ innovation).
  Demonstrated that replays from frozen fossil checkpoints reveal historical potentiation.
- Travisano, Mongold, Bennett, Lenski (1995, Science):
  Partitioning phenotypic variance into adaptation, chance (stochasticity), and history.
- Wagenaar & Adami (2004) / Pennock (2007):
  Digital organisms and replay experiments: deterministic physics with branching PRNG streams.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import shutil
import sys
import time
from pathlib import Path
from typing import Any

from codontrace.console.runs import runs_directory
from codontrace.console.simulation import read_simulation
from codontrace.engine_results import GenesisRun
from codontrace.genesis.engine import GenesisEngine
from codontrace.genesis.runtime_profiles import GenesisRuntimeProfile
from codontrace.visualization import SimulationRecorder


def setup_run_dir(run_id: str, title: str) -> Path:
    base = runs_directory()
    run_dir = base / run_id
    if run_dir.exists():
        shutil.rmtree(run_dir)
    run_dir.mkdir(parents=True, exist_ok=True)

    manifest = {
        "run_id": run_id,
        "title": title,
        "created_at": time.time(),
        "runner": "GenesisEngine",
        "real_engine": True,
        "challenge": 4,
        "theory": "Gould_Lenski_Historical_Contingency_Replay",
        "platform": sys.platform,
    }
    (run_dir / "run_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    (run_dir / "run.pid").write_text(str(os.getpid()), encoding="utf-8")
    return run_dir


def log_event(run_dir: Path, msg: str) -> None:
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    with (run_dir / "live.log").open("a", encoding="utf-8") as f:
        f.write(line + "\n")
    with (run_dir / "console.log").open("a", encoding="utf-8") as f:
        f.write(line + "\n")


def update_status(
    run_dir: Path,
    run_id: str,
    title: str,
    pct: float,
    status: str,
    t_start: float,
    metrics: dict[str, Any],
) -> None:
    now = time.time()
    elapsed = round(now - t_start, 2)
    data = {
        "id": run_id,
        "title": title,
        "status": status,
        "pid": os.getpid(),
        "pct": round(pct, 1),
        "elapsed_seconds": elapsed,
        "updated_at": now,
        "metrics": metrics,
        "historical_contingency_evaluated": True,
    }
    target = run_dir / "status.json"
    for _ in range(10):
        try:
            with target.open("w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            break
        except OSError:
            time.sleep(0.05)


def finalize_run(run_dir: Path, run_id: str, title: str, t_start: float, metrics: dict[str, Any]) -> None:
    update_status(run_dir, run_id, title, 100.0, "COMPLETED", t_start, metrics)
    try:
        (run_dir / "COMPLETE").touch()
    except OSError:
        pass
    summary = {
        "run_id": run_id,
        "title": title,
        "status": "COMPLETED",
        "duration_seconds": round(time.time() - t_start, 2),
        "metrics": metrics,
        "engine": "GenesisEngine",
        "historical_contingency_evaluated": True,
    }
    (run_dir / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")


def run_historical_contingency_experiment(
    *,
    base_seed: int = 401,
    fork_seeds: list[int] | None = None,
    checkpoint_tick: int = 4,
    fork_ticks: int = 4,
    initial_population: int = 8,
) -> dict[str, Any]:
    if fork_seeds is None:
        fork_seeds = [401, 402, 403, 404]

    run_id = "real_engine_c4_contingency_replay"
    title = "Real Engine C4: Historical Contingency & Replay Forks (Gould & Lenski)"
    run_dir = setup_run_dir(run_id, title)
    t_start = time.time()
    total_ticks = checkpoint_tick + fork_ticks

    log_event(run_dir, "==========================================================================")
    log_event(run_dir, "STARTING CHALLENGE 4: HISTORICAL CONTINGENCY & REPLAY FORKS")
    log_event(run_dir, "Theoretical Model: Stephen Jay Gould (1989) & Lenski LTEE (2008)")
    log_event(run_dir, f"Protocol: Ancestor Seed={base_seed} -> Checkpoint T={checkpoint_tick} -> Forks={fork_seeds}")
    log_event(run_dir, "==========================================================================")

    # --------------------------------------------------------------------------
    # Phase 1: Pre-Fork Baseline Ancestor Lineage (Generations 0 .. T_checkpoint)
    # --------------------------------------------------------------------------
    log_event(run_dir, f"[Phase 1: Ancestor] Running lineage to checkpoint T={checkpoint_tick}...")
    base_profile = GenesisRuntimeProfile.life_loop_world(
        seed=base_seed,
        tick_count=total_ticks,
        population=initial_population,
    )
    base_engine = GenesisEngine.from_spec(base_profile)
    base_engine.run = GenesisRun(run_id=run_id, spec_digest=base_engine.run.spec_digest, seed=base_seed)
    SimulationRecorder(run_dir).attach(base_engine)
    base_engine.run_ticks(checkpoint_tick)

    ckpt_pop = len(base_engine.runner.population.organisms)
    log_event(run_dir, f"[Phase 1: Complete] Checkpoint reached at T={checkpoint_tick}. Living organisms: {ckpt_pop}")
    update_status(run_dir, run_id, title, 30.0, "CHECKPOINT_FROZEN", t_start, {
        "checkpoint_tick": checkpoint_tick,
        "checkpoint_population": ckpt_pop,
    })

    # --------------------------------------------------------------------------
    # Phase 2: Capture Exact State Checkpoint
    # --------------------------------------------------------------------------
    log_event(run_dir, f"[Phase 2: Checkpoint] Freezing isolated recoverable checkpoint at generation {checkpoint_tick}...")
    fork_payload = base_engine.capture_fork()

    # --------------------------------------------------------------------------
    # Phase 3: Branch 1 (Deterministic Control Continuation)
    # --------------------------------------------------------------------------
    log_event(run_dir, "[Phase 3: Branch 401] Running deterministic control continuation...")
    res_branch1 = base_engine.run_ticks(fork_ticks)
    branches: dict[int, dict[str, Any]] = {
        base_seed: {
            "engine": base_engine,
            "res": res_branch1,
            "seed": base_seed,
            "label": "Fork 1 (Deterministic Baseline Continuation)",
        }
    }

    # --------------------------------------------------------------------------
    # Phase 4: Stochastic Replay Branches (Seeds 402, 403, 404)
    # --------------------------------------------------------------------------
    for idx, s in enumerate(fork_seeds[1:], start=2):
        log_event(run_dir, f"[Phase 4: Branch {s}] Forking from frozen checkpoint T={checkpoint_tick} (Fork {idx}/{len(fork_seeds)})...")
        fork_profile = GenesisRuntimeProfile.life_loop_world(
            seed=s,
            tick_count=fork_ticks,
            population=initial_population,
        )
        fork_engine = GenesisEngine.from_fork(
            fork_profile,
            fork_payload,
            allow_spec_change=True,
            spec_change_reason=f"Gouldian Historical Contingency Replay Branch (Seed {s})",
        )
        fork_engine.run = GenesisRun(run_id=run_id, spec_digest=fork_engine.run.spec_digest, seed=s)
        SimulationRecorder(run_dir).attach(fork_engine)
        res_fork = fork_engine.run_ticks(fork_ticks)

        # Replicate ancestral frames 0..T-1 so the Simulation Atlas contains the full continuous timeline
        for g in range(checkpoint_tick):
            src_frame = run_dir / "simulation" / f"seed_{base_seed}" / f"frame_{g:012d}.json"
            if src_frame.exists():
                f_data = json.loads(src_frame.read_text(encoding="utf-8"))
                f_data["seed"] = s
                dst_frame = run_dir / "simulation" / f"seed_{s}" / f"frame_{g:012d}.json"
                dst_frame.write_text(json.dumps(f_data, separators=(",", ":")), encoding="utf-8")

        branches[s] = {
            "engine": fork_engine,
            "res": res_fork,
            "seed": s,
            "label": f"Fork Replay (Seed {s})",
        }
        pct = 30.0 + (idx / len(fork_seeds)) * 50.0
        update_status(run_dir, run_id, title, pct, "RUNNING_FORKS", t_start, {"completed_fork": s})

    # --------------------------------------------------------------------------
    # Phase 5: Quantitative Historical Contingency & Divergence Analysis
    # --------------------------------------------------------------------------
    log_event(run_dir, "[Phase 5: Analysis] Calculating genetic and phenotypic divergence across replay branches...")
    branch_stats: dict[int, dict[str, Any]] = {}
    for s, b_data in branches.items():
        eng = b_data["engine"]
        pop = eng.runner.population
        orgs = pop.organisms
        n = len(orgs)

        genomes = [org.genome.to_codons() for org in orgs]
        digests = [org.genome.digest() for org in orgs]

        atps = [float(org.atp_state.runtime_available) for org in orgs] if orgs else [0.0]
        mean_atp = sum(atps) / len(atps) if atps else 0.0
        var_atp = sum((a - mean_atp) ** 2 for a in atps) / len(atps) if len(atps) > 1 else 0.0

        xs = [org.position[0] for org in orgs] if orgs else [0]
        ys = [org.position[1] for org in orgs] if orgs else [0]
        mean_x = sum(xs) / len(xs) if xs else 0.0
        mean_y = sum(ys) / len(ys) if ys else 0.0
        rg = math.sqrt(sum((x - mean_x) ** 2 + (y - mean_y) ** 2 for x, y in zip(xs, ys, strict=False)) / len(xs)) if xs else 0.0

        total_births = sum(t.generation_result.births for t in eng.tick_results)
        total_deaths = sum(t.generation_result.deaths for t in eng.tick_results)

        branch_stats[s] = {
            "pop_size": n,
            "genomes": genomes,
            "digests": digests,
            "mean_atp": round(mean_atp, 3),
            "var_atp": round(var_atp, 3),
            "mean_x": round(mean_x, 2),
            "mean_y": round(mean_y, 2),
            "rg": round(rg, 2),
            "births": total_births,
            "deaths": total_deaths,
        }
        log_event(
            run_dir,
            f"  Branch Seed {s}: Pop={n} | Mean ATP={round(mean_atp, 2)} | "
            f"Centroid=({round(mean_x, 1)}, {round(mean_y, 1)}) | Births={total_births} | Deaths={total_deaths}",
        )

    world_diag = math.hypot(base_profile.world_width, base_profile.world_height)
    pairwise_genetic: dict[str, float] = {}
    pairwise_phenotypic: dict[str, float] = {}
    genetic_vals: list[float] = []
    phenotypic_vals: list[float] = []

    for i in fork_seeds:
        for j in fork_seeds:
            if i >= j:
                continue
            pair_key = f"{i}_vs_{j}"
            st_i = branch_stats[i]
            st_j = branch_stats[j]

            # Genetic Divergence (Jaccard dissimilarity of digests + mean sequence mismatch)
            u_i = set(st_i["digests"])
            u_j = set(st_j["digests"])
            union_len = len(u_i | u_j)
            jaccard_dist = 1.0 - (len(u_i & u_j) / union_len) if union_len > 0 else 0.0

            seq_dists: list[float] = []
            for g1 in st_i["genomes"]:
                for g2 in st_j["genomes"]:
                    max_len = max(len(g1), len(g2))
                    if max_len == 0:
                        continue
                    mismatches = sum(1 for c1, c2 in zip(g1, g2, strict=False) if c1 != c2) + abs(len(g1) - len(g2))
                    seq_dists.append(mismatches / max_len)
            avg_seq_dist = sum(seq_dists) / len(seq_dists) if seq_dists else 0.0
            d_gen = round(0.5 * jaccard_dist + 0.5 * avg_seq_dist, 4)
            pairwise_genetic[pair_key] = d_gen
            genetic_vals.append(d_gen)

            # Phenotypic Divergence (Normalized population, energetics, spatial centroids, and metabolic turnover)
            d_pop = abs(st_i["pop_size"] - st_j["pop_size"]) / max(st_i["pop_size"], st_j["pop_size"], 1)
            d_atp = abs(st_i["mean_atp"] - st_j["mean_atp"]) / max(st_i["mean_atp"], st_j["mean_atp"], 1.0)
            d_spatial = math.hypot(st_i["mean_x"] - st_j["mean_x"], st_i["mean_y"] - st_j["mean_y"]) / (world_diag or 1.0)
            d_net = abs((st_i["births"] - st_i["deaths"]) - (st_j["births"] - st_j["deaths"])) / max(
                abs(st_i["births"] - st_i["deaths"]) + abs(st_j["births"] - st_j["deaths"]), 1
            )
            d_pheno = round(math.sqrt(0.25 * (d_pop**2 + d_atp**2 + d_spatial**2 + d_net**2)), 4)
            pairwise_phenotypic[pair_key] = d_pheno
            phenotypic_vals.append(d_pheno)

    mean_genetic_div = round(sum(genetic_vals) / len(genetic_vals), 4) if genetic_vals else 0.0
    mean_phenotypic_div = round(sum(phenotypic_vals) / len(phenotypic_vals), 4) if phenotypic_vals else 0.0
    gould_contingency_index = round(0.5 * (mean_genetic_div + mean_phenotypic_div), 4)

    log_event(
        run_dir,
        f"Historical Divergence Summary: Mean Genetic={mean_genetic_div} | "
        f"Mean Phenotypic={mean_phenotypic_div} | Gould Contingency Index={gould_contingency_index}",
    )

    metrics = {
        "checkpoint_generation": checkpoint_tick,
        "total_generations": total_ticks,
        "checkpoint_population": ckpt_pop,
        "fork_seeds": fork_seeds,
        "branch_populations": {s: branch_stats[s]["pop_size"] for s in fork_seeds},
        "mean_genetic_divergence": mean_genetic_div,
        "mean_phenotypic_divergence": mean_phenotypic_div,
        "gould_historical_contingency_index": gould_contingency_index,
        "pairwise_genetic_divergence": pairwise_genetic,
        "pairwise_phenotypic_divergence": pairwise_phenotypic,
        "contingency_verdict": (
            "historical_contingency_confirmed_gouldian_divergence"
            if gould_contingency_index > 0.15
            else "deterministic_convergence_observed"
        ),
    }

    finalize_run(run_dir, run_id, title, t_start, metrics)

    # Cross-directory replication for workspace root simulation_runs
    try:
        root_runs = Path("E:/Zero3/simulation_runs") / run_id
        if root_runs.resolve() != run_dir.resolve():
            if root_runs.exists():
                shutil.rmtree(root_runs)
            shutil.copytree(run_dir, root_runs)
            log_event(run_dir, f"Mirrored run artifacts to {root_runs}")
    except Exception as exc:
        log_event(run_dir, f"Mirroring notice: {exc}")

    # Validate Simulation Atlas stream integrity across all seeds
    log_event(run_dir, "[Phase 6: Verification] Verifying Simulation Atlas frame stream integrity...")
    verification = {}
    for s in fork_seeds:
        page = read_simulation(run_id, seed=s, limit=16)
        verification[s] = {
            "available": page.get("available", False),
            "total_frames": page.get("total_frames", 0),
            "generations": page.get("generations", []),
        }
        log_event(run_dir, f"  Seed {s}: available={verification[s]['available']}, frames={verification[s]['total_frames']}, gens={verification[s]['generations']}")

    log_event(run_dir, f"Run {run_id} completed successfully in {round(time.time() - t_start, 2)}s.")
    return metrics


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Challenge 4: Gouldian Historical Contingency Replay Experiment")
    parser.add_argument("--base-seed", type=int, default=401, help="Base seed for ancestor lineage")
    parser.add_argument("--checkpoint", type=int, default=4, help="Generation tick to take checkpoint")
    parser.add_argument("--fork-ticks", type=int, default=4, help="Ticks to execute on each replay branch")
    parser.add_argument("--population", type=int, default=8, help="Initial population size")
    args = parser.parse_args()

    run_historical_contingency_experiment(
        base_seed=args.base_seed,
        checkpoint_tick=args.checkpoint,
        fork_ticks=args.fork_ticks,
        initial_population=args.population,
    )


if __name__ == "__main__":
    main()
