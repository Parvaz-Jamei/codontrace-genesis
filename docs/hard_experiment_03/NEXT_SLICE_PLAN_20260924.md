# HE03 next slice — literature check, cross-field input, and locked design

Product: CodonTrace Genesis. Date: 2026-09-24 (Asia/Tehran).
Subject: the continuation of locked queue step (1), "HARD_EXPERIMENT collective:
task-switching -> division of labour -> ablation -> isolation multi-seed".
Branch reviewed: `pr63` at `370cb2c`. Companion documents: `PILOT_V1_REPORT.md`,
`WAVE_MUTATIONAL_SPECIALIZATION_BRAINSTORM.md`, `docs/HARD_EXPERIMENT_03_PREREG.md`.

This document is design work. It does not unlock any claim, does not change any
pinned file, and does not by itself authorise a research-scale campaign.

---

## Amendment 1 (2026-09-24) — status of this plan and of two literature figures

This plan is retained as the **design record** for the wave. It is **not** the
operative plan, and two of its elements are superseded. Read this amendment
before using any number below.

1. **The locked slice in Part 3 is superseded.** The replacement isolation readout
   was designed on the assumption that the primary manipulation was realized and
   only the secondary instrument was broken. Measurement since then shows the
   primary manipulation is not realized at the geometry this plan locks: at
   8 ticks and population 4 all five arms produce an identical activity trace, and
   even at 24 ticks the ablated arm coincides with the zero-cost arm. Measured per
   arm on seed 1000 at 24 ticks: `cost_0`, `cost_moderate` and `channel_off` all
   0.0307564295 at n = 36, `cost_high` and `isolation_probe` both 0.0369351046 at
   n = 28. The replacement readout measures a response that cannot yet exist.
   The operative order of work is recorded in
   `BRAINSTORM_WAVE_PRE_PUSH_20260924.md`: repair the sample-count handling of the
   primary metric first, then make the charge bind, then replace the secondary
   readout.
2. **Pass criterion 2 of the locked slice is withdrawn.** That criterion required
   `cost_high` mean `d_sym` to exceed `channel_off`. Two seeds show the opposite
   once both arms are read at equal sample size (seed 1000: +0.0061786751 at
   unequal n, -0.0323527113 at equal n, cost_high ahead in 12.2 per cent of draws;
   seed 1001: +0.0080505093 then -0.0387629476 and 2.0 per cent). A criterion that
   is satisfied only by the unequal-sample reading is not usable. The evidence is
   in `WAVE_MUTATIONAL_CRITIQUE_POST.md` and `ABLATION_VERIFICATION_20260924.md`.
3. **The Goldsby scale figures in Part 1 are disputed and are stated here as
   unverified.** Part 1 says the PubMed Central deposit was read in full and that
   50 trials of 400 colonies over 201,000 updates were taken from its methods
   section. Two other reviews of the same record could not retrieve the full text
   (the deposit returned an interstitial and the publisher returned 403), so those
   figures could not be independently confirmed. They may not be cited as
   established until the methods text is read again and the reading is recorded.
   The bibliographic record itself (title, authors, journal, volume, pages, DOI) is
   confirmed through the publisher's metadata and is not in question.
4. Everything else in this plan stands unchanged: the trace-only sampling rule, the
   ancestor-only founder, the pin and digest fences, the pre-committed null branch,
   the refuse list, and the comparator findings in Part 1 that do not rest on the
   disputed scale figures.

---

## Part 1 — Literature and comparator findings

Every citation below was checked against a bibliographic record. Where a claim
could not be checked, it is marked **unverified** in plain words rather than
softened. No identifier in this document was written from memory.

### 1.1 Goldsby, Dornhaus, Kerr, Ofria (2012) — task-switching costs and division of labour

- Title: "Task-switching costs promote the evolution of division of labor and shifts in individuality".
- *Proceedings of the National Academy of Sciences* 109(34):13686-13691. doi:10.1073/pnas.1202233109.
- Verification: Crossref record (author list, volume, issue, pages, dates) and the
  PubMed Central deposit PMC3427090, whose full text, tables and methods section were read.
  The study data are separately deposited at doi:10.5061/dryad.f8j02, whose deposit record
  was read and which lists the treatment files and the sharing cost levels (0, 25, 50).

What the study actually did, as stated in its own methods:

- 50 trials per treatment, each trial a world of 400 colonies, each colony a 5x5 torus
  holding up to 25 clonal organisms at a time.
- Trials ran 201,000 updates: 200,000 evolutionary updates followed by 1,000 updates with
  the mutation rate set to zero, so that lineages carrying deleterious mutations could be
  pruned before measurement.
- Mutations occurred only when a colony divided; the rate was about one mutation per genome
  per replication event, with a fixed genotype length of 100 instructions.
- Three explicit switching-cost treatments (a 0, 25 or 50 CPU-cycle delay charged before
  the second task is collected) and three colony-level resource requirements (250, 500 and
  1,000 units to replicate).
