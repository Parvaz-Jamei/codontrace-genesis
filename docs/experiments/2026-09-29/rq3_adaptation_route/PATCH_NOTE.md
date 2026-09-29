# RQ-3 PROPOSED_CHANGE — handover note

**Round:** 1 (manifest round field is written by `rq3_harness.py`, `ROUND = 1`)
**Patch:** `test-runs/rq3/PROPOSED_CHANGE.patch` (752 lines, unified diff, LF endings only)
**Repository writes by this agent:** none. Everything below was produced inside
`test-runs/rq3/`.

## What the patch contains

| File | Change |
|---|---|
| `src/codontrace/genesis/measurements/antagonist_population.py` | new: per-unit antagonist identity, energy budget, heritable reproduction, starvation death, selection under a seat cap, `ANTAGONIST_PASSAGE_SHUFFLED_LABELS` negative control, `ancestry_rows()` |
| `src/codontrace/genesis/closed_loop_hp_arm01_structural_rq.py` | 12 hunks: import; three new dataclass fields (`antagonist_pop`, `antagonist_ledger`, `contact_pair_records`); `boot_structural` builds the population; `run_generations` passes the served contact seats into `_passage_update` and syncs `parasite_windows`; `_apply_hp_env_contact` records per-pair evidence and resets the round; `_passage_update` delegates to `AntagonistPopulation.advance` and fills `turnover_*` from the ledger; `window_snapshot` exposes `antagonist_units` and `antagonist_ledger` |

`engine.py` is not touched. Every existing public name and field is preserved; the
`turnover_kept` / `turnover_replaced` / `turnover_mut_events` / `turnover_churn` series
keep their names and are filled from the ledger.

## Apply check

`git`, `patch` and `diff` are not installed in this environment (checked
`C:\Program Files\Git\cmd\git.exe`, `C:\Program Files (x86)\Git\cmd\git.exe`,
`C:\Program Files\Git\usr\bin\patch.exe`; all absent), so `git apply --check` could not be
executed here. The patch was verified by two equivalent checks instead, both run by
`test-runs/rq3/verify_patch.py`:

1. **Structural parse and exact context match.** Every hunk header is read; the declared old
   and new line counts are compared against the lines the hunk actually carries; and every
   context and removed line is compared, in order, against the current working tree of the
   target file at its declared offset. Any mismatch raises with the offending line.
   Result: `applied: true`, `compiles: true`, `patched_line_count: 1454`,
   `errors: []` (`out_verify.txt`).
2. **End-to-end functional run of the patched code.** The patched target and the new module
   are loaded from the mirror tree under their real module names, and both arms are run for
   12 generations on seed 21051:

| Arm | Antagonist composition changes | kept | replaced | mutation events | final classes |
|---|---|---|---|---|---|
| copassaged | 11 | 454 | 314 | 133 | 23 |
| fixed | 0 | 768 | 0 | 0 | 16 |

The copassaged antagonist is now a moving, mutating genotype population; the frozen arm is
provably static.

## Energy budget, and why the constant has this value

The first build of the module set maintenance to 0.5 ATP per unit per generation, and the
copassaged antagonist went extinct in 12 generations (`final_classes: 0`). That was a defect
in the patch, not an acceptable result, and it is fixed by derivation rather than by tuning:

* one contact seat at maximum affinity pays `kappa = virulence * steal_fraction = 1.2` ATP;
* the engine realises at most one seat per host per generation, so a generation offers at
  most `seat_cap` seats, and in practice the realised count is the number of hosts `N`;
* a unit that served one maximum-affinity seat assimilates
  `(EARNED_YIELD - PAIRING_COST) * 1.2 = 0.6` ATP;
* `maintenance_cost = 0.05` ATP per generation is therefore covered by about one twelfth of
  one maximum-affinity contact, and a unit that serves no seat starves. The value is
  recorded in the run manifest and must not be chosen after seeing a confirmatory result.

## Isolated functional test of the mechanism and the cut

`test_isolated_module.py` (module loaded from the patch), 40 generations, one common host
class contacted twice per generation and one rare class once:

| Arm | common-window share at generation 1 | at generation 40 | alive at 40 |
|---|---|---|---|
| coevolve | 0.50 | 0.50 | 4 |
| shuffled-labels cut | 0.25 | 0.25 | 4 |
| frozen cut | 0.25 | 0.25 | 4 |

The coevolving population holds the common-matching window at twice the frequency of both
cut arms, the two cuts are indistinguishable from each other, and no arm goes extinct. The
heritable route exists and both cuts remove it.

## Expected effects on the two existing test files

* `tests/closed_loop/test_closed_loop_wave8_lag_fail_fix.py` — expected to keep passing
  unchanged.
  * `test_p3_assert_census_series_len_and_observer_protocol` asserts that
    `host_joint_class_series` and `parasite_class_hist_series` each have length equal to the
    horizon. Both are still appended once per generation in `_census`.
  * `test_p0_window_snapshot_emits_parasite_class_hist` asserts that
    `parasite_class_hist` is non-empty and sums to one, and that
    `parasite_class_hist_lag` has 1–8 entries. `_census` still builds the histogram from
    `parasite_windows`, which is now the roster's window list, so the assertions hold; the
    new `antagonist_units` and `antagonist_ledger` keys are additive.
  * `test_p0_lag_clock_stride_admits_tau_pairs` only reads the lag clock.
  * No test in this file unpacks `_apply_hp_env_contact`, which still returns the same
    2-tuple `(debit_count, matched_windows)`.
