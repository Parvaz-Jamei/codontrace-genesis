"""Causal validation protocols for GENESIS experiments.

These helpers deliberately separate *causal evidence levels* from stronger
causal claims. A plain :class:`CausalGraph` that records temporal precedence is
useful evidence, but it is not causal inference by itself. Stronger decisions
require association checks, conditional/context checks, intervention scenarios,
or ground-truth recovery benchmarks.
"""

from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from enum import Enum

from codontrace._types import JsonValue
from codontrace.errors import ConfigurationError
from codontrace.genesis.canonical import require_finite_float


class CausalEvidenceLevel(str, Enum):
    TEMPORAL_PRECEDENCE = "temporal_precedence"
    ASSOCIATION = "association"
    CONDITIONAL_ASSOCIATION = "conditional_association"
    INTERVENTIONAL_SUPPORT = "interventional_support"
    GROUND_TRUTH_RECOVERY = "ground_truth_recovery"


class CausalClaimDecision(str, Enum):
    EVIDENCE_LOG_ONLY = "evidence_log_only"
    ASSOCIATION_SUPPORTED = "association_supported"
    CONDITIONAL_ASSOCIATION_SUPPORTED = "conditional_association_supported"
    INTERVENTIONAL_SUPPORT = "interventional_support"
    GROUND_TRUTH_RECOVERY = "ground_truth_recovery"
    TRUE_CAUSALITY_NOT_CLAIMED = "true_causality_not_claimed"


@dataclass(frozen=True, slots=True)
class CausalValidationConfig:
    min_effect_size: float = 0.05
    min_samples: int = 4
    bootstrap_rounds: int = 64
    alpha: float = 0.05
    require_intervention_for_causal_claim: bool = True

    def __post_init__(self) -> None:
        object.__setattr__(self, "min_effect_size", require_finite_float("min_effect_size", self.min_effect_size, non_negative=True))
        object.__setattr__(self, "alpha", require_finite_float("alpha", self.alpha, probability=True))
        if self.min_samples < 0 or self.bootstrap_rounds < 0:
            raise ConfigurationError("min_samples/bootstrap_rounds must be non-negative")

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "min_effect_size": self.min_effect_size,
            "min_samples": self.min_samples,
            "bootstrap_rounds": self.bootstrap_rounds,
            "alpha": self.alpha,
            "require_intervention_for_causal_claim": self.require_intervention_for_causal_claim,
        }


@dataclass(frozen=True, slots=True)
class CausalAssociationTest:
    action: str
    outcome: str
    exposed_positive: int
    exposed_total: int
    unexposed_positive: int
    unexposed_total: int
    effect_size: float
    p_value: float
    supported: bool

    def __post_init__(self) -> None:
        object.__setattr__(self, "effect_size", require_finite_float("effect_size", self.effect_size))
        object.__setattr__(self, "p_value", require_finite_float("p_value", self.p_value, probability=True))

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "action": self.action,
            "outcome": self.outcome,
            "exposed_positive": self.exposed_positive,
            "exposed_total": self.exposed_total,
            "unexposed_positive": self.unexposed_positive,
            "unexposed_total": self.unexposed_total,
            "effect_size": self.effect_size,
            "p_value": self.p_value,
            "supported": self.supported,
        }

    def digest(self) -> str:
        return _digest(self.to_dict())


@dataclass(frozen=True, slots=True)
class ConditionalAssociationResult:
    action: str
    outcome: str
    context_key: str
    strata: tuple[CausalAssociationTest, ...]
    supported_strata: int
    supported: bool

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "action": self.action,
            "outcome": self.outcome,
            "context_key": self.context_key,
            "strata": [item.to_dict() for item in self.strata],
            "supported_strata": self.supported_strata,
            "supported": self.supported,
        }

    def digest(self) -> str:
        return _digest(self.to_dict())


@dataclass(frozen=True, slots=True)
class InterventionScenario:
    scenario_id: str
    control_label: str
    intervention_label: str
    target: str
    expected_direction: str = "different"
    metadata: dict[str, JsonValue] = field(default_factory=dict)

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "scenario_id": self.scenario_id,
            "control_label": self.control_label,
            "intervention_label": self.intervention_label,
            "target": self.target,
            "expected_direction": self.expected_direction,
            "metadata": dict(sorted(self.metadata.items())),
        }

    def digest(self) -> str:
        return _digest(self.to_dict())


