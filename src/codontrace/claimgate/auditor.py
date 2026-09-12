"""Simulator-agnostic ClaimGate auditor.

Rules are CLAIMS.md §5 + §8. Forbidden aliases are never loosened.
Measurement neighbors (MODES, Channon 2024 Tokyo Type 1, ASME V&V 40)
do not grant a claim pass. Bitwise-identical outcomes across arms are
``assay_invalid`` (manipulation not realized), not a scientific null.
"""

from __future__ import annotations

import struct
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from codontrace._types import JsonValue
from codontrace.claimgate.ladder import (
    PUBLIC_CLAIM_LEVEL_NAMES,
    public_level_name,
    require_public_level,
)
from codontrace.claimgate.schema import (
    SOFTWARE_PACKAGE_DOI,
    ClaimgateBundle,
    ClaimgateComparison,
    parse_claimgate_bundle,
)
from codontrace.errors import ConfigurationError
from codontrace.genesis.canonical import canonical_digest, is_real_evidence_digest
from codontrace.genesis.claim_gate import (
    ClaimRequest,
    ScientificClaimGate,
    default_claim_gate_policy,
    normalize_claim_label,
)
from codontrace.genesis.statistical_protocol import validate_statistical_claim_inputs

ALPHA = 0.05
LEVEL4_MIN_SEEDS = 16
NEXT_REQUIREMENTS: dict[int, tuple[str, ...]] = {
    0: (
        "software_version",
        "recorded_source_or_artifact",
        "seed_list",
        "config_digest",
        "artifact_manifest",
        "runtime_records",
    ),
    1: (
        "treatment_and_control",
        "paired_comparison",
        "consistent_measured_difference",
    ),
    2: (
        "ablation_or_intervention",
        "negative_control",
        "replay_audit",
        "effect_direction",
        "artifact_completeness",
    ),
    3: (
        "confidence_interval",
        "seed_count_ge_16",
    ),
    4: (
        "archived_artifact_or_doi",
        "documented_limitations",
        "statistical_and_ablation_evidence",
    ),
    5: (),
}


@dataclass(frozen=True, slots=True)
class ClaimAuditReport:
    """Public 0–5 ClaimGate grade for one evidence bundle."""

    achieved_level: int
    missing_for_next: tuple[str, ...]
    warnings: tuple[str, ...]
    digest: str = ""
    public_name: str = ""
    schema_version: str = "claim_audit_report_v1"

    def __post_init__(self) -> None:
        level = require_public_level(self.achieved_level)
        object.__setattr__(self, "achieved_level", level)
        object.__setattr__(self, "public_name", public_level_name(level))
        object.__setattr__(
            self,
            "missing_for_next",
            tuple(sorted(str(item) for item in self.missing_for_next)),
        )
        object.__setattr__(
            self, "warnings", tuple(sorted(str(item) for item in self.warnings))
        )
        computed = canonical_digest(self._payload())
        if self.digest and self.digest != computed:
            raise ConfigurationError("ClaimAuditReport digest mismatch.")
        object.__setattr__(self, "digest", computed)

    def _payload(self) -> dict[str, JsonValue]:
        return {
            "schema_version": self.schema_version,
            "achieved_level": self.achieved_level,
            "public_name": self.public_name,
            "missing_for_next": list(self.missing_for_next),
            "warnings": list(self.warnings),
        }

    def to_dict(self) -> dict[str, JsonValue]:
        return {**self._payload(), "digest": self.digest}


def _roles(bundle: ClaimgateBundle) -> set[str]:
    return {arm.role for arm in bundle.arms}


def _has_runtime_records(bundle: ClaimgateBundle) -> bool:
    return any(values for outcome in bundle.outcomes for values in outcome.values_by_arm.values())


def _has_artifact_manifest(bundle: ClaimgateBundle) -> bool:
    return any(
        item.path and is_real_evidence_digest(item.sha256) for item in bundle.artifacts
    )


def _has_source_record(bundle: ClaimgateBundle) -> bool:
    if bundle.software.commit.strip() or bundle.software.name.strip():
        return True
    return _has_artifact_manifest(bundle)


def _ci_excludes_zero(low: float | None, high: float | None) -> bool:
    if low is None or high is None:
        return False
    return low > 0.0 or high < 0.0


