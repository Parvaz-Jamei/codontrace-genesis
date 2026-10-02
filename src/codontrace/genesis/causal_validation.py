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


ASSOCIATION_ESTIMATOR = "fisher_exact_independent_v1"
HISTORICAL_ASSOCIATION_ESTIMATOR = "circular_shift_empty_rate_v0"
STRATA_AGGREGATION_RULE = "bonferroni_eligible_strata_v1"
# Fisher (1922, JRSS 85:87–94) is an exact test of independence in a 2×2 table
# when the records are exchangeable and the margins are conditioned on. A
# circular shift of the action labels is not that test: it only visits n
# rotations, and the historical helper also treated a missing group as rate 0.
# Ordered trials are not exchangeable records, so a temporal series does not
# inherit this p-value. Eligible strata are those with both exposure groups
# and at least ``min_samples`` rows; their family-wise threshold is
# alpha / n_eligible (Bonferroni; Dunn 1961, JASA 56:52–64). The threshold is
# never lowered to fit a small stratum.
RECORD_STRUCTURES = ("unspecified", "independent", "temporal")


def _log_comb(n: int, k: int) -> float:
    if k < 0 or k > n:
        return float("-inf")
    return math.lgamma(n + 1) - math.lgamma(k + 1) - math.lgamma(n - k + 1)


def _fisher_exact_two_sided(a: int, b: int, c: int, d: int) -> float:
    """Two-sided Fisher exact p-value. Tables at least as rare as the observed one."""

    row1 = a + b
    row2 = c + d
    col1 = a + c
    n = row1 + row2
    if min(row1, row2) <= 0 or n <= 0:
        raise ValueError("Fisher's exact test needs both exposure groups")
    lo = max(0, col1 - row2)
    hi = min(row1, col1)
    logs = [
        _log_comb(row1, aa) + _log_comb(row2, col1 - aa) - _log_comb(n, col1)
        for aa in range(lo, hi + 1)
    ]
    observed = logs[a - lo]
    total = 0.0
    for log_p in logs:
        if log_p <= observed + 1e-12:
            total += math.exp(log_p)
    return min(1.0, total)


@dataclass(frozen=True, slots=True)
class CausalAssociationTest:
    action: str
    outcome: str
    exposed_positive: int
    exposed_total: int
    unexposed_positive: int
    unexposed_total: int
    effect_size: float | None
    p_value: float | None
    supported: bool
    status: str = "tested"
    effect_defined: bool = False
    effect_observed: bool = False
    statistical_support: bool = False
    alpha: float = 0.05
    nominal_alpha: float = 0.05
    record_structure: str = "unspecified"
    test_name: str = ASSOCIATION_ESTIMATOR
    p_value_role: str = "not_applicable"
    min_samples_applied: int = 0
    historical_supported: bool = False
    historical_circular_shift_p: float | None = None
    eligible_for_family: bool = False

    def __post_init__(self) -> None:
        if self.effect_size is not None:
            object.__setattr__(self, "effect_size", require_finite_float("effect_size", self.effect_size))
        if self.p_value is not None:
            object.__setattr__(self, "p_value", require_finite_float("p_value", self.p_value, probability=True))
        object.__setattr__(self, "alpha", require_finite_float("alpha", self.alpha, probability=True))
        object.__setattr__(self, "nominal_alpha", require_finite_float("nominal_alpha", self.nominal_alpha, probability=True))

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "action": self.action,
            "outcome": self.outcome,
            "exposed_positive": self.exposed_positive,
            "exposed_total": self.exposed_total,
            "unexposed_positive": self.unexposed_positive,
            "unexposed_total": self.unexposed_total,
            "effect_size": self.effect_size,
            "effect_defined": self.effect_defined,
            "effect_observed": self.effect_observed,
            "p_value": self.p_value,
            "p_value_role": self.p_value_role,
            "supported": self.supported,
            "statistical_support": self.statistical_support,
            "status": self.status,
            "alpha": self.alpha,
            "nominal_alpha": self.nominal_alpha,
            "record_structure": self.record_structure,
            "test_name": self.test_name,
            "min_samples_applied": self.min_samples_applied,
            "historical_estimator": HISTORICAL_ASSOCIATION_ESTIMATOR,
            "historical_supported": self.historical_supported,
            "historical_circular_shift_p": self.historical_circular_shift_p,
            "eligible_for_family": self.eligible_for_family,
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
    statistical_support: bool = False
    status: str = "no_eligible_stratum"
    n_strata: int = 0
    n_eligible_strata: int = 0
    historical_supported_strata: int = 0
    aggregation_rule: str = STRATA_AGGREGATION_RULE
    nominal_alpha: float = 0.05
    alpha_adjusted: float | None = None

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "action": self.action,
            "outcome": self.outcome,
            "context_key": self.context_key,
            "strata": [item.to_dict() for item in self.strata],
            "supported_strata": self.supported_strata,
            "supported": self.supported,
            "statistical_support": self.statistical_support,
            "status": self.status,
            "n_strata": self.n_strata,
            "n_eligible_strata": self.n_eligible_strata,
            "historical_supported_strata": self.historical_supported_strata,
            "aggregation_rule": self.aggregation_rule,
            "nominal_alpha": self.nominal_alpha,
            "alpha_adjusted": self.alpha_adjusted,
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


