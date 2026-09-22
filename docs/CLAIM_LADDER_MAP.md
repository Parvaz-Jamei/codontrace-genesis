# Claim ladder map (internal 9 levels → public 0–5)

This table is a **correspondence only**. It does not unlock any claim,
skip an internal rung, or loosen ClaimGate. Forbidden aliases stay
blocked at every mapped level.

The public policy ladder is [`CLAIMS.md`](../CLAIMS.md) §5 /
[`CLAIM_LADDER.md`](CLAIM_LADDER.md). `StrongClaimLadderResult.public_level`
is this map applied to `achieved_level`.

## Surfaces

| Surface | How many rungs | Where |
|---|---|---|
| Public policy | 0–5 | [`CLAIMS.md`](../CLAIMS.md) §5 |
| Internal ClaimGate / strong-claim evaluator | 9 named levels | `claim_gate.py`; this map |
| Standalone auditor | 0–5 | `codontrace.claimgate.audit_bundle` |

## Mapping table

Internal order is the ClaimGate sequence (index 0–8). “Nearest public”
describes the same *kind* of evidence, not a promotion rule.

| Internal # | Internal level | Nearest public # | Public name (CLAIMS.md §5) | Why this pairing |
|---:|---|---:|---|---|
| 0 | `metadata_only` | 0 | Software capability | Schema, API, or record type exists; no runtime evidence. |
| 1 | `instrumented_runtime` | 1 | Runtime observation | Digest-backed records from a valid run. |
| 2 | `pilot_supported` | 1 | Runtime observation | Small pilot still sits at “it ran,” not a controlled difference. |
| 3 | `control_supported` | 2 | Candidate evidence | Treatment vs control / negative-control comparison. |
| 4 | `ablation_supported` | 3 | Mechanism support | Removing a mechanism changes the measured outcome. |
| 5 | `multi_seed_supported` | 4 | Replicated effect | Paired seeds, effect size, and an uncertainty interval. |
| 6 | `heldout_supported` | 4 | Replicated effect | Stability under partner/world shift plus leakage checks. |
| 7 | `intervention_supported` | 3 | Mechanism support | Explicit baseline/treatment intervention. Internally this sits *after* multi-seed; publicly it is still mechanism evidence. The name does not grant public 4. A bundle that also has a confidence interval and at least 16 seeds is graded 4 by `audit_bundle`. HE01 `results_v7.json` keeps this ceiling string and audits at 4. |
| 8 | `claim_ready_research_alpha` | 5 | Publication-grade scientific claim | All required surfaces plus replay and a ClaimGate decision digest. Still not a license to claim intelligence or an Avida replacement. |

## What this map is not

- Not evidence that any public-5 claim is currently earned.
- Not a change to ClaimGate ceilings.
- Not a Tokyo Type 1 or OEE pass.
- Not a Phase letter.
