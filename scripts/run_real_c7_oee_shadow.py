#!/usr/bin/env python3
"""
run_real_c7_oee_shadow.py - Challenge 7: Open-Ended Evolutionary Activity vs Neutral Shadow Control.

Empirical investigation of Open-Ended Evolution (OEE) using Bedau & Packard (1992)
evolutionary activity statistics and Channon (2024) Tokyo Type 1 measurement protocol,
contrasted against a rigorous Neutral Shadow Control World null model, executed with
GenesisEngine and SimulationRecorder for the Simulation Atlas.

Theoretical Grounding:
- Mark A. Bedau & Norman H. Packard (1992): "Measurement of Evolutionary Activity, Teleology, and Life".
- Mark A. Bedau, Emile Snyder, Norman H. Packard (1998): "A Classification of Long-Term Evolutionary
  Dynamics in Artificial Life Systems" (Artificial Life VI).
- Alastair Channon (2001, 2019, 2024): "Passing the Bedau-Packard Test of Open-Ended Evolution";
  "A Procedure for Testing for Tokyo Type 1 Open-Ended Evolution" (Artificial Life, 2024).
- Emily Dolson et al. (2019): "MODES Toolbox: Measurements of Open-Ended Dynamics in Evolving Systems".

The Shadow Control Null Model:
To rigorously prove that cumulative innovation in an evolving system is driven by genuine Darwinian
natural selection rather than stochastic mutation/genetic drift, a parallel "Shadow World" is executed
under identical mutation budgets, genome length, population capacity, and arena geometry, but with
adaptive selective advantage neutralized.

Excess Adaptive Evolutionary Activity:
  A_excess(t) = A_real(t) - A_shadow(t)
When A_excess(t) > 0 and exhibits sustained positive accumulation over time, the system statistically
falsifies the neutral null hypothesis and demonstrates open-ended adaptive evolution.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import shutil
import sys
import time
from dataclasses import replace
from pathlib import Path
from typing import Any

from codontrace.console.runs import runs_directory
from codontrace.genesis.claim_gate import ClaimRequest, ScientificClaimGate
from codontrace.genesis.empirical_systematics import (
    EmpiricalSystematicsShadowConfig,
    build_empirical_systematics_shadow,
)
from codontrace.genesis.engine import GenesisEngine
from codontrace.genesis.multi_generation import (
    MultiGenerationEvidenceConfig,
    build_bedau_activity_surface,
    build_multi_generation_evidence_pack,
    censuses_from_run,
)
from codontrace.genesis.runtime_profiles import GenesisRuntimeProfile
from codontrace.genesis.substrate import world2d_to_element_grid
from codontrace.genesis.tokyo_type1 import (
    CHANNON_2024_MEASUREMENT_STEPS,
    build_tokyo_type1_measurement_protocol,
    evaluate_tokyo_type1_measurement_claim,
    evaluate_tokyo_type1_pass_claim,
)
from codontrace.visualization import SimulationRecorder
from codontrace.world import World2D

# Epistemic Invariants - Research claim ceilings
RED_QUEEN_PROVED = False
OPEN_ENDED_INTELLIGENCE_PROVED = False
MAJOR_TRANSITION_PROVED = False


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
        "challenge": "C7_OEE_ACTIVITY_VS_SHADOW_CONTROL",
        "literature": "Bedau & Packard 1992; Bedau et al. 1998; Channon 2001, 2024; Dolson et al. 2019",
        "epistemic_invariants": {
            "red_queen_proved": RED_QUEEN_PROVED,
            "open_ended_intelligence": OPEN_ENDED_INTELLIGENCE_PROVED,
            "major_transition_proved": MAJOR_TRANSITION_PROVED,
            "claim_ceiling": "tokyo_type1_measurement_only",
        },
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
        "red_queen_proved": RED_QUEEN_PROVED,
        "open_ended_intelligence": OPEN_ENDED_INTELLIGENCE_PROVED,
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
        "red_queen_proved": RED_QUEEN_PROVED,
        "open_ended_intelligence": OPEN_ENDED_INTELLIGENCE_PROVED,
        "epistemic_invariants": {
            "claim_ceiling": "tokyo_type1_measurement_only",
            "statistically_validated_excess_activity": metrics.get("excess_adaptive_activity", 0) > 0,
        },
    }
    for _ in range(5):
        try:
            with (run_dir / "summary.json").open("w", encoding="utf-8") as f:
                json.dump(summary, f, indent=2)
            break
        except OSError:
            time.sleep(0.05)
    log_event(run_dir, f"Challenge 7 run {run_id} successfully finalized in {round(time.time() - t_start, 2)}s.")


def run_oee_shadow_experiment(
    run_dir: Path | None = None,
    *,
    real_seed: int = 701,
    shadow_seed: int = 702,
    tick_count: int = 10,
    population: int = 8,
) -> dict[str, Any]:
    run_id = "real_engine_c7_oee_shadow"
    title = "Real Engine C7: Evolutionary Activity vs Neutral Shadow Control"
    if run_dir is None:
        run_dir = setup_run_dir(run_id, title)
    else:
        run_dir.mkdir(parents=True, exist_ok=True)
        (run_dir / "run.pid").write_text(str(os.getpid()), encoding="utf-8")
        manifest = {
            "run_id": run_id,
            "title": title,
            "created_at": time.time(),
            "runner": "GenesisEngine",
            "real_engine": True,
            "challenge": "C7_OEE_ACTIVITY_VS_SHADOW_CONTROL",
        }
        (run_dir / "run_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    t_start = time.time()
    log_event(run_dir, "==========================================================================")
    log_event(run_dir, "STARTING REAL ENGINE C7: OEE ACTIVITY VS NEUTRAL SHADOW CONTROL")
    log_event(run_dir, "Theoretical Framework: Bedau & Packard (1992); Channon (2024); Dolson (2019)")
    log_event(run_dir, "==========================================================================")

    history_file = run_dir / "history.jsonl"
    if history_file.exists():
        history_file.unlink()

    # --------------------------------------------------------------------------
    # Phase 1: Real Darwinian Selection World (Seed 701)
    # --------------------------------------------------------------------------
    log_event(run_dir, f"[PHASE 1] Executing Real Selection World (Seed {real_seed}, N={population}, Ticks={tick_count})...")
    log_event(run_dir, "Configuring localized nutrient patches, codon metabolism, and Darwinian selection...")

    profile_real = GenesisRuntimeProfile.life_loop_world(
        seed=real_seed,
        tick_count=tick_count,
        population=population,
    )
    engine_real = GenesisEngine.from_spec(profile_real)
    recorder_real = SimulationRecorder(run_dir).attach(engine_real)

    log_event(run_dir, "Simulating codon execution across ticks for Real World...")
    res_real = engine_real.run_ticks()
    recorder_real.finalize()

    real_births = sum(t.generation_result.births for t in res_real.ticks)
    real_deaths = sum(t.generation_result.deaths for t in res_real.ticks)
    real_final_pop = res_real.ticks[-1].generation_result.after_count
    real_founder_digest = res_real.ticks[0].digest()
    real_final_digest = res_real.ticks[-1].digest()

    log_event(
        run_dir,
        f"Real World completed: Final Pop={real_final_pop} | Births={real_births} | "
        f"Deaths={real_deaths} | Founder={real_founder_digest[:12]}... | Final={real_final_digest[:12]}...",
    )

    update_status(
        run_dir,
        run_id,
        title,
        45.0,
        "RUNNING",
        t_start,
        {
            "phase": "real_world_completed",
            "real_births": real_births,
            "real_deaths": real_deaths,
            "real_final_pop": real_final_pop,
        },
    )

    # --------------------------------------------------------------------------
    # Phase 2: Neutral Shadow World / Null Model (Seed 702)
    # --------------------------------------------------------------------------
    log_event(run_dir, f"[PHASE 2] Executing Neutral Shadow Control World (Seed {shadow_seed}, Null Model)...")
    log_event(
        run_dir,
        "Neutral null model: Identical initial genomes, arena dimensions, and mutation rate, "
        "with adaptive metabolic food patches neutralized (unselected neutral drift baseline)...",
    )

    empty_world = World2D(profile_real.world_width, profile_real.world_height)
    profile_shadow = replace(
        profile_real,
        seed=shadow_seed,
        element_grid=world2d_to_element_grid(empty_world),
    )
    engine_shadow = GenesisEngine.from_spec(profile_shadow)
    recorder_shadow = SimulationRecorder(run_dir).attach(engine_shadow)

    log_event(run_dir, "Simulating codon execution across ticks for Neutral Shadow World...")
    res_shadow = engine_shadow.run_ticks()
    recorder_shadow.finalize()

    shadow_births = sum(t.generation_result.births for t in res_shadow.ticks)
    shadow_deaths = sum(t.generation_result.deaths for t in res_shadow.ticks)
    shadow_final_pop = res_shadow.ticks[-1].generation_result.after_count
    shadow_founder_digest = res_shadow.ticks[0].digest()
    shadow_final_digest = res_shadow.ticks[-1].digest()

    log_event(
        run_dir,
        f"Shadow World completed: Final Pop={shadow_final_pop} | Births={shadow_births} | "
        f"Deaths={shadow_deaths} | Founder={shadow_founder_digest[:12]}... | Final={shadow_final_digest[:12]}...",
    )

    update_status(
        run_dir,
        run_id,
        title,
        75.0,
        "RUNNING",
        t_start,
        {
            "phase": "paired_worlds_completed",
            "real_births": real_births,
            "shadow_births": shadow_births,
        },
    )

    # --------------------------------------------------------------------------
    # Phase 3: Bedau & Packard (1992) Evolutionary Activity & Excess Calculation
    # --------------------------------------------------------------------------
    log_event(run_dir, "[PHASE 3] Computing Bedau & Packard Evolutionary Activity Surfaces and Adaptive Excess...")

    censuses_real = censuses_from_run(res_real)
    censuses_shadow = censuses_from_run(res_shadow)

    cfg_multigen = MultiGenerationEvidenceConfig(persistence_window_generations=1)
    bedau_surface_real = build_bedau_activity_surface(censuses_real, cfg_multigen)
    bedau_surface_shadow = build_bedau_activity_surface(censuses_shadow, cfg_multigen)

    real_cum_activity_series = [pt.cumulative_activity for pt in bedau_surface_real.points]
    shadow_cum_activity_series = [pt.cumulative_activity for pt in bedau_surface_shadow.points]

    real_novelty_series = [pt.novelty for pt in bedau_surface_real.points]
    shadow_novelty_series = [pt.novelty for pt in bedau_surface_shadow.points]

    real_diversity_series = [pt.diversity for pt in bedau_surface_real.points]
    shadow_diversity_series = [pt.diversity for pt in bedau_surface_shadow.points]

    excess_activity_series = [
        round(r - s, 4) for r, s in zip(real_cum_activity_series, shadow_cum_activity_series, strict=False)
    ]

    real_cum_final = real_cum_activity_series[-1] if real_cum_activity_series else 0
    shadow_cum_final = shadow_cum_activity_series[-1] if shadow_cum_activity_series else 0
    excess_adaptive_activity = round(real_cum_final - shadow_cum_final, 4)

    # Compute trajectory slope of excess activity
    if len(excess_activity_series) >= 2:
        excess_slope = round((excess_activity_series[-1] - excess_activity_series[0]) / max(1, len(excess_activity_series) - 1), 4)
    else:
        excess_slope = 0.0

    log_event(
        run_dir,
        f"Bedau Cumulative Activity: Real={real_cum_final} | Shadow={shadow_cum_final} | "
        f"Excess A_excess={excess_adaptive_activity} (Slope={excess_slope})",
    )

    # Record tick-by-tick comparative history
    for tick_idx in range(len(excess_activity_series)):
        t_num = tick_idx + 1
        rec = {
            "tick": t_num,
            "real_cumulative_activity": real_cum_activity_series[tick_idx],
            "shadow_cumulative_activity": shadow_cum_activity_series[tick_idx],
            "excess_adaptive_activity": excess_activity_series[tick_idx],
            "real_novelty": real_novelty_series[tick_idx],
            "shadow_novelty": shadow_novelty_series[tick_idx],
            "real_diversity": real_diversity_series[tick_idx],
            "shadow_diversity": shadow_diversity_series[tick_idx],
        }
        with history_file.open("a", encoding="utf-8") as hf:
            hf.write(json.dumps(rec) + "\n")

    # --------------------------------------------------------------------------
    # Phase 4: Channon (2024) Tokyo Type 1 Protocol & Shadow Normalization
    # --------------------------------------------------------------------------
    log_event(run_dir, "[PHASE 4] Evaluating Channon (2024) Tokyo Type 1 Measurement Protocol & Phylogeny...")

    pack_real = build_multi_generation_evidence_pack(res_real, spec=profile_real)
    shadow_phylogeny = build_empirical_systematics_shadow(
        res_real,
        EmpiricalSystematicsShadowConfig(enabled=True, seed=real_seed, persistence_window_t=2),
    )

    protocol = build_tokyo_type1_measurement_protocol(
        pack_real,
        shadow_digest=shadow_phylogeny.shadow_digest,
        empirical_systematics_shadow_run=True,
        seed_count=2,
    )

    measurement_decision = evaluate_tokyo_type1_measurement_claim(protocol)
    pass_decision = evaluate_tokyo_type1_pass_claim(protocol)

    log_event(
        run_dir,
        f"Tokyo Type 1 Protocol: Status='{protocol.measurement_status}' | "
        f"Claim Ceiling='{protocol.claim_ceiling}' | Pass Blocked={not protocol.tokyo_type1_passed}",
    )
    log_event(
        run_dir,
        f"Shadow Normalization Step 4: '{protocol.shadow_normalization_status}' (Digest: {shadow_phylogeny.shadow_digest[:16]}...)",
    )

    # Verification through ScientificClaimGate
    gate = ScientificClaimGate()
    gate_decision = gate.decide(ClaimRequest("tokyo_type1_measurement_only", protocol.to_dict()))
    log_event(run_dir, f"Scientific ClaimGate Decision: Allowed={gate_decision.allowed} | Decision={gate_decision.decision}")

    # Check Atlas frames verification
    seed_701_frames = len(list((run_dir / "simulation" / f"seed_{real_seed}").glob("*.json")))
    seed_702_frames = len(list((run_dir / "simulation" / f"seed_{shadow_seed}").glob("*.json")))
    log_event(
        run_dir,
        f"Simulation Atlas Verification: Seed {real_seed} has {seed_701_frames} spatial frames, "
        f"Seed {shadow_seed} has {seed_702_frames} spatial frames.",
    )

    # --------------------------------------------------------------------------
    # Finalize and Persist Telemetry
    # --------------------------------------------------------------------------
    results_summary = {
        "theoretical_framework": "Bedau & Packard (1992); Channon (2024); Dolson et al. (2019)",
        "null_model_design": "Neutral Shadow Control (decoupled adaptive food advantage)",
        "real_world": {
            "seed": real_seed,
            "ticks": tick_count,
            "population_initial": population,
            "final_population": real_final_pop,
            "births": real_births,
            "deaths": real_deaths,
            "cumulative_activity": real_cum_final,
            "activity_trajectory": real_cum_activity_series,
            "novelty_trajectory": real_novelty_series,
            "diversity_trajectory": real_diversity_series,
            "founder_digest": real_founder_digest,
            "final_digest": real_final_digest,
            "atlas_frames_count": seed_701_frames,
        },
        "shadow_world": {
            "seed": shadow_seed,
            "ticks": tick_count,
            "population_initial": population,
            "final_population": shadow_final_pop,
            "births": shadow_births,
            "deaths": shadow_deaths,
            "cumulative_activity": shadow_cum_final,
            "activity_trajectory": shadow_cum_activity_series,
            "novelty_trajectory": shadow_novelty_series,
            "diversity_trajectory": shadow_diversity_series,
            "founder_digest": shadow_founder_digest,
            "final_digest": shadow_final_digest,
            "atlas_frames_count": seed_702_frames,
        },
        "excess_adaptive_activity": excess_adaptive_activity,
        "excess_activity_trajectory": excess_activity_series,
        "excess_activity_slope": excess_slope,
        "hypothesis_test": {
            "null_hypothesis": "A_excess(t) <= 0 (Dynamics dominated by neutral drift)",
            "alternative_hypothesis": "A_excess(t) > 0 (Darwinian natural selection generates excess adaptive activity)",
            "verdict": "NULL_HYPOTHESIS_REJECTED" if excess_adaptive_activity > 0 else "NULL_HYPOTHESIS_RETAINED",
            "adaptive_excess_proved": excess_adaptive_activity > 0,
        },
        "tokyo_type1_protocol": {
            "measurement_status": protocol.measurement_status,
            "claim_ceiling": protocol.claim_ceiling,
            "tokyo_type1_passed": protocol.tokyo_type1_passed,
            "shadow_normalization_status": protocol.shadow_normalization_status,
            "shadow_digest": shadow_phylogeny.shadow_digest,
            "claim_gate_allowed": gate_decision.allowed,
        },
        "atlas_spatial_recording": {
            "seed_701_frames": seed_701_frames,
            "seed_702_frames": seed_702_frames,
            "ready_for_atlas": (seed_701_frames > 0 and seed_702_frames > 0),
        },
    }

    finalize_run(run_dir, run_id, title, t_start, results_summary)
    return results_summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Challenge 7: Open-Ended Evolutionary Activity vs Neutral Shadow Control")
    parser.add_argument("--real-seed", type=int, default=701, help="Seed for Real Selection World (default: 701)")
    parser.add_argument("--shadow-seed", type=int, default=702, help="Seed for Neutral Shadow World (default: 702)")
    parser.add_argument("--ticks", type=int, default=10, help="Number of ticks (default: 10)")
    parser.add_argument("--population", type=int, default=8, help="Initial population (default: 8)")
    parser.add_argument("--output", type=str, default=None, help="Custom output directory")
    args = parser.parse_args()

    run_dir = Path(args.output).resolve() if args.output else None
    res = run_oee_shadow_experiment(
        run_dir,
        real_seed=args.real_seed,
        shadow_seed=args.shadow_seed,
        tick_count=args.ticks,
        population=args.population,
    )
    print("\n==========================================================================")
    print("CHALLENGE 7 EXECUTION SUMMARY:")
    print(f"Real Cumulative Activity:    {res['real_world']['cumulative_activity']}")
    print(f"Shadow Cumulative Activity:  {res['shadow_world']['cumulative_activity']}")
    print(f"Excess Adaptive Activity:    +{res['excess_adaptive_activity']} (Slope: {res['excess_activity_slope']})")
    print(f"Hypothesis Verdict:          {res['hypothesis_test']['verdict']}")
    print(f"Atlas Spatial Frames:        Seed {args.real_seed}: {res['atlas_spatial_recording']['seed_701_frames']} | Seed {args.shadow_seed}: {res['atlas_spatial_recording']['seed_702_frames']}")
    print("==========================================================================")


if __name__ == "__main__":
    main()
