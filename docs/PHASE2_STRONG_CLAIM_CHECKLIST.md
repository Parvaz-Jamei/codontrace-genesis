# Phase 2 Strong Claim Checklist

Before a Phase 2 claim is accepted, reviewers must check:

- The feature changed an existing module, not a parallel runtime.
- Default/fixed behavior remains backward-compatible.
- Artifact has schema, digest, status, and replay policy coverage.
- Negative/control evidence exists for strong claims.
- Ablation/intervention exists for causal or attribution claims.
- Multi-seed/effect-size/CI requirements are satisfied where stochastic claims are made.
- Metadata-only artifacts do not unlock claim labels.
- Docs and tests describe the same capability level.
- No birth, discovery, macro utility, social success, or OEE result is hard-coded.

The project goal is a strong AI/evolution/discovery research library. Strong claims are welcome when the evidence is strong enough.

## Strict acceptance addendum

Phase 2 is treated as an integrated candidate until the full evidence chain is valid:

```text
runtime → artifact → digest → manifest → status → evidence flags → ClaimGate → replay tests
```

A field with `measured`, `runtime_effective`, or `provisional` status must carry a real deterministic runtime hash. Placeholder values are not evidence. Engine-built semantic proxy reports are active/provisional evidence surfaces, not fixed defaults. ADF usefulness/compression claims require reusable source-mapped macros with controls and positive compression; single-action task shortcuts must use lower-level utility language.
