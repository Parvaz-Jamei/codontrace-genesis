# Phase-2 lock

Outcomes have not been observed. No generation of seeds 9301, 9302, 9303, or 9304 has been run. This file is the lock, written before any phase-2 generation. `red_queen_proved` is false. This is not a Red Queen claim.

Code commit: `4135792b278bc7eaaf460946bbb55a7ef29d301f` on branch `rq/mechanism-v2`. Nothing has been pushed, merged, or rebased. `runs/rq-bidirectional-timeshift-01` is untouched and untracked.

## Locked settings

- Output directory: `runs/rq-mechanism-v2/phase2-short/` only.
- Seeds, four fresh histories: 9301, 9302, 9303, 9304.
- Forbidden, and not used for this phase: 9099, 9101, 9102, 9103, 9104, 9201 through 9224, and structural `PILOT_SEEDS` (601, 602, 603).
- Horizon: 200 generations. This is `PHASE1_GENERATIONS` in `src/codontrace/genesis/rq_bidirectional_timeshift.py`. It is not 600. It will not be shortened or lengthened after a sign.
- `maintenance_cost` stays 0.15. Seeds, horizon, lag, thresholds, and `maintenance_cost` are not retuned after a sign.
- CPU workers at most 4.
- If one process and four workers disagree, or one-shot and resume disagree, stop. That is a bug, not a reason to retune.
- If a real invariant bug fires, stop that history, keep the partial archive, and record the reason. Do not delete the partial and do not replace the seed.
- Extinction, fixation, and zeros stay in the archive. Unmeasurable is missing, not zero. Do not impute.
- Not run, and not started by this lock: an A/B frequency panel, a fitness link, a new confirmatory, and any Red Queen claim.

## Arms

Same initial state for a given seed. Arms A-D are booted through `build_arm("A")`, which calls `StructuralRQArm.boot_structural(arm=copassaged, seed=seed)` and then sets the timeshift stream. Treatment flags are applied only after that boot. A direct `boot_structural` call was checked, in unit tests on seed 9401 only, to produce the same host and parasite founders (ids, windows, energy). 9401 is not a phase-2 history. No phase-2 seed was booted. The boot RNG was not retuned. The shared-boot guard is so a later arm-specific boot cannot split founders. The recorded RNG sharing policy below was not changed.

- A: both genotypes evolve. Host inheritance on (`transmit`). Parasite passage `PASSAGE_COEVOLVE`.
- B: host evolves. Parasite genotypic inheritance is frozen via `PASSAGE_FROZEN` / mode `"frozen"` (`AntagonistPopulation` mode `== "frozen"` and `_reseat_frozen`). This is not `shuffled_labels`. `shuffled_labels` is not a frozen genotype. The parasite population is not deleted. Contact and cost stay.
- C: parasite evolves (`PASSAGE_COEVOLVE`). Host genotypic inheritance is frozen via `freeze_host_genotypic_inheritance`, which turns host reproduction off and `bit_flip_rate` to 0. This is not a pure evolution control. It does not delete the host population. Contact and cost stay. Parasites still reproduce.
- D: both of those cuts. Same labeling limits. Frozen does not delete the other side, contact, or cost.

Phase-1 `build_arm` still sets B and D to `shuffled_labels`. That confirmatory wording for 9201-9224 is not redefined. Phase-2 uses `build_phase2_arm` and `control_statement(..., phase=2)`.

## RNG policy

Timeshift arms use `stream_root` + `history_id=str(seed)` + subsystem + generation. The arm name is not in the hash. Each call returns a separate `RNGManager`. Arms must not share a mutable RNG object, and they do not. The recorded policy id is `shared-derivation-separate-objects`:

> Arms of one history derive host-step and passage streams from the same (root, history_id, subsystem, generation) tuple, so the draws offered at a generation do not depend on the arm label. Each arm constructs its own RNGManager. Arms do not share a mutable RNG object. Independent histories differ in history_id. Order of histories is not an input.

`stream_root` is `RQ-BIDIRECTIONAL-TIMESHIFT-01`. Subsystems are `host-step` and `passage`. Derivation is `derive_stream_seed` / `open_stream` (`rq-stream/1`), not seed plus generation.

## Invariants

Every generation checks energy, id, parent, contact, birth/death, and archive fields through `invariant_status` and `archive_field_status`. A missing required field is a bug. Stop immediately. Keep the partial run and the reason.

## Replay

After the short run, and only after this lock is committed, replay contact-time populations from the archive with `replay_archived_contact` (evolution, reproduction, and mutation off) on an independent copy. Compare named engine fields `total_debit`, `credit`, `evolution`, `reproduction`, and `mutation` to the archived contact ATP and credit. Do not use a shortcut formula. One-shot `run_generations(200)` must match the resumed `run_generations(1)` path on `scientific_body`. One process and four workers must match on `archive.jsonl` and `initial.json` bytes.
