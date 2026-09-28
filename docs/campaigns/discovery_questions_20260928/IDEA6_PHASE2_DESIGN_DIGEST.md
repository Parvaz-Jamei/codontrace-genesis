# Idea 6 — Phase-2 design digest: adaptive epistemic restraint

**Date:** 2026-09-28  
**Base commit:** `71cbebd` (`71cbebd`), `main`  
**Campaign folder:** `docs/campaigns/discovery_questions_20260928/`  
**Status:** phase-2 design freeze only; not a discovery claim; not authorisation to run  
**Claim ceiling:** `phase2_design`  
**Phase-1 anchor:** [`IDEA6_PHASE1_PROBLEM_BOUNDARY.md`](IDEA6_PHASE1_PROBLEM_BOUNDARY.md)  
**Prior-art support:** [`IDEA6_PHASE2_PRIOR_ART_20260928.md`](IDEA6_PHASE2_PRIOR_ART_20260928.md)

This digest records the sealed phase-2 design for testing whether evidence-based epistemic restraint — withhold and experiment or consult when evidence is below a locked threshold — can invade and persist as a heritable decision trait when acting on weak hypotheses harms self and neighbours, including a deception × structural-support factorial and a named support-cut collapse. It fixes no empirical result. No runner, pilot, or campaign is authorised by this file. Empty required identity fields at run time reopen the freeze.

---

## 1. Standing locks

- Engine remains domain-free: no infection physics in `engine.py`.
- No second population engine; no Euler-in-loop; no Avida paths into the engine.
- Sealed campaign seeds `801–816` remain untouched.
- `red_queen_proved` remains false.
- Unit of replication = **run**; series via `GenerationBoundaryObserver`; contact pairs are not N.
- **ClaimGate** is an auditor of researcher/software claims only. It is **not** a heritable decision trait of lineages on the ledger and must not be re-labelled as epistemic restraint.
- Reject equating passive non-action, fear-driven freeze, or ClaimGate audit logs with evidence-based restraint.
- Engineered calibration / confidence-threshold software practice remains deferred; it is not an evolutionary invasion result here.
- Runners stay off until the owner explicitly allows execution.
- Claim language limited to “not aware of a published precedent for …”; search gap ≠ uniqueness.

---

## 2. Design core (from pre-build rounds)

**Adopted core:** Combo D (tactical deception vs vigilance vs restraint-with-sanction / support) with Combos A and B as required supporting arms (costly VOI × neighbour-harm × bold rival; social-learning consult channel gated by evidence threshold).

**Not core alone:** Combo C (passive veil / ignorance-as-cooperation) — contrast only; passive veil ≠ active restraint. Combo E (error-management × changing-env learning costs) as optional speed-limit / threshold modulator, not the H2 core.

**Rejected:** ClaimGate-as-trait; freeze/non-action labelled as restraint; vigilance psychology silently re-implemented as researcher-side claim audit inside the lineage loop.

**Representation hypotheses (locked for design):**

| ID | Statement |
|---|---|
| **H0** | Bold action wins every pre-registered cell by the locked margin; restraint does not invade. |
| **H1** | Restraint evolves only as an individual uncertainty heuristic; deception/support cuts do not move lineage survival-share beyond individual payoff noise. |
| **H2** | Restraint clears ≥ 0.15 survival-share in the deception + **support-on** cell **and** loses ≥ 0.15 relative to support-on (or falls below bold) in the **support-cut** cell — named collapse. |

Collapse without the support-cut contrast does not by itself establish H2. Collapse **with** support still on is a different failure mode (do not claim H2 as stated).

---

## 3. Mandatory one-line operations (ledger only; generation boundary)

All four act on the contact/ATP ledger at a generation boundary. None open infection physics in `engine.py`. None read ClaimGate audit logs as lineage state.

1. `withhold_if_u_below` — when evidence strength \(u < u^*\), withhold the harmful action and declare experiment and/or consult before acting.
2. `consult_verified_neighbour` — query a ledger-visible neighbour’s **verified** recent outcome on the support channel (unverified advice is not this op).
3. `bold_act_below_threshold` — act on the best current hypothesis even when \(u < u^*\), paying weak-hypothesis harm when wrong (primary rival arm).
4. `support_cut` — remove or disable registered support channels (verify / re-test / sanction) for the support-cut cell used to test H2 collapse.

Neighbour harm from bold or mistaken action is **ledger-visible** on ATP/survival for self and declared neighbours (section 4.2).

---

## 4. Locked identity fields (non-empty; empty = reopen freeze)

### 4.1 Evidence threshold and restraint rule

| Field | Locked value |
|---|---|
| **Evidence measure ID** | `U-LEDGER-EVIDENCE-STRENGTH-V1` |
| **Definition** | Ledger-visible strength for the candidate action hypothesis (pre-registered sufficient statistic on contact/ATP history). |
| **Threshold \(u^*\)** | `USTAR-RESTRAINT-V1` — numeric threshold locked in execution preregistration before any run; empty \(u^*\) = reopen freeze. |
| **Restraint rule** | If \(u < u^*\), issue `withhold_if_u_below` then allowed experiment and/or `consult_verified_neighbour` before acting. |
| **Fail condition** | ClaimGate logs used as \(u\) or as the restraint trait → design FAIL. Passive freeze with no declared experiment/consult → not restraint. |

