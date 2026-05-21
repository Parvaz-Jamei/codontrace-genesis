"""D0 baseline and Discovery Witness evidence scaffolds for GENESIS.

These objects are dependency-free evidence infrastructure. They do not prove
open-ended discovery, artificial life, causal learning, or knowledge transfer.
"""

from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import cast

from codontrace._types import JsonValue
from codontrace.errors import ConfigurationError
from codontrace.genesis.discovery import D0BaselineConfig, DiscoveryClaimLevel

Descriptor = Mapping[str, float]


@dataclass(frozen=True, slots=True)
class D0BaselineRun:
    """One calibrated D0 reference run snapshot."""

    run_id: str
    seed: int
    config_digest: str
    behavior_descriptor: dict[str, float]
    behavior_digest: str
    trace_digest: str
    population_digest: str
    graph_digest: str
    vocabulary_digest: str
    capsule_store_digest: str
    metadata: dict[str, JsonValue] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.run_id:
            msg = "D0BaselineRun.run_id must not be empty."
            raise ConfigurationError(msg)
        copied_descriptor = dict(self.behavior_descriptor)
        copied_metadata = dict(self.metadata)
        _validate_descriptor(copied_descriptor)
        object.__setattr__(self, "behavior_descriptor", copied_descriptor)
        object.__setattr__(self, "metadata", copied_metadata)

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "run_id": self.run_id,
            "seed": self.seed,
            "config_digest": self.config_digest,
            "behavior_descriptor": dict(sorted(self.behavior_descriptor.items())),
            "behavior_digest": self.behavior_digest,
            "trace_digest": self.trace_digest,
            "population_digest": self.population_digest,
            "graph_digest": self.graph_digest,
            "vocabulary_digest": self.vocabulary_digest,
            "capsule_store_digest": self.capsule_store_digest,
            "metadata": dict(sorted(self.metadata.items())),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, JsonValue]) -> D0BaselineRun:
        return cls(
            run_id=_str(data, "run_id"),
            seed=_int(data, "seed", 0),
            config_digest=_str(data, "config_digest"),
            behavior_descriptor=_descriptor(data.get("behavior_descriptor")),
            behavior_digest=_str(data, "behavior_digest"),
            trace_digest=_str(data, "trace_digest"),
            population_digest=_str(data, "population_digest"),
            graph_digest=_str(data, "graph_digest"),
            vocabulary_digest=_str(data, "vocabulary_digest"),
            capsule_store_digest=_str(data, "capsule_store_digest"),
            metadata=_metadata(data.get("metadata", {})),
        )

    def digest(self) -> str:
        return _digest(self.to_dict())


@dataclass(frozen=True, slots=True)
class D0BaselineSet:
    """Calibrated D0 behavior-space reference set."""

    baseline_id: str
    baseline_config: D0BaselineConfig
    runs: tuple[D0BaselineRun, ...]
    descriptor_schema: tuple[str, ...]
    calibration_summary: dict[str, JsonValue]

    def __post_init__(self) -> None:
        if not self.baseline_id:
            msg = "D0BaselineSet.baseline_id must not be empty."
            raise ConfigurationError(msg)
        if not self.descriptor_schema:
            msg = "D0BaselineSet.descriptor_schema must not be empty."
            raise ConfigurationError(msg)

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "baseline_id": self.baseline_id,
            "baseline_config": self.baseline_config.to_dict(),
            "runs": [run.to_dict() for run in self.runs],
            "descriptor_schema": list(self.descriptor_schema),
            "calibration_summary": dict(sorted(self.calibration_summary.items())),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, JsonValue]) -> D0BaselineSet:
        raw_config = data.get("baseline_config")
        raw_runs = data.get("runs")
        raw_schema = data.get("descriptor_schema")
        if not isinstance(raw_config, Mapping):
            msg = "D0BaselineSet.baseline_config must be an object."
            raise ConfigurationError(msg)
        if not isinstance(raw_runs, list):
            msg = "D0BaselineSet.runs must be a list."
            raise ConfigurationError(msg)
        if not isinstance(raw_schema, list) or not all(
            isinstance(item, str) for item in raw_schema
        ):
            msg = "D0BaselineSet.descriptor_schema must be a list of strings."
            raise ConfigurationError(msg)
        return cls(
            baseline_id=_str(data, "baseline_id"),
            baseline_config=D0BaselineConfig.from_dict(raw_config),
            runs=tuple(D0BaselineRun.from_dict(_mapping(item, "run")) for item in raw_runs),
            descriptor_schema=tuple(cast(list[str], raw_schema)),
            calibration_summary=_metadata(data.get("calibration_summary", {})),
        )

    def digest(self) -> str:
        return _digest(self.to_dict())


