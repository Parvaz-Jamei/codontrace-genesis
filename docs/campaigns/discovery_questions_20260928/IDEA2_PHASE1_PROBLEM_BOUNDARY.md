# Idea 2 — Phase-1 problem boundary: causality under coevolving antagonist pressure

**Date:** 2026-09-28  
**Base commit:** `58241b274b911e45fa1a7ccc8d05f806525359fb` (`58241b2`), `main`  
**Campaign folder:** `docs/campaigns/discovery_questions_20260928/`  
**Status:** phase-1 problem boundary only; not a discovery claim  
**Claim ceiling:** `phase1_problem_boundary`  
**Track note:** Track C is not landed in this record.

This document fixes the scientific question, the nearest published precedent, the open boundary, competing hypotheses G0–G3, mandatory operational definitions for the causal and pattern-deception arms, locked estimands, falsifiers, and standing locks. It fixes no empirical result. No runner, pilot, or campaign is authorised by this file.

---

## 1. Standing locks

- The life-loop engine remains domain-free: no infection physics in `engine.py`.
- Sealed campaign seeds `801–816` remain untouched (`ABORT / sealed FAIL`).
- `red_queen_proved` remains false (and related proved-claim flags stay closed).
- Runners stay off until the owner explicitly allows execution.
- Unit of replication = **run**. Generation boundaries are observed via `GenerationBoundaryObserver`. Host–antagonist contact pairs are not N.
- **Reject** equating time-shift assays with causal knowledge.
- **Reject** infection physics in `engine.py`.
- **Defer** CausalEvolve / ECR-Net comparisons to later literature watch; they are not results here.

---

## 2. Question

Under coevolving antagonist pressure on the contact/ATP ledger, is there a falsifiable temporal or ecological regime that separates (i) revisable interventional causal hypotheses, (ii) genetic adaptation alone, and (iii) correlational pattern memory — including regimes where **none** of these channels help in time?

The question is not Red Queen cycling, sex-advantage, or time-shift signature alone.

---

## 3. Prior art (verified DOIs)

| Place in argument | Citation | DOI |
|---|---|---|
| Host–parasite coevolution / digital networks | Zaman et al. 2014 *PLOS Biology* | `10.1371/journal.pbio.1002023` |
| Digital coevolution / ALife | Luo & Ofria 2020 *Artif. Life* | `10.1162/artl_a_00305` |
| Pathogen evolution / inference limits | Barrat-Charlaix & Neher 2024 *eLife* | `10.7554/elife.97350` |
| Time-shift / coevolution assays (review context) | Gaba & Ebert 2009 *Trends Ecol. Evol.* | `10.1016/j.tree.2008.11.005` |
| Cyclic causation / Pearl-style framing | Watson et al. | `10.1007/s10539-020-09753-3` |
| Polymorphism ≠ Red Queen dynamics | Ashby 2020 *J. Evol. Biol.* | `10.1111/jeb.13718` |

The published record includes gene-level coevolution, time-shift assays, and ecological or immune-like memory. We are not aware of a published precedent for a **falsifiable temporal/ecological regime map** that separates revisable interventional causal hypotheses from genetic adaptation and correlational pattern memory under coevolving antagonist pressure — including cells where no channel reaches a pre-registered survival margin in time.

---

## 4. Open boundary (gap wording)

We are not aware of a published precedent for a pre-registered, run-level contrast among gene, pattern, and causal channels on a contact/ATP ledger, with a pattern-deception cell that deliberately places predicted correlations antiphase to realised pressure, and with an explicit “none help in time” outcome (G3). Time-shift or cycling alone never passes a channel.

Absence of a hit in the present search is not proof of uniqueness. The claim ceiling remains `phase1_problem_boundary`.

---

## 5. Competing hypotheses (G0–G3)

