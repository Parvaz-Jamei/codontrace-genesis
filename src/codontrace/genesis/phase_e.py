"""Phase E capsule/memory/role/collective substrate and Avida-parity protocol hooks.

Opt-in runtime effects for organism-local or lineage capsule memory, role /
propagule-eligibility gates, deme containers with a messaging buffer, a
plasticity *protocol* object that reads Phase C environment cues, and a
head-to-head ``AvidaParityProtocolSpec``. Defaults are off so Phase A–D
presets and pinned digests stay stable.

Literature grounding (software capability / experimental-design checklist
only — not an Avida replacement and not proof of learning, plasticity, or
collective intelligence):

- Avida demes / group selection: ``devosoft/avida`` wiki Deme-introduction;
  ``DEMES_*`` config and GermlineReplication; Goldsby et al. coordination
  instructions ``send_message``, ``retrieve_message``, ``broadcast_message``,
  ``block_propagation``.
- Cooperative networks / digital germlines (GECCO 2008 GermlineReplication).
- Phenotypic plasticity in fluctuating environments (Clune 2007; Lalejini &
  Ofria 2016; Frontiers 2021 Adaptive Phenotypic Plasticity ``sense-react-*``
  cues). Phase C already supplies the fluctuating-env substrate.
- Associative learning / memory / odometry in Avida (Am Nat 2020 learning;
  PLOS One odometry case study) mapped here to capsule/memory hooks with
  **real** subsequent action / ATP / task-eligibility effects.
- OntoAvida / avidaR (Sci Data 2023; PeerJ CS) — exportable
  phenotype/transcriptome-ish evidence objects.

Claim ceiling: ``runtime_observation`` / software capability /
``oee_measurement_only``. Blocked: Avida-replacement, intelligence,
proved collective intelligence, evolved-plasticity proof.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field, replace
from enum import StrEnum
from typing import Any

from codontrace._types import JsonValue
from codontrace.errors import ConfigurationError
from codontrace.genesis.canonical import canonical_digest, require_finite_float
from codontrace.genesis.claim_gate import ClaimDecision, ClaimRequest, ScientificClaimGate

_PHASE_E_CLAIM_CEILING = "runtime_observation"
_PACK_SCHEMA = "phase_e_evidence_pack_v1"
_FORBIDDEN_PACK_CLAIMS = frozenset(
    {
        "collective_intelligence",
        "proved_collective_intelligence",
        "real_collective_intelligence",
        "open_ended_intelligence",
        "agi",
        "evolved_plasticity",
        "phenotypic_plasticity_evolved",
        "avida_replacement",
        "associative_learning_proved",
        "instinct_evolution_proved",
    }
)

LITERATURE_CHECKLIST: tuple[tuple[str, str], ...] = (
    (
        "avida_demes_group_selection",
        "devosoft/avida wiki Deme-introduction; DEMES_* configuration and "
        "GermlineReplication as the group-selection / deme-replication substrate.",
    ),
    (
        "goldsby_coordination_instructions",
        "Goldsby et al. coordination instructions: send_message, retrieve_message, "
        "broadcast_message, block_propagation (Avida-parity messaging subset).",
    ),
    (
        "gecco_2008_germline_replication",
        "Cooperative network / digital-germline papers around GECCO 2008 "
        "GermlineReplication: soma vs germline / propagule eligibility.",
    ),
    (
        "plasticity_fluctuating_env",
        "Clune 2007; Lalejini & Ofria 2016; Frontiers 2021 Adaptive Phenotypic "
        "Plasticity (sense-react-* cues). Phase C supplies fluctuating env; "
        "Phase E adds a sensory-read + sense-react protocol object.",
    ),
    (
        "ghalambor_clune_four_conditions",
        "Ghalambor/Clune-style four experimental conditions (ancestral static, "
        "novel static, fluctuating, assimilation under constant novel) as an "
        "experimental-design checklist, not evolved-plasticity proof.",
    ),
    (
        "associative_learning_odometry",
        "Am Nat 2020 associative learning in Avida; PLOS One odometry case study. "
        "Mapped to organism-local/lineage capsule slots that change later action, "
        "ATP, or task eligibility under a fixed seed.",
    ),
    (
        "ontoavida_avidar",
        "OntoAvida / avidaR (Sci Data 2023; PeerJ CS): exportable "
        "phenotype/transcriptome-ish evidence objects with JSON + digest.",
    ),
)


class RoleKind(StrEnum):
    """Avida-inspired differentiation tags. Not proof of evolved division of labor."""

    UNASSIGNED = "unassigned"
    SOMA = "soma"
    GERMLINE = "germline"
    MESSENGER = "messenger"
    FORAGER = "forager"


class MessageKind(StrEnum):
    """Goldsby-style coordination instruction kinds (Avida-parity subset)."""

    SEND = "send_message"
    RETRIEVE = "retrieve_message"
    BROADCAST = "broadcast_message"
    BLOCK_PROPAGATION = "block_propagation"


class PlasticityCondition(StrEnum):
    """Ghalambor/Clune-style experimental-design conditions (checklist, not proof)."""

    ANCESTRAL_STATIC = "ancestral_static"
    NOVEL_STATIC = "novel_static"
    FLUCTUATING = "fluctuating"
    ASSIMILATION_CONSTANT_NOVEL = "assimilation_constant_novel"


GHALAMBOR_CLUNE_CONDITIONS: tuple[tuple[str, str], ...] = (
    (
        PlasticityCondition.ANCESTRAL_STATIC.value,
        "Ancestral environment held static; plastic response is not expected. Baseline.",
    ),
    (
        PlasticityCondition.NOVEL_STATIC.value,
        "Sudden novel environment held static; a plastic response may be maladaptive.",
    ),
    (
        PlasticityCondition.FLUCTUATING.value,
        "Fluctuating/seasonal environment (Phase C periodic or seeded regimes); "
        "selection *for* reversible plasticity is the experimental hypothesis, not a result.",
    ),
    (
        PlasticityCondition.ASSIMILATION_CONSTANT_NOVEL.value,
        "Constant novel environment after a plastic episode; genetic-assimilation "
        "design, not a claim that assimilation occurred.",
    ),
)


@dataclass(frozen=True, slots=True)
class SensoryCue:
    """One organism's Phase C / local sensory read. Not a plasticity proof."""

    tick: int = 0
    regime_name: str = ""
    hazard_intensity: float = 0.0
    local_resource: float = 0.0
    has_local_food: bool = False
    nearby_resource: bool = False
    source: str = "unspecified"

    def __post_init__(self) -> None:
        if self.tick < 0:
            raise ConfigurationError("SensoryCue.tick must be non-negative.")
        object.__setattr__(
            self,
            "hazard_intensity",
            require_finite_float("hazard_intensity", self.hazard_intensity, non_negative=True),
        )
        object.__setattr__(
            self,
            "local_resource",
            require_finite_float("local_resource", self.local_resource, non_negative=True),
        )

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "tick": self.tick,
            "regime_name": self.regime_name,
            "hazard_intensity": self.hazard_intensity,
            "local_resource": self.local_resource,
            "has_local_food": self.has_local_food,
            "nearby_resource": self.nearby_resource,
            "source": self.source,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, JsonValue]) -> SensoryCue:
        return cls(
            tick=_int(data, "tick", 0),
            regime_name=_str(data, "regime_name", ""),
            hazard_intensity=_float(data, "hazard_intensity", 0.0),
            local_resource=_float(data, "local_resource", 0.0),
            has_local_food=_bool(data, "has_local_food", False),
            nearby_resource=_bool(data, "nearby_resource", False),
            source=_str(data, "source", "unspecified"),
        )

    def digest(self) -> str:
        return canonical_digest(self.to_dict())


def read_environment_cue(
    *,
    tick: int,
    position: tuple[int, int],
    world: object | None,
    environment: object | None = None,
    sense_radius: int = 1,
) -> SensoryCue:
    """First-class sensory-read API over Phase C env state + local patches.

    Reuses existing World2D resources and ``EnvironmentState.active_regime`` /
    ``hazard_intensity``. Does not claim evolved ``sense-react-*`` instructions.
    """

    regime = str(getattr(environment, "active_regime", "") or "")
    hazard = float(getattr(environment, "hazard_intensity", 0.0) or 0.0)
    resources = getattr(world, "resources", None)
    local = 0.0
    nearby = False
    if isinstance(resources, Mapping):
        raw_local = resources.get(position, 0.0)
        if isinstance(raw_local, (int, float)) and not isinstance(raw_local, bool):
            local = float(raw_local)
        if sense_radius > 0:
            width = int(getattr(world, "width", 0) or 0)
            height = int(getattr(world, "height", 0) or 0)
            px, py = position
            for dx in range(-sense_radius, sense_radius + 1):
                for dy in range(-sense_radius, sense_radius + 1):
                    if dx == 0 and dy == 0:
                        continue
                    cell = (px + dx, py + dy)
                    if width and height:
                        if not (0 <= cell[0] < width and 0 <= cell[1] < height):
                            continue
                    amount = resources.get(cell, 0.0)
                    if isinstance(amount, (int, float)) and not isinstance(amount, bool) and amount > 0:
                        nearby = True
                        break
                if nearby:
                    break
    return SensoryCue(
        tick=tick,
        regime_name=regime,
        hazard_intensity=round(hazard, 10),
        local_resource=round(local, 10),
        has_local_food=local > 0.0,
        nearby_resource=nearby or local > 0.0,
        source="phase_c_env_and_local_patches",
    )


