# PR #63 ClaimGate audit — adversarial review

Product: CodonTrace Genesis.
Date: 2026-09-24 (Asia/Tehran).
Auditor role: causal / ClaimGate auditor (B), with the measurement / information-theory lens (C).

**Pull request under audit.** Branch `pr63`, head commit `370cb2c`
("test(he03): adapter refuses only when pilot+research both absent"), parent
`abb7172` ("feat(he03): mutational specialization under switch cost (ablation
fix)"), merge base `bdf8125`. Base branch `main` head at audit time `b3772ce`.
Two commits are unique to the branch (`git log --oneline main..pr63`), one commit
is unique to `main` (`git log --oneline pr63..main`).

**Revision actually read.** Line references below were verified against the
committed blob `git show pr63:src/codontrace/genesis/hard_experiment_03.py`, not
only against the working tree. The working tree carries one uncommitted edit by
the repository owner: a two-line reorder inside the import block (moving
`from codontrace.codon import CodonTable` above `from codontrace.errors import
ConfigurationError`). That edit is a pure line swap, so every line number in this
audit is valid for both the committed revision and the working tree. Where a
statement depends on the uncommitted edit, it says so.

**Environment.** CPython 3.14.4; numpy 2.4.4; scipy 1.17.1; pytest 9.1.1;
ruff 0.16.8. Interpreters and versions read directly, not inferred.

---

## 1. Search log

### 1.1 Scientific record search

Every query below was issued on 2026-09-24 and its identifier was opened and read.

| # | Exact query / request | Resolving identifier | What the source actually supports | What it does not license |
|---|---|---|---|---|
| S1 | web search: `Goldsby Dornhaus Kerr Ofria 2012 PNAS 109 13686 task-switching costs promote the evolution of division of labor doi 10.1073/pnas.1202233109` | `https://api.crossref.org/works/10.1073/pnas.1202233109` (HTTP 200) | Record exists and matches the citation used in this repository: Goldsby, Dornhaus, Kerr, Ofria; *Proceedings of the National Academy of Sciences* 109(34):13686-13691; published online 2012-08-07, print 2012-08-21; publisher National Academy of Sciences. The deposited abstract states that rising task-switching costs promote the evolution of division of labour in actively evolving populations of digital organisms, and that under high cost individuals in many cases cease to be able to perform tasks in isolation, requiring other group members | Nothing about this project's scale, engine, or update counts. No equivalence between Avida instruction cycles and this project's ATP units. The abstract is the publisher's deposit; the methods (replicate structure, colony-level replication, number of populations) were **not** retrieved — see the not-verified list in section 8 |
| S2 | web search: `Gorelick Bertram Killeen Fewell 2004 American Naturalist 164 677 normalized mutual entropy quantifying division of labor doi 10.1086/424968` | `https://api.crossref.org/works/10.1086/424968` (HTTP 200) | Record exists and matches: Gorelick, Bertram, Killeen, Fewell; *The American Naturalist* 164(5):677-682; November 2004; publisher University of Chicago Press; title "Normalized Mutual Entropy in Biology: Quantifying Division of Labor". The deposited reference list includes a work titled "Note on the bias of information estimates" (Miller), i.e. the information-estimate bias question is inside the anchor paper's own citation network | Nothing about this project's implementation. It does not license treating a plug-in estimate at a small sample count as if it were unbiased |
| S3 | web search for Goldsby replicate/scale detail: `Goldsby 2012 PNAS task-switching costs division of labor "replicates" Avida populations methods 50 replicates`; and `Goldsby Dornhaus Kerr Ofria PNAS 2012 PMC free full text task-switching costs methods deme` | PMC identifier `PMC3427090` appeared in a third-party index record | That a PMC deposit exists | The full text could not be read: `pmc.ncbi.nlm.nih.gov` returned a browser-verification interstitial, `pnas.org` returned HTTP 403, and the Europe PMC REST endpoints failed to connect. **The claim "Goldsby used about 50 replicates" that appears in this repository's own design documents is therefore NOT verified by this audit** (`docs/hard_experiment_03/WAVE_COLLECTIVE_DOL_BRAINSTORM.md`:60; `docs/hard_experiment_03/WAVE_COLLECTIVE_DOL_CRITIQUE_POST.md`:9-10; `docs/PHASE_L_AVIDA_FIDELITY.md`:105, 124; `docs/rag/corpus/goldsby_2012_pnas_task_switching.md`:22) |

Consequence for the claim ceiling: the two anchors are real, correctly attributed,
and correctly used as *motivation* for the design. Any sentence in this project
that asserts the same result at the same strength is unsupported by these
searches, because the only thing read here is deposited metadata and an abstract.

### 1.2 Current-code search