def _comparison_has_difference(item: ClaimgateComparison) -> bool:
    if item.effect_size is None:
        return False
    if item.effect_size == 0.0:
        return False
    if item.ci_low is not None and item.ci_high is not None:
        return _ci_excludes_zero(item.ci_low, item.ci_high)
    if item.p is not None:
        return item.p < ALPHA
    return True


def _has_consistent_difference(bundle: ClaimgateBundle) -> bool:
    return any(_comparison_has_difference(item) for item in bundle.comparisons)


def _floats_bitwise_identical(values: list[float]) -> bool:
    if len(values) < 2:
        return False
    first = struct.pack("<d", values[0])
    return all(struct.pack("<d", item) == first for item in values)


def _primary_arm_means_bitwise_identical(bundle: ClaimgateBundle) -> bool:
    """True when the primary metric's arm-level means are bitwise identical."""

    if not bundle.outcomes:
        return False
    preferred = next(
        (
            outcome
            for outcome in bundle.outcomes
            if outcome.metric in {"terminal_mean_fitness", "fitness"}
        ),
        None,
    )
    outcome = preferred or bundle.outcomes[0]
    means: list[float] = []
    for values in outcome.values_by_arm.values():
        if not values:
            continue
        means.append(sum(values) / len(values))
    return _floats_bitwise_identical(means)


def _assay_invalid(bundle: ClaimgateBundle) -> bool:
    extra = bundle.extra or {}
    if extra.get("assay_invalid") is True:
        return True
    return _primary_arm_means_bitwise_identical(bundle)


def _he01_validity_required(bundle: ClaimgateBundle) -> bool:
    extra = bundle.extra or {}
    if extra.get("assay_validity_required") is True:
        return True
    if extra.get("adapter") == "codontrace_hard_experiment_01":
        return True
    if extra.get("next_generation_claim") is True:
        return True
    experiment = str(extra.get("experiment_id") or "")
    return experiment.startswith("hard_experiment_01")


def _within_arm_variance_positive(bundle: ClaimgateBundle) -> bool:
    if not bundle.outcomes:
        return False
    preferred = next(
        (
            outcome
            for outcome in bundle.outcomes
            if outcome.metric in {"terminal_mean_fitness", "fitness"}
        ),
        None,
    )
    outcome = preferred or bundle.outcomes[0]
    if not outcome.values_by_arm:
        return False
    for values in outcome.values_by_arm.values():
        if len(values) < 2:
            return False
        mean = sum(values) / len(values)
        if all(item == values[0] for item in values) or sum((item - mean) ** 2 for item in values) == 0.0:
            return False
    return True


def _he01_validity_failures(bundle: ClaimgateBundle) -> tuple[str, ...]:
    if not _he01_validity_required(bundle):
        return ()
    extra = bundle.extra or {}
    reasons: list[str] = []
    if extra.get("manipulation_check_passed") is not True:
        reasons.append("manipulation_check_not_passed")
    if extra.get("positive_control_detected") is not True:
        waiver = extra.get("positive_control_waiver")
        if not (isinstance(waiver, str) and waiver.strip()):
            reasons.append("positive_control_not_detected")
    if not _within_arm_variance_positive(bundle):
        reasons.append("within_arm_outcome_variance_zero")
    if extra.get("next_generation_claim") is True and extra.get("births_positive") is not True:
        reasons.append("births_not_positive")
    return tuple(reasons)


def _has_confidence_interval(bundle: ClaimgateBundle) -> bool:
    return any(
        item.ci_low is not None and item.ci_high is not None for item in bundle.comparisons
    )


def _has_paired_comparison(bundle: ClaimgateBundle) -> bool:
    names = {arm.name for arm in bundle.arms}
    return any(
        item.a in names and item.b in names and item.a != item.b
        for item in bundle.comparisons
    )


def _normalized_doi(value: str | None) -> str:
    if not value:
        return ""
    text = value.strip().lower()
    for prefix in ("https://doi.org/", "http://doi.org/", "doi:"):
        if text.startswith(prefix):
            text = text[len(prefix) :]
    return text


