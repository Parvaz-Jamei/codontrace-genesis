"""Domain profiles: biomedical is one port; engine is not forked."""

from __future__ import annotations

from pathlib import Path

import pytest

from codontrace.claimgate import ALIFE, HARDWARE, audit_bundle, bundle_from_declared_scores
from codontrace.claimgate.adapters.biomedical import (
    BLOCKED_BIOMEDICAL_CLAIMS,
    attach_credibility_worksheet,
    audit_biomedical_study,
    audit_biomedical_study_file,
    biomedical_study_payload,
    bundle_from_biomedical_cou,
    bundle_from_device_model_cou,
    credibility_worksheet,
)
from codontrace.claimgate.adapters.codontrace import bundle_from_hard_experiment_01
from codontrace.errors import ConfigurationError


def test_biomedical_wrapper_records_risk_and_stays_unverified() -> None:
    bundle = bundle_from_biomedical_cou(
        question_of_interest="Does a toy AUROC table license a screening claim?",
        context_of_use="Synthetic scores only. No bedside use.",
        model_influence=2,
        decision_consequence=3,
        treatment_scores=(0.71, 0.68, 0.73),
        control_scores=(0.50, 0.52, 0.49),
        metric="auroc_toy",
    )
    extra = bundle.extra or {}
    assert extra["domain"] == "biomedical"
    assert extra["model_risk"] == 3
    assert extra["asme_vv40"] == "complement_only"
    assert extra["device_software_kind"] == "analog_table"
    assert extra["fda_2023_scope"] == "out_of_scope_standalone_ml"
    assert extra["iec_62304"] == "label_only"
    assert bundle.replay.verified is False
    report = audit_bundle(bundle)
    assert report.achieved_level <= 2


def test_alife_profile_blocks_avida_replacement() -> None:
    with pytest.raises(ConfigurationError):
        bundle_from_declared_scores(
            profile=ALIFE,
            question_of_interest="q",
            context_of_use="c",
            model_influence=1,
            decision_consequence=1,
            treatment_scores=(0.2,),
            control_scores=(0.1,),
            claimed="avida_replacement",
        )


def test_hardware_profile_is_independent_of_biomedical() -> None:
    with pytest.raises(ConfigurationError):
        bundle_from_declared_scores(
            profile=HARDWARE,
            question_of_interest="q",
            context_of_use="c",
            model_influence=1,
            decision_consequence=1,
            treatment_scores=(0.2,),
            control_scores=(0.1,),
            claimed="physical_robot_platform",
        )
    bundle = bundle_from_declared_scores(
        profile=HARDWARE,
        question_of_interest="q",
        context_of_use="SimEsp32Bridge stub; no robot ran.",
        model_influence=1,
        decision_consequence=1,
        treatment_scores=(0.2,),
        control_scores=(0.1,),
    )
    extra = bundle.extra or {}
    assert extra["domain"] == "hardware"
    assert extra["domain"] != "biomedical"
    assert extra["engine"] == "optional_bridge"
    assert extra["certification"] == "none"


@pytest.mark.parametrize("alias", sorted(BLOCKED_BIOMEDICAL_CLAIMS))
def test_biomedical_wrapper_rejects_blocked_aliases(alias: str) -> None:
    with pytest.raises(ConfigurationError):
        bundle_from_biomedical_cou(
            question_of_interest="q",
            context_of_use="c",
            model_influence=1,
            decision_consequence=1,
            treatment_scores=(0.1,),
            control_scores=(0.0,),
            claimed=alias,
        )


def test_device_model_cou_records_simd_labels_without_raising_the_ladder() -> None:
    bundle = bundle_from_device_model_cou(
        question_of_interest="Would a tibial-tray fatigue analog license a worst-case size pick?",
        context_of_use="Synthetic bench-like scores only. No ISO 14879-1 test. No implant.",
        model_influence=2,
        decision_consequence=3,
        treatment_scores=(0.12, 0.11, 0.13, 0.10),
        control_scores=(0.20, 0.19, 0.21, 0.22),
        device_software_kind="simd_declared",
        iec_62304_class="B",
        imdrf_n12_category="II",
        fda_2023_evidence=(1, 3, 8),
        physics_based=True,
        metric="declared_peak_stress_toy",
    )
    extra = bundle.extra or {}
    assert extra["device_software_kind"] == "simd_declared"
    assert extra["iec_62304_class"] == "B"
    assert extra["imdrf_n12_category"] == "II"
    assert extra["fda_2023_evidence"] == [1, 3, 8] or extra["fda_2023_evidence"] == (1, 3, 8)
    assert extra["fda_2023_scope"] == "physics_mechanistic"
    assert extra["certification"] == "none"
    assert extra["asme_vv40"] == "complement_only"
    assert any("not a regulatory class" in item.lower() for item in bundle.limitations)
    report = audit_bundle(bundle)
    assert report.achieved_level <= 2


