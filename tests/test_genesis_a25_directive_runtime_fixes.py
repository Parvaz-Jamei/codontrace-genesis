from __future__ import annotations

import math

import pytest

from codontrace.actions import ActionRegistry, ActionResult, ActionRuntimeConfig, EnergyEffect, default_action_registry
from codontrace.energy import ATPAccount
from codontrace.trace import Trace, TraceEvent
from codontrace.world import World2D
from codontrace.codon import Codon, CodonTable
from codontrace.genesis import (
    AliveGateResult,
    EpisodicEvent,
    EpisodicMemory,
    EpisodicMemoryConfig,
    GenesisATPState,
    GenesisEngine,
    GenesisEngineConfig,
    GenesisExperimentSpec,
    GenesisOrganism,
    MutationConfig,
    OffspringPlacementPolicy,
    QDSearchArchive,
    QDSearchCandidate,
    ReproductionConfig,
    reproduce,
    social_events_from_trace,
)
from codontrace.genesis.adf_runtime import ADFExecutionPolicy, ADFMacroDefinition, ADFMacroRegistry
from codontrace.genesis.atp import DualATPBudget
from codontrace.genesis.capsule import CapsuleTransferConfig, CapsuleTransferMetric, CausalCapsule
from codontrace.genesis.death import DeathClassificationRecord
from codontrace.genesis.qd_search import QDDescriptorConfig, QDSearchConfig
from codontrace.genesis.learning import LearningATPConfig, consolidate_memory
from codontrace.genesis.fitness import FitnessBreakdown, FitnessComponent, FitnessComponentValue, SelectionFitnessScore, build_fitness_component_value
from codontrace.genesis.qd_descriptors import DescriptorSpec, DescriptorValue, QDDescriptorRegistry, QDSelectionFeedbackConfig
from codontrace.genesis.quality_diversity import BehaviorBin, BehaviorDescriptorSchema, QDElite
from codontrace.genesis.ribosome import Ribosome
from codontrace.genesis.population import FitnessResult, OrganismStepRecord
from codontrace.genesis.benchmark_suite import BenchmarkScenario, BaselineConfig, AblationConfig
from codontrace.genesis.substrate_runtime import GenesisWorldState, SubstrateActionBridge


def _memory_event(tick: int, digest: str) -> EpisodicEvent:
    return EpisodicEvent(
        tick=tick,
        organism_id="org",
        action="WAIT",
        status="executed",
        position_before=(0, 0),
        position_after=(0, 0),
        atp_runtime_before=1.0,
        atp_runtime_after=1.0,
        atp_learning_before=2.0,
        atp_learning_after=2.0,
        world_digest_before="world",
        trace_event_digest=digest,
        observation={},
        outcome={},
    )


def test_finite_numeric_rejects_nan_and_inf_in_atp_and_action_energy() -> None:
    with pytest.raises(Exception):
        ATPAccount(float("nan"))
    with pytest.raises(Exception):
        ATPAccount(float("inf"))
    with pytest.raises(Exception):
        EnergyEffect(credit=float("nan"))
    with pytest.raises(Exception):
        EnergyEffect(debit_extra=float("inf"))


def test_memory_write_capacity_block_is_truthful_and_does_not_debit_learning_atp() -> None:
    memory = EpisodicMemory(EpisodicMemoryConfig(max_events_per_tick=1))
    state = GenesisATPState.from_runtime(1.0, learning_atp=3.0, learning_enabled=True)
    first = memory.write_event(_memory_event(0, "e0"), state, cost=0.5)
    digest_after_first = memory.digest()
    second = memory.write_event(_memory_event(0, "e1"), state, cost=0.5)

    assert first.written is True
    assert second.written is False
    assert second.blocked_reason == "max_events_per_tick_reached"
    assert second.learning_ledger_entry_id is None
    assert second.memory_digest_before == second.memory_digest_after == digest_after_first
    assert state.learning_available == 2.5
    assert len(memory.events) == 1


