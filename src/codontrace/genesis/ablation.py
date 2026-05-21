"""Dependency-free ablation protocol records for GENESIS research audits.

This module defines typed records and small deterministic comparison helpers. It
is not an experiment runner, report generator, or statistical significance
engine.
"""

from __future__ import annotations

import hashlib
import json
import statistics
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import cast

from codontrace._types import JsonValue
from codontrace.errors import ConfigurationError


@dataclass(frozen=True, slots=True)
class AblationFactor:
    """One controlled intervention or explicit control factor."""

    factor_id: str
    name: str
    disabled_components: tuple[str, ...] = ()
    config_overrides: dict[str, JsonValue] = field(default_factory=dict)
    rationale: str = ""
    factor_type: str = "mixed"

    def __post_init__(self) -> None:
        if not self.factor_id or not self.name:
            msg = "AblationFactor.factor_id and name must not be empty."
            raise ConfigurationError(msg)
        if self.factor_type not in {"control", "disable_component", "config_override", "mixed"}:
            msg = (
                "AblationFactor.factor_type must be control, disable_component, "
                "config_override, or mixed."
            )
            raise ConfigurationError(msg)
        copied_overrides = dict(self.config_overrides)
        object.__setattr__(self, "config_overrides", copied_overrides)
        has_disabled = bool(self.disabled_components)
        has_overrides = bool(copied_overrides)
        if self.factor_type == "control":
            return
        if self.factor_type == "disable_component" and not has_disabled:
            msg = "disable_component ablation factors require disabled_components."
            raise ConfigurationError(msg)
        if self.factor_type == "config_override" and not has_overrides:
            msg = "config_override ablation factors require config_overrides."
            raise ConfigurationError(msg)
        if self.factor_type == "mixed" and not (has_disabled or has_overrides):
            msg = "non-control ablation factors require disabled_components or config_overrides."
            raise ConfigurationError(msg)

    @classmethod
    def control(cls, factor_id: str = "baseline", name: str = "Baseline control") -> AblationFactor:
        return cls(factor_id=factor_id, name=name, factor_type="control")

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "factor_id": self.factor_id,
            "name": self.name,
            "disabled_components": list(self.disabled_components),
            "config_overrides": dict(sorted(self.config_overrides.items())),
            "rationale": self.rationale,
            "factor_type": self.factor_type,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, JsonValue]) -> AblationFactor:
        return cls(
            factor_id=_str(data, "factor_id"),
            name=_str(data, "name"),
            disabled_components=_str_tuple(data, "disabled_components"),
            config_overrides=_metadata(data.get("config_overrides", {})),
            rationale=_str(data, "rationale", ""),
            factor_type=_str(
                data,
                "factor_type",
                "control" if _str(data, "factor_id", "") == "baseline" else "mixed",
            ),
        )

    def digest(self) -> str:
        return _digest(self.to_dict())


@dataclass(frozen=True, slots=True)
class AblationRunRecord:
    """One run-level evidence record for an ablation factor."""

    run_id: str
    factor_id: str
    seed: int
    config_digest: str
    trace_digest: str
    behavior_digest: str
    fitness_score: float
    witness_digest: str = ""
    qd_archive_digest: str = ""
    metadata: dict[str, JsonValue] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.run_id or not self.factor_id:
            msg = "AblationRunRecord.run_id and factor_id must not be empty."
            raise ConfigurationError(msg)
        object.__setattr__(self, "metadata", dict(self.metadata))

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "run_id": self.run_id,
            "factor_id": self.factor_id,
            "seed": self.seed,
            "config_digest": self.config_digest,
            "trace_digest": self.trace_digest,
            "behavior_digest": self.behavior_digest,
            "fitness_score": self.fitness_score,
            "witness_digest": self.witness_digest,
            "qd_archive_digest": self.qd_archive_digest,
            "metadata": dict(sorted(self.metadata.items())),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, JsonValue]) -> AblationRunRecord:
        return cls(
            run_id=_str(data, "run_id"),
            factor_id=_str(data, "factor_id"),
            seed=_int(data, "seed", 0),
            config_digest=_str(data, "config_digest"),
            trace_digest=_str(data, "trace_digest"),
            behavior_digest=_str(data, "behavior_digest"),
            fitness_score=_float(data, "fitness_score", 0.0),
            witness_digest=_str(data, "witness_digest", ""),
            qd_archive_digest=_str(data, "qd_archive_digest", ""),
            metadata=_metadata(data.get("metadata", {})),
        )

    def digest(self) -> str:
        return _digest(self.to_dict())


