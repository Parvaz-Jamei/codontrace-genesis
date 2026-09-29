"""R2 red-team probe: agent-substrate resolution and cost."""
from __future__ import annotations

import time

import numpy as np

from harness import agent_outcome, run_tape

from codontrace.genome import SemanticGenome

rng = np.random.default_rng(0)
# resolution probe: sample random genomes, count distinct outcomes
vals = []
for _ in range(200):
    codons = ["".join(str(int(b)) for b in rng.integers(0, 2, 3)) for _ in range(6)]
    vals.append(agent_outcome(SemanticGenome.from_codons(codons), steps=8))
vals = np.array(vals)
print(f"steps=8  n=200 unique_outcomes={len(set(np.round(vals,9)))} mean={vals.mean():.4f} sd={vals.std():.4f}")
print("distinct values:", sorted(set(np.round(vals, 9)))[:30])

for steps in (8, 24):
    t0 = time.perf_counter()
    n = 30 if steps == 8 else 15
    for _ in range(n):
        codons = ["".join(str(int(b)) for b in rng.integers(0, 2, 3)) for _ in range(6)]
        agent_outcome(SemanticGenome.from_codons(codons), steps=steps)
    dt = (time.perf_counter() - t0) / n
    print(f"agent_outcome steps={steps}: {dt*1e3:.2f} ms per call")

# full-tape cost at depth 40 with k suppressed arms (substrate='agent').
t0 = time.perf_counter()
run_tape(seed=1000, generations=10, substrate="agent")
print(f"one agent tape depth=10: {(time.perf_counter()-t0):.2f} s")
