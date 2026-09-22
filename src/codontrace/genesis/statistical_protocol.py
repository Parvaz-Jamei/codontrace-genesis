"""Statistical protocol scaffolds for GENESIS evidence records.

Dependency-free audit scaffolds. Inferential helpers here compute
descriptive p-values, intervals, and corrections. They do not run
experiments, write reports, or prove scientific claims.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Literal

from codontrace._types import JsonValue
from codontrace.errors import ConfigurationError
from codontrace.rng import RNGManager


@dataclass(frozen=True, slots=True)
class StatisticalProtocolConfig:
    """Minimal pre-registered descriptive protocol configuration."""

    min_seeds: int = 5
    paired_by_seed: bool = True
    report_effect_size: bool = True
    require_pre_registered_metrics: bool = False
    metric_names: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.min_seeds <= 0:
            msg = "StatisticalProtocolConfig.min_seeds must be > 0."
            raise ConfigurationError(msg)
        if self.require_pre_registered_metrics and not self.metric_names:
            msg = "metric_names must be provided when pre-registered metrics are required."
            raise ConfigurationError(msg)
        if len(set(self.metric_names)) != len(self.metric_names):
            msg = "metric_names must be unique."
            raise ConfigurationError(msg)

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "min_seeds": self.min_seeds,
            "paired_by_seed": self.paired_by_seed,
            "report_effect_size": self.report_effect_size,
            "require_pre_registered_metrics": self.require_pre_registered_metrics,
            "metric_names": list(self.metric_names),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, JsonValue]) -> StatisticalProtocolConfig:
        return cls(
            min_seeds=_int(data, "min_seeds", 5),
            paired_by_seed=_bool(data, "paired_by_seed", True),
            report_effect_size=_bool(data, "report_effect_size", True),
            require_pre_registered_metrics=_bool(data, "require_pre_registered_metrics", False),
            metric_names=_str_tuple(data, "metric_names"),
        )

    def digest(self) -> str:
        return _digest(self.to_dict())


@dataclass(frozen=True, slots=True)
class EffectSizeResult:
    """Descriptive standardized delta; not a significance test."""

    metric_name: str
    baseline_mean: float
    treatment_mean: float
    mean_delta: float
    standardized_delta_lite: float
    sample_count: int
    interpretation: str

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "metric_name": self.metric_name,
            "baseline_mean": self.baseline_mean,
            "treatment_mean": self.treatment_mean,
            "mean_delta": self.mean_delta,
            "standardized_delta_lite": self.standardized_delta_lite,
            "sample_count": self.sample_count,
            "interpretation": self.interpretation,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, JsonValue]) -> EffectSizeResult:
        return cls(
            metric_name=_str(data, "metric_name"),
            baseline_mean=_float(data, "baseline_mean", 0.0),
            treatment_mean=_float(data, "treatment_mean", 0.0),
            mean_delta=_float(data, "mean_delta", 0.0),
            standardized_delta_lite=_float(data, "standardized_delta_lite", 0.0),
            sample_count=_int(data, "sample_count", 0),
            interpretation=_str(data, "interpretation"),
        )

    def digest(self) -> str:
        return _digest(self.to_dict())


def estimate_effect_size_lite(
    metric_name: str,
    baseline_values: Sequence[float],
    treatment_values: Sequence[float],
) -> EffectSizeResult:
    """Compute a small descriptive effect-size proxy without p-values."""

    if not baseline_values or not treatment_values:
        msg = "baseline_values and treatment_values must not be empty."
        raise ConfigurationError(msg)
    if any(
        isinstance(value, bool) or not isinstance(value, int | float) for value in baseline_values
    ):
        msg = "baseline_values must be numeric."
        raise ConfigurationError(msg)
    if any(
        isinstance(value, bool) or not isinstance(value, int | float) for value in treatment_values
    ):
        msg = "treatment_values must be numeric."
        raise ConfigurationError(msg)
    baseline = [float(value) for value in baseline_values]
    treatment = [float(value) for value in treatment_values]
    baseline_mean = sum(baseline) / len(baseline)
    treatment_mean = sum(treatment) / len(treatment)
    mean_delta = treatment_mean - baseline_mean
    pooled = _pooled_std(baseline, treatment)
    standardized = mean_delta / pooled if pooled > 0 else 0.0
    magnitude = abs(standardized)
    if magnitude < 0.2:
        interpretation = "negligible_descriptive_effect"
    elif magnitude < 0.5:
        interpretation = "small_descriptive_effect"
    elif magnitude < 0.8:
        interpretation = "medium_descriptive_effect"
    else:
        interpretation = "large_descriptive_effect"
    return EffectSizeResult(
        metric_name=metric_name,
        baseline_mean=round(baseline_mean, 10),
        treatment_mean=round(treatment_mean, 10),
        mean_delta=round(mean_delta, 10),
        standardized_delta_lite=round(standardized, 10),
        sample_count=min(len(baseline), len(treatment)),
        interpretation=interpretation,
    )


def paired_effect_size(deltas: Sequence[float]) -> float:
    """Cohen's dz = mean(Δ) / s_Δ using the sample SD (ddof=1).

    Zero variance with a non-zero mean is undefined (not a zero effect).
    """

    if any(isinstance(value, bool) or not isinstance(value, int | float) for value in deltas):
        msg = "deltas must be numeric."
        raise ConfigurationError(msg)
    values = [float(value) for value in deltas]
    if len(values) < 2:
        msg = "paired_effect_size requires at least two deltas."
        raise ConfigurationError(msg)
    mean_delta = sum(values) / len(values)
    sample_sd = math.sqrt(sum((value - mean_delta) ** 2 for value in values) / (len(values) - 1))
    if sample_sd == 0.0:
        if mean_delta == 0.0:
            return 0.0
        raise ConfigurationError(
            "paired_effect_size is undefined when s_delta is 0 and mean(delta) is not 0."
        )
    return mean_delta / sample_sd


def _sample_sum_of_squares(values: Sequence[float]) -> float:
    mean = sum(values) / len(values)
    return sum((value - mean) ** 2 for value in values)


def _pooled_std(a: Sequence[float], b: Sequence[float]) -> float:
    """Classical pooled SD: sqrt(((n1-1)s1² + (n2-1)s2²) / (n1+n2-2))."""

    n1 = len(a)
    n2 = len(b)
    degrees = n1 + n2 - 2
    if n1 < 1 or n2 < 1 or degrees <= 0:
        return 0.0
    return math.sqrt((_sample_sum_of_squares(a) + _sample_sum_of_squares(b)) / degrees)


def _digest(payload: Mapping[str, JsonValue]) -> str:
    from codontrace.genesis.canonical import canonical_digest

    return canonical_digest(payload)


def _str(data: Mapping[str, JsonValue], key: str, default: str | None = None) -> str:
    value = data.get(key, default)
    if not isinstance(value, str):
        msg = f"{key} must be a string."
        raise ConfigurationError(msg)
    return value


def _bool(data: Mapping[str, JsonValue], key: str, default: bool) -> bool:
    value = data.get(key, default)
    if not isinstance(value, bool):
        msg = f"{key} must be a boolean."
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


# --- Strong Library Phase 2/3 statistical/OEE policy objects ---
def choose_paired_test(
    policy: StatisticalTestPolicy, *, paired: bool, independent: bool = False
) -> str:
    if paired:
        if policy.test_name in {"mann_whitney", "mannwhitneyu"}:
            raise ConfigurationError(
                "Mann-Whitney is for independent groups, not paired seed deltas."
            )
        return policy.test_name
    if independent:
        return "mann_whitney" if policy.test_name == "mann_whitney" else policy.test_name
    return policy.fallback_test_name


@dataclass(frozen=True, slots=True)
class OEEClaimThresholds:
    min_seed_count_research_grade: int = 30
    min_generation_count: int = 1000
    burn_in_fraction: float = 0.20
    min_persistence_window_generations: int = 10
    require_shadow_run: bool = True
    require_confidence_intervals: bool = True
    required_metrics: tuple[str, ...] = (
        "archive_coverage_slope",
        "persistent_novelty_rate",
        "lineage_persistence",
        "behavior_entropy",
    )

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "min_seed_count_research_grade": self.min_seed_count_research_grade,
            "min_generation_count": self.min_generation_count,
            "burn_in_fraction": self.burn_in_fraction,
            "min_persistence_window_generations": self.min_persistence_window_generations,
            "require_shadow_run": self.require_shadow_run,
            "require_confidence_intervals": self.require_confidence_intervals,
            "required_metrics": list(self.required_metrics),
        }

    def digest(self) -> str:
        return _digest(self.to_dict())


@dataclass(frozen=True, slots=True)
class OEEMetricsReport:
    protocol_version: str
    seed_count: int
    generation_count: int
    burn_in: int
    metrics: tuple[tuple[str, float], ...]
    confidence_intervals: tuple[tuple[str, tuple[float, float]], ...]
    shadow_adjusted: bool
    threshold_digest: str
    claim_level: str
    persistence_window_observed: int = 0
    stagnation_window: int = 0
    diversity_collapse_flag: bool = False
    shadow_adjusted_novelty: float = 0.0
    digest: str = ""

    def __post_init__(self) -> None:
        if self.claim_level == "proved_open_endedness":
            raise ConfigurationError("OEEMetricsReport must never claim proof of open-endedness.")
        computed = _digest(self._payload())
        if self.digest and self.digest != computed:
            raise ConfigurationError("OEEMetricsReport digest mismatch.")
        object.__setattr__(self, "digest", computed)

    @property
    def persistence_window_t(self) -> int:
        """Explicit persistence / coalescence window used for measurement."""

        return self.persistence_window_observed

    def _payload(self) -> dict[str, JsonValue]:
        return {
            "protocol_version": self.protocol_version,
            "seed_count": self.seed_count,
            "generation_count": self.generation_count,
            "burn_in": self.burn_in,
            "metrics": [[k, v] for k, v in self.metrics],
            "confidence_intervals": [[k, [v[0], v[1]]] for k, v in self.confidence_intervals],
            "shadow_adjusted": self.shadow_adjusted,
            "threshold_digest": self.threshold_digest,
            "claim_level": self.claim_level,
            "persistence_window_observed": self.persistence_window_observed,
            "stagnation_window": self.stagnation_window,
            "diversity_collapse_flag": self.diversity_collapse_flag,
            "shadow_adjusted_novelty": self.shadow_adjusted_novelty,
        }

    def to_dict(self) -> dict[str, JsonValue]:
        return {**self._payload(), "digest": self.digest}


def build_oee_metrics_report(
    seed_count: int,
    generation_count: int,
    metrics: Mapping[str, float],
    *,
    confidence_intervals: Mapping[str, tuple[float, float]] | None = None,
    shadow_adjusted: bool = False,
    thresholds: OEEClaimThresholds | None = None,
    persistence_window_observed: int | None = None,
    stagnation_window: int = 0,
    diversity_collapse_flag: bool = False,
    shadow_adjusted_novelty: float | None = None,
) -> OEEMetricsReport:
    th = thresholds or OEEClaimThresholds()
    burn_in = int(generation_count * th.burn_in_fraction)
    missing = [name for name in th.required_metrics if name not in metrics]
    has_ci = bool(confidence_intervals) or not th.require_confidence_intervals
    observed_persistence = (
        persistence_window_observed
        if persistence_window_observed is not None
        else int(metrics.get("lineage_persistence", 0.0))
    )
    adjusted_novelty = (
        shadow_adjusted_novelty
        if shadow_adjusted_novelty is not None
        else float(metrics.get("persistent_novelty_rate", 0.0))
    )
    if (
        seed_count >= th.min_seed_count_research_grade
        and generation_count >= th.min_generation_count
        and shadow_adjusted
        and has_ci
        and not missing
        and observed_persistence >= th.min_persistence_window_generations
        and not diversity_collapse_flag
    ):
        level = "oee_candidate"
    elif metrics:
        level = "measurement_only"
    else:
        level = "insufficient"
    return OEEMetricsReport(
        protocol_version="oee_metrics_v1",
        seed_count=seed_count,
        generation_count=generation_count,
        burn_in=burn_in,
        metrics=tuple(sorted((str(k), float(v)) for k, v in metrics.items())),
        confidence_intervals=tuple(
            sorted(
                (str(k), (float(v[0]), float(v[1])))
                for k, v in (confidence_intervals or {}).items()
            )
        ),
        shadow_adjusted=shadow_adjusted,
        threshold_digest=th.digest(),
        claim_level=level,
        persistence_window_observed=observed_persistence,
        stagnation_window=stagnation_window,
        diversity_collapse_flag=diversity_collapse_flag,
        shadow_adjusted_novelty=float(adjusted_novelty),
    )

from codontrace.genesis.canonical import canonical_digest as _phase3_digest, require_finite_float as _phase3_finite

@dataclass(frozen=True, slots=True)
class PreregisteredMetric:
    metric_name: str
    objective: str
    direction: str = "maximize"
    schema_version: str = "preregistered_metric_v1"
    def __post_init__(self) -> None:
        if not self.metric_name or not self.objective:
            raise ConfigurationError("PreregisteredMetric requires name and objective")
        if self.direction not in {"maximize", "minimize", "two_sided"}:
            raise ConfigurationError("invalid metric direction")
    def to_dict(self) -> dict[str, JsonValue]:
        return {"schema_version": self.schema_version, "metric_name": self.metric_name, "objective": self.objective, "direction": self.direction}
    def digest(self) -> str:
        return _phase3_digest(self.to_dict())

@dataclass(frozen=True, slots=True)
class SeedSweepPlan:
    seeds: tuple[int, ...]
    paired: bool = True
    min_seeds: int = 2
    schema_version: str = "seed_sweep_plan_v1"
    def __post_init__(self) -> None:
        object.__setattr__(self, "seeds", tuple(int(s) for s in self.seeds))
        if len(self.seeds) < self.min_seeds or len(self.seeds) != len(set(self.seeds)):
            raise ConfigurationError("SeedSweepPlan requires enough unique seeds")
    def to_dict(self) -> dict[str, JsonValue]:
        return {"schema_version": self.schema_version, "seeds": list(self.seeds), "paired": self.paired, "min_seeds": self.min_seeds}
    def digest(self) -> str:
        return _phase3_digest(self.to_dict())

@dataclass(frozen=True, slots=True)
class MultipleComparisonAudit:
    metric_count: int
    correction_policy: str = "holm_or_bh_required"
    warning: str = "multiple_metric_family_audit_present"
    schema_version: str = "multiple_comparison_audit_v1"
    def __post_init__(self) -> None:
        if self.metric_count < 1:
            raise ConfigurationError("metric_count must be positive")
    def to_dict(self) -> dict[str, JsonValue]:
        return {"schema_version": self.schema_version, "metric_count": self.metric_count, "correction_policy": self.correction_policy, "warning": self.warning}
    def digest(self) -> str:
        return _phase3_digest(self.to_dict())

@dataclass(frozen=True, slots=True)
class DowngradeRule:
    reason: str
    applies_when: str
    target_level: str
    schema_version: str = "downgrade_rule_v1"
    def to_dict(self) -> dict[str, JsonValue]:
        return {"schema_version": self.schema_version, "reason": self.reason, "applies_when": self.applies_when, "target_level": self.target_level}
    def digest(self) -> str:
        return _phase3_digest(self.to_dict())

# Phase 3 P0/P1 strict statistical validation contracts.
from codontrace.genesis.canonical import (
    canonical_digest as _strict_stat_digest,
    is_real_evidence_digest as _strict_stat_is_real_digest,
    require_finite_float as _strict_stat_finite,
    require_real_evidence_digest as _strict_stat_require_real_digest,
)


@dataclass(frozen=True, slots=True)
class StatisticalTestPolicy:
    """Seed-count tiers for descriptive vs research-grade language.

    n=12 is ``exploratory_only`` (smoke / exploratory). Research-grade
    language requires ``n >= min_research_grade_n`` (default 30).
    """

    paired: bool = True
    ci_method: str = "bca_bootstrap"
    test_name: str = "paired_permutation"
    fallback_test_name: str = "deterministic_summary"
    min_descriptive_n: int = 2
    min_exploratory_n: int = 8
    min_benchmark_preliminary_n: int = 16
    min_research_grade_n: int = 30

    def __post_init__(self) -> None:
        thresholds = (
            int(self.min_descriptive_n),
            int(self.min_exploratory_n),
            int(self.min_benchmark_preliminary_n),
            int(self.min_research_grade_n),
        )
        if thresholds[0] <= 0 or thresholds != tuple(sorted(thresholds)):
            raise ConfigurationError("statistical thresholds must be positive and monotonic")

    def tier_for_n(self, n: int) -> str:
        if n < self.min_descriptive_n:
            return "too_few_seeds"
        if n < self.min_exploratory_n:
            return "descriptive_only"
        if n < self.min_benchmark_preliminary_n:
            return "exploratory_only"
        if n < self.min_research_grade_n:
            return "preliminary_benchmark"
        return "research_grade_benchmark_candidate"

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "paired": self.paired,
            "ci_method": self.ci_method,
            "test_name": self.test_name,
            "fallback_test_name": self.fallback_test_name,
            "min_descriptive_n": self.min_descriptive_n,
            "min_exploratory_n": self.min_exploratory_n,
            "min_benchmark_preliminary_n": self.min_benchmark_preliminary_n,
            "min_research_grade_n": self.min_research_grade_n,
        }

    def digest(self) -> str:
        return _strict_stat_digest(self.to_dict())


def validate_statistical_claim_inputs(
    *,
    p_value: float | None,
    effect_size: float | None,
    confidence_interval: tuple[float, float] | None,
    replay_artifact_digest: str | None,
    protocol_digest: str | None,
    claim_gate_decision_digest: str | None,
) -> tuple[bool, str]:
    if effect_size is None:
        return False, "missing_effect_size"
    try:
        _strict_stat_finite("effect_size", effect_size)
    except ConfigurationError:
        return False, "non_finite_effect_size"
    if confidence_interval is None:
        return False, "missing_confidence_interval"
    try:
        ci_low = _strict_stat_finite("ci_low", confidence_interval[0])
        ci_high = _strict_stat_finite("ci_high", confidence_interval[1])
    except (ConfigurationError, IndexError, TypeError):
        return False, "non_finite_confidence_interval"
    if ci_low > ci_high:
        return False, "invalid_confidence_interval"
    if p_value is not None:
        try:
            p = _strict_stat_finite("p_value", p_value)
        except ConfigurationError:
            return False, "non_finite_p_value"
        if not 0.0 <= p <= 1.0:
            return False, "p_value_out_of_range"
    if not _strict_stat_is_real_digest(replay_artifact_digest):
        return False, "missing_replay_artifact"
    if not _strict_stat_is_real_digest(protocol_digest):
        return False, "missing_protocol_digest"
    if not _strict_stat_is_real_digest(claim_gate_decision_digest):
        return False, "missing_claim_gate_decision"
    return True, "claim_inputs_complete"


@dataclass(frozen=True, slots=True)
class PairedComparisonResult:
    metric: PreregisteredMetric
    baseline_values_digest: str
    treatment_values_digest: str
    paired_seed_digest: str
    effect_size: float
    sample_count: int
    ci_low: float
    ci_high: float
    schema_version: str = "paired_comparison_result_v2"

    def __post_init__(self) -> None:
        object.__setattr__(self, "effect_size", _strict_stat_finite("effect_size", self.effect_size))
        object.__setattr__(self, "ci_low", _strict_stat_finite("ci_low", self.ci_low))
        object.__setattr__(self, "ci_high", _strict_stat_finite("ci_high", self.ci_high))
        if self.sample_count <= 0:
            raise ConfigurationError("sample_count must be positive")
        if self.ci_low > self.ci_high:
            raise ConfigurationError("invalid_confidence_interval")
        _strict_stat_require_real_digest("baseline_values_digest", self.baseline_values_digest)
        _strict_stat_require_real_digest("treatment_values_digest", self.treatment_values_digest)
        _strict_stat_require_real_digest("paired_seed_digest", self.paired_seed_digest)

    @property
    def claim_downgraded(self) -> bool:
        return self.ci_low <= 0.0 <= self.ci_high

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "schema_version": self.schema_version,
            "metric": self.metric.to_dict(),
            "baseline_values_digest": self.baseline_values_digest,
            "treatment_values_digest": self.treatment_values_digest,
            "paired_seed_digest": self.paired_seed_digest,
            "effect_size": self.effect_size,
            "sample_count": self.sample_count,
            "ci_low": self.ci_low,
            "ci_high": self.ci_high,
            "claim_downgraded": self.claim_downgraded,
        }

    def digest(self) -> str:
        return _strict_stat_digest(self.to_dict())


_DEFAULT_INFERENTIAL_SEED = 20260911
_MONTE_CARLO_SIGN_FLIPS = 20000
_EXACT_SIGN_FLIP_MAX_N = 20
_MEET_IN_THE_MIDDLE_MAX_N = 40
_SIGN_FLIP_ABS_EPS = 1e-15


@dataclass(frozen=True, slots=True)
class SignFlipPermutationDetail:
    """How a sign-flip p-value was produced. Does not unlock a claim."""

    p: float
    n: int
    method: str
    n_patterns: int
    censored_floor: bool
    floor: float | None

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "p": self.p,
            "n": self.n,
            "method": self.method,
            "n_patterns": self.n_patterns,
            "censored_floor": self.censored_floor,
            "floor": self.floor,
        }


def _require_numeric_sequence(name: str, values: Sequence[float]) -> list[float]:
    if any(isinstance(value, bool) or not isinstance(value, int | float) for value in values):
        raise ConfigurationError(f"{name} must be numeric.")
    return [float(value) for value in values]


def _norm_cdf(value: float) -> float:
    return 0.5 * (1.0 + math.erf(value / math.sqrt(2.0)))


def _norm_ppf(probability: float) -> float:
    """Acklam rational approximation to the standard-normal quantile."""

    if probability <= 0.0:
        return float("-inf")
    if probability >= 1.0:
        return float("inf")
    a = (
        -3.969683028665376e01,
        2.209460984245205e02,
        -2.759285104469687e02,
        1.383577518672690e02,
        -3.066479806614716e01,
        2.506628277459239e00,
    )
    b = (
        -5.447609879822406e01,
        1.615858368580409e02,
        -1.556989798598866e02,
        6.680131188771972e01,
        -1.328068155288572e01,
    )
    c = (
        -7.784894002430293e-03,
        -3.223964580411365e-01,
        -2.400758277161838e00,
        -2.549732539343734e00,
        4.374664141464968e00,
        2.938163982698783e00,
    )
    d = (
        7.784695709041462e-03,
        3.224671290700398e-01,
        2.445134137142996e00,
        3.754408661907416e00,
    )
    plow = 0.02425
    phigh = 1.0 - plow
    if probability < plow:
        q = math.sqrt(-2.0 * math.log(probability))
        return (((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) / (
            (((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1.0
        )
    if probability > phigh:
        q = math.sqrt(-2.0 * math.log(1.0 - probability))
        return -(((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) / (
            (((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1.0
        )
    q = probability - 0.5
    r = q * q
    return (
        (((((a[0] * r + a[1]) * r + a[2]) * r + a[3]) * r + a[4]) * r + a[5])
        * q
        / (((((b[0] * r + b[1]) * r + b[2]) * r + b[3]) * r + b[4]) * r + 1.0)
    )


def _mean_of(values: Sequence[float]) -> float:
    return sum(values) / len(values)


def exact_sign_flip_permutation_p(
    deltas: Sequence[float],
    *,
    seed: int = _DEFAULT_INFERENTIAL_SEED,
) -> float:
    """Two-sided sign-flip permutation p-value for paired deltas.

    Exhaustive over all 2^n sign patterns when n≤20. Larger n uses a
    20000-draw Monte Carlo with a fixed seed. Monte Carlo p-values use
    (1 + extreme) / (1 + draws) so a finite draw cannot report p=0.
    This is a measurement, not a claim unlock.
    """

    values = _require_numeric_sequence("deltas", deltas)
    if not values:
        raise ConfigurationError("exact_sign_flip_permutation_p requires at least one delta.")
    observed = abs(sum(values))
    n = len(values)
    if n <= _EXACT_SIGN_FLIP_MAX_N:
        return _exhaustive_sign_flip_count(values, observed) / float(1 << n)
    return _monte_carlo_sign_flip_p(values, observed, seed)


def _monte_carlo_sign_flip_p(values: Sequence[float], observed: float, seed: int) -> float:
    rng = RNGManager(seed=int(seed), namespace="sign_flip_permutation")
    count = 0
    for _ in range(_MONTE_CARLO_SIGN_FLIPS):
        total = 0.0
        for value in values:
            total += value if rng.randrange(2) == 0 else -value
        if abs(total) + _SIGN_FLIP_ABS_EPS >= observed:
            count += 1
    return (1 + count) / (1 + _MONTE_CARLO_SIGN_FLIPS)


def _exhaustive_sign_flip_count(values: Sequence[float], observed: float) -> int:
    count = 0
    n = len(values)
    for mask in range(1 << n):
        total = 0.0
        for index, value in enumerate(values):
            total += value if (mask >> index) & 1 else -value
        if abs(total) + _SIGN_FLIP_ABS_EPS >= observed:
            count += 1
    return count


def _signed_sums(values: Sequence[float]) -> list[float]:
    n = len(values)
    out = [0.0] * (1 << n)
    for mask in range(1 << n):
        total = 0.0
        for index, value in enumerate(values):
            total += value if (mask >> index) & 1 else -value
        out[mask] = total
    return out


def meet_in_the_middle_sign_flip_p(deltas: Sequence[float]) -> float:
    """Exact two-sided sign-flip p for n≤40 via split enumeration.

    Default ``exact_sign_flip_permutation_p`` is unchanged (exhaustive n≤20,
    Monte Carlo otherwise) so published campaign pins stay stable.
    """

    values = _require_numeric_sequence("deltas", deltas)
    if not values:
        raise ConfigurationError("meet_in_the_middle_sign_flip_p requires at least one delta.")
    n = len(values)
    if n > _MEET_IN_THE_MIDDLE_MAX_N:
        raise ConfigurationError(
            f"meet_in_the_middle_sign_flip_p supports n<= {_MEET_IN_THE_MIDDLE_MAX_N}, got {n}."
        )
    observed = abs(sum(values))
    return _meet_in_the_middle_count(values, observed) / float(1 << n)


def _meet_in_the_middle_count(values: Sequence[float], observed: float) -> int:
    n = len(values)
    if n <= 1:
        return _exhaustive_sign_flip_count(values, observed)
    n1 = n // 2
    left = _signed_sums(values[:n1])
    right = sorted(_signed_sums(values[n1:]))
    threshold = observed - _SIGN_FLIP_ABS_EPS
    if threshold <= 0.0:
        return 1 << n
    lo_bound = -threshold
    hi_bound = threshold
    count = 0
    m = len(right)
    for left_sum in left:
        # |L+R| >= observed - eps  <=>  R >= hi_bound-L  or  R <= lo_bound-L
        hi_start = _bisect_left(right, hi_bound - left_sum)
        lo_end = _bisect_right(right, lo_bound - left_sum)
        count += (m - hi_start) + lo_end
    return count


def _bisect_left(sorted_values: Sequence[float], target: float) -> int:
    low = 0
    high = len(sorted_values)
    while low < high:
        mid = (low + high) // 2
        if sorted_values[mid] < target:
            low = mid + 1
        else:
            high = mid
    return low


def _bisect_right(sorted_values: Sequence[float], target: float) -> int:
    low = 0
    high = len(sorted_values)
    while low < high:
        mid = (low + high) // 2
        if sorted_values[mid] <= target:
            low = mid + 1
        else:
            high = mid
    return low


def sign_flip_permutation_detail(
    deltas: Sequence[float],
    *,
    seed: int = _DEFAULT_INFERENTIAL_SEED,
    method: Literal["auto", "exhaustive", "meet_in_the_middle", "monte_carlo"] = "auto",
) -> SignFlipPermutationDetail:
    """Report p together with the method. Auto matches ``exact_sign_flip_permutation_p``."""

    values = _require_numeric_sequence("deltas", deltas)
    if not values:
        raise ConfigurationError("sign_flip_permutation_detail requires at least one delta.")
    n = len(values)
    observed = abs(sum(values))
    resolved = method
    if method == "auto":
        resolved = "exhaustive" if n <= _EXACT_SIGN_FLIP_MAX_N else "monte_carlo"
    if resolved == "exhaustive":
        if n > _EXACT_SIGN_FLIP_MAX_N:
            raise ConfigurationError("exhaustive sign-flip is limited to n<=20.")
        count = _exhaustive_sign_flip_count(values, observed)
        return SignFlipPermutationDetail(
            p=count / float(1 << n),
            n=n,
            method="exhaustive",
            n_patterns=1 << n,
            censored_floor=False,
            floor=None,
        )
    if resolved == "meet_in_the_middle":
        p_value = meet_in_the_middle_sign_flip_p(values)
        return SignFlipPermutationDetail(
            p=p_value,
            n=n,
            method="meet_in_the_middle",
            n_patterns=1 << n,
            censored_floor=False,
            floor=None,
        )
    if resolved != "monte_carlo":
        raise ConfigurationError(
            'sign_flip method must be "auto", "exhaustive", "meet_in_the_middle", or "monte_carlo".'
        )
    p_value = _monte_carlo_sign_flip_p(values, observed, seed)
    floor = 1.0 / (1 + _MONTE_CARLO_SIGN_FLIPS)
    return SignFlipPermutationDetail(
        p=p_value,
        n=n,
        method="monte_carlo",
        n_patterns=_MONTE_CARLO_SIGN_FLIPS,
        censored_floor=True,
        floor=floor,
    )


def _percentile(sorted_values: Sequence[float], quantile: float) -> float:
    if not sorted_values:
        return 0.0
    if quantile <= 0.0:
        return sorted_values[0]
    if quantile >= 1.0:
        return sorted_values[-1]
    position = quantile * (len(sorted_values) - 1)
    low = int(math.floor(position))
    high = int(math.ceil(position))
    if low == high:
        return sorted_values[low]
    fraction = position - low
    return sorted_values[low] * (1.0 - fraction) + sorted_values[high] * fraction


def _bootstrap_means(
    values: Sequence[float],
    *,
    resamples: int,
    seed: int,
) -> list[float]:
    rng = RNGManager(seed=int(seed), namespace="bootstrap_paired")
    n = len(values)
    means: list[float] = []
    for _ in range(resamples):
        draw = [values[rng.randrange(n)] for _ in range(n)]
        means.append(_mean_of(draw))
    return means


def _bca_acceleration(values: Sequence[float]) -> float:
    n = len(values)
    if n < 2:
        return 0.0
    jack = [(_mean_of(values) * n - values[index]) / (n - 1) for index in range(n)]
    center = _mean_of(jack)
    cubed = sum((center - item) ** 3 for item in jack)
    squared = sum((center - item) ** 2 for item in jack)
    if squared <= 0.0:
        return 0.0
    return cubed / (6.0 * (squared**1.5))


def bootstrap_ci_paired(
    deltas: Sequence[float],
    *,
    method: Literal["bca", "percentile"] = "bca",
    resamples: int = 10000,
    seed: int = _DEFAULT_INFERENTIAL_SEED,
    confidence: float = 0.95,
) -> tuple[float, float]:
    """Paired-delta CI for the mean. ``method`` is ``bca`` or ``percentile``.

    Resamples the paired differences (not the two arms independently).
    n=1 and zero-width bootstrap clouds fall back to a point / percentile
    interval because BCa jackknife acceleration is undefined there.
    """

    values = _require_numeric_sequence("deltas", deltas)
    if not values:
        raise ConfigurationError("bootstrap_ci_paired requires at least one delta.")
    if method not in {"bca", "percentile"}:
        raise ConfigurationError('bootstrap_ci_paired method must be "bca" or "percentile".')
    if resamples < 1:
        raise ConfigurationError("resamples must be >= 1.")
    if not 0.0 < confidence < 1.0:
        raise ConfigurationError("confidence must be in (0, 1).")
    theta = _mean_of(values)
    if len(values) == 1:
        return (theta, theta)
    boots = sorted(_bootstrap_means(values, resamples=resamples, seed=seed))
    alpha = (1.0 - confidence) / 2.0
    if method == "percentile":
        return (_percentile(boots, alpha), _percentile(boots, 1.0 - alpha))
    less = sum(1 for item in boots if item < theta)
    proportion = less / len(boots)
    if proportion <= 0.0 or proportion >= 1.0:
        return (_percentile(boots, alpha), _percentile(boots, 1.0 - alpha))
    z0 = _norm_ppf(proportion)
    acceleration = _bca_acceleration(values)

    def _adjusted(tail: float) -> float:
        z_tail = _norm_ppf(tail)
        denom = 1.0 - acceleration * (z0 + z_tail)
        if denom == 0.0:
            return tail
        return _norm_cdf(z0 + (z0 + z_tail) / denom)

    low_q = min(max(_adjusted(alpha), 0.0), 1.0)
    high_q = min(max(_adjusted(1.0 - alpha), 0.0), 1.0)
    if low_q > high_q:
        low_q, high_q = high_q, low_q
    return (_percentile(boots, low_q), _percentile(boots, high_q))


def holm_correction(p_values: Sequence[float]) -> tuple[float, ...]:
    """Holm step-down adjusted p-values, returned in the original order."""

    values = _require_numeric_sequence("p_values", p_values)
    if any(value < 0.0 or value > 1.0 for value in values):
        raise ConfigurationError("p_values must lie in [0, 1].")
    count = len(values)
    if count == 0:
        return ()
    order = sorted(range(count), key=lambda index: (values[index], index))
    adjusted = [0.0] * count
    running = 0.0
    for rank, index in enumerate(order):
        running = min(1.0, max(running, (count - rank) * values[index]))
        adjusted[index] = running
    return tuple(adjusted)

