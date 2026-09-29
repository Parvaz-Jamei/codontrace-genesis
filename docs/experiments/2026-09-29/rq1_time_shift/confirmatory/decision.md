# RQ-1 confirmatory decision

**Pack:** RQ-1 confirmatory · **Round:** 3 · **Commit:** `6187ff4` (isolated
extraction `test-runs/verify/full6187ff4`, never the live checkout)
**Config digest:** `rq1_confirmatory:d44a70140eeef5876ea68c838ca442de38f5e05cfeaeabd71bab2be38479c807`
**Seeds locked:** [5701, 5702, 5703, 5704, 5705, 5706, 5707, 5708] · **completed:** [5701, 5702]
**Generations per seed:** 200 (never shortened) · **slots:** {'past': 90, 'now': 100, 'future': 110}
**Regimes:** copassaged (coevolve) and fixed (frozen antagonist)
**Status:** partial

## Decision

`INCONCLUSIVE`

pattern not met at the locked threshold: completed 2/8 seeds, support labels 1/2, contemporary vs frozen interval [-0.0558017386, 0.0693853373] excludes_zero=False, lagged vs frozen [-0.0345598529, 0.0312625394] excludes_zero=False

## Integrity

* analysis derived only from raw JSONL: `raw_recompute_matches_all_seeds =
  True`
* all completed-seed gates OK: `True`
* frozen negative control exactly zero: `True`
* shuffled time-label control: 0 of 6 permutations
  receive a support label
* hypothesis_supported = false · red_queen_proved = false

## Effect table

| arm | n | mean | 95% paired t interval vs frozen |
|---|---|---|---|
| contemporary | 2 | 0.00679179935 | [-0.0558017386, 0.0693853373] |
| lagged | 2 | -0.00164865675 | [-0.0345598529, 0.0312625394] |
| frozen | 2 | 0.0 fixed | [0.0, 0.0] |
| contemporary − lagged | 2 | 0.0084404561 | [-0.087064278, 0.1039451902] |

## Exclusions

- no seed was dropped on the basis of its result
- the confirmatory generation count was not shortened
- seeds not yet complete: [5703, 5704, 5705, 5706, 5707, 5708]

## Note

No seed, threshold, arm, estimator or generation count was changed after any
result. Seeds [5703, 5704, 5705, 5706, 5707, 5708] remain; the pack is resumed by re-running the same locked command.