| # | Command / probe | What it established |
|---|---|---|
| C1 | `git diff main...pr63 --stat`, `--name-only`, and the full patch | Four paths touched: the HE03 module, two test files, one document. No pinned file touched |
| C2 | `git log --oneline main..pr63`, `git log --oneline pr63..main`, `git merge-base main pr63`, `git show --stat <rev>`, `git patch-id --stable` | The exact commit overlap reported in section 7 |
| C3 | `git rev-parse main:<path>`, `pr63:<path>`, `git hash-object -- <path>` for the three pinned files; and `sha256_text_file` from the checked-in package | Pins identical across both branches and the working tree, and their LF-normalised digests equal the documented pin values (section 6) |
| C4 | Direct reads of `hard_experiment_03.py`, `population.py`, `task_switch_cost.py`, `isolation_assay.py`, `metrics/division_of_labor.py`, `engine.py`, `claimgate/adapters/codontrace_he03.py`, `he03_status.py` | Every behavioural statement in this audit carries a line reference from these reads |
| C5 | Probe through the checked-in interpreter comparing arm configurations: `_task_switch_for_arm` equality and digests, `build_hard_experiment_03_spec(...).to_dict()` equality, per-field comparison of the population configs | Finding 3 (section 4) |
| C6 | Probe decoding the ancestral genome and measuring genome task width for every arm | Ancestral width is exactly 2.0, so the isolation drop has a fixed ceiling (finding 1) |
| C7 | Partial campaign: seeds 1000 and 1001, arms `cost_0`/`cost_moderate`/`cost_high`, pilot geometry (24 ticks, population 8); run interrupted after three of ten arm-runs on the repository owner's resource instruction | The only campaign numbers this audit produced itself; reported in section 3 with the interruption stated |
| C8 | `python -m ruff check src tests` on the working tree; `git show pr63:<module>` piped to `ruff check --stdin-filename` | Section 5 |
| C9 | Monte Carlo probe of the plug-in estimator through the checked-in `gorelick_nmi` (4,000 draws per cell, fixed seed, no engine runs) | Section 3.4 |
| C10 | Fixed-list vocabulary scan over the lines added by the diff (`git diff main...pr63` filtered to added lines) and over both documents written by this task | Section 9 |

---

## 2. Verdict summary

| # | Audit question | Verdict | Anchor |
|---|---|---|---|
| 1 | Does the pilot path write `results_v1.json`? | **No — pass** | `hard_experiment_03.py`:1125-1131 has no default path and no in-repository caller; the file is absent; `he03_status.py`:9 reads it but never writes it |
| 2 | Does the diff add prohibited document vocabulary? | **No — pass** | 0 matches on the 297 added lines (section 9) |
| 3 | Are `collective_intelligence` / `collective_intelligence_candidate` still false? | **Yes — pass** | `hard_experiment_03.py`:492, 530-531, 844-845, 1009, 1121; adapter `codontrace_he03.py`:182-187 |
| 4 | Is the claim ceiling still `runtime_observation`? | **Yes — pass** | `hard_experiment_03.py`:48, 830, 841, 1097; `isolation_assay.py`:20, 100-103 |
| 5 | Is the ablation contrast computed or hardcoded? | **Computed for real — pass** (the pilot_v1 defect is fixed) | `_build_paired_contrast`:872-936; `_apply_holm_to_contrasts`:939-953; `build_hard_experiment_03_paired_contrasts`:956-977 |
| 6 | Can a positive-looking delta alone flip the candidate? | **No, but the rule is a hardcoded constant** — defect 5 | `_decision_failures_from_contrasts`:980-1013, `passed = False`:1012; `cleared_for_research: False`:824 |
| 7 | Is the ordinal gate a real gradient? | **Partly — the first rung is an exact tie** — defect 4 | gate:808-818; measured tie in section 3.3 |
| 8 | Are the isolation conditions honest and enforced? | **No — blocking defect** | findings 1 and 2 in section 4 |
| 9 | Are the BAIC pins touched? | **No — pass** | section 6 |
| 10 | Does the branch duplicate a commit already on main? | **Yes** | section 7 |

**Recommendation: DO-NOT-MERGE as-is.** The measurement repair in this pull
request is real and should be preserved, but three of its headline claims do not
survive inspection: the isolation readout cannot fail, the ablation is
confounded and collinear with the primary contrast, and the secondary readout
contradicts the locked preregistration without an amendment. Section 10 lists
exactly what would have to change for the opposite recommendation to hold.

---

## 3. The measurement repair, and what it does not repair

### 3.1 What is genuinely fixed

The pilot_v1 sampling asymmetry is gone. `_extract_task_samples`
(`hard_experiment_03.py`:570-595) now builds the Gorelick matrix from activity
traces only; the switch-record endpoints are no longer folded in, and the
docstring at 573-578 states the reason. The switch bookkeeping is still
available for `n_switches` and realised cost through `_extract_switch_stats`
(656-666). This is a real correctness improvement over the pilot_v1 artifact,
where the cost arms contributed two extra samples per switch and `channel_off`
contributed none, which is the documented cause of the inverted ablation
(`docs/hard_experiment_03/WAVE_MUTATIONAL_SPECIALIZATION_BRAINSTORM.md`:21-23;
`docs/hard_experiment_03/PILOT_V1_REPORT.md`:36-40, 58-60).

