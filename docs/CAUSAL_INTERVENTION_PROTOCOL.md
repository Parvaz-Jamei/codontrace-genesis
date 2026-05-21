# Causal Intervention Protocol

CodonTrace distinguishes event association from intervention-backed evidence. `EventGraph` records temporal association and predictive support; it is not a causal proof by itself.

## What it implements

The causal protocol supports:

- temporal event association through `EventGraph`
- predictive probes with lag, controls, sample count, and status
- intervention scenarios with paired seeds
- intervention results with effect size and confidence interval fields
- ground-truth benchmark worlds for limited recovery tests

## What it does not claim

Pairwise Granger-like or predictive probes do not establish mechanistic causality. PCMCI/conditional predictive backends, when available, still do not provide intervention evidence. ClaimGate may only allow `intervention_supported` when an executed `InterventionResult` exists and the evidence status is not `not_run`.

## Runtime hooks

Causal validation is post-run or benchmark-run library logic. It must not alter organism decisions inside the simulation hot loop.

## Artifacts

Manifests record `event_graph_digest`, `predictive_probe_digest`, `intervention_protocol_digest`, `intervention_result_digest`, and protocol statuses. `not_run` digests do not count as evidence.

## Tests

Tests cover EventGraph compatibility, predictive probe audit fields, overclaim rejection, intervention-required claims, and known ground-truth worlds.
