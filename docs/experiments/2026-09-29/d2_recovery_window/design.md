# D-2 design — locked before the confirmatory seed

**Agent:** D-2 test agent (`mechanism-test`) · **Date:** 2026-09-29 · **Round:** 1
**Program:** `DISCOVERY_TEST_PROGRAM_2026-09-29_FA.md`, package B, D-2 (idea 4)
**Design digest:** `IDEA4_PHASE2_DESIGN_DIGEST.md` (sealed phase-2 design; this file does not revise it)
**Claim ceiling:** `phase2_design`. `hypothesis_supported` and `red_queen_proved` stay `false`.

This file is written **before** any confirmatory seed is run. It locks the question, the arms,
the two versioned endpoints, the refusal conditions, the calibration ceilings, the statistics and
the stop rules. Nothing here moves after a result is seen.

## 1. Question

From three early/middle/late checkpoints of one history, does a complete fork plus a
pre-registered contact intervention change (a) the retention of the functional innovation
`FI-RARECLASS-CONTACT-YIELD-V1` and (b) its recovery time and lineage paths — and is any such
change mediated by **contact structure** rather than by a global cost penalty?

## 2. Unit of replication

The independent population **history** is the unit: one seed, one checkpoint time, one arm.
Within a seed, all arms start from the *same fork point*; after the intervention each arm runs on
its own labelled, replayable RNG stream. No arm gets an advantage in seed choice or tuning.
Contact pairs, generations and class-generation pairs are never `N`.

## 3. Two endpoints, versioned separately (never pooled)

| Endpoint | ID | Date | Rule | Role |
|---|---|---|---|---|
| Competence | `FI-RARECLASS-CONTACT-YIELD-V1` | 2026-09-28 | mean rare-class contact yield ≥ **1.25×** the run's own pre-checkpoint baseline, sustained for ≥ **3 consecutive** generation boundaries within `T = 40` | pre-registered |
| Digest return | `GENOME-DIGEST-LOST-THEN-REGAINED-V1` | 2026-09-29 | a checkpoint genome digest disappears and is present again later | exploratory; reported separately, never merged with the row above |

An analyst may not use the digest-return endpoint as a substitute for the competence endpoint, and
a row that carries only one of the two is labelled with that ID.

## 4. Arms (applied at the checkpoint boundary, `CKPT-RELOCATE-RECOVERY-TOKEN-V1` first)

1. `control` — checkpoint only (neutral control).
2. `cut_named_scaffold` — cut `SCAF-CONTACT-SRC-PATH-V1` membership (`E0`, `E1`).
3. `cut_matched_random` — cut `E6`, `E7`: the planted mirror with equal edge count, degree and
   ATP (the independent-rewiring control).
4. `scramble_contacts` — degree-preserving rewiring.
5. `ablate_knowledge_digest` — remove `digest:pred_fail:smoke_v1` (negative control).
6. `sham` — relocate the token with no other change.

Locked facts about (3) already recorded in the repository and measured here: on this revision
`match_exact = true`, `independent_control = false`, `scientific_contrast_eligible = false`,
`design_failure = true`; the mirror is a code check, not a scientific control. If it stays
indistinguishable from (2), the Combo-E contrast dies (design digest falsifier 3).

## 5. Locked thresholds and guards (unchanged by this pack)

* success multiplier `1.25×`, consecutive boundaries `3`, horizon `T = 40`, `t̃` grid `{10,20,30}/40`;
* window slope `≥ 0.15`, ecology/knowledge margin `|ΔP| ≥ 0.20` (carried, not re-fitted);
* budget: ≤ 8 min wall per test, ≤ 45 min for the pack, one worker, RAM soft stop 3.5 GiB;
* calibration ceilings: two development seeds × ≤ 80 generations; pilot four seeds × ≤ 150;
  confirmatory eight locked unseen seeds × ≤ 200 — each tier only if the previous gate is healthy.

## 6. Refusal conditions (locked; a fired refusal blocks the window claim)

* **R1** named and rewired arms have identical realised contacts **and** identical population
  trajectory;
* **R2** the only difference between arms is the coupler's fixed global edge-cost penalty
  (`n_edge_changes × 0.35` plus the matching food term);
* **R3** the pre-registered endpoint never reaches 1.25× in any arm and the control arm has no
  observed recovery opportunity (a flat-zero curve does not test a window law).

## 7. Falsifiers

| Observation | Reading |
|---|---|
| `named ≈ matched` on recovery and on population path | Combo E dies; mediation by contact structure not identified |
| All arm differences equal the count penalty | global cost, not topology |
| Recovery only from the injected positive control | instrument check, **not** a discovery |
| `class=rare` mapped to a genotype class | class-shortcut FAIL |
| Infection physics or domain RNG opened in `engine.py` | design FAIL, discard |

## 8. Statistics

Paired seed-level effect with an exact sign-flip randomisation interval, or a cluster bootstrap
over histories when the number of pairs allows; effect size reported separately from extinction
and censoring; an interval containing zero is **inconclusive**, not a success. With two
development seeds the minimum attainable two-sided p is 0.5, so the calibration tier can only
produce an inconclusive statement and is labelled as such.

## 9. Stop rules (applied exactly)

Early stop only on: invariant violation, no heritable variation, zero contacts or zero frequency,
arm mismatch before the intervention, checkpoint/replay corruption, incomplete data, or over
budget. Never because the result is unwelcome. A cut run keeps its valid prefix and records an
`INCOMPLETE`/stop-coded manifest.

## 10. Deliverables of this pack

`prior_art.md`, this `design.md`, `raw/<run>/events.jsonl`, `raw/<run>/population.jsonl`,
`raw/<run>/run_manifest.json`, checksums, `stage0_report.json`, `patch_evidence.json`,
`analysis.json`, `harness/d2_replay.py`, `decision.md`, and `PROPOSED_CHANGE.patch` plus
`NOTE_TO_MANAGER.md` for any blocking defect.

## 11. Round-1 status of the two preconditions

Both preconditions named by stage 0 fail on the live revision, and both have an unblocking patch
with computational evidence (`patch_evidence.json`, `NOTE_TO_MANAGER.md`):

* no full fork at a generation boundary (state + RNG + parent/child) — fixed by
  `capture_fork()/from_fork()`; restored continuation verified byte-identical;
* topology not identified — fixed by `incident_endpoints_realised`; named vs matched now differ,
  with the count penalty held at zero.

Per owner policy the verdict is `BLOCKED_MEASUREMENT` **with the patch attached**, and the
confirmatory tier stays closed until the patch lands and the pack is re-run.