def _exposure_counts(
    records: Sequence[Mapping[str, object]],
    *,
    action: str,
    outcome: str,
) -> tuple[int, int, int, int]:
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
    return exposed_positive, exposed_total, unexposed_positive, unexposed_total


def _legacy_empty_rate_supported(
    records: Sequence[Mapping[str, object]],
    *,
    action: str,
    outcome: str,
    min_samples: int,
    min_effect_size: float,
    lower_floor: bool,
) -> bool:
    """Historical rule. A missing group was given rate 0, and alpha was ignored.

    ``lower_floor`` is the old conditional path, which also reduced
    ``min_samples`` to the stratum size. Neither path is a decision.
    """

    exposed_positive, exposed_total, unexposed_positive, unexposed_total = _exposure_counts(
        records, action=action, outcome=outcome
    )
    exposed_rate = exposed_positive / exposed_total if exposed_total else 0.0
    unexposed_rate = unexposed_positive / unexposed_total if unexposed_total else 0.0
    effect = exposed_rate - unexposed_rate
    floor = min(min_samples, max(1, len(records))) if lower_floor else min_samples
    return (exposed_total + unexposed_total) >= floor and abs(effect) >= min_effect_size


def simple_association_test(
    records: Sequence[Mapping[str, object]],
    *,
    action: str,
    outcome: str,
    config: CausalValidationConfig | None = None,
    record_structure: str = "unspecified",
) -> CausalAssociationTest:
    """Action/outcome association with the comparison and the test kept apart.

    ``effect_observed`` is the substantive rate difference. ``supported`` is
    statistical support only: both exposure groups exist, the caller's
    ``min_samples`` is met and is not reduced, ``record_structure`` is
    ``independent``, and a two-sided Fisher exact p-value is at or below
    ``alpha``. Changing ``alpha`` changes that decision.

    A missing group is ``insufficient_comparison``. Its rate is not filled in
    with zero, so the old ``effect_size == 1`` does not reappear.
    ``historical_supported`` records that old pass and does not grant support.

    ``temporal`` records are not treated as exchangeable trials. The historical
    circular-shift p-value is stored and is not used for either structure.
    """

    config = config or CausalValidationConfig()
    if record_structure not in RECORD_STRUCTURES:
        raise ValueError(f"record_structure must be one of {RECORD_STRUCTURES}")
    exposed_positive, exposed_total, unexposed_positive, unexposed_total = _exposure_counts(
        records, action=action, outcome=outcome
    )
    n_records = exposed_total + unexposed_total
    effect_defined = exposed_total > 0 and unexposed_total > 0
    effect: float | None = None
    if effect_defined:
        effect = round(
            exposed_positive / exposed_total - unexposed_positive / unexposed_total,
            10,
        )
    effect_observed = bool(effect is not None and abs(effect) >= config.min_effect_size)
    historical_p = _deterministic_permutation_p(
        records,
        action=action,
        outcome=outcome,
        observed_effect=abs(effect) if effect is not None else 1.0,
        rounds=config.bootstrap_rounds,
    )
    historical = _legacy_empty_rate_supported(
        records,
        action=action,
        outcome=outcome,
        min_samples=config.min_samples,
        min_effect_size=config.min_effect_size,
        lower_floor=False,
    )
    fisher: float | None = None
    if effect_defined:
        fisher = _fisher_exact_two_sided(
            exposed_positive,
            exposed_total - exposed_positive,
            unexposed_positive,
            unexposed_total - unexposed_positive,
        )
    eligible = bool(
        effect_defined and n_records >= config.min_samples and record_structure == "independent"
    )
    statistical = bool(eligible and fisher is not None and fisher <= config.alpha)
    if not effect_defined:
        status = "insufficient_comparison"
        role = "not_applicable"
    elif n_records < config.min_samples:
        status = "insufficient_sample"
        role = "descriptive_fisher_not_used"
    elif record_structure == "unspecified":
        status = "record_structure_unspecified"
        role = "descriptive_fisher_not_used"
    elif record_structure == "temporal":
        status = "temporal_dependence_not_tested"
        role = "descriptive_fisher_not_used"
    else:
        status = "tested"
        role = "fisher_exact_two_sided"
    return CausalAssociationTest(
        action=action,
        outcome=outcome,
        exposed_positive=exposed_positive,
        exposed_total=exposed_total,
        unexposed_positive=unexposed_positive,
        unexposed_total=unexposed_total,
        effect_size=effect,
        p_value=fisher,
        supported=statistical,
        status=status,
        effect_defined=effect_defined,
        effect_observed=effect_observed,
        statistical_support=statistical,
        alpha=config.alpha,
        nominal_alpha=config.alpha,
        record_structure=record_structure,
        test_name=ASSOCIATION_ESTIMATOR,
        p_value_role=role,
        min_samples_applied=config.min_samples,
        historical_supported=historical,
        historical_circular_shift_p=historical_p,
        eligible_for_family=eligible,
    )