- The measured quantity was Shannon mutual information between the tasks exported and the
  individuals exporting them. It was **not** the normalised variant. The published values
  are tabulated as 0.027 to 1.066 depending on treatment.

What the study actually found:

- At the 500-unit requirement, higher switching cost produced more division of labour
  (Kruskal-Wallis multiple comparison, p = 0.005). Row means: control 0.400 +/- 0.04,
  moderate 0.813 +/- 0.04, high 1.066 +/- 0.04.
- At the 1,000-unit requirement the three cost treatments were **not significantly
  different**. Control colonies reached 0.735 +/- 0.05 on their own, because abundant
  resources let them export more complex tasks, which carry intrinsic switching costs.
  In other words, the causal story holds at intermediate resource requirements and
  dissolves when resources are abundant.
- Loss of autonomy was shown through knockouts, not through resource monopolies. A
  specialist colony was sterile at both the individual and the colony level once its
  messaging instructions were replaced by a neutral instruction. An organism in isolation
  performed only the OR task, while the group performed up to seven. Control colonies
  mostly kept all their task types when messaging was removed.
- The abstract's qualifier is "in many cases". Loss of autonomy was a frequent outcome of
  the high-cost treatment, not a universal one.

What it does not license here:

1. It does not license a scale claim. The pilot runs 10 seeds, 24 ticks, 8 organisms.
   The published experiment is 50 trials x 400 colonies x 200,000 updates. The two are
   not comparable, and no map from one to the other exists. Every sentence in our
   documents that places a pilot number next to that paper must carry that gap.
2. It does not license an effect-size expectation. Published mutual information spans
   roughly 0.03 to 1.07. The pilot's per-arm values sit near 0.022 to 0.046, one to two
   orders of magnitude smaller, which is consistent with traces that are far too short
   for individuals to accumulate distinguishable task profiles.
3. It does not license a claim that rising cost always raises division of labour. The
   1,000-unit treatment is a published null and must be cited as such whenever the
   ordinal expectation is stated.
4. It does not license an isolation readout built on resource or energy accounting. In
   the paper, autonomy loss is a knockout result and a within-group versus isolation
   task-repertoire result. The pilot's original "solo exceeds group" inversion is a
   property of the accounting used, not a contradiction of the paper.
5. It does not license any claim of intelligence, collective intelligence, or higher-level
   individuality. The paper itself calls its individuality evidence "preliminary".

### 1.2 Gorelick, Bertram, Killeen, Fewell (2004) — normalised mutual entropy

- Title: "Normalized Mutual Entropy in Biology: Quantifying Division of Labor".
- *The American Naturalist* 164(5):677-682. doi:10.1086/424968.
- Verification: Crossref record read (four authors, volume 164, issue 5, pages 677-682,
  published November 2004). The title and the record's category place it in the journal's
  Notes and Comments section, so it is a short methodological note rather than a
  data-generating study: 15 reference entries, six journal pages.

What this means for us:

- It is the correct anchor for the normalised measure the repository implements, and it
  is a methods note. It carries no experimental sample size, no replicates, and no
  causal claim about switching costs. Citing it as support for a mechanism would be
  wrong; citing it for the measure is right.
- The note's own reference list includes a bias-of-information-estimates entry. That
  suggests the original discussion attended to small-sample bias in entropy estimation.
  Whether the original text prescribes a specific correction, and which one, is
  **unverified**: the full text was not retrieved, so this document does not claim to
  reproduce its formula.
- Consequence: the repository's `d_sym` is a plausible symmetric normalisation, and it
  is mathematically bounded in [0, 1]. But which of the note's several normalisations it
  corresponds to is not something this document could confirm, and the implementation
  uses an uncorrected plug-in estimator on short traces. Small-sample bias in short
  trace matrices is therefore a live concern and belongs in the limitations of any
  future report.

### 1.3 Goldsby, Knoester, Kerr, Ofria (2014) — checked because the brainstorm cites it

- Title: "The Effect of Conflicting Pressures on the Evolution of Division of Labor".
- *PLOS ONE* 9(8):e102713. doi:10.1371/journal.pone.0102713.
- Verification: article page read, published 2014-08-05, open access.

Correction to our own record: the brainstorm table lists this paper as "multi-lineage
specialists from mutation during replication". That is not what it studies. It studies
antagonistic multilevel selection, where a within-group pressure rewards a single
high-value role and a between-group pressure rewards role diversity, and it reports that
groups become single-lineage or multi-lineage depending on parameters, with phenotypic
plasticity as the main mechanism by which genetically similar individuals take different
roles. It is relevant background for queue step (3), not support for a mutational
specialisation mechanism in queue step (1), and the brainstorm wording should not be
reused.

### 1.4 Dolson, Vostinar, Wiser, Ofria (2019) MODES — comparator, not a verdict

