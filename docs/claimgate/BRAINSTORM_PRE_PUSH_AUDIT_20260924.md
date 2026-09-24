# Pre-push brainstorm audit — documentation set, test adequacy, push safety

Product: CodonTrace Genesis.
Date: 2026-09-24 (Asia/Tehran).
Seat: causal / ClaimGate auditor (B), with the measurement / information-theory lens (C).
Subject: the documentation-only push onto the existing PR #63 branch, plus the three
local analysis tools, ahead of an authorised commit and push.

**Method.** This round is read-only verification. No campaign was run and no test file
was executed, on the resource instruction that the machine is mid-run. Every claim
below is anchored to a file and line, or to a predicate computed directly against the
working tree. Where a statement depends on a number produced by another researcher,
it is attributed and not adopted as this audit's own measurement.

**Revision read.** Branch `pr63` at `370cb2c`, working tree with one uncommitted
one-line import reorder in `src/codontrace/genesis/hard_experiment_03.py`. The reorder
is a pure line swap, so line references below are valid for the committed revision as
well. `docs/hard_experiment_03/WAVE_MUTATIONAL_CRITIQUE_POST.md` and the three
`tools/` files are new in the working tree and untracked.

**Payload under review.**

| Path | State | Notes |
|---|---|---|
| `docs/PROCESS_CHARTER.md` | new, untracked | the durable process document |
| `docs/claimgate/PR63_CLAIMGATE_AUDIT_20260924.md` | new, untracked | the gating audit |
| `docs/hard_experiment_03/NEXT_SLICE_PLAN_20260924.md` | new, untracked | the next-slice design |
| `docs/hard_experiment_03/WAVE_MUTATIONAL_CRITIQUE_POST.md` | new, untracked | post-results critique waves 3 and 4 |
| `docs/hard_experiment_03/BRAINSTORM_WAVE_PRE_PUSH_20260924.md` | new, untracked | not in the stated payload, but it is untracked in the same working tree and belongs to this round, so it is inside the consistency scope |
| `tools/run_he03_parallel.py` | new, untracked | parallel pilot runner, writes an optional JSON |
| `tools/probe_he03_traces.py` | new, untracked | per-arm trace comparison |
| `tools/probe_nmi_bias.py` | new, untracked | equal-n rarefaction and chance-corrected comparison |
| source | one uncommitted line | the import reorder that clears `ruff` code `I001` |
| tests | unchanged | no test edits in this push |

**Headline.** The payload violates no hard lock: no pinned file is touched, no source
behaviour changes beyond an import reorder, no research artifact is created, and the
claim ceiling is untouched. The block is a quality block, not a lock block. Five of the
contradictions in section 1 are load-bearing, because each one lets a reader reach the
opposite conclusion from the same evidence, and two of them — the locked pass criterion
and the two competing next slices — change what the next slice would build.

---

## 1. Consistency audit of the document set

Thirteen findings. Each names both sides. The five marked **load-bearing** must be
resolved before the set is pushed together, because each one changes what a reader
concludes about the merge, about the ablation, or about the next slice.

### C1 — the critique inverts which arms coincide. **load-bearing**

| Side | Anchor | Statement |
|---|---|---|
| A | `docs/hard_experiment_03/WAVE_MUTATIONAL_CRITIQUE_POST.md`:80-81 | "the dose ladder has two states, not three. `cost_0`, `cost_moderate` and `cost_high` are the same behaviour; `channel_off` differs" |
| B | same file, :16-24 (the measured table) | `cost_0`, `cost_moderate` and `channel_off` are all `0.0307564295` at n = 36; `cost_high` and `isolation_probe` are both `0.0369351046` at n = 28 |
| C | same file, :76-78 | "At 24 ticks the two baselines and the ablated arm still coincide exactly" |

Statement A is the exact inverse of the measurement two paragraphs above it and of
statement C. The table says the three zero-or-disabled-cost conditions coincide and the
high-cost condition differs; A says the three cost conditions coincide and the disabled
condition differs. Independent anchors agree with the table:

- this audit's code entailment, `docs/claimgate/PR63_CLAIMGATE_AUDIT_20260924.md`:319-333,
  that `channel_off` is behaviourally the zero-cost arm, since the enabled zero-cost arm
  performs no debit (`src/codontrace/genesis/task_switch_cost.py`:177-188) and the only
  cross-tick state the enabled branch writes is never read for behaviour
  (`src/codontrace/genesis/population.py`:3149, 3162, 4574);
- the same document's finding 3, :276-301, that `isolation_probe` duplicates `cost_high`.