The paired contrast machinery is also real. Deltas are computed per seed
(`_paired_d_sym_deltas`:858-869), then a bias-corrected bootstrap interval and
an exact sign-flip permutation p (`_build_paired_contrast`:872-936), then Holm
across the three preregistered contrasts (`_apply_holm_to_contrasts`:939-953).
The committed `pilot_v1.json` contains actual numbers and CIs, so the pilot_v1
"documentation theater" complaint is genuinely resolved.

### 3.2 The ablation sign flip is real but confounded

Own measurement, from the partial campaign (C7), pilot geometry, seed 1000:

| Arm | d_sym | trace samples | switches | realised cost | terminal ATP |
|---|---:|---:|---:|---:|---:|
| cost_0 | 0.0307564295 | 36 | 26 | 0.0 | 4.2625 |
| cost_moderate | 0.0307564295 | 36 | 26 | 6.5 | 4.1031914894 |
| cost_high | 0.0369351046 | 28 | 18 | 9.0 | 4.2348837209 |

Two facts stand out. First, the dose ladder is not a ladder: `cost_0` and
`cost_moderate` are bit-identical on every measured quantity, so the 0.25 ATP
analogue is behaviourally inert at this geometry. Second, `cost_high` has a
higher `d_sym` while producing **eight fewer trace samples** than the arms it is
compared against.

The repository owner's independent measurement reports the same structure
(trace-only ablation delta positive at +0.0062 on seed 1000, previously negative
at −0.0139 before the sampling fix; trace counts `cost_high` 28 vs `channel_off`
36 on seed 1000 and 30 vs 38 on seed 1001). Those counts are reproduced in my
own run for `cost_high` (28 samples, seed 1000).

### 3.3 The ordinal gate is satisfied by an exact tie at the first rung

The gate (`hard_experiment_03.py`:808-818) requires
`cost_0.d_sym_mean <= cost_moderate.d_sym_mean <= cost_high.d_sym_mean` with a
1e-12 tolerance. On the seed-1000 data the first comparison is an equality to
ten decimal places. The preregistration asks for a rising-cost pattern
(`docs/HARD_EXPERIMENT_03_PREREG.md`:16), and a two-level step function that
happens to be monotone satisfies a three-level monotonicity check without
demonstrating a gradient. The gate is therefore weakly informative on its first
rung, and `overall_pass` does not even include it: line 820 computes
`overall = bool(assay_ok and schema_ok)`, so the ordinal result is reported but
never enforced.

### 3.4 `D_sym` is a plug-in estimator whose bias favours the smaller arm

`gorelick_nmi` computes mutual information as `h_x + h_y - h_xy` with no bias
correction or coverage adjustment (`src/codontrace/genesis/metrics/division_of_labor.py`:97-138,
especially 118 and 135-138). Plug-in mutual information is positively biased at
small sample counts, and the bias shrinks as n grows, so an arm with fewer
samples is mechanically favoured whenever the same estimator is applied to
unequal sample counts.

Monte Carlo check through the checked-in function (probe C9; null model of
independent individual and task draws, eight individuals, equal task
probabilities, 4,000 draws per cell, fixed seed). Under the null the true
`D_sym` is zero, so every positive value below is pure finite-sample bias:

| n | E[D_sym] under independence | sd |
|---:|---:|---:|
| 20 | 0.19487 | 0.08136 |
| 24 | 0.16221 | 0.07039 |
| 28 | 0.13650 | 0.06298 |
| 30 | 0.12684 | 0.05975 |
| 36 | 0.10232 | 0.05007 |
| 38 | 0.09660 | 0.04851 |
| 40 | 0.09073 | 0.04677 |
| 80 | 0.03957 | 0.02156 |

The spurious gap between the sample counts actually observed in this design is
about +0.034 (n=28 minus n=36) and +0.030 (n=30 minus n=38) under independence.
The ablation delta being defended is +0.0062. Two honest qualifications, both
stated against the audit's own argument: (i) the real traces are temporally
correlated within organisms, so the effective sample size is below the nominal n
and the i.i.d. figures above are a lower bound on the bias, not an exact
prediction; (ii) the real marginals are not the uniform/null marginals used
here, so the absolute bias in this dataset is unknown. What is not in doubt is
the sign of the mechanism: with a plug-in estimator, fewer samples produce a
larger expected `D_sym`, and the arm that is being credited with the effect is
the arm with fewer samples.

