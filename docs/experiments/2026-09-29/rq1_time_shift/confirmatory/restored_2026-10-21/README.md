# RQ-1 locked pack: seeds 5706–5708 rerun at the locked commit (2026-10-21)

## Correction

Earlier files said the locked commit `6187ff4` is not in this repository
(`README.md`, `closure_2026-10-03/README.md`, the closure seed JSONs and
`tests/science_gates/test_closure_runs_20261003.py`). That was wrong.
`git cat-file -t 6187ff4` gives `commit`, and `git merge-base --is-ancestor
6187ff4 HEAD` succeeds. The closure JSONs are left unchanged as a historical
record. Their `locked_commit_absent` field is a statement that turned out to
be false. It does not describe the repository.

## What was done

1. Created a detached worktree at `6187ff4` and a clean virtual environment
   with that worktree installed.
2. Confirmed that the meter blobs the analysis pins match `6187ff4`.
3. Ran the archived runner `../confirmatory_rq1.py` unchanged for each seed
   through `run_one_seed.py`, which only selects the seed and the output
   directory. Seed 5701 was run as a control and was not stored again.
4. Compared every record with the archive, ignoring only `wall_s`.
   `verify_provenance.py` does this, and its output is in `verify_<seed>.json`.

Box run times were 476 s (5701), 536 s (5706), 533 s (5707) and 739 s (5708).

## Results of the comparison

* **5701 (control):** events, population and summary match the archive
  exactly (400 / 400 / 40 records). All 13 other fields of the seed JSON
  match. The one exception is `frozen_is_zero`: the archived value is
  `false` and the reproduction gives `true`. Applying the runner's own rule
  (`confirmatory_rq1.py:328-335`) to the *archived* fixed-regime matrix also
  gives `true`. The archived seeds 5701 and 5702 carry `false`, while
  5703–5705 carry `true`. So the stored flag on 5701 and 5702 came from an
  earlier form of the rule. The data are unaffected. The archived
  `decision.md` already reports the frozen control as exactly zero.
* **5706:** the archived partial log (325 events, 325 population, 32 summary
  records) is a byte-identical prefix of the rerun (400 / 400 / 40).
* **5707, 5708:** no archived counterpart exists, so these are new runs at
  the locked commit. The engine is deterministic, and the 5701 control and
  the 5706 prefix both match the archive exactly.

The restored files are in `raw/` (gzip `-n -9`), with checksums in
`MANIFEST.sha256`.

## Eight-seed rebuild

`analysis_eight_seeds/` is the output of the unchanged
`../analysis_confirmatory_rq1.py --reference-checkout <6187ff4 worktree>`.
Its inputs were archived seeds 5701–5705 plus the restored 5706–5708.
`raw_recompute_matches_all_seeds = True` and all seed gates are OK.

**Verdict: `INCONCLUSIVE`.** 3 of 8 seeds receive the support label. The
contemporary-vs-frozen interval is [0.00071, 0.01220] and the lagged-vs-frozen
interval is [-0.00726, -0.00196]. The locked pattern is not met.
`hypothesis_supported` and `red_queen_proved` stay false. Line 11 of the
generated `decision.md` is boilerplate from the rebuild script. For this
directory, seeds 5706–5708 *were* run, at `6187ff4`, as described above.

The top-level `../decision.md` and `../raw/` are not modified.
