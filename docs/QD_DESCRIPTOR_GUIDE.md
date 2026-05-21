# QD Descriptor Guide

Quality-Diversity in CodonTrace uses explicit descriptor schemas. Descriptors are experiment-defined measures, not universal life metrics.

## What it implements

`DescriptorSpec` and `DescriptorSchema` define descriptor names, source, range, bins, normalization, and digest. Phase 1/2 descriptors include survival, energy efficiency, resource gain, blocked ratio, capsule usage, lineage depth, genome length, unique positions, and action entropy. Optional descriptors include causal accuracy, substrate interaction, translation profile diversity, and ADF usage.

## Active vs passive QD

Passive QD updates an archive and reports coverage. Active QD requires archive/novelty feedback to affect parent selection or reproduction. ClaimGate downgrades to `qd_reporting_supported` when parent-selection feedback is absent.

## Replay and artifacts

Descriptor schemas, QD archive digests, scheduler state digests, ask/evaluate/tell records, and QDCandidate genome digest status must be artifacted. Inline `genome_bits` must verify against `genome_digest`.

## Tests

Tests cover descriptor digest validation, missing descriptor policy, QDCandidate object shape, ask/evaluate/tell, replay state, and active QD claim gating.
