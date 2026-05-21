"""Publication-safe scientific evidence pack objects for GENESIS.

The objects in this module summarize D0, QD, ablation, witness, validation, and
limitation evidence. They do not prove discovery, generate reports, run
experiments, write files, compute p-values, or provide benchmark-superiority
claims.
"""

from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import TypeVar

from codontrace._types import JsonValue
from codontrace.errors import ConfigurationError
from codontrace.genesis.limitations import LimitationRecord, LimitationSeverity
from codontrace.genesis.validation_matrix import ValidationMatrixResult

_CEILINGS = ("NONE", "CANDIDATE", "EVIDENCE_SUPPORTED")
_T = TypeVar("_T")


@dataclass(frozen=True, slots=True)
class D0EvidenceSummary:
    baseline_digest: str
    run_count: int
    seed_count: int
    descriptor_names: tuple[str, ...]
    distance_metric: str
    threshold_summary: str
    limitations: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _positive_int(self.run_count, "D0EvidenceSummary.run_count", allow_zero=True)
        _positive_int(self.seed_count, "D0EvidenceSummary.seed_count", allow_zero=True)

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "baseline_digest": self.baseline_digest,
            "run_count": self.run_count,
            "seed_count": self.seed_count,
            "descriptor_names": list(self.descriptor_names),
            "distance_metric": self.distance_metric,
            "threshold_summary": self.threshold_summary,
            "limitations": list(self.limitations),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, JsonValue]) -> D0EvidenceSummary:
        return cls(
            _str(data, "baseline_digest", ""),
            _int(data, "run_count", 0),
            _int(data, "seed_count", 0),
            _str_tuple(data, "descriptor_names"),
            _str(data, "distance_metric", ""),
            _str(data, "threshold_summary", ""),
            _str_tuple(data, "limitations"),
        )

    def digest(self) -> str:
        return _digest(self.to_dict())


@dataclass(frozen=True, slots=True)
class QDEvidenceSummary:
    archive_digest: str
    filled_bins: int
    total_bins: int
    coverage: float
    qd_score: float
    best_fitness: float | None
    rejected_count: int
    descriptor_schema_digest: str
    limitations: tuple[str, ...] = ()
    seed_count: int = 0

    def __post_init__(self) -> None:
        _positive_int(self.filled_bins, "QDEvidenceSummary.filled_bins", allow_zero=True)
        _positive_int(self.total_bins, "QDEvidenceSummary.total_bins", allow_zero=True)
        _positive_int(self.rejected_count, "QDEvidenceSummary.rejected_count", allow_zero=True)
        _positive_int(self.seed_count, "QDEvidenceSummary.seed_count", allow_zero=True)
        if self.total_bins <= 0 and self.filled_bins > 0:
            raise ConfigurationError(
                "QDEvidenceSummary.total_bins must be > 0 when bins are filled."
            )
        if self.total_bins > 0 and self.filled_bins > self.total_bins:
            raise ConfigurationError("QDEvidenceSummary.filled_bins must be <= total_bins.")
        if not math.isfinite(self.coverage) or not 0.0 <= self.coverage <= 1.0:
            raise ConfigurationError("QDEvidenceSummary.coverage must be finite and in [0, 1].")
        if self.total_bins > 0:
            expected = self.filled_bins / self.total_bins
            if abs(self.coverage - expected) > 1e-9:
                raise ConfigurationError(
                    "QDEvidenceSummary.coverage must equal filled_bins / total_bins."
                )
        if not math.isfinite(self.qd_score):
            raise ConfigurationError("QDEvidenceSummary.qd_score must be finite.")
        if self.best_fitness is not None and not math.isfinite(self.best_fitness):
            raise ConfigurationError("QDEvidenceSummary.best_fitness must be finite or None.")

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "archive_digest": self.archive_digest,
            "filled_bins": self.filled_bins,
            "total_bins": self.total_bins,
            "coverage": self.coverage,
            "qd_score": self.qd_score,
            "best_fitness": self.best_fitness,
            "rejected_count": self.rejected_count,
            "descriptor_schema_digest": self.descriptor_schema_digest,
            "limitations": list(self.limitations),
            "seed_count": self.seed_count,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, JsonValue]) -> QDEvidenceSummary:
        return cls(
            _str(data, "archive_digest", ""),
            _int(data, "filled_bins", 0),
            _int(data, "total_bins", 0),
            _float(data, "coverage", 0.0),
            _float(data, "qd_score", 0.0),
            _optional_float(data.get("best_fitness"), "best_fitness"),
            _int(data, "rejected_count", 0),
            _str(data, "descriptor_schema_digest", ""),
            _str_tuple(data, "limitations"),
            _int(data, "seed_count", 0),
        )

    def digest(self) -> str:
        return _digest(self.to_dict())


