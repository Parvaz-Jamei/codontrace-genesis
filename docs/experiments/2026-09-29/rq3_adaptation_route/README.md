# Rq3 Adaptation Route - experiment record, 2026-09-29

This directory is the archived experiment record: design, protocol, raw data and result together.
All paths below are relative to `docs/experiments/2026-09-29/rq3_adaptation_route/`.

**Files in this record:** 95 (excluding any tarball listed as excluded).
**Raw-data manifest:** `evidence_files.sha256` (one `sha256  size  path` line per file).

## Question and hypothesis

Does the apparent cycle require heritable antagonist feedback? The bare `S < -0.20` statistic is not
the outcome; the outcome is the composition of (a) the rare-ness effect on growth and (b) later
pressure on the previously common genotype.

## Design

Arms: `coevolve`, fixed-composition antagonist paying real contact and energy cost,
`shuffled_labels` (roster re-drawn each generation from the ancestral window pool with offspring
windows permuted against the parents that earned the energy) and absent. All arms share the same
maintenance value. Locked thresholds, the `0.20` floor and the `-0.148` magnitude barrier were not
recomputed or changed.

## Protocol and provenance

`PROPOSED_CHANGE.patch` and `PROPOSED_CHANGE_3.patch` are the handed patches; the underlying
mechanism is `AntagonistPopulation` (per-unit identity, heritable windows, realised per-seat income,
strict starvation death, seat-cap selection, no top-up). Provenance fields are in
`run_manifest.json`.

## What was executed

Mechanism fixtures plus the copassaged seed-43 50-generation regression; the confirmatory arm
comparison as recorded in the pack. Campaign seeds 801-816 remain sealed, with no raw outcome here.

## Raw data

Full sha256 manifest: `evidence_files.sha256`.

## Analysis

`rq3_analyze.py` and `rq3_harness.py` over the raw JSONL only.

## Result

`SUPPORTED_IN_MODEL` with the small-effect caveat recorded in `decision.md` (one contrast seed, no
interval); `hypothesis_supported` and `red_queen_proved` remain `false` at campaign level.

## What this does NOT show

It does not establish a nature-level Red Queen, and the effect size is small; the mechanism is
measurement machinery whose admissible difference is the label-shuffled control, not a novelty
claim.

## Replay

`python test-runs/rq3/rq3_harness.py`; patch evidence `out_verify3.txt`.

## References

* "An experimental test of parasite adaptation to common versus rare host genotypes", *Biol. Lett.*
  16, 20200210 (2020) - https://doi.org/10.1098/rsbl.2020.0210
* "Runaway coevolution: adaptation to heritable and nonheritable environments", *Evolution* 68
  (2014) - https://doi.org/10.1111/evo.12470

