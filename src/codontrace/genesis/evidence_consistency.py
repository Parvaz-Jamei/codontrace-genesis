"""Integration evidence/manifest/replay consistency audit."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from codontrace._types import JsonValue
from codontrace.genesis.canonical import canonical_digest, is_real_evidence_digest
from codontrace.genesis.replay_integrity import replay_digest_class_policies

_POSITIVE_STATUSES = {"allowed", "claim_ready", "measured", "runtime_effective", "supported", "complete", "complete_limited_claim"}
_NEGATIVE_STATUSES = {"blocked", "rejected", "downgraded", "descriptive_only", "provisional", "not_claim_relevant", "disabled_by_config", "empty_but_available", "skipped_by_resource_budget"}

@dataclass(frozen=True, slots=True)
class EvidenceConsistencyIssue:
    code: str
    detail: str
    record_digest: str = ""

    def __post_init__(self) -> None:
        if not self.record_digest:
            object.__setattr__(self, "record_digest", canonical_digest({"code": self.code, "detail": self.detail}, prefix="integration_evidence_issue"))

    def to_dict(self) -> dict[str, JsonValue]:
        return {"code": self.code, "detail": self.detail, "record_digest": self.record_digest}


def _bad_positive_digest(value: object) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        low = value.strip().lower()
        return low == "" or low.startswith(("not_run:", "fake", "placeholder")) or low in {"missing", "none", "null", "unknown"}
    return False


def audit_claim_payloads(claims: list[dict[str, Any]]) -> list[EvidenceConsistencyIssue]:
    issues: list[EvidenceConsistencyIssue] = []
    for idx, claim in enumerate(claims):
        status = str(claim.get("status", claim.get("decision", ""))).lower()
        required = claim.get("required_evidence", claim.get("evidence_digests", ()))
        if isinstance(required, str):
            required = [required]
        if status in _POSITIVE_STATUSES:
            if not required:
                issues.append(EvidenceConsistencyIssue("positive_claim_without_required_evidence", str(idx)))
            for digest in required:
                if _bad_positive_digest(digest) or not is_real_evidence_digest(digest):
                    issues.append(EvidenceConsistencyIssue("positive_claim_with_non_real_digest", f"{idx}:{digest}"))
        if status in _NEGATIVE_STATUSES and claim.get("hidden") is True:
            issues.append(EvidenceConsistencyIssue("negative_result_hidden", str(idx)))
    return issues


def audit_result_evidence_consistency(result: Any | None = None, *, claims: list[dict[str, Any]] | None = None, required_class_paths: tuple[str, ...] = ()) -> dict[str, JsonValue]:
    issues: list[EvidenceConsistencyIssue] = []
    policy_paths = {item.class_path for item in replay_digest_class_policies()}
    for path in required_class_paths:
        if path not in policy_paths:
            issues.append(EvidenceConsistencyIssue("missing_replay_policy", path))
    if result is not None:
        manifest = getattr(result, "evidence_manifest", None)
        if manifest is None:
            issues.append(EvidenceConsistencyIssue("missing_manifest", "result"))
        else:
            artifact_map = dict(getattr(manifest, "artifact_digest_map", {}))
            feature_status = dict(getattr(manifest, "feature_status", {}))
            for key, digest in artifact_map.items():
                if not isinstance(digest, str) or not digest:
                    issues.append(EvidenceConsistencyIssue("empty_artifact_digest", key))
                status = feature_status.get(key)
                if status in _POSITIVE_STATUSES and not is_real_evidence_digest(digest):
                    issues.append(EvidenceConsistencyIssue("positive_manifest_non_real_digest", key))
            payload = result.to_dict() if hasattr(result, "to_dict") else {}
            if "phase1_runtime_maturity_report" in payload and "phase1_runtime_maturity_report" not in artifact_map:
                issues.append(EvidenceConsistencyIssue("result_artifact_missing_manifest_entry", "phase1_runtime_maturity_report"))
            if "phase_b_scientific_maturity_report" in payload and "phase_b_scientific_maturity_report" not in artifact_map:
                issues.append(EvidenceConsistencyIssue("result_artifact_missing_manifest_entry", "phase_b_scientific_maturity_report"))
    if claims:
        issues.extend(audit_claim_payloads(claims))
    payload = {"schema_version": "integration_evidence_consistency_audit_v1", "passed": not issues, "issues": [i.to_dict() for i in issues]}
    payload["audit_digest"] = canonical_digest(payload, prefix="integration_evidence")
    return payload
