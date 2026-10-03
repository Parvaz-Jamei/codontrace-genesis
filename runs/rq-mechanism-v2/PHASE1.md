# Phase 1 validity review

Branch `rq/mechanism-v2`, created from `9dba28f1bc101be607ee31bc98645a9edb97a8c8` (main after PR 102). `9dba28f` is an ancestor. Nothing was pushed, merged, or rebased. The old confirmatory tree `runs/rq-bidirectional-timeshift-01` was not committed and was not modified. Its verdict stays `NEGATIVE_IN_MODEL`. `red_queen_proved` stays false. This note is not timestamped `20261003T151015`.

Mechanism fixes: `a810be697a0545d401e9bef15242a436ae403753`.
This document is the following commit on the same branch.

No new confirmatory was run. Seeds, horizon, lag, thresholds, and `maintenance_cost` (0.15) were not retuned. No A/B frequency panel and no fitness link.

## Literature

What was opened, and what was not. Quotes below are from the copies that were fetched. Page numbers are given only where that copy prints them.

1. Decaestecker et al. 2007, DOI 10.1038/nature06291. Opened the KU Leuven Lirias copy of the Nature letter (Vol 450, 6 December 2007, doi:10.1038/nature06291), not the nature.com HTML. *Daphnia magna* / *Pasteuria ramosa* sediment time-shift. The letter states: "On average, infectivity was higher when Daphnia were exposed to contemporary (average infectivity 0.65) parasites than to parasites from previous (average infectivity 0.55) growing seasons" and "average parasite infectivity was lower when Daphnia clones were confronted with future parasites (average infectivity 0.57)". Table 1 reports a time-shift effect (deviance 5.89, P = 0.05) and a clone-depth × time-shift interaction (P < 0.0001). The model they compare with is a matching-allele matrix. Nature.com was not the copy read. The supplementary PDF was not opened.

2. Hall et al. 2011, DOI 10.1111/j.1461-0248.2011.01624.x. Full text was not read. The Wiley page was not opened as full text. What was read is the University College Cork publication record, which prints the abstract and the journal line *Ecology Letters* 14(7), pages 635–642, July 2011. The abstract says arms-race dynamics "decelerate over time" because of "increasing costs of generalism", while "fluctuating selection on individual host and parasite genotypes was maintained". Organisms named there: *Pseudomonas fluorescens* SBW25 and phage SBW25Φ2. No page-internal quotation is claimed. Papkou et al. 2019, which was read in full on PMC, cites this paper as Hall et al., *Ecol Lett* 14:635–642, for bacteria–phage time-shifts in which arms-race dynamics can give way to fluctuating selection. That citation is not a substitute for the Hall full text.

3. Zaman et al. 2014, DOI 10.1371/journal.pbio.1002023. Opened the PMC full text, PMC4267771. Avida hosts and parasites. The frozen treatment holds parasite genotypes at the frequencies from 250,000 updates and assigns each newborn parasite a random genotype from that set. The text says those hosts "evolved significantly higher complexity than in the treatment without parasites" but "did not reach as high a level of complexity as when the parasites coevolved". Replay of past parasite frequencies, without a response to the current hosts, likewise stayed below reciprocal coevolution. Data: Dryad doi:10.5061/dryad.485qq. This is the source for not calling a static or shuffled antagonist a full coevolution treatment, and for not calling a measurement freeze a pure evolution control.

4. Papkou et al. 2019, DOI 10.1073/pnas.1810402116. PNAS HTML was not the copy read. Opened PMC6338873. *C. elegans* and *B. thuringiensis* MYBT18247. Time-shifts of transfer-10 hosts and pathogens against past, present, and future antagonists were "consistent with aFDS". Controls were passaged without the antagonist. Pathogen adaptation tracked copy number of a 113-kb plasmid carrying `cry6B` (up at transfer 12, back by transfer 22). The host genomic pattern did not match single-locus aFDS; the paper says the host response "likely involve[s] selective responses at more than one locus". Sequence data: NCBI BioProject PRJNA475030.

How this is used. The time-shift estimand (performance of one time against a partner from another time, with no evolution during the score) is the Decaestecker / Papkou design, not a new mechanism. Hall is only an abstract-level warning that an arms-race label and a fluctuating-selection label are different claims; it is not used as a fitted model. Zaman is the control-language source: a frozen or replayed antagonist is not reciprocal coevolution. Nothing outside that reading was imported as a confirmatory rule. No exploratory reanalysis of the old 24-seed verdict was run.

## Raw data