def test_device_model_cou_ml_table_stays_out_of_fda_2023_scope() -> None:
    bundle = bundle_from_device_model_cou(
        question_of_interest="Does a toy AUROC table license a screening claim?",
        context_of_use="Standalone ML scores. Guidance does not apply.",
        model_influence=3,
        decision_consequence=3,
        treatment_scores=(0.9, 0.88),
        control_scores=(0.5, 0.51),
        device_software_kind="samd_declared",
        fda_2023_evidence=(5, 7),
        physics_based=False,
    )
    extra = bundle.extra or {}
    assert extra["fda_2023_scope"] == "out_of_scope_standalone_ml"
    assert any("standalone ML" in item for item in bundle.limitations)
    assert audit_bundle(bundle).achieved_level <= 2


def test_he01_v7_auditor_is_level_4_and_file_label_stays_intervention_supported() -> None:
    bundle = bundle_from_hard_experiment_01(
        Path("docs/hard_experiment_01/results_v7.json")
    )
    report = audit_bundle(bundle)
    assert report.achieved_level == 4
    assert report.public_name == "replicated_effect"
    assert report.missing_for_next == ("archived_artifact_or_doi",)
    assert (bundle.extra or {})["claim_ceiling"] == "intervention_supported"
    assert bundle.replay.verified is True
    assert len(bundle.seeds) == 30


def test_device_table_without_execution_evidence_stays_at_zero() -> None:
    bundle = bundle_from_device_model_cou(
        question_of_interest="Would a declared score table license a worst-case size pick?",
        context_of_use="Declared labels only. No replay. No intervention. No implant.",
        model_influence=2,
        decision_consequence=3,
        treatment_scores=(0.12, 0.11, 0.13),
        control_scores=(0.20, 0.19, 0.21),
        device_software_kind="simd_declared",
        iec_62304_class="B",
        imdrf_n12_category="II",
        fda_2023_evidence=(1, 3, 8),
        physics_based=True,
        metric="declared_peak_stress",
    )
    report = audit_bundle(bundle)
    assert report.achieved_level == 0
    assert "artifact_manifest" in report.missing_for_next
    assert bundle.replay.verified is False


def test_papers_keep_biomedical_as_a_port_not_a_certificate() -> None:
    joss = Path("paper/paper.md").read_text(encoding="utf-8")
    bib = Path("paper/paper.bib").read_text(encoding="utf-8")
    baic = Path("paper/baic/paper.md").read_text(encoding="utf-8")
    baic_readme = Path("paper/baic/README.md").read_text(encoding="utf-8")
    assert "DomainProfile" in joss
    assert "not a device certification" in joss
    assert "SimEsp32Bridge" in joss
    assert "opt-in exact meet-in-the-middle" in joss
    assert "10.1109/TEVC.2025.3548438" in bib
    assert "10.1109/TEVC.2024.3462281" not in bib
    assert "DomainProfile" in baic
    assert "asme_vv40_passed" in baic
    assert "اختیاری" in baic
    assert "studentized" in baic.lower()
    assert "پیاده نشده" not in baic
    assert "28f812c5" in baic
    assert "NASA-STD-7009B" in baic
    assert "read_bytes" in baic
    assert "results_v7.json" in baic
    assert "IMDRF" in baic
    assert "62304" in baic
    assert "VVUQ 40.1" in baic
    assert "10.1371/journal.pcbi.1012289" in baic
    assert "simd_declared" in baic
    assert "ESP32" in baic
    assert "کنترل مثبت" in baic
    assert "کنترل منفی" in baic
    assert "سطح ۴" in baic
    assert "intervention_supported" in baic
    assert "برای نمایش قالب" not in baic
    assert "برای نشان دادن قالب" not in baic
    assert "FITNESS_WEIGHTED" in baic
    assert "MIRROR" in baic
    assert "فقط سوگیری برداشته" not in baic
    assert "ladder_validation.json" in baic_readme
    assert "fix/small-sample-ci-coverage" in baic_readme
    assert "does not exist" in baic_readme.lower()
    assert "not" in baic_readme.lower() and "tree" in baic_readme.lower()
    assert "opt-in" in baic_readme.lower()
    assert "Studentized" in baic_readme or "studentized" in baic_readme