@dataclass(frozen=True, slots=True)
class AblationEvidenceSummary:
    comparison_digest: str
    baseline_factor_id: str
    compared_factor_ids: tuple[str, ...]
    seed_count: int
    mean_deltas: dict[str, float]
    median_deltas: dict[str, float]
    limitations: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _positive_int(self.seed_count, "AblationEvidenceSummary.seed_count", allow_zero=True)
        object.__setattr__(self, "mean_deltas", dict(self.mean_deltas))
        object.__setattr__(self, "median_deltas", dict(self.median_deltas))

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "comparison_digest": self.comparison_digest,
            "baseline_factor_id": self.baseline_factor_id,
            "compared_factor_ids": list(self.compared_factor_ids),
            "seed_count": self.seed_count,
            "mean_deltas": dict(sorted(self.mean_deltas.items())),
            "median_deltas": dict(sorted(self.median_deltas.items())),
            "limitations": list(self.limitations),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, JsonValue]) -> AblationEvidenceSummary:
        return cls(
            _str(data, "comparison_digest", ""),
            _str(data, "baseline_factor_id", ""),
            _str_tuple(data, "compared_factor_ids"),
            _int(data, "seed_count", 0),
            _float_map(data.get("mean_deltas"), "mean_deltas"),
            _float_map(data.get("median_deltas"), "median_deltas"),
            _str_tuple(data, "limitations"),
        )

    def digest(self) -> str:
        return _digest(self.to_dict())


@dataclass(frozen=True, slots=True)
class WitnessEvidenceSummary:
    witness_digest: str
    claim_level: str
    evidence_status: str
    baseline_digest: str
    trace_digest: str
    replay_digest: str
    ablation_validation_digest: str
    seed_count: int
    limitations: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _positive_int(self.seed_count, "WitnessEvidenceSummary.seed_count", allow_zero=True)
        if "PROOF" in self.claim_level.upper():
            raise ConfigurationError("WitnessEvidenceSummary.claim_level must not be proof-like.")

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "witness_digest": self.witness_digest,
            "claim_level": self.claim_level,
            "evidence_status": self.evidence_status,
            "baseline_digest": self.baseline_digest,
            "trace_digest": self.trace_digest,
            "replay_digest": self.replay_digest,
            "ablation_validation_digest": self.ablation_validation_digest,
            "seed_count": self.seed_count,
            "limitations": list(self.limitations),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, JsonValue]) -> WitnessEvidenceSummary:
        return cls(
            _str(data, "witness_digest", ""),
            _str(data, "claim_level", "CANDIDATE"),
            _str(data, "evidence_status", ""),
            _str(data, "baseline_digest", ""),
            _str(data, "trace_digest", ""),
            _str(data, "replay_digest", ""),
            _str(data, "ablation_validation_digest", ""),
            _int(data, "seed_count", 0),
            _str_tuple(data, "limitations"),
        )

    def digest(self) -> str:
        return _digest(self.to_dict())


