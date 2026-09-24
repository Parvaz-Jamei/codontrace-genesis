# HE03 brainstorm wave before the documentation push

Product: CodonTrace Genesis. Date: 2026-09-24 (Asia/Tehran).
Seat: cross-field innovator (Expert D). Input: the pre-push gate round.

This note answers three questions about what is about to ship. It is written by the
innovator seat, so its subject is design correctness: whether the plan we are about to
commit is still the right plan now that two new facts have arrived. It changes no source
file, no test and no other researcher's document. It answers the questions directly,
including where the answer is that my own earlier plan is wrong.

---

## Question 1 — Does the locked slice survive the two new findings?

Short answer: **no, not in the form I wrote it.** The primary metric is not usable at this
geometry, and the manipulation is inert. A corrected secondary readout cannot rescue a
design whose primary instrument is measuring sampling noise and whose treatment never
reaches behaviour. I recommend reordering the work and dropping the part of my plan that
put the readout replacement first.

### 1.1 What finding (a) does to my plan

The reported behaviour is a sign reversal between unequal and equal sample size: seed 1000
gives plus 0.0062 unequal-n and minus 0.0324 at equal n; seed 1001 gives plus 0.0081 and
minus 0.0388. Chance-corrected mutual information is negative for every arm, between minus
0.112 and minus 0.178.

That pattern is the signature of a sample-size artefact, and the arithmetic is easy to
state. The plug-in mutual information estimator on a contingency table with I rows and T
columns is biased upward at finite n. To leading order the bias is
(I − 1)(T − 1) / (2 n ln 2) bits. For our case, with eight individuals and two task
classes, that is about 3.6 / n bits. When the true mutual information is near zero, the
apparent value therefore scales roughly as one over the sample count, and any normalised
version scales as one over the sample count divided by the entropy floor.

Two consequences follow directly.

1. The arm means in the pilot are not measurements of division of labour. They are
   measurements of how many trace samples each arm happened to accumulate. Arms that
   switch less, or that survive differently, produce different sample counts, and the
   metric rewards whichever arm has fewer samples.
2. This is a better explanation of the wrong-signed ablation than the one recorded in
   the mutational specialisation brainstorm. That note attributed the inversion to cost
   arms folding switch-record endpoints into the matrix while the channel-off arm used
   traces only. Folding endpoints in adds samples, which under a one-over-n bias
   *lowers* the cost arms' apparent value and inflates the channel-off arm. The two
   explanations point the same way, but the sample-size account is the general one, and
   it predicts the equal-n reversal that was just observed. The trace-only change was
   worth making and is not sufficient.

A negative chance-corrected value is also informative in its own right: it means the
observed matrix sits at or below the permutation baseline. In plain terms, there is no
detectable task structure in any arm, at any cost level. That is exactly what an inert
manipulation should look like.

One modelling caution, stated so the record is clean: the repository computes plug-in
mutual information and normalises it. It does not currently compute a chance-corrected
value, so the negative numbers come from a separate analysis and should be recorded as
such rather than attributed to `gorelick_nmi` without a note.

**What this costs my plan.** My slice named "a right-signed `cost_high − cost_0` contrast
that survives Holm" as its primary pass criterion. That criterion cannot be evaluated
while each arm is read at a different sample count, and it will not be evaluable after a
readout repair either. Before any contrast is read, all arms have to be read at one
common sample count, with the count, the subsampling rule and its seed fixed in advance
and the spread across subsamples reported. That is a prerequisite, not a refinement.

### 1.2 What finding (b) does to my plan

The charge is applied after the organism has already chosen and executed its action. In
`src/codontrace/genesis/population.py` the sequence is: the organism steps and produces
an event, and only then, when `configs.task_switch_cost.enabled` is set, does
`apply_task_switch_cost` run on that event's action and call `debit_runtime`. The debit
never gates the action. The only gating in the engine is the pre-action payment check in
`src/codontrace/genesis/organism.py`, where an action is marked blocked with reason
`insufficient_runtime_atp` only if the action's own token cost cannot be paid
(`src/codontrace/genesis/atp.py` documents that runtime ATP is never allowed to go
negative, so a charge that cannot be paid simply does not happen).