This also weakens the pilot_v1 "positive narrow hint" in the same direction:
there, `cost_high` had 34 samples against `cost_0`'s 40 while reporting the
higher `D_sym` (`pilot_v1.json`, arm summaries and per-seed arm records).

### 3.5 At short geometry the manipulation is bookkeeping only

The repository owner's measurement at 8 ticks and population 4 finds the five
arms producing identical (individual, task) multisets — same mutual information
0.050326, same entropies 2.505587 and 0.918296 — while the switch cost is
genuinely charged (realised cost 2.25 and 4.50) and terminal ATP differs. The
arm specification digests differ, so the arms are distinct configurations whose
measured behaviour is identical. This is corroborated by my seed-1000 result in
which the 0.25 ATP arm is indistinguishable from the zero-cost arm, and by the
committed pilot artifact in which `cost_moderate` and `cost_high` share one
`d_sym` value.

The consequence is a gate hole, not merely a scale note: `assay_failed` is
derived from `_manipulation_failures` (768-797), which only checks that
switch *records* exist and that realised cost on `cost_high` exceeds realised
cost on `cost_0` (787-789) — that is, that the debit was recorded. It never
checks that the manipulation changed behaviour. Combined with line 820
(`overall_pass` ignores the ordinal gate), a smoke campaign can report
`overall_pass` true while the switch cost has had no behavioural effect at all.

---

## 4. The four assigned findings

### Finding 1 — the isolation drop is an algebraic identity. **CONFIRMED**

`_group_scores_for_isolation` (`hard_experiment_03.py`:692-696) returns the
constant `HE03_ANCESTRAL_TASK_WIDTH` (2.0, line 79) for every organism in the
last non-empty population. `_solo_scores_for_isolation` (669-689) returns
`_genome_task_width` per organism, which counts the distinct task classes
present in the decoded genome and therefore lies in {0, 1, 2}
(`_genome_task_width`:618-626; the set is built from `config.classify_task`,
which can return only `TASK_A`, `TASK_B`, or `None`,
`task_switch_cost.py`:102-108). `run_isolation_assay` computes
`drop = group - solo` (`isolation_assay.py`:166) and the mean at line 180.

Therefore `mean_isolation_drop = 2.0 - mean(evolved task width)`, always, with
no dependence on group performance. The non-negativity requirement is satisfied
by arithmetic construction rather than by measurement, and the quantity cannot
distinguish genuine complementarity from capability loss: a population in which
one survivor retains only task A and another retains only task B produces the
same mean drop as a population in which every survivor lost the same task.

Two further properties follow from the same code. The readout uses only the last
non-empty tick's population (`_last_evolved_genomes`:629-653), so all earlier
generations are discarded. And because each survivor contributes a width in
{0, 1, 2}, the mean over a surviving population of m organisms can take only
`2m + 1` values: with the pilot population of 8 that is 17 possible values in
steps of 0.125 — a very low-information statistic for a "secondary confirmatory
readout", to use the wording of `isolation_assay.py`:3-5.

There is also no gate on it anywhere: the gates dictionary contains only
`assay`, `ordinal_cost0_le_moderate_le_high`, and `schema`
(`hard_experiment_03.py`:825-829), and the decision failures mention isolation
nowhere (980-1013). The claim that "isolation drop is now honest and
non-negative" is therefore not testable from the artifact, because no value of
the readout can fail.

### Finding 2 — the preregistration requires a solo re-run; the code re-runs nothing. **CONFIRMED**

Preregistration side: "Re-run evolved specialists alone in a single-individual
environment; report performance drop vs group context"
(`docs/HARD_EXPERIMENT_03_PREREG.md`:40), and the arm table says "evolved
genotypes from cost arms re-run solo" (line 26). The preregistration is locked
by a document digest (line 71-72), and the campaign embeds that digest in every
artifact (`hard_experiment_03.py`:52, 1110), with a test asserting the digest is
real (`tests/test_hard_experiment_03.py`:161).

Implementation side: `_solo_scores_for_isolation` begins with
`del seed, tick_count  # genome-carry assay; no solo re-simulation required`
(line 684). No engine is constructed anywhere in either isolation helper, and
the only use of the simulation is `_run_arm`'s single group run (706-709). The
docstring at 675-682 restates that the readout is genome task width and that the
ATP scores are not used — the last clause refers to the pilot_v1 implementation,
which did re-run organisms (`_solo_scores_for_isolation` in the pilot_v1 code
built a one-organism spec per survivor), although it rebuilt ancestral genomes
rather than carrying survivors.