@dataclass(frozen=True, slots=True)
class D0CalibrationResult:
    """Audit result for D0 baseline calibration."""

    attempted: bool
    succeeded: bool
    run_count: int
    seed_count: int
    descriptor_names: tuple[str, ...]
    thresholds: dict[str, float]
    percentile_method: str
    baseline_digest: str
    reasons: tuple[str, ...]
    baseline_set: D0BaselineSet | None = None

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "attempted": self.attempted,
            "succeeded": self.succeeded,
            "run_count": self.run_count,
            "seed_count": self.seed_count,
            "descriptor_names": list(self.descriptor_names),
            "thresholds": dict(sorted(self.thresholds.items())),
            "percentile_method": self.percentile_method,
            "baseline_digest": self.baseline_digest,
            "reasons": list(self.reasons),
            "baseline_set": self.baseline_set.to_dict() if self.baseline_set is not None else None,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, JsonValue]) -> D0CalibrationResult:
        raw_baseline = data.get("baseline_set")
        return cls(
            attempted=_bool(data, "attempted", False),
            succeeded=_bool(data, "succeeded", False),
            run_count=_int(data, "run_count", 0),
            seed_count=_int(data, "seed_count", 0),
            descriptor_names=_str_tuple(data, "descriptor_names"),
            thresholds=_descriptor(data.get("thresholds")),
            percentile_method=_str(data, "percentile_method"),
            baseline_digest=_str(data, "baseline_digest"),
            reasons=_str_tuple(data, "reasons"),
            baseline_set=D0BaselineSet.from_dict(raw_baseline)
            if isinstance(raw_baseline, Mapping)
            else None,
        )

    def digest(self) -> str:
        return _digest(self.to_dict())


@dataclass(frozen=True, slots=True)
class D0DistanceMetricConfig:
    """Deterministic distance metric for D0 comparison."""

    metric: str = "normalized_l1"
    epsilon: float = 1e-9
    include_below_baseline_deviation: bool = False

    def __post_init__(self) -> None:
        if self.metric not in {
            "normalized_l1",
            "z_score_lite",
            "bin_distance",
            "out_of_envelope_count",
        }:
            msg = "Unsupported D0 distance metric."
            raise ConfigurationError(msg)
        if self.epsilon <= 0:
            msg = "D0DistanceMetricConfig.epsilon must be > 0."
            raise ConfigurationError(msg)

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "metric": self.metric,
            "epsilon": self.epsilon,
            "include_below_baseline_deviation": self.include_below_baseline_deviation,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, JsonValue]) -> D0DistanceMetricConfig:
        return cls(
            metric=_str(data, "metric", "normalized_l1"),
            epsilon=_float(data, "epsilon", 1e-9),
            include_below_baseline_deviation=_bool(data, "include_below_baseline_deviation", False),
        )

    def digest(self) -> str:
        return _digest(self.to_dict())


@dataclass(frozen=True, slots=True)
class DistanceToD0Result:
    """Distance between a candidate descriptor and a calibrated D0 set."""

    attempted: bool
    succeeded: bool
    distance: float
    metric: str
    baseline_digest: str
    descriptor_names: tuple[str, ...]
    reasons: tuple[str, ...]

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "attempted": self.attempted,
            "succeeded": self.succeeded,
            "distance": self.distance,
            "metric": self.metric,
            "baseline_digest": self.baseline_digest,
            "descriptor_names": list(self.descriptor_names),
            "reasons": list(self.reasons),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, JsonValue]) -> DistanceToD0Result:
        return cls(
            attempted=_bool(data, "attempted", False),
            succeeded=_bool(data, "succeeded", False),
            distance=_float(data, "distance", 0.0),
            metric=_str(data, "metric"),
            baseline_digest=_str(data, "baseline_digest"),
            descriptor_names=_str_tuple(data, "descriptor_names"),
            reasons=_str_tuple(data, "reasons"),
        )

    def digest(self) -> str:
        return _digest(self.to_dict())