So the switch charge can only matter indirectly, by draining a budget that later actions
need. With roughly 4.2 ATP available against a 0.50 ATP charge at the highest cost arm — or
0.25 at the moderate arm — the budget does not run down. The arm's behaviour is therefore
the same as the control's, and the treatment is a bookkeeping entry.

There is a second defect in the same area, and it matters for the plan because my own pass
criteria leaned on this number. `_extract_switch_stats` sums
`TaskSwitchCostRecord.switch_cost_atp` over records. That field is set to the configured
cost before the debit is attempted, and it is left at the configured value even when the
debit fails and the record is marked `charged = False`. The reported
`switch_cost_realized` is therefore the configured cost multiplied by the number of switch
events, not the ATP that was actually taken. In the pilot both figures coincide, which is
precisely why the arm appeared to have spent 8.1 switches' worth of charge. The quantity
named "realized" does not report what its name says.

**What this costs my plan.** My slice treated the manipulation as a given and spent its
budget on the secondary readout. That is the wrong order. If the treatment does not reach
behaviour, then no arm can evolve specialisation, the group repertoires cannot differ
between arms, and a corrected autonomy readout would return a row of zeros and a
confidence interval. Worse, it would return those zeros *after* a solo stage that
multiplies the campaign's wall-clock cost, to measure a difference that the manipulation
was never able to create. Replacing the readout while the manipulation is inert buys
nothing.

### 1.3 The deeper question I should have asked first

My previous plan's structural finding was that the published work selects at the colony
level and ours does not. That finding stands and is unchanged. What the two new facts add
is a sharper statement of the same problem at a smaller scale: our design has to make
switching *cost something an organism wants*, and it currently does not. In the published
work the penalty is wasted central-processor cycles, which are the single scarce resource
that determines how fast an organism replicates. Here the penalty is drawn from a budget
that is not scarce at this geometry, applied after the choice has been made.

So the honest ordering is: make the treatment real, verify it is real behaviourally, and
only then ask whether the population responded to it.

### 1.4 Recommended order of work

**Stage 1 — make the primary instrument readable.** Fix the sampling asymmetry before
anything else. Every arm reports its metrics at one common sample count, chosen in
advance, with subsampling from each arm's own pool using a recorded seed, and with the
spread across subsamples reported alongside the point estimate. This is cheap, it does not
require new dynamics, and without it no contrast in this experiment means anything. This
stage must also record how many observations each arm actually has, because if certain
arms cannot reach the common count, that is itself a finding and it caps what the
experiment can conclude.

**Stage 2 — make the manipulation reach behaviour, then verify it did.** Two things are
needed, in this order. First, a charge large enough to matter, derived rather than chosen:
measure the median per-tick net ATP surplus in the zero-cost arm, and set the high-cost
charge to at least that surplus times a pre-declared safety factor, with the rule and the
resulting number written down before the gating run so that the cost cannot be tuned until
the gate passes. Second, and preferably, a mechanism in which a switch consumes the
action slot instead of only a balance, because that is the closest available analogue of
the published delay and it creates a real trade-off rather than a drain. Then verify
behaviourally: the switch rate in the high-cost arm must be strictly below the switch rate
in the zero-cost arm, paired by seed. This is now the manipulation check that actually
gates the experiment, replacing the current one, which passes whenever a record exists.

**Stage 3 — only now replace the secondary readout.** The two-stage behavioural autonomy
readout, with superadditivity and complementarity as companions, becomes the headline of
the *following* slice rather than this one. It is the right instrument — my confidence in
that is unchanged — but it is a measurement of a response, and there is currently no
evidence of a response to measure.

Rationale for this order, in one sentence: stage 1 is required for any number to be
interpretable, stage 2 is required for any difference between arms to be possible, and
stage 3 is required for the autonomy story, which is meaningless until the first two hold.

### 1.5 What I would drop from my own plan

- **Drop the two-stage solo re-run from the immediate next slice.** It was the centrepiece
  of what I wrote. It should move one slice later. Running it now multiplies compute cost
  to measure a difference the manipulation cannot produce, and its denominator is the
  group repertoire, which the negative chance-corrected result suggests is often empty or
  single-tasked anyway.
