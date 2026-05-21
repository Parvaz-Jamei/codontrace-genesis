# GENESIS causal/capsule runtime integration

CodonTrace phase 2 connects existing GENESIS primitives into an auditable runtime path:

```text
Organism action → optional memory event → causal graph update → optional capsule/nexus transfer → population metrics
```

## What `CausalGraph` is in this version

`CausalGraph` is a bounded, deterministic evidence graph attached to an organism when the caller opts in. It stores lightweight action/outcome evidence, local prediction edges, ATP-learning accounting, and digest-before/digest-after audit fields.

It is not Pearl-grade causal discovery, not scientific proof of causal intelligence, and not a full discovery detector.

## Memory → causal update

When an organism has `episodic_memory`, a successful memory write produces an event reference that can be used by the causal update helper. When memory is disabled, the causal update can still use the current action result directly. Causal updates spend `ATP_learning` and fail with an explicit reason when learning ATP is unavailable.

## Lightweight prediction

`predict_next_outcome()` reuses existing `predicts_local` edges to make a deterministic local prediction for the next action. `evaluate_prediction()` records whether the observed outcome matched. This is a scaffold-level evidence helper, not full causal discovery.

## Capsule adoption in this version

Capsule emission/read/adoption is connected to the population loop when `CapsuleTransferConfig.enabled=True` and Nexus stigmergy is enabled. Adoption is deterministic and bounded by local radius, read limits, confidence thresholds, and `ATP_learning` cost.

This is scaffold-level capsule adoption, not full uncertainty-reducing MDL graph merge.

## Nexus stigmergy

`EMIT_NEXUS` still keeps the backward-compatible world object behavior, and the population path can also deposit a capsule-backed signal into `NexusStigmergyLayer`. Nearby organisms read through `CapsuleStore.nearby(position, radius)`, so locality is explicit.

## LLM role

LLM integration is API-mediated and review/rule-proposal oriented. The LLM must interact through CodonTrace-defined request/response schemas and validators. It must not control organism decisions inside the simulation hot loop, and it must not mutate core state outside approved library APIs.

## Remaining non-claims

This phase does not implement full causal discovery, MDL graph surgery, open-ended intelligence, UI, or an LLM agent inside the tick loop.
