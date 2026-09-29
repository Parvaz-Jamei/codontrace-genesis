# Sex Cost - experiment record, 2026-09-29

This directory is the archived experiment record: design, protocol, raw data and result together.
All paths below are relative to `docs/experiments/2026-09-29/sex_cost/`.

**Files in this record:** 12 (excluding any tarball listed as excluded).
**Raw-data manifest:** `evidence_files.sha256` (one `sha256  size  path` line per file).

## Question and hypothesis

Does coevolution maintain costly sex in the audited ATP ledger, and where does the critical cost
`c*` sit?

## Design

7 costs x 3 antagonist turnovers x 100 paired seeds = 2100 runs, with the ledger identity as the
instrument check (maximum residual 2.556e-10). Thresholds are the pre-derived brackets, not tuned.

## Protocol and provenance

`manifest.json`, `analysis.json`, `analysis.log`, `sweep.log`, `fill_gap.log`; harnesses
`sweep_sex_cost.py`, `analyze_sex_cost.py`.

## What was executed

The full 2100-run sweep; `RESULT.md` is the pack's own summary.

## Raw data

Full sha256 manifest: `evidence_files.sha256` (raw `raw.jsonl` included).

## Analysis

`analyze_sex_cost.py` over `raw.jsonl`.

## Result

The `c*` bracket from the intervals is `(1.1, 1.2]`: `c = 1.1` passes all three turnovers and
`c = 1.2` fails all three, with strictly disjoint intervals. The old narrowing is **confirmed**, not
superseded. The earlier single-seed probe is a superseded pilot whose magnitudes do not survive the
intervals.

## What this does NOT show

It does not show a mechanism for the cost threshold, and the result is a negative for the two-fold
cost of sex in this model.

## Replay

`python docs/experiments/2026-09-29/sex_cost/sweep_sex_cost.py` then `python docs/experiments/2026-09-29/sex_cost/analyze_sex_cost.py`

## References

* "Runaway coevolution: adaptation to heritable and nonheritable environments", *Evolution* 68
  (2014) - https://doi.org/10.1111/evo.12470

