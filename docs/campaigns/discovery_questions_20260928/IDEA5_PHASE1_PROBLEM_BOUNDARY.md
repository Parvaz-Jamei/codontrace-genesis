# Idea 5 — Phase-1 problem boundary: transferable symbolic laws

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
- **Reject** equating offline symbolic regression on a fixed dataset with evolutionary selection and transfer of falsifiable causal laws across worlds.
- **Reject** scoring transfer by train-world fit alone; held-out worlds with shared causal structure are mandatory for any transfer claim.
- **Defer** pure geometry-prover or offline program-synthesis benchmarks as adjacent methods literature; they are not evolutionary multi-world transfer results here.

---

## 2. Question

In worlds that differ in appearance and history but share a causal structure on the contact/ATP ledger, can a population retain **short, composable, falsifiable rules** that work in unseen worlds — and does survival pressure alone sustain that abstraction, or are memory and social teaching required?

The question is stronger than “a symbolic regressor recovers an equation offline” and stronger than “behaviour transfers within one world.” It asks for **evolutionary selection and transmission of transferable symbolic causal laws**, plus an explicit boundary where an apparently true law is only a **simulator shortcut** (private features that do not travel with the shared causal structure), measured at run level with generation-boundary series.

---

## 3. Prior art (verified DOIs)

| Place in argument | Citation | DOI |
|---|---|---|
| Physics-inspired symbolic regression from data | Udrescu & Tegmark 2020 *Sci. Adv.* | `10.1126/sciadv.aay2631` |
| Sparse identification of nonlinear dynamics (SINDy) | Brunton, Proctor & Kutz 2016 *PNAS* | `10.1073/pnas.1517384113` |
| Distilling free-form natural laws from experimental data | Schmidt & Lipson 2009 *Science* | `10.1126/science.1165893` |
| Data-driven discovery of PDEs | Rudy, Brunton, Proctor & Kutz 2017 *Sci. Adv.* | `10.1126/sciadv.1602614` |
| Geometry theorem proving without human demonstrations | Trinh et al. 2024 *Nature* | `10.1038/s41586-023-06747-5` |

**Adjacent [PREPRINT], not locked journal precedent:** DreamCoder (arXiv:2006.08381) and related wake–sleep program synthesis — relevant as compositional symbolic learning methods, but not as evolutionary selection + population transfer of falsifiable causal laws across held-out worlds under survival pressure.

The published record covers offline symbolic regression, sparse equation discovery, and neural–symbolic theorem proving. We are not aware of a published precedent for **evolutionary selection and inter-generation transfer of short, composable, falsifiable causal laws** that succeed on held-out worlds sharing causal structure while failing a pre-registered simulator-shortcut probe — with explicit contrasts of survival-only versus memory / social-teaching arms, run-level replication, and generation-boundary series.

---

## 4. Open boundary (gap wording)

We are not aware of a published precedent for a pre-registered multi-world protocol in which a population under survival pressure retains short composable causal rules that transfer to held-out worlds with shared structure, where transfer is scored by interventional accuracy (not train-world fit), where survival-only is contrasted with memory / social teaching, and where a simulator-shortcut probe shows when an apparently true rule depends on engine-private features rather than the shared causal structure.

Absence of a hit in the present search is not proof of uniqueness. The claim ceiling remains `phase1_problem_boundary`.

---

## 5. Competing hypotheses

| ID | Statement |
|---|---|
| **H0** | No transferable short law: under the pre-registered world family, no arm retains a short composable rule that clears the locked interventional accuracy on held-out worlds; apparent laws are noise or non-transferable. |
| **H1** | World-specific heuristics only: lineages adapt within each training world, but retained rules fail held-out transfer by the locked margin; any within-world success is local policy, not a shared-structure law. |
| **H2** | Short composable laws transfer: under survival pressure plus the registered memory / teaching condition, the population retains rules that meet pre-registered interventional accuracy on held-out worlds sharing causal structure, and pass the simulator-shortcut probe (fail when only private features remain). |
| **H3** | Survival alone insufficient: H2-level transfer appears only when memory and/or social teaching are enabled; the survival-only arm stays at H0/H1. |

H2 is claimed only if transfer clears the locked margin on held-out worlds **and** the shortcut probe shows dependence on shared structure. H3 is claimed only if survival-only fails while memory/teaching succeeds under otherwise matched conditions.

---

## 6. Operational definitions (mandatory; empty = reopen freeze)

These definitions must be filled in the design digest **before any run**. Leaving a required field empty, or filling it only after seeing data, reopens this freeze.

