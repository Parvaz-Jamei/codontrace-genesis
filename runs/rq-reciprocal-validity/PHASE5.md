# Phase 5 confirmatory

`red_queen_proved` is false. Horizon, lag, seeds, and the importance bound were not changed after these numbers. The lock remains `runs/rq-reciprocal-validity/PHASE4_CONFIRM_LOCK.md`.

Seeds 9911 through 9922. Generations 31. Arms `coevolve`, `adaptation_cut`, and `constant_parasite`. Workers 7. `compare_one_shot` true. Output: `runs/rq-reciprocal-validity/phase5-confirm/`.

Past generation 25, present 28, future 31. No history failed. `dropped_seeds` is `[]`. `n_independent` is 12. `MEASUREMENT_FLOOR` stays 12. Every scored cell was present. No margin was filled in from a missing cell. Replay of each archive matched, 93 compared generations, mismatches empty.

The run finished before 600 seconds. `health.log` was not written. No 10-minute tick elapsed.

Importance bound stays `0.0026041666666666665`. `supported_forbidden` is false because that bound was declared before the run. `SUPPORTED` still requires both continuous lower bounds to clear it. Neither does.

## Coevolve margins

Host margin mean `-0.01265986927038675`. Interval `[-0.03433459674045918, 0.00901485819968568]`. One-sided p `0.8874993182022344`. Verdict `INCONCLUSIVE`.

Parasite margin mean `0.010514852388075003`. Interval `[-0.010217518407846198, 0.031247223183996205]`. One-sided p `0.14404753353303373`. Verdict `INCONCLUSIVE`.

Binary index: 5 of 12 histories have both margins positive. Wilson interval `[0.19326031353363787, 0.6804886876249334]`. Mean `0.4166666666666667`. One-sided p `0.38720703125`. Two-sided p `0.7744140625`. Verdict `INCONCLUSIVE`. The binary index is not the continuous margin.

Joint verdict `INCONCLUSIVE`. The two margins were not added.

| Seed | Host margin | Parasite margin |
| --- | --- | --- |
| 9911 | 0.023504273504273532 | 0.0006550356094429111 |
| 9912 | 0.037634408602150615 | 0.04352244859460486 |
| 9913 | 0.0030864197530862114 | 0.043584992567468506 |
| 9914 | -0.0478723404255319 | -0.048712206047032414 |
| 9915 | -0.07602339181286544 | -0.04883040935672511 |
| 9916 | -0.004098360655737765 | 0.02279396883222018 |
| 9917 | 0.0062893081761007386 | 0.03704650370232676 |
| 9918 | -0.04924242424242431 | -0.0044915254237287705 |
| 9919 | -0.022222222222222365 | 0.01913580246913571 |
| 9920 | -0.02777777777777768 | 0.012287347155768291 |
| 9921 | 0.023809523809523725 | 0.04518883824716324 |
| 9922 | -0.01900584795321636 | 0.003997432306255877 |

## Controls

Same cells. Not the primary estimand. Zeros are kept.

Adaptation-cut host margin is `0.0` on every seed. Adaptation-cut parasite margin is `-0.007017543859649145` on every seed.

Constant-parasite host margin is `0.0` on every seed. Constant-parasite parasite margins, seeds 9911 through 9922: `-0.02091895971206309`, `0.030577601410934796`, `-0.08229651509726693`, `-0.0191632022172476`, `0.04258284818629643`, `-0.015437158469945367`, `0.03721875309743283`, `0.0508221675984834`, `-0.01576095720886539`, `-0.021024904214559326`, `-0.01711961815702312`, `0.04351395730706081`.