@dataclass(frozen=True, slots=True)
class ScientificEvidencePack:
    pack_id: str
    version: str
    d0_summary: D0EvidenceSummary | None = None
    qd_summary: QDEvidenceSummary | None = None
    ablation_summary: AblationEvidenceSummary | None = None
    witness_summary: WitnessEvidenceSummary | None = None
    validation_matrix_digest: str = ""
    claim_audit_digest: str = ""
    limitation_ids: tuple[str, ...] = ()
    claim_ceiling: str = "CANDIDATE"
    replay_digest: str = ""

    def __post_init__(self) -> None:
        if not self.pack_id or not self.version:
            raise ConfigurationError("ScientificEvidencePack pack_id/version must not be empty.")
        if self.claim_ceiling not in _CEILINGS:
            raise ConfigurationError("ScientificEvidencePack.claim_ceiling must be conservative.")

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "pack_id": self.pack_id,
            "version": self.version,
            "d0_summary": None if self.d0_summary is None else self.d0_summary.to_dict(),
            "qd_summary": None if self.qd_summary is None else self.qd_summary.to_dict(),
            "ablation_summary": None
            if self.ablation_summary is None
            else self.ablation_summary.to_dict(),
            "witness_summary": None
            if self.witness_summary is None
            else self.witness_summary.to_dict(),
            "validation_matrix_digest": self.validation_matrix_digest,
            "claim_audit_digest": self.claim_audit_digest,
            "limitation_ids": list(self.limitation_ids),
            "claim_ceiling": self.claim_ceiling,
            "replay_digest": self.replay_digest,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, JsonValue]) -> ScientificEvidencePack:
        return cls(
            _str(data, "pack_id"),
            _str(data, "version"),
            _maybe(data.get("d0_summary"), D0EvidenceSummary.from_dict),
            _maybe(data.get("qd_summary"), QDEvidenceSummary.from_dict),
            _maybe(data.get("ablation_summary"), AblationEvidenceSummary.from_dict),
            _maybe(data.get("witness_summary"), WitnessEvidenceSummary.from_dict),
            _str(data, "validation_matrix_digest", ""),
            _str(data, "claim_audit_digest", ""),
            _str_tuple(data, "limitation_ids"),
            _str(data, "claim_ceiling", "CANDIDATE"),
            _str(data, "replay_digest", ""),
        )

    def digest(self) -> str:
        return _digest(self.to_dict())


@dataclass(frozen=True, slots=True)
class ClaimDowngradeRule:
    rule_id: str
    trigger: str
    from_ceiling: str
    to_ceiling: str
    reason: str

    def __post_init__(self) -> None:
        if not self.rule_id or not self.trigger:
            raise ConfigurationError("ClaimDowngradeRule rule_id/trigger must not be empty.")
        if self.from_ceiling not in _CEILINGS or self.to_ceiling not in _CEILINGS:
            raise ConfigurationError("ClaimDowngradeRule ceilings must be conservative.")

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "rule_id": self.rule_id,
            "trigger": self.trigger,
            "from_ceiling": self.from_ceiling,
            "to_ceiling": self.to_ceiling,
            "reason": self.reason,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, JsonValue]) -> ClaimDowngradeRule:
        return cls(
            _str(data, "rule_id"),
            _str(data, "trigger"),
            _str(data, "from_ceiling", "EVIDENCE_SUPPORTED"),
            _str(data, "to_ceiling", "CANDIDATE"),
            _str(data, "reason", ""),
        )

    def digest(self) -> str:
        return _digest(self.to_dict())


@dataclass(frozen=True, slots=True)
class ClaimDowngradeResult:
    original_ceiling: str
    final_ceiling: str
    applied_rules: tuple[ClaimDowngradeRule, ...]
    reasons: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.original_ceiling not in _CEILINGS or self.final_ceiling not in _CEILINGS:
            raise ConfigurationError("ClaimDowngradeResult ceilings must be conservative.")

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "original_ceiling": self.original_ceiling,
            "final_ceiling": self.final_ceiling,
            "applied_rules": [rule.to_dict() for rule in self.applied_rules],
            "reasons": list(self.reasons),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, JsonValue]) -> ClaimDowngradeResult:
        raw = data.get("applied_rules", [])
        if not isinstance(raw, list):
            raise ConfigurationError("ClaimDowngradeResult.applied_rules must be a list.")
        return cls(
            _str(data, "original_ceiling", "CANDIDATE"),
            _str(data, "final_ceiling", "CANDIDATE"),
            tuple(ClaimDowngradeRule.from_dict(_mapping(item, "rule")) for item in raw),
            _str_tuple(data, "reasons"),
        )

    def digest(self) -> str:
        return _digest(self.to_dict())


@dataclass(frozen=True, slots=True)
class EvidenceCompletenessScore:
    score_0_to_1: float
    required_items: tuple[str, ...]
    present_items: tuple[str, ...]
    missing_items: tuple[str, ...]
    warnings: tuple[str, ...] = ()
    duplicate_required_items: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not 0.0 <= self.score_0_to_1 <= 1.0:
            raise ConfigurationError("EvidenceCompletenessScore.score_0_to_1 must be in [0, 1].")

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "score_0_to_1": self.score_0_to_1,
            "required_items": list(self.required_items),
            "present_items": list(self.present_items),
            "missing_items": list(self.missing_items),
            "warnings": list(self.warnings),
            "duplicate_required_items": list(self.duplicate_required_items),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, JsonValue]) -> EvidenceCompletenessScore:
        return cls(
            _float(data, "score_0_to_1", 0.0),
            _str_tuple(data, "required_items"),
            _str_tuple(data, "present_items"),
            _str_tuple(data, "missing_items"),
            _str_tuple(data, "warnings"),
            _str_tuple(data, "duplicate_required_items"),
        )

    def digest(self) -> str:
        return _digest(self.to_dict())


