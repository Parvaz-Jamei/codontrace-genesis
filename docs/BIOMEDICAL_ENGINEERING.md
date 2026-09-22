# Biomedical engineering interface (honest scope)

CodonTrace Genesis is **not** a medical device, SaMD, IVD, or ASME V&V 40
implementation. It does not diagnose, treat, or certify a clinical model.

What it can do for biomedical *engineering* is the same thing it does for
digital evolution: refuse to let a written claim outrun the evidence bundle.

## Map to ASME V&V 40-2018 (complement, not substitute)

| V&V 40 concept | ClaimGate analog | What this repo does **not** do |
|---|---|---|
| Question of interest (QOI) | `extra.question_of_interest` | Answer the clinical question |
| Context of use (COU) | `extra.context_of_use` | Approve a regulatory COU |
| Model influence | `extra.model_influence` (1–3, user-declared) | Measure influence on a real decision |
| Decision consequence | `extra.decision_consequence` (1–3, user-declared) | Estimate patient harm |
| Model risk | `extra.model_risk = max(influence, consequence)` | A numeric V&V 40 risk grade |
| Credibility vs risk | public ladder 0–5 on the *claim* | A credibility score for the *model* |

Risk fields are **labels supplied by the user**. The auditor does not infer
them from AUROC, sensitivity, or a hospital log.

## Blocked biomedical claims

These strings must not be treated as earned by a passing audit:

- `medical_device`, `samd_certified`, `fda_cleared`, `ce_marked`
- `clinical_validated`, `asme_vv40_passed`, `patient_safe`
- any diagnosis / treatment performance claim

A high ClaimGate level on a toy or retrospective table is still only a claim
grade. It is not clinical validity.

## How to use

```python
from codontrace.claimgate import audit_bundle
from codontrace.claimgate.adapters.biomedical import bundle_from_biomedical_cou

bundle = bundle_from_biomedical_cou(
    question_of_interest="Would this in-silico AUROC support a screening claim?",
    context_of_use="Retrospective table only; no bedside use.",
    model_influence=2,
    decision_consequence=3,
    treatment_scores=(0.71, 0.68, 0.73),
    control_scores=(0.50, 0.52, 0.49),
)
report = audit_bundle(bundle)
print(report.achieved_level, bundle.extra["model_risk"])
```

See `examples/claimgate_audit_biomedical_toy.py`.
The toy numbers are synthetic. They are not a clinical study.
