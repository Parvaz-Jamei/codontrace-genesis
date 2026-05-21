# GENESIS Scientific Claim Ladder

**Status:** Phase 1 strong-core artifact
**Purpose:** connect ambitious claims to increasingly strong evidence without weakening the project vision.

GENESIS is designed to support serious claims in AI, digital evolution, causal trace, discovery, memory, tool-use, and multi-agent behavior. The right policy is not to delete strong claims. The right policy is to require evidence strong enough for each level.

## Public API

```python
from codontrace.genesis import evaluate_strong_claim_ladder

result = evaluate_strong_claim_ladder(
    "digital_evolution_claim",
    {
        "schema_version": True,
        "artifact_digest": True,
        "runtime_records": True,
        "pilot_run": True,
        "negative_control": True,
    },
)
print(result.achieved_level, result.missing_for_target)
```

## Levels

| Level | Meaning | Typical evidence |
|---|---|---|
| `metadata_only` | claim text is known but runtime evidence is not present | schema metadata |
| `instrumented_runtime` | public runtime records and artifact digests exist | schema, artifact digest, runtime records |
| `pilot_supported` | small pilot confirms the surface works | pilot artifact, runtime trace |
| `control_supported` | negative/control baseline is present | negative control, control digest |
| `ablation_supported` | ablation witness exists | ablation result and digest |
| `multi_seed_supported` | statistics are not single-run only | seed protocol, effect size, confidence interval |
| `heldout_supported` | train/eval separation is represented | heldout protocol, leakage check |
| `intervention_supported` | causal/intervention evidence exists | baseline/treatment/intervention digests |
| `claim_ready_research_alpha` | all above are present plus replay and ClaimGate digest | replay verification and claim gate decision digest |

## Rule

A large claim is not rejected because it is ambitious. It is mapped to the strongest **cumulative** level supported by evidence. Levels are not skippable: `intervention_supported` requires every lower layer, including schema, artifact digest, runtime records, pilot support, controls, ablation, multi-seed statistics, and heldout evidence. Missing evidence becomes an actionable next engineering target, not defeatist wording.
