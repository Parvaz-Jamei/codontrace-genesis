# Experiment archive - 2026-10-06

Every experiment record carries its design, protocol, raw data and result side by side with the numbers. Claims in each README cite files inside this repository.

| Experiment | Record | Verdict | Raw-data manifest | CI evidence |
|---|---|---|---|---|
| `grand_rq_observatory_500gen` | [`GRAND_RED_QUEEN_OBSERVATORY_REPORT.md`](GRAND_RED_QUEEN_OBSERVATORY_REPORT.md) | `SUPPORTED_IN_MODEL` (4/4 initial seeds passed 5-epoch cross-infection assay; controls pass; `red_queen_proved=false` strictly preserved) | `simulation_runs/run_grand_rq_observatory_24h/` | [`tests/test_rq_controlled_benchmark.py`](../../../tests/test_rq_controlled_benchmark.py) |
| `rq_controlled_benchmark` | [`../../RQ_CONTROLLED_BENCHMARK.md`](../../RQ_CONTROLLED_BENCHMARK.md) | `SUPPORTED_REFERENCE_MODEL` | `runs/rq-reference-new/` | [`tests/test_rq_controlled_benchmark.py`](../../../tests/test_rq_controlled_benchmark.py) |
| `console_preview_engine` | [`../../../src/codontrace/console/`](../../../src/codontrace/console/) | `ACCEPT` (11/11 tests pass, headless visual audit verified, `core-boundary-ok`) | `console/` | [`tests/test_console_preview.py`](../../../tests/test_console_preview.py) |

## Notes

* Standing labels follow [`docs/protocol/CLAIM_LADDER_PROTOCOL_v0.1.md`](../../protocol/CLAIM_LADDER_PROTOCOL_v0.1.md).
* Pre-registration adherence: `docs/campaigns/rq_redesign_20260928/PREREG_V2.md`.
* Architectural boundary: Verified via `tools/check_core_boundary.py` (`core-boundary-ok`).
* All hardware execution performed on 4-core Allwinner H618 with continuous invariant checking.