@dataclass(frozen=True, slots=True)
class CapsuleSlot:
    """One associative cue→action memory slot (Am Nat 2020 / odometry mapping)."""

    cue_regime: str = ""
    cue_has_local_food: bool = False
    preferred_action: str = "EAT_LUMEN"
    written_tick: int = 0
    source: str = "self"

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "cue_regime": self.cue_regime,
            "cue_has_local_food": self.cue_has_local_food,
            "preferred_action": self.preferred_action,
            "written_tick": self.written_tick,
            "source": self.source,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, JsonValue]) -> CapsuleSlot:
        return cls(
            cue_regime=_str(data, "cue_regime", ""),
            cue_has_local_food=_bool(data, "cue_has_local_food", False),
            preferred_action=_str(data, "preferred_action", "EAT_LUMEN"),
            written_tick=_int(data, "written_tick", 0),
            source=_str(data, "source", "self"),
        )

    def digest(self) -> str:
        return canonical_digest(self.to_dict())

    def matches(self, cue: SensoryCue) -> bool:
        if self.cue_has_local_food and not cue.has_local_food:
            return False
        if self.cue_regime and cue.regime_name and self.cue_regime != cue.regime_name:
            return False
        if self.cue_has_local_food:
            return cue.has_local_food
        if self.cue_regime:
            return self.cue_regime == cue.regime_name
        # Unconstrained slot (seed prior / message write with empty regime)
        # matches any cue so WAIT genomes can substitute under a seeded action.
        return True


@dataclass(slots=True)
class CapsuleMemoryState:
    """Organism-local (optionally lineage-copied) capsule slots with counters."""

    slots: tuple[CapsuleSlot, ...] = ()
    write_count: int = 0
    read_count: int = 0
    substitutions: int = 0
    atp_bonus_applied: float = 0.0
    enabled: bool = True

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "slots": [item.to_dict() for item in self.slots],
            "write_count": self.write_count,
            "read_count": self.read_count,
            "substitutions": self.substitutions,
            "atp_bonus_applied": self.atp_bonus_applied,
            "enabled": self.enabled,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, JsonValue]) -> CapsuleMemoryState:
        raw_slots = data.get("slots", [])
        slots = tuple(
            CapsuleSlot.from_dict(item) for item in raw_slots if isinstance(item, Mapping)
        ) if isinstance(raw_slots, list) else ()
        return cls(
            slots=slots,
            write_count=_int(data, "write_count", 0),
            read_count=_int(data, "read_count", 0),
            substitutions=_int(data, "substitutions", 0),
            atp_bonus_applied=_float(data, "atp_bonus_applied", 0.0),
            enabled=_bool(data, "enabled", True),
        )

    def digest(self) -> str:
        return canonical_digest(self.to_dict())

    def matching_slot(self, cue: SensoryCue) -> CapsuleSlot | None:
        for slot in reversed(self.slots):
            if slot.matches(cue):
                return slot
        return None

    def write_slot(self, slot: CapsuleSlot, *, capacity: int = 4) -> None:
        existing = [item for item in self.slots if not (
            item.cue_regime == slot.cue_regime
            and item.cue_has_local_food == slot.cue_has_local_food
            and item.preferred_action == slot.preferred_action
        )]
        existing.append(slot)
        self.slots = tuple(existing[-max(1, capacity) :])
        self.write_count += 1


@dataclass(frozen=True, slots=True)
class CapsuleMemoryConfig:
    """Opt-in associative capsule/memory with real subsequent effects."""

    enabled: bool = False
    inherit_lineage: bool = False
    effect_action_choice: bool = True
    effect_atp: bool = True
    effect_task_eligibility: bool = True
    atp_bonus: float = 0.5
    slot_capacity: int = 4
    substitutable_actions: tuple[str, ...] = ("WAIT",)
    write_actions: tuple[str, ...] = ("EAT_LUMEN",)
    seed_preferred_action: str = ""
    seed_requires_local_food: bool = True

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "atp_bonus",
            require_finite_float("atp_bonus", self.atp_bonus, non_negative=True),
        )
        if self.slot_capacity <= 0:
            raise ConfigurationError("CapsuleMemoryConfig.slot_capacity must be > 0.")
        object.__setattr__(self, "substitutable_actions", tuple(self.substitutable_actions))
        object.__setattr__(self, "write_actions", tuple(self.write_actions))

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "enabled": self.enabled,
            "inherit_lineage": self.inherit_lineage,
            "effect_action_choice": self.effect_action_choice,
            "effect_atp": self.effect_atp,
            "effect_task_eligibility": self.effect_task_eligibility,
            "atp_bonus": self.atp_bonus,
            "slot_capacity": self.slot_capacity,
            "substitutable_actions": list(self.substitutable_actions),
            "write_actions": list(self.write_actions),
            "seed_preferred_action": self.seed_preferred_action,
            "seed_requires_local_food": self.seed_requires_local_food,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, JsonValue]) -> CapsuleMemoryConfig:
        return cls(
            enabled=_bool(data, "enabled", False),
            inherit_lineage=_bool(data, "inherit_lineage", False),
            effect_action_choice=_bool(data, "effect_action_choice", True),
            effect_atp=_bool(data, "effect_atp", True),
            effect_task_eligibility=_bool(data, "effect_task_eligibility", True),
            atp_bonus=_float(data, "atp_bonus", 0.5),
            slot_capacity=_int(data, "slot_capacity", 4),
            substitutable_actions=_str_tuple(data, "substitutable_actions", ("WAIT",)),
            write_actions=_str_tuple(data, "write_actions", ("EAT_LUMEN",)),
            seed_preferred_action=_str(data, "seed_preferred_action", ""),
            seed_requires_local_food=_bool(data, "seed_requires_local_food", True),
        )

    def digest(self) -> str:
        return canonical_digest(self.to_dict())


@dataclass(frozen=True, slots=True)
class DifferentiationRole:
    """Propagule-eligibility / messaging flags inspired by Avida germlines."""

    kind: RoleKind | str = RoleKind.UNASSIGNED
    propagule_eligible: bool = True
    can_message: bool = True
    can_forward: bool = True

    def __post_init__(self) -> None:
        object.__setattr__(self, "kind", _role_kind(self.kind))

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "kind": _role_kind(self.kind).value,
            "propagule_eligible": self.propagule_eligible,
            "can_message": self.can_message,
            "can_forward": self.can_forward,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, JsonValue]) -> DifferentiationRole:
        return cls(
            kind=_str(data, "kind", RoleKind.UNASSIGNED.value),
            propagule_eligible=_bool(data, "propagule_eligible", True),
            can_message=_bool(data, "can_message", True),
            can_forward=_bool(data, "can_forward", True),
        )

    def digest(self) -> str:
        return canonical_digest(self.to_dict())


def role_for_kind(kind: RoleKind | str) -> DifferentiationRole:
    resolved = _role_kind(kind)
    if resolved is RoleKind.GERMLINE:
        return DifferentiationRole(
            kind=resolved, propagule_eligible=True, can_message=False, can_forward=False
        )
    if resolved is RoleKind.SOMA:
        return DifferentiationRole(
            kind=resolved, propagule_eligible=False, can_message=False, can_forward=False
        )
    if resolved is RoleKind.MESSENGER:
        return DifferentiationRole(
            kind=resolved, propagule_eligible=False, can_message=True, can_forward=True
        )
    if resolved is RoleKind.FORAGER:
        return DifferentiationRole(
            kind=resolved, propagule_eligible=False, can_message=True, can_forward=False
        )
    return DifferentiationRole(kind=RoleKind.UNASSIGNED)


