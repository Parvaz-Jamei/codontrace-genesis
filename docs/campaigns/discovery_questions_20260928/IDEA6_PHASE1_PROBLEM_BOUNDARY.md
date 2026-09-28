# Idea 6 — Phase-1 problem boundary: adaptive epistemic restraint as an evolvable trait

**Date:** 2026-09-28  
**Base commit:** `f0d1d50c16707223fcf799007c20f95f47ddea2a` (`f0d1d50`), `main`  
**Campaign folder:** `docs/campaigns/discovery_questions_20260928/`  
**Status:** phase-1 problem boundary only; not a discovery claim  
**Claim ceiling:** `phase1_problem_boundary`  
**Track note:** Ambitious-track phase-1 problem boundary (ideas 1, 3, 5, and 6).

This document fixes the scientific question, the nearest published precedent, the open boundary, competing hypotheses, mandatory operational definitions, locked thresholds, falsifiers, and standing locks. It fixes no empirical result. No runner, pilot, or campaign is authorised by this file.

---

## 1. Standing locks

- The life-loop engine remains domain-free: no infection physics in `engine.py`.
- Sealed campaign seeds `801–816` remain untouched (`ABORT / sealed FAIL`).
- `red_queen_proved` remains false (and related proved-claim flags stay closed).
- Runners stay off until the owner explicitly allows execution.
- Unit of replication = **run**. Generation boundaries are observed via `GenerationBoundaryObserver`. Host–antagonist contact pairs are not N.
- **ClaimGate** is an auditor of researcher/software claims only. It is **not** a heritable decision trait of lineages on the ledger, and must not be re-labelled as epistemic restraint in this idea.
- **Reject** equating passive non-action, fear-driven freeze, or ClaimGate audit logs with evidence-based restraint.
- **Defer** engineered calibration / confidence-threshold literature as software practice; it is not an evolutionary invasion result here.

---

## 2. Question

Can adaptive epistemic restraint — the rule “I do not know; experiment or consult before acting” — invade and persist as an evolvable trait when acting on weak hypotheses harms self and neighbours?

When does correct restraint remain selectively stable, and when does it become weakness relative to deceivers or bold exploiters? The potential discovery is a selective boundary among trust, restraint, and re-testing under deception/cooperation pressure, with lineage consequences — including the failure mode that honest restraint collapses without structural support.

The claim ceiling for this phase remains `phase1_problem_boundary`.

---

## 3. Prior art (verified DOIs)

| Place in argument | Citation | DOI |
|---|---|---|
| Ignorance can be evolutionarily beneficial (costly information) | Field & Bonsall 2017 *Ecol. Evol.* | `10.1002/ece3.3627` |
| Social learning transition / ALife | Gonzalez, Watson & Bullock 2017 *Artif. Life* | `10.1162/artl_a_00244` |
| Information as a fitness-enhancing resource | McNamara & Dall 2010 *Oikos* | `10.1111/j.1600-0706.2009.17509.x` |
| Reproductive value of information (general expression) | Pike, McNamara & Houston 2016 *Behav. Ecol.* | `10.1093/beheco/arw044` |
| Veil of ignorance can favour biological cooperation | Queller & Strassmann 2013 *Biol. Lett.* | `10.1098/rsbl.2013.0365` |
| Cost and benefit of learning in changing environments | Arehart & Adler 2023 *Proc. R. Soc. B* | `10.1098/rspb.2023.1084` |

The published record covers adaptive ignorance under collection cost, value-of-information theory, social-learning transitions, and ignorance-as-cooperation constraints. We are not aware of a published precedent for a **pre-registered coevolution** of evidence-based restraint with deception/cooperation pressure that reports lineage-level survival consequences **and** an explicit collapse mode when restraint lacks structural support — scored at run level on a contact/ATP ledger, distinct from researcher-side claim auditing.

---

## 4. Open boundary (gap wording)

We are not aware of a published precedent for a run-level selective map
\(P(\text{restraint persists} \mid u, h, d, s)\)
where \(u\) is uncertainty / evidence strength at decision time, \(h\) is harm to self and neighbours from acting on weak hypotheses, \(d\) is deception pressure, \(s\) is structural support (consult / re-test / sanction channels on the ledger), persistence is lineage survival-share across **runs**, and collapse under deception without \(s\) is a named failure mode rather than an after-the-fact story.

Absence of a hit in the present search is not proof of uniqueness. The claim ceiling remains `phase1_problem_boundary`.

---

## 5. Competing hypotheses

| ID | Statement |
|---|---|
| **H0** | Restraint does not invade; under the pre-registered cost structure, bold action (act on weak hypotheses) is always favoured on the primary estimand. |
| **H1** | Restraint evolves only as an individual uncertainty heuristic: it tracks own evidence strength but does **not** account for population / kin harm, and shows no lineage-level response to deception beyond individual payoff. |
| **H2** | Evidence-based restraint coevolves with deception/cooperation pressure and has lineage consequences (survival-share margin locked below); **falsify H2** if restraint collapses under deception without structural support — name that failure mode (e.g. exploiter invasion when consult/sanction channels are cut). |

