"""Wrap a user-declared biomedical context-of-use as a ClaimGate bundle.

This is an evidence-pack helper. It is not a medical device, SaMD validator,
ASME V&V 40 implementation, or clinical study runner.
"""

from __future__ import annotations

from collections.abc import Sequence

from codontrace.errors import ConfigurationError
from codontrace.genesis.canonical import canonical_digest, canonical_payload
from codontrace.claimgate.schema import (
    ClaimgateArm,
    ClaimgateBundle,
    ClaimgateComparison,
    ClaimgateOutcome,
    ClaimgateReplay,
    ClaimgateSoftware,
    parse_claimgate_bundle,
)

BLOCKED_BIOMEDICAL_CLAIMS = frozenset(
    {
        "medical_device",
        "samd_certified",
        "fda_cleared",
        "ce_marked",
        "clinical_validated",
        "asme_vv40_passed",
        "patient_safe",
    }
)

_DEFAULT_LIMITATIONS = (
    "Not a medical device, SaMD, IVD, or diagnostic tool.",
    "Not an ASME V&V 40-2018 implementation or certification.",
    "Question of interest, context of use, and risk labels are user-declared.",
    "A ClaimGate grade is a claim ceiling, not clinical validity.",
)


def _grade_int(name: str, value: int) -> int:
    if value not in (1, 2, 3):
        raise ConfigurationError(f"{name} must be 1, 2, or 3 (user-declared V&V 40 analog).")
    return value


def _finite_series(name: str, values: Sequence[float]) -> tuple[float, ...]:
    if len(values) < 1:
        raise ConfigurationError(f"{name} must contain at least one finite score.")
    out: list[float] = []
    for item in values:
        number = float(item)
        if number != number or number in (float("inf"), float("-inf")):
            raise ConfigurationError(f"{name} must be finite.")
        out.append(number)
    return tuple(out)


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
    """Build a claimgate_bundle_v1 from a declared COU and two score series.

    ``claimed`` must not be a blocked biomedical alias. Risk is
    ``max(model_influence, decision_consequence)`` and is recorded only.
    """

    qoi = question_of_interest.strip()
    cou = context_of_use.strip()
    if not qoi or not cou:
        raise ConfigurationError("question_of_interest and context_of_use are required.")
    claim = claimed.strip().lower()
    if claim in BLOCKED_BIOMEDICAL_CLAIMS:
        raise ConfigurationError(
            f"{claimed!r} is a blocked biomedical alias; ClaimGate will not wrap it."
        )
    influence = _grade_int("model_influence", model_influence)
    consequence = _grade_int("decision_consequence", decision_consequence)
    risk = max(influence, consequence)
    treatment = _finite_series("treatment_scores", treatment_scores)
    control = _finite_series("control_scores", control_scores)

    extra = {
        "domain": "biomedical_engineering_analog",
        "question_of_interest": qoi,
        "context_of_use": cou,
        "model_influence": influence,
        "decision_consequence": consequence,
        "model_risk": risk,
        "requested_claim": claim,
        "asme_vv40": "complement_only",
        "certification": "none",
    }
    config_digest = canonical_digest(canonical_payload(extra))
    bundle = ClaimgateBundle(
        software=ClaimgateSoftware(
            name=software_name,
            version=software_version,
            commit="",
        ),
        seeds=tuple(range(1, min(len(treatment), len(control)) + 1)),
        config_digest=config_digest,
        arms=(
            ClaimgateArm(name="declared_model", role="treatment", n=len(treatment)),
            ClaimgateArm(name="declared_baseline", role="negative_control", n=len(control)),
        ),
        outcomes=(
            ClaimgateOutcome(
                metric=metric,
                values_by_arm={
                    "declared_model": treatment,
                    "declared_baseline": control,
                },
            ),
        ),
        comparisons=(
            ClaimgateComparison(
                a="declared_model",
                b="declared_baseline",
                effect_size=None,
                ci_low=None,
                ci_high=None,
                p=None,
                test="",
                correction="",
            ),
        ),
        replay=ClaimgateReplay(verified=False, digests=()),
        artifacts=(),
        limitations=_DEFAULT_LIMITATIONS + (f"Requested claim stays {claim!r}.",),
        extra=extra,
    )
    return parse_claimgate_bundle(bundle)
