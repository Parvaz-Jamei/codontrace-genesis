"""Final Mature Research Alpha manifest objects.

These records summarize caller-provided evidence only. They do not read files,
write files, publish packages, run CI, or generate reports.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass

from codontrace._types import JsonValue
from codontrace.errors import ConfigurationError


@dataclass(frozen=True, slots=True)
class FinalReleaseManifest:
    version: str
    artifact_name: str
    source_zip_digest: str
    wheel_digest: str = ""
    sdist_digest: str = ""
    api_stability_map_digest: str = ""
    compatibility_policy_digest: str = ""
    documentation_audit_digest: str = ""
    claim_audit_digest: str = ""
    scientific_evidence_validation_digest: str = ""
    mature_alpha_readiness_digest: str = ""
    release_decision_digest: str = ""
    citation_digest: str = ""
    security_evidence_digest: str = ""
    limitations_digest: str = ""

    def __post_init__(self) -> None:
        if not self.version or not self.artifact_name or not self.source_zip_digest:
            raise ConfigurationError(
                "FinalReleaseManifest version/artifact/source digest required."
            )

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "version": self.version,
            "artifact_name": self.artifact_name,
            "source_zip_digest": self.source_zip_digest,
            "wheel_digest": self.wheel_digest,
            "sdist_digest": self.sdist_digest,
            "api_stability_map_digest": self.api_stability_map_digest,
            "compatibility_policy_digest": self.compatibility_policy_digest,
            "documentation_audit_digest": self.documentation_audit_digest,
            "claim_audit_digest": self.claim_audit_digest,
            "scientific_evidence_validation_digest": self.scientific_evidence_validation_digest,
            "mature_alpha_readiness_digest": self.mature_alpha_readiness_digest,
            "release_decision_digest": self.release_decision_digest,
            "citation_digest": self.citation_digest,
            "security_evidence_digest": self.security_evidence_digest,
            "limitations_digest": self.limitations_digest,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, JsonValue]) -> FinalReleaseManifest:
        return cls(
            _str(data, "version"),
            _str(data, "artifact_name"),
            _str(data, "source_zip_digest"),
            _str(data, "wheel_digest", ""),
            _str(data, "sdist_digest", ""),
            _str(data, "api_stability_map_digest", ""),
            _str(data, "compatibility_policy_digest", ""),
            _str(data, "documentation_audit_digest", ""),
            _str(data, "claim_audit_digest", ""),
            _str(data, "scientific_evidence_validation_digest", ""),
            _str(data, "mature_alpha_readiness_digest", ""),
            _str(data, "release_decision_digest", ""),
            _str(data, "citation_digest", ""),
            _str(data, "security_evidence_digest", ""),
            _str(data, "limitations_digest", ""),
        )

    def digest(self) -> str:
        return _digest(self.to_dict())


@dataclass(frozen=True, slots=True)
class FinalGateSummary:
    version: str
    code_gates_passed: bool
    docs_gates_passed: bool
    claim_gates_passed: bool
    package_gates_passed: bool
    scientific_evidence_gates_passed: bool
    external_release_gates_passed: bool
    blocked_for_public_release: bool
    accepted_as_code_level_mature_alpha: bool
    reasons: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "version": self.version,
            "code_gates_passed": self.code_gates_passed,
            "docs_gates_passed": self.docs_gates_passed,
            "claim_gates_passed": self.claim_gates_passed,
            "package_gates_passed": self.package_gates_passed,
            "scientific_evidence_gates_passed": self.scientific_evidence_gates_passed,
            "external_release_gates_passed": self.external_release_gates_passed,
            "blocked_for_public_release": self.blocked_for_public_release,
            "accepted_as_code_level_mature_alpha": self.accepted_as_code_level_mature_alpha,
            "reasons": list(self.reasons),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, JsonValue]) -> FinalGateSummary:
        return cls(
            _str(data, "version"),
            _bool(data, "code_gates_passed"),
            _bool(data, "docs_gates_passed"),
            _bool(data, "claim_gates_passed"),
            _bool(data, "package_gates_passed"),
            _bool(data, "scientific_evidence_gates_passed"),
            _bool(data, "external_release_gates_passed"),
            _bool(data, "blocked_for_public_release"),
            _bool(data, "accepted_as_code_level_mature_alpha"),
            _str_tuple(data, "reasons"),
        )

    def digest(self) -> str:
        return _digest(self.to_dict())


@dataclass(frozen=True, slots=True)
class FinalExamplesMatrix:
    example_name: str
    category: str
    expected_no_file_output: bool = True
    expected_runtime_dependency_free: bool = True
    smoke_status: str = "NOT RUN"
    notes: str = ""

    def __post_init__(self) -> None:
        if not self.example_name or not self.category:
            raise ConfigurationError("FinalExamplesMatrix example_name/category required.")
        if self.smoke_status not in {"PASS", "FAIL", "NOT RUN", "NOT COMPLETED", "NOT APPLICABLE"}:
            raise ConfigurationError("FinalExamplesMatrix.smoke_status is invalid.")

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "example_name": self.example_name,
            "category": self.category,
            "expected_no_file_output": self.expected_no_file_output,
            "expected_runtime_dependency_free": self.expected_runtime_dependency_free,
            "smoke_status": self.smoke_status,
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, JsonValue]) -> FinalExamplesMatrix:
        return cls(
            _str(data, "example_name"),
            _str(data, "category"),
            _bool(data, "expected_no_file_output", True),
            _bool(data, "expected_runtime_dependency_free", True),
            _str(data, "smoke_status", "NOT RUN"),
            _str(data, "notes", ""),
        )

    def digest(self) -> str:
        return _digest(self.to_dict())


@dataclass(frozen=True, slots=True)
class FinalExamplesMatrixSummary:
    examples: tuple[FinalExamplesMatrix, ...]

    @property
    def total_examples(self) -> int:
        return len(self.examples)

    @property
    def passed_examples(self) -> int:
        return sum(1 for item in self.examples if item.smoke_status == "PASS")

    @property
    def failed_examples(self) -> int:
        return sum(1 for item in self.examples if item.smoke_status == "FAIL")

    @property
    def categories(self) -> tuple[str, ...]:
        return tuple(sorted({item.category for item in self.examples}))

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "examples": [item.to_dict() for item in self.examples],
            "total_examples": self.total_examples,
            "passed_examples": self.passed_examples,
            "failed_examples": self.failed_examples,
            "categories": list(self.categories),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, JsonValue]) -> FinalExamplesMatrixSummary:
        raw = data.get("examples", [])
        if not isinstance(raw, list):
            raise ConfigurationError("FinalExamplesMatrixSummary.examples must be a list.")
        return cls(tuple(FinalExamplesMatrix.from_dict(_mapping(item, "example")) for item in raw))

    def digest(self) -> str:
        return _digest(self.to_dict())


@dataclass(frozen=True, slots=True)
class FinalNonClaimStatement:
    version: str
    non_claims: tuple[str, ...]
    allowed_claims: tuple[str, ...]
    prohibited_claims: tuple[str, ...]

    def __post_init__(self) -> None:
        required = {
            "AGI",
            "consciousness",
            "artificial life proof",
            "open-ended discovery proof",
            "causal proof",
            "knowledge transfer proof",
            "benchmark superiority",
            "production autonomous intelligence",
            "superintelligence",
        }
        missing = tuple(
            sorted(item for item in required if item not in set(self.prohibited_claims))
        )
        if missing:
            raise ConfigurationError(f"FinalNonClaimStatement missing prohibited claims: {missing}")

    @classmethod
    def mature_alpha(cls, version: str) -> FinalNonClaimStatement:
        return cls(
            version=version,
            non_claims=(
                "No AGI claim.",
                "No artificial life proof.",
                "No open-ended discovery proof.",
                "No benchmark superiority claim.",
            ),
            allowed_claims=(
                "professional library-first research toolkit",
                "auditable evidence infrastructure",
                "GENESIS-aligned research alpha",
            ),
            prohibited_claims=(
                "AGI",
                "consciousness",
                "artificial life proof",
                "open-ended discovery proof",
                "causal proof",
                "knowledge transfer proof",
                "benchmark superiority",
                "production autonomous intelligence",
                "superintelligence",
            ),
        )

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "version": self.version,
            "non_claims": list(self.non_claims),
            "allowed_claims": list(self.allowed_claims),
            "prohibited_claims": list(self.prohibited_claims),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, JsonValue]) -> FinalNonClaimStatement:
        return cls(
            _str(data, "version"),
            _str_tuple(data, "non_claims"),
            _str_tuple(data, "allowed_claims"),
            _str_tuple(data, "prohibited_claims"),
        )

    def digest(self) -> str:
        return _digest(self.to_dict())


def _digest(payload: Mapping[str, JsonValue]) -> str:
    from codontrace.genesis.canonical import canonical_digest

    return canonical_digest(payload)


def _mapping(value: object, name: str) -> Mapping[str, JsonValue]:
    if not isinstance(value, Mapping):
        raise ConfigurationError(f"{name} must be an object.")
    return value


def _str(data: Mapping[str, JsonValue], key: str, default: str | None = None) -> str:
    value = data.get(key, default)
    if not isinstance(value, str):
        raise ConfigurationError(f"{key} must be a string.")
    return value


def _bool(data: Mapping[str, JsonValue], key: str, default: bool | None = None) -> bool:
    value = data.get(key, default)
    if not isinstance(value, bool):
        raise ConfigurationError(f"{key} must be a boolean.")
    return value


def _str_tuple(data: Mapping[str, JsonValue], key: str) -> tuple[str, ...]:
    raw = data.get(key, [])
    if not isinstance(raw, list) or not all(isinstance(item, str) for item in raw):
        raise ConfigurationError(f"{key} must be a list of strings.")
    return tuple(str(item) for item in raw)

# Phase 3 P0/P1 strict final claim/release-pack contracts.
from codontrace.genesis.canonical import (
    PHASE3_STATUS_VALUES as _PHASE3_STATUS_VALUES,
    canonical_digest as _strict_phase3_digest,
    is_real_evidence_digest as _strict_is_real_digest,
    require_finite_float as _phase3_finite,
    require_phase3_status as _require_phase3_status,
    require_real_evidence_digest as _strict_require_real_digest,
)


@dataclass(frozen=True, slots=True)
class FinalClaimValidationResult:
    passed: bool
    claim_eligible: bool
    reasons: tuple[str, ...]
    missing_evidence: tuple[str, ...]
    non_finite_fields: tuple[str, ...] = ()
    invalid_digest_fields: tuple[str, ...] = ()
    schema_version: str = "final_claim_validation_result_v1"

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "schema_version": self.schema_version,
            "passed": self.passed,
            "claim_eligible": self.claim_eligible,
            "reasons": list(self.reasons),
            "missing_evidence": list(self.missing_evidence),
            "non_finite_fields": list(self.non_finite_fields),
            "invalid_digest_fields": list(self.invalid_digest_fields),
        }

    def digest(self) -> str:
        return _strict_phase3_digest(self.to_dict())



_FINAL_RESEARCH_CLAIM_LEVEL_MARKERS = ("final", "research", "claim_ready", "alpha", "supported")


def _is_final_research_claim_level(level: str) -> bool:
    text = str(level).lower()
    return any(marker in text for marker in _FINAL_RESEARCH_CLAIM_LEVEL_MARKERS)


@dataclass(frozen=True, slots=True)
class FinalClaimManifest:
    claim_id: str
    claim_text: str
    claim_level: str
    allowed: bool
    required_evidence: tuple[str, ...]
    available_evidence: tuple[str, ...]
    missing_evidence: tuple[str, ...]
    replay_bundle_digest: str
    claim_gate_decision_digest: str
    evidence_lineage_path: tuple[str, ...]
    effect_size: float = 0.0
    ci_low: float = 0.0
    ci_high: float = 0.0
    validation_reasons: tuple[str, ...] = ()
    schema_version: str = "final_claim_manifest_v2"

    def __post_init__(self) -> None:
        required = tuple(sorted(set(str(item) for item in self.required_evidence)))
        available = tuple(sorted(set(str(item) for item in self.available_evidence)))
        computed_missing = tuple(sorted(set(required) - set(available)))
        reasons = set(str(item) for item in self.validation_reasons)
        object.__setattr__(self, "required_evidence", required)
        object.__setattr__(self, "available_evidence", available)
        object.__setattr__(self, "missing_evidence", computed_missing)
        object.__setattr__(self, "effect_size", _phase3_finite("effect_size", self.effect_size))
        object.__setattr__(self, "ci_low", _phase3_finite("ci_low", self.ci_low))
        object.__setattr__(self, "ci_high", _phase3_finite("ci_high", self.ci_high))
        if self.ci_low > self.ci_high:
            raise ConfigurationError("invalid_confidence_interval")
        if computed_missing:
            reasons.add("missing_required_evidence")
        if self.allowed and not required:
            raise ConfigurationError("missing_required_evidence_contract")
        if not self.allowed and _is_final_research_claim_level(self.claim_level) and not required:
            reasons.add("missing_required_evidence_contract")
        if not self.evidence_lineage_path:
            reasons.add("missing_evidence_lineage_path")
        else:
            invalid_lineage = tuple(
                item for item in self.evidence_lineage_path if not _strict_is_real_digest(item)
            )
            if invalid_lineage:
                if self.allowed:
                    raise ConfigurationError("invalid_evidence_lineage_path")
                reasons.add("invalid_evidence_lineage_path")
        if not _strict_is_real_digest(self.replay_bundle_digest):
            reasons.add("missing_replay_bundle_digest")
        if not _strict_is_real_digest(self.claim_gate_decision_digest):
            reasons.add("missing_claim_gate_decision_digest")
        if self.allowed and reasons:
            reasons.add("claim_downgraded_missing_final_evidence")
            object.__setattr__(self, "allowed", False)
        object.__setattr__(self, "validation_reasons", tuple(sorted(reasons)))

    @property
    def claim_eligible(self) -> bool:
        return bool(self.allowed and not self.validation_reasons and not self.missing_evidence)

    def validate(self, *, strict: bool = True) -> FinalClaimValidationResult:
        reasons = set(self.validation_reasons)
        invalid_digest_fields: list[str] = []
        if self.allowed or strict:
            for name in ("replay_bundle_digest", "claim_gate_decision_digest"):
                if not _strict_is_real_digest(getattr(self, name)):
                    invalid_digest_fields.append(name)
            for index, digest in enumerate(self.evidence_lineage_path):
                if not _strict_is_real_digest(digest):
                    invalid_digest_fields.append(f"evidence_lineage_path[{index}]")
        if invalid_digest_fields:
            reasons.update(f"invalid_{name}" for name in invalid_digest_fields)
        if self.ci_low > self.ci_high:
            reasons.add("invalid_confidence_interval")
        if self.missing_evidence:
            reasons.add("missing_required_evidence")
        passed = not reasons and (not strict or self.claim_eligible == self.allowed)
        return FinalClaimValidationResult(
            passed=passed,
            claim_eligible=self.claim_eligible,
            reasons=tuple(sorted(reasons)),
            missing_evidence=self.missing_evidence,
            invalid_digest_fields=tuple(invalid_digest_fields),
        )

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "schema_version": self.schema_version,
            "claim_id": self.claim_id,
            "claim_text": self.claim_text,
            "claim_level": self.claim_level,
            "allowed": self.allowed,
            "claim_eligible": self.claim_eligible,
            "required_evidence": list(self.required_evidence),
            "available_evidence": list(self.available_evidence),
            "missing_evidence": list(self.missing_evidence),
            "effect_size": self.effect_size,
            "confidence_interval": [self.ci_low, self.ci_high],
            "replay_bundle_digest": self.replay_bundle_digest,
            "claim_gate_decision_digest": self.claim_gate_decision_digest,
            "evidence_lineage_path": list(self.evidence_lineage_path),
            "validation_reasons": list(self.validation_reasons),
        }

    def digest(self) -> str:
        return _strict_phase3_digest(self.to_dict())


@dataclass(frozen=True, slots=True)
class ReleaseEvidencePack:
    release_label: str
    claim_manifests: tuple[FinalClaimManifest, ...]
    replay_bundle_index_digest: str
    ablation_matrix_digest: str
    status: str = "claim_ready"
    validation_result_digest: str = ""
    validation_passed: bool = False
    validation_reasons: tuple[str, ...] = ()
    schema_version: str = "release_evidence_pack_v2"

    def __post_init__(self) -> None:
        _require_phase3_status("ReleaseEvidencePack.status", self.status)
        claim_manifests = tuple(self.claim_manifests)
        object.__setattr__(self, "claim_manifests", claim_manifests)
        _strict_require_real_digest("replay_bundle_index_digest", self.replay_bundle_index_digest)
        _strict_require_real_digest("ablation_matrix_digest", self.ablation_matrix_digest)
        reasons = set(str(item) for item in self.validation_reasons)
        for index, claim in enumerate(claim_manifests):
            result = claim.validate(strict=True)
            if claim.allowed and not result.passed:
                reasons.add(f"invalid_allowed_claim_{index}")
            reasons.update(f"claim_{index}:{reason}" for reason in result.reasons)
        any_allowed = any(claim.claim_eligible for claim in claim_manifests)
        if not any_allowed:
            object.__setattr__(self, "status", "negative_result_pack")
            reasons.add("no_final_claim_allowed")
        elif reasons:
            object.__setattr__(self, "status", "incomplete_evidence")
        validation_payload = {
            "release_label": self.release_label,
            "status": self.status,
            "claim_digests": [claim.digest() for claim in claim_manifests],
            "reasons": sorted(reasons),
        }
        computed_validation_digest = _strict_phase3_digest(validation_payload)
        if self.validation_result_digest and self.validation_result_digest != computed_validation_digest:
            raise ConfigurationError("validation_result_digest mismatch")
        object.__setattr__(self, "validation_result_digest", computed_validation_digest)
        object.__setattr__(self, "validation_passed", not reasons)
        object.__setattr__(self, "validation_reasons", tuple(sorted(reasons)))
        if any_allowed and not self.validation_passed:
            raise ConfigurationError("ReleaseEvidencePack contains invalid allowed claims")

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "schema_version": self.schema_version,
            "release_label": self.release_label,
            "status": self.status,
            "claim_manifests": [c.to_dict() for c in self.claim_manifests],
            "replay_bundle_index_digest": self.replay_bundle_index_digest,
            "ablation_matrix_digest": self.ablation_matrix_digest,
            "validation_result_digest": self.validation_result_digest,
            "validation_passed": self.validation_passed,
            "validation_reasons": list(self.validation_reasons),
        }

    def digest(self) -> str:
        return _strict_phase3_digest(self.to_dict())


def validate_final_claim_manifest(
    manifest: FinalClaimManifest, *, strict: bool = True
) -> FinalClaimValidationResult:
    return manifest.validate(strict=strict)



def _str_nonempty(name: str, value: object) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ConfigurationError(f"{name} must be a non-empty string.")
    return value.strip()


def _str_tuple_nonempty(name: str, values: tuple[str, ...]) -> tuple[str, ...]:
    out = tuple(_str_nonempty(f"{name}[{index}]", item) for index, item in enumerate(values))
    if not out:
        raise ConfigurationError(f"{name} must not be empty.")
    return out


def _real_digest_tuple(name: str, values: tuple[str, ...]) -> tuple[str, ...]:
    out = tuple(str(item).strip() for item in values)
    if not out:
        raise ConfigurationError(f"{name} must not be empty.")
    for index, value in enumerate(out):
        _strict_require_real_digest(f"{name}[{index}]", value)
    return out


@dataclass(frozen=True, slots=True)
class ReplayBundleIndex:
    replay_bundle_digests: tuple[str, ...]
    scenario_ids: tuple[str, ...]
    seed_ids: tuple[int, ...]
    seed_plan_digest: str
    config_digest: str
    availability_status: str = "measured"
    schema_version: str = "replay_bundle_index_v1"

    def __post_init__(self) -> None:
        object.__setattr__(self, "replay_bundle_digests", _real_digest_tuple("replay_bundle_digests", self.replay_bundle_digests))
        object.__setattr__(self, "scenario_ids", _str_tuple_nonempty("scenario_ids", self.scenario_ids))
        object.__setattr__(self, "seed_ids", tuple(int(seed) for seed in self.seed_ids))
        if not self.seed_ids:
            raise ConfigurationError("seed_ids must not be empty.")
        _strict_require_real_digest("seed_plan_digest", self.seed_plan_digest)
        _strict_require_real_digest("config_digest", self.config_digest)
        _require_phase3_status("ReplayBundleIndex.availability_status", self.availability_status)

    @property
    def replay_bundle_count(self) -> int:
        return len(self.replay_bundle_digests)

    def validate(self) -> FinalClaimValidationResult:
        reasons: list[str] = []
        if len(self.replay_bundle_digests) != len(self.seed_ids):
            reasons.append("replay_seed_count_mismatch")
        if self.availability_status in {"not_run", "disabled_by_config", "placeholder_digest_rejected"}:
            reasons.append("replay_bundle_unavailable")
        return FinalClaimValidationResult(not reasons, not reasons, tuple(reasons), ())

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "schema_version": self.schema_version,
            "replay_bundle_digests": list(self.replay_bundle_digests),
            "replay_bundle_count": self.replay_bundle_count,
            "scenario_ids": list(self.scenario_ids),
            "seed_ids": list(self.seed_ids),
            "seed_plan_digest": self.seed_plan_digest,
            "config_digest": self.config_digest,
            "availability_status": self.availability_status,
        }

    def digest(self) -> str:
        return _strict_phase3_digest(self.to_dict())


@dataclass(frozen=True, slots=True)
class BenchmarkLeaderboardArtifact:
    scenario_id: str
    metric_names: tuple[str, ...]
    seed_count: int
    seed_policy_digest: str
    ranking_method: str
    effect_size: float
    ci_low: float
    ci_high: float
    confidence_interval_status: str = "measured"
    downgrade_status: str = "not_applicable"
    schema_version: str = "benchmark_leaderboard_artifact_v1"

    def __post_init__(self) -> None:
        object.__setattr__(self, "scenario_id", _str_nonempty("scenario_id", self.scenario_id))
        object.__setattr__(self, "metric_names", _str_tuple_nonempty("metric_names", self.metric_names))
        if int(self.seed_count) < 0:
            raise ConfigurationError("seed_count must be non-negative.")
        object.__setattr__(self, "seed_count", int(self.seed_count))
        _strict_require_real_digest("seed_policy_digest", self.seed_policy_digest)
        object.__setattr__(self, "ranking_method", _str_nonempty("ranking_method", self.ranking_method))
        object.__setattr__(self, "effect_size", _phase3_finite("effect_size", self.effect_size))
        object.__setattr__(self, "ci_low", _phase3_finite("ci_low", self.ci_low))
        object.__setattr__(self, "ci_high", _phase3_finite("ci_high", self.ci_high))
        if self.ci_low > self.ci_high:
            raise ConfigurationError("invalid_confidence_interval")
        _require_phase3_status("BenchmarkLeaderboardArtifact.confidence_interval_status", self.confidence_interval_status)
        _require_phase3_status("BenchmarkLeaderboardArtifact.downgrade_status", self.downgrade_status)

    def validate(self) -> FinalClaimValidationResult:
        reasons = [] if self.seed_count > 0 else ["missing_seed_count"]
        return FinalClaimValidationResult(not reasons, not reasons, tuple(reasons), ())

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "schema_version": self.schema_version,
            "scenario_id": self.scenario_id,
            "metric_names": list(self.metric_names),
            "seed_count": self.seed_count,
            "seed_policy_digest": self.seed_policy_digest,
            "ranking_method": self.ranking_method,
            "effect_size": self.effect_size,
            "confidence_interval": [self.ci_low, self.ci_high],
            "confidence_interval_status": self.confidence_interval_status,
            "downgrade_status": self.downgrade_status,
        }

    def digest(self) -> str:
        return _strict_phase3_digest(self.to_dict())


@dataclass(frozen=True, slots=True)
class AblationMatrixArtifact:
    ablation_factors: tuple[str, ...]
    baseline_digest: str
    treatment_digest: str
    ablated_component: str
    effect_size: float
    ci_low: float
    ci_high: float
    negative_control_digests: tuple[str, ...] = ()
    status: str = "measured"
    schema_version: str = "ablation_matrix_artifact_v1"

    def __post_init__(self) -> None:
        object.__setattr__(self, "ablation_factors", _str_tuple_nonempty("ablation_factors", self.ablation_factors))
        _strict_require_real_digest("baseline_digest", self.baseline_digest)
        _strict_require_real_digest("treatment_digest", self.treatment_digest)
        object.__setattr__(self, "ablated_component", _str_nonempty("ablated_component", self.ablated_component))
        object.__setattr__(self, "effect_size", _phase3_finite("effect_size", self.effect_size))
        object.__setattr__(self, "ci_low", _phase3_finite("ci_low", self.ci_low))
        object.__setattr__(self, "ci_high", _phase3_finite("ci_high", self.ci_high))
        if self.ci_low > self.ci_high:
            raise ConfigurationError("invalid_confidence_interval")
        if self.negative_control_digests:
            object.__setattr__(self, "negative_control_digests", _real_digest_tuple("negative_control_digests", self.negative_control_digests))
        _require_phase3_status("AblationMatrixArtifact.status", self.status)

    def validate(self) -> FinalClaimValidationResult:
        reasons = [] if self.negative_control_digests else ["missing_negative_controls"]
        return FinalClaimValidationResult(not reasons, not reasons, tuple(reasons), ())

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "schema_version": self.schema_version,
            "ablation_factors": list(self.ablation_factors),
            "baseline_digest": self.baseline_digest,
            "treatment_digest": self.treatment_digest,
            "ablated_component": self.ablated_component,
            "effect_size": self.effect_size,
            "confidence_interval": [self.ci_low, self.ci_high],
            "negative_control_digests": list(self.negative_control_digests),
            "status": self.status,
        }

    def digest(self) -> str:
        return _strict_phase3_digest(self.to_dict())


@dataclass(frozen=True, slots=True)
class ClaimDowngradeReport:
    requested_claim: str
    achieved_claim: str
    missing_evidence: tuple[str, ...]
    downgrade_reason: str
    claim_gate_digest: str
    status: str = "incomplete_evidence"
    schema_version: str = "claim_downgrade_report_v1"

    def __post_init__(self) -> None:
        object.__setattr__(self, "requested_claim", _str_nonempty("requested_claim", self.requested_claim))
        object.__setattr__(self, "achieved_claim", _str_nonempty("achieved_claim", self.achieved_claim))
        object.__setattr__(self, "missing_evidence", tuple(str(item) for item in self.missing_evidence))
        object.__setattr__(self, "downgrade_reason", _str_nonempty("downgrade_reason", self.downgrade_reason))
        _strict_require_real_digest("claim_gate_digest", self.claim_gate_digest)
        _require_phase3_status("ClaimDowngradeReport.status", self.status)

    def validate(self) -> FinalClaimValidationResult:
        reasons = [] if self.requested_claim != self.achieved_claim else ["no_downgrade_recorded"]
        if not self.missing_evidence:
            reasons.append("missing_evidence_not_recorded")
        return FinalClaimValidationResult(not reasons, False, tuple(reasons), self.missing_evidence)

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "schema_version": self.schema_version,
            "requested_claim": self.requested_claim,
            "achieved_claim": self.achieved_claim,
            "missing_evidence": list(self.missing_evidence),
            "downgrade_reason": self.downgrade_reason,
            "claim_gate_digest": self.claim_gate_digest,
            "status": self.status,
        }

    def digest(self) -> str:
        return _strict_phase3_digest(self.to_dict())


@dataclass(frozen=True, slots=True)
class NegativeResultReport:
    rejected_claim: str
    evidence_present: tuple[str, ...]
    evidence_missing: tuple[str, ...]
    scientific_value: str
    claim_gate_digest: str
    replay_digest: str
    status: str = "negative_result_pack"
    schema_version: str = "negative_result_report_v1"

    def __post_init__(self) -> None:
        object.__setattr__(self, "rejected_claim", _str_nonempty("rejected_claim", self.rejected_claim))
        object.__setattr__(self, "evidence_present", tuple(str(item) for item in self.evidence_present))
        object.__setattr__(self, "evidence_missing", tuple(str(item) for item in self.evidence_missing))
        object.__setattr__(self, "scientific_value", _str_nonempty("scientific_value", self.scientific_value))
        _strict_require_real_digest("claim_gate_digest", self.claim_gate_digest)
        _strict_require_real_digest("replay_digest", self.replay_digest)
        _require_phase3_status("NegativeResultReport.status", self.status)

    def validate(self) -> FinalClaimValidationResult:
        reasons = [] if self.evidence_missing else ["negative_result_without_missing_evidence"]
        return FinalClaimValidationResult(not reasons, False, tuple(reasons), self.evidence_missing)

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "schema_version": self.schema_version,
            "rejected_claim": self.rejected_claim,
            "evidence_present": list(self.evidence_present),
            "evidence_missing": list(self.evidence_missing),
            "scientific_value": self.scientific_value,
            "claim_gate_digest": self.claim_gate_digest,
            "replay_digest": self.replay_digest,
            "status": self.status,
        }

    def digest(self) -> str:
        return _strict_phase3_digest(self.to_dict())


@dataclass(frozen=True, slots=True)
class Phase3ScientificSummary:
    release_label: str
    replay_bundle_index_digest: str
    benchmark_leaderboard_digest: str
    ablation_matrix_digest: str
    accepted_claims: tuple[str, ...] = ()
    downgraded_claims: tuple[str, ...] = ()
    negative_result_digests: tuple[str, ...] = ()
    status: str = "claim_ready"
    schema_version: str = "phase3_scientific_summary_v1"

    def __post_init__(self) -> None:
        object.__setattr__(self, "release_label", _str_nonempty("release_label", self.release_label))
        _strict_require_real_digest("replay_bundle_index_digest", self.replay_bundle_index_digest)
        _strict_require_real_digest("benchmark_leaderboard_digest", self.benchmark_leaderboard_digest)
        _strict_require_real_digest("ablation_matrix_digest", self.ablation_matrix_digest)
        object.__setattr__(self, "accepted_claims", tuple(str(item) for item in self.accepted_claims))
        object.__setattr__(self, "downgraded_claims", tuple(str(item) for item in self.downgraded_claims))
        if self.negative_result_digests:
            object.__setattr__(self, "negative_result_digests", _real_digest_tuple("negative_result_digests", self.negative_result_digests))
        _require_phase3_status("Phase3ScientificSummary.status", self.status)
        forbidden = ("fake", "placeholder", "not_run")
        for claim in self.accepted_claims:
            if any(marker in claim.lower() for marker in forbidden):
                raise ConfigurationError("accepted_claims must not contain fake/not_run/placeholder markers")

    def validate(self) -> FinalClaimValidationResult:
        reasons: list[str] = []
        if not self.accepted_claims and not self.downgraded_claims and not self.negative_result_digests:
            reasons.append("empty_scientific_summary")
        return FinalClaimValidationResult(not reasons, bool(self.accepted_claims and not reasons), tuple(reasons), ())

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "schema_version": self.schema_version,
            "release_label": self.release_label,
            "replay_bundle_index_digest": self.replay_bundle_index_digest,
            "benchmark_leaderboard_digest": self.benchmark_leaderboard_digest,
            "ablation_matrix_digest": self.ablation_matrix_digest,
            "accepted_claims": list(self.accepted_claims),
            "downgraded_claims": list(self.downgraded_claims),
            "negative_result_digests": list(self.negative_result_digests),
            "status": self.status,
        }

    def digest(self) -> str:
        return _strict_phase3_digest(self.to_dict())
