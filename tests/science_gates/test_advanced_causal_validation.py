from codontrace.genesis.causal_validation import (
    CausalClaimDecision,
    CausalGroundTruthScenario,
    InterventionRunResult,
    InterventionScenario,
    conditional_association_test,
    evaluate_ground_truth_recovery,
    simple_association_test,
    temporal_precedence_audit,
    validate_causal_graph,
)


def test_causal_temporal_precedence_is_not_causal_claim() -> None:
    report = temporal_precedence_audit(graph=None)
    assert report.decision is CausalClaimDecision.EVIDENCE_LOG_ONLY
    assert "temporal_precedence_is_not_causal_inference" in report.limitations


def test_causal_association_and_conditional_context() -> None:
    events = [
        {"action": "EAT_LUMEN", "outcome": "success", "resource_nearby": True},
        {"action": "EAT_LUMEN", "outcome": "success", "resource_nearby": True},
        {"action": "WAIT", "outcome": "blocked", "resource_nearby": True},
        {"action": "WAIT", "outcome": "blocked", "resource_nearby": False},
        {"action": "MOVE", "outcome": "blocked", "resource_nearby": False},
    ]
    association = simple_association_test(events, action="EAT_LUMEN", outcome="success")
    conditional = conditional_association_test(
        events, action="EAT_LUMEN", outcome="success", context_key="resource_nearby"
    )
    assert association.supported
    assert association.effect_size > 0
    assert conditional.supported
    assert conditional.supported_strata >= 1


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
