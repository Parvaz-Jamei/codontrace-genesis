# Ci Repair - experiment record, 2026-09-29

This directory is the archived experiment record: design, protocol, raw data and result together.
All paths below are relative to `docs/experiments/2026-09-29/ci_repair/`.

**Files in this record:** 16 (excluding any tarball listed as excluded).
**Raw-data manifest:** `evidence_files.sha256` (one `sha256  size  path` line per file).

## Question and hypothesis

Not a scientific question: the repair of the CI red state and the guarantee that no recorded draw or
locked digest moved while fixing it.

## Design

Four red classes: tick-index double count, banned-token docstring hygiene, RNG bypass scan, and fork
state restoration. Each fix was gated on ruff 0, compileall clean, the affected suites green and
every locked pin byte-identical.

## Protocol and provenance

`INVENTORY.md`, `verify_patch_applies.py` (`PATCH_REPRODUCES_TREE: True`, 7/7),
`campaigns_before.json` vs `campaigns_after.json` (20 scored cells byte-equal,
sha256 `2394fd82f06a0557bbfb4d95adf75e40...`).

## What was executed

The RNG equality proof (8 call sites x 32 draws, mixed-method schedules, the real ledger op
schedule, scaffold digests for seeds 0/1/7/11/401/5501), the offender scan (18 -> 0), and the
2026-09-29 commit chain `44a06f4`, `6187ff4`, `c4d8638`, `d421104`, `cc675a4`, `40138c9`, `913f18e`.

## Raw data

`rng_equality_out.json`, `rng_equality_out.txt`, `campaigns_before.json`,
`campaigns_after.json`; full sha256 manifest `evidence_files.sha256`.

## Analysis

`make_rng_patch.py`, `apply_rng_patch.py`, `prove_rng_equality.py`.

## Result

All gates green with no pin re-locked. This is maintenance, not a scientific result.

## What this does NOT show

Nothing about the science; it only shows the repairs left every recorded draw and locked digest
unchanged.

## Replay

`python test-runs/ci_repair/prove_rng_equality.py <out.json>`

## References

* CI evidence map: `docs/ci/CI_REPAIR_AND_TEST_STATUS_2026-09-29.md`

