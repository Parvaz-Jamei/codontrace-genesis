# Reciprocal validity literature

Opened before any reciprocal-validity mechanism change and before any confirmatory number. Hall et al. 2011 full text was not obtained. Sci-Hub was not used. No quotation below is taken from a page that was not opened.

## Papkou et al. 2019

Andrei Papkou, Thiago Guzella, Wentao Yang, Svenja Koepper, Barbara Pees, Rebecca Schalkowski, Mike-Christoph Barg, Philip C. Rosenstiel, Henrique Teotónio, and Hinrich Schulenburg. "The genomic basis of Red Queen dynamics during rapid reciprocal host–pathogen coevolution." Proceedings of the National Academy of Sciences 116(3): 923-928. DOI 10.1073/pnas.1810402116.

Copy opened: https://www.ncbi.nlm.nih.gov/pmc/articles/PMC6338873/ (fetched as HTML on 2026-10-04).

What was read, not paraphrased into a new claim. The abstract on that page says a time-shift experiment is one "in which a focal host or pathogen is tested against a coevolved antagonist from the past, present, or future". The significance statement on that page says "distinct selective processes underlie rapid coadaptation in the two antagonists". The results section says "We ensured comparability of results for the two antagonists by assaying the same trait for both, namely, the effect on host egg production". The design on that page used 16 biological replicates and 23 transfers, and it says generation time was controlled "only for the host". Under aFDS, that page says "the faster-evolving partner (usually the pathogen) is expected to have higher fitness in the presence of the contemporaneous antagonist than those from the evolutionary past or future". Under RSS, "the focal organism produces high fitness toward its past and low fitness toward its future antagonist". Host genomic allele trajectories on that page "do not match the phenotypic pattern".

Prediction used here. The same infectivity trait is scored for both antagonists on a past/present/future by past/present/future matrix. A reversal of two fixed genotypes is not that matrix. A positive infectivity number is not, by itself, a change in the direction of host selection.

Engine path. `infectivity` calls `replay_archived_contact`. The matrix is filled from archived host and parasite rosters. It does not retune virulence, steal fraction, mutation, or the birth ATP.

Control. `adaptation_cut` and `constant_parasite` are scored with the same function as the coevolve arm. The absent passage is the no-parasite baseline for the host selection loop, not a pressure estimate.

Estimand. Two continuous margins of the same trait: contemporary parasites against contemporary hosts, minus the mean of the past and future parasite rosters on those hosts; and contemporary parasites against contemporary hosts, minus the mean of the past and future host rosters. A missing roster stays missing.

Limit. Their 23 transfers and their egg counts are not this engine's horizon and not its importance bound. Host genomic mismatch with the phenotypic pattern is a warning that one locus reversal is not the whole claim. `red_queen_proved` is not set from a margin.

## Brockhurst and Koskella 2013

Michael A. Brockhurst and Britt Koskella. "Experimental coevolution of species interactions." Trends in Ecology & Evolution 28: 367-375. DOI 10.1016/j.tree.2013.02.009.

Copy opened: the submitted version at https://eprints.whiterose.ac.uk/id/eprint/77995/1/Brockhurst_Koskella_TREE_2013.pdf.

What was read. They define a time-shift experiment as studies in which samples "are collected through time (either artificially by cryogenic freezing, or naturally by the deposition of resting stages) and then resurrected to challenge against coevolving partners from past, contemporary and future time-points." Figure 2 says a pattern in which "fitness is lowest against populations from the future and highest against those from the past might indicate arms race dynamics" whereas "peak fitness against contemporary populations or those from only the recent past is more in line with negative frequency dependent selection," and "the exact pattern will depend on the lag in evolutionary response." Box 1 separates coevolution from one-sided evolution, where one partner is held in evolutionary stasis, and from single-species evolution. They cite Gandon and coauthors for local adaptation and for the lag, but those Gandon pages were not opened here, so no Gandon sentence is quoted.

