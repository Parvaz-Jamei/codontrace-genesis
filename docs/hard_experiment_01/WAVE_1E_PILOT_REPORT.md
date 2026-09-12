# WAVE 1E PILOT REPORT — seeds 1000–1009

## Summary

**Overall Amd 04 pilot gates: FAIL**

| Gate | Result | Notes |
|------|--------|-------|
| 1. `assay_failed is False` (oracle > capsules_off) | PASS | assay_failed=False; assay_failures=[]; oracle_mean=78.4887 > capsules_off_mean=28 → True |
| 2. content_null: EAT/profitable payload rate ≈ 0; content_changed evidence | PASS | EAT_rate=0; content_changed_rate=1 |
| 3. mean_abs_activity_match_gap ≤ 1 (ε=1) | FAIL | mean_abs_activity_match_gap=25.4; ε=1.0 |
| 4. Legacy shuffled > off (sensitivity only) | PASS | shuffled_mean=43.9825; capsules_off_mean=28; expected shuffled > off |
| 5. schema v6 + amd04 digest present | PASS | schema=hard_experiment_01_v6; amd04_digest=6a1facb02ba502299a17fc856c7ece611ca1854bc906d921729186ae1421fd60 |

## Arm mean / sd

| arm | n | mean | sd |
|-----|---|------|----|
| source_bias_on | 10 | 64.4975 | 9.14637 |
| source_bias_off | 10 | 44.5487 | 12.0707 |
| capsules_off | 10 | 28 | 0 |
| capsules_content_null | 10 | 28 | 0 |
| capsules_activity_matched | 10 | 28 | 0 |
| capsules_shuffled | 10 | 43.9825 | 8.10874 |
| oracle_capsule | 10 | 78.4887 | 0.188419 |

## Primary contrasts / decision (report-only beyond Amd 04 pilot gates)

| contrast | n | mean_delta | sd_delta | ci_low | ci_high | p_holm | dz |
|----------|---|------------|----------|--------|---------|--------|-----|
| source_bias_on vs source_bias_off | 10 | 19.9488 | 9.62025 | 14.4388 | 25.9212 | 0.00585938 | 2.07362 |
| source_bias_on vs capsules_off | 10 | 36.4975 | 9.14637 | 31.3788 | 42.2366 | 0.00585938 | 3.99038 |
| source_bias_on vs capsules_content_null | 10 | 36.4975 | 9.14637 | 31.3788 | 42.2366 | 0.00585938 | 3.99038 |
| capsules_content_null vs capsules_off | 10 | 0 | 0 | 0 | 0 | None | 0 |

- assay_failed: False
- assay_failures: []
- decision_rule_passed: False
- decision_rule_failures: ['statistical_tier_not_research_grade']
- claim_ceiling: runtime_observation
- statistical_tier: exploratory_only
- mean_abs_activity_match_gap: 25.4

## Activity-match diagnostic (Gate 3 FAIL — do not retune)

Amd 04 ε=1 on mean |activity_match_gap|. Gap = accepted_matched − budget(=source_bias_on accepts).
When treatment accept volume is high, content-null channel cannot reach the yoke budget → large negative gaps.

| seed | on_accepted (budget) | am_accepted | am_gap | cn_accepted | on_ATP | am_ATP | cn_ATP |
|------|----------------------|-------------|--------|-------------|--------|--------|--------|
| 1000 | 390 | 239 | -151 | 239 | 78.375 | 28.0 | 28.0 |
| 1001 | 299 | 272 | -27 | 272 | 77.725 | 28.0 | 28.0 |
| 1002 | 143 | 143 | 0 | 262 | 52.375 | 28.0 | 28.0 |
| 1003 | 156 | 156 | 0 | 233 | 70.0875 | 28.0 | 28.0 |
| 1004 | 377 | 317 | -60 | 317 | 65.7 | 28.0 | 28.0 |
| 1005 | 143 | 143 | 0 | 230 | 64.075 | 28.0 | 28.0 |
| 1006 | 221 | 221 | 0 | 241 | 59.3625 | 28.0 | 28.0 |
| 1007 | 104 | 104 | 0 | 256 | 52.05 | 28.0 | 28.0 |
| 1008 | 260 | 244 | -16 | 244 | 65.5375 | 28.0 | 28.0 |
| 1009 | 234 | 234 | 0 | 334 | 59.6875 | 28.0 | 28.0 |

- mean |gap| = 25.4 (threshold ≤ 1) — **FAIL**
- seeds with |gap|>0: 1000, 1001, 1004, 1008
- content_null / activity_matched ATP both = capsules_off (28): null payload destroys surplus (good for Gate 2 / confirmatory null).
- content_null EAT profitable rate = 0; shuffle_content_changed_rate = 1.0; bias_payload_totals empty (no EAT_LUMEN counted).
- Legacy shuffled mean 43.98 > off 28 as expected (sensitivity only; not confirmatory).

## Recommendation

**DO NOT run analysis seeds 11–40** — Amd 04 pilot gates FAIL. cleared_for_11_40=false.

Gate 3 (activity match ε) FAILED — report clearly; do **not** retune Amd 04 or peek 11–40.

## Meta

- Wall time: 722.8s (12.05 min)
- Seeds: [1000, 1001, 1002, 1003, 1004, 1005, 1006, 1007, 1008, 1009] (PILOT ONLY — no 11–40)
- Scale: research (40 ticks × 16 pop)
- schema_version: `hard_experiment_01_v6`
- prereg_amendment_04_digest: `6a1facb02ba502299a17fc856c7ece611ca1854bc906d921729186ae1421fd60`
- prereg_digest: `cb4643a305a48a17250b4e38af3f423afc0c040b4ffac039c8b0ec1413b4fc40`
- prereg_amendment_02_digest: `14c111af81e415c8a381411a3520294e8bbdec311e4ffe3bc421d46992202f2f`
- prereg_amendment_03_digest: `3a9d4fd441f71f5f60ef5b5b1496148ae4178a9126170765a76d712465b87058`
- food_layout: `every_cell`
- role_layout: `seed_permuted_v3_multiset`
- HEAD: wave-1d-seed-variance @ a1ce4e6 — SCHEMA v6 / Amendment 04
- JSON: `/workspace/codontrace-handoff/WAVE_1E_PILOT_1000_1009.json`
- No `docs/results_v5.json` write; no ClaimGate raise; no Amd edits; no push.

---
MACHINE_SUMMARY
overall=FAIL
cleared_for_11_40=false
wall_seconds=722.8431981650065
assay_failed=False
content_null_eat_rate=0.0
content_changed_rate=1.0
mean_abs_activity_match_gap=25.4
source_bias_on_mean=64.4975 source_bias_on_sd=9.1463748891
source_bias_off_mean=44.54875 source_bias_off_sd=12.070726829
capsules_off_mean=28.0 capsules_off_sd=0.0
capsules_content_null_mean=28.0 capsules_content_null_sd=0.0
capsules_activity_matched_mean=28.0 capsules_activity_matched_sd=0.0
capsules_shuffled_mean=43.9825 capsules_shuffled_sd=8.1087405687
oracle_capsule_mean=78.48875 oracle_capsule_sd=0.1884190439
