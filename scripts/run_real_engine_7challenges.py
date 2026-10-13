#!/usr/bin/env python3
"""
run_real_engine_7challenges.py - Master Unified Orchestrator for 7 Real ALife Engine Challenges.

Executes all 7 frontier scientific experiments using the full GenesisEngine virtual machine,
codon dispatch, organism metabolic homeostasis, and SimulationRecorder for the Simulation Atlas.

Challenges:
- Challenge 1: Open-Ended Novelty & Diversity (Bedau & Channon OEE, Stanley Novelty)
- Challenge 2: Multilevel Selection & Demes (George Price 1970/1972, Samir Okasha 2006)
- Challenge 3: Emergent Mutualism Transition (Maynard Smith & Szathmáry 1995, Michod 2007)
- Challenge 4: Gouldian Historical Contingency & Lenski Replay (Gould 1989, Lenski 2008)
- Challenge 5: Functional Information (Hazen Bits) & Neutral Networks (Hazen 2007, Schuster 1994)
- Challenge 6: Quasispecies & Error Catastrophe Threshold (Manfred Eigen 1971, Nowak 2006)
- Challenge 7: Open-Ended Evolutionary Activity vs Shadow Control (Bedau 1992, Channon 2024)

Zero-Dictation Policy:
Strictly zero hardcoded algebraic fitness formulas. All dynamics arise emergently from
virtual machine codon execution, energy metabolism, and spatial lattice interactions.
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

# Add project root and src to sys.path
_SCRIPTS_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _SCRIPTS_DIR.parent
_SRC_DIR = _REPO_ROOT / "src"
for p in (str(_REPO_ROOT), str(_SRC_DIR)):
    if p not in sys.path:
        sys.path.insert(0, p)

# Epistemic Invariants
RED_QUEEN_PROVED = False
MAJOR_TRANSITION_PROVED = False
OPEN_ENDED_INTELLIGENCE_PROVED = False


def run_c1_oee_novelty(ticks: int = 8) -> None:
    print("\n" + "=" * 70)
    print("Executing Challenge 1: Open-Ended Novelty & Diversity (Codons)")
    print("=" * 70)
    try:
        from scripts.run_c1_oee_novelty import run_c1_oee_novelty as c1_runner
    except ImportError:
        try:
            from run_c1_oee_novelty import run_c1_oee_novelty as c1_runner
        except ImportError:
            import sys
            from pathlib import Path
            sys.path.insert(0, str(Path(__file__).resolve().parent))
            from run_c1_oee_novelty import run_c1_oee_novelty as c1_runner
    c1_runner(total_ticks=ticks)


def run_c2_mls_price(ticks: int = 8, pop: int = 8) -> None:
    print("\n" + "=" * 70)
    print("Executing Challenge 2: Multilevel Selection & Demes (Price Equation)")
    print("=" * 70)
    from scripts.run_real_c2_mls_price import run_c2_mls_price_experiment
    run_c2_mls_price_experiment(total_ticks=ticks, pop_per_deme=pop)


def run_c3_coevolution(ticks: int = 8, pop: int = 8) -> None:
    print("\n" + "=" * 70)
    print("Executing Challenge 3: Emergent Mutualism & Symbiosis Transition")
    print("=" * 70)
    from scripts.run_real_c3_coevolution import run_c3_coevolution_experiment
    run_c3_coevolution_experiment(ticks=ticks, pop=pop)


def run_c4_contingency(base_seed: int = 401, ckpt: int = 4, fork_ticks: int = 4, pop: int = 8) -> None:
    print("\n" + "=" * 70)
    print("Executing Challenge 4: Gould & Lenski Historical Contingency Replay")
    print("=" * 70)
    from scripts.run_real_c4_contingency import run_historical_contingency_experiment
    run_historical_contingency_experiment(
        base_seed=base_seed,
        checkpoint_tick=ckpt,
        fork_ticks=fork_ticks,
        initial_population=pop,
    )


def run_c5_functional_info(ticks: int = 8, pop: int = 8) -> None:
    print("\n" + "=" * 70)
    print("Executing Challenge 5: Functional Information (Hazen Bits) & Neutral Nets")
    print("=" * 70)
    from scripts.run_real_c5_functional_info import run_c5_functional_info_experiment
    run_c5_functional_info_experiment(total_ticks=ticks, init_pop=pop)


def run_c6_error_catastrophe(ticks: int = 6, pop: int = 8) -> None:
    print("\n" + "=" * 70)
    print("Executing Challenge 6: Quasispecies & Error Catastrophe Threshold")
    print("=" * 70)
    from scripts.run_real_c6_error_catastrophe import run_quasispecies_experiment
    run_quasispecies_experiment(ticks=ticks, pop=pop)


def run_c7_oee_shadow(ticks: int = 8, pop: int = 8) -> None:
    print("\n" + "=" * 70)
    print("Executing Challenge 7: Open-Ended Evolutionary Activity vs Shadow Control")
    print("=" * 70)
    from scripts.run_real_c7_oee_shadow import run_oee_shadow_experiment
    run_oee_shadow_experiment(total_ticks=ticks, pop_size=pop)


def main() -> None:
    parser = argparse.ArgumentParser(description="Master Unified Runner for 7 Real ALife Engine Challenges")
    parser.add_argument("--challenge", "-c", type=str, default="all",
                        help="Target challenge to execute ('1', '2', '3', '4', '5', '6', '7', or 'all')")
    parser.add_argument("--ticks", "-t", type=int, default=8, help="Simulation ticks per challenge (default: 8)")
    parser.add_argument("--pop", "-p", type=int, default=8, help="Population size (default: 8)")
    args = parser.parse_args()

    t_all = time.time()
    target = args.challenge.strip().lower()

    dispatch = {
        "1": lambda: run_c1_oee_novelty(ticks=args.ticks),
        "2": lambda: run_c2_mls_price(ticks=args.ticks, pop=args.pop),
        "3": lambda: run_c3_coevolution(ticks=args.ticks, pop=args.pop),
        "4": lambda: run_c4_contingency(ckpt=args.ticks // 2 or 4, fork_ticks=args.ticks // 2 or 4, pop=args.pop),
        "5": lambda: run_c5_functional_info(ticks=args.ticks, pop=args.pop),
        "6": lambda: run_c6_error_catastrophe(ticks=args.ticks, pop=args.pop),
        "7": lambda: run_c7_oee_shadow(ticks=args.ticks, pop=args.pop),
    }

    if target in dispatch:
        dispatch[target]()
        print("\n" + "=" * 70)
        print(f"Target Challenge {target} completed in {round(time.time() - t_all, 2)}s!")
        print("=" * 70)
        return

    if target == "all":
        print("\n" + "=" * 70)
        print("LAUNCHING ALL 7 REAL BIOLOGICAL ENGINE CHALLENGES ON GENESIS ENGINE")
        print("=" * 70)
        run_c1_oee_novelty(ticks=args.ticks)
        run_c2_mls_price(ticks=args.ticks, pop=args.pop)
        run_c3_coevolution(ticks=args.ticks, pop=args.pop)
        run_c4_contingency(ckpt=args.ticks // 2 or 4, fork_ticks=args.ticks // 2 or 4, pop=args.pop)
        run_c5_functional_info(ticks=args.ticks, pop=args.pop)
        run_c6_error_catastrophe(ticks=args.ticks, pop=args.pop)
        run_c7_oee_shadow(ticks=args.ticks, pop=args.pop)

        print("\n" + "=" * 70)
        print(f"ALL 7 REAL ENGINE CHALLENGES SUCCESSFULLY COMPLETED IN {round(time.time() - t_all, 2)}s!")
        print("All spatial frames, lineages, and telemetry recorded for Simulation Atlas!")
        print("=" * 70)
        return

    print(f"Unknown challenge target: '{args.challenge}'. Valid options: 1, 2, 3, 4, 5, 6, 7, all")
    sys.exit(1)


if __name__ == "__main__":
    main()
