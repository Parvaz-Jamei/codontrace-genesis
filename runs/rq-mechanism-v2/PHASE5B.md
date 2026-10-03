# Phase 5b full coevolution

Branch `rq/mechanism-v2`. Nothing was pushed, merged, or rewritten. `runs/rq-mechanism-v2/phase5-coevolution/` was not modified. `PHASE5_LOCK.md` was not modified. Commit `60a9a0fec9b542bd216c23d1ac6c080e3c254918` was not amended. The engine was not edited after this verdict and was not edited to make the coevolve claim positive.

`red_queen_proved` is false. Red Queen was not declared. Claim B's locked criterion was not met.

## Commits

- Control fix, before the lock and before any phase-5b history: `5c1c99ed526bdc36d5db9525330f567acb73886e`
- Rejection of the phase-5 control zeros, with the coevolve numbers left in place: `cf77f58448f720d08d8893bb3db0afe2ba528dde`
- Lock, before any phase-5b history: `762959733f1da8d46b4ef1cb3dbdc0ee456dedc8`

The lock file's sentence, in that commit, is: "No confirmatory number has been computed." It is the third line of `runs/rq-mechanism-v2/PHASE5B_LOCK.md` and the last sentence of that file. The lock commit contains no phase-5b archive and no claim mean. The rejected coevolve mean and the rejected control zeros are not in the lock.

## Why these settings

Lag 3 and horizon 10 are the values already locked from the seed-9600 probe. They were not re-chosen from the rejected confirmatory. Exploratory lag search was not done. Seed 9600 was not rerun. Seed 9700 was not used.

n is 12, the measurement floor. Seeds are 9701 through 9712. Seeds 9601 through 9612 were not reused. No seed was added after the sign.

Importance is undeclared. SUPPORTED is forbidden. The minimum detectable effects, kept separate from importance, are 0.22216378635389802 and 0.44432757270779605 from the planning sigmas 0.25 and 0.5 at n = 12. They were not taken from the rejected mean or from the control zeros. `MEASUREMENT_FLOOR` stays 12.

Workers: at most 7. The run used 7.

Claim A on the coevolve arm is unchanged: `I(hosts at generation 10, parasites at generation 10) - I(hosts at generation 10, parasites at generation 7) > 0`.

Claim B on the coevolve arm is unchanged: window counts, contact pressure, lineage relative fitness, and a sign reversal of `I(A) - I(B)`, together.

`constant_parasite` is host change against the same frozen parasite: `I(hosts at generation 10, parasites at generation 10) - I(hosts at generation 7, parasites at generation 10)`. The past parasite generation is not a second input.

`adaptation_cut` is the matched-pair change: `I(hosts at generation 10, parasites at generation 10) - I(hosts at generation 7, parasites at generation 7)`. Each generation contributes its own roster.

## Run

Twelve seeds, three arms, 10 generations, worker cap 7. Output is only `runs/rq-mechanism-v2/phase5b-coevolution/`. No history failed. No `REASON.txt`. No `STOP`. Every seed has `COMPLETE`. About 9.3 MB. Raw archives were kept.

Replay of this same run matched. Each of the 12 archives was re-scored with `replay_archived_contact`: 360 generations compared, 0 unmeasurable, 0 mismatches. One-shot versus resume matched on `scientific_body` inside each history before `COMPLETE`.

## Claim A

The coevolve estimand is the unchanged parasite time-shift on the horizon hosts. Controls are not substituted into it.

| Seed | coevolve | adaptation_cut | constant_parasite |
| --- | --- | --- | --- |
| 9701 | 0.03508771929824561 | 0.0 | 0.020066238067406927 |
| 9702 | 0.05747126436781602 | 0.0 | 0.031009984639016885 |
| 9703 | 0.048387096774193616 | 0.0 | -0.049550801148467216 |
| 9704 | 0.040935672514619936 | 0.0 | -0.006877708686640338 |
| 9705 | -0.011299435028248483 | 0.0 | -0.03121955971166962 |
| 9706 | -0.05084745762711873 | 0.0 | -0.053831417624521094 |
| 9707 | -0.07499999999999996 | 0.0 | 0.05688681083187219 |
| 9708 | -0.04678362573099415 | 0.0 | -0.04602411908799697 |
| 9709 | -0.008474576271186529 | 0.0 | 0.006885493303150303 |
| 9710 | 0.010752688172043001 | 0.0 | 0.04904982023626092 |
| 9711 | 0.05454545454545451 | 0.0 | -0.026144714527981894 |
| 9712 | -0.028248587570621486 | 0.0 | 0.06686798964624674 |

