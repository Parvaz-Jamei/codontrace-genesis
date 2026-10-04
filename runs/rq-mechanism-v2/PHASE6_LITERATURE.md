# Phase 6 literature

Opened before the phase-6 code. No confirmatory number is in this note. Hall et al. 2011 full text was not obtained. Sci-Hub was not used.

## Brown, Cai, and DasGupta 2001

Lawrence D. Brown, T. Tony Cai, and Anirban DasGupta. "Interval Estimation for a Binomial Proportion." Statistical Science 16(2): 101-133. DOI 10.1214/ss/1009213286.

Copy opened: University of Pennsylvania repository PDF, https://repository.upenn.edu/bitstreams/c3690c8b-efaf-485b-a984-39cfc22aae13/download (the ScholarlyCommons posting of the Statistical Science article).

What was used. The Wald interval is the estimated-standard-error interval. The paper says its coverage "is poor for p near 0 or 1" and that the usual textbook caveats "are defective". Section 3.1.1 gives the Wilson interval, their equation (4), as the inversion of the score test that uses the null standard error. For small n they recommend the Wilson interval or the equal-tailed Jeffreys interval. Phase 6 uses the Wilson interval for a reversal count, including 0/n and n/n. The Wald standard error is stored and is not the p-value. A zero Wald standard error does not set that p-value to 0 and does not drop the boundary. The null for the reversal index is 0.5. The continuous claim-A mean is a different estimand.

## Papkou et al. 2019

Andrei Papkou, Thiago Guzella, Wentao Yang, Svenja Koepper, Barbara Pees, Rebecca Schalkowski, Mike-Christoph Barg, Philip C. Rosenstiel, Henrique Teotónio, and Hinrich Schulenburg. "The genomic basis of Red Queen dynamics during rapid reciprocal host–pathogen coevolution." Proceedings of the National Academy of Sciences 116(3): 923-928. DOI 10.1073/pnas.1810402116. PMC6338873.

Copy opened: https://www.ncbi.nlm.nih.gov/pmc/articles/PMC6338873/

What was used. The time-shift is "a focal host or pathogen is tested against a coevolved antagonist from the past, present, or future". They "assay the same trait for both" antagonists, "the effect on host egg production". The abstract that is on that page says "distinct selective processes underlie rapid coadaptation in the two antagonists". Phase 6 keeps one paired estimand and reports the host effect and the parasite effect separately. A diagnostic contrast is not added into that pair. A fitness number by itself is not scored as a change in the direction of selection. One sign change is not a continuing cycle.

The horizon is not taken from their transfer schedule, and it is not three times a parasite replacement time. Their result is not an importance bound.

## What was not opened

Hall et al. 2011, DOI 10.1111/j.1461-0248.2011.01624.x. Full text was not reached. The abstract-only limit recorded in PHASE1.md still stands. No quotation from a full text is used.

Decaestecker et al. 2007 was not re-fetched for this phase. The contemporary-versus-previous infectivity contrast already recorded in PHASE1.md is not redefined here.

## Engine facts used as the control, not as a paper

On the absent branch of phase 4b, seed 9501, generation 1, the archive has alive 34 and 30, births 4 and 0, deaths 0 and 0, contacts 0. The four child parent ids are host-A-001 through host-A-004. `PopulationState` is stepped in id order (`population.py`, the sorted organism loop). `STRUCT_SOFT_K` is 64 and the founder census is 60, so four seats are open. `two_fold_cost_sex` is false, so one chamber pair places two offspring. Two pairs of the earliest ids fill the cap. Food patches are 16 and the interleaved seats put 30 hosts of each class on patches, so the 34/30 gap is not a food headcount. Swapping the names, and not the windows, moves the four births to the class whose ids sort first. That is the rule. It was not retuned.

No population-model parameter was changed. The adaptation-cut hold no longer rebuilds a living id at the birth ATP. That is a bug fix of the instrument, not a new birth rule.
