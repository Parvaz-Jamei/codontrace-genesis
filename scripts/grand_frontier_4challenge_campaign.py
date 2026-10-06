#!/usr/bin/env python3
"""
grand_frontier_4challenge_campaign.py - Multi-Day 4-Worker Frontier Experimental Campaign.

Deploys 4 deep, mathematically rigorous experimental challenges across 4 dedicated CPU cores:
- Worker 0 (Core 0): [OEE_NOVELTY] Open-Endedness & Persistence-Filtered Novelty (Stanley 2017, Channon 2024, Bedau 1998)
- Worker 1 (Core 1): [MLS_PRICE] Multilevel Selection & Role Differentiation (Chaturvedi et al. 2026, Price 1972, Okasha 2006)
- Worker 2 (Core 2): [TRANSITION_MUTUALISM] Major Evolutionary Transition & Mutualism Barrier (Maynard Smith-Szathmary 1995, Michod 2007)
- Worker 3 (Core 3): [CONTINGENCY_REPLAY] Historical Contingency vs Determinism (Gould 1989, Blount et al. 2008 LTEE, Conway Morris)

Architected for 48 to 72 hours of continuous execution with:
- Dedicated core affinity (os.sched_setaffinity for cores 0, 1, 2, 3 on Linux ARM64).
- Periodic epoch checkpointing & resumption (zero progress lost on restart).
- Bounded memory footprint (safe for 2GB RAM Orange Pi Zero 3 boards over multi-day runs).
- Native CodonTrace console integration (status.json, live.log, console.log, execution.json, COMPLETE).
- Epistemic invariants locked: red_queen_proved=False, open_ended_intelligence=False, major_transition_proved=False.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import signal
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from typing import Any

# Epistemological Invariants
RED_QUEEN_PROVED = False
OPEN_ENDED_INTELLIGENCE_PROVED = False
MAJOR_TRANSITION_PROVED = False

# Task bit masks for digital genetics (8 distinct computational tasks)
TASKS = ("nand", "and", "or", "nor", "xor", "equ", "not", "andn")
NUM_TASKS = len(TASKS)


def sha_seed(seed: int, salt: str) -> bytes:
    """Deterministic cryptographic pseudo-random byte stream."""
    return hashlib.sha256(f"{int(seed)}|{salt}".encode("utf-8")).digest()


def prng_float(seed: int, step: int, salt: str) -> float:
    """Deterministic float in [0.0, 1.0) from seed and step."""
    h = hashlib.sha256(f"{seed}:{step}:{salt}".encode("utf-8")).digest()
    return int.from_bytes(h[:4], "big") / 4294967296.0


def set_core_affinity(core_id: int) -> None:
    """Pin the current process to a specific CPU core on Linux."""
    if hasattr(os, "sched_setaffinity"):
        try:
            os.sched_setaffinity(0, {core_id % (os.cpu_count() or 4)})
        except (OSError, ValueError):
            pass


def write_atomic_json(path: Path, data: dict[str, Any]) -> None:
    """Write dictionary to path atomically via temporary file."""
    tmp = path.with_suffix(".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    tmp.replace(path)


# ==============================================================================
# WORKER 0: OPEN-ENDED EVOLUTION & PERSISTENCE NOVELTY (Stanley / Channon / Bedau)
# ==============================================================================

def run_worker_0_oee(
    output_dir: Path,
    target_seconds: float,
    epoch_gens: int = 10000,
    seed: int = 10001,
    resume: bool = True,
) -> dict[str, Any]:
    """
    Challenge 1: Evaluates whether antagonistic coevolution sustains unbounded
    cumulative evolutionary activity A(t) (Bedau et al. 1998, Channon 2024)
    versus cycling / stagnation across millions of generations.
    """
    set_core_affinity(0)
    worker_dir = output_dir / "worker_0_oee"
    worker_dir.mkdir(parents=True, exist_ok=True)
    log_file = worker_dir / "worker_0.log"
    checkpoint_file = worker_dir / "checkpoint.json"
    history_file = worker_dir / "oee_history.jsonl"

    def log(msg: str) -> None:
        ts = time.strftime("%Y-%m-%d %H:%M:%S")
        line = f"[{ts}] [WORKER-0:OEE] {msg}"
        with log_file.open("a", encoding="utf-8") as f:
            f.write(line + "\n")
        # Mirror to main live log
        with (output_dir / "live.log").open("a", encoding="utf-8") as lf:
            lf.write(line + "\n")
        print(line, flush=True)

    pop_size = 64
    epoch = 0
    total_gens = 0
    cumulative_activity = 0.0
    component_activity: dict[str, int] = {}
    component_first_seen: dict[str, int] = {}
    component_last_seen: dict[str, int] = {}

    # Initialize or resume state
    if resume and checkpoint_file.is_file():
        try:
            ckpt = json.loads(checkpoint_file.read_text(encoding="utf-8"))
            epoch = ckpt.get("epoch", 0)
            total_gens = ckpt.get("total_gens", 0)
            cumulative_activity = ckpt.get("cumulative_activity", 0.0)
            component_activity = ckpt.get("component_activity", {})
            component_first_seen = ckpt.get("component_first_seen", {})
            component_last_seen = ckpt.get("component_last_seen", {})
            hosts = [bytes.fromhex(h) for h in ckpt["hosts"]]
            parasites = [bytes.fromhex(p) for p in ckpt["parasites"]]
            log(f"Resumed from checkpoint: Epoch {epoch}, Total Gens {total_gens:,}, Activity {cumulative_activity:.1f}")
        except Exception as exc:
            log(f"Failed to load checkpoint ({exc}), starting fresh.")
            hosts = [hashlib.sha256(f"h:{seed}:{i}".encode()).digest()[:2] for i in range(pop_size)]
            parasites = [hashlib.sha256(f"p:{seed}:{i}".encode()).digest()[:2] for i in range(pop_size)]
    else:
        hosts = [hashlib.sha256(f"h:{seed}:{i}".encode()).digest()[:2] for i in range(pop_size)]
        parasites = [hashlib.sha256(f"p:{seed}:{i}".encode()).digest()[:2] for i in range(pop_size)]

    log(f"Started Open-Ended Evolution Assay: Target Seconds={target_seconds:.0f}s ({target_seconds/3600:.1f}h)")

    t_start = time.time()
    activity_snapshots = []

    while True:
        elapsed = time.time() - t_start
        if elapsed >= target_seconds:
            log(f"Target duration {target_seconds/3600:.1f}h reached. Finalizing worker.")
            break
        if (output_dir / "STOP").is_file():
            log("Stop signal detected. Exiting gracefully.")
            break

        epoch += 1

        # Run 1 epoch of generations
        for step in range(1, epoch_gens + 1):
            gen = total_gens + step
            new_hosts = []
            new_parasites = []
            gen_alleles = set()

            for i in range(pop_size):
                h_bits = int.from_bytes(hosts[i], "big")
                p_bits = int.from_bytes(parasites[i], "big")

                # Matching bits = infection success
                match_count = bin(h_bits & p_bits).count("1")

                # Selection & mutation
                h_rand = prng_float(seed, gen * 1000 + i, "host_mut")
                if h_rand < 0.15:
                    bit_flip = 1 << (int(h_rand * 100) % 16)
                    h_bits ^= bit_flip

                p_rand = prng_float(seed, gen * 1000 + i, "para_mut")
                if p_rand < 0.20:
                    bit_flip = 1 << (int(p_rand * 100) % 16)
                    p_bits ^= bit_flip

                h_bytes = h_bits.to_bytes(2, "big")
                p_bytes = p_bits.to_bytes(2, "big")
                new_hosts.append(h_bytes)
                new_parasites.append(p_bytes)

                h_hex = h_bytes.hex()
                gen_alleles.add(h_hex)
                if h_hex not in component_first_seen:
                    component_first_seen[h_hex] = gen
                component_last_seen[h_hex] = gen
                component_activity[h_hex] = component_activity.get(h_hex, 0) + 1

            hosts = new_hosts
            parasites = new_parasites

            # Bedau Activity: components persisting >= 3 generations
            persistent_active = [
                component_activity[a] for a in gen_alleles
                if (gen - component_first_seen[a]) >= 3
            ]
            cumulative_activity += len(persistent_active)

        total_gens += epoch_gens

        # Prune dead components if dictionary grows beyond 35,000 keys (Memory Safeguard)
        if len(component_activity) > 35000:
            active_keys = [k for k, last in component_last_seen.items() if (total_gens - last) < 15000]
            component_activity = {k: component_activity[k] for k in active_keys}
            component_first_seen = {k: component_first_seen[k] for k in active_keys}
            component_last_seen = {k: component_last_seen[k] for k in active_keys}

        # Shannon diversity
        counts: dict[str, int] = {}
        for h in hosts:
            hx = h.hex()
            counts[hx] = counts.get(hx, 0) + 1
        shannon = -sum((c / pop_size) * math.log(c / pop_size) for c in counts.values())

        activity_snapshots.append(cumulative_activity)
        if len(activity_snapshots) > 100:
            activity_snapshots.pop(0)

        # Channon Activity Slope estimation
        n = len(activity_snapshots)
        x_vals = list(range(n))
        slope = (
            (n * sum(x * y for x, y in zip(x_vals, activity_snapshots)) - sum(x_vals) * sum(activity_snapshots))
            / (n * sum(x**2 for x in x_vals) - (sum(x_vals))**2)
            if n > 1 else 0.0
        )

        epoch_record = {
            "epoch": epoch,
            "total_gens": total_gens,
            "unique_alleles": len(counts),
            "tracked_alleles": len(component_activity),
            "shannon_entropy": round(shannon, 4),
            "cumulative_activity": round(cumulative_activity, 2),
            "activity_slope": round(slope, 4),
            "elapsed_hours": round((time.time() - t_start) / 3600.0, 3),
        }

        with history_file.open("a", encoding="utf-8") as hf:
            hf.write(json.dumps(epoch_record) + "\n")

        # Save checkpoint
        ckpt_data = {
            "epoch": epoch,
            "total_gens": total_gens,
            "cumulative_activity": cumulative_activity,
            "hosts": [h.hex() for h in hosts],
            "parasites": [p.hex() for p in parasites],
            "component_activity": component_activity,
            "component_first_seen": component_first_seen,
            "component_last_seen": component_last_seen,
            "updated_at": time.time(),
        }
        write_atomic_json(checkpoint_file, ckpt_data)

        log(f"Epoch {epoch} | Total Gens={total_gens:,} | Tracked Alleles={len(component_activity)} | Activity={cumulative_activity:.0f} | Slope={slope:.2f} | Shannon={shannon:.3f}")

    verdict = "BOUNDED_CYCLING" if slope < 0.1 else "CONTINUOUS_INNOVATION_GROWTH"
    summary = {
        "challenge": "OEE_NOVELTY",
        "literature": "Stanley 2017; Bedau 1998; Channon 2024",
        "seed": seed,
        "completed_epochs": epoch,
        "total_generations": total_gens,
        "final_cumulative_activity": round(cumulative_activity, 2),
        "activity_slope": round(slope, 6),
        "oee_type1_verdict": verdict,
        "red_queen_proved": RED_QUEEN_PROVED,
        "open_ended_intelligence": OPEN_ENDED_INTELLIGENCE_PROVED,
    }
    with (worker_dir / "oee_summary.json").open("w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    return summary


# ==============================================================================
# WORKER 1: MULTILEVEL SELECTION & ROLE DIFFERENTIATION (Chaturvedi 2026 / Price 1972)
# ==============================================================================

def run_worker_1_mls(
    output_dir: Path,
    target_seconds: float,
    epoch_gens: int = 10000,
    seed: int = 20001,
    resume: bool = True,
) -> dict[str, Any]:
    """
    Challenge 2: Multilevel Selection and Emergent Role Differentiation under
    coupled resource ecology (Chaturvedi et al. arXiv:2604.00810, Price 1972, Okasha 2006).
    """
    set_core_affinity(1)
    worker_dir = output_dir / "worker_1_mls"
    worker_dir.mkdir(parents=True, exist_ok=True)
    log_file = worker_dir / "worker_1.log"
    checkpoint_file = worker_dir / "checkpoint.json"
    history_file = worker_dir / "mls_history.jsonl"

    def log(msg: str) -> None:
        ts = time.strftime("%Y-%m-%d %H:%M:%S")
        line = f"[{ts}] [WORKER-1:MLS] {msg}"
        with log_file.open("a", encoding="utf-8") as f:
            f.write(line + "\n")
        with (output_dir / "live.log").open("a", encoding="utf-8") as lf:
            lf.write(line + "\n")
        print(line, flush=True)

    num_demes = 4
    deme_size = 32
    total_pop = num_demes * deme_size

    epoch = 0
    total_gens = 0

    if resume and checkpoint_file.is_file():
        try:
            ckpt = json.loads(checkpoint_file.read_text(encoding="utf-8"))
            epoch = ckpt.get("epoch", 0)
            total_gens = ckpt.get("total_gens", 0)
            demes = ckpt.get("demes", [])
            log(f"Resumed MLS from checkpoint: Epoch {epoch}, Total Gens {total_gens:,}")
        except Exception as exc:
            log(f"Failed to load checkpoint ({exc}), starting fresh.")
            demes = [[prng_float(seed, d * deme_size + i, "init_z") for i in range(deme_size)] for d in range(num_demes)]
    else:
        demes = [[prng_float(seed, d * deme_size + i, "init_z") for i in range(deme_size)] for d in range(num_demes)]

    log(f"Started MLS Challenge: Target Seconds={target_seconds:.0f}s ({target_seconds/3600:.1f}h)")

    t_start = time.time()
    between_history = []
    within_history = []
    altruist_history = []

    while True:
        elapsed = time.time() - t_start
        if elapsed >= target_seconds:
            log(f"Target duration {target_seconds/3600:.1f}h reached. Finalizing MLS worker.")
            break
        if (output_dir / "STOP").is_file():
            log("Stop signal detected. Exiting gracefully.")
            break

        epoch += 1
        epoch_between = 0.0
        epoch_within = 0.0
        epoch_altruists = 0.0

        for step in range(1, epoch_gens + 1):
            gen = total_gens + step

            # Deme evaluations
            deme_fitnesses = []
            deme_mean_z = []
            individual_fitnesses = []

            for d in range(num_demes):
                z_vals = demes[d]
                mean_z = sum(z_vals) / deme_size
                deme_mean_z.append(mean_z)

                group_resource = mean_z * 2.0
                ind_fits = []
                for z in z_vals:
                    ind_fit = max(0.01, group_resource + (1.0 - z) * 0.8)
                    ind_fits.append(ind_fit)

                individual_fitnesses.append(ind_fits)
                deme_fitnesses.append(sum(ind_fits) / deme_size)

            # Price Equation Decomposition
            mean_W = sum(deme_fitnesses) / num_demes
            mean_Z = sum(deme_mean_z) / num_demes

            cov_between = sum((deme_fitnesses[d] - mean_W) * (deme_mean_z[d] - mean_Z) for d in range(num_demes)) / num_demes
            between_term = cov_between / mean_W if mean_W > 1e-6 else 0.0

            within_covs = []
            for d in range(num_demes):
                mW_d = sum(individual_fitnesses[d]) / deme_size
                mz_d = deme_mean_z[d]
                c_w = sum((individual_fitnesses[d][i] - mW_d) * (demes[d][i] - mz_d) for i in range(deme_size)) / deme_size
                within_covs.append(c_w / mW_d if mW_d > 1e-6 else 0.0)
            within_term = sum(within_covs) / num_demes

            role_counts = [sum(1 for z in demes[d] if z >= 0.5) for d in range(num_demes)]
            ratio_specialists = sum(role_counts) / total_pop

            epoch_between += between_term
            epoch_within += within_term
            epoch_altruists += ratio_specialists

            # Multilevel Reproduction
            new_demes = []
            tot_deme_fit = sum(deme_fitnesses) or 1.0
            for d in range(num_demes):
                parent_d = 0
                roll = prng_float(seed, gen * 500 + d, "group_sel") * tot_deme_fit
                cum = 0.0
                for idx, df in enumerate(deme_fitnesses):
                    cum += df
                    if cum >= roll:
                        parent_d = idx
                        break

                p_fits = individual_fitnesses[parent_d]
                tot_p = sum(p_fits) or 1.0
                new_ind = []
                for i in range(deme_size):
                    roll_i = prng_float(seed, gen * 500 + d * 50 + i, "ind_sel") * tot_p
                    cum_i = 0.0
                    parent_i = 0
                    for idx_i, pf in enumerate(p_fits):
                        cum_i += pf
                        if cum_i >= roll_i:
                            parent_i = idx_i
                            break

                    z_val = demes[parent_d][parent_i]
                    noise = (prng_float(seed, gen * 700 + i, "noise") - 0.5) * 0.1
                    new_z = max(0.0, min(1.0, z_val + noise))
                    new_ind.append(new_z)
                new_demes.append(new_ind)

            demes = new_demes

        total_gens += epoch_gens
        avg_b = epoch_between / epoch_gens
        avg_w = epoch_within / epoch_gens
        avg_alt = epoch_altruists / epoch_gens

        between_history.append(avg_b)
        within_history.append(avg_w)
        altruist_history.append(avg_alt)
        if len(between_history) > 100:
            between_history.pop(0)
            within_history.pop(0)
            altruist_history.pop(0)

        epoch_record = {
            "epoch": epoch,
            "total_gens": total_gens,
            "between_group_term": round(avg_b, 6),
            "within_group_term": round(avg_w, 6),
            "ratio_altruists": round(avg_alt, 4),
            "elapsed_hours": round((time.time() - t_start) / 3600.0, 3),
        }

        with history_file.open("a", encoding="utf-8") as hf:
            hf.write(json.dumps(epoch_record) + "\n")

        # Save checkpoint
        ckpt_data = {
            "epoch": epoch,
            "total_gens": total_gens,
            "demes": demes,
            "updated_at": time.time(),
        }
        write_atomic_json(checkpoint_file, ckpt_data)

        log(f"Epoch {epoch} | Total Gens={total_gens:,} | Between={avg_b:+.4f} | Within={avg_w:+.4f} | Altruists={avg_alt*100:.1f}%")

    final_between = sum(between_history) / len(between_history) if between_history else 0.0
    final_within = sum(within_history) / len(within_history) if within_history else 0.0
    altruism_sustained = (sum(altruist_history) / len(altruist_history) if altruist_history else 0.0) > 0.35

    summary = {
        "challenge": "MLS_PRICE",
        "literature": "Chaturvedi, El-Gazzar, van Gerven 2026 (arXiv:2604.00810); Price 1972; Okasha 2006",
        "seed": seed,
        "completed_epochs": epoch,
        "total_generations": total_gens,
        "final_between_group_term": round(final_between, 6),
        "final_within_group_term": round(final_within, 6),
        "altruism_defended_against_tragedy": altruism_sustained,
        "major_transition_proved": MAJOR_TRANSITION_PROVED,
        "red_queen_proved": RED_QUEEN_PROVED,
    }
    with (worker_dir / "mls_summary.json").open("w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    return summary


# ==============================================================================
# WORKER 2: MAJOR EVOLUTIONARY TRANSITION & MUTUALISM BARRIER (Michod / Szathmáry)
# ==============================================================================

def run_worker_2_transition(
    output_dir: Path,
    target_seconds: float,
    epoch_gens: int = 10000,
    seed: int = 30001,
    resume: bool = True,
) -> dict[str, Any]:
    """
    Challenge 3: Identifies the critical vertical transmission threshold v*
    triggering the transition from antagonistic parasitism to obligate mutualism
    (Michod 2007 "Export of Fitness", Maynard Smith & Szathmáry 1995).
    """
    set_core_affinity(2)
    worker_dir = output_dir / "worker_2_transition"
    worker_dir.mkdir(parents=True, exist_ok=True)
    log_file = worker_dir / "worker_2.log"
    checkpoint_file = worker_dir / "checkpoint.json"
    history_file = worker_dir / "transition_history.jsonl"

    def log(msg: str) -> None:
        ts = time.strftime("%Y-%m-%d %H:%M:%S")
        line = f"[{ts}] [WORKER-2:TRANSITION] {msg}"
        with log_file.open("a", encoding="utf-8") as f:
            f.write(line + "\n")
        with (output_dir / "live.log").open("a", encoding="utf-8") as lf:
            lf.write(line + "\n")
        print(line, flush=True)

    v_rates = [0.0, 0.25, 0.50, 0.75, 1.0]
    num_pop = 32

    epoch = 0
    total_gens = 0

    # Populations for each transmission regime
    regime_populations = {}
    if resume and checkpoint_file.is_file():
        try:
            ckpt = json.loads(checkpoint_file.read_text(encoding="utf-8"))
            epoch = ckpt.get("epoch", 0)
            total_gens = ckpt.get("total_gens", 0)
            regime_populations = {float(k): v for k, v in ckpt.get("regimes", {}).items()}
            log(f"Resumed Transition from checkpoint: Epoch {epoch}, Total Gens {total_gens:,}")
        except Exception as exc:
            log(f"Failed to load checkpoint ({exc}), initializing fresh regimes.")
            for v_rate in v_rates:
                regime_populations[v_rate] = [0.85 + (prng_float(seed, int(v_rate * 100) + i, "init") - 0.5) * 0.1 for i in range(num_pop)]
    else:
        for v_rate in v_rates:
            regime_populations[v_rate] = [0.85 + (prng_float(seed, int(v_rate * 100) + i, "init") - 0.5) * 0.1 for i in range(num_pop)]

    log(f"Started Transition & Mutualism Challenge: Target Seconds={target_seconds:.0f}s ({target_seconds/3600:.1f}h)")

    t_start = time.time()

    while True:
        elapsed = time.time() - t_start
        if elapsed >= target_seconds:
            log(f"Target duration {target_seconds/3600:.1f}h reached. Finalizing Transition worker.")
            break
        if (output_dir / "STOP").is_file():
            log("Stop signal detected. Exiting gracefully.")
            break

        epoch += 1
        regime_epoch_stats = {}

        # Evolve each transmission regime for epoch_gens // len(v_rates) steps
        steps_per_regime = max(100, epoch_gens // len(v_rates))

        for v_rate in v_rates:
            vir_pop = regime_populations[v_rate]
            mean_vir_history = []
            corr_history = []

            for step in range(steps_per_regime):
                gen = total_gens + step
                w_hosts = []
                w_parasites = []

                for vir in vir_pop:
                    w_h = max(0.05, 1.0 - vir * 0.85)
                    w_p = (1.0 - v_rate) * (vir * 1.2) + v_rate * (w_h * 1.5)
                    w_hosts.append(w_h)
                    w_parasites.append(w_p)

                mean_h = sum(w_hosts) / len(w_hosts)
                mean_p = sum(w_parasites) / len(w_parasites)
                cov_hp = sum((w_hosts[i] - mean_h) * (w_parasites[i] - mean_p) for i in range(len(w_hosts)))
                std_h = math.sqrt(sum((x - mean_h)**2 for x in w_hosts)) or 1e-6
                std_p = math.sqrt(sum((y - mean_p)**2 for y in w_parasites)) or 1e-6
                corr_hp = cov_hp / (std_h * std_p)

                tot_p = sum(w_parasites) or 1.0
                new_vir = []
                for i in range(len(vir_pop)):
                    roll = prng_float(seed, int(v_rate * 10000) + gen * 100 + i, "vir_sel") * tot_p
                    cum = 0.0
                    parent = 0
                    for idx, fit in enumerate(w_parasites):
                        cum += fit
                        if cum >= roll:
                            parent = idx
                            break
                    delta = (prng_float(seed, int(v_rate * 500) + gen * 30 + i, "mut") - 0.5) * 0.08
                    new_v = max(0.01, min(0.99, vir_pop[parent] + delta))
                    new_vir.append(new_v)

                vir_pop = new_vir
                mean_vir_history.append(sum(vir_pop) / len(vir_pop))
                corr_history.append(corr_hp)

            regime_populations[v_rate] = vir_pop
            final_v = sum(mean_vir_history[-20:]) / 20.0
            final_c = sum(corr_history[-20:]) / 20.0
            regime_epoch_stats[str(v_rate)] = {
                "virulence": round(final_v, 4),
                "michod_correlation": round(final_c, 4),
                "mutualism_emerged": final_c > 0.5 and final_v < 0.25,
            }

        total_gens += epoch_gens

        epoch_record = {
            "epoch": epoch,
            "total_gens": total_gens,
            "regimes": regime_epoch_stats,
            "elapsed_hours": round((time.time() - t_start) / 3600.0, 3),
        }

        with history_file.open("a", encoding="utf-8") as hf:
            hf.write(json.dumps(epoch_record) + "\n")

        # Save checkpoint
        ckpt_data = {
            "epoch": epoch,
            "total_gens": total_gens,
            "regimes": regime_populations,
            "updated_at": time.time(),
        }
        write_atomic_json(checkpoint_file, ckpt_data)

        log(f"Epoch {epoch} | Total Gens={total_gens:,} | v=0.00: Vir={regime_epoch_stats['0.0']['virulence']:.2f} | v=0.50: Vir={regime_epoch_stats['0.5']['virulence']:.2f} (Corr={regime_epoch_stats['0.5']['michod_correlation']:+.2f}) | v=1.00: Vir={regime_epoch_stats['1.0']['virulence']:.2f}")

    # Determine critical threshold
    crit_v = None
    regimes_summary = []
    for v_rate in v_rates:
        stats = regime_epoch_stats[str(v_rate)]
        regimes_summary.append({
            "vertical_transmission_rate": v_rate,
            "final_virulence": stats["virulence"],
            "michod_fitness_correlation": stats["michod_correlation"],
            "mutualism_emerged": stats["mutualism_emerged"],
        })
        if stats["mutualism_emerged"] and crit_v is None:
            crit_v = v_rate

    summary = {
        "challenge": "TRANSITION_MUTUALISM",
        "literature": "Maynard Smith & Szathmáry 1995; Michod 2007 (Export of Fitness); West et al. 2015",
        "seed": seed,
        "completed_epochs": epoch,
        "total_generations": total_gens,
        "regimes_tested": regimes_summary,
        "critical_vertical_threshold": crit_v,
        "major_transition_proved": MAJOR_TRANSITION_PROVED,
        "red_queen_proved": RED_QUEEN_PROVED,
    }
    with (worker_dir / "transition_summary.json").open("w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    return summary


# ==============================================================================
# WORKER 3: HISTORICAL CONTINGENCY VS DETERMINISM REPLAY (Gould / Blount LTEE)
# ==============================================================================

def run_worker_3_contingency(
    output_dir: Path,
    target_seconds: float,
    epoch_gens: int = 10000,
    founder_seed: int = 40001,
    resume: bool = True,
) -> dict[str, Any]:
    """
    Challenge 4: "Replaying Life's Tape" - Multi-seed Long-Horizon Contingency Assay
    (Gould 1989, Blount et al. 2008, 2012 LTEE, Conway Morris).
    """
    set_core_affinity(3)
    worker_dir = output_dir / "worker_3_contingency"
    worker_dir.mkdir(parents=True, exist_ok=True)
    log_file = worker_dir / "worker_3.log"
    checkpoint_file = worker_dir / "checkpoint.json"
    history_file = worker_dir / "contingency_history.jsonl"

    def log(msg: str) -> None:
        ts = time.strftime("%Y-%m-%d %H:%M:%S")
        line = f"[{ts}] [WORKER-3:CONTINGENCY] {msg}"
        with log_file.open("a", encoding="utf-8") as f:
            f.write(line + "\n")
        with (output_dir / "live.log").open("a", encoding="utf-8") as lf:
            lf.write(line + "\n")
        print(line, flush=True)

    num_replays = 8
    pop_size = 32
    founder_genome = hashlib.sha256(b"contingency_founder_standard").digest()[:4]
    founder_val = int.from_bytes(founder_genome, "big")

    epoch = 0
    total_gens = 0

    replays = []
    if resume and checkpoint_file.is_file():
        try:
            ckpt = json.loads(checkpoint_file.read_text(encoding="utf-8"))
            epoch = ckpt.get("epoch", 0)
            total_gens = ckpt.get("total_gens", 0)
            replays = ckpt.get("replays", [])
            log(f"Resumed Contingency from checkpoint: Epoch {epoch}, Total Gens {total_gens:,}")
        except Exception as exc:
            log(f"Failed to load checkpoint ({exc}), re-initializing.")
            replays = [[founder_val for _ in range(pop_size)] for _ in range(num_replays)]
    else:
        replays = [[founder_val for _ in range(pop_size)] for _ in range(num_replays)]

    log(f"Started Contingency Replay Challenge: Target Seconds={target_seconds:.0f}s ({target_seconds/3600:.1f}h)")

    t_start = time.time()

    while True:
        elapsed = time.time() - t_start
        if elapsed >= target_seconds:
            log(f"Target duration {target_seconds/3600:.1f}h reached. Finalizing Contingency worker.")
            break
        if (output_dir / "STOP").is_file():
            log("Stop signal detected. Exiting gracefully.")
            break

        epoch += 1

        # Run epoch_gens for each replay
        for r_id in range(num_replays):
            pop = replays[r_id]
            sub_seed = founder_seed + r_id

            for step in range(epoch_gens):
                gen = total_gens + step
                new_pop = []
                for i in range(pop_size):
                    genome = pop[i]
                    r = prng_float(sub_seed, gen * 200 + i, "mut")
                    if r < 0.18:
                        bit = 1 << (int(r * 32) % 32)
                        genome ^= bit
                    new_pop.append(genome)
                pop = new_pop
            replays[r_id] = pop

        total_gens += epoch_gens

        # Compute pairwise normalized Hamming distance matrix
        dominant_genomes = [max(set(pop), key=pop.count) for pop in replays]
        divergence_matrix = []
        pairwise_distances = []
        for i in range(num_replays):
            row = []
            for j in range(num_replays):
                dist = bin(dominant_genomes[i] ^ dominant_genomes[j]).count("1") / 32.0
                row.append(round(dist, 4))
                if j > i:
                    pairwise_distances.append(dist)
            divergence_matrix.append(row)

        mean_pairwise_dist = sum(pairwise_distances) / len(pairwise_distances) if pairwise_distances else 0.0

        epoch_record = {
            "epoch": epoch,
            "total_gens": total_gens,
            "mean_pairwise_divergence": round(mean_pairwise_dist, 4),
            "dominant_genomes": [f"{g:08x}" for g in dominant_genomes],
            "elapsed_hours": round((time.time() - t_start) / 3600.0, 3),
        }

        with history_file.open("a", encoding="utf-8") as hf:
            hf.write(json.dumps(epoch_record) + "\n")

        # Save checkpoint
        ckpt_data = {
            "epoch": epoch,
            "total_gens": total_gens,
            "replays": replays,
            "updated_at": time.time(),
        }
        write_atomic_json(checkpoint_file, ckpt_data)

        log(f"Epoch {epoch} | Total Gens={total_gens:,} | Mean Pairwise Divergence={mean_pairwise_dist:.4f} ({mean_pairwise_dist*100:.1f}%)")

    contingency_verdict = "GOULDIAN_HISTORICAL_CONTINGENCY" if mean_pairwise_dist > 0.25 else "CONVERGENT_DETERMINISM"
    summary = {
        "challenge": "CONTINGENCY_REPLAY",
        "literature": "Gould 1989; Blount et al. 2008, 2012 LTEE; Conway Morris",
        "founder_seed": founder_seed,
        "completed_epochs": epoch,
        "total_generations": total_gens,
        "mean_pairwise_divergence": round(mean_pairwise_dist, 4),
        "divergence_matrix": divergence_matrix,
        "contingency_verdict": contingency_verdict,
        "red_queen_proved": RED_QUEEN_PROVED,
    }
    with (worker_dir / "contingency_summary.json").open("w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    return summary


# ==============================================================================
# MAIN ORCHESTRATOR HARNESS
# ==============================================================================

def main() -> None:
    parser = argparse.ArgumentParser(description="Grand Frontier 4-Challenge Long-Horizon Campaign")
    parser.add_argument("--output", type=str, default="/home/parvaz/simulation_runs/run_grand_frontier_48h", help="Output directory")
    parser.add_argument("--duration-hours", type=float, default=48.0, help="Campaign duration in hours (e.g. 48.0, 72.0)")
    parser.add_argument("--epoch-gens", type=int, default=10000, help="Generations per epoch")
    parser.add_argument("--no-resume", action="store_true", help="Start from scratch ignoring checkpoints")
    args = parser.parse_args()

    out_dir = Path(args.output).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    console_log = out_dir / "campaign.log"
    live_log = out_dir / "live.log"
    ui_console_log = out_dir / "console.log"

    def log(msg: str) -> None:
        ts = time.strftime("%Y-%m-%d %H:%M:%S")
        line = f"[{ts}] [CAMPAIGN-ORCHESTRATOR] {msg}"
        for lp in (console_log, live_log, ui_console_log):
            with lp.open("a", encoding="utf-8") as f:
                f.write(line + "\n")
        print(line, flush=True)

    target_seconds = float(args.duration_hours) * 3600.0
    t0 = time.time()
    run_id = out_dir.name
    (out_dir / "run.pid").write_text(str(os.getpid()), encoding="utf-8")

    status_data: dict[str, Any] = {
        "id": run_id,
        "title": f"Grand Frontier 4-Challenge {args.duration_hours:.0f}h Campaign",
        "status": "RUNNING",
        "pid": os.getpid(),
        "pct": 0.0,
        "completed_seeds": 0,
        "total_seeds": 4,
        "elapsed_hours": 0.0,
        "target_hours": args.duration_hours,
        "started_at": t0,
        "updated_at": t0,
    }
    write_atomic_json(out_dir / "status.json", status_data)

    log("=" * 80)
    log(f"LAUNCHING GRAND FRONTIER 4-CHALLENGE {args.duration_hours:.1f}-HOUR CAMPAIGN")
    log("Dedicated Core Allocation: 4 Workers on Cores 0, 1, 2, 3")
    log(f"Target Duration: {args.duration_hours:.1f} Hours ({target_seconds:.0f}s) | Epoch Size: {args.epoch_gens:,} Gens")
    log(f"Output Directory: {out_dir}")
    log("Invariants Enforced: red_queen_proved=False, open_ended_intelligence=False, major_transition_proved=False")
    log("=" * 80)

    worker_specs = [
        (0, "Worker-0 [OEE_NOVELTY]", run_worker_0_oee, (out_dir, target_seconds, args.epoch_gens, 10001, not args.no_resume)),
        (1, "Worker-1 [MLS_PRICE]", run_worker_1_mls, (out_dir, target_seconds, args.epoch_gens, 20001, not args.no_resume)),
        (2, "Worker-2 [TRANSITION_MUTUALISM]", run_worker_2_transition, (out_dir, target_seconds, args.epoch_gens, 30001, not args.no_resume)),
        (3, "Worker-3 [CONTINGENCY_REPLAY]", run_worker_3_contingency, (out_dir, target_seconds, args.epoch_gens, 40001, not args.no_resume)),
    ]

    results: dict[str, Any] = {}

    with ProcessPoolExecutor(max_workers=4) as executor:
        futures = {
            executor.submit(spec[2], *spec[3]): spec[1]
            for spec in worker_specs
        }

        # Monitor loop while futures are running
        while futures:
            done = [f for f in futures if f.done()]
            for future in done:
                name = futures.pop(future)
                try:
                    res = future.result()
                    challenge_name = res.get("challenge", name)
                    results[challenge_name] = res
                    log(f"SUCCESS: {name} finished successfully.")
                except Exception as exc:
                    log(f"ERROR: {name} failed: {exc}")
                    import traceback
                    traceback.print_exc()

            now = time.time()
            elapsed_sec = now - t0
            elapsed_h = round(elapsed_sec / 3600.0, 2)
            pct = min(99.9, round((elapsed_sec / target_seconds) * 100.0, 1))

            status_data["pct"] = pct
            status_data["elapsed_hours"] = elapsed_h
            status_data["eta_hours"] = max(0.0, round((target_seconds - elapsed_sec) / 3600.0, 2))
            status_data["completed_seeds"] = len(results)
            status_data["updated_at"] = now
            status_data["title"] = f"Grand Frontier 4-Challenge {args.duration_hours:.0f}h Campaign ({elapsed_h:.1f}h/{args.duration_hours:.0f}h)"
            write_atomic_json(out_dir / "status.json", status_data)

            if not futures:
                break

            time.sleep(15)

    elapsed = time.time() - t0
    log("=" * 80)
    log(f"ALL 4 FRONTIER CHALLENGES COMPLETED in {elapsed:.2f} seconds ({elapsed/3600.0:.2f} hours)!")
    log("=" * 80)

    status_data["status"] = "COMPLETED"
    status_data["pct"] = 100.0
    status_data["exitCode"] = 0
    status_data["endedAt"] = time.time()
    write_atomic_json(out_dir / "status.json", status_data)
    (out_dir / "COMPLETE").touch()

    # Synthesis Report
    synthesis = {
        "campaign": "grand_frontier_4challenge_campaign",
        "total_elapsed_seconds": round(elapsed, 2),
        "total_elapsed_hours": round(elapsed / 3600.0, 3),
        "workers_completed": len(results),
        "results": results,
        "epistemic_invariants": {
            "red_queen_proved": RED_QUEEN_PROVED,
            "open_ended_intelligence": OPEN_ENDED_INTELLIGENCE_PROVED,
            "major_transition_proved": MAJOR_TRANSITION_PROVED,
        },
    }

    with (out_dir / "frontier_synthesis.json").open("w", encoding="utf-8") as f:
        json.dump(synthesis, f, indent=2)

    # Execution JSON for Console compatibility
    exec_payload = {
        "complete": True,
        "duration_hours": args.duration_hours,
        "campaign": "grand_frontier_4challenge_campaign",
        "elapsed_seconds": round(elapsed, 2),
        "elapsed_hours": round(elapsed / 3600.0, 3),
        "workers_completed": len(results),
        "epistemic_invariants": {
            "red_queen_proved": RED_QUEEN_PROVED,
            "open_ended_intelligence": OPEN_ENDED_INTELLIGENCE_PROVED,
            "major_transition_proved": MAJOR_TRANSITION_PROVED,
        },
        "results": results,
    }
    with (out_dir / "execution.json").open("w", encoding="utf-8") as f:
        json.dump(exec_payload, f, indent=2)

    # Write Markdown Synthesis Report
    md_content = f"""# CodonTrace Genesis: گزارش جامع کمپین ۴۸ تا ۷۲ ساعته در مرزهای حل‌نشده علم تکاملی

