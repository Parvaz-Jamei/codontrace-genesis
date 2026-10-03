# Phase-3 lock

No measurement D has been computed.
No generation of seeds 9501, 9502, 9503, or 9504 has been run.
This file is the lock, written before any phase-3 measurement history.
`red_queen_proved` is false. This is not a Red Queen claim.
A positive D would not be Red Queen.

Code commit: `9a50ca2daca7da3c420dcff551f6e9c4531d58f7` on branch `rq/mechanism-v2`.
Nothing has been pushed, merged, or rebased.
`runs/rq-bidirectional-timeshift-01` is untouched and is not part of this commit.

## Genotypes

Chosen from the seed-9500 selection experiment, not from a measurement D.
Window A: `000000`
Window B: `111111`
Exemplar id A: `host-A-001`
Exemplar id B: `host-B-001`
Genome A: `101111000100000001000000`
Genome B: `101111000100000001111111`
Shared prefix: `101111000100000001`
Outcross cost A: 1.0
Outcross cost B: 1.0
Engine recognition gap (parasite window = A, one host): 1.0
That gap is the instrument difference, not D.

## Horizon

Conditioning generations: 7
Replacement generations: 2.3076923076923075
Mean seated newborns on the 9500 probe: 26.0
Census: 60
Turnover multiple, pre-declared: 3
one antagonist advance per engine generation
The horizon was not chosen from the sign of D.

## Seeds and rules

Measurement histories: 9501, 9502, 9503, 9504.
Selection seed 9500 is not a measurement history and is not reused as one.
Forbidden and not used: 9099, 9101-9104, 9201-9224, 9301-9304, 9401, structural pilot seeds 601, 602, 603.
Importance for this estimand is undeclared. SUPPORTED is forbidden. The minimum detectable effect is not the importance bound.
SUPPORTED is forbidden.
`MEASUREMENT_FLOOR` stays 12 and is not lowered. It is not the importance bound.
If a locked seed is missing or unmeasurable, the verdict is BLOCKED_MEASUREMENT, not a negative on the reduced sample.
Unmeasurable is missing, not zero.
CPU workers at most 4.
Output: `runs/rq-mechanism-v2/phase3-frequency/`.
Raw archives are kept. A partial run is kept. The seed is not replaced.
`red_queen_proved` stays false.


## Why these two genomes

The seed-9500 selection scored every unordered pair among the 16 structural recognition windows (120 pairs) with the engine infectivity path: one parasite whose window equals the first host, one host of each window, birth ATP. The score is that infectivity difference. It is not D. Costs were the outcross mating fee on the full tape. Both genomes use outcross codon 001, so that fee is 1.0 on each. The shared prefix is the program, the quiet kappa codon, and the mating codon (18 bits). Only the last 6 bits differ. The maximum engine gap was 1.0. Several complementary pairs tied. The tie break is lexicographic order of the window pair, which selects 000000 and 111111. Exemplar ids are host-A-001 and host-B-001. Every other A or B seat uses the same genome with its own id. Census is 60, not the structural 64, because 64 is not divisible by 5 and an exact 80/20 mix would leave parasites unseated or use a non-integer count. 48 seats are A and 12 are B when A is common, and the reverse when B is common. Index modulo 5 equal to 4 is the rare genome. Virulence, steal fraction, mutation rate, maintenance cost, and birth ATP stay the structural values.

## Why seven generations

A parasite generation is one `advance` inside one engine generation. The 9500 probe held the 80/20 mix for 24 generations, which is the pre-declared probe length, not the horizon. Mean seated newborns were 26 on a census of 60, so one replacement time is 60/26 generations. The multiple 3 was declared in code before this probe. The horizon is the ceiling of 3 times that replacement time, which is 7. Every probe generation had contacts, so the debit path is measurable. The horizon was not shortened or lengthened after a sign. No measurement D has been computed.

## Branches

From one shared parasite initial state, three branches:
- common_a: 80% A and 20% B, parasite passage coevolve
- common_b: 20% A and 80% B, parasite passage coevolve
- locked: 80% A and 20% B, parasite passage frozen. A third host frequency was not part of the design. The control is the genotype lock, not another mix. The assay reports this branch beside D and does not substitute it into D.

Host composition is reinstalled before contact. There is no score for being common. Contact, resource bolus, birth ATP, maintenance, and seat cap are the same on every branch. Parasite evolution is on only in the first two branches.

No measurement D has been computed.