def apply_claim_downgrade_rules(
    evidence_pack: ScientificEvidencePack,
    limitations: tuple[LimitationRecord, ...] = (),
    validation_result: ValidationMatrixResult | None = None,
) -> ClaimDowngradeResult:
    original = evidence_pack.claim_ceiling
    final = original
    applied: list[ClaimDowngradeRule] = []
    reasons: list[str] = []

    def apply(rule: ClaimDowngradeRule) -> None:
        nonlocal final
        if _rank(rule.to_ceiling) < _rank(final):
            final = rule.to_ceiling
        applied.append(rule)
        reasons.append(rule.trigger)

    if evidence_pack.d0_summary is None or not evidence_pack.d0_summary.baseline_digest:
        apply(
            ClaimDowngradeRule(
                "missing_d0",
                "missing_d0",
                original,
                "CANDIDATE",
                "Missing D0 evidence lowers claim ceiling.",
            )
        )
    if evidence_pack.ablation_summary is None:
        apply(
            ClaimDowngradeRule(
                "missing_ablation",
                "missing_ablation",
                original,
                "CANDIDATE",
                "Missing ablation evidence lowers claim ceiling.",
            )
        )
    if evidence_pack.witness_summary is None or not evidence_pack.witness_summary.replay_digest:
        apply(
            ClaimDowngradeRule(
                "missing_replay",
                "missing_replay",
                original,
                "CANDIDATE",
                "Missing replay-backed witness lowers claim ceiling.",
            )
        )
    for limitation in limitations:
        if limitation.severity == LimitationSeverity.CRITICAL:
            target = "NONE" if limitation.blocks_claims else "CANDIDATE"
            apply(
                ClaimDowngradeRule(
                    f"critical_{limitation.limitation_id}",
                    "critical_limitation",
                    original,
                    target,
                    limitation.impact,
                )
            )
    if validation_result is not None and not validation_result.succeeded:
        apply(
            ClaimDowngradeRule(
                "validation_matrix_failed",
                "validation_matrix_failed",
                original,
                "CANDIDATE",
                "Validation matrix failed.",
            )
        )
    return ClaimDowngradeResult(original, final, tuple(applied), tuple(reasons))


def score_evidence_completeness(
    evidence_pack: ScientificEvidencePack, profile: str | tuple[str, ...] = "mature_alpha"
) -> EvidenceCompletenessScore:
    required = _required_items(profile)
    duplicates = tuple(sorted({item for item in required if required.count(item) > 1}))
    if duplicates:
        raise ConfigurationError("Evidence completeness required_items must be unique.")
    present: list[str] = []
    if evidence_pack.d0_summary is not None and evidence_pack.d0_summary.baseline_digest:
        present.append("d0")
    if evidence_pack.qd_summary is not None and evidence_pack.qd_summary.archive_digest:
        present.append("qd")
    if (
        evidence_pack.ablation_summary is not None
        and evidence_pack.ablation_summary.comparison_digest
    ):
        present.append("ablation")
    if evidence_pack.witness_summary is not None and evidence_pack.witness_summary.witness_digest:
        present.append("witness")
    if evidence_pack.validation_matrix_digest:
        present.append("validation_matrix")
    if evidence_pack.claim_audit_digest:
        present.append("claim_audit")
    if evidence_pack.limitation_ids:
        present.append("limitations")
    if evidence_pack.replay_digest or (
        evidence_pack.witness_summary is not None and evidence_pack.witness_summary.replay_digest
    ):
        present.append("replay")
    present_set = set(present)
    missing = tuple(item for item in required if item not in present_set)
    score = 1.0 if not required else (len(required) - len(missing)) / len(required)
    warnings = ("completeness_only_not_truth_or_proof",)
    return EvidenceCompletenessScore(
        score, tuple(required), tuple(sorted(present_set)), missing, warnings, duplicates
    )