**Direct answer to the question asked.** The critique's claim that "`channel_off`
differs from the cost arms" does **not** survive. At 24 ticks it coincides exactly with
`cost_0` and `cost_moderate` (:16-24). At the small geometry the critique itself reports
all five arms producing identical multisets (:60-66). There is no geometry measured in
this set at which `channel_off` differs from `cost_0`. The sentence at :80-81 must be
rewritten before the document ships, because as written it tells a reader that the cost
knob is inert and the disabled channel is the active condition — the opposite of the
data. Note also that `PR63_CLAIMGATE_AUDIT_20260924.md`:494-497 lists exactly this
equality as *not* directly run by that audit; the critique's table supplies the
measurement that closes it, so the two documents should be reconciled rather than left
as one inferring and one contradicting.

### C2 — the critique gives two incompatible mechanisms for the same fact

| Side | Anchor | Statement |
|---|---|---|
| A | `WAVE_MUTATIONAL_CRITIQUE_POST.md`:52-56 | "The cost arms structurally yield fewer trace events, because a charged switch cost reduces the ATP available and therefore the number of affordable actions" |
| B | same file, :70-78 | "the balance is never exhausted and no action is ever blocked ... it does not change which actions are taken" |

Both cannot be true. The table at :22 supports A for the high-cost arm (28 events and
18 switches against 36 and 26 for the zero-cost arm), so B's "no action is ever blocked"
is the claim that needs qualifying — most likely it holds at the 8-tick, population-4
geometry and not at 24 ticks, which is precisely what the document says elsewhere
(:60-66) and what `PR63_CLAIMGATE_AUDIT_20260924.md`:184-205 records. The mechanism
paragraph should state the geometry to which it applies.

### C3 — the plan's locked pass criterion is contradicted by the critique's own evidence. **load-bearing**

| Side | Anchor | Statement |
|---|---|---|
| A | `docs/hard_experiment_03/NEXT_SLICE_PLAN_20260924.md`:516-518 | criterion 2: "`cost_high - cost_0` on `d_sym` survives Holm ... and `cost_high` mean `d_sym` exceeds `channel_off` mean `d_sym`. The second condition is the one pilot_v1 failed." |
| B | `NEXT_SLICE_PLAN_20260924.md`:472-486 | the slice freezes "trace-only Gorelick samples for all arms" and "the existing paired Holm contrasts", with no equal-sample-size requirement |
| C | `WAVE_MUTATIONAL_CRITIQUE_POST.md`:45-47 | equal-n rarefaction reverses the sign on both seeds (delta −0.0323527113 and −0.0387629516); only 12.2 per cent and 2.0 per cent of draws favour `cost_high` |
| D | `WAVE_MUTATIONAL_CRITIQUE_POST.md`:147-149 | wave-4 item 6: "pre-register its sample-size handling: state the expected per-arm event count, fix a common n for the primary contrast, and commit the bias treatment before the campaign runs" |

So the plan locks a pass condition that the post-results critique has already shown is
satisfied only by the sample-count imbalance the critique rejects, and the plan does not
adopt the equal-n requirement that the critique makes mandatory. A reader who takes the
plan as the operating design will accept a right-signed `cost_high` versus `channel_off`
comparison that the other document calls an artefact. Either criterion 2 must adopt the
equal-n comparison, or the plan must say explicitly that its primary contrast remains
unequal-n, that this is a known confound, and that no mechanism sentence will be
written from it.

### C4 — the charter's step-(1) exit criterion and the plan's own wave 2 cannot both govern. **load-bearing**

| Side | Anchor | Statement |
|---|---|---|
| A | `docs/PROCESS_CHARTER.md`:140 | queue step (1) exit requires "the dose–response gate is a real gradient rather than a tie" |
| B | `NEXT_SLICE_PLAN_20260924.md`:559-564 | "the ordinal gate may remain trivially satisfied ... The ordinal gate must therefore not be presented as evidence of a dose-response; only the paired contrasts carry information" |

The plan concedes in advance that the charter's exit condition for the step it is
executing will not be met, and proposes to exit on the paired contrasts instead. The
charter is the document that binds process, so as written the slice cannot clear step
(1) while the plan describes a route that skips that requirement. One of the two texts
must change: either the charter's step-(1) exit drops the gradient requirement in favour
of "a pre-registered contrast that survives matched-sample correction", or the plan adds
a gradient test to its criteria. The critique's own conclusion agrees with the charter
on the substance: the ladder has two states, so no gradient exists
(`WAVE_MUTATIONAL_CRITIQUE_POST.md`:80-81, once corrected per C1).

### C5 — the plan keeps an ablation contrast it has just concluded cannot isolate the mechanism. **load-bearing**

| Side | Anchor | Statement |
|---|---|---|
| A | `NEXT_SLICE_PLAN_20260924.md`:433-441 | "comparing `cost_high` to `channel_off` compares 'cost on and tasks classified' with 'cost off and no task classification at all', which cannot isolate the cost" and the arm must not be "upgraded to a mechanism-exclusive control" |
| B | `NEXT_SLICE_PLAN_20260924.md`:485-486 | "Primary contrasts, unchanged: `cost_high - cost_0`, `cost_moderate - cost_0` and `cost_high - channel_off`, paired by seed with Holm correction over the three" |
| C | `PR63_CLAIMGATE_AUDIT_20260924.md`:335-344 | because `channel_off` equals `cost_0`, that contrast is numerically the primary contrast, so Holm is applied to non-independent hypotheses |

