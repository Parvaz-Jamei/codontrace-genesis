#!/usr/bin/env python3
"""
grand_frontier_suite_extension.py - Challenges 5 to 8 for the 72-Hour Grand Frontier Campaign.

Extends the CodonTrace Genesis campaign with 4 additional deep, mathematically rigorous
scientific frontier challenges targeting open, unsolved problems in evolutionary biology,
artificial life, and complex adaptive systems:

- Challenge 5: [FUNCTIONAL_INFO] Functional Information Accretion & Neutral Network Percolation
  (Hazen et al. 2007, Adami & Cerf 2000, Wagner 2008)
- Challenge 6: [QUASISPECIES] Eigen's Error Catastrophe & Quasispecies Critical Threshold
  (Eigen 1971, Nowak 2006, Wilke 2005)
- Challenge 7: [OEE_SHADOW] Open-Ended Evolutionary Activity & Neutral Shadow Divergence
  (Bedau et al. 1998, Taylor et al. 2016, Channon 2024)
- Challenge 8: [FISHER_GEOMETRIC] Fisher's Geometric Model & Distribution of Fitness Effects (DFE)
  (Fisher 1930, Orr 2005, Tenaillon 2014)

Fully integrated with the CodonTrace Console (status.json, live.log, console.log, execution.json).
Epistemic invariants locked: red_queen_proved=False, open_ended_intelligence=False.

EXECUTION BOUNDARY & ARCHITECTURAL CLASSIFICATION:
Backend: FRONTIER_REFERENCE_MODEL (Independent Mathematical Benchmarks)
Engine Substrate: Standalone computational biology reference models (Challenges 5-8).
Boundary Separation: This extension executes isolated reference models for functional
information (Hazen et al.), quasispecies error threshold (Eigen), neutral shadow activity
(Bedau et al.), and Fisher's geometric model. It does NOT execute the codon-translating
GenesisEngine virtual machine. For full digital organism codon execution, use GenesisEngine.
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
from collections import Counter
from pathlib import Path
from typing import Any

# Epistemic Invariants
RED_QUEEN_PROVED = False
OPEN_ENDED_INTELLIGENCE_PROVED = False
MAJOR_TRANSITION_PROVED = False

# Global shutdown flag
_SHUTDOWN = False


def _signal_handler(signum: int, frame: Any) -> None:
    global _SHUTDOWN
    _SHUTDOWN = True


signal.signal(signal.SIGINT, _signal_handler)
signal.signal(signal.SIGTERM, _signal_handler)


def prng_float(seed: int, step: int, salt: str) -> float:
    """Deterministic cryptographic PRNG float in [0.0, 1.0)."""
    h = hashlib.sha256(f"{seed}:{step}:{salt}".encode("utf-8")).digest()
    return int.from_bytes(h[:4], "big") / 4294967296.0


def prng_int(seed: int, step: int, salt: str, low: int, high: int) -> int:
    """Deterministic integer in [low, high]."""
    f = prng_float(seed, step, salt)
    return low + int(f * (high - low + 1))


def set_core_affinity(core_id: int) -> None:
    """Pin process to specific CPU core on Linux if supported."""
    if hasattr(os, "sched_setaffinity"):
        try:
            os.sched_setaffinity(0, {core_id % (os.cpu_count() or 4)})
        except (OSError, ValueError):
            pass


def write_atomic_json(path: Path, data: dict[str, Any]) -> None:
    """Atomically write JSON to avoid partial reads by web console."""
    tmp_path = path.with_suffix(f".tmp.{os.getpid()}")
    try:
        tmp_path.write_text(json.dumps(data, indent=2, allow_nan=False), encoding="utf-8")
        tmp_path.replace(path)
    except Exception:
        if tmp_path.exists():
            tmp_path.unlink(missing_ok=True)


class DualLogger:
    def __init__(self, log_files: list[Path]):
        self.log_files = log_files

    def log(self, msg: str) -> None:
        ts = time.strftime("%Y-%m-%d %H:%M:%S")
        line = f"[{ts}] {msg}"
        for lf in self.log_files:
            try:
                with lf.open("a", encoding="utf-8") as f:
                    f.write(line + "\n")
            except Exception:
                pass
        print(line, flush=True)


# ==============================================================================
# CHALLENGE 5: Functional Information & Neutral Network Percolation
# ==============================================================================
def run_worker_5_functional_info(output_dir: Path, duration_hours: float, core_id: int = 0) -> None:
    """Challenge 5: Measures Functional Information accretion and Wagner neutral percolation."""
    set_core_affinity(core_id)
    output_dir.mkdir(parents=True, exist_ok=True)

    status_file = output_dir / "status.json"
    live_log = output_dir / "live.log"
    ui_log = output_dir / "console.log"
    exec_file = output_dir / "execution.json"

    logger = DualLogger([live_log, ui_log])
    logger.log("Challenge 5: Functional Information & Neutral Networks started")

    start_time = time.time()
    stop_reason = "INCOMPLETE"
    target_seconds = duration_hours * 3600.0
    seed = 50001
    epoch = 0

    genome_len = 64
    pop_size = 120
    alphabet = ("0", "1")

    # Initial status
    write_atomic_json(status_file, {
        "id": output_dir.name,
        "title": f"Challenge 5: Functional Info & Neutral Net (0.0h/{duration_hours:.0f}h | Ep 0)",
        "status": "RUNNING",
        "pid": os.getpid(),
        "pct": 0.0,
        "completed_seeds": 0,
        "total_seeds": 1,
        "elapsed_hours": 0.0,
        "target_hours": duration_hours,
        "started_at": start_time,
        "updated_at": start_time,
        "eta_hours": round(duration_hours, 2),
        "metrics": {
            "epoch": 0,
            "functional_info_bits": 0.0,
            "neutral_percolation": 0.0,
            "entropy": float(genome_len),
        },
        "red_queen_proved": False,
    })

    # Initial random population
    population = [
        "".join(alphabet[prng_int(seed, i * genome_len + j, "c5_init", 0, 1)] for j in range(genome_len))
        for i in range(pop_size)
    ]

    sequence_information_bits = 0.0
    hazen_functional_info_bits = 0.0
    neutral_percolation = 0.0
    viable_percolation = 0.0
    total_entropy = float(genome_len)

    try:
        while not _SHUTDOWN:
            elapsed = time.time() - start_time
            if elapsed >= target_seconds and epoch > 0:
                stop_reason = "WALL_TIME_EXHAUSTED"
                break
            if (output_dir / "STOP").is_file():
                stop_reason = "STOP_FILE_DETECTED"
                break

            epoch += 1

            # Multi-locus Shannon Entropy & Sequence Information (Adami & Cerf 2000)
            total_entropy = 0.0
            for pos in range(genome_len):
                col = [seq[pos] for seq in population]
                cnts = Counter(col)
                for c in cnts.values():
                    p = c / pop_size
                    total_entropy -= p * math.log2(p)

            max_entropy = float(genome_len)  # binary alphabet log2(2) = 1
            sequence_information_bits = max(0.0, max_entropy - total_entropy)

            # Evaluate fitness of current population to define functional threshold
            scores = [seq.count("110") * 2 - seq.count("000") for seq in population]
            theta = min(scores)

            # Hazen Functional Information: I(Ex) = -log2(M(Ex)/N) via reference space sampling
            sample_size = 500
            viable_count = 0
            for _s in range(sample_size):
                rand_seq = "".join(alphabet[prng_int(seed, ((epoch * sample_size + _s) * genome_len) + pos, "c5_ref", 0, 1)] for pos in range(genome_len))
                rand_score = rand_seq.count("110") * 2 - rand_seq.count("000")
                if rand_score >= theta:
                    viable_count += 1
            
            p_f = viable_count / sample_size
            hazen_functional_info_bits = -math.log2(p_f) if p_f > 0 else float(genome_len)

            # Wagner Neutral Network Percolation: 1-mutant sampling on top quartile
            sample_elites = population[:pop_size // 4]
            strict_neutral = 0
            viable_neighbors = 0
            total_neighbors = 0

            for seq in sample_elites:
                base_score = seq.count("110") * 2 - seq.count("000")
                for _ in range(8):
                    mut_pos = prng_int(seed, epoch * 100 + total_neighbors, "c5_mut", 0, genome_len - 1)
                    mutated = list(seq)
                    mutated[mut_pos] = "0" if mutated[mut_pos] == "1" else "1"
                    mut_score = "".join(mutated).count("110") * 2 - "".join(mutated).count("000")
                    if mut_score == base_score:
                        strict_neutral += 1
                    if mut_score >= base_score:
                        viable_neighbors += 1
                    total_neighbors += 1

            neutral_percolation = strict_neutral / max(1, total_neighbors)
            viable_percolation = viable_neighbors / max(1, total_neighbors)

            # Selection & Replacement
            min_score = min(scores)
            fitnesses = [max(0.1, s - min_score + 1.0) for s in scores]

            new_pop = []
            for i in range(pop_size):
                p1_idx = prng_int(seed, epoch * pop_size * 2 + i * 2, "c5_p1", 0, pop_size - 1)
                p2_idx = prng_int(seed, epoch * pop_size * 2 + i * 2 + 1, "c5_p2", 0, pop_size - 1)
                winner = population[p1_idx] if fitnesses[p1_idx] >= fitnesses[p2_idx] else population[p2_idx]

                mutated = list(winner)
                for pos in range(genome_len):
                    if prng_float(seed, epoch * pop_size * genome_len + i * genome_len + pos, "c5_point") < (1.0 / genome_len):
                        mutated[pos] = "0" if mutated[pos] == "1" else "1"
                new_pop.append("".join(mutated))

            population = new_pop

            # Telemetry updates every 10 epochs
            if epoch % 10 == 0 or elapsed >= target_seconds:
                pct = min(100.0, (elapsed / target_seconds) * 100.0)
                eta_h = max(0.0, (target_seconds - elapsed) / 3600.0)

                st_data = {
                    "id": output_dir.name,
                    "title": f"Challenge 5: Functional Info & Neutral Net ({elapsed/3600.0:.1f}h/72h | Ep {epoch})",
                    "status": "RUNNING",
                    "pid": os.getpid(),
                    "pct": round(pct, 1),
                    "completed_seeds": 0,
                    "total_seeds": 1,
                    "elapsed_hours": round(elapsed / 3600.0, 2),
                    "target_hours": duration_hours,
                    "started_at": start_time,
                    "updated_at": time.time(),
                    "eta_hours": round(eta_h, 2),
                    "metrics": {
                        "epoch": epoch,
                        "sequence_information_bits": round(sequence_information_bits, 3),
                        "hazen_functional_info_bits": round(hazen_functional_info_bits, 3),
                        "functional_info_bits": round(hazen_functional_info_bits, 3),
                        "neutral_percolation": round(neutral_percolation, 3),
                        "viable_percolation": round(viable_percolation, 3),
                        "entropy": round(total_entropy, 3),
                    },
                    "red_queen_proved": False,
                }
                write_atomic_json(status_file, st_data)
                logger.log(f"[Epoch {epoch:6d}] Elapsed: {elapsed/3600.0:5.2f}h | FI: {hazen_functional_info_bits:5.2f} bits | Strict Neutral: {neutral_percolation*100:5.1f}%")

            time.sleep(0.05)

        if _SHUTDOWN and stop_reason == "INCOMPLETE":
            stop_reason = "SIGNAL_INTERRUPT"
    except KeyboardInterrupt:
        logger.log("SIGNAL_INTERRUPT detected.")
        stop_reason = "SIGNAL_INTERRUPT"
    except Exception as exc:
        logger.log(f"Exception: {exc}")
        stop_reason = "EXCEPTION"
    final_elapsed = time.time() - start_time
    is_completed = (stop_reason == "WALL_TIME_EXHAUSTED")
    final_status = "COMPLETED" if is_completed else ("FAILED" if stop_reason == "EXCEPTION" else ("STOPPED" if stop_reason in ["STOP_FILE_DETECTED", "SIGNAL_INTERRUPT"] else "INCOMPLETE"))
    final_pct = 100.0 if is_completed else min(99.9, round((final_elapsed / target_seconds) * 100.0, 1))
    logger.log(f"Challenge 5 Complete ({final_status}).")

    write_atomic_json(status_file, {
        "id": output_dir.name,
        "title": f"Challenge 5: Functional Info & Neutral Net ({final_status} | Ep {epoch})",
        "status": final_status,
        "pid": os.getpid(),
        "pct": final_pct,
        "completed_seeds": 1 if is_completed else 0,
        "total_seeds": 1,
        "elapsed_hours": round(final_elapsed / 3600.0, 2),
        "target_hours": duration_hours,
        "started_at": start_time,
        "updated_at": time.time(),
        "eta_hours": 0.0,
        "metrics": {
            "epoch": epoch,
            "sequence_information_bits": round(sequence_information_bits, 3),
            "hazen_functional_info_bits": round(hazen_functional_info_bits, 3),
            "functional_info_bits": round(hazen_functional_info_bits, 3),
            "neutral_percolation": round(neutral_percolation, 3),
            "viable_percolation": round(viable_percolation, 3),
            "entropy": round(total_entropy, 3),
        },
        "red_queen_proved": False,
    })

    if stop_reason == "WALL_TIME_EXHAUSTED":
        (output_dir / "COMPLETE").touch()
    elif stop_reason in ["STOP_FILE_DETECTED", "SIGNAL_INTERRUPT"]:
        (output_dir / "STOPPED").touch()

    write_atomic_json(exec_file, {
        "complete": (stop_reason == "WALL_TIME_EXHAUSTED"),
        "stop_reason": stop_reason,
        "challenge": 5,
        "engine_backend": "frontier_reference_model",
        "model_scope": "frontier_reference_exploration",
        "model_boundary_notice": "Isolated mathematical reference exploration model; distinct from full GenesisEngine codon VM.",
        "epochs": epoch,
        "elapsed_seconds": final_elapsed,
        "red_queen_proved": False,
    })


# ==============================================================================
# CHALLENGE 6: Eigen's Error Catastrophe & Quasispecies Critical Threshold
# ==============================================================================
def run_worker_6_quasispecies(output_dir: Path, duration_hours: float, core_id: int = 1) -> None:
    """Challenge 6: Locates the critical error threshold mu_c in finite quasispecies populations."""
    set_core_affinity(core_id)
    output_dir.mkdir(parents=True, exist_ok=True)

    status_file = output_dir / "status.json"
    live_log = output_dir / "live.log"
    ui_log = output_dir / "console.log"
    exec_file = output_dir / "execution.json"

    logger = DualLogger([live_log, ui_log])
    logger.log("Challenge 6: Quasispecies & Error Threshold started")

    start_time = time.time()
    stop_reason = "INCOMPLETE"
    target_seconds = duration_hours * 3600.0
    seed = 60001
    epoch = 0

    genome_len = 50
    pop_size = 150
    master_seq = "1" * genome_len
    superiority_sigma = 3.0  # Master sequence selective advantage

    # Population starts cloned from master
    population = [master_seq for _ in range(pop_size)]

    # Theoretical Eigen threshold: mu_c = ln(sigma) / L = ln(3.0) / 50 ~= 0.02197
    eigen_mu_c = math.log(superiority_sigma) / float(genome_len)

    # Initial status
    write_atomic_json(status_file, {
        "id": output_dir.name,
        "title": f"Challenge 6: Quasispecies & Error Catastrophe (0.0h/{duration_hours:.0f}h | Ep 0)",
        "status": "RUNNING",
        "pid": os.getpid(),
        "pct": 0.0,
        "completed_seeds": 0,
        "total_seeds": 1,
        "elapsed_hours": 0.0,
        "target_hours": duration_hours,
        "started_at": start_time,
        "updated_at": start_time,
        "eta_hours": round(duration_hours, 2),
        "metrics": {
            "epoch": 0,
            "mutation_rate": 0.005,
            "theoretical_mu_c": round(eigen_mu_c, 4),
            "master_sequence_retention": 1.0,
            "mean_hamming_distance": 0.0,
            "quasispecies_variance": 0.0,
            "regime": "ORGANIZED_QUASISPECIES",
        },
        "red_queen_proved": False,
    })

    mu = 0.005
    master_fraction = 1.0
    mean_hamming = 0.0
    quasispecies_var = 0.0

    try:
        while not _SHUTDOWN:
            elapsed = time.time() - start_time
            if elapsed >= target_seconds and epoch > 0:
                stop_reason = "WALL_TIME_EXHAUSTED"
                break
            if (output_dir / "STOP").is_file():
                stop_reason = "STOP_FILE_DETECTED"
                break

            epoch += 1

            # Discrete test step points relative to mu_c
            test_points = [0.5, 0.8, 1.0, 1.2, 1.5]
            point_idx = (epoch // 100) % len(test_points)
            mu = test_points[point_idx] * eigen_mu_c

            # Evaluate fitness
            fitnesses = []
            master_count = 0
            hamming_distances = []

            for seq in population:
                d = sum(1 for a, b in zip(seq, master_seq) if a != b)
                hamming_distances.append(d)
                if d == 0:
                    master_count += 1
                    fitnesses.append(superiority_sigma)
                else:
                    fitnesses.append(1.0)

            master_fraction = master_count / pop_size
            mean_hamming = sum(hamming_distances) / pop_size

            # Quasispecies Variance (distance variance from master)
            quasispecies_var = sum((d - mean_hamming) ** 2 for d in hamming_distances) / pop_size

            # Wright-Fisher fitness-proportional selection
            total_fitness = sum(fitnesses)
            
            new_pop = []
            for i in range(pop_size):
                roll = prng_float(seed, epoch * pop_size + i, "c6_sel") * total_fitness
                cum = 0.0
                chosen = population[0]
                for idx, fit in enumerate(fitnesses):
                    cum += fit
                    if cum >= roll:
                        chosen = population[idx]
                        break

                mutated = list(chosen)
                for pos in range(genome_len):
                    if prng_float(seed, epoch * pop_size * genome_len + i * genome_len + pos, "c6_mu") < mu:
                        mutated[pos] = "0" if mutated[pos] == "1" else "1"
                new_pop.append("".join(mutated))

            population = new_pop

            if epoch % 10 == 0 or elapsed >= target_seconds:
                pct = min(100.0, (elapsed / target_seconds) * 100.0)
                eta_h = max(0.0, (target_seconds - elapsed) / 3600.0)
                above_threshold = mu > eigen_mu_c

                st_data = {
                    "id": output_dir.name,
                    "title": f"Challenge 6: Quasispecies & Error Catastrophe ({elapsed/3600.0:.1f}h/72h | Ep {epoch})",
                    "status": "RUNNING",
                    "pid": os.getpid(),
                    "pct": round(pct, 1),
                    "completed_seeds": 0,
                    "total_seeds": 1,
                    "elapsed_hours": round(elapsed / 3600.0, 2),
                    "target_hours": duration_hours,
                    "started_at": start_time,
                    "updated_at": time.time(),
                    "eta_hours": round(eta_h, 2),
                    "metrics": {
                        "epoch": epoch,
                        "mutation_rate": round(mu, 4),
                        "theoretical_mu_c": round(eigen_mu_c, 4),
                        "master_sequence_retention": round(master_fraction, 3),
                        "mean_hamming_distance": round(mean_hamming, 2),
                        "quasispecies_variance": round(quasispecies_var, 3),
                        "regime": "CATASTROPHE_DRIFT" if above_threshold else "ORGANIZED_QUASISPECIES",
                    },
                    "red_queen_proved": False,
                }
                write_atomic_json(status_file, st_data)
                logger.log(f"[Epoch {epoch:6d}] mu: {mu:.4f} (mu_c: {eigen_mu_c:.4f}) | Master Ret: {master_fraction*100:5.1f}% | HamDist: {mean_hamming:4.1f} | Regime: {'DRIFT' if above_threshold else 'STABLE'}")

            time.sleep(0.05)

        if _SHUTDOWN and stop_reason == "INCOMPLETE":
            stop_reason = "SIGNAL_INTERRUPT"
    except KeyboardInterrupt:
        logger.log("SIGNAL_INTERRUPT detected.")
        stop_reason = "SIGNAL_INTERRUPT"
    except Exception as exc:
        logger.log(f"Exception: {exc}")
        stop_reason = "EXCEPTION"
    final_elapsed = time.time() - start_time
    is_completed = (stop_reason == "WALL_TIME_EXHAUSTED")
    final_status = "COMPLETED" if is_completed else ("FAILED" if stop_reason == "EXCEPTION" else ("STOPPED" if stop_reason in ["STOP_FILE_DETECTED", "SIGNAL_INTERRUPT"] else "INCOMPLETE"))
    final_pct = 100.0 if is_completed else min(99.9, round((final_elapsed / target_seconds) * 100.0, 1))
    logger.log(f"Challenge 6 Complete ({final_status}).")

    write_atomic_json(status_file, {
        "id": output_dir.name,
        "title": f"Challenge 6: Quasispecies & Error Catastrophe ({final_status} | Ep {epoch})",
        "status": final_status,
        "pid": os.getpid(),
        "pct": final_pct,
        "completed_seeds": 1 if is_completed else 0,
        "total_seeds": 1,
        "elapsed_hours": round(final_elapsed / 3600.0, 2),
        "target_hours": duration_hours,
        "started_at": start_time,
        "updated_at": time.time(),
        "eta_hours": 0.0,
        "metrics": {
            "epoch": epoch,
            "mutation_rate": round(mu, 4),
            "theoretical_mu_c": round(eigen_mu_c, 4),
            "master_sequence_retention": round(master_fraction, 3),
            "mean_hamming_distance": round(mean_hamming, 2),
            "quasispecies_variance": round(quasispecies_var, 3),
            "regime": "CATASTROPHE_DRIFT" if mu > eigen_mu_c else "ORGANIZED_QUASISPECIES",
        },
        "red_queen_proved": False,
    })

    if stop_reason == "WALL_TIME_EXHAUSTED":
        (output_dir / "COMPLETE").touch()
    elif stop_reason in ["STOP_FILE_DETECTED", "SIGNAL_INTERRUPT"]:
        (output_dir / "STOPPED").touch()

    write_atomic_json(exec_file, {
        "complete": (stop_reason == "WALL_TIME_EXHAUSTED"),
        "stop_reason": stop_reason,
        "challenge": 6,
        "engine_backend": "frontier_reference_model",
        "model_scope": "frontier_reference_exploration",
        "model_boundary_notice": "Isolated mathematical reference exploration model; distinct from full GenesisEngine codon VM.",
        "epochs": epoch,
        "elapsed_seconds": final_elapsed,
        "red_queen_proved": False,
    })


# ==============================================================================
# CHALLENGE 7: Open-Ended Evolution & Cumulative Evolutionary Activity
# ==============================================================================
def run_worker_7_oee_shadow(output_dir: Path, duration_hours: float, core_id: int = 2) -> None:
    """Challenge 7: Measures Cumulative Evolutionary Activity A(t) vs a Neutral Shadow Run."""
    set_core_affinity(core_id)
    output_dir.mkdir(parents=True, exist_ok=True)

    status_file = output_dir / "status.json"
    live_log = output_dir / "live.log"
    ui_log = output_dir / "console.log"
    exec_file = output_dir / "execution.json"

    logger = DualLogger([live_log, ui_log])
    logger.log("Challenge 7: Open-Ended Evolution Activity started")

    start_time = time.time()
    stop_reason = "INCOMPLETE"
    target_seconds = duration_hours * 3600.0
    seed = 70001
    epoch = 0

    genome_len = 40
    pop_size = 100

    # Two parallel populations: Real (Evolving with selection) vs Shadow (Drift only)
    pop_real = ["0" * genome_len for _ in range(pop_size)]
    pop_shadow = ["0" * genome_len for _ in range(pop_size)]

    activity_real: dict[str, float] = {}
    activity_shadow: dict[str, float] = {}

    cum_activity_real = 0.0
    cum_activity_shadow = 0.0

    # Initial status
    write_atomic_json(status_file, {
        "id": output_dir.name,
        "title": f"Challenge 7: Open-Ended Evolutionary Activity (0.0h/{duration_hours:.0f}h | Ep 0)",
        "status": "RUNNING",
        "pid": os.getpid(),
        "pct": 0.0,
        "completed_seeds": 0,
        "total_seeds": 1,
        "elapsed_hours": 0.0,
        "target_hours": duration_hours,
        "started_at": start_time,
        "updated_at": start_time,
        "eta_hours": round(duration_hours, 2),
        "metrics": {
            "epoch": 0,
            "cumulative_activity_real": 0.0,
            "cumulative_activity_shadow": 0.0,
            "excess_adaptive_activity": 0.0,
            "distinct_genotypes_real": 1,
            "distinct_genotypes_shadow": 1,
        },
        "red_queen_proved": False,
    })

    excess_activity = 0.0
    freq_real: Counter[str] = Counter(pop_real)
    freq_shadow: Counter[str] = Counter(pop_shadow)

    try:
        while not _SHUTDOWN:
            elapsed = time.time() - start_time
            if elapsed >= target_seconds and epoch > 0:
                stop_reason = "WALL_TIME_EXHAUSTED"
                break
            if (output_dir / "STOP").is_file():
                stop_reason = "STOP_FILE_DETECTED"
                break

            epoch += 1

            # Real population: Selection based on computational motif diversity
            scores_real = [seq.count("101") * 3 + seq.count("010") * 2 for seq in pop_real]
            fit_real = [max(0.1, s + 1.0) for s in scores_real]

            # Shadow population: Neutral random fitness (drift only, Bedau 1998)
            freq_real = Counter(pop_real)
            freq_shadow = Counter(pop_shadow)

            # Update activity increments: a_i(t) += 1 if present above frequency threshold
            for seq, count in freq_real.items():
                if count >= 3:
                    activity_real[seq] = activity_real.get(seq, 0.0) + (count / pop_size)

            for seq, count in freq_shadow.items():
                if count >= 3:
                    activity_shadow[seq] = activity_shadow.get(seq, 0.0) + (count / pop_size)

            cum_activity_real = sum(activity_real.get(seq, 0.0) for seq in pop_real)
            cum_activity_shadow = sum(activity_shadow.get(seq, 0.0) for seq in pop_shadow)

            # Reproduction for Real
            new_real = []
            for i in range(pop_size):
                p1 = prng_int(seed, epoch * pop_size * 2 + i * 2, "c7_r1", 0, pop_size - 1)
                p2 = prng_int(seed, epoch * pop_size * 2 + i * 2 + 1, "c7_r2", 0, pop_size - 1)
                winner = pop_real[p1] if fit_real[p1] >= fit_real[p2] else pop_real[p2]
                mut = list(winner)
                for pos in range(genome_len):
                    if prng_float(seed, epoch * pop_size * genome_len + i * genome_len + pos, "c7_mr") < 0.025:
                        mut[pos] = "0" if mut[pos] == "1" else "1"
                new_real.append("".join(mut))
            pop_real = new_real

            # Reproduction for Shadow (pure neutral drift)
            new_shadow = []
            for i in range(pop_size):
                parent_idx = prng_int(seed, epoch * pop_size + i, "c7_sh", 0, pop_size - 1)
                parent = pop_shadow[parent_idx]
                mut = list(parent)
                for pos in range(genome_len):
                    if prng_float(seed, epoch * pop_size * genome_len + i * genome_len + pos, "c7_ms") < 0.025:
                        mut[pos] = "0" if mut[pos] == "1" else "1"
                new_shadow.append("".join(mut))
            pop_shadow = new_shadow

            if epoch % 10 == 0 or elapsed >= target_seconds:
                pct = min(100.0, (elapsed / target_seconds) * 100.0)
                eta_h = max(0.0, (target_seconds - elapsed) / 3600.0)
                excess_activity = max(0.0, cum_activity_real - cum_activity_shadow)

                st_data = {
                    "id": output_dir.name,
                    "title": f"Challenge 7: Open-Ended Evolutionary Activity ({elapsed/3600.0:.1f}h/72h | Ep {epoch})",
                    "status": "RUNNING",
                    "pid": os.getpid(),
                    "pct": round(pct, 1),
                    "completed_seeds": 0,
                    "total_seeds": 1,
                    "elapsed_hours": round(elapsed / 3600.0, 2),
                    "target_hours": duration_hours,
                    "started_at": start_time,
                    "updated_at": time.time(),
                    "eta_hours": round(eta_h, 2),
                    "metrics": {
                        "epoch": epoch,
                        "cumulative_activity_real": round(cum_activity_real, 1),
                        "cumulative_activity_shadow": round(cum_activity_shadow, 1),
                        "excess_adaptive_activity": round(excess_activity, 1),
                        "distinct_genotypes_real": len(freq_real),
                        "distinct_genotypes_shadow": len(freq_shadow),
                    },
                    "red_queen_proved": False,
                }
                write_atomic_json(status_file, st_data)
                logger.log(f"[Epoch {epoch:6d}] Real Activity: {cum_activity_real:8.1f} | Shadow: {cum_activity_shadow:8.1f} | Excess: {excess_activity:8.1f}")

            time.sleep(0.05)

        if _SHUTDOWN and stop_reason == "INCOMPLETE":
            stop_reason = "SIGNAL_INTERRUPT"
    except KeyboardInterrupt:
        logger.log("SIGNAL_INTERRUPT detected.")
        stop_reason = "SIGNAL_INTERRUPT"
    except Exception as exc:
        logger.log(f"Exception: {exc}")
        stop_reason = "EXCEPTION"
    final_elapsed = time.time() - start_time
    is_completed = (stop_reason == "WALL_TIME_EXHAUSTED")
    final_status = "COMPLETED" if is_completed else ("FAILED" if stop_reason == "EXCEPTION" else ("STOPPED" if stop_reason in ["STOP_FILE_DETECTED", "SIGNAL_INTERRUPT"] else "INCOMPLETE"))
    final_pct = 100.0 if is_completed else min(99.9, round((final_elapsed / target_seconds) * 100.0, 1))
    logger.log(f"Challenge 7 Complete ({final_status}).")

    write_atomic_json(status_file, {
        "id": output_dir.name,
        "title": f"Challenge 7: Open-Ended Evolutionary Activity ({final_status} | Ep {epoch})",
        "status": final_status,
        "pid": os.getpid(),
        "pct": final_pct,
        "completed_seeds": 1 if is_completed else 0,
        "total_seeds": 1,
        "elapsed_hours": round(final_elapsed / 3600.0, 2),
        "target_hours": duration_hours,
        "started_at": start_time,
        "updated_at": time.time(),
        "eta_hours": 0.0,
        "metrics": {
            "epoch": epoch,
            "cumulative_activity_real": round(cum_activity_real, 1),
            "cumulative_activity_shadow": round(cum_activity_shadow, 1),
            "excess_adaptive_activity": round(excess_activity, 1),
            "distinct_genotypes_real": len(freq_real),
            "distinct_genotypes_shadow": len(freq_shadow),
        },
        "red_queen_proved": False,
    })

    if stop_reason == "WALL_TIME_EXHAUSTED":
        (output_dir / "COMPLETE").touch()
    elif stop_reason in ["STOP_FILE_DETECTED", "SIGNAL_INTERRUPT"]:
        (output_dir / "STOPPED").touch()

    write_atomic_json(exec_file, {
        "complete": (stop_reason == "WALL_TIME_EXHAUSTED"),
        "stop_reason": stop_reason,
        "challenge": 7,
        "engine_backend": "frontier_reference_model",
        "model_scope": "frontier_reference_exploration",
        "model_boundary_notice": "Isolated mathematical reference exploration model; distinct from full GenesisEngine codon VM.",
        "epochs": epoch,
        "elapsed_seconds": final_elapsed,
        "red_queen_proved": False,
    })


# ==============================================================================
# CHALLENGE 8: Fisher's Geometric Model & Distribution of Fitness Effects (DFE)
# ==============================================================================
def run_worker_8_fisher_geometric(output_dir: Path, duration_hours: float, core_id: int = 3) -> None:
    """Challenge 8: Tests Fisher's Geometric Model of adaptation in high dimensions."""
    set_core_affinity(core_id)
    output_dir.mkdir(parents=True, exist_ok=True)

    status_file = output_dir / "status.json"
    live_log = output_dir / "live.log"
    ui_log = output_dir / "console.log"
    exec_file = output_dir / "execution.json"

    logger = DualLogger([live_log, ui_log])
    logger.log("Challenge 8: Fisher Geometric Model started")

    start_time = time.time()
    stop_reason = "INCOMPLETE"
    target_seconds = duration_hours * 3600.0
    seed = 80001
    epoch = 0

    dimensions = 16  # 16-dimensional continuous phenotypic space
    pop_size = 120
    selection_strength = 2.0  # Gaussian fitness width

    # Optimum starts at origin
    optimum = [0.0] * dimensions

    # Initial population displaced by Euclidean distance d=2.0
    initial_displacement = 2.0
    init_trait = [initial_displacement / math.sqrt(dimensions)] * dimensions
    population = [list(init_trait) for _ in range(pop_size)]

    beneficial_count = 0
    deleterious_count = 0

    # Initial status
    write_atomic_json(status_file, {
        "id": output_dir.name,
        "title": f"Challenge 8: Fisher Geometric Model (0.0h/{duration_hours:.0f}h | Ep 0)",
        "status": "RUNNING",
        "pid": os.getpid(),
        "pct": 0.0,
        "completed_seeds": 0,
        "total_seeds": 1,
        "elapsed_hours": 0.0,
        "target_hours": duration_hours,
        "started_at": start_time,
        "updated_at": start_time,
        "eta_hours": round(duration_hours, 2),
        "metrics": {
            "epoch": 0,
            "dimensions": dimensions,
            "mean_phenotypic_distance": initial_displacement,
            "mean_fitness": round(math.exp(-(initial_displacement**2) / (2.0 * selection_strength)), 4),
            "p_beneficial_mutations": 0.0,
            "total_mutations_observed": 0,
        },
        "red_queen_proved": False,
    })

    mean_distance = initial_displacement
    mean_fitness = math.exp(-(initial_displacement**2) / (2.0 * selection_strength))
    p_beneficial = 0.0
    total_muts = 0

    try:
        while not _SHUTDOWN:
            elapsed = time.time() - start_time
            if elapsed >= target_seconds and epoch > 0:
                stop_reason = "WALL_TIME_EXHAUSTED"
                break
            if (output_dir / "STOP").is_file():
                stop_reason = "STOP_FILE_DETECTED"
                break

            epoch += 1

            # Environmental shift every 500 epochs (moving optimum, Orr 2005)
            if epoch % 500 == 0:
                shift_dim = prng_int(seed, epoch, "c8_shift_dim", 0, dimensions - 1)
                optimum[shift_dim] += 0.5

            # Compute fitness: W(z) = exp(-||z - z*||^2 / (2 * Vs))
            fitnesses = []
            distances = []
            for ind in population:
                dist_sq = sum((z - z_star) ** 2 for z, z_star in zip(ind, optimum))
                dist = math.sqrt(dist_sq)
                fit = math.exp(-dist_sq / (2.0 * selection_strength))
                fitnesses.append(fit)
                distances.append(dist)

            mean_distance = sum(distances) / pop_size
            mean_fitness = sum(fitnesses) / pop_size

            # Reproduction with multidimensional mutations
            new_pop = []
            for i in range(pop_size):
                p1 = prng_int(seed, epoch * pop_size * 2 + i * 2, "c8_p1", 0, pop_size - 1)
                p2 = prng_int(seed, epoch * pop_size * 2 + i * 2 + 1, "c8_p2", 0, pop_size - 1)
                parent = population[p1] if fitnesses[p1] >= fitnesses[p2] else population[p2]
                parent_dist_sq = sum((z - z_star) ** 2 for z, z_star in zip(parent, optimum))

                child = list(parent)
                for d in range(dimensions):
                    u1 = max(1e-7, prng_float(seed, epoch * pop_size * dimensions + i * dimensions + d, "c8_u1"))
                    u2 = prng_float(seed, epoch * pop_size * dimensions + i * dimensions + d, "c8_u2")
                    mutation_delta = math.sqrt(-2.0 * math.log(u1)) * math.cos(2.0 * math.pi * u2) * 0.15
                    child[d] += mutation_delta

                child_dist_sq = sum((z - z_star) ** 2 for z, z_star in zip(child, optimum))
                if child_dist_sq < parent_dist_sq:
                    beneficial_count += 1
                else:
                    deleterious_count += 1

                new_pop.append(child)

            population = new_pop

            if epoch % 10 == 0 or elapsed >= target_seconds:
                pct = min(100.0, (elapsed / target_seconds) * 100.0)
                eta_h = max(0.0, (target_seconds - elapsed) / 3600.0)
                total_muts = max(1, beneficial_count + deleterious_count)
                p_beneficial = beneficial_count / total_muts

                st_data = {
                    "id": output_dir.name,
                    "title": f"Challenge 8: Fisher Geometric Model ({elapsed/3600.0:.1f}h/72h | Ep {epoch})",
                    "status": "RUNNING",
                    "pid": os.getpid(),
                    "pct": round(pct, 1),
                    "completed_seeds": 0,
                    "total_seeds": 1,
                    "elapsed_hours": round(elapsed / 3600.0, 2),
                    "target_hours": duration_hours,
                    "started_at": start_time,
                    "updated_at": time.time(),
                    "eta_hours": round(eta_h, 2),
                    "metrics": {
                        "epoch": epoch,
                        "dimensions": dimensions,
                        "mean_phenotypic_distance": round(mean_distance, 3),
                        "mean_fitness": round(mean_fitness, 4),
                        "p_beneficial_mutations": round(p_beneficial, 4),
                        "beneficial_ratio": round(p_beneficial, 4),
                        "total_mutations_observed": total_muts,
                    },
                    "red_queen_proved": False,
                }
                write_atomic_json(status_file, st_data)
                logger.log(f"[Epoch {epoch:6d}] Mean Dist to Optimum: {mean_distance:5.3f} | Mean Fit: {mean_fitness:6.4f} | P(Beneficial): {p_beneficial*100:4.1f}%")

            time.sleep(0.05)

        if _SHUTDOWN and stop_reason == "INCOMPLETE":
            stop_reason = "SIGNAL_INTERRUPT"
    except KeyboardInterrupt:
        logger.log("SIGNAL_INTERRUPT detected.")
        stop_reason = "SIGNAL_INTERRUPT"
    except Exception as exc:
        logger.log(f"Exception: {exc}")
        stop_reason = "EXCEPTION"
    final_elapsed = time.time() - start_time
    is_completed = (stop_reason == "WALL_TIME_EXHAUSTED")
    final_status = "COMPLETED" if is_completed else ("FAILED" if stop_reason == "EXCEPTION" else ("STOPPED" if stop_reason in ["STOP_FILE_DETECTED", "SIGNAL_INTERRUPT"] else "INCOMPLETE"))
    final_pct = 100.0 if is_completed else min(99.9, round((final_elapsed / target_seconds) * 100.0, 1))
    logger.log(f"Challenge 8 Complete ({final_status}).")

    write_atomic_json(status_file, {
        "id": output_dir.name,
        "title": f"Challenge 8: Fisher Geometric Model ({final_status} | Ep {epoch})",
        "status": final_status,
        "pid": os.getpid(),
        "pct": final_pct,
        "completed_seeds": 1 if is_completed else 0,
        "total_seeds": 1,
        "elapsed_hours": round(final_elapsed / 3600.0, 2),
        "target_hours": duration_hours,
        "started_at": start_time,
        "updated_at": time.time(),
        "eta_hours": 0.0,
        "metrics": {
            "epoch": epoch,
            "dimensions": dimensions,
            "mean_phenotypic_distance": round(mean_distance, 3),
            "mean_fitness": round(mean_fitness, 4),
            "p_beneficial_mutations": round(p_beneficial, 4),
            "beneficial_ratio": round(p_beneficial, 4),
            "total_mutations_observed": total_muts,
        },
        "red_queen_proved": False,
    })

    if stop_reason == "WALL_TIME_EXHAUSTED":
        (output_dir / "COMPLETE").touch()
    elif stop_reason in ["STOP_FILE_DETECTED", "SIGNAL_INTERRUPT"]:
        (output_dir / "STOPPED").touch()

    write_atomic_json(exec_file, {
        "complete": (stop_reason == "WALL_TIME_EXHAUSTED"),
        "stop_reason": stop_reason,
        "challenge": 8,
        "engine_backend": "frontier_reference_model",
        "model_scope": "frontier_reference_exploration",
        "model_boundary_notice": "Isolated mathematical reference exploration model; distinct from full GenesisEngine codon VM.",
        "epochs": epoch,
        "elapsed_seconds": final_elapsed,
        "red_queen_proved": False,
    })


# ==============================================================================
# CLI Entrypoint
# ==============================================================================
def main() -> None:
    parser = argparse.ArgumentParser(description="Grand Frontier Challenges 5-8")
    parser.add_argument("--challenge", type=int, required=True, choices=[5, 6, 7, 8], help="Challenge ID (5-8)")
    parser.add_argument("--duration-hours", type=float, default=72.0, help="Target duration in hours (default: 72.0)")
    parser.add_argument("--output", type=str, required=True, help="Output directory path")
    parser.add_argument("--core", type=int, default=None, help="Specific CPU core to pin to (default: challenge %% 4)")

    args = parser.parse_args()
    out_dir = Path(args.output).resolve()
    core = args.core if args.core is not None else ((args.challenge - 1) % 4)

    if args.challenge == 5:
        run_worker_5_functional_info(out_dir, args.duration_hours, core_id=core)
    elif args.challenge == 6:
        run_worker_6_quasispecies(out_dir, args.duration_hours, core_id=core)
    elif args.challenge == 7:
        run_worker_7_oee_shadow(out_dir, args.duration_hours, core_id=core)
    elif args.challenge == 8:
        run_worker_8_fisher_geometric(out_dir, args.duration_hours, core_id=core)


if __name__ == "__main__":
    main()
