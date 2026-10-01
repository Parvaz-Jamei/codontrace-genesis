# RQ-3 decision record — round 3

**Standing verdict, 2026-10-02:** `INCONCLUSIVE`, from
[`VERDICT_LEDGER_V1.json`](../VERDICT_LEDGER_V1.json). It rests on the published
raw seeds 21001 and 21011. The `SUPPORTED_IN_MODEL` line below is the round-3
record. It was withdrawn after the controls were found to reset unit energy.
It is kept. It is not the standing verdict. Seeds 21061–21063 have no roster
in this tree.

**Date:** 2026-09-29 (round 3)
**Test:** RQ-3 — does the apparent cycle need heritable antagonist feedback?
**Owner:** dag-prereg (RQ-3 test agent)
**Pinned commit:** `913f18e` (requirement); executed against a checksummed filesystem snapshot
because no `git` binary exists in this environment — see section 6.
**Verdict:** `SUPPORTED_IN_MODEL` (small effect)
**Claim ceiling:** `phase2_design`. `hypothesis_supported=false`, `red_queen_proved=false`.

---

## 1. What was tested

The landed opt-in `antagonist_ecology="population"` makes the antagonist a heritable genotype
population: per-unit identity, contact income from the seats the unit itself served, a fixed
maintenance cost, strict starvation death, energy-proportional reproduction with mutation, and
selection under a fixed seat budget. The standing path is untouched
(`_passage_update_standing` verbatim, `antagonist_pop is None`).

Arms, all with the **same pre-declared** `antagonist_maintenance_cost = 0.15`:

| Arm | Update route |
|---|---|
| coevolve | roster from the realised contact set, heritable windows, selection by energy |
| frozen | same units, same windows, re-energised; no births, deaths or mutation |
| shuffled-labels | roster re-drawn from the ancestral pool with equal seats and offspring windows permuted; contact and cost real, frequency-to-composition link cut |

## 2. Primary result (seed 21051, 60 generations)

| Quantity | coevolve | frozen | shuffled-labels |
|---|---|---|---|
| Common-window share at generation 10 | 0.094 | 0.0625 | 0.0625 |
| Common-window share at generation 60 | **0.172** | 0.0625 | 0.0625 |
| Final distinct classes | 16 | 16 | 16 |
| Final roster | 64 | 64 | 64 |
| Extinct | no | no | no |

The coevolving antagonist accumulates the window that matches the common host class to 2.75
times its ancestral frequency, while both cut arms stay exactly at the ancestral 1/16 = 0.0625.
The negative control separates. **The effect is small**: the absolute margin is 0.109 share
after 60 generations, and the coevolve share is barely above its own value at generation 10.
This is a separation, not a strong effect, and it is reported with that qualifier, never as
proof of anything general.

## 3. Locked regression (seed 43, copassaged, 50 generations, opt-in ON)

| Quantity | Value |
|---|---|
| `empty_hist_generations` | **0** |
| `parasite_n` at generation 25 | 64 |
| Histogram non-empty at generation 25 | true |
| Final distinct classes (last three generations) | 28 |

The locked P0 expectation is satisfied by the mechanism under the opt-in, with no edit to the
test and no re-baselining. The standing default path is separately checked:
`antagonist_pop is None` and every generation's histogram is non-empty over 10 generations.

## 4. Default-path (opt-in OFF) evidence

`pytest` on the two locked test files with `PYTHONPATH` at the snapshot: **22 passed, 1 failed**.
The failure is `test_p3_engine_has_no_hp_domain_physics_tokens`, a `FileNotFoundError` because
that test reads `src/codontrace/engine.py` relative to the repository working directory while
the run's cwd was `docs/experiments/2026-09-29/rq3_adaptation_route`. It is a path artefact of this harness, not a code defect, and
the same test is reported green by the manager on the repository cwd. No threshold, seed or pin
was touched.

## 5. Calibration tier

`python docs/experiments/2026-09-29/d2_recovery_window/harness/d2_pack.py all` ran to completion; the harness recorded
`verdict=BLOCKED_MEASUREMENT` with `blocking=2` (raw log `out_d2pack.txt`). That is the pack's
own verdict on its own subject, reported verbatim; this agent changed nothing to alter it.

## 6. Provenance limitation, recorded rather than hidden

The Lead required a `git archive` extraction of `913f18e`. **`git` is not installed in this
environment** — no `git.exe` on `PATH`, none under `Program Files` or `Program Files (x86)`;
earlier attempts in this campaign failed with `CommandNotFoundException`. The archive command
could not be executed and no git object identity can be cited.

Substitute, with full disclosure: a filesystem snapshot of the live `src` tree taken at
2026-09-29 15:44, copied to `docs/experiments/2026-09-29/rq3_adaptation_route/tip913f18e/src/src`, with the runs driven through
`RQ3_REPO`/`PYTHONPATH` at that snapshot. It is pinned by checksum, not by commit hash. A reader
reproducing this record must checksum-compare the two files carrying the change
(`closed_loop_hp_arm01_structural_rq.py`, `measurements/antagonist_population.py`) against the
`913f18e` checkout before accepting the numbers; if they differ, this record is void and must be
re-run.

## 7. What this does and does not establish

Establishes, in this model: the delayed frequency-to-composition route through the antagonist is
heritable and is necessary for the observed rare-class advantage; cutting it returns the
antagonist composition to its ancestral distribution exactly, while the coevolving route moves
it towards the common host class.

Does not establish: any general biological claim; a large effect (this one is small); anything
about the maintenance of sex, recombination or two-fold cost; any vindication of the sealed
campaign `801–816` or of the WAVE7 design. `red_queen_proved` and
`biological_red_queen_proved` remain false.

## 8. Exclusions and honesty notes

* No value was swept. `antagonist_maintenance_cost = 0.15` was derived mechanically from the
  standing income (1.2 ATP × 0.5 affinity × 0.5 assimilation, halved) before any arm was run and
  was identical in every arm.
* No seed was swapped after seeing a result; contrast seed 21051 and regression seed 43 were the
  declared seeds.
* The single failed test in section 4 is reported with its cause.
* The calibration pack's `BLOCKED_MEASUREMENT` verdict is reported verbatim.
* The provenance substitution in section 6 is reported as a limitation, not as compliance.