@dataclass(frozen=True, slots=True)
class DiscoveryCandidate:
    """Conservative candidate evidence record against D0."""

    candidate_id: str
    source_run_id: str
    behavior_descriptor: dict[str, float]
    behavior_digest: str
    distance_to_d0: float
    novelty_threshold: float
    persistence_ticks: int
    mechanism_tags: tuple[str, ...]
    evidence_refs: tuple[str, ...]
    claim_level: DiscoveryClaimLevel
    reasons: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.candidate_id or not self.source_run_id:
            msg = "DiscoveryCandidate ids must not be empty."
            raise ConfigurationError(msg)
        if not isinstance(self.claim_level, DiscoveryClaimLevel):
            object.__setattr__(self, "claim_level", DiscoveryClaimLevel(str(self.claim_level)))
        copied_descriptor = dict(self.behavior_descriptor)
        _validate_descriptor(copied_descriptor)
        object.__setattr__(self, "behavior_descriptor", copied_descriptor)

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "candidate_id": self.candidate_id,
            "source_run_id": self.source_run_id,
            "behavior_descriptor": dict(sorted(self.behavior_descriptor.items())),
            "behavior_digest": self.behavior_digest,
            "distance_to_d0": self.distance_to_d0,
            "novelty_threshold": self.novelty_threshold,
            "persistence_ticks": self.persistence_ticks,
            "mechanism_tags": list(self.mechanism_tags),
            "evidence_refs": list(self.evidence_refs),
            "claim_level": self.claim_level.value,
            "reasons": list(self.reasons),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, JsonValue]) -> DiscoveryCandidate:
        return cls(
            candidate_id=_str(data, "candidate_id"),
            source_run_id=_str(data, "source_run_id"),
            behavior_descriptor=_descriptor(data.get("behavior_descriptor")),
            behavior_digest=_str(data, "behavior_digest"),
            distance_to_d0=_float(data, "distance_to_d0", 0.0),
            novelty_threshold=_float(data, "novelty_threshold", 0.0),
            persistence_ticks=_int(data, "persistence_ticks", 0),
            mechanism_tags=_str_tuple(data, "mechanism_tags"),
            evidence_refs=_str_tuple(data, "evidence_refs"),
            claim_level=DiscoveryClaimLevel(
                _str(data, "claim_level", DiscoveryClaimLevel.NONE.value)
            ),
            reasons=_str_tuple(data, "reasons"),
        )

    def digest(self) -> str:
        return _digest(self.to_dict())


@dataclass(frozen=True, slots=True)
class DiscoveryWitnessConfig:
    """Conservative gates for witness scaffolds; this is not proof logic."""

    min_witness_seeds: int = 3
    require_trace_digest: bool = True
    require_replay_digest: bool = True
    require_ablation_coverage: bool = True
    require_baseline_digest: bool = True
    min_persistence_ticks: int = 1
    supported_status_name: str = "supported_scaffold"

    def __post_init__(self) -> None:
        if self.min_witness_seeds <= 0:
            msg = "DiscoveryWitnessConfig.min_witness_seeds must be > 0."
            raise ConfigurationError(msg)
        if self.min_persistence_ticks < 0:
            msg = "DiscoveryWitnessConfig.min_persistence_ticks must be >= 0."
            raise ConfigurationError(msg)
        if not self.supported_status_name:
            msg = "DiscoveryWitnessConfig.supported_status_name must not be empty."
            raise ConfigurationError(msg)

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "min_witness_seeds": self.min_witness_seeds,
            "require_trace_digest": self.require_trace_digest,
            "require_replay_digest": self.require_replay_digest,
            "require_ablation_coverage": self.require_ablation_coverage,
            "require_baseline_digest": self.require_baseline_digest,
            "min_persistence_ticks": self.min_persistence_ticks,
            "supported_status_name": self.supported_status_name,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, JsonValue]) -> DiscoveryWitnessConfig:
        return cls(
            min_witness_seeds=_int(data, "min_witness_seeds", 3),
            require_trace_digest=_bool(data, "require_trace_digest", True),
            require_replay_digest=_bool(data, "require_replay_digest", True),
            require_ablation_coverage=_bool(data, "require_ablation_coverage", True),
            require_baseline_digest=_bool(data, "require_baseline_digest", True),
            min_persistence_ticks=_int(data, "min_persistence_ticks", 1),
            supported_status_name=_str(data, "supported_status_name", "supported_scaffold"),
        )

    def digest(self) -> str:
        return _digest(self.to_dict())


