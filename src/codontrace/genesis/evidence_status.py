"""Canonical evidence status vocabulary for GENESIS manifests and ClaimGate wiring."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from codontrace._types import JsonValue
from codontrace.errors import ConfigurationError


class EvidenceStatus(StrEnum):
    MEASURED = "measured"
    RUNTIME_EFFECTIVE = "runtime_effective"
    CONTROL_SUPPORTED = "control_supported"
    ABLATION_SUPPORTED = "ablation_supported"
    HELDOUT_SUPPORTED = "heldout_supported"
    INTERVENTION_SUPPORTED = "intervention_supported"
    PROVISIONAL = "provisional"
    EMPTY_BUT_AVAILABLE = "empty_but_available"
    UNAVAILABLE = "unavailable"
    DISABLED_BY_CONFIG = "disabled_by_config"
    NOT_CONFIGURED = "not_configured"
    FIXED_DEFAULT = "fixed_default"
    NOT_APPLICABLE = "not_applicable"
    NOT_OBSERVED = "not_observed"
    NOT_RUN = "not_run"
    METADATA_ONLY = "metadata_only"


CLAIM_ELIGIBLE_STATUSES = frozenset({
    EvidenceStatus.MEASURED,
    EvidenceStatus.RUNTIME_EFFECTIVE,
    EvidenceStatus.CONTROL_SUPPORTED,
    EvidenceStatus.ABLATION_SUPPORTED,
    EvidenceStatus.HELDOUT_SUPPORTED,
    EvidenceStatus.INTERVENTION_SUPPORTED,
})

NON_CLAIM_STATUSES = frozenset(set(EvidenceStatus) - CLAIM_ELIGIBLE_STATUSES)

_ALLOWED_TRANSITIONS = {
    EvidenceStatus.METADATA_ONLY: {EvidenceStatus.EMPTY_BUT_AVAILABLE, EvidenceStatus.PROVISIONAL, EvidenceStatus.MEASURED},
    EvidenceStatus.EMPTY_BUT_AVAILABLE: {EvidenceStatus.PROVISIONAL, EvidenceStatus.MEASURED, EvidenceStatus.DISABLED_BY_CONFIG},
    EvidenceStatus.NOT_RUN: {EvidenceStatus.PROVISIONAL, EvidenceStatus.MEASURED, EvidenceStatus.DISABLED_BY_CONFIG},
    EvidenceStatus.PROVISIONAL: {EvidenceStatus.MEASURED, EvidenceStatus.RUNTIME_EFFECTIVE, EvidenceStatus.CONTROL_SUPPORTED, EvidenceStatus.NOT_RUN},
    EvidenceStatus.MEASURED: {EvidenceStatus.RUNTIME_EFFECTIVE, EvidenceStatus.CONTROL_SUPPORTED, EvidenceStatus.ABLATION_SUPPORTED},
    EvidenceStatus.RUNTIME_EFFECTIVE: {EvidenceStatus.CONTROL_SUPPORTED, EvidenceStatus.ABLATION_SUPPORTED},
    EvidenceStatus.CONTROL_SUPPORTED: {EvidenceStatus.ABLATION_SUPPORTED, EvidenceStatus.HELDOUT_SUPPORTED},
    EvidenceStatus.ABLATION_SUPPORTED: {EvidenceStatus.HELDOUT_SUPPORTED, EvidenceStatus.INTERVENTION_SUPPORTED},
    EvidenceStatus.HELDOUT_SUPPORTED: {EvidenceStatus.INTERVENTION_SUPPORTED},
}


def coerce_evidence_status(value: str | EvidenceStatus) -> EvidenceStatus:
    try:
        return value if isinstance(value, EvidenceStatus) else EvidenceStatus(str(value))
    except ValueError as exc:
        raise ConfigurationError(f"Unknown evidence status: {value!r}") from exc


def is_claim_eligible_status(value: str | EvidenceStatus) -> bool:
    return coerce_evidence_status(value) in CLAIM_ELIGIBLE_STATUSES


def validate_status_transition(old: str | EvidenceStatus, new: str | EvidenceStatus) -> bool:
    old_status = coerce_evidence_status(old)
    new_status = coerce_evidence_status(new)
    return old_status == new_status or new_status in _ALLOWED_TRANSITIONS.get(old_status, set())


@dataclass(frozen=True, slots=True)
class EvidenceStatusRecord:
    field_name: str
    status: EvidenceStatus
    reason: str = ""

    def to_dict(self) -> dict[str, JsonValue]:
        return {"field_name": self.field_name, "status": self.status.value, "reason": self.reason}
