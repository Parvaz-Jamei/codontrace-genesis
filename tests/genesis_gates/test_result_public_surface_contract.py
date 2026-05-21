from codontrace.genesis import GenesisEngine, GenesisExperimentSpec, GenesisEngineConfig


def test_engine_result_public_surface_contract_phase1():
    result = GenesisEngine.from_spec(GenesisExperimentSpec(tick_count=1, engine_config=GenesisEngineConfig(qd_mode="off"))).run_ticks()
    expected = (
        "energy_accounting_records",
        "death_reason_records",
        "action_cost_records",
        "action_reward_records",
        "fitness_breakdown_records",
        "selection_fitness_records",
        "reproduction_attempt_records",
        "reproduction_gate_records",
        "lineage_growth_records",
        "behavior_descriptors",
        "qd_archive_summary",
        "qd_selection_audit",
        "qd_parent_feedback_audit",
        "capsule_adoption_records",
        "capsule_cost_records",
        "capsule_utility_records",
        "capsule_shuffle_records",
        "memory_use_records",
        "delayed_reward_records",
        "social_interaction_records",
        "partner_interaction_records",
        "role_timeline_records",
        "role_contribution_records",
        "tool_chain_records",
        "inventory_records",
        "action_precondition_records",
        "exportable_population_snapshot",
        "exportable_lineage_snapshots",
        "evaluation_protocol_digest",
        "engine_frames",
        "engine_digest_audit",
        "evidence_manifest",
        "action_wiring_matrix",
        "strong_claim_ladder_records",
    )
    for name in expected:
        assert hasattr(result, name), name
    assert result.evidence_manifest.validate_claim_ready_schema() == ()
    assert result.evaluation_protocol_digest


def test_phase1_new_surfaces_are_wired_into_result_payload_and_manifest():
    result = GenesisEngine.from_spec(
        GenesisExperimentSpec(tick_count=1, engine_config=GenesisEngineConfig(qd_mode="off"))
    ).run_ticks()
    payload = result.to_dict()
    assert payload["action_wiring_matrix"]["registered_count"] >= 1
    assert payload["strong_claim_ladder_records"][0]["schema_version"] == "strong_claim_ladder_result_v1"
    manifest = result.evidence_manifest.to_dict()
    assert "action_wiring_matrix" in manifest["artifact_digest_map"]
    assert "strong_claim_ladder_records" in manifest["artifact_digest_map"]
    assert result.export_records("action_wiring_matrix").feature_status == "provisional"
    assert result.export_records("strong_claim_ladder_records").feature_status == "measured"
    assert result.export_records("action_wiring_matrix").status_reason == "contract_only_action_wiring_not_runtime_smoke_validated"


def test_phase1_new_surfaces_preserve_digest_determinism():
    spec = GenesisExperimentSpec(tick_count=1, engine_config=GenesisEngineConfig(qd_mode="off"))
    first = GenesisEngine.from_spec(spec).run_ticks()
    second = GenesisEngine.from_spec(spec).run_ticks()
    assert first.digest() == second.digest()
    assert first.evidence_manifest.digest() == second.evidence_manifest.digest()
    assert first.action_wiring_matrix.digest() == second.action_wiring_matrix.digest()
    assert first.strong_claim_ladder_records[0].digest == second.strong_claim_ladder_records[0].digest