@dataclass(frozen=True, slots=True)
class InterventionRunResult:
    scenario: InterventionScenario
    control_metric: float
    intervention_metric: float
    metric_name: str = "outcome_rate"

    def __post_init__(self) -> None:
        object.__setattr__(self, "control_metric", require_finite_float("control_metric", self.control_metric))
        object.__setattr__(self, "intervention_metric", require_finite_float("intervention_metric", self.intervention_metric))

    @property
    def delta(self) -> float:
        return round(self.intervention_metric - self.control_metric, 10)

    @property
    def supported(self) -> bool:
        if self.scenario.expected_direction == "decrease":
            return self.delta < 0
        if self.scenario.expected_direction == "increase":
            return self.delta > 0
        return not math.isclose(self.delta, 0.0, abs_tol=1e-12)

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "scenario": self.scenario.to_dict(),
            "metric_name": self.metric_name,
            "control_metric": self.control_metric,
            "intervention_metric": self.intervention_metric,
            "delta": self.delta,
            "supported": self.supported,
        }

    def digest(self) -> str:
        return _digest(self.to_dict())


@dataclass(frozen=True, slots=True)
class CounterfactualProbe:
    probe_id: str
    factual_outcome: str
    counterfactual_outcome: str
    expected_change: bool

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "probe_id": self.probe_id,
            "factual_outcome": self.factual_outcome,
            "counterfactual_outcome": self.counterfactual_outcome,
            "expected_change": self.expected_change,
            "observed_change": self.factual_outcome != self.counterfactual_outcome,
        }


@dataclass(frozen=True, slots=True)
class CausalGroundTruthScenario:
    scenario_id: str
    expected_edges: tuple[tuple[str, str], ...]
    baseline_accuracy: float = 0.0

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "scenario_id": self.scenario_id,
            "expected_edges": [[a, b] for a, b in self.expected_edges],
            "baseline_accuracy": self.baseline_accuracy,
        }

    def digest(self) -> str:
        return _digest(self.to_dict())


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
    def improvement(self) -> float:
        return round(self.accuracy - self.baseline_accuracy, 10)

    @property
    def supported(self) -> bool:
        return self.total > 0 and self.improvement > 0

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "scenario_id": self.scenario_id,
            "correct": self.correct,
            "total": self.total,
            "accuracy": self.accuracy,
            "baseline_accuracy": self.baseline_accuracy,
            "improvement": self.improvement,
            "supported": self.supported,
        }

    def digest(self) -> str:
        return _digest(self.to_dict())


@dataclass(frozen=True, slots=True)
class CausalValidationReport:
    evidence_levels: tuple[CausalEvidenceLevel, ...]
    decision: CausalClaimDecision
    temporal_edge_count: int = 0
    association: CausalAssociationTest | None = None
    conditional_association: ConditionalAssociationResult | None = None
    intervention: InterventionRunResult | None = None
    ground_truth: CausalPredictionAccuracyReport | None = None
    manifest_digest: str | None = None
    limitations: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "evidence_levels": [item.value for item in self.evidence_levels],
            "decision": self.decision.value,
            "temporal_edge_count": self.temporal_edge_count,
            "association": None if self.association is None else self.association.to_dict(),
            "conditional_association": None
            if self.conditional_association is None
            else self.conditional_association.to_dict(),
            "intervention": None if self.intervention is None else self.intervention.to_dict(),
            "ground_truth": None if self.ground_truth is None else self.ground_truth.to_dict(),
            "manifest_digest": self.manifest_digest,
            "limitations": list(self.limitations),
        }

    def digest(self) -> str:
        return _digest(self.to_dict())


def temporal_precedence_audit(graph: object | None) -> CausalValidationReport:
    """Return a limited evidence-log report for a CausalGraph-like object."""

    edge_count = len(getattr(graph, "edges", ()) or ()) if graph is not None else 0
    return CausalValidationReport(
        evidence_levels=(CausalEvidenceLevel.TEMPORAL_PRECEDENCE,),
        decision=CausalClaimDecision.EVIDENCE_LOG_ONLY,
        temporal_edge_count=edge_count,
        limitations=("temporal_precedence_is_not_causal_inference",),
    )


