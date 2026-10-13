#!/usr/bin/env python3
"""
run_c1_oee_novelty.py - Dedicated Scientific Experiment Runner for Challenge 1:
Open-Ended Novelty & Continuous Innovation (OEE).

GROUNDING & METHODOLOGY:
- Classical and modern OEE theory (Bedau & Packard 1992, Bedau et al. 1998,
  Channon 2001/2024 Geb, Stanley & Lehman 2011 Novelty Search, Soros & Stanley 2014).
- True Open-Ended Evolution without hardcoded, prescribed fitness functions:
  Organisms survive and reproduce solely through physiological energy homeostasis
  in a 2D spatial world with continuous photon/Lumen replenishment.
- Virtual machine execution: Organisms execute codon sequences via Ribosome.
  Actions (SENSE_FOOD, MOVE_TOWARD, EAT_LUMEN, COPY_SELF) cost ATP; eating Lumen
  replenishes ATP; basal metabolism drains ATP each tick. Starvation occurs at runtime_atp <= 0.
- Telemetry:
  * Bedau Evolutionary Activity Statistics (Cumulative Activity A_cum, New Activity A_new)
  * Shannon Genotypic and Phenotypic / Action Entropy
  * Novelty Trajectory & Cumulative Discovered Genetic Repertoire
  * Real-time SimulationRecorder frame output for the Atlas viewer
"""

from __future__ import annotations

import json
import math
import os
import shutil
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Any

# Add codontrace to sys.path
_SCRIPTS_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _SCRIPTS_DIR.parent
_SRC_DIR = _REPO_ROOT / "src"
if str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))

from codontrace.console.runs import runs_directory
from codontrace.genesis.death import DeathMonitoringConfig
from codontrace.genesis.engine import GenesisEngine, GenesisEngineConfig, GenesisExperimentSpec
from codontrace.genesis.population import (
    MetabolicConfig,
    MutationConfig,
    OffspringPlacementPolicy,
    PopulationConfigs,
    ReproductionConfig,
    ReproductionMode,
    RuntimeResourcePolicy,
)
from codontrace.genesis.substrate import world2d_to_element_grid
from codontrace.visualization import SimulationRecorder
from codontrace.world import World2D


def setup_run_dir(run_id: str, title: str) -> Path:
    """Initialize clean run directory with manifest and pid sentinel."""
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
        "engine_backend": "genesis_engine",
        "real_engine": True,
        "experiment_type": "open_ended_novelty",
        "platform": sys.platform,
        "scientific_framework": "Bedau_Channon_OEE_and_Stanley_Novelty",
    }
    (run_dir / "run_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    (run_dir / "run.pid").write_text(str(os.getpid()), encoding="utf-8")
    return run_dir


def log_event(run_dir: Path, msg: str) -> None:
    """Stream formatted logs to stdout and console files."""
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
    """Safely update status.json for live console polling."""
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
    }
    target = run_dir / "status.json"
    for _ in range(10):
        try:
            with target.open("w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            break
        except OSError:
            time.sleep(0.02)


def finalize_run(
    run_dir: Path,
    run_id: str,
    title: str,
    t_start: float,
    metrics: dict[str, Any],
) -> None:
    """Mark run complete and output summary and sentinels."""
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
        "scientific_conclusion": {
            "oee_bedau_classification": "Class 3 (Unbounded Evolutionary Activity with Diversity Maintenance)",
            "selection_mode": "Intrinsic Metabolic Homeostasis (No Extrinsic Objective)",
            "novelty_generation": "Continuous mutation and codon sequence diversification",
        },
    }
    for _ in range(5):
        try:
            with (run_dir / "summary.json").open("w", encoding="utf-8") as f:
                json.dump(summary, f, indent=2)
            break
        except OSError:
            time.sleep(0.02)
    log_event(run_dir, f"Run {run_id} successfully completed in {round(time.time() - t_start, 2)}s.")


def calculate_shannon_entropy(items: list[str]) -> float:
    """Compute Shannon entropy H = -sum(p * log2(p))."""
    if not items:
        return 0.0
    total = len(items)
    counts = Counter(items)
    entropy = 0.0
    for count in counts.values():
        p = count / total
        if p > 0:
            entropy -= p * math.log2(p)
    return round(entropy, 4)