A and B are in the same document, forty lines apart. Keeping a contrast while conceding
it cannot isolate its mechanism, and then making it a pass condition, is the soft-pass
shape this project refuses elsewhere: the third contrast contributes no independent
falsification but is counted as multiplicity.

### C6 — the plan's wave 2 carries a stale premise about the cost arms

| Side | Anchor | Statement |
|---|---|---|
| A | `NEXT_SLICE_PLAN_20260924.md`:559-562 | "`cost_moderate` and `cost_high` produce identical `d_sym` in pilot_v1 because the two arms differ only in the ATP charged, which may not change which actions are affordable" |
| B | `WAVE_MUTATIONAL_CRITIQUE_POST.md`:16-28 | at 24 ticks `cost_high` differs from `cost_moderate` (28 events against 36; `d_sym` 0.0369351046 against 0.0307564295), and seed 1001 reproduces the shape |

The pilot_v1 half of statement A is true — the committed pilot artifact shows both at
`0.0254163808` — but the plan uses it to predict the next slice, and the new
measurement contradicts the prediction. The plan's wave 2 should be updated to say that
the 0.25 ATP level is inert while the 0.50 ATP level is not, which is also what this
audit measured independently (`PR63_CLAIMGATE_AUDIT_20260924.md`:112-121).

### C7 — the set contains two mutually exclusive provenance claims about the same source. **load-bearing for any literature sentence**

| Side | Anchor | Statement |
|---|---|---|
| A | `NEXT_SLICE_PLAN_20260924.md`:611-613 and :624-626 | the PubMed Central deposit "whose main text and methods were read"; the report of 50 replicates per treatment is "verified from that paper's own methods section only as '50 trials'" |
| B | `NEXT_SLICE_PLAN_20260924.md`:526-529 | the report must state that "the published experiment used 50 trials of 400 colonies over 200,000 updates" |
| C | `WAVE_MUTATIONAL_CRITIQUE_POST.md`:91-92 | "the published comparison it imitates used fifty trials of four hundred colonies over two hundred thousand updates" |
| D | `WAVE_MUTATIONAL_CRITIQUE_POST.md`:166-168 | "the full text could not be retrieved, so its replicate count is stated as unverified rather than assumed" |
| E | `PR63_CLAIMGATE_AUDIT_20260924.md`:38 (query S3) | the full text could not be retrieved independently: browser verification interstitial, HTTP 403, and failing REST endpoints |

A says the methods were read; D says the full text could not be retrieved. C and B quote
scale figures — "400 colonies", "200,000 updates" — that appear nowhere else in the set
with a resolvable citation, and E records an independent retrieval failure. At most one
of A and D is correct. This is the exact failure the project's refuse list names, and it
matters more than usual here because the plan turns the figure into a required sentence
in the next report (:526-529). Required resolution: state one provenance, and if the
methods text was in fact read, cite what it says verbatim; if it was not, delete the
figures at :528 and :92 and say the scale is unverified, as the critique already does.

### C8 — the plan requires an amendment but not the ordering the charter and the critique require

| Side | Anchor | Statement |
|---|---|---|
| A | `docs/PROCESS_CHARTER.md`:192-196 | "A preregistration is hashed before any campaign number is produced, and any change to the operational definition of a preregistered metric ... needs a hashed amendment **before** the new numbers" |
| B | `WAVE_MUTATIONAL_CRITIQUE_POST.md`:144-146 | "a hashed preregistration amendment before any replacement readout is used for numbers" |
| C | `NEXT_SLICE_PLAN_20260924.md`:537-538 | "Any prereg change to the isolation criterion lands as its own committed amendment with its own digest" — no ordering stated |
| D | `NEXT_SLICE_PLAN_20260924.md`:259 | by contrast, for tick and population changes the plan does state the ordering: "a recorded amendment, made before the campaign" |

The plan applies before-the-campaign ordering to the geometry knobs and omits it for the
readout replacement, which is the more consequential of the two. One sentence at
:537-538 fixes it: the amendment is hashed and committed before the pilot_v2 campaign
runs. Without it, the set's own rule is satisfiable by committing the amendment
afterwards.

### C9 — no document still claims the ablation is fixed, but one implies it

No text in the set states as fact that the ablation is right-signed. The nearest
approach is `NEXT_SLICE_PLAN_20260924.md`:472-475, which freezes the PR #63 sampling
repair and the existing contrasts as settled, and :518, "The second condition is the one
pilot_v1 failed" — an implication that the frozen repair now satisfies it. Read against
`WAVE_MUTATIONAL_CRITIQUE_POST.md`:45-47 and `PR63_CLAIMGATE_AUDIT_20260924.md`:552-571,
that implication is wrong. It should be stated as an open question, not as a frozen
result. This is a wording finding rather than a logical contradiction, and it is the
cheapest of the nine to fix.

