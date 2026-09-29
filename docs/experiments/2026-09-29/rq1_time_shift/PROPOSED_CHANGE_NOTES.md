# RQ-1 proposed change — notes

## 1. WITHDRAWN draft (do not apply)

An earlier draft of this file proposed a `ContactPressurePolicy` plus a
`HostParasiteWorld.fork()` and recorded realised pressure through
`HostMeter.record_related_total("pi_intended_total", ...)`. **That draft is
withdrawn.** It is defective and was never handed over.

**Defect.** `HookMeter.record_related_total` validates its key:

* `src/codontrace/life_loop/hook_meters.py:214-219` — it raises
  `ConfigurationError(f"unknown related total: {k!r}")` when `k` is not in
  `RELATED_TALLY_KEYS`;
* `src/codontrace/life_loop/hook_meters.py:23-37` — `RELATED_TALLY_KEYS` contains
  `attach_occupancy, attach_capacity, coupling_total, coupling_loss_total,
  contact_success, contact_fail, birth_count, death_count, match_pass, match_fail,
  match_score_sum`. Neither `pi_intended_total` nor `pi_realised_total` is there.

**Effect.** The draft would have raised `ConfigurationError` on the first
successful contact, breaking `HostParasiteWorld` entirely.

**Evidence.** `logs/patch_verify.txt` verified the draft's hunks applied and
compiled — compilation is not execution, which is exactly how the defect slipped
through. Reading `hook_meters.py:214-231` shows the runtime guard. No test was
run against the draft because the header is now withdrawn.

**Smallest fix if that route is ever chosen again.** Add the two keys to
`RELATED_TALLY_KEYS` (hook_meters.py:23-37) and add the test
`assert ContactPressurePolicy.realised_debit(1.2, 0.0) == 0.0` plus a real
one-tick world run asserting the meter accepts the keys — a compile-only check is
not sufficient.

## 2. Current patch — documentation addendum (one new file, no code)

`PROPOSED_CHANGE.patch` now adds
`docs/campaigns/discovery_questions_20260928/DISCOVERY_PROGRAM_STAGE0_ADDENDUM_20260929_RQ1_ROUTE.md`.

**Defect it fixes (documentation, not code).**
`DISCOVERY_PROGRAM_STAGE0_20260929.md` (sealed, §7 and TESTS_DONE_STATUS) records
RQ-1 as `BLOCKED_MEASUREMENT` on the live model because "the antagonist is not a
genotype population". That statement is route-specific: it is true of the Idea-2
engine cell (`parasite_is_genotype_population=false`), but false for
`StructuralRQArm` in `src/codontrace/genesis/closed_loop_hp_arm01_structural_rq.py`.

**Evidence (computed, this session — `raw/feasibility_structural.json`).**

* `ECOLOGY_ARMS = ("avirulent", "fixed", "copassaged")` with passages
  `absent / frozen / coevolve`; each arm boots and runs.
* `copassaged` at generation 5: 64 antagonist windows occupying 29 distinct
  antagonist classes, 35 host classes, 64 hosts, 35 host classes carrying
  realised pressure.
* `fixed` at generation 5: 64 antagonists in exactly 16 classes (the frozen
  16-window cycle), so the frozen control cannot adapt.
* `avirulent` at generation 5: 0 antagonists.
* `_passage_update` (`closed_loop_hp_arm01_structural_rq.py:739-769`) keeps
  `kappa=0.5` of the window stock, re-draws the rest from this generation's
  `matched_windows`, and mutates at `parasite_mutation=0.25`: heritable,
  mutating, selected.
* `window_snapshot` (`:808-914`) exposes per-generation host class frequencies
  (`joint_freq`), antagonist class frequencies (`parasite_class_hist`) and the
  realised pressure per host class (`host_realised_pressure`).

**Why no code change is needed for RQ-1.** The three arms boot from the same
seed and the same initial state — verified by identical founder genome digests
and identical initial parasite-window digests across the three arms for a seed
(`raw/live_run.json` → `seeds[].arm_initial_state`) — and each arm uses its own
labelled RNG namespace (`hp-struct-rq-{arm}`). The 3×3 cross-time matrix is
assembled outside evolution from the archived class tables with the existing
measurement kernel (`realised_conditional_host_pressure`, `full_matrix` equal
exposure). Verified with the live run in `test-runs/rq1/rq1_live_run.py`.

**Risk if the addendum is applied.** None to code: it adds one markdown file and
edits nothing. The sealed stage-0 record is left untouched, as the program
requires.

## 3. Files touched

| Path | Change |
|---|---|
| `docs/campaigns/discovery_questions_20260928/DISCOVERY_PROGRAM_STAGE0_ADDENDUM_20260929_RQ1_ROUTE.md` | new, 30 lines |

No code file is modified. No sealed record is modified.
