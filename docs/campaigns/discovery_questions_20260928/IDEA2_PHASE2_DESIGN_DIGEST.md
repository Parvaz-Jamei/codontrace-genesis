# Idea 2 — Phase-2 design digest: gene / pattern / causal competition under coevolving antagonist pressure

**Date:** 2026-09-28  
**Base commit:** `1f77d5c` (`1f77d5c`), `main` (distinction patch on this tip)  
**Campaign folder:** `docs/campaigns/discovery_questions_20260928/`  
**Status:** phase-2 design freeze only; not a discovery claim; not authorisation to run  
**Claim ceiling:** `phase2_design`  
**Phase-1 anchor:** [`IDEA2_PHASE1_PROBLEM_BOUNDARY.md`](IDEA2_PHASE1_PROBLEM_BOUNDARY.md)

This digest records the sealed phase-2 design for contrasting genetic adaptation, correlational pattern memory, and revisable interventional causal hypotheses under coevolving antagonist pressure on the contact/ATP ledger, including a pattern-deception cell and an explicit none-help-in-time outcome. It fixes no empirical result. No runner, pilot, or campaign is authorised by this file.

---

## 1. Standing locks

- Engine remains domain-free: no infection physics in `engine.py`.
- Match-allele, virulence, steal, and infection live only in thin domain/ledger modules — never as engine physics.
- Sealed campaign seeds `801–816` remain untouched.
- `red_queen_proved` remains false.
- Unit of replication = **run**; series via `GenerationBoundaryObserver`; contact pairs are not N.
- Time-shift assays and Red Queen cycling are **background / assay context only**; they never pass a channel.
- Runners stay off until the owner explicitly allows execution.
- Claim language limited to “not aware of a published precedent for …”; search gap ≠ uniqueness.

---

## 2. Design core (from pre-build rounds)

**Adopted core:** Combo C — mandatory `do` ablation as the channel discriminator — with conditional A/D (pattern must be ledger-visible and ablatable without genotype change; FRQ/ERQ regimes only with pre-registered antiphase deception).

**Rejected / deferred:** Combo B as half-dead priming without confounding break; Combo E as statistical detector soft-novelty unless contact/ATP policy changes via explicit `do`; any causal advantage that requires infection physics in `engine.py`.

**Mechanism hypotheses (locked for design):**

| ID | Statement |
|---|---|
| **M0** | Arms are not separable; “causal” is only better pattern memory — `do` ablation leaves survival-to-\(T\) unchanged. |
| **M1** | Gene + pattern suffice; `do` is dead budget — under antiphase deception, pattern or gene wins by \(\ge 0.15\), causal does not. |
| **M2** | Causal wins the deception cell by \(\ge 0.15\) only when `do` targets ledger parents of pressure; cue-parent targeting FAIL → M0. |
| **M3** | Revision + `do` clock fails relative to antagonist period — G3 holds even with a correct schema. |

Phase-1 G0–G3 remain the outcome map; M0–M3 are the phase-2 mechanism competitors.

---

## 3. Mandatory one-line `do` list (generation boundary; outside `engine.py`)

1. `mask_named_contacts(one_generation)`
2. `reallocate_contact_budget(class_blind, zero_sum, one_generation)`
3. `cut_or_restore_named_contact_edge` with matched control `matched_random_edge`

**Allowed surface:** contact opportunity, contact ATP budget, and named contact edges on the ledger at a generation boundary.  
**Forbidden:** opening domain RNG or infection physics inside `engine.py`; `do` that only retargets a correlated cue rather than a pressure parent.

---

## 4. Locked identity fields — named contacts (non-empty; empty = reopen freeze)

`named_contact` means a **ledger edge identity**, never a genotype class and never a correlated cue label.

| Field | Locked value |
|---|---|
| **Edge-ID set** | `NC-H0-A0`, `NC-H0-A1`, `NC-H1-A0`, `NC-H1-A1`, `NC-H2-A0`, `NC-H2-A1` |
| **Meaning** | Six pre-registered host–antagonist contact edges on the contact ledger (`H*` = host slot, `A*` = antagonist slot). Mask, cut, and restore operations in section 3 address members of this set by **edge ID**. |
| **Fail condition** | If `mask_named_contacts` is implemented as masking a genotype class rather than these edge IDs → class-shortcut FAIL; freeze reopens. |

