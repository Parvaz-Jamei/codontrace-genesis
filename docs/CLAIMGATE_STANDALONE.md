# ClaimGate standalone auditor

Wave 2 only. CodonTrace Genesis ships a **simulator-agnostic evidence
auditor** that grades *claims given evidence*. It does not run the
Genesis engine, loosen CLAIMS.md §5 + §8, or publish a numeric
“validation score.”

```bash
python -m codontrace.claimgate audit bundle.json
```

```python
from codontrace.claimgate import audit_bundle
from codontrace.claimgate.adapters.codontrace import bundle_from_hard_experiment_01

report = audit_bundle(bundle_from_hard_experiment_01())
print(report.achieved_level, report.public_name, report.missing_for_next)
```

`achieved_level` is the public 0–5 ladder in [`CLAIM_LADDER.md`](CLAIM_LADDER.md).
HARD_EXPERIMENT_01 v2 (`docs/hard_experiment_01/results_v2.json`) is an
interpretable null: the auditor returns **`runtime_observation` / public
level 1**, the same ceiling ClaimGate granted on `main`.

## What the auditor is

- A `claimgate_bundle_v1` schema plus `audit_bundle(bundle) -> ClaimAuditReport`.
- Adapters: complete CodonTrace Genesis (`HardExperiment01Campaign` /
  `results_v2.json`); **skeletons** for Avida `.dat` and MABE2 DataFile CSV.
- Import-isolated from `engine` / `population` (AST-enforced).

## What it is not

- Not a universal validation score (see ASME V&V 40 below).
- Not an OEE or Tokyo Type 1 pass from metrics.
- Not full Avida or MABE2 support.
- Not Wave 3, a tag, a PyPI release, or Phase M+.

## Neighbors and complements (not substitutes)

| Neighbor | Role relative to ClaimGate |
|---|---|
| **ASME V&V 40** | Credibility is *context-of-use / risk-informed*. ClaimGate grades claims given evidence. Complementary, not a numeric score. |
| **MODES (Dolson et al. 2019)** | Measurement procedure for novelty / change / complexity after a persistence filter. Measurement ≠ claim pass. |
| **Channon 2024 Tokyo Type 1** | Measurement-step vocabulary. CodonTrace Genesis may record steps; ClaimGate must **not** auto-grant `tokyo_type1_passed`. |
| **Avida `.dat` / MABE2 DataFile** | Ingest skeletons so foreign run artifacts can be wrapped as bundles. Arm mapping is user-supplied. |

Design notes: [`design/AVIDA_DAT.md`](design/AVIDA_DAT.md),
[`design/MABE2_DATAFILE.md`](design/MABE2_DATAFILE.md),
[`design/ASME_VV40_CONTEXT_OF_USE.md`](design/ASME_VV40_CONTEXT_OF_USE.md),
[`design/MODES_CHANNON_MEASUREMENT_NEIGHBORS.md`](design/MODES_CHANNON_MEASUREMENT_NEIGHBORS.md),
[`design/HARD_EXPERIMENT_01_V2_NULL.md`](design/HARD_EXPERIMENT_01_V2_NULL.md).

Forbidden aliases (`intelligence`, `collective_intelligence`, AGI,
`tokyo_type1_passed`, `avida_replacement`, …) are unchanged. Example:
[`examples/claimgate_audit_hard_experiment_01.py`](../examples/claimgate_audit_hard_experiment_01.py).