def conditional_association_test(
    records: Sequence[Mapping[str, object]],
    *,
    action: str,
    outcome: str,
    context_key: str,
    config: CausalValidationConfig | None = None,
    record_structure: str = "unspecified",
) -> ConditionalAssociationResult:
    """Per-context association. The sample floor is not lowered inside a stratum.

    Aggregation is locked as ``bonferroni_eligible_strata_v1``: only strata
    with both exposure groups, ``n >= min_samples`` and independent records
    are tests. Their threshold is ``alpha / n_eligible``. One stratum surviving
    that threshold is the conditional claim. Empty or single-record strata
    are not tests and do not count toward support. The historical count, which
    lowered ``min_samples`` to the stratum size and treated a missing group as
    rate 0, is reported separately and is not the decision.
    """

    config = config or CausalValidationConfig()
    buckets: dict[str, list[Mapping[str, object]]] = {}
    for record in records:
        buckets.setdefault(str(record.get(context_key, "missing")), []).append(record)
    ordered = [buckets[key] for key in sorted(buckets)]
    drafts = [
        simple_association_test(
            bucket, action=action, outcome=outcome, config=config, record_structure=record_structure
        )
        for bucket in ordered
    ]
    eligible_buckets = [bucket for bucket, draft in zip(ordered, drafts, strict=True) if draft.eligible_for_family]
    n_eligible = len(eligible_buckets)
    adjusted = (config.alpha / n_eligible) if n_eligible else None
    if adjusted is None:
        strata = tuple(drafts)
    else:
        adjusted_config = CausalValidationConfig(
            min_effect_size=config.min_effect_size,
            min_samples=config.min_samples,
            bootstrap_rounds=config.bootstrap_rounds,
            alpha=adjusted,
            require_intervention_for_causal_claim=config.require_intervention_for_causal_claim,
        )
        strata_items = []
        for bucket, draft in zip(ordered, drafts, strict=True):
            if draft.eligible_for_family:
                tested = simple_association_test(
                    bucket,
                    action=action,
                    outcome=outcome,
                    config=adjusted_config,
                    record_structure=record_structure,
                )
                strata_items.append(
                    CausalAssociationTest(
                        action=tested.action,
                        outcome=tested.outcome,
                        exposed_positive=tested.exposed_positive,
                        exposed_total=tested.exposed_total,
                        unexposed_positive=tested.unexposed_positive,
                        unexposed_total=tested.unexposed_total,
                        effect_size=tested.effect_size,
                        p_value=tested.p_value,
                        supported=tested.supported,
                        status=tested.status,
                        effect_defined=tested.effect_defined,
                        effect_observed=tested.effect_observed,
                        statistical_support=tested.statistical_support,
                        alpha=tested.alpha,
                        nominal_alpha=config.alpha,
                        record_structure=tested.record_structure,
                        test_name=tested.test_name,
                        p_value_role=tested.p_value_role,
                        min_samples_applied=config.min_samples,
                        historical_supported=tested.historical_supported,
                        historical_circular_shift_p=tested.historical_circular_shift_p,
                        eligible_for_family=tested.eligible_for_family,
                    )
                )
            else:
                strata_items.append(draft)
        strata = tuple(strata_items)
    supported_strata = sum(1 for item in strata if item.statistical_support)
    historical_strata = sum(
        1
        for bucket in ordered
        if _legacy_empty_rate_supported(
            bucket,
            action=action,
            outcome=outcome,
            min_samples=config.min_samples,
            min_effect_size=config.min_effect_size,
            lower_floor=True,
        )
    )
    if record_structure != "independent":
        status = "record_structure_unspecified" if record_structure == "unspecified" else "temporal_dependence_not_tested"
    elif n_eligible == 0:
        status = "no_eligible_stratum"
    elif supported_strata > 0:
        status = "statistical_support"
    else:
        status = "not_significant"
    statistical = supported_strata > 0
    return ConditionalAssociationResult(
        action=action,
        outcome=outcome,
        context_key=context_key,
        strata=strata,
        supported_strata=supported_strata,
        supported=statistical,
        statistical_support=statistical,
        status=status,
        n_strata=len(strata),
        n_eligible_strata=n_eligible,
        historical_supported_strata=historical_strata,
        aggregation_rule=STRATA_AGGREGATION_RULE,
        nominal_alpha=config.alpha,
        alpha_adjusted=adjusted,
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
    record_structure: str = "unspecified",
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
        association = simple_association_test(
            events,
            action=action,
            outcome=outcome,
            config=config,
            record_structure=record_structure,
        )
        if association.statistical_support and association.effect_observed:
            levels.append(CausalEvidenceLevel.ASSOCIATION)
            decision = CausalClaimDecision.ASSOCIATION_SUPPORTED
        elif association.status == "insufficient_comparison":
            limitations.append("insufficient_comparison")
        elif association.effect_observed and not association.statistical_support:
            limitations.append("effect_without_statistical_support")
    if events and action is not None and outcome is not None and context_key is not None:
        conditional = conditional_association_test(
            events,
            action=action,
            outcome=outcome,
            context_key=context_key,
            config=config,
            record_structure=record_structure,
        )
        if conditional.statistical_support:
            levels.append(CausalEvidenceLevel.CONDITIONAL_ASSOCIATION)
            decision = CausalClaimDecision.CONDITIONAL_ASSOCIATION_SUPPORTED
        elif conditional.historical_supported_strata and not conditional.statistical_support:
            limitations.append("historical_strata_pass_is_not_statistical_support")
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

def _normalize_settings(value: object) -> tuple[tuple[str, str], ...]:
    """Canonical setting pairs. Key order does not matter; the value does."""

    if value is None:
        return ()
    if isinstance(value, Mapping):
        raw = list(value.items())
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        raw = list(value)
    else:
        raise ConfigurationError("settings must be a mapping or a list of pairs")
    out: list[tuple[str, str]] = []
    for item in raw:
        if not isinstance(item, tuple) or len(item) != 2:
            raise ConfigurationError("setting pairs must be (key, value)")
        key, item_value = item
        if not isinstance(key, str) or not key.strip():
            raise ConfigurationError("setting keys must be non-empty strings")
        rendered = json.dumps(item_value, sort_keys=True, separators=(",", ":"))
        out.append((key, rendered))
    if len({key for key, _ in out}) != len(out):
        raise ConfigurationError("setting keys must be unique")
    return tuple(sorted(out))


@dataclass(frozen=True, slots=True)
class InterventionSpec:
    intervention_id: str
    target_factor: str
    baseline_config_digest: str
    treatment_config_digest: str
    seed_family_digest: str
    isolated_factor: bool = True
    schema_version: str = "intervention_spec_v1"
    baseline_settings: tuple[tuple[str, str], ...] = ()
    treatment_settings: tuple[tuple[str, str], ...] = ()

    def __post_init__(self) -> None:
        if not str(self.target_factor).strip():
            raise ConfigurationError("target_factor must be non-empty")
        object.__setattr__(self, "baseline_settings", _normalize_settings(self.baseline_settings))
        object.__setattr__(self, "treatment_settings", _normalize_settings(self.treatment_settings))

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "schema_version": self.schema_version,
            "intervention_id": self.intervention_id,
            "target_factor": self.target_factor,
            "baseline_config_digest": self.baseline_config_digest,
            "treatment_config_digest": self.treatment_config_digest,
            "seed_family_digest": self.seed_family_digest,
            "isolated_factor": self.isolated_factor,
            "baseline_settings": [list(item) for item in self.baseline_settings],
            "treatment_settings": [list(item) for item in self.treatment_settings],
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
    run_id: str = ""
    seed: int | None = None
    history_id: str = ""
    checkpoint_id: str = ""

    def __post_init__(self) -> None:
        from codontrace.genesis.canonical import require_finite_float
        object.__setattr__(self, "baseline_metric", require_finite_float("baseline_metric", self.baseline_metric))
        object.__setattr__(self, "treatment_metric", require_finite_float("treatment_metric", self.treatment_metric))
        object.__setattr__(self, "run_id", str(self.run_id).strip())
        object.__setattr__(self, "history_id", str(self.history_id).strip())
        object.__setattr__(self, "checkpoint_id", str(self.checkpoint_id).strip())
        if self.seed is not None:
            if isinstance(self.seed, bool) or not isinstance(self.seed, int):
                raise ConfigurationError("seed must be an integer")
            object.__setattr__(self, "seed", int(self.seed))

    @property
    def paired_delta(self) -> float:
        return round(self.treatment_metric - self.baseline_metric, 10)

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "schema_version": self.schema_version,
            "spec": self.spec.to_dict(),
            "baseline_digest": self.baseline_digest,
            "treatment_digest": self.treatment_digest,
            "baseline_metric": self.baseline_metric,
            "treatment_metric": self.treatment_metric,
            "paired_delta": self.paired_delta,
            "run_id": self.run_id,
            "seed": self.seed,
            "history_id": self.history_id,
            "checkpoint_id": self.checkpoint_id,
        }

    def digest(self) -> str:
        from codontrace.genesis.canonical import canonical_digest
        return canonical_digest(self.to_dict())