def test_memory_from_dict_rejects_capacity_or_tick_truncation() -> None:
    payload = {
        "config": EpisodicMemoryConfig(capacity=1, max_events_per_tick=2).to_dict(),
        "events": [_memory_event(0, "e0").to_dict(), _memory_event(1, "e1").to_dict()],
    }
    with pytest.raises(ValueError, match="capacity"):
        EpisodicMemory.from_dict(payload)

    payload = {
        "config": EpisodicMemoryConfig(capacity=4, max_events_per_tick=1).to_dict(),
        "events": [_memory_event(0, "e0").to_dict(), _memory_event(0, "e1").to_dict()],
    }
    with pytest.raises(ValueError, match="max_events_per_tick"):
        EpisodicMemory.from_dict(payload)


def test_qd_search_rejects_nonfinite_quality_and_descriptors() -> None:
    with pytest.raises(Exception):
        QDSearchCandidate("g", math.nan, {"x": 0.5})
    with pytest.raises(Exception):
        QDSearchCandidate("g", 1.0, {"x": math.inf})

    config = QDDescriptorConfig(
        descriptor_names=("x",),
        min_values={"x": 0.0},
        max_values={"x": 1.0},
        bins_per_descriptor={"x": 4},
    )
    archive, changed = QDSearchArchive().update(QDSearchCandidate("valid", 1.0, {"x": 0.5}), config)
    assert changed is True
    assert next(iter(archive.elites.values())).quality == 1.0


def test_social_events_ignore_environment_missing_and_self_targets() -> None:
    events = [
        TraceEvent(0, "org", "000", "RETURN_HOME", 1.0, 1.0, (0, 0), (0, 0), {"tool_chain_order_correct": False}),
        TraceEvent(1, "org", "000", "WAIT", 1.0, 1.0, (0, 0), (0, 0), {"tool_chain_stage_event": True, "target_organism_id": "environment"}),
        TraceEvent(2, "org", "000", "WAIT", 1.0, 1.0, (0, 0), (0, 0), {"tool_chain_stage_event": True, "target_organism_id": "org"}),
    ]
    assert social_events_from_trace(events, organism_id="org") == ()

    real = TraceEvent(3, "org", "000", "WAIT", 1.0, 1.0, (0, 0), (0, 0), {"tool_chain_stage_event": True, "target_organism_id": "peer"})
    rows = social_events_from_trace([real], organism_id="org")
    assert len(rows) == 1
    assert rows[0].target_organism_id == "peer"


def test_direct_reproduce_adjacent_free_requires_world_context() -> None:
    parent = GenesisOrganism.from_bits("parent", "111", initial_runtime_atp=20.0)
    alive = AliveGateResult(True, 1, 1, 0, 0.0, 20.0, 0, 0, ())
    result = reproduce(
        parent,
        ReproductionConfig(
            min_runtime_atp=1.0,
            parent_atp_cost=1.0,
            offspring_placement=OffspringPlacementPolicy.ADJACENT_FREE,
        ),
        MutationConfig(bit_flip_rate=0.0),
        alive_result=alive,
    )
    assert result.succeeded is False
    assert result.decision.reasons == ("placement_requires_world_context",)
    assert result.child_admission_result is not None
    assert result.child_admission_result.admitted is False


def test_direct_reproduce_adjacent_free_uses_world_context() -> None:
    parent = GenesisOrganism.from_bits("parent", "111", initial_runtime_atp=20.0, position=(0, 0))
    alive = AliveGateResult(True, 1, 1, 0, 0.0, 20.0, 0, 0, ())
    result = reproduce(
        parent,
        ReproductionConfig(
            min_runtime_atp=1.0,
            parent_atp_cost=1.0,
            offspring_placement=OffspringPlacementPolicy.ADJACENT_FREE,
        ),
        MutationConfig(bit_flip_rate=0.0),
        alive_result=alive,
        world=World2D(2, 1),
        live_positions={"parent": (0, 0)},
    )
    assert result.succeeded is True
    assert result.child is not None
    assert result.child.position == (1, 0)
    assert result.child_admission_result is not None
    assert result.child_admission_result.placement_cell == (1, 0)


