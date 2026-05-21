from codontrace.genesis import CausalGraph, CausalGraphConfig, GenesisATPState
from codontrace.genesis.causal_graph import update_causal_graph_from_trace
from codontrace.genesis.liveness import AliveGateResult
from codontrace.genesis.population import (
    FitnessResult,
    GenerationResult,
    OrganismStepRecord,
    PopulationState,
)
from codontrace.trace import Trace, TraceEvent
from codontrace.world import World2D


def _event(action="WAIT", status="executed", reason="waited"):
    return TraceEvent(
        step=0,
        agent_id="org",
        codon="000",
        action=action,
        atp_before=10.0,
        atp_after=9.9,
        position_before=(0, 0),
        position_after=(0, 0),
        status=status,
        reason=reason,
    )


def test_executed_wait_reason_does_not_create_leads_to_block():
    graph = CausalGraph()
    atp = GenesisATPState.from_runtime(10.0, learning_atp=2.0, learning_enabled=True)
    result = update_causal_graph_from_trace(
        graph, [_event()], atp, CausalGraphConfig(update_cost=0.1), tick=0, organism_id="org"
    )
    assert result.succeeded
    assert not graph.edges_for_relation("leads_to_block")
    assert graph.edges_for_relation("has_outcome_detail")


def test_executed_move_reason_does_not_create_leads_to_block():
    graph = CausalGraph()
    atp = GenesisATPState.from_runtime(10.0, learning_atp=2.0, learning_enabled=True)
    update_causal_graph_from_trace(
        graph,
        [_event(action="MOVE_TOWARD", reason="moved")],
        atp,
        CausalGraphConfig(update_cost=0.1),
        tick=0,
        organism_id="org",
    )
    assert not graph.edges_for_relation("leads_to_block")


def test_blocked_event_creates_leads_to_block():
    graph = CausalGraph()
    atp = GenesisATPState.from_runtime(10.0, learning_atp=2.0, learning_enabled=True)
    update_causal_graph_from_trace(
        graph,
        [_event(status="blocked", reason="wall_blocked")],
        atp,
        CausalGraphConfig(update_cost=0.1),
        tick=0,
        organism_id="org",
    )
    assert graph.edges_for_relation("leads_to_block")


def test_causal_graph_limit_audit_is_not_silent():
    graph = CausalGraph(CausalGraphConfig(max_nodes=1, max_edges=1, update_cost=0.1))
    atp = GenesisATPState.from_runtime(10.0, learning_atp=2.0, learning_enabled=True)
    result = graph.update_from_trace([_event()], atp, tick=0, organism_id="org")
    assert result.truncated or not result.succeeded
    assert result.dropped_nodes > 0 or result.blocked_reason == "graph_limits_reached"


def test_organism_step_record_roundtrip_preserves_causal_graph_fields():
    alive = AliveGateResult(
        passed=True,
        survived_ticks=1,
        executed_actions=1,
        blocked_actions=0,
        blocked_ratio=0.0,
        final_runtime_atp=1.0,
        lumen_interactions=0,
        reproduction_events=0,
        reasons=(),
    )
    fitness = FitnessResult("org", 1.0, 1, 0, 0, 0, 0, ())
    record = OrganismStepRecord(
        organism_id="org",
        trace_digest="trace",
        runtime_atp_before=2.0,
        runtime_atp_after=1.0,
        alive_result=alive,
        fitness_result=fitness,
        reproduction_result=None,
        world_before_digest="wb",
        world_after_digest="wa",
        causal_graph_digest_before="gb",
        causal_graph_digest_after="ga",
        causal_graph_update_attempts=1,
        causal_graph_update_successes=1,
        causal_graph_update_blocked_reason=None,
    )
    restored = OrganismStepRecord.from_dict(record.to_dict())
    assert restored.causal_graph_digest_before == "gb"
    assert restored.causal_graph_digest_after == "ga"
    assert restored.causal_graph_update_attempts == 1
    assert restored.causal_graph_update_successes == 1


def test_generation_result_roundtrip_preserves_organism_records_causal_fields():
    alive = AliveGateResult(True, 1, 1, 0, 0.0, 1.0, 0, 0, ())
    fitness = FitnessResult("org", 1.0, 1, 0, 0, 0, 0, ())
    record = OrganismStepRecord(
        "org", "td", 1.0, 1.0, alive, fitness, None, "wb", "wa", causal_graph_digest_after="ga"
    )
    population = PopulationState(generation=0, tick=0, organisms=(), lineage=(), fitness=())
    world = World2D(width=2, height=2)
    result = GenerationResult(
        before_count=0,
        after_count=0,
        births=0,
        deaths=0,
        reproduction_attempts=0,
        blocked_reproduction=0,
        mean_fitness=0.0,
        best_fitness=0.0,
        population=population,
        world_after=world,
        world_before_digest="wb",
        world_after_digest="wa",
        traces=(Trace(),),
        organism_records=(record,),
    )
    restored = GenerationResult.from_dict(result.to_dict())
    assert restored.organism_records[0].causal_graph_digest_after == "ga"


def test_reserved_causal_graph_fields_are_stable_noops():
    e = _event()
    atp_a = GenesisATPState.from_runtime(10.0, learning_atp=2.0, learning_enabled=True)
    atp_b = GenesisATPState.from_runtime(10.0, learning_atp=2.0, learning_enabled=True)
    graph_a = CausalGraph()
    graph_b = CausalGraph()
    graph_a.update_from_trace(
        [e], atp_a, CausalGraphConfig(update_cost=0.1), tick=0, organism_id="org"
    )
    graph_b.update_from_trace(
        [e],
        atp_b,
        CausalGraphConfig(update_cost=0.1, decay=0.9, allow_negative_evidence=True),
        tick=0,
        organism_id="org",
    )
    assert graph_a.digest() == graph_b.digest()
