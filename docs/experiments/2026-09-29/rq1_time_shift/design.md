# RQ-1 design (locked before any confirmatory seed)

**Test:** RQ-1 — time-shift with past / present / future antagonist.
**Pack id:** `RQ1-TIME-SHIFT-20260929`
**Base revision under test:** `codontrace-genesis` `main` = `a014ed4d6bce6edbf87664344b371f4af8d32f97`
(read from `.git/refs/heads/main`; the git executable is not on this session's
`PATH`, so the dirty flag is recorded as `null` with that reason, never guessed).
**Locked:** 2026-09-29, before any confirmatory seed was drawn. No confirmatory
seed was run: the stage-0 gate below failed on a precondition.
**Claim ceiling:** instrument + precondition evidence. No discovery is claimed.

## 1. Question

Does the antagonist's realised pressure on a host change with the time gap
between them — contemporary or slightly lagged antagonist against the recently
common host, with a drop on the old host and no uniform increase in every cell —
or is the only structure a directional (arms-race) increase?

## 2. Unit of replication

One **independent population history**, never an organism or a generation. In one
seed, arms start from the same initial state or fork point; after an
intervention the arms use independent, replayable, labelled RNG streams. No arm
may get an advantage in seed choice or tuning.

## 3. Inputs

Three host snapshots and three antagonist snapshots of the **same dated
history**, at `t - lag`, `t`, `t + lag`. The matrix is built **outside
evolution**: snapshots are frozen and the contact assay is applied to them, not
nine full simulations. Contact opportunity and resources are equal in every cell
(`contact_mode="full_matrix"`, one contact opportunity per host class, the same
per-host reserve in every cell).

## 4. Primary quantity

`π_realised(h, a)` in ATP per host per generation, from the repository's
measurement kernel
(`codontrace.genesis.measurements.rq_frequency_clocks.realised_conditional_host_pressure`):
graded affinity over the 3-sub-locus × 2-bit recognition window, `κ = virulence ×
steal_fraction = 1.2`, per-contact debit capped at the host's reserve.

The primary outcome is the **host-time × antagonist-time interaction contrast**

    I(h, a) = π(h, a) − row_mean(h) − col_mean(a) + grand_mean

summarised by two pre-declared scalars:

* `I_contemp = I(now, now)`
* `I_lag = mean(I(now, past), I(future, now))`

A frequency change alone is **not** the primary outcome. A uniform increase in
every cell is a main effect (arms race), not an interaction; it must not be read
as fluctuating selection.

## 5. Arms

| Arm | Definition |
|---|---|
| coevolve | host and antagonist snapshots from the dated history |
| frozen antagonist | antagonist label held at one time slice in every cell |
| host-only | no antagonist classes; π_realised is 0 in every cell |
| shuffled time labels | random rotation of antagonist time labels (6 permutations) |

## 6. Pre-declared decision rule

Support for fluctuating selection requires **all** of:

1. the matrix receives the repository's `contemporary_match` or `lagged_match`
   label, and
2. `I_contemp > 0` or `I_lag > 0`, and
3. `max |I|` falls on a contemporary or lagged cell, and
4. `uniform_increase` is false, and
5. the same pattern does **not** appear under the frozen, host-only or rotated
   label controls.

Refusal (falsified in model): the same pattern appears under frozen or shuffled
labels, or there is no fitness/lineage difference despite the matrix sign.

No effect, an interval containing zero, or too few events → `INCONCLUSIVE`.
A missing input or missing fork → `BLOCKED_MEASUREMENT` with the exact missing
precondition and raw evidence.

## 7. Locked thresholds

The program's `0.20` and `−0.148` locks are **not** used as RQ-1 acceptance
thresholds and are not changed here. RQ-1's primary outcome is an interaction
contrast, and its decision rule in §6 is ordinal and pre-declared.

## 8. Stage 0 (mandatory before any population run)

Unit and property tests; two or three hand-computed cases; energy and population
invariants; byte-identical replay; a neutral control; a pre-defined mechanism
positive control; and a negative control that must remove the effect. An
injected positive is not a discovery.

Concretely: the repository's own stage-0 module is re-run
(`tests/campaigns/discovery_questions_20260928/test_discovery_program_stage0.py`
plus `tests/campaigns/open_problem_20260925/test_time_shift_open_problem.py`),
the four pre-registered fixture matrices are pushed through the interaction
contrast, the six-permutation label null is computed, and replay determinism is
checked on the engine, the abstract world and the measurement kernel.

## 9. Seeds and horizon

* Calibration: 2 development seeds × ≤ 80 generations.
* Pilot: 4 further seeds × ≤ 150 generations.
* Confirmatory: 8 locked, unseen seeds × ≤ 200 generations — **only if** the
  stage-0 gate and the pilot gate are healthy.