@dataclass(frozen=True, slots=True)
class RoleDifferentiationConfig:
    """Opt-in role tags that can gate reproduction or messaging."""

    enabled: bool = False
    assignment: str = "round_robin"
    gate_reproduction: bool = False
    gate_messaging: bool = False
    explicit_roles: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.assignment not in {"round_robin", "genome_prefix", "explicit", "unassigned"}:
            raise ConfigurationError(
                "RoleDifferentiationConfig.assignment must be round_robin, "
                "genome_prefix, explicit, or unassigned."
            )
        object.__setattr__(self, "explicit_roles", tuple(self.explicit_roles))

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "enabled": self.enabled,
            "assignment": self.assignment,
            "gate_reproduction": self.gate_reproduction,
            "gate_messaging": self.gate_messaging,
            "explicit_roles": list(self.explicit_roles),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, JsonValue]) -> RoleDifferentiationConfig:
        return cls(
            enabled=_bool(data, "enabled", False),
            assignment=_str(data, "assignment", "round_robin"),
            gate_reproduction=_bool(data, "gate_reproduction", False),
            gate_messaging=_bool(data, "gate_messaging", False),
            explicit_roles=_str_tuple(data, "explicit_roles", ()),
        )

    def digest(self) -> str:
        return canonical_digest(self.to_dict())


@dataclass(frozen=True, slots=True)
class DemeMessage:
    """One recorded deme messaging event (Goldsby-instruction analog)."""

    tick: int
    deme_id: str
    sender_id: str
    kind: MessageKind | str
    payload: str
    recipient_ids: tuple[str, ...] = ()
    blocked: bool = False
    blocked_reason: str = ""

    def __post_init__(self) -> None:
        if self.tick < 0:
            raise ConfigurationError("DemeMessage.tick must be non-negative.")
        object.__setattr__(self, "kind", _message_kind(self.kind))
        object.__setattr__(self, "recipient_ids", tuple(str(item) for item in self.recipient_ids))

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "tick": self.tick,
            "deme_id": self.deme_id,
            "sender_id": self.sender_id,
            "kind": _message_kind(self.kind).value,
            "payload": self.payload,
            "recipient_ids": list(self.recipient_ids),
            "blocked": self.blocked,
            "blocked_reason": self.blocked_reason,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, JsonValue]) -> DemeMessage:
        return cls(
            tick=_int(data, "tick", 0),
            deme_id=_str(data, "deme_id"),
            sender_id=_str(data, "sender_id"),
            kind=_str(data, "kind", MessageKind.SEND.value),
            payload=_str(data, "payload", ""),
            recipient_ids=_str_tuple(data, "recipient_ids", ()),
            blocked=_bool(data, "blocked", False),
            blocked_reason=_str(data, "blocked_reason", ""),
        )

    def digest(self) -> str:
        return canonical_digest(self.to_dict())


@dataclass(frozen=True, slots=True)
class DemeReplicationEvent:
    """Minimal real deme-replication path (Avida DEMES_* / GermlineReplication analog)."""

    tick: int
    source_deme_id: str
    target_deme_id: str
    mean_fitness: float
    germline_parent_id: str = ""
    child_id: str = ""
    trigger: str = "mean_fitness_threshold"

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "mean_fitness",
            round(require_finite_float("mean_fitness", self.mean_fitness), 10),
        )

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "tick": self.tick,
            "source_deme_id": self.source_deme_id,
            "target_deme_id": self.target_deme_id,
            "mean_fitness": self.mean_fitness,
            "germline_parent_id": self.germline_parent_id,
            "child_id": self.child_id,
            "trigger": self.trigger,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, JsonValue]) -> DemeReplicationEvent:
        return cls(
            tick=_int(data, "tick", 0),
            source_deme_id=_str(data, "source_deme_id"),
            target_deme_id=_str(data, "target_deme_id"),
            mean_fitness=_float(data, "mean_fitness", 0.0),
            germline_parent_id=_str(data, "germline_parent_id", ""),
            child_id=_str(data, "child_id", ""),
            trigger=_str(data, "trigger", "mean_fitness_threshold"),
        )

    def digest(self) -> str:
        return canonical_digest(self.to_dict())


@dataclass(frozen=True, slots=True)
class Deme:
    deme_id: str
    member_ids: tuple[str, ...] = ()
    generation: int = 0

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "deme_id": self.deme_id,
            "member_ids": list(self.member_ids),
            "generation": self.generation,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, JsonValue]) -> Deme:
        return cls(
            deme_id=_str(data, "deme_id"),
            member_ids=_str_tuple(data, "member_ids", ()),
            generation=_int(data, "generation", 0),
        )

    def digest(self) -> str:
        return canonical_digest(self.to_dict())


@dataclass(slots=True)
class DemeState:
    """Group containers plus a messaging buffer. Defaults unused when demes are off."""

    demes: tuple[Deme, ...] = ()
    inbox: tuple[DemeMessage, ...] = ()
    replication_events: tuple[DemeReplicationEvent, ...] = ()

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "demes": [item.to_dict() for item in self.demes],
            "inbox": [item.to_dict() for item in self.inbox],
            "replication_events": [item.to_dict() for item in self.replication_events],
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, JsonValue]) -> DemeState:
        return cls(
            demes=tuple(
                Deme.from_dict(item)
                for item in data.get("demes", [])
                if isinstance(item, Mapping)
            ) if isinstance(data.get("demes", []), list) else (),
            inbox=tuple(
                DemeMessage.from_dict(item)
                for item in data.get("inbox", [])
                if isinstance(item, Mapping)
            ) if isinstance(data.get("inbox", []), list) else (),
            replication_events=tuple(
                DemeReplicationEvent.from_dict(item)
                for item in data.get("replication_events", [])
                if isinstance(item, Mapping)
            ) if isinstance(data.get("replication_events", []), list) else (),
        )

    def digest(self) -> str:
        return canonical_digest(self.to_dict())

    def members_of(self, deme_id: str) -> tuple[str, ...]:
        for deme in self.demes:
            if deme.deme_id == deme_id:
                return deme.member_ids
        return ()

    def append_message(self, message: DemeMessage, *, capacity: int = 32) -> None:
        self.inbox = tuple((*self.inbox, message)[-max(1, capacity) :])

    def latest_for_deme(self, deme_id: str) -> DemeMessage | None:
        for message in reversed(self.inbox):
            if message.deme_id == deme_id and not message.blocked:
                return message
        return None


@dataclass(frozen=True, slots=True)
class DemeConfig:
    """Opt-in deme/group substrate. Defaults off."""

    enabled: bool = False
    deme_size: int = 3
    messaging_enabled: bool = False
    inbox_capacity: int = 32
    replicate_on_mean_fitness: float | None = None
    replicate_copy_germline: bool = False
    send_on_eat: bool = True

    def __post_init__(self) -> None:
        if self.deme_size <= 0:
            raise ConfigurationError("DemeConfig.deme_size must be > 0.")
        if self.inbox_capacity <= 0:
            raise ConfigurationError("DemeConfig.inbox_capacity must be > 0.")
        if self.replicate_on_mean_fitness is not None:
            object.__setattr__(
                self,
                "replicate_on_mean_fitness",
                require_finite_float(
                    "replicate_on_mean_fitness",
                    self.replicate_on_mean_fitness,
                    non_negative=True,
                ),
            )

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "enabled": self.enabled,
            "deme_size": self.deme_size,
            "messaging_enabled": self.messaging_enabled,
            "inbox_capacity": self.inbox_capacity,
            "replicate_on_mean_fitness": self.replicate_on_mean_fitness,
            "replicate_copy_germline": self.replicate_copy_germline,
            "send_on_eat": self.send_on_eat,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, JsonValue]) -> DemeConfig:
        raw_threshold = data.get("replicate_on_mean_fitness")
        threshold = None
        if isinstance(raw_threshold, (int, float)) and not isinstance(raw_threshold, bool):
            threshold = float(raw_threshold)
        return cls(
            enabled=_bool(data, "enabled", False),
            deme_size=_int(data, "deme_size", 3),
            messaging_enabled=_bool(data, "messaging_enabled", False),
            inbox_capacity=_int(data, "inbox_capacity", 32),
            replicate_on_mean_fitness=threshold,
            replicate_copy_germline=_bool(data, "replicate_copy_germline", False),
            send_on_eat=_bool(data, "send_on_eat", True),
        )

    def digest(self) -> str:
        return canonical_digest(self.to_dict())


