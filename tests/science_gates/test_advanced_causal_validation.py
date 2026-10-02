import pytest

from codontrace.genesis.causal_validation import (
    CausalClaimDecision,
    CausalGroundTruthScenario,
    CausalValidationConfig,
    InterventionRunResult,
    InterventionScenario,
    conditional_association_test,
    evaluate_ground_truth_recovery,
    simple_association_test,
    temporal_precedence_audit,
    validate_causal_graph,
)


def _perfect_split() -> list[dict[str, object]]:
    """4 exposed successes and 4 unexposed failures. Two-sided Fisher p is 2/70."""

    exposed = [{"action": "EAT_LUMEN", "outcome": "success"} for _ in range(4)]
    unexposed = [{"action": "WAIT", "outcome": "blocked"} for _ in range(4)]
    return exposed + unexposed


def test_causal_temporal_precedence_is_not_causal_claim() -> None:
    report = temporal_precedence_audit(graph=None)
    assert report.decision is CausalClaimDecision.EVIDENCE_LOG_ONLY
    assert "temporal_precedence_is_not_causal_inference" in report.limitations


def test_causal_association_and_conditional_context() -> None:
    """A real contrast is an effect. It is not statistical support until the test says so."""

    events = [
        {"action": "EAT_LUMEN", "outcome": "success", "resource_nearby": True},
        {"action": "EAT_LUMEN", "outcome": "success", "resource_nearby": True},
        {"action": "WAIT", "outcome": "blocked", "resource_nearby": True},
        {"action": "WAIT", "outcome": "blocked", "resource_nearby": False},
        {"action": "MOVE", "outcome": "blocked", "resource_nearby": False},
    ]
    association = simple_association_test(
        events, action="EAT_LUMEN", outcome="success", record_structure="independent"
    )
    conditional = conditional_association_test(
        events,
        action="EAT_LUMEN",
        outcome="success",
        context_key="resource_nearby",
        record_structure="independent",
    )
    # 2/2 versus 0/3. Fisher two-sided p is 0.1, which does not meet alpha 0.05.
    assert association.effect_observed
    assert association.effect_size is not None and association.effect_size > 0
    assert association.p_value == pytest.approx(0.1)
    assert association.statistical_support is False
    assert association.supported is False
    assert conditional.supported is False
    assert conditional.supported_strata == 0
    assert all(item.min_samples_applied == 4 for item in conditional.strata)


def test_missing_comparison_is_not_statistical_support() -> None:
    """Witness 1. Four exposed successes used to pass with effect 1 and p 1."""

    events = [{"action": "A", "outcome": "Y"} for _ in range(4)]
    for alpha in (0.05, 0.0001):
        config = CausalValidationConfig(alpha=alpha)
        result = simple_association_test(
            events, action="A", outcome="Y", config=config, record_structure="independent"
        )
        assert result.exposed_total == 4
        assert result.unexposed_total == 0
        assert result.effect_defined is False
        assert result.effect_size is None
        assert result.p_value is None
        assert result.status == "insufficient_comparison"
        assert result.statistical_support is False
        assert result.supported is False
        assert result.historical_supported is True
        assert result.historical_circular_shift_p == 1.0
        assert result.min_samples_applied == 4
        report = validate_causal_graph(
            graph=None, events=events, action="A", outcome="Y", config=config, record_structure="independent"
        )
        assert report.decision is CausalClaimDecision.EVIDENCE_LOG_ONLY
        assert report.decision is not CausalClaimDecision.ASSOCIATION_SUPPORTED
        assert "insufficient_comparison" in report.limitations


