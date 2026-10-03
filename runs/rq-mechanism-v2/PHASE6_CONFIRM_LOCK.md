No confirmatory number has been computed.

# Phase-6 confirmatory lock

Code commit before this lock: `066fa3da1e64c2d7f77319052fc3d93fb7c1131a`.
Nothing in this lock is a confirmatory claim mean.
Phase-5b seeds 9701 through 9712 are not reused. Seeds 9601 through 9612 are not reused.
The horizon was not recomputed from a new probe.

## Budget

The budget moves from 16 to 70 so the pre-registered maximum of the parasite replacement time,
the host replacement time, and the fitness-response delay can run.
It is not a parameter tune. Seeds, lag, thresholds, and population parameters are unchanged.
Papkou et al. 2019, Proceedings of the National Academy of Sciences, DOI 10.1073/pnas.1810402116,
ran 23 host transfers and controlled generation time for the host, not the parasite.
The 2010 Caenorhabditis elegans and Bacillus thuringiensis coevolution experiment, PMC2867683,
used 48 host generations.
Brockhurst and Koskella 2013, Trends in Ecology and Evolution, time-shift the interaction over evolutionary time,
not over a budget shorter than one host replacement.
The horizon is not shortened to 16.
`PHASE6_LOCK.md` still records the refusal under the old budget.

## Estimand

Every arm is scored with the same paired estimand:
`I(hosts at the horizon, parasites at the horizon) - I(hosts at horizon - lag, parasites at horizon - lag)`.
Host effect, parasites held at the past generation:
`I(hosts at the horizon, parasites at horizon - lag) - I(hosts at horizon - lag, parasites at horizon - lag)`.
Parasite effect, hosts held at the horizon:
`I(hosts at the horizon, parasites at the horizon) - I(hosts at the horizon, parasites at horizon - lag)`.
Those two effects add to the paired estimand. The diagnostic host contrast on contemporary parasites is not added in.
The score is `infectivity` on `replay_archived_contact` with evolution, reproduction, and mutation off.

## Oscillation

A direction of selection is the sign of ancestry fitness of genotypes that are both present, on a generation with contact pressure.
An infectivity gap alone is not that direction.
The registered times are the horizon, one lag earlier, and two lags earlier, when two lags fit.
One sign change is not a continuing cycle. A scan of every generation stays exploratory.
`red_queen_proved` is not set from this criterion. Importance is undeclared.

## Horizon

The horizon is the maximum of the parasite replacement time, the host replacement time,
and the fitness-response delay when that delay was measured.
It is not three times the parasite replacement time.
Parasite replacement: 2.9201520912547525.
Host replacement: 69.54545454545455.
Fitness delay: 9.0. Unmeasurable: False.
Primary lag: 3.
Horizon: 70 generations. Budget: 70. The horizon was not shortened.
n: 12.
Seeds: 9811 through 9822 (9811, 9812, 9813, 9814, 9815, 9816, 9817, 9818, 9819, 9820, 9821, 9822).

Importance for this estimand is undeclared. SUPPORTED is forbidden.
`MEASUREMENT_FLOOR` stays 12 and is not lowered.
CPU workers at most 7. Reject 8.
Output: `runs/rq-mechanism-v2/phase6-coevolution`.
One-shot and resume are compared on `scientific_body` before `COMPLETE`.

```json
{
  "budget": 70,
  "fitness_delay": 9.0,
  "fitness_delay_unmeasurable": false,
  "horizon": 70,
  "host_replacement": 69.54545454545455,
  "importance_bound": null,
  "measurement_floor": 12,
  "n": 12,
  "parasite_replacement": 2.9201520912547525,
  "primary_lag": 3,
  "seeds": [
    9811,
    9812,
    9813,
    9814,
    9815,
    9816,
    9817,
    9818,
    9819,
    9820,
    9821,
    9822
  ],
  "supported_forbidden": true,
  "turnover_multiple_used": false,
  "workers": 7
}
```

No confirmatory number has been computed.
