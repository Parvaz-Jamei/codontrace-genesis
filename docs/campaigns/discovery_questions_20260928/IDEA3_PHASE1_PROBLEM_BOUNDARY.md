# Idea 3 — Phase-1 problem boundary: collective causal knowledge

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
- **Reject** equating raw data pooling, imitation of successful acts, or mere memory sharing with critiqueable cumulative causal knowledge.
- **Defer** offline symbolic-regression collectives and multi-model equation-discovery pipelines that are not embedded in an autonomous evolutionary ecosystem with limited lifetimes; they are adjacent literature, not results here.

---

## 2. Question

When lineages transmit **reasons**, **failed interventions**, and **validity bounds** (not only successful outcomes or raw observations), can a population discover a pre-registered causal law that no single lifetime has enough ledger data alone to establish — and under what transmission regimes does error propagation or imitation reverse that advantage?

The question is stronger than “more individuals help,” stronger than “more pooled data helps,” and stronger than “shared memory helps.” It asks for a **cumulative, critiqueable, re-testable causal-knowledge channel** under limited lifetimes and resources, contrasted against size, pooling, and imitation controls, with run-level replication and generation-boundary series.

---

## 3. Prior art (verified DOIs)

| Place in argument | Citation | DOI |
|---|---|---|
| Social learning evolves in ALife without rich decision bias | Gonzalez, Watson & Bullock 2017 *Artif. Life* | `10.1162/artl_a_00244` |
| Cultural niche / social learning as adaptation | Boyd, Richerson & Henrich 2011 *PNAS* | `10.1073/pnas.1100290108` |
| Causal reasoning vs cultural transmission in technology chains | Saral, Ibáñez de Aldecoa & Derex 2026 *PNAS Nexus* | `10.1093/pnasnexus/pgag090` |
| Technical reasoning and cumulative technological culture | Osiurak et al. 2022 *Sci. Adv.* | `10.1126/sciadv.abl7446` |
| Copying vs reasoning in cumulative technological culture (review) | Osiurak, Claidière & Federico 2023 *Trends Cogn. Sci.* | `10.1016/j.tics.2022.09.024` |
| Causal understanding not necessary for some cultural improvement | Derex et al. 2019 *Nat. Hum. Behav.* | `10.1038/s41562-019-0567-9` |
| Social/cognitive processes underlying cumulative culture | Dean et al. 2012 *Science* | `10.1126/science.1213969` |
| Group size and cultural complexity | Derex, Beugin, Godelle & Raymond 2013 *Nature* | `10.1038/nature12774` |
| Partial connectivity and cultural accumulation | Derex & Boyd 2016 *PNAS* | `10.1073/pnas.1518798113` |
| Open-ended vs uniquely cumulative culture | Morgan & Feldman 2024 *Nat. Hum. Behav.* | `10.1038/s41562-024-02035-y` |

**Adjacent [PREPRINT], not locked journal precedent:** machine collective equation-discovery pipelines (e.g. arXiv:2604.27297) operate outside an autonomous evolutionary ecosystem with survival, limited lifetimes, and transmission of failed interventions / validity bounds. They are listed only as adjacent literature watch; they do not close this gap.

The published record covers social learning in ALife, human cultural transmission, and roles of causal or technical reasoning in cumulative technology. We are not aware of a published precedent for **critiqueable, re-testable cumulative causal knowledge** — transmitting reasons, failed interventions, and validity bounds across generations in an autonomous evolutionary ecosystem — that finds a law unreachable by any single lifetime, with explicit controls that separate that channel from more individuals, more pooled data, and mere memory sharing, measured at **run** level with generation-boundary series.

---

## 4. Open boundary (gap wording)

We are not aware of a published precedent for a pre-registered, run-level contrast in which transmission of **reasons + failed interventions + validity bounds** yields discovery of a causal law that no single lifetime can establish from its own ledger sample, while cutting that transmission (but retaining raw data pooling or imitation of successes) removes the advantage — including regimes where error transmission or imitation **reverses** the collective benefit.

Absence of a hit in the present search is not proof of uniqueness. The claim ceiling remains `phase1_problem_boundary`.

---

## 5. Competing hypotheses

| ID | Statement |
|---|---|
| **H0** | No cumulative causal advantage beyond pooling data: under the pre-registered cells, transmitting reasons / failed interventions / bounds does not improve law-discovery rate over equalised data pooling; apparent collective gains are noise or demography. |
| **H1** | Imitation or more data enough: increasing population size, pooling raw observations, or imitating successful acts matches the full transmission arm within the locked margin; critiqueable hypothesis packages are unnecessary. |
| **H2** | Cumulative critiqueable hypotheses across generations: transmitting reasons, failed interventions, and validity bounds finds a pre-registered law unreachable by any single lifetime (and by H1 controls) by a locked margin. |
| **H3** | Error / imitation reversal: under a pre-registered high-noise or high-imitation regime, the full transmission arm **underperforms** pooling or asocial controls by the locked margin (collective channel harms). |

