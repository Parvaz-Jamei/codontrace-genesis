# HE03 ablation verification — independent reproduction on PR #63

Product: CodonTrace Genesis. Date: 2026-09-24 (Asia/Tehran).

Branch `pr63`, head commit `370cb2cae1723e87bc2abff86c4d19f6c332e36a`.

Module under test: `src/codontrace/genesis/hard_experiment_03.py`. The campaign
ran against a working-tree revision whose raw bytes hash to
`aa845b9f9c4aa09ac172d0583eb8e0481d23fe4763ae3d46d85ee4f011829909`; that hash was
recorded by every runner at import time and is identical in all three.

Role: Expert A (digital-evolution empiricist) acting as independent verifier.
No source file, test file or pinned artifact was modified for this report.

**Revision note, and a limitation on it.** The working tree was not frozen while
this work ran: other contributors edited it between 14:00 and 16:58. The
campaign's byte hash `aa845b9f…` matches neither the committed PR #63 head blob
for that path (`2b2d3652…` as stored, `fe39862f…` as checked out with the
repository's `core.autocrlf=true` and `* text=auto`), nor that blob for any
other local or remote ref, so the exact pre-campaign byte content cannot be
recovered from the repository and the campaign cannot be tied to a commit by
hash. What can be said:

- The measured values are pinned to the algorithm, not to a commit, by exact
  agreement with independent probe runs on the same seeds and geometry made
  separately in this session: seed 1000 `cost_high` D_sym `0.0369351046` at
  n = 28 and `channel_off` `0.0307564295` at n = 36, and seed 1001 `cost_high`
  `0.0111763135`. Those runs used a different harness on a possibly different
  byte state and returned identical numbers to ten decimal places, which shows
  the sampling and metric code was unchanged across those states.
- The code-reading findings below were made on the committed PR #63 head, by
  reading the file and the `git diff main...pr63` patch. The only working-tree
  change to that file observed afterwards adds a `charged` guard to
  `_extract_switch_stats`; it cannot affect trace sampling, the Gorelick matrix,
  the paired contrasts or the isolation path, and for the ten seeds reported
  here every switch record was charged, so realized cost equals switches times
  configured cost exactly in all 40 arm-seed cells and no number below changes
  under it.
- Nothing else in the file was observed to change, but because the pre-campaign
  bytes are unrecoverable I cannot prove that by hash. Treat the byte-level
  provenance of the campaign as unverified, and the algorithmic content as
  corroborated by the agreement described above.

---

## 0. Verdict

**VERDICT: STILL WRONG-SIGNED.**

The ablation contrast is `cost_high` mean D_sym against `channel_off` mean
D_sym, paired over the ten pilot seeds. Two numbers decide it.

1. With the arms' unequal trace sizes left in place, exactly as the campaign
   code computes it: mean paired difference **+0.00731219338**, positive in
   **10 of 10** seeds, Holm-adjusted exact sign-flip p = **0.005859375**. On
   its own this reads as right-signed, and this is the number the production
   artifact reports.
2. With the sample size equalised — the same contrast, both arms rarefied to
   the common n — the mean paired difference is **−0.03518272531**, positive in
   **0 of 10** seeds. The chance-corrected estimator agrees: adjusted mutual
   information gives **−0.04841818649**, positive in **0 of 10** seeds, under
   both the unadjusted and the equal-n comparison.

The positive sign in (1) is an artefact of unequal sampling, not a mechanism
effect. The ablation is not honestly signed, and the pilot artifact's
right-signed result should not be read as evidence for the intended causal
story.

A second finding is more serious than the sign itself:

**The switch-cost manipulation is not realized as a behavioural change.** In
every one of the ten pilot seeds the arms `cost_0`, `cost_moderate` and
`channel_off` produced *identical* (individual x task) trace multisets, and
`cost_high` and `isolation_probe` produced a second identical multiset. There
are two behavioural states in the pilot, not five. The cost gradient is not one
of the variables that separates them: charging 0.0, 6.5–7.0 or 9.0–10.0 ATP of
switch cost per seed leaves the recorded task trace bit-for-bit unchanged in the
0.0 and 6.5–7.0 cases.

---

## 1. What was run, and how

The pilot campaign is ten seeds (1000–1009) at 24 ticks and population 8, five
arms per seed, fifty engine runs in total. One arm run takes roughly 183 s of
one core on this machine, so the campaign is about 2.5 core-hours. A single
sequential invocation was started, measured, and then stopped under the
project's CPU-coordination rule; the campaign reported here was produced by
three processes each owning a disjoint set of seeds, with the campaign object
then assembled through the production assembly code path.

Assembly detail, because it matters for trust: the harness replaces only
`hard_experiment_03._run_arm` with a cache lookup and then calls the real
`run_hard_experiment_03(seeds=..., scale="pilot")`. Arm summaries, manipulation
checks, paired contrasts, the Holm step-down, the decision rule and the campaign
digest therefore all come from unmodified production code. The only wrapped
functions were pure readers — `_extract_task_samples`, `_solo_scores_for_isolation`
and `_group_scores_for_isolation` — whose return values were also recorded so
that the raw matrices survive in the artifact.

Commands, in order:

```text
# lock check (worktree bytes, LF-normalised bytes, and the git blob)
python -c "hashlib.sha256 of <file>, of <file>.replace(CRLF,LF), and of git cat-file blob HEAD:<file>"

# environment and API surface actually installed
python -c "importlib.metadata.version for numpy/scipy/scikit-learn/pytest/ruff/codontrace"
python -c "inspect.signature for _run_arm, _extract_task_samples, gorelick_nmi, run_isolation_assay, paired_effect_size, bootstrap_ci_paired, exact_sign_flip_permutation_p, holm_correction"

# campaign, three seed-disjoint processes
python -u he03_worker.py "1000,1001,1002,1003" he03_run_a.jsonl
python -u he03_worker.py "1004,1005,1006"      he03_run_b.jsonl
python -u he03_worker.py "1007,1008,1009"      he03_run_c.jsonl

# production assembly of the campaign object
python -u he03_assemble.py "he03_run_[abc].jsonl" he03_pilot_10seed.json

# equal-n and bias-aware treatment of the same matrices
python -u he03_analyze.py

# sequential 2-seed reference, for cross-checking the assembled digest
python -c "run_hard_experiment_03(seeds=(1000,1_001), scale='pilot')"

# tests
python -m pytest tests/test_hard_experiment_03.py tests/test_claimgate_he03_adapter.py -q
python -m pytest -q
```

The runner and analysis scripts are scratch files in the operating system's
temporary directory, not repository files. The raw matrices they produced are
reproduced in Appendix A so that the equal-n and chance-corrected comparisons
can be repeated by anyone without re-simulating anything.

Campaign identity: digest
`3dd1b51b32c096c650525f88c3e6298e724c2d6a14a1a44a2db6ce81d88c55ba`,
preregister digest `e8cd1f1dd744d6d31f65b68fb0e73ce31d9856ff1f613c3e44f2e459dd86b157`,
protocol digest `5853551405c0b533470f3bfde1c9c6babf76cac46f357250ceb49bcf6298690d`.

---

## 2. Search record (required before acting)

### 2.1 Literature

- **Gorelick, Bertram, Killeen, Fewell (2004)**, "Normalized mutual entropy in
  biology: Quantifying division of labor", *American Naturalist* 164(5):677–682,
  doi:10.1086/424968. Verified against the Arizona State University research
  record (title, four authors, volume, issue, pages, month, DOI) and its
  abstract, which states: "We divide Shannon's mutual entropy by marginal
  entropy to quantify division of labor, rendering it robust over changes in
  number of individuals or tasks."
  <https://experts.azregents.edu/en/publications/normalized-mutual-entropy-in-biology-quantifying-division-of-labo>
  What it licenses: a normalized mutual-information measure of division of
  labour that is comparable across different numbers of individuals and tasks.
  What it does **not** license: treating a plug-in estimate of that measure as
  bias-free at the sample sizes used here. The paper's justification is about
  the *number* of categories, not about finite-sample bias, and I found no
  statement in the accessible text correcting for the latter. The preregistered
  formula `D_sym = I(X;Y)/sqrt(H(X)H(Y))` is implemented exactly as specified
  (`src/codontrace/genesis/metrics/division_of_labor.py`, lines 135–138).
- **Goldsby, Dornhaus, Kerr, Ofria (2012)**, "Task-switching costs promote the
  evolution of division of labor and shifts in individuality", *PNAS*
  109(34):13686–13691, doi:10.1073/pnas.1202233109. The published article is
  paywalled and could not be retrieved (publisher and several indexes refused);
  verified instead through the Dryad data record deposited for that paper, which
  carries the abstract and the supplementary treatment list.
  <https://zenodo.org/records/4932183>
  Two details from that record matter for signing anything here. First, the
  paper's central outcome is the *Shannon mutual information* among tasks and
  individuals across switch costs of 0, 25 and 50 (their Table 2), not the
  normalized D_sym used here, so the repo's primary metric is a normalized
  relative of their outcome, not their outcome. Second, their isolation claim is
  qualified: "In many cases, under high task-switching costs, individuals cease
  to be able to perform tasks in isolation, instead requiring the context of
  other group members."
  What it does **not** license: a claim that switch costs raise D_sym at
  pure-Python scale, or that a two-state trace difference of the size seen here
  is the Goldsby effect.
- **Vinh, Epps, Bailey (2010)**, "Information Theoretic Measures for Clusterings
  Comparison: Variants, Properties, Normalization and Correction for Chance",
  *JMLR* 11(95):2837–2854. Verified at
  <https://jmlr.csail.mit.edu/papers/v11/vinh10a.html>. This is the source of
  the chance-corrected adjusted mutual information used below as an independent
  estimator. Its own abstract warns about exactly this situation: correcting
  information-theoretic measures for chance is important "especially when the
  data size is small compared to the number of clusters present therein".
- First-order plug-in bias of mutual information: the correction term
  `(K-1)(L-1)/(2 n ln 2)` for K individual values, L task values and n samples
  is the standard Miller–Madow style term, used here only as a diagnostic
  reference magnitude (see section 6). I did not verify a primary source for the
  constant to my own satisfaction and therefore cite no DOI for it.

No citation in this report was invented. Everything not verified above is
listed in section 11.

### 2.2 Current code and versions actually installed

Verified live, not from memory:

| Item | Value |
|---|---|
| Python | 3.14.4 |
| numpy | 2.4.4 |
| scipy | 1.17.1 |
| scikit-learn | 1.8.0 |
| pytest | 9.1.1 |
| ruff | 0.16.8 |
| `codontrace` distribution in site-packages | 0.3.0b1 (**stale**) |

A reproduction hazard worth recording. Site-packages contains a non-editable
copy of `codontrace` at version 0.3.0b1 with 103 modules under `genesis/` and
**no** `hard_experiment_03.py`. Any script that imports `codontrace` *before*
putting the repository's `src` directory first on the path silently receives
that stale copy. My first probe failed exactly this way with an `ImportError`.
The test suite is safe because `pyproject.toml` sets
`pythonpath = ["src", "."]`, but ad-hoc runners must guard the path themselves.
Every runner used here asserted that the imported module resolved to
`<repo>/src/codontrace/genesis/hard_experiment_03.py` and recorded that fact.

Signatures checked live: `run_hard_experiment_03(seeds=None, *, scale, tick_count,
population)`, `_run_arm(*, seed, arm, tick_count, population)`,
`gorelick_nmi(individual_tasks)`, `run_isolation_assay(*, group_scores,
solo_scores, config=None)`, `bootstrap_ci_paired(...)`,
`exact_sign_flip_permutation_p(...)`, `holm_correction(p_values)`,
`normalized_mutual_info_score(labels_true, labels_pred, *,
average_method='arithmetic')`,
`adjusted_mutual_info_score(labels_true, labels_pred, *,
average_method='arithmetic')`.

---

## 3. Lock checks

The three pinned artifacts hash byte-identically to their pins **on the
LF-normalised bytes**:

| Artifact | Pin | Result |
|---|---|---|
| `docs/hard_experiment_01/results_v7.json` | `35bb593604438797755e5e7b28af4d1371992a6181a403d08005f7f45421cbd6` | match |
| `docs/claimgate/risk_bar.json` | `4dbe4aa3a6ef8e771f180d2a6589c64b0dd5ffebe0aa73703a7256c17d771cd7` | match |
| `docs/claimgate/biomedical_study.json` | `9685f2fbafb21477d977dfa0c0bf73e02bea81d084e7605978ea25c47bf5ddce` | match |

Note on method, because a naive byte hash disagrees: this checkout materialises
those files with CRLF endings, so a raw byte hash of the working tree gives
`4a5987c2…`, `b7091921…` and `2e519363…` respectively. The pinned values are the
LF-normalised content, and they equal `sha256` of `git cat-file blob HEAD:<path>`
exactly for all three files. The pins are intact; the apparent mismatch is a
checkout artefact.

`git diff main...pr63 --stat` touches four files — the HE03 module, two test
files and one brainstorm document — and none of the three pinned artifacts.

Pre-registration digest: the campaign records
`e8cd1f1dd744d6d31f65b68fb0e73ce31d9856ff1f613c3e44f2e459dd86b157`, which is
the full-file digest of `docs/HARD_EXPERIMENT_03_PREREG.md` and matches the
working tree and the committed blob. The value printed inside that document,
`eef3469f…`, is the digest of its content *up to* the `## Document digest`
heading; I confirmed that convention reproduces the printed value exactly. Both
digests are internally consistent; there is no preregistration integrity
failure.

---

## 4. Pilot campaign results (ten seeds, production assembly)

### 4.1 Per-arm means

| Arm | mean D_sym | mean switches | mean trace n | mean folded n | mean cost realized (ATP) | mean terminal ATP | mean isolation drop |
|---|---:|---:|---:|---:|---:|---:|---:|
| `cost_0` | 0.0087601705 | 27.3 | 37.1 | 91.7 | 0.00 | 4.2650 | — |
| `cost_moderate` | 0.0087601705 | 27.3 | 37.1 | 91.7 | 6.83 | 4.1050 | — |
| `cost_high` | 0.0160723639 | 19.3 | 29.1 | 67.7 | 9.65 | 4.2422 | — |
| `channel_off` | 0.0087601705 | 0.0 | 37.1 | 37.1 | 0.00 | 4.2650 | — |
| `isolation_probe` | 0.0160723639 | 19.3 | 29.1 | 67.7 | 9.65 | 4.2422 | **0.0** |

"Folded n" is the sample size the pilot_v1 construction would have used, i.e.
trace samples plus both endpoints of every recorded switch. It is reported so
that the sampling asymmetry is visible in the artifact rather than only in
prose.

Three arms share one D_sym mean to ten decimal places. That is not a rounding
coincidence: section 7 shows the underlying matrices are identical.

### 4.2 Paired Holm contrasts, exactly as the code reports them

| Contrast | mean Δ | dz | 95% CI | p raw | p Holm | claim downgraded |
|---|---:|---:|---|---:|---:|---|
| `cost_high − cost_0` | +0.00731219338 | 7.38844 | [0.006533321235, 0.007728746260] | 0.001953125 | 0.005859375 | no |
| `cost_moderate − cost_0` | 0.00000000000 | 0.0 | [0.0, 0.0] | 1.0 | 1.0 | yes |
| `cost_high − channel_off` | **+0.00731219338** | 7.38844 | [0.006533321235, 0.007728746260] | 0.001953125 | 0.005859375 | no |

Gates and claim dictionaries as returned by the module:

```text
summary: CodonTrace Genesis hard_experiment_03_task_switch_dol scale=pilot
         claim_ceiling=runtime_observation assay_failed=False cleared_for_research=False
gates:   overall_pass=true
         assay.pass=true
         ordinal_cost0_le_moderate_le_high.pass=true
         schema.pass=true
         cleared_for_research=false
claim:   claim_ceiling=runtime_observation, assay_failed=false,
         decision_rule_passed=false, collective_intelligence=false,
         collective_intelligence_candidate=false, intelligence=false, agi=false,
         tokyo_type1_passed=false, modes_passed=false, avida_replacement=false
decision_rule_failures: ["scale_not_research",
                         "collective_intelligence_candidate_refused"]
```

The claim ceiling is unchanged, the candidate flag is refused and the decision
rule still fails closed. Note however that
`ablation_contrast_wrong_sign_or_null` — present in the pilot_v1 failure list —
is **absent** here. Section 10 returns to that.

### 4.3 Per-seed D_sym

| seed | cost_0 | cost_moderate | cost_high | channel_off | isolation_probe |
|---:|---:|---:|---:|---:|---:|
| 1000 | 0.0307564295 | 0.0307564295 | 0.0369351046 | 0.0307564295 | 0.0369351046 |
| 1001 | 0.0031258042 | 0.0031258042 | 0.0111763135 | 0.0031258042 | 0.0111763135 |
| 1002 | 0.0052303002 | 0.0052303002 | 0.0102373099 | 0.0052303002 | 0.0102373099 |
| 1003 | 0.0033024435 | 0.0033024435 | 0.0109780503 | 0.0033024435 | 0.0109780503 |
| 1004 | 0.0033024435 | 0.0033024435 | 0.0109780503 | 0.0033024435 | 0.0109780503 |
| 1005 | 0.0031258042 | 0.0031258042 | 0.0111763135 | 0.0031258042 | 0.0111763135 |
| 1006 | 0.0033024435 | 0.0033024435 | 0.0109780503 | 0.0033024435 | 0.0109780503 |
| 1007 | 0.0033024435 | 0.0033024435 | 0.0109780503 | 0.0033024435 | 0.0109780503 |
| 1008 | 0.0290277886 | 0.0290277886 | 0.0361100825 | 0.0290277886 | 0.0361100825 |
| 1009 | 0.0031258042 | 0.0031258042 | 0.0111763135 | 0.0031258042 | 0.0111763135 |

Seven of the ten seeds return one of three repeated values per arm, so the
effective number of distinct traces is much smaller than the nominal n = 10.
The exact sign-flip test treats the ten pairs as exchangeable, which they are,
but it does not know that most pairs carry duplicate information.

---

## 5. The two numbers that decide the verdict

Paired across the ten seeds, `cost_high − channel_off`:

| Estimator | mean Δ | seeds positive | p raw (exact sign-flip) | Holm |
|---|---:|---:|---:|---:|
| Repo plug-in D_sym, unequal n (as the campaign reports it) | **+0.00731219338** | 10 / 10 | 0.001953125 | 0.005859375 |
| Repo plug-in D_sym, equal-n rarefied to common n = 28–31 | **−0.03518272531** | 0 / 10 | 0.001953125 | — |
| Repo plug-in D_sym, symmetric rarefaction, both arms to n = 24 | −0.02698443893 | 0 / 10 | 0.001953125 | — |
| Repo plug-in D_sym, symmetric rarefaction, both arms to n = 20 | −0.01957459329 | 0 / 10 | 0.001953125 | — |
| Repo plug-in D_sym, symmetric rarefaction, both arms to n = 16 | −0.01508268199 | 0 / 10 | 0.001953125 | — |
| Delete-one jackknife-corrected D_sym | −0.10042592025 | 0 / 10 | 0.001953125 | 0.005859375 |
| Chance-corrected adjusted mutual information | **−0.04841818649** | 0 / 10 | 0.001953125 | 0.005859375 |
| First-order (Miller–Madow style) corrected D_sym | 0.0 | 0 / 10 | 1.0 | — |

Per-seed plug-in deltas, for the record:
`[+0.0061786751, +0.0080505093, +0.0050070097, +0.0076756068, +0.0076756068,
+0.0080505093, +0.0076756068, +0.0076756068, +0.0070822939, +0.0080505093]`.

Per-seed equal-n rarefied deltas are negative in every seed. The exact
sign-flip p is identical (0.001953125 = 2/1024) for the positive and the
negative series because the test is two-sided on the absolute mean; what
changes is the sign of the effect, and that is what decides the verdict.

Rarefaction detail, so the comparison can be audited. The common-n test thins
`channel_off` from 36–39 samples down to the size of `cost_high` (28–31), while
`cost_high` is already at that size, so the thinning is not perfectly symmetric;
that is why the symmetric variants were added, thinning *both* arms to 24, 20
and 16. Three hundred and ninety of four hundred draws per seed are computed at
each target. Under every one of these variants, and under both bias-corrected
estimators, the contrast stays negative.

The Miller–Madow row is not a contradiction; it is a floor. The first-order
correction term exceeds the observed mutual information for every arm in every
seed, the corrected information is clamped at zero, and the corrected D_sym
therefore collapses to exactly 0.0 for all arms and carries no comparison. That
collapse is itself the most compact statement of the problem and is quantified
in section 6.

---

## 6. Why the plug-in metric cannot sign this experiment

### 6.1 The estimate is smaller than its own bias term

For the observed samples the first-order bias term `(K-1)(L-1)/(2 n ln 2)`
exceeds the estimated mutual information in all twenty arm-seed cells examined
for the two arms that matter (K ≈ 9–10 individuals, L = 2 tasks, n = 28–39):

| seed | arm | n | K | L | MI observed (bits) | first-order bias term | ratio |
|---:|---|---:|---:|---:|---:|---:|---:|
| 1000 | cost_high | 28 | 10 | 2 | 0.064239 | 0.231862 | 0.277 |
| 1000 | channel_off | 36 | 10 | 2 | 0.054701 | 0.180337 | 0.303 |
| 1001 | cost_high | 30 | 10 | 2 | 0.019973 | 0.216404 | 0.092 |
| 1001 | channel_off | 38 | 10 | 2 | 0.005645 | 0.170845 | 0.033 |
| 1003 | cost_high | 28 | 9 | 2 | 0.019143 | 0.206099 | 0.093 |
| 1003 | channel_off | 36 | 9 | 2 | 0.005842 | 0.160299 | 0.036 |

Across all twenty cells the ratio ranges from 0.033 to 0.306. The estimated
mutual information is between three and thirty times smaller than the first-order
correction it would need. Nothing that small can be carried into a normalized
ratio and compared between arms that have different n.

### 6.2 A permutation null puts the observations below chance

Permuting task labels across rows preserves both marginals exactly and destroys
any individual–task association. With 500 seeded permutations per arm-seed
cell, the observed D_sym lies *below* the null distribution in essentially every
draw:

| seed | arm | observed D_sym | null mean | null 95th percentile | upper-tail p |
|---:|---|---:|---:|---:|---:|
| 1000 | cost_high | 0.0369351046 | 0.177793 | 0.294219 | 1.0 |
| 1000 | channel_off | 0.0307564295 | 0.131806 | 0.229968 | 1.0 |
| 1001 | cost_high | 0.0111763135 | 0.165438 | 0.268558 | 1.0 |
| 1001 | channel_off | 0.0031258042 | 0.116378 | 0.210971 | 1.0 |
| 1008 | cost_high | 0.0361100825 | 0.163180 | 0.272826 | 0.988 |

The same pattern holds for the other seeds. In other words, the observed
individual x task matrices are *less* associated than chance-permuted matrices
with identical marginals. The chance-corrected adjusted mutual information says
the same thing numerically: it is negative for every arm and every seed
(campaign means: `cost_0`, `cost_moderate`, `channel_off` −0.122975;
`cost_high`, `isolation_probe` −0.171393).

What a negative adjusted mutual information does and does not license:

- It licenses the statement that at this geometry the recorded traces contain no
  detectable individual–task association, and that the positive plug-in D_sym
  values (0.003 to 0.037) are the estimator's small-sample floor rather than
  measured division of labour.
- It does not license the claim that individuals are actively anti-specialised,
  or that any biological mechanism suppresses division of labour. Adjusted
  mutual information is a chance-corrected index, not a physical quantity, and a
  negative value means "less agreement than matched random partitions", nothing
  more.
- It does not, by itself, invalidate every division-of-labour number in the
  repository. It shows that the estimator needs either many more observations
  per arm or a chance-corrected estimator whenever n is small relative to the
  number of individuals. Any other figure in the project that reports a plug-in
  normalized mutual information at comparable n is exposed to the same bias, and
  that exposure should be audited separately.

### 6.3 The mechanism of the artefact, concretely

`cost_high` produces fewer classified trace events than `channel_off` (29.1
against 37.1 samples on average). Positive finite-sample bias in the plug-in
mutual information shrinks as n grows, so the smaller-n arm is mechanically
inflated. That is the entire source of the +0.0073 in the production artifact.
The same mechanism operated in pilot_v1 in the opposite direction: the folded
construction added 2 x switches endpoints to the cost arms only
(`cost_0` n = 40, `cost_moderate`/`cost_high` n = 34, `channel_off` n = 20), so
`channel_off` carried the largest bias and looked strongest. The trace-only fix
removed one asymmetry and reversed the sign of the artefact without removing the
asymmetry itself.

---

## 7. Is the switch-cost manipulation realized as a behavioural change? No.

Comparing raw matrices rather than D_sym is decisive. In **all ten seeds** the
five arms fall into exactly two identical-multiset groups:

```text
seed 1000: [cost_0, cost_moderate, channel_off]  and  [cost_high, isolation_probe]
seed 1001: [cost_0, cost_moderate, channel_off]  and  [cost_high, isolation_probe]
... identical grouping for seeds 1002 through 1009 ...
```

`cost_0` (switch cost 0.0 ATP), `cost_moderate` (0.25 ATP per switch, 6.5–7.0 ATP
charged per seed) and `channel_off` (cost path disabled) produce the **same
matrix**. So:

- The switch charge does not change behaviour at 0.25 ATP per switch.
- Disabling the switch-cost path entirely does not change behaviour either.
- Only `cost_high` (0.50 ATP per switch, 9.0–10.0 ATP charged per seed) differs,
  and it differs by exactly one fewer classified task event for most organisms
  (for seed 1000: `org-0` 3/2 → 2/2 and `org-2`…`org-7` 2/2 → 2/1, i.e. 36 → 28
  samples). No organism drops a task; every organism keeps performing both.

That is not division of labour and it is not a graded response to a cost. It is
a uniform one-event reduction of the trace in the highest-cost arm, which also
lowers task entropy (0.9911 → 0.9403 bits) and mildly raises the individual
entropy (3.1916 → 3.2170 bits). The resulting D_sym difference follows from the
marginals, not from individuals specialising.

The ATP debit itself is real, not bookkeeping-only. The chain is:

- `src/codontrace/genesis/population.py:3137` runs `organism.step(...)`;
  `population.py:3148–3164` then calls `apply_task_switch_cost` and appends the
  returned record.
- `src/codontrace/genesis/task_switch_cost.py:178–188` calls
  `atp_state.debit_runtime(cost, ...)` and sets
  `charged = ledger_id is not None`.
- `src/codontrace/genesis/atp.py:89–96` delegates to the runtime account, and
  `src/codontrace/energy.py:100–124` `ATPAccount.debit` mutates `current_atp`
  from `balance_before` to `balance_after` whenever the balance can pay,
  returning `None` otherwise. `runtime_available` reads that same balance
  (`atp.py:47–51`), and that balance gates action execution, reproduction
  thresholds and the starvation floor.

So the charge does reduce spendable runtime ATP — it simply never binds at this
geometry. Terminal runtime ATP sits at 4.105 to 4.265 on average in every arm, far
above the starvation region, and rising the charge from 6.83 to 9.65 ATP per
seed is what finally perturbs the trace. The debit is also applied *after* the
tick's action has already executed, so it can only affect later ticks.

Consequence for the ablation logic: `channel_off` is not a knockout of a
mechanism that the cost arms use. It is the same run as `cost_0` and
`cost_moderate`. The pipeline's ablation arm therefore does not contrast
"mechanism disabled" against "mechanism engaged"; it contrasts the
highest-charge run against a run that is behaviourally identical to the control.

---

## 8. The isolation readout

`isolation_drop_mean` is **0.0** for `isolation_probe` in all ten seeds. Per
seed the captured score maps are unambiguous: two surviving organisms, every one
of them carrying the ancestral dual-task genome with task width 2.0, group score
2.0, solo score 2.0, drop 0.0.

Two separate problems sit behind that zero.

First, the code path is as described in the task: evolved survivor genomes *are*
carried. `_solo_scores_for_isolation` (`hard_experiment_03.py:669–689`) reads
`_last_evolved_genomes(result)` (`:629–653`), which walks the ticks and keeps the
last non-empty population snapshot, then scores each genome by
`_genome_task_width`. The pilot_v1 behaviour of rebuilding ancestral solo
genomes and re-simulating ATP has been removed. That part of the fix is real.

Second, the readout is degenerate by construction. `_group_scores_for_isolation`
(`:692–696`) returns the constant `HE03_ANCESTRAL_TASK_WIDTH = 2.0` for every
organism, and `_genome_task_width` returns a value in {0, 1, 2}. Since
`run_isolation_assay` computes `drop = group − solo`
(`isolation_assay.py:166`), the drop is confined to {0, 1, 2} and **can never be
negative**. The condition "isolation drop ≥ 0 under high cost" is therefore an
algebraic identity of the construction, not a measurement outcome, and it cannot
fail. The observed 0.0 is the honest null — no specialist evolved, so no task was
lost — but the same 0.0 would be returned by any run whatsoever.

The implementation also no longer matches the preregistration. The prereg
(`docs/HARD_EXPERIMENT_03_PREREG.md`, line 40) requires evolved specialists to be
"re-run alone in a single-individual environment" and compared against group
context. The current code re-runs nothing and never measures group context: the
group side is a constant. The assay now measures "how many task classes remain
encoded in the genome relative to the ancestor", which is a different quantity
from the one that was registered.

---

## 9. The ordinal gate is vacuous

`evaluate_hard_experiment_03_pilot_gates` tests
`cost_0 ≤ cost_moderate ≤ cost_high` on mean D_sym and reports `pass = true`.
It passes for two reasons that have nothing to do with a dose response:

- `cost_moderate − cost_0` is exactly **0.0** in all ten seeds (`p = 1.0`), and
  the matrices are identical. The first inequality is satisfied by equality
  between two runs of the same experiment.
- `cost_high − cost_moderate` is +0.0073 on the plug-in metric and −0.1004 on
  the jackknife-corrected metric, in all ten seeds. The second inequality is
  satisfied only by the sampling artefact described in section 6.

Two of the three arms in the ordinal chain are the same run, so the chain tests
one comparison, and that comparison is the artefactual one.

---

## 10. Regression in decision-rule signalling

This is a consequence of the sign flip and deserves its own line. The decision
failures reported by the ten-seed pilot are:

```text
["scale_not_research", "collective_intelligence_candidate_refused"]
```

`ablation_contrast_wrong_sign_or_null` is absent. In pilot_v1 that flag was the
honest refusal signal: the ablation was wrong-signed and the decision rule said
so. `_decision_failures_from_contrasts` only raises it when
`mean_delta <= 0.0`, and with the artefactual +0.0073 the condition is no longer
met. The pilot now reports a Holm-surviving, right-signed primary contrast and a
passing ordinal gate while the same data, correctly analysed, is wrong-signed in
ten of ten seeds. The overall `decision_rule_passed` value remains false because
it is hard-coded false for pilot and smoke scale, and `cleared_for_research` is
also hard-coded false, so no claim is escalated today — but the pipeline has
lost the ability to say *why* this experiment fails, and the loss is invisible in
the artifact.

The paired effect size makes the same point from another angle: dz = 7.39 with a
95% confidence interval of [0.00653, 0.00773]. That precision is an illusion of
the paired design. The ten "independent" seeds contain three distinct trace
patterns for the low arms and two for the high arm, so the between-seed variance
is near zero by construction and the interval is far narrower than the data can
support.

---

## 11. Tests

| Command | Tree revision | Result |
|---|---|---|
| `python -m pytest tests/test_hard_experiment_03.py tests/test_claimgate_he03_adapter.py -q` | PR #63 head (`tests/test_hard_experiment_03.py` unchanged, 274 lines) | **23 passed, 0 failed** (exit code 0) |
| `python -m pytest tests/test_hard_experiment_03.py tests/test_claimgate_he03_adapter.py -q` | current working tree, 17:05, after other contributors' edits | **26 passed, 1 failed** (27 collected) |
| `python -m pytest -q` (full suite) | PR #63 head, mutating during the run | not obtained; see below |

The two HE03 files pass in full against the revision this report verifies.

The failure on the current tree is worth recording because it bears directly on
whether any campaign artifact from this tree can be used as evidence:

```text
FAILED tests/test_hard_experiment_03.py::test_phase_a_life_loop_digest_pin_unchanged_by_hard_experiment_03
  assert result.digest() == replay.digest()
  '2b67c3c76bc2edb1940a82936bd9f0c9be9ca0df875aaf5b9289756e38a97658'
  != 'dd4cae73fb0d2ffd87b2c635862d12fbf84846292ea8bc8a2492173c406e5e24'
```

Two runs of the identical life-loop specification in one process produced two
different result digests. The specification digest pin still matches
(`spec.digest() == LIFE_LOOP_SPEC_DIGEST` passes), so the pinned configuration is
intact; what fails is replay of the run itself. This is the same symptom observed
independently in my own runners: a repeated `(seed, arm)` run reproduced the same
D_sym and switch counts but a different `result_digest` in two of three runners.
On the PR #63 head this test passed, so the loss of replay determinism is in the
later working-tree state, not in the change under review. It is reported here
rather than fixed, and it means that digest-level reproducibility of any
campaign run from the current tree is currently broken.
After that run, other contributors modified both the source module (15:45) and
`tests/test_hard_experiment_03.py` (16:11, +156 lines), so this count does not
describe the current working tree; a fresh run against the current tree was
started separately and is not part of the verified result above.

The full suite was started and collected 1799 tests across 330 files, but the
working tree was being edited by other contributors while it ran — both source
and test files changed mid-run — so its counts would describe no single
revision. The run was stopped rather than reported.

Two test-suite observations from the same session:

- `tests/test_genesis_a18_hardening.py::test_version_artifact_identity` fails
  in this environment with `assert 'version = "0.3.0b1"' in <pyproject with
  version = "0.3.0b9">`. The cause is environmental, not a defect in the change
  under review: `package_version()` consults `importlib.metadata` first, and the
  stale non-editable `codontrace 0.3.0b1` distribution in site-packages shadows
  the repository's `pyproject.toml`. Imported code still resolves to the
  repository (`src/codontrace/__init__.py`); only the distribution metadata is
  stale. This is the same root cause as the reproduction hazard in section 2.2.
- The suite contains a test named for the trace-only fix
  (`test_he03_trace_samples_exclude_switch_endpoints`) whose only assertion is
  `any(task == "TASK_A" for _, task in samples)`. It does not assert that switch
  endpoints are excluded, and it would pass unchanged under the pilot_v1
  construction. The measurement fix is therefore not actually guarded by the
  test suite, which is consistent with the fix having reversed an artefact
  rather than removed it.

---

## 12. What I could NOT verify

1. **The full test suite.** 1799 tests across 330 files were collected and the
   run was started, but the working tree was being edited by other contributors
   while it ran (source at 15:45, HE03 tests at 16:11), so its counts would
   describe no single revision. The run was stopped rather than reported. Only
   the two HE03 files are confirmed, at 23 passed, against the PR #63 head
   revision.
2. **A single sequential `run_hard_experiment_03(scale='pilot')` for all ten
   seeds.** A sequential invocation was started, measured at ~183 s per arm run
   (~2.5 core-hours for the campaign), and stopped under the project's CPU
   coordination rule. The campaign reported here was assembled from three
   seed-disjoint processes through the production assembly path. I did not
   personally confirm that the ten-seed assembled digest equals a fully
   sequential ten-seed digest.
3. **Byte-level provenance of the campaign.** The campaign's module hash
   `aa845b9f…` matches no committed revision of that path, so the campaign cannot
   be tied to a commit by hash. The working tree was edited by other
   contributors during the session. The algorithmic content is corroborated by
   exact agreement with independently run probes on the same seeds (see the
   revision note), but byte identity with PR #63's head is not established.
   A frozen checkout and a re-run would settle this.
4. **Cross-process determinism of the assembled artifact.** The current working
   tree fails its own replay test, `result.digest() != replay.digest()` for one
   identical specification in one process (section 11), and the same symptom
   appeared in two of my three runners. Until that is resolved, digest-level
   reproducibility of any campaign run from the current tree should be treated
   as broken. The D_sym and switch values did reproduce exactly.
5. **The full text of Goldsby et al. 2012.** Paywalled. Replicate counts, colony
   replication and the exact isolation protocol are unverified; only the
   abstract and the deposited treatment list were read.
6. **Avida/MODES comparator behaviour.** Not examined at all. No comparison to
   Avida update counts, deme structure or `modes_passed` is made or implied
   here.
7. **Whether the same bias affects other division-of-labour numbers in the
   repository.** I established the problem for HE03's arms only. Other
   experiments that report a plug-in normalized mutual information at small n
   are exposed in principle; I did not audit them.
8. **Behaviour at research scale.** Only the pilot geometry (24 ticks,
   population 8) was reproduced. Whether the two-state degeneracy persists at 32
   ticks and population 12 is untested.

---

## 13. Defects found, reported and not fixed

Per the task, nothing below was edited. Each item is a finding for the owner.

1. **Unequal trace sample sizes across arms are not controlled.**
   `cost_high` yields 28–31 samples where the other arms yield 36–39. Since D_sym
   is a plug-in estimator with n-dependent bias, the primary metric is not
   comparable across arms as computed. Suggested direction: compare at a common
   n, or replace the estimator with a chance-corrected one, or both.
2. **The plug-in estimate is below its own first-order bias term** in every
   arm-seed cell examined (ratio 0.033–0.306). The primary metric cannot resolve
   the effect it is asked to measure at this geometry.
3. **`isolation_drop` is non-negative by construction**
   (`_group_scores_for_isolation` returns the constant 2.0), so the "≥ 0"
   manipulation check cannot fail.
4. **The isolation assay no longer implements the preregistered design.** The
   prereg requires solo re-runs against measured group context; the code re-runs
   nothing and compares against a constant.
5. **The ordinal gate is satisfied through arm duplication.**
   `cost_0`, `cost_moderate` and `channel_off` are the same run in all ten seeds.
6. **The switch-cost manipulation is not behaviourally realized** at 0.25 ATP per
   switch, and only perturbs the trace at 0.50 ATP per switch, by removing one
   event per organism rather than by partitioning tasks.
7. **`ablation_contrast_wrong_sign_or_null` no longer fires**, so the artifact no
   longer records that the ablation is not honestly signed.
8. **The trace-only fix is not guarded by its test**, which asserts only that
   some TASK_A sample exists.
9. **A stale non-editable `codontrace` 0.3.0b1 sits in site-packages** with no
   HE03 module; ad-hoc runners that do not force the repository `src` path first
   will silently import the wrong code. The same stale distribution also makes
   `test_genesis_a18_hardening.py::test_version_artifact_identity` fail, because
   `package_version()` prefers installed metadata over `pyproject.toml`.
10. **Replay determinism is broken on the current working tree.**
    `tests/test_hard_experiment_03.py::test_phase_a_life_loop_digest_pin_unchanged_by_hard_experiment_03`
    fails with two different `result.digest()` values for two runs of one
    identical specification. This passed on the PR #63 head and appeared only
    after later edits to the tree, so it is a regression in the shared working
    state. Until it is fixed, no campaign artifact from the current tree can
    claim digest-level reproducibility.

**RECOMMENDATION.** Do not treat the pilot's right-signed ablation as evidence
that PR #63 fixed the mechanism question. The sign is an artefact of unequal
sampling, and the manipulation it signs is not behaviourally realized. The
honest state of step (1) of the locked queue is unchanged from pilot_v1: the
ablation is not right-signed, and the primary readout additionally needs a
chance-corrected estimator or a much larger sample before it can sign anything.

---

## Appendix A. Raw matrices, for independent re-analysis

### A1. Per-arm bookkeeping and scalar fields, by seed

| seed | arm | trace n | folded n | switches | cost realized | D_sym | jackknife | adjusted MI | terminal ATP | isolation drop |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1000 | cost_0 | 36 | 88 | 26 | 0.0000 | 0.0307564295 | -0.0797005084 | -0.111864 | 4.262500 | - |
| 1000 | cost_moderate | 36 | 88 | 26 | 6.5000 | 0.0307564295 | -0.0797005084 | -0.111864 | 4.103191 | - |
| 1000 | cost_high | 28 | 64 | 18 | 9.0000 | 0.0369351046 | -0.1774272669 | -0.168449 | 4.234884 | - |
| 1000 | channel_off | 36 | 36 | 0 | 0.0000 | 0.0307564295 | -0.0797005084 | -0.111864 | 4.262500 | - |
| 1000 | isolation_probe | 28 | 64 | 18 | 9.0000 | 0.0369351046 | -0.1774272669 | -0.168449 | 4.234884 | 0.000000 |
| 1001 | cost_0 | 38 | 94 | 28 | 0.0000 | 0.0031258042 | -0.1576901152 | -0.132120 | 4.234021 | - |
| 1001 | cost_moderate | 38 | 94 | 28 | 7.0000 | 0.0031258042 | -0.1576901152 | -0.132120 | 4.073158 | - |
| 1001 | cost_high | 30 | 70 | 20 | 10.0000 | 0.0111763135 | -0.2570928580 | -0.178431 | 4.203448 | - |
| 1001 | channel_off | 38 | 38 | 0 | 0.0000 | 0.0031258042 | -0.1576901152 | -0.132120 | 4.234021 | - |
| 1001 | isolation_probe | 30 | 70 | 20 | 10.0000 | 0.0111763135 | -0.2570928580 | -0.178431 | 4.203448 | 0.000000 |
| 1002 | cost_0 | 39 | 95 | 28 | 0.0000 | 0.0052303002 | -0.1442727291 | -0.124313 | 4.260417 | - |
| 1002 | cost_moderate | 39 | 95 | 28 | 7.0000 | 0.0052303002 | -0.1442727291 | -0.124313 | 4.101064 | - |
| 1002 | cost_high | 31 | 71 | 20 | 10.0000 | 0.0102373099 | -0.2411925689 | -0.171086 | 4.232558 | - |
| 1002 | channel_off | 39 | 39 | 0 | 0.0000 | 0.0052303002 | -0.1442727291 | -0.124313 | 4.260417 | - |
| 1002 | isolation_probe | 31 | 71 | 20 | 10.0000 | 0.0102373099 | -0.2411925689 | -0.171086 | 4.232558 | 0.000000 |
| 1003 | cost_0 | 36 | 90 | 27 | 0.0000 | 0.0033024435 | -0.1384575336 | -0.123489 | 4.289474 | - |
| 1003 | cost_moderate | 36 | 90 | 27 | 6.7500 | 0.0033024435 | -0.1384575336 | -0.123489 | 4.129032 | - |
| 1003 | cost_high | 28 | 66 | 19 | 9.5000 | 0.0109780503 | -0.2425431155 | -0.172132 | 4.264706 | - |
| 1003 | channel_off | 36 | 36 | 0 | 0.0000 | 0.0033024435 | -0.1384575336 | -0.123489 | 4.289474 | - |
| 1003 | isolation_probe | 28 | 66 | 19 | 9.5000 | 0.0109780503 | -0.2425431155 | -0.172132 | 4.264706 | 0.000000 |
| 1004 | cost_0 | 36 | 90 | 27 | 0.0000 | 0.0033024435 | -0.1384575336 | -0.123489 | 4.324468 | - |
| 1004 | cost_moderate | 36 | 90 | 27 | 6.7500 | 0.0033024435 | -0.1384575336 | -0.123489 | 4.160326 | - |
| 1004 | cost_high | 28 | 66 | 19 | 9.5000 | 0.0109780503 | -0.2425431155 | -0.172132 | 4.349398 | - |
| 1004 | channel_off | 36 | 36 | 0 | 0.0000 | 0.0033024435 | -0.1384575336 | -0.123489 | 4.324468 | - |
| 1004 | isolation_probe | 28 | 66 | 19 | 9.5000 | 0.0109780503 | -0.2425431155 | -0.172132 | 4.349398 | 0.000000 |
| 1005 | cost_0 | 38 | 94 | 28 | 0.0000 | 0.0031258042 | -0.1576901152 | -0.132120 | 4.262500 | - |
| 1005 | cost_moderate | 38 | 94 | 28 | 7.0000 | 0.0031258042 | -0.1576901152 | -0.132120 | 4.103191 | - |
| 1005 | cost_high | 30 | 70 | 20 | 10.0000 | 0.0111763135 | -0.2570928580 | -0.178431 | 4.234884 | - |
| 1005 | channel_off | 38 | 38 | 0 | 0.0000 | 0.0031258042 | -0.1576901152 | -0.132120 | 4.262500 | - |
| 1005 | isolation_probe | 30 | 70 | 20 | 10.0000 | 0.0111763135 | -0.2570928580 | -0.178431 | 4.234884 | 0.000000 |
| 1006 | cost_0 | 36 | 90 | 27 | 0.0000 | 0.0033024435 | -0.1384575336 | -0.123489 | 4.289474 | - |
| 1006 | cost_moderate | 36 | 90 | 27 | 6.7500 | 0.0033024435 | -0.1384575336 | -0.123489 | 4.129032 | - |
| 1006 | cost_high | 28 | 66 | 19 | 9.5000 | 0.0109780503 | -0.2425431155 | -0.172132 | 4.264706 | - |
| 1006 | channel_off | 36 | 36 | 0 | 0.0000 | 0.0033024435 | -0.1384575336 | -0.123489 | 4.289474 | - |
| 1006 | isolation_probe | 28 | 66 | 19 | 9.5000 | 0.0109780503 | -0.2425431155 | -0.172132 | 4.264706 | 0.000000 |
| 1007 | cost_0 | 36 | 90 | 27 | 0.0000 | 0.0033024435 | -0.1384575336 | -0.123489 | 4.208163 | - |
| 1007 | cost_moderate | 36 | 90 | 27 | 6.7500 | 0.0033024435 | -0.1384575336 | -0.123489 | 4.051042 | - |
| 1007 | cost_high | 28 | 66 | 19 | 9.5000 | 0.0109780503 | -0.2425431155 | -0.172132 | 4.175000 | - |
| 1007 | channel_off | 36 | 36 | 0 | 0.0000 | 0.0033024435 | -0.1384575336 | -0.123489 | 4.208163 | - |
| 1007 | isolation_probe | 28 | 66 | 19 | 9.5000 | 0.0109780503 | -0.2425431155 | -0.172132 | 4.175000 | 0.000000 |
| 1008 | cost_0 | 38 | 92 | 27 | 0.0000 | 0.0290277886 | -0.1037594600 | -0.103257 | 4.259375 | - |
| 1008 | cost_moderate | 38 | 92 | 27 | 6.7500 | 0.0290277886 | -0.1037594600 | -0.103257 | 4.100000 | - |
| 1008 | cost_high | 30 | 68 | 19 | 9.5000 | 0.0361100825 | -0.1988215082 | -0.150573 | 4.231395 | - |
| 1008 | channel_off | 38 | 38 | 0 | 0.0000 | 0.0290277886 | -0.1037594600 | -0.103257 | 4.259375 | - |
| 1008 | isolation_probe | 30 | 68 | 19 | 9.5000 | 0.0361100825 | -0.1988215082 | -0.150573 | 4.231395 | 0.000000 |
| 1009 | cost_0 | 38 | 94 | 28 | 0.0000 | 0.0031258042 | -0.1576901152 | -0.132120 | 4.259375 | - |
| 1009 | cost_moderate | 38 | 94 | 28 | 7.0000 | 0.0031258042 | -0.1576901152 | -0.132120 | 4.100000 | - |
| 1009 | cost_high | 30 | 70 | 20 | 10.0000 | 0.0111763135 | -0.2570928580 | -0.178431 | 4.231395 | - |
| 1009 | channel_off | 38 | 38 | 0 | 0.0000 | 0.0031258042 | -0.1576901152 | -0.132120 | 4.259375 | - |
| 1009 | isolation_probe | 30 | 70 | 20 | 10.0000 | 0.0111763135 | -0.2570928580 | -0.178431 | 4.231395 | 0.000000 |

### A2. Distinct trace matrices, by seed

Counts are written `organism=A/B`, where A is the number of TASK_A events and B
the number of TASK_B events in that organism's trace. Arms listed together
produced an identical multiset on that seed.

| seed | arms sharing this matrix | trace n | per-organism counts (TASK_A/TASK_B) |
|---|---|---:|---|
| 1000 | cost_0, cost_moderate, channel_off | 36 | org-0=3/2, org-0-g2-ecf524efa8=1/0, org-1=3/2, org-1-g2-be91c58371=1/0, org-2=2/2, org-3=2/2, org-4=2/2, org-5=2/2, org-6=2/2, org-7=2/2 |
| 1000 | cost_high, isolation_probe | 28 | org-0=2/2, org-0-g2-ecf524efa8=1/0, org-1=2/2, org-1-g2-be91c58371=1/0, org-2=2/1, org-3=2/1, org-4=2/1, org-5=2/1, org-6=2/1, org-7=2/1 |
| 1001 | cost_0, cost_moderate, channel_off | 38 | org-0=3/2, org-0-g2-909f7864da=1/1, org-1=3/2, org-1-g2-01e72f9a12=1/1, org-2=2/2, org-3=2/2, org-4=2/2, org-5=2/2, org-6=2/2, org-7=2/2 |
| 1001 | cost_high, isolation_probe | 30 | org-0=2/2, org-0-g2-909f7864da=1/1, org-1=2/2, org-1-g2-01e72f9a12=1/1, org-2=2/1, org-3=2/1, org-4=2/1, org-5=2/1, org-6=2/1, org-7=2/1 |
| 1002 | cost_0, cost_moderate, channel_off | 39 | org-0=3/2, org-0-g2-f0926cff75=1/1, org-1=3/2, org-1-g2-7ae6b3c5d0=2/1, org-2=2/2, org-3=2/2, org-4=2/2, org-5=2/2, org-6=2/2, org-7=2/2 |
| 1002 | cost_high, isolation_probe | 31 | org-0=2/2, org-0-g2-f0926cff75=1/1, org-1=2/2, org-1-g2-7ae6b3c5d0=2/1, org-2=2/1, org-3=2/1, org-4=2/1, org-5=2/1, org-6=2/1, org-7=2/1 |
| 1003 | cost_0, cost_moderate, channel_off | 36 | org-0=3/2, org-1=3/2, org-1-g2-efb3808c38=1/1, org-2=2/2, org-3=2/2, org-4=2/2, org-5=2/2, org-6=2/2, org-7=2/2 |
| 1003 | cost_high, isolation_probe | 28 | org-0=2/2, org-1=2/2, org-1-g2-efb3808c38=1/1, org-2=2/1, org-3=2/1, org-4=2/1, org-5=2/1, org-6=2/1, org-7=2/1 |
| 1004 | cost_0, cost_moderate, channel_off | 36 | org-0=3/2, org-1=3/2, org-1-g2-3e5fc1b9e8=1/1, org-2=2/2, org-3=2/2, org-4=2/2, org-5=2/2, org-6=2/2, org-7=2/2 |
| 1004 | cost_high, isolation_probe | 28 | org-0=2/2, org-1=2/2, org-1-g2-3e5fc1b9e8=1/1, org-2=2/1, org-3=2/1, org-4=2/1, org-5=2/1, org-6=2/1, org-7=2/1 |
| 1005 | cost_0, cost_moderate, channel_off | 38 | org-0=3/2, org-0-g2-dcdb0ee498=1/1, org-1=3/2, org-1-g2-01e72f9a12=1/1, org-2=2/2, org-3=2/2, org-4=2/2, org-5=2/2, org-6=2/2, org-7=2/2 |
| 1005 | cost_high, isolation_probe | 30 | org-0=2/2, org-0-g2-dcdb0ee498=1/1, org-1=2/2, org-1-g2-01e72f9a12=1/1, org-2=2/1, org-3=2/1, org-4=2/1, org-5=2/1, org-6=2/1, org-7=2/1 |
| 1006 | cost_0, cost_moderate, channel_off | 36 | org-0=3/2, org-1=3/2, org-1-g2-f0926cff75=1/1, org-2=2/2, org-3=2/2, org-4=2/2, org-5=2/2, org-6=2/2, org-7=2/2 |
| 1006 | cost_high, isolation_probe | 28 | org-0=2/2, org-1=2/2, org-1-g2-f0926cff75=1/1, org-2=2/1, org-3=2/1, org-4=2/1, org-5=2/1, org-6=2/1, org-7=2/1 |
| 1007 | cost_0, cost_moderate, channel_off | 36 | org-0=3/2, org-0-g2-01e72f9a12=1/1, org-1=3/2, org-2=2/2, org-3=2/2, org-4=2/2, org-5=2/2, org-6=2/2, org-7=2/2 |
| 1007 | cost_high, isolation_probe | 28 | org-0=2/2, org-0-g2-01e72f9a12=1/1, org-1=2/2, org-2=2/1, org-3=2/1, org-4=2/1, org-5=2/1, org-6=2/1, org-7=2/1 |
| 1008 | cost_0, cost_moderate, channel_off | 38 | org-0=3/2, org-0-g2-00b7d702ce=1/1, org-1=3/2, org-1-g2-e10f1912d6=2/0, org-2=2/2, org-3=2/2, org-4=2/2, org-5=2/2, org-6=2/2, org-7=2/2 |
| 1008 | cost_high, isolation_probe | 30 | org-0=2/2, org-0-g2-00b7d702ce=1/1, org-1=2/2, org-1-g2-e10f1912d6=2/0, org-2=2/1, org-3=2/1, org-4=2/1, org-5=2/1, org-6=2/1, org-7=2/1 |
| 1009 | cost_0, cost_moderate, channel_off | 38 | org-0=3/2, org-0-g2-01e72f9a12=1/1, org-1=3/2, org-1-g2-685dae9315=1/1, org-2=2/2, org-3=2/2, org-4=2/2, org-5=2/2, org-6=2/2, org-7=2/2 |
| 1009 | cost_high, isolation_probe | 30 | org-0=2/2, org-0-g2-01e72f9a12=1/1, org-1=2/2, org-1-g2-685dae9315=1/1, org-2=2/1, org-3=2/1, org-4=2/1, org-5=2/1, org-6=2/1, org-7=2/1 |

### A3. Isolation score maps (all ten seeds)

Every seed, `isolation_probe`: two survivors, each with genome task width 2.0;
group score 2.0; solo score 2.0; drop 0.0.

### A4. Derived quantities used above

- Equal-n rarefaction: 400 seeded draws per seed, thinning both arms to the
  common n, seeded from 20260924 plus the seed index; symmetric variants thin
  both arms to 24, 20 and 16 with 200 draws each.
- Permutation null: 500 seeded draws per arm-seed cell, task labels permuted
  across rows.
- Jackknife: `n * D_full − (n − 1) * mean(delete-one D)`.
- Adjusted mutual information: `sklearn.metrics.adjusted_mutual_info_score`
  with `average_method="geometric"`; the same call with
  `normalized_mutual_info_score` reproduces the repository's `d_sym` to ten
  decimal places, which independently confirms the normaliser is implemented
  correctly.
