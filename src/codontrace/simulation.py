"""Deterministic multi-agent simulation runner."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import ClassVar, Literal

from codontrace._types import JsonValue, Position
from codontrace.agent import WhiteBoxAgent
from codontrace.errors import ConfigurationError, ReplayError
from codontrace.rng import RNGManager
from codontrace.scheduling import SchedulerProtocol, scheduler_from_name
from codontrace.trace import Trace
from codontrace.world import World2D

SchedulerName = Literal[
    "sequential", "round_robin", "random_order", "energy_priority", "fitness_weighted"
]
CollisionPolicy = Literal["block", "allow_overlap"]
TraceMode = Literal["combined"]


@dataclass(frozen=True, slots=True)
class SimulationConfig:
    """Configuration for deterministic multi-agent runs."""

    steps: int
    scheduler: SchedulerName | SchedulerProtocol = "sequential"
    collision_policy: CollisionPolicy = "block"
    trace_mode: TraceMode = "combined"
    seed: int | None = None
    allow_agent_on_wall: bool = False

    def __post_init__(self) -> None:
        if self.steps < 0:
            msg = "SimulationConfig.steps cannot be negative."
            raise ConfigurationError(msg)
        if isinstance(self.scheduler, str):
            if self.scheduler not in {
                "sequential",
                "round_robin",
                "random_order",
                "energy_priority",
                "fitness_weighted",
            }:
                msg = f"Unsupported scheduler {self.scheduler!r}."
                raise ConfigurationError(msg)
        elif not hasattr(self.scheduler, "order"):
            msg = "SimulationConfig.scheduler must be a preset name or SchedulerProtocol object."
            raise ConfigurationError(msg)
        if self.collision_policy not in {"block", "allow_overlap"}:
            msg = f"Unsupported collision_policy {self.collision_policy!r}."
            raise ConfigurationError(msg)
        if self.trace_mode != "combined":
            msg = "Only trace_mode='combined' is supported by the current simulation contract."
            raise ConfigurationError(msg)
        if not isinstance(self.allow_agent_on_wall, bool):
            msg = "SimulationConfig.allow_agent_on_wall must be a bool."
            raise ConfigurationError(msg)


@dataclass(frozen=True, slots=True)
class SimulationResult:
    """Result of a multi-agent simulation.

    This is a library object. It intentionally provides object/dict conversion
    only and performs no file I/O.
    """

    __hash__: ClassVar[None] = None  # type: ignore[assignment]

    trace: Trace
    final_world: World2D
    agent_states: tuple[dict[str, JsonValue], ...]
    world_digest: str
    trace_digest: str

    def to_dict(self) -> dict[str, JsonValue]:
        """Return a JSON-friendly result dictionary."""

        trace_items: list[JsonValue] = [item for item in self.trace.to_list()]
        agent_states: list[JsonValue] = [dict(state) for state in self.agent_states]
        final_world: JsonValue = self.final_world.to_dict()
        return {
            "trace": trace_items,
            "final_world": final_world,
            "agent_states": agent_states,
            "world_digest": self.world_digest,
            "trace_digest": self.trace_digest,
        }

    @classmethod
    def from_dict(cls, data: dict[str, JsonValue]) -> SimulationResult:
        """Restore a SimulationResult from ``to_dict()`` output; no file I/O is performed."""

        trace_raw = data.get("trace")
        world_raw = data.get("final_world")
        states_raw = data.get("agent_states")
        world_digest = data.get("world_digest")
        trace_digest = data.get("trace_digest")
        if not isinstance(trace_raw, list):
            msg = "SimulationResult.trace must be a list."
            raise ReplayError(msg)
        trace_items: list[dict[str, JsonValue]] = []
        for item in trace_raw:
            if not isinstance(item, dict):
                msg = "SimulationResult.trace entries must be dictionaries."
                raise ReplayError(msg)
            trace_items.append(item)
        if not isinstance(world_raw, dict):
            msg = "SimulationResult.final_world must be a dictionary."
            raise ReplayError(msg)
        if not isinstance(states_raw, list) or not all(
            isinstance(item, dict) for item in states_raw
        ):
            msg = "SimulationResult.agent_states must be a list of dictionaries."
            raise ReplayError(msg)
        if not isinstance(world_digest, str) or not isinstance(trace_digest, str):
            msg = "SimulationResult digests must be strings."
            raise ReplayError(msg)
        return cls(
            trace=Trace.from_list(trace_items),
            final_world=World2D.from_dict(world_raw),
            agent_states=tuple(item for item in states_raw if isinstance(item, dict)),
            world_digest=world_digest,
            trace_digest=trace_digest,
        )

    def to_viewer_bundle(self, world: World2D | None = None) -> dict[str, JsonValue]:
        """Return a viewer/game-engine-friendly bundle without file I/O."""

        resolved_world = world or self.final_world
        return {
            "schema_version": 1,
            "format": "codontrace.viewer.bundle",
            "trace": self.trace.to_bundle(),
            "final_world": resolved_world.to_dict(),
            "agent_states": [dict(state) for state in self.agent_states],
            "metrics": {
                "agent_count": len(self.agent_states),
                "agent_events": len(self.trace.events),
                "world_events": len(self.trace.world_events),
                "world_digest": self.world_digest,
                "trace_digest": self.trace_digest,
                "bundle_digest": self.trace.bundle_digest(),
            },
        }

    def to_viewer_json(self, *, indent: int | None = 2) -> str:
        """Serialize the viewer bundle to JSON without writing files."""

        return json.dumps(self.to_viewer_bundle(), indent=indent, sort_keys=True)

    def summary(self) -> dict[str, JsonValue]:
        """Return a compact run summary for notebooks and examples."""

        return {
            "events": len(self.trace),
            "agents": len(self.agent_states),
            "world_digest": self.world_digest,
            "trace_digest": self.trace_digest,
        }


class Simulation:
    """Stateless simulation facade.

    Use ``Simulation.run(...)``. This class is intentionally not instantiated;
    it groups deterministic runtime helpers as static methods.
    """

    @staticmethod
    def run(
        *,
        world: World2D,
        agents: tuple[WhiteBoxAgent, ...],
        config: SimulationConfig,
    ) -> SimulationResult:
        """Run ``agents`` in ``world`` according to ``config``."""

        if not agents:
            msg = "Simulation.run() requires at least one agent."
            raise ConfigurationError(msg)
        _validate_agents(world, agents, allow_agent_on_wall=config.allow_agent_on_wall)
        runtime_world = world.clone()
        trace = Trace()
        rng = RNGManager(seed=config.seed).fork("simulation")
        for tick in range(config.steps):
            order = _order_agents(
                agents,
                config.scheduler,
                rng.fork(f"tick-{tick}"),
                tick=tick,
                context={"world": runtime_world},
            )
            occupied = {agent.position for agent in agents}
            for agent in order:
                previous_position = agent.position
                blocked_positions = (
                    occupied - {previous_position} if config.collision_policy == "block" else set()
                )
                agent.step(
                    runtime_world,
                    trace,
                    blocked_positions=tuple(sorted(blocked_positions)),
                )
                occupied.discard(previous_position)
                occupied.add(agent.position)
        runtime_world.agent_position = None
        states = tuple(_agent_state(agent) for agent in sorted(agents, key=lambda item: item.id))
        return SimulationResult(
            trace=trace,
            final_world=runtime_world,
            agent_states=states,
            world_digest=runtime_world.digest(),
            trace_digest=trace.digest(),
        )


def _validate_agents(
    world: World2D,
    agents: tuple[WhiteBoxAgent, ...],
    *,
    allow_agent_on_wall: bool = False,
) -> None:
    seen_ids: set[str] = set()
    seen_positions: set[Position] = set()
    for agent in agents:
        if agent.id in seen_ids:
            msg = f"Duplicate agent id {agent.id!r}."
            raise ConfigurationError(msg)
        seen_ids.add(agent.id)
        if not world.in_bounds(agent.position):
            msg = f"Agent {agent.id!r} starts outside the world."
            raise ConfigurationError(msg)
        if world.is_wall(agent.position) and not allow_agent_on_wall:
            msg = f"Agent {agent.id!r} starts on a wall."
            raise ConfigurationError(msg)
        if agent.position in seen_positions:
            msg = f"Multiple agents start at {agent.position!r}."
            raise ConfigurationError(msg)
        seen_positions.add(agent.position)


def _order_agents(
    agents: tuple[WhiteBoxAgent, ...],
    scheduler: SchedulerName | SchedulerProtocol,
    rng: RNGManager,
    *,
    tick: int = 0,
    context: dict[str, object] | None = None,
) -> tuple[WhiteBoxAgent, ...]:
    ordered = tuple(sorted(agents, key=lambda agent: agent.id))
    if len(ordered) <= 1:
        return ordered
    resolved = scheduler_from_name(scheduler) if isinstance(scheduler, str) else scheduler
    indexes = resolved.order(ordered, tick, rng, context)
    if sorted(indexes) != list(range(len(ordered))):
        msg = "SchedulerProtocol.order() must return each agent index exactly once."
        raise ConfigurationError(msg)
    return tuple(ordered[index] for index in indexes)


def _agent_state(agent: WhiteBoxAgent) -> dict[str, JsonValue]:
    return {
        "id": agent.id,
        "position": list(agent.position),
        "atp": agent.atp_account.current_atp,
        "cursor": agent.cursor,
        "step_index": agent.step_index,
        "profile": agent.profile,
        "lineage_id": agent.lineage_id,
        "parent_id": agent.parent_id,
        "generation": agent.generation,
        "genome": list(agent.genome.to_codons()),
        "state_digest": agent.state_digest(),
    }