### 6.1 World family (shared structure, different appearance)

A **world family** is a pre-registered set of environments that:

1. Share a declared causal skeleton on the contact/ATP ledger (same interventional relations among named variables).
2. Differ in appearance / history (surface statistics, resource schedules, or trajectory draws) under domain-free engine rules.
3. Include a held-out subset never used for selection or teaching during training generations.

Before any run, the design digest must register the shared skeleton, the appearance axes, the train/held-out split, and that worlds are ledger-visible. Empty skeleton or empty held-out split = reopen freeze.

### 6.2 Short composable symbolic law

A **short composable symbolic law** is a falsifiable rule over ledger variables that:

1. Has a pre-registered maximum length / complexity bound.
2. Is composable (may be combined with other retained rules under a declared algebra).
3. Issues or constrains low-cost `do` predictions without opening domain RNG.
4. Is stored in a form that can be inherited or taught across generation boundaries.

Before any run, the design digest must register complexity bound, composition rules, and the interventional assay used to score the law. Empty complexity bound or empty assay = reopen freeze.

### 6.3 Survival-only vs memory / social teaching

- **Survival-only arm:** selection on reproductive / energetic success; no explicit law memory beyond genotype effects registered in the digest; no teaching events.
- **Memory arm:** individuals retain law candidates across their lifetime on the ledger.
- **Social-teaching arm:** law candidates (and optionally failed tests / bounds) may be transmitted at generation boundaries.

Before any run, the design digest must register which channels are on/off per cell. Empty arm definition = reopen freeze.

### 6.4 Simulator-shortcut probe

A **simulator-shortcut probe** is a pre-registered held-out variant that preserves surface cues or engine-private correlates while **breaking** or **relocating** the shared causal skeleton (or the reverse: preserves the skeleton while scrambling private correlates).

A candidate law **fails** the probe if it succeeds only when private correlates are present and fails when only the shared skeleton remains (or vice versa, as registered).

Before any run, the design digest must register the probe construction. Empty probe = reopen freeze.

### 6.5 Transfer success

**Transfer success** for a run means the retained law set meets interventional accuracy ≥ θ on the held-out world subset by horizon T, and passes the simulator-shortcut probe under the digest rule.

θ, T, and scoring-per-**run** must be registered before any run.

---

## 7. Locked estimand and thresholds (pre-data)

- **Primary estimand:** share of **runs** achieving transfer success (held-out interventional accuracy ≥ θ and shortcut-probe pass) by horizon T.
- **θ (pre-data):** ≥ 0.80 interventional accuracy on held-out worlds (exact assay in digest); train-world fit alone never counts.
- **H0:** no arm clears transfer success share ≥ 0.15 above chance / null baseline over ≥ 6 runs.
- **H1:** within-world success without held-out transfer (held-out accuracy drop ≥ 0.20 relative to train world).
- **H2 support:** transfer success share ≥ 0.15 above best non-transfer control, with shortcut-probe pass rate ≥ 0.80 among successful runs.
- **H3 support:** memory and/or teaching arms clear H2 margin; survival-only does not.
- \(N\) = runs. Contact pairs are not N. Series via `GenerationBoundaryObserver`.

---

## 8. Falsifiers

| Outcome | Reading |
|---|---|
| No arm clears held-out interventional threshold | Favour H0. |
| Within-world fit high; held-out fails by ≥ 0.20 | Favour H1. |
| Held-out success but shortcut probe fails (private features only) | Not H2; treat as simulator shortcut; discard as transfer law. |
| Survival-only matches memory/teaching on transfer | H3 fails; survival may suffice under that cell. |
| Advantage only via infection physics in `engine.py` or domain RNG hacks | Design FAIL. |
| Pass claimed from offline symbolic regression without evolutionary multi-world protocol | Invalid for this question. |

---

## 9. Mechanism surface (domain-free)

Worlds, laws, memory, and teaching are expressed only as:

- contact / ATP ledger variables and resource schedules,
- generation-boundary retention or teaching of short symbolic candidates,
- held-out world swaps and shortcut probes on the ledger,

using the general engine. No infection physics is added to `engine.py`. Generation series are collected through `GenerationBoundaryObserver`.

---

## 10. What this phase does not claim

- Not a discovery, law, or “first” claim.
- Not authorisation to start runners, pilots, or campaigns.
- Not a revision of sealed seeds `801–816`.
- Not a claim that offline symbolic regression or theorem-proving systems already settle evolutionary multi-world transfer.
- DreamCoder and related synthesis preprints remain deferred method literature.
- `red_queen_proved` stays false.