@dataclass(frozen=True, slots=True)
class PlasticityProtocolSpec:
    """Experimental-design object for Ghalambor/Clune-style plasticity runs.

    This is a checklist plus a sense-react hook over Phase C cues. It does
    **not** claim that phenotypic plasticity evolved.
    """

    condition: PlasticityCondition | str = PlasticityCondition.FLUCTUATING
    sensory_read_enabled: bool = True
    sense_react_enabled: bool = False
    high_food_action: str = "EAT_LUMEN"
    low_food_action: str = "WAIT"
    literature_refs: tuple[str, ...] = (
        "clune_2007",
        "lalejini_ofria_2016",
        "frontiers_2021_adaptive_phenotypic_plasticity",
        "ghalambor_clune_four_conditions",
    )
    claim_ceiling: str = _PHASE_E_CLAIM_CEILING
    schema_version: str = "plasticity_protocol_spec_v1"
    digest: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "condition", _plasticity_condition(self.condition))
        if self.claim_ceiling != _PHASE_E_CLAIM_CEILING:
            raise ConfigurationError("PlasticityProtocolSpec ceiling is runtime_observation only.")
        computed = canonical_digest(self._payload())
        if self.digest and self.digest != computed:
            raise ConfigurationError("PlasticityProtocolSpec digest mismatch.")
        object.__setattr__(self, "digest", computed)

    def _payload(self) -> dict[str, JsonValue]:
        return {
            "schema_version": self.schema_version,
            "condition": _plasticity_condition(self.condition).value,
            "sensory_read_enabled": self.sensory_read_enabled,
            "sense_react_enabled": self.sense_react_enabled,
            "high_food_action": self.high_food_action,
            "low_food_action": self.low_food_action,
            "literature_refs": list(self.literature_refs),
            "claim_ceiling": self.claim_ceiling,
            "ghalambor_clune_conditions": [
                [name, detail] for name, detail in GHALAMBOR_CLUNE_CONDITIONS
            ],
            "plasticity_evolved": False,
        }

    def to_dict(self) -> dict[str, JsonValue]:
        return {**self._payload(), "digest": self.digest}

    @classmethod
    def from_dict(cls, data: Mapping[str, JsonValue]) -> PlasticityProtocolSpec:
        return cls(
            condition=_str(data, "condition", PlasticityCondition.FLUCTUATING.value),
            sensory_read_enabled=_bool(data, "sensory_read_enabled", True),
            sense_react_enabled=_bool(data, "sense_react_enabled", False),
            high_food_action=_str(data, "high_food_action", "EAT_LUMEN"),
            low_food_action=_str(data, "low_food_action", "WAIT"),
            literature_refs=_str_tuple(
                data,
                "literature_refs",
                (
                    "clune_2007",
                    "lalejini_ofria_2016",
                    "frontiers_2021_adaptive_phenotypic_plasticity",
                    "ghalambor_clune_four_conditions",
                ),
            ),
            claim_ceiling=_str(data, "claim_ceiling", _PHASE_E_CLAIM_CEILING),
            digest=_str(data, "digest", ""),
        )

    def experimental_design_checklist(self) -> tuple[tuple[str, str], ...]:
        return GHALAMBOR_CLUNE_CONDITIONS


@dataclass(frozen=True, slots=True)
class PlasticityConfig:
    enabled: bool = False
    spec: PlasticityProtocolSpec = field(default_factory=PlasticityProtocolSpec)

    def to_dict(self) -> dict[str, JsonValue]:
        return {"enabled": self.enabled, "spec": self.spec.to_dict()}

    @classmethod
    def from_dict(cls, data: Mapping[str, JsonValue]) -> PlasticityConfig:
        spec_raw = data.get("spec")
        return cls(
            enabled=_bool(data, "enabled", False),
            spec=PlasticityProtocolSpec.from_dict(spec_raw)
            if isinstance(spec_raw, Mapping)
            else PlasticityProtocolSpec(),
        )

    def digest(self) -> str:
        return canonical_digest(self.to_dict())


@dataclass(frozen=True, slots=True)
class PhaseESubstrateConfig:
    """Master opt-in. Omitted from default ``PopulationConfigs`` serialization."""

    enabled: bool = False
    capsule_memory: CapsuleMemoryConfig = field(default_factory=CapsuleMemoryConfig)
    roles: RoleDifferentiationConfig = field(default_factory=RoleDifferentiationConfig)
    demes: DemeConfig = field(default_factory=DemeConfig)
    plasticity: PlasticityConfig = field(default_factory=PlasticityConfig)

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "enabled": self.enabled,
            "capsule_memory": self.capsule_memory.to_dict(),
            "roles": self.roles.to_dict(),
            "demes": self.demes.to_dict(),
            "plasticity": self.plasticity.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, JsonValue]) -> PhaseESubstrateConfig:
        capsule_raw = data.get("capsule_memory")
        roles_raw = data.get("roles")
        demes_raw = data.get("demes")
        plasticity_raw = data.get("plasticity")
        return cls(
            enabled=_bool(data, "enabled", False),
            capsule_memory=CapsuleMemoryConfig.from_dict(capsule_raw)
            if isinstance(capsule_raw, Mapping)
            else CapsuleMemoryConfig(),
            roles=RoleDifferentiationConfig.from_dict(roles_raw)
            if isinstance(roles_raw, Mapping)
            else RoleDifferentiationConfig(),
            demes=DemeConfig.from_dict(demes_raw)
            if isinstance(demes_raw, Mapping)
            else DemeConfig(),
            plasticity=PlasticityConfig.from_dict(plasticity_raw)
            if isinstance(plasticity_raw, Mapping)
            else PlasticityConfig(),
        )

    def digest(self) -> str:
        return canonical_digest(self.to_dict())

    @staticmethod
    def capsule_memory_preset(
        *,
        inherit_lineage: bool = False,
        seed_preferred_action: str = "EAT_LUMEN",
        atp_bonus: float = 0.5,
    ) -> PhaseESubstrateConfig:
        return PhaseESubstrateConfig(
            enabled=True,
            capsule_memory=CapsuleMemoryConfig(
                enabled=True,
                inherit_lineage=inherit_lineage,
                seed_preferred_action=seed_preferred_action,
                atp_bonus=atp_bonus,
            ),
        )

    @staticmethod
    def deme_messaging_preset(*, deme_size: int = 2, replicate_on_mean_fitness: float | None = None) -> PhaseESubstrateConfig:
        return PhaseESubstrateConfig(
            enabled=True,
            capsule_memory=CapsuleMemoryConfig(enabled=True, seed_preferred_action=""),
            roles=RoleDifferentiationConfig(
                enabled=True,
                assignment="round_robin",
                gate_reproduction=True,
                gate_messaging=True,
            ),
            demes=DemeConfig(
                enabled=True,
                deme_size=deme_size,
                messaging_enabled=True,
                replicate_on_mean_fitness=replicate_on_mean_fitness,
                replicate_copy_germline=replicate_on_mean_fitness is not None,
            ),
        )


@dataclass(slots=True)
class PhaseEOrganismState:
    """Per-organism Phase E runtime state. Absent (None) on default organisms."""

    enabled: bool = True
    organism_id: str = ""
    capsule: CapsuleMemoryState = field(default_factory=CapsuleMemoryState)
    role: DifferentiationRole = field(default_factory=DifferentiationRole)
    deme_id: str | None = None
    sensory: SensoryCue = field(default_factory=SensoryCue)
    inherit_capsule: bool = False
    gate_reproduction: bool = False
    gate_messaging: bool = False
    effect_action_choice: bool = True
    effect_atp: bool = True
    effect_task_eligibility: bool = True
    atp_bonus: float = 0.5
    substitutable_actions: tuple[str, ...] = ("WAIT",)
    write_actions: tuple[str, ...] = ("EAT_LUMEN",)
    slot_capacity: int = 4
    plasticity_sense_react: bool = False
    high_food_action: str = "EAT_LUMEN"
    low_food_action: str = "WAIT"

    def to_dict(self) -> dict[str, JsonValue]:
        payload: dict[str, JsonValue] = {
            "enabled": self.enabled,
            "organism_id": self.organism_id,
            "capsule": self.capsule.to_dict(),
            "role": self.role.to_dict(),
            "sensory": self.sensory.to_dict(),
            "inherit_capsule": self.inherit_capsule,
            "gate_reproduction": self.gate_reproduction,
            "gate_messaging": self.gate_messaging,
            "effect_action_choice": self.effect_action_choice,
            "effect_atp": self.effect_atp,
            "effect_task_eligibility": self.effect_task_eligibility,
            "atp_bonus": self.atp_bonus,
            "substitutable_actions": list(self.substitutable_actions),
            "write_actions": list(self.write_actions),
            "slot_capacity": self.slot_capacity,
            "plasticity_sense_react": self.plasticity_sense_react,
            "high_food_action": self.high_food_action,
            "low_food_action": self.low_food_action,
        }
        if self.deme_id is not None:
            payload["deme_id"] = self.deme_id
        return payload

    @classmethod
    def from_dict(cls, data: Mapping[str, JsonValue]) -> PhaseEOrganismState:
        capsule_raw = data.get("capsule")
        role_raw = data.get("role")
        sensory_raw = data.get("sensory")
        deme_raw = data.get("deme_id")
        return cls(
            enabled=_bool(data, "enabled", True),
            organism_id=_str(data, "organism_id", ""),
            capsule=CapsuleMemoryState.from_dict(capsule_raw)
            if isinstance(capsule_raw, Mapping)
            else CapsuleMemoryState(),
            role=DifferentiationRole.from_dict(role_raw)
            if isinstance(role_raw, Mapping)
            else DifferentiationRole(),
            deme_id=None if deme_raw is None else str(deme_raw),
            sensory=SensoryCue.from_dict(sensory_raw)
            if isinstance(sensory_raw, Mapping)
            else SensoryCue(),
            inherit_capsule=_bool(data, "inherit_capsule", False),
            gate_reproduction=_bool(data, "gate_reproduction", False),
            gate_messaging=_bool(data, "gate_messaging", False),
            effect_action_choice=_bool(data, "effect_action_choice", True),
            effect_atp=_bool(data, "effect_atp", True),
            effect_task_eligibility=_bool(data, "effect_task_eligibility", True),
            atp_bonus=_float(data, "atp_bonus", 0.5),
            substitutable_actions=_str_tuple(data, "substitutable_actions", ("WAIT",)),
            write_actions=_str_tuple(data, "write_actions", ("EAT_LUMEN",)),
            slot_capacity=_int(data, "slot_capacity", 4),
            plasticity_sense_react=_bool(data, "plasticity_sense_react", False),
            high_food_action=_str(data, "high_food_action", "EAT_LUMEN"),
            low_food_action=_str(data, "low_food_action", "WAIT"),
        )

    def digest(self) -> str:
        return canonical_digest(self.to_dict())