So the committed design contradicts the committed preregistration on the
operational definition of a preregistered readout, and no HE03 amendment exists
in the tree: `docs/` contains `HARD_EXPERIMENT_03.md` and
`HARD_EXPERIMENT_03_PREREG.md` and no amendment file, unlike HE01 which carries
dated amendments. Meanwhile `CLAIMS.md`:569-570 continues to describe the
IsolationAssay as "a secondary readout of lost lower-level autonomy under
task-switch costs (Goldsby-style)", and the new limitation string says only
"uses ancestral-relative genetic task width, not ATP food-monopoly scores"
(line 1081-1082) — which discloses the substitution of one proxy for another
without disclosing that neither is the preregistered autonomy measurement.
Under the repository's own standing rule (preregistration or a hashed amendment
**before** the numbers, `handoff/00_NEXT_BOT_STATUS_2026-09-13.md`:37), this is a
process violation. This is my strongest objection to merging as-is.

### Finding 3 — `isolation_probe` duplicates `cost_high`. **CONFIRMED**

`_task_switch_for_arm` (239-248) returns the same configuration object value for
both arms: line 246 handles `{"cost_high", "isolation_probe"}` together, and the
two configs are equal with equal digests (probe C5). Building both specs at the
same seed yields dictionaries that differ only in the `metadata` key (probe C5);
within metadata only `hard_experiment_03_arm` and `isolation_secondary` differ
(lines 313, 322); the serialised population configurations are equal, and every
named sub-config (task-switch cost, mutation, metabolism, resource policy) is
equal.

The engine folds metadata into the spec digest (`src/codontrace/engine.py`:376),
so the two runs have different spec and result digests while sharing identical
behavioural configuration. The committed pilot artifact confirms this at the
observable level: for seeds 1000-1002, `cost_high` and `isolation_probe` agree on
`d_sym`, `d_task`, `d_indiv`, `n_task_samples`, `n_switches`,
`switch_cost_realized`, and `mean_terminal_runtime_atp`, and differ only on the
digests and on the isolation readout that only one of them computes.

Consequence: the "secondary assay" arm is a second copy of a treatment arm, and
the survivor genomes it scores come from its own duplicate run
(`_run_arm`:716-720 passes `result` from the `isolation_probe` run), not from
the cost arms as the preregistration's arm table requires
(`docs/HARD_EXPERIMENT_03_PREREG.md`:26). The preregistration's own word for
this arm is "secondary assay (not a primary contrast)"; as implemented it also
buys a full extra campaign run for a trajectory that is already available.

### Finding 4 — `channel_off` implements only half of the preregistered ablation. **CONFIRMED, with one qualification**

The preregistration describes the ablation arm as "dual-resource A/B tasks
unavailable **or** switch cost path disabled" (`docs/HARD_EXPERIMENT_03_PREREG.md`:25).
`_task_switch_for_arm` implements the second branch only: line 241 returns
`TaskSwitchCostConfig(enabled=False)`. The dual-task substrate is enabled for
every arm, including this one: `enable_nexus_stigmergy=True` is applied
unconditionally (line 288) and the ancestral dual-task genome is used whenever
`genome_bits` is not supplied (300-303), so task A and task B remain fully
available in `channel_off`. The intervention record even declares the cut it
claims to make — `cuts_edges=("e3_task_switch_cost",)` (217-226) — while the
edge is already inactive in `cost_0`, where the debit is skipped because the
cost is zero (`task_switch_cost.py`:177-188; for the zero-cost arm
`switch_cost_atp` is 0.0, line 23).

The qualification is that this branch of the finding is stronger than the Lead's
phrasing: `channel_off` is not merely a partial ablation, it is behaviourally
identical to `cost_0`. The two arms differ only in whether
`apply_task_switch_cost` is entered at all (`population.py`:3148-3164); in the
zero-cost arm the function returns a record without debiting, and nothing else
in the engine consumes that record now that the metric ignores it
(`_extract_task_samples`:570-595). The only cross-tick state the enabled branch
writes is `organism.last_task_class` (`population.py`:3162), which is read back
only inside the same block (3149) and copied on cloning (4574) — never for
action selection, energy, or fitness. Since the engine is deterministic for a
given seed, the two arms must produce identical traces.

I did not run `channel_off` itself (section 8), so this last equality is a
code-level entailment supported by the partial-campaign observation that two
arms with different cost values but the same behavioural effect
(`cost_0` and `cost_moderate`) produced bit-identical output.

The audit-level consequence is the one that matters: if `channel_off` equals
`cost_0`, then the "mechanism ablation" contrast `cost_high - channel_off`
(`build_hard_experiment_03_paired_contrasts`:961-965) is numerically the same
test as the primary contrast `cost_high - cost_0` (lines 962-963). Two of the
three contrasts that Holm corrects over are therefore the same hypothesis, and
the third (`cost_moderate - cost_0`) is exactly zero in the data measured here.
The multiplicity correction is applied to non-independent hypotheses, and the
"ablation" supplies no independent falsification of the switch-cost channel.

---

## 5. Continuous-integration and lint status