def simple_association_test(
    records: Sequence[Mapping[str, object]],
    *,
    action: str,
    outcome: str,
    config: CausalValidationConfig | None = None,
) -> CausalAssociationTest:
    """Compute a small deterministic action/outcome association report."""

    config = config or CausalValidationConfig()
    exposed_positive = exposed_total = unexposed_positive = unexposed_total = 0
    for record in records:
        is_exposed = record.get("action") == action
        observed = str(record.get("outcome", record.get("status", ""))) == outcome
        if is_exposed:
            exposed_total += 1
            exposed_positive += int(observed)
        else:
            unexposed_total += 1
            unexposed_positive += int(observed)
    exposed_rate = exposed_positive / exposed_total if exposed_total else 0.0
    unexposed_rate = unexposed_positive / unexposed_total if unexposed_total else 0.0
    effect = round(exposed_rate - unexposed_rate, 10)
    p_value = _deterministic_permutation_p(
        records,
        action=action,
        outcome=outcome,
        observed_effect=abs(effect),
        rounds=config.bootstrap_rounds,
    )
    supported = (exposed_total + unexposed_total) >= config.min_samples and abs(
        effect
    ) >= config.min_effect_size
    return CausalAssociationTest(
        action,
        outcome,
        exposed_positive,
        exposed_total,
        unexposed_positive,
        unexposed_total,
        effect,
        p_value,
        supported,
    )


def conditional_association_test(
    records: Sequence[Mapping[str, object]],
    *,
    action: str,
    outcome: str,
    context_key: str,
    config: CausalValidationConfig | None = None,
) -> ConditionalAssociationResult:
    config = config or CausalValidationConfig()
    buckets: dict[str, list[Mapping[str, object]]] = {}
    for record in records:
        buckets.setdefault(str(record.get(context_key, "missing")), []).append(record)
    strata_items = []
    for _, bucket in sorted(buckets.items()):
        bucket_config = CausalValidationConfig(
            min_effect_size=config.min_effect_size,
            min_samples=min(config.min_samples, max(1, len(bucket))),
            bootstrap_rounds=config.bootstrap_rounds,
            alpha=config.alpha,
            require_intervention_for_causal_claim=config.require_intervention_for_causal_claim,
        )
        strata_items.append(
            simple_association_test(bucket, action=action, outcome=outcome, config=bucket_config)
        )
    strata = tuple(strata_items)
    supported_strata = sum(1 for item in strata if item.supported)
    return ConditionalAssociationResult(
        action, outcome, context_key, strata, supported_strata, supported_strata > 0
    )


def evaluate_ground_truth_recovery(
    scenario: CausalGroundTruthScenario,
    predicted_edges: Sequence[tuple[str, str]],
) -> CausalPredictionAccuracyReport:
    expected = set(scenario.expected_edges)
    predicted = set(predicted_edges)
    correct = len(expected & predicted)
    total = len(expected)
    return CausalPredictionAccuracyReport(
        scenario.scenario_id, correct, total, scenario.baseline_accuracy
    )


def validate_causal_graph(
    *,
    graph: object | None,
    events: Sequence[Mapping[str, object]] = (),
    action: str | None = None,
    outcome: str | None = None,
    context_key: str | None = None,
    intervention: InterventionRunResult | None = None,
    ground_truth: CausalPredictionAccuracyReport | None = None,
    manifest_digest: str | None = None,
    config: CausalValidationConfig | None = None,
) -> CausalValidationReport:
    """Build a bounded causal validation report from available evidence.

    The function upgrades evidence levels only when the corresponding controlled
    evidence object is supplied. It never returns a ``true causality`` decision.
    """

    config = config or CausalValidationConfig()
    levels: list[CausalEvidenceLevel] = [CausalEvidenceLevel.TEMPORAL_PRECEDENCE]
    association = None
    conditional = None
    limitations: list[str] = ["causal_graph_is_evidence_scaffold_not_true_causal_discovery"]
    decision = CausalClaimDecision.EVIDENCE_LOG_ONLY
    edge_count = len(getattr(graph, "edges", ()) or ()) if graph is not None else 0

    if events and action is not None and outcome is not None:
        association = simple_association_test(events, action=action, outcome=outcome, config=config)
        if association.supported:
            levels.append(CausalEvidenceLevel.ASSOCIATION)
            decision = CausalClaimDecision.ASSOCIATION_SUPPORTED
    if events and action is not None and outcome is not None and context_key is not None:
        conditional = conditional_association_test(
            events, action=action, outcome=outcome, context_key=context_key, config=config
        )
        if conditional.supported:
            levels.append(CausalEvidenceLevel.CONDITIONAL_ASSOCIATION)
            decision = CausalClaimDecision.CONDITIONAL_ASSOCIATION_SUPPORTED
    if intervention is not None and intervention.supported:
        levels.append(CausalEvidenceLevel.INTERVENTIONAL_SUPPORT)
        decision = CausalClaimDecision.INTERVENTIONAL_SUPPORT
    if ground_truth is not None and ground_truth.supported:
        levels.append(CausalEvidenceLevel.GROUND_TRUTH_RECOVERY)
        decision = CausalClaimDecision.GROUND_TRUTH_RECOVERY
    return CausalValidationReport(
        evidence_levels=tuple(dict.fromkeys(levels)),
        decision=decision,
        temporal_edge_count=edge_count,
        association=association,
        conditional_association=conditional,
        intervention=intervention,
        ground_truth=ground_truth,
        manifest_digest=manifest_digest,
        limitations=tuple(limitations),
    )


