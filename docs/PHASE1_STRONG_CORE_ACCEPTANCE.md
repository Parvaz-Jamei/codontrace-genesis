# Phase 1 Strong Core Acceptance

**Phase:** Strong Core, Evidence Engine, Feature Power-Up
**Target:** claim-ready research-alpha core without hard-code or success forcing.

## Implemented in this patch

- Added public action wiring matrix API:
  - `ActionWiringRecord`
  - `ActionWiringMatrix`
  - `export_action_wiring_matrix(...)`
- Strengthened `EvidenceManifest`:
  - canonical finite JSON digest helper
  - aggregate `artifact_digest`
  - `determinism_policy`
  - public `feature_status`
  - schema validation helper
- Added strong claim ladder API:
  - `StrongClaimLadderResult`
  - `evaluate_strong_claim_ladder(...)`
- Added QD mode alias:
  - `qd_mode="off"` maps safely to existing disabled mode.
- Fixed a real primitive bug:
  - `collect_resource_primitive_handler` now defines inventory state before missing-resource failure.
- Added Phase 1 gate tests for:
  - action wiring
  - artifact manifest schema
  - strong claim ladder
  - public result surface
  - toolchain missing-resource failure
- Added documentation matrices for:
  - feature maturity
  - action wiring
  - mutation operators
  - scientific claim ladder

## Acceptance principle

The patch strengthens the library as a large scientific AI/evolution experiment engine. It does not force success, does not weaken controls, and does not turn core into an app. It gives stronger public primitives, status, digest, and claim-level evidence.

## Required gates

```bash
python -m compileall -q src tests examples
PYTHONPATH=src pytest -q tests/genesis_gates/test_action_wiring_matrix.py \
  tests/genesis_gates/test_artifact_manifest_claim_ready_schema.py \
  tests/genesis_gates/test_claim_gate_strong_claim_ladder.py \
  tests/genesis_gates/test_result_public_surface_contract.py \
  tests/genesis_gates/test_toolchain_primitives_and_failures.py
```
