"""Release-candidate evidence objects for CodonTrace.

This module models release gates, conservative exception policy, and
supply-chain posture. It does not publish, upload, run CI, call GitHub, write
files, or access the network.
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import Enum

from codontrace._types import JsonValue
from codontrace.errors import ConfigurationError
from codontrace.genesis.release_readiness import ReleaseReadinessProfile


class ReleaseGateStatus(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    NOT_RUN = "NOT RUN"
    NOT_COMPLETED = "NOT COMPLETED"
    NOT_APPLICABLE = "NOT APPLICABLE"


@dataclass(frozen=True, slots=True)
class ReleaseGateRecord:
    gate_name: str
    status: ReleaseGateStatus
    command: str = ""
    summary: str = ""
    evidence_digest: str = ""
    required_for_rc: bool = True
    required_for_publish: bool = True

    def __post_init__(self) -> None:
        if not self.gate_name:
            raise ConfigurationError("ReleaseGateRecord.gate_name must not be empty.")
        if not isinstance(self.status, ReleaseGateStatus):
            object.__setattr__(self, "status", ReleaseGateStatus(str(self.status)))

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "gate_name": self.gate_name,
            "status": self.status.value,
            "command": self.command,
            "summary": self.summary,
            "evidence_digest": self.evidence_digest,
            "required_for_rc": self.required_for_rc,
            "required_for_publish": self.required_for_publish,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, JsonValue]) -> ReleaseGateRecord:
        return cls(
            _str(data, "gate_name"),
            ReleaseGateStatus(_str(data, "status")),
            _str(data, "command", ""),
            _str(data, "summary", ""),
            _str(data, "evidence_digest", ""),
            _bool(data, "required_for_rc", True),
            _bool(data, "required_for_publish", True),
        )

    def digest(self) -> str:
        return _digest(self.to_dict())


@dataclass(frozen=True, slots=True)
class ReleaseGateException:
    """Documented exception for a non-PASS gate.

    Exceptions are intentionally conservative. Core proof/claim/build gates are
    never overridden by the evaluator.
    """

    gate_name: str
    approved: bool
    reason: str
    approved_by: str = ""
    expires_after_version: str = ""
    allow_fail_override: bool = False

    def __post_init__(self) -> None:
        if not self.gate_name:
            raise ConfigurationError("ReleaseGateException.gate_name must not be empty.")
        if self.approved and not self.reason:
            raise ConfigurationError("Approved release-gate exceptions need a reason.")

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "gate_name": self.gate_name,
            "approved": self.approved,
            "reason": self.reason,
            "approved_by": self.approved_by,
            "expires_after_version": self.expires_after_version,
            "allow_fail_override": self.allow_fail_override,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, JsonValue]) -> ReleaseGateException:
        return cls(
            _str(data, "gate_name"),
            _bool(data, "approved", False),
            _str(data, "reason", ""),
            _str(data, "approved_by", ""),
            _str(data, "expires_after_version", ""),
            _bool(data, "allow_fail_override", False),
        )

    def digest(self) -> str:
        return _digest(self.to_dict())


@dataclass(frozen=True, slots=True)
class ReleaseCandidateChecklist:
    version: str
    artifact_name: str
    gates: tuple[ReleaseGateRecord, ...]
    api_snapshot_digest: str = ""
    claim_audit_digest: str = ""
    validation_bundle_digest: str = ""
    compatibility_snapshot_digest: str = ""
    citation_digest: str = ""
    limitations_digest: str = ""
    gate_exceptions: tuple[ReleaseGateException, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if not self.version or not self.artifact_name:
            raise ConfigurationError(
                "ReleaseCandidateChecklist version/artifact_name must not be empty."
            )

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "version": self.version,
            "artifact_name": self.artifact_name,
            "gates": [gate.to_dict() for gate in self.gates],
            "api_snapshot_digest": self.api_snapshot_digest,
            "claim_audit_digest": self.claim_audit_digest,
            "validation_bundle_digest": self.validation_bundle_digest,
            "compatibility_snapshot_digest": self.compatibility_snapshot_digest,
            "citation_digest": self.citation_digest,
            "limitations_digest": self.limitations_digest,
            "gate_exceptions": [item.to_dict() for item in self.gate_exceptions],
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, JsonValue]) -> ReleaseCandidateChecklist:
        raw = data.get("gates", [])
        raw_exceptions = data.get("gate_exceptions", [])
        if not isinstance(raw, list):
            raise ConfigurationError("ReleaseCandidateChecklist.gates must be a list.")
        if not isinstance(raw_exceptions, list):
            raise ConfigurationError("ReleaseCandidateChecklist.gate_exceptions must be a list.")
        return cls(
            _str(data, "version"),
            _str(data, "artifact_name"),
            tuple(ReleaseGateRecord.from_dict(_mapping(item, "gate")) for item in raw),
            _str(data, "api_snapshot_digest", ""),
            _str(data, "claim_audit_digest", ""),
            _str(data, "validation_bundle_digest", ""),
            _str(data, "compatibility_snapshot_digest", ""),
            _str(data, "citation_digest", ""),
            _str(data, "limitations_digest", ""),
            tuple(
                ReleaseGateException.from_dict(_mapping(item, "gate_exception"))
                for item in raw_exceptions
            ),
        )

    def digest(self) -> str:
        return _digest(self.to_dict())


@dataclass(frozen=True, slots=True)
class ReleaseCandidateDecision:
    attempted: bool
    accepted_for_testpypi: bool
    accepted_for_pypi: bool
    blocked_reasons: tuple[str, ...] = ()
    warning_reasons: tuple[str, ...] = ()
    required_missing_gates: tuple[str, ...] = ()
    duplicate_gate_names: tuple[str, ...] = ()
    accepted_for_mature_alpha: bool = False
    accepted_with_exceptions: bool = False
    exception_gate_names: tuple[str, ...] = ()
    profile_name: str = "prepublic"
    accepted_for_pypi_with_exception: bool = False

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "attempted": self.attempted,
            "accepted_for_testpypi": self.accepted_for_testpypi,
            "accepted_for_pypi": self.accepted_for_pypi,
            "blocked_reasons": list(self.blocked_reasons),
            "warning_reasons": list(self.warning_reasons),
            "required_missing_gates": list(self.required_missing_gates),
            "duplicate_gate_names": list(self.duplicate_gate_names),
            "accepted_for_mature_alpha": self.accepted_for_mature_alpha,
            "accepted_with_exceptions": self.accepted_with_exceptions,
            "exception_gate_names": list(self.exception_gate_names),
            "profile_name": self.profile_name,
            "accepted_for_pypi_with_exception": self.accepted_for_pypi_with_exception,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, JsonValue]) -> ReleaseCandidateDecision:
        return cls(
            _bool(data, "attempted", False),
            _bool(data, "accepted_for_testpypi", False),
            _bool(data, "accepted_for_pypi", False),
            _str_tuple(data, "blocked_reasons"),
            _str_tuple(data, "warning_reasons"),
            _str_tuple(data, "required_missing_gates"),
            _str_tuple(data, "duplicate_gate_names"),
            _bool(data, "accepted_for_mature_alpha", False),
            _bool(data, "accepted_with_exceptions", False),
            _str_tuple(data, "exception_gate_names"),
            _str(data, "profile_name", "prepublic"),
            _bool(data, "accepted_for_pypi_with_exception", False),
        )

    def digest(self) -> str:
        return _digest(self.to_dict())


@dataclass(frozen=True, slots=True)
class SupplyChainCheck:
    check_name: str
    status: ReleaseGateStatus
    evidence: str = ""
    notes: str = ""
    required: bool = True

    def __post_init__(self) -> None:
        if not self.check_name:
            raise ConfigurationError("SupplyChainCheck.check_name must not be empty.")
        if not isinstance(self.status, ReleaseGateStatus):
            object.__setattr__(self, "status", ReleaseGateStatus(str(self.status)))

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "check_name": self.check_name,
            "status": self.status.value,
            "evidence": self.evidence,
            "notes": self.notes,
            "required": self.required,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, JsonValue]) -> SupplyChainCheck:
        return cls(
            _str(data, "check_name"),
            ReleaseGateStatus(_str(data, "status")),
            _str(data, "evidence", ""),
            _str(data, "notes", ""),
            _bool(data, "required", True),
        )

    def digest(self) -> str:
        return _digest(self.to_dict())


@dataclass(frozen=True, slots=True)
class SupplyChainAuditResult:
    attempted: bool
    succeeded: bool
    checks: tuple[SupplyChainCheck, ...]
    blocker_count: int = 0
    warning_count: int = 0

    def __post_init__(self) -> None:
        blockers = sum(1 for check in self.checks if check.status == ReleaseGateStatus.FAIL)
        warnings = sum(
            1
            for check in self.checks
            if check.status in {ReleaseGateStatus.NOT_RUN, ReleaseGateStatus.NOT_COMPLETED}
        )
        object.__setattr__(self, "blocker_count", blockers)
        object.__setattr__(self, "warning_count", warnings)
        if blockers:
            object.__setattr__(self, "succeeded", False)

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "attempted": self.attempted,
            "succeeded": self.succeeded,
            "checks": [check.to_dict() for check in self.checks],
            "blocker_count": self.blocker_count,
            "warning_count": self.warning_count,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, JsonValue]) -> SupplyChainAuditResult:
        raw = data.get("checks", [])
        if not isinstance(raw, list):
            raise ConfigurationError("SupplyChainAuditResult.checks must be a list.")
        return cls(
            _bool(data, "attempted", False),
            _bool(data, "succeeded", False),
            tuple(SupplyChainCheck.from_dict(_mapping(item, "check")) for item in raw),
            _int(data, "blocker_count", 0),
            _int(data, "warning_count", 0),
        )

    def digest(self) -> str:
        return _digest(self.to_dict())


def evaluate_supply_chain_checks(
    checks: tuple[SupplyChainCheck, ...], *, strict: bool = False
) -> SupplyChainAuditResult:
    blockers = sum(1 for check in checks if check.status == ReleaseGateStatus.FAIL)
    warnings = sum(
        1
        for check in checks
        if check.status in {ReleaseGateStatus.NOT_RUN, ReleaseGateStatus.NOT_COMPLETED}
    )
    succeeded = blockers == 0 and (not strict or warnings == 0)
    return SupplyChainAuditResult(True, succeeded, checks, blockers, warnings)


_NON_OVERRIDABLE_GATES = {
    "claim_audit",
    "api_audit",
    "pytest",
    "compileall",
    "build",
    "twine",
    "wheel_smoke",
    "zip_hygiene",
}


def evaluate_release_candidate(
    checklist: ReleaseCandidateChecklist, profile: ReleaseReadinessProfile | None = None
) -> ReleaseCandidateDecision:
    profile = profile or ReleaseReadinessProfile.prepublic()
    counts = Counter(gate.gate_name for gate in checklist.gates)
    duplicates = tuple(sorted(name for name, count in counts.items() if count > 1))
    gates: dict[str, ReleaseGateStatus] = {}
    for gate in checklist.gates:
        gates.setdefault(gate.gate_name, gate.status)

    exceptions = {exc.gate_name: exc for exc in checklist.gate_exceptions if exc.approved}
    blocked: list[str] = []
    warnings: list[str] = []
    missing: list[str] = []
    exception_gate_names: list[str] = []

    if duplicates:
        blocked.append("duplicate_release_gates")

    for gate_name in profile.required_gates:
        status = gates.get(gate_name)
        if status == ReleaseGateStatus.PASS:
            continue
        exception = exceptions.get(gate_name)
        if _exception_allows(gate_name, status, exception):
            warnings.append(f"approved_exception:{gate_name}")
            exception_gate_names.append(gate_name)
            continue
        missing.append(gate_name)

    if checklist.claim_audit_digest == "" and profile.requires_claim_audit:
        blocked.append("missing_claim_audit_digest")
    if checklist.api_snapshot_digest == "" and profile.requires_api_audit:
        blocked.append("missing_api_snapshot_digest")
    if checklist.citation_digest == "" and profile.requires_citation:
        blocked.append("missing_citation_digest")
    if checklist.limitations_digest == "" and profile.requires_no_critical_limitations:
        blocked.append("missing_limitations_digest")
    if checklist.validation_bundle_digest == "" and "validation_bundle" in profile.required_gates:
        blocked.append("missing_validation_bundle_digest")

    if missing:
        blocked.append("required_gates_missing")
    if profile.profile_name == "prepublic" and gates.get("hosted_ci") != ReleaseGateStatus.PASS:
        warnings.append("hosted_ci_not_passed")

    pip_audit_exception = "pip_audit" in exception_gate_names
    if (
        profile.profile_name in {"pypi", "mature_alpha"}
        and gates.get("pip_audit") != ReleaseGateStatus.PASS
    ):
        if pip_audit_exception:
            warnings.append("security_exception:pip_audit")
            # PyPI/Mature Alpha exception is explicit and visible; it is not a clean PASS.
            blocked.append("pip_audit_required_for_clean_pypi")
        else:
            blocked.append("pip_audit_required_for_pypi")

    no_blockers = not blocked
    accepted_for_testpypi = profile.profile_name in {"prepublic", "testpypi"} and no_blockers
    accepted_for_pypi = profile.profile_name == "pypi" and no_blockers
    accepted_for_mature_alpha = profile.profile_name == "mature_alpha" and no_blockers
    accepted_with_exceptions = bool(exception_gate_names)
    accepted_for_pypi_with_exception = (
        profile.profile_name == "pypi"
        and pip_audit_exception
        and not any(reason for reason in blocked if reason != "pip_audit_required_for_clean_pypi")
    )
    return ReleaseCandidateDecision(
        True,
        accepted_for_testpypi,
        accepted_for_pypi,
        tuple(sorted(set(blocked))),
        tuple(sorted(set(warnings))),
        tuple(sorted(set(missing))),
        duplicates,
        accepted_for_mature_alpha,
        accepted_with_exceptions,
        tuple(sorted(set(exception_gate_names))),
        profile.profile_name,
        accepted_for_pypi_with_exception,
    )


def _exception_allows(
    gate_name: str, status: ReleaseGateStatus | None, exception: ReleaseGateException | None
) -> bool:
    if exception is None or status is None:
        return False
    if gate_name in _NON_OVERRIDABLE_GATES:
        return False
    if status == ReleaseGateStatus.FAIL and not exception.allow_fail_override:
        return False
    return status in {
        ReleaseGateStatus.NOT_COMPLETED,
        ReleaseGateStatus.NOT_RUN,
        ReleaseGateStatus.FAIL,
    }


def _digest(payload: Mapping[str, JsonValue]) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def _mapping(value: object, name: str) -> Mapping[str, JsonValue]:
    if not isinstance(value, Mapping):
        raise ConfigurationError(f"{name} must be an object.")
    return value


def _str(data: Mapping[str, JsonValue], key: str, default: str | None = None) -> str:
    value = data.get(key, default)
    if not isinstance(value, str):
        raise ConfigurationError(f"{key} must be a string.")
    return value


def _bool(data: Mapping[str, JsonValue], key: str, default: bool) -> bool:
    value = data.get(key, default)
    if not isinstance(value, bool):
        raise ConfigurationError(f"{key} must be a boolean.")
    return value


def _int(data: Mapping[str, JsonValue], key: str, default: int) -> int:
    value = data.get(key, default)
    if isinstance(value, bool) or not isinstance(value, int):
        raise ConfigurationError(f"{key} must be an integer.")
    return value


def _str_tuple(data: Mapping[str, JsonValue], key: str) -> tuple[str, ...]:
    raw = data.get(key, [])
    if not isinstance(raw, list) or not all(isinstance(item, str) for item in raw):
        raise ConfigurationError(f"{key} must be a list of strings.")
    return tuple(str(item) for item in raw)