def _deterministic_permutation_p(
    records: Sequence[Mapping[str, object]],
    *,
    action: str,
    outcome: str,
    observed_effect: float,
    rounds: int,
) -> float:
    if not records or rounds <= 0:
        return 1.0
    actions = [record.get("action") for record in records]
    outcomes = [str(record.get("outcome", record.get("status", ""))) for record in records]
    exceed = 0
    total = min(rounds, max(1, len(records)))
    for shift in range(total):
        rotated = actions[shift:] + actions[:shift]
        exposed = [outcomes[i] == outcome for i, value in enumerate(rotated) if value == action]
        unexposed = [outcomes[i] == outcome for i, value in enumerate(rotated) if value != action]
        e_rate = sum(exposed) / len(exposed) if exposed else 0.0
        u_rate = sum(unexposed) / len(unexposed) if unexposed else 0.0
        if abs(e_rate - u_rate) >= observed_effect:
            exceed += 1
    return round((exceed + 1) / (total + 1), 10)


def _digest(payload: Mapping[str, JsonValue]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


# --- Strong Library Phase 2 predictive/intervention audit objects ---
@dataclass(frozen=True, slots=True)
class PredictiveProbeResult:
    source_signal: str
    target_signal: str
    method: str
    predictive_gain: float
    p_value: float | None
    selected_lag: int | None
    tested_lags: tuple[int, ...]
    controls: tuple[str, ...]
    stationarity_check: str | None
    sample_count: int
    status: str
    evidence_level: str = "lagged_predictive_support"
    caveat: str = "predictive_precedence_not_mechanistic_causality"
    digest: str = ""

    def __post_init__(self) -> None:
        if self.method not in {"granger_lite", "statsmodels_granger", "pcmci", "permutation"}:
            raise ValueError("Unsupported predictive probe method.")
        if self.status not in {
            "insufficient_data",
            "predictive",
            "not_predictive",
            "confounded_candidate",
        }:
            raise ValueError("Unsupported predictive probe status.")
        if (
            self.method in {"granger_lite", "statsmodels_granger"}
            and not self.controls
            and self.status == "predictive"
        ):
            object.__setattr__(self, "status", "confounded_candidate")
        if self.method == "pcmci" and self.evidence_level == "intervention_supported":
            object.__setattr__(self, "evidence_level", "conditional_predictive_support")
        computed = _digest(self._payload())
        if self.digest and self.digest != computed:
            raise ConfigurationError(f"{self.__class__.__name__} digest mismatch.")
        object.__setattr__(self, "digest", computed)

    def _payload(self) -> dict[str, JsonValue]:
        return {
            "source_signal": self.source_signal,
            "target_signal": self.target_signal,
            "method": self.method,
            "predictive_gain": self.predictive_gain,
            "p_value": self.p_value,
            "selected_lag": self.selected_lag,
            "tested_lags": list(self.tested_lags),
            "controls": list(self.controls),
            "stationarity_check": self.stationarity_check,
            "sample_count": self.sample_count,
            "status": self.status,
            "evidence_level": self.evidence_level,
            "caveat": self.caveat,
        }

    def to_dict(self) -> dict[str, JsonValue]:
        return {**self._payload(), "digest": self.digest}


def granger_lite_probe(
    source: Sequence[float],
    target: Sequence[float],
    *,
    source_signal: str = "source",
    target_signal: str = "target",
    max_lag: int = 1,
) -> PredictiveProbeResult:
    n = min(len(source), len(target))
    if n <= max_lag + 1:
        return PredictiveProbeResult(
            source_signal,
            target_signal,
            "granger_lite",
            0.0,
            None,
            None,
            tuple(range(1, max_lag + 1)),
            (),
            None,
            n,
            "insufficient_data",
        )
    lag = max(1, max_lag)
    paired = [(float(source[i - lag]), float(target[i])) for i in range(lag, n)]
    x_mean = sum(x for x, _ in paired) / len(paired)
    y_mean = sum(y for _, y in paired) / len(paired)
    cov = sum((x - x_mean) * (y - y_mean) for x, y in paired)
    var = sum((x - x_mean) ** 2 for x, _ in paired) or 1.0
    gain = round(abs(cov / var), 10)
    status = "predictive" if gain > 0 else "not_predictive"
    return PredictiveProbeResult(
        source_signal,
        target_signal,
        "granger_lite",
        gain,
        None,
        lag,
        tuple(range(1, max_lag + 1)),
        (),
        "not_checked",
        n,
        status,
    )


@dataclass(frozen=True, slots=True)
class InterventionResult:
    scenario_id: str
    baseline_digest: str
    treatment_digest: str
    effect_size: float
    confidence_interval: tuple[float, float] | None
    paired_seed_count: int
    evidence_level: str = "intervention_supported"
    digest: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "effect_size", require_finite_float("effect_size", self.effect_size))
        if self.confidence_interval is not None:
            lo, hi = self.confidence_interval
            object.__setattr__(self, "confidence_interval", (require_finite_float("ci_low", lo), require_finite_float("ci_high", hi)))
        computed = _digest(self._payload())
        if self.digest and self.digest != computed:
            raise ConfigurationError("InterventionResult digest mismatch.")
        object.__setattr__(self, "digest", computed)

    def _payload(self) -> dict[str, JsonValue]:
        return {
            "scenario_id": self.scenario_id,
            "baseline_digest": self.baseline_digest,
            "treatment_digest": self.treatment_digest,
            "effect_size": self.effect_size,
            "confidence_interval": None
            if self.confidence_interval is None
            else list(self.confidence_interval),
            "paired_seed_count": self.paired_seed_count,
            "evidence_level": self.evidence_level,
        }

    def to_dict(self) -> dict[str, JsonValue]:
        return {**self._payload(), "digest": self.digest}


