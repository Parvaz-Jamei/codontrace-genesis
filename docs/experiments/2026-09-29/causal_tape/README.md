# Causal Tape - experiment record, 2026-09-29

This directory is the archived experiment record: design, protocol, raw data and result together.
All paths below are relative to `docs/experiments/2026-09-29/causal_tape/`.

**Files in this record:** 57 (excluding any tarball listed as excluded).
**Raw-data manifest:** `evidence_files.sha256` (one `sha256  size  path` line per file).

## Question and hypothesis

What is the exact interventional effect of a single substitution, and how much of the quantity
previously labelled estimator bias is a whole-tape re-routing gap rather than model
misspecification?

## Design

Two estimators are reported side by side, always with their labels: the re-routing share is around
63-65 per cent at the highest epistasis level, with `64.1` per cent being the bootstrap median of
the ratio of medians, the raw pooled ratio of medians `62.97` per cent, the mean per-draw ratio of
medians `63.75` per cent and the ratio of means `64.8` per cent; the ratio-of-medians interval is
`[55.8, 73.3]` and the ratio-of-means interval `[59.9, 69.2]`; the interval is knife-edge sensitive
to the rank tolerance (Cholesky `[56.02, 73.25]`, published 1e-8 SVD `[55.78, 73.33]`, 6 of 1500
resamples on the boundary).

## Protocol and provenance

`PREREG.md`, `SCALE_DESIGN.md`, `harness.py`, `telemetry.py`, `workers.py`; the results files are
`results/*.json`.

## What was executed

`heavy1` with 121500 paired seeds plus the estimand-split, order-effect and replication campaigns
recorded in `results/`.

## Raw data

Full sha256 manifest: `evidence_files.sha256` (result JSON; the per-generation `*.npz` dumps are
excluded as dataset dumps).

## Analysis

`estimand_split.py`, `verify_estimand_split.py`, `summarize.py`, `red_team_causal_decomposition.py`.

## Result

A verified instrument claim (bit-exact independent recompute; fit health rank 172/172) with an
estimator-sensitive headline number; two-fold cost is a negative (see `sex_cost/`).

## What this does NOT show

No conceptual novelty for "estimand mismatch != misspecification", and no unlabelled `64.1` per cent
number may be quoted.

## Replay

`python causal-tape-experiment/heavy1.py` (see `RESULTS.md` for the exact invocation)

## References

* `NOVELTY_VERDICT.md` (in this directory) and its dated URLs