def copy_phase_e_state(state: PhaseEOrganismState | None) -> PhaseEOrganismState | None:
    if state is None:
        return None
    return PhaseEOrganismState.from_dict(state.to_dict())


def inherit_phase_e_state(
    parent_state: PhaseEOrganismState | None,
    *,
    child_id: str,
) -> PhaseEOrganismState | None:
    if parent_state is None:
        return None
    child = copy_phase_e_state(parent_state)
    if child is None:
        return None
    child.organism_id = child_id
    if not parent_state.inherit_capsule:
        child.capsule = CapsuleMemoryState(enabled=parent_state.capsule.enabled)
    # Digital germline: germline parents produce germline offspring.
    if _role_kind(parent_state.role.kind) is RoleKind.GERMLINE:
        child.role = role_for_kind(RoleKind.GERMLINE)
    return child


def assign_role(
    config: RoleDifferentiationConfig,
    *,
    index: int,
    genome_bits: str,
) -> DifferentiationRole:
    if not config.enabled:
        return DifferentiationRole()
    if config.assignment == "unassigned":
        return DifferentiationRole()
    if config.assignment == "explicit" and config.explicit_roles:
        kind = config.explicit_roles[index % len(config.explicit_roles)]
        return role_for_kind(kind)
    if config.assignment == "genome_prefix":
        prefix = genome_bits[:3] if genome_bits else ""
        if prefix == "111":
            return role_for_kind(RoleKind.GERMLINE)
        if prefix == "101":
            return role_for_kind(RoleKind.FORAGER)
        if prefix == "110":
            return role_for_kind(RoleKind.MESSENGER)
        return role_for_kind(RoleKind.SOMA)
    cycle = (RoleKind.GERMLINE, RoleKind.SOMA, RoleKind.MESSENGER)
    return role_for_kind(cycle[index % len(cycle)])


def build_phase_e_organism_state(
    config: PhaseESubstrateConfig,
    *,
    organism_id: str,
    index: int,
    genome_bits: str,
) -> PhaseEOrganismState | None:
    if not config.enabled:
        return None
    capsule = CapsuleMemoryState(enabled=config.capsule_memory.enabled)
    if config.capsule_memory.enabled and config.capsule_memory.seed_preferred_action:
        capsule.write_slot(
            CapsuleSlot(
                cue_regime="",
                cue_has_local_food=config.capsule_memory.seed_requires_local_food,
                preferred_action=config.capsule_memory.seed_preferred_action,
                written_tick=0,
                source="seed",
            ),
            capacity=config.capsule_memory.slot_capacity,
        )
    deme_id = None
    if config.demes.enabled:
        deme_id = f"deme-{index // config.demes.deme_size}"
    plasticity = config.plasticity
    return PhaseEOrganismState(
        enabled=True,
        organism_id=organism_id,
        capsule=capsule,
        role=assign_role(config.roles, index=index, genome_bits=genome_bits),
        deme_id=deme_id,
        inherit_capsule=config.capsule_memory.inherit_lineage,
        gate_reproduction=config.roles.enabled and config.roles.gate_reproduction,
        gate_messaging=config.roles.enabled and config.roles.gate_messaging,
        effect_action_choice=config.capsule_memory.effect_action_choice,
        effect_atp=config.capsule_memory.effect_atp,
        effect_task_eligibility=config.capsule_memory.effect_task_eligibility,
        atp_bonus=config.capsule_memory.atp_bonus,
        substitutable_actions=config.capsule_memory.substitutable_actions,
        write_actions=config.capsule_memory.write_actions,
        slot_capacity=config.capsule_memory.slot_capacity,
        plasticity_sense_react=plasticity.enabled and plasticity.spec.sense_react_enabled,
        high_food_action=plasticity.spec.high_food_action,
        low_food_action=plasticity.spec.low_food_action,
    )


def attach_phase_e_to_organisms(
    organisms: Sequence[Any],
    config: PhaseESubstrateConfig,
) -> tuple[Any, ...]:
    if not config.enabled:
        return tuple(organisms)
    attached = []
    for index, organism in enumerate(organisms):
        if getattr(organism, "phase_e_state", None) is None:
            bits = ""
            genome = getattr(organism, "genome", None)
            if genome is not None and hasattr(genome, "to_compact"):
                bits = str(genome.to_compact())
            organism.phase_e_state = build_phase_e_organism_state(
                config,
                organism_id=str(getattr(organism, "id", f"org-{index}")),
                index=index,
                genome_bits=bits,
            )
        attached.append(organism)
    return tuple(attached)


def build_deme_state(organisms: Sequence[Any]) -> DemeState:
    groups: dict[str, list[str]] = {}
    for organism in organisms:
        state = getattr(organism, "phase_e_state", None)
        deme_id = None if state is None else state.deme_id
        if not deme_id:
            continue
        groups.setdefault(str(deme_id), []).append(str(organism.id))
    demes = tuple(
        Deme(deme_id=deme_id, member_ids=tuple(member_ids), generation=0)
        for deme_id, member_ids in sorted(groups.items())
    )
    return DemeState(demes=demes)


def refresh_phase_e_sensory(
    organism: Any,
    *,
    world: object | None,
    environment: object | None,
    tick: int,
) -> SensoryCue | None:
    state = getattr(organism, "phase_e_state", None)
    if state is None or not state.enabled:
        return None
    cue = read_environment_cue(
        tick=tick,
        position=tuple(getattr(organism, "position", (0, 0))),
        world=world,
        environment=environment,
    )
    state.sensory = cue
    return cue


