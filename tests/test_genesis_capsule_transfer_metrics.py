from codontrace.genesis import CapsuleTransferMetric, estimate_capsule_transfer_effect


def test_transfer_metric_measurement_and_insufficient_evidence():
    metric = estimate_capsule_transfer_effect(source_capsule_id="cap", target_organism_id="org")
    assert metric.interpretation == "insufficient_evidence"
    assert CapsuleTransferMetric.from_dict(metric.to_dict()).digest() == metric.digest()
    measured = estimate_capsule_transfer_effect(
        source_capsule_id="cap",
        target_organism_id="org",
        pre_adoption_fitness=1.0,
        post_adoption_fitness=2.5,
    )
    assert measured.effect_score == 1.5
    assert measured.interpretation == "measured_delta_not_causal_proof"