`python -m ruff check src tests` is the continuous-integration command
(`.github/workflows/ci.yml`:132-133). On the working tree it reports "All checks
passed". On the committed revision `pr63` it reports **exactly one** error,
`I001` (un-sorted import block) in `src/codontrace/genesis/hard_experiment_03.py`,
caused by the import this pull request adds: `from codontrace.codon import
CodonTable` was placed after `from codontrace.genesis.canonical import ...`.
One correction to the summary the repository owner circulated: this failure
**is** attributable to the pull request's own added line, not to pre-existing
code; it is a one-line reorder away from green, and the owner's uncommitted edit
is exactly that reorder.

For completeness, `python -m ruff check .` (which is not the continuous-integration
command) reports 49 findings, all in paths outside the linted scope:
`examples/` (25), `tools/` (21), `docs/claimgate/novel_valuable_evidence_20260924/run_suite.py` (1),
plus import-order and unused-import codes. None of them is in `src` or `tests`,
and none is introduced by this pull request. The strict type-check backlog has
not been measured by this audit and is out of scope for the merge decision here.

The two HE03 test files were **not** executed by this audit (section 8), so this
document does not certify that the added tests pass. It does certify one defect
in the added tests: `test_he03_trace_samples_exclude_switch_endpoints`
(`tests/test_hard_experiment_03.py`:260-270) asserts only that some sample with
task A is present. The pre-fix implementation also produced task-A samples, so
this test would have passed against the code that caused the inverted ablation.
It does not regress the defect it is named after; it should assert that no
sample is derived from a switch record, for example by comparing against a run
whose switch records are non-empty while the trace action set is fixed.

---

## 6. Hard locks

**BAIC pins are untouched.** `git diff main...pr63 --stat` touches four files
(the HE03 module, `tests/test_hard_experiment_03.py`,
`tests/test_claimgate_he03_adapter.py`, and the mutational-specialization
brainstorm document) and none of the three pinned files. Verified three ways:
the LF-normalising digest of each pinned file equals its documented value
(`docs/hard_experiment_03/PILOT_V1_REPORT.md`:66-70); the git object identifiers
are identical on `main`, on `pr63`, and in the working tree; and the raw git
hash of each working-tree file equals the branch blob.

The method note matters and is worth recording, because the raw bytes of these
files **do not** match the pins on this Windows checkout: `results_v7.json`
hashes to `4a5987c2ed0f09d1088b3c1bca6d81fe2310f3867fa84f22a33fbeee7b5d7efd`
by raw bytes but to the documented
`35bb593604438797755e5e7b28af4d1371992a6181a403d08005f7f45421cbd6` through
`codontrace.genesis.text_digest.sha256_text_file`, which normalises CRLF to LF
(`src/codontrace/genesis/text_digest.py`:1-15;
`docs/claimgate/WINDOWS_TEXT_DIGEST.md`:1-14). The same trap applies to
`pilot_v1.json`: raw bytes give `94b6fe32ad8dd774895c92098427188f33ba8b3b8893dd88e5b5e8b6d310464d`
while the LF-normalised digest is
`1788b0c56420f673d280a9247324ebd5af422779b7aca4392ebbb1efe203b482`, which is
exactly the value the pilot report claims (line 6). A reviewer who hashes bytes
will announce three broken pins and one fabricated artifact; both conclusions
would be wrong.

**Engine hygiene.** `git diff main..pr63 --name-only` contains no engine module.
The infection-boundary lock is unaffected.

**Prohibited vocabulary.** Zero matches on the 297 added lines for the fixed
list of conversational-tool, text-generator, and automation-worker terms.
Pre-existing deviations exist elsewhere in the tree, mostly dated material under
`handoff/` and `paper/`, plus a handful of documentation files and one local
variable inside the changed module whose identifier coincides with a prohibited
term; that variable is present on `main` as well (previously at main's line 539
of this module, now 591-594 after this pull request's additions, in
`_extract_task_samples`). Reporting it here by line rather than by name keeps
this audit inside the same prose rule it is checking. These are out of scope and
were not modified — the audit's write scope is two documents, and the pinned
files are untouched regardless.

**No fabricated artifact.** `docs/hard_experiment_03/results_v1.json` does not
exist, no code path in the repository writes it
(`write_hard_experiment_03_results`:1125-1131 has no caller; only the export in
`src/codontrace/genesis/__init__.py`:397), and the continuous-integration
workflow contains no reference to it. `he03_status.py` reads the path and
reports presence only.

**Claim ceiling and flags.** The ceiling is `runtime_observation` at
`hard_experiment_03.py`:48 and is asserted in the campaign payload (830, 841),
the protocol digest (1097), the adapter (178, 216), and by test (line 154). The
collective-intelligence flags are false at 492, 530-531, 844-845 and 1121, and
the adapter hardcodes them false as well (`codontrace_he03.py`:182-187). The
repository-wide "flags proposed only when opted in" path
(`src/codontrace/genesis/phase_l.py`:1354-1393) still asserts that
collective-intelligence stays blocked and that flags are never auto-set, so I
found no reachable path that sets a candidate true from this pull request.