def build_intervention_result(
    scenario_id: str, baseline_values: Sequence[float], treatment_values: Sequence[float]
) -> InterventionResult:
    baseline_digest = _digest({"values": [float(v) for v in baseline_values]})
    treatment_digest = _digest({"values": [float(v) for v in treatment_values]})
    count = min(len(baseline_values), len(treatment_values))
    if count == 0:
        effect = 0.0
    else:
        effect = (
            sum(float(treatment_values[i]) - float(baseline_values[i]) for i in range(count))
            / count
        )
    return InterventionResult(
        scenario_id,
        baseline_digest,
        treatment_digest,
        round(effect, 10),
        (round(effect, 10), round(effect, 10)),
        count,
    )

@dataclass(frozen=True, slots=True)
class InterventionSpec:
    intervention_id: str
    target_factor: str
    baseline_config_digest: str
    treatment_config_digest: str
    seed_family_digest: str
    isolated_factor: bool = True
    schema_version: str = "intervention_spec_v1"

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "schema_version": self.schema_version,
            "intervention_id": self.intervention_id,
            "target_factor": self.target_factor,
            "baseline_config_digest": self.baseline_config_digest,
            "treatment_config_digest": self.treatment_config_digest,
            "seed_family_digest": self.seed_family_digest,
            "isolated_factor": self.isolated_factor,
        }

    def digest(self) -> str:
        from codontrace.genesis.canonical import canonical_digest
        return canonical_digest(self.to_dict())


@dataclass(frozen=True, slots=True)
class CounterfactualReplaySpec:
    baseline_replay_digest: str
    counterfactual_change: str
    expected_treatment_digest: str | None = None
    schema_version: str = "counterfactual_replay_spec_v1"

    def to_dict(self) -> dict[str, JsonValue]:
        return {"schema_version": self.schema_version, "baseline_replay_digest": self.baseline_replay_digest, "counterfactual_change": self.counterfactual_change, "expected_treatment_digest": self.expected_treatment_digest}

    def digest(self) -> str:
        from codontrace.genesis.canonical import canonical_digest
        return canonical_digest(self.to_dict())


