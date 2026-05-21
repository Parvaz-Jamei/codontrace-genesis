"""Pure diversity and reproducibility metrics for CodonTrace objects."""

from __future__ import annotations

import math
from collections import Counter
from collections.abc import Sequence
from typing import TYPE_CHECKING

from codontrace._types import JsonValue, Position
from codontrace.agent import WhiteBoxAgent
from codontrace.genome import SemanticGenome
from codontrace.trace import Trace
from codontrace.world import World2D

if TYPE_CHECKING:
    from codontrace.scenario import Scenario

GenomeMetricInput = SemanticGenome | WhiteBoxAgent


def unique_genome_count(items: Sequence[GenomeMetricInput]) -> int:
    """Return the number of unique compact genomes.

    The public metrics contract accepts ``SemanticGenome`` objects directly.
    ``WhiteBoxAgent`` objects are also accepted as a convenience because they
    carry a ``genome`` attribute.
    """

    return len({_compact_genome(item) for item in items})


def mean_genome_distance(items: Sequence[GenomeMetricInput]) -> float:
    """Return mean normalized Hamming distance across compact genomes."""

    genomes = [_compact_genome(item) for item in items]
    if len(genomes) < 2:
        return 0.0
    total = 0.0
    pairs = 0
    for i, left in enumerate(genomes):
        for right in genomes[i + 1 :]:
            width = max(len(left), len(right))
            padded_left = left.ljust(width, "-")
            padded_right = right.ljust(width, "-")
            total += sum(a != b for a, b in zip(padded_left, padded_right, strict=True)) / width
            pairs += 1
    return total / pairs


def codon_usage_entropy(items: Sequence[GenomeMetricInput]) -> float:
    """Return Shannon entropy of codon usage across genomes."""

    counts: Counter[str] = Counter()
    for item in items:
        counts.update(_codons(item))
    return _entropy(counts)


def genome_length_distribution(items: Sequence[GenomeMetricInput]) -> dict[str, JsonValue]:
    """Return compact genome length distribution."""

    counts = Counter(str(len(_codons(item))) for item in items)
    return dict(sorted(counts.items()))


def behavior_signature_distribution(traces: Sequence[Trace]) -> dict[str, JsonValue]:
    """Return deterministic counts of compact trace behavior signatures.

    The signature intentionally stays simple and JSON-friendly: action counts,
    status counts, and movement/reason counts derived from ``world_delta`` and
    event metadata. It is a distribution over traces, not a mutation of traces.
    """

    counts: Counter[str] = Counter(_behavior_signature(trace) for trace in traces)
    return dict(sorted(counts.items()))


def lineage_depth_distribution(agents: Sequence[WhiteBoxAgent]) -> dict[str, JsonValue]:
    """Return generation/lineage depth distribution."""

    counts = Counter(str(agent.generation) for agent in agents)
    return dict(sorted(counts.items()))


def profile_distribution(agents: Sequence[WhiteBoxAgent]) -> dict[str, JsonValue]:
    """Return agent profile counts."""

    counts = Counter(agent.profile or "default" for agent in agents)
    return dict(sorted(counts.items()))


def atp_distribution(agents: Sequence[WhiteBoxAgent]) -> dict[str, JsonValue]:
    """Return basic ATP summary statistics."""

    values = [agent.atp_account.current_atp for agent in agents]
    if not values:
        return {"count": 0, "min": 0.0, "max": 0.0, "mean": 0.0}
    return {
        "count": len(values),
        "min": min(values),
        "max": max(values),
        "mean": sum(values) / len(values),
    }


def action_entropy(trace: Trace) -> float:
    """Return Shannon entropy of agent action names in a trace."""

    return _entropy(Counter(event.action for event in trace.events))


def wall_density_actual(world: World2D) -> float:
    """Return actual wall density in the world."""

    return len(world.walls) / _area(world)


def resource_density_actual(world: World2D) -> float:
    """Return actual resource-cell density in the world."""

    return len(world.resources) / _area(world)


def object_type_distribution(world: World2D) -> dict[str, JsonValue]:
    """Return counts for WorldObject kinds."""

    counts: Counter[str] = Counter()
    for objects in world.objects.values():
        counts.update(obj.kind for obj in objects)
    return dict(sorted(counts.items()))


def traversable_ratio(world: World2D) -> float:
    """Return the non-wall ratio of the world."""

    return (_area(world) - len(world.walls)) / _area(world)


def resource_clustering_score(world: World2D) -> float:
    """Return a simple resource adjacency score in [0, 1]."""

    return _clustering_score(tuple(world.resources))


def hazard_clustering_score(world: World2D) -> float:
    """Return a simple hazard-object adjacency score in [0, 1]."""

    hazards = tuple(
        position
        for position, objects in world.objects.items()
        if any(obj.kind == "hazard" for obj in objects)
    )
    return _clustering_score(hazards)


