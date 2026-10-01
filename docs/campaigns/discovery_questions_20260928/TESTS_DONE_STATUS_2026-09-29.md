# Discovery test program — which tests have actually been run

**Date:** 2026-09-29 · **Local tip:** `cd74b85` · **Program base revision:** `e5ae88a`
**Source of truth for status:** `docs/campaigns/discovery_questions_20260928/DISCOVERY_PROGRAM_STAGE0_20260929.md` (sealed) plus the result records listed below.

## Short answer

**None of the eight program tests has been executed as a population test.** The
stage-0 record states it directly: the program names eight tests, none of the
eight had been written as a population test, and the population-run count in the
pack is **0**. What exists is instrument and stage-0 validation, phase-1 problem
boundaries, phase-2 design digests, harness and JSONL smoke under sealed digests,
and two engineering-gated engine pilots (ideas 2 and 4). The formal decision on
the three tests that were to be piloted first is `BLOCKED_MEASUREMENT`.

## Test-by-test status

| Test | Status | Evidence | What exists | What does not |
|---|---|---|---|---|
| **RQ-1** time-shift, past/present/future antagonist | `BLOCKED_MEASUREMENT` (live model) | `DISCOVERY_PROGRAM_STAGE0_20260929.md` §4, §7 | Hand fixtures: a contemporary matrix and a lagged matrix receive those labels; a flat matrix, a directional increase and one rotation of the time labels do not | No live matrices were produced; no population run |
| **RQ-2** causal frequency swap with the genotype set held fixed | instrument only | `tests/closed_loop/test_closed_loop_frequency_swap_mechanism.py` (8 tests) + `STATS_AND_NULL_DESIGN.md` | The swap statistic `S = pi_A(swap) − pi_A(swap^-1)` with sign-locked expectation, positive synthetic case, anti-phase counter-sample and two further nulls; run-level bootstrap defined | No checkpoint-based population swap; the stage-0 record notes the multiset is not held fixed in the live model |
| **RQ-3** cut the antagonist adaptation route, keep the ecological cost | `BLOCKED_MEASUREMENT` (live model) | `DISCOVERY_PROGRAM_STAGE0_20260929.md` §5, §7 | Hand channel `S = −0.600`, so the pre-registered direction and the `0.20` floor hold as arithmetic; the same pairing held fixed gives `S = 0` | The live census is not this channel; no arm comparison on a real population |
| **RQ-4** time and ecological boundary, `2x2x2` locked grid | not run | stage-0 | Calibration advice only (verify every cell has survival and heritable variation before the grid) | No grid, no cells, no interaction analysis |
| **D-1** costly causal experimentation under antagonist pressure (ideas 1 and 2) | design + engineering pilot only | `IDEA2_PHASE2_RESULT.md` and its engine `N>=64` addendum, `PHASE2_ENGINE_N64_POSTDATA_GATE.md`, `IDEA1_PHASE2_DESIGN_DIGEST.md`, `IDEA1_PHASE2_PRIOR_ART_20260928.md` | Phase-2 harness with ledger `do` operations outside `engine.py`, sham control, shared decision budget, sealed smoke; engine closed-loop pilot at `N=64` with all four cells | **G2 FAIL** (causal × pi_deception), no scored survival-share margin ≥ 0.15, no scored M0–M3 separation, smoke used single-seed wiring checks. `hypothesis_supported=false` |
| **D-2** function-recovery window with contact structure (idea 4) | design + engineering pilot only; `BLOCKED_MEASUREMENT` for the live test | `IDEA4_PHASE2_RESULT.md`, `IDEA4_PHASE2_DESIGN_DIGEST.md`, stage-0 §7 | Locked ledger operations and identity fields, recovery token distinct from knowledge digest and named-scaffold cuts | Checkpoint is not a full fork, topology is not identified, `window_test_valid` not established in one branch and cohort |
| **D-3** transferable symbolic law (ideas 3 and 5) | `BLOCKED_MEASUREMENT` | stage-0 §"Explicit non-outcomes"; `IDEA3_*`, `IDEA5_*`, `PHASE2_TRACK_C_JSONL_NOTE.md`, `PHASE2_TRACK_C_JSONL_POSTDATA_GATE.md` | Design digests, prior-art notes, Track C scored JSONL harness and smoke | This stage has no inputs for it; no unseen-world transfer run |
| **D-4** epistemic restraint under deception (idea 6) | `BLOCKED_MEASUREMENT` | stage-0 §"Explicit non-outcomes"; `IDEA6_PHASE2_DESIGN_DIGEST.md`, Track C JSONL note | Design digest and identity-ID locking, harness smoke | No policy-inheritance or calibration outcome |

