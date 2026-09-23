"""Host–parasite / microbe–virus port: a DomainProfile, not a second engine.

This adapter is claim-labeling only. It does not implement infection physics,
does not certify vaccines, antivirals, phage therapy, epidemic forecasts, or
biosafety levels, and must not be read as a clinical pathogen model.
"""

from __future__ import annotations

from collections.abc import Sequence

from codontrace.claimgate.domain import HOST_PARASITE, bundle_from_declared_scores
from codontrace.claimgate.schema import ClaimgateBundle
from codontrace.errors import ConfigurationError

BLOCKED_HOST_PARASITE_CLAIMS = HOST_PARASITE.blocked_claims


def assert_claim_allowed(claimed: str) -> str:
    """Fail closed if ``claimed`` is blocked on the host_parasite profile.

    Returns the normalized claim string. Does not grant evidence or run the
    engine.
    """

    claim = claimed.strip().lower()
    if claim in HOST_PARASITE.blocked_claims:
        raise ConfigurationError(
            f"{claimed!r} is blocked on domain profile {HOST_PARASITE.name!r}."
        )
    return claim


def bundle_from_host_parasite_cou(
    *,
    question_of_interest: str,
    context_of_use: str,
    model_influence: int,
    decision_consequence: int,
    treatment_scores: Sequence[float],
    control_scores: Sequence[float],
    metric: str = "declared_score",
    software_name: str = "external-host-parasite-table",
    software_version: str = "unspecified",
    claimed: str = "runtime_observation",
    device_software_kind: str = "analog_table",
    iec_62304_class: str = "undeclared",
    imdrf_n12_category: str = "undeclared",
    fda_2023_evidence: Sequence[int] = (),
    physics_based: bool = False,
) -> ClaimgateBundle:
    """Wrap declared digital coevolution scores under the host_parasite profile.

    Engine ticks are not invoked. Infection / transmission physics are not
    implemented. Clinical and therapy claims stay blocked.
    """

    assert_claim_allowed(claimed)
    return bundle_from_declared_scores(
        profile=HOST_PARASITE,
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
