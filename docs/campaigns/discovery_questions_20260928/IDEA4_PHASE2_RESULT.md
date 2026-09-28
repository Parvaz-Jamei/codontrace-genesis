# Idea 4 — Phase-2 result record (branching-history recovery window)

**Date:** 2026-09-28  
**Harness tip:** `ab8e5d6`  
**Test-gate tip:** `b118517`  
**Design digest:** [`IDEA4_PHASE2_DESIGN_DIGEST.md`](IDEA4_PHASE2_DESIGN_DIGEST.md)  
**Test gate:** [`PHASE2_HARNESS_TEST_GATE.md`](PHASE2_HARNESS_TEST_GATE.md)  
**Claim ceiling:** `phase2_design`  
**Status:** sealed result after two result rounds — engineering outcome only

## Sealed positive outcome

1. Phase-2 harness implements the locked ledger operations and identity fields from the design digest, including checkpoint `CKPT-RELOCATE-RECOVERY-TOKEN-V1` on `token:recovery:FI-RARECLASS-CONTACT-YIELD-V1`, distinct from `ablate_knowledge_digest` / `digest:pred_fail:*` and from `cut_named_scaffold` / `SCAF-CONTACT-SRC-PATH-V1`.
2. Distinction locks hold under smoke: recovery token, knowledge digest, and named-scaffold cuts do not collapse into one another; `class=rare` remains a contact-ledger tag only.
3. `GenerationBoundaryObserver` wiring is present for generation-boundary interventions outside `engine.py`.
4. Smoke packs report `hypothesis_supported=False` and `red_queen_proved=False`.
5. Pre-registered thresholds remain in constants (slope ≥0.15, |ΔP|≥0.20); they are not outcome-tuned in this phase.

## Explicit non-outcomes (soft-pass if claimed)

This phase does **not** establish:

- a recovery window in \(P(\mathrm{recover}\mid \tilde{t},\,\mathrm{ecology},\,\mathrm{knowledge})\);
- scored slope ≥0.15 or |ΔP|≥0.20 on a pre-registered normalised \(\tilde{t}\) series;
- scored functional-innovation recovery under the 1.25× / ≥3-boundary rule;
- N = independent runs (smoke used single-seed wiring checks);
- factorial resolution of R0–R3.

Short smoke grids are wiring/distinction checks, not campaign evidence. Reading `engineering_green` as a recovery-window result is FAIL.

## Deferred

Authorised JSONL campaigns (prefer ≥6 cores) remain off until the owner allows execution. Sealed seeds `801–816` untouched. No infection physics in `engine.py`.

## Gap wording (ceiling)

We are not aware of a published precedent for the sealed digest’s mid-history branching-history estimand with the locked ledger ops. Absence of a search hit is not proof of uniqueness. This result record does not claim that estimand was demonstrated.
