from codontrace.actions import ActionContext, default_action_registry
from codontrace.genesis import (
    CapsuleAdoptionBlockedReason,
    CausalCapsule,
    EvolutionConfig,
    GenesisEngine,
    GenesisEngineConfig,
    GenesisExperimentSpec,
    SourceFitnessStatus,
)
from codontrace.genesis.capsule import (
    CapsuleAdoptionRecord,
    CapsulePolicyProfile,
    capsule_policy_profile_config,
)
from codontrace.genesis.toolchain import evaluate_tool_chain_state
from codontrace.trace import Trace, TraceEvent
from codontrace.world import World2D


def _event(step: int, action: str) -> TraceEvent:
    return TraceEvent(
        step=step,
        agent_id="agent",
        codon="000",
        action=action,
        status="executed",
        reason="test",
        position_before=(0, 0),
        position_after=(0, 0),
        atp_before=10.0,
        atp_after=9.0,
        world_delta={"tool_chain_action": action},
    )


def test_final_public_result_exports_are_present_and_digestible() -> None:
    spec = GenesisExperimentSpec(
        genome_bits=("101110000", "110101000", "111000111", "000111000"),
        seed=7,
        tick_count=2,
        population_max=2,
        engine_config=GenesisEngineConfig(ticks_per_generation=2, enable_qd=True),
        evolution_config=EvolutionConfig(
            selection_policy="novelty_weighted",
            max_population=2,
            novelty_weight=10.0,
            fitness_weight=0.0,
        ),
    )
    result = GenesisEngine.from_spec(spec).run_ticks()

    assert result.qd_selection_audit
    assert result.qd_parent_feedback_audit
    assert result.qd_archive_summary.digest()
    assert result.selection_fitness_records
    assert result.fitness_breakdown_records
    assert result.role_timeline_records
    assert result.role_contribution_records
    assert result.tool_chain_records
    assert result.engine_frames and all(frame.digest() for frame in result.engine_frames)
    assert result.evidence_manifest.digest()
    # Capsule attempts produce concrete social records, not only aggregate counters.
    assert len(result.social_interaction_records) == len(result.capsule_adoption_records)


def test_toolchain_gates_door_and_water_until_tool_and_key_exist() -> None:
    invalid = Trace()
    invalid.append(_event(0, "OPEN_DOOR"))
    invalid.append(_event(1, "CROSS_WATER"))
    invalid_state = evaluate_tool_chain_state(invalid)
    assert not invalid_state.order_correct
    assert not invalid_state.door_opened
    assert not invalid_state.water_crossed

    valid = Trace()
    for i, action in enumerate(
        (
            "COLLECT_WOOD",
            "COLLECT_STONE",
            "CRAFT_TOOL",
            "COLLECT_KEY",
            "OPEN_DOOR",
            "CROSS_WATER",
            "COLLECT_FOOD",
            "RETURN_HOME",
        )
    ):
        valid.append(_event(i, action))
    valid_state = evaluate_tool_chain_state(valid)
    assert valid_state.order_correct
    assert valid_state.completion == 1.0
    assert valid_state.tool_chain_score > invalid_state.tool_chain_score


def test_unavailable_source_fitness_is_not_interpreted_as_low_zero() -> None:
    capsule = CausalCapsule(
        capsule_id="c",
        source_organism_id="src",
        source_fitness=0.0,
        source_fitness_status=SourceFitnessStatus.UNAVAILABLE,
        source_graph_digest="g",
        event_pattern=("a",),
        predicted_outcome="b",
        confidence=0.8,
        emitted_tick=0,
        ttl=4,
    )
    record = CapsuleAdoptionRecord(
        capsule_id=capsule.capsule_id,
        source_organism_id=capsule.source_organism_id,
        target_organism_id="dst",
        emitted_tick=capsule.emitted_tick,
        read_tick=1,
        adoption_attempt_tick=1,
        adoption_success=False,
        blocked_reason=CapsuleAdoptionBlockedReason.SOURCE_FITNESS_UNAVAILABLE.value,
        source_fitness=capsule.source_fitness,
        source_fitness_status=capsule.source_fitness_status,
        confidence=capsule.confidence,
        runtime_atp_before=5.0,
        learning_atp_before=5.0,
        runtime_atp_after=5.0,
        learning_atp_after=5.0,
    )
    assert record.to_dict()["source_fitness"] == 0.0
    assert record.to_dict()["source_fitness_status"] == "unavailable"
    assert record.blocked_reason == "source_fitness_unavailable"
    assert record.runtime_atp_after == record.runtime_atp_before


def _tool_ctx(action: str, world: World2D) -> ActionContext:
    return ActionContext(
        agent_id="agent",
        position=(0, 0),
        codon_bits="000",
        action_name=action,
        step_index=0,
        world=world,
    )


def test_toolchain_default_handler_blocks_invalid_order_and_mutates_world_state() -> None:
    registry = default_action_registry()
    world = World2D(width=2, height=2)

    blocked = registry.get("OPEN_DOOR")(_tool_ctx("OPEN_DOOR", world))
    assert blocked.status == "blocked"
    assert blocked.world_delta["tool_chain_missing_prerequisites"] == ["CRAFT_TOOL", "COLLECT_KEY"]

    for action in ("COLLECT_WOOD", "COLLECT_STONE", "CRAFT_TOOL", "COLLECT_KEY", "OPEN_DOOR"):
        result = registry.get(action)(_tool_ctx(action, world))
        assert result.status == "executed"
        assert result.world_delta["tool_chain_world_state_changed"] is True

    stages = {
        item.metadata["stage"]
        for objects in world.objects.values()
        for item in objects
        if item.kind == "tool_chain_state"
    }
    assert {"COLLECT_WOOD", "COLLECT_STONE", "CRAFT_TOOL", "COLLECT_KEY", "OPEN_DOOR"} <= stages


def test_moderate_capsule_profile_matches_final_science_protocol_values() -> None:
    cfg = capsule_policy_profile_config(CapsulePolicyProfile.MODERATE)
    assert cfg.min_confidence == 0.45
    assert cfg.adoption_min_confidence == 0.55
    assert cfg.min_source_fitness == 2.0
    assert cfg.max_capsules_per_tick == 4
    assert cfg.max_capsules_read_per_tick == 4
    assert cfg.max_adoptions_per_organism == 2
    assert cfg.min_atp_runtime_to_emit == 5.0
    assert cfg.adoption_cost_learning_atp == 0.4
    assert cfg.emission_cost_runtime_atp == 0.4
    assert cfg.emission_cost_learning_atp == 0.2


def test_final_hardening_symbols_are_public_exports() -> None:
    import codontrace.genesis as genesis

    for name in (
        "ClaimEvidenceRequirement",
        "QDSearchCandidate",
        "QDSearchArchive",
        "QDEmitter",
        "RandomEmitter",
        "MutationEmitter",
        "ArchiveSamplingEmitter",
        "NoveltyBiasedEmitter",
        "QDParentSelection",
        "qd_candidate_from_dict",
        "social_events_from_capsule_records",
        "EliteRecord",
        "DiscoveryCandidateFromQD",
        "QDUpdateResult",
    ):
        assert name in genesis.__all__
        assert hasattr(genesis, name)