### C10 — the set contains two mutually exclusive next slices. **load-bearing**

A fifth document is untracked in the same working tree and belongs to the same round:
`docs/hard_experiment_03/BRAINSTORM_WAVE_PRE_PUSH_20260924.md`, written from the
innovator seat. It was not in the payload list given to this audit, but it will land in
the same push, so it is inside the consistency scope.

| Side | Anchor | Statement |
|---|---|---|
| A | `NEXT_SLICE_PLAN_20260924.md`:463-475 | the locked slice is pilot_v2, "replace the width census with a two-stage behavioural autonomy readout on carried survivor genomes ... and re-run the pilot once", with the trace-only rule and the existing contrasts frozen |
| B | `NEXT_SLICE_PLAN_20260924.md`:516-518 | criterion 2 is the right-signed `cost_high - cost_0` and `cost_high` above `channel_off` |
| C | `BRAINSTORM_WAVE_PRE_PUSH_20260924.md`:16-20 | "no, not in the form I wrote it ... I recommend reordering the work and dropping the part of my plan that put the readout replacement first" |
| D | `BRAINSTORM_WAVE_PRE_PUSH_20260924.md`:151-162 and :388-396 | drop the two-stage solo re-run from the immediate slice, drop "right-signed contrast survives Holm" as written, and reorder into stage 1 (equal-n instrument), stage 2 (a charge that matters plus a behavioural gate), stage 3 (the autonomy readout) |

Two documents in the same push specify different next slices: one locks a solo-stage
readout and the unequal-n criterion, the other says that criterion cannot be evaluated and
that the readout should move a slice later. A reader who implements the plan builds the
design the other document rejects. One of the two must be amended or marked superseded in
this pass. The honest resolution is the one the second document proposes, since its
reasoning is confirmed by the measurement in `WAVE_MUTATIONAL_CRITIQUE_POST.md`:45-47 and
by the code facts in sections 1.2 and 1.3 of its own text.

### C11 — one document calls the treatment inert; the measurement says it is inert only at the small geometry

| Side | Anchor | Statement |
|---|---|---|
| A | `BRAINSTORM_WAVE_PRE_PUSH_20260924.md`:81-84 | "the budget does not run down. The arm's behaviour is therefore the same as the control's, and the treatment is a bookkeeping entry" |
| B | `WAVE_MUTATIONAL_CRITIQUE_POST.md`:16-28 | at 24 ticks the high-cost arm differs from control: 28 events and 18 switches against 36 and 26, `d_sym` `0.0369351046` against `0.0307564295`, reproduced on seed 1001 |

This audit's own partial campaign measured the same 24-tick structure independently
(`PR63_CLAIMGATE_AUDIT_20260924.md`:112-121). Statement A is correct at 8 ticks and
population 4, where all five arms produce identical multisets
(`WAVE_MUTATIONAL_CRITIQUE_POST.md`:60-66), and wrong at 24 ticks. The scan is also
harder to sustain against A's own later text, which requires the high-cost arm's switch
rate to be strictly below the zero-cost arm's (`BRAINSTORM_WAVE_PRE_PUSH_20260924.md`:137-138)
— a requirement that presupposes the treatment can reach behaviour. The paragraph needs
its geometry named, exactly as C2 does.

### C12 — a stated bias constant does not follow from its own stated dimensions

`BRAINSTORM_WAVE_PRE_PUSH_20260924.md`:30-33 states the leading-order plug-in bias as
`(I - 1)(T - 1) / (2 n ln 2)` bits and then evaluates it as "about 3.6 / n bits" for
"eight individuals and two task classes". For `I = 8` and `T = 2` the stated formula
gives `7 / (2 ln 2)`, which is about 5.05, not 3.6; 3.6 follows from six observed
individuals. The discrepancy is one word away from fixed and may simply be a mismatch
between the illustrative count and the arithmetic. It is recorded because the paragraph
is being shipped as the quantitative account of the central defect, and because this
audit's own Monte Carlo through the checked-in estimator confirms the qualitative claim —
the bias falls monotonically with sample size, from 0.137 at n = 28 to 0.102 at n = 36
under an independence null (`PR63_CLAIMGATE_AUDIT_20260924.md`:143-183) — while not
confirming the constant. Correct the sentence or the dimensions, not the conclusion.

### C13 — the endpoint-folding account and the sample-size account are the same mechanism, told twice