@dataclass(frozen=True, slots=True)
class CausalInterventionRunPair:
    spec: InterventionSpec
    baseline_digest: str
    treatment_digest: str
    baseline_metric: float
    treatment_metric: float
    schema_version: str = "causal_intervention_run_pair_v1"

    def __post_init__(self) -> None:
        from codontrace.genesis.canonical import require_finite_float
        object.__setattr__(self, "baseline_metric", require_finite_float("baseline_metric", self.baseline_metric))
        object.__setattr__(self, "treatment_metric", require_finite_float("treatment_metric", self.treatment_metric))

    @property
    def paired_delta(self) -> float:
        return round(self.treatment_metric - self.baseline_metric, 10)

    def to_dict(self) -> dict[str, JsonValue]:
        return {"schema_version": self.schema_version, "spec": self.spec.to_dict(), "baseline_digest": self.baseline_digest, "treatment_digest": self.treatment_digest, "baseline_metric": self.baseline_metric, "treatment_metric": self.treatment_metric, "paired_delta": self.paired_delta}

    def digest(self) -> str:
        from codontrace.genesis.canonical import canonical_digest
        return canonical_digest(self.to_dict())


@dataclass(frozen=True, slots=True)
class CausalEffectEstimate:
    effect_size: float
    confidence_interval: tuple[float, float]
    sample_count: int
    non_finite_guard_status: str = "passed"
    schema_version: str = "causal_effect_estimate_v1"

    def __post_init__(self) -> None:
        from codontrace.genesis.canonical import require_finite_float
        object.__setattr__(self, "effect_size", require_finite_float("effect_size", self.effect_size))
        lo, hi = self.confidence_interval
        object.__setattr__(self, "confidence_interval", (require_finite_float("ci_low", lo), require_finite_float("ci_high", hi)))
        if self.sample_count < 0:
            raise ConfigurationError("sample_count must be non-negative")

    def to_dict(self) -> dict[str, JsonValue]:
        return {"schema_version": self.schema_version, "effect_size": self.effect_size, "confidence_interval": list(self.confidence_interval), "sample_count": self.sample_count, "non_finite_guard_status": self.non_finite_guard_status}

    def digest(self) -> str:
        from codontrace.genesis.canonical import canonical_digest
        return canonical_digest(self.to_dict())


@dataclass(frozen=True, slots=True)
class CausalEvidenceReport:
    run_pairs: tuple[CausalInterventionRunPair, ...]
    effect: CausalEffectEstimate
    failure_status: str = "passed"
    schema_version: str = "causal_evidence_report_v1"

    @property
    def claim_eligible(self) -> bool:
        return bool(self.run_pairs) and self.failure_status == "passed" and self.effect.sample_count == len(self.run_pairs)

    def to_dict(self) -> dict[str, JsonValue]:
        return {"schema_version": self.schema_version, "run_pairs": [p.to_dict() for p in self.run_pairs], "effect": self.effect.to_dict(), "failure_status": self.failure_status, "claim_eligible": self.claim_eligible}

    def digest(self) -> str:
        from codontrace.genesis.canonical import canonical_digest
        return canonical_digest(self.to_dict())


def build_causal_evidence_report(run_pairs: Sequence[CausalInterventionRunPair]) -> CausalEvidenceReport:
    pairs = tuple(run_pairs)
    if not pairs:
        effect = CausalEffectEstimate(0.0, (0.0, 0.0), 0)
        return CausalEvidenceReport((), effect, "not_run")
    deltas = [pair.paired_delta for pair in pairs]
    mean = round(sum(deltas) / len(deltas), 10)
    effect = CausalEffectEstimate(mean, (mean, mean), len(pairs))
    isolated = all(pair.spec.isolated_factor for pair in pairs)
    return CausalEvidenceReport(pairs, effect, "passed" if isolated else "intervention_not_isolated")

@dataclass(frozen=True, slots=True)
class InterventionExecutor:
    executor_id: str = "deterministic_public_api_executor_v1"
    schema_version: str = "intervention_executor_v1"
    def execute(self, spec: InterventionSpec, *, baseline_metric: float, treatment_metric: float) -> CausalInterventionRunPair:
        return CausalInterventionRunPair(spec, spec.baseline_config_digest, spec.treatment_config_digest, baseline_metric, treatment_metric)
    def to_dict(self) -> dict[str, JsonValue]:
        return {"schema_version": self.schema_version, "executor_id": self.executor_id}
    def digest(self) -> str:
        from codontrace.genesis.canonical import canonical_digest
        return canonical_digest(self.to_dict())

CausalEffectReport = CausalEvidenceReport
CausalAblationReport = CausalEvidenceReport
