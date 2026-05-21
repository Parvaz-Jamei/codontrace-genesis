"""ADF candidate validation with deterministic null-model controls."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from enum import Enum

from codontrace._types import JsonValue
from codontrace.genesis.adf_runtime import ADFMacroDefinition


class ADFClaimDecision(str, Enum):
    PATTERN_CANDIDATE = "pattern_candidate"
    MACRO_SUPPORTED = "adf_macro_supported"
    LANGUAGE_EMERGENCE_NOT_CLAIMED = "language_emergence_not_claimed"


@dataclass(frozen=True, slots=True)
class ADFValidationControls:
    permutation_controls: int = 8
    random_baseline_controls: int = 8
    min_support_delta: int = 1
    require_ablation: bool = True
    require_compression_gain: bool = True

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "permutation_controls": self.permutation_controls,
            "random_baseline_controls": self.random_baseline_controls,
            "min_support_delta": self.min_support_delta,
            "require_ablation": self.require_ablation,
            "require_compression_gain": self.require_compression_gain,
        }


@dataclass(frozen=True, slots=True)
class ADFNullModelReport:
    observed_support: int
    permutation_support: int
    random_genome_support: int
    passed: bool

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "observed_support": self.observed_support,
            "permutation_support": self.permutation_support,
            "random_genome_support": self.random_genome_support,
            "passed": self.passed,
        }


@dataclass(frozen=True, slots=True)
class ADFAblationReport:
    with_adf_metric: float
    without_adf_metric: float
    metric_name: str = "fitness"

    @property
    def delta(self) -> float:
        return round(self.with_adf_metric - self.without_adf_metric, 10)

    @property
    def passed(self) -> bool:
        return self.delta > 0

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "metric_name": self.metric_name,
            "with_adf_metric": self.with_adf_metric,
            "without_adf_metric": self.without_adf_metric,
            "delta": self.delta,
            "passed": self.passed,
        }


@dataclass(frozen=True, slots=True)
class ADFProposalValidation:
    candidate: ADFMacroDefinition
    null_model: ADFNullModelReport
    ablation: ADFAblationReport | None
    compression_gain: float
    decision: ADFClaimDecision
    limitations: tuple[str, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "candidate": self.candidate.to_dict(),
            "null_model": self.null_model.to_dict(),
            "ablation": None if self.ablation is None else self.ablation.to_dict(),
            "compression_gain": self.compression_gain,
            "decision": self.decision.value,
            "limitations": list(self.limitations),
        }

    def digest(self) -> str:
        return _digest(self.to_dict())


def validate_adf_candidate(
    *,
    candidate: ADFMacroDefinition,
    traces: Sequence[Sequence[str]],
    controls: ADFValidationControls | None = None,
    ablation: ADFAblationReport | None = None,
) -> ADFProposalValidation:
    controls = controls or ADFValidationControls()
    pattern = candidate.primitive_actions
    observed = sum(_count_pattern(trace, pattern) for trace in traces)
    permutation = _permutation_control_support(traces, pattern, controls.permutation_controls)
    random_support = _random_baseline_support(traces, pattern, controls.random_baseline_controls)
    null_passed = (
        observed >= permutation + controls.min_support_delta
        and observed >= random_support + controls.min_support_delta
    )
    null_report = ADFNullModelReport(observed, permutation, random_support, null_passed)
    compression_gain = 0.0 if len(pattern) <= 1 else round((len(pattern) - 1) / len(pattern), 10)
    limitations: list[str] = ["adf_validation_does_not_prove_language_emergence"]
    ablation_ok = ablation is not None and ablation.passed
    compression_ok = (not controls.require_compression_gain) or compression_gain > 0
    if null_passed and compression_ok and ((not controls.require_ablation) or ablation_ok):
        decision = ADFClaimDecision.MACRO_SUPPORTED
    else:
        decision = ADFClaimDecision.PATTERN_CANDIDATE
        if controls.require_ablation and ablation is None:
            limitations.append("missing_ablation_control")
        if not null_passed:
            limitations.append("null_model_not_passed")
    return ADFProposalValidation(
        candidate, null_report, ablation, compression_gain, decision, tuple(limitations)
    )


def _count_pattern(trace: Sequence[str], pattern: Sequence[str]) -> int:
    if not pattern or len(trace) < len(pattern):
        return 0
    return sum(
        1
        for index in range(len(trace) - len(pattern) + 1)
        if tuple(trace[index : index + len(pattern)]) == tuple(pattern)
    )


def _permutation_control_support(
    traces: Sequence[Sequence[str]], pattern: Sequence[str], rounds: int
) -> int:
    if rounds <= 0:
        return 0
    total = 0
    for trace in traces:
        values = list(trace)
        if not values:
            continue
        best = 0
        for shift in range(min(rounds, len(values))):
            rotated = values[shift:] + values[:shift]
            if shift % 2:
                rotated = list(reversed(rotated))
            best = max(best, _count_pattern(rotated, pattern))
        total += best
    return total


def _random_baseline_support(
    traces: Sequence[Sequence[str]], pattern: Sequence[str], rounds: int
) -> int:
    alphabet = sorted({action for trace in traces for action in trace} | set(pattern))
    if not alphabet or rounds <= 0:
        return 0
    support = 0
    for trace_index, trace in enumerate(traces):
        generated = [alphabet[(trace_index + idx) % len(alphabet)] for idx in range(len(trace))]
        support += _count_pattern(generated, pattern)
    return support


def _digest(payload: Mapping[str, JsonValue]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()