def test_death_classification_and_genome_digest_survive_step_record_roundtrip() -> None:
    death = DeathClassificationRecord(
        organism_id="org",
        tick=0,
        actual_death_removed_from_population=False,
        removal_reason=None,
        alive_gate_failed=True,
        alive_gate_reasons=("starvation",),
        death_risk_event=True,
        fatal_policy_matched=False,
        fatal_policy_reason=None,
        runtime_atp_before=1.0,
        runtime_atp_after=0.0,
        blocked_actions=0,
        death_policy_digest="policy",
        death_attribution_level="alive_gate_warning",
    )
    alive = AliveGateResult(False, 1, 0, 0, 0.0, 0.0, 0, 0, ("starvation",))
    fitness = FitnessResult("org", 0.0, 1, 0, 0, 0, 0, ("starvation",), death_classification=death)
    record = OrganismStepRecord(
        "org",
        "trace",
        1.0,
        0.0,
        alive,
        fitness,
        None,
        "wb",
        "wa",
        genome_digest="genome-digest",
        death_classification=death,
    )
    payload = record.to_dict()
    assert payload["death_classification_consistency_status"] == "matched"
    restored = OrganismStepRecord.from_dict(payload)
    assert restored.genome_digest == "genome-digest"
    assert restored.death_classification is not None
    assert restored.death_classification.alive_gate_reasons == ("starvation",)


def test_qd_elite_uses_real_genome_digest_from_engine_record() -> None:
    engine = GenesisEngine.from_spec(
        GenesisExperimentSpec(
            genome_bits=("000",),
            tick_count=1,
            engine_config=GenesisEngineConfig(enable_qd=True, qd_mode="archive_only"),
        )
    )
    engine.run_ticks()
    assert engine.qd_archive is not None
    elite = next(iter(engine.qd_archive.elites.values()))
    assert elite.genome_digest not in {"", "unknown"}
    assert elite.metadata.get("provenance_status") == "verified_genome_digest"


def test_action_runtime_config_wires_from_spec_to_organism_and_manifest_digest() -> None:
    runtime_config = ActionRuntimeConfig(open_statuses=True)
    spec = GenesisExperimentSpec(action_runtime_config=runtime_config, tick_count=0)
    payload = spec.to_dict()
    assert payload["action_runtime_config_hash"] is not None
    assert payload["status_registry_digest"] is not None
    engine = GenesisEngine.from_spec(spec)
    organism = engine.runner.population.organisms[0]
    assert organism.action_runtime_config.open_statuses is True


def test_qd_mode_disabled_is_not_silently_converted_to_archive_only() -> None:
    config = GenesisEngineConfig(enable_qd=True, qd_mode="disabled")
    assert config.enable_qd is False
    assert config.qd_mode == "disabled"


def test_learning_consolidation_audit_only_has_no_compression_claim_or_debit() -> None:
    memory = EpisodicMemory(EpisodicMemoryConfig(prediction_error_threshold=0.1))
    state = GenesisATPState.from_runtime(1.0, learning_atp=2.0, learning_enabled=True)
    result = consolidate_memory(
        memory,
        0.5,
        LearningATPConfig(memory_consolidation_cost=0.5),
        state,
        tick=0,
        organism_id="org",
    )
    assert result.succeeded is False
    assert result.mode == "audit_summary_only"
    assert result.state_changed is False
    assert result.ledger_entry_id is None
    assert state.learning_available == 2.0
    assert result.claim_allowed_for_learning_compression is False


def test_substrate_bridge_public_status_is_audit_only_not_claim_eligible() -> None:
    _, audit = SubstrateActionBridge().apply_action(
        GenesisWorldState(world=World2D(2, 2), element_grid=None), "EAT_LUMEN", (0, 0)
    )
    assert audit["feature_status"] == "provisional_audit_only"
    assert audit["evidence_bearing"] is False
    assert audit["claim_allowed"] is False


