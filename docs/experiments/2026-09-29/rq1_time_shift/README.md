# Rq1 Time Shift - experiment record, 2026-09-29

This directory is the archived experiment record: design, protocol, raw data and result together.
All paths below are relative to `docs/experiments/2026-09-29/rq1_time_shift/`.

**Files in this record:** 96 (excluding any tarball listed as excluded).
**Raw-data manifest:** `evidence_files.sha256` (one `sha256  size  path` line per file).

## Question and hypothesis

Does a delayed antagonist adapt to the recently common host genotype, or is the observed pattern
only a directional arms race? Primary quantity: the host-time x antagonist-time interaction in
realised contact pressure `pi_realised`, not a match rate.

## Design

Cross-time 3x3 matrix built **outside evolution** from archived per-generation class tables of the
`StructuralRQArm` route; arms and controls as recorded in `design.md` (contemporaneous, lagged,
frozen-parasite, host-only, shuffled time labels). The locked thresholds `0.20` and `-0.148` were
not recomputed and not changed. Seed blocks: development, pilot and the sealed confirmatory seeds
(5701-5708 for the confirmatory pack; campaign seeds 801-816 stay sealed and no raw outcome for
them is included here).

## Protocol and provenance

Harness and digests are recorded in `run_manifest.json` and `raw/`; the design is reproduced
verbatim in `design.md` and the prior-art bound in `prior_art.md`.

## What was executed

Pilot plus a partial confirmatory pack: 2 of 8 sealed seeds analysed, interval containing zero at
n = 2.

## Raw data

Full sha256 manifest: `evidence_files.sha256`.

## Analysis

`analysis_rq1.py`; derived summary `analysis.json` and `effect_table.json` are built from the raw
JSONL only.

## Result

`INCONCLUSIVE`, in flight. `hypothesis_supported = false`, `red_queen_proved = false`.

## What this does NOT show

It is not a supported Red Queen result, not a trend, and not near-threshold. Time-shift as an assay
is prior art (Decaestecker et al. 2007).

## Replay

`python test-runs/rq1/replay_rq1.py --from-manifest run_manifest.json`

## References

* Decaestecker et al., *Nature* 450, 870-873 (2007) - https://doi.org/10.1038/nature06291

