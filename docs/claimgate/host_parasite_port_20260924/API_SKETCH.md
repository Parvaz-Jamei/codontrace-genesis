# API sketch — `host_parasite` DomainProfile

Status: **partially implemented** in this PR (profile + thin adapter + tests).
Infection physics and `HostParasiteEnv` are **not** implemented.

## Profile name

- Preferred: `host_parasite`
- Alias discussion: `microbe_virus` (not registered in MVP; avoid dual names)

```python
from codontrace.claimgate import HOST_PARASITE, PROFILES
assert PROFILES["host_parasite"] is HOST_PARASITE
```

## Blocked claims (fail closed)

```text
vaccine_efficacy_proved
antiviral_therapy_validated
clinical_pathogen_model
epidemic_forecast_certified
phage_therapy_cleared
virulence_optimized_for_humans
biosafety_level_certified
intelligence
collective_intelligence
agi
tokyo_type1_passed
avida_replacement
```

Blocked set also reuses ALife intelligence / Avida-replacement aliases so this
port cannot be used to launder those overclaims.

## Adapter surface (thin, mirrors biomedical)

Module: `codontrace.claimgate.adapters.host_parasite`

| Symbol | Role |
|---|---|
| `BLOCKED_HOST_PARASITE_CLAIMS` | `frozenset` mirror of profile blocks |
| `assert_claim_allowed(claimed)` | normalize + raise `ConfigurationError` if blocked |
| `bundle_from_host_parasite_cou(...)` | wrap declared scores via `bundle_from_declared_scores(profile=HOST_PARASITE, ...)` |

Docstring contract: **DomainProfile port, not a second engine / not clinical.**

### Example

```python
from codontrace.claimgate.adapters.host_parasite import (
    assert_claim_allowed,
    bundle_from_host_parasite_cou,
)

assert_claim_allowed("runtime_observation")  # ok

bundle = bundle_from_host_parasite_cou(
    question_of_interest="Does task-overlap raise infection-eligible contacts?",
    context_of_use="Synthetic digital scores only. No wet lab. No clinic.",
    model_influence=2,
    decision_consequence=2,
    treatment_scores=(0.4, 0.38, 0.42),
    control_scores=(0.2, 0.22, 0.19),
    metric="task_overlap_toy",
)
# bundle.extra["domain"] == "host_parasite"
# bundle.extra["infection_physics"] == "not_implemented"
```

Clinical aliases raise:

```python
bundle_from_host_parasite_cou(..., claimed="phage_therapy_cleared")
# ConfigurationError
```

## Optional later hooks (NOT implemented)

Sketch only — do not treat as present API:

```python
# FUTURE — HostParasiteEnv (not in this PR)
class HostParasiteEnv:
    """Optional env wrapper; must not live inside engine.py tick core."""

    def infection_eligible(self, host_tasks, parasite_tasks) -> bool:
        """Task-overlap rule (Fortuna et al. 2021) — future."""

    def steal_cpu_fraction(self) -> float:
        """Obligate resource draw; literature ~0.8 in Avida parasites — future."""

    def transmission_mode(self) -> str:
        """horizontal | vertical | mixed — Symbulation continuum — future."""

    def content_null_parasite_payload(self) -> bytes:
        """HE02-style shuffle control — future campaign wiring."""
```

ClaimGate remains the evidence auditor; the env would only produce scores /
artifacts for adapters to wrap.

## COU / risk labels (declared only)

Same stance as biomedical:

- `asme_vv40`: `complement_only`
- `fda_2023`: `declared_labels_only`
- `certification`: `none`
- `clinical_scope`: `blocked`
- `infection_physics`: `not_implemented`

## Tests

`tests/test_claimgate_host_parasite.py` — profile registration, domain label,
parametrized blocked aliases, `assert_claim_allowed`, independence from
`biomedical` domain string.