`PR63_CLAIMGATE_AUDIT_20260924.md`:88-107 attributes the pilot_v1 inversion to the folding
of switch-record endpoints into the cost arms, following
`WAVE_MUTATIONAL_SPECIALIZATION_BRAINSTORM.md`:21-23.
`BRAINSTORM_WAVE_PRE_PUSH_20260924.md`:43-50 argues the general cause is the sample-count
bias and that folding is one instance of it, since the folded arms accumulated more
samples (40, 34 and 34 against 20 for the disabled arm), which under a falling-with-n
bias lowers their apparent value. The two accounts agree in direction and the second
subsumes the first. The set should present the sample-count mechanism once, with folding
named as its pilot_v1 instance, or a reader will treat them as competing explanations.



### Consistency verdict

Thirteen findings, five of them load-bearing. The documents do not yet read as one
voice. C1 inverts the measured geometry, C3 locks a criterion the set's own evidence
rejects, C5 keeps a contrast the same document says cannot isolate its mechanism, C4
sets the charter against the plan's stated exit route, and C10 ships two mutually
exclusive next slices in the same push. C7 offers a reader two incompatible accounts of
whether a literature source was read. C2, C6, C11 and C13 are geometry and mechanism
statements that need one clause each; C8 is a missing ordering sentence; C9 and C12 are
wording and arithmetic. Every one of the thirteen is a text edit; none requires new
computation, and eleven of them are a paragraph or less.

---

## 2. Test adequacy, adversarially

The question for each behaviour: is there a test that would fail if the behaviour
broke? A test that passes under the old defective code is not coverage of the defect,
so the old-code check is applied to each row.

**Standing result first.** The campaign-aggregate and isolation surfaces have no direct
test coverage at all. A repository-wide search over `tests/` finds zero references to
`_solo_scores_for_isolation`, `_group_scores_for_isolation`, `_last_evolved_genomes`,
`_extract_switch_stats`, `_manipulation_failures`, or `switch_cost_realized`. Every
behaviour that decides the HE03 result lives in code that no test names.

| # | Behaviour | Test that would fail if it broke | Verdict |
|---|---|---|---|
| i | switch cost charged, `switch_cost_realized` correct | `tests/test_hard_experiment_03.py`:85-106 asserts the returned task, the record type, `record.charged is True`, and a 10.0 to 9.5 ATP debit | **Partially covered.** The unit path is pinned. The campaign aggregate is uncovered, and it is wrong in a way no test could catch: `_extract_switch_stats` (`hard_experiment_03.py`:656-666) sums `record.switch_cost_atp` for every record and ignores `record.charged`, so a debit that fails still inflates the total. The failure path of `apply_task_switch_cost` (debit returns `None` to `charged=False`, `task_switch_cost.py`:176-188) is untested |
| ii | the charge changes which actions are taken | none. `test_he03_dual_task_overlay_enables_switches_and_refuses_ci` (:194-209) asserts `campaign.assay_failed is False` and `n_switches > 0` — both true when the arms are behaviourally identical, which is exactly the state `WAVE_MUTATIONAL_CRITIQUE_POST.md`:60-66 reports | **Not covered.** The suite is green while the manipulation is inert: `_manipulation_failures` (`hard_experiment_03.py`:768-797) checks that a debit was recorded, never that behaviour changed, and `overall_pass` (:820) does not read the ordinal gate |
| iii | the isolation readout can return a failing value | none for the HE03 path. `test_isolation_assay_secondary_drop` (:128-137) drives the generic helper `run_isolation_assay` with hand-written scores and asserts a mean drop of 0.6 | **Not covered for the code that produced the artifact.** The helper is not the wiring; a change that made the HE03 readout constant would not fail any test |
| iv | the ablation uses equal-n samples | none, and the behaviour does not exist: `build_hard_experiment_03_paired_contrasts` (:956-977) compares raw unequal-length sample sets | **Not covered, not implemented** |
| v | BAIC pins byte-identical under the LF-normalising digest | coverage is extensive but uses the wrong method. Thirteen test files carry the three pin digests and assert them with `hashlib.sha256((ROOT / path).read_bytes()).hexdigest()`, for example `tests/test_host_parasite_phase25.py`:104-106, `tests/test_host_parasite_abstract_phenotype.py`:60-62, `tests/test_host_parasite_hard_regressions.py`:317-320, `tests/test_host_parasite_sim_fidelity.py`:246-249 | **Covered in intent, wrong in method.** See the finding below |
| vi | the claim ceiling cannot be raised by a pilot | `tests/test_hard_experiment_03.py`:166-178 asserts the ceiling, the flags, and `gates.get("cleared_for_research") is False`; :154-158 asserts the module constant and the DAG | **Covered against constant edits, vacuous against rule changes.** Every one of those assertions is entailed by a literal (`CLAIM_CEILING` at :48, `cleared_for_research` at :824, the hardcoded false block at :838-850), so none would fail if the rule became evidence-dependent but still refused |

### The raw-byte pin assertions are false on this checkout

This is the one finding in this section that affects the run happening now.

