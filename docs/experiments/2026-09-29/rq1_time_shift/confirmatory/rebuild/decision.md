# RQ-1 confirmatory decision

**Pack:** RQ-1 confirmatory · **Round:** 3 · **Commit:** `6187ff4` (isolated
extraction `test-runs/verify/full6187ff4`, never the live checkout)
**Config digest:** `rq1_confirmatory:d44a70140eeef5876ea68c838ca442de38f5e05cfeaeabd71bab2be38479c807`
**Seeds locked:** [5701, 5702, 5703, 5704, 5705, 5706, 5707, 5708] · **completed:** [5701, 5702, 5703, 5704, 5705]
**Generations per seed:** 200 (never shortened) · **slots:** {'past': 90, 'now': 100, 'future': 110}
**Regimes:** copassaged (coevolve) and fixed (frozen antagonist)
**Status:** incomplete_archive

## Decision

`INCONCLUSIVE`

pattern not met at the locked threshold: completed 5/8 seeds, support labels 1/5, contemporary vs frozen interval [-0.0021566859, 0.0148486238] excludes_zero=False, lagged vs frozen [-0.0069487013, -0.0002544981] excludes_zero=True

## Integrity

* analysis derived only from raw JSONL: `raw_recompute_matches_all_seeds =
  True`
* all completed-seed gates OK: `True`
* frozen negative control exactly zero: `True`
* shuffled time-label control: 0 of 15 permutations
  receive a support label
* hypothesis_supported = false · red_queen_proved = false

## Effect table

| arm | n | mean | 95% paired t interval vs frozen |
|---|---|---|---|
| contemporary | 5 | 0.006345968939999999 | [-0.0021566859, 0.0148486238] |
| lagged | 5 | -0.00360159968 | [-0.0069487013, -0.0002544981] |
| frozen | 5 | 0.0 fixed | [0.0, 0.0] |
| contemporary − lagged | 5 | 0.00994756862 | [-0.0007844261, 0.0206795633] |

## Exclusions

- no seed was dropped on the basis of its result
- the confirmatory generation count was not shortened
- seeds not yet complete: [5706, 5707, 5708]

## Note

No seed, threshold, arm, estimator or generation count was changed after any
result. Seeds [5706, 5707, 5708] remain; the pack is resumed by re-running the same locked command.