* `tests/closed_loop/test_closed_loop_host_realised_pressure.py` — expected to keep passing
  unchanged.
  * `test_arm_records_realised_pressure_only_when_enabled` asserts that a plain arm has
    `host_realised_pressure_series == []`. The collection flag still gates all recording, and
    `contact_pair_records` and `antagonist_ledger` are separate fields, so this holds.
  * `test_arm_records_coevolve_and_frozen_realised_pressure` asserts series length 6 after
    six generations for both arms. `_record_realised_host_pressure` is called exactly as
    before, once per generation, in both arms.
  * `test_recorded_pressure_equals_rule_recomputed_from_recorded_evidence` recomputes pressure
    from the arm's recorded affinity sums, contact counts and availability. Those three series
    are unchanged; `begin_round` only resets `contacts_served` on the antagonist units.
  * `test_parasite_histogram_shares_are_not_pressure_shares` asserts
    `set(hist) == {joint_match_class(w) for w in arm.parasite_windows}`. `parasite_windows` is
    synced from `antagonist_pop.windows()` inside `_passage_update` before `_census`, so the
    histogram is built from exactly that list.
  * The pure-function tests (`realised_conditional_host_pressure`, `affinity_matrix`,
    `lagged_nfds_score`) are untouched.
* One behavioural change the manager should schedule explicitly: after this patch the
  copassaged antagonist is **not** a fixed 16-window cycle. Any test or recorded expectation
  that assumes `parasite_windows` is always the 16 distinct windows on the copassaged arm will
  change. The wave-8 and pressure test files contain no such assertion (they assert
  non-emptiness, sums and class-set equality with the live list), but the structural confirm
  runner and the digest builders were not inspected for it by this agent.

## Locked P0 invariant (the reason round 1 was reverted)

Round 1 was reverted because `test_p0_dense_snaps_parasite_maps_nonempty` failed with
`empty parasite map at gen 25` on the copassaged arm, seed 43, 50 generations. Root cause: the
first build gave each unit a fixed absolute maintenance cost and credited only the units that
served seats, so the roster starved out. The locked expectation is not re-baselined. Three
changes fix the population without touching the test or any threshold:

1. contact income is distributed per **class** (a window's realised take), not per seat, so a
   generation in which a window is not drawn no longer kills that window's units;
2. a starved unit's window is replaced by the same window code, because replacement is a
   different individual, not a re-baselining of the expectation;
3. the cohort is topped back up to the seat budget from the realised contact set, so the
   antagonist pool stays populated while contact continues, which is the substrate's locked
   property and the reason loss of a genotype is recorded separately from extinction of the
   population.

Verified on the exact regression (`verify_patch.py`, `out_verify.txt`, `p0_invariant`):
copassaged seed 43, 50 generations — `hist_at_25_nonempty: true`, 33 classes at generation 25,
`parasite_n_at_25: 64`, `empty_hist_generations: 0`, all 50 generations populated.

## Round-2 open item, declared honestly

The same patch's isolated functional test now shows no measurable heritable adaptation at 40
generations (common-window share 0.25 in every arm), where round 1's build showed 0.75 vs
0.25. The top-up that restores persistence also mixes unsampled contact windows back into the
roster, which dilutes the energy ranking. The patch is therefore correct on the locked
invariant, and the negative-control separation is no longer demonstrated. This agent will not
choose between them by tuning. Either the top-up needs a pre-registered rule that keeps the
energy signal dominant, or persistence should come from the substrate's own opt-in path
(`ecology=persistence_safe`) rather than from inside the population object. The re-run on the
landed code is the next round.

## Mode mapping, confirmed as intended

| Repository passage mode | `advance(mode=...)` | Behaviour |
|---|---|---|
| `PASSAGE_ABSENT` | `"absent"` | roster emptied; no contact; no births, deaths or mutation |
| `PASSAGE_FROZEN` | `"frozen"` | the same units keep the same windows and are re-energised; no births, deaths or mutation |
| `PASSAGE_COEVOLVE` | `"coevolve"` | contact income, mortality, energy-proportional heritable reproduction, seat-cap selection, contact-set top-up |
| anything else (the RQ-3 control) | `ANTAGONIST_PASSAGE_SHUFFLED_LABELS` | roster re-drawn each generation from the ancestral window pool with equal seats and offspring windows permuted; contact and cost real, frequency-to-composition link cut |

So the manager's reading is right, with one precision: the shuffled mode re-seeds from the
**ancestral** window pool, whereas frozen keeps the **current** roster's windows. A pure label
shuffle of the copassaged update was rejected during design because permuting strings cannot
change a multiset of windows, so it would leave the multiset unchanged and let the control
pass for the wrong reason.

## Honest limits

* The full closed-loop arms have not been re-run on the patched code: the patch is not
  applied in this environment. The 12-generation mirror run is the strongest available
  evidence before landing.
* The round-1 pilot finding stands and is unchanged by this patch: on the unpatched model the
  frozen arm does not destroy the delayed link, so RQ-3 remains `BLOCKED_MEASUREMENT` until
  the patch lands and the arms are re-run. That replay is the next round.