`runs/rq-bidirectional-timeshift-01/OMITTED.txt` says the raw archives were left out because the set is about 700 MB, and it lists local paths. It does not give a URL. No archive URL was invented. The independent raw-data audit is incomplete. The old verdict file was not rewritten.

## Bugs on 9dba28f

Checked on that tree with `PYTHONPATH=src python3` before the mechanism edits. `python` is not installed; `python3` is.

1. RNG. Reproduced. `StructuralRQArm.run_generations` called `step_generation(seed=self.seed + self.tick_index + 1)`. 9201 at generation 2 and 9202 at generation 1 both yield 9203. The archive field `host_step_seed` used the same sum.

2. Snapshot identity. Reproduced. `read_snapshot` checked only the content digest. A copy with `seed` changed and the digest recomputed was accepted. Snapshots did not carry schema, run id, config digest, or code/design version. Archive acceptance treated line count as enough.

3. Controls and assay. Mixed.
   - Reproduced as a labeling defect, not as the literal phrase "pure evolution control" (that phrase was absent). Arm C set `reproduction.enabled` false and `host_inheritance` to `"frozen"`. Turning reproduction off stops births as well as bit flips, so it is not a pure evolution control.
   - `shuffled_labels` was already the passage string. It was not explicitly denied as a frozen genotype. That denial was missing, not a second passage mode.
   - Founders as births: not reproduced. Already absent. At boot, host lineage does not count founders as births, and parasite founders have `parent_id is None` and `born_generation` 0. The archive now also drops any generation-0 no-parent record. Locked by test, not by a new birth rule.
   - Assay: reproduced. Cartesian `infectivity` returned 0.5 while `replay_archived_contact` on 2 hosts and 1 parasite had 1 contact, debit 1.2, affinity 1.0.
   - Restart: reproduced. `restart_clean` deleted `confirmatory/` and stripped `phase=2` lines from `live.log`.
   - Workers: reproduced. `run_confirmatory` used `os.cpu_count()` with no cap of 4.
   - MDE: reproduced. `pilot_dispersion` stored the minimum detectable effect under `practical_effect`, and the verdict used that number as the scientific threshold.

4. Stats. Reproduced. `one_sample_t([0.2] * 24, 0.05)` returned `p_one_sided == 0.0`, `reject` true, and `decide_verdict` returned `SUPPORTED_IN_MODEL`. The old test asserted that support. The test was changed to the correct gate. It was not weakened to stay green.

5. Affinity note. Reproduced as a comment, not as a wrong numeric score. `graded_affinity` already equals matching bits / 6 on the 6-bit window. `AntagonistPopulation.maintenance_cost` treated mean affinity 0.5 as given and set maintenance to 0.15. The number was not changed.

## Fixes

### 1. RNG

Prediction. Two histories must not share a random stream just because `seed + generation` collides, and resuming a history must continue the same stream.

Engine path. Timeshift `build_arm` sets `stream_root` to `RQ-BIDIRECTIONAL-TIMESHIFT-01` and `stream_history` to `str(seed)`. `run_generations` then calls `open_stream` for subsystems `host-step` and `passage` at the 1-based generation. `derive_stream_seed` hashes canonical JSON `{version, root, history_id, subsystem, generation}` with SHA-256. It does not add the seed to the generation.

Control that removes the alternative. The negative control is the old sum: 9201+2 equals 9202+1, and the new integers are not those sums and are not equal to each other. Arms use policy `shared-derivation-separate-objects`: the arm name is not in the hash, and each call returns its own `RNGManager`. A draw on one object does not advance the other. Seed order and one process versus `ProcessPoolExecutor(max_workers=4)` write the same per-seed archive bytes. One-shot `run_generations(3)` matches `run_generations(1)` then `run_generations(2)`. `capture_rng_and_births` / `restore_rng_and_births` restore RNG state and `child_serial` / `known_unit_ids`.

Source. The collision is an engine-identity bug, not a biological claim. The domain separation is ordinary stream hygiene, labeled as software validity, not as a new coevolution mechanism.

Estimand. The timeshift stream changes which mutations and pairings a new run would draw. It does not rewrite a sealed structural trajectory: if `stream_root` is None, the arm still uses `seed + tick_index + 1`. That legacy mixer is intentional and is not a claim that 9201/g2 and 9202/g1 are independent on that old path.

Limit. Existing confirmatory archives were produced with the old mixer. They were not regenerated. A future run is a different random experiment, not a replay of `20261003T151015`.

### 2. Snapshot, archive, and one run

Prediction. A file with a correct content digest but the wrong experiment, schema, history, seed, arm, generation, run id, config digest, or code/design version is not the requested observation.

