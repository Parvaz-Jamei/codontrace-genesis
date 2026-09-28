# Idea 1 — Phase-2 design digest: costly causal experimentation vs reactive learning

**Date:** 2026-09-28  
**Base commit:** `71cbebd` (`71cbebd`), `main`  
**Campaign folder:** `docs/campaigns/discovery_questions_20260928/`  
**Status:** phase-2 design freeze only; not a discovery claim; not authorisation to run  
**Claim ceiling:** `phase2_design`  
**Phase-1 anchor:** [`IDEA1_PHASE1_PROBLEM_BOUNDARY.md`](IDEA1_PHASE1_PROBLEM_BOUNDARY.md)  
**Prior-art support:** [`IDEA1_PHASE2_PRIOR_ART_20260928.md`](IDEA1_PHASE2_PRIOR_ART_20260928.md)  
**hypothesis_supported:** `false` (pre-data; no outcome claimed)

This digest records the sealed phase-2 design for mapping when lineages pay survival-cost interventions whose selective value is discrimination of rival world-explanations, versus reactive ledger update and reward-oriented exploration, under cost, lifespan, and world-change on the contact/ATP ledger. It fixes no empirical result. No runner, pilot, or campaign is authorised by this file. Empty required identity fields at run time reopen the freeze.

---

## 1. Standing locks

- Engine remains domain-free: no infection physics in `engine.py`.
- No second population engine; no Euler-in-loop; no Avida paths into the engine.
- Sealed campaign seeds `801–816` remain untouched.
- `red_queen_proved` remains false.
- Unit of replication = **run**; series via `GenerationBoundaryObserver`; contact pairs are not N.
- Reject equating reward-seeking exploration or reactive memory update with rival-hypothesis discrimination.
- EvoSCM (arXiv:2609.01526) remains **deferred** preprint watch only — not a locked journal precedent, not Combo-D core, not a result claim.
- Runners stay off until the owner explicitly allows execution.
- Claim language limited to “not aware of a published precedent for …”; search gap ≠ uniqueness.
- `hypothesis_supported` stays `false` until a later authorised phase raises it under locked falsifiers.

---

## 2. Design core (from pre-build rounds)

**Adopted core:** Combo A (restless learning-cost schedule + locked rival-discrimination assay) plus Combo B (lifespan × world-change gate), with Combo E (Pontes-style associative / reactive module) as the explicit **H1 control**.

**Not core without a discrimination gate:** Combo C (evolvable curiosity / novelty propensity). Curiosity spend that is not gated by a non-empty rival-discrimination schema never counts as causal experimentation.

**Deferred (not core):** Combo D (EvoSCM-style disagreement-maximising `do`). Preprint watch only; do not treat EvoSCM metrics as locked precedent.

**Representation hypotheses (locked for design):**

| ID | Statement |
|---|---|
| **H0** | Costly discrimination interventions do not invade under the pre-registered \((c, L, \rho)\) cells; report a named selective barrier. |
| **H1** | Reactive update and/or reward exploration (including associative cue→action) match or beat the discrimination arm; no selective need for rival-hypothesis tests. |
| **H2** | The discrimination arm clears ≥ 0.15 survival-share vs the best rival **and** passes the discrimination assay in a pre-registered mid band of \((c, L, \rho)\). |

Advantage without assay pass fails H2 and is read as H1 (or design FAIL if the assay was empty).

---

## 3. Mandatory one-line operations (ledger only; generation boundary)

All three act on the contact/ATP ledger at a generation boundary. None mutate genotype as a silent discrimination substitute. None open infection physics in `engine.py`. Each arm receives a shared per-boundary decision budget of **1.0** (unused units do not bank).

1. `do_rival_discriminate` — issue a pre-registered intervention from the allowed `do` set whose outcome distribution separates the locked rival pair (section 4.1); debit real ATP/survival cost \(c\).
2. `update_reactive_ledger` — update from observed contact/ATP outcomes **without** issuing a discrimination intervention (reactive / associative H1 arm).
3. `reward_explore_ε` — explore actions to improve short-horizon ATP under an ε-style schedule **without** a locked rival-explanation contrast (reward-exploration H1 arm).

Arms using `update_reactive_ledger` or `reward_explore_ε` are **forbidden** from silently calling `do_rival_discriminate`. Empty discrimination schema at run time = reopen freeze.

---

## 4. Locked identity fields (non-empty; empty = reopen freeze)

### 4.1 Rival explanation pair

| Field | Locked value |
|---|---|
| **Rival-pair ID** | `RP-LEDGER-ATP-DRAIN-V1` |
| **Explanation R1** | ATP drain on tagged contacts is mediated by a **contact-parent** ledger edge (intervenable parent). |
| **Explanation R2** | ATP drain on the same tagged contacts is mediated by a **resource-schedule** process independent of that contact parent. |
| **Distinct predictions** | After `do_rival_discriminate` on the registered parent edge, R1 and R2 make different predictions on next-boundary ATP observables for the tagged contacts. |
| **Fail condition** | If reward gain alone can satisfy the discrimination scorer without separating R1 from R2 → assay FAIL; freeze reopens. |