def test_pirt_gap_and_weakest_submodel_do_not_raise_the_ladder() -> None:
    sheet = credibility_worksheet(
        phenomena=(
            {"name": "contact_stress", "importance": "high", "knowledge": "partial"},
            {"name": "wear_debris", "importance": "high", "knowledge": "none"},
            {"name": "packaging", "importance": "low", "knowledge": "none"},
            {"name": "fatigue", "importance": "medium", "knowledge": "adequate"},
        ),
        submodels=(
            {
                "name": "device_fea",
                "role": "device",
                "level": 3,
                "evidence_categories": (1, 3),
            },
            {
                "name": "patient_geometry",
                "role": "patient",
                "level": 4,
                "identifiable": False,
                "evidence_categories": (2,),
            },
        ),
    )
    assert sheet.open_gaps == (
        "pirt:contact_stress",
        "pirt:wear_debris",
        "nonidentifiable:patient_geometry",
        "supporting_evidence_only:patient_geometry",
    )
    assert sheet.limiting_submodel == "patient_geometry"
    assert sheet.limiting_level == 1
    assert sheet.coupled_ceiling == 1
    assert sheet.to_dict()["raises_claim_ladder"] is False

    bundle = bundle_from_device_model_cou(
        question_of_interest="Would this bench-like score table license a worst-case size pick?",
        context_of_use="Synthetic table only; no ISO 14879-1 test; no implant.",
        model_influence=2,
        decision_consequence=3,
        treatment_scores=(0.12, 0.11, 0.13),
        control_scores=(0.20, 0.19, 0.21),
        device_software_kind="simd_declared",
        physics_based=True,
    )
    before = audit_bundle(bundle).achieved_level
    annotated = attach_credibility_worksheet(
        bundle,
        phenomena=({"name": "contact_stress", "importance": "high", "knowledge": "adequate"},),
        submodels=(
            {"name": "device_fea", "role": "device", "level": 3, "evidence_categories": (1, 8)},
            {"name": "patient_geometry", "role": "patient", "level": 1, "evidence_categories": (4,)},
        ),
    )
    assert audit_bundle(annotated).achieved_level == before
    stored = annotated.extra["credibility_worksheet"]
    assert stored["coupled_ceiling"] == 1
    assert stored["open_gaps"] == ["pirt:contact_stress"]


def test_worksheet_rejects_an_empty_table_and_a_certificate_is_still_blocked() -> None:
    with pytest.raises(ConfigurationError, match="phenomenon or a submodel"):
        credibility_worksheet()
    with pytest.raises(ConfigurationError):
        bundle_from_device_model_cou(
            question_of_interest="q",
            context_of_use="c",
            model_influence=1,
            decision_consequence=1,
            treatment_scores=(1.0,),
            control_scores=(1.0,),
            device_software_kind="simd_declared",
            claimed="asme_vv40_passed",
        )


def test_study_closes_only_the_arm_that_was_executed() -> None:
    study = audit_biomedical_study_file("examples/studies/he01_phenomena.json")
    assert study.claim_level == 4
    assert study.ceiling_measured is False
    assert "source_fitness_bias" in study.executed
    assert "life_loop" in study.executed
    assert "contact_stress" in study.declared_only
    assert study.not_closed == ()
    assert "pirt:source_fitness_bias" not in study.worksheet.open_gaps
    assert "pirt:contact_stress" in study.worksheet.open_gaps
    assert "declared_only:contact_stress" in study.worksheet.open_gaps
    assert "declared_only:patient_geometry" in study.worksheet.open_gaps
    assert study.worksheet.coupled_ceiling is None
    assert study.context_of_use.startswith("Life-loop")
    assert study.worksheet.to_dict()["raises_claim_ladder"] is False
    sources = {name: (level, source) for name, level, source in study.submodel_sources}
    assert sources["life_loop"] == (4, "executed")
    assert sources["patient_geometry"] == (2, "declared")


