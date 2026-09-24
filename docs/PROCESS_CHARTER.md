# CodonTrace Genesis — process charter

Status: durable operating process for every scientific wave and slice.
Date of this revision: 2026-09-24 (Asia/Tehran).
Scope: how work is chosen, searched, reviewed, locked, and committed.

This charter governs process only. It does not raise any claim ceiling, does
not replace [`CLAIMS.md`](../CLAIMS.md) (claim policy), and does not replace a
per-experiment preregistration. Where this charter and a prereg disagree, the
prereg governs the experiment and this charter governs the process. Where a
sentence in a pull request, README, or paper cannot be mapped to a row in
`CLAIMS.md`, that sentence must not be written (`docs/WHY_NOT_INTELLIGENCE_YET.md`:407-408).

Every rule below names the file and line that anchors it. A rule whose anchor
no longer exists must be re-anchored or withdrawn; that check is part of the
audit in section 9.

---

## 1. Roles

Four roles are required on every scientific slice. Role D is required, not
optional: a slice that ships without external input has not been designed, only
implemented. The four-role template is recorded in
`docs/hard_experiment_03/WAVE_COLLECTIVE_DOL_BRAINSTORM.md`:27-39 and repeated
per wave in `docs/hard_experiment_03/WAVE_MUTATIONAL_SPECIALIZATION_BRAINSTORM.md`:31-51.

| Role | Owns | Must produce per slice | Must not |
|---|---|---|---|
| A — digital-evolution empiricist | the mechanism claim and its ecology | the causal story, the substrate prerequisites, the honest scale statement | plant the outcome (roles assigned by hand and then reported as evolved) |
| B — causal / ClaimGate auditor | falsification | for every gate and readout: what could make it pass wrongly, and the file:line evidence for how it is computed | audit a slice they authored; accept a summary in place of a computation |
| C — measurement / information theory | the readout | the metric definition, its information content, its degenerate cases, its units, and what it cannot distinguish | report a proxy as if it were the construct named in the prereg |
| D — cross-field innovator | outside input | at least one concrete import from outside digital evolution, each marked ADOPT or REJECT with reasoning; a REJECT with reasoning counts fully | pad the list with ideas that do not change any measurement |

Two further role rules follow from how the current waves were run:

1. The auditor (B) is adversarial by construction. The expected output of an
   audit is either a refusal or a specific defect list; "no findings" must be
   argued, not assumed (`docs/hard_experiment_03/WAVE_COLLECTIVE_DOL_BRAINSTORM.md`:33).
2. The innovator (D) must state, for each import, the module or hook where it
   would land, so the idea is testable rather than rhetorical. The live example
   is `docs/hard_experiment_03/NEXT_SLICE_PLAN_20260924.md`:200-393.

---

## 2. Search before every action

Two kinds of search are mandatory. Both are auditable: a search that leaves no
record did not happen.

### 2.1 Scientific record search

| | |
|---|---|
| Trigger | before locking a slice; before writing any citation, DOI, or numeric claim about an external system; before writing a pass/fail criterion that depends on an external result; before comparing this project's scale to another project's scale |
| Recorded artifact | a **Search log** table in that wave's design document with one row per query: the exact query string as issued, the identifier that resolved (DOI or URL), the date, one line on what the source actually supports, and one line on what it does **not** license |
| Reviewer check | open the recorded identifier and re-read it. If it does not resolve, the citation is blocking. If the recorded "supports" line is stronger than the source, that is a blocking claim defect. A remembered paraphrase with no identifier does not count as a search |

Anchors: literature is searched **before** design or code, DOIs are cited, and
mechanisms are not invented from memory (`handoff/00_NEXT_BOT_STATUS_2026-09-13.md`:36);
the existing wave designs reserve a section for anchors found before action
(`docs/hard_experiment_03/WAVE_COLLECTIVE_DOL_BRAINSTORM.md`:7-18,
`docs/hard_experiment_03/WAVE_MUTATIONAL_SPECIALIZATION_BRAINSTORM.md`:7-17);
invented DOIs are a refuse-list item (`docs/claimgate/host_parasite_port_20260924/DETOY_PHASE_PLAN.md`:10).