The project ships a helper for exactly this problem.
`src/codontrace/genesis/text_digest.py`:1-15 documents it: "SHA-256 after CRLF/CR -> LF
... Document pins must match the repository blob (LF), not the checkout. Keep
`hashlib.sha256(Path.read_bytes())` only for true binary artifacts."
`docs/claimgate/WINDOWS_TEXT_DIGEST.md`:1-14 repeats the rule and lists the call sites
that must use it.

The pin tests do the opposite. Measured on this working tree, with
`core.autocrlf=true` and `.gitattributes` set to `* text=auto`:

| Pinned file | raw `read_bytes()` digest equals the pin? | LF-normalised digest equals the pin? |
|---|---|---|
| `docs/hard_experiment_01/results_v7.json` | no (raw `4a5987c2ed0f09d1088b3c1bca6d81fe2310f3867fa84f22a33fbeee7b5d7efd`) | yes |
| `docs/claimgate/risk_bar.json` | no (raw `b7091921bf00c350fa286caf117fa46af81e9760b1b6d4d135eefd042dabd404`) | yes |
| `docs/claimgate/biomedical_study.json` | no (raw `2e5193639aad58ceda68ef9bc33943f8eae2c45f042209a060af890c93785079`) | yes |

So every one of those thirteen parametrised assertions is false here. This is a
predicate evaluation against the working tree, not a test run, which is why it can be
stated without executing the suite.

Why it has never surfaced: the full-suite job runs only on `ubuntu-latest`
(`.github/workflows/ci.yml`:22), where a checkout is LF and raw bytes equal the pin,
and the Windows and macOS job (`ci.yml`:86) runs a subset (`ci.yml`:110) that contains
no host-parasite file. The defect is therefore latent in integration and visible only
on a local Windows checkout — which is the situation right now.

Consequence for the push decision, stated plainly: if the local full-suite run reports
pin failures, they are **not** caused by PR #63, and they are not evidence that the
pins moved. The pins are intact, verified three ways in
`docs/claimgate/PR63_CLAIMGATE_AUDIT_20260924.md`:378-401. The repair is to switch the
thirteen assertions to `sha256_text_file`, which the project already ships and already
tests: `tests/test_text_digest.py`:17-19 pins the helper's semantics (LF digest equals
CRLF digest, and the CRLF digest differs from the raw byte hash).

One piece of genuine coverage worth crediting: `tests/test_claimgate_he03_adapter.py`:22-27
reads the tree and asserts `he03_research_not_in_tree is True`, so a stray research
artifact at the canonical path would break a test loudly rather than pass silently.
That is the tripwire that makes the `results_v1.json` lock enforceable in practice.

### Tests that must be added before the next code push

Each is cheap and synthetic: none needs a campaign, so all of them can live in the
continuous-integration suite without wall-clock cost. Naming only, as instructed.

1. **`test_he03_switch_cost_realized_counts_only_charged_debits`** — assert
   `_extract_switch_stats` returns a realised total equal to the sum over records with
   `charged` true, using synthetic records that include at least one `charged=False`
   entry. The assertion must fail against today's sum-over-everything implementation.
2. **`test_he03_manipulation_check_fails_when_arms_are_behaviourally_identical`** —
   build synthetic seed records whose five arms share one `d_sym` and one
   `n_task_samples`, and assert `_manipulation_failures` returns a behavioural failure
   code. This is the gate test for behaviour (ii); it requires adding that code path,
   which is the point of the test.
3. **`test_he03_ordinal_tie_is_not_reported_as_overall_pass`** — construct a campaign
   whose `cost_0` and `cost_moderate` means are equal, and assert
   `evaluate_hard_experiment_03_pilot_gates(...)["overall_pass"] is False` with the tie
   named in the gate payload. Assertion must fail while `overall_pass` ignores the
   ordinal gate at `hard_experiment_03.py`:820.
4. **`test_he03_isolation_readout_can_fail`** — drive the isolation helpers on a
   synthetic group result where every survivor retains both task classes, assert the
   readout reports the null value, then drive a population where one class is lost and
   assert a positive value; finally assert that a constant-baseline implementation is
   flagged (`assay_failed_isolation_uninformative`) rather than passing.
5. **`test_he03_isolation_readout_separates_complementarity_from_capability_loss`** —
   feed two synthetic populations with the same mean task width but different
   structure: in one, survivors split across the two single-task classes; in the other,
   all survivors lost the same class. Assert the readout or its declared companion
   diagnostic distinguishes them. The width census cannot pass this test, which is the
   assertion's purpose.
6. **`test_he03_primary_contrast_uses_matched_sample_counts`** — run two arms whose
   trace counts differ, and assert the contrast helper either rarefies to a common n or
   raises a configuration error; then assert the reported n used in the contrast is
   equal across arms and recorded in the artifact.
7. **`test_he03_ablation_arm_differs_behaviourally_from_cost_0`** — assert that
   `channel_off` and `cost_0` produce different trace multisets at a fixed seed and
   geometry, or, if the arm is replaced, that the new ablation arm changes a
   configuration field that `_extract_task_samples` consumes. Must fail against the
   current pair, which differ only in whether the debit path is entered.
