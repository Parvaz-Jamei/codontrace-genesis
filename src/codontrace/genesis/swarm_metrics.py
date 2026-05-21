"""Swarm coordination metrics separate from ordinary social interaction."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from codontrace._types import JsonValue
from codontrace.genesis.canonical import canonical_digest, require_finite_float


@dataclass(frozen=True, slots=True)
class SwarmMetricReport:
    alignment_score: float
    cohesion_score: float
    separation_score: float
    distributed_task_coverage: float
    decentralized_coordination_score: float
    local_rule_dependency: float
    shuffled_agent_control_delta: float
    single_agent_baseline_delta: float
    no_communication_baseline_delta: float
    sample_count: int
    schema_version: str = "swarm_metric_report_v1"
    digest: str = ""

    def __post_init__(self) -> None:
        for attr in (
            "alignment_score", "cohesion_score", "separation_score",
            "distributed_task_coverage", "decentralized_coordination_score",
            "local_rule_dependency", "shuffled_agent_control_delta",
            "single_agent_baseline_delta", "no_communication_baseline_delta",
        ):
            object.__setattr__(self, attr, round(require_finite_float(attr, getattr(self, attr)), 10))
        if self.sample_count < 0:
            raise ValueError("sample_count must be non-negative")
        computed = canonical_digest(self._payload())
        if self.digest and self.digest != computed:
            raise ValueError("SwarmMetricReport digest mismatch")
        object.__setattr__(self, "digest", computed)

    @property
    def claim_eligible(self) -> bool:
        return (
            self.sample_count >= 2
            and self.decentralized_coordination_score > 0.0
            and self.distributed_task_coverage > 0.0
            and self.shuffled_agent_control_delta > 0.0
            and self.single_agent_baseline_delta > 0.0
            and self.no_communication_baseline_delta > 0.0
        )

    def _payload(self) -> dict[str, JsonValue]:
        return {
            "schema_version": self.schema_version,
            "alignment_score": self.alignment_score,
            "cohesion_score": self.cohesion_score,
            "separation_score": self.separation_score,
            "distributed_task_coverage": self.distributed_task_coverage,
            "decentralized_coordination_score": self.decentralized_coordination_score,
            "local_rule_dependency": self.local_rule_dependency,
            "shuffled_agent_control_delta": self.shuffled_agent_control_delta,
            "single_agent_baseline_delta": self.single_agent_baseline_delta,
            "no_communication_baseline_delta": self.no_communication_baseline_delta,
            "sample_count": self.sample_count,
        }

    def to_dict(self) -> dict[str, JsonValue]:
        return {**self._payload(), "claim_eligible": self.claim_eligible, "digest": self.digest}


def compute_swarm_metric_report(
    positions_by_tick: Sequence[Mapping[str, tuple[int, int]]],
    *,
    group_task_coverage: float = 0.0,
    shuffled_agent_control_delta: float = 0.0,
    single_agent_baseline_delta: float = 0.0,
    no_communication_baseline_delta: float = 0.0,
) -> SwarmMetricReport:
    ticks = [dict(item) for item in positions_by_tick if len(item) >= 2]
    sample_count = len(ticks)
    if not ticks:
        return SwarmMetricReport(0.0, 0.0, 0.0, group_task_coverage, 0.0, 0.0, shuffled_agent_control_delta, single_agent_baseline_delta, no_communication_baseline_delta, 0)
    # Simple deterministic spatial proxies; enough for library-level evidence surfaces.
    avg_pair_distance = 0.0
    for mapping in ticks:
        values = list(mapping.values())
        distances = []
        for i, a in enumerate(values):
            for b in values[i+1:]:
                distances.append(abs(a[0]-b[0]) + abs(a[1]-b[1]))
        avg_pair_distance += sum(distances) / max(1, len(distances))
    avg_pair_distance /= sample_count
    cohesion = 1.0 / (1.0 + avg_pair_distance)
    separation = min(1.0, avg_pair_distance / 10.0)
    alignment = 1.0 if sample_count > 1 else 0.0
    decentralized = group_task_coverage * cohesion
    return SwarmMetricReport(alignment, cohesion, separation, group_task_coverage, decentralized, 1.0 if sample_count > 0 else 0.0, shuffled_agent_control_delta, single_agent_baseline_delta, no_communication_baseline_delta, sample_count)

@dataclass(frozen=True, slots=True)
class SwarmResilienceReport:
    baseline_performance: float
    dropout_performance: float
    perturbation_digest: str
    control_digest: str
    schema_version: str = "swarm_resilience_report_v1"
    def __post_init__(self) -> None:
        object.__setattr__(self, "baseline_performance", require_finite_float("baseline_performance", self.baseline_performance))
        object.__setattr__(self, "dropout_performance", require_finite_float("dropout_performance", self.dropout_performance))
    @property
    def resilience_delta(self) -> float:
        return round(self.dropout_performance - self.baseline_performance, 10)
    @property
    def claim_eligible(self) -> bool:
        return bool(self.perturbation_digest) and bool(self.control_digest)
    def to_dict(self) -> dict[str, JsonValue]:
        return {"schema_version": self.schema_version, "baseline_performance": self.baseline_performance, "dropout_performance": self.dropout_performance, "resilience_delta": self.resilience_delta, "perturbation_digest": self.perturbation_digest, "control_digest": self.control_digest, "claim_eligible": self.claim_eligible}
    def digest(self) -> str:
        return canonical_digest(self.to_dict())

ScalingCurveReport = SwarmResilienceReport
