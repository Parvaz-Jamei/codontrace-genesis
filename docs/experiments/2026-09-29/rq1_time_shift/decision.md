# RQ-1 decision

**Test:** RQ-1 — time-shift with past / present / future antagonist.
**Pack id:** `RQ1-TIME-SHIFT-20260929` · **Round:** 2
**Base revision:** `codontrace-genesis` `main` = `a014ed4d6bce6edbf87664344b371f4af8d32f97`
**Raw evidence:** `raw/live_run.json`, `raw/live_events.jsonl`,
`raw/live_population.jsonl`, `raw/feasibility_structural.json`,
`raw/probe_*.json`, `raw/stage0_fixtures.json`
**Derived summary:** `analysis_live.json`, `analysis.json`, `effect_table.json`

## Decision

`INCONCLUSIVE`

## What was run

A live RQ-1 pack on `StructuralRQArm` (a live life-loop host/antagonist
coevolutionary arm whose antagonist is a heritable, mutating, selected 64-window
genotype stock), not a hand fixture:

* **6 independent population histories** (seeds 5501, 5502 calibration;
  5601–5604 pilot) × **3 arms** (`copassaged` coevolve, `fixed` frozen
  antagonist, `avirulent` host-only) × **40 generations**;
* the 3×3 cross-time π_realised matrix built **outside evolution** from the
  archived per-generation class tables with equal exposure (`full_matrix`),
  equal κ = 1.2 and equal reserve, slots `past=20`, `now=30`, `future=40`,
  lag = 10 (`raw/live_run.json`);
* wall 2041 s for the pack (34 min < 45 min cap); ~2.3 s per arm-generation;
  each seed ≈ 5 min < 8 min per-test cap.

**Gates, all healthy.** Calibration gate passed; pilot gate passed; the three
arms boot from the identical initial state for every seed (identical founder
genome digest `250879f3…` and identical initial parasite-window digest
`28e18a5d…` across arms); no zero-census, zero-antagonist or zero-variation slot
(host classes 18–35, antagonist classes 16–36, census 21–55, antagonist n = 64);
every stored contrast reproduces from the raw matrices
(`analysis_live.json` → `integrity.all_stored_contrasts_match_recompute = true`).

## Result

| arm | labels over 6 seeds | `I_contemp` mean [95% run-level bootstrap] | `I_lag` mean [95%] | supports |
|---|---|---|---|---|
| copassaged (coevolve) | `lagged_match`, `contemporary_match`, `other` ×4 | **+0.005396** [+0.003430, +0.007602] | **−0.003454** [−0.005321, −0.001438] | 0/6 |
| fixed (frozen antagonist) | `flat` ×6 | 0.0 [0, 0] | 0.0 [0, 0] | 0/6 |
| avirulent (host-only) | `flat` ×6 | 0.0 [0, 0] | 0.0 [0, 0] | 0/6 |

Rotation control (shuffled antagonist time labels): **0 of 18** permutations
receive a support label.

## Why `INCONCLUSIVE` and not supported

The pre-declared decision rule (`design.md` §6) requires the matrix to receive
the repository's `contemporary_match` or `lagged_match` label **and** a positive
contemporary or lagged interaction **and** the maximum interaction on a
contemporary/lagged cell. The observed pattern satisfies only part of it:

* `I_contemp` is small but consistently **positive** and its seed-level interval
  excludes zero — the diagonal (contemporary) interaction is real at this
  resolution;
* but the label is `contemporary_match`/`lagged_match` in only **2 of 6** seeds
  (4 seeds label `other`), and `I_lag` is consistently **negative**, so the
  pre-declared full pattern does not hold;
* `n_support = 0/6` under the locked rule.

The refusal branch is **not** triggered: the frozen-antagonist control is exactly
flat (its 16-window ancestral stock gives every host class the same mean
affinity, so the interaction is structurally zero) and the host-only control is
exactly zero, so neither reproduces the pattern; the shuffled-label control is
clean (0/18).

`SUPPORTED_IN_MODEL` is reserved for the eight-seed locked confirmatory run,
which this pack's budget did not fund (the measured cost is ~2.3 s per
arm-generation; eight seeds × three arms × 200 generations ≈ 3.1 h, far beyond
the 45-minute first-pack cap). A pilot cannot promote itself.

## Flags

`hypothesis_supported = false` · `red_queen_proved = false` ·
`arms_race_proved = false` · `population_run = true`.

## What is still missing for a definitive verdict

A fresh budget locked before holdout, funding the eight reserved unseen seeds
(`5701`–`5708`) × 3 arms × a longer horizon, plus a decision on whether the
label-based rule or the interaction-only rule is primary. That is a design
question, not a code defect: **no repository code change is required to run
RQ-1**, and none was made. The previously proposed code draft is withdrawn as
defective (see `PROPOSED_CHANGE_NOTES.md` §1: `HookMeter.record_related_total`
rejects unknown keys at `hook_meters.py:214-219`). The only repository artifact
handed over is the documentation addendum
`docs/campaigns/discovery_questions_20260928/DISCOVERY_PROGRAM_STAGE0_ADDENDUM_20260929_RQ1_ROUTE.md`,
which the manager has landed, recording that the stage-0 `BLOCKED_MEASUREMENT`
statement is route-specific to the Idea-2 engine.
