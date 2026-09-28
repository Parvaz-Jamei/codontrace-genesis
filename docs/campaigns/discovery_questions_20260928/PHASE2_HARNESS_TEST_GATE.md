# Phase-2 harness — test gate (ideas 4 and 2)

**Date:** 2026-09-28  
**Base commit:** `ab8e5d6` (`ab8e5d6`), `main`  
**Status:** engineering pass recorded; measurement claims deferred  
**Claim ceiling:** `phase2_design` (unchanged)  
**Design digests:** [`IDEA4_PHASE2_DESIGN_DIGEST.md`](IDEA4_PHASE2_DESIGN_DIGEST.md), [`IDEA2_PHASE2_DESIGN_DIGEST.md`](IDEA2_PHASE2_DESIGN_DIGEST.md)

This note records the sealed test-gate reading of the phase-2 harness smoke on `ab8e5d6`. It does not authorise JSONL campaigns, elevate the claim ceiling, or report a discovery.

## Engineering pass (accepted)

- Locked identity fields present: Idea 4 checkpoint `CKPT-RELOCATE-RECOVERY-TOKEN-V1` distinct from knowledge digests and from `SCAF-*`; Idea 2 sham `SHAM-CUE-PREDPHASE-V1` distinct from `NC-*` named-contact edges.
- `named_contact` = ledger edge ID; `class=rare` = contact-ledger tag only.
- Boundary hooks follow the `GenerationBoundaryObserver` contract (generation index only).
- Pre-registered thresholds remain in constants (Idea 4 slope ≥0.15, |ΔP|≥0.20; Idea 2 margin ≥0.15).
- Smoke packs set `hypothesis_supported=False` and `red_queen_proved=False`.
- No infection physics added to `engine.py`. Sealed seeds `801–816` untouched.

## Measurement gate (smoke is not evidence)

1. `engineering_green` is not evidence for \(P(\mathrm{recover}\mid \tilde{t},\,\mathrm{ecology},\,\mathrm{knowledge})\) (Idea 4) and is not a survival-share margin to horizon \(T\) (Idea 2).
2. Short smoke grids (for example Idea 4 `t_tilde_grid=(2,3,4)`) are not a pre-registered normalised \(\tilde{t}=t/T\) intervention series on ≥3 mid-history points. Reading them as a recovery window is soft-novelty FAIL.
3. Idea 4 functional-innovation rule (1.25× rare-class yield for ≥3 consecutive boundaries) is present as a shape only in smoke; it is not scored campaign evidence.
4. Single-seed smoke does not exercise N = independent runs. Contact pairs are not N.
5. Sequential smoke schedules that fire all ops in one path check wiring and distinctions; they are not factorial R0–R3 (Idea 4) or gene/pattern/causal cells with separate `do` ablation (Idea 2).
6. Idea 2 sham wiring is checked; a sham that would produce a G2-like win remains an unscored control until a campaign is authorised.

## Deferred

Full JSONL campaigns remain off until the owner allows execution and sufficient compute is available (prefer ≥6 cores). No design delta is introduced by this note.

## Gap wording (ceiling)

We are not aware of a published precedent matching the sealed digests’ estimands; absence of a search hit is not proof of uniqueness. This harness land does not claim such a precedent was demonstrated.
