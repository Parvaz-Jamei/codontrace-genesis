# Biomedical engineering interface (honest scope)

CodonTrace Genesis is **not** a medical device, SaMD, SiMD, IVD, or ASME V&V 40
implementation. It does not diagnose, treat, or certify a clinical model.

What it can do for biomedical *engineering* is the same thing it does for
digital evolution: refuse to let a written claim outrun the evidence bundle.

Equipment-adjacent work uses the **same** `DomainProfile` port. Declaring
`simd_declared` (software in a medical device) or `samd_declared` records
IMDRF language. It does not classify a product.

## Map to ASME V&V 40-2018 and FDA 2023 CM&S (complement, not substitute)

| Standard concept | ClaimGate analog | What this repo does **not** do |
|---|---|---|
| Question of interest (QOI) | `extra.question_of_interest` | Answer the clinical question |
| Context of use (COU) | `extra.context_of_use` | Approve a regulatory COU |
| Model influence | `extra.model_influence` (1–3, user-declared) | Measure influence on a real decision |
| Decision consequence | `extra.decision_consequence` (1–3, user-declared) | Estimate patient harm |
| Model risk | `extra.model_risk = max(influence, consequence)` | A numeric V&V 40 risk grade |
| FDA 2023 evidence cats 1–8 | `extra.fda_2023_evidence` (declared subset) | Collect or grade VVUQ evidence |
| IEC 62304 A/B/C | `extra.iec_62304_class` (declared) | Software safety classification |
| IMDRF N12 I–IV | `extra.imdrf_n12_category` (declared) | SaMD risk categorization |
| SiMD vs SaMD | `extra.device_software_kind` | Device file, 510(k), CE, or MDSW |
| Credibility vs risk | public ladder 0–5 on the *claim* | A credibility score for the *model* |

FDA 2023 Table 2 categories recorded as labels: (1) code verification,
(2) model calibration, (3) bench-test validation, (4) in vivo validation,
(5) population-based validation, (6) emergent behaviour, (7) model
plausibility, (8) calculation verification / UQ on COU simulations.
Cats 1, 3, and 4 overlap ASME V&V 40. The 2023 guidance applies to
**physics-based or mechanistic** models, not standalone ML. If
`physics_based=False`, `fda_2023_scope` is `out_of_scope_standalone_ml`
even if categories are declared.

ASME VVUQ 40.1-2026 is a worked tibial-tray *example*, not a pass bit.
IMDRF N81 (2025) characterizes medical-device software including
embedded software; this port stores characterization labels only.

Risk fields are **labels supplied by the user**. The auditor does not infer
them from AUROC, sensitivity, or a hospital log. Declaring evidence
categories does **not** raise the ClaimGate ladder.

## Blocked biomedical claims

These strings must not be treated as earned by a passing audit:

- `medical_device`, `samd_certified`, `simd_certified`, `fda_cleared`, `ce_marked`
- `clinical_validated`, `asme_vv40_passed`, `vvuq_40_1_passed`, `patient_safe`
- `iec_62304_certified`, `imdrf_n81_passed`, `in_silico_trial_validated`, `digital_twin_certified`
- any diagnosis / treatment performance claim

A high ClaimGate level on a toy or retrospective table is still only a claim
grade. It is not clinical validity.

## How to use

```python
from codontrace.claimgate import audit_bundle
from codontrace.claimgate.adapters.biomedical import bundle_from_device_model_cou

bundle = bundle_from_device_model_cou(
    question_of_interest="Would this bench-like score table license a worst-case size pick?",
    context_of_use="Synthetic table only; no ISO 14879-1 test; no implant.",
    model_influence=2,
    decision_consequence=3,
    treatment_scores=(0.12, 0.11, 0.13),
    control_scores=(0.20, 0.19, 0.21),
    device_software_kind="simd_declared",
    iec_62304_class="B",
    imdrf_n12_category="II",
    fda_2023_evidence=(1, 3, 8),
    physics_based=True,
)
report = audit_bundle(bundle)
print(report.achieved_level, bundle.extra["model_risk"], bundle.extra["fda_2023_scope"])
```

That call is the negative control: regulatory labels and no execution bundle.
`audit_bundle` returns `0` because `artifact_manifest` is missing. It is not
a display fixture. HE01 `docs/hard_experiment_01/results_v7.json` is the
positive control. Its file label stays `intervention_supported` (internal
map: public 3, and the name alone does not promote). `audit_bundle` on that
file returns `4` (`replicated_effect`): replay, intervention, an interval,
and 30 seeds are in the bundle. Level 5 still needs an archived DOI.