The "does not license" line is the part that carries the discipline. Goldsby et
al. 2012 reports division of labour in actively evolving populations of digital
organisms under rising task-switching costs, including loss of the ability to
perform tasks in isolation under high cost. It does not license update-count
equivalence, and this project's prereg forbids claiming it
(`docs/HARD_EXPERIMENT_03_PREREG.md`:46). Verified metadata for the two anchors
used by HE03: Goldsby, Dornhaus, Kerr, Ofria, *PNAS* 109(34):13686-13691,
doi:10.1073/pnas.1202233109; Gorelick, Bertram, Killeen, Fewell, *The American
Naturalist* 164(5):677-682, doi:10.1086/424968 (both resolved through Crossref
on 2026-09-24; see `docs/claimgate/PR63_CLAIMGATE_AUDIT_20260924.md` for the
full search log).

### 2.2 Current-code search

| | |
|---|---|
| Trigger | before asserting any behaviour of the repository (what a function returns, what a gate enforces, what an arm configures, what a file contains), and before writing any `file:line` in a committed document |
| Recorded artifact | next to the claim: the exact command or probe used, the revision it was run against, and the line read. Record the revision explicitly, because the working tree may carry uncommitted edits that a reader will not reproduce |
| Reviewer check | re-run the recorded command at the recorded revision. If the cited line no longer contains the assertion, the finding is stale and blocking. Prose summaries, docstrings, and plan documents are not evidence of behaviour; they are claims to be tested |

Anchors: evidence levels require source code and artifacts, not descriptions
(`CLAIMS.md`:304-309); a prereg fixes the metric definition before code, so the
implementation must be read against it rather than inferred from its own
comments (`docs/HARD_EXPERIMENT_03_PREREG.md`:6, 30-40). Two method notes that
count as part of a code search:

- Text pins are compared with the LF-normalising helper
  `codontrace.genesis.text_digest.sha256_text_file`, never with raw byte
  hashing of a Windows checkout, or a correct pin will appear broken
  (`docs/claimgate/WINDOWS_TEXT_DIGEST.md`:1-14).
- Environment facts (interpreter, linter, test runner versions) are recorded
  with the finding, because a result that cannot be reproduced on the stated
  environment is not evidence.

---

## 3. Critique waves: two before build, two after results

Every slice runs four critique waves. Each wave produces numbered items, and
every item is either adopted into the locked slice or explicitly rejected with
a reason. A wave that produces only agreement is not a wave.

| Wave | When | Required content | Anchor |
|---|---|---|---|
| 1 | pre-build | soft-pass risk, pin risk, claim-escalation risk, scope creep | `WAVE_COLLECTIVE_DOL_BRAINSTORM.md`:41-46; `WAVE_MUTATIONAL_SPECIALIZATION_BRAINSTORM.md`:53-59 |
| 2 | pre-build, after the slice is locked | what the lock still gets wrong, stated against the lock text | `WAVE_COLLECTIVE_DOL_BRAINSTORM.md`:57-61; `WAVE_MUTATIONAL_SPECIALIZATION_BRAINSTORM.md`:71-77 |
| 3 | post-results | one position per role, written against the numbers actually produced | `WAVE_COLLECTIVE_DOL_CRITIQUE_POST.md`:6-24 |
| 4 | post-results | what is accepted and what is rejected for the next wave | `WAVE_COLLECTIVE_DOL_CRITIQUE_POST.md`:26-32 |

Additional rules that the existing waves establish:

- The post-results waves are required even when the slice fails. A committed
  failure with explicit FAIL lines is the expected output, not a reason to
  withhold the artifact (`docs/hard_experiment_03/PILOT_V1_REPORT.md`:52-64;
  `WAVE_COLLECTIVE_DOL_CRITIQUE_POST.md`:30).
- Wave 2 must be written after the lock and before the build, and must engage
  the lock text, not the earlier brainstorm
  (`WAVE_MUTATIONAL_SPECIALIZATION_BRAINSTORM.md`:71-77).
- A positive-looking number is never sufficient on its own: the smallest
  contrast must survive correction **and** the ablation must be right-signed
  before any ceiling moves (`WAVE_COLLECTIVE_DOL_CRITIQUE_POST.md`:28).

---

## 4. Locked execution queue

The order below is binding. A step may not begin until the previous step's exit
criteria are recorded in a committed document. No step may be skipped to reach
an earlier-numbered claim outcome; in particular, step (2) is not entered to
escape a failure at step (1) (`docs/hard_experiment_03/PILOT_V1_REPORT.md`:74-80).

