# Applied medical evidence suite (2026-09-24)

**New evidence only.** This folder does **not** replace or rewrite:

- `docs/hard_experiment_01/results_v7.json`
- `docs/claimgate/risk_bar.json`
- `docs/claimgate/biomedical_study.json`

Those pins stay the BAIC / paper anchors. This suite shows how the existing
ClaimGate **biomedical DomainProfile port** behaves on well-known credibility
failure modes in computational modeling for medical devices — without claiming
FDA clearance, ASME V&V 40 pass, SaMD certification, or clinical validity.

## What this is / is not

| Is | Is not |
|---|---|
| Methodological stress tests of claim–evidence fit | A clinical study |
| Mapped to FDA 2023 CM&S + ASME V&V 40 language | An FDA submission package |
| Fail-closed checks (overclaim, ML-out-of-scope, weak submodel, width gate) | Proof of collective intelligence or medical AI |
| Reproducibility check that live `risk_bar` still matches the committed pin | A device certificate |

## Literature problems (short)

1. **Risk / COU mismatch** — evidence not commensurate with model risk (FDA 2023; ASME V&V 40-2018).
2. **Standalone ML out of CM&S scope** — FDA 2023 CM&S targets physics/mechanistic models, not standalone AI/ML.
3. **Right answer for the wrong reason** — population-only validation without hierarchical submodel credibility (Pathmanathan et al., PLOS Comp Biol 2024; Frontiers 2024 ISCT hierarchy).
4. **Calibration ≠ validation** — FDA evidence categories 2 / 6 / 7 (calibration, emergent behaviour, plausibility) must not be treated as full validating evidence.
5. **Certification language without a regulatory process** — blocked claim strings in the biomedical port.
6. **Adequacy vs decision thresholds** — a statistically significant interval can still be too wide for the question of interest (FDA post-study adequacy).

## Citations (primary)

- FDA (2023). *Assessing the Credibility of Computational Modeling and Simulation in Medical Device Submissions* (final guidance). https://www.fda.gov/media/175363/download
- ASME V&V 40-2018. *Assessing Credibility of Computational Modeling through Verification and Validation: Application to Medical Devices*.
- Pathmanathan et al. (2024). Credibility assessment of in silico clinical trials for medical devices. *PLOS Computational Biology*. https://doi.org/10.1371/journal.pcbi.1012289
- Frontiers in Medicine (2024). Toward trustworthy medical device in silico clinical trials: a hierarchical framework… https://doi.org/10.3389/fmed.2024.1433372
- Federal Register notice of FDA CM&S guidance availability (2023-11-17).

## Suite results

See `suite_results.json` and `SUMMARY.md`.

| ID | Result | Maps to |
|---|---|---|
| T1 | PASS | High-risk declared table, no execution → level 0, risk bar fails |
| T2 | PASS | Standalone ML → `out_of_scope_standalone_ml` |
| T3 | PASS | Weakest-submodel + open PIRT gaps; ladder not raised |
| T4 | PASS | Cats 2/6/7 only → usable cap 2 + `supporting_evidence_only` |
| T5 | PASS | All blocked certification strings raise `ConfigurationError` |
| T6 | PASS | Typed `knowledge: adequate` without arm stays `declared_only` |
| T7 | PASS | Fresh `biomedical_risk_bar_payload()` rows match committed pin |
| T8 | PASS | Tight `max_interval_width` blocks closing even with HE01 contrast |

**8/8 PASS.** Code unchanged. Prior evidence digests unchanged at suite run time.

## How to re-run (read-only on pins)

From a checkout with `PYTHONPATH=src` (or an installed wheel), adapt the
study JSON under `studies/` and call:

```python
from codontrace.claimgate.adapters.biomedical import (
    audit_biomedical_study_file,
    biomedical_risk_bar_payload,
)
```

Do **not** overwrite the three pin files above when regenerating this suite.
Write new outputs under this folder only.

## Honest limits

- HE01 is a life-loop campaign used here as an *executed* evidence bundle analog, not an implant or patient model.
- `raises_claim_ladder` stays false for worksheet / study overlays.
- This package strengthens the **applied claim-gating story**; it does not upgrade the paper's empirical HE01 numbers.
