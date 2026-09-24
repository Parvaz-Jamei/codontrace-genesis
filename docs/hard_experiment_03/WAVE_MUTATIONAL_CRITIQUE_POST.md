# HE03 mutational specialization — critique waves after results

Product: CodonTrace Genesis. Date: 2026-09-24 (Asia/Tehran).
Subject: PR #63 `feat/he03-mutational-specialization` (head 370cb2c), pilot-scale
re-measurement of the task-switch ablation under the trace-only sampling fix.
Claim ceiling: `runtime_observation`. No claim in this document is an
intelligence, collective-intelligence, or division-of-labour result.

## Measurement summary

Two independent harnesses (one assembled by each of two researchers) ran the
campaign on the PR head at pilot geometry, 24 ticks, population 8, seeds 1000 and
1001. The figures below are trace-only samples, so the pilot_v1 endpoint folding
is not part of them.

Per-arm values, seed 1000:

| Arm | n samples | n switches | realized cost (ATP) | plug-in `d_sym` | adjusted MI |
|---|---:|---:|---:|---:|---:|
| cost_0 | 36 | 26 | 0.00 | 0.0307564295 | -0.1118640572 |
| cost_moderate | 36 | 26 | 6.50 | 0.0307564295 | -0.1118640572 |
| cost_high | 28 | 18 | 9.00 | 0.0369351046 | -0.1684491689 |
| channel_off | 36 | 0 | 0.00 | 0.0307564295 | -0.1118640572 |
| isolation_probe | 28 | 18 | 9.00 | 0.0369351046 | -0.1684491689 |

Seed 1001 reproduces the same shape with different magnitudes: cost_0,
cost_moderate and channel_off all 0.0031258042 at n = 38, cost_high and
isolation_probe both 0.0111763135 at n = 30.

`adjusted MI` is the chance-corrected mutual information
(`adjusted_mutual_info_score(average_method='geometric')`), used here only as a
check on the plug-in estimator. The geometric normaliser reproduces the
repository's `d_sym` to ten decimals on every arm, which confirms that the
normaliser in `src/codontrace/genesis/metrics/division_of_labor.py` is
implemented as documented. The two quantities differ only in that one is
corrected for chance and the other is not.

### The ablation sign depends on the sampling comparison, not on the mechanism

Rarefying both arms of the ablation contrast to their common sample size and
drawing 400 seeded subsets:

| Comparison | seed 1000 | seed 1001 |
|---|---:|---:|
| plug-in `d_sym` delta, unequal n (28 vs 36 / 30 vs 38) | +0.0061786751 | +0.0080505093 |
| plug-in `d_sym` delta, equal n | -0.0323527113 | -0.0387629516 |
| share of draws with cost_high > channel_off, equal n | 0.122 | 0.020 |
| adjusted MI delta, equal n | -0.0523783354 | -0.0483959141 |

The unequal-sample comparison favours `cost_high`. The equal-sample comparison
reverses it, and the chance-corrected comparison agrees with the equal-sample
result on both seeds. The cost arms structurally yield fewer trace events while
the charge binds, because charged switches reduce the ATP available and therefore
the number of affordable actions, so the arm with fewer events is compared against
one with more. The plug-in NMI has a positive finite-sample bias that shrinks as n
grows, so the arm with fewer events is inflated. The apparent right-signed
ablation is a property of the sample-count imbalance. Where the charge does not
bind, as at 8 ticks, the arms produce the same number of events and the same
trace, and this route to a spurious difference is not available.

### The manipulation does not reach behaviour at the small geometry

At 8 ticks and population 4, one engine run per arm produced **identical**
(individual, task) multisets in all five arms — the same mutual information
(0.050326), the same marginal entropies (2.505587 and 0.918296), the same
per-organism counts — while the cost was genuinely charged (realized 2.25 and
4.50 ATP for moderate and high) and terminal ATP differed between arms. The
specification digests differ across all five arms, so the configurations are
distinct; the behaviour is not.

The mechanism is visible in the code. The switch cost is debited at
`src/codontrace/genesis/population.py`:3148-3164, which runs per action event and
therefore after the action for that tick has already been chosen and executed; it
can only affect later ticks. The debit lands on `organism.atp_state` and reduces
spendable runtime ATP, so the charge is real and not a ledger-only entry. An
action is blocked only when the debit returns `None`, which happens when the
runtime balance cannot pay (`src/codontrace/genesis/organism.py`:388-410). At the
smaller geometry the runtime balance is about 4.2 ATP against a 0.25 to 0.50 ATP
charge per switch, so the balance is never exhausted and no action is ever
blocked; the cost is recorded and the trace is unchanged. At 24 ticks the balance
does bind, which is why the arms separate there.