**Decision rule.** It refuses closed, and it cannot do otherwise: `passed` is
assigned the literal `False` at `_decision_failures_from_contrasts`:1012 with no
branch that sets it true, `cleared_for_research` is a literal `False` at line 824,
and the failure list always receives `collective_intelligence_candidate_refused`
at line 1009 while pilot and smoke scales always receive `scale_not_research`
(1007-1008). No delta, however positive, can flip a candidate — which answers
the audit question favourably on the overclaim axis. But it is the mirror image
of the pilot_v1 defect this pull request set out to fix: the refusal is no
longer derived from the evidence either, so the artifact's "REFUSED" status
cannot be cited as proof that the gates work, and a genuinely correct
research-scale result could never clear the rule without a code change.
`overall_pass` (819-823) likewise ignores the ordinal gate, so the gate
structure reports more than it enforces.

---

## 7. Duplicate-commit overlap with `main`

| Commit | Branch | Content |
|---|---|---|
| `b3772ce` "docs(he03): add mutational specialization design brainstorm" | only on `main` | adds `docs/hard_experiment_03/WAVE_MUTATIONAL_SPECIALIZATION_BRAINSTORM.md`, 77 lines |
| `abb7172` "feat(he03): mutational specialization under switch cost (ablation fix)" | only on `pr63` | adds the same 77-line document **plus** 226 changed lines in the HE03 module and 48 added test lines |

The two additions are byte-identical: the blob is
`78c5a5c6295f0c4eda1d31c5f36ed767a65878dd` on both branches, and
`git diff b3772ce pr63 -- docs/hard_experiment_03/WAVE_MUTATIONAL_SPECIALIZATION_BRAINSTORM.md`
is empty. The merge base is `bdf8125`, which is why
`git diff main...pr63 --stat` still lists the document as an addition for the
pull request even though `main` already contains it.

Consequences for merging:

1. A merge into `main` is content-clean for that path — identical content on
   both sides — but the history then records the same document addition twice,
   which will read as a duplicate to anyone auditing the documentation history.
2. Rebasing `pr63` onto `main` drops the document hunk from `abb7172` (that
   hunk becomes empty) and leaves the code and test changes intact. That is the
   correct resolution and matches the repository's own standing rule to rebase
   before coding (`handoff/00_NEXT_BOT_STATUS_2026-09-13.md`:35), a rule this
   branch did not follow: the brainstorm document was written locally and
   committed before `main`'s copy landed.
3. `git patch-id` does not flag this: `abb7172`'s patch identifier differs from
   `b3772ce`'s because `abb7172` also carries the code change. Only a
   file-content comparison finds the overlap, so a reviewer relying on
   duplicate-patch detection alone will miss it.

---

## 8. What this audit could not verify

Stated plainly rather than inferred:

1. **The full pilot was not reproduced.** Only three arm-runs on seed 1000
   completed (`cost_0`, `cost_moderate`, `cost_high`, geometry 24 ticks and
   population 8). The campaign was interrupted on the repository owner's
   resource instruction because the machine was saturated. No claim in this
   audit depends on unreported pilot numbers, and the n=10 pilot of the revised
   design has not been run by anyone at the time of writing.
2. **`channel_off` and `isolation_probe` were not run by this audit.** The
   `channel_off`-equals-`cost_0` argument in finding 4 is a code-level
   entailment (configuration equality plus the absence of any behavioural
   consumer of the switch record and of `last_task_class`), supported by the
   observed bit-identical output of two differently-configured arms with the
   same behavioural effect. It is not a directly measured equality.
3. **The HE03 test files were not executed.** `pytest` on
   `tests/test_hard_experiment_03.py` and `tests/test_claimgate_he03_adapter.py`
   was not run, so this audit does not certify the test suite's status; the
   Lead's independent report of the adapter test behaviour is not adopted here
   as evidence. The one test defect in section 5 was established by reading the
   assertion, which does not require execution.
4. **The strict type-check backlog was not measured.**
5. **Goldsby's experimental scale was not verified.** The full text was
   unreachable (browser verification, HTTP 403, and failing API endpoints, as
   recorded in query S3), so the "about 50 replicates" figure used in this
   repository's own design documents
   (`docs/hard_experiment_03/WAVE_COLLECTIVE_DOL_BRAINSTORM.md`:60;
   `docs/PHASE_L_AVIDA_FIDELITY.md`:105, 124) is unverified by this audit, and so
   is any claim about colony-level replication in that paper.
6. **The behavioural reach of `cost_moderate` beyond seed 1000 is not
   established by this audit.** One seed shows an exact tie with `cost_0`; the
   repository owner's independent measurements corroborate the pattern, and the
   committed pilot artifact shows `cost_moderate` and `cost_high` sharing a
   value across all ten seeds, but no single run in this audit covers ten seeds
   of the revised design.