@dataclass(frozen=True, slots=True)
class WitnessValidationResult:
    """Gate-level validation result for witness evidence coverage."""

    passed: bool
    missing_ablation_ids: tuple[str, ...]
    seed_count: int
    required_seed_count: int
    coverage_ratio: float
    reasons: tuple[str, ...]

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "passed": self.passed,
            "missing_ablation_ids": list(self.missing_ablation_ids),
            "seed_count": self.seed_count,
            "required_seed_count": self.required_seed_count,
            "coverage_ratio": self.coverage_ratio,
            "reasons": list(self.reasons),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, JsonValue]) -> WitnessValidationResult:
        return cls(
            passed=_bool(data, "passed", False),
            missing_ablation_ids=_str_tuple(data, "missing_ablation_ids"),
            seed_count=_int(data, "seed_count", 0),
            required_seed_count=_int(data, "required_seed_count", 0),
            coverage_ratio=_float(data, "coverage_ratio", 0.0),
            reasons=_str_tuple(data, "reasons"),
        )

    def digest(self) -> str:
        return _digest(self.to_dict())


@dataclass(frozen=True, slots=True)
class DiscoveryWitness:
    """Auditable witness scaffold; never a proof by itself."""

    witness_id: str
    candidate: DiscoveryCandidate
    baseline_digest: str
    trace_digest: str
    replay_digest: str
    graph_digest: str
    vocabulary_digest: str
    capsule_store_digest: str
    required_ablation_ids: tuple[str, ...]
    supporting_ablation_ids: tuple[str, ...]
    witness_seeds: tuple[int, ...]
    persistence_summary: dict[str, JsonValue]
    status: str
    claim_level: DiscoveryClaimLevel
    reasons: tuple[str, ...]
    ablation_validation: WitnessValidationResult | None = None
    statistical_protocol_digest: str | None = None
    qd_archive_digest: str | None = None

    def __post_init__(self) -> None:
        if not self.witness_id:
            msg = "DiscoveryWitness.witness_id must not be empty."
            raise ConfigurationError(msg)
        if not isinstance(self.claim_level, DiscoveryClaimLevel):
            object.__setattr__(self, "claim_level", DiscoveryClaimLevel(str(self.claim_level)))

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "witness_id": self.witness_id,
            "candidate": self.candidate.to_dict(),
            "baseline_digest": self.baseline_digest,
            "trace_digest": self.trace_digest,
            "replay_digest": self.replay_digest,
            "graph_digest": self.graph_digest,
            "vocabulary_digest": self.vocabulary_digest,
            "capsule_store_digest": self.capsule_store_digest,
            "required_ablation_ids": list(self.required_ablation_ids),
            "supporting_ablation_ids": list(self.supporting_ablation_ids),
            "witness_seeds": list(self.witness_seeds),
            "persistence_summary": dict(sorted(self.persistence_summary.items())),
            "status": self.status,
            "claim_level": self.claim_level.value,
            "reasons": list(self.reasons),
            "ablation_validation": self.ablation_validation.to_dict()
            if self.ablation_validation is not None
            else None,
            "statistical_protocol_digest": self.statistical_protocol_digest,
            "qd_archive_digest": self.qd_archive_digest,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, JsonValue]) -> DiscoveryWitness:
        candidate_raw = data.get("candidate")
        raw_validation = data.get("ablation_validation")
        if not isinstance(candidate_raw, Mapping):
            msg = "DiscoveryWitness.candidate must be an object."
            raise ConfigurationError(msg)
        return cls(
            witness_id=_str(data, "witness_id"),
            candidate=DiscoveryCandidate.from_dict(candidate_raw),
            baseline_digest=_str(data, "baseline_digest"),
            trace_digest=_str(data, "trace_digest"),
            replay_digest=_str(data, "replay_digest"),
            graph_digest=_str(data, "graph_digest"),
            vocabulary_digest=_str(data, "vocabulary_digest"),
            capsule_store_digest=_str(data, "capsule_store_digest"),
            required_ablation_ids=_str_tuple(data, "required_ablation_ids"),
            supporting_ablation_ids=_str_tuple(data, "supporting_ablation_ids"),
            witness_seeds=_int_tuple(data, "witness_seeds"),
            persistence_summary=_metadata(data.get("persistence_summary", {})),
            status=_str(data, "status"),
            claim_level=DiscoveryClaimLevel(
                _str(data, "claim_level", DiscoveryClaimLevel.NONE.value)
            ),
            reasons=_str_tuple(data, "reasons"),
            ablation_validation=WitnessValidationResult.from_dict(raw_validation)
            if isinstance(raw_validation, Mapping)
            else None,
            statistical_protocol_digest=_optional_str(
                data.get("statistical_protocol_digest"), "statistical_protocol_digest"
            ),
            qd_archive_digest=_optional_str(data.get("qd_archive_digest"), "qd_archive_digest"),
        )

    def digest(self) -> str:
        return _digest(self.to_dict())


