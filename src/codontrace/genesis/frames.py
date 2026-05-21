"""Exact engine-frame export contracts for visualizers and audits."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any

from codontrace._types import JsonValue


@dataclass(frozen=True, slots=True)
class AgentFrame:
    organism_id: str
    position: tuple[int, int] | None
    role: str = "unknown"
    action: str = ""
    runtime_atp: float = 0.0
    learning_atp: float = 0.0
    fitness_components: dict[str, float] | None = None

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "organism_id": self.organism_id,
            "position": None if self.position is None else [self.position[0], self.position[1]],
            "role": self.role,
            "action": self.action,
            "runtime_atp": self.runtime_atp,
            "learning_atp": self.learning_atp,
            "fitness_components": dict(sorted((self.fitness_components or {}).items())),
        }

    def digest(self) -> str:
        return _digest(self.to_dict())


@dataclass(frozen=True, slots=True)
class CapsuleFrame:
    capsule_id: str
    source_organism_id: str
    emitted_tick: int
    confidence: float
    source_fitness: float

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "capsule_id": self.capsule_id,
            "source_organism_id": self.source_organism_id,
            "emitted_tick": self.emitted_tick,
            "confidence": self.confidence,
            "source_fitness": self.source_fitness,
        }

    def digest(self) -> str:
        return _digest(self.to_dict())


@dataclass(frozen=True, slots=True)
class EventFrame:
    tick: int
    organism_id: str
    action: str
    status: str
    reason: str = ""
    digest: str = ""

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "tick": self.tick,
            "organism_id": self.organism_id,
            "action": self.action,
            "status": self.status,
            "reason": self.reason,
            "digest": self.digest,
        }


@dataclass(frozen=True, slots=True)
class WorldFrame:
    tick: int
    world_grid: dict[str, JsonValue]
    world_digest: str

    def to_dict(self) -> dict[str, JsonValue]:
        return {"tick": self.tick, "world_grid": self.world_grid, "world_digest": self.world_digest}

    def digest(self) -> str:
        return _digest(self.to_dict())


@dataclass(frozen=True, slots=True)
class EngineFrame:
    tick: int
    world: WorldFrame
    agents: tuple[AgentFrame, ...]
    capsules: tuple[CapsuleFrame, ...] = ()
    events: tuple[EventFrame, ...] = ()
    digests: dict[str, str] | None = None
    schema_version: str = "engine_frame_v1"

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "schema_version": self.schema_version,
            "tick": self.tick,
            "world": self.world.to_dict(),
            "agents": [agent.to_dict() for agent in self.agents],
            "capsules": [capsule.to_dict() for capsule in self.capsules],
            "events": [event.to_dict() for event in self.events],
            "digests": dict(sorted((self.digests or {}).items())),
        }

    def digest(self) -> str:
        return _digest(self.to_dict())


def engine_frame_from_generation(index: int, generation_result: Any) -> EngineFrame:
    world_payload = generation_result.world_after.to_dict()
    world = WorldFrame(
        tick=index, world_grid=world_payload, world_digest=generation_result.world_after_digest
    )
    events_by_agent = {}
    events = []
    for trace in generation_result.traces:
        for event in trace.events:
            events_by_agent[event.agent_id] = event
            events.append(
                EventFrame(
                    event.step,
                    event.agent_id,
                    event.action,
                    event.status,
                    event.reason,
                    _digest(event.to_dict()),
                )
            )
    agents = []
    for record in sorted(generation_result.organism_records, key=lambda item: item.organism_id):
        descriptor = record.behavior_descriptor
        role = "unknown" if descriptor is None else descriptor.role_signature
        components = {}
        if record.fitness_breakdown is not None:
            for component in record.fitness_breakdown.components:
                name = getattr(component, "name", "component")
                value = getattr(component, "weighted", getattr(component, "contribution", 0.0))
                components[str(name)] = float(value)
        last_event = events_by_agent.get(record.organism_id)
        agents.append(
            AgentFrame(
                organism_id=record.organism_id,
                position=None if last_event is None else last_event.position_after,
                action="" if last_event is None else last_event.action,
                role=role,
                runtime_atp=record.runtime_atp_after,
                learning_atp=0.0,
                fitness_components=components,
            )
        )
    capsules = []
    if generation_result.nexus_layer is not None:
        for capsule in generation_result.nexus_layer.store.capsules:
            capsules.append(
                CapsuleFrame(
                    capsule.capsule_id,
                    capsule.source_organism_id,
                    capsule.emitted_tick,
                    capsule.confidence,
                    capsule.source_fitness,
                )
            )
    return EngineFrame(
        tick=index,
        world=world,
        agents=tuple(agents),
        capsules=tuple(sorted(capsules, key=lambda item: item.capsule_id)),
        events=tuple(
            sorted(events, key=lambda item: (item.tick, item.organism_id, item.action, item.digest))
        ),
        digests={
            "generation": generation_result.digest(),
            "world": generation_result.world_after_digest,
        },
    )


def _digest(payload: dict[str, JsonValue]) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
