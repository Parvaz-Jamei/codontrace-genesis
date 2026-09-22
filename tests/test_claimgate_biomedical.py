"""Biomedical COU wrapper: analog only, blocked clinical aliases."""

from __future__ import annotations

import pytest

from codontrace.claimgate import audit_bundle
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
    assert extra["model_risk"] == 3
    assert extra["asme_vv40"] == "complement_only"
    assert extra["certification"] == "none"
    assert bundle.replay.verified is False
    report = audit_bundle(bundle)
    assert report.achieved_level <= 2
    assert any("Not a medical device" in item for item in bundle.limitations)


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
