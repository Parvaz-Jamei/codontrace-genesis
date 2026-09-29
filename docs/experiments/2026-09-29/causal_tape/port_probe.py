"""Probe: does the engine-native substrate respond to accumulated mutations?"""

from __future__ import annotations

import numpy as np

from harness import agent_outcome, run_tape

GENOMES = {
    "all-wait": ["000", "000", "000", "000"],
    "one-move": ["101", "000", "000", "000"],
    "mixed": ["111", "101", "011", "000"],
}

for name, codons in GENOMES.items():
    from codontrace.genome import SemanticGenome

    print(f"{name:>10}: outcome={agent_outcome(SemanticGenome.from_codons(codons)):.6f}", flush=True)

print()
for depth in (10, 20, 40):
    tapes = [run_tape(seed=seed, generations=depth, substrate="agent") for seed in range(0, 30)]
    accepted = [sum(1 for ev in tape.events if ev.accepted) for tape in tapes]
    fitness = np.array([tape.fitness for tape in tapes])
    uniq = len({round(float(value), 9) for value in fitness})
    print(
        f"depth={depth:<3} accepted/total={sum(accepted):<4} "
        f"seeds_with_any={sum(1 for a in accepted if a):<3} "
        f"fitness mean={fitness.mean():.4f} sd={fitness.std():.4f} unique={uniq}",
        flush=True,
    )
