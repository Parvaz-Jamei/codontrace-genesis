# Idea 4 — Phase-1 problem boundary: evolutionary reversibility window

**Date:** 2026-09-28  
**Base commit:** `58241b274b911e45fa1a7ccc8d05f806525359fb` (`58241b2`), `main`  
**Campaign folder:** `docs/campaigns/discovery_questions_20260928/`  
**Status:** phase-1 problem boundary only; not a discovery claim  
**Claim ceiling:** `phase1_problem_boundary`  
**Track note:** Track C is not landed in this record.

This document fixes the scientific question, the nearest published precedent, the open boundary, competing hypotheses, mandatory operational definitions, locked thresholds, falsifiers, and standing locks. It fixes no empirical result. No runner, pilot, or campaign is authorised by this file.

---

## 1. Standing locks

- The life-loop engine remains domain-free: no infection physics in `engine.py`.
- Sealed campaign seeds `801–816` remain untouched (`ABORT / sealed FAIL`).
- `red_queen_proved` remains false (and related proved-claim flags stay closed).
- Runners stay off until the owner explicitly allows execution.
- Unit of replication = **run**. Generation boundaries are observed via `GenerationBoundaryObserver`. Host–antagonist contact pairs are not N.

---

## 2. Question

After a small, pre-registered intervention at a mid-history generation boundary, does the probability of recovering a declared functional innovation by horizon T decline as a closing window of intervention time, and does that window depend on ecological structure and transferable knowledge on the contact/ATP ledger?

The question is stronger than “replay outcomes diverge” and stronger than “a trait can re-evolve after loss.” It asks for a **predictable recovery window** as a function of intervention time plus ecology/knowledge structure, with run-level replication and generation-boundary series.

---

## 3. Prior art (verified DOIs)

| Place in argument | Citation | DOI |
|---|---|---|
| Historical contingency / citrate | Blount et al. 2008 *PNAS* | `10.1073/pnas.0803151105` |
| Digital trait re-evolution after loss | Yedid et al. 2008 *J. Evol. Biol.* | `10.1111/j.1420-9101.2008.01564.x` |
| Replay of evolutionary history (review) | Blount, Lenski & Losos 2018 *Science* | `10.1126/science.aam5979` |
| Contingency and replaying digital evolution | Yedid et al. 2009 *Am. Nat.* | `10.1086/597228` |

**Deferred:** analytical replay preprint Ferguson/Lalejini 2026 — cited only as deferred literature watch; not used as a result claim here.

The published record covers divergent replay outcomes and re-evolution of traits after loss. We are not aware of a published precedent for a closing recovery window for a **functional innovation** as a joint function of (i) normalised intervention time on a generation boundary and (ii) ecological / transferable-knowledge structure, measured with **run-level** replication and generation-boundary series rather than pair counts.

---

## 4. Open boundary (gap wording)

We are not aware of a published precedent for mapping a closing recovery window
\(P(\text{recover} \mid \tilde{t}, \text{ecology}, \text{knowledge})\)
where recovery is of a pre-registered functional innovation, \(\tilde{t}\) is intervention time on the generation boundary, ecology and knowledge are ledger-visible structures, and N is the number of independent runs.

Absence of a hit in the present search is not proof of uniqueness. The claim ceiling remains `phase1_problem_boundary`.

---

## 5. Competing hypotheses

| ID | Statement |
|---|---|
| **H0** | Occupied contingency only: recovery probability does not show a monotone closing window in \(\tilde{t}\); apparent path dependence is not a recoverable-window law. |
| **H1** | Genetic-background window: recovery declines with \(\tilde{t}\) because the genetic background drifts away from states that support the innovation; ecology/knowledge cuts do not move recovery beyond noise once \(\tilde{t}\) is fixed. |
| **H2** | Ecology + knowledge window: at fixed \(\tilde{t}\), scrambling contact structure or cutting transferable knowledge changes recovery probability by a pre-registered margin relative to control. |

---

## 6. Operational definitions (mandatory; empty = reopen freeze)

These definitions must be filled in the design digest **before any run**. Leaving either field empty, or filling them only after seeing data, reopens this freeze.

### 6.1 Functional innovation

A **functional innovation** is a pre-registered behavioural competence on the contact/ATP ledger.

Before any run, the design digest must register, at minimum:

1. A concrete competence ID (example placeholders only — exact ID is fixed in the digest, not here): e.g. recovering a declared rare-class growth advantage, or succeeding at a declared contact-ledger task, within horizon T after the intervention.
2. The measurement rule on the ledger (what counts as success at horizon T).
3. Horizon T in generation-boundary units.
4. That the competence is scored per **run**, not per contact pair.

The exact competence ID is fixed in the design digest before runs. This boundary document only requires that the slot exist and be non-empty before execution.

### 6.2 Intervention event

An **intervention event** is, at a generation-boundary time \(t\), a pre-registered small removal or relocation of a **declared checkpoint event** (not an anonymous random bit flip), followed by multi-seed replay from that boundary.

Before any run, the design digest must register:

1. The checkpoint event identity being removed or relocated.
2. The generation-boundary index \(t\) (or the set of pre-registered \(t\) points).
3. The replay protocol (seed set, what is held fixed, what is re-drawn under the domain-free engine rules).
4. That the intervention is ledger-visible and does not open domain RNG hacks in `engine.py`.

---

## 7. Locked thresholds (pre-data)

- Normalised intervention time: \(\tilde{t} = t_{\mathrm{intervene}} / T_{\mathrm{horizon}}\) on the generation boundary.
- **H0 rejected** if \(P(\mathrm{recover} \mid \tilde{t})\) shows a monotone decline with slope \(\ge 0.15\) per unit \(\tilde{t}\) on \(\ge 3\) pre-registered \(t\) points.
- **H2 support** if, at fixed \(t\), a contact scramble or a knowledge-transfer cut yields \(|\Delta P| \ge 0.20\) versus control; otherwise favour H1 given a declining window.
- \(P(\mathrm{recover})\) = share of **runs** recovering the functional innovation by horizon T after intervention at \(t\).
- \(N\) = runs (\(\ge 6\) cores when execution is allowed). Contact pairs are not N.

---

## 8. Falsifiers

| Outcome | Reading |
|---|---|
| Flat recovery curve in \(\tilde{t}\) | Favour H0; no closing window claimed. |
| Scramble / knowledge cut ineffective at fixed \(t\) while the window declines | Favour H1, not H2. |
| Recovery only via domain RNG hacks or infection physics in `engine.py` | Design FAIL; result discarded. |

Time-shift or cycling signatures alone do not establish a recovery window.

---

## 9. Mechanism surface (domain-free)

Ecology and knowledge are expressed only as:

- contact / ATP network structure on the ledger,
- resource schedule,
- antagonist passage on the ledger,

using the general engine. No infection physics is added to `engine.py`. Generation series are collected through `GenerationBoundaryObserver`.

---

## 10. What this phase does not claim

- Not a discovery, law, or “first” claim.
- Not authorisation to start runners, pilots, or campaigns.
- Not a revision of sealed seeds `801–816`.
- Not Track C (not landed here).
- Deferred Ferguson/Lalejini 2026 analytical replay work remains deferred.