## Blocker-by-blocker status

| Blocker | Status | Evidence |
|---|---|---|
| 1. RQ sign: DAG expects `S < 0` but the helper accepted positive values | **Addressed in the design and the meter, refused in substance** | `SCIENTIFIC_QUESTION_AND_DAG.md` commits `S < 0` with lag and sign per link; the meter reproduces the hand arithmetic `S = −0.600`; the synthetic `−0.148` remains inside the magnitude barrier and was deliberately **not** recomputed, raised, or rescued by parameter or seed choice (stage-0 §"Explicit non-outcomes") |
| 2. The antagonist is not a real evolving parasite (genotype, reproduction, death, selection) | **Not fixed** | stage-0 §7: the antagonist is not a genotype population; short live cells stay blocked |
| 3. Idea 4 coupler: edge cost is split across organisms; no edge→local contact, ATP transfer or survival link; `recover` returns a genome digest while the locked plan measures recovery of rare-contact yield; checkpoint must fork full state and RNG; `window_test_valid` must hold in one branch and cohort | **Not fixed** | stage-0 §7: the checkpoint is not a full fork and topology is not identified; the idea 4 result record lists the two endpoints separately |
| 4. Every failing gate must return `BLOCKED_MEASUREMENT` or `FALSIFIED_HYPOTHESIS` with cause and raw data; no more seeds on a broken meter; `hypothesis_supported` and `red_queen_proved` stay false | **Satisfied in practice** | stage-0 issues `BLOCKED_MEASUREMENT` for RQ-1, RQ-3, D-2 on the live model and for D-3 and D-4; `hypothesis_supported=false` and `red_queen_proved=false` are sealed in the same record; the idea 2 and idea 4 records list explicit non-outcomes |

## Protocol elements already implemented

| Program requirement | Status | Where |
|---|---|---|
| Live append-only JSONL events, summary every 10 generations, snapshot every 25 | Implemented for the causal-tape campaigns; JSONL harness exists for the discovery track | `causal-tape-experiment/telemetry.py`; `PHASE2_TRACK_C_JSONL_NOTE.md`, `tests/campaigns/discovery_questions_20260928/` |
| `run_manifest.json` with commit, dirty flag, config hash, schema, seed, RNG, timing and parent snapshot | Partly: config digest, timings, pid, status, resume index | `telemetry.py` |
| One replay command from the manifest reproducing the summary | Not implemented | deterministic replay exists at the engine level, not as a manifest-driven command |
| Unit and property tests, hand-computed cases, energy and population invariants, byte-identical replay | Present for the closed-loop and causal-tape work | `tests/closed_loop/`, `tests/campaigns/discovery_questions_20260928/` |
| Calibration, exploratory pilot and sealed holdout split with a locked stopping rule | Written, not run | `rq_redesign_20260928/PREREG_V2.md`, `STATS_AND_NULL_DESIGN.md` |

## Work outside this program that did produce results

These are recorded separately and are not part of the eight program tests:

* **Causal-tape estimator campaign** (`docs/campaigns/causal_tape_20260927/`):
  the exact interventional effect of a single substitution is computable, naive
  conditioning is biased before any epistasis is present, and at high epistasis
  about **64 per cent** of the quantity previously labelled estimator bias is a
  whole-tape re-routing gap rather than model misspecification.
* **Two-fold cost of sex** (`docs/experiments/2026-09-29/sex_cost/`): inside the
  locked grid only (infection_cost=0.4, 400 generations, host_cap=400,
  turnovers 1/6/12, seeds 8000–8099) the measured bracket is `(1.1, 1.2]`.
  That bracket is not a result for other regimes or horizons, and it is not
  evidence that coevolution maintains sex at the classical two-fold cost.
  Standing label: `INCONCLUSIVE`.
* **Biotic versus abiotic turnover** (`causal-tape-experiment/results/rjcj_results.json`):
  antagonist-dominant within the model world, stable across window lengths, with
  a genotype-blind tax control passing.

## Next actions, in the program's own order

Historical list. Where it disagrees with the standing table at the end of this
file, the table and `docs/experiments/2026-09-29/VERDICT_LEDGER_V1.json` win.

