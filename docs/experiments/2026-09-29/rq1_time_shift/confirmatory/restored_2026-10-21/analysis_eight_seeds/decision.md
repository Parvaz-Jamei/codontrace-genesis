# RQ-1 confirmatory decision

**Pack:** RQ-1 confirmatory · **Round:** 3 · **Commit pin:** `6187ff4`
**Config digest:** `rq1_confirmatory:d44a70140eeef5876ea68c838ca442de38f5e05cfeaeabd71bab2be38479c807`
**Seeds locked:** [5701, 5702, 5703, 5704, 5705, 5706, 5707, 5708] · **seed JSON present:** [5701, 5702, 5703, 5704, 5705, 5706, 5707, 5708]
**Archive complete:** True
**Generations per seed:** 200 (never shortened) · **slots:** {'past': 90, 'now': 100, 'future': 110}
**Regimes:** copassaged (coevolve) and fixed (frozen antagonist)
**Status:** complete

This file is a derived rebuild from imported raw files after the meter blobs matched the pin. It is not a new simulation, and it is not evidence that the absent seeds ran.

## Decision

`INCONCLUSIVE`

pattern not met at the locked threshold: completed 8/8 seeds, support labels 3/8, contemporary vs frozen interval [0.0007116288, 0.0122027363] excludes_zero=True, lagged vs frozen [-0.0072586535, -0.0019644048] excludes_zero=True

## Integrity

* analysis derived only from raw JSONL: `raw_recompute_matches_all_seeds =
  True`
* all completed-seed gates OK: `True`
* frozen negative control exactly zero: `True`
* shuffled time-label control: 0 of 24 permutations
  receive a support label
* hypothesis_supported = false · red_queen_proved = false

## Effect table

| arm | n | mean | 95% paired t interval vs frozen |
|---|---|---|---|
| contemporary | 8 | 0.006457182525 | [0.0007116288, 0.0122027363] |
| lagged | 8 | -0.0046115291625 | [-0.0072586535, -0.0019644048] |
| frozen | 8 | 0.0 fixed | [0.0, 0.0] |
| contemporary − lagged | 8 | 0.0110687116875 | [0.0034061762, 0.0187312472] |

## Exclusions

- no seed was dropped on the basis of its result
- the confirmatory generation count was not shortened
- all locked seeds complete

## Note

No seed, threshold, arm, estimator or generation count was changed after any
result. The locked pack is complete.