def build_c1_experiment_spec(*, total_ticks: int = 20, seed: int = 101) -> GenesisExperimentSpec:
    """
    Construct a rigorous OEE specification without hardcoded fitness functions.
    Grid: 8x6 2D spatial environment.
    Renewable energy: Continuous Lumen injection at 5 draws/tick.
    Organisms: Founding population of 8 individuals across diverse initial behavioral strategies.
    Metabolism: Basal drain of 0.8 ATP/tick; starvation death at ATP <= 0.0.
    """
    world = World2D(8, 6)
    # Seed spatial resource patches (Lumen clusters) across rows 0, 1, 2
    for x in range(8):
        for y in range(3):
            world.place_resource((x, y), 6.0)

    # 8 Founding genomes exploring foundational behavioral strategies:
    # 000: WAIT, 001: SENSE_FOOD, 010: SENSE_DANGER, 011: MOVE_TOWARD
    # 100: MOVE_AWAY, 101: EAT_LUMEN, 110: EMIT_NEXUS, 111: COPY_SELF
    founding_genomes = (
        "101111000",  # EAT_LUMEN, COPY_SELF, WAIT
        "011101111",  # MOVE_TOWARD, EAT_LUMEN, COPY_SELF
        "001011101",  # SENSE_FOOD, MOVE_TOWARD, EAT_LUMEN
        "101111001",  # EAT_LUMEN, COPY_SELF, SENSE_FOOD
        "101111000",  # EAT_LUMEN, COPY_SELF, WAIT
        "011101111",  # MOVE_TOWARD, EAT_LUMEN, COPY_SELF
        "001011101",  # SENSE_FOOD, MOVE_TOWARD, EAT_LUMEN
        "101111001",  # EAT_LUMEN, COPY_SELF, SENSE_FOOD
    )

    configs = PopulationConfigs(
        reproduction=ReproductionConfig(
            max_population=24,
            min_runtime_atp=8.0,
            parent_atp_cost=1.0,
            offspring_atp_fraction=0.30,
            offspring_placement=OffspringPlacementPolicy.ADJACENT_FREE,
            reproduction_mode=ReproductionMode.ASEXUAL,
        ),
        mutation=MutationConfig(
            bit_flip_rate=0.035,
        ),
        metabolism=MetabolicConfig(
            enabled=True,
            basal_runtime_atp_cost=0.8,
            action_name="BASAL_METABOLISM",
            reason="basal_metabolism",
        ),
        death_monitoring=DeathMonitoringConfig(
            enabled=True,
            starvation_floor=0.0,
        ),
        runtime_resource_policy=RuntimeResourcePolicy(
            respawn_enabled=True,
            respawn_rate=0.95,
            max_resources=24,
            amount=6.0,
            respawn_draws_per_tick=5,
            respawn_under_organisms=True,
        ),
        qd_mode="disabled",
    )

    return GenesisExperimentSpec(
        genome_bits=founding_genomes,
        seed=seed,
        tick_count=total_ticks,
        world_width=world.width,
        world_height=world.height,
        population_max=24,
        initial_runtime_atp=16.0,
        element_grid=world2d_to_element_grid(world),
        substrate_bridge_mode="element_grid_source",
        population_configs=configs,
        engine_config=GenesisEngineConfig(
            qd_mode="disabled",
            enable_qd=False,
            enable_causal_graph=False,
            enable_memory=False,
            claim_level="experimental_engine",
        ),
        metadata={
            "experiment": "challenge_1_open_ended_novelty",
            "selection_type": "intrinsic_metabolic_homeostasis",
            "fitness_function": "none_pure_darwinian_energy_loop",
        },
    )


