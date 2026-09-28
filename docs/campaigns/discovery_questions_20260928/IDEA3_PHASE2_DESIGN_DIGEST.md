# Idea 3 — Phase-2 design digest: collective causal knowledge

**Date:** 2026-09-28  
**Base commit:** `71cbebd` (`71cbebd`), `main`  
**Campaign folder:** `docs/campaigns/discovery_questions_20260928/`  
**Status:** phase-2 design freeze only; not a discovery claim; not authorisation to run  
**Claim ceiling:** `phase2_design`  
**Phase-1 anchor:** [`IDEA3_PHASE1_PROBLEM_BOUNDARY.md`](IDEA3_PHASE1_PROBLEM_BOUNDARY.md)  
**Prior-art support:** [`IDEA3_PHASE2_PRIOR_ART_20260928.md`](IDEA3_PHASE2_PRIOR_ART_20260928.md)

This digest records the sealed phase-2 design for testing whether transmission of reasons, failed interventions, and validity bounds can yield discovery of a pre-registered causal law unreachable by any single lifetime ledger sample, contrasted against lifetime-alone, raw pooling, and success-imitation controls, including a cut test and an error/imitation reversal cell. It fixes no empirical result. No runner, pilot, or campaign is authorised by this file. Empty required identity fields at run time reopen the freeze.

---

## 1. Standing locks

- Engine remains domain-free: no infection physics in `engine.py`.
- No second population engine; no Euler-in-loop; no Avida paths into the engine.
- Sealed campaign seeds `801–816` remain untouched.
- `red_queen_proved` remains false.
- Unit of replication = **run**; series via `GenerationBoundaryObserver`; contact pairs are not N.
- Reject equating raw data pooling, imitation of successful acts, or mere memory sharing with critiqueable cumulative causal knowledge.
- Offline symbolic-regression collectives and multi-model equation-discovery pipelines not embedded in an autonomous evolutionary ecosystem with limited lifetimes remain **deferred** adjacent literature watch only.
- Runners stay off until the owner explicitly allows execution.
- Claim language limited to “not aware of a published precedent for …”; search gap ≠ uniqueness.

---

## 2. Design core (from pre-build rounds)

**Adopted core:** Combo B (failed-intervention / bounds **cut test**) together with Combo A (imitation-error × beyond-lifetime unreachability) and Combo D (critical revision filter × reversal cell).

**Supporting, not sole core:** Combo C (early vs late generation-boundary windows) and Combo E (size/connectivity demography with information-volume matching) as modulators and demography controls.

**Rejected as core claims:** “more individuals help,” “more pooled data helps,” or “shared memory helps” without package-content and cut-test contrast; offline equation-discovery collectives as gap-closing precedent.

**Representation hypotheses (locked for design):**

| ID | Statement |
|---|---|
| **H0** | No cumulative causal advantage beyond pooling: full package does not beat equalised raw pooling on discovery-share. |
| **H1** | Size, pooling, or success-imitation match the full package within margin while beating lifetime-alone. |
| **H2** | Full package (reasons + failed interventions + validity bounds) exceeds lifetime-alone **and** pooling **and** imitation by ≥ 0.15 discovery-share on a law unreachable under lifetime \(L\). |
| **H3** | In the pre-registered reversal cell, full transmission **underperforms** pooling or asocial control by ≥ 0.15 discovery-share. |

H2 requires the cut test (section 3): stripping failed-intervention and bound fields while keeping pooling must remove the H2 margin.

---

## 3. Mandatory one-line operations (ledger only; generation boundary)

All four act as ledger-visible transmission or control events at a generation boundary. None open infection physics in `engine.py`. None substitute genotype bits for package fields.

1. `transmit_package` — transmit a critiqueable causal hypothesis package (stated interventional claim + ≥1 failed intervention + validity bounds + revision rule).
2. `pool_raw_only` — share raw observations or sufficient statistics **without** reasons, failed interventions, or validity bounds (pooling control).
3. `imitate_success_only` — copy successful acts or high-payoff trajectories only; negatives and bounds are not transmitted (imitation control).
4. `cut_failed_and_bounds` — remove failed-intervention and validity-bound fields while retaining raw pooling (Combo B cut test).

Lifetime-alone arms issue none of the transmission ops across individuals or generations within horizon \(L\).

---

## 4. Locked identity fields (non-empty; empty = reopen freeze)

### 4.1 Target law and unreachability

| Field | Locked value |
|---|---|
| **Target law ID** | `LAW-LEDGER-CONTACT-ATP-PARENT-V1` |
| **Law content** | Pre-registered intervenable causal relation on the contact/ATP ledger: which named contact-parent edges control a held-out ATP yield class under the assay protocol. |
| **L-unreachability ID** | `UNREACH-L-SINGLE-LIFETIME-V1` |
| **Unreachability criterion** | Under lifetime horizon \(L\) generation boundaries, no single lineage’s own ledger sample of the size available under \(L\) suffices to pass the held-out interventional assay at the locked accuracy threshold (information / sample-ceiling argument fixed in execution preregistration before any run). |
| **Discovery (per run)** | Population states a hypothesis that passes the held-out interventional assay by horizon \(T\) under the pre-registered accuracy threshold. |
| **Fail condition** | Empty law ID, empty unreachability criterion, or “discovery” claimed from memory sharing without the interventional assay → reopen freeze / invalid. |

