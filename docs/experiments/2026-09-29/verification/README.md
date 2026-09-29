# Verification - experiment record, 2026-09-29

This directory is the archived experiment record: design, protocol, raw data and result together.
All paths below are relative to `docs/experiments/2026-09-29/verification/`.

**Files in this record:** 43 (excluding any tarball listed as excluded).
**Raw-data manifest:** `evidence_files.sha256` (one `sha256  size  path` line per file).

## Excluded large artifacts (sha256 recorded, not imported)

* `docs/experiments/2026-09-29/d2_recovery_window/provenance/tip.tar` - `e4ba113bbc5858f90f579309cc5c7510771d1c25e221b06d96e01f0043926c7e`
* `docs/experiments/2026-09-29/verification/full44a06f4.tar` - `a20845bca785959d7849a6bf9e4d4e4daf33e8d6945b763682033367fbff1cbe`
* `docs/experiments/2026-09-29/verification/full6187ff4.tar` - `416fae0f4af225e1f6029c881c49612ab10f45a6dd9f49612c5b00823ff80a82`
* `docs/experiments/2026-09-29/verification/base49750b1.tar` - `236de879e12c7c020588d0e1f46bebb969856d35914012f91659adb766870075`

## Question and hypothesis

Independent verification of the manager's landed changes: does each claimed gate reproduce from the
raw artifacts on a separate code path?

## Design

Independent recomputation of the tick-index batch equivalence, the RNG stream equality, the 6/6 fork
identity cells, the unpatched negative control, the pin byte-identity and the fork isolation
residual.

## Protocol and provenance

`CLAIMS.json`, `claim-a.md`/`claim-b.md`/`claim-c.md`, `task10_*`, `probe_report.json`. The
`base*.tar` and `full*.tar` source trees are **excluded** by the size rule; their sha256 is recorded
below.

## What was executed

`VERIFICATION_REPORT.md` records **ACCEPT** of `44a06f4` (batch(N) == N x `run_ticks(1)` for
N = 1, 5, 17; fork offset honoured; 12/12 pins byte-identical);
`VERIFICATION_TASK10_REPORT.md` records the task-10 verification (offender count, equality, 6/6
identity, unpatched negative control, pin identity).

## Raw data

`task10_A1_offenders.txt`, `task10_A1_test_rng.txt`, `task10_A2_author_equality.json`,
`task10_B1_identity_913f18e.txt`, `task10_B2_identity_40138c9_negctrl.txt`,
`task10_B3_pin_identity.txt`, `task10_B4_fork_isolation.txt`, `task10_C_ruff.txt`,
`task10_C_compile.txt`; full sha256 manifest `evidence_files.sha256`.

## Analysis

`check_fork_identity.py`, `check_rng_equality.py`, `check_pins_vs_434bbd1.py`,
`scan_rng_offenders.py`, `build_frozen_drift.py`.

## Result

`ACCEPT` for the tick-index fix and the RNG migration; the frozen-drift verdict was
`RE-LOCK_IS_MAINTENANCE` (separately documented and owner-approved in `6c979f5`). No pin was
re-locked by the verifier.

## What this does NOT show

It does not re-derive the science results; it verifies the engineering gates and the digest
invariants only.

## Replay

`python docs/experiments/2026-09-29/verification/check_fork_identity.py` and the `check_*.py` scripts in this directory.

## References

* `docs/ci/CI_REPAIR_AND_TEST_STATUS_2026-09-29.md` and
  `docs/ci/evidence/` for the in-repo regenerated outputs