def apply_phase_e_action_choice(
    organism: Any,
    action_name: str,
    *,
    world: object | None = None,
) -> tuple[str, dict[str, JsonValue]]:
    """Change subsequent action choice / ATP / task eligibility when enabled.

    Default organisms have ``phase_e_state is None`` and this is a no-op, so
    Phase A–D traces stay byte-stable.
    """

    state: PhaseEOrganismState | None = getattr(organism, "phase_e_state", None)
    if state is None or not state.enabled:
        return action_name, {}
    original = action_name
    delta: dict[str, JsonValue] = {
        "phase_e_applied": True,
        "phase_e_from_action": original,
    }
    cue = state.sensory
    if world is not None and cue.source == "unspecified":
        cue = read_environment_cue(
            tick=cue.tick,
            position=tuple(getattr(organism, "position", (0, 0))),
            world=world,
        )
        state.sensory = cue

    if state.effect_task_eligibility and state.gate_reproduction:
        if action_name == "COPY_SELF" and not state.role.propagule_eligible:
            action_name = "WAIT"
            delta["phase_e_task_gate"] = "copy_self_not_propagule_eligible"

    if state.plasticity_sense_react:
        regime = cue.regime_name
        if regime == "high_food" and action_name in state.substitutable_actions:
            action_name = state.high_food_action
            delta["phase_e_plasticity_bias"] = "high_food_sense_react"
        elif regime == "low_food" and action_name == state.high_food_action:
            action_name = state.low_food_action
            delta["phase_e_plasticity_bias"] = "low_food_sense_react"

    slot = None
    if state.capsule.enabled:
        slot = state.capsule.matching_slot(cue)
        if slot is not None:
            state.capsule.read_count += 1
            delta["phase_e_capsule_read"] = True
            delta["phase_e_capsule_slot_digest"] = slot.digest()
            if state.effect_action_choice and original in state.substitutable_actions:
                action_name = slot.preferred_action
                state.capsule.substitutions += 1
                delta["phase_e_action_bias"] = True
            if state.effect_atp and state.atp_bonus > 0:
                atp_state = getattr(organism, "atp_state", None)
                credit = getattr(atp_state, "credit_runtime", None)
                if callable(credit):
                    credit(
                        state.atp_bonus,
                        tick=int(getattr(cue, "tick", 0) or 0),
                        organism_id=str(getattr(organism, "id", state.organism_id)),
                        codon="000",
                        action="PHASE_E_CAPSULE_ATP",
                        reason="capsule_memory_atp_bonus",
                    )
                    state.capsule.atp_bonus_applied = round(
                        state.capsule.atp_bonus_applied + state.atp_bonus, 10
                    )
                    delta["phase_e_atp_bonus"] = state.atp_bonus

    if action_name != original:
        delta["phase_e_to_action"] = action_name
        delta["phase_e_action_changed"] = True
    else:
        delta["phase_e_to_action"] = action_name
        delta["phase_e_action_changed"] = False
    return action_name, delta


def record_phase_e_after_event(organism: Any, event: object) -> None:
    """Write a capsule slot after a successful write-action (associative memory)."""

    state: PhaseEOrganismState | None = getattr(organism, "phase_e_state", None)
    if state is None or not state.enabled or not state.capsule.enabled:
        return
    action = str(getattr(event, "action", "") or "")
    status = str(getattr(event, "status", "") or "")
    if action not in state.write_actions:
        return
    if status not in {"executed", "success"}:
        return
    cue = state.sensory
    state.capsule.write_slot(
        CapsuleSlot(
            cue_regime=cue.regime_name,
            cue_has_local_food=cue.has_local_food or action == "EAT_LUMEN",
            preferred_action=action,
            written_tick=int(getattr(event, "step", cue.tick) or 0),
            source="self",
        ),
        capacity=state.slot_capacity,
    )


def send_message(
    state: DemeState,
    *,
    tick: int,
    sender_id: str,
    deme_id: str,
    payload: str,
    kind: MessageKind | str = MessageKind.SEND,
    recipient_ids: Sequence[str] = (),
    can_message: bool = True,
    can_forward: bool = True,
    inbox_capacity: int = 32,
) -> DemeMessage:
    resolved = _message_kind(kind)
    if resolved is MessageKind.BLOCK_PROPAGATION or not can_forward and resolved is MessageKind.BROADCAST:
        message = DemeMessage(
            tick=tick,
            deme_id=deme_id,
            sender_id=sender_id,
            kind=resolved,
            payload=payload,
            recipient_ids=tuple(recipient_ids),
            blocked=True,
            blocked_reason="block_propagation" if resolved is MessageKind.BLOCK_PROPAGATION else "cannot_forward",
        )
        state.append_message(message, capacity=inbox_capacity)
        return message
    if not can_message:
        message = DemeMessage(
            tick=tick,
            deme_id=deme_id,
            sender_id=sender_id,
            kind=resolved,
            payload=payload,
            recipient_ids=tuple(recipient_ids),
            blocked=True,
            blocked_reason="role_cannot_message",
        )
        state.append_message(message, capacity=inbox_capacity)
        return message
    targets = tuple(recipient_ids) if recipient_ids else (
        state.members_of(deme_id) if resolved is MessageKind.BROADCAST else ()
    )
    message = DemeMessage(
        tick=tick,
        deme_id=deme_id,
        sender_id=sender_id,
        kind=resolved,
        payload=payload,
        recipient_ids=targets,
        blocked=False,
    )
    state.append_message(message, capacity=inbox_capacity)
    return message


def retrieve_message(state: DemeState, *, deme_id: str) -> DemeMessage | None:
    return state.latest_for_deme(deme_id)


def apply_deme_messaging_after_event(
    organism: Any,
    event: object,
    deme_state: DemeState,
    config: DemeConfig,
    *,
    tick: int,
) -> tuple[DemeMessage, ...] | tuple[()]:
    if not config.enabled or not config.messaging_enabled:
        return ()
    state: PhaseEOrganismState | None = getattr(organism, "phase_e_state", None)
    if state is None or not state.deme_id:
        return ()
    can_message = state.role.can_message if state.gate_messaging else True
    can_forward = state.role.can_forward if state.gate_messaging else True
    recorded: list[DemeMessage] = []
    action = str(getattr(event, "action", "") or "")
    status = str(getattr(event, "status", "") or "")
    if (
        config.send_on_eat
        and action == "EAT_LUMEN"
        and status in {"executed", "success"}
    ):
        recorded.append(
            send_message(
                deme_state,
                tick=tick,
                sender_id=str(getattr(organism, "id", "")),
                deme_id=state.deme_id,
                payload="EAT_SUCCESS",
                kind=MessageKind.BROADCAST if can_forward else MessageKind.SEND,
                recipient_ids=deme_state.members_of(state.deme_id),
                can_message=can_message,
                can_forward=can_forward,
                inbox_capacity=config.inbox_capacity,
            )
        )
    retrieved = retrieve_message(deme_state, deme_id=state.deme_id)
    if retrieved is not None and retrieved.sender_id != str(getattr(organism, "id", "")):
        if state.capsule.enabled and retrieved.payload == "EAT_SUCCESS":
            state.capsule.write_slot(
                CapsuleSlot(
                    cue_regime=state.sensory.regime_name,
                    cue_has_local_food=True,
                    preferred_action="EAT_LUMEN",
                    written_tick=tick,
                    source="message",
                ),
                capacity=state.slot_capacity,
            )
        recorded.append(
            DemeMessage(
                tick=tick,
                deme_id=state.deme_id,
                sender_id=retrieved.sender_id,
                kind=MessageKind.RETRIEVE,
                payload=retrieved.payload,
                recipient_ids=(str(getattr(organism, "id", "")),),
            )
        )
    return tuple(recorded)


def maybe_replicate_demes(
    deme_state: DemeState,
    organisms: Sequence[Any],
    fitness_by_id: Mapping[str, float],
    config: DemeConfig,
    *,
    tick: int,
) -> tuple[DemeState, tuple[DemeReplicationEvent, ...]]:
    """Minimal real deme-replication trigger. Records events; optional germline copy is caller-owned."""

    if not config.enabled or config.replicate_on_mean_fitness is None:
        return deme_state, ()
    threshold = config.replicate_on_mean_fitness
    events: list[DemeReplicationEvent] = []
    updated: list[Deme] = []
    next_index = len(deme_state.demes)
    for deme in deme_state.demes:
        scores = [fitness_by_id.get(member_id, 0.0) for member_id in deme.member_ids]
        mean = round(sum(scores) / len(scores), 10) if scores else 0.0
        if mean >= threshold:
            germline_id = ""
            for member_id in deme.member_ids:
                organism = next((item for item in organisms if item.id == member_id), None)
                role = getattr(getattr(organism, "phase_e_state", None), "role", None)
                if role is not None and role.propagule_eligible:
                    germline_id = member_id
                    break
            if not germline_id and deme.member_ids:
                germline_id = max(deme.member_ids, key=lambda item: fitness_by_id.get(item, 0.0))
            target_id = f"deme-{next_index}"
            next_index += 1
            events.append(
                DemeReplicationEvent(
                    tick=tick,
                    source_deme_id=deme.deme_id,
                    target_deme_id=target_id,
                    mean_fitness=mean,
                    germline_parent_id=germline_id,
                    trigger="mean_fitness_threshold",
                )
            )
            updated.append(replace(deme, generation=deme.generation + 1))
        else:
            updated.append(deme)
    if not events:
        return deme_state, ()
    deme_state.demes = tuple(updated)
    deme_state.replication_events = tuple((*deme_state.replication_events, *events))
    return deme_state, tuple(events)