`n_locked` = 12. `n_used` = 12. `dropped_seeds` = []. Coevolve mean = 0.002210517787016947. The 95% interval is [-0.026830037999167188, 0.03125107357320108]. One-sided p = 0.43499462297059094. `se_zero` is false. Verdict `INCONCLUSIVE`.

The interval contains 0. Importance is undeclared, so the verdict is not `SUPPORTED`.

`constant_parasite` is not a forced zero. Every seed's host windows at generation 10 differ from generation 7, so the past and present inputs are not copies. The horizon and generation-7 parasite rosters do match, and the past parasite roster was not used as a second input. The twelve values above are host change against that one frozen roster. None of them is 0. Their mean is 0.0014265013280564027. That mean is not claim A.

`adaptation_cut` is 0 on every seed. The inputs were not actually different: on every seed the host window sequence and the parasite window sequence at generation 10 are the same as at generation 7 (`inputs_are_copies` true, `hosts_differ` false, `parasites_differ` false). The hold and the frozen reseat left both populations unchanged, so the matched-pair change is zero because the two pairs are the same windows. It is not the rejected contrast, which scored one host list against two copies of the parasite roster and could not be nonzero. This estimand can be nonzero when one window differs. A hand-computed seat check, not this output, moves 64 seats from affinity 0.5 to one seat at affinity 0 by 0.5/64.

## Claim B

| Seed | reversal | fitness measured | contacts | ATP paid | windows in the focal census |
| --- | --- | --- | --- | --- | --- |
| 9701 | false | true | 640 | 378.753125 | 37 |
| 9702 | false | true | 639 | 394.79999999999995 | 37 |
| 9703 | false | true | 640 | 379.8 | 31 |
| 9704 | false | true | 639 | 391.85625 | 33 |
| 9705 | false | true | 639 | 376.478125 | 32 |
| 9706 | false | true | 640 | 382.09375 | 33 |
| 9707 | false | true | 639 | 383.26250000000005 | 31 |
| 9708 | false | true | 639 | 373.7171874999999 | 29 |
| 9709 | false | true | 639 | 375.265625 | 32 |
| 9710 | false | true | 640 | 385.5499999999999 | 35 |
| 9711 | false | true | 638 | 384.75624999999997 | 35 |
| 9712 | false | true | 639 | 381.325 | 28 |

`frequency_measured_n` = 12. `contact_ok_n` = 12. `fitness_measured_n` = 12. `reversal_true_n` = 0. `used_census_wave_as_estimand` is false. Reversal-rate mean = 0.0. `se_zero` is true. The one-sided p-value is null, not 0. The interval is null. `criterion_met` is false. Verdict `INCONCLUSIVE`.

## Verdict

Claim A: `INCONCLUSIVE`. Claim B: `INCONCLUSIVE`. `importance_bound` is null. `supported_forbidden` is true. `measurement_floor` is 12. `measurement_floor_lowered` is false. `red_queen_proved` is false.

Red Queen was not declared. The locked criterion for claim B was not met.

## Tests

Not stacked with pytest-xdist. The validity file's pool stays at 4.

```
/tmp/ct-tools/bin/python -m pytest \
  tests/test_rq_mechanism_v2_phase5.py \
  tests/test_rq_mechanism_v2_validity.py \
  -o addopts='--disable-plugin-autoload --import-mode=importlib' \
  --tb=line -q
```

23 passed in 5.32s. Thirteen in `test_rq_mechanism_v2_phase5.py`, ten in `test_rq_mechanism_v2_validity.py`.

Ruff, on the touched files:

```
/tmp/ct-tools/bin/ruff check \
  src/codontrace/genesis/rq_mechanism_v2_phase5.py \
  tests/test_rq_mechanism_v2_phase5.py
```

All checks passed.

## What was not done

No push, merge, or history rewrite. The engine was not changed after the verdict. `red_queen_proved` was not set true by hand. Seeds were not added or replaced. Raw archives were kept. `phase5-coevolution/` and `PHASE5_LOCK.md` were not rewritten.