def _required_items(profile: str | tuple[str, ...]) -> tuple[str, ...]:
    if isinstance(profile, tuple):
        return profile
    if profile == "mature_alpha":
        return (
            "d0",
            "qd",
            "ablation",
            "witness",
            "validation_matrix",
            "claim_audit",
            "limitations",
        )
    if profile == "paper_ready":
        return (
            "d0",
            "qd",
            "ablation",
            "witness",
            "validation_matrix",
            "claim_audit",
            "limitations",
            "replay",
        )
    if profile == "prepublic":
        return ("claim_audit", "limitations")
    raise ConfigurationError("Unknown evidence completeness profile.")


@dataclass(frozen=True, slots=True)
class ScientificEvidenceProfile:
    profile_name: str
    require_d0: bool = False
    require_qd: bool = False
    require_ablation: bool = False
    require_witness: bool = False
    require_validation_matrix: bool = False
    require_claim_audit: bool = True
    require_limitations: bool = True
    min_seed_count: int = 1
    require_replay: bool = False

    def __post_init__(self) -> None:
        if self.profile_name not in {"prepublic", "mature_alpha", "paper_ready"}:
            raise ConfigurationError("Unsupported ScientificEvidenceProfile.profile_name.")
        _positive_int(self.min_seed_count, "ScientificEvidenceProfile.min_seed_count")

    @classmethod
    def prepublic(cls) -> ScientificEvidenceProfile:
        return cls("prepublic", require_claim_audit=True, require_limitations=False)

    @classmethod
    def mature_alpha(cls) -> ScientificEvidenceProfile:
        return cls(
            "mature_alpha",
            require_d0=True,
            require_qd=True,
            require_ablation=True,
            require_witness=True,
            require_validation_matrix=True,
            require_claim_audit=True,
            require_limitations=True,
            min_seed_count=3,
            require_replay=True,
        )

    @classmethod
    def paper_ready(cls) -> ScientificEvidenceProfile:
        return cls(
            "paper_ready",
            require_d0=True,
            require_qd=True,
            require_ablation=True,
            require_witness=True,
            require_validation_matrix=True,
            require_claim_audit=True,
            require_limitations=True,
            min_seed_count=5,
            require_replay=True,
        )

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "profile_name": self.profile_name,
            "require_d0": self.require_d0,
            "require_qd": self.require_qd,
            "require_ablation": self.require_ablation,
            "require_witness": self.require_witness,
            "require_validation_matrix": self.require_validation_matrix,
            "require_claim_audit": self.require_claim_audit,
            "require_limitations": self.require_limitations,
            "min_seed_count": self.min_seed_count,
            "require_replay": self.require_replay,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, JsonValue]) -> ScientificEvidenceProfile:
        return cls(
            _str(data, "profile_name"),
            _bool(data, "require_d0", False),
            _bool(data, "require_qd", False),
            _bool(data, "require_ablation", False),
            _bool(data, "require_witness", False),
            _bool(data, "require_validation_matrix", False),
            _bool(data, "require_claim_audit", True),
            _bool(data, "require_limitations", True),
            _int(data, "min_seed_count", 1),
            _bool(data, "require_replay", False),
        )

    def digest(self) -> str:
        return _digest(self.to_dict())


@dataclass(frozen=True, slots=True)
class ScientificEvidenceValidationResult:
    attempted: bool
    succeeded: bool
    profile_name: str
    missing_items: tuple[str, ...]
    warning_items: tuple[str, ...] = ()
    claim_ceiling: str = "CANDIDATE"
    reasons: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.claim_ceiling not in _CEILINGS:
            raise ConfigurationError(
                "ScientificEvidenceValidationResult.claim_ceiling must be conservative."
            )

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "attempted": self.attempted,
            "succeeded": self.succeeded,
            "profile_name": self.profile_name,
            "missing_items": list(self.missing_items),
            "warning_items": list(self.warning_items),
            "claim_ceiling": self.claim_ceiling,
            "reasons": list(self.reasons),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, JsonValue]) -> ScientificEvidenceValidationResult:
        return cls(
            _bool(data, "attempted", False),
            _bool(data, "succeeded", False),
            _str(data, "profile_name"),
            _str_tuple(data, "missing_items"),
            _str_tuple(data, "warning_items"),
            _str(data, "claim_ceiling", "CANDIDATE"),
            _str_tuple(data, "reasons"),
        )

    def digest(self) -> str:
        return _digest(self.to_dict())


