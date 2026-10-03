# Phase-4b lock

No fitness number has been computed.
No generation of seeds 9501, 9502, 9503, or 9504 has been run for this phase-4b fitness assay.
This file is the lock, written before any phase-4b fitness history.
`red_queen_proved` is false. This is not a Red Queen claim.
A positive fitness link is not Red Queen. A negative fitness link is not Red Queen.
A nonzero F is not Red Queen.

Code commit: `d91b88a2496c16ef55b7eb012091cdaf40751d19` on branch `rq/mechanism-v2`.
Nothing has been pushed, merged, or rebased.
`runs/rq-bidirectional-timeshift-01` is untouched and is not part of this commit.
The rejected run stays at `runs/rq-mechanism-v2/phase4-fitness/`. It is not deleted and its seeds are not changed.

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
The absent control is passage absent, not a pure evolution control. Host reproduction stays enabled.
Prediction, not a support bound: F below zero would mean the parasite conditioned while A was common
reduced A's relative advantage compared with the parasite conditioned while B was common, and the converse.
The sign is not an importance bound.
Survival is the count of deaths of each class. Reproduction is the count of lineage births of each class.
Those counts are not an ATP drop.

## Extinction

A class is extinct in a generation when its living count after that generation is 0.
The archive line is still written. The history is not deleted. The seed is not replaced.
An empty terminal census makes the share null, not zero.
If a locked seed is missing or its F is null, the verdict is BLOCKED_MEASUREMENT,
not a negative on the reduced sample.
Unmeasurable is missing, not zero.
`n_locked`, `n_used`, and `dropped_seeds` are reported.

## Horizon

Fitness generations: 9
The horizon is not the parasite replacement time 60/26 and not the ceiling of 3 times that time.
It was not chosen from the sign of F. No fitness number has been computed.
Opening runtime ATP is the structural birth ATP, 48.
One contact debit is virulence 8.0 times steal fraction 0.15 times graded affinity.
Affinity is at most 1, so the per-generation debit cap is 1.2.
The life-loop applies basal maintenance 0.05 at each of 2 ticks, when that amount is payable.
After the outcross and recognition windows are silenced, the program is EAT_LUMEN 0.8, COPY_SELF 8.0, WAIT 0.1.
The cursor starts at 0 and advances 2 codons per generation, including a codon whose full cost is not payable.
The death account credits no food. The resource bolus is not placed on that account.
Evaluated on that account, balance after the life-loop and then after a 1.2 debit:
- generation 1: 48 - 8.9 = 39.1, then 37.9
- generation 2: 37.9 - 1.0 = 36.9, then 35.7
- generation 3: 35.7 - 8.2 = 27.5, then 26.3
- generation 4: 26.3 - 8.9 = 17.4, then 16.2
- generation 5: 16.2 - 1.0 = 15.2, then 14.0
- generation 6: 14.0 - 8.2 = 5.8, then 4.6
- generation 7: COPY_SELF 8.0 is not payable; 4.6 - 0.9 = 3.7, then 2.5. Still alive.
- generation 8: 2.5 - 1.0 = 1.5, then 0.3. Still alive.
- generation 9: COPY_SELF 8.0 is not payable; 0.3 - 0.2 = 0.1, then the debit takes the last 0.1 and the balance is 0.
Death is first reachable at generation 9. Generation 7 leaves 2.5.
The life-loop on the assay path does place a 20.0 bolus on each food patch before the step.
When EAT_LUMEN collects that bolus the balance rises, so the fed path is not the death bound.
The bolus is not turned off to create a death or to make F nonzero.
The locked horizon is 9 because that is the first generation of the no-food maximum-debit account at which death is reachable.
An accepted birth is a separate way for the census to move. The horizon was not shortened to the first birth.

## Seeds and genomes

Measurement histories: 9501, 9502, 9503, 9504.
Hosts were not re-selected from a fitness sign. They are the phase-3 lock.
Parasites stay the phase-3 frequency-panel archives for those seeds. Those archives are read only.
Exemplar id A: `host-A-001`
Exemplar id B: `host-B-001`
Genome A: `101111000100000001000000`
Genome B: `101111000100000001111111`
Window A: `000000`
Window B: `111111`
Equal counts: 30 of A and 30 of B. Census 60.
Index modulo 2 equal to 0 is A. The first two ids are the exemplars.
Virulence, steal fraction, maintenance, birth ATP, bolus, mutation rate, and `MEASUREMENT_FLOOR` are not retuned.

## Control and mutation

Three branches, each from that seed's own phase-3 parasites:
- `common_a`: parasite list from `common_a/archive.jsonl`, passage `coevolve`, parasite mutation rate 0.
- `common_b`: parasite list from `common_b/archive.jsonl`, passage `coevolve`, parasite mutation rate 0.
- `absent`: passage `absent` (`PASSAGE_ABSENT`). `_apply_hp_env_contact` returns no contacts and no debit.
Host `reproduction.enabled` stays true. Host `parent_atp_cost` stays the booted cost.
Host `bit_flip_rate` is 0. That is recognition mutation off, not reproduction off.
The birth chamber is on, because the outcross locus requires it. That is not a virulence change.
`freeze_host_genotypic_inheritance` is not used. The absent branch is not a pure evolution control.
`shuffled_labels` is not used. `shuffled_labels` is not a frozen genotype.
Passage `frozen` is not used.
Each branch stores its own archive hash. The common_a digest is not written onto the other branches.

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
Output: `runs/rq-mechanism-v2/phase4b-fitness/`.
Do not write into `runs/rq-mechanism-v2/phase4-fitness/`.
Raw archives are kept. A partial run is kept. The seed is not replaced.
`red_queen_proved` stays false.

No fitness number has been computed.