@dataclass(frozen=True, slots=True)
class CausalEffectEstimate:
    effect_size: float
    confidence_interval: tuple[float, float] | None
    sample_count: int
    non_finite_guard_status: str = "passed"
    schema_version: str = "causal_effect_estimate_v1"
    interval_defined: bool = True
    interval_status: str = "student_t_95"
    statistical_support: bool = False
    estimator: str = "student_t_paired_mean_v2"
    df: int | None = None
    critical_value: float | None = None

    def __post_init__(self) -> None:
        from codontrace.genesis.canonical import require_finite_float
        object.__setattr__(self, "effect_size", require_finite_float("effect_size", self.effect_size))
        if self.confidence_interval is None:
            if self.interval_defined:
                raise ConfigurationError("an undefined interval has no endpoints")
        else:
            if not self.interval_defined:
                raise ConfigurationError("endpoints were supplied for an undefined interval")
            lo, hi = self.confidence_interval
            lo = require_finite_float("ci_low", lo)
            hi = require_finite_float("ci_high", hi)
            if lo > hi:
                raise ConfigurationError("ci_low cannot exceed ci_high")
            object.__setattr__(self, "confidence_interval", (lo, hi))
        if self.critical_value is not None:
            object.__setattr__(self, "critical_value", require_finite_float("critical_value", self.critical_value, non_negative=True))
        if self.sample_count < 0:
            raise ConfigurationError("sample_count must be non-negative")

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "schema_version": self.schema_version,
            "effect_size": self.effect_size,
            "confidence_interval": None if self.confidence_interval is None else list(self.confidence_interval),
            "sample_count": self.sample_count,
            "non_finite_guard_status": self.non_finite_guard_status,
            "interval_defined": self.interval_defined,
            "interval_status": self.interval_status,
            "statistical_support": self.statistical_support,
            "estimator": self.estimator,
            "df": self.df,
            "critical_value": self.critical_value,
        }

    def digest(self) -> str:
        from codontrace.genesis.canonical import canonical_digest
        return canonical_digest(self.to_dict())