- **Drop the "right-signed contrast survives Holm" primary criterion as written**, and
  replace it with the same criterion evaluated at a fixed common sample count, which is a
  precondition rather than a criterion.
- **Drop `switch_cost_realized` as evidence that the manipulation is real.** It reports
  nominal cost. The replacement evidence is the behavioural contrast in stage 2.
- **Keep** the trace-only sampling rule, the ancestor-as-only-founder rule, the pin and
  digest fences, the pre-committed null branch, and the refuse list. None of those is
  affected by either finding. In particular the pre-committed null branch becomes *more*
  important, because there are now two independent ways to reach a null that is nobody's
  fault — no power, or no manipulation — and the report has to distinguish them.
- **Keep, and promote,** the complementarity and coverage diagnostic from import D1. It
  now does double duty: it is the cheapest possible early warning that the population has
  no task structure at all, which is what the negative chance-corrected values are telling
  us.

---

## Question 2 — Test adequacy

Your concern is correct, and I can name it more precisely: the suite's tests were written
around synthetic objects with enough budget to pay and around hard-coded scores, so it
passes under the old behaviour and the new alike. Below is the per-behaviour answer. For
each of the four I name the test that would catch a regression, or say that none exists.

### (i) The debit is charged and `switch_cost_realized` is correct

**Partially pinned, and the important half is not.**

The debit itself is pinned by `test_task_switch_cost_charges_on_switch` in
`tests/test_hard_experiment_03.py`. It constructs a stand-in account with
`runtime_available = 10.0` and a debit function that always succeeds, asserts
`record.charged is True`, and asserts the balance falls by exactly the configured cost.
That test does catch a regression in the debit arithmetic. Note what makes it pass,
though: the fake account can always pay. The branch where the debit fails is never
exercised anywhere in the file, and the disabled path is only checked by an assertion that
the debit function must not be called.

`switch_cost_realized` is **not** pinned by any test. No test asserts that the reported
realized value equals the sum of amounts actually debited. As section 1.2 shows, the
implementation sums the nominal configured cost, so a test that compared the reported
value against the sum of debits for records with `charged = True` would fail today. That
is the test that should exist:

> a test that runs the switch-cost step against an account with insufficient balance for
> the charge, asserts the record is marked uncharged, and asserts that the reported
> realized total excludes the uncharged amount.

A second, campaign-level version is also missing: `test_he03_dual_task_overlay_enables_switches_and_refuses_ci`
asserts only that switch counts are positive, never that any charge landed.

### (ii) The charge changes which actions are taken

**No such test exists.** This is the most serious gap of the four, because it is exactly
the failure the project is living through.

The nearest tests are `test_he03_dual_task_overlay_enables_switches_and_refuses_ci` and
`test_he03_last_task_persists_across_ticks`. Both assert that switch records exist. A
record existing means the classifier saw an action change; it says nothing about whether
the charge altered anything. They pass today, when the charge alters nothing, which is the
definition of a test that cannot fail on the defect it is meant to guard.

The test that should exist:

> a test that runs the same seed and geometry under two configs that differ only in the
> charge amount, and asserts that the trace-derived per-organism action-mixture or switch
> rate differs between them beyond a stated tolerance.

That test fails today. It is also the test that would have prevented the current situation,
and I would treat it as the single highest-value test in the whole file.

The engine-level manipulation check is not a substitute. `_manipulation_failures` compares
`max(cost_high.switch_cost_realized)` against `min(cost_0.switch_cost_realized)`. Since
both sides are nominal sums, that comparison is satisfied as soon as any switch record
exists in the high arm, regardless of whether a single unit of ATP moved.

### (iii) The isolation readout can produce a failing value

**No such test exists, and the one test that looks like it is worse than nothing.**

`test_isolation_assay_secondary_drop` calls `run_isolation_assay` with hand-written
scores, `group_scores = {"a": 1.0, "b": 0.8}` and `solo_scores = {"a": 0.2, "b": 0.4}`,
and asserts the mean drop is 0.6. It tests the arithmetic of a subtraction and the claim
ceiling. It cannot fail on any campaign defect, because it never touches the campaign
path.

`test_he03_genome_task_width_counts_a_and_b` is likewise a two-literal unit test of the
width function.

