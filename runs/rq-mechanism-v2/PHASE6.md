# Phase 6

`red_queen_proved` is false. No phase-6 confirmatory was run. The horizon rule refused to shorten 70 generations into the budget of 16. That refusal is in `PHASE6_LOCK.md`. It is not a Red Queen result and it is not a positive claim.

## Instrument fixes, before the prelim that finished

Absent passage did not append `pre_selection_signatures`. Seed 9801 stopped at generation 1 with `preselection-checkpoint-length`. The checkpoint now records the roster that absent passage removes, with zero seats and zero contact income.

The same branch returned before `contact_pair_records` grew. Seed 9805 stopped with `contact-record-length`. An empty contact record is appended. No debit is added.

A `STOP` file already on disk used to write `COMPLETE` for the next seed. Seed 9802 has that false `COMPLETE` and an empty archive. The runner now sets the failure to `stopped` and does not write `COMPLETE`. Seed 9806 has `REASON.txt` and no `COMPLETE`.

Those trees were not deleted and those seeds were not rerun.

## Short run

Seed 9803. Two generations. Arms `coevolve`, `adaptation_cut`, `constant_parasite`. One-shot and resume matched on `scientific_body` before `COMPLETE`, because `failed` is null. Replay of `archive.jsonl` compared 6 generations, 0 unmeasurable, 0 mismatches. `red_queen_proved` is false. Output: `runs/rq-mechanism-v2/phase6-short/`.

## What was not run

No confirmatory. Seeds 9811 through 9822 were not opened. Workers were not retuned. `MEASUREMENT_FLOOR` was not lowered. The population cap, virulence, steal fraction, and birth ATP were not changed.

## Budget

The registered budget is now 70, the horizon the max-of-three-times rule already returned from the phase6-prelim-3 measurements. The move lets that rule run. It is not a parameter tune. Seeds, lag, thresholds, and population parameters are unchanged. Papkou et al. 2019, Proceedings of the National Academy of Sciences, DOI 10.1073/pnas.1810402116, ran 23 host transfers and controlled generation time for the host, not the parasite. The 2010 Caenorhabditis elegans and Bacillus thuringiensis coevolution experiment, PMC2867683, used 48 host generations. Brockhurst and Koskella 2013, Trends in Ecology and Evolution, time-shift the interaction over evolutionary time, not over a budget shorter than one host replacement. The horizon is not shortened to 16. The refusal under the old budget stays in `PHASE6_LOCK.md`. No confirmatory number has been computed.
