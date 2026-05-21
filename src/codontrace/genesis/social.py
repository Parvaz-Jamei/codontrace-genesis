"""Deterministic social-interaction records for GENESIS experiments.

These records are evidence carriers only. They do not claim social intelligence
unless a protocol supplies comparative, held-out evidence.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable, Mapping
from dataclasses import dataclass

from codontrace.genesis.canonical import require_finite_float

from codontrace._types import JsonValue
from codontrace._numeric import finite_json_dumps

SOCIAL_INTERACTION_TYPES = (
    "resource_sharing",
    "resource_competition",
    "capsule_teaching",
    "capsule_learning",
    "cooperative_task_progress",
    "free_riding",
    "partner_help",
    "partner_harm",
    "role_complementarity",
)


@dataclass(frozen=True, slots=True)
class SocialInteractionEvent:
    source_organism_id: str
    target_organism_id: str
    interaction_type: str
    resource_delta: float = 0.0
    fitness_delta: float = 0.0
    capsule_delta: float = 0.0
    cooperation_score_delta: float = 0.0
    exploitation_score_delta: float = 0.0
    tick: int = 0
    event_id: str = ""
    resource_delta_source: float = 0.0
    resource_delta_target: float = 0.0
    fitness_delta_source: float = 0.0
    fitness_delta_target: float = 0.0
    world_position: tuple[int, int] | None = None
    lineage_source: str = ""
    lineage_target: str = ""
    world_state_before_digest: str | None = None
    world_state_after_digest: str | None = None
    world_state_delta: dict[str, JsonValue] | None = None
    interaction_status: str = "measured"
    schema_version: str = "social_interaction_v3"

    def __post_init__(self) -> None:
        for attr in (
            "resource_delta",
            "fitness_delta",
            "capsule_delta",
            "cooperation_score_delta",
            "exploitation_score_delta",
            "resource_delta_source",
            "resource_delta_target",
            "fitness_delta_source",
            "fitness_delta_target",
        ):
            object.__setattr__(self, attr, round(require_finite_float(attr, getattr(self, attr)), 10))
        if self.interaction_type not in SOCIAL_INTERACTION_TYPES and self.interaction_type not in {"cooperation", "competition", "partner_interaction"}:
            raise ValueError(f"Unsupported social interaction type: {self.interaction_type}")
        if not self.event_id:
            object.__setattr__(self, "event_id", self.digest_payload_id())

    def digest_payload_id(self) -> str:
        return _digest(
            {
                "tick": self.tick,
                "source_organism_id": self.source_organism_id,
                "target_organism_id": self.target_organism_id,
                "interaction_type": self.interaction_type,
                "capsule_delta": self.capsule_delta,
                "world_state_before_digest": self.world_state_before_digest,
                "world_state_after_digest": self.world_state_after_digest,
                "interaction_status": self.interaction_status,
            }
        )[:16]

    def _payload(self) -> dict[str, JsonValue]:
        return {
            "schema_version": self.schema_version,
            "event_id": self.event_id,
            "tick": self.tick,
            "source_organism_id": self.source_organism_id,
            "target_organism_id": self.target_organism_id,
            "interaction_type": self.interaction_type,
            "resource_delta": self.resource_delta,
            "fitness_delta": self.fitness_delta,
            "capsule_delta": self.capsule_delta,
            "cooperation_score_delta": self.cooperation_score_delta,
            "exploitation_score_delta": self.exploitation_score_delta,
            "resource_delta_source": self.resource_delta_source,
            "resource_delta_target": self.resource_delta_target,
            "fitness_delta_source": self.fitness_delta_source,
            "fitness_delta_target": self.fitness_delta_target,
            "world_position": None
            if self.world_position is None
            else [self.world_position[0], self.world_position[1]],
            "lineage_source": self.lineage_source,
            "lineage_target": self.lineage_target,
            "world_state_before_digest": self.world_state_before_digest,
            "world_state_after_digest": self.world_state_after_digest,
            "world_state_delta": {} if self.world_state_delta is None else dict(self.world_state_delta),
            "interaction_status": self.interaction_status,
        }

    def to_dict(self) -> dict[str, JsonValue]:
        payload = self._payload()
        payload["interaction_digest"] = self.digest()
        return payload

    @classmethod
    def from_dict(cls, data: Mapping[str, JsonValue]) -> SocialInteractionEvent:
        return cls(
            source_organism_id=_str(data, "source_organism_id"),
            target_organism_id=_str(data, "target_organism_id"),
            interaction_type=_str(data, "interaction_type", "partner_interaction"),
            resource_delta=_float(data, "resource_delta", 0.0),
            fitness_delta=_float(data, "fitness_delta", 0.0),
            capsule_delta=_float(data, "capsule_delta", 0.0),
            cooperation_score_delta=_float(data, "cooperation_score_delta", 0.0),
            exploitation_score_delta=_float(data, "exploitation_score_delta", 0.0),
            tick=_int(data, "tick", 0),
            event_id=_str(data, "event_id", ""),
            resource_delta_source=_float(data, "resource_delta_source", 0.0),
            resource_delta_target=_float(data, "resource_delta_target", 0.0),
            fitness_delta_source=_float(data, "fitness_delta_source", 0.0),
            fitness_delta_target=_float(data, "fitness_delta_target", 0.0),
            world_position=_position_or_none(data.get("world_position")),
            lineage_source=_str(data, "lineage_source", ""),
            lineage_target=_str(data, "lineage_target", ""),
            world_state_before_digest=_optional_str(data, "world_state_before_digest"),
            world_state_after_digest=_optional_str(data, "world_state_after_digest"),
            world_state_delta=dict(data.get("world_state_delta", {})) if isinstance(data.get("world_state_delta", {}), Mapping) else {},
            interaction_status=_str(data, "interaction_status", "measured"),
            schema_version=_str(data, "schema_version", "social_interaction_v3"),
        )

    def digest(self) -> str:
        return _digest(self._payload())


@dataclass(frozen=True, slots=True)
class CooperationEvent(SocialInteractionEvent):
    interaction_type: str = "cooperation"


@dataclass(frozen=True, slots=True)
class CompetitionEvent(SocialInteractionEvent):
    interaction_type: str = "competition"


@dataclass(frozen=True, slots=True)
class ResourceSharingEvent(SocialInteractionEvent):
    interaction_type: str = "resource_sharing"


@dataclass(frozen=True, slots=True)
class PartnerInteractionEvent(SocialInteractionEvent):
    interaction_type: str = "partner_interaction"


def social_events_from_capsule_records(
    records: Iterable[object], *, tick: int = 0
) -> tuple[SocialInteractionEvent, ...]:
    """Create deterministic engine-level social events from per-capsule attempts."""

    events: list[SocialInteractionEvent] = []
    for record in records:
        source = str(getattr(record, "source_organism_id", ""))
        target = str(getattr(record, "target_organism_id", ""))
        if not source or not target or source == target:
            continue
        success = bool(getattr(record, "adoption_success", False))
        kind = "capsule_learning" if success else "capsule_teaching"
        events.append(
            SocialInteractionEvent(
                source_organism_id=source,
                target_organism_id=target,
                interaction_type=kind,
                capsule_delta=1.0 if success else 0.0,
                cooperation_score_delta=1.0 if success else 0.25,
                tick=int(getattr(record, "adoption_attempt_tick", tick)),
            )
        )
    return tuple(
        sorted(
            events,
            key=lambda item: (
                item.tick,
                item.source_organism_id,
                item.target_organism_id,
                item.event_id,
            ),
        )
    )


def social_events_from_trace(
    trace: object, *, organism_id: str, tick: int = 0
) -> tuple[SocialInteractionEvent, ...]:
    """Emit conservative non-capsule social/task events from runtime trace evidence.

    These are interaction records, not proof of social intelligence. They become
    useful only when paired with held-out/cross-partner controls.
    """

    raw_events = getattr(trace, "events", trace)
    events: tuple[object, ...] = (
        tuple(raw_events)
        if isinstance(raw_events, Iterable) and not isinstance(raw_events, str | bytes)
        else ()
    )
    rows: list[SocialInteractionEvent] = []
    for event in events:
        target = _event_target(event)
        if not _is_real_social_pair(organism_id, target):
            continue
        position = getattr(event, "position_after", None)
        world_position = position if isinstance(position, tuple) and len(position) == 2 else None
        delta = getattr(event, "world_delta", {})
        if not isinstance(delta, Mapping):
            delta = {}
        action = str(getattr(event, "action", ""))
        status = str(getattr(event, "status", ""))
        if delta.get("resource_credit", 0.0) or action in {"COLLECT_RESOURCE", "EAT_LUMEN"}:
            amount = _float(delta, "resource_credit", 0.0)
            rows.append(
                SocialInteractionEvent(
                    source_organism_id=organism_id,
                    target_organism_id=target,
                    interaction_type="resource_competition",
                    resource_delta_source=amount,
                    resource_delta_target=-amount,
                    cooperation_score_delta=0.0,
                    exploitation_score_delta=max(0.0, amount),
                    tick=int(getattr(event, "step", tick)),
                    world_position=world_position,
                )
            )
        if delta.get("tool_chain_stage_event") is True and status == "executed":
            rows.append(
                SocialInteractionEvent(
                    source_organism_id=organism_id,
                    target_organism_id=target,
                    interaction_type="cooperative_task_progress",
                    cooperation_score_delta=1.0,
                    tick=int(getattr(event, "step", tick)),
                    world_position=world_position,
                )
            )
        if delta.get("tool_chain_order_correct") is False:
            rows.append(
                SocialInteractionEvent(
                    source_organism_id=organism_id,
                    target_organism_id=target,
                    interaction_type="free_riding"
                    if action.startswith("RETURN")
                    else "partner_harm",
                    exploitation_score_delta=0.25,
                    tick=int(getattr(event, "step", tick)),
                    world_position=world_position,
                )
            )
    return tuple(
        sorted(
            rows,
            key=lambda item: (
                item.tick,
                item.source_organism_id,
                item.target_organism_id,
                item.interaction_type,
                item.event_id,
            ),
        )
    )


def social_events_from_local_resource_context(
    trace: object,
    *,
    organism_id: str,
    live_positions: Mapping[str, tuple[int, int]],
    tick: int = 0,
) -> tuple[SocialInteractionEvent, ...]:
    """Infer conservative non-capsule resource competition/sharing events.

    The function only emits events when a real peer is present in the same or an
    adjacent cell and the source trace has an actual resource/fitness delta.
    It is interaction evidence, not a social-intelligence claim.
    """

    raw_events = getattr(trace, "events", trace)
    events: tuple[object, ...] = (
        tuple(raw_events)
        if isinstance(raw_events, Iterable) and not isinstance(raw_events, str | bytes)
        else ()
    )
    source_pos = live_positions.get(organism_id)
    if source_pos is None:
        return ()
    candidates = tuple(
        sorted(
            (
                (abs(source_pos[0] - pos[0]) + abs(source_pos[1] - pos[1]), peer_id, pos)
                for peer_id, pos in live_positions.items()
                if peer_id != organism_id
            ),
            key=lambda item: (item[0], item[1]),
        )
    )
    if not candidates:
        return ()
    rows: list[SocialInteractionEvent] = []
    for event in events:
        delta = getattr(event, "world_delta", {})
        if not isinstance(delta, Mapping):
            continue
        amount = _float(delta, "resource_credit", 0.0) or _float(delta, "lumen_consumed", 0.0)
        if amount <= 0.0:
            continue
        distance, target_id, target_pos = candidates[0]
        if distance > 1:
            continue
        before_digest = getattr(event, "world_digest_before", None)
        after_digest = delta.get("world_digest_after")
        rows.append(
            SocialInteractionEvent(
                source_organism_id=organism_id,
                target_organism_id=target_id,
                interaction_type="resource_competition",
                resource_delta_source=amount,
                resource_delta_target=-amount,
                fitness_delta_source=amount,
                fitness_delta_target=-amount,
                exploitation_score_delta=max(0.0, amount),
                tick=int(getattr(event, "step", tick)),
                world_position=getattr(event, "position_after", source_pos),
                world_state_before_digest=before_digest if isinstance(before_digest, str) else None,
                world_state_after_digest=after_digest if isinstance(after_digest, str) else before_digest if isinstance(before_digest, str) else None,
                world_state_delta={
                    "resource_delta_source": amount,
                    "resource_delta_target": -amount,
                    "target_position": [target_pos[0], target_pos[1]],
                },
                interaction_status="non_capsule_resource_delta",
            )
        )
    return tuple(
        sorted(
            rows,
            key=lambda item: (
                item.tick,
                item.source_organism_id,
                item.target_organism_id,
                item.interaction_type,
                item.event_id,
            ),
        )
    )



@dataclass(frozen=True, slots=True)
class SocialScoreBreakdown:
    """Separated social evidence scores; capsule transfer is not cooperation proof."""

    capsule_social_transfer_score: float
    non_capsule_cooperation_score: float
    resource_competition_score: float
    role_complementarity_score: float
    collective_coordination_score: float
    event_count: int
    schema_version: str = "social_score_breakdown_v1"

    def __post_init__(self) -> None:
        for attr in (
            "capsule_social_transfer_score",
            "non_capsule_cooperation_score",
            "resource_competition_score",
            "role_complementarity_score",
            "collective_coordination_score",
        ):
            object.__setattr__(self, attr, round(require_finite_float(attr, getattr(self, attr), non_negative=True), 10))
        if self.event_count < 0:
            raise ValueError("event_count must be non-negative")

    @property
    def social_interaction_observed(self) -> bool:
        return self.event_count > 0

    @property
    def social_intelligence_claim_eligible(self) -> bool:
        return (
            self.non_capsule_cooperation_score > 0.0
            and self.role_complementarity_score > 0.0
            and self.collective_coordination_score > 0.0
        )

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "schema_version": self.schema_version,
            "capsule_social_transfer_score": self.capsule_social_transfer_score,
            "non_capsule_cooperation_score": self.non_capsule_cooperation_score,
            "resource_competition_score": self.resource_competition_score,
            "role_complementarity_score": self.role_complementarity_score,
            "collective_coordination_score": self.collective_coordination_score,
            "event_count": self.event_count,
            "social_intelligence_claim_eligible": self.social_intelligence_claim_eligible,
        }

    def digest(self) -> str:
        return _digest(self.to_dict())


def score_social_interactions(events: Iterable[SocialInteractionEvent]) -> SocialScoreBreakdown:
    rows = tuple(events)
    capsule = 0.0
    coop = 0.0
    competition = 0.0
    role = 0.0
    for item in rows:
        if item.interaction_type in {"capsule_teaching", "capsule_learning"}:
            capsule += max(0.0, item.capsule_delta or item.cooperation_score_delta)
        elif item.interaction_type in {"cooperative_task_progress", "partner_help"}:
            coop += max(0.0, item.cooperation_score_delta)
        elif item.interaction_type in {"resource_competition", "partner_harm", "free_riding"}:
            competition += max(0.0, item.exploitation_score_delta)
        elif item.interaction_type == "role_complementarity":
            role += max(0.0, item.cooperation_score_delta or item.fitness_delta)
    coordination = min(coop, role) if coop > 0.0 and role > 0.0 else 0.0
    return SocialScoreBreakdown(capsule, coop, competition, role, coordination, len(rows))

def _optional_str(data: Mapping[str, JsonValue], key: str) -> str | None:
    value = data.get(key)
    return value if isinstance(value, str) else None


def _is_real_social_pair(source_id: str | None, target_id: str | None) -> bool:
    if not source_id or not target_id:
        return False
    if target_id == "environment":
        return False
    if source_id == target_id:
        return False
    return True


def _event_target(event: object) -> str:
    delta = getattr(event, "world_delta", {})
    if isinstance(delta, Mapping):
        for key in ("target_organism_id", "partner_id", "blocked_by", "source_organism_id"):
            value = delta.get(key)
            if isinstance(value, str) and value:
                return value
    return ""


def _digest(payload: Mapping[str, JsonValue]) -> str:
    return hashlib.sha256(
        finite_json_dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def _str(data: Mapping[str, JsonValue], key: str, default: str = "") -> str:
    value = data.get(key, default)
    return value if isinstance(value, str) else default


def _int(data: Mapping[str, JsonValue], key: str, default: int) -> int:
    value = data.get(key, default)
    return int(value) if isinstance(value, int) and not isinstance(value, bool) else default


def _float(data: Mapping[str, JsonValue], key: str, default: float) -> float:
    value = data.get(key, default)
    return (
        float(value) if isinstance(value, (int, float)) and not isinstance(value, bool) else default
    )


def _position_or_none(value: object) -> tuple[int, int] | None:
    if (
        isinstance(value, list)
        and len(value) == 2
        and all(isinstance(item, int) and not isinstance(item, bool) for item in value)
    ):
        return (value[0], value[1])
    return None