- Title: "The MODES Toolbox: Measurements of Open-Ended Dynamics in Evolving Systems".
- *Artificial Life* 25(1):50-73. doi:10.1162/artl_a_00280.
- Verification: Crossref record and abstract read.

What it is: a measurement toolbox for four hallmarks of open-ended dynamics — change
potential, novelty potential, complexity potential and ecological potential — with
algorithms and reference implementations, tested on NK landscapes and on Avida so that
different systems can be compared on common axes.

What it is not: a division-of-labour instrument and not a pass/fail certificate. Its own
abstract invites, as future work, a measurement of the potential to produce major
transitions in individuality. So running a MODES-style computation can never tell us
whether our division-of-labour result is real or whether an autonomy shift occurred.

The repository's policy on this point is already correct and pre-existing:
`src/codontrace/claimgate/domain.py` lists `modes_passed` and its aliases among blocked
claims and states that the MODES and Channon rows are comparators only, while
`src/codontrace/claimgate/adapters/avida.py` labels itself a skeleton and records
`"full_avida_support": False` and `"avida_replacement": False`. Nothing in this plan
changes that.

### 1.5 Competitor code — what was and was not inspected

- `devosoft/avida` itself was **not** cloned, built or read in this review. The
  repository's references to it (`src/codontrace/genesis/birth.py`,
  `src/codontrace/genesis/collective_deme.py`, `src/codontrace/genesis/environment.py`)
  cite the Avida configuration keys, the deme introduction material and the coordination
  instruction set. Those citations are consistent with the platform's documentation but
  this document does not certify them.
- The one platform reference that is verified here is Ofria and Wilke,
  "Avida: a software platform for research in computational evolutionary biology",
  *Artificial Life* 10(2):191-229, 2004, doi:10.1162/106454604773563612, which appears in
  the repository's own reference list.
- The honest position is therefore: our work is informed by Avida studies, it is
  implemented in a different substrate, and it is not a port.

What a pure-Python system cannot claim, stated plainly:

- No Avida update-count equivalence. Our tick is not an update, our organisms are not
  running a virtual CPU over a circular instruction list, and the 200,000-update
  trajectories of the published experiment have no counterpart here. The prereg document
  already disclaims this in writing and the campaign returns a limitations string saying
  the same thing; keep both.
- No `modes_passed` and no open-endedness pass.
- No Avida replacement, at any coverage level. The adapter's own `"avida_skeleton"`
  marker is the ceiling.
- Above all, no comparison that treats our ten-seed pilot as a small version of a
  four-hundred-colony, fifty-replicate experiment. It is a different experiment.

### 1.6 The structural gap this check exposes

The published work selects at the colony level: a colony that collectively accumulates
enough resources divides and replaces a random competing colony, so a group whose members
divide their labour can out-replicate a group of equally capable generalists. Division of
labour is therefore a group-level adaptation that arises because groups compete.

Our current HE03 design has no colony level. `build_hard_experiment_03_spec` starts a
single population of `population` identical dual-action genomes from
`HE03_DUAL_TASK_GENOME` and evolves it under mutation and switch cost. There is no colony
division event driven by collective resource accumulation and no between-group
replacement. The individual-by-task matrix can only reflect behavioural variation among
organisms in one population.

This is the deepest reason the primary contrast is fragile: the mechanism that makes
division of labour advantageous in the published work is absent, so what we are measuring
is drift in behaviour under a cost, not selection for specialisation. The design
brainstorm recorded this as a "mechanism gap" and answered it by raising the mutation
rate. Raising mutation does not create group selection. It only accelerates the loss of
task genes, which is exactly the failure mode Part 2 identifies.

---

## Part 2 — Cross-field input on the isolation readout

The isolation readout is the broken one: the pilot recorded minus 0.93675 on a quantity
that is supposed to be non-negative when autonomy is lost. Before importing ideas, here
is what the current code actually computes, because the failure is structural rather than
numerical.

Reading `src/codontrace/genesis/isolation_assay.py` and
`src/codontrace/genesis/hard_experiment_03.py` together:

1. `_solo_scores_for_isolation` returns, per evolved organism, a genome task width in
   {0, 1, 2}: the number of distinct task classes encoded in that organism's codons.
2. `_group_scores_for_isolation` returns the constant `HE03_ANCESTRAL_TASK_WIDTH`, which
   is 2.0, for every organism. The group term is not measured at all.
3. Therefore `mean_isolation_drop` equals 2.0 minus the mean evolved genome task width.
   The assay reduces to a genetic-width census, and `group_performance` is a constant.
4. A genetic width census cannot separate specialisation from capability loss. An
   organism that encodes only EAT_LUMEN and an organism that encodes only EMIT_NEXUS both
   score 1.0, and so do two organisms that both dropped EMIT_NEXUS and kept EAT_LUMEN.
   The census is blind to complementarity, which is the entire content of division of
   labour.
