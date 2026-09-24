# Test suite layout — Phase 10

**Date:** 2026-09-24 (Asia/Tehran)  
**Goal:** Clear unit / campaign / pin organization without breaking green suites.

## Pytest markers

Declared in `pyproject.toml`:

- `unit` — fast domain-free or module unit tests
- `campaign` — HostParasiteWorld / analytics / calibration campaigns
- `pin` — BAIC/HE01 pin integrity and static architecture audits

## New layout (Phase 10+)

```
tests/platform/unit/       # e.g. life_loop export CSV, export helpers
tests/platform/campaign/   # calibration suite, World campaigns
tests/platform/pin/        # BAIC pins + static import audits
```

Legacy flat `tests/test_*.py` files are **not** mass-moved (CI path / import-mode stability). New platform-track tests prefer `tests/platform/...`.

## Legacy mapping (informational)

| Legacy glob | Suggested marker |
|---|---|
| `test_life_loop_*.py` | unit |
| `test_host_parasite_world_phase6.py`, `test_host_parasite_metrics_phase7.py`, `test_life_loop_match_phenotype_phase8.py`, `test_host_parasite_analytics_phase9.py` | campaign |
| `test_claimgate_*.py`, BAIC asserts inside phase6+ | pin (+ honesty) |

Selective runs:

```bash
uv run pytest -m unit
uv run pytest -m campaign
uv run pytest -m pin
```