def validate_scientific_evidence_pack(
    pack: ScientificEvidencePack, profile: ScientificEvidenceProfile | None = None
) -> ScientificEvidenceValidationResult:
    profile = profile or ScientificEvidenceProfile.prepublic()
    missing: list[str] = []
    warnings: list[str] = []
    if profile.require_d0 and pack.d0_summary is None:
        missing.append("d0")
    if profile.require_qd and pack.qd_summary is None:
        missing.append("qd")
    if profile.require_ablation and pack.ablation_summary is None:
        missing.append("ablation")
    if profile.require_witness and pack.witness_summary is None:
        missing.append("witness")
    if profile.require_validation_matrix and not pack.validation_matrix_digest:
        missing.append("validation_matrix")
    if profile.require_claim_audit and not pack.claim_audit_digest:
        missing.append("claim_audit")
    if profile.require_limitations and not pack.limitation_ids:
        missing.append("limitations")
    if profile.require_replay and (
        pack.witness_summary is None or not pack.witness_summary.replay_digest
    ):
        missing.append("replay")
    if (
        profile.require_d0
        and pack.d0_summary is not None
        and pack.d0_summary.seed_count < profile.min_seed_count
    ):
        missing.append("d0_multi_seed")
    if (
        profile.require_qd
        and pack.qd_summary is not None
        and pack.qd_summary.seed_count < profile.min_seed_count
    ):
        missing.append("qd_multi_seed")
    if (
        profile.require_ablation
        and pack.ablation_summary is not None
        and pack.ablation_summary.seed_count < profile.min_seed_count
    ):
        missing.append("ablation_multi_seed")
    if (
        profile.require_witness
        and pack.witness_summary is not None
        and pack.witness_summary.seed_count < profile.min_seed_count
    ):
        missing.append("witness_multi_seed")
    if profile.profile_name == "prepublic" and missing:
        warnings.extend(missing)
        missing = []
    ceiling = "EVIDENCE_SUPPORTED" if not missing else "CANDIDATE"
    if profile.profile_name == "prepublic" and warnings:
        ceiling = "CANDIDATE"
    reasons = tuple(sorted(set(missing))) if missing else ("scientific_evidence_validated",)
    if warnings and not missing:
        reasons = ("scientific_evidence_prepublic_warnings",)
    return ScientificEvidenceValidationResult(
        True,
        not missing,
        profile.profile_name,
        tuple(sorted(set(missing))),
        tuple(sorted(set(warnings))),
        ceiling,
        reasons,
    )


def _bool(data: Mapping[str, JsonValue], key: str, default: bool) -> bool:
    value = data.get(key, default)
    if not isinstance(value, bool):
        raise ConfigurationError(f"{key} must be a boolean.")
    return value


def _rank(ceiling: str) -> int:
    return _CEILINGS.index(ceiling)


def _positive_int(value: int, name: str, *, allow_zero: bool = False) -> None:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ConfigurationError(f"{name} must be an integer.")
    if value < 0 or (value == 0 and not allow_zero):
        raise ConfigurationError(f"{name} must be positive.")


def _maybe(value: JsonValue | None, factory: Callable[[Mapping[str, JsonValue]], _T]) -> _T | None:
    if value is None:
        return None
    if not isinstance(value, Mapping):
        raise ConfigurationError("Nested evidence summary must be an object or None.")
    return factory(value)


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


def _int(data: Mapping[str, JsonValue], key: str, default: int) -> int:
    value = data.get(key, default)
    if isinstance(value, bool) or not isinstance(value, int):
        raise ConfigurationError(f"{key} must be an integer.")
    return value


def _float(data: Mapping[str, JsonValue], key: str, default: float) -> float:
    value = data.get(key, default)
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise ConfigurationError(f"{key} must be numeric.")
    return float(value)


def _optional_float(value: JsonValue | None, name: str) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise ConfigurationError(f"{name} must be numeric or None.")
    return float(value)


def _str_tuple(data: Mapping[str, JsonValue], key: str) -> tuple[str, ...]:
    raw = data.get(key, [])
    if not isinstance(raw, list) or not all(isinstance(item, str) for item in raw):
        raise ConfigurationError(f"{key} must be a list of strings.")
    return tuple(str(item) for item in raw)


def _float_map(value: JsonValue | None, name: str) -> dict[str, float]:
    if value is None:
        return {}
    if not isinstance(value, Mapping):
        raise ConfigurationError(f"{name} must be an object.")
    out: dict[str, float] = {}
    for key, item in value.items():
        if not isinstance(key, str) or isinstance(item, bool) or not isinstance(item, int | float):
            raise ConfigurationError(f"{name} must map strings to numbers.")
        out[key] = float(item)
    return out