5. The prereg document says the isolation probe re-runs evolved specialists alone in a
   single-individual environment. The implementation does not re-run anything; its own
   docstring says no solo re-simulation is required. The committed design and the
   committed prereg disagree.
6. Under an elevated bit-flip rate and a short evolution window, the most likely way to
   score a large positive drop is for organisms to lose task genes outright. The readout
   would then be reporting degradation, not division of labour, while looking correct.
7. No test covers this path (`tests/test_hard_experiment_03.py` exercises
   `run_isolation_assay` with hand-written scores and checks `_genome_task_width` on two
   literals, but never constrains a campaign-level isolation result), so a broken
   readout can pass the suite.

The baseline brainstorm's answer — score "genetic task-autonomy loss relative to the
ancestral dual repertoire" and "drop >= 0 when specialists evolve" — therefore fixes the
sign but keeps a non-identifying quantity. The ideas below are chosen against that
diagnosis.

One direct check was run against the working tree to confirm the deduction. A single
`isolation_probe` record at smoke geometry (seed 1000, 8 ticks, 6 organisms) returns
`d_sym = 0.1306226204` on 8 switches, `isolation_drop = 0.0`, and no assay failure
flags; the run took about three minutes of wall clock. A drop of exactly zero is what the
deduction predicts: the readout returns zero whenever the surviving organisms still
encode both task classes, and it can only move away from zero by losing a task gene.
That is the confound. Two consequences follow. First, no autonomy evidence of any kind
exists at this geometry, so the pilot's minus 0.93675 came from the earlier
energy-accounting readout, not from this one. Second, the compute cost of a
survivor-by-survivor solo stage is not free, which the budget note at the end of this
part addresses.

Wall-clock budget, measured rather than assumed: the smoke-geometry record above is one
arm-seed comparison and took about three minutes. The next slice multiplies that by five
arms, ten seeds, a larger tick count, a larger population and a solo stage, so the
straightforward arithmetic puts a 32-tick, population-10 pilot in the range of many hours
to more than a day of single-machine time. That is a real risk to the slice being run at
all, and it is a risk of the design rather than of the engine. The mitigation is
sequencing, not a smaller readout: measure one `cost_high` and one `cost_0` arm-seed at
the proposed geometry first, publish that timing in the slice report, and only then
choose between the locked 32 ticks and a reduced 24 ticks with the population kept at 10.
Any reduction in ticks or population is a recorded amendment, made before the campaign
runs and never after seeing a result.

### Idea D1 — Comparative advantage: autonomy loss is not the same as capability loss (economics)

- Source field: classical trade theory, from Smith's task-switching argument through
  Ricardo's comparative advantage. The published experiment cites Smith for exactly this
  point, and the underlying statement is that gains from specialisation require
  complementary allocation across participants, not merely lower individual breadth.
- Mechanism: the group gain from specialisation is positive only when the joint
  allocation covers the tasks the group needs. Breadth loss is neither necessary nor
  sufficient for that. A population of two organisms that both keep both tasks has zero
  division of labour and zero autonomy loss; a population where one keeps task A and the
  other keeps task B has maximal division of labour at a moderate breadth drop; a
  population where both lost task B has maximal breadth drop and zero division of labour.
