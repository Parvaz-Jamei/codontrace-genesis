# Experiment archive - 2026-09-29

Every experiment record carries its design, protocol, raw data and result side by side with the
numbers. Claims in each README cite files inside this repository.

| Experiment | Record | Verdict | Raw-data manifest | CI evidence |
|---|---|---|---|---|
| rq1_time_shift | [`README.md`](rq1_time_shift/README.md) | `INCONCLUSIVE` (in flight, 2/8 seeds) | [`evidence_files.sha256`](rq1_time_shift/evidence_files.sha256) | [`docs/ci/evidence/`](../../ci/evidence/) |
| rq3_adaptation_route | [`README.md`](rq3_adaptation_route/README.md) | `INCONCLUSIVE` (energy-confounded single-pilot separation; see README section i-b) | [`evidence_files.sha256`](rq3_adaptation_route/evidence_files.sha256) | [`docs/ci/evidence/`](../../ci/evidence/) |
| d2_recovery_window | [`README.md`](d2_recovery_window/README.md) | `FALSIFIED_IN_MODEL` (calibration tier) | [`evidence_files.sha256`](d2_recovery_window/evidence_files.sha256) | [`docs/ci/evidence/`](../../ci/evidence/) |
| sex_cost | [`README.md`](sex_cost/README.md) | negative; `c*` in `(1.1, 1.2]` confirmed | [`evidence_files.sha256`](sex_cost/evidence_files.sha256) | [`docs/ci/evidence/`](../../ci/evidence/) |
| causal_tape | [`README.md`](causal_tape/README.md) | instrument verified; estimator-labelled share 63-65 % | [`evidence_files.sha256`](causal_tape/evidence_files.sha256) | [`docs/ci/evidence/`](../../ci/evidence/) |
| ci_repair | [`README.md`](ci_repair/README.md) | maintenance; all gates green, no pin re-locked | [`evidence_files.sha256`](ci_repair/evidence_files.sha256) | [`docs/ci/evidence/`](../../ci/evidence/) |
| verification | [`README.md`](verification/README.md) | `ACCEPT` of the landed fixes | [`evidence_files.sha256`](verification/evidence_files.sha256) | [`docs/ci/evidence/`](../../ci/evidence/) |

## Notes

* Records: 7; files: 521; total: 30.64 MB.
* Large per-generation JSONL dumps are stored gzip-compressed; extracted trees, `*.tar`, `*.zip`, `__pycache__` and non-chain dataset dumps are excluded.
* Campaign seeds 801-816 remain sealed: no raw outcome for them appears anywhere in this archive, only the pre-existing sealed-ABORT record.
* The two-fold-cost line in `docs/campaigns/discovery_questions_20260928/TESTS_DONE_STATUS_2026-09-29.md` now cites the `sex_cost/` record in this archive.
