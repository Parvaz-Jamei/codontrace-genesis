from codontrace.actions import ActionContext, default_action_registry
from codontrace.genesis.campaign import EvolutionCampaign, EvolutionCampaignConfig
from codontrace.genesis.capsule import (
    CapsuleAdoptionBlockedReason,
    CapsuleTransferConfig,
    CausalCapsule,
    CausalCapsuleAdoptionPolicy,
    SourceFitnessStatus,
)
from codontrace.genesis.causal_graph import CausalGraph, CausalGraphConfig
from codontrace.genesis.engine import GenesisEngine, GenesisEngineConfig, GenesisExperimentSpec
from codontrace.genesis.organism import GenesisOrganism
from codontrace.genesis.selection import EvolutionConfig, QDFallbackReason
from codontrace.world import World2D, WorldObject


def test_qd_mode_selection_pressure_auto_uses_novelty_policy() -> None:
    spec = GenesisExperimentSpec(
        genome_bits=("101110000", "110101000", "111000111", "000111000"),
        seed=11,
        tick_count=1,
        population_max=2,
        engine_config=GenesisEngineConfig(enable_qd=True, qd_mode="selection_pressure"),
        evolution_config=EvolutionConfig(max_population=2),
    )
    result = GenesisEngine.from_spec(spec).run_ticks()

    assert result.qd_selection_audit
    first = result.qd_selection_audit[0]
    assert first.policy_name == "novelty_weighted"
    assert first.qd_mode == "selection_pressure"
    assert first.fallback_reason in {item.value for item in QDFallbackReason}
    assert result.qd_archive_summary.mode == "selection_pressure"


def test_capsule_unavailable_source_fitness_is_not_threshold_zero() -> None:
    capsule = CausalCapsule(
        capsule_id="c",
        source_organism_id="source",
        source_fitness=0.0,
        source_fitness_status=SourceFitnessStatus.UNAVAILABLE,
        source_graph_digest="g",
        event_pattern=("a",),
        predicted_outcome="outcome",
        confidence=1.0,
        emitted_tick=0,
        ttl=5,
    )
    target = GenesisOrganism.from_bits(
        "target",
        "000",
        causal_graph=CausalGraph(CausalGraphConfig(update_cost=0.0)),
        initial_runtime_atp=10.0,
        initial_learning_atp=10.0,
    )

    result = CausalCapsuleAdoptionPolicy().apply(
        target,
        capsule,
        target.causal_graph,  # type: ignore[arg-type]
        target.episodic_memory,
        target.atp_state,
        CapsuleTransferConfig(enabled=True, min_source_fitness=2.0, adoption_min_confidence=0.0),
        tick=1,
    )

    assert capsule.source_fitness_numeric_for_threshold is None
    assert result.blocked_reason == CapsuleAdoptionBlockedReason.SOURCE_FITNESS_UNAVAILABLE.value


def test_tool_chain_actions_mutate_world_objects_and_block_bad_order() -> None:
    registry = default_action_registry()
    world = World2D(3, 3)
    world.add_object((1, 1), WorldObject(kind="wood"))
    collect = registry.get("COLLECT_WOOD")
    open_door = registry.get("OPEN_DOOR")
    assert collect is not None and open_door is not None

    collect_result = collect(
        ActionContext(
            agent_id="a",
            position=(1, 1),
            codon_bits="111",
            action_name="COLLECT_WOOD",
            step_index=0,
            world=world,
        )
    )
    assert collect_result.status == "executed"
    assert not any(item.kind == "wood" for item in world.objects_at((1, 1)))
    assert any(item.kind == "tool_chain_inventory" for item in world.objects_at((1, 1)))

    blocked = open_door(
        ActionContext(
            agent_id="a",
            position=(1, 1),
            codon_bits="111",
            action_name="OPEN_DOOR",
            step_index=1,
            world=world,
        )
    )
    assert blocked.status == "blocked"
    assert blocked.world_delta is not None
    assert blocked.world_delta["tool_chain_order_correct"] is False


def test_engine_frame_exports_exact_position_and_action() -> None:
    result = GenesisEngine.from_spec(
        GenesisExperimentSpec(
            genome_bits=("101110000",),
            seed=12,
            tick_count=1,
            engine_config=GenesisEngineConfig(ticks_per_generation=1),
        )
    ).run_ticks()

    frame = result.engine_frames[0]
    assert frame.agents
    assert frame.agents[0].position is not None
    assert frame.agents[0].action
    assert "engine_frames" in result.evidence_manifest.to_dict()["artifact_digest_map"]


def test_campaign_core_methods_produce_result_surfaces_without_leakage() -> None:
    train = GenesisEngine.from_spec(
        GenesisExperimentSpec(genome_bits=("101110000", "110101000"), seed=21, tick_count=1)
    ).run_ticks()
    heldout = GenesisEngine.from_spec(
        GenesisExperimentSpec(genome_bits=("101110000", "110101000"), seed=22, tick_count=1)
    ).run_ticks()

    campaign = (
        EvolutionCampaign(EvolutionCampaignConfig(seed=21))
        .run_train(train)
        .select_elites(train)
        .replay_elites()
        .evaluate_heldout(heldout)
        .evaluate_cross_partner(heldout)
    )

    assert campaign.result.elite_lineages
    assert campaign.result.heldout_results[0].leakage_guard_passed
    assert campaign.result.cross_partner_results[0].partner_mode == "unfamiliar_partner"
    assert campaign.result.campaign_manifest["train_digest"] == train.digest()  # type: ignore[index]