@dataclass(frozen=True, slots=True)
class CausalEvidenceReport:
    run_pairs: tuple[CausalInterventionRunPair, ...]
    effect: CausalEffectEstimate
    failure_status: str = "passed"
    schema_version: str = "causal_evidence_report_v1"
    submitted_count: int = 0
    independent_count: int = 0
    dropped_duplicate_count: int = 0
    checkpoint_conflict_count: int = 0
    identity_complete: bool = False
    isolation_status: str = "isolation_unverified"
    historical_sample_count: int = 0
    unit_rule: str = "independent_history_seed_run_v1"

    @property
    def claim_eligible(self) -> bool:
        """True only when this package would not be rejected by the ClaimGate rules it can check.

        Those rules are the ones in ``claimgate.auditor``: no pseudoreplication
        (Hurlbert 1984), a defined interval that excludes zero, and at least
        ``INDEPENDENT_RUN_FLOOR`` independent units (the same floor as
        ``LEVEL4_MIN_SEEDS``). A self-declared ``isolated_factor`` is not enough.
        ``failure_status == "passed"`` means the rows were usable. It is not itself
        a claim.
        """

        return not self.claim_blockers

    @property
    def claim_blockers(self) -> tuple[str, ...]:
        blockers: list[str] = []
        if self.failure_status != "passed":
            blockers.append(self.failure_status)
        if not self.identity_complete:
            blockers.append("identity_unspecified")
        if self.isolation_status != "isolated":
            blockers.append(self.isolation_status)
        if self.dropped_duplicate_count or self.checkpoint_conflict_count:
            blockers.append("pseudoreplicated")
        if not self.effect.interval_defined:
            blockers.append(self.effect.interval_status)
        elif not self.effect.statistical_support:
            blockers.append("interval_includes_zero")
        if self.independent_count < INDEPENDENT_RUN_FLOOR:
            blockers.append("below_claimgate_seed_floor")
        if self.effect.sample_count != self.independent_count:
            blockers.append("sample_count_mismatch")
        return tuple(dict.fromkeys(blockers))

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "schema_version": self.schema_version,
            "run_pairs": [p.to_dict() for p in self.run_pairs],
            "effect": self.effect.to_dict(),
            "failure_status": self.failure_status,
            "claim_eligible": self.claim_eligible,
            "claim_blockers": list(self.claim_blockers),
            "submitted_count": self.submitted_count,
            "independent_count": self.independent_count,
            "dropped_duplicate_count": self.dropped_duplicate_count,
            "checkpoint_conflict_count": self.checkpoint_conflict_count,
            "identity_complete": self.identity_complete,
            "isolation_status": self.isolation_status,
            "historical_sample_count": self.historical_sample_count,
            "unit_rule": self.unit_rule,
        }

    def digest(self) -> str:
        from codontrace.genesis.canonical import canonical_digest
        return canonical_digest(self.to_dict())