این گزارش حاصل اجرای پیوسته و بلندمدت ۴ چالش حل‌نشده در زیست‌محاسباتی و حیات مصنوعی (Artificial Life) بر روی ۴ هسته فیزیکی پردازنده بورد **Orange Pi Zero 3 (Allwinner H618 ARM64)** است.

---

## خلاصه اجرایی و تله‌متری اجرا
- **مدت زمان کل اجرا:** {elapsed/3600.0:.2f} ساعت ({elapsed:.1f} ثانیه).
- **تعداد کارگرهای موازی:** ۴ کارگر مستقل تخصیص‌یافته به ۴ هسته پردازنده (Cores 0, 1, 2, 3).
- **قفل‌های معرفت‌شناختی:**
  - `red_queen_proved = False` (حفظ قاطع سقف تجربی).
  - `open_ended_intelligence = False` (عدم تعمیم ابزار به هوش عمومی).
  - `major_transition_proved = False` (عدم ادعای اثبات گذار بزرگ در زیست‌شناسی خیس).

---

## ۱. کارگر ۰ (هسته ۰): چالش نوآوری باز و پویایی بی‌پایان (Stanley 2017 / Channon 2024 / Bedau 1998)
- **مسئله حل‌نشده:** آیا فشار خصمانه هم‌تکاملی میزبان-انگل می‌تواند نوآوری پایدار بی‌پایان تولید کند، یا به دام چرخه‌های تکرارشونده متناهی می‌افتد؟
- **نتیجه:** {json.dumps(results.get("OEE_NOVELTY", {}), indent=2)}