def scenario_summary(scenario: Scenario) -> dict[str, JsonValue]:
    """Return a deterministic summary for a generated scenario."""

    return {
        "config_hash": scenario.config_hash,
        "initial_world_digest": scenario.initial_world_digest,
        "initial_agent_digest": scenario.initial_agent_digest,
        "agent_count": len(scenario.agents),
        "world_width": scenario.world.width,
        "world_height": scenario.world.height,
        "wall_density_actual": wall_density_actual(scenario.world),
        "resource_density_actual": resource_density_actual(scenario.world),
        "traversable_ratio": traversable_ratio(scenario.world),
        "profile_distribution": profile_distribution(scenario.agents),
        "unique_genome_count": unique_genome_count(scenario.agents),
    }


def scenario_reproducibility_metadata(scenario: Scenario) -> dict[str, JsonValue]:
    """Return one-scenario reproducibility metadata."""

    return {
        "config_hash": scenario.config_hash,
        "seed": scenario.config.seed,
        "world_seed": scenario.config.world.seed,
        "initial_world_digest": scenario.initial_world_digest,
        "initial_agent_digest": scenario.initial_agent_digest,
        "config_roundtrip_hash": scenario.config.from_json(scenario.config.to_json()).config_hash,
    }


def reproducibility_report(
    scenario_a: Scenario,
    scenario_b: Scenario,
) -> dict[str, JsonValue]:
    """Compare two scenarios and report deterministic reproducibility matches."""

    fields = (
        "config_hash",
        "initial_world_digest",
        "initial_agent_digest",
    )
    left = scenario_reproducibility_metadata(scenario_a)
    right = scenario_reproducibility_metadata(scenario_b)
    mismatches = [field for field in fields if left[field] != right[field]]
    mismatches_json: list[JsonValue] = [field for field in mismatches]
    return {
        "match": not mismatches,
        "mismatches": mismatches_json,
        "left": {field: left[field] for field in fields},
        "right": {field: right[field] for field in fields},
    }


def diversity_report(scenario: Scenario, trace: Trace | None = None) -> dict[str, JsonValue]:
    """Return a combined pure diversity report for worlds, agents, and traces."""

    data = scenario_summary(scenario)
    data.update(
        {
            "mean_genome_distance": mean_genome_distance(scenario.agents),
            "codon_usage_entropy": codon_usage_entropy(scenario.agents),
            "genome_length_distribution": genome_length_distribution(scenario.agents),
            "lineage_depth_distribution": lineage_depth_distribution(scenario.agents),
            "atp_distribution": atp_distribution(scenario.agents),
            "object_type_distribution": object_type_distribution(scenario.world),
            "resource_clustering_score": resource_clustering_score(scenario.world),
            "hazard_clustering_score": hazard_clustering_score(scenario.world),
        }
    )
    if trace is not None:
        data["action_entropy"] = action_entropy(trace)
        data["agent_event_count"] = len(trace.events)
        data["world_event_count"] = len(trace.world_events)
        data["behavior_signature_distribution"] = behavior_signature_distribution([trace])
    return data


def _compact_genome(item: GenomeMetricInput) -> str:
    if isinstance(item, SemanticGenome):
        return item.to_compact()
    return item.genome.to_compact()


def _codons(item: GenomeMetricInput) -> tuple[str, ...]:
    if isinstance(item, SemanticGenome):
        return item.to_codons()
    return item.genome.to_codons()


def _behavior_signature(trace: Trace) -> str:
    actions: Counter[str] = Counter(event.action for event in trace.events)
    statuses: Counter[str] = Counter(event.status for event in trace.events)
    movements: Counter[str] = Counter()
    for event in trace.events:
        reason = event.world_delta.get("move_reason", event.reason or "unknown")
        if not isinstance(reason, str):
            reason = "unknown"
        movement = "moved" if event.position_before != event.position_after else "stationary"
        movements[f"{movement}:{reason}"] += 1
    return "|".join(
        (
            f"actions={_counter_token(actions)}",
            f"statuses={_counter_token(statuses)}",
            f"movement={_counter_token(movements)}",
        )
    )


def _counter_token(counts: Counter[str]) -> str:
    return ",".join(f"{key}:{value}" for key, value in sorted(counts.items())) or "none"


def _entropy(counts: Counter[str]) -> float:
    total = sum(counts.values())
    if total == 0:
        return 0.0
    return -sum((count / total) * math.log2(count / total) for count in counts.values())


def _area(world: World2D) -> float:
    return float(world.width * world.height)


def _clustering_score(positions: Sequence[Position]) -> float:
    if len(positions) < 2:
        return 0.0
    pos_set = set(positions)
    neighboring = 0
    for x, y in pos_set:
        if any((x + dx, y + dy) in pos_set for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))):
            neighboring += 1
    return neighboring / len(pos_set)
