# GENESIS Scientific Claim Ladder

**Collapsed.** Use [`CLAIM_LADDER.md`](CLAIM_LADDER.md) for the public
0–5 ladder and [`CLAIM_LADDER_MAP.md`](CLAIM_LADDER_MAP.md) for the nine
internal rungs. Policy remains [`CLAIMS.md`](../CLAIMS.md) §5 + §8.

```python
from codontrace.genesis import evaluate_strong_claim_ladder

result = evaluate_strong_claim_ladder(
    "digital_evolution_claim",
    {"schema_version": True, "artifact_digest": True, "runtime_records": True},
)
print(result.achieved_level, result.public_level, result.missing_for_target)
```

Internal rungs are still cumulative. `public_level` is the CLAIMS.md §5
integer from the map. It does not unlock claims.