What is missing is a test that exercises the path where a population has lost a task class
and asserts that the readout does not report it as divided labour. Concretely:

> a test that constructs an evolved population in which a task class is absent from every
> genome, drives the readout, and asserts that the result is distinguishable from a
> population holding one class in one organism and the other class in another.

Today that test would fail, because the current implementation cannot distinguish those
two populations: the group term is the constant ancestral width of 2.0 and the drop is
2.0 minus the mean evolved width, so both cases produce the same number. That is the
design defect described in my previous plan, and it is invisible to the suite.

There is a broader point about this specific test. A unit test that supplies its own
`solo_scores` has no way to notice when the caller stops supplying real ones. The test is
asserting the subtraction is correct, not that anything was measured.

### (iv) The ablation contrast is computed from equal-n samples

**No such test exists.** The contrasts are built by `_paired_d_sym_deltas` and
`_build_paired_contrast` on whatever the arms report, and nothing anywhere asserts
anything about observation counts. `HardExperiment03ArmSummary` carries no sample-count
field that a test could pin; the per-record field `n_task_samples` exists on the arm
record but no test constrains it, and it is never printed in the summary table that a
reader would look at.

The test that should exist, once stage 1 lands:

> a test that builds two arms with deliberately unequal observation counts and asserts
> that the resulting contrast equals the contrast computed at the common count within a
> stated tolerance, and that the campaign reports the common count.

That test fails today by construction, because the equal-n machinery does not exist yet.

### The pattern behind the four answers

Three of the four behaviours have no test at all, and the tests that come closest are
unit tests on synthetic inputs whose properties were chosen so they would pass. The file
pins the shape of the application programming interface — digest stability, claim
ceilings, that interventions cover all arms, that the offset does not alias the pinned
life-loop digest — and it pins arithmetic on hand-written values. It does not pin any
statement of the form "this treatment changed the trajectory" or "this instrument would
report a failure if one occurred".

For a suite guarding a mechanism claim, that is the wrong centre of gravity. The two tests
I would add before the next campaign are the behavioural-contrast test from (ii) and the
lost-task-class test from (iii). Both are cheap relative to a campaign, and both would fail
today, which is the point.

One caveat I want on the record, since I did not run the suite and was asked not to: the
conclusions above come from reading `tests/test_hard_experiment_03.py`,
`src/codontrace/genesis/task_switch_cost.py`, `src/codontrace/genesis/hard_experiment_03.py`,
`src/codontrace/genesis/population.py` and `src/codontrace/genesis/atp.py`. If a test
elsewhere in the tree covers one of these four behaviours, the conclusion is wrong for
that behaviour; the search I ran over the file names and the switch-cost symbols did not
turn one up.

---

## Question 3 — Innovator contribution for the next wave

### 3.1 The first move is D1, and it is no longer merely a diagnostic

D1 was the comparative-advantage import: count per-organism modal tasks and task coverage
from the group traces. I adopted it before as a cheap companion. With the primary metric
degenerate, it becomes the right *first* move, for three reasons.

1. It costs nothing beyond reading traces that already exist. No new dynamics, no new
   currency, no second stage, no multiplied wall clock.
2. It answers the question the negative chance-corrected values raise. If almost no
   organism has an unambiguous modal task, then there is no allocation to divide, and the
   division-of-labour question is not yet well posed at this geometry. That is worth
   knowing before spending hours on stage-2 and stage-3 work.
3. It is the diagnostic most likely to be reported honestly, because a modal-task count
   cannot be inflated by a cost parameter the way a normalised information score can. It
   is a count of something a reader can picture.

### 3.2 Re-adjudication of D1 to D6 on the new evidence

- **D1, comparative advantage — ADOPT, promote to first move.** Reasoning above. Report
  the fraction of surviving organisms with an unambiguous modal task, whether both task
  classes are covered by at least one organism each, and the two class counts.
- **D2, behavioural contrapositive — ADOPT in principle, DEFER to the following slice.**
  The instrument is still the right one and my confidence in the design is unchanged. What
  changed is the sequencing: it measures a response, and there is no response to measure
  while the treatment is inert. Its denominator also becomes fragile if most organisms
  have no group repertoire at all, which the new evidence suggests is likely.
