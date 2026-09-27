# Causal tape campaign — adversarial review log (stage 3)

**Date:** 2026-09-27 · Two review rounds were completed before the confirmatory
runs, and each defect they found was repaired and the affected run repeated.

## Round 1 — attacks on the brief

| Attack | Verdict | Action |
|---|---|---|
| The estimator decomposition is standard selection-bias theory and cannot be presented as new | Accepted | The brief states the identity as textbook and locates the contribution in the exact instrument |
| Conditioning on mutation absence is already known to be wrong | Accepted | The claim is reduced to measuring the size of the error; the prior result is cited as the motivation |
| A structured causal model in a deterministic program re-describes the program | Accepted in part | The brief drops any identification language; confounding is stated to be absent by construction, and the estimand is defined over the coupling-draw ensemble instead |
| The antecedent "the two-fold cost is an energy debt" may be false at carrying capacity | Accepted | The primary outcome for question 2 is frequency and extinction time; realised equilibrium fitness is not used |
| A matched-schedule order contrast is inflated if the two arms do not carry the same proposal multiset | Accepted | Every scheduled arm carries a schedule digest; an unmatched comparison is reported separately as an inflation factor rather than as the order effect |
| An inert-locus null collapses to zero and degenerates into testing `delta != 0` | Accepted | The drift null for question 3 is built from the effective number of breeders, and the null band is cross-locus |
| The turnover statistic may be saturated and dominated by mutation supply | Accepted | Primary metric changed to temporal `F_ST(w)` with a closed-form drift expectation |

## Round 2 — attacks on the implementation

| Attack | Verdict | Action |
|---|---|---|
| Resampling environments and then mutations is invalid with only three independent coupling draws | Accepted | The environment-level claim is withdrawn from the headline; three draws are reported as a descriptive sweep and the estimator question is reported within-environment |
| The closed-form bias multiplier uses the same ensemble as the estimate, risking a tautology | Accepted | The multiplier test is deferred until a permutation null is defined for it; it is not reported as a result |
| An orthogonal-score estimator would re-impose conditioning on descendants of the process under study | Accepted | No debiased-machine-learning estimator is used; the linear-versus-quadratic comparison is reported as a specification check instead |
| The antibody-free control set omits a matched static antagonist | Accepted | A non-evolving antagonist arm was added; it produces almost no infection and therefore no selection |
| The census used to score antagonist reproduction was taken before mortality | Accepted | The census is recomputed after mortality; the contrast was re-run |
| The host and antagonist shared one random stream, so the paired contrast was only partly paired | Accepted | Separate streams are forked for host mutation, antagonist mutation and shock draws |
| A fixed-period resource pulse aliases with the window-length sweep | Accepted | The pulse is aperiodic with a mean interval of 25 generations |

## Consequences for the record

Two pre-registered readings were refused rather than repaired, because the
instrument was working and the prediction was simply wrong: the sign of the
conditioning bias, and the existence of a clean order-effect threshold. Both are
reported as negative results in the acceptance-test record.
