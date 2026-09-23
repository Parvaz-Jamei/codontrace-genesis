# Applied medical evidence suite (2026-09-24)

New evidence only. No code changes. Paper pins unchanged.

- Pass: **8/8**
- Pins unchanged: **True**

- PASS `T1_high_risk_no_execution` — Overclaiming / risk not commensurate with evidence (FDA 2023; ASME V&V40)
- PASS `T2_standalone_ml_out_of_fda2023_scope` — FDA 2023 CM&S excludes standalone AI/ML
- PASS `T3_weakest_submodel_and_pirt_gaps` — Right answer for wrong reason / hierarchical ISCT
- PASS `T4_calibration_plausibility_cap` — Treating FDA cats 2/6/7 as full validation
- PASS `T5_blocked_certification_strings` — Certification / clinical-validity language without regulatory process
- PASS `T6_study_typed_adequate_vs_executed_arm` — Declaring knowledge/population validation without executed comparator
- PASS `T7_risk_bar_reproducibility_vs_paper_pin` — Reproducibility of commensurate-evidence check without mutating published pins
- PASS `T8_interval_width_gate` — Significant interval still too wide for the decision threshold (FDA Step 8)
