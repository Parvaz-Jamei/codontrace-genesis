"""Preregistration schema required before host–parasite campaign attach."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
from typing import cast

from codontrace._types import JsonValue
from codontrace.claimgate.domain import HOST_PARASITE
from codontrace.claimgate.schema import ClaimgateBundle
from codontrace.errors import ConfigurationError
from codontrace.genesis.canonical import canonical_digest, canonical_payload

_FORBIDDEN_DEFAULT = frozenset(
    {
        "red_queen_proved",
        "crispr_identity_proved",
        "phage_therapy_cleared",
        "vaccine_efficacy_proved",
        "epidemic_forecast_certified",
        "biosafety_level_certified",
        "major_transition_proved",
        "intelligence",
    }
)

_PREREG_NOTE = (
    "Preregistration records success metrics and forbidden claims; it does not "
    "raise the public ClaimGate ladder by itself."
)


@dataclass(frozen=True, slots=True)
class HostParasitePreregistration:
    """QOI / COU / arms / success metrics / forbidden claims before attach."""

    question_of_interest: str
    context_of_use: str
    arms: tuple[str, ...]
    success_metrics: tuple[str, ...]
    forbidden_claims: tuple[str, ...]
    planned_claim_ceiling: str

    def to_dict(self) -> dict[str, object]:
        body: dict[str, object] = {
            "schema": "host_parasite_preregistration_v1",
            "question_of_interest": self.question_of_interest,
            "context_of_use": self.context_of_use,
            "arms": list(self.arms),
            "success_metrics": list(self.success_metrics),
            "forbidden_claims": list(self.forbidden_claims),
            "planned_claim_ceiling": self.planned_claim_ceiling,
            "raises_claim_ladder": False,
            "red_queen_proved": False,
        }
        body["digest"] = canonical_digest(
            canonical_payload({k: body[k] for k in body if k != "digest"})
        )
        return body


def _text(raw: object, field: str) -> str:
    if not isinstance(raw, str) or not raw.strip():
        raise ConfigurationError(f"{field} is required.")
    return raw.strip()


def host_parasite_preregistration(
    *,
    question_of_interest: str,
    context_of_use: str,
    arms: Sequence[str],
    success_metrics: Sequence[str],
    forbidden_claims: Sequence[str] | None = None,
    planned_claim_ceiling: str = "runtime_observation",
) -> HostParasitePreregistration:
    """Validate and freeze a preregistration record."""

    qoi = _text(question_of_interest, "question_of_interest")
    cou = _text(context_of_use, "context_of_use")
    if not arms:
        raise ConfigurationError("preregistration arms must be non-empty.")
    if not success_metrics:
        raise ConfigurationError("preregistration success_metrics must be non-empty.")
    arm_tuple = tuple(_text(item, f"arms[{index}]") for index, item in enumerate(arms))
    metric_tuple = tuple(
        _text(item, f"success_metrics[{index}]") for index, item in enumerate(success_metrics)
    )
    forbidden_raw = (
        tuple(_FORBIDDEN_DEFAULT)
        if forbidden_claims is None
        else tuple(
            _text(item, f"forbidden_claims[{index}]").lower()
            for index, item in enumerate(forbidden_claims)
        )
    )
    if not forbidden_raw:
        raise ConfigurationError("forbidden_claims must be non-empty.")
    # Always keep core clinical / overclaim bans present.
    merged = tuple(sorted(set(forbidden_raw) | set(_FORBIDDEN_DEFAULT)))
    ceiling = _text(planned_claim_ceiling, "planned_claim_ceiling").lower()
    if ceiling not in {"runtime_observation", "candidate_evidence"}:
        raise ConfigurationError(
            "planned_claim_ceiling must be runtime_observation or candidate_evidence."
        )
    if any(claim in HOST_PARASITE.blocked_claims for claim in arm_tuple):
        raise ConfigurationError("preregistration arms must not use blocked claim names.")
    return HostParasitePreregistration(
        question_of_interest=qoi,
        context_of_use=cou,
        arms=arm_tuple,
        success_metrics=metric_tuple,
        forbidden_claims=merged,
        planned_claim_ceiling=ceiling,
    )


def attach_host_parasite_preregistration(
    bundle: ClaimgateBundle,
    prereg: HostParasitePreregistration | Mapping[str, object],
) -> ClaimgateBundle:
    """Attach preregistration; refuse overwrite and wrong domain."""

    if isinstance(prereg, HostParasitePreregistration):
        record = prereg
    elif isinstance(prereg, Mapping):
        record = host_parasite_preregistration(
            question_of_interest=str(prereg.get("question_of_interest", "")),
            context_of_use=str(prereg.get("context_of_use", "")),
            arms=tuple(prereg.get("arms") or ()),
            success_metrics=tuple(prereg.get("success_metrics") or ()),
            forbidden_claims=tuple(prereg.get("forbidden_claims") or ()) or None,
            planned_claim_ceiling=str(
                prereg.get("planned_claim_ceiling") or "runtime_observation"
            ),
        )
    else:
        raise ConfigurationError("prereg must be a HostParasitePreregistration or mapping.")
    extra = dict(bundle.extra or {})
    if extra.get("domain") != HOST_PARASITE.name:
        raise ConfigurationError(
            "attach_host_parasite_preregistration requires a host_parasite domain bundle."
        )
    if "host_parasite_preregistration" in extra:
        raise ConfigurationError("host_parasite_preregistration already attached.")
    extra["host_parasite_preregistration"] = cast(JsonValue, record.to_dict())
    limitations = bundle.limitations
    if _PREREG_NOTE not in limitations:
        limitations = limitations + (_PREREG_NOTE,)
    return replace(bundle, extra=extra, limitations=limitations)


def require_preregistration_before_campaign_attach(bundle: ClaimgateBundle) -> None:
    """Fail closed if campaign attach is attempted without preregistration."""

    extra = dict(bundle.extra or {})
    if extra.get("domain") != HOST_PARASITE.name:
        raise ConfigurationError("require_preregistration expects a host_parasite bundle.")
    if "host_parasite_preregistration" not in extra:
        raise ConfigurationError(
            "host_parasite_preregistration is required before campaign attach."
        )


__all__ = [
    "HostParasitePreregistration",
    "attach_host_parasite_preregistration",
    "host_parasite_preregistration",
    "require_preregistration_before_campaign_attach",
]
