# Phase-5 lock

No confirmatory number has been computed.

Code commit: `46c318f298e0c27f6fd636e6f37a1df61581912a` on branch `rq/mechanism-v2`.
Nothing has been pushed, merged, or rebased.
`runs/rq-bidirectional-timeshift-01` is untouched and is not part of this commit.
Previous mechanism-v2 runs are not modified. `PHASE3_LOCK.md` is not modified.

## Claim A

Directional reciprocal adaptation.
Direction, locked before the confirmatory:
`I(hosts at the horizon, parasites at the horizon) - I(hosts at the horizon, parasites at horizon - lag) > 0`.
Contemporary parasite performance on the focal hosts is predicted to exceed performance of the past parasites.
The score is `infectivity` on `replay_archived_contact` with evolution, reproduction, and mutation off.
The direction is the contemporary-versus-previous comparison read from Decaestecker et al. 2007 in `PHASE1.md`
(contemporary infectivity 0.65, previous 0.55). It was not chosen from a probe contrast.
The primary arm is `coevolve`.

## Claim B

Frequency-dependent selection and an oscillating Red Queen.
Required together on the coevolve arm: genotype frequency as window counts;
real contact pressure (contacts and ATP paid on the debit path);
relative fitness from the lineage (parent ids, births, deaths, next-generation share over start frequency);
and a sign reversal of `I(A) - I(B)` between the contemporary and past parasite populations.
ATP loss is not fitness. A census wave, a lagged correlation, or a renamed class is not claim B.
Claim A is not claim B. A positive D or a nonzero F from an earlier phase is not this confirmatory.
`red_queen_proved` is true only if claim B's locked criterion is met, including a declared importance bound.

## Controls

`adaptation_cut`: host bit-flip 0, parasite passage `frozen`, founder host genomes restored before contact.
Host `reproduction.enabled` stays true. This is not reproduction-off and not `freeze_host_genotypic_inheritance`.
`shuffled_labels` is not used. `shuffled_labels` is not a frozen genotype.
`constant_parasite`: parasite passage `frozen`, so parasite genotype composition is held.
Contact and the debit stay. Host bit-flip stays the structural rate. The host population is not deleted.
Passage `absent` is not used.

## Lag, horizon, and n

Probe seed: 9600 only. It is not a confirmatory history.
Exploratory budget: 24 generations, coevolve arm only, no lag grid.
Primary lag is `max(1, round(parasite census / mean seated newborns))`.
Turnover multiple: 3, the phase-3 multiple, not a contrast search.
Primary lag: 3.
Horizon: 10 generations.
Replacement generations: 3.173553719008264.
n: 12.
Seeds: 9601 through 9612 (9601, 9602, 9603, 9604, 9605, 9606, 9607, 9608, 9609, 9610, 9611, 9612).

## Importance and the minimum detectable effect

Importance for this estimand is undeclared. SUPPORTED is forbidden.
The Decaestecker gap of 0.10 is a different system and is not this engine's importance bound.
The probe was not used to invent an importance bound after a sign.
Planning sigma for claim A is 0.25 (at least 0.25).
Planning sigma for claim B is 0.5. It is not a probe reversal rate.
Precision targets, separate from importance: claim A 0.25, claim B 0.5.
MDE claim A: 0.22216378635389802. MDE claim B: 0.44432757270779605.
The minimum detectable effect is not the importance bound.
`MEASUREMENT_FLOOR` stays 12 and is not lowered.
`precision_met`: True.

## Run rules

CPU workers at most 7.
Output: `runs/rq-mechanism-v2/phase5-coevolution`.
Raw archives are kept. A partial run is kept. A seed is not replaced.
Extinction and fixation stay in the archive.
Energy invariants are checked every generation. A real invariant failure stops the run.
Replay of the same confirmatory run is required. One-shot and resume must match.
Evolution, reproduction, and mutation are off on the replay copy.
If replay does not match, stop. That is a bug. Do not edit the engine after the verdict.

```json
{
  "horizon": 10,
  "importance_bound": null,
  "mde_a": 0.22216378635389802,
  "mde_b": 0.44432757270779605,
  "measurement_floor": 12,
  "n": 12,
  "primary_lag": 3,
  "probe_generations": 24,
  "probe_seed": 9600,
  "seeds": [
    9601,
    9602,
    9603,
    9604,
    9605,
    9606,
    9607,
    9608,
    9609,
    9610,
    9611,
    9612
  ],
  "workers": 7
}
```

No confirmatory number has been computed.
