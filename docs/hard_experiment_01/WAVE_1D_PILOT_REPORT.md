# WAVE 1D PILOT REPORT — seeds 1000–1009

## خلاصه / Summary

**Overall Amd 02 calibration gates: FAIL**

| Gate | Result | Notes |
|------|--------|-------|
| assay valid (`assay_failed=False`) | FAIL | failures=['assay_failed_positive_control_did_not_move_outcome'] |
| analysis-arm `sd > 0` (all 4) | FAIL | ANALYSIS_ARMS=['source_bias_on', 'source_bias_off', 'capsules_off', 'capsules_shuffled'] |
| primary contrast `sd_delta > 0` (recommended) | PASS | PRIMARY_CONTRASTS=[('source_bias_on', 'source_bias_off'), ('source_bias_on', 'capsules_off'), ('source_bias_on', 'capsules_shuffled')] |
| decision_rule_* (n≠30 expected) | REPORT ONLY | passed=False; failures=['assay_failed_positive_control_did_not_move_outcome', 'statistical_tier_not_research_grade', 'ci_on_vs_off_includes_0', 'holm_on_vs_off_not_below_alpha', 'ci_on_vs_shuffled_includes_0', 'holm_on_vs_shuffled_not_below_alpha', 'dose_pattern_not_supported'] |

## Arm mean / sd

| arm | n | mean | sd | sd>0 |
|-----|---|------|----|------|
| source_bias_on | 10 | 27.6225 | 4.42539 | PASS |
| source_bias_off | 10 | 27.8725 | 2.14933 | PASS |
| capsules_off | 10 | 28 | 0 | FAIL |
| capsules_shuffled | 10 | 27.6462 | 2.16465 | PASS |

Oracle vs capsules_off means: oracle=21.205 (sd=1.70532); capsules_off=28 (sd=0)

## Primary contrasts (mean_delta / sd_delta)

| contrast | n | mean_delta | sd_delta | sd_delta>0 |
|----------|---|------------|----------|------------|
| source_bias_on vs source_bias_off | 10 | -0.25 | 4.29595 | PASS |
| source_bias_on vs capsules_off | 10 | -0.3775 | 4.42539 | PASS |
| source_bias_on vs capsules_shuffled | 10 | -0.02375 | 5.2185 | PASS |

## Assay failures

- assay_failed_positive_control_did_not_move_outcome

## Recommendation

**STOP / amend consideration** — pilot calibration FAIL. Do not clear analysis seeds 11–40 until gates pass. Prefer report-fail first; amend Amd 02 only if locked text must change.

## Meta

- Wall time: 564.8s (9.41 min)
- Seeds: [1000, 1001, 1002, 1003, 1004, 1005, 1006, 1007, 1008, 1009]
- Scale: research (40 ticks × 16 pop)
- Digest: `01932a561866b37f9c3b67de5fef9a025c434848cfb69364c9c60f4d3df07e30`
- JSON: `/workspace/codontrace-handoff/WAVE_1D_PILOT_1000_1009.json`

---

### فارسی

پایلوت کالیبراسیون رد شد. دانه‌های ۱۱–۴۰ آزاد نیستند. ابتدا گزارش شکست؛ اصلاح Amd 02 فقط در صورت لزوم.
