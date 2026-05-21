from codontrace.genesis.intervention import (
    CausalGroundTruthScenario,
    InterventionProtocol,
    InterventionScenario,
)


def test_causal_intervention_accuracy_and_downgrade():
    scenario = InterventionScenario(
        "resource_move", "move resource", "EAT_LUMEN_changes", "move_resource", "Lu"
    )
    gt = CausalGroundTruthScenario(scenario, "success", "blocked")
    protocol = InterventionProtocol((gt,), min_accuracy_delta=0.1)

    report = protocol.evaluate_predictions({"resource_move": "blocked"}, baseline_accuracy=0.0)
    assert report.accuracy == 1.0
    assert report.claim_status == "causal_prediction_supported"

    failed = protocol.evaluate_predictions({"resource_move": "success"}, baseline_accuracy=0.0)
    assert failed.claim_status == "causal_claim_downgraded"
