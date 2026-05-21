# A35 Developer Evidence-Chain Hardening

Status: developer patch on top of `codontrace-v0.3.0a1-phase3-recheck-followup-fixed.zip`.

## Goal

Strengthen CodonTrace / GENESIS as a high-power scientific library without turning it into an app or success-forcer. This patch targets cross-module evidence wiring: every public export envelope that a runner can use for claim/report decisions must also be present in the evidence manifest, and the result payload must carry the claim-ready evidence surfaces directly.

## Scientific rationale

Quality-diversity, digital-evolution, and research-software workflows depend on auditable artifacts, not only runtime counters. A public export with no manifest digest is reusable for humans but weak for replay and publication. The patch therefore treats public export envelopes, output completeness records, and the evidence manifest as first-class result payload surfaces.

## Code changes

- `GenesisRunResult.to_dict()` now includes:
  - `export_status_records`
  - `output_completeness_records`
  - `evidence_manifest`
- `GenesisRunResult.evidence_manifest` now automatically backfills any public export envelope missing from `artifact_digest_map`.
- `engine_digest_audit` records the deterministic `result_core_payload_digest` to avoid recursive result-digest dependency after evidence surfaces are embedded in the result payload.
- Active QD search classes/functions already imported at package level are now fully listed in `codontrace.genesis.__all__` for star-import/API stability.

## Newly covered gap

Before this patch, these export surfaces had export/status records but were absent from `evidence_manifest.artifact_digest_map`:

- `child_admission_records`
- `death_classification_records`
- `death_energy_summary_records`

After the patch, the manifest covers every current public export envelope.

## New regression tests

Added `tests/test_genesis_a35_developer_evidence_chain_hardening.py`:

- verifies every public export envelope is present in the evidence manifest;
- verifies `to_dict()` carries the evidence manifest, export status records, and output completeness records;
- verifies result/manifest/payload determinism after the evidence-chain hardening;
- verifies active QD search symbols are complete in `codontrace.genesis.__all__`.

## Compatibility

- SemVer remains `0.3.0a1`.
- No existing public API was removed or renamed.
- The result payload is extended with new fields; older code reading prior fields remains compatible.
- The engine remains Library-as-Tool: no success is hard-coded and no claim gate is weakened.
