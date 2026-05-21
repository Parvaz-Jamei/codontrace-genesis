from codontrace.genesis.engine import GenesisEngine, GenesisExperimentSpec


def test_selection_fitness_records_are_one_per_available_organism_record() -> None:
    result = GenesisEngine.from_spec(
        GenesisExperimentSpec(genome_bits=("111", "101110000"), seed=11, tick_count=2)
    ).run_ticks()
    expected = sum(
        1
        for tick in result.ticks
        for record in tick.generation_result.organism_records
        if (record.selection_fitness_score or record.fitness_result.selection_fitness_score)
        is not None
    )
    assert len(result.selection_fitness_records) == expected


def test_evidence_manifest_covers_library_as_tool_public_surfaces() -> None:
    result = GenesisEngine.from_spec(
        GenesisExperimentSpec(genome_bits=("111", "101110000"), seed=12, tick_count=2)
    ).run_ticks()
    required = {
        "behavior_descriptors",
        "qd_selection_audit",
        "qd_parent_feedback_audit",
        "qd_archive_summary",
        "capsule_adoption_records",
        "capsule_source_fitness_records",
        "capsule_shuffle_records",
        "fitness_breakdown_records",
        "selection_fitness_records",
        "memory_use_records",
        "delayed_reward_records",
        "social_interaction_records",
        "partner_interaction_records",
        "role_timeline_records",
        "role_contribution_records",
        "tool_chain_records",
        "generalization_records",
        "engine_frames",
        "energy_accounting_records",
        "death_reason_records",
        "action_cost_records",
        "action_reward_records",
        "survival_baseline_records",
        "baseline_comparison_records",
        "reproduction_attempt_records",
        "reproduction_gate_records",
        "lineage_growth_records",
        "capsule_cost_records",
        "capsule_utility_records",
        "post_capsule_behavior_records",
        "inventory_records",
        "action_precondition_records",
        "export_status_records",
        "output_completeness_records",
        "exportable_population_snapshot",
        "exportable_lineage_snapshots",
        "evaluation_protocol_digest",
        "engine_digest_audit",
        "digest_instability_reasons",
    }
    assert required <= set(result.evidence_manifest.artifact_digest_map)


def test_export_status_records_cover_library_as_tool_public_surfaces() -> None:
    result = GenesisEngine.from_spec(
        GenesisExperimentSpec(genome_bits=("111",), seed=13, tick_count=1)
    ).run_ticks()
    exported = {
        item.schema_version.removesuffix("_export_v1") for item in result.export_status_records
    }
    assert "behavior_descriptors" in exported
    assert "qd_archive_summary" in exported
    assert "memory_use_records" in exported
    assert "exportable_population_snapshot" in exported
    assert "evaluation_protocol_digest" in exported
    assert all(
        item.feature_status in {"measured", "empty_but_available", "provisional"}
        for item in result.export_status_records
    )