_T975_BY_DF: dict[int, float] = {
    1: 12.706, 2: 4.303, 3: 3.182, 4: 2.776, 5: 2.571, 6: 2.447, 7: 2.365,
    8: 2.306, 9: 2.262, 10: 2.228, 11: 2.201, 12: 2.179, 13: 2.160, 14: 2.145,
    15: 2.131, 16: 2.120, 17: 2.110, 18: 2.101, 19: 2.093, 20: 2.086, 21: 2.080,
    22: 2.074, 23: 2.069, 24: 2.064, 25: 2.060, 26: 2.056, 27: 2.052, 28: 2.048,
    29: 2.045, 30: 2.042,
}
# Historical only. df > 30 used to fall through to the normal 1.96. That cliff
# is not a Student-t quantile (at df=31 the 0.975 quantile is about 2.0395).
PAIRED_MEAN_ESTIMATOR = "student_t_paired_mean_v2"
HISTORICAL_PAIRED_ESTIMATOR = "t_table_through_df30_then_1.96_v0"
_NORMAL_975 = 1.96


def _historical_t975(df: int) -> float:
    """Old critical value: three-decimal table through df=30, then 1.96."""

    return _T975_BY_DF.get(df, _NORMAL_975)


def _betacf(a: float, b: float, x: float) -> float:
    """Modified Lentz continued fraction for the incomplete-beta tail."""

    qab = a + b
    qap = a + 1.0
    qam = a - 1.0
    c = 1.0
    d = 1.0 - qab * x / qap
    if abs(d) < 1e-30:
        d = 1e-30
    d = 1.0 / d
    h = d
    for m in range(1, 201):
        m2 = 2 * m
        aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        d = 1.0 + aa * d
        if abs(d) < 1e-30:
            d = 1e-30
        c = 1.0 + aa / c
        if abs(c) < 1e-30:
            c = 1e-30
        d = 1.0 / d
        h *= d * c
        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        d = 1.0 + aa * d
        if abs(d) < 1e-30:
            d = 1e-30
        c = 1.0 + aa / c
        if abs(c) < 1e-30:
            c = 1e-30
        d = 1.0 / d
        delta = d * c
        h *= delta
        if abs(delta - 1.0) <= 3e-14:
            return h
    raise ConfigurationError("incomplete-beta continued fraction did not converge")


def _regularized_incomplete_beta(a: float, b: float, x: float) -> float:
    """Regularized incomplete beta I_x(a, b). Same continued fraction scipy uses."""

    if x <= 0.0:
        return 0.0
    if x >= 1.0:
        return 1.0
    log_bt = (
        math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b)
        + a * math.log(x) + b * math.log(1.0 - x)
    )
    bt = math.exp(log_bt)
    if x < (a + 1.0) / (a + b + 2.0):
        return bt * _betacf(a, b, x) / a
    return 1.0 - bt * _betacf(b, a, 1.0 - x) / b


def _inverse_regularized_beta(a: float, b: float, p: float) -> float:
    """Inverse of I_x(a, b) by bisection. Used only to invert the t identity."""

    if p <= 0.0:
        return 0.0
    if p >= 1.0:
        return 1.0
    lo = 0.0
    hi = 1.0
    for _ in range(80):
        mid = 0.5 * (lo + hi)
        if _regularized_incomplete_beta(a, b, mid) < p:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def student_t_quantile(df: int, probability: float = 0.975) -> float:
    """Upper Student-t quantile. No normal approximation and no df cutoff.

    For q > 1/2 the identity used by ``scipy.stats.t.ppf`` is
    ``t = sqrt(df * (1 - x) / x)`` with ``x = I^{-1}_{2(1-q)}(df/2, 1/2)``.
    The df → ∞ limit is the normal quantile. It is not substituted at df=31.
    """

    if isinstance(df, bool) or not isinstance(df, int) or df < 1:
        raise ConfigurationError("df must be an integer >= 1")
    if isinstance(probability, bool) or not isinstance(probability, (int, float)):
        raise ConfigurationError("probability must be in (0.5, 1)")
    q = float(probability)
    if not math.isfinite(q) or not 0.5 < q < 1.0:
        raise ConfigurationError("probability must be in (0.5, 1)")
    x = _inverse_regularized_beta(df / 2.0, 0.5, 2.0 * (1.0 - q))
    if x <= 0.0:
        raise ConfigurationError("Student-t quantile is undefined for this tail")
    return math.sqrt(df * (1.0 - x) / x)