@dataclass(frozen=True, slots=True)
class PhaseERuntimeEvent:
    """Generation-level Phase E audit event. Omitted from default generation payloads."""

    tick: int
    organism_id: str
    kind: str
    detail: str
    digest_ref: str = ""

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "tick": self.tick,
            "organism_id": self.organism_id,
            "kind": self.kind,
            "detail": self.detail,
            "digest_ref": self.digest_ref,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, JsonValue]) -> PhaseERuntimeEvent:
        return cls(
            tick=_int(data, "tick", 0),
            organism_id=_str(data, "organism_id", ""),
            kind=_str(data, "kind"),
            detail=_str(data, "detail", ""),
            digest_ref=_str(data, "digest_ref", ""),
        )

    def digest(self) -> str:
        return canonical_digest(self.to_dict())


@dataclass(frozen=True, slots=True)
class PhenotypeTranscriptomeEvidence:
    """OntoAvida / avidaR-inspired exportable phenotype/transcriptome-ish object."""

    organism_id: str
    tick: int
    generation: int
    genome_bits: str
    action_counts: tuple[tuple[str, int], ...]
    runtime_atp: float
    role_kind: str
    capsule_digest: str
    sensory_regime: str
    deme_id: str | None
    message_count: int
    claim_ceiling: str = _PHASE_E_CLAIM_CEILING
    schema_version: str = "phenotype_transcriptome_evidence_v1"
    digest: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "runtime_atp",
            round(require_finite_float("runtime_atp", self.runtime_atp, non_negative=True), 10),
        )
        computed = canonical_digest(self._payload())
        if self.digest and self.digest != computed:
            raise ConfigurationError("PhenotypeTranscriptomeEvidence digest mismatch.")
        object.__setattr__(self, "digest", computed)

    def _payload(self) -> dict[str, JsonValue]:
        return {
            "schema_version": self.schema_version,
            "organism_id": self.organism_id,
            "tick": self.tick,
            "generation": self.generation,
            "genome_bits": self.genome_bits,
            "action_counts": [[name, count] for name, count in self.action_counts],
            "runtime_atp": self.runtime_atp,
            "role_kind": self.role_kind,
            "capsule_digest": self.capsule_digest,
            "sensory_regime": self.sensory_regime,
            "deme_id": self.deme_id,
            "message_count": self.message_count,
            "claim_ceiling": self.claim_ceiling,
        }

    def to_dict(self) -> dict[str, JsonValue]:
        return {**self._payload(), "digest": self.digest}


@dataclass(frozen=True, slots=True)
class AvidaParityProtocolSpec:
    """Software-capability recipe for comparable CodonTrace vs Avida-style runs.

    Not a superiority claim and not a bit-identical Avida clone.
    """

    include_life_loop: bool = True
    include_sexual: bool = False
    include_dynamic_environment: bool = False
    include_multi_generation_evidence: bool = True
    include_capsule_memory: bool = True
    include_deme_messaging: bool = False
    seed: int = 7
    tick_count: int = 12
    population: int = 6
    notes: str = (
        "Run GenesisRuntimeProfile.life_loop_world for the Darwinian loop; "
        "opt into SEXUAL_CROSSOVER, dynamic_environment_world, "
        "build_multi_generation_evidence_pack, and phase_e_substrate_world "
        "for capsule/role/deme effects. Compare recorded JSON+digest objects, "
        "not undocumented analyze-mode dumps. Not an Avida replacement."
    )
    claim_ceiling: str = _PHASE_E_CLAIM_CEILING
    schema_version: str = "avida_parity_protocol_spec_v1"
    digest: str = ""

    def __post_init__(self) -> None:
        if self.claim_ceiling != _PHASE_E_CLAIM_CEILING:
            raise ConfigurationError("AvidaParityProtocolSpec ceiling is runtime_observation only.")
        computed = canonical_digest(self._payload())
        if self.digest and self.digest != computed:
            raise ConfigurationError("AvidaParityProtocolSpec digest mismatch.")
        object.__setattr__(self, "digest", computed)

    def _payload(self) -> dict[str, JsonValue]:
        return {
            "schema_version": self.schema_version,
            "include_life_loop": self.include_life_loop,
            "include_sexual": self.include_sexual,
            "include_dynamic_environment": self.include_dynamic_environment,
            "include_multi_generation_evidence": self.include_multi_generation_evidence,
            "include_capsule_memory": self.include_capsule_memory,
            "include_deme_messaging": self.include_deme_messaging,
            "seed": self.seed,
            "tick_count": self.tick_count,
            "population": self.population,
            "notes": self.notes,
            "claim_ceiling": self.claim_ceiling,
            "superiority_claimed": False,
            "avida_replacement": False,
        }

    def to_dict(self) -> dict[str, JsonValue]:
        return {**self._payload(), "digest": self.digest}

    @classmethod
    def comparable_default(cls, **kwargs: Any) -> AvidaParityProtocolSpec:
        return cls(**kwargs)


@dataclass(frozen=True, slots=True)
class PhaseEObservation:
    """Runtime observation of one Phase E enabled run. Not a collective-intelligence claim."""

    capsule_substitutions: int
    capsule_writes: int
    capsule_reads: int
    atp_bonus_total: float
    role_gated_reproduction_blocks: int
    messages_sent: int
    messages_retrieved: int
    messages_blocked: int
    deme_replications: int
    sensory_reads: int
    replay_digest: str
    claim_ceiling: str = _PHASE_E_CLAIM_CEILING
    collective_intelligence_proved: bool = False
    plasticity_evolved: bool = False

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "capsule_substitutions": self.capsule_substitutions,
            "capsule_writes": self.capsule_writes,
            "capsule_reads": self.capsule_reads,
            "atp_bonus_total": self.atp_bonus_total,
            "role_gated_reproduction_blocks": self.role_gated_reproduction_blocks,
            "messages_sent": self.messages_sent,
            "messages_retrieved": self.messages_retrieved,
            "messages_blocked": self.messages_blocked,
            "deme_replications": self.deme_replications,
            "sensory_reads": self.sensory_reads,
            "replay_digest": self.replay_digest,
            "claim_ceiling": self.claim_ceiling,
            "collective_intelligence_proved": self.collective_intelligence_proved,
            "plasticity_evolved": self.plasticity_evolved,
        }

    def digest(self) -> str:
        return canonical_digest(self.to_dict())


def summarize_phase_e_observation(result: object) -> PhaseEObservation:
    if result is None:
        raise TypeError("summarize_phase_e_observation requires a run result, not None.")
    if not hasattr(result, "ticks"):
        raise TypeError("summarize_phase_e_observation expected an object with a ticks collection.")
    substitutions = 0
    writes = 0
    reads = 0
    atp_bonus = 0.0
    sensory_reads = 0
    gated_blocks = 0
    last_pop = None
    ticks = getattr(result, "ticks")
    messages_sent = 0
    messages_retrieved = 0
    messages_blocked = 0
    deme_replications = 0
    last_capsule: dict[str, tuple[int, int, int, float, bool]] = {}
    for tick in ticks:
        generation = getattr(tick, "generation_result", None)
        if generation is None:
            continue
        last_pop = getattr(generation, "population", last_pop)
        for organism in getattr(last_pop, "organisms", ()) or ():
            state = getattr(organism, "phase_e_state", None)
            if state is None:
                continue
            last_capsule[str(organism.id)] = (
                int(state.capsule.substitutions),
                int(state.capsule.write_count),
                int(state.capsule.read_count),
                float(state.capsule.atp_bonus_applied),
                state.sensory.source != "unspecified",
            )
        for message in getattr(generation, "phase_e_messages", ()) or ():
            kind = getattr(message, "kind", None)
            kind_value = kind.value if hasattr(kind, "value") else str(kind)
            if getattr(message, "blocked", False):
                messages_blocked += 1
            elif kind_value == MessageKind.RETRIEVE.value:
                messages_retrieved += 1
            else:
                messages_sent += 1
        deme_state = getattr(generation, "deme_state", None)
        if deme_state is not None:
            deme_replications = max(
                deme_replications, len(getattr(deme_state, "replication_events", ()) or ())
            )
        for record in getattr(generation, "organism_records", ()):
            repro = getattr(record, "reproduction_result", None)
            decision = getattr(repro, "decision", None) if repro is not None else None
            reasons = getattr(decision, "reasons", ()) if decision is not None else ()
            if "not_propagule_eligible" in reasons:
                gated_blocks += 1
    for subs, write_count, read_count, bonus, sensed in last_capsule.values():
        substitutions += subs
        writes += write_count
        reads += read_count
        atp_bonus += bonus
        if sensed:
            sensory_reads += 1
    replay = ""
    digest_fn = getattr(result, "digest", None)
    if callable(digest_fn):
        replay = str(digest_fn())
    return PhaseEObservation(
        capsule_substitutions=substitutions,
        capsule_writes=writes,
        capsule_reads=reads,
        atp_bonus_total=round(atp_bonus, 10),
        role_gated_reproduction_blocks=gated_blocks,
        messages_sent=messages_sent,
        messages_retrieved=messages_retrieved,
        messages_blocked=messages_blocked,
        deme_replications=deme_replications,
        sensory_reads=sensory_reads,
        replay_digest=replay,
    )


