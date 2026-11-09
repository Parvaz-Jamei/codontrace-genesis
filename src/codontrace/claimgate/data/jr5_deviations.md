# JR5 deviations

PREREG.md section 12: any change after the lock is logged here with the reason and the new record digest.

When the lock took effect: phase 1 was merged to main as 7d7ab8a (PR 130) on 2026-10-31 at 17:21 UTC+3. Edits to this folder before that merge were review of an unlocked draft. Every edit after it is logged below; the first entry was written late, on 2026-11-01, for edits that had been merged without one.

Record digest: `manifest.digest` in `record.json` over every plan file except this one. This file is also in the manifest, so it cannot name a digest that includes its own hash; `record.json` adds it on top. Each entry's old digest is the previous entry's new digest.

## 2026-11-01 (recorded late): phase 1 review changes merged after the lock

- Reason: fixes from the phase 1 review, merged in PR 133 (merge 73c3bff, 2026-11-01 00:36 UTC+3) after the lock without a log entry. They add the E1 simulation script and the bias-reduced fit, the sexes-on engine mode and the self-arm rules (like-for-like fecundity and ATP, no delayed selfing, male-free self arms, sex fixed for life), the outcross mating fee set to 0 with a report-only fee run, the realised-w pilot and its seed block, and the diploid fertilisation fix as a hard dependency.
- Commits: the 14 commits that `git log 7d7ab8a..73c3bff -- docs/prereg/jr5` lists, 8a9fac2 to d20a72b.
- Files: PREREG.md, MATING_TYPES_DESIGN_NOTE.md, RED_QUEEN_CLAIM_PATH.md, REFERENCES.md, jr5_prereg_constants.json, scripts/e1_power_sim.py (new), record.json.
- Record digest: `633aa9c84336e946fc7d8e3e2178acc658caeed791f5a484bbe7d0814264b757` -> `a4f76d603a21a02d523fbdba86966dfe7df9faf41ba0d01813ae53f29be44daa`
- Runs: no JR5 run has started, the pilot included, so no endpoint moves to exploratory. This is the author's declaration. What the repository shows at this entry: no JR5 run script, campaign module or run output is committed (no path under `runs/` names JR5, and the only JR5 script is the E1 power simulation, which runs no engine arm).

## 2026-11-01: diploid fertilisation fix pinned by merge commit and engine test

- Reason: the fill-in announced in PREREG.md section 4, made after PR 134 merged the fix as 4400e07. The text said the dependency was pinned by branch name until the merge, and that the merge commit and the node id of the engine test would then be added. This entry adds those two pins, ties the generation count to the engine test, and adds this file and the lock date.
- Files: PREREG.md, MATING_TYPES_DESIGN_NOTE.md, jr5_prereg_constants.json, DEVIATIONS.md (new), record.json.
- Record digest: `a4f76d603a21a02d523fbdba86966dfe7df9faf41ba0d01813ae53f29be44daa` -> `577bd4ac643c02da6ab53976afbdbc216cacce95b5c68ba2a348c24cd226c382`
- At e5cd2c0, before this file and the lock note in PREREG.md section 12 were added, the digest was `aede93c859df80d313de7f7e1b3aedf73d59cef4de52f6c0c8fe43e75e109e3f`.
- Runs: no JR5 run has started, the pilot included, so no endpoint moves to exploratory. This is the author's declaration. What the repository shows at this entry: no JR5 run script, campaign module or run output is committed (no path under `runs/` names JR5, and the only JR5 script is the E1 power simulation, which runs no engine arm).

## 2026-11-09 (recorded late): E1 regression re-pin after gamete fusion and the selfing length fix