1. Fix blockers 2 and 3 (a real evolving antagonist; the idea 4 contact/ATP
   coupling and full-state checkpoint fork). Until then RQ-1, RQ-3, D-2 stay
   `BLOCKED_MEASUREMENT` and D-1, D-3, D-4 stay blocked behind them.
2. Then pilot only RQ-1, RQ-3 and D-2 under the pre-registered budget (8 minutes
   per test, 45 minutes for the first pack, 4 GiB), with raw JSONL and manifest.
3. Deliver per test: locked `design.md`, `prior_art.md`, manifest, raw events,
   derived summary, replay script, effect and interval table, negative control,
   exclusions and `decision.md` holding exactly one of `SUPPORTED_IN_MODEL`,
   `FALSIFIED_IN_MODEL`, `INCONCLUSIVE`, `BLOCKED_MEASUREMENT`.
4. No `PASS` label for smoke or for an injected positive; absence of a search hit
   is not a uniqueness claim.

**CI repair and executed-test status (2026-09-29):** the red-state root causes, the fixing commit
chain and the evidence map are recorded in
[`docs/ci/CI_REPAIR_AND_TEST_STATUS_2026-09-29.md`](../../ci/CI_REPAIR_AND_TEST_STATUS_2026-09-29.md);
no locked pin was re-locked for those fixes.

**Novelty and results synthesis (2026-09-29):** the reviewed claim-discipline synthesis is committed
as [`NOVELTY_AND_RESULTS_SYNTHESIS_2026-09-29.md`](NOVELTY_AND_RESULTS_SYNTHESIS_2026-09-29.md)
(RQ-1 `INCONCLUSIVE`, archive incomplete; D-2 `BLOCKED_MEASUREMENT`, with round-4
`FALSIFIED_IN_MODEL` kept as history; RQ-3 `INCONCLUSIVE` on seeds 21001 and
21011, while the 21061–21063 quotation is `INCOMPLETE`; the CausalTape share
only with its estimator label; the sex-cost bracket only inside its own grid).

## Confirmed results superseding the stage-0 rows (2026-09-29)

The stage-0 status map above is the sealed record of the stage-0 decision and is left as written;
this section records the confirmed results that now supersede the `BLOCKED_MEASUREMENT` / "not run"
wording in its RQ-1, RQ-3 and D-2 rows and in its "Next actions" list.

| Test | Standing result | Evidence |
|---|---|---|
| **RQ-1** time-shift | **`INCONCLUSIVE`, archive incomplete.** The imported tree has `seed_<N>.json` for 5701–5705 only. 5706 has population and summary files and no final seed JSON. 5707 and 5708 are not in the tree. `confirmatory/analysis_confirmatory.json` still says `status=partial` and `seeds_completed=[5701, 5702]`. The 8/8 means and intervals in the 2026-09-29 owner draft are not recomputed from imported raw files and are not a completion claim. `hypothesis_supported = false`, `red_queen_proved = false`. | `docs/experiments/2026-09-29/rq1_time_shift/README.md` (archive integrity section), `confirmatory/raw/` |
| **RQ-3** adaptation-route cut | **`INCONCLUSIVE`** on the published raw seeds 21001 and 21011. The README table for seeds 21061–21063 has no roster in the tree, so that table is `INCOMPLETE` and is not a reconstructable analysis. The earlier `SUPPORTED_IN_MODEL` wording stays withdrawn. Standing label: `docs/experiments/2026-09-29/VERDICT_LEDGER_V1.json`. | `docs/experiments/2026-09-29/rq3_adaptation_route/README.md` |
| **D-2** recovery window | **`BLOCKED_MEASUREMENT`.** The positive control did not reach the locked 1.25× for three consecutive boundaries, so zeros on the arms do not falsify an intervention. Round-4 `FALSIFIED_IN_MODEL` is retained history, not the standing verdict. | `docs/experiments/2026-09-29/d2_recovery_window/README.md`, `docs/experiments/2026-09-29/VERDICT_LEDGER_V1.json` |

Consequences for the "Next actions" list above: RQ-1 is not a finished 8-seed pack, because seeds 5707 and 5708 are not in the imported archive. RQ-3 is no longer
blocked and no longer supported, and D-2's live test is no longer blocked for lack of a fork or a
topology identification - it is a measurement-level negative with a positive control reported first.
The remaining blocks of that list stay as written for D-1, D-3 and D-4. No threshold, seed, lock,
claim ceiling or flag is changed here.