def test_single_record_strata_are_not_counted_and_the_floor_is_not_lowered() -> None:
    """Witness 2. Four one-record contexts used to be four supported strata."""

    events = [
        {"action": "A", "outcome": "Y", "context": f"c{i}"}
        for i in range(4)
    ]
    result = conditional_association_test(
        events, action="A", outcome="Y", context_key="context", record_structure="independent"
    )
    assert result.n_strata == 4
    assert result.historical_supported_strata == 4
    assert result.n_eligible_strata == 0
    assert result.supported_strata == 0
    assert result.supported is False
    assert result.statistical_support is False
    assert result.status == "no_eligible_stratum"
    assert result.aggregation_rule == "bonferroni_eligible_strata_v1"
    for stratum in result.strata:
        assert stratum.exposed_total == 1
        assert stratum.unexposed_total == 0
        assert stratum.status == "insufficient_comparison"
        assert stratum.p_value is None
        assert stratum.supported is False
        assert stratum.min_samples_applied == 4

    small = [
        {"action": "A", "outcome": "Y", "context": "only"},
        {"action": "A", "outcome": "Y", "context": "only"},
        {"action": "B", "outcome": "N", "context": "only"},
    ]
    rescued = conditional_association_test(
        small, action="A", outcome="Y", context_key="context", record_structure="independent"
    )
    assert rescued.historical_supported_strata == 1
    assert rescued.strata[0].min_samples_applied == 4
    assert rescued.strata[0].status == "insufficient_sample"
    assert rescued.supported is False


def test_alpha_enters_the_decision_and_temporal_records_do_not_inherit_it() -> None:
    events = _perfect_split()
    loose = simple_association_test(
        events, action="EAT_LUMEN", outcome="success", record_structure="independent"
    )
    assert loose.p_value == pytest.approx(2 / 70)
    assert loose.effect_observed is True
    assert loose.statistical_support is True
    assert loose.supported is True
    assert loose.p_value_role == "fisher_exact_two_sided"

    strict = simple_association_test(
        events,
        action="EAT_LUMEN",
        outcome="success",
        config=CausalValidationConfig(alpha=0.0001),
        record_structure="independent",
    )
    assert strict.effect_observed is True
    assert strict.statistical_support is False
    assert strict.supported is False
    assert strict.status == "tested"

    temporal = simple_association_test(
        events, action="EAT_LUMEN", outcome="success", record_structure="temporal"
    )
    assert temporal.effect_observed is True
    assert temporal.p_value == pytest.approx(2 / 70)
    assert temporal.p_value_role == "descriptive_fisher_not_used"
    assert temporal.statistical_support is False
    assert temporal.status == "temporal_dependence_not_tested"

    unspecified = simple_association_test(events, action="EAT_LUMEN", outcome="success")
    assert unspecified.statistical_support is False
    assert unspecified.status == "record_structure_unspecified"

    report = validate_causal_graph(
        graph=None,
        events=events,
        action="EAT_LUMEN",
        outcome="success",
        record_structure="independent",
    )
    assert report.decision is CausalClaimDecision.ASSOCIATION_SUPPORTED


def test_bonferroni_keeps_two_marginal_strata_from_becoming_support() -> None:
    one = [{"context": "only", **row} for row in _perfect_split()]
    single = conditional_association_test(
        one, action="EAT_LUMEN", outcome="success", context_key="context", record_structure="independent"
    )
    assert single.n_eligible_strata == 1
    assert single.alpha_adjusted == pytest.approx(0.05)
    assert single.supported_strata == 1
    assert single.statistical_support is True

    two = [{"context": "a", **row} for row in _perfect_split()]
    two += [{"context": "b", **row} for row in _perfect_split()]
    both = conditional_association_test(
        two, action="EAT_LUMEN", outcome="success", context_key="context", record_structure="independent"
    )
    assert both.n_eligible_strata == 2
    assert both.alpha_adjusted == pytest.approx(0.025)
    assert both.supported_strata == 0
    assert both.statistical_support is False
    assert both.status == "not_significant"
    assert all(item.min_samples_applied == 4 for item in both.strata)


def test_causal_intervention_and_ground_truth_upgrade_but_not_true_causality() -> None:
    scenario = InterventionScenario(
        "resource_remove", "resource", "resource_removed", "Lu", "decrease"
    )
    intervention = InterventionRunResult(scenario, control_metric=0.8, intervention_metric=0.2)
    ground_truth = CausalGroundTruthScenario(
        "mini", (("resource_nearby", "eat_success"),), baseline_accuracy=0.0
    )
    accuracy = evaluate_ground_truth_recovery(ground_truth, [("resource_nearby", "eat_success")])
    report = validate_causal_graph(graph=None, intervention=intervention, ground_truth=accuracy)
    assert report.decision is CausalClaimDecision.GROUND_TRUTH_RECOVERY
    assert report.ground_truth is not None and report.ground_truth.supported
    assert all(level.value != "true_causality" for level in report.evidence_levels)