def test_benchmark_ablation_has_behavior_digest_and_effective_runtime_toggle() -> None:
    scenario = BenchmarkScenario(
        scenario_id="capsule_transfer_world",
        description="capsules on/off fixture",
        baseline_config=BaselineConfig(seed=1, tick_count=1),
        ablation_config=AblationConfig(disabled_components=("capsules",)),
    )
    baseline = scenario.build_spec()
    ablation = scenario.build_spec(ablation=True)
    assert baseline.metadata["scenario_behavior_spec_digest"] != ablation.metadata["scenario_behavior_spec_digest"]
    assert baseline.engine_config.enable_capsules is True
    assert ablation.engine_config.enable_capsules is False
    assert ablation.metadata["ablation_effective"] is True


def test_metadata_only_benchmark_is_not_evidence_bearing() -> None:
    scenario = BenchmarkScenario(
        scenario_id="adf_usefulness_world",
        description="not fully wired in core yet",
        baseline_config=BaselineConfig(seed=1, tick_count=1),
        ablation_config=AblationConfig(disabled_components=("adf",)),
    )
    spec = scenario.build_spec()
    assert spec.metadata["scenario_runtime_status"] in {"measured", "metadata_only_not_evidence_bearing"}
    assert spec.metadata["scenario_evidence_bearing"] is (spec.metadata["scenario_runtime_status"] == "measured")
    assert spec.metadata["claim_allowed"] is (spec.metadata["scenario_runtime_status"] == "measured")


def test_reserved_world_config_features_export_non_claim_status() -> None:
    from codontrace.scenario import ResourceConfig, ObstacleConfig, WorldConfig

    resource = ResourceConfig(density=0.0, distribution="none", respawn=True, respawn_rate=0.2)
    assert resource.to_dict()["respawn_status"] == "reserved_config_only"
    assert resource.to_dict()["respawn_runtime_enabled"] is False
    assert resource.to_dict()["respawn_claim_allowed"] is False

    obstacle = ObstacleConfig(density=0.0, pattern="none", block_sight=True)
    assert obstacle.to_dict()["block_sight_status"] == "reserved_config_only"
    assert obstacle.to_dict()["block_sight_runtime_enabled"] is False
    assert obstacle.to_dict()["line_of_sight_claim_allowed"] is False

    world = WorldConfig(
        width=3,
        height=3,
        resource_respawn=True,
        resource_respawn_rate=0.2,
        beacon_density=0.1,
        beacon_distribution="uniform",
        obstacle_block_sight=True,
    )
    payload = world.to_dict()
    assert payload["resource_respawn_status"] == "reserved_config_only"
    assert payload["obstacle_block_sight_status"] == "reserved_config_only"
    assert payload["beacon_runtime_semantics"] == "extension_only"
    assert payload["beacon_claim_allowed"] is False