Reserved unseen confirmatory seeds, not drawn:
`901, 902, 903, 904, 905, 906, 907, 908`.
Randomisation seed `20260929`; cluster-bootstrap seed `20260928`.
Probe-only seeds actually used here: live engine `301, 302`; abstract-world
histories `11, 22`. Numbers are ceilings; if events are rare the result is
low-power and unclear, and extending the horizon needs a fresh design and budget
locked before seeing holdout.

## 10. Budget

Measure one seed's wall time first and record it in the manifest. Caps: 8
minutes wall per test, 45 minutes for the first pack, target memory 4 GiB with a
soft stop at 3.5 GiB and a checkpoint. If the real cost is higher, reduce scope
before seeing results.

## 11. Early stop

Only on: invariant violation, no heritable variation, zero contacts or zero
frequency, arm mismatch before the intervention, checkpoint or replay
corruption, incomplete data, or going over budget. Never stop because the result
is unwelcome; report no effect.

## 12. Outputs

Append-and-flush raw events per generation to JSONL; summary every 10
generations; snapshot every 25. `run_manifest.json` holds commit and dirty flag,
config and design hashes, schema version, seed and RNG streams, wall/CPU/RAM,
stop code, parent snapshot id, parameters and arm name. `events.jsonl` carries
the program's field list with defined nulls. `analysis.json` is derived from raw
only. Every file gets a checksum. One replay command from the manifest
reproduces the summary.

## 13. Deliverables of this pack

`prior_art.md`, this locked `design.md`, raw events, manifest, derived summary,
replay script, effect and interval table, negative controls, exclusions, and
`decision.md` holding exactly one of `SUPPORTED_IN_MODEL`, `FALSIFIED_IN_MODEL`,
`INCONCLUSIVE`, `BLOCKED_MEASUREMENT`.

## 14. Live route (pre-declared before the recorded run)

The dated history is produced by `StructuralRQArm`
(`src/codontrace/genesis/closed_loop_hp_arm01_structural_rq.py`), a live
life-loop host/antagonist coevolutionary arm:

* host match windows are genomes under a bit-flip mutation regime;
* the antagonist is a stock of 64 recognition windows, partly kept
  (`parasite_keep_fraction = 0.5`) and partly re-drawn each generation from that
  generation's **matched** windows and mutated (`parasite_mutation = 0.25`) —
  heritable, mutating, selected;
* `fixed` restores the ancestral 16-window cycle each generation (frozen
  antagonist control); `avirulent` empties the stock (host-only control);
* `window_snapshot(generation)` exposes the host joint match class frequencies,
  the antagonist class frequencies, and the realised pressure per host class.

Class strings `"aa|bb|cc"` map 1:1 onto the 6-bit recognition window `aabbcc`,
so the archived class tables are genotype tables.

**Assay.** Three slots `past = t-10`, `now = t`, `future = t+10` with
`t = 30`, `lag = 10`, on a 40-generation history. For each cell `(ti, tj)`:

    pi_cell(ti, tj) = sum_h w_h(ti) * mean_{a in A(tj)} pi(h, a)
    pi(h, a)        = min(R, kappa * A(h, a)),  kappa = 1.2  (R = infinity primary)

with `contact_mode = "full_matrix"` (equal exposure: every host class meets every
antagonist class once), equal `kappa`, and equal reserve. Secondary variant: the
dominant host class at `ti` instead of the frequency-weighted mean; a capped
variant at `R = 1.2` ATP is reported as a robustness check. The matrix is built
outside evolution; the arm is not advanced during the assay.

**Arms.** `copassaged` (coevolve) is the test arm; `fixed` (frozen antagonist)
and `avirulent` (host-only) are the pre-declared negative controls; the shuffled
time-label control is the six permutations of the antagonist time labels.
All three arms boot from the same seed and the same initial state (verified:
identical founder genome digest and identical initial parasite-window digest
across arms) with per-arm labelled RNG namespaces.

**Budget (measured, then reduced before seeing results).** Measured cost
~1.6-2.3 s per arm per generation. Each seed runs 3 arms x 40 generations
(about 3-5 min, under the 8-minute per-test cap). This pack is **calibration
(2 seeds) plus pilot (4 further seeds)**, about 19-30 minutes, under the
45-minute first-pack cap. The confirmatory stage (8 locked unseen seeds,
reserved `5701`-`5708`) is **not** funded by this pack and requires a fresh
budget locked before holdout. 40 generations is inside the program's ceilings
(80 calibration, 150 pilot, 200 confirmatory); the reduction is a scope
reduction made before results, as the program permits.

**Gates before the pilot.** Host classes >= 2, antagonist classes >= 2,
zero contacts and zero census ruled out at every slot, and the three arms
identical at generation 0. A failed calibration gate stops the pilot.

**Verdict mapping.** `SUPPORTED_IN_MODEL` is reserved for the eight-seed locked
confirmatory run. A pilot therefore yields `FALSIFIED_IN_MODEL` (the frozen or
shuffled control reproduces the pattern, or the sign is absent) or
`INCONCLUSIVE` (pattern not consistent, or the seed-level interval contains
zero). No threshold, parameter or seed is tuned to change this.
