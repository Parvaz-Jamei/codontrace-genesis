# Discovery Gate Protocol

Discovery in CodonTrace is a review-needed evidence pipeline. It is never a proof of open-ended evolution or artificial life.

## What it implements

A discovery candidate must pass structured gates before its claim level can increase:

1. candidate detection
2. executable D0 baseline
3. shadow/control run
4. persistence over ticks/generations
5. lineage persistence
6. multi-seed repeatability
7. ablation matrix
8. QD novelty check
9. replay verification
10. LLM/human review status outside the hot loop

## Claim levels

Allowed statuses include `metadata_only`, `candidate`, `reproducible_candidate`, `supported_by_ablation`, and `experimentally_supported_candidate`. Forbidden outputs include “proved artificial life,” “proved open-ended evolution,” and “autonomous discovery proof.”

## Artifacts

Discovery artifacts must link to manifest digests, replay digests, benchmark scenario digests, D0/shadow/ablation result digests, and review status.

## Tests

Tests require D0, shadow, persistence, ablation, replay, and ClaimGate downgrade behavior.