def test_second_pass_finite_numeric_closes_config_and_evidence_gaps() -> None:
    with pytest.raises(Exception):
        GenesisATPState.from_runtime(1.0, learning_atp=math.nan, learning_enabled=False)
    with pytest.raises(Exception):
        DualATPBudget(math.nan)
    with pytest.raises(Exception):
        ReproductionConfig(min_runtime_atp=math.nan)
    with pytest.raises(Exception):
        BehaviorDescriptorSchema(
            descriptor_names=("x",),
            bins_per_descriptor={"x": 4},
            min_values={"x": 0.0},
            max_values={"x": math.nan},
        )
    with pytest.raises(Exception):
        QDElite(
            organism_id="org",
            fitness=1.0,
            behavior_descriptor={"x": math.nan},
            behavior_bin=BehaviorBin((0,)),
            genome_digest="genome",
            trace_digest="trace",
            behavior_digest="precomputed-but-invalid",
        )
    with pytest.raises(Exception):
        QDDescriptorConfig(min_values={"action_entropy": math.nan})
    with pytest.raises(Exception):
        QDSearchConfig(novelty_weight=math.inf)
    with pytest.raises(Exception):
        FitnessResult("org", math.nan, 1, 1, 0, 0, 0, ())
    with pytest.raises(Exception):
        FitnessComponent("novelty", math.nan)
    with pytest.raises(Exception):
        FitnessComponentValue("x", raw=math.nan, normalized=0.0, weight=1.0, polarity="reward", weighted=0.0, normalizer="none", status="available")
    with pytest.raises(Exception):
        FitnessBreakdown((), total=math.nan)
    with pytest.raises(Exception):
        SelectionFitnessScore("org", 1.0, math.nan, 0.0, "digest")
    with pytest.raises(Exception):
        build_fitness_component_value("x", raw=math.nan, normalizer="identity")
    with pytest.raises(Exception):
        CapsuleTransferConfig(min_confidence=math.nan)
    with pytest.raises(Exception):
        CausalCapsule("cap", "source", math.nan, "graph", ("a",), "b", 0.5, 0, 1)
    with pytest.raises(Exception):
        CapsuleTransferMetric("cap", "target", None, None, None, None, "g0", "g1", math.nan, 0.5, "unknown")
    with pytest.raises(Exception):
        QDSelectionFeedbackConfig(novelty_weight=math.nan)
    with pytest.raises(Exception):
        DescriptorValue("x", math.nan, "available")
    with pytest.raises(Exception):
        DescriptorSpec("x", "source", math.nan, 1.0, 4)
    registry = QDDescriptorRegistry().register("x", lambda _subject: math.nan)
    with pytest.raises(Exception):
        registry.describe(object(), ("x",))


def test_adf_primitive_ledger_ids_are_per_primitive_not_cumulative() -> None:
    def _credit_one(ctx):
        return ActionResult.executed(
            reason="credit-one",
            position_after=ctx.position,
            world_delta={"primitive": "one"},
            energy=EnergyEffect(credit=1.0, reason="credit_one"),
        )

    def _credit_two(ctx):
        return ActionResult.executed(
            reason="credit-two",
            position_after=ctx.position,
            world_delta={"primitive": "two"},
            energy=EnergyEffect(credit=2.0, reason="credit_two"),
        )

    registry: ActionRegistry = (
        default_action_registry()
        .extend("CREDIT_ONE", _credit_one)
        .extend("CREDIT_TWO", _credit_two)
    )
    table = CodonTable([Codon("000", "ADF_LEDGER", 0.0)])
    macro_registry = ADFMacroRegistry().register(
        ADFMacroDefinition(
            macro_id="ADF_LEDGER",
            primitive_actions=("WAIT", "CREDIT_ONE", "CREDIT_TWO"),
            body_codons=("000", "001", "010"),
        )
    )
    organism = GenesisOrganism.from_bits(
        "org-adf-ledger",
        "000",
        ribosome=Ribosome(table),
        initial_runtime_atp=5.0,
        action_registry=registry,
        adf_macro_registry=macro_registry,
        adf_execution_policy=ADFExecutionPolicy(max_expansion_length=4),
    )

    event = organism.step(World2D(3, 3), Trace())

    assert event.status == "executed"
    assert event.reason == "adf_all_primitives_executed"
    assert event.atp_after == 8.0
    assert event.ledger_entry_ids == (0, 1)
    assert event.world_delta["adf_primitive_1_ledger_entry_ids"] == [0]
    assert event.world_delta["adf_primitive_2_ledger_entry_ids"] == [1]
    statuses = event.world_delta["adf_primitive_statuses"]
    assert statuses[0]["ledger_entry_ids"] == [0]
    assert statuses[1]["ledger_entry_ids"] == [1]
    assert len(set(event.world_delta["adf_primitive_event_digests"])) == 2