See `examples/claimgate_audit_biomedical_toy.py`.
The toy numbers are synthetic. They are not a clinical study or a device test.

## Executable worksheet (PIRT + weakest submodel)

Two checks from outside this field, wired as a port and not as a second engine:

- **PIRT** (phenomena identification and ranking), used in nuclear safety
  (OECD/NEA). Each phenomenon has an importance (`low` / `medium` / `high`)
  and a knowledge rank (`none` / `partial` / `adequate`). High importance
  stays an open gap until knowledge is adequate. Low importance is screened
  out. The ranks are declared by the user; the port does not discover physics.
- **Weakest-submodel cap**, the building-block rule from aerospace VVUQ and
  the hierarchical in-silico trial layout (device, patient, coupled, cohort,
  clinician, outcome map, or an executed non-device `campaign`). The coupled ceiling is the minimum usable level
  of the recorded submodels, and only when a study has executed every
  submodel. A non-identifiable submodel cannot contribute
  above 1. Evidence that is only calibration, plausibility, or emergent
  behaviour (FDA 2023 categories 2, 6, 7) cannot contribute above 2.

`audit_bundle` is not called by the worksheet and its public level does not
move. `raises_claim_ladder` is false. Strings such as `asme_vv40_passed`
remain `ConfigurationError`.

```python
from codontrace.claimgate.adapters.biomedical import (
    attach_credibility_worksheet,
    bundle_from_device_model_cou,
)

bundle = bundle_from_device_model_cou(
    question_of_interest="Which recorded gap blocks a coupled claim?",
    context_of_use="Declared worksheet only; no implant.",
    model_influence=2,
    decision_consequence=3,
    treatment_scores=(0.12, 0.11, 0.13),
    control_scores=(0.20, 0.19, 0.21),
    device_software_kind="simd_declared",
    physics_based=True,
)
annotated = attach_credibility_worksheet(
    bundle,
    phenomena=(
        {"name": "contact_stress", "importance": "high", "knowledge": "partial"},
    ),
    submodels=(
        {"name": "device_fea", "role": "device", "level": 3, "evidence_categories": (1, 3)},
        {"name": "patient_geometry", "role": "patient", "level": 1, "evidence_categories": (4,)},
    ),
)
print(annotated.extra["credibility_worksheet"]["coupled_ceiling"])
```

See `examples/claimgate_biomedical_worksheet.py`.

## Study file: executed run versus a declared rank

`audit_biomedical_study_file` reads a JSON study. A phenomenon closes only
when its arm is the treatment side of a comparison that has an interval,
`audit_bundle` is at least 4, and replay is verified. One arm closes one
phenomenon. If `max_interval_width` is set, that treatment contrast must
be no wider: a significant interval can still be too wide for the question.
Typing `knowledge: adequate` does not close the row. An arm that is present
but fails those checks is `not_closed`, not a declaration. A submodel is
`executed` only on that same bar. Two submodels that share a config digest
are one run, not two. A typed level with no bundle is capped at 2.
`coupled_ceiling` is filled only when every submodel cleared that bar on
its own run.

`examples/studies/he01_phenomena.json` points at
`docs/hard_experiment_01/results_v7.json`, a life-loop campaign, not a
device model. The source-bias treatment arm closes. Contact stress and
the patient submodel stay declared, so there is no measured coupled
ceiling. The claim ladder is the campaign's own grade. The study does
not raise it. The committed copy is
`docs/claimgate/biomedical_study.json`.

## Risk bar (commensurate evidence, not a second grade)

ASME V&V 40 asks for evidence commensurate with model risk. This port
makes that check executable and keeps it off the ladder. Risk is
`max(model_influence, decision_consequence)` on the declared 1–3 labels.
The required public level is 2, 3, or 4 for risk 1, 2, or 3. From risk 2
up, an open `pirt:` gap also blocks. The numbers are this implementation,
not an FDA table and not a certificate.

`docs/claimgate/risk_bar.json` is the live result. The device-score table
is risk 3 at level 0 and does not meet the bar. HE01 stays at level 4:
it meets risk 3 when the only listed phenomenon is the executed treatment
arm, and it does not meet risk 3 when contact stress is listed with no arm.
Declaring the risk does not lower the campaign grade.

```python
from codontrace.claimgate.adapters.biomedical import biomedical_risk_bar_payload

print(biomedical_risk_bar_payload()["rows"])
```

```python
from codontrace.claimgate.adapters.biomedical import audit_biomedical_study_file

study = audit_biomedical_study_file("examples/studies/he01_phenomena.json")
print(study.claim_level, study.worksheet.open_gaps, study.worksheet.coupled_ceiling)
```


