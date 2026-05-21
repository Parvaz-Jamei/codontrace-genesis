"""Behavior measurement descriptors for future GENESIS analysis phases."""

from __future__ import annotations

import hashlib
import json
import math
from collections import Counter
from dataclasses import dataclass

from codontrace._types import JsonValue, Position
from codontrace.genesis.atp import GenesisATPState
from codontrace.genesis.liveness import AliveGateResult
from codontrace.trace import Trace, TraceEvent


@dataclass(frozen=True, slots=True)
class BehaviorDescriptor:
    """Deterministic, JSON-serializable behavior descriptor.

    The first ten fields preserve the historical v1 shape. Additional fields are
    optional v2 measurements used by QD, roles, social/capsule diagnostics, and
    task-sensitive scoring. They default to zero/unknown so old serialized
    descriptors still round-trip.
    """

    survival_ticks: int
    reproduction_count: int
    lumen_eaten: int
    nexus_emitted: int
    blocked_ratio: float
    path_entropy_lite: float
    unique_positions: int
    mean_runtime_atp: float
    final_runtime_atp: float
    final_learning_atp: float
    schema_version: str = "behavior_descriptor_v2"
    unique_cells_visited: int = 0
    movement_diversity: float = 0.0
    resource_interactions: int = 0
    hazard_interactions: int = 0
    capsule_emit_count: int = 0
    capsule_read_count: int = 0
    capsule_adoption_count: int = 0
    memory_write_count: int = 0
    memory_read_count: int = 0
    causal_update_count: int = 0
    tool_chain_stage: int = 0
    role_signature: str = "unknown"
    energy_profile: float = 0.0
    lineage_depth: int = 0
    social_interaction_count: int = 0
    partner_interaction_count: int = 0
    homeostasis_state: str = "unknown"

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "schema_version": self.schema_version,
            "survival_ticks": self.survival_ticks,
            "reproduction_count": self.reproduction_count,
            "lumen_eaten": self.lumen_eaten,
            "nexus_emitted": self.nexus_emitted,
            "blocked_ratio": self.blocked_ratio,
            "path_entropy_lite": self.path_entropy_lite,
            "unique_positions": self.unique_positions,
            "unique_cells_visited": self.unique_cells_visited or self.unique_positions,
            "mean_runtime_atp": self.mean_runtime_atp,
            "final_runtime_atp": self.final_runtime_atp,
            "final_learning_atp": self.final_learning_atp,
            "movement_diversity": self.movement_diversity,
            "resource_interactions": self.resource_interactions,
            "hazard_interactions": self.hazard_interactions,
            "capsule_emit_count": self.capsule_emit_count,
            "capsule_read_count": self.capsule_read_count,
            "capsule_adoption_count": self.capsule_adoption_count,
            "memory_write_count": self.memory_write_count,
            "memory_read_count": self.memory_read_count,
            "causal_update_count": self.causal_update_count,
            "tool_chain_stage": self.tool_chain_stage,
            "role_signature": self.role_signature,
            "energy_profile": self.energy_profile,
            "lineage_depth": self.lineage_depth,
            "social_interaction_count": self.social_interaction_count,
            "partner_interaction_count": self.partner_interaction_count,
            "homeostasis_state": self.homeostasis_state,
        }

    @classmethod
    def from_dict(cls, data: dict[str, JsonValue]) -> BehaviorDescriptor:
        return cls(
            survival_ticks=_int(data, "survival_ticks", 0),
            reproduction_count=_int(data, "reproduction_count", 0),
            lumen_eaten=_int(data, "lumen_eaten", 0),
            nexus_emitted=_int(data, "nexus_emitted", 0),
            blocked_ratio=_float(data, "blocked_ratio", 0.0),
            path_entropy_lite=_float(data, "path_entropy_lite", 0.0),
            unique_positions=_int(data, "unique_positions", _int(data, "unique_cells_visited", 0)),
            unique_cells_visited=_int(
                data, "unique_cells_visited", _int(data, "unique_positions", 0)
            ),
            mean_runtime_atp=_float(data, "mean_runtime_atp", 0.0),
            final_runtime_atp=_float(data, "final_runtime_atp", 0.0),
            final_learning_atp=_float(data, "final_learning_atp", 0.0),
            schema_version=_str(data, "schema_version", "behavior_descriptor_v1"),
            movement_diversity=_float(data, "movement_diversity", 0.0),
            resource_interactions=_int(data, "resource_interactions", _int(data, "lumen_eaten", 0)),
            hazard_interactions=_int(data, "hazard_interactions", 0),
            capsule_emit_count=_int(data, "capsule_emit_count", _int(data, "nexus_emitted", 0)),
            capsule_read_count=_int(data, "capsule_read_count", 0),
            capsule_adoption_count=_int(data, "capsule_adoption_count", 0),
            memory_write_count=_int(data, "memory_write_count", 0),
            memory_read_count=_int(data, "memory_read_count", 0),
            causal_update_count=_int(data, "causal_update_count", 0),
            tool_chain_stage=_int(data, "tool_chain_stage", 0),
            role_signature=_str(data, "role_signature", "unknown"),
            energy_profile=_float(data, "energy_profile", 0.0),
            lineage_depth=_int(data, "lineage_depth", 0),
            social_interaction_count=_int(data, "social_interaction_count", 0),
            partner_interaction_count=_int(data, "partner_interaction_count", 0),
            homeostasis_state=_str(data, "homeostasis_state", "unknown"),
        )

    def digest(self) -> str:
        encoded = json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def describe_behavior(
    trace: Trace | tuple[TraceEvent, ...] | list[TraceEvent],
    alive_result: AliveGateResult,
    atp_state: GenesisATPState | None = None,
    *,
    social_interaction_count: int | None = None,
    partner_interaction_count: int | None = None,
) -> BehaviorDescriptor:
    """Return a deterministic behavior measurement descriptor."""

    events = tuple(trace.events if isinstance(trace, Trace) else trace)
    positions: list[Position] = [event.position_after for event in events]
    counts = Counter(positions)
    entropy = 0.0
    if positions:
        total = len(positions)
        for count in counts.values():
            p = count / total
            entropy -= p * math.log2(p)
    runtime_values = [event.atp_after for event in events]
    mean_runtime = round(sum(runtime_values) / len(runtime_values), 10) if runtime_values else 0.0
    final_runtime = (
        atp_state.runtime_available if atp_state is not None else alive_result.final_runtime_atp
    )
    final_learning = 0.0 if atp_state is None else atp_state.learning_available
    reproduction_count = sum(
        1 for event in events if event.world_delta.get("reproduction_succeeded") is True
    )
    lumen_eaten = sum(
        1
        for event in events
        if event.action == "EAT_LUMEN" and event.world_delta.get("lumen_interaction") is True
    )
    nexus_emitted = sum(1 for event in events if event.action == "EMIT_NEXUS")
    capsule_read_count = sum(
        1
        for event in events
        if event.world_delta.get("capsule_transfer_status") == "capsule_read"
        or event.world_delta.get("capsules_read", 0)
    )
    capsule_adoption_count = sum(
        1 for event in events if event.world_delta.get("capsule_adoption_success") is True
    )
    memory_write_count = sum(
        1 for event in events if event.world_delta.get("memory_write_succeeded") is True
    )
    causal_update_count = sum(
        1 for event in events if event.world_delta.get("causal_graph_update_succeeded") is True
    )
    hazard_interactions = sum(
        1
        for event in events
        if event.world_delta.get("hazard_interaction") is True or "hazard" in event.action.lower()
    )
    tool_chain_stage = max(
        (
            int(value)
            for event in events
            if isinstance((value := event.world_delta.get("tool_chain_stage")), int)
        ),
        default=0,
    )
    movement_diversity = round(len(counts) / max(1, len(positions)), 10)
    energy_profile = round((mean_runtime + final_runtime) / 2.0, 10)
    role_signature = infer_role_signature(
        lumen_eaten=lumen_eaten,
        unique_positions=len(counts),
        nexus_emitted=nexus_emitted,
        reproduction_count=reproduction_count,
        blocked_ratio=alive_result.blocked_ratio,
        capsule_read_count=capsule_read_count,
        capsule_adoption_count=capsule_adoption_count,
    )
    return BehaviorDescriptor(
        survival_ticks=alive_result.survived_ticks,
        reproduction_count=reproduction_count,
        lumen_eaten=lumen_eaten,
        nexus_emitted=nexus_emitted,
        blocked_ratio=alive_result.blocked_ratio,
        path_entropy_lite=round(entropy, 10),
        unique_positions=len(counts),
        unique_cells_visited=len(counts),
        mean_runtime_atp=mean_runtime,
        final_runtime_atp=round(final_runtime, 10),
        final_learning_atp=round(final_learning, 10),
        movement_diversity=movement_diversity,
        resource_interactions=lumen_eaten,
        hazard_interactions=hazard_interactions,
        capsule_emit_count=nexus_emitted,
        capsule_read_count=capsule_read_count,
        capsule_adoption_count=capsule_adoption_count,
        memory_write_count=memory_write_count,
        causal_update_count=causal_update_count,
        tool_chain_stage=tool_chain_stage,
        role_signature=role_signature,
        energy_profile=energy_profile,
        social_interaction_count=(
            capsule_read_count + capsule_adoption_count
            if social_interaction_count is None
            else int(social_interaction_count)
        ),
        partner_interaction_count=(0 if partner_interaction_count is None else int(partner_interaction_count)),
    )