def _has_archived_doi(bundle: ClaimgateBundle) -> bool:
    doi = _normalized_doi(bundle.doi)
    if doi and doi != SOFTWARE_PACKAGE_DOI:
        return True
    for item in bundle.artifacts:
        path = item.path.strip().lower()
        archived_path = (
            "doi.org/" in path or "zenodo.org/records/" in path or path.startswith("doi:")
        )
        if archived_path and SOFTWARE_PACKAGE_DOI not in path:
            return True
    extra = bundle.extra or {}
    archived = extra.get("archived")
    extra_doi = extra.get("archive_doi") or extra.get("experiment_doi")
    extra_ok = (
        archived is True
        and isinstance(extra_doi, str)
        and _normalized_doi(extra_doi) not in {"", SOFTWARE_PACKAGE_DOI}
    )
    return extra_ok


def _bundle_flags(bundle: ClaimgateBundle) -> dict[str, bool]:
    extra = bundle.extra or {}
    flags: dict[str, bool] = {}
    for key, value in extra.items():
        if isinstance(value, bool):
            flags[str(key)] = value
    for name in (
        "tokyo_type1_passed",
        "tokyo_type_1_passed",
        "collective_intelligence",
        "agi",
        "avida_replacement",
        "intelligence",
    ):
        if extra.get(name) is True:
            flags[name] = True
    return flags


def _forbidden_hits(bundle: ClaimgateBundle) -> tuple[str, ...]:
    policy = default_claim_gate_policy()
    forbidden = set(policy.forbidden_aliases)
    hits: set[str] = set()
    extra = bundle.extra or {}
    for key, value in extra.items():
        label = normalize_claim_label(str(key))
        if label in forbidden and value is True:
            hits.add(label)
        if isinstance(value, str) and normalize_claim_label(value) in forbidden:
            hits.add(normalize_claim_label(value))
    requested = extra.get("requested_claim")
    if isinstance(requested, str) and normalize_claim_label(requested) in forbidden:
        hits.add(normalize_claim_label(requested))
    return tuple(sorted(hits))


def _neighbor_warnings(bundle: ClaimgateBundle) -> list[str]:
    warnings = [
        "asme_vv40_is_context_of_use_not_a_numeric_score",
        "modes_and_channon_tokyo_type1_are_measurement_neighbors_not_a_pass",
        "claimgate_rules_not_loosened",
    ]
    extra = bundle.extra or {}
    if extra.get("tokyo_type1_passed") is True or extra.get("oee_passed") is True:
        warnings.append("metrics_do_not_auto_grant_oee_or_tokyo_type1")
    if extra.get("assay_failed") is True:
        warnings.append("assay_failed_keeps_runtime_observation")
    validity = _he01_validity_failures(bundle)
    if _assay_invalid(bundle) or validity:
        warnings.append("assay_invalid_manipulation_not_realized")
        warnings.extend(f"assay_validity_{item}" for item in validity)
    elif bundle.comparisons and not _has_consistent_difference(bundle):
        warnings.append("no_consistent_measured_difference")
    if extra.get("arms_bitwise_identical_warning") is True:
        warnings.append("arms_bitwise_identical")
    if extra.get("adapter") == "avida_skeleton":
        warnings.append("avida_adapter_is_a_skeleton_not_full_support")
    if extra.get("adapter") == "mabe2_skeleton":
        warnings.append("mabe2_adapter_is_a_skeleton_not_full_support")
    return warnings


def _satisfied_flags(bundle: ClaimgateBundle) -> dict[str, bool]:
    roles = _roles(bundle)
    has_treatment = "treatment" in roles
    has_control = bool(roles & {"mechanism_ablation", "channel_off", "negative_control"})
    has_ablation = bool(roles & {"mechanism_ablation", "channel_off"})
    has_negative = "negative_control" in roles
    difference = _has_consistent_difference(bundle)
    return {
        "software_version": bool(bundle.software.version.strip()),
        "recorded_source_or_artifact": _has_source_record(bundle),
        "seed_list": bool(bundle.seeds),
        "config_digest": is_real_evidence_digest(bundle.config_digest),
        "artifact_manifest": _has_artifact_manifest(bundle),
        "runtime_records": _has_runtime_records(bundle),
        "treatment_and_control": has_treatment and has_control,
        "paired_comparison": _has_paired_comparison(bundle),
        "consistent_measured_difference": difference,
        "ablation_or_intervention": has_ablation,
        "negative_control": has_negative,
        "replay_audit": bundle.replay.verified and bool(bundle.replay.digests),
        "effect_direction": difference,
        "artifact_completeness": _has_artifact_manifest(bundle) and bool(bundle.limitations),
        "confidence_interval": _has_confidence_interval(bundle),
        "seed_count_ge_16": len(bundle.seeds) >= LEVEL4_MIN_SEEDS,
        "archived_artifact_or_doi": _has_archived_doi(bundle),
        "documented_limitations": bool(bundle.limitations),
        "statistical_and_ablation_evidence": difference
        and has_ablation
        and _has_confidence_interval(bundle),
    }


