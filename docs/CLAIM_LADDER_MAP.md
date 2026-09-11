# Claim ladder map (internal 9 levels → public 0–5)

This table is a **correspondence only**. It does not unify
`ScientificClaimGate` with [`CLAIMS.md`](../CLAIMS.md) §5, and it does
not unlock any claim. Wave 2 may collapse the three ladders; Wave 0
only documents how they sit next to each other.

CodonTrace Genesis still blocks `intelligence`, `collective_intelligence`,
AGI, `tokyo_type1_passed`, and `avida_replacement` at every mapped level.

## The three current ladders

| Surface | How many rungs | Where |
|---|---|---|
| Public policy | 0–5 | [`CLAIMS.md`](../CLAIMS.md) §5 |
| Internal ClaimGate / strong-claim evaluator | 9 named levels | `claim_gate.py` `_CLAIM_LADDER_LEVELS`; [`SCIENTIFIC_CLAIM_LADDER.md`](SCIENTIFIC_CLAIM_LADDER.md) |
| Phase 2 evidence write-up | 8 named levels (omits `pilot_supported`) | [`PHASE2_SCIENTIFIC_EVIDENCE_LADDER.md`](PHASE2_SCIENTIFIC_EVIDENCE_LADDER.md) |

The historical page [`CLAIM_LADDER.md`](CLAIM_LADDER.md) is superseded.
See CLAIMS.md §5.

## Mapping table

Internal order is the ClaimGate / `SCIENTIFIC_CLAIM_LADDER.md` sequence
(index 0–8). “Nearest public” is the CLAIMS.md §5 level that describes
the same *kind* of evidence, not a promotion rule. Internal rungs are
not skippable inside ClaimGate; public 0–5 is a coarser policy ladder.

| Internal # | Internal level | Nearest public # | Public name (CLAIMS.md §5) | Why this pairing |
|---:|---|---:|---|---|
| 0 | `metadata_only` | 0 | Software capability | Schema, API, or record type exists; no runtime evidence. |
| 1 | `instrumented_runtime` | 1 | Runtime observation | Digest-backed records from a valid run. |
| 2 | `pilot_supported` | 1 | Runtime observation | Small pilot still sits at “it ran,” not a controlled difference. The Phase 2 write-up omits this rung. |
| 3 | `control_supported` | 2 | Candidate evidence | Treatment vs control / negative-control comparison. |
| 4 | `ablation_supported` | 3 | Mechanism support | Removing a mechanism changes the measured outcome. |
| 5 | `multi_seed_supported` | 4 | Replicated effect | Paired seeds, effect size, and an uncertainty interval. |
| 6 | `heldout_supported` | 4 | Replicated effect | Stability under partner/world shift plus leakage checks. |
| 7 | `intervention_supported` | 3 | Mechanism support | Explicit baseline/treatment intervention. Internally this sits *after* multi-seed; publicly it is still mechanism evidence, not a paper-grade claim. |
| 8 | `claim_ready_research_alpha` | 5 | Publication-grade scientific claim | All required surfaces plus replay and a ClaimGate decision digest. Still not a license to claim intelligence or an Avida replacement. |

## What this map is not

- Not a unification of the three ladders (that is later work).
- Not a new Phase letter.
- Not evidence that any public-5 claim is currently earned.
- Not a change to ClaimGate ceilings.