def _finite_deltas(deltas: Sequence[float]) -> list[float]:
    out: list[float] = []
    for value in deltas:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ConfigurationError("paired deltas must be finite numbers")
        number = float(value)
        if not math.isfinite(number):
            raise ConfigurationError("paired deltas must be finite numbers")
        out.append(number)
    return out


@dataclass(frozen=True, slots=True)
class PairedMeanInterval:
    """95% interval for a mean of independent paired deltas.

    ``statistical_support`` is true only when a real Student-t interval is
    defined and excludes zero. A missing dispersion estimate is not an
    interval at the origin, and it is not support.
    """

    point: float | None
    low: float | None
    high: float | None
    n: int
    status: str
    interval_defined: bool
    statistical_support: bool
    df: int | None = None
    critical: float | None = None
    historical_critical: float | None = None
    historical_low: float | None = None
    historical_high: float | None = None
    estimator: str = PAIRED_MEAN_ESTIMATOR
    historical_estimator: str = HISTORICAL_PAIRED_ESTIMATOR

    def endpoints(self) -> tuple[float, float]:
        if not self.interval_defined or self.low is None or self.high is None:
            raise ConfigurationError(f"paired interval is not defined ({self.status})")
        return (self.low, self.high)


def paired_mean_interval(deltas: Sequence[float]) -> PairedMeanInterval:
    """Student-t interval for the mean. The 1.96 cliff at df>30 is gone.

    One observation, or two or more identical observations, has no residual
    degrees of freedom that can be turned into a confidence interval. The
    point estimate is kept. The old helper returned ``(0, 0)`` in both cases
    and that placeholder is not reproduced.
    """

    values = _finite_deltas(deltas)
    n = len(values)
    if n == 0:
        return PairedMeanInterval(None, None, None, 0, "empty", False, False)
    point = round(sum(values) / n, 10)
    if n < 2:
        return PairedMeanInterval(point, None, None, n, "insufficient_sample", False, False)
    variance = sum((value - (sum(values) / n)) ** 2 for value in values) / (n - 1)
    df = n - 1
    historical = _historical_t975(df)
    if variance <= 0.0:
        return PairedMeanInterval(
            point, None, None, n, "degenerate_variance", False, False,
            df=df, historical_critical=historical,
        )
    mean = sum(values) / n
    standard_error = math.sqrt(variance / n)
    critical = student_t_quantile(df)
    half = critical * standard_error
    historical_half = historical * standard_error
    low = round(mean - half, 10)
    high = round(mean + half, 10)
    return PairedMeanInterval(
        point=round(mean, 10),
        low=low,
        high=high,
        n=n,
        status="student_t_95",
        interval_defined=True,
        statistical_support=bool(low > 0.0 or high < 0.0),
        df=df,
        critical=critical,
        historical_critical=historical,
        historical_low=round(mean - historical_half, 10),
        historical_high=round(mean + historical_half, 10),
    )


def _paired_interval(deltas: Sequence[float]) -> tuple[float, float]:
    """Endpoints of a defined 95% paired-t interval.

    Raises when the interval is not defined. The historical ``(0, 0)``
    placeholder is not a confidence interval for the mean.
    """

    return paired_mean_interval(deltas).endpoints()


# Same floor as claimgate.auditor.LEVEL4_MIN_SEEDS. Repeating rows does not buy it.
INDEPENDENT_RUN_FLOOR = 16


def _isolation_status(spec: InterventionSpec) -> str:
    """Isolation is a diff of settings, not the ``isolated_factor`` boolean.

    The boolean cannot grant isolation. It can only refuse it. With no settings
    on both sides the factor is unverified even when the boolean is true.
    """

    if spec.isolated_factor is False:
        return "intervention_not_isolated"
    if not spec.baseline_settings or not spec.treatment_settings:
        return "isolation_unverified"
    base = dict(spec.baseline_settings)
    treat = dict(spec.treatment_settings)
    changed = sorted(key for key in set(base) | set(treat) if base.get(key) != treat.get(key))
    target = spec.target_factor
    if changed == [target] and base.get(target) != treat.get(target):
        return "isolated"
    return "intervention_not_isolated"


def _identity_complete(pair: CausalInterventionRunPair) -> bool:
    return bool(pair.run_id) and pair.seed is not None and bool(pair.history_id)


def _unit_key(pair: CausalInterventionRunPair) -> tuple[object, ...]:
    """One experimental unit. A checkpoint of that unit is not another unit.

    Hurlbert (1984) simple pseudoreplication: subsamples and repeated measures
    of one unit are not replicates. An unidentified row collapses only with an
    exact copy of itself; it still cannot support a claim.
    """

    if _identity_complete(pair):
        return ("unit", pair.history_id, pair.seed, pair.run_id)
    return ("unidentified", pair.digest())