8. **`test_he03_paired_contrasts_are_computed_from_data`** — build two synthetic seed
   record sets with different deltas and assert the contrast means, intervals and
   `p_holm` differ between them, and that a deliberately wrong-signed set yields
   `claim_downgraded is True`. Guards against another hardcoded failure string.
9. **`test_he03_decision_failures_respond_to_evidence`** — pass a synthetic
   research-scale contrast set with a Holm-surviving right-signed primary and a
   right-signed ablation, and assert the returned failures no longer contain
   `no_holm_surviving_primary_contrast` or `ablation_contrast_wrong_sign_or_null`, while
   the separate candidate-refusal policy code remains. Must fail against the current
   unconditional implementation (`hard_experiment_03.py`:980-1013).
10. **`test_baic_pins_lf_normalised_digest_matches`** — for each of the three pins,
    assert `sha256_text_file(path) == expected`. Add it, and refactor the thirteen
    raw-byte assertions to call the same helper, so the platform rule has one
    implementation and one place to break. Must fail if a pinned file changes.
11. **`test_he03_pilot_and_research_seeds_are_disjoint`** — assert
    `set(PILOT_SEEDS).isdisjoint(default_research_seeds())`, pinning the preregistration's
    seed fence (`docs/HARD_EXPERIMENT_03_PREREG.md`:43-44). Today only the pilot tuple
    itself is asserted (`tests/test_hard_experiment_03.py`:190-191).
12. **`test_he03_trace_samples_ignore_switch_records`** — replace the weak assertion at
    `tests/test_hard_experiment_03.py`:260-270 with one that constructs a stub result
    whose generation carries populated `task_switch_cost_records` and empty `traces`,
    and asserts `_extract_task_samples(...) == ()`. Under the pre-fix construction that
    call returns the switch endpoints, so this is the test that actually regresses the
    pilot_v1 defect; the current test asserts only that some task-A sample exists and
    passes under both implementations.

Priority order if the next push carries code: 12 and 10 first (both regress defects
already observed in the wild), then 1, 2, 3 and 9 (the gate holes), then 4 to 8 (the
instruments, which the plan is about to replace anyway).

---

## 3. Safety of the push itself

### Answers to the direct questions

**Should the documents go on the existing PR branch?** Yes — onto `pr63`, rebased first.
The audit is the merge gate for the code in that branch, and a gate that lives on a
different branch as the code it gates is the dangling-reference problem in a larger
form: the branch could merge without its audit, and the audit's line references would
age against a moving branch. Pushing to `main` directly is the worst of the three
options: it would put a "do not merge" recommendation about an unmerged branch into the
main history, ahead of the review surface, and it would separate the critique from the
commit it criticises. A separate branch is the second-worst: the payload fragments into
two review conversations, and one of them will be forgotten before the merge decision.

**The failure mode this guards against.** Three, in order of likelihood:

1. **The duplicated document commit.** `main` at `b3772ce` already adds
   `docs/hard_experiment_03/WAVE_MUTATIONAL_SPECIALIZATION_BRAINSTORM.md` (77 lines), and
   the branch's `abb7172` adds the same 77 lines with the identical blob
   `78c5a5c6295f0c4eda1d31c5f36ed767a65878dd`.
   `git diff b3772ce pr63 -- docs/hard_experiment_03/WAVE_MUTATIONAL_SPECIALIZATION_BRAINSTORM.md`
   is empty; `git patch-id` does not flag the pair because `abb7172` also carries the
   code change. If the new documents are committed on top without rebasing, merging
   records the same document addition twice, and the duplicate survives into history as
   if the branch had authored a document `main` already had. Rebasing first drops that
   hunk entirely and leaves the code and test changes intact.
2. **A force-push racing another researcher.** The working tree is shared and the
   machine is mid-run, so a rebase is a real possibility while others hold the branch.
   A plain force-push here can silently discard a colleague's commit. The rebase must be
   followed by `--force-with-lease` and by fetching immediately before it, never by
   `--force`.
3. **A stray research artifact written by a pushed tool.** `tools/run_he03_parallel.py`:113-118
   writes to any caller-supplied `--out` path, with `parent.mkdir(parents=True,
   exist_ok=True)`. Nothing stops `--out docs/hard_experiment_03/results_v1.json`, and
   the tool's own default scale is pilot, so the mistake is one flag wide. Two things
   currently mitigate it: the file it writes is a flat list of per-arm summaries rather
   than a campaign payload, so the adapter would refuse it
   (`src/codontrace/claimgate/adapters/codontrace_he03.py`:68-75 requires a JSON object,
   and :165-167 requires a real protocol digest), and
   `tests/test_claimgate_he03_adapter.py`:22-27 reads the tree and would fail once the
   file existed. Recommend a guard that refuses any `--out` inside the repository, or
   refuses the names `results_v1.json` and any path under `docs/`. Until then the tool
   should carry a docstring line saying it must write outside the tree.