def _achieved_level(flags: Mapping[str, bool]) -> int:
    if not all(flags[name] for name in NEXT_REQUIREMENTS[0]):
        return 0
    if not all(flags[name] for name in NEXT_REQUIREMENTS[1]):
        return 1
    if not all(flags[name] for name in NEXT_REQUIREMENTS[2]):
        return 2
    if not all(flags[name] for name in NEXT_REQUIREMENTS[3]):
        return 3
    if not all(flags[name] for name in NEXT_REQUIREMENTS[4]):
        return 4
    return 5


def _assert_forbidden_still_blocked() -> None:
    gate = ScientificClaimGate()
    for label in (
        "collective_intelligence",
        "intelligence",
        "agi",
        "tokyo_type1_passed",
        "avida_replacement",
        "open_ended_intelligence",
    ):
        if gate.decide(ClaimRequest(label, {})).allowed:
            raise ConfigurationError(f"{label} must remain blocked.")


def audit_bundle(bundle: Mapping[str, Any] | ClaimgateBundle) -> ClaimAuditReport:
    """Grade a claimgate_bundle_v1. Deterministic. Rules = CLAIMS.md §5 + §8."""

    parsed = parse_claimgate_bundle(bundle)
    _assert_forbidden_still_blocked()
    flags = _satisfied_flags(parsed)
    extra = parsed.extra or {}
    validity = _he01_validity_failures(parsed)
    if extra.get("assay_failed") is True or _assay_invalid(parsed) or validity:
        flags["consistent_measured_difference"] = False
        flags["effect_direction"] = False
        flags["statistical_and_ablation_evidence"] = False
        if validity:
            extra = {**extra, "assay_invalid": True}
    hits = _forbidden_hits(parsed)
    if hits:
        flags["consistent_measured_difference"] = False
        flags["effect_direction"] = False
        flags["archived_artifact_or_doi"] = False
        flags["statistical_and_ablation_evidence"] = False
    level = _achieved_level(flags)
    missing = tuple(name for name in NEXT_REQUIREMENTS[level] if not flags.get(name, False))
    warnings = _neighbor_warnings(parsed)
    if hits:
        warnings.append("forbidden_alias_present_no_promotion:" + ",".join(hits))
    if extra.get("oee_metrics") or extra.get("tokyo_type1_metrics"):
        warnings.append("metrics_do_not_auto_grant_oee_or_tokyo_type1")
    if parsed.comparisons:
        first = parsed.comparisons[0]
        ok, reason = validate_statistical_claim_inputs(
            p_value=first.p,
            effect_size=first.effect_size,
            confidence_interval=(
                None
                if first.ci_low is None or first.ci_high is None
                else (first.ci_low, first.ci_high)
            ),
            replay_artifact_digest=parsed.replay.digests[0] if parsed.replay.digests else None,
            protocol_digest=parsed.config_digest,
            claim_gate_decision_digest=None,
        )
        if not ok and reason in {
            "non_finite_effect_size",
            "non_finite_confidence_interval",
            "invalid_confidence_interval",
            "p_value_out_of_range",
        }:
            warnings.append(f"statistical_input_{reason}")
    report = ClaimAuditReport(
        achieved_level=level,
        missing_for_next=missing,
        warnings=tuple(warnings),
    )
    if report.public_name not in PUBLIC_CLAIM_LEVEL_NAMES:
        raise ConfigurationError("auditor produced an unknown public level name.")
    return report
