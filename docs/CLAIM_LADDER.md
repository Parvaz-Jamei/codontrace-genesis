# GENESIS Claim Ladder

**Superseded.** Use [`CLAIMS.md`](../CLAIMS.md) §5 for the public 0–5
ladder. This page is kept only as a historical evidence-chain note.

CodonTrace Genesis is a scientific digital-evolution and causal-discovery
library. The library supports ambitious claims only through deterministic
evidence chains, not through claim text or placeholder metadata.

## Standard evidence chain

```text
runtime event / protocol
→ schema-versioned artifact
→ canonical digest
→ manifest runtime hash
→ protocol status
→ evidence flags
→ ClaimGate decision
→ replay/audit test
```

A claim may be promoted only when every required evidence surface has a real digest, a valid status, and replay-consistent protocol context.

## Status discipline

`measured`, `runtime_effective`, `control_supported`, `ablation_supported`, `heldout_supported`, and `intervention_supported` require real non-placeholder runtime hashes. `provisional` requires a deterministic digest and a status reason. `not_run`, `disabled_by_config`, `not_configured`, `fixed_default`, `not_applicable`, and `not_observed` are valid reporting statuses but are not claim evidence.

## Social and collective claims

Social interaction is currently observable through event records. Capsule communication is observable as information transfer. Collective-behavior labels are not claim-eligible until the result contains coordination, non-capsule cooperation, role complementarity, heldout partner distinction, ablation evidence, and replay digest evidence. ClaimGate still blocks `intelligence`, `collective_intelligence`, AGI, `tokyo_type1_passed`, and `avida_replacement`.

## Historical note (retired phrasing)

Earlier drafts called this tree a Phase 2 integrated candidate. That
phrasing is retired. Claim promotion remains evidence-gated and
replay-audited; see CLAIMS.md §5.