def infer_role_signature(
    *,
    lumen_eaten: int = 0,
    unique_positions: int = 0,
    nexus_emitted: int = 0,
    reproduction_count: int = 0,
    blocked_ratio: float = 0.0,
    capsule_read_count: int = 0,
    capsule_adoption_count: int = 0,
) -> str:
    """Return a stable, conservative role label from observed behavior counters."""

    scores = {
        "forager": float(lumen_eaten),
        "explorer": float(unique_positions),
        "capsule_emitter": float(nexus_emitted),
        "capsule_reader": float(capsule_read_count + capsule_adoption_count),
        "reproducer": float(reproduction_count),
        "hazard_avoider": max(0.0, 1.0 - float(blocked_ratio)),
    }
    best_role, best_score = sorted(scores.items(), key=lambda item: (-item[1], item[0]))[0]
    return best_role if best_score > 0 else "unknown"


@dataclass(frozen=True, slots=True)
class BehaviorDescriptorFactory:
    """Public factory so QD/analysis use one descriptor implementation."""

    schema_version: str = "behavior_descriptor_v2"

    def build(
        self,
        trace: Trace | tuple[TraceEvent, ...] | list[TraceEvent],
        alive_result: AliveGateResult,
        atp_state: GenesisATPState | None = None,
    ) -> BehaviorDescriptor:
        descriptor = describe_behavior(trace, alive_result, atp_state)
        if descriptor.schema_version == self.schema_version:
            return descriptor
        return BehaviorDescriptor.from_dict(
            {**descriptor.to_dict(), "schema_version": self.schema_version}
        )


