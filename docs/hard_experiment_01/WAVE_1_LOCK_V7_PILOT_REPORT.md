# HE01 SCHEMA v7 / LOCK — pilot report (seeds 1000–1009)

**Date:** 2026-09-17 (Asia/Tehran). **Branch:** `fix/he01-seed-variance-negative-control`.
**Schema:** `hard_experiment_01_v7`. **Lock digest:** `818b4efe364d5248…`.

## Gates

| Gate | Result |
|---|---|
| Assay (oracle > off; not extinct; channel active) | PASS |
| content_null EAT rate ≈ 0 + content_changed | PASS (eat_rate=0, rate=1.0) |
| Treatment across-seed sd > 0 | PASS (sd ≈ 9.24) |
| SCHEMA v7 + amd04 + amd05 + lock digests | PASS |
| Activity match | exploratory / non-blocking (gap ≈ 27.1 ≫ ε=1) |
| **cleared_for_11_40** | **True** |

## Arm means (pilot n=10)

| Arm | mean | sd |
|---|---:|---:|
| source_bias_on | 64.52 | 9.24 |
| source_bias_off | 44.57 | 12.10 |
| capsules_off | 28.00 | 0.00 |
| capsules_content_null | 28.00 | 0.00 |
| capsules_shuffled | 42.94 | 7.32 |
| oracle_capsule | 78.49 | 0.27 |

Confirmatory null equals channel-off. Shuffled > off expected (sensitivity).
Artifact: `pilot_v7.json`. Analysis seeds 11–40 run after this clearance → `results_v7.json`.