def calibrate_d0_baseline(
    runs: Sequence[D0BaselineRun], config: D0BaselineConfig
) -> D0CalibrationResult:
    """Calibrate D0 descriptor ranges without running experiments."""

    run_tuple = tuple(runs)
    descriptor_names = tuple(
        sorted({name for run in run_tuple for name in run.behavior_descriptor})
    )
    seed_count = len({run.seed for run in run_tuple})
    if not config.enabled:
        return D0CalibrationResult(
            attempted=True,
            succeeded=False,
            run_count=len(run_tuple),
            seed_count=seed_count,
            descriptor_names=descriptor_names,
            thresholds={},
            percentile_method="disabled",
            baseline_digest="",
            reasons=("d0_disabled",),
            baseline_set=None,
        )
    reasons: list[str] = []
    if len(run_tuple) < config.min_reference_runs:
        reasons.append("min_reference_runs_not_met")
    if seed_count < config.min_seeds:
        reasons.append("min_seeds_not_met")
    if not descriptor_names:
        reasons.append("descriptor_schema_empty")
    thresholds = {
        name: round(
            max((run.behavior_descriptor.get(name, 0.0) for run in run_tuple), default=0.0), 10
        )
        for name in descriptor_names
    }
    minima = {
        name: round(
            min((run.behavior_descriptor.get(name, 0.0) for run in run_tuple), default=0.0), 10
        )
        for name in descriptor_names
    }
    means = {
        name: round(_mean([run.behavior_descriptor.get(name, 0.0) for run in run_tuple]), 10)
        for name in descriptor_names
    }
    stds = {
        name: round(_std([run.behavior_descriptor.get(name, 0.0) for run in run_tuple]), 10)
        for name in descriptor_names
    }
    calibration_summary: dict[str, JsonValue] = {
        "thresholds": cast(dict[str, JsonValue], thresholds),
        "minima": cast(dict[str, JsonValue], minima),
        "means": cast(dict[str, JsonValue], means),
        "stds": cast(dict[str, JsonValue], stds),
        "percentile_method": "max_observed",
        "run_count": len(run_tuple),
        "seed_count": seed_count,
    }
    baseline_set = D0BaselineSet(
        baseline_id=f"d0:{_digest({'runs': [run.digest() for run in run_tuple]})[:16]}",
        baseline_config=config,
        runs=run_tuple,
        descriptor_schema=descriptor_names,
        calibration_summary=calibration_summary,
    )
    succeeded = not reasons
    return D0CalibrationResult(
        attempted=True,
        succeeded=succeeded,
        run_count=len(run_tuple),
        seed_count=seed_count,
        descriptor_names=descriptor_names,
        thresholds=thresholds,
        percentile_method="max_observed",
        baseline_digest=baseline_set.digest(),
        reasons=tuple(reasons) if reasons else ("calibrated",),
        baseline_set=baseline_set,
    )


