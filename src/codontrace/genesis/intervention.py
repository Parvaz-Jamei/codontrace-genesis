"""Causal intervention protocol for controlled GENESIS benchmarks."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass, field

from codontrace._types import JsonValue


@dataclass(frozen=True, slots=True)
class InterventionScenario:
    scenario_id: str
    description: str
    expected_causal_outcome: str
    intervention_type: str
    target: str
    metadata: dict[str, JsonValue] = field(default_factory=dict)

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "scenario_id": self.scenario_id,
            "description": self.description,
            "expected_causal_outcome": self.expected_causal_outcome,
            "intervention_type": self.intervention_type,
            "target": self.target,
            "metadata": dict(sorted(self.metadata.items())),
        }

    def digest(self) -> str:
        return _digest(self.to_dict())


@dataclass(frozen=True, slots=True)
class CausalGroundTruthScenario:
    scenario: InterventionScenario
    control_outcome: str
    intervention_outcome: str

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "scenario": self.scenario.to_dict(),
            "control_outcome": self.control_outcome,
            "intervention_outcome": self.intervention_outcome,
        }

    def digest(self) -> str:
        return _digest(self.to_dict())


@dataclass(frozen=True, slots=True)
class CounterfactualProbe:
    probe_id: str
    control_digest: str
    intervention_digest: str
    expected_change: str

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "probe_id": self.probe_id,
            "control_digest": self.control_digest,
            "intervention_digest": self.intervention_digest,
            "expected_change": self.expected_change,
        }


@dataclass(frozen=True, slots=True)
class CausalPredictionAccuracyReport:
    scenario_id: str
    correct: int
    total: int
    baseline_accuracy: float = 0.0

    @property
    def accuracy(self) -> float:
        return 0.0 if self.total == 0 else round(self.correct / self.total, 10)

    @property
    def claim_status(self) -> str:
        return (
            "causal_prediction_supported"
            if self.total > 0 and self.accuracy > self.baseline_accuracy
            else "causal_claim_downgraded"
        )

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "scenario_id": self.scenario_id,
            "correct": self.correct,
            "total": self.total,
            "accuracy": self.accuracy,
            "baseline_accuracy": self.baseline_accuracy,
            "claim_status": self.claim_status,
        }

    def digest(self) -> str:
        return _digest(self.to_dict())


@dataclass(frozen=True, slots=True)
class CausalAblationMatrix:
    scenario_id: str
    rows: tuple[dict[str, JsonValue], ...]

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "scenario_id": self.scenario_id,
            "rows": [dict(sorted(row.items())) for row in self.rows],
        }

    def digest(self) -> str:
        return _digest(self.to_dict())


@dataclass(frozen=True, slots=True)
class InterventionProtocol:
    scenarios: tuple[CausalGroundTruthScenario, ...]
    min_accuracy_delta: float = 0.0

    def evaluate_predictions(
        self, predictions: Mapping[str, str], *, baseline_accuracy: float = 0.0
    ) -> CausalPredictionAccuracyReport:
        total = len(self.scenarios)
        correct = 0
        first_id = self.scenarios[0].scenario.scenario_id if self.scenarios else "empty"
        for scenario in self.scenarios:
            expected = scenario.intervention_outcome
            if predictions.get(scenario.scenario.scenario_id) == expected:
                correct += 1
        report = CausalPredictionAccuracyReport(first_id, correct, total, baseline_accuracy)
        if report.accuracy - baseline_accuracy < self.min_accuracy_delta:
            return CausalPredictionAccuracyReport(first_id, correct, total, baseline_accuracy)
        return report

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "scenarios": [item.to_dict() for item in self.scenarios],
            "min_accuracy_delta": self.min_accuracy_delta,
        }

    def digest(self) -> str:
        return _digest(self.to_dict())


def _digest(payload: Mapping[str, JsonValue]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()

# ---------------------------------------------------------------------------
# Counterfactual replay protocol (P2)
# ---------------------------------------------------------------------------
from codontrace.genesis.canonical import canonical_digest as _intervention_canonical_digest, require_finite_float as _intervention_require_finite_float

_COUNTERFACTUAL_REPLAY_INTERVENTIONS = {
    "disable_capsule_transfer",
    "disable_capsule_utility",
    "disable_source_fitness_weighting",
    "disable_signal_memory_link",
    "disable_skill_compression",
    "ablate_role",
    "remove_memory",
    "remove_capsule",
    "remove_qd_pressure",
    "remove_adf_macro",
    "remove_causal_edge",
    "remove_tool_action",
    "remove_social_partner",
    "counterfactual_world_seed",
}


@dataclass(frozen=True, slots=True)
class CounterfactualReplayProtocol:
    base_replay_digest: str
    intervention_type: str
    target_tick: int
    target_agent_id: str | None = None
    preserve_rng_stream: bool = True
    protocol_id: str = "counterfactual_replay_protocol"
    schema_version: str = "counterfactual_replay_protocol_v1"

    def __post_init__(self) -> None:
        if not self.base_replay_digest:
            raise ValueError("base_replay_digest is required")
        if self.intervention_type not in _COUNTERFACTUAL_REPLAY_INTERVENTIONS:
            raise ValueError(f"unsupported counterfactual intervention_type {self.intervention_type!r}")
        if self.target_tick < 0:
            raise ValueError("target_tick must be non-negative")

    def to_dict(self) -> dict[str, JsonValue]:
        return {"schema_version": self.schema_version, "protocol_id": self.protocol_id, "base_replay_digest": self.base_replay_digest, "intervention_type": self.intervention_type, "target_tick": self.target_tick, "target_agent_id": self.target_agent_id, "preserve_rng_stream": self.preserve_rng_stream}

    def digest(self) -> str:
        return _intervention_canonical_digest(self.to_dict(), prefix="counterfactual_replay_protocol")


@dataclass(frozen=True, slots=True)
class CounterfactualReplayResult:
    protocol_digest: str
    base_replay_digest: str
    counterfactual_replay_digest: str
    outcome_delta: float
    rng_stream_preserved: bool
    intervention_manifest_digest: str | None = None
    failure_reason: str | None = None
    schema_version: str = "counterfactual_replay_result_v1"
    record_digest: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "outcome_delta", round(_intervention_require_finite_float("outcome_delta", self.outcome_delta), 10))
        if not self.record_digest:
            object.__setattr__(self, "record_digest", _intervention_canonical_digest(self._payload(), prefix="counterfactual_replay_result"))

    @property
    def claim_eligible(self) -> bool:
        return not self.failure_reason and self.rng_stream_preserved and bool(self.intervention_manifest_digest) and self.outcome_delta != 0.0

    def _payload(self) -> dict[str, JsonValue]:
        return {"schema_version": self.schema_version, "protocol_digest": self.protocol_digest, "base_replay_digest": self.base_replay_digest, "counterfactual_replay_digest": self.counterfactual_replay_digest, "outcome_delta": self.outcome_delta, "rng_stream_preserved": self.rng_stream_preserved, "intervention_manifest_digest": self.intervention_manifest_digest, "failure_reason": self.failure_reason, "claim_eligible": self.claim_eligible}

    def to_dict(self) -> dict[str, JsonValue]:
        return {**self._payload(), "record_digest": self.record_digest}

    def digest(self) -> str:
        return self.record_digest


CounterfactualReplayIntervention = CounterfactualReplayProtocol
