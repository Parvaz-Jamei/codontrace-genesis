"""Domain profiles for ClaimGate. The engine stays domain-agnostic.

A profile is a named set of blocked aliases and default limitations.
It does not change tick semantics, grant a claim, or certify a device.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

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


@dataclass(frozen=True, slots=True)
class DomainProfile:
    """Port: how an evidence table is labeled, not how the world runs."""

    name: str
    blocked_claims: frozenset[str]
    limitations: tuple[str, ...]
    extra_defaults: Mapping[str, str]


ALIFE = DomainProfile(
    name="alife",
    blocked_claims=frozenset(
        {
            "intelligence",
            "collective_intelligence",
            "agi",
            "tokyo_type1_passed",
            "avida_replacement",
        }
    ),
    limitations=(
        "Genesis engine ticks are domain-agnostic; this profile only labels claims.",
        "Not an Avida replacement or intelligence proof.",
    ),
    extra_defaults={"engine": "genesis_ticks", "certification": "none"},
)

BIOMEDICAL = DomainProfile(
    name="biomedical",
    blocked_claims=frozenset(
        {
            "medical_device",
            "samd_certified",
            "fda_cleared",
            "ce_marked",
            "clinical_validated",
            "asme_vv40_passed",
            "patient_safe",
        }
    ),
    limitations=(
        "Not a medical device, SaMD, IVD, or diagnostic tool.",
        "Not an ASME V&V 40-2018 implementation or certification.",
        "Question of interest, context of use, and risk labels are user-declared.",
        "A ClaimGate grade is a claim ceiling, not clinical validity.",
    ),
    extra_defaults={
        "asme_vv40": "complement_only",
        "certification": "none",
        "engine": "unused_for_table_wrap",
    },
)

HARDWARE = DomainProfile(
    name="hardware",
    blocked_claims=frozenset({"physical_robot_platform", "esp32_validated"}),
    limitations=(
        "Hardware bridge is an engineering stub unless a transport actually ran.",
        "A score table is not a robot experiment.",
    ),
    extra_defaults={"engine": "optional_bridge", "certification": "none"},
)

PROFILES: dict[str, DomainProfile] = {
    ALIFE.name: ALIFE,
    BIOMEDICAL.name: BIOMEDICAL,
    HARDWARE.name: HARDWARE,
}


def _grade_int(name: str, value: int) -> int:
    if value not in (1, 2, 3):
        raise ConfigurationError(f"{name} must be 1, 2, or 3 (user-declared).")
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


def bundle_from_declared_scores(
    *,
    profile: DomainProfile | str,
    question_of_interest: str,
    context_of_use: str,
    model_influence: int,
    decision_consequence: int,
    treatment_scores: Sequence[float],
    control_scores: Sequence[float],
    metric: str = "declared_score",
    software_name: str = "external-score-table",
    software_version: str = "unspecified",
    claimed: str = "runtime_observation",
) -> ClaimgateBundle:
    """Wrap two score series plus a declared COU. Engine is not invoked."""

    resolved = PROFILES[profile] if isinstance(profile, str) else profile
    qoi = question_of_interest.strip()
    cou = context_of_use.strip()
    if not qoi or not cou:
        raise ConfigurationError("question_of_interest and context_of_use are required.")
    claim = claimed.strip().lower()
    if claim in resolved.blocked_claims:
        raise ConfigurationError(
            f"{claimed!r} is blocked on domain profile {resolved.name!r}."
        )
    influence = _grade_int("model_influence", model_influence)
    consequence = _grade_int("decision_consequence", decision_consequence)
    treatment = _finite_series("treatment_scores", treatment_scores)
    control = _finite_series("control_scores", control_scores)
    extra = {
        "domain": resolved.name,
        "question_of_interest": qoi,
        "context_of_use": cou,
        "model_influence": influence,
        "decision_consequence": consequence,
        "model_risk": max(influence, consequence),
        "requested_claim": claim,
        **dict(resolved.extra_defaults),
    }
    bundle = ClaimgateBundle(
        software=ClaimgateSoftware(
            name=software_name,
            version=software_version,
            commit="",
        ),
        seeds=tuple(range(1, min(len(treatment), len(control)) + 1)),
        config_digest=canonical_digest(canonical_payload(extra)),
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
        limitations=resolved.limitations + (f"Requested claim stays {claim!r}.",),
        extra=extra,
    )
    return parse_claimgate_bundle(bundle)
