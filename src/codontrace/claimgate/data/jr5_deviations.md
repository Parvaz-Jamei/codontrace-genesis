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

## 2026-11-09 (recorded late): E1 regression re-pin after the selfing length fix

- Reason: commits adda4f3 and 203984b changed only `tests/test_jr5_phase2b_self_mode.py`. Before the selfing length fix a selfed child was the parent's even homolog alone, so genomes halved each selfed generation and the E1 regression fit was taken on shrinking genomes. Selfing is now two meioses of one parent plus fusion (length kept). The male-count regression pins were refit on the confirmatory setup (outcross fee 0.0, diploid_meiosis on). Locked PREREG.md, constants, and the other plan files were not edited.
- Old pins: outcross arm `(0.79900229, -0.09470521)` only.
- New pins: outcross arm `(0.80725957, -0.32454182)`; self arm `(-3.91594154, -0.16053908)` (zero males, intercept at the bias-reduced lower bound).
- Files: DEVIATIONS.md (this entry), record.json.
- Record digest: `577bd4ac643c02da6ab53976afbdbc216cacce95b5c68ba2a348c24cd226c382` -> `577bd4ac643c02da6ab53976afbdbc216cacce95b5c68ba2a348c24cd226c382`
- Runs: no JR5 run has started, the pilot included, so no endpoint moves to exploratory. This is the author's declaration. What the repository shows at this entry: no JR5 run script, campaign module or run output is committed (no path under `runs/` names JR5, and the only JR5 script is the E1 power simulation, which runs no engine arm).