def measure_distance_to_d0(
    candidate_descriptor: Descriptor,
    baseline_set: D0BaselineSet,
    metric_config: D0DistanceMetricConfig | None = None,
) -> DistanceToD0Result:
    """Measure candidate distance from D0 using deterministic pure-Python metrics."""

    config = metric_config or D0DistanceMetricConfig()
    descriptor = {str(k): float(v) for k, v in candidate_descriptor.items()}
    _validate_descriptor(descriptor)
    reasons: list[str] = []
    names = baseline_set.descriptor_schema
    if not baseline_set.runs:
        reasons.append("baseline_empty")
    if not names:
        reasons.append("descriptor_schema_empty")
    missing = tuple(name for name in names if name not in descriptor)
    if missing:
        reasons.append("descriptor_missing")
    if reasons:
        return DistanceToD0Result(
            True, False, 0.0, config.metric, baseline_set.digest(), names, tuple(reasons)
        )
    minima = {
        name: min(run.behavior_descriptor.get(name, 0.0) for run in baseline_set.runs)
        for name in names
    }
    maxima = {
        name: max(run.behavior_descriptor.get(name, 0.0) for run in baseline_set.runs)
        for name in names
    }
    if config.metric == "normalized_l1":
        distance = 0.0
        for name in names:
            candidate_value = descriptor[name]
            above = max(0.0, candidate_value - maxima[name])
            below = (
                max(0.0, minima[name] - candidate_value)
                if config.include_below_baseline_deviation
                else 0.0
            )
            scale = max(abs(maxima[name]), abs(minima[name]), 1.0, config.epsilon)
            distance += (above + below) / scale
        normalized = round(distance / max(1, len(names)), 10)
    elif config.metric == "z_score_lite":
        distance = 0.0
        for name in names:
            values = [run.behavior_descriptor.get(name, 0.0) for run in baseline_set.runs]
            mean = _mean(values)
            std = max(_std(values), config.epsilon)
            candidate_value = descriptor[name]
            deviation = max(0.0, candidate_value - maxima[name])
            if config.include_below_baseline_deviation:
                deviation = max(deviation, max(0.0, minima[name] - candidate_value))
            if deviation == 0.0:
                deviation = max(0.0, abs(candidate_value - mean) - std)
            distance += deviation / std
        normalized = round(distance / max(1, len(names)), 10)
    elif config.metric == "bin_distance":
        distance = 0.0
        bins = baseline_set.baseline_config.behavior_descriptor_bins
        for name in names:
            bin_count = bins.get(name, 1)
            if bin_count <= 0:
                reasons.append("invalid_descriptor_bins")
                break
            span = max(maxima[name] - minima[name], config.epsilon)
            baseline_bin = min(
                bin_count - 1, max(0, int((maxima[name] - minima[name]) / span * bin_count))
            )
            candidate_bin = min(
                bin_count - 1, max(0, int((descriptor[name] - minima[name]) / span * bin_count))
            )
            if descriptor[name] > maxima[name]:
                candidate_bin = bin_count
            elif descriptor[name] < minima[name]:
                candidate_bin = -1
            distance += abs(candidate_bin - baseline_bin) / max(1, bin_count)
        normalized = round(distance / max(1, len(names)), 10) if not reasons else 0.0
    else:
        count = 0
        for name in names:
            candidate_value = descriptor[name]
            if candidate_value > maxima[name] or (
                config.include_below_baseline_deviation and candidate_value < minima[name]
            ):
                count += 1
        normalized = float(count)
    if reasons:
        return DistanceToD0Result(
            True, False, 0.0, config.metric, baseline_set.digest(), names, tuple(reasons)
        )
    return DistanceToD0Result(
        attempted=True,
        succeeded=True,
        distance=normalized,
        metric=config.metric,
        baseline_digest=baseline_set.digest(),
        descriptor_names=names,
        reasons=("measured",),
    )