H2 is claimed only if restraint clears the locked margin in the deception cell **with** structural support present, and the collapse cell (support cut) shows the pre-registered failure. Collapse without the support-cut contrast does not by itself establish H2.

---

## 6. Operational definitions (mandatory; empty = reopen freeze)

These definitions must be filled in the design digest **before any run**. Leaving a required field empty, or filling it only after seeing data, reopens this freeze.

### 6.1 Epistemic restraint

**Epistemic restraint** is a pre-registered decision rule on the ledger: when evidence strength for a candidate action hypothesis is below a locked threshold, the lineage **withholds** the harmful action and instead issues a declared experiment and/or consult action before acting.

Before any run, the design digest must register:

1. Evidence-strength measure (ledger-visible).
2. Threshold below which restraint triggers.
3. Allowed experiment / consult actions and their costs.
4. That ClaimGate logs are not used as the restraint trait.

Empty threshold or empty experiment/consult set = reopen freeze.

### 6.2 Weak-hypothesis harm

**Weak-hypothesis harm** is a pre-registered expected cost to self and to declared neighbours when an action is taken while evidence is below threshold.

Before any run, the design digest must register:

1. Who counts as neighbour (contact/kin rule on the ledger).
2. Harm schedule (ATP / survival) for self and neighbours.
3. That bold-action arms face the same harm schedule when they act below threshold.

### 6.3 Deception pressure and structural support

- **Deception pressure:** a pre-registered regime in which some lineages send misleading evidence, advice, or signals that would induce harmful action under low evidence.
- **Structural support:** ledger-visible channels that make restraint viable (e.g. consult verification, re-test, sanction, or shared evidence that cannot be silently forged under the digest rules).

Before any run, the design digest must register:

1. How deceptive signals are generated and scored.
2. Which support channels exist in the support-on cell.
3. The support-cut cell used to test the H2 collapse / failure mode.
4. That bold and restraint arms face the same realised deception process when compared.

Empty deception construction or empty support-cut cell = reopen freeze.

### 6.4 Bold-action arm

The **bold-action** arm acts on the best current hypothesis even when evidence is below the restraint threshold, paying weak-hypothesis harm when wrong. It is the primary rival for H0/H1 contrasts.

---

## 7. Locked estimand and thresholds (pre-data)

- **Primary estimand:** survival share to horizon T (run-level), including neighbour-harm externalities where the digest registers them as part of lineage payoff.
- **Invasion / win:** ≥ 0.15 survival-share versus the best rival arm in the same cell, over ≥ 6 runs when execution is later allowed.
- **H2 support:** restraint clears 0.15 in the deception + support-on cell **and** loses at least 0.15 relative to its support-on performance (or falls below bold) in the support-cut cell — the named collapse / failure mode.
- **H1 favoured** if restraint helps only via individual uncertainty tracking and shows no lineage-level differential under deception/support cuts beyond individual payoff noise.
- **H0 favoured** if bold action wins every pre-registered cell by the locked margin.
- \(N\) = runs. Contact pairs are not N. Series via `GenerationBoundaryObserver`.

---

## 8. Falsifiers

| Outcome | Reading |
|---|---|
| Bold wins all pre-registered cells by ≥ 0.15 | Favour H0. |
| Restraint appears only as individual uncertainty heuristic; deception/support cuts do not move lineage estimand beyond noise | Favour H1. |
| Restraint wins with support but does not collapse when support is cut | H2’s coevolution-with-support claim fails (re-specify or favour a weaker reading). |
| Restraint collapses under deception **with** support still on | Different failure mode; do not claim H2 as stated. |
| ClaimGate audit behaviour used as the restraint trait | Design FAIL; architectural conflation. |
| Advantage only via infection physics in `engine.py` or domain RNG hacks | Design FAIL; result discarded. |

---

## 9. Mechanism surface (domain-free)

Restraint, harm, deception, consult, and sanction are expressed only as:

- contact / ATP ledger actions and signals,
- evidence and threshold state on the ledger,
- resource and survival schedules,
- generation-boundary timing via `GenerationBoundaryObserver`,

using the general engine. No infection physics is added to `engine.py`. ClaimGate remains outside the lineage decision loop.

---

## 10. What this phase does not claim

- Not a discovery, law, or “first” claim.
- Not authorisation to start runners, pilots, or campaigns.
- Not a revision of sealed seeds `801–816`.
- ClaimGate ≠ epistemic restraint; researcher/software claim audit ≠ lineage decision trait.
- Passive non-action or fear-driven freeze ≠ evidence-based restraint.
