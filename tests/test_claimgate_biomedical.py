"""Domain profiles: biomedical is one port; engine is not forked."""

from __future__ import annotations

from pathlib import Path

import pytest

from codontrace.claimgate import ALIFE, HARDWARE, audit_bundle, bundle_from_declared_scores
from codontrace.claimgate.adapters.biomedical import (
    BLOCKED_BIOMEDICAL_CLAIMS,
    bundle_from_biomedical_cou,
    bundle_from_device_model_cou,
)
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
    assert "ladder_validation.json" in baic_readme
    assert "fix/small-sample-ci-coverage" in baic_readme
    assert "does not exist" in baic_readme.lower()
    assert "not" in baic_readme.lower() and "tree" in baic_readme.lower()
    assert "opt-in" in baic_readme.lower()
    assert "Studentized" in baic_readme or "studentized" in baic_readme
