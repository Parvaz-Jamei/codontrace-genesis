from codontrace.genesis import evaluate_strong_claim_ladder


def test_claim_ladder_downgrades_to_current_evidence_without_rejecting_ambition():
    result = evaluate_strong_claim_ladder(
        "digital_evolution_claim",
        {"schema_version": True, "artifact_digest": True, "runtime_records": True},
    )
    assert result.achieved_level == "instrumented_runtime"
    assert result.target_level == "claim_ready_research_alpha"
    assert "multi_seed_protocol" in result.missing_for_target
    assert result.digest == evaluate_strong_claim_ladder(
        "digital_evolution_claim",
        {"runtime_records": True, "artifact_digest": True, "schema_version": True},
    ).digest


def test_claim_ladder_reaches_research_alpha_when_all_required_evidence_exists():
    flags = {
        "schema_version": True,
        "artifact_digest": True,
        "runtime_records": True,
        "pilot_run": True,
        "negative_control": True,
        "control_digest": True,
        "ablation_result": True,
        "ablation_digest": True,
        "multi_seed_protocol": True,
        "effect_size": True,
        "confidence_interval": True,
        "heldout_protocol": True,
        "leakage_check": True,
        "partner_or_world_shift": True,
        "intervention_result": True,
        "treatment_digest": True,
        "baseline_digest": True,
        "replay_verification": True,
        "claim_gate_decision_digest": True,
    }
    result = evaluate_strong_claim_ladder("open_ended_claim", flags)
    assert result.achieved_level == "claim_ready_research_alpha"
    assert result.missing_for_target == ()


def test_claim_ladder_cannot_skip_lower_levels():
    result = evaluate_strong_claim_ladder(
        "causal_intervention_claim",
        {
            "intervention_result": True,
            "treatment_digest": True,
            "baseline_digest": True,
        },
    )
    assert result.achieved_level == "metadata_only"
    assert "schema_version" in result.missing_for_target
    assert "runtime_records" in result.missing_for_target


def test_claim_ladder_requires_pilot_before_control_supported():
    result = evaluate_strong_claim_ladder(
        "digital_evolution_claim",
        {
            "schema_version": True,
            "artifact_digest": True,
            "runtime_records": True,
            "negative_control": True,
            "control_digest": True,
        },
    )
    assert result.achieved_level == "instrumented_runtime"
    assert "pilot_run" in result.missing_for_target
