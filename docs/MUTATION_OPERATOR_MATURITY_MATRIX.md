# GENESIS Mutation Operator Maturity Matrix

**Status:** Phase 1 strong-core artifact
**Purpose:** separate birth-level mutation operators from structural genome mutation families and future learning-guided mutation paths.

The birth module exposes a broad mutation vocabulary for ambitious digital evolution experiments. Structural mutation is a narrower implementation family. These two layers must not be confused.

| Operator | Family | Location | Genome length | Codon content | ADF/macro | Capsule/partner | Learning state | Replay policy | Maturity |
|---|---|---|---:|---:|---:|---:|---:|---|---|
| `point_flip` | birth-level | `birth.py` | no | yes | no | no | no | mutation plan digest | pilot_effective |
| `point_substitution` | birth-level | `birth.py` | no | yes | no | no | no | mutation plan digest | partial |
| `insert_codon` | birth-level | `birth.py` | yes | yes | no | no | no | mutation plan digest | pilot_effective |
| `delete_codon` | birth-level | `birth.py` | yes | yes | no | no | no | mutation plan digest | pilot_effective |
| `duplicate_segment` | birth-level | `birth.py` | yes | yes | no | no | no | mutation plan digest | partial |
| `delete_segment` | birth-level | `birth.py` | yes | yes | no | no | no | mutation plan digest | partial |
| `transpose_segment` | birth-level | `birth.py` | no/yes | yes | no | no | no | mutation plan digest | partial |
| `invert_segment` | birth-level | `birth.py` | no | yes | no | no | no | mutation plan digest | partial |
| `copy_segment` | birth-level | `birth.py` | yes | yes | no | no | no | mutation plan digest | partial |
| `recombine_with_capsule` | recombination | `birth.py` / capsule evidence | possible | possible | no | capsule | no | capsule + mutation digest | scaffold |
| `recombine_with_partner` | recombination | `birth.py` / population evidence | possible | possible | no | partner | no | partner + mutation digest | scaffold |
| `repair_invalid_region` | validity repair | `birth.py` | possible | yes | no | no | no | validation digest | partial |
| `macro_mutation` | ADF/macro | `birth.py` / `adf_runtime.py` | possible | possible | yes | no | no | macro source-map digest | partial |
| `semantic_mutation` | semantic/learning-guided | `birth.py` / learning hooks | possible | possible | possible | no | possible | source evidence digest | scaffold |
| `neutral_drift_mutation` | birth-level | `birth.py` | possible | possible | no | no | no | mutation plan digest | pilot_effective |

## Acceptance rules

- Birth success must not be injected artificially.
- Non-birth must produce a gate reason.
- Same seed must produce stable mutation evidence.
- Different seed should be able to produce different mutation paths.
- Child lineage digest must remain stable across processes.
- Learning inheritance must expose enabled/disabled/blocked status.
