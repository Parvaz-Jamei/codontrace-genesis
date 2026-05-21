# GENESIS Feature Maturity Status

**Status:** Phase 1 strong-core artifact
**Purpose:** show which capabilities are runtime-effective, pilot-effective, partial, scaffolded, or missing, without defensive/minimal wording.

## Maturity classes

| Class | Meaning |
|---|---|
| `mature` | stable public API, runtime effect, replay/digest tests, negative controls |
| `pilot_effective` | works in official pilot or focused integration test |
| `partial` | real API/evidence exists, but one or more claim-level requirements remain |
| `scaffold` | public schema/hook exists for future protocol; not a behavioral claim |
| `missing` | not yet implemented |

## Phase 1 baseline after patch

| Capability | Status | Public evidence surface |
|---|---|---|
| Public result contract | `pilot_effective` | `GenesisRunResult` properties and export envelopes |
| Evidence manifest | `pilot_effective` | `EvidenceManifest.artifact_digest`, `feature_status`, canonical digest |
| Action wiring | `pilot_effective` | `ActionWiringMatrix`, `ActionWiringRecord` |
| Energy / death / failure intelligence | `pilot_effective` | diagnostics records and engine export status |
| Reproduction / mutation / lineage | `pilot_effective` | reproduction gates, mutation plans, lineage records |
| QD selection pressure | `pilot_effective` | QD summaries, selection audit, parent feedback audit |
| Capsule transfer | `pilot_effective` | adoption/cost/utility/shuffle records |
| Memory delayed reward | `pilot_effective` | memory use and delayed reward traces |
| Toolchain primitives | `pilot_effective` | `ToolActionSpec`, `ToolChainRecord`, primitive handlers |
| Causal / discovery / generalization hooks | `partial` | protocol hooks and claim-gated status records |
| Strong claim ladder | `pilot_effective` | `StrongClaimLadderResult` |

## Engineering rule

Empty outputs are allowed only when they carry schema and status. Dummy constant fields are not acceptable evidence. A feature can be disabled, unavailable, or provisional, but that state must be explicitly represented.