### Additional pre-push findings on the tools

These are small but cheap to fix in the same commit, and two of them affect whether the
critique's numbers can be reproduced at all.

1. **An undeclared dependency.** `tools/probe_nmi_bias.py`:29-32 imports `sklearn`, and
   scikit-learn appears nowhere in the repository's declared dependencies: `pyproject.toml`
   declares `dependencies = []`, and the `dev`, `science`, `qd`, `research` and `causal`
   extras contain no scikit-learn. A search over the repository's `.toml`, `.txt`, `.cfg`,
   `.md`, `.yml` and `.yaml` files finds no mention. The package is installed in this
   developer's interpreter (1.8.0), which is why the tool runs locally, but a reviewer
   reproducing the critique from a clean install of the declared extras cannot run it.
   Since `WAVE_MUTATIONAL_CRITIQUE_POST.md`:30-36 and :43-48 rest on that tool's output —
   the chance-corrected column and the equal-n adjusted-MI deltas — those numbers are not
   reproducible from the declared environment. Either add an extra that declares it, or
   replace the two sklearn calls with an in-repository chance correction.
2. **Six new lint findings.** `tools/probe_nmi_bias.py`:18 (`collections` imported and
   unused) and `tools/run_he03_parallel.py`:51, 58, 59, 60, 61 (import block un-sorted,
   four unused imports). Continuous integration lints only `src` and `tests`
   (`ci.yml`:133), so the build is unaffected, but the repository-wide count grows from
   49 to 55 and five of the six are one-line deletions.
3. **The tools do run in continuous integration, in one respect.**
   `ci.yml`:39-40 runs `python -m compileall -q src tests examples tools`, so a syntax
   error in any pushed tool breaks the build. All three compile as written.
4. **The "Reject probe leftovers" step will not trip.** `ci.yml`:45-74 matches only
   `.grok_write_probe*`, `.size_test_*.txt`, `*_FULL_RESTORE*`, `*_backup*` and `*.orig`.
   `probe_he03_traces.py` and `probe_nmi_bias.py` do not match any pattern, so the step's
   alarming name does not apply to them. Verified by reading the matcher, not by running
   the pipeline.
5. **The parallel runner bypasses the campaign object.** `tools/run_he03_parallel.py`
   calls the private `_run_arm` per shard and assembles its own list, so it produces
   neither a `HardExperiment03Campaign` nor a protocol digest, and it never checks its
   sharded output against the sequential path. Anything published from it is therefore
   not comparable to `pilot_v1.json` by digest. Recommend a self-check flag that runs one
   seed sequentially and asserts the records match, or an explicit note that the tool is
   a probe and not an artifact producer.

### The zip copy

Take the archive before the push, while the untracked documents and tools are still in
the tree, because those six files are the entire payload and none of them is recoverable
from git until the push succeeds. Archive the working tree including untracked files,
record the archive digest next to the commit identifier in the push note, and keep the
previous archive until the new one is verified. The archive is the only protection
against a mistaken force-push; a lease guard prevents the common case but not a
mistyped refspec.

### Recommendation

**Push, but not this revision of the set.** Specifically:

1. Fix C1, C3, C4, C5, C7 and C10 in the documents first. Each is a wording or criteria
   change, not new computation, and each one currently lets a reader reach the opposite
   conclusion from the same evidence — or, for C10, build a different next slice. C2, C6,
   C8, C9, C11, C12 and C13 should ride in the same pass because they are single
   sentences or a corrected constant.
2. Rebase `pr63` onto current `main` before committing the documents, so the duplicated
   brainstorm hunk is dropped and the set lands as one commit on top of a clean base.
   Keep two commits, not one: the import reorder as a source fix, the six documents as a
   documentation commit. That keeps the source change independently reviewable and
   revertible, which matters because the audit's recommendation is to refuse the code as
   it stands.
3. Decide the tools separately from the documents. If `probe_nmi_bias.py` ships without
   a declared dependency, add the dependency or an in-repo correction in the same
   commit, and fix the six lint findings. Add the write guard to
   `run_he03_parallel.py`.
4. Archive first, fetch, rebase, commit, then `--force-with-lease`. Never `--force`.
5. After the push, record in the PR conversation that the local pin-test failures the
   full suite will report are caused by raw-byte hashing on a CRLF checkout
   (section 2), and are not evidence that a pinned file moved, so that the merge
   decision is not made on a misread test result.

**What would make the push unsafe in the lock sense.** Nothing in this payload touches a
hard lock: no pinned file is modified, the only source change is an import reorder, no
`results_v1.json` is written or proposed, the ceiling and the refuse list are unchanged,
and the added prose carries no prohibited vocabulary. The block above is about the
documents contradicting each other and about test gaps, and it should be reported as
exactly that rather than as a lock violation.
