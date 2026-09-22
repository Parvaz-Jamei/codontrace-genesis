"""Domain profiles: biomedical is one port; engine is not forked."""

from __future__ import annotations

from pathlib import Path

import pytest

from codontrace.claimgate import ALIFE, HARDWARE, audit_bundle, bundle_from_declared_scores
from codontrace.claimgate.adapters.biomedical import (
    BLOCKED_BIOMEDICAL_CLAIMS,
    bundle_from_biomedical_cou,
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
    assert "پیاده نشده" in baic
    assert "studentized" in baic.lower()
    assert "ladder_validation.json" in baic_readme
    assert "fix/small-sample-ci-coverage" in baic_readme
    assert "does not exist" in baic_readme.lower()
    assert "not" in baic_readme.lower() and "tree" in baic_readme.lower()
    assert "Studentized" in baic_readme or "studentized" in baic_readme
