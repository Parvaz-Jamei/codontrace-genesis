# Phase 2 short run

Branch `rq/mechanism-v2`. Nothing was pushed, merged, or rewritten. `runs/rq-bidirectional-timeshift-01` was not modified and was not committed. `red_queen_proved` is false. This note does not call the result Red Queen.

## Commits

- Mechanism code, before any phase-2 generation: `4135792b278bc7eaaf460946bbb55a7ef29d301f`
- Lock, also before any phase-2 generation: `55f82233a716a9e855a6413d697b60911250c233`
- The process ran with `HEAD` at the lock commit. `summary.json` records that hash as `code_commit`.

`55f82233a716a9e855a6413d697b60911250c233` is a descendant of `4135792b278bc7eaaf460946bbb55a7ef29d301f` and an ancestor of the commit that adds this note and the archives.

## Locked settings

From `runs/rq-mechanism-v2/PHASE2_LOCK.md`, not changed after the run:

- Output: `runs/rq-mechanism-v2/phase2-short/`
- Seeds: 9301, 9302, 9303, 9304
- Forbidden and not used: 9099, 9101, 9102, 9103, 9104, 9201–9224, structural pilot seeds 601, 602, 603
- Horizon: 200 generations (`PHASE1_GENERATIONS`, not 600)
- `maintenance_cost` 0.15, not retuned. Seeds, horizon, lag, and thresholds were not retuned.
- Workers at most 4
- Arm A: host inheritance on, parasite `PASSAGE_COEVOLVE`
- Arm B: host evolves; parasite genotype frozen with `PASSAGE_FROZEN` / mode `"frozen"`, not `shuffled_labels`
- Arm C: parasite `PASSAGE_COEVOLVE`; host reproduction off and `bit_flip_rate` 0 via `freeze_host_genotypic_inheritance`. Not a pure evolution control. Host population not deleted.
- Arm D: both cuts. Same labeling limits.
- Phase-1 `build_arm` B/D remains `shuffled_labels` for the 9201–9224 design.
- RNG: `stream_root` `RQ-BIDIRECTIONAL-TIMESHIFT-01`, `history_id=str(seed)`, subsystem `host-step` or `passage`, generation. Arm name is not in the hash. Separate `RNGManager` objects. Policy `shared-derivation-separate-objects`. Not changed.
- Shared founders: each arm boots through `build_arm("A")` before cuts. No boot retune.

## Run

Four seeds, four arms, 200 generations. The four-worker pass finished with no failure (wall 405.6 s). The one-process pass then finished with no failure (wall 1348.8 s). Every seed has `by_seed/seed93xx/COMPLETE` with `generations=200 red_queen_proved=false`. There was no partial stop and no invariant stop.

Scientific record kept: `runs/rq-mechanism-v2/phase2-short/workers4/` (archives, `initial.json`, `live.log`, `trajectory.jsonl`) and `summary.json`. About 59 MB. The one-process archives matched and were removed after that match. Their SHA-256 hashes remain in `summary.json` under `worker_compare.hashes`.

## Replay, resume, workers

Replay matched. Comparison was named fields from `replay_archived_contact` on an independent JSON copy of the archived contact-time populations, not archive bytes and not a second formula: `total_debit`, `credit`, and the flags `evolution`, `reproduction`, and `mutation` (all false). `total_debit` was also compared to the sum of archived contact ATP. Each seed: 800 generations compared (4 arms × 200), 0 unmeasurable, 0 mismatches. 3200 generations in total.

One-shot versus resume matched. Inside each history, before `COMPLETE`, `run_generations(1)` repeated for 200 generations was compared to one `run_generations(200)` on `scientific_body` (host ids and ATP, parasite ids, windows, energy, parents, contact counts, debits, paid ATP, incomes, births, deaths, tick). No mismatch, so no retune.

One process versus four workers matched. Byte comparison of `archive.jsonl` and `initial.json` for all four seeds (8 files). `worker_compare.matched` is true and `mismatches` is empty. Live logs were not part of that comparison.

## Invariants

All 3200 lines in `workers4/live.log` have `invariant=ok`. No history was stopped. Extinction, fixation, and zeros would have stayed in the archive. None of the replayed generations had an empty side, so none were recorded as unmeasurable. Nothing was imputed.

## What was not run

No A/B frequency panel. No fitness link. No new confirmatory. No Red Queen claim. `red_queen_proved` is false in `summary.json` and in every archive row that carries the field. Seeds, horizon, lag, thresholds, and `maintenance_cost` were not changed after the sign of any result.