Prediction used here. The primary pattern is the contemporary peak on both sides of one trait (fluctuating selection), not an arms-race sign and not a two-genotype reversal. The lag is taken from measured replacement times. It is not chosen after the confirmatory sign.

Engine path. Coevolve passage is the reciprocal treatment. `constant_parasite` holds the parasite roster (frozen reseat). `adaptation_cut` holds founder host windows and sets host bit-flip to 0. Absent passage removes the antagonist.

Control. Those three are the controls. A rebuilt population, if one is required, is named `rebuilt_population` and is not called a hold.

Estimand. The matrix margins above. Exploratory cells of the matrix are not a second primary.

Limit. The review states patterns. It does not give a numeric importance bound for this engine.

## Brown, Cai, and DasGupta 2001

Lawrence D. Brown, T. Tony Cai, and Anirban DasGupta. "Interval Estimation for a Binomial Proportion." Statistical Science 16(2): 101-133. DOI 10.1214/ss/1009213286.

Copy opened: the text returned from https://projecteuclid.org/journalArticle/Download?urlId=10.1214%2Fss%2F1009213286 and the matching excerpt at https://core.ac.uk/download/pdf/132271468.pdf (the PDF itself returned HTTP 403 to a direct download; the excerpt in the index was the opened text). The University of Pennsylvania repository PDF used in PHASE6_LITERATURE.md timed out on this pass.

What was read. Section 3.1.1 gives the Wilson interval as the inversion of the score test that uses the null standard error, their equation (4):

CI_W = (X + κ²/2) / (n + κ²) ± (κ n^{1/2} / (n + κ²)) (p̂q̂ + κ²/(4n))^{1/2}

They recommend the Wilson interval or the equal-tailed Jeffreys interval for small n. The standard Wald interval is the one whose coverage they call poor near 0 and 1.

Prediction used here. A reversal rate, and the rate of histories with both margins positive, use this Wilson interval, including 0/n and n/n. The Wald standard error is stored and is not the p-value. The continuous margin is not this interval.

Engine path. `wilson_interval` in `rq_mechanism_v2_phase5.py`, already the equation (4) implementation. This phase does not replace it.

Control. A boolean `reversal` label is not a count of successes.

Estimand. k successes in n independent valid histories. n is not the number of repeated rows.

Limit. The interval is not an importance bound. Importance left undeclared still forbids SUPPORTED.

## Decaestecker et al. 2007

Ellen Decaestecker, Sabrina Gaba, Joost A. M. Raeymaekers, Robby Stoks, Liesbeth Van Kerckhoven, Dieter Ebert, and Luc De Meester. "Host–parasite 'Red Queen' dynamics archived in pond sediment." Nature 450: 870-873. DOI 10.1038/nature06291.

Copy opened: https://lirias.kuleuven.be/bitstream/handle/123456789/137612/Decaesteckeretal_2007.pdf (the institutional PDF).

What was read. Hosts from a sediment layer were exposed to parasite isolates "from the next layer down, the same layer and the next layer up", called past, contemporary, and future. The fetched text says temporal variation in parasite infectivity "changed little over time" while virulence increased. The same fetch is truncated in the Fig. 1 sentence; the only infectivity figure recovered in that sentence is 0.57, in a comparison with contemporary parasites. A clean 0.65 versus 0.55 sentence was not recovered on this pass. PHASE1.md already recorded that contrast. It is not re-derived here and it is not used as a threshold.

Prediction used here. Past, contemporary, and future are three times, not two. The contrast recorded in PHASE1.md is not this engine's importance bound.

Engine path. None of their sediment layers are simulated. The three times are generations inside one archive.

Control. Not a second confirmatory of their pond.

Estimand. Not their infectivity percentages.

Limit. Full typesetting of the Nature PDF was not rechecked against the journal site. Numbers above are from the institutional PDF that was fetched. They are not imported as thresholds.

## What this note does not do

It does not set `red_queen_proved`. It does not choose a seed, a horizon, or a lag from a confirmatory mean. No confirmatory number has been computed.