At 24 ticks the measured grouping is: `cost_0`, `cost_moderate` and `channel_off`
carry one identical value (0.0307564295 at n = 36 on seed 1000) and `cost_high`
and `isolation_probe` carry another (0.0369351046 at n = 28). Seed 1001 reproduces
that grouping. So at this geometry the separating variable is the size of the
charge, not whether channel classification is active: the ablated arm coincides
with the zero-cost arm exactly. At 8 ticks and population 4 the charge does not
bind at all and all five arms are identical.

Two consequences follow, and both matter more than the sign of any contrast.
First, `channel_off` does not isolate the cost mechanism, because it is
behaviourally the zero-cost arm; the preregistered contrast against it is
therefore numerically the same test as the contrast against `cost_0`, and Holm is
being applied over hypotheses that are not independent. Second, the dose ladder
has two measured states, not three: `cost_0` and `cost_moderate` are
indistinguishable at every geometry measured, so the ordinal gate cannot report a
gradient.

## Critique wave 3 (post-results)

**A — empiricist.** The trace-only repair is real and worth keeping: on seed 1000
the folded construction gave a cost_high minus channel_off delta of -0.0138773368
and the trace-only construction gave +0.0061786751. The repair removed a genuine
defect. It did not remove the confound, because the repair addressed which events
enter the matrix, not how many. A right-signed readout that disappears when the
two arms are compared at equal sample size is not evidence of a mechanism, and
the published comparison it imitates used fifty trials of four hundred colonies
over two hundred thousand updates. Nothing here is comparable to that scale.

**B — ClaimGate auditor.** The refusal was already correct and remains correct.
`_decision_failures_from_contrasts` returns `passed = False` unconditionally
(`hard_experiment_03.py`:1012) and `cleared_for_research` is false
(`:824`), so no combination of these numbers could have moved the ceiling. That
is the right posture, but it also means the pilot cannot distinguish a fixed
experiment from a broken one: the rule refuses either way. The audit's separate
finding stands — `overall_pass` (`:820`) does not read the ordinal gate, and
`_manipulation_failures` (`:768-797`) checks that the debit was recorded, never
that behaviour changed. A campaign can therefore report a passing manipulation
check while the manipulation is behaviourally inert.

**C — measurement and information theory.** The decisive number is not the sign
of the delta but the chance-corrected mutual information, which is negative in
every arm (-0.112 to -0.178). A negative adjusted mutual information means the
joint individual-by-task arrangement carries less information than chance-matched
random arrangements with the same marginals. With 28 to 38 events spread over 6
to 8 individuals and 2 tasks, the trace is too thin for a division-of-labour
measurement to be well posed. The equal-sample rarefaction is a repair of the
comparison, not of the data: it discards events, and after discarding them the
estimator is still uncorrected. The honest statement is that this geometry cannot
support the primary metric, so no sign should be read from it in either
direction.

**D — cross-field innovator.** The failure mode here is the one the economics
import anticipated. Breadth and specialisation are different quantities, and a
per-organism decrement cannot separate "one organism keeps task A, another keeps
task B" from "both lost task B". The same lesson applies to the sample-count
problem: an estimator whose value depends on how much evidence each arm happens
to produce cannot compare arms that produce different amounts of evidence. The
knockout-protocol import (re-run carried survivors alone, score the repertoire
that disappears) and its mandatory superadditivity companion remain the right
instrument, and they are insensitive to event counts because both repertoires
come from the same classifier.

## Ten-seed confirmation, and the refusal flag that disappeared

The two-seed figures above were extended to the full pilot set of ten seeds on the
PR head. The direction is unchanged and the sample-size account is confirmed:

| Treatment of the `cost_high` minus `channel_off` contrast | mean delta | seeds positive |
|---|---:|---:|
| As the campaign code computes it (unequal n) | +0.00731219338 | 10 of 10 |
| Equal-n rarefied to the common n | -0.03518272531 | 0 of 10 |
| Chance-corrected adjusted MI | -0.04841818649 | 0 of 10 |
| Symmetric rarefaction, both arms to n = 24 / 20 / 16 | -0.02698 / -0.01957 / -0.01508 | 0 of 10 each |
| Delete-one jackknife | -0.10042592025 | 0 of 10 |

Per-arm means over ten seeds: `cost_0` 0.0087601705, `cost_moderate` 0.0087601705,
`cost_high` 0.0160723639, `channel_off` 0.0087601705, `isolation_probe`
0.0160723639. The mean isolation drop is 0.0 in all ten seeds, with every survivor
still carrying the ancestral genome, so no specialist evolved in any seed.

Two consequences that matter more than the sign itself.

