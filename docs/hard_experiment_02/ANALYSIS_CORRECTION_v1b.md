# HE02 analysis correction v1b

Product: CodonTrace Genesis `0.3.0b4.dev0`.
Source artifact: [`results_v1.json`](results_v1.json) (digest
`45741d911facd4eae0e7f000c2fcd3873280d4b344d3266c4fab9fbe28295419`).
Corrected contrasts: [`analysis_v1b_contrasts.json`](analysis_v1b_contrasts.json).

## Bug

`run_hard_experiment_02` called `paired_effect_size(lefts, rights)`.
The library function takes a single sequence of paired *deltas*.
The `TypeError` was swallowed by a bare `except Exception`, so every
research contrast was stored as `dz=None`, `p_raw=None`, `p_holm=None`.
The committed seed-level ATP values were not wrong. The summary was.

## Reanalysis (same 30 seeds, primary = receiver ATP)

| Contrast | n | dz | p_raw | p_holm |
|---|---:|---:|---:|---:|
| treatment vs `content_null` | 30 | 1.1294 | 5.0e-5 | 1.5e-4 |
| treatment vs `channel_off` | 30 | 1.1294 | 5.0e-5 | 1.5e-4 |
| treatment vs `capsules_shuffled` | 30 | 0.1954 | 0.366 | 0.366 |

Mean ATP: treatment 44.533, content_null = channel_off = activity_matched = 44.000,
shuffled 44.417, oracle 44.933. Delta vs off is +0.533 ATP on a 44 baseline
(about one percent). content_null and channel_off ATP series are identical,
so those two contrasts are the same test twice.

## ClaimGate

Ceiling stays **`runtime_observation`**.

- Holm survives vs off/null because variance is a 0 / 0.5 / 1.0 grid, not
  because a large ecological effect appeared.
- Holm does **not** survive vs `capsules_shuffled`. Information-content
  control is not separated from treatment.
- Decision rule therefore still fails (`information_control_not_separated`).
- No `intervention_supported`. No intelligence / CI / Avida-replacement.

`results_v1.json` seed records stay frozen. Do not treat the original null
`dz` fields as a scientific null.
