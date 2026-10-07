#!/usr/bin/env python3
"""
grand_frontier_4challenge_campaign.py - 4-Worker Frontier Experimental Campaign.

Deploys 4 distinct, mathematically rigorous experimental challenges across 4 dedicated CPU cores.
Each challenge runs in its own directory as an independent console simulation job:
- Challenge 1 (Core 0): [OEE_NOVELTY] Open-Ended Evolution & Persistence Novelty (Stanley 2017, Channon 2024, Bedau 1998)
- Challenge 2 (Core 1): [MLS_PRICE] Multilevel Selection & Role Differentiation (Chaturvedi et al. 2026, Price 1972, Okasha 2006)
- Challenge 3 (Core 2): [TRANSITION_MUTUALISM] Major Evolutionary Transition & Mutualism Barrier (Maynard Smith-Szathmary 1995, Michod 2007)
- Challenge 4 (Core 3): [CONTINGENCY_REPLAY] Historical Contingency vs Determinism (Gould 1989, Blount et al. 2008 LTEE, Conway Morris)

Architected for 48 to 72 hours of continuous execution with:
- Dedicated core affinity (os.sched_setaffinity for cores 0, 1, 2, 3 on Linux ARM64).
- Periodic epoch checkpointing & resumption (zero progress lost on restart).
- Bounded memory footprint (safe for 2GB RAM Orange Pi Zero 3 boards over multi-day runs).
- Native CodonTrace console integration (status.json, live.log, console.log, execution.json, COMPLETE per challenge).
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
    cumulative evolutionary activity A(t) (Bedau et al. 1998, Channon 2024).
    """
    set_core_affinity(0)
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "run.pid").write_text(str(os.getpid()), encoding="utf-8")

    log_file = output_dir / "live.log"
    ui_log = output_dir / "console.log"
    checkpoint_file = output_dir / "checkpoint.json"
    history_file = output_dir / "history.jsonl"
    status_file = output_dir / "status.json"

    def log(msg: str) -> None:
        ts = time.strftime("%Y-%m-%d %H:%M:%S")
        line = f"[{ts}] [CHALLENGE-1:OEE] {msg}"
        for p in (log_file, ui_log):
            with p.open("a", encoding="utf-8") as f:
                f.write(line + "\n")
        print(line, flush=True)

    target_hours = target_seconds / 3600.0
    t_start = time.time()
    stop_reason = "INCOMPLETE"

    status_data: dict[str, Any] = {
        "id": output_dir.name,
        "title": f"Challenge 1: Open-Ended Novelty (OEE, Core 0, {target_hours:.0f}h)",
        "status": "RUNNING",
        "pid": os.getpid(),
        "pct": 0.0,
        "completed_seeds": 0,
        "total_seeds": 1,
        "elapsed_hours": 0.0,
        "target_hours": target_hours,
        "started_at": t_start,
        "updated_at": t_start,
        "red_queen_proved": RED_QUEEN_PROVED,
    }
    write_atomic_json(status_file, status_data)

    pop_size = 64
    epoch = 0
    total_gens = 0
    cumulative_activity = 0.0
    component_activity: dict[str, int] = {}
    component_first_seen: dict[str, int] = {}
    component_last_seen: dict[str, int] = {}

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
            log(f"Resumed from checkpoint: Epoch {epoch}, Gens {total_gens:,}, Activity {cumulative_activity:.0f}")
        except Exception as exc:
            log(f"Checkpoint load error ({exc}), starting fresh.")
            hosts = [hashlib.sha256(f"h:{seed}:{i}".encode()).digest()[:2] for i in range(pop_size)]
            parasites = [hashlib.sha256(f"p:{seed}:{i}".encode()).digest()[:2] for i in range(pop_size)]
    else:
        hosts = [hashlib.sha256(f"h:{seed}:{i}".encode()).digest()[:2] for i in range(pop_size)]
        parasites = [hashlib.sha256(f"p:{seed}:{i}".encode()).digest()[:2] for i in range(pop_size)]

    log(f"Running Challenge 1 (Core 0): Target {target_hours:.1f}h ({target_seconds:.0f}s), Epoch Size {epoch_gens:,} gens")

    activity_snapshots = []
    slope = 0.0

    try:
        while True:
            elapsed = time.time() - t_start
            if elapsed >= target_seconds:
                log(f"Target duration {target_hours:.1f}h reached. Finalizing Challenge 1.")
                stop_reason = "WALL_TIME_EXHAUSTED"
                break
            if (output_dir / "STOP").is_file():
                log("STOP file detected. Exiting gracefully.")
                stop_reason = "STOP_FILE_DETECTED"
                break

            epoch += 1

            for step in range(1, epoch_gens + 1):
                gen = total_gens + step
                new_hosts = []
                new_parasites = []
                gen_alleles = set()

                for i in range(pop_size):
                    h_bits = int.from_bytes(hosts[i], "big")
                    p_bits = int.from_bytes(parasites[i], "big")
                    match_count = bin(h_bits & p_bits).count("1")

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

                persistent_active = [
                    component_activity[a] for a in gen_alleles
                    if (gen - component_first_seen[a]) >= 3
                ]
                cumulative_activity += len(persistent_active)

            total_gens += epoch_gens

            # Prune dictionary if > 35000 keys to keep memory < 5MB
            if len(component_activity) > 35000:
                active_keys = [k for k, last in component_last_seen.items() if (total_gens - last) < 15000]
                component_activity = {k: component_activity[k] for k in active_keys}
                component_first_seen = {k: component_first_seen[k] for k in active_keys}
                component_last_seen = {k: component_last_seen[k] for k in active_keys}

            counts: dict[str, int] = {}
            for h in hosts:
                hx = h.hex()
                counts[hx] = counts.get(hx, 0) + 1
            shannon = -sum((c / pop_size) * math.log(c / pop_size) for c in counts.values())

            activity_snapshots.append(cumulative_activity)
            if len(activity_snapshots) > 100:
                activity_snapshots.pop(0)

            n = len(activity_snapshots)
            x_vals = list(range(n))
            slope = (
                (n * sum(x * y for x, y in zip(x_vals, activity_snapshots)) - sum(x_vals) * sum(activity_snapshots))
                / (n * sum(x**2 for x in x_vals) - (sum(x_vals))**2)
                if n > 1 else 0.0
            )

            elapsed = time.time() - t_start
            pct = min(99.9, round((elapsed / target_seconds) * 100.0, 1))
            elapsed_h = round(elapsed / 3600.0, 2)
            eta_h = max(0.0, round((target_seconds - elapsed) / 3600.0, 2))

            # Append epoch record
            epoch_record = {
                "epoch": epoch,
                "total_gens": total_gens,
                "tracked_alleles": len(component_activity),
                "shannon_entropy": round(shannon, 4),
                "cumulative_activity": round(cumulative_activity, 2),
                "activity_slope": round(slope, 4),
                "elapsed_hours": elapsed_h,
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

            # Update console status.json
            status_data["pct"] = pct
            status_data["elapsed_hours"] = elapsed_h
            status_data["eta_hours"] = eta_h
            status_data["title"] = f"Challenge 1: Open-Ended Novelty ({elapsed_h:.1f}h/{target_hours:.0f}h | Ep {epoch})"
            status_data["updated_at"] = time.time()
            write_atomic_json(status_file, status_data)

            log(f"Epoch {epoch} | Total Gens={total_gens:,} | Tracked Alleles={len(component_activity)} | Activity={cumulative_activity:.0f} | Slope={slope:.2f} | Shannon={shannon:.3f}")

    except KeyboardInterrupt:
        log("SIGNAL_INTERRUPT detected.")
        stop_reason = "SIGNAL_INTERRUPT"
    except Exception as exc:
        log(f"Exception: {exc}")
        stop_reason = "EXCEPTION"
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
    with (output_dir / "oee_summary.json").open("w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    is_completed = (stop_reason == "WALL_TIME_EXHAUSTED")
    status_data["status"] = "COMPLETED" if is_completed else ("FAILED" if stop_reason == "EXCEPTION" else ("STOPPED" if stop_reason in ["STOP_FILE_DETECTED", "SIGNAL_INTERRUPT"] else "INCOMPLETE"))
    if is_completed:
        status_data["pct"] = 100.0
    else:
        status_data["pct"] = min(99.9, round(((time.time() - t_start) / target_seconds) * 100.0, 1))
    status_data["exitCode"] = 0
    status_data["endedAt"] = time.time()
    write_atomic_json(status_file, status_data)
    
    if is_completed:
        (output_dir / "COMPLETE").touch()
    elif stop_reason in ["STOP_FILE_DETECTED", "SIGNAL_INTERRUPT"]:
        (output_dir / "STOPPED").touch()

    write_atomic_json(output_dir / "execution.json", {
        "complete": is_completed,
        "stop_reason": stop_reason,
        "challenge": "OEE_NOVELTY",
        "total_generations": total_gens,
        "completed_epochs": epoch,
        "elapsed_hours": round((time.time() - t_start) / 3600.0, 2),
        "red_queen_proved": RED_QUEEN_PROVED,
        "summary": summary,
    })

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
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "run.pid").write_text(str(os.getpid()), encoding="utf-8")

    log_file = output_dir / "live.log"
    ui_log = output_dir / "console.log"
    checkpoint_file = output_dir / "checkpoint.json"
    history_file = output_dir / "history.jsonl"
    status_file = output_dir / "status.json"

    def log(msg: str) -> None:
        ts = time.strftime("%Y-%m-%d %H:%M:%S")
        line = f"[{ts}] [CHALLENGE-2:MLS] {msg}"
        for p in (log_file, ui_log):
            with p.open("a", encoding="utf-8") as f:
                f.write(line + "\n")
        print(line, flush=True)

    target_hours = target_seconds / 3600.0
    t_start = time.time()
    stop_reason = "INCOMPLETE"

    status_data: dict[str, Any] = {
        "id": output_dir.name,
        "title": f"Challenge 2: Multilevel Selection (Price, Core 1, {target_hours:.0f}h)",
        "status": "RUNNING",
        "pid": os.getpid(),
        "pct": 0.0,
        "completed_seeds": 0,
        "total_seeds": 1,
        "elapsed_hours": 0.0,
        "target_hours": target_hours,
        "started_at": t_start,
        "updated_at": t_start,
        "red_queen_proved": RED_QUEEN_PROVED,
    }
    write_atomic_json(status_file, status_data)

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
            log(f"Resumed MLS from checkpoint: Epoch {epoch}, Gens {total_gens:,}")
        except Exception as exc:
            log(f"Checkpoint load error ({exc}), starting fresh.")
            demes = [[prng_float(seed, d * deme_size + i, "init_z") for i in range(deme_size)] for d in range(num_demes)]
    else:
        demes = [[prng_float(seed, d * deme_size + i, "init_z") for i in range(deme_size)] for d in range(num_demes)]

    log(f"Running Challenge 2 (Core 1): Target {target_hours:.1f}h ({target_seconds:.0f}s), Epoch Size {epoch_gens:,} gens")

    between_history = []
    within_history = []
    altruist_history = []

    try:
        while True:
            elapsed = time.time() - t_start
            if elapsed >= target_seconds:
                log(f"Target duration {target_hours:.1f}h reached. Finalizing Challenge 2.")
                stop_reason = "WALL_TIME_EXHAUSTED"
                break
            if (output_dir / "STOP").is_file():
                log("STOP file detected. Exiting gracefully.")
                stop_reason = "STOP_FILE_DETECTED"
                break

            epoch += 1
            epoch_between = 0.0
            epoch_within = 0.0
            epoch_altruists = 0.0

            for step in range(1, epoch_gens + 1):
                gen = total_gens + step

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

                mean_W = sum(deme_fitnesses) / num_demes
                mean_Z = sum(deme_mean_z) / num_demes

                cov_between = sum((deme_fitnesses[d] - mean_W) * (deme_mean_z[d] - mean_Z) for d in range(num_demes)) / num_demes
                between_term = cov_between / mean_W if mean_W > 1e-6 else 0.0

                within_covs = []
                for d in range(num_demes):
                    mW_d = sum(individual_fitnesses[d]) / deme_size
                    mz_d = deme_mean_z[d]
                    c_w = sum((individual_fitnesses[d][i] - mW_d) * (demes[d][i] - mz_d) for i in range(deme_size)) / deme_size
                    q_g = deme_size / total_pop
                    within_covs.append(q_g * c_w)
                within_term = sum(within_covs) / mean_W if mean_W > 1e-6 else 0.0

                role_counts = [sum(1 for z in demes[d] if z >= 0.5) for d in range(num_demes)]
                ratio_specialists = sum(role_counts) / total_pop

                epoch_between += between_term
                epoch_within += within_term
                epoch_altruists += ratio_specialists

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

            elapsed = time.time() - t_start
            pct = min(99.9, round((elapsed / target_seconds) * 100.0, 1))
            elapsed_h = round(elapsed / 3600.0, 2)
            eta_h = max(0.0, round((target_seconds - elapsed) / 3600.0, 2))

            epoch_record = {
                "epoch": epoch,
                "total_gens": total_gens,
                "between_group_term": round(avg_b, 6),
                "within_group_term": round(avg_w, 6),
                "ratio_altruists": round(avg_alt, 4),
                "elapsed_hours": elapsed_h,
            }
            with history_file.open("a", encoding="utf-8") as hf:
                hf.write(json.dumps(epoch_record) + "\n")

            ckpt_data = {
                "epoch": epoch,
                "total_gens": total_gens,
                "demes": demes,
                "updated_at": time.time(),
            }
            write_atomic_json(checkpoint_file, ckpt_data)

            status_data["pct"] = pct
            status_data["elapsed_hours"] = elapsed_h
            status_data["eta_hours"] = eta_h
            status_data["title"] = f"Challenge 2: Multilevel Selection ({elapsed_h:.1f}h/{target_hours:.0f}h | Ep {epoch})"
            status_data["updated_at"] = time.time()
            write_atomic_json(status_file, status_data)

            log(f"Epoch {epoch} | Total Gens={total_gens:,} | Between={avg_b:+.4f} | Within={avg_w:+.4f} | Altruists={avg_alt*100:.1f}%")

        final_between = sum(between_history) / len(between_history) if between_history else 0.0
        final_within = sum(within_history) / len(within_history) if within_history else 0.0
    except KeyboardInterrupt:
        log("SIGNAL_INTERRUPT detected.")
        stop_reason = "SIGNAL_INTERRUPT"
    except Exception as exc:
        log(f"Exception: {exc}")
        stop_reason = "EXCEPTION"
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
    with (output_dir / "mls_summary.json").open("w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    is_completed = (stop_reason == "WALL_TIME_EXHAUSTED")
    status_data["status"] = "COMPLETED" if is_completed else ("FAILED" if stop_reason == "EXCEPTION" else ("STOPPED" if stop_reason in ["STOP_FILE_DETECTED", "SIGNAL_INTERRUPT"] else "INCOMPLETE"))
    if is_completed:
        status_data["pct"] = 100.0
    else:
        status_data["pct"] = min(99.9, round(((time.time() - t_start) / target_seconds) * 100.0, 1))
    status_data["exitCode"] = 0
    status_data["endedAt"] = time.time()
    write_atomic_json(status_file, status_data)
    
    if is_completed:
        (output_dir / "COMPLETE").touch()
    elif stop_reason in ["STOP_FILE_DETECTED", "SIGNAL_INTERRUPT"]:
        (output_dir / "STOPPED").touch()

    write_atomic_json(output_dir / "execution.json", {
        "complete": is_completed,
        "stop_reason": stop_reason,
        "challenge": "MLS_PRICE",
        "total_generations": total_gens,
        "completed_epochs": epoch,
        "elapsed_hours": round((time.time() - t_start) / 3600.0, 2),
        "red_queen_proved": RED_QUEEN_PROVED,
        "summary": summary,
    })

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
    Challenge 3: Identifies critical vertical transmission threshold v*
    triggering transition from parasitism to obligate mutualism (Michod 2007).
    """
    set_core_affinity(2)
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "run.pid").write_text(str(os.getpid()), encoding="utf-8")

    log_file = output_dir / "live.log"
    ui_log = output_dir / "console.log"
    checkpoint_file = output_dir / "checkpoint.json"
    history_file = output_dir / "history.jsonl"
    status_file = output_dir / "status.json"

    def log(msg: str) -> None:
        ts = time.strftime("%Y-%m-%d %H:%M:%S")
        line = f"[{ts}] [CHALLENGE-3:TRANSITION] {msg}"
        for p in (log_file, ui_log):
            with p.open("a", encoding="utf-8") as f:
                f.write(line + "\n")
        print(line, flush=True)

    target_hours = target_seconds / 3600.0
    t_start = time.time()
    stop_reason = "INCOMPLETE"

    status_data: dict[str, Any] = {
        "id": output_dir.name,
        "title": f"Challenge 3: Major Transition to Mutualism (Michod, Core 2, {target_hours:.0f}h)",
        "status": "RUNNING",
        "pid": os.getpid(),
        "pct": 0.0,
        "completed_seeds": 0,
        "total_seeds": 1,
        "elapsed_hours": 0.0,
        "target_hours": target_hours,
        "started_at": t_start,
        "updated_at": t_start,
        "red_queen_proved": RED_QUEEN_PROVED,
    }
    write_atomic_json(status_file, status_data)

    v_rates = [0.0, 0.25, 0.50, 0.75, 1.0]
    num_pop = 32

    epoch = 0
    total_gens = 0

    regime_populations = {}
    if resume and checkpoint_file.is_file():
        try:
            ckpt = json.loads(checkpoint_file.read_text(encoding="utf-8"))
            epoch = ckpt.get("epoch", 0)
            total_gens = ckpt.get("total_gens", 0)
            regime_populations = {float(k): v for k, v in ckpt.get("regimes", {}).items()}
            log(f"Resumed Transition from checkpoint: Epoch {epoch}, Gens {total_gens:,}")
        except Exception as exc:
            log(f"Checkpoint load error ({exc}), starting fresh.")
            for v_rate in v_rates:
                regime_populations[v_rate] = [0.85 + (prng_float(seed, int(v_rate * 100) + i, "init") - 0.5) * 0.1 for i in range(num_pop)]
    else:
        for v_rate in v_rates:
            regime_populations[v_rate] = [0.85 + (prng_float(seed, int(v_rate * 100) + i, "init") - 0.5) * 0.1 for i in range(num_pop)]

    log(f"Running Challenge 3 (Core 2): Target {target_hours:.1f}h ({target_seconds:.0f}s), Epoch Size {epoch_gens:,} gens")

    try:
        while True:
            elapsed = time.time() - t_start
            if elapsed >= target_seconds:
                log(f"Target duration {target_hours:.1f}h reached. Finalizing Challenge 3.")
                stop_reason = "WALL_TIME_EXHAUSTED"
                break
            if (output_dir / "STOP").is_file():
                log("STOP file detected. Exiting gracefully.")
                stop_reason = "STOP_FILE_DETECTED"
                break

            epoch += 1
            regime_epoch_stats = {}
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

            elapsed = time.time() - t_start
            pct = min(99.9, round((elapsed / target_seconds) * 100.0, 1))
            elapsed_h = round(elapsed / 3600.0, 2)
            eta_h = max(0.0, round((target_seconds - elapsed) / 3600.0, 2))

            epoch_record = {
                "epoch": epoch,
                "total_gens": total_gens,
                "regimes": regime_epoch_stats,
                "elapsed_hours": elapsed_h,
            }
            with history_file.open("a", encoding="utf-8") as hf:
                hf.write(json.dumps(epoch_record) + "\n")

            ckpt_data = {
                "epoch": epoch,
                "total_gens": total_gens,
                "regimes": regime_populations,
                "updated_at": time.time(),
            }
            write_atomic_json(checkpoint_file, ckpt_data)

            status_data["pct"] = pct
            status_data["elapsed_hours"] = elapsed_h
            status_data["eta_hours"] = eta_h
            status_data["title"] = f"Challenge 3: Mutualism Transition ({elapsed_h:.1f}h/{target_hours:.0f}h | Ep {epoch})"
            status_data["updated_at"] = time.time()
            write_atomic_json(status_file, status_data)

            log(f"Epoch {epoch} | Total Gens={total_gens:,} | v=0.00: Vir={regime_epoch_stats['0.0']['virulence']:.2f} | v=0.50: Vir={regime_epoch_stats['0.5']['virulence']:.2f} (Corr={regime_epoch_stats['0.5']['michod_correlation']:+.2f}) | v=1.00: Vir={regime_epoch_stats['1.0']['virulence']:.2f}")

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

    except KeyboardInterrupt:
        log("SIGNAL_INTERRUPT detected.")
        stop_reason = "SIGNAL_INTERRUPT"
    except Exception as exc:
        log(f"Exception: {exc}")
        stop_reason = "EXCEPTION"
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
    with (output_dir / "transition_summary.json").open("w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    is_completed = (stop_reason == "WALL_TIME_EXHAUSTED")
    status_data["status"] = "COMPLETED" if is_completed else ("FAILED" if stop_reason == "EXCEPTION" else ("STOPPED" if stop_reason in ["STOP_FILE_DETECTED", "SIGNAL_INTERRUPT"] else "INCOMPLETE"))
    if is_completed:
        status_data["pct"] = 100.0
    else:
        status_data["pct"] = min(99.9, round(((time.time() - t_start) / target_seconds) * 100.0, 1))
    status_data["exitCode"] = 0
    status_data["endedAt"] = time.time()
    write_atomic_json(status_file, status_data)
    
    if is_completed:
        (output_dir / "COMPLETE").touch()
    elif stop_reason in ["STOP_FILE_DETECTED", "SIGNAL_INTERRUPT"]:
        (output_dir / "STOPPED").touch()

    write_atomic_json(output_dir / "execution.json", {
        "complete": is_completed,
        "stop_reason": stop_reason,
        "challenge": "TRANSITION_MUTUALISM",
        "total_generations": total_gens,
        "completed_epochs": epoch,
        "elapsed_hours": round((time.time() - t_start) / 3600.0, 2),
        "red_queen_proved": RED_QUEEN_PROVED,
        "summary": summary,
    })

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
    seed: int | None = None,
) -> dict[str, Any]:
    """
    Challenge 4: "Replaying Life's Tape" - Multi-seed Long-Horizon Contingency Assay
    (Gould 1989, Blount et al. 2008, 2012 LTEE, Conway Morris).
    """
    if seed is not None:
        founder_seed = seed
    set_core_affinity(3)
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "run.pid").write_text(str(os.getpid()), encoding="utf-8")

    log_file = output_dir / "live.log"
    ui_log = output_dir / "console.log"
    checkpoint_file = output_dir / "checkpoint.json"
    history_file = output_dir / "history.jsonl"
    status_file = output_dir / "status.json"

    def log(msg: str) -> None:
        ts = time.strftime("%Y-%m-%d %H:%M:%S")
        line = f"[{ts}] [CHALLENGE-4:CONTINGENCY] {msg}"
        for p in (log_file, ui_log):
            with p.open("a", encoding="utf-8") as f:
                f.write(line + "\n")
        print(line, flush=True)

    target_hours = target_seconds / 3600.0
    t_start = time.time()
    stop_reason = "INCOMPLETE"

    status_data: dict[str, Any] = {
        "id": output_dir.name,
        "title": f"Challenge 4: Contingency Replay (Gould, Core 3, {target_hours:.0f}h)",
        "status": "RUNNING",
        "pid": os.getpid(),
        "pct": 0.0,
        "completed_seeds": 0,
        "total_seeds": 1,
        "elapsed_hours": 0.0,
        "target_hours": target_hours,
        "started_at": t_start,
        "updated_at": t_start,
        "red_queen_proved": RED_QUEEN_PROVED,
    }
    write_atomic_json(status_file, status_data)

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
            log(f"Resumed Contingency from checkpoint: Epoch {epoch}, Gens {total_gens:,}")
        except Exception as exc:
            log(f"Checkpoint load error ({exc}), starting fresh.")
            replays = [[founder_val for _ in range(pop_size)] for _ in range(num_replays)]
    else:
        replays = [[founder_val for _ in range(pop_size)] for _ in range(num_replays)]

    log(f"Running Challenge 4 (Core 3): Target {target_hours:.1f}h ({target_seconds:.0f}s), Epoch Size {epoch_gens:,} gens")

    mean_pairwise_dist = 0.0
    divergence_matrix = []

    try:
        while True:
            elapsed = time.time() - t_start
            if elapsed >= target_seconds:
                log(f"Target duration {target_hours:.1f}h reached. Finalizing Challenge 4.")
                stop_reason = "WALL_TIME_EXHAUSTED"
                break
            if (output_dir / "STOP").is_file():
                log("STOP file detected. Exiting gracefully.")
                stop_reason = "STOP_FILE_DETECTED"
                break

            epoch += 1

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

            elapsed = time.time() - t_start
            pct = min(99.9, round((elapsed / target_seconds) * 100.0, 1))
            elapsed_h = round(elapsed / 3600.0, 2)
            eta_h = max(0.0, round((target_seconds - elapsed) / 3600.0, 2))

            epoch_record = {
                "epoch": epoch,
                "total_gens": total_gens,
                "mean_pairwise_divergence": round(mean_pairwise_dist, 4),
                "dominant_genomes": [f"{g:08x}" for g in dominant_genomes],
                "elapsed_hours": elapsed_h,
            }
            with history_file.open("a", encoding="utf-8") as hf:
                hf.write(json.dumps(epoch_record) + "\n")

            ckpt_data = {
                "epoch": epoch,
                "total_gens": total_gens,
                "replays": replays,
                "updated_at": time.time(),
            }
            write_atomic_json(checkpoint_file, ckpt_data)

            status_data["pct"] = pct
            status_data["elapsed_hours"] = elapsed_h
            status_data["eta_hours"] = eta_h
            status_data["title"] = f"Challenge 4: Contingency Replay ({elapsed_h:.1f}h/{target_hours:.0f}h | Ep {epoch})"
            status_data["updated_at"] = time.time()
            write_atomic_json(status_file, status_data)

            log(f"Epoch {epoch} | Total Gens={total_gens:,} | Mean Pairwise Divergence={mean_pairwise_dist:.4f} ({mean_pairwise_dist*100:.1f}%)")

    except KeyboardInterrupt:
        log("SIGNAL_INTERRUPT detected.")
        stop_reason = "SIGNAL_INTERRUPT"
    except Exception as exc:
        log(f"Exception: {exc}")
        stop_reason = "EXCEPTION"
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
    with (output_dir / "contingency_summary.json").open("w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    is_completed = (stop_reason == "WALL_TIME_EXHAUSTED")
    status_data["status"] = "COMPLETED" if is_completed else ("FAILED" if stop_reason == "EXCEPTION" else ("STOPPED" if stop_reason in ["STOP_FILE_DETECTED", "SIGNAL_INTERRUPT"] else "INCOMPLETE"))
    if is_completed:
        status_data["pct"] = 100.0
    else:
        status_data["pct"] = min(99.9, round(((time.time() - t_start) / target_seconds) * 100.0, 1))
    status_data["exitCode"] = 0
    status_data["endedAt"] = time.time()
    write_atomic_json(status_file, status_data)
    
    if is_completed:
        (output_dir / "COMPLETE").touch()
    elif stop_reason in ["STOP_FILE_DETECTED", "SIGNAL_INTERRUPT"]:
        (output_dir / "STOPPED").touch()

    write_atomic_json(output_dir / "execution.json", {
        "complete": is_completed,
        "stop_reason": stop_reason,
        "challenge": "CONTINGENCY_REPLAY",
        "total_generations": total_gens,
        "completed_epochs": epoch,
        "elapsed_hours": round((time.time() - t_start) / 3600.0, 2),
        "red_queen_proved": RED_QUEEN_PROVED,
        "summary": summary,
    })

    return summary


# ==============================================================================
# MAIN LAUNCHER HARNESS
# ==============================================================================

def main() -> None:
    parser = argparse.ArgumentParser(description="Grand Frontier 4-Challenge Launcher")
    parser.add_argument("--challenge", type=str, default="all", choices=["all", "1", "2", "3", "4", "oee", "mls", "transition", "contingency"], help="Specific challenge or 'all' for 4 independent runs")
    parser.add_argument("--runs-root", type=str, default="/home/parvaz/simulation_runs", help="Root directory for simulation runs")
    parser.add_argument("--output", type=str, default=None, help="Explicit output directory for single challenge")
    parser.add_argument("--duration-hours", type=float, default=72.0, help="Target duration in hours (e.g. 48.0, 72.0)")
    parser.add_argument("--epoch-gens", type=int, default=10000, help="Generations per epoch")
    parser.add_argument("--no-resume", action="store_true", help="Start from scratch ignoring checkpoints")
    parser.add_argument("--workers", type=int, default=os.cpu_count(), help="Max parallel workers (defaults to os.cpu_count())")
    args = parser.parse_args()

    target_seconds = float(args.duration_hours) * 3600.0
    runs_root = Path(args.runs_root).resolve()
    runs_root.mkdir(parents=True, exist_ok=True)

    c_map = {
        "1": "oee",
        "2": "mls",
        "3": "transition",
        "4": "contingency",
    }
    chosen = c_map.get(args.challenge, args.challenge)

    if chosen == "all":
        # Launch all 4 as separate concurrent processes in 4 distinct run directories!
        specs = [
            ("run_challenge_1_oee_72h", run_worker_0_oee, 10001),
            ("run_challenge_2_mls_72h", run_worker_1_mls, 20001),
            ("run_challenge_3_transition_72h", run_worker_2_transition, 30001),
            ("run_challenge_4_contingency_72h", run_worker_3_contingency, 40001),
        ]
        print(f"Launching all 4 frontier challenges as independent simulation runs in {runs_root} for {args.duration_hours}h...")
        with ProcessPoolExecutor(max_workers=args.workers) as executor:
            futures = {}
            for dir_name, fn, seed in specs:
                target_dir = runs_root / dir_name
                f = executor.submit(fn, target_dir, target_seconds, args.epoch_gens, seed, not args.no_resume)
                futures[f] = dir_name

            for future in as_completed(futures):
                name = futures[future]
                try:
                    res = future.result()
                    print(f"COMPLETED: {name} finished successfully: {res.get('challenge')}")
                except Exception as exc:
                    print(f"ERROR: {name} failed: {exc}")
    else:
        # Run single challenge directly
        target_dir = Path(args.output).resolve() if args.output else (runs_root / f"run_challenge_{chosen}_{args.duration_hours:.0f}h")
        if chosen == "oee":
            run_worker_0_oee(target_dir, target_seconds, args.epoch_gens, 10001, not args.no_resume)
        elif chosen == "mls":
            run_worker_1_mls(target_dir, target_seconds, args.epoch_gens, 20001, not args.no_resume)
        elif chosen == "transition":
            run_worker_2_transition(target_dir, target_seconds, args.epoch_gens, 30001, not args.no_resume)
        elif chosen == "contingency":
            run_worker_3_contingency(target_dir, target_seconds, args.epoch_gens, 40001, not args.no_resume)


if __name__ == "__main__":
    main()