def test_a_named_arm_must_exist_and_a_weak_run_does_not_close_the_phenomenon() -> None:
    weak = bundle_from_device_model_cou(
        question_of_interest="q",
        context_of_use="synthetic table",
        model_influence=2,
        decision_consequence=2,
        treatment_scores=(0.1, 0.2),
        control_scores=(0.2, 0.3),
        device_software_kind="analog_table",
    )
    with pytest.raises(ConfigurationError, match="not in the experiment"):
        audit_biomedical_study(
            {"phenomena": ({"name": "bias", "importance": "high", "arm": "source_bias_on"},)},
            experiment=weak,
        )
    closed = audit_biomedical_study(
        {"phenomena": ({"name": "score_table", "importance": "high", "arm": "declared_model"},)},
        experiment=weak,
    )
    assert closed.claim_level == 0
    assert "pirt:score_table" in closed.worksheet.open_gaps
    assert "score_table" in closed.not_closed
    assert "score_table" not in closed.executed

    he01 = bundle_from_hard_experiment_01(Path("docs/hard_experiment_01/results_v7.json"))
    stolen = audit_biomedical_study(
        {
            "phenomena": (
                {"name": "source_fitness_bias", "importance": "high", "arm": "source_bias_on"},
                {"name": "contact_stress", "importance": "high", "arm": "source_bias_on"},
                {"name": "capsule_channel", "importance": "high", "arm": "capsules_off"},
            )
        },
        experiment=he01,
    )
    assert stolen.executed == ("source_fitness_bias",)
    assert "contact_stress" in stolen.not_closed
    assert "capsule_channel" in stolen.not_closed
    assert "shared_arm:contact_stress" in stolen.worksheet.open_gaps
    assert "pirt:capsule_channel" in stolen.worksheet.open_gaps
    assert "pirt:contact_stress" in stolen.worksheet.open_gaps


def test_committed_biomedical_study_matches_the_live_audit() -> None:
    import json

    live = biomedical_study_payload()
    committed = json.loads(Path("docs/claimgate/biomedical_study.json").read_text(encoding="utf-8"))
    assert live["claim_level"] == 4
    assert live["coupled_ceiling"] is None
    assert live["ceiling_measured"] is False
    assert live["raises_claim_ladder"] is False
    assert live["not_a_device_certificate"] is True
    assert committed == live


def test_a_wide_interval_does_not_close_and_one_run_is_not_two() -> None:
    import hashlib
    from dataclasses import replace

    he01 = bundle_from_hard_experiment_01(Path("docs/hard_experiment_01/results_v7.json"))
    wide = audit_biomedical_study(
        {
            "phenomena": (
                {
                    "name": "source_fitness_bias",
                    "importance": "high",
                    "arm": "source_bias_on",
                    "max_interval_width": 1.0,
                },
            )
        },
        experiment=he01,
    )
    assert "source_fitness_bias" in wide.not_closed
    assert "interval_too_wide:source_fitness_bias" in wide.worksheet.open_gaps

    tight = audit_biomedical_study(
        {
            "phenomena": (
                {
                    "name": "source_fitness_bias",
                    "importance": "high",
                    "arm": "source_bias_on",
                    "max_interval_width": 6.0,
                },
            )
        },
        experiment=he01,
    )
    assert tight.executed == ("source_fitness_bias",)

    other = replace(he01, config_digest=hashlib.sha256(b"second-protocol").hexdigest())
    measured = audit_biomedical_study(
        {
            "submodels": (
                {"name": "loop_a", "role": "campaign", "use_experiment": True},
                {"name": "loop_b", "role": "campaign", "bundle": "other"},
            )
        },
        experiment=he01,
        bundles={"other": other},
    )
    assert measured.ceiling_measured is True
    assert measured.worksheet.coupled_ceiling == 4

    repeated = audit_biomedical_study(
        {
            "submodels": (
                {"name": "loop_a", "role": "campaign", "use_experiment": True},
                {"name": "loop_b", "role": "campaign", "bundle": "same"},
            )
        },
        experiment=he01,
        bundles={"same": he01},
    )
    assert repeated.ceiling_measured is False
    assert repeated.worksheet.coupled_ceiling is None
    assert "not_independent:loop_b" in repeated.worksheet.open_gaps