**The honest refusal flag is now absent.** `_decision_failures_from_contrasts`
(`hard_experiment_03.py`:1011-1014) appends
`ablation_contrast_wrong_sign_or_null` only when the ablation contrast is
non-positive. Because the unequal-sample contrast is positive on all ten seeds,
that flag is no longer appended, and the artifact reports a Holm-surviving
right-signed ablation with no failure recorded against it. The metric remains
uninterpretable for the reasons in this document, so the code's own honest
warning has been extinguished by the sampling artefact. The pilot still cannot
raise the ceiling (`scale_not_research` and
`collective_intelligence_candidate_refused` are appended unconditionally, and
`passed` is false at `:1022`), so no claim is unlocked; but the audit trail no
longer tells a reader that the ablation failed.

**There is one behavioural difference, not two arms differing by mechanism.**
Comparing raw matrices rather than the metric, all ten seeds group as
`[cost_0, cost_moderate, channel_off]` together and `[cost_high, isolation_probe]`
together. `channel_off` is literally the same run as `cost_0`: disabling the
switch-cost path changes nothing. `cost_high` differs from the others by one
fewer classified event per organism (seed 1000: 36 samples against 28), the task
marginal shifts, and the metric moves. No organism drops a task class in any
seed. So the pilot does not contain a cost gradient and does not contain a
mechanism-versus-ablated comparison; it contains one arm that charges enough ATP
to lose an event, and four that do not.

## Critique wave 4 (post-results)

1. **Reject** signing the ablation from the unequal-sample `d_sym` comparison.
   Ten seeds reverse it under every bias-aware treatment, and the equal-n and
   chance-corrected deltas are negative in every seed.
2. **Reject** merging PR #63 on the current evidence. The trace-only repair is a
   real improvement and should be preserved as a separate, honestly-labelled
   change; the branch should not carry a division-of-labour result.
3. **Accept** the negative result as the deliverable. The pilot's value is the
   demonstration that the metric as defined cannot separate these arms, which is
   a stronger and more useful finding than another refused candidate.
4. **Accept** the code-level findings for the next slice: the isolation readout is
   an algebraic identity and no longer matches the preregistered solo re-run; the
   ablation arm is behaviourally identical to the zero-cost arm; the manipulation
   check tests recording rather than effect; and `overall_pass` omits the ordinal
   gate.
5. **Require** a hashed preregistration amendment before any replacement readout
   is used for numbers, because the change replaces a preregistered secondary
   readout rather than merely fixing its implementation.
6. **Require** that the next slice pre-register its sample-size handling: state
   the expected per-arm event count, fix a common n for the primary contrast, and
   commit the bias treatment before the campaign runs.
7. **Do not** enter queue step (2). The exit criteria of step (1) are not met.

## Non-goals and refuse list

No intelligence, collective intelligence, AGI, `red_queen_proved`,
`tokyo_type1_passed`, `modes_passed`, `avida_replacement`, or `samd_certified`
claim is made or implied. No research `results_v1.json` is produced or proposed.
The BAIC pins are unchanged and were verified unchanged by both harnesses. This
document is ordinary research prose.

## Verification status

Run by two harnesses, both on the PR head: the per-arm table, the equal-sample
rarefaction, and the adjusted mutual information figures are reproduced above, and
the two harnesses agree to ten decimal places on the seed-1000 per-arm values. The
HE03 test files were run and pass.

One test-order sensitivity was observed and is recorded here rather than resolved.
`test_phase_a_life_loop_digest_pin_unchanged_by_hard_experiment_03` compares the
result digest of two runs of one identical specification. It passes when the HE03
file is run alone (24 of 24) and was reported failing once inside the full suite,
with two different result digests. A direct probe of four consecutive runs of that
specification in one process returned one identical digest every time
(`d40af494…`, spec digest `7d199ae5…`), so the engine is not nondeterministic on
its own and the failure is a cross-test state interaction. It is not attributable
to the changes in this wave, which touch no engine path, and no fix is proposed
here because the responsible test has not been isolated. Anyone running the full
suite should expect it to be order-sensitive until that isolation is done.

Not run and therefore not certified here: a complete full-suite pass on one frozen
revision. The suite exceeds two hours on this machine and the tree was edited
during the attempt, so no whole-suite count is reported for any single revision.
The mypy backlog is likewise not measured.

The scale figures of the published comparison (number of trials, colonies, and
updates) are **disputed** rather than verified. They appear in
`NEXT_SLICE_PLAN_20260924.md` as read from the deposit's methods section, but two
independent reviews of the same deposit could not retrieve its full text. This
document therefore relies on none of them: it cites the comparison only for the
qualitative point that its design is not comparable to a ten-seed, eight-organism
run, which holds on any reading of the disputed numbers. See Amendment 1 of
`NEXT_SLICE_PLAN_20260924.md`.