def export_phenotype_transcriptome(
    result: object,
    *,
    generation_index: int = -1,
) -> tuple[PhenotypeTranscriptomeEvidence, ...]:
    ticks = tuple(getattr(result, "ticks", ()) or ())
    if not ticks:
        return ()
    tick = ticks[generation_index]
    generation_result = getattr(tick, "generation_result", None)
    if generation_result is None:
        return ()
    population = getattr(generation_result, "population", None)
    organisms = getattr(population, "organisms", ()) if population is not None else ()
    traces_by_id: dict[str, object] = {}
    for trace in getattr(generation_result, "traces", ()) or ():
        events = getattr(trace, "events", ())
        if events:
            agent_id = str(getattr(events[0], "agent_id", "") or "")
            if agent_id:
                traces_by_id[agent_id] = trace
    messages = tuple(getattr(generation_result, "phase_e_messages", ()) or ())
    generation_no = int(getattr(population, "generation", 0) or 0) if population is not None else 0
    tick_no = int(getattr(population, "tick", 0) or 0) if population is not None else 0
    rows: list[PhenotypeTranscriptomeEvidence] = []
    for organism in organisms:
        counts: dict[str, int] = {}
        trace = traces_by_id.get(str(organism.id))
        for event in getattr(trace, "events", ()) or ():
            action = str(getattr(event, "action", "") or "")
            counts[action] = counts.get(action, 0) + 1
        state = getattr(organism, "phase_e_state", None)
        role_kind = RoleKind.UNASSIGNED.value
        capsule_digest = ""
        regime = ""
        deme_id = None
        if state is not None:
            role_kind = _role_kind(state.role.kind).value
            capsule_digest = state.capsule.digest()
            regime = state.sensory.regime_name
            deme_id = state.deme_id
        message_count = sum(
            1
            for message in messages
            if str(getattr(message, "sender_id", "")) == str(organism.id)
            or str(organism.id) in tuple(getattr(message, "recipient_ids", ()) or ())
        )
        genome_bits = ""
        genome = getattr(organism, "genome", None)
        if genome is not None and hasattr(genome, "to_compact"):
            genome_bits = str(genome.to_compact())
        rows.append(
            PhenotypeTranscriptomeEvidence(
                organism_id=str(organism.id),
                tick=tick_no,
                generation=generation_no,
                genome_bits=genome_bits,
                action_counts=tuple(sorted(counts.items())),
                runtime_atp=float(organism.atp_state.runtime_available),
                role_kind=role_kind,
                capsule_digest=capsule_digest,
                sensory_regime=regime,
                deme_id=deme_id,
                message_count=message_count,
            )
        )
    return tuple(rows)


@dataclass(frozen=True, slots=True)
class PhaseEEvidencePack:
    """First-class JSON+digest export for Phase E runtime observations."""

    observation: PhaseEObservation
    transcriptome: tuple[PhenotypeTranscriptomeEvidence, ...]
    protocol: AvidaParityProtocolSpec
    plasticity: PlasticityProtocolSpec
    literature_checklist: tuple[tuple[str, str], ...] = LITERATURE_CHECKLIST
    run_digest: str = ""
    claim_ceiling: str = _PHASE_E_CLAIM_CEILING
    schema_version: str = _PACK_SCHEMA
    digest: str = ""

    def __post_init__(self) -> None:
        if self.claim_ceiling != _PHASE_E_CLAIM_CEILING:
            raise ConfigurationError("PhaseEEvidencePack ceiling is runtime_observation only.")
        if self.claim_ceiling in _FORBIDDEN_PACK_CLAIMS:
            raise ConfigurationError("PhaseEEvidencePack must never claim collective intelligence.")
        computed = canonical_digest(self._payload())
        if self.digest and self.digest != computed:
            raise ConfigurationError("PhaseEEvidencePack digest mismatch.")
        object.__setattr__(self, "digest", computed)

    def _payload(self) -> dict[str, JsonValue]:
        return {
            "schema_version": self.schema_version,
            "observation": self.observation.to_dict(),
            "transcriptome": [item.to_dict() for item in self.transcriptome],
            "protocol": self.protocol.to_dict(),
            "plasticity": self.plasticity.to_dict(),
            "literature_checklist": [[name, detail] for name, detail in self.literature_checklist],
            "run_digest": self.run_digest,
            "claim_ceiling": self.claim_ceiling,
            "collective_intelligence_proved": False,
            "plasticity_evolved": False,
            "avida_replacement": False,
        }

    def to_dict(self) -> dict[str, JsonValue]:
        return {**self._payload(), "digest": self.digest}

    def to_json(self) -> str:
        from codontrace._numeric import finite_json_dumps

        return finite_json_dumps(self.to_dict(), sort_keys=True, separators=(",", ":"))


def build_phase_e_evidence_pack(
    result: object,
    *,
    protocol: AvidaParityProtocolSpec | None = None,
    plasticity: PlasticityProtocolSpec | None = None,
) -> PhaseEEvidencePack:
    observation = summarize_phase_e_observation(result)
    run_digest = ""
    digest_fn = getattr(result, "digest", None)
    if callable(digest_fn):
        run_digest = str(digest_fn())
    return PhaseEEvidencePack(
        observation=observation,
        transcriptome=export_phenotype_transcriptome(result),
        protocol=protocol or AvidaParityProtocolSpec(),
        plasticity=plasticity or PlasticityProtocolSpec(),
        run_digest=run_digest,
    )


def evaluate_phase_e_claim(pack: PhaseEEvidencePack) -> ClaimDecision:
    """Always ceiling ``runtime_observation``. Collective intelligence stays blocked."""

    gate = ScientificClaimGate()
    blocked = gate.decide(ClaimRequest("collective_intelligence", {}))
    if blocked.allowed:
        raise ConfigurationError("ClaimGate must not allow collective_intelligence.")
    return gate.decide(
        ClaimRequest(
            "runtime_observation",
            {
                "capsule_or_role_or_deme_records": (
                    pack.observation.capsule_substitutions > 0
                    or pack.observation.messages_sent > 0
                    or pack.observation.role_gated_reproduction_blocks > 0
                )
            },
            manifest_digest=pack.digest,
            evidence_digests=(pack.digest, pack.run_digest) if pack.run_digest else (pack.digest,),
        )
    )


def _role_kind(value: RoleKind | str) -> RoleKind:
    if isinstance(value, RoleKind):
        return value
    try:
        return RoleKind(str(value))
    except ValueError as exc:
        raise ConfigurationError(f"Unknown RoleKind: {value!r}") from exc


def _message_kind(value: MessageKind | str) -> MessageKind:
    if isinstance(value, MessageKind):
        return value
    try:
        return MessageKind(str(value))
    except ValueError as exc:
        raise ConfigurationError(f"Unknown MessageKind: {value!r}") from exc


def _plasticity_condition(value: PlasticityCondition | str) -> PlasticityCondition:
    if isinstance(value, PlasticityCondition):
        return value
    try:
        return PlasticityCondition(str(value))
    except ValueError as exc:
        raise ConfigurationError(f"Unknown PlasticityCondition: {value!r}") from exc


def _str(data: Mapping[str, JsonValue], key: str, default: str | None = None) -> str:
    value = data.get(key, default)
    if value is None and default is not None:
        return default
    if not isinstance(value, str):
        raise ConfigurationError(f"{key} must be a string.")
    return value


def _bool(data: Mapping[str, JsonValue], key: str, default: bool) -> bool:
    value = data.get(key, default)
    if not isinstance(value, bool):
        raise ConfigurationError(f"{key} must be a boolean.")
    return value


def _int(data: Mapping[str, JsonValue], key: str, default: int) -> int:
    value = data.get(key, default)
    if isinstance(value, bool) or not isinstance(value, int):
        raise ConfigurationError(f"{key} must be an integer.")
    return value


def _float(data: Mapping[str, JsonValue], key: str, default: float) -> float:
    value = data.get(key, default)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ConfigurationError(f"{key} must be a number.")
    return float(value)


def _str_tuple(
    data: Mapping[str, JsonValue], key: str, default: tuple[str, ...]
) -> tuple[str, ...]:
    raw = data.get(key, list(default))
    if not isinstance(raw, list) or not all(isinstance(item, str) for item in raw):
        raise ConfigurationError(f"{key} must be a list of strings.")
    return tuple(str(item) for item in raw)