H2 is claimed only if the cumulative causal-transmission arm beats lifetime-alone, size-matched pooling, and imitation controls. H3 is claimed only in the pre-registered reversal cell. Mere memory sharing without failed-intervention / bound packages never passes H2.

---

## 6. Operational definitions (mandatory; empty = reopen freeze)

These definitions must be filled in the design digest **before any run**. Leaving a required field empty, or filling it only after seeing data, reopens this freeze.

### 6.1 Critiqueable causal hypothesis package

A **critiqueable causal hypothesis package** is a ledger-visible record that a lineage may transmit, containing at minimum:

1. A stated interventional claim (what contact/ATP ledger variables are candidates for `do`).
2. At least one **failed intervention** or negative assay logged under the same schema.
3. Explicit **validity bounds** (conditions under which the claim is asserted to hold or not).
4. A revision rule (retain / edit / drop) that peers or descendants can apply without opening domain RNG.

Before any run, the design digest must register the schema fields, allowed `do` set, cost bound, and generation-boundary timing. Empty package schema = reopen freeze.

### 6.2 Lifetime-alone baseline

A **lifetime-alone** arm has no inter-individual or inter-generation transmission of hypothesis packages. Each lineage may use only its own ledger sample within one lifetime horizon \(L\).

Before any run, the design digest must register \(L\) in generation-boundary units and that N is still counted in **runs**.

### 6.3 Pooling and imitation controls

- **Pooling control:** raw observations (or sufficient statistics) are shared without reasons, failed interventions, or validity bounds.
- **Imitation control:** only successful acts or high-payoff trajectories are copied; negatives and bounds are not transmitted.

Before any run, the design digest must register how pooling and imitation are constructed on the ledger so that information volume is matched or bounded relative to the full package arm. Empty control construction = reopen freeze.

### 6.4 Target law and discovery criterion

A **target law** is a pre-registered causal relation on the contact/ATP ledger (intervenable, falsifiable) that is **unreachable** from any single lifetime sample of size available under \(L\), under a pre-registered information argument or empirical ceiling registered in the digest.

**Discovery** for a run means the population states a hypothesis that passes a held-out interventional assay by horizon T under the pre-registered accuracy threshold.

Before any run, the design digest must register: law ID, unreachability criterion, assay protocol, horizon T, and that scoring is per **run**. Empty law ID or empty unreachability criterion = reopen freeze.

### 6.5 Reversal cell (error / imitation)

A **reversal cell** is a pre-registered regime with elevated transmission noise, biased imitation, or bound stripping, used to test H3.

Empty reversal construction = reopen freeze if H3 is to be evaluated.

---

## 7. Locked estimand and thresholds (pre-data)

- **Primary estimand:** share of **runs** that discover the target law by horizon T (interventional held-out assay), not contact-pair counts.
- **H0 rejected / H2 support:** full package arm exceeds lifetime-alone **and** pooling **and** imitation controls by ≥ 0.15 discovery-share, over ≥ 6 runs.
- **H1 favoured:** size / pooling / imitation match the full arm within 0.15 while beating lifetime-alone.
- **H3 support:** in the reversal cell, full arm underperforms pooling or asocial control by ≥ 0.15 discovery-share.
- Cut test (pre-registered): removing failed-intervention and bound fields while keeping raw pooling must remove the H2 margin if H2 is claimed.
- \(N\) = runs. Contact pairs are not N. Series via `GenerationBoundaryObserver`.

---

## 8. Falsifiers

| Outcome | Reading |
|---|---|
| Full arm indistinguishable from pooling / imitation within margin | Favour H0 or H1; no cumulative causal channel claimed. |
| Advantage disappears when failed interventions / bounds are stripped but pooling remains | H2 fails the cut test; package content was doing the work — or design incomplete if cut not registered. |
| Advantage only from larger N or longer lifetime, not from package transmission | Favour H1; reframe as demography / sampling. |
| Reversal cell shows full arm worse by ≥ 0.15 | Favour H3 in that regime. |
| “Discovery” only via domain RNG hacks or infection physics in `engine.py` | Design FAIL; result discarded. |
| Pass claimed from memory sharing without interventional assay | Invalid; channel does not pass. |

---

## 9. Mechanism surface (domain-free)

Transmission, critique, and re-test are expressed only as:

- ledger-visible hypothesis packages (reasons, failed interventions, bounds),
- contact / ATP network structure and resource schedule,
- generation-boundary inheritance or teaching events on the ledger,

using the general engine. No infection physics is added to `engine.py`. Generation series are collected through `GenerationBoundaryObserver`.

---

## 10. What this phase does not claim

- Not a discovery, law, or “first” claim.
- Not authorisation to start runners, pilots, or campaigns.
- Not a revision of sealed seeds `801–816`.
- Not a claim that human cultural-evolution experiments already settle this digital-ecosystem contrast.
- Adjacent machine collective equation-discovery preprints remain deferred and do not close the gap.
- `red_queen_proved` stays false.

