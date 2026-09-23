# Phase 4 review — auditable multi-seed campaign runner

Human research review of the host–parasite ClaimGate campaign layer:
deterministic multi-seed arms, freeze/replay (Zaman analogy), canonical
digests, and a fail-closed bundle factory. Two critique rounds each name a
real defect, the fix, and the retest result.

## What Phase 4 delivers

- `codontrace.genesis.host_parasite_campaign.run_host_parasite_campaign` —
  multi-seed campaign **outside** `engine.py`.
- Arms: `intact`, `content_null`, `structure_null`, `dual_null`,
  `abiotic_only`, `freeze_replay_parasites`.
- Canonical digests per arm and for the whole campaign.
- ClaimGate factory:
  `bundle_from_host_parasite_campaign` / `attach_host_parasite_campaign`.
- Refuse ceilings above `candidate_evidence`. Grant `candidate_evidence` only
  when falsification rules pass **and** the campaign was run with that ceiling.
- Strip “toy” wording from public env/campaign docstrings.
- Tests in `tests/test_host_parasite_campaign_phase4.py` (16 cases).

## Critique round 1

### Flaws found

1. **Invalid `device_software_kind`.** The first factory draft passed
   `device_software_kind="digital_campaign"`, which domain validation rejects
   (`none` / `analog_table` / `simd_declared` / `samd_declared` only). Bundle
   construction crashed before digests could attach.
2. **Attach read a non-existent `claimed` attribute.** `ClaimgateBundle` stores
   the request in `extra["requested_claim"]`. Looking for `bundle.claimed`
   (always absent) skipped ceiling checks on attach.

### Fixes

- Use `device_software_kind="analog_table"` for the declared score table; set
  `infection_physics` override to `optional_env_outside_core`.
- Require `extra["requested_claim"]` on attach; refuse ceilings outside
  `{runtime_observation, candidate_evidence}` and refuse
  `candidate_evidence` unless the campaign itself carries that ceiling and
  passed falsification.

### Retest

`pytest tests/test_host_parasite_campaign_phase4.py` — green, including
overwrite refusal and missing-`requested_claim` refusal.

## Critique round 2

### Flaws found

1. **Score-only falsification failed at `steal_fraction=0`.** With zero steal,
   intact / content-null / abiotic scores all equal `1.0`, so
   `candidate_evidence` was refused even though structure-null and dual-null
   still change **injection fraction**. That treats a working structural null
   as a failed assay.
2. **`candidate_evidence` could be requested against a runtime-ceiling
   campaign.** A campaign run with `request_claim_ceiling="runtime_observation"`
   still computes `falsification_rules_passed=True` when contrasts exist. An
   early factory draft checked only the falsification flag, not whether the
   campaign actually granted the higher ceiling.

### Fixes

- Falsification now accepts mean-score **or** injected-fraction differences
  versus intact; freeze/replay vs abiotic digests must still differ when both
  arms are present.
- Factory and attach both require
  `campaign.claim_ceiling == "candidate_evidence"` before labeling a bundle at
  that ceiling.

### Retest

Same pytest file (including steal-zero and runtime-ceiling mismatch cases) plus
Phase 1–3 host–parasite suites — all green.

## Honest limits after Phase 4

- Digests audit digital campaigns; they do not prove Red Queen dynamics,
  CRISPR identity, phage therapy, vaccine effect, epidemic forecast, or BSL.
- Freeze/replay is a Zaman-style **analogy** (frozen parasite task/payload
  reused while hosts update), not a wet-lab replication of Zaman 2014.
- Public ladder stays at most `candidate_evidence` through this factory.
- `engine.py` remains untouched; `src/codontrace/genesis/population/` stays
  untracked; BAIC pins untouched.
