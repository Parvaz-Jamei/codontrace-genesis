"""Statistical reporting helpers for scientific GENESIS experiments."""

from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from codontrace._types import JsonValue
from codontrace.errors import ConfigurationError
from codontrace.genesis.statistical_protocol import StatisticalTestPolicy


@dataclass(frozen=True, slots=True)
class MetricDistribution:
    metric_name: str
    values: tuple[float, ...]

    def __post_init__(self) -> None:
        if not self.metric_name:
            raise ConfigurationError("metric_name must not be empty.")

    @property
    def mean(self) -> float:
        return 0.0 if not self.values else round(sum(self.values) / len(self.values), 10)

    @property
    def std(self) -> float:
        if not self.values:
            return 0.0
        mean = self.mean
        return round(
            math.sqrt(sum((value - mean) ** 2 for value in self.values) / len(self.values)), 10
        )

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "metric_name": self.metric_name,
            "values": list(self.values),
            "mean": self.mean,
            "std": self.std,
        }


@dataclass(frozen=True, slots=True)
class BootstrapCI:
    metric_name: str
    mean: float
    lower: float
    upper: float
    confidence: float = 0.95
    method: str = "deterministic_percentile_lite"

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "metric_name": self.metric_name,
            "mean": self.mean,
            "lower": self.lower,
            "upper": self.upper,
            "confidence": self.confidence,
            "method": self.method,
        }


def deterministic_bootstrap_ci(
    values: Sequence[float], metric_name: str, confidence: float = 0.95
) -> BootstrapCI:
    if not values:
        return BootstrapCI(metric_name, 0.0, 0.0, 0.0, confidence)
    ordered = sorted(float(value) for value in values)
    mean = round(sum(ordered) / len(ordered), 10)
    if len(ordered) == 1:
        return BootstrapCI(metric_name, mean, ordered[0], ordered[0], confidence)
    alpha = max(0.0, min(1.0, (1.0 - confidence) / 2.0))
    low_index = int(math.floor(alpha * (len(ordered) - 1)))
    high_index = int(math.ceil((1.0 - alpha) * (len(ordered) - 1)))
    return BootstrapCI(
        metric_name, mean, round(ordered[low_index], 10), round(ordered[high_index], 10), confidence
    )


@dataclass(frozen=True, slots=True)
class PairedSeedComparison:
    metric_name: str
    seed_deltas: dict[int, float]

    @property
    def mean_delta(self) -> float:
        if not self.seed_deltas:
            return 0.0
        return round(sum(self.seed_deltas.values()) / len(self.seed_deltas), 10)

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "metric_name": self.metric_name,
            "seed_deltas": {str(k): v for k, v in sorted(self.seed_deltas.items())},
            "mean_delta": self.mean_delta,
        }


@dataclass(frozen=True, slots=True)
class EffectSizeReport:
    metric_name: str
    mean_delta: float
    standardized_delta_lite: float
    interpretation: str

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "metric_name": self.metric_name,
            "mean_delta": self.mean_delta,
            "standardized_delta_lite": self.standardized_delta_lite,
            "interpretation": self.interpretation,
        }


@dataclass(frozen=True, slots=True)
class MinimumSeedPolicy:
    min_seeds: int = 5

    def evaluate(self, seed_count: int) -> tuple[bool, str]:
        if seed_count < self.min_seeds:
            return False, "insufficient_seed_count"
        return True, "seed_policy_passed"


@dataclass(frozen=True, slots=True)
class StatisticalExperimentReport:
    distributions: tuple[MetricDistribution, ...]
    confidence_intervals: tuple[BootstrapCI, ...]
    paired_comparisons: tuple[PairedSeedComparison, ...] = ()
    effect_sizes: tuple[EffectSizeReport, ...] = ()
    claim_status: str = "descriptive_only"
    limitations: tuple[str, ...] = ()
    seed_count: int = 0
    design_marker: str = "descriptive_unpaired"
    statistical_policy_version: str = "statistical_test_policy_v1"
    protocol_digest: str | None = None

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "distributions": [item.to_dict() for item in self.distributions],
            "confidence_intervals": [item.to_dict() for item in self.confidence_intervals],
            "paired_comparisons": [item.to_dict() for item in self.paired_comparisons],
            "effect_sizes": [item.to_dict() for item in self.effect_sizes],
            "claim_status": self.claim_status,
            "limitations": list(self.limitations),
            "seed_count": self.seed_count,
            "design_marker": self.design_marker,
            "statistical_policy_version": self.statistical_policy_version,
            "protocol_digest": self.protocol_digest,
        }

    def digest(self) -> str:
        return _digest(self.to_dict())


def build_statistical_report(
    metric_values: Mapping[str, Sequence[float]],
    *,
    min_seed_policy: MinimumSeedPolicy | None = None,
    statistical_policy: StatisticalTestPolicy | None = None,
    paired_design: bool = True,
) -> StatisticalExperimentReport:
    # ``min_seed_policy`` is retained for backward compatibility, but the claim
    # level is governed by StatisticalTestPolicy so reports never imply a
    # p-value-only scientific benchmark.
    legacy_policy = min_seed_policy or MinimumSeedPolicy()
    policy = statistical_policy or StatisticalTestPolicy()
    distributions = tuple(
        MetricDistribution(name, tuple(float(v) for v in values))
        for name, values in sorted(metric_values.items())
    )
    intervals = tuple(
        deterministic_bootstrap_ci(dist.values, dist.metric_name) for dist in distributions
    )
    max_seed_count = max((len(dist.values) for dist in distributions), default=0)
    _, legacy_reason = legacy_policy.evaluate(max_seed_count)
    tier = policy.tier_for_n(max_seed_count)
    limitations = (legacy_reason,) if max_seed_count < legacy_policy.min_seeds else ()
    return StatisticalExperimentReport(
        distributions=distributions,
        confidence_intervals=intervals,
        claim_status=tier,
        limitations=limitations,
        seed_count=max_seed_count,
        design_marker="paired_by_seed" if paired_design else "independent_groups",
        statistical_policy_version="statistical_test_policy_v1",
        protocol_digest=policy.digest(),
    )


def paired_seed_comparison(
    baseline: Mapping[int, float], treatment: Mapping[int, float], metric_name: str
) -> PairedSeedComparison:
    common = sorted(set(baseline) & set(treatment))
    return PairedSeedComparison(
        metric_name,
        {seed: round(float(treatment[seed]) - float(baseline[seed]), 10) for seed in common},
    )


def _digest(payload: Mapping[str, JsonValue]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()