- **D3, switch-direction asymmetry — ADOPT as a required early diagnostic, upgraded from
  optional.** Report A-to-B and B-to-A switch counts separately, per arm, alongside the
  per-tick charge actually debited. This is now load-bearing rather than decorative: it is
  one of the few readouts that can distinguish "switching is happening but is free" from
  "switching has stopped", and it needs no new engine surface because
  `TaskSwitchCostRecord` already carries both task fields.
- **D4, syntrophic cross-feeding — REJECT as a primary readout, unchanged.** Keep at most
  a one-line disjoint-pair count, and only once the group repertoires are non-trivial.
- **D5, hysteresis and the reversion test — DEFER, unchanged.** Correct test, wrong slice;
  it needs a carry-over evolution stage.
- **D6, superadditivity — DEFER with D2.** It is a companion to D2 by construction and has
  no meaning without the solo stage.

### 3.3 The one measurable that tells us the manipulation is working

Asked for one number, this is it:

> **The paired per-seed difference in per-organism task-switch rate between the high-cost
> arm and the zero-cost arm, expressed in switch events per organism per tick, with the
> high-cost arm required to be strictly lower.**

Why this one:

- It is behavioural. It is counted from the traces of actions actually taken, not from
  records of charges attempted, so it cannot be satisfied by bookkeeping.
- It is paired by seed, so it uses the design that is already there and does not need more
  seeds.
- It is sensitive in the right direction. A larger charge can only reduce switching or
  leave it unchanged; it can never increase it. So a positive difference is either a real
  behavioural response or a red flag about the implementation, and both are worth knowing.
- It has an honest failure mode. If the difference is zero, the treatment is inert by
  definition and no division-of-labour number should be read from that run.

Two conditions have to be attached to it, or it becomes a tuning exercise.

1. The threshold and the charging rule are declared before the gating run, not chosen
   after seeing the difference. My recommendation for the rule: measure the median per-tick
   net ATP surplus in the zero-cost arm, set the high-cost charge to at least that surplus
   multiplied by a pre-declared factor, and report both numbers. That derives the cost from
   the ecology instead of fitting it to the outcome, which is the mistake the ordinal gate
   has already made once.
2. It is reported with the count of switch events per organism per tick for both arms, not
   only the difference, so that a reader can see whether either arm is switching at all. A
   difference of zero between two arms that both have zero switch events is not a subtle
   result; it is a different statement, and the two must not be merged.

A useful second number to sit beside it, from D3: the charge actually debited per organism
per tick, computed from the ledger rather than from the record's nominal field. If the
behavioural contrast moves but the debited amount is at or near zero, the money is not
what moved the behaviour, and the causal story needs rewriting before any autonomy
sentence is written.

---

## Summary of my position

1. **The locked slice does not survive.** Its primary criterion cannot be evaluated under
   unequal sampling, and its secondary readout measures a response the manipulation cannot
   produce. I recommend stage 1 (equal-n instrument), then stage 2 (a charge that matters,
   plus the behavioural gate), and only then stage 3 (the behavioural autonomy readout).
2. **The part of my plan I would drop** is the immediate two-stage solo re-run as the
   next slice's centrepiece, together with reliance on `switch_cost_realized` as evidence
   of manipulation and the single-stage pass criterion. I would keep the trace-only rule,
   the fences, the null branch and the refuse list, and I would promote the modal-task and
   coverage diagnostic.
3. **The test suite cannot fail on the two defects that matter.** No test pins that the
   charge changes behaviour, and no test pins that the isolation readout can report a
   failure; the one isolation test supplies its own scores and is therefore blind to the
   campaign path. One test that looks relevant, the realized-cost comparison, is
   satisfied by nominal arithmetic.
4. **The first cross-field move is D1**, with D3 upgraded to a required early diagnostic,
   D2 and D6 deferred one slice, and D4 and D5 unchanged.
5. **The gate number is the paired switch-rate difference**, declared with its charging
   rule before the run, reported with the underlying counts.

Two of these points are findings about code rather than about design, and they belong to
whoever owns the source: `switch_cost_realized` reports nominal cost rather than debited
cost, and the switch charge is applied after action selection so it cannot gate behaviour.
I am reporting both rather than fixing them, because fixing source is outside this seat's
scope in this round.