| Step | Content | Exit criteria | Anchor |
|---|---|---|---|
| 0 | hygiene: vocabulary, cite, and artifact hygiene before any new science | no invented DOIs, no loosened refuse list, pins byte-identical, registry and docs consistent | `docs/claimgate/host_parasite_port_20260924/DETOY_PHASE_PLAN.md`:8-11 |
| 1 | HARD_EXPERIMENT collective: task-switching → division of labour → ablation → isolation, multi-seed | manipulation checks pass on a committed artifact, the ablation contrast is right-signed, the secondary readout is non-degenerate, and the dose–response gate is a real gradient rather than a tie | `docs/hard_experiment_03/WAVE_COLLECTIVE_DOL_BRAINSTORM.md`:4; `docs/hard_experiment_03/NEXT_SLICE_PLAN_20260924.md`:4, 532-533 |
| 2 | earn the candidate honestly | the full flag set for a candidate is actually earned under `ScientificClaimGate`; no label is granted by amendment text or by a positive delta alone | `docs/WHY_NOT_INTELLIGENCE_YET.md`:395-400; `CLAIMS.md`:559-574 |
| 3 | Goldsby-grade group work: replication at a scale that can support a group-level claim | multi-replicate design, colony-level replication where the claim is group-level, prereg amendment before numbers | `docs/hard_experiment_03/PILOT_V1_REPORT.md`:80; `docs/HARD_EXPERIMENT_03_PREREG.md`:44 |
| 4 | long-horizon open-endedness measurement | Channon 2024 measurement protocol run as measurement only; a Type 1 pass stays blocked | `docs/OEE_LONG_HORIZON_PROTOCOL.md`:16-19; `README.md`:320 |

Steps (0) to (2) are recorded by the queue text itself and by the queue-step
references in the HE03 wave documents; step (3) is named as the next group-work
step after step (2); step (4) is the documented long-horizon target, explicitly
"measurement only" and never a pass. Pilot seeds and research seeds are
disjoint, and pilot results never serve as confirmatory evidence
(`docs/HARD_EXPERIMENT_03_PREREG.md`:43-44).

---

## 5. Hard locks

These do not change between waves. Each is verified and reported per wave, not
assumed.

1. **BAIC pins.** Three files are frozen:
   `docs/hard_experiment_01/results_v7.json` =
   `35bb593604438797755e5e7b28af4d1371992a6181a403d08005f7f45421cbd6`,
   `docs/claimgate/risk_bar.json` =
   `4dbe4aa3a6ef8e771f180d2a6589c64b0dd5ffebe0aa73703a7256c17d771cd7`,
   `docs/claimgate/biomedical_study.json` =
   `9685f2fbafb21477d977dfa0c0bf73e02bea81d084e7605978ea25c47bf5ddce`
   (`docs/hard_experiment_03/PILOT_V1_REPORT.md`:66-70). The comparison uses the
   LF-normalising text digest (`docs/claimgate/WINDOWS_TEXT_DIGEST.md`:1-14).
   Pins stay byte-identical forever (`docs/claimgate/host_parasite_port_20260924/PHASE25_REVIEW.md`:5).
2. **Engine hygiene.** Infection, virulence, and comparable domain physics live
   in the port, never in the engine module; the engine boundary check is a
   standing campaign (`docs/claimgate/host_parasite_port_20260924/SIM_FIDELITY_CAMPAIGNS_20260924.md`:42, 66).
3. **No population-package commit.** The population package stays out of the
   committed tree (`docs/claimgate/host_parasite_port_20260924/DETOY_PHASE_PLAN.md`:10;
   `.../DETOY_D5_D7_BRAINSTORM_5ROUND_20260924.md`:12).
4. **Human research prose in committed documents.** Committed prose reads as
   ordinary human research writing: no vocabulary from conversational writing
   tools, text generators, or automation workers, and no statements about how
   the text was produced (`docs/claimgate/host_parasite_port_20260924/DETOY_BRAINSTORM_5ROUND_20260924.md`:24;
   `.../DEPTH_BRAINSTORM_WAVE5.md`:27). The `handoff/` directory is an older
   era with pre-existing deviations from this rule; it is kept as history and is
   not a style model for new documents.