---

## 9. Vocabulary scan of the reviewed diff and of the two documents written here

Fixed-list scan, applied to (a) the added lines of `git diff main...pr63`
(297 lines) and (b) `docs/PROCESS_CHARTER.md` and this file. The list covers
conversational-tool names and abbreviations, text-generator names, and
automation-worker nouns; the definition is the one already used by this
repository's own audits, for example
`docs/claimgate/host_parasite_port_20260924/DETOY_BRAINSTORM_5ROUND_20260924.md`:24.

| Target | Matches |
|---|---:|
| added lines of the pull-request diff | 0 |
| `docs/PROCESS_CHARTER.md` | 0 |
| this file | 0 |

The only near-match anywhere in the changed source is the pre-existing local
variable in `_extract_task_samples` (lines 591-594) whose identifier coincides
with one of the prohibited terms; it exists on `main` unchanged and is code, not
committed prose. It is cited by line so that this audit does not itself carry
the term it is checking for.

---

## 10. Recommendation

**DO-NOT-MERGE as-is.**

Top three reasons, in order of weight:

1. **The isolation readout cannot fail, is not gated, and contradicts the locked
   preregistration.** `mean_isolation_drop` reduces to
   `2.0 - mean(genome task width)` by construction
   (`hard_experiment_03.py`:79, 618-626, 692-696, 669-689; `isolation_assay.py`:166, 180),
   so the "non-negative isolation drop under high cost" result carries no
   evidential weight; no gate or decision rule reads it (825-829, 980-1013); and
   the preregistered operation is a solo re-run in a single-individual
   environment (`docs/HARD_EXPERIMENT_03_PREREG.md`:26, 40) which the code
   explicitly no longer performs (line 684), with no HE03 amendment in the tree
   while `CLAIMS.md`:569-570 continues to describe the readout as loss of
   lower-level autonomy.
2. **The ablation repair is confounded and does not isolate the mechanism.**
   `cost_high` produces fewer trace samples than the arms it is compared with
   (28 versus 36 on seed 1000), and the plug-in estimator used here is
   monotonically favoured by smaller n — under an independence null the
   spurious gap for those counts is about +0.034 against a defended delta of
   +0.0062 (section 3.4). Independently, `channel_off` is behaviourally the same
   condition as `cost_0` (240-241, 288, 300-303; `population.py`:3148-3164,
   4574), so the "ablation" contrast is numerically the primary contrast and the
   Holm correction is applied to non-independent hypotheses.
3. **The refusal is hardcoded and the committed revision fails continuous
   integration.** `passed = False` (1012) and `cleared_for_research: False`
   (824) make the decision rule independent of the evidence, `overall_pass`
   ignores the ordinal gate (820), and the committed head fails
   `python -m ruff check src tests` with one import-order error introduced by
   this pull request's own added import. The branch also duplicates a document
   commit already on `main` (section 7).

The pull request also does real work that should not be lost: the trace-only
sample construction (570-595) is a genuine correctness fix, the paired
Holm machinery (872-977) is real computation with real numbers in
`pilot_v1.json`, the pins are untouched, no fabricated artifact is introduced,
and the claim flags stay closed. This is a repair worth landing after the
following is true; **if all of it holds, the correct recommendation flips to
MERGE**:

1. The ablation contrast is recomputed with matched sample counts across arms
   (rarefaction to a common n, or a fixed per-tick window, or a bias-corrected
   estimator), and the right sign survives that comparison; the artifact reports
   the per-arm sample counts next to the metric.
2. The isolation readout either performs the preregistered solo re-run, or an
   HE03 amendment is hashed and committed **before** the numbers that redefines
   it as a genotype-breadth census with a constant baseline, together with a
   gate that can fail (for example a declared non-degeneracy condition and a
   requirement that the drop be distinguishable from the no-specialist null).
3. The ablation arm is made behaviourally distinct from `cost_0` — implementing
   the preregistration's "tasks unavailable" branch, or replacing the arm with a
   contrast that genuinely cuts a traversed edge — so that the third Holm
   contrast tests an independent hypothesis.
4. `passed` and `cleared_for_research` are derived from the evidence rather than
   assigned literals, and `overall_pass` includes the ordinal gate while a
   behavioural-effect check joins the manipulation checks (768-797) so that an
   inert manipulation cannot report a pass.
5. The committed revision passes `python -m ruff check src tests`, the branch is
   rebased onto `main` so the duplicated brainstorm commit disappears, and the
   trace-sample test asserts exclusion rather than mere presence
   (`tests/test_hard_experiment_03.py`:260-270).

Until then the honest status of this pull request is: a real measurement fix
carrying an unearned secondary-claim repair. Refusing it is the correct
outcome.