- Measurable in this codebase: from `_extract_task_samples` (activity traces, already
  trace-only for every arm after PR #63) build the per-organism task distribution and
  derive (a) the fraction of surviving organisms with an unambiguous modal task, and
  (b) task coverage: how many of the two task classes are covered by at least one
  organism. Report both next to the existing `d_sym`. Add a population-level
  complementarity flag: at least two organisms with different modal tasks and both
  classes covered.
- Verdict: **ADOPT**, as a reported diagnostic in the next slice. It is cheap, it comes
  from observation already recorded by the engine, and it is the only one of these ideas
  that would have caught the current failure, because it separates the "both lost B"
  case from the "one A, one B" case that the width census merges.

### Idea D2 — Behavioural contrapositive: compare solo repertoire against group repertoire (microbiology / knockout protocol)

- Source field: microbiology's ablation-and-knockout tradition, and the published
  experiment's own method. Autonomy loss is demonstrated by removing the group context
  and observing which capabilities disappear, as in a gene knockout.
- Mechanism: an organism is group-dependent with respect to task class t if it performs
  t while embedded in the group and fails to perform t when alone. This definition is
  about observed behaviour, so it is immune to which currency (ATP, resources, cycle
  analog) the world happens to use, and it is exactly the comparison the original study
  made when it reported that an isolated organism performed only OR while the group
  performed seven tasks.
- Measurable in this codebase: run the group stage as today, carry the evolved survivor
  genomes (the `genome_bits` argument of `build_hard_experiment_03_spec`, plus
  `_last_evolved_genomes`) into a single-organism re-run of the same world, and compute
  `autonomy_loss = |repertoire_group \ repertoire_solo| / |repertoire_group|` per
  surviving organism, averaged over survivors and then over seeds. Both repertoires come
  from the same trace classifier used for the primary metric, so no new currency and no
  new ecology are introduced.
- Verdict: **ADOPT**. This replaces the width census and is the core of the proposed
  slice. It is the direct counterfactual the prereg already describes, it is orthogonal
  to energy accounting, and its denominator is the organism's own group repertoire, so a
  degenerate organism that performs nothing in either context scores 0 rather than
  scoring as maximally isolated.

### Idea D3 — Switch cost asymmetry and residual cost (cognitive psychology / task switching)

- Source field: the task-switching literature, where a switch to a less-prepared or
  more difficult task carries a larger residual cost even after preparation time, and
  where repeat trials are cheaper than switch trials.
- Mechanism: if the cost of switching A-to-B is not the same as B-to-A, then organisms
  can lower their costs by committing to whichever direction is cheaper, which produces
  one-sided specialisation rather than symmetric role splitting. A symmetric scalar cost
  cannot produce that, and if it is what the world charges, an asymmetric division of
  labour is unreachable by construction.
- Measurable in this codebase: `apply_task_switch_cost` already has
  `from_task` and `to_task` on every `TaskSwitchCostRecord`, and `_extract_switch_stats`
  already aggregates them. Report the A-to-B and B-to-A switch counts and realised cost
  separately per arm instead of one pooled total.
- Verdict: **REJECT as a design change, ADOPT as a reported diagnostic.** Adding a new
  asymmetric-cost knob would change what "cost level" means and would break the prereg's
  ordinal gate, for a mechanism the published work does not test. Counting the two
  directions costs almost nothing and tells us whether the current symmetric knob is
  even being exercised in both directions; if it is not, that is a finding about our
  manipulation check, not a reason to change the manipulation.

### Idea D4 — Redundancy is not specialisation: a functional-repertoire measure with its own denominator (metabolic division of labour in syntrophic communities)

- Source field: syntrophic and cross-feeding communities, where the test for division of
  labour is that each partner's product is another partner's substrate, and where a
  community that loses a function entirely is described as degraded rather than as
  divided.
- Mechanism: mutual dependence is a relational property between partners. It is not a
  per-organism decrement, which is why a per-organism drop statistic keeps conflating
  the two failure modes.
- Measurable in this codebase: for each ordered pair of surviving organisms, count tasks
  performed by one and not the other, and report the fraction of pairs whose repertoires
  are disjoint or strictly nested. A population of complementary specialists has many
  disjoint pairs; a population of degraded generalists has none.
- Verdict: **REJECT as a primary readout, ADOPT as a one-line pair diagnostic.** The
  primary readout should stay per-organism and understandable; a pairwise statistic in a
  population of eight to twelve organisms is noisy and would multiply the number of
  reported numbers without adding power. The disjoint-pair fraction is worth printing
  because it makes complementarity visible in one line.

### Idea D5 — Hysteresis and the reversion test (regulatory plasticity / evolutionary reversibility)

- Source field: regulatory-network plasticity in microbiology, where the honest test for
  whether a phenotype is a compelled adaptation or a plastic response is whether it
  reverts when the selecting condition is removed.
- Mechanism: if autonomy loss is genuinely driven by switch cost, then specialisation
  should at least partly revert when the cost is set back to zero; if it does not revert,
  either the loss is mutational and partly irreversible, or the cost was never the driver.
- Measurable in this codebase: take the evolved survivor genomes from a high-cost group
  run and re-run them for a short block at switch cost zero, then compare task
  repertoires before and after.
- Verdict: **REJECT for the next slice.** It is a genuinely good discriminator and
  belongs in the slice after next, but it requires a carry-over evolution stage that the
  engine does not currently expose for these arms, and adding two stages at once to a
  readout that has never once produced a valid number is how a measurement fix turns
  into a redesign. Recorded here so it is not lost.

### Idea D6 — Comparative-advantage control: does the group exceed its best solo member? (economics, counterfactual branch)

- Source field: the same trade-theoretic logic as D1, used as a control rather than a
  diagnostic. If division of labour produces higher-level function, the group must
  outperform what any single member achieves alone, otherwise the "higher level" adds
  nothing and the autonomy story is empty.
- Mechanism: this is a superadditivity test. It is the mirror image of the autonomy test
  and the two must be reported together, because a population can score high on autonomy
  loss simply by collapsing.
- Measurable in this codebase: from the same group and solo traces used by D2, compare a
  group-level task count against the maximum solo task count among survivors.
- Verdict: **ADOPT as a mandatory companion number to D2.** It costs nothing extra once
  the solo re-run exists, and it blocks the exact soft pass that the width census would
  have granted: a population that lost capability everywhere would show a large
  autonomy loss and no superadditivity, and the pair of numbers makes that visible.

### Most promising single import

**D2, the behavioural contrapositive, with D6 as its mandatory companion and D1 as the
complementarity diagnostic.** It is the one import that (a) replaces a non-identifying
quantity with an identifying one, (b) uses the counterfactual the prereg document
already promised, (c) needs no new currency, no new ecology and no new engine surface,
and (d) is cheap enough that a null result is still informative. D1 alone would only add
a warning label to a broken readout; D3, D4 and D5 are diagnostics or later slices.

---

## Part 3 — Next-slice execution plan

### 3.1 The four expert positions

**A — digital-evolution empiricist.** The published design selects at the colony level;
ours does not (Part 1.6). At 24 ticks and 8 organisms there is not enough individual
history for trace-derived task profiles to separate organisms, which is consistent with
pilot values one to two orders of magnitude below the published range. Conclusion: the
primary outcome cannot be rescued by more seeds alone at the current scale, but before
asking for a colony-level redesign the queue should settle whether the instrument is
capable of producing a valid number at all. A verified readout with a documented null is
worth more than an unverified positive at ten seeds.

**B — ClaimGate auditor.** Renaming and repairing an assay is measurement honesty, not a
claim escalation. The claim ceiling stays `runtime_observation`; the collective
intelligence candidate stays refused; `intelligence`, `agi`, `tokyo_type1_passed`,
`modes_passed` and `avida_replacement` stay false; no decision-rule threshold is
loosened; no pinned file is touched. Two additional requirements: any change to the
isolation criterion in the prereg must land as an explicit, digest-visible amendment
rather than as a silent code edit, and the null branch must be pre-committed, so that a
zero autonomy loss is reported as a null result and not re-read as a soft pass.

**C — measurement.** The current assay has an unmeasured group term, a width census in
place of behaviour, no population-level complementarity statistic, and no test coverage
on the campaign path. Conclusion: the replacement readout must be defined before any code
is written, must have a stated degenerate case, and must ship with a test that fails if a
population of equally degraded organisms scores as divided. Two measurement cautions:
traces from a single-organism world are still an engine-level contrast rather than a
literal removal of partners, so the readout is a conservative proxy and must be described
as one; and the uncorrected plug-in entropy estimator on short traces is a known
small-sample concern that belongs in the limitations.

**D — cross-field innovator.** Adopt the comparative-advantage and knockout-contrapositive
imports (D1, D2, D6 above); adopt the switch-direction and disjoint-pair numbers as
reporting only; defer hysteresis (D5) to the following slice and reject asymmetric-cost
and pairwise-primary proposals for now. The single most promising import is D2 with D6.

### 3.2 Critique wave 1 (pre-build)

1. **The ablation arm is not an ablation of the mechanism.** The prereg describes
   `channel_off` as tasks unavailable or the switch-cost path disabled; the code
   implements only the second reading, returning `TaskSwitchCostConfig(enabled=False)`,
   so the arm switches off the cost path and the task classification together. Under that
   reading, comparing `cost_high` to `channel_off` compares "cost on and tasks classified"
   with "cost off and no task classification at all", which cannot isolate the cost.
   Resolution: keep the arm standing for the next slice but state in the plan and in any
   report that it ablates the cost path rather than the cost, and do not upgrade its
   status to a mechanism-exclusive control.
2. **The isolation arm duplicates a treatment arm.** `_task_switch_for_arm` returns the
   identical configuration for `cost_high` and `isolation_probe`, and the pilot's two
   rows are numerically identical (both 0.0254163808 with 8.1 switches). The probe is a
   re-run of a treatment with an extra readout, not an independent condition. Resolution:
   rename the arm to say what it is — a readout arm carrying `cost_high` settings — and
   stop presenting it as an experimental arm in tables.
3. **The proposed isolation criterion is not falsifiable in its current wording.** "Drop
   >= 0 when specialists evolve" is satisfied by total capability collapse and by the
   constant-width artefact, and it was satisfied in neither direction by the current code.
   Resolution: the criterion in the locked slice below is stated as a positive autonomy
   loss measured from behaviour, with superadditivity required alongside it.
4. **Nothing in the test suite protects this readout.** The only campaign-adjacent tests
   are unit tests with hand-written scores. Resolution: the slice must not be declared
   complete until a test exists that constructs a degraded population and asserts that
   the readout does not report it as divided labour.
5. **Scale and power.** Ten seeds, eight organisms and a trace whose per-organism event
   count may be in the single digits cannot support a Holm-surviving contrast on a
   quantity whose published range starts at 0.027. Resolution: report observed per-arm
   event counts and per-organism trace counts alongside every metric in the next slice,
   so that a null can be attributed to power rather than to absence of mechanism.

### 3.3 The locked slice

**One slice: pilot_v2, "correct the isolation instrument and re-run once, at a scale the
instrument can actually support."**

Scope in one line: replace the width census with a two-stage behavioural autonomy
readout on carried survivor genomes, add the comparative-advantage diagnostics, and re-run
the pilot once at increased ticks with the arms, seeds and gates fixed below.

Frozen elements from PR #63, which this slice does not reopen: trace-only Gorelick samples
for all arms; the ancestral dual-action genome as the only founder; the elevated HE03-only
mutation and cushioned metabolism overlay; the existing paired Holm contrasts on the
primary metric.

Concrete configuration:

- Arms, unchanged in meaning: `cost_0` (cost path enabled, zero cost), `cost_moderate`
  (0.25 ATP), `cost_high` (0.50 ATP), `channel_off` (cost path disabled), and the readout
  arm `isolation_probe`, which carries the `cost_high` settings and is reported as a
  readout, never as an independent arm.
- Primary metric: `d_sym` from `gorelick_nmi` on trace samples classified by the same
  TASK_A/TASK_B lexicon for every arm.
- Primary contrasts, unchanged: `cost_high - cost_0`, `cost_moderate - cost_0` and
  `cost_high - channel_off`, paired by seed with Holm correction over the three.
- Secondary readout, new: two stages. Stage one is the ordinary group run. Stage two
  re-runs the carried survivor genomes, obtained from `_last_evolved_genomes`, in a
  single-organism world with the identical switch-cost configuration, tick count and
  resource policy, and records traces with the same classifier. Then, per surviving
  organism, `autonomy_loss = |group repertoire \ solo repertoire| / |group repertoire|`,
  defined as 0 when the group repertoire is empty; averaged over survivors, then over
  seeds. Mandatory companions: superadditivity (group task count versus best solo task
  count), complementarity (fraction of survivors with an unambiguous modal task, and
  whether both classes are covered by different organisms), group and solo repertoire
  sizes per organism, and per-organism trace event counts.
- Stage geometry: both stages use the same tick count, fixed at 32 ticks for the pilot.
  Unmatched stage lengths would make repertoire differences an artefact of duration, so
  a report-only sensitivity check at 24 and 40 ticks may be run but may not replace the
  locked 32.
- Seeds: pilot 1000-1009, unchanged, so the pilot_v1 and pilot_v2 numbers are directly
  comparable. Research seeds 2000-2029 remain reserved and are not used by this slice.
- Population: 10 organisms per seed, raised from 8 only because the complementarity and
  disjoint-pair diagnostics need a population large enough to contain two distinct modal
  tasks. If wall-clock cost is prohibitive, drop back to 8 and record the change.
- Artifacts: the pilot writes no `results_v1.json`. The campaign payload and its digest
  are the artifact, plus an updated pilot report.

Pass and fail criteria, all fixed before the run:

1. **Instrument validity (blocks everything else).** The campaign reports a numeric
   autonomy loss for every seed, no isolation-stage failure flags, at least one
   `cost_high` contrast and one `cost_0` contrast retain non-degenerate matrices, and the
   instrumentation test of wave-1 item 4 passes. If this does not hold, the slice fails
   as `instrument_invalid` and no scientific reading is offered.
2. **Primary outcome, right-signed.** `cost_high - cost_0` on `d_sym` survives Holm at
   alpha = 0.05 with a positive mean, and `cost_high` mean `d_sym` exceeds `channel_off`
   mean `d_sym`. The second condition is the one pilot_v1 failed.
3. **Secondary outcome, non-degenerate and directional.** Mean autonomy loss under
   `cost_high` is strictly positive; superadditivity holds in the same direction (group
   task count exceeds the best solo task count); and the complementarity diagnostic shows
   at least two survivors with different modal tasks with both classes covered. The
   readout is supporting evidence; passing it does not raise the claim ceiling, and
   failing it does not invalidate a right-signed primary outcome, it only forbids an
   autonomy sentence.
4. **Scale honesty.** Every reported number carries n = 10 seeds, and the report states in
   the same paragraph that this is not the published design, that the published
   experiment used 50 trials of 400 colonies over 200,000 updates, and that no
   update-count equivalence is claimed.
5. **Null branch, pre-committed.** If criterion 2 fails, the slice closes as a documented
   null: the instrument is repaired, the primary mechanism is not confirmed at this scale,
   and queue step (2) is not entered. Advancing to step (2) requires criteria 1 to 3
   together, and entering step (2) still does not grant any claim; it only permits
   designing the next step.
6. **Pins and fences.** The three pinned files stay byte-identical; Phase A life-loop
   digests stay unchanged with the HE03 knobs off; the arm configuration digests for
   every non-HE03 path are unchanged. Any prereg change to the isolation criterion lands
   as its own committed amendment with its own digest.

Explicitly out of scope for this slice: any colony-level or deme-level redesign, any
change to the cost levels or their ATP mapping, any new asymmetric-cost knob, any
research-scale campaign, any `results_v1.json` on the pilot path, and any modification to
ClaimGate behaviour.

### 3.4 Critique wave 2 (pre-build, after the slice lock)

1. **Criterion 2 may be unreachable at 32 ticks even with a correct instrument.** If the
   primary contrast is still null after the instrument is repaired, the slice will have
   spent its budget on a null. That is the correct outcome under the pre-committed null
   branch and must not be softened by adding seeds mid-run; the follow-up would be the
   colony-level redesign named in Part 1.6, which is a new slice and a new prereg
   amendment.
2. **The solo stage is a new engine invocation and can fail independently of the group
   stage.** A survivor whose genome cannot express a task in a single-organism world
   produces an empty solo repertoire, which reads as maximal autonomy loss. The
   degenerate rule in the readout handles the empty-group case, but the empty-solo case
   needs its own guard: report it separately and exclude it from the mean rather than
   letting it dominate, and record how often it happens.
3. **Cost levels, trace-only sampling and the ordinal gate are unchanged, so the ordinal
   gate may remain trivially satisfied.** Measured under the current code, `cost_0` and
   `cost_moderate` carry one identical value at every geometry tried (seed 1000 at 24
   ticks: both 0.0307564295 at n = 36; seed 1001: both 0.0031258042 at n = 38), so the
   ladder has two measured states rather than three. The ordinal gate must therefore not
   be presented as evidence of a dose-response; only the paired contrasts carry
   information. See Amendment 1, which supersedes this plan's pass criteria.
4. **Renaming the readout arm changes committed artifacts.** Arm names appear in
   `isolation_secondary` metadata and in the ClaimGate adapter's role mapping. Any rename
   must be accompanied by an adapter and digest review, or the arm keeps its current name
   and only its presentation changes. Prefer the latter for this slice.
5. **Twelve reported numbers per seed is a reporting hazard.** Autonomy loss,
   superadditivity, modal-task fraction, coverage, repertoire sizes, trace counts,
   switch directions and disjoint-pair fraction can bury the two numbers that decide the
   slice. The report must lead with the decision numbers and relegate the rest to a
   table, with one sentence each saying what a bad value would have looked like.
6. **The published null at the 1,000-unit resource requirement must be cited, not
   omitted.** If our high-cost arm fails to beat control, the honest framing is that the
   published work also reports a treatment-insensitive regime, so a null here is
   consistent with the literature rather than a refutation of it — and equally, a null
   here cannot be explained away by that comparison alone.

---

## Non-goals and the refuse list

Non-goals for the next slice: colony or deme redesign; longer-horizon evolutionary
campaigns; any change to the cost mapping; new metrics beyond the diagnostics listed in
3.3; any research-scale run; any new ClaimGate rule; any paper or release artifact.

The refuse list stays closed, unchanged, and is restated so that no later reading of this
plan can widen it:

- `intelligence` — refused.
- `collective_intelligence` and `collective_intelligence_candidate` — refused; the honest
  outcome is refusal until the published-grade conditions are met, which they are not.
- `red_queen_proved` — refused.
- `tokyo_type1_passed` — refused.
- `modes_passed` and all its aliases — refused; the MODES work remains a comparator.
- `avida_replacement` — refused; no update-count equivalence is claimed, ever.
- Any open-endedness, AGI or higher-level-individuality verdict — refused.
- Any edit to the pinned files (`docs/hard_experiment_01/results_v7.json`,
  `docs/claimgate/risk_bar.json`, `docs/claimgate/biomedical_study.json`) — forbidden.
- Any loosening of a decision-rule threshold — forbidden.
- Any infection-related change in the engine path — forbidden.
- Any `results_v1.json` produced by a pilot-scale run — forbidden.

A repaired instrument is not a result. If the slice returns a right-signed primary
contrast and a non-degenerate autonomy readout, the correct next sentence is "step (2)
design may begin", not "collective intelligence has been shown".

## Verification status summary

Verified against bibliographic records or full text: Goldsby et al. 2012
(doi:10.1073/pnas.1202233109, Crossref record, PubMed Central deposit PMC3427090 whose
main text and methods were read, and the deposit record at doi:10.5061/dryad.f8j02);
Gorelick et al. 2004 (doi:10.1086/424968, Crossref record only, which is where the
volume, issue, pages and author list above were read); Goldsby et al. 2014
(doi:10.1371/journal.pone.0102713, article page); Dolson et al. 2019
(doi:10.1162/artl_a_00280, Crossref record and abstract); Ofria and Wilke 2004,
*Artificial Life* 10(2):191-229, doi:10.1162/106454604773563612, whose identifier was
read from the repository's own reference list rather than from a publisher record.

Not verified, and therefore not relied upon: the full text and any prescribed bias
correction in Gorelick et al. 2004; the upstream `devosoft/avida` source and
configuration files; the exact wording of any supplementary section of Goldsby et al.
2012 beyond what the main text quotes; and the report of 50 replicates per treatment in
Goldsby et al. 2012, which is verified from that paper's own methods section only as
"50 trials", not as a separate replication count. No identifier in this document was
constructed from memory; every one above was read from a bibliographic record or from a
repository file named in place.
