from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from codontrace import (
    ScenarioAgentProfile,
    ScenarioConfig,
    ScenarioFactory,
    SemanticGenome,
    Trace,
    TraceEvent,
    World2D,
    WorldConfig,
)
from codontrace.metrics.diversity import (
    behavior_signature_distribution,
    codon_usage_entropy,
    genome_length_distribution,
    mean_genome_distance,
    reproducibility_report,
    scenario_reproducibility_metadata,
    unique_genome_count,
)


def test_genome_metrics_accept_semantic_genomes_directly() -> None:
    genomes = [
        SemanticGenome.from_codons(("000", "111")),
        SemanticGenome.from_codons(("000", "111")),
        SemanticGenome.from_codons(("101", "111", "000")),
    ]

    assert unique_genome_count(genomes) == 2
    assert mean_genome_distance(genomes) > 0.0
    assert codon_usage_entropy(genomes) > 0.0
    assert genome_length_distribution(genomes) == {"2": 2, "3": 1}


def test_behavior_signature_distribution_counts_trace_shapes() -> None:
    trace_a = Trace()
    trace_a.append(
        TraceEvent(
            step=0,
            agent_id="a",
            codon="000",
            action="WAIT",
            atp_before=1.0,
            atp_after=0.9,
            position_before=(0, 0),
            position_after=(0, 0),
            status="executed",
            reason="waited",
        )
    )
    trace_b = Trace.from_jsonl(trace_a.to_jsonl())

    distribution = behavior_signature_distribution([trace_a, trace_b])

    assert sum(int(value) for value in distribution.values()) == 2
    assert len(distribution) == 1


def test_reproducibility_report_compares_two_scenarios() -> None:
    config = ScenarioConfig(
        seed=41,
        world=WorldConfig(width=8, height=8, seed=41),
        agents=(ScenarioAgentProfile(name="agent", count=2),),
    )
    left = ScenarioFactory.from_config(config)
    right = ScenarioFactory.from_config(ScenarioConfig.from_json(config.to_json()))
    changed = ScenarioFactory.from_config(
        ScenarioConfig(seed=42, world=WorldConfig(width=8, height=8, seed=42))
    )

    report = reproducibility_report(left, right)
    mismatch = reproducibility_report(left, changed)

    assert report["match"] is True
    assert report["mismatches"] == []
    assert scenario_reproducibility_metadata(left)["config_hash"] == config.config_hash
    assert mismatch["match"] is False
    assert "config_hash" in mismatch["mismatches"]


def test_scenario_run_propagates_config_hash_into_trace_events() -> None:
    config = ScenarioConfig(
        seed=51,
        max_steps=3,
        world=WorldConfig(width=8, height=8, seed=51),
        agents=(ScenarioAgentProfile(name="runner", count=1, genome_length_range=(1, 1)),),
    )

    result = ScenarioFactory.run(config)

    assert result.config_hash == config.config_hash
    assert result.trace.events
    assert {event.config_hash for event in result.trace.events} == {config.config_hash}


def test_scenario_trace_enabled_false_returns_empty_trace() -> None:
    config = ScenarioConfig(
        seed=52,
        max_steps=3,
        trace_enabled=False,
        replay_enabled=False,
        metadata={"purpose": "no-trace-smoke"},
        world=WorldConfig(width=8, height=8, seed=52),
        agents=(ScenarioAgentProfile(name="runner", count=1, genome_length_range=(1, 1)),),
    )

    result = ScenarioFactory.run(config)
    bundle = result.to_viewer_bundle()

    assert len(result.trace.events) == 0
    assert bundle["scenario"]["trace_enabled"] is False
    assert bundle["scenario"]["replay_enabled"] is False


def test_boundary_wrap_has_runtime_movement_semantics() -> None:
    world = World2D(3, 3, boundary="wrap")

    east, east_reason = world.move_agent((2, 1), (1, 0))
    west, west_reason = world.move_agent((0, 1), (-1, 0))
    north, north_reason = world.move_agent((1, 0), (0, -1))
    south, south_reason = world.move_agent((1, 2), (0, 1))

    assert (east, east_reason) == ((0, 1), "moved")
    assert (west, west_reason) == ((2, 1), "moved")
    assert (north, north_reason) == ((1, 2), "moved")
    assert (south, south_reason) == ((1, 0), "moved")


def test_world_event_timeline_example_runs_without_mismatch_language() -> None:
    example = Path("examples/world_event_timeline.py")
    result = subprocess.run(
        [sys.executable, str(example)],
        check=True,
        capture_output=True,
        text=True,
    )
    output = result.stdout

    assert "world-event-replay-match True" in output
    assert "replayed_world_digest" not in output
    assert "final_world_digest_after_agent_actions" in output