5. **Refuse list stays closed.** `intelligence`, `collective_intelligence`,
   `agi`, `tokyo_type1_passed`, `avida_replacement`, `open_ended_intelligence`
   and the related aliases stay blocked (`docs/PHASE_INDEX.md`:14-16;
   `CLAIMS.md`:356-367; `docs/WHY_NOT_INTELLIGENCE_YET.md`:401-406). A candidate
   label requires the full flag set, and smoke campaigns do not set those flags
   (`docs/WHY_NOT_INTELLIGENCE_YET.md`:395-400).
6. **No fabricated artifacts.** No research `results_v1.json` before the
   prereg's decision rule clears; the research path stays absent on purpose
   (`CLAIMS.md`:571-574; `docs/HARD_EXPERIMENT_03.md`:14).
7. **No invented citations or DOIs** (`docs/claimgate/host_parasite_port_20260924/DETOY_PHASE_PLAN.md`:10).
8. **Preregistration before numbers.** A preregistration is hashed before any
   campaign number is produced, and any change to the operational definition of
   a preregistered metric, including a secondary readout, needs a hashed
   amendment **before** the new numbers, not a docstring note after them
   (`handoff/00_NEXT_BOT_STATUS_2026-09-13.md`:37;
   `docs/HARD_EXPERIMENT_03_PREREG.md`:6, 39-40, 71-72).

---

## 6. Working-tree, branch, and commit discipline

1. **Rebase before coding.** Fetch and work from the latest main, or rebase the
   branch, before writing code (`handoff/00_NEXT_BOT_STATUS_2026-09-13.md`:35).
   Skipping this produced a duplicated document commit across two branches in
   the HE03 wave; a document that already exists on main with identical content
   must not be committed a second time on the branch.
2. **Commit and push every finished slice** so no unit of work is lost
   (`handoff/00_NEXT_BOT_STATUS_2026-09-13.md`:38).
3. **One slice, one branch, one pull request**, squash-merged, with the
   slice's own pass/fail lines in the commit body
   (`docs/claimgate/host_parasite_port_20260924/DEPTH_BRAINSTORM_WAVE6.md`:36).
4. **Pilot and research artifacts are different objects.** Pilot JSON goes to
   the pilot path with its own digest; research JSON is written only when the
   prereg clears it. Smoke runs in continuous integration; research runs outside
   it (`docs/HARD_EXPERIMENT_03_PREREG.md`:43-46).
5. **Review the revision, not the working tree.** An audit names the commit it
   examined. Uncommitted edits are not part of a review artifact, and a reviewer
   who cannot reproduce the audited revision must say so.
6. **No tag or package release without its own cut**, and no version recut
   (`handoff/00_README_START_HERE.md`:29).

---

## 7. What this charter does not do

- It does not grant, accelerate, or imply any claim. The ceiling is whatever
  `CLAIMS.md` and the current prereg allow, currently `runtime_observation` for
  the hard experiments (`CLAIMS.md`:564-567).
- It does not replace the honesty pointer; when a "we are not claiming
  intelligence" citation is needed, cite `docs/WHY_NOT_INTELLIGENCE_YET.md`
  once rather than restating it in every document (`docs/PHASE_INDEX.md`:39-41).
- It does not license removing a failing line from a report. Failing contrasts
  and inverted readouts are reported as failures
  (`docs/hard_experiment_03/PILOT_V1_REPORT.md`:58-62).

---

## 8. Live example

`docs/hard_experiment_03/NEXT_SLICE_PLAN_20260924.md` is the current worked
example of this process: literature and comparator findings (Part 1), the
cross-field import list (Part 2), the four role positions (3.1), the two
pre-build critique waves (3.2, 3.4), one locked slice with its own pass/fail
criteria (3.3), and the non-goals and refuse list (582-608). New slices should
follow that shape and cite it, not restate it.

---

## 9. Keeping this charter honest

- The auditor verifies once per wave that every rule in sections 2 to 6 still
  has a live anchor in the working tree. A rule with a dead anchor is either
  re-anchored in the same wave or withdrawn in the same wave.
- A rule that cannot be checked by re-running a recorded command or re-reading a
  recorded line is not a rule and must be rewritten until it can be.
- Changes to this charter are ordinary commits under the rules in section 6 and
  carry a one-line reason in the commit body.