| ID | Statement |
|---|---|
| **G0** | No channel separation: under the pre-registered cells, gene, pattern, and causal arms are indistinguishable on the primary estimand; apparent advantages are noise or demography. |
| **G1** | Gene channel sufficient: genotype evolution alone wins the cell (≥ 0.15 survival-share over best rival); memory and interventional `do` are unnecessary. |
| **G2** | Causal channel required under deception: the causal arm beats **both** gene and pattern in the pattern-deception cell by the locked margin. |
| **G3** | None help in time: under high antagonist pressure, **no** channel reaches a ≥ 0.15 survival-share advantage over the best rival in that cell. |

G2 is claimed only if the causal arm beats both rivals in the deception cell. G3 is claimed only if no channel clears the margin under high pressure. Time-shift or cycling signatures alone never pass a channel.

---

## 6. Operational definitions (mandatory; empty = reopen freeze)

These definitions must be filled in the design digest **before any run**. Leaving a required field empty, or filling it only after seeing data, reopens this freeze.

### 6.1 Gene arm

- Genotype evolution only.
- Predictive memory off.
- Interventional `do` off.

### 6.2 Pattern arm

- Correlational predictive memory of realised pressure patterns.
- No interventional `do`.
- Memory may be correct or, in the deception cell, deliberately mismatched (see 6.4).

### 6.3 Causal arm — revisable interventional hypothesis

A **causal hypothesis** here is a pre-registered, revisable account that may issue a **low-cost `do` on the contact/ATP ledger** without opening domain RNG and without adding infection physics to `engine.py`.

Before any run, the design digest must register:

1. The hypothesis schema (what variables on the ledger are candidates for intervention).
2. The allowed `do` set (which contact/ATP ledger actions are legal, cost bound, and generation-boundary timing).
3. The revision rule (when a hypothesis is retained, edited, or dropped).
4. That `do` never opens domain RNG hacks in `engine.py`.

Empty `do` specification = reopen freeze. Equating a time-shift readout with this causal arm is rejected.

### 6.4 Pattern-deception cell

A **pattern-deception cell** is a pre-registered regime in which the correlational predictions available to the pattern arm are **deliberately antiphase** to realised antagonist pressure on the ledger (predicted high-pressure phases align with realised low-pressure phases, and vice versa).

Before any run, the design digest must register:

1. How antiphase is constructed (ledger-visible rule).
2. That gene and causal arms face the same realised pressure process.
3. That G2 is evaluated in this cell: causal must beat both gene and pattern.

Empty deception construction = reopen freeze.

---

## 7. Locked estimand and thresholds (pre-data)

- **Primary estimand:** survival share to horizon T only (not Δ growth).
- **Channel win:** ≥ 0.15 survival-share versus the best rival in the same cell, over ≥ 6 runs.
- **G2:** only if causal beats both gene and pattern in the pattern-deception cell by that margin.
- **G3:** if no channel reaches 0.15 under high antagonist pressure.
- \(N\) = runs. Contact pairs are not N. Series are taken at generation boundaries via `GenerationBoundaryObserver`.

---

## 8. Falsifiers

| Outcome | Reading |
|---|---|
| No arm clears 0.15 in any pre-registered cell | Favour G0 (or report underpowered / design FAIL if protocol broken). |
| Gene wins; causal and pattern do not clear margin | Favour G1. |
| Causal fails to beat both rivals in the deception cell | G2 fails. |
| No channel clears 0.15 under high pressure | Favour G3. |
| Pass claimed from time-shift or cycling alone | Invalid; channel does not pass. |
| Advantage only via infection physics in `engine.py` or domain RNG hacks | Design FAIL. |

---

## 9. Mechanism surface (domain-free)

Antagonist pressure, contact, and ATP effects remain on the ledger and in thin domain modules outside `engine.py`. The engine stays domain-free. No infection physics is landed in `engine.py` by this boundary.

---

## 10. What this phase does not claim

- Not a discovery, law, or “first” claim.
- Not authorisation to start runners, pilots, or campaigns.
- Not a revision of sealed seeds `801–816`.
- Not Track C (not landed here).
- CausalEvolve / ECR-Net remain deferred.
- Time-shift ≠ causal knowledge; polymorphism ≠ Red Queen proved (`red_queen_proved` stays false).

