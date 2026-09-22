"""Biomedical port: a DomainProfile, not a second engine."""

from __future__ import annotations

from collections.abc import Sequence

from codontrace.claimgate.domain import BIOMEDICAL, bundle_from_declared_scores
from codontrace.claimgate.schema import ClaimgateBundle
from codontrace.errors import ConfigurationError

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
    device_software_kind: str = "analog_table",
    iec_62304_class: str = "undeclared",
    imdrf_n12_category: str = "undeclared",
    fda_2023_evidence: Sequence[int] = (),
    physics_based: bool = False,
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
        device_software_kind=device_software_kind,
        iec_62304_class=iec_62304_class,
        imdrf_n12_category=imdrf_n12_category,
        fda_2023_evidence=fda_2023_evidence,
        physics_based=physics_based,
    )


def bundle_from_device_model_cou(
    *,
    question_of_interest: str,
    context_of_use: str,
    model_influence: int,
    decision_consequence: int,
    treatment_scores: Sequence[float],
    control_scores: Sequence[float],
    device_software_kind: str,
    iec_62304_class: str = "undeclared",
    imdrf_n12_category: str = "undeclared",
    fda_2023_evidence: Sequence[int] = (),
    physics_based: bool = False,
    metric: str = "declared_score",
    software_name: str = "external-device-model-table",
    software_version: str = "unspecified",
    claimed: str = "runtime_observation",
) -> ClaimgateBundle:
    """Equipment-adjacent analog: SiMD/SaMD *labels*, not a device file.

    ``device_software_kind`` must be declared. Declaring ``simd_declared``
    records IMDRF medical-device-software language; it does not classify
    a product or invoke IEC 62304.
    """

    kind = device_software_kind.strip().lower()
    if kind not in {"simd_declared", "samd_declared", "analog_table"}:
        raise ConfigurationError(
            "bundle_from_device_model_cou requires analog_table, simd_declared, or samd_declared;"
            f" got {device_software_kind!r}."
        )
    return bundle_from_biomedical_cou(
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
        device_software_kind=kind,
        iec_62304_class=iec_62304_class,
        imdrf_n12_category=imdrf_n12_category,
        fda_2023_evidence=fda_2023_evidence,
        physics_based=physics_based,
    )