def _str(data: dict[str, JsonValue], key: str, default: str) -> str:
    value = data.get(key, default)
    if not isinstance(value, str):
        msg = f"{key} must be a string."
        raise ValueError(msg)
    return value


def _int(data: dict[str, JsonValue], key: str, default: int) -> int:
    value = data.get(key, default)
    if isinstance(value, bool) or not isinstance(value, int):
        msg = f"{key} must be an integer."
        raise ValueError(msg)
    return value


def _float(data: dict[str, JsonValue], key: str, default: float) -> float:
    value = data.get(key, default)
    if isinstance(value, bool) or not isinstance(value, int | float):
        msg = f"{key} must be numeric."
        raise ValueError(msg)
    return float(value)


@dataclass(frozen=True, slots=True)
class BehaviorDescriptorSchema:
    """Extensible behavior descriptor schema for UI/selection/fitness contracts."""

    metric_names: tuple[str, ...]
    version: str = "behavior_descriptor_schema_v1"

    def __post_init__(self) -> None:
        if not self.metric_names:
            msg = "BehaviorDescriptorSchema.metric_names must not be empty."
            raise ValueError(msg)
        if len(set(self.metric_names)) != len(self.metric_names):
            msg = "BehaviorDescriptorSchema.metric_names must be unique."
            raise ValueError(msg)

    def to_dict(self) -> dict[str, JsonValue]:
        return {"version": self.version, "metric_names": list(self.metric_names)}

    def digest(self) -> str:
        payload = json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()


class BehaviorMetricRegistry:
    """Small deterministic registry for custom behavior metrics."""

    def __init__(self, metrics: dict[str, object] | None = None) -> None:
        self._metrics = dict(metrics or {})

    @classmethod
    def genesis_v1(cls) -> BehaviorMetricRegistry:
        return cls(
            {
                "survival_ticks": lambda descriptor, context=None: descriptor.survival_ticks,
                "blocked_ratio": lambda descriptor, context=None: descriptor.blocked_ratio,
                "resource_gain": lambda descriptor, context=None: descriptor.lumen_eaten,
                "capsule_activity": lambda descriptor, context=None: descriptor.nexus_emitted,
            }
        )

    def register(self, name: str, extractor: object) -> BehaviorMetricRegistry:
        if not name:
            msg = "metric name must not be empty."
            raise ValueError(msg)
        if name in self._metrics:
            msg = f"metric {name!r} is already registered."
            raise ValueError(msg)
        copied = dict(self._metrics)
        copied[name] = extractor
        return BehaviorMetricRegistry(copied)

    def names(self) -> tuple[str, ...]:
        return tuple(sorted(self._metrics))

    def extract(
        self, descriptor: BehaviorDescriptor, context: dict[str, object] | None = None
    ) -> dict[str, float]:
        values: dict[str, float] = {}
        for name in self.names():
            extractor = self._metrics[name]
            if not callable(extractor):
                msg = f"metric {name!r} extractor is not callable."
                raise ValueError(msg)
            values[name] = round(float(extractor(descriptor, context)), 10)
        return values

    def schema(self) -> BehaviorDescriptorSchema:
        return BehaviorDescriptorSchema(metric_names=self.names())


@dataclass(frozen=True, slots=True)
class BehaviorDescriptorBuilder:
    """Build a flat extensible descriptor dict from the core descriptor."""

    registry: BehaviorMetricRegistry

    @classmethod
    def genesis_v1(cls) -> BehaviorDescriptorBuilder:
        return cls(registry=BehaviorMetricRegistry.genesis_v1())

    def build(
        self,
        trace: Trace | list[TraceEvent],
        alive_result: AliveGateResult,
        atp_state: GenesisATPState | None = None,
        context: dict[str, object] | None = None,
    ) -> dict[str, float]:
        descriptor = describe_behavior(trace, alive_result, atp_state)
        return self.registry.extract(descriptor, context)
