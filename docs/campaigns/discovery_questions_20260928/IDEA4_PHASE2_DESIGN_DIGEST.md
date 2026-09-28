# Idea 4 — Phase-2 design digest: branching-history recovery window

**Date:** 2026-09-28  
**Base commit:** `4a5ab88` (`4a5ab88`), `main`  
**Campaign folder:** `docs/campaigns/discovery_questions_20260928/`  
**Status:** phase-2 design freeze only; not a discovery claim; not authorisation to run  
**Claim ceiling:** `phase2_design`  
**Phase-1 anchor:** [`IDEA4_PHASE1_PROBLEM_BOUNDARY.md`](IDEA4_PHASE1_PROBLEM_BOUNDARY.md)

This digest records the sealed phase-2 design for representing branching histories from mid-history generation boundaries so that recovery of a pre-registered functional innovation is measurable as  
\(P(\mathrm{recover}\mid \tilde{t},\,\mathrm{ecology},\,\mathrm{knowledge})\).  
It fixes no empirical result. No runner, pilot, or campaign is authorised by this file.

---

## 1. Standing locks

- Engine remains domain-free: no infection physics in `engine.py`.
- No second population engine.
- Sealed campaign seeds `801–816` remain untouched.
- `red_queen_proved` remains false.
- Unit of replication = **run**; series via `GenerationBoundaryObserver`; contact pairs are not N.
- Runners stay off until the owner explicitly allows execution.
- Claim language limited to “not aware of a published precedent for …”; search gap ≠ uniqueness.

---

## 2. Design core (from pre-build rounds)

**Adopted core:** contact-topology ecology (Combo A) plus named-scaffold cut vs degree-matched random cut (Combo E), with conditional ledger knowledge (Combo B).

**Rejected as core:** Combo D (rescue race / survival-only); ecology as ATP/resource schedule alone; knowledge as HGT, genotype bits, or generic cultural transfer.

**Representation hypotheses (locked for design):**

| ID | Statement |
|---|---|
| **R0** | Apparent branches collapse to census / \(N_e\) or resource schedule; “strong” cuts leave a flat recovery curve. |
| **R1** | Degree-preserving contact scramble plus named-scaffold removal suffice; knowledge is zero or redundant. |
| **R2** | Ablatable ledger digests of failed predictions/interventions (no genotype change) steepen the \(\tilde{t}\times\)knowledge interaction. |
| **R3** | Restoring scramble after the same \(\tilde{t}\) does not restore recovery within the locked margin (path hysteresis). |

---

## 3. Mandatory one-line operations (ledger only; generation boundary)

All three act on the contact/ATP ledger at a generation boundary. None mutate genotype. None open infection physics in `engine.py`.

1. `scramble_contacts(degree_preserving)`
2. `cut_named_scaffold` versus `cut_matched_random` (same degree)
3. `ablate_knowledge_digest` (cut failed-prediction / failed-intervention digests without genotype change)

Resource schedules and Combo-D-style rescue controls are **negative controls only**, not core modulators.

---

## 4. Locked identity fields (non-empty; empty = reopen freeze)

### 4.1 Functional innovation

| Field | Locked value |
|---|---|
| **Competence ID** | `FI-RARECLASS-CONTACT-YIELD-V1` |
| **Success rule** | Within horizon \(T\) generation boundaries after the checkpoint intervention, the run recovers a **rare-class contact yield advantage**: mean ATP obtained per generation boundary from contacts tagged `class=rare` is at least **1.25×** the run’s own pre-checkpoint baseline for that class, sustained for **≥3 consecutive** generation boundaries ending at or before \(T\). |
| **Horizon \(T\)** | `T = 40` generation boundaries after checkpoint (inclusive of the first post-checkpoint boundary). |
| **Unit** | Scored **per run**. Contact pairs are not N. |

Fitness raw score, EQU, or Cit+-style proxies are **not** this competence.

### 4.2 Checkpoint event

| Field | Locked value |
|---|---|
| **Checkpoint ID** | `CKPT-REMOVE-PREDFAIL-DIGEST-MID-V1` |
| **Event** | At generation-boundary index \(t\) on the mid-history series, remove the ledger object `digest:pred_fail:FI-RARECLASS-CONTACT-YIELD-V1` (the accumulated failed-prediction / failed-intervention digest tied to this competence) and freeze a multi-seed replay from that boundary. |
| **Not allowed** | Deleting an anonymous random bit string; undocumented mid-run edits. |

### 4.3 Named scaffold (≠ max degree)

| Field | Locked value |
|---|---|
| **Scaffold ID** | `SCAF-CONTACT-SRC-PATH-V1` |
| **Definition** | The pre-registered set of contact **edge IDs** that, in the sealed control history for this competence, carried the **source-path** role for rare-class yield (edges listed in the control digest under `scaffold_edges:SCAF-CONTACT-SRC-PATH-V1`). Membership is by **named edge ID**, not by degree rank. |
| **Fail condition** | If “named scaffold” is operationalised as highest-degree contacts only, Combo E dies and the freeze reopens. |

Control-history edge membership for `SCAF-CONTACT-SRC-PATH-V1` must be written into the execution preregistration before any phase-2 run; this digest locks the **identity and rule**, not an outcome.

---

## 5. Locked thresholds (pre-data)

| Quantity | Lock |
|---|---|
| Window slope magnitude | \(\ge 0.15\) on the pre-registered \(\tilde{t}\) series |
| Ecology/knowledge cut margin | \(\lvert\Delta P\rvert \ge 0.20\) vs matched control at fixed \(\tilde{t}\) |
| \(\tilde{t}\) grid | At least **three** distinct normalised intervention times on the generation-boundary series |
| N | Number of independent **runs** |

Post-hoc threshold moves reopen the freeze.

---

## 6. Explicit falsifiers

1. Ecology cut is only ATP/resource schedule and still claims \(\lvert\Delta P\rvert\ge 0.20\) → soft-novelty FAIL.  
2. Knowledge channel is HGT or genotype bits yet credited as “knowledge” → channel-collapse FAIL.  
3. `cut_matched_random` ≈ `cut_named_scaffold` on recovery → Combo E dies.  
4. Combo D used as the core estimand for \(P(\mathrm{recover})\) → REJECT.  
5. Infection physics or domain RNG opened in `engine.py` → design FAIL; discard.

---

## 7. Gap wording (ceiling)

We are not aware of a published precedent for an explicit mid-history branching-history design that maps  
\(P(\mathrm{recover}\mid \tilde{t},\,\mathrm{ecology},\,\mathrm{knowledge})\)  
for a pre-registered functional innovation with degree-preserving contact scramble, named-scaffold versus degree-matched random cuts, and ablatable failed-prediction digests on a contact/ATP ledger, scored at run level. Absence of a search hit is not proof of uniqueness.

---

## 8. What this phase does not claim

- Not a discovery, law, or “first” claim.  
- Not authorisation to start runners, pilots, or campaigns.  
- Not a revision of sealed seeds `801–816`.  
- Not an update to phase-9 `vt_spatial_factorial` digests.  