def evaluate_discovery_candidate(
    *,
    candidate_id: str,
    source_run_id: str,
    behavior_descriptor: Descriptor,
    behavior_digest: str,
    baseline_set: D0BaselineSet,
    metric_config: D0DistanceMetricConfig | None = None,
    novelty_threshold: float = 0.1,
    persistence_ticks: int = 0,
    min_persistence_ticks: int = 1,
    mechanism_tags: Sequence[str] = (),
    evidence_refs: Sequence[str] = (),
) -> DiscoveryCandidate:
    """Evaluate conservative candidate status against D0 evidence."""

    distance = measure_distance_to_d0(behavior_descriptor, baseline_set, metric_config)
    reasons: list[str] = []
    if not distance.succeeded:
        reasons.extend(distance.reasons)
    if distance.distance <= novelty_threshold:
        reasons.append("novelty_threshold_not_met")
    if persistence_ticks < min_persistence_ticks:
        reasons.append("persistence_not_met")
    if not evidence_refs:
        reasons.append("evidence_refs_missing")
    level = DiscoveryClaimLevel.NONE if reasons else DiscoveryClaimLevel.CANDIDATE
    return DiscoveryCandidate(
        candidate_id=candidate_id,
        source_run_id=source_run_id,
        behavior_descriptor=dict(
            sorted((str(k), float(v)) for k, v in behavior_descriptor.items())
        ),
        behavior_digest=behavior_digest,
        distance_to_d0=distance.distance,
        novelty_threshold=novelty_threshold,
        persistence_ticks=persistence_ticks,
        mechanism_tags=tuple(str(item) for item in mechanism_tags),
        evidence_refs=tuple(str(item) for item in evidence_refs),
        claim_level=level,
        reasons=tuple(reasons) if reasons else ("candidate_only_not_proof",),
    )


def validate_witness_evidence(
    *,
    required_ablation_ids: Sequence[str],
    supporting_ablation_ids: Sequence[str],
    witness_seeds: Sequence[int],
    config: DiscoveryWitnessConfig,
) -> WitnessValidationResult:
    """Validate seed count and ablation coverage for witness scaffolds."""

    required = tuple(str(item) for item in required_ablation_ids)
    supporting = tuple(str(item) for item in supporting_ablation_ids)
    missing = tuple(sorted(set(required) - set(supporting)))
    seed_count = len(set(int(item) for item in witness_seeds))
    reasons: list[str] = []
    if config.require_ablation_coverage and (not required or not supporting):
        reasons.append("ablation_metadata_missing")
    if config.require_ablation_coverage and missing:
        reasons.append("ablation_coverage_incomplete")
    if seed_count < config.min_witness_seeds:
        reasons.append("multi_seed_evidence_missing")
    coverage_ratio = (
        1.0 if not required else round((len(required) - len(missing)) / len(required), 10)
    )
    return WitnessValidationResult(
        passed=not reasons,
        missing_ablation_ids=missing,
        seed_count=seed_count,
        required_seed_count=config.min_witness_seeds,
        coverage_ratio=coverage_ratio,
        reasons=tuple(reasons) if reasons else ("validated",),
    )


