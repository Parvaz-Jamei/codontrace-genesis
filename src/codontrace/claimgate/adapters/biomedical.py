"""Biomedical port: a DomainProfile, not a second engine."""

from __future__ import annotations

from collections.abc import Sequence

from codontrace.claimgate.domain import BIOMEDICAL, bundle_from_declared_scores
from codontrace.claimgate.schema import ClaimgateBundle

BLOCKED_BIOMEDICAL_CLAIMS = BIOMEDICAL.blocked_claims


def bundle_from_biomedical_cou(
    *,
    question_of_interest: str,
    context_of_use: str,
    model_influence: int,
    decision_consequence: int,
    treatment_scores: Sequence[float],
    control_scores: Sequence[float],
    metric: str = "declared_score",
    software_name: str = "external-biomedical-table",
    software_version: str = "unspecified",
    claimed: str = "runtime_observation",
) -> ClaimgateBundle:
    return bundle_from_declared_scores(
        profile=BIOMEDICAL,
        question_of_interest=question_of_interest,
        context_of_use=context_of_use,
        model_influence=model_influence,
        decision_consequence=decision_consequence,
        treatment_scores=treatment_scores,
        control_scores=control_scores,
        metric=metric,
        software_name=software_name,
        software_version=software_version,
        claimed=claimed,
    )