Engine path. `write_snapshot` still hashes the body. `read_bound_snapshot` checks the digest and then the identity fields. `validate_archive` requires schema `rq-timeshift-archive/1` and exactly one row per arm and generation, not merely the right line count. `assert_artifacts_one_run` requires `initial.json`, `COMPLETE`, and, if present, `verdict.json` to name the same `run_id`. `analyze` calls both and sets `archive_ok` false on failure. Historical pilot snapshots stay on digest-only `read_snapshot`. They are not pretended to pass the new gate.

Control. Positive: a complete identity snapshot loads. Negative: seed copy, arm A versus D, wrong generation, other run, other config digest, bad or missing schema, and a body edited under the old digest are rejected. An archive with two copies of arm A generation 1 and no arm D, same line count, is rejected.

Source. Software validity. Papkou and Decaestecker time-shifts are only interpretable if past and present samples are the ones named.

Estimand. Wrong identity no longer enters CH, CP, or S. Dropping a center is reported as `estimand_changed` and is not imputed as 0. If the estimand changed, or the importance bound was not declared, `SUPPORTED_IN_MODEL` is forced to `BLOCKED`.

Limit. The old run's snapshots do not carry the new identity fields. They were not rewritten. Scoring them with `analyze` would fail closed; that was not done.

### 3. Controls and assay

Prediction. The scored infectivity is the ATP the engine actually moves on its seat pairs, divided by virulence × steal fraction (8 × 0.15 = 1.2). An empty side is unmeasurable. A measurement freeze is not an evolution control.

Engine path. `infectivity` calls `replay_archived_contact`, which builds a scratch arm, turns host reproduction off only so the archived individuals are not replaced, and calls `_apply_hp_env_contact`. Pair count is `min(n_hosts, n_parasites)` with host rotation by `tick_index`. Debit is `min(available ATP, 1.2 × affinity)`. Credit is the engine `_credit`: `(EARNED_YIELD - PAIRING_COST) × paid` = `0.5 × paid`. Loss is the host ATP drop. Input lists are copied and compared after the call.

Control. Positive: 6 matching bits, ATP 48, debit 1.2, loss 1.2, credit 0.6, infectivity 1. Three matching bits give affinity 0.5 and debit 0.6. Zero matching bits give infectivity 0, which is measurable, not null. Negative: hosts `[000000, 000000, 111111]` and one parasite `111111` pair only the first host at tick 0, so infectivity is 0, not the cartesian mean 1/3. Swapping host order changes the seat result. ATP 0.3 clips a perfect match to 0.3. Empty populations return None, not 0. `control_statement` says arm C is not a pure evolution control and arm B `shuffled_labels` is not a frozen genotype. `restart_clean` moves `confirmatory/` to `retained/restart-<count>/` and copies `live.log` without stripping it. `MAX_WORKERS` is 4.

Source. Zaman: frozen and replayed parasites raised complexity above the no-parasite treatment but not to the reciprocal-coevolution level, so a static antagonist is not that treatment. The seat rule is the existing engine, not a new contact model.

Estimand. CH and CP now use seat infectivity. They are not the cartesian mean. Unequal censuses and order matter. Unmeasurable stays missing.

Limit. The scratch arm uses arm C's reproduction-off switch as a measurement freeze. That does not make arm C, in an evolutionary run, a pure evolution control. Host demography is stopped there. A control that keeps births and removes only selection was not built. That would be a new mechanism and was out of scope.

### 4. Stats

Prediction. A Student-t test with sample SE 0 has an undefined p-value. It does not support the contrast and does not, by a degenerate interval, prove a negative. Practical support is the one-sided lower bound against an importance bound. The MDE is a different number.

Engine path. `one_sample_t` returns `p_one_sided = None`, `reject = False`, `ci95 = None`, `se_zero = True` when SE is 0. NaN and infinity raise. `decide_verdict` returns `BLOCKED` if n < 12, then `INCONCLUSIVE` if SE is 0 or p is missing, then `SUPPORTED_IN_MODEL` only if every test rejects and its lower bound meets the importance bound. `pilot_dispersion` still stores `practical_effect` equal to the MDE so the old power-revision arithmetic has a number, and sets `practical_effect_role` to say that alias is not the importance bound, and `importance_bound: None`. `analyze` does not substitute the MDE when importance is undeclared.