### 4.2 Package schema (minimum fields)

| Field | Locked value |
|---|---|
| **Schema ID** | `PKG-REASON-FAIL-BOUND-V1` |
| **Required contents** | (i) interventional claim on allowed `do` set; (ii) ≥1 failed intervention / negative assay; (iii) explicit validity bounds; (iv) revision rule (retain / edit / drop) applicable without domain RNG. |
| **Cost bound** | Transmission and re-test costs ledger-visible on ATP/survival; fixed before any run. |
| **Timing** | Generation-boundary inheritance or teaching events via `GenerationBoundaryObserver`. |

### 4.3 Reversal cell (H3)

| Field | Locked value |
|---|---|
| **Reversal cell ID** | `REV-HIGH-NOISE-BLIND-ACCEPT-V1` |
| **Construction** | Elevated transmission noise, bound stripping, and/or blind-accept (revision rule disabled) as registered in execution preregistration. |
| **Fail condition** | Empty reversal construction if H3 is to be evaluated → reopen freeze. |

---

## 5. Locked thresholds (pre-data)

| Quantity | Lock |
|---|---|
| Primary estimand | **Discovery-share**: share of **runs** that discover `LAW-LEDGER-CONTACT-ATP-PARENT-V1` by horizon \(T\) (held-out interventional assay) |
| H2 support | Full package exceeds lifetime-alone **and** `pool_raw_only` **and** `imitate_success_only` by ≥ **0.15** discovery-share |
| Cut test | `cut_failed_and_bounds` must remove the H2 margin if H2 is claimed |
| H3 support | In `REV-HIGH-NOISE-BLIND-ACCEPT-V1`, full arm underperforms pooling or asocial by ≥ **0.15** discovery-share |
| Minimum replication (when execution later allowed) | ≥ **6** independent **runs** |
| Soft-pass | Forbidden |
| N | Number of independent **runs** |

Post-hoc threshold moves reopen the freeze once sealed.

---

## 6. Explicit falsifiers

1. Full arm indistinguishable from pooling / imitation within 0.15 → favour H0 or H1; no cumulative causal channel claimed.  
2. Advantage survives `cut_failed_and_bounds` while pooling remains → H2 fails the cut test.  
3. Advantage only from larger population size or longer lifetime, not from package transmission → favour H1 (demography).  
4. Reversal cell shows full arm worse by ≥ 0.15 → favour H3 in that regime.  
5. Empty `LAW-LEDGER-CONTACT-ATP-PARENT-V1` or empty `UNREACH-L-SINGLE-LIFETIME-V1` at run time → freeze reopen.  
6. “Discovery” only via domain RNG hacks or infection physics in `engine.py` → design FAIL; discard.  
7. Pass claimed from memory sharing without interventional assay → invalid.  
8. Offline equation-discovery collectives cited as closing this gap → reject (deferred adjacent only).

---

## 7. Gap wording (ceiling)

We are not aware of a published precedent for a pre-registered, run-level contrast in which transmission of reasons + failed interventions + validity bounds yields discovery of a causal law that no single lifetime can establish from its own ledger sample, while cutting that transmission (but retaining raw data pooling or imitation of successes) removes the advantage — including regimes where error transmission or imitation reverses the collective benefit. Absence of a search hit is not proof of uniqueness.

Verified nearest published ingredients (DOIs from the prior-art report only): Gonzalez, Watson & Bullock 2017 `10.1162/artl_a_00244`; Boyd, Richerson & Henrich 2011 `10.1073/pnas.1100290108`; Saral, Ibáñez de Aldecoa & Derex 2026 `10.1093/pnasnexus/pgag090`; Osiurak et al. 2022 `10.1126/sciadv.abl7446`; Osiurak, Claidière & Federico 2023 `10.1016/j.tics.2022.09.024`; Derex et al. 2019 `10.1038/s41562-019-0567-9`; Derex et al. 2025 `10.1098/rspb.2024.2499`; Dean et al. 2012 `10.1126/science.1213969`; Derex, Beugin, Godelle & Raymond 2013 `10.1038/nature12774`; Derex & Boyd 2016 `10.1073/pnas.1518798113`; Morgan & Feldman 2024 `10.1038/s41562-024-02035-y`; Rogers 1988 `10.1525/aa.1988.90.4.02a00030`; Enquist, Eriksson & Ghirlanda 2007 `10.1525/aa.2007.109.4.727`. Offline collectives (e.g. arXiv:2604.27297) remain deferred adjacent.

---

## 8. What this phase does not claim

- Not a discovery, law, or “first” claim.  
- Not authorisation to start runners, pilots, or campaigns.  
- Not a revision of sealed seeds `801–816`.  
- Not an update to phase-9 `vt_spatial_factorial` digests.  
- Not a claim that human cultural-evolution experiments already settle this digital-ecosystem contrast.  
- Adjacent machine collective equation-discovery preprints remain deferred and do not close the gap.  
- `red_queen_proved` stays false.
