# RQ-1 exclusions

Every item below is excluded from the RQ-1 primary analysis, and the reason is
recorded. Nothing was silently dropped.

| # | Item | Where it appears | Why it is excluded |
|---|---|---|---|
| 1 | Live engine cells, seeds 301 and 302, generations 8, population 4 | `raw/probe_engine_antagonist.json`, `raw/events.jsonl`, `raw/population.jsonl` | They are a **host-lineage census**. `hypothesis_test_eligible=false`, `parasite_is_genotype_population=false`. Raw evidence of the missing precondition, not RQ-1 data. |
| 2 | Idea-2 antagonist counter (`parasite_end`, `parasite_series_tail`) | `raw/probe_engine_antagonist.json` | A capped scalar counter with no genotype, reproduction or death of its own. It is not an antagonist population and carries no contact information. |
| 3 | `HostParasiteWorld` allele-exact cross-time matrix, seeds 11 and 22 | `raw/probe_cross_time_matrix.json` → `matrix_allele_exact` | Allele-exact (or feature) match rate is the time-shift witness's own currency. It is not ATP pressure and has no contact cost, so it is not `π_realised`. Its values are 0.41–0.56 regardless of the time gap. |
| 4 | `HostParasiteWorld` affinity-derived matrix, seeds 11 and 22 | `raw/probe_cross_time_matrix.json` → `matrix_affinity_pi` | Computed on `compact[:6]` windows **invented by this probe**. The live model defines no recognition window and no graded-affinity ATP debit, so this matrix is the analysis kernel applied to an imposed definition. It is not the model's pressure. |
| 5 | Live per-generation records with contact fields null | `raw/events.jsonl` | They carry `contact_edge_id`, `opportunity`, `matched`, `intended_debit`, `realised_debit`, `antagonist_digest` as defined nulls with an explicit `*_null_reason`. They are precondition evidence, not contact events. |
| 6 | The `directional_increase` fixture (arms race) | `raw/stage0_fixtures.json` | Not excluded from the pack — it is the **pre-declared refutation shape** for a uniform increase. Its near-zero interaction (+0.011) is recorded and it is not counted as support. |
| 7 | The Idea-4 checkpoint cell | `raw/probe_checkpoint_fork.json` | Used only to read `checkpoint_fork_complete`, `parent_child_ids_recorded` and the `RunCheckpoint` field list. No RQ-1 effect is taken from it. |

## Seeds

* Used for probe/precondition evidence only: live engine `301, 302`; abstract
  world histories `11, 22`.
* Reserved and **not drawn**: `901, 902, 903, 904, 905, 906, 907, 908`.
* No seed was chosen or dropped on the basis of a result. There was no RQ-1
  result to be influenced by.

## Thresholds

The program's locked `0.20` and `−0.148` were neither recomputed nor changed.
They are not used as RQ-1 acceptance thresholds; RQ-1's decision rule is the
ordinal rule in `design.md` §6.

## Superseding note (round 2)

The paragraph above applied to the **instrument-only** pack, before a live route
was found. In round 2 the live RQ-1 pilot ran on `StructuralRQArm` (6 seeds × 3
arms × 40 generations) and supersedes the `BLOCKED_MEASUREMENT` narrative: the
required inputs exist on that route. The live-run exclusions that now apply are
recorded in `analysis_live.json` → `exclusions`, plus:

* the **smoke-phase** run (`logs/live_smoke.txt`) is not the recorded run — it
  used the full 40-generation configuration because `RQ1_SMOKE` carried a
  trailing space, and its generation-0 gate wrongly compared the arm name as
  part of the state. It is retained as raw evidence only.
* the confirmatory stage (8 reserved unseen seeds) is **not run**; the pilot
  yields `INCONCLUSIVE`, and no confirmatory seed was drawn or inspected.
* `probe_engine_antagonist` and `probe_checkpoint_fork` remain valid evidence
  about the **Idea-2 engine** route, but they no longer carry the RQ-1 verdict.

The instruments' locked constants `0.20` and `−0.148` remain unused and
unchanged.

## Protocol ladder actually run (round 2)

Calibration (2 seeds × 40 generations) then pilot (4 further seeds × 40
generations) on the live `StructuralRQArm` route, 3 arms each. 40 generations is
inside the program's ceilings (80 / 150 / 200) and was chosen by measured cost
(~2.3 s per arm-generation) before any result was read, to keep each seed under
the 8-minute per-test cap and the pack under the 45-minute cap. The confirmatory
stage (8 locked unseen seeds) was **not** started: the budget did not fund it and
a pilot cannot promote itself to `SUPPORTED_IN_MODEL`. Pack wall was 2041 s
(34 min) with a 480 s per-test cap. No wall-time or memory cap was exceeded.