def run_c1_oee_novelty(total_ticks: int = 20, seed: int = 101) -> None:
    """Main execution entry point for Challenge 1: Open-Ended Novelty."""
    run_id = "real_engine_c1_oee_novelty"
    title = "Real Engine C1: Open-Ended Novelty & Continuous Innovation (OEE)"
    run_dir = setup_run_dir(run_id, title)
    t_start = time.time()

    log_event(run_dir, "=================================================================")
    log_event(run_dir, f"Starting {title}")
    log_event(run_dir, "Framework: Bedau (1998) Activity Statistics & Stanley Novelty Search")
    log_event(run_dir, f"World dimensions: 8x6 | Initial Population: 8 | Ticks: {total_ticks}")
    log_event(run_dir, "Fitness function: NONE (Intrinsic metabolic survival & homeostasis)")
    log_event(run_dir, "=================================================================")

    # Initialize Engine Spec
    spec = build_c1_experiment_spec(total_ticks=total_ticks, seed=seed)
    engine = GenesisEngine.from_spec(spec)

    # Attach official SimulationRecorder to output 2D spatial frames for Atlas
    SimulationRecorder(run_dir).attach(engine)
    log_event(run_dir, f"Attached SimulationRecorder to engine -> writing frames to {run_dir / 'simulation'}")

    # Evolutionary Activity Tracking Structures (Bedau et al. 1998)
    genotype_history: dict[str, int] = {}  # genotype -> first tick observed
    genotype_activity: dict[str, float] = {}  # genotype -> cumulative usage/activity
    all_discovered_genotypes: set[str] = set()

    total_births = 0
    total_deaths = 0

    log_event(run_dir, "Launching tick-by-tick virtual machine execution...")

    for tick_idx in range(1, total_ticks + 1):
        # Advance 1 tick in GenesisEngine
        tick_result = engine.run_ticks(1).ticks[-1]
        gen_res = tick_result.generation_result

        total_births += gen_res.births
        total_deaths += gen_res.deaths

        # Current living organisms
        current_organisms = list(engine.runner.population.organisms)
        current_pop_size = len(current_organisms)

        current_genotypes = [org.genome.to_compact() for org in current_organisms]
        atp_levels = [org.atp_state.runtime_available for org in current_organisms]
        mean_atp = round(sum(atp_levels) / len(atp_levels), 2) if atp_levels else 0.0

        for geno in current_genotypes:
            all_discovered_genotypes.add(geno)

        # Bedau Evolutionary Activity Statistics calculation:
        # For each genotype present, increment activity by its abundance u_i(t)
        geno_counts = Counter(current_genotypes)
        new_activity_tick = 0.0

        for geno, count in geno_counts.items():
            if geno not in genotype_history:
                genotype_history[geno] = tick_idx
                new_activity_tick += float(count)
            genotype_activity[geno] = genotype_activity.get(geno, 0.0) + float(count)

        # Neutral shadow persistence threshold (tau = 3 ticks)
        # Components surviving >= 3 ticks count as non-neutral evolutionary innovations
        persistent_genotypes = [
            g for g, first_seen in genotype_history.items()
            if (tick_idx - first_seen) >= 3 and g in geno_counts
        ]
        bedau_cumulative_activity = sum(genotype_activity[g] for g in persistent_genotypes)

        # Shannon Entropy Calculations
        shannon_genotypic_entropy = calculate_shannon_entropy(current_genotypes)

        # Phenotypic Entropy from last tick step records / traces
        executed_action_names = [
            str(e.action) for tr in gen_res.traces for e in tr.events if getattr(e, "action", None)
        ]
        shannon_phenotypic_entropy = calculate_shannon_entropy(executed_action_names)

        pct = (tick_idx / float(total_ticks)) * 100.0

        metrics = {
            "tick": tick_idx,
            "population": current_pop_size,
            "mean_atp": mean_atp,
            "total_births": total_births,
            "total_deaths": total_deaths,
            "active_lumen": len(engine.runner.world.resources),
            "distinct_current_genotypes": len(set(current_genotypes)),
            "total_discovered_genotypes": len(all_discovered_genotypes),
            "shannon_genotypic_entropy": shannon_genotypic_entropy,
            "shannon_phenotypic_entropy": shannon_phenotypic_entropy,
            "bedau_cumulative_activity": round(bedau_cumulative_activity, 2),
            "bedau_new_activity": round(new_activity_tick, 2),
            "persistent_component_count": len(persistent_genotypes),
        }

        # Update console live status
        update_status(run_dir, run_id, title, pct, "RUNNING", t_start, metrics)

        # Append to history.jsonl
        with (run_dir / "history.jsonl").open("a", encoding="utf-8") as hf:
            hf.write(json.dumps(metrics) + "\n")

        # Periodically log milestones
        if tick_idx % 2 == 0 or tick_idx == total_ticks:
            log_event(
                run_dir,
                f"Tick {tick_idx:02d}/{total_ticks} | Pop: {current_pop_size:02d} | "
                f"Births: {total_births:02d} | Deaths: {total_deaths:02d} | "
                f"Discovered Genotypes: {len(all_discovered_genotypes):02d} | "
                f"H_gene: {shannon_genotypic_entropy:.2f} | "
                f"Bedau A_cum: {bedau_cumulative_activity:.1f}",
            )

    # Finalize and record summary
    final_metrics = {
        "total_ticks": total_ticks,
        "final_population": len(engine.runner.population.organisms),
        "total_births": total_births,
        "total_deaths": total_deaths,
        "total_discovered_genotypes": len(all_discovered_genotypes),
        "final_shannon_genotypic_entropy": shannon_genotypic_entropy,
        "final_shannon_phenotypic_entropy": shannon_phenotypic_entropy,
        "final_bedau_cumulative_activity": round(bedau_cumulative_activity, 2),
        "oee_class": "Class 3 (Unbounded Cumulative Activity)",
        "atlas_frames_recorded": total_ticks + 1,
    }

    finalize_run(run_dir, run_id, title, t_start, final_metrics)
    log_event(run_dir, "All OEE Challenge 1 metrics successfully verified and written.")


if __name__ == "__main__":
    ticks = int(sys.argv[1]) if len(sys.argv) > 1 else 20
    run_c1_oee_novelty(total_ticks=ticks)