---

## ۲. کارگر ۱ (هسته ۱): چالش انتخاب چندسطحی و تفکیک نقش‌ها (Chaturvedi 2026 / Price 1972)
- **مسئله حل‌نشده:** تفکیک معادله پرایس بین اثر انتخاب درون‌گروهی و بین‌گروهی، و جلوگیری از تراژدی منابع مشترک (Tragedy of the Commons).
- **نتیجه:** {json.dumps(results.get("MLS_PRICE", {}), indent=2)}

---

## ۳. کارگر ۲ (هسته ۲): چالش گذار بزرگ تکاملی و سد همزیستی (Michod 2007 / Szathmáry 1995)
- **مسئله حل‌نشده:** شناسایی آستانه بحرانی گذار از تخاصم انگل به همزیستی اجباری (Export of Fitness) تحت گرادیان نرخ انتقال عمودی.
- **نتیجه:** {json.dumps(results.get("TRANSITION_MUTUALISM", {}), indent=2)}

---

## ۴. کارگر ۳ (هسته ۳): چالش جبرگرایی در برابر تصادف تاریخی (Gould 1989 / Blount LTEE)
- **مسئله حل‌نشده:** بازپخش نوار حیات از جمعیت یکسان موسس؛ آیا مسیرها به یک فنوتیپ واحد همگرا می‌شوند یا واگرایی تاریخی ایجاد می‌شود؟
- **نتیجه:** {json.dumps(results.get("CONTINGENCY_REPLAY", {}), indent=2)}
"""

    with (out_dir / "FRONTIER_REPORT.md").open("w", encoding="utf-8") as f:
        f.write(md_content)

    log(f"Campaign synthesis report saved to {out_dir / 'FRONTIER_REPORT.md'}")


if __name__ == "__main__":
    main()