def _effect_from_interval(interval: PairedMeanInterval, sample_count: int) -> CausalEffectEstimate:
    if not interval.interval_defined or interval.low is None or interval.high is None:
        return CausalEffectEstimate(
            0.0 if interval.point is None else interval.point,
            None,
            sample_count,
            interval_defined=False,
            interval_status=interval.status,
            statistical_support=False,
            estimator=interval.estimator,
            df=interval.df,
            critical_value=interval.critical,
        )
    return CausalEffectEstimate(
        0.0 if interval.point is None else interval.point,
        (interval.low, interval.high),
        sample_count,
        interval_defined=True,
        interval_status=interval.status,
        statistical_support=interval.statistical_support,
        estimator=interval.estimator,
        df=interval.df,
        critical_value=interval.critical,
    )


def build_causal_evidence_report(run_pairs: Sequence[CausalInterventionRunPair]) -> CausalEvidenceReport:
    """Interval over independent histories, not over submitted rows.

    Repeating a run-pair, or offering several checkpoints of one history, does
    not increase ``sample_count`` and does not narrow the interval. The count
    the old helper would have used is kept as ``historical_sample_count`` and
    is not the estimate.
    """

    submitted = tuple(run_pairs)
    if not submitted:
        effect = CausalEffectEstimate(
            0.0, None, 0, interval_defined=False, interval_status="not_run",
            statistical_support=False, estimator=PAIRED_MEAN_ESTIMATOR,
        )
        return CausalEvidenceReport((), effect, "not_run", submitted_count=0, historical_sample_count=0)

    groups: dict[tuple[object, ...], list[CausalInterventionRunPair]] = {}
    order: list[tuple[object, ...]] = []
    for pair in submitted:
        key = _unit_key(pair)
        if key not in groups:
            groups[key] = []
            order.append(key)
        groups[key].append(pair)

    usable: list[CausalInterventionRunPair] = []
    dropped = 0
    conflicts = 0
    collapsed_checkpoints = 0
    for key in order:
        group = groups[key]
        deltas = {item.paired_delta for item in group}
        checkpoints = {item.checkpoint_id for item in group}
        if len(deltas) > 1:
            conflicts += 1
            continue
        if len(group) > 1 and len(checkpoints) > 1:
            collapsed_checkpoints += 1
            dropped += len(group) - 1
        elif len(group) > 1:
            dropped += len(group) - 1
        usable.append(group[0])

    interval = paired_mean_interval([item.paired_delta for item in usable]) if usable else PairedMeanInterval(
        None, None, None, 0, "empty", False, False,
    )
    effect = _effect_from_interval(interval, len(usable))
    identity_complete = all(_identity_complete(item) for item in submitted)
    states = {_isolation_status(item.spec) for item in submitted}
    if states == {"isolated"}:
        isolation = "isolated"
    elif len(states) == 1:
        isolation = next(iter(states))
    else:
        isolation = "intervention_not_isolated"
    if conflicts or collapsed_checkpoints:
        status = "checkpoint_not_independent"
    elif dropped:
        status = "duplicate_units_removed"
    elif not identity_complete:
        status = "identity_unspecified"
    elif isolation != "isolated":
        status = isolation
    elif not interval.interval_defined:
        status = interval.status
    else:
        status = "passed"
    return CausalEvidenceReport(
        tuple(usable),
        effect,
        status,
        submitted_count=len(submitted),
        independent_count=len(usable),
        dropped_duplicate_count=dropped,
        checkpoint_conflict_count=conflicts,
        identity_complete=identity_complete,
        isolation_status=isolation,
        historical_sample_count=len(submitted),
    )


@dataclass(frozen=True, slots=True)
class InterventionExecutor:
    executor_id: str = "deterministic_public_api_executor_v1"
    schema_version: str = "intervention_executor_v1"

    def execute(
        self,
        spec: InterventionSpec,
        *,
        baseline_metric: float,
        treatment_metric: float,
        run_id: str = "",
        seed: int | None = None,
        history_id: str = "",
        checkpoint_id: str = "",
    ) -> CausalInterventionRunPair:
        return CausalInterventionRunPair(
            spec,
            spec.baseline_config_digest,
            spec.treatment_config_digest,
            baseline_metric,
            treatment_metric,
            run_id=run_id,
            seed=seed,
            history_id=history_id,
            checkpoint_id=checkpoint_id,
        )
    def to_dict(self) -> dict[str, JsonValue]:
        return {"schema_version": self.schema_version, "executor_id": self.executor_id}
    def digest(self) -> str:
        from codontrace.genesis.canonical import canonical_digest
        return canonical_digest(self.to_dict())

CausalEffectReport = CausalEvidenceReport
CausalAblationReport = CausalEvidenceReport