Execution preregistration may refine observable names under this ID but may not empty the pair or collapse R1 into R2.

### 4.2 Cost, lifespan, change-rate, inheritance

| Field | Locked value |
|---|---|
| **Cost schedule \(c\)** | Ledger-visible ATP/survival debit per `do_rival_discriminate`; not a cosmetic counter. Mid-cell nominal cost locked in execution preregistration before any run. |
| **Lifespan \(L\)** | Horizon in **generation-boundary** units (Combo B grid includes short / mid / long \(L\)). |
| **World-change rate \(\rho\)** | Turnover rate of rival-relevant ledger structure across generation boundaries (Combo B grid). |
| **Inheritance** | Experimentation propensity (use of `do_rival_discriminate`) is heritable / persistent across generation boundaries under a rule fixed in execution preregistration. |
| **Decision budget** | **1.0** unit per generation boundary per arm. |

### 4.3 Discrimination scoring rule

A trial **discriminates** only if the post-intervention update selects R1 over R2 (or R2 over R1) under the locked scoring rule for `RP-LEDGER-ATP-DRAIN-V1`. Survival advantage without this pass does **not** support H2.

---

## 5. Locked thresholds (pre-data)

| Quantity | Lock |
|---|---|
| Primary estimand | Survival share to horizon \(T\) (**run**-level), not Δ growth of contact pairs |
| Invasion / win margin | ≥ **0.15** survival-share vs best rival arm in the same \((c, L, \rho)\) cell |
| Minimum replication (when execution later allowed) | ≥ **6** independent **runs** |
| Combo B grid | At least one pre-registered mid band where H2 is reachable, plus cells that name H0 barriers (too short \(L\); too fast \(\rho\); stable world → H1) |
| Soft-pass | Forbidden (including “near 0.15”) |
| N | Number of independent **runs** |
| `hypothesis_supported` | `false` |

Post-hoc threshold moves reopen the freeze once sealed.

---

## 6. Explicit falsifiers

1. No discrimination arm clears 0.15 in any pre-registered cell → favour H0; report named barrier in \(c\) / \(L\) / \(\rho\).  
2. `update_reactive_ledger` or `reward_explore_ε` (or associative cue→action) matches or beats discrimination without assay pass → favour H1.  
3. Survival advantage without measurable rival discrimination → H2 fails; do not claim causal experimentation.  
4. Combo C curiosity spend wins while failing the discrimination assay → not causal experimentation (H1).  
5. Combo D / EvoSCM treated as locked journal precedent or core estimand → design FAIL (deferred only).  
6. Empty rival-pair ID or empty distinct predictions at run time → freeze reopen; results invalid.  
7. Advantage only via infection physics in `engine.py` or domain RNG hacks → design FAIL; discard.  
8. Cost \(c\) cosmetic (not survival/ATP-coupled) → design FAIL.

---

## 7. Gap wording (ceiling)

We are not aware of a published precedent for a pre-registered evolutionary invasion regime in which lineages pay survival-cost interventions whose selective value is measured by discrimination of rival world-explanations (not by reward gain alone), with run-level survival-share replication, explicit reactive and reward-exploration rival arms, and an honest non-emergence outcome when a named selective barrier (cost / lifespan / change-rate) holds. Absence of a search hit is not proof of uniqueness.

Verified nearest published ingredients (DOIs from the prior-art report only): Giannakakis et al. 2024 `10.1162/artl_a_00458`; Arehart & Adler 2023 `10.1098/rspb.2023.1084`; Kozielska & Weissing 2024 `10.1371/journal.pcbi.1011840`; Zhang et al. 2023 `10.1038/s42256-023-00719-0`; Zemplenyi & Miller 2023 `10.1214/22-ba1335`; Turner et al. 2024 `10.1098/rspb.2024.1524`; Pontes et al. 2020 `10.1086/706252`; Eliassen et al. 2007 `10.1111/j.2006.0030-1299.15462.x`. EvoSCM arXiv:2609.01526 remains deferred preprint watch.

---

## 8. What this phase does not claim

- Not a discovery, law, or “first” claim.  
- Not authorisation to start runners, pilots, or campaigns.  
- Not a revision of sealed seeds `801–816`.  
- Not an update to phase-9 `vt_spatial_factorial` digests.  
- Not support for H0/H1/H2 (`hypothesis_supported=false`).  
- Reward exploration ≠ rival-hypothesis discrimination; reactive learning ≠ causal experimentation.  
- EvoSCM remains deferred preprint watch only.