Execution preregistration may subset which of these six edges are active in a given cell, but may not replace edge IDs with genotype-class masks.

---

## 5. Shared decision budget and \(\kappa\)

| Field | Lock |
|---|---|
| **Per-boundary budget** | Each arm receives exactly **1.0** decision unit per generation boundary; unused units do not bank. |
| **Gene arm spend** | `1.0` → one genotype-update opportunity. |
| **Pattern arm spend** | `1.0` → one correlational-memory update. |
| **Causal arm spend** | `0.5` hypothesis revision + `0.5` one allowed `do`. |
| **\(\kappa\)** | Common map from decision units to ATP debit. **\(\kappa\) is locked before each execution** and is **not** chosen from outcomes. This design freeze does not invent a numerical \(\kappa\); empty \(\kappa\) at run time reopens execution preregistration, not this design freeze. |

Absolute ATP costs are not free parameters invented per arm; environment-dependent cost structure is acknowledged (Arehart lineage), hence the shared unit + \(\kappa\) rule.

---

## 6. Pattern-deception cell (ledger-visible)

| Field | Lock |
|---|---|
| **Phase offset** | Predicted cue is exactly **half a period (\(\pi\))** out of phase with realised antagonist pressure. |
| **Shared pressure** | All three arms face the **same** realised pressure process; only the causal arm may issue `do`. |
| **Required controls** | (i) `do` ablation; (ii) cue-parent sham `SHAM-CUE-PREDPHASE-V1`. |

### 6.1 Locked sham identity (distinct from named contacts)

| Field | Locked value |
|---|---|
| **Sham ID** | `SHAM-CUE-PREDPHASE-V1` |
| **Target** | The ledger field for **predicted pressure phase** (the antiphase cue), at a generation boundary. |
| **Must not target** | Any edge in the `NC-*` named-contact set. Sham on `NC-*` collapses into `mask_named_contacts` and makes M2 / ablation unidentifiable. |
| **Fail condition** | If sham produces a G2-like win, channel FAIL. If sham is implemented as masking or cutting `NC-*` edges → distinction FAIL. |

Time-shift or cycling signatures alone never pass a channel.


---

## 7. Locked estimand and thresholds (pre-data)

| Quantity | Lock |
|---|---|
| Primary estimand | Survival to horizon \(T\) (phase-1 survival-share framing) |
| Channel margin | \(\ge 0.15\) survival-share over best rival in the cell |
| G3 | No channel reaches \(\ge 0.15\) under the high-pressure cell |
| Soft-pass | Forbidden (including “near 0.15”) |
| N | Independent **runs** |

---

## 8. Explicit falsifiers

1. `do` ablation with no drop in the causal arm → M0 (not “almost causal”).  
2. Causal advantage only via infection physics / domain RNG in `engine.py` → design FAIL.  
3. Pass claimed from time-shift or cycling alone → FAIL.  
4. Pattern stored as heritable genotype → collapses to gene; M1 contaminated.  
5. `do` on correlated cue parent yields G2-like claim → FAIL → M0.  
6. `named_contact` implemented as genotype class → FAIL.
7. Sham implemented on `NC-*` edges (rather than `SHAM-CUE-PREDPHASE-V1`) → distinction FAIL; M2 unidentifiable.

---

## 9. Gap wording (ceiling)

We are not aware of a published precedent for a pre-registered, run-level contrast among gene, correlational pattern, and revisable interventional causal channels under a coevolving antagonist, with a ledger-visible antiphase deception cell, mandatory `do` ablation, and an explicit none-help-in-time (G3) outcome on a contact/ATP ledger. Absence of a search hit is not proof of uniqueness.

---

## 10. What this phase does not claim

- Not a discovery, law, or “first” claim.  
- Not authorisation to start runners, pilots, or campaigns.  
- Not a revision of sealed seeds `801–816`.  
- Not an update to phase-9 `vt_spatial_factorial` digests.  
- Not a ClaimGate soft-pass.  