Control. Positive: values `[0.30] * 12 + [0.50] * 12`, n = 24, importance 0.05. Mean and lower bound were recomputed with `statistics` and the locked df=23 critical value 2.3978750646571103, not by pasting the function's previous output. The lower bound is above 0.05 and below the mean, so support is real. An importance placed between the lower bound and the mean does not meet, which rejects the point-estimate rule. Negative: constant 0.2 is inconclusive, not supported. Constant −0.02 is inconclusive, not a negative. A non-constant negative sample with SE > 0 can be `NEGATIVE_IN_MODEL`. n = 11 is `BLOCKED`. Duplicate seeds are a history alias. A missing value changes the estimand and is not imputed as 0. Missing times and mis-paired arms raise.

Source. The zero-SE rule is ordinary sampling theory, not a biological retune. Decaestecker's time-shift P-value is a reminder that a reported P is not a proof of Red Queen; this code still sets `red_queen_proved` false on support.

Estimand. Support no longer fires from p = 0. Dropped histories are an estimand change (`mean of measurable histories only`). `n_used` is reported next to `n_locked`.

Limit. The importance bound is not declared (`None`). Support of a future confirmatory is blocked until an importance bound is locked from data that are not the confirmatory outcomes. The MDE remains a power quantity. No such lock was written here.

### 5. Affinity note only

Prediction. Mean affinity 0.5 is not a property of every population.

Engine path. `graded_affinity` is unchanged: three 2-bit sub-locus scores, which equal matching bits / 6. The comment on `maintenance_cost` now says that Binomial(6, 0.5) and mean 0.5 require independent uniform bits, and that an evolved population must be measured. The value stays 0.15.

Control. The test asserts the default is still 0.15. No historical run was restarted.

Source. Arithmetic of the window, labeled as an assumption. Not a new affinity function.

Estimand. None. The debit scale is still 1.2 times the measured affinity of the paired windows. The 0.5 figure is not used as an empirical mean.

Limit. The historical derivation of 0.15 used the unmeasured mean. That derivation is now marked as conditional. The parameter was not refit.

## Tests

Not `pytest -n 4`. The validity test itself opens a four-worker pool. Stacking pytest-xdist on that pool would exceed the cap of 4. Serial pytest is the equivalent that stays at 4. No test was marked `slow`; the file finishes in a few seconds, so a slow mark would be false. Unregistered `slow` marks in tests this phase did not touch were left as they were.

```
/tmp/ct-tools/bin/python -m pytest \
  tests/test_rq_mechanism_v2_validity.py \
  tests/test_rq_bidirectional_timeshift_confirm.py \
  -o addopts='--disable-plugin-autoload --import-mode=importlib' \
  --tb=no -rA
```

Result: 15 passed, 0 failed, 4.18s. Nine in `test_rq_mechanism_v2_validity.py`, six in `test_rq_bidirectional_timeshift_confirm.py`.

Ruff, on the touched files only:

```
/tmp/ct-tools/bin/ruff check \
  src/codontrace/genesis/rq_stream.py \
  src/codontrace/genesis/rq_bidirectional_timeshift.py \
  src/codontrace/genesis/rq_bidirectional_timeshift_confirm.py \
  src/codontrace/genesis/closed_loop_hp_arm01_structural_rq.py \
  src/codontrace/genesis/measurements/antagonist_population.py \
  tests/test_rq_mechanism_v2_validity.py \
  tests/test_rq_bidirectional_timeshift_confirm.py
```

All checks passed.

Mypy 2.4.0, `--strict --follow-imports=silent` on the five source files: `rq_stream.py` has no errors. The new stream, bound-snapshot, and infectivity-return lines have no errors. 86 errors remain inside those five files and were left. They are the old debt: `antagonist_pop` typed as `object` (attribute access on units, ledgers, windows, advance), mismatched `# type: ignore` codes on `list(object)` in `rq_bidirectional_timeshift.py`, a dict-append mismatch in `antagonist_population.py`, and the structural override / untyped-def / ellipsis items. A mypy run without `--follow-imports=silent` also reported 443 errors in 53 files because it followed the rest of the package. That package debt was not fixed. No blanket `# type: ignore` and no module-level mypy disable were added.

## What was not fixed

- Legacy structural arms with `stream_root is None` still mix `seed + tick_index + 1`. Sealed trajectories stay byte-identical. The collision remains on that path by design.
- `maintenance_cost` stays 0.15. Mean affinity of an evolved population was not measured.
- No new confirmatory, no unused-history campaign, no frequency panel, no fitness link.
- The old run was not reanalyzed and its files were not edited. Fingerprint of file size and mtime before and after the edits matched.
- Hall 2011 full text was not read.
- The ~700 MB raw archives have no published URL in `OMITTED.txt`. The independent raw-data audit is incomplete.
- Pre-existing mypy debt listed above.
- A pure evolution control that keeps host demography and removes only the evolutionary operator was not added.
