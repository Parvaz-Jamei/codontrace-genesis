# Phase-4 lock

No fitness number has been computed.
No generation of seeds 9501, 9502, 9503, or 9504 has been run for this fitness assay.
This file is the lock, written before any phase-4 fitness history.
`red_queen_proved` is false. This is not a Red Queen claim.
A positive fitness link is not Red Queen. A negative fitness link is not Red Queen.

Code commit: `f7f6da4a45964c552673f31eb1961860185f212b` on branch `rq/mechanism-v2`.
Nothing has been pushed, merged, or rebased.
`runs/rq-bidirectional-timeshift-01` is untouched and is not part of this commit.

## Fitness definition

ATP loss is not host success and is not this score.
Each branch starts with equal counts of host A and host B on the shared food patches,
the shared resource bolus, the shared birth ATP, and the shared reproduction cost.
`L_A` is the fraction of hosts alive after the horizon whose founder class is A.
Founder class is the class installed on that id, or the class reached by walking `parent_id`.
Founders are not counted as births. `L_B` is the fraction whose founder class is B.
The walk uses births' parent ids. It does not use ATP.
If nobody is alive, or any living id cannot be walked to A or B, `L_A` and `L_B` are null.
Null is not zero.
If one class is absent and the other is present, the shares are the measured 0 and 1.
That zero is a counted absence in the living census, not a missing seed.
Relative advantage `R = L_A - L_B`.
`F = R(parasite from that seed's phase-3 common_a archive) - R(parasite from that seed's phase-3 common_b archive)`.
The absent-passage advantage is reported beside F and is not written into F.
Prediction, not a support bound: F below zero would mean the parasite conditioned while A was common
reduced A's relative advantage compared with the parasite conditioned while B was common, and the converse.
The sign is not an importance bound.
Survival is the count of deaths of each class: an id that was alive at the start of the generation
or born during it, and is not alive after the generation. Contact removal does not write `death_tick`;
the id difference is the death record. Reproduction is the count of lineage births of each class.
Those counts are not an ATP drop.

## Extinction

A class is extinct in a generation when its living count after that generation is 0.
The archive line is still written. The history is not deleted. The seed is not replaced.
The run keeps stepping through the locked horizon while the engine accepts the step.
An empty terminal census makes the share null, not zero.
If a locked seed is missing or its F is null, the verdict is BLOCKED_MEASUREMENT,
not a negative on the reduced sample.
Unmeasurable is missing, not zero.
`n_locked`, `n_used`, and `dropped_seeds` are reported.

## Horizon

Fitness generations: 7
Recorded replacement generations: 2.3076923076923075
Recorded mean seated newborns: 26.0
Recorded census: 60
Turnover multiple, pre-declared: 3
The replacement time 60/26 and the multiple 3 are the phase-3 record.
They were not remeasured for this contrast and were not chosen from the sign of F.
One engine generation is one `run_generations` step: the host life-loop, then contact, then one parasite advance.
generation-1 host births are inside step_generation, which runs before contact, so a one-generation horizon cannot be a post-contact census.
The horizon was not chosen from the sign of F.

## Seeds and genomes

Measurement histories: 9501, 9502, 9503, 9504.
Hosts were not re-selected from a fitness sign. They are the phase-3 lock.
Exemplar id A: `host-A-001`
Exemplar id B: `host-B-001`
Genome A: `101111000100000001000000`
Genome B: `101111000100000001111111`
Window A: `000000`
Window B: `111111`
Equal counts: 30 of A and 30 of B. Census 60, so every parasite seat from the phase-3 census can be paired.
Index modulo 2 equal to 0 is A. The first two ids are the exemplars.
Virulence, steal fraction, maintenance, birth ATP, bolus, and `MEASUREMENT_FLOOR` are not retuned.

## Control and mutation

Three branches, each from that seed's own phase-3 parasites:
- `common_a`: parasite list from `common_a/archive.jsonl`, passage `coevolve`, parasite mutation rate 0.
- `common_b`: parasite list from `common_b/archive.jsonl`, passage `coevolve`, parasite mutation rate 0.
- `absent`: passage `absent` (`PASSAGE_ABSENT`). `_apply_hp_env_contact` returns no contacts and no debit.
Host `reproduction.enabled` stays true. Host `parent_atp_cost` stays the booted cost.
Host `bit_flip_rate` is 0. That is recognition mutation off, not reproduction off.
`freeze_host_genotypic_inheritance` is not used. The absent branch is not a pure evolution control.
`shuffled_labels` is not used. `shuffled_labels` is not a frozen genotype.
Passage `frozen` is not used. The frozen reseat would replace conditioned windows with founders.
The absent roster is loaded only so `advance` has a population to remove. It is not a third genotype treatment.

## Rules

Importance for this estimand is undeclared. SUPPORTED is forbidden. The minimum detectable effect is not the importance bound.
SUPPORTED is forbidden.
`MEASUREMENT_FLOOR` stays 12 and is not lowered. It is not the importance bound.
CPU workers at most 7.
Source archives are read-only. They are not modified, deleted, or rewritten:
- `runs/rq-mechanism-v2/phase3-frequency/by_seed/seed9501/common_a/archive.jsonl`
- `runs/rq-mechanism-v2/phase3-frequency/by_seed/seed9501/common_b/archive.jsonl`
- `runs/rq-mechanism-v2/phase3-frequency/by_seed/seed9502/common_a/archive.jsonl`
- `runs/rq-mechanism-v2/phase3-frequency/by_seed/seed9502/common_b/archive.jsonl`
- `runs/rq-mechanism-v2/phase3-frequency/by_seed/seed9503/common_a/archive.jsonl`
- `runs/rq-mechanism-v2/phase3-frequency/by_seed/seed9503/common_b/archive.jsonl`
- `runs/rq-mechanism-v2/phase3-frequency/by_seed/seed9504/common_a/archive.jsonl`
- `runs/rq-mechanism-v2/phase3-frequency/by_seed/seed9504/common_b/archive.jsonl`
Output: `runs/rq-mechanism-v2/phase4-fitness/`.
Raw archives are kept. A partial run is kept. The seed is not replaced.
`red_queen_proved` stays false.

No fitness number has been computed.
