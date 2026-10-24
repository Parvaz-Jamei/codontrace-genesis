# Identified effects vs. engine reruns, and replay decomposition

Regenerate with `python docs/experiments/2026-10-21/causal_validation/run_validation.py`
(about 55-70 s). `result.json` records the commit, version and Python it ran on.

## Design

Engine: `GenesisRuntimeProfile.life_loop_world`, 12 ticks, unmodified.
Variables: `env:population` (founding population 4 or 8), `bit:1` (focal
founder-genome bit), `bit:2` (background bit), `event:births` (number of
birth events). `do(bit:i = b)` edits the founders that carry the preset's
primary genome and reruns the engine with the same seed.

Observational sample: each unit draws a seed (0-7), an environment and a
background from `RNGManager`; the focal bit is then assigned with
P(bit:1 = 1 | env, bg) = 0.2, 0.3, 0.6, 0.85, so the focal bit is confounded
with both. The assumed diagram is `env -> bit:1`, `bit:2 -> bit:1`,
`env -> births`, `bit:2 -> births`, `bit:1 -> births`.

ID returns the back-door formula
`sum_{bit:2, env} P(bit:2) P(env) P(births | bit:1, bit:2, env)`; it is
estimated by plug-in on the sample, with a 400-draw bootstrap interval. The
ground truth is the mean of the *same* units rerun under `do(bit:1 = 0)` and
`do(bit:1 = 1)`.

## Result (`result.json`, three assignment seeds, 400 units each)

| assignment seed | identified ATE [95% bootstrap] | rerun ATE (truth) | naive contrast |
|---|---|---|---|
| 0 | 5.23 [4.76, 5.75] | 5.15 | 8.75 |
| 1 | 4.80 [4.25, 5.34] | 4.72 | 9.07 |
| 2 | 4.73 [4.13, 5.27] | 4.89 | 9.44 |

The identified estimate covers the rerun truth every time; the naive
contrast is outside every interval. With the environment unrecorded the
diagram has `bit:1 <-> births` and ID reports the effect as not identifiable
(a hedge); no number is produced.

## Contingency vs. selection

Histories are the two backgrounds (`bit:2 = 0/1`), the treatment is
`do(bit:1)`, and the replicates are eight engine seeds. In both environments
the focal bit has no effect on the `bit:2 = 0` background and a large one on
`bit:2 = 1` (potentiation). The interaction is significant (permutation
p = 0.0005, 1999 permutations), so the verdict is `historically_contingent`;
chance explains under 0.3% of the variance.

Scope: one preset, a 12-tick horizon, two bits. This is a validation of the
identification machinery against the engine's own interventions, not a claim
about biological evolution.
