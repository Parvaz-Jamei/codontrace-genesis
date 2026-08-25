# Changelog

## 0.3.0b2 — Scientific evidence-gate hardening (capsule / memory / generalization)

### Added

- `codontrace.genesis.capsule_utility`: pure outcome-based capsule utility evaluator (`capsule_outcome_utility_v2`). Utility is measured selection-fitness delta only; synthetic fixed rewards (e.g. `task_delta = 1.0`) are forbidden. `claim_eligible` requires adoption + measured positive delta + trusted source status (`measured` / `last_known`).
- `codontrace.genesis.memory_evidence`: pure delayed-reward evidence classifier. Write→later reward without read is `temporal_correlation` only. Causal claim requires read-linked evidence plus ablation `control_digest`.
- Science unit tests:
  - `tests/test_capsule_utility_science.py`
  - `tests/test_memory_delayed_evidence_science.py`
  - `tests/test_generalization_protocol_science.py`

### Changed

- `engine.capsule_utility_records` now delegates to the pure evaluator (single source of truth).
- `engine.memory_use_records` classifies delayed-reward chains via the evidence ladder (`observed_write` → `temporal_correlation` → `read_linked` → `causal_support`).
- `engine.generalization_records` no longer emits first/last-tick digest proxies. Without a real heldout protocol, status is `protocol_not_run` with digests `not_run:*` and `claim_eligible=False`.
- `SignalActionLink` / `MemoryUseEvidence` schema → v2 evidence fields (`evidence_status`, `causal_status`, `control_digest`, `claim_eligible`).
- `GeneralizationResult` schema → v2 with hard gate against `protocol_not_run` and identical train/heldout digests.
- Package identity: `0.3.0b1` → `0.3.0b2` (`pyproject.toml`, `codontrace.__version__`, `CITATION.cff`).

### Claim policy

No loosening of scientific claims. Changes tighten evidence surfaces so ClaimGate cannot treat correlation or synthetic rewards as causal success. GENESIS remains research-beta software; it does not claim AGI, consciousness, proven collective intelligence, or peer-reviewed superiority.

## 0.3.0b1 — Studio-readiness beta release

### Changed

- Promoted current package identity from `0.3.0a2` alpha to `0.3.0b1` beta.
- Updated package metadata, runtime `codontrace.__version__`, citation metadata, release evidence, README install pins, and current release artifact identity.
- Kept historical `added_in`/compatibility provenance fields intact where they describe APIs introduced during the alpha line.

### Added

- Added `docs/STUDIO_PHASE1_EXECUTION_SPEC.html` as the repo-ready Phase 1 Studio execution handoff.
- Added `docs/STUDIO_BOUNDARY.md` to lock the library/UI boundary before Studio work begins.
- Added `docs/PERFORMANCE_PHASE1.md` as a safe profiling and optimization plan for live execution without changing scientific semantics.

### Notes

This beta promotion does not make CodonTrace a UI product and does not loosen the claim boundary. The core remains a dependency-free research library; Studio/API/Desktop work belongs in a separate consumer repository.

## 0.3.0a2 — AGPL metadata correction alpha release

### Changed

- Updated release identity from `0.3.0a1` to `0.3.0a2`.
- Updated package, citation, and runtime version metadata for the AGPL public alpha line.
- Removed deprecated license classifier from `pyproject.toml` to comply with modern Python packaging license-expression behavior.
- Kept `AGPL-3.0-or-later` as the package license expression.

### Notes

This release is a metadata/legal-packaging correction release. It does not change the scientific claim boundary: CodonTrace Genesis remains alpha research software and does not claim final peer-reviewed benchmark results, AGI, consciousness, or proven collective intelligence.

## 0.3.0a1 — Alpha research release

This release prepares CodonTrace Genesis for public alpha distribution as a deterministic research-software library.

### Added

- Causal mechanism surfaces for capsule ablation, capsule outcome windows, signal-memory-action links, skill-compression ablation, and child-outcome audits.
- Role, territory, collective-task, role-ablation, heldout-partner, multi-agent contribution, source-reputation, counterfactual-replay, and extended OEE schema surfaces.
- Runtime-wiring manifest digests for the new causal mechanism policies.
- Integration audit helpers for public API, replay-policy coverage, evidence consistency, package hygiene, and reference hygiene.
- CI and PyPI Trusted Publishing workflow templates.

### Changed

- Release identity is aligned to `0.3.0a1`.
- Public documentation was rewritten for release-facing clarity and claim control.

### Claim policy

This is an alpha research-software release. It exposes deterministic primitives and evidence structures; it does not claim AGI, consciousness, artificial life, benchmark superiority, causal certainty, or autonomous open-ended discovery.