- Reason: commits adda4f3 and 203984b changed only `tests/test_jr5_phase2b_self_mode.py`. Re-pin history, each step checked by re-running the fit at the commits named. Outcross arm (no selfing): `(0.79900229, -0.09470521)` on the 2b tip 8be79b1 with the old setup (outcross fee 1.0). Merging the gamete-fusion fix (4400e07) moved it to `(0.38787177, -0.00003415)` on that fee-1.0 setup; the setup change to the registered PREREG section 4 confirmatory outcross fee 0.0 then gave `(0.80725957, -0.32454182)`. The selfing length fix did not move the outcross pin. Self arm: only this pin moved with the selfing length fix (before that fix a selfed child was the parent's even homolog alone, so the genome halved; selfing is now two meioses of one parent plus fusion, length kept). The self arm has zero males, so its intercept sits at the bias-reduced lower bound. Selfing pays no outcross fee, so the fee setting does not enter the self arm. Locked PREREG.md, constants, and the other plan files were not edited. The digest line below is the plan digest over every manifest file except this one, so it stays `577bd4ac...` when only DEVIATIONS.md changes; `record.json` manifest.digest (which includes this file) moves from `1e1fe67f...` (at f4748ac, before this entry) to the refreshed value written with this entry.
- Old pins: outcross arm `(0.79900229, -0.09470521)` only (taken at outcross fee 1.0).
- New pins: outcross arm `(0.80725957, -0.32454182)`; self arm `(-3.91594154, -0.16053908)` (zero males, intercept at the bias-reduced lower bound).
- Files: DEVIATIONS.md (this entry), record.json.
- Record digest: `577bd4ac643c02da6ab53976afbdbc216cacce95b5c68ba2a348c24cd226c382` -> `577bd4ac643c02da6ab53976afbdbc216cacce95b5c68ba2a348c24cd226c382`
- Runs: no JR5 run has started, the pilot included, so no endpoint moves to exploratory. This is the author's declaration. What the repository shows at this entry: no JR5 run script, campaign module or run output is committed (no path under `runs/` names JR5, and the only JR5 script is the E1 power simulation, which runs no engine arm).

## 2026-11-09: correction of the 2b entry point of the gamete-fusion fix and the self-pin causes

- Reason: the previous entry named merge commit `4400e07` as the step that moved the outcross E1 pin to `(0.38787177, -0.00003415)` on the fee-1.0 setup. That is where the gamete-fusion fix landed on main (PR 134). On the phase 2b line the same fix first entered at `9aec9b2` (merge of `origin/fix/diploid-fertilisation` into `local/2b-self-diploid`); the intermediate and fee-0.0 outcross pins are otherwise unchanged. The previous entry also said the self arm pin moved only with the selfing length fix. The self pin likewise carries the fusion-fix effect: before fusion a selfed child was a single homolog (length halved), and after `9aec9b2` / the length fix the selfed child is two meioses plus fusion (length kept), so both the length repair and the fusion path shape that pin. Locked PREREG.md, constants, and the other plan files were not edited.
- Files: DEVIATIONS.md (this entry), record.json.
- Record digest: `577bd4ac643c02da6ab53976afbdbc216cacce95b5c68ba2a348c24cd226c382` -> `577bd4ac643c02da6ab53976afbdbc216cacce95b5c68ba2a348c24cd226c382`
- Runs: no JR5 run has started, the pilot included, so no endpoint moves to exploratory. This is the author's declaration. What the repository shows at this entry: no JR5 run script, campaign module or run output is committed (no path under `runs/` names JR5, and the only JR5 script is the E1 power simulation, which runs no engine arm).

## 2026-11-09: selfing at merge 9aec9b2 and the commit that made selfing two meioses plus fusion

- Reason: the previous entry says that after `9aec9b2` / the length fix the selfed child is two meioses plus fusion. `9aec9b2` is a merge (of `origin/fix/diploid-fertilisation` into `local/2b-self-diploid`) and did not change selfing: at `9aec9b2` a selfed child was still the parent's even homolog alone, 9 of 18 bits. Two meioses of one parent plus fusion, with the length of 18 bits kept, came with commit `c36e637`, the selfing length fix. Self-arm E1 fit (intercept, slope; bias-reduced, the setup of the test), re-run at each commit: `(-3.83763587, -0.11716161)` at `8be79b1`, before the merge (selfed length 9); `(-3.85058832, -0.13561451)` at `9aec9b2`, after the merge (selfed length still 9); `(-3.91594154, -0.16053908)` at `c36e637` (selfed length 18), which is the registered self pin. The merge moved the self fit without changing selfing; `c36e637` then changed selfing and gave the pin. The outcross fee does not enter the self arm: each of the three fits is the same at fee 1.0 and fee 0.0. The outcross values in the two entries above are unchanged. The heading of the previous entry, which is not on main, was reworded at this entry to drop a dash; its text is otherwise unchanged. From this entry on, the gate and the verdict pin the sha256 of this file up to the end of this entry, and the first entry's text and old digest, so earlier entries cannot be edited or removed; later entries can only be appended. Locked PREREG.md, constants, and the other plan files were not edited.
- Files: DEVIATIONS.md (this entry and the previous heading), record.json.
- Record digest: `577bd4ac643c02da6ab53976afbdbc216cacce95b5c68ba2a348c24cd226c382` -> `577bd4ac643c02da6ab53976afbdbc216cacce95b5c68ba2a348c24cd226c382`
- Runs: no JR5 run has started, the pilot included, so no endpoint moves to exploratory. This is the author's declaration. What the repository shows at this entry: no JR5 run script, campaign module or run output is committed (no path under `runs/` names JR5, and the only JR5 script is the E1 power simulation, which runs no engine arm).
