# Phase 6

`red_queen_proved` is false. The horizon rule refused to shorten 70 generations into the budget of 16. That refusal is in `PHASE6_LOCK.md`. It is not a Red Queen result and it is not a positive claim.

The budget was later raised to 70 so that same rule could run. The confirmatory archive is `runs/rq-mechanism-v2/phase6-coevolution/`. Numbers below are copied from `summary.json`.

## Instrument fixes, before the prelim that finished

Absent passage did not append `pre_selection_signatures`. Seed 9801 stopped at generation 1 with `preselection-checkpoint-length`. The checkpoint now records the roster that absent passage removes, with zero seats and zero contact income.

The same branch returned before `contact_pair_records` grew. Seed 9805 stopped with `contact-record-length`. An empty contact record is appended. No debit is added.

A `STOP` file already on disk used to write `COMPLETE` for the next seed. Seed 9802 has that false `COMPLETE` and an empty archive. The runner now sets the failure to `stopped` and does not write `COMPLETE`. Seed 9806 has `REASON.txt` and no `COMPLETE`.

Those trees were not deleted and those seeds were not rerun.

## Short run

Seed 9803. Two generations. Arms `coevolve`, `adaptation_cut`, `constant_parasite`. One-shot and resume matched on `scientific_body` before `COMPLETE`, because `failed` is null. Replay of `archive.jsonl` compared 6 generations, 0 unmeasurable, 0 mismatches. `red_queen_proved` is false. Output: `runs/rq-mechanism-v2/phase6-short/`.

## Confirmatory

Seeds 9811 through 9822. Horizon 70. Budget 70. Primary lag 3. Workers 7. `n_locked` 12. `n_used` 12. `stopped` is null. `failed` is empty. `replay_matched` is true. Each replay compared 210 generations, with 0 unmeasurable and 0 mismatches. One-shot and resume matched on `scientific_body` before `COMPLETE`.

Paired verdict on the coevolve arm: INCONCLUSIVE. Mean 0.018122859505747057. Lower -0.0023058732090795488. Upper 0.038551592220573666. One-sided p 0.03839158853444875. n 12.

Oscillation verdict: NEGATIVE. Continuing cycles 2 of 12 measurable. Mean 0.16666666666666666. Wilson upper 0.4480308624940672, which is below the null 0.5. Importance is null. `supported_forbidden` is true. `red_queen_proved` is false.

No bug stop. `MEASUREMENT_FLOOR` was not lowered. The population cap, virulence, steal fraction, and birth ATP were not changed.

## Budget

The registered budget is now 70, the horizon the max-of-three-times rule already returned from the phase6-prelim-3 measurements. The move lets that rule run. It is not a parameter tune. Seeds, lag, thresholds, and population parameters are unchanged. Papkou et al. 2019, Proceedings of the National Academy of Sciences, DOI 10.1073/pnas.1810402116, ran 23 host transfers and controlled generation time for the host, not the parasite. The 2010 Caenorhabditis elegans and Bacillus thuringiensis coevolution experiment, PMC2867683, used 48 host generations. Brockhurst and Koskella 2013, Trends in Ecology and Evolution, time-shift the interaction over evolutionary time, not over a budget shorter than one host replacement. The horizon is not shortened to 16. The refusal under the old budget stays in `PHASE6_LOCK.md`. No confirmatory number has been computed.