def build_discovery_witness(
    *,
    witness_id: str,
    candidate: DiscoveryCandidate,
    baseline_digest: str,
    trace_digest: str,
    replay_digest: str,
    graph_digest: str,
    vocabulary_digest: str,
    capsule_store_digest: str,
    required_ablation_ids: Sequence[str] = (),
    supporting_ablation_ids: Sequence[str] = (),
    witness_seeds: Sequence[int] = (),
    persistence_summary: Mapping[str, JsonValue] | None = None,
    config: DiscoveryWitnessConfig | None = None,
    statistical_protocol_digest: str | None = None,
    qd_archive_digest: str | None = None,
) -> DiscoveryWitness:
    """Build a witness scaffold only when conservative evidence is present."""

    witness_config = config or DiscoveryWitnessConfig()
    validation = validate_witness_evidence(
        required_ablation_ids=required_ablation_ids,
        supporting_ablation_ids=supporting_ablation_ids,
        witness_seeds=witness_seeds,
        config=witness_config,
    )
    reasons: list[str] = []
    if candidate.claim_level is DiscoveryClaimLevel.NONE:
        reasons.append("candidate_not_supported")
    if witness_config.require_baseline_digest and not baseline_digest:
        reasons.append("baseline_missing")
    if witness_config.require_trace_digest and not trace_digest:
        reasons.append("trace_missing")
    if witness_config.require_replay_digest and not replay_digest:
        reasons.append("replay_missing")
    if candidate.persistence_ticks < witness_config.min_persistence_ticks:
        reasons.append("persistence_not_met")
    if not validation.passed:
        reasons.extend(validation.reasons)
    status = witness_config.supported_status_name if not reasons else "blocked"
    claim = DiscoveryClaimLevel.EVIDENCE_SUPPORTED if not reasons else DiscoveryClaimLevel.CANDIDATE
    return DiscoveryWitness(
        witness_id=witness_id,
        candidate=candidate,
        baseline_digest=baseline_digest,
        trace_digest=trace_digest,
        replay_digest=replay_digest,
        graph_digest=graph_digest,
        vocabulary_digest=vocabulary_digest,
        capsule_store_digest=capsule_store_digest,
        required_ablation_ids=tuple(str(item) for item in required_ablation_ids),
        supporting_ablation_ids=tuple(str(item) for item in supporting_ablation_ids),
        witness_seeds=tuple(int(item) for item in witness_seeds),
        persistence_summary=dict(persistence_summary or {}),
        status=status,
        claim_level=claim,
        reasons=tuple(reasons) if reasons else ("evidence_supported_scaffold_not_proof",),
        ablation_validation=validation,
        statistical_protocol_digest=statistical_protocol_digest,
        qd_archive_digest=qd_archive_digest,
    )


def _mean(values: Sequence[float]) -> float:
    if not values:
        return 0.0
    return sum(values) / len(values)


def _std(values: Sequence[float]) -> float:
    if len(values) < 2:
        return 0.0
    mean = _mean(values)
    return math.sqrt(sum((value - mean) ** 2 for value in values) / len(values))


def _validate_descriptor(value: Mapping[str, float]) -> None:
    for key, raw in value.items():
        if not isinstance(key, str) or isinstance(raw, bool) or not isinstance(raw, int | float):
            msg = "Behavior descriptors must be string -> numeric."
            raise ConfigurationError(msg)


def _descriptor(value: object) -> dict[str, float]:
    if not isinstance(value, Mapping):
        msg = "descriptor must be an object."
        raise ConfigurationError(msg)
    out: dict[str, float] = {}
    for key, raw in value.items():
        if not isinstance(key, str) or isinstance(raw, bool) or not isinstance(raw, int | float):
            msg = "descriptor entries must be string -> numeric."
            raise ConfigurationError(msg)
        out[key] = float(raw)
    return out


def _metadata(value: object) -> dict[str, JsonValue]:
    if not isinstance(value, Mapping):
        msg = "metadata must be an object."
        raise ConfigurationError(msg)
    return {str(key): raw for key, raw in value.items()}


def _mapping(value: object, name: str) -> Mapping[str, JsonValue]:
    if not isinstance(value, Mapping):
        msg = f"{name} must be an object."
        raise ConfigurationError(msg)
    return value


def _digest(payload: Mapping[str, JsonValue]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _str(data: Mapping[str, JsonValue], key: str, default: str | None = None) -> str:
    value = data.get(key, default)
    if not isinstance(value, str):
        msg = f"{key} must be a string."
        raise ConfigurationError(msg)
    return value


def _optional_str(value: object, key: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        msg = f"{key} must be a string or null."
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


def _int_tuple(data: Mapping[str, JsonValue], key: str) -> tuple[int, ...]:
    raw = data.get(key, [])
    if not isinstance(raw, list) or not all(
        isinstance(item, int) and not isinstance(item, bool) for item in raw
    ):
        msg = f"{key} must be a list of integers."
        raise ConfigurationError(msg)
    return tuple(cast(list[int], raw))