@dataclass(frozen=True, slots=True)
class AblationComparisonResult:
    """Deterministic paired-by-seed fitness comparison; no p-values claimed."""

    baseline_factor_id: str
    compared_factor_id: str
    seed_count: int
    mean_delta: float
    median_delta: float
    improved_count: int
    worsened_count: int
    unchanged_count: int
    reasons: tuple[str, ...]
    attempted: bool = True
    succeeded: bool = True
    duplicate_baseline_seeds: tuple[int, ...] = ()
    duplicate_compared_seeds: tuple[int, ...] = ()

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "baseline_factor_id": self.baseline_factor_id,
            "compared_factor_id": self.compared_factor_id,
            "seed_count": self.seed_count,
            "mean_delta": self.mean_delta,
            "median_delta": self.median_delta,
            "improved_count": self.improved_count,
            "worsened_count": self.worsened_count,
            "unchanged_count": self.unchanged_count,
            "reasons": list(self.reasons),
            "attempted": self.attempted,
            "succeeded": self.succeeded,
            "duplicate_baseline_seeds": list(self.duplicate_baseline_seeds),
            "duplicate_compared_seeds": list(self.duplicate_compared_seeds),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, JsonValue]) -> AblationComparisonResult:
        return cls(
            baseline_factor_id=_str(data, "baseline_factor_id"),
            compared_factor_id=_str(data, "compared_factor_id"),
            seed_count=_int(data, "seed_count", 0),
            mean_delta=_float(data, "mean_delta", 0.0),
            median_delta=_float(data, "median_delta", 0.0),
            improved_count=_int(data, "improved_count", 0),
            worsened_count=_int(data, "worsened_count", 0),
            unchanged_count=_int(data, "unchanged_count", 0),
            reasons=_str_tuple(data, "reasons"),
            attempted=_bool(data, "attempted", True),
            succeeded=_bool(data, "succeeded", True),
            duplicate_baseline_seeds=_int_tuple(data, "duplicate_baseline_seeds"),
            duplicate_compared_seeds=_int_tuple(data, "duplicate_compared_seeds"),
        )

    def digest(self) -> str:
        return _digest(self.to_dict())


def compare_ablation_runs(
    baseline_runs: Sequence[AblationRunRecord],
    compared_runs: Sequence[AblationRunRecord],
    *,
    baseline_factor_id: str = "baseline",
    compared_factor_id: str = "treatment",
) -> AblationComparisonResult:
    """Compare paired runs by seed using simple descriptive statistics only."""

    duplicate_baseline = _duplicate_seeds(baseline_runs)
    duplicate_compared = _duplicate_seeds(compared_runs)
    if duplicate_baseline or duplicate_compared:
        return AblationComparisonResult(
            baseline_factor_id=baseline_factor_id,
            compared_factor_id=compared_factor_id,
            seed_count=0,
            mean_delta=0.0,
            median_delta=0.0,
            improved_count=0,
            worsened_count=0,
            unchanged_count=0,
            reasons=("duplicate_seed",),
            attempted=True,
            succeeded=False,
            duplicate_baseline_seeds=duplicate_baseline,
            duplicate_compared_seeds=duplicate_compared,
        )
    baseline_by_seed = {run.seed: run for run in baseline_runs}
    compared_by_seed = {run.seed: run for run in compared_runs}
    common_seeds = tuple(sorted(set(baseline_by_seed) & set(compared_by_seed)))
    deltas = [
        compared_by_seed[seed].fitness_score - baseline_by_seed[seed].fitness_score
        for seed in common_seeds
    ]
    reasons: list[str] = []
    if not common_seeds:
        reasons.append("no_paired_seeds")
    return AblationComparisonResult(
        baseline_factor_id=baseline_factor_id,
        compared_factor_id=compared_factor_id,
        seed_count=len(common_seeds),
        mean_delta=round(statistics.fmean(deltas), 10) if deltas else 0.0,
        median_delta=round(float(statistics.median(deltas)), 10) if deltas else 0.0,
        improved_count=sum(1 for delta in deltas if delta > 0),
        worsened_count=sum(1 for delta in deltas if delta < 0),
        unchanged_count=sum(1 for delta in deltas if delta == 0),
        reasons=tuple(reasons) if reasons else ("descriptive_comparison_only_no_p_value",),
        attempted=True,
        succeeded=bool(common_seeds),
    )


def _duplicate_seeds(runs: Sequence[AblationRunRecord]) -> tuple[int, ...]:
    seen: set[int] = set()
    duplicates: set[int] = set()
    for run in runs:
        if run.seed in seen:
            duplicates.add(run.seed)
        seen.add(run.seed)
    return tuple(sorted(duplicates))


def _digest(payload: Mapping[str, JsonValue]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _str(data: Mapping[str, JsonValue], key: str, default: str | None = None) -> str:
    value = data.get(key, default)
    if not isinstance(value, str):
        msg = f"{key} must be a string."
        raise ConfigurationError(msg)
    return value


def _int(data: Mapping[str, JsonValue], key: str, default: int) -> int:
    value = data.get(key, default)
    if isinstance(value, bool) or not isinstance(value, int):
        msg = f"{key} must be an integer."
        raise ConfigurationError(msg)
    return value


def _float(data: Mapping[str, JsonValue], key: str, default: float) -> float:
    value = data.get(key, default)
    if isinstance(value, bool) or not isinstance(value, int | float):
        msg = f"{key} must be numeric."
        raise ConfigurationError(msg)
    return float(value)


def _str_tuple(data: Mapping[str, JsonValue], key: str) -> tuple[str, ...]:
    raw = data.get(key, [])
    if not isinstance(raw, list) or not all(isinstance(item, str) for item in raw):
        msg = f"{key} must be a list of strings."
        raise ConfigurationError(msg)
    return tuple(str(item) for item in raw)


def _metadata(value: object) -> dict[str, JsonValue]:
    if not isinstance(value, Mapping):
        msg = "metadata must be an object."
        raise ConfigurationError(msg)
    return {str(key): raw for key, raw in value.items()}


def _bool(data: Mapping[str, JsonValue], key: str, default: bool) -> bool:
    value = data.get(key, default)
    if not isinstance(value, bool):
        msg = f"{key} must be a boolean."
        raise ConfigurationError(msg)
    return value


def _int_tuple(data: Mapping[str, JsonValue], key: str) -> tuple[int, ...]:
    raw = data.get(key, [])
    if not isinstance(raw, list) or any(
        isinstance(item, bool) or not isinstance(item, int) for item in raw
    ):
        msg = f"{key} must be a list of integers."
        raise ConfigurationError(msg)
    return tuple(cast(list[int], raw))
