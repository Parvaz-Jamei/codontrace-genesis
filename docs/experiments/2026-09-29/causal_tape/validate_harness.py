"""CausalTape-1 gate A/B -- harness validity before any measurement.

Gate A: determinism floor. Re-running one tape must reproduce every digest,
         fitness value and the full event list bit-for-bit.
Gate B: intervention minimality. Suppressing one drawn event must
         (i) leave the RNG stream digest unchanged, so the rest of the tape is
             bit-identical, and
         (ii) on a neutral (accept-all) tape whose event touches a bit exactly
              once, change exactly that one bit and match the closed-form
              fitness delta.
         If the gates fail, every downstream number is void.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from harness import BITS, build_env, run_tape

RESULTS = Path(__file__).resolve().parent / "results"
RESULTS.mkdir(exist_ok=True)


def gate_a(generations: int = 40, seeds: tuple[int, ...] = (3, 11, 29)) -> dict:
    checks = []
    for seed in seeds:
        env = build_env(0.2)
        first = run_tape(seed=seed, generations=generations, env=env, proposal="engine")
        second = run_tape(seed=seed, generations=generations, env=env, proposal="engine")
        fast_first = run_tape(seed=seed, generations=generations, env=env, proposal="fast")
        fast_second = run_tape(seed=seed, generations=generations, env=env, proposal="fast")
        same = (
            first.digest() == second.digest()
            and first.events == second.events
            and first.final_bits == second.final_bits
        )
        fast_same = fast_first.digest() == fast_second.digest() and fast_first.events == fast_second.events
        checks.append(
            {
                "seed": seed,
                "digest": first.digest()[:48],
                "events": len(first.events),
                "accepted": sum(1 for ev in first.events if ev.accepted),
                "identical": same,
                "fast_identical": fast_same,
            }
        )
    passed = all(c["identical"] and c["fast_identical"] for c in checks)
    return {"gate": "A_determinism_floor", "passed": passed, "checks": checks}


def gate_c(generations: int = 40, seeds: tuple[int, ...] = (0, 1, 2, 3, 4, 5)) -> dict:
    """The fast path must reproduce the engine Mutation path exactly."""

    checks = []
    for eps in (0.0, 0.4):
        env = build_env(eps)
        for seed in seeds:
            engine = run_tape(seed=seed, generations=generations, env=env, proposal="engine")
            fast = run_tape(seed=seed, generations=generations, env=env, proposal="fast")
            checks.append(
                {
                    "eps": eps,
                    "seed": seed,
                    "events_equal": engine.events == fast.events,
                    "bits_equal": engine.final_bits == fast.final_bits,
                    "fitness_equal": engine.fitness == fast.fitness,
                    "rng_equal": engine.rng_digest == fast.rng_digest,
                }
            )
    passed = all(
        c["events_equal"] and c["bits_equal"] and c["fitness_equal"] and c["rng_equal"] for c in checks
    )
    return {"gate": "C_fast_path_equivalence", "passed": passed, "checks": checks}


def gate_b(seed: int = 5, generations: int = 40, eps: float = 0.2) -> dict:
    env = build_env(eps)
    natural = run_tape(seed=seed, generations=generations, env=env, accept_all=True)

    counts: dict[int, int] = {}
    for ev in natural.events:
        counts[ev.bit] = counts.get(ev.bit, 0) + 1
    unique = [ev for ev in natural.events if counts[ev.bit] == 1]
    if not unique:
        return {"gate": "B_intervention_minimality", "passed": False, "reason": "no unique-bit event"}

    checks = []
    for ev in unique[:4]:
        intervened = run_tape(
            seed=seed, generations=generations, env=env, accept_all=True, suppress=frozenset({ev.mutation_id})
        )
        diff_bits = [i for i in range(BITS) if natural.final_bits[i] != intervened.final_bits[i]]
        nat = list(natural.final_bits)
        expected_cleared = [value if i != ev.bit else 0 for i, value in enumerate(nat)]
        analytic_delta = env.analytic_clear_delta(np.array(nat, dtype=float), ev.bit)
        checks.append(
            {
                "event": ev.mutation_id,
                "stream_unchanged": natural.rng_digest == intervened.rng_digest,
                "changed_bits": diff_bits,
                "single_bit_is_target": diff_bits == [ev.bit],
                "bits_match_clear": list(intervened.final_bits) == expected_cleared,
                "fitness_matches_clear": abs(intervened.fitness - float(env.fitness(np.array(expected_cleared, dtype=float)))) < 1e-12,
                "delta_matches_analytic": abs((intervened.fitness - natural.fitness) - analytic_delta) < 1e-12,
                "suppressed_hits": intervened.suppressed_hits,
            }
        )

    passed = all(
        c["stream_unchanged"]
        and c["single_bit_is_target"]
        and c["bits_match_clear"]
        and c["fitness_matches_clear"]
        and c["delta_matches_analytic"]
        and c["suppressed_hits"] == 1
        for c in checks
    )
    return {"gate": "B_intervention_minimality", "passed": passed, "checks": checks}


def gate_b_selection(seed: int = 8, generations: int = 40, eps: float = 0.4) -> dict:
    """Minimality must also hold when selection is active."""

    env = build_env(eps)
    natural = run_tape(seed=seed, generations=generations, env=env)
    present = sorted(natural.mutation_ids())
    if not present:
        return {"gate": "B_selection_minimality", "passed": False, "reason": "no accepted events"}
    target = present[0]
    intervened = run_tape(seed=seed, generations=generations, env=env, suppress=frozenset({target}))
    return {
        "gate": "B_selection_minimality",
        "passed": natural.rng_digest == intervened.rng_digest and intervened.suppressed_hits >= 1,
        "target": target,
        "stream_unchanged": natural.rng_digest == intervened.rng_digest,
        "suppressed_hits": intervened.suppressed_hits,
        "natural_fitness": natural.fitness,
        "intervened_fitness": intervened.fitness,
    }


def gate_d(seeds: tuple[int, ...] = (0, 1, 2, 3, 4, 5), generations: int = 40) -> dict:
    """Perturbed seeds must produce genuinely different tapes."""

    env = build_env(0.2)
    digests = {}
    for seed in seeds:
        tape = run_tape(seed=seed, generations=generations, env=env)
        digests[seed] = tape.digest()
    unique = len(set(digests.values()))
    return {
        "gate": "D_perturbed_seed_inequality",
        "passed": unique == len(seeds),
        "unique_digests": unique,
        "n_seeds": len(seeds),
    }


def main() -> int:
    report = {
        "gate_a": gate_a(),
        "gate_b_neutral": gate_b(),
        "gate_b_selection": gate_b_selection(),
        "gate_c": gate_c(),
        "gate_d": gate_d(),
    }
    report["all_passed"] = all(
        report[key]["passed"] for key in ("gate_a", "gate_b_neutral", "gate_b_selection", "gate_c", "gate_d")
    )
    out = RESULTS / "harness_gates.json"
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print(json.dumps(report, indent=2)[:4000], flush=True)
    print("HARNESS_GATES_OK" if report["all_passed"] else "HARNESS_GATES_FAIL", flush=True)
    return 0 if report["all_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
