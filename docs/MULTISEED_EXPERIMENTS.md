# Multi-Seed Experiments

Multi-seed runs are the minimum boundary between deterministic smoke tests and scientific comparisons.

## Modes

`reproducibility` mode checks that the same seed/config/backend schedule produces the same digest. `evolutionary_variation` mode allows mutation/stochastic variation and reports distributions across seeds.

## Statistical policy

Seed-count policy is explicit:

- n < 8: descriptive only
- 8 <= n < 16: exploratory
- 16 <= n < 30: preliminary benchmark
- n >= 30: research-grade benchmark candidate

No claim passes on p-value alone. Evidence must include effect size, paired-seed deltas, confidence interval, replay artifact, protocol digest, and ClaimGate decision.

## Artifacts

Each seed has a manifest, replay digest, summary, QD digest, and optional discovery/capsule/causal records. Aggregate reports include mean, std, min/max, success/extinction rates, and claim ceilings.

## Limitations

Multi-seed statistics can support candidates, not proofs of artificial life or unbounded OEE.
