# API sketch — `host_parasite` DomainProfile

Status: **Phase 1 complete** (profile + hardened adapter + declared intervention menu stub + tests).
Infection physics and `HostParasiteEnv` remain Phase 2+; not in engine core.

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
crispr_identity_proved
crispr_therapy_validated
red_queen_proved
major_transition_proved
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
| `DECLARED_INTERVENTION_KINDS` | allowed digital falsification hook kinds |
| `assert_claim_allowed(claimed)` | normalize + raise `ConfigurationError` if blocked |
| `declared_cou_risk_labels(...)` | merge/validate declared COU risk labels |
| `declared_intervention_menu(...)` | schema stub for later falsification planning |
| `attach_declared_intervention_menu(...)` | store menu on a host_parasite bundle only |
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

## Optional HostParasiteEnv (Phase 2 — outside engine core)

Module: `codontrace.genesis.host_parasite_env` (does **not** import or modify
`engine.py`).

```python
from codontrace.genesis.host_parasite_env import (
    HostParasiteEnv,
    dual_null_template,
    run_dual_null_contrast,
)

env = HostParasiteEnv(steal_fraction=0.8, transmission_mode="horizontal")
env.add_host("H0", ("nand", "and"))
env.try_horizontal_inject(
    host_id="H0", parasite_id="P0", parasite_tasks=("and",), payload=(1, 2)
)
contrast = run_dual_null_contrast(
    host_tasks=("nand", "and"),
    parasite_tasks=("and", "or"),
    payload=(1, 2, 3),
)
assert contrast["nulls_change_outcomes"] is True
```

ClaimGate remains the evidence auditor; the env only produces digital toy
scores / snapshots for adapters to wrap. Vertical transmission physics stay
labeled `not_implemented`.

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
