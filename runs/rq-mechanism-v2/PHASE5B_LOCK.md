# Phase-5b lock

No confirmatory number has been computed.

Code commit: `5c1c99ed526bdc36d5db9525330f567acb73886e` on branch `rq/mechanism-v2`.
Nothing has been pushed, merged, or rebased.
This lock is committed before the phase-5b run.
`runs/rq-mechanism-v2/phase5-coevolution/` is not rewritten.
`PHASE5_LOCK.md` is not rewritten. Commit `60a9a0fec9b542bd216c23d1ac6c080e3c254918` is not amended.
Seeds 9601 through 9612 are not reused. Seed 9600 is not rerun. Seed 9700 is not used.

## Claim A on the coevolve arm

Unchanged. Direction, already locked from the seed-9600 probe:
`I(hosts at the horizon, parasites at the horizon) - I(hosts at the horizon, parasites at horizon - lag) > 0`.
The primary arm is `coevolve`. This estimand was not redefined to make the coevolve arm look larger.
The score is `infectivity` on `replay_archived_contact` with evolution, reproduction, and mutation off.

## Claim B on the coevolve arm

Unchanged. Required together: genotype frequency as window counts;
real contact pressure; lineage relative fitness; and a sign reversal of `I(A) - I(B)`
between the contemporary and past parasite populations.
A census wave is not claim B. Claim A is not claim B.
`red_queen_proved` is true only if claim B's locked criterion is met, including a declared importance bound.
Importance is undeclared, so that criterion is not met by declaration.

## Controls

The phase-5 control zero was an instrument failure. It is not reused as a bound.
`constant_parasite`: host change against the same frozen parasite.
`I(hosts at the horizon, parasites at the horizon) - I(hosts at horizon - lag, parasites at the horizon)`.
The past parasite generation is not a second input. This is not the difference of two parasite copies.
`adaptation_cut`: matched-pair change.
`I(hosts at the horizon, parasites at the horizon) - I(hosts at horizon - lag, parasites at horizon - lag)`.
Past and present parasite inputs are the two generations' own rosters, not copies of one roster.
The contrast can be nonzero if the host windows change or the parasite windows change.
Host bit-flip stays 0 on this arm, parasite passage stays `frozen`, and reproduction stays enabled.
`shuffled_labels` is not used. Passage `absent` is not used.

## Lag, horizon, and n

Primary lag 3 and horizon 10 are taken from the seed-9600 probe already locked in `PHASE5_LOCK.md`.
They are not re-chosen from the rejected confirmatory. Exploratory lag search is forbidden.
Primary lag: 3.
Horizon: 10 generations.
n: 12.
Seeds: 9701 through 9712 (9701, 9702, 9703, 9704, 9705, 9706, 9707, 9708, 9709, 9710, 9711, 9712).
No seed is added after a sign.

## Importance and the minimum detectable effect

Importance for this estimand is undeclared. SUPPORTED is forbidden.
The rejected coevolve mean and the rejected control zeros are not an importance bound.
The Decaestecker gap of 0.10 is not this engine's importance bound.
Planning sigma for claim A is 0.25. Planning sigma for claim B is 0.5.
MDE claim A: 0.22216378635389802. MDE claim B: 0.44432757270779605.
The minimum detectable effect is not the importance bound.
`MEASUREMENT_FLOOR` stays 12 and is not lowered.

## Run rules

CPU workers at most 7.
Output: `runs/rq-mechanism-v2/phase5b-coevolution`.
Do not write into `runs/rq-mechanism-v2/phase5-coevolution/`.
Raw archives are kept. A partial run is kept. A seed is not replaced.
Replay of the same run is required.
If replay does not match, stop. Do not edit the engine after the verdict.

```json
{
  "horizon": 10,
  "importance_bound": null,
  "importance_undeclared": true,
  "mde_a": 0.22216378635389802,
  "mde_b": 0.44432757270779605,
  "mde_is_importance": false,
  "measurement_floor": 12,
  "n": 12,
  "primary_lag": 3,
  "seeds": [
    9701,
    9702,
    9703,
    9704,
    9705,
    9706,
    9707,
    9708,
    9709,
    9710,
    9711,
    9712
  ],
  "supported_forbidden": true,
  "workers": 7
}
```

No confirmatory number has been computed.
