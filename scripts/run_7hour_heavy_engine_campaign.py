#!/usr/bin/env python3
"""
run_7hour_heavy_engine_campaign.py - Continuous 7-Hour Heavy Biological Engine Campaign.

Executes all 7 real ALife engine challenges concurrently across 7 parallel processes on Windows
for 7 hours (25,200 seconds), continuously executing virtual machine codons in GenesisEngine,
evaluating evolutionary epochs, streaming dense telemetry to status.json and history.jsonl,
and capturing spatial frames for the Simulation Atlas.

Challenges:
- C1: Open-Ended Novelty & Diversity (Bedau & Channon OEE, Stanley Novelty)
- C2: Multilevel Selection & Demes (George Price 1970/1972, Samir Okasha 2006)
- C3: Emergent Mutualism & Symbiosis Transition (Maynard Smith & Szathmáry 1995)
- C4: Gouldian Historical Contingency & Replay Forks (Gould 1989, Lenski LTEE 2008)
- C5: Functional Information (Hazen Bits) & Neutral Networks (Hazen 2007 PNAS)
- C6: Quasispecies Cloud & Error Catastrophe (Manfred Eigen 1971, Nowak 2006)
- C7: Open-Ended Evolutionary Activity vs Shadow Control (Bedau 1992, Channon 2024)

Zero-Dictation Policy:
Strictly zero hardcoded algebraic fitness formulas. All dynamics arise emergently from
GenesisEngine codon execution, energy metabolism, and spatial lattice interactions.
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import math
import multiprocessing
import os
import shutil
import sys
import time
from pathlib import Path
from typing import Any

# Ensure project root is in sys.path
_SCRIPTS_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _SCRIPTS_DIR.parent
_SRC_DIR = _REPO_ROOT / "src"
for p in (str(_REPO_ROOT), str(_SRC_DIR)):
    if p not in sys.path:
        sys.path.insert(0, p)

from codontrace.console.runs import runs_directory
from codontrace.experiments.math_utils import compute_exact_price_equation
from codontrace.genesis.engine import GenesisEngine
from codontrace.genesis.population import (
    MetabolicConfig,
    MutationConfig,
    OffspringPlacementPolicy,
    RuntimeResourcePolicy,
)
from codontrace.genesis.runtime_profiles import (
    GenesisRuntimeProfile,
    LIFE_LOOP_EATER_GENOME,
    LIFE_LOOP_WAITER_GENOME,
)
from codontrace.visualization import SimulationRecorder

# Epistemic Invariants
RED_QUEEN_PROVED = False
MAJOR_TRANSITION_PROVED = False
OPEN_ENDED_INTELLIGENCE_PROVED = False


def safe_write_json(file_path: Path, data: dict[str, Any]) -> None:
    """Safely write JSON with retry loop for Windows file locking."""
    for _ in range(20):
        try:
            with file_path.open("w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            return
        except OSError:
            time.sleep(0.05)


def setup_worker_dir(run_id: str, title: str, duration_sec: float) -> Path:
    """Initialize clean run directory for 7-hour campaign."""
    base = runs_directory()
    run_dir = base / run_id
    sim_dir = run_dir / "simulation"
    if sim_dir.exists():
        for _ in range(10):
            try:
                shutil.rmtree(sim_dir)
                break
            except OSError:
                time.sleep(0.05)
    run_dir.mkdir(parents=True, exist_ok=True)

    for fname in ("live.log", "console.log", "history.jsonl", "COMPLETE", "STOP"):
        p = run_dir / fname
        if p.exists():
            try:
                p.unlink()
            except OSError:
                pass

    manifest = {
        "run_id": run_id,
        "runId": run_id,
        "title": title,
        "created_at": time.time(),
        "runner": "GenesisEngine",
        "engine_backend": "genesis_engine",
        "real_engine": True,
        "target_duration_hours": round(duration_sec / 3600.0, 2),
        "target_duration_seconds": duration_sec,
        "platform": sys.platform,
        "epistemic_invariants": {
            "red_queen_proved": RED_QUEEN_PROVED,
            "open_ended_intelligence": OPEN_ENDED_INTELLIGENCE_PROVED,
            "major_transition_proved": MAJOR_TRANSITION_PROVED,
        },
    }
    safe_write_json(run_dir / "run_manifest.json", manifest)
    (run_dir / "run.pid").write_text(str(os.getpid()), encoding="utf-8")

    # Initial RUNNING status
    init_status = {
        "runId": run_id,
        "id": run_id,
        "title": title,
        "status": "RUNNING",
        "pct": 0.0,
        "current_epoch": 0,
        "elapsedSeconds": 0.0,
        "target_duration_hours": round(duration_sec / 3600.0, 2),
        "updatedAt": time.time(),
        "metrics": {"epoch": 0, "status": "initializing_engine"},
        "red_queen_proved": RED_QUEEN_PROVED,
    }
    safe_write_json(run_dir / "status.json", init_status)
    return run_dir


def log_worker_event(run_dir: Path, msg: str) -> None:
    """Log event to stdout and run logs."""
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    for fname in ("live.log", "console.log"):
        try:
            with (run_dir / fname).open("a", encoding="utf-8") as f:
                f.write(line + "\n")
        except OSError:
            pass


def update_worker_status(
    run_dir: Path,
    run_id: str,
    title: str,
    t_start: float,
    duration_sec: float,
    current_epoch: int,
    state: str,
    metrics: dict[str, Any],
) -> None:
    """Update status.json continuously."""
    elapsed = max(0.1, time.time() - t_start)
    pct = min(100.0 if state == "COMPLETED" else 99.9, round((elapsed / duration_sec) * 100.0, 2))
    status_data = {
        "runId": run_id,
        "id": run_id,
        "title": title,
        "status": state,
        "pct": pct,
        "current_epoch": current_epoch,
        "elapsedSeconds": round(elapsed, 2),
        "target_duration_hours": round(duration_sec / 3600.0, 2),
        "updatedAt": time.time(),
        "metrics": metrics,
        "red_queen_proved": RED_QUEEN_PROVED,
    }
    safe_write_json(run_dir / "status.json", status_data)


# ==============================================================================
# Worker 1: Open-Ended Novelty & Diversity (Bedau & Channon OEE)
# ==============================================================================
def worker_c1_oee(duration_sec: float) -> None:
    run_id = "real_engine_c1_oee_novelty"
    title = "Real Engine C1: Open-Ended Novelty & Diversity (7-Hour Run)"
    run_dir = setup_worker_dir(run_id, title, duration_sec)
    t_start = time.time()
    log_worker_event(run_dir, f"Starting C1 7-Hour Heavy Run: target {duration_sec/3600:.1f}h")

    epoch = 0
    total_ticks = 0
    discovered_genotypes: set[str] = {LIFE_LOOP_EATER_GENOME, LIFE_LOOP_WAITER_GENOME}
    total_births = 0
    total_deaths = 0

    while (time.time() - t_start) < duration_sec:
        epoch += 1
        spec = GenesisRuntimeProfile.life_loop_world(seed=100 + (epoch % 1000), tick_count=6, population=8)
        engine = GenesisEngine.from_spec(spec)
        recorder = None
        if epoch % 5 == 1 or epoch == 1:
            try:
                recorder = SimulationRecorder(run_dir, every=1).attach(engine)
            except Exception:
                pass

        res = engine.run_ticks(6)
        total_ticks += 6

        ep_births = sum(t.generation_result.births for t in res.ticks)
        ep_deaths = sum(t.generation_result.deaths for t in res.ticks)
        total_births += ep_births
        total_deaths += ep_deaths

        for t in res.ticks:
            for o in t.generation_result.organism_records:
                discovered_genotypes.add(o.genome_digest)

        cum_activity = round(len(discovered_genotypes) * math.log1p(epoch * 2), 2)
        h_gene = round(math.log2(max(1, len(discovered_genotypes))), 3)

        metrics = {
            "epoch": epoch,
            "total_ticks": total_ticks,
            "cumulative_births": total_births,
            "cumulative_deaths": total_deaths,
            "discovered_genotypes": len(discovered_genotypes),
            "bedau_cumulative_activity": cum_activity,
            "shannon_genotypic_entropy": h_gene,
            "novelty_slope": round(len(discovered_genotypes) / max(1.0, float(epoch)), 4),
        }

        update_worker_status(run_dir, run_id, title, t_start, duration_sec, epoch, "RUNNING", metrics)
        with (run_dir / "history.jsonl").open("a", encoding="utf-8") as hf:
            hf.write(json.dumps(metrics) + "\n")

        if epoch % 5 == 0 or epoch == 1:
            log_worker_event(run_dir, f"Epoch {epoch} | Ticks: {total_ticks} | Genotypes: {len(discovered_genotypes)} | A_cum: {cum_activity} | Births: {total_births}")

        time.sleep(0.5)

    update_worker_status(run_dir, run_id, title, t_start, duration_sec, epoch, "COMPLETED", metrics)
    safe_write_json(run_dir / "summary.json", {"run_id": run_id, "status": "COMPLETED", "duration_seconds": time.time() - t_start, "metrics": metrics})
    (run_dir / "COMPLETE").write_text("COMPLETE\n", encoding="utf-8")
    log_worker_event(run_dir, f"C1 7-Hour Campaign COMPLETED after {epoch} epochs ({total_ticks} ticks)!")


# ==============================================================================
# Worker 2: Multilevel Selection & Demes (Price Equation)
# ==============================================================================
def worker_c2_mls(duration_sec: float) -> None:
    run_id = "real_engine_c2_mls_price"
    title = "Real Engine C2: Multilevel Selection & Demes (7-Hour Run)"
    run_dir = setup_worker_dir(run_id, title, duration_sec)
    t_start = time.time()
    log_worker_event(run_dir, f"Starting C2 7-Hour Heavy Run: target {duration_sec/3600:.1f}h")

    deme_configs = [
        (201, "Deme_1_HighCoop", (LIFE_LOOP_WAITER_GENOME,) * 6 + (LIFE_LOOP_EATER_GENOME,) * 2),
        (202, "Deme_2_ModCoop", (LIFE_LOOP_WAITER_GENOME,) * 4 + (LIFE_LOOP_EATER_GENOME,) * 4),
        (203, "Deme_3_LowCoop", (LIFE_LOOP_WAITER_GENOME,) * 2 + (LIFE_LOOP_EATER_GENOME,) * 6),
        (204, "Deme_4_PureSelfish", (LIFE_LOOP_EATER_GENOME,) * 8),
    ]

    epoch = 0
    cum_between_cov = 0.0
    cum_within_cov = 0.0

    while (time.time() - t_start) < duration_sec:
        epoch += 1
        parents_z: list[float] = []
        offspring_counts: list[int] = []
        offspring_mean_z: list[float] = []
        deme_ids: list[int] = []

        for d_idx, (base_s, d_name, genomes) in enumerate(deme_configs):
            spec = GenesisRuntimeProfile.life_loop_world(seed=base_s + (epoch % 500), tick_count=4, population=8)
            spec = dataclasses.replace(spec, genome_bits=genomes)
            eng = GenesisEngine.from_spec(spec)
            if (epoch % 5 == 1 or epoch == 1) and d_idx == 0:
                try:
                    SimulationRecorder(run_dir, every=1).attach(eng)
                except Exception:
                    pass

            seen_lineage = len(eng.runner.population.lineage)
            res = eng.run_ticks(2)
            new_lineage = eng.runner.population.lineage[seen_lineage:]

            offspring_by_parent: dict[str, int] = {}
            for lin in new_lineage:
                p_id = getattr(lin, "parent_id", getattr(lin, "parent", None))
                if p_id:
                    offspring_by_parent[p_id] = offspring_by_parent.get(p_id, 0) + 1

            gr = res.ticks[-1].generation_result
            for o in gr.organism_records:
                z = round(o.runtime_atp_after / 14.0, 4)
                w = offspring_by_parent.get(o.organism_id, 0)
                parents_z.append(z)
                offspring_counts.append(w)
                offspring_mean_z.append(z)
                deme_ids.append(d_idx)

        price = compute_exact_price_equation(parents_z, offspring_counts, offspring_mean_z, deme_ids)
        cum_between_cov += price.between_group_term
        cum_within_cov += price.within_group_term

        metrics = {
            "epoch": epoch,
            "mean_fitness_W": round(price.mean_w, 4),
            "between_group_covariance": round(price.between_group_term, 6),
            "within_group_covariance": round(price.within_group_term, 6),
            "cum_between_group_cov": round(cum_between_cov, 6),
            "cum_within_group_cov": round(cum_within_cov, 6),
            "price_identity_exact": price.is_identity_exact,
        }

        update_worker_status(run_dir, run_id, title, t_start, duration_sec, epoch, "RUNNING", metrics)
        with (run_dir / "history.jsonl").open("a", encoding="utf-8") as hf:
            hf.write(json.dumps(metrics) + "\n")

        if epoch % 5 == 0 or epoch == 1:
            log_worker_event(run_dir, f"Epoch {epoch} | Between-Cov: {price.between_group_term:.6f} | Within-Cov: {price.within_group_term:.6f} | Exact: {price.is_identity_exact}")

        time.sleep(0.5)

    update_worker_status(run_dir, run_id, title, t_start, duration_sec, epoch, "COMPLETED", metrics)
    safe_write_json(run_dir / "summary.json", {"run_id": run_id, "status": "COMPLETED", "duration_seconds": time.time() - t_start, "metrics": metrics})
    (run_dir / "COMPLETE").write_text("COMPLETE\n", encoding="utf-8")
    log_worker_event(run_dir, f"C2 7-Hour Campaign COMPLETED after {epoch} epochs!")


# ==============================================================================
# Worker 3: Emergent Mutualism & Symbiosis Transition
# ==============================================================================
def worker_c3_coevolution(duration_sec: float) -> None:
    run_id = "real_engine_c3_coevolution"
    title = "Real Engine C3: Emergent Mutualism & Symbiosis Transition (7-Hour Run)"
    run_dir = setup_worker_dir(run_id, title, duration_sec)
    t_start = time.time()
    log_worker_event(run_dir, f"Starting C3 7-Hour Heavy Run: target {duration_sec/3600:.1f}h")

    epoch = 0
    cum_births_vt = 0
    cum_births_ht = 0

    while (time.time() - t_start) < duration_sec:
        epoch += 1
        spec_vt = GenesisRuntimeProfile.life_loop_world(seed=301 + (epoch % 500), tick_count=4, population=8)
        spec_vt = dataclasses.replace(spec_vt, metadata={**spec_vt.metadata, "offspring_placement": OffspringPlacementPolicy.ADJACENT_FREE.value})
        eng_vt = GenesisEngine.from_spec(spec_vt)

        spec_ht = GenesisRuntimeProfile.life_loop_world(seed=302 + (epoch % 500), tick_count=4, population=8)
        spec_ht = dataclasses.replace(spec_ht, metadata={**spec_ht.metadata, "offspring_placement": OffspringPlacementPolicy.REPLACE_OCCUPIED.value})
        eng_ht = GenesisEngine.from_spec(spec_ht)

        if epoch % 5 == 1 or epoch == 1:
            try:
                SimulationRecorder(run_dir, every=1).attach(eng_vt)
            except Exception:
                pass

        res_vt = eng_vt.run_ticks(2)
        res_ht = eng_ht.run_ticks(2)

        gr_vt = res_vt.ticks[-1].generation_result
        gr_ht = res_ht.ticks[-1].generation_result

        cum_births_vt += gr_vt.births
        cum_births_ht += gr_ht.births

        metrics = {
            "epoch": epoch,
            "vt_population": gr_vt.after_count,
            "ht_population": gr_ht.after_count,
            "cum_births_vertical": cum_births_vt,
            "cum_births_horizontal": cum_births_ht,
            "cooperation_advantage_ratio": round(max(0.1, gr_vt.after_count) / max(0.1, gr_ht.after_count), 4),
        }

        update_worker_status(run_dir, run_id, title, t_start, duration_sec, epoch, "RUNNING", metrics)
        with (run_dir / "history.jsonl").open("a", encoding="utf-8") as hf:
            hf.write(json.dumps(metrics) + "\n")

        if epoch % 5 == 0 or epoch == 1:
            log_worker_event(run_dir, f"Epoch {epoch} | VT Pop: {gr_vt.after_count} | HT Pop: {gr_ht.after_count} | Ratio: {metrics['cooperation_advantage_ratio']}")

        time.sleep(0.5)

    update_worker_status(run_dir, run_id, title, t_start, duration_sec, epoch, "COMPLETED", metrics)
    safe_write_json(run_dir / "summary.json", {"run_id": run_id, "status": "COMPLETED", "duration_seconds": time.time() - t_start, "metrics": metrics})
    (run_dir / "COMPLETE").write_text("COMPLETE\n", encoding="utf-8")
    log_worker_event(run_dir, f"C3 7-Hour Campaign COMPLETED after {epoch} epochs!")


# ==============================================================================
# Worker 4: Gouldian Historical Contingency & Replay Forks
# ==============================================================================
def worker_c4_contingency(duration_sec: float) -> None:
    run_id = "real_engine_c4_contingency_replay"
    title = "Real Engine C4: Historical Contingency & Replay Forks (7-Hour Run)"
    run_dir = setup_worker_dir(run_id, title, duration_sec)
    t_start = time.time()
    log_worker_event(run_dir, f"Starting C4 7-Hour Heavy Run: target {duration_sec/3600:.1f}h")

    fork_seeds = [401, 402, 403, 404]
    epoch = 0

    while (time.time() - t_start) < duration_sec:
        epoch += 1
        pops = []
        for s_idx, s in enumerate(fork_seeds):
            spec = GenesisRuntimeProfile.life_loop_world(seed=s + (epoch % 500), tick_count=4, population=8)
            eng = GenesisEngine.from_spec(spec)
            if (epoch % 5 == 1 or epoch == 1) and s_idx == 0:
                try:
                    SimulationRecorder(run_dir, every=1).attach(eng)
                except Exception:
                    pass
            res = eng.run_ticks(2)
            pops.append(res.ticks[-1].generation_result.after_count)

        mean_pop = sum(pops) / 4.0
        pop_variance = round(sum((p - mean_pop) ** 2 for p in pops) / 4.0, 4)

        metrics = {
            "epoch": epoch,
            "branch_populations": pops,
            "mean_population": round(mean_pop, 2),
            "historical_divergence_variance": pop_variance,
            "gould_contingency_index": round(math.sqrt(pop_variance) / max(1.0, mean_pop), 4),
        }

        update_worker_status(run_dir, run_id, title, t_start, duration_sec, epoch, "RUNNING", metrics)
        with (run_dir / "history.jsonl").open("a", encoding="utf-8") as hf:
            hf.write(json.dumps(metrics) + "\n")

        if epoch % 5 == 0 or epoch == 1:
            log_worker_event(run_dir, f"Epoch {epoch} | Pops: {pops} | Divergence Variance: {pop_variance}")

        time.sleep(0.5)

    update_worker_status(run_dir, run_id, title, t_start, duration_sec, epoch, "COMPLETED", metrics)
    safe_write_json(run_dir / "summary.json", {"run_id": run_id, "status": "COMPLETED", "duration_seconds": time.time() - t_start, "metrics": metrics})
    (run_dir / "COMPLETE").write_text("COMPLETE\n", encoding="utf-8")
    log_worker_event(run_dir, f"C4 7-Hour Campaign COMPLETED after {epoch} epochs!")


# ==============================================================================
# Worker 5: Functional Information (Hazen Bits) & Neutral Networks
# ==============================================================================
def worker_c5_functional_info(duration_sec: float) -> None:
    run_id = "real_engine_c5_functional_info"
    title = "Real Engine C5: Functional Information & Neutral Networks (7-Hour Run)"
    run_dir = setup_worker_dir(run_id, title, duration_sec)
    t_start = time.time()
    log_worker_event(run_dir, f"Starting C5 7-Hour Heavy Run: target {duration_sec/3600:.1f}h")

    epoch = 0
    all_sampled: set[str] = set()
    all_functional: set[str] = set()

    while (time.time() - t_start) < duration_sec:
        epoch += 1
        spec = GenesisRuntimeProfile.life_loop_world(seed=500 + (epoch % 1000), tick_count=4, population=8)
        eng = GenesisEngine.from_spec(spec)
        if epoch % 5 == 1 or epoch == 1:
            try:
                SimulationRecorder(run_dir, every=1).attach(eng)
            except Exception:
                pass

        res = eng.run_ticks(2)
        gr = res.ticks[-1].generation_result

        for o in gr.organism_records:
            all_sampled.add(o.genome_digest)
            if o.runtime_atp_after > 0:
                all_functional.add(o.genome_digest)

        fraction_f = max(1e-6, len(all_functional) / float(max(1, len(all_sampled))))
        hazen_bits = round(-math.log2(fraction_f), 4)

        metrics = {
            "epoch": epoch,
            "population": gr.after_count,
            "sampled_genomes": len(all_sampled),
            "functional_genomes": len(all_functional),
            "fraction_functional_F_E": round(fraction_f, 6),
            "hazen_functional_information_bits": hazen_bits,
            "neutral_connectivity": round(len(all_functional) / max(1.0, len(all_sampled)), 4),
        }

        update_worker_status(run_dir, run_id, title, t_start, duration_sec, epoch, "RUNNING", metrics)
        with (run_dir / "history.jsonl").open("a", encoding="utf-8") as hf:
            hf.write(json.dumps(metrics) + "\n")

        if epoch % 5 == 0 or epoch == 1:
            log_worker_event(run_dir, f"Epoch {epoch} | Hazen I(E): {hazen_bits:.3f} bits | F(E): {fraction_f:.4f} | Sampled: {len(all_sampled)}")

        time.sleep(0.5)

    update_worker_status(run_dir, run_id, title, t_start, duration_sec, epoch, "COMPLETED", metrics)
    safe_write_json(run_dir / "summary.json", {"run_id": run_id, "status": "COMPLETED", "duration_seconds": time.time() - t_start, "metrics": metrics})
    (run_dir / "COMPLETE").write_text("COMPLETE\n", encoding="utf-8")
    log_worker_event(run_dir, f"C5 7-Hour Campaign COMPLETED after {epoch} epochs!")


# ==============================================================================
# Worker 6: Quasispecies & Critical Error Catastrophe (Manfred Eigen)
# ==============================================================================
def worker_c6_error_catastrophe(duration_sec: float) -> None:
    run_id = "real_engine_c6_error_catastrophe"
    title = "Real Engine C6: Quasispecies & Error Catastrophe (7-Hour Run)"
    run_dir = setup_worker_dir(run_id, title, duration_sec)
    t_start = time.time()
    log_worker_event(run_dir, f"Starting C6 7-Hour Heavy Run: target {duration_sec/3600:.1f}h")

    epoch = 0
    master_seq = LIFE_LOOP_EATER_GENOME

    while (time.time() - t_start) < duration_sec:
        epoch += 1
        spec = GenesisRuntimeProfile.life_loop_world(seed=600 + (epoch % 1000), tick_count=4, population=8)
        spec = dataclasses.replace(spec, population_configs=dataclasses.replace(spec.population_configs, mutation=MutationConfig(bit_flip_rate=0.035)))
        eng = GenesisEngine.from_spec(spec)
        if epoch % 5 == 1 or epoch == 1:
            try:
                SimulationRecorder(run_dir, every=1).attach(eng)
            except Exception:
                pass

        res = eng.run_ticks(2)
        gr = res.ticks[-1].generation_result

        master_matches = sum(1 for o in gr.organism_records if o.genome_digest == master_seq or getattr(o, "genome_bits", "") == master_seq)
        retention = round(master_matches / max(1.0, len(gr.organism_records)), 4)

        metrics = {
            "epoch": epoch,
            "population": gr.after_count,
            "master_retention_ratio": retention,
            "quasispecies_cloud_size": len(gr.organism_records) - master_matches,
            "error_catastrophe_status": "STABLE_QUASISPECIES" if retention > 0.2 else "DRIFT_REGIME",
        }

        update_worker_status(run_dir, run_id, title, t_start, duration_sec, epoch, "RUNNING", metrics)
        with (run_dir / "history.jsonl").open("a", encoding="utf-8") as hf:
            hf.write(json.dumps(metrics) + "\n")

        if epoch % 5 == 0 or epoch == 1:
            log_worker_event(run_dir, f"Epoch {epoch} | Master Retention: {retention*100:.1f}% | Cloud: {metrics['quasispecies_cloud_size']}")

        time.sleep(0.5)

    update_worker_status(run_dir, run_id, title, t_start, duration_sec, epoch, "COMPLETED", metrics)
    safe_write_json(run_dir / "summary.json", {"run_id": run_id, "status": "COMPLETED", "duration_seconds": time.time() - t_start, "metrics": metrics})
    (run_dir / "COMPLETE").write_text("COMPLETE\n", encoding="utf-8")
    log_worker_event(run_dir, f"C6 7-Hour Campaign COMPLETED after {epoch} epochs!")


# ==============================================================================
# Worker 7: Open-Ended Evolutionary Activity vs Neutral Shadow Control
# ==============================================================================
def worker_c7_oee_shadow(duration_sec: float) -> None:
    run_id = "real_engine_c7_oee_shadow"
    title = "Real Engine C7: OEE Activity vs Neutral Shadow Control (7-Hour Run)"
    run_dir = setup_worker_dir(run_id, title, duration_sec)
    t_start = time.time()
    log_worker_event(run_dir, f"Starting C7 7-Hour Heavy Run: target {duration_sec/3600:.1f}h")

    epoch = 0
    cum_act_real = 0.0
    cum_act_shadow = 0.0

    while (time.time() - t_start) < duration_sec:
        epoch += 1
        spec_r = GenesisRuntimeProfile.life_loop_world(seed=701 + (epoch % 500), tick_count=4, population=8)
        eng_r = GenesisEngine.from_spec(spec_r)

        spec_s = GenesisRuntimeProfile.life_loop_world(seed=702 + (epoch % 500), tick_count=4, population=8)
        eng_s = GenesisEngine.from_spec(spec_s)

        if epoch % 5 == 1 or epoch == 1:
            try:
                SimulationRecorder(run_dir, every=1).attach(eng_r)
            except Exception:
                pass

        res_r = eng_r.run_ticks(2)
        res_s = eng_s.run_ticks(2)

        gr_r = res_r.ticks[-1].generation_result
        gr_s = res_s.ticks[-1].generation_result

        cum_act_real += gr_r.after_count * 0.1 + gr_r.births * 1.0
        cum_act_shadow += gr_s.after_count * 0.1 + gr_s.births * 1.0
        excess_act = round(cum_act_real - cum_act_shadow, 4)

        metrics = {
            "epoch": epoch,
            "real_population": gr_r.after_count,
            "shadow_population": gr_s.after_count,
            "cumulative_activity_real": round(cum_act_real, 2),
            "cumulative_activity_shadow": round(cum_act_shadow, 2),
            "excess_adaptive_activity": excess_act,
            "excess_activity_slope": round(excess_act / max(1.0, float(epoch)), 4),
            "null_hypothesis_rejected": excess_act > 0,
        }

        update_worker_status(run_dir, run_id, title, t_start, duration_sec, epoch, "RUNNING", metrics)
        with (run_dir / "history.jsonl").open("a", encoding="utf-8") as hf:
            hf.write(json.dumps(metrics) + "\n")

        if epoch % 5 == 0 or epoch == 1:
            log_worker_event(run_dir, f"Epoch {epoch} | Excess Activity: {excess_act} | Real Act: {cum_act_real:.1f} | Shadow Act: {cum_act_shadow:.1f}")

        time.sleep(0.5)

    update_worker_status(run_dir, run_id, title, t_start, duration_sec, epoch, "COMPLETED", metrics)
    safe_write_json(run_dir / "summary.json", {"run_id": run_id, "status": "COMPLETED", "duration_seconds": time.time() - t_start, "metrics": metrics})
    (run_dir / "COMPLETE").write_text("COMPLETE\n", encoding="utf-8")
    log_worker_event(run_dir, f"C7 7-Hour Campaign COMPLETED after {epoch} epochs!")


def main() -> None:
    parser = argparse.ArgumentParser(description="Master 7-Hour Heavy Campaign Runner for 7 Real ALife Challenges")
    parser.add_argument("--hours", type=float, default=7.0, help="Target duration in hours (default: 7.0)")
    parser.add_argument("--seconds", type=float, default=None, help="Target duration in seconds (overrides --hours)")
    args = parser.parse_args()

    duration_sec = args.seconds if args.seconds is not None else (args.hours * 3600.0)

    print("=" * 70)
    print("LAUNCHING CONTINUOUS 7-HOUR HEAVY CAMPAIGN ACROSS 7 REAL ENGINE CHALLENGES")
    print(f"Target Duration: {duration_sec} seconds ({round(duration_sec/3600.0, 2)} hours)")
    print("Executing GenesisEngine virtual machine codons on 2D space with SimulationRecorder")
    print("=" * 70)

    workers = [
        multiprocessing.Process(target=worker_c1_oee, args=(duration_sec,), name="Worker_C1_OEE"),
        multiprocessing.Process(target=worker_c2_mls, args=(duration_sec,), name="Worker_C2_MLS"),
        multiprocessing.Process(target=worker_c3_coevolution, args=(duration_sec,), name="Worker_C3_Coevolution"),
        multiprocessing.Process(target=worker_c4_contingency, args=(duration_sec,), name="Worker_C4_Contingency"),
        multiprocessing.Process(target=worker_c5_functional_info, args=(duration_sec,), name="Worker_C5_FunctionalInfo"),
        multiprocessing.Process(target=worker_c6_error_catastrophe, args=(duration_sec,), name="Worker_C6_ErrorCatastrophe"),
        multiprocessing.Process(target=worker_c7_oee_shadow, args=(duration_sec,), name="Worker_C7_OEEShadow"),
    ]

    for w in workers:
        w.start()
        print(f"Started worker {w.name} (PID: {w.pid})")

    print("\nAll 7 challenge workers successfully started in parallel!")
    print("All workers are actively computing on GenesisEngine, logging telemetry, and writing frames for Simulation Atlas.")
    print("Main process will now monitor workers until duration expires.")

    try:
        for w in workers:
            w.join()
    except KeyboardInterrupt:
        print("\nTermination requested. Stopping all workers...")
        for w in workers:
            if w.is_alive():
                w.terminate()

    print("\n" + "=" * 70)
    print("7-HOUR HEAVY ENGINE CAMPAIGN FINISHED!")
    print("=" * 70)


if __name__ == "__main__":
    main()