### 4.2 Weak-hypothesis harm (self + neighbours)

| Field | Locked value |
|---|---|
| **Neighbour rule ID** | `NBR-CONTACT-KIN-V1` |
| **Who counts** | Declared neighbours by contact/kin rule on the ledger (fixed before any run). |
| **Harm schedule ID** | `HARM-WEAK-HYP-SELF-NBR-V1` |
| **Schedule** | Expected ATP/survival cost to self and to neighbours when acting while \(u < u^*\); **ledger-visible**. Bold and restraint arms face the same realised harm schedule when they act below threshold. |
| **Fail condition** | Neighbour harm only a private payoff rescale that erases externality → Combo A collapses; reopen freeze for H2 lineage claim. |

### 4.3 Deception and structural support

| Field | Locked value |
|---|---|
| **Deception regime ID** | `DEC-MISLEAD-EVIDENCE-V1` |
| **Deception** | Some lineages send misleading evidence, advice, or signals that would induce harmful action under low evidence; bold and restraint face the same realised deception process when compared. |
| **Support channel IDs (support-on)** | `SUP-VERIFY-CONSULT-V1`, `SUP-RETEST-V1`, `SUP-SANCTION-V1` |
| **Support-on cell** | At least one of the above channels available so restraint can verify, re-test, or sanction. |
| **Support-cut cell ID** | `SUPCUT-REMOVE-CHANNELS-V1` |
| **Support-cut** | Registered channels removed via `support_cut`; used for the named H2 collapse / failure mode. |
| **Fail condition** | Empty deception construction or empty support-cut cell → reopen freeze. |

---

## 5. Locked thresholds (pre-data)

| Quantity | Lock |
|---|---|
| Primary estimand | Survival share to horizon \(T\) (**run**-level), including neighbour-harm externalities where registered as lineage payoff |
| Invasion / win | ≥ **0.15** survival-share vs best rival arm in the same cell |
| H2 support | Restraint clears 0.15 in deception + support-on **and** loses ≥ 0.15 vs its support-on share (or falls below bold) in `SUPCUT-REMOVE-CHANNELS-V1` |
| Minimum replication (when execution later allowed) | ≥ **6** independent **runs** |
| Soft-pass | Forbidden |
| N | Number of independent **runs** |

Post-hoc threshold moves reopen the freeze once sealed.

---

## 6. Explicit falsifiers

1. Bold wins all pre-registered cells by ≥ 0.15 → favour H0.  
2. Restraint appears only as individual uncertainty tracking; deception/support cuts do not move lineage estimand beyond noise → favour H1.  
3. Restraint wins with support but does not collapse when support is cut → H2’s coevolution-with-support claim fails.  
4. Restraint collapses under deception **with** support still on → different failure mode; do not claim H2 as stated.  
5. ClaimGate audit behaviour used as the restraint trait → design FAIL; architectural conflation.  
6. Empty \(u^*\) (`USTAR-RESTRAINT-V1`) or empty support channel IDs at run time → freeze reopen.  
7. “Restraint” implemented as freeze/non-action with no experiment/consult → Phase-1 reject; design FAIL.  
8. Advantage only via infection physics in `engine.py` or domain RNG hacks → design FAIL; discard.  
9. Neighbour harm not ledger-visible → design FAIL for the H2 externality claim.

---

## 7. Gap wording (ceiling)

We are not aware of a published precedent for a pre-registered coevolution of evidence-based restraint with deception/cooperation pressure that reports lineage-level survival consequences and an explicit collapse mode when restraint lacks structural support — scored at run level on a contact/ATP ledger, distinct from researcher-side claim auditing. Absence of a search hit is not proof of uniqueness.

Verified nearest published ingredients (DOIs from the prior-art report only): Field & Bonsall 2018 `10.1002/ece3.3627`; Gonzalez, Watson & Bullock 2017 `10.1162/artl_a_00244`; McNamara & Dall 2010 `10.1111/j.1600-0706.2009.17509.x`; Pike, McNamara & Houston 2016 `10.1093/beheco/arw044`; Queller & Strassmann 2013 `10.1098/rsbl.2013.0365`; Arehart & Adler 2023 `10.1098/rspb.2023.1084`; Sperber et al. 2010 `10.1111/j.1468-0017.2010.01394.x`; Heintz, Karabegovic & Molnar 2016 `10.3389/fpsyg.2016.01503`; McNally & Jackson 2013 `10.1098/rspb.2013.0699`; Clark & Kimbrough 2017 `10.1371/journal.pone.0188249`; Tump et al. 2022 `10.1371/journal.pcbi.1010442`.

---

## 8. What this phase does not claim

- Not a discovery, law, or “first” claim.  
- Not authorisation to start runners, pilots, or campaigns.  
- Not a revision of sealed seeds `801–816`.  
- Not an update to phase-9 `vt_spatial_factorial` digests.  
- ClaimGate ≠ epistemic restraint; researcher/software claim audit ≠ lineage decision trait.  
- Passive non-action or fear-driven freeze ≠ evidence-based restraint.  
- Value-of-information or social-learning invasion alone ≠ this H2 assembly.
