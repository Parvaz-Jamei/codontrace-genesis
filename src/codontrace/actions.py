"""Extensible action handlers for codontrace."""

from __future__ import annotations

import re
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import TYPE_CHECKING, ClassVar, Protocol

from codontrace._types import JsonValue, Position
from codontrace.errors import ConfigurationError
from codontrace._numeric import finite_float

if TYPE_CHECKING:
    from codontrace.world import World2D, WorldObject


class ActionStatusRegistryProtocol(Protocol):
    """Small structural interface needed by action runtime status validation."""

    def get(self, name: str) -> object: ...

    def counts_as_executed(self, name: str) -> bool: ...

    def counts_as_blocked(self, name: str) -> bool: ...

    def counts_as_failed(self, name: str) -> bool: ...


def _default_status_registry() -> ActionStatusRegistryProtocol:
    from codontrace.genesis.status import ActionStatusRegistry

    return ActionStatusRegistry.genesis_v0()


ActionStatus = str
_CUSTOM_STATUS_RE = re.compile(r"^(custom|plugin|experimental):[a-z][a-z0-9_]*(\.[a-z0-9_]+)*$")


@dataclass(frozen=True, slots=True)
class ActionRuntimeConfig:
    """Runtime validation and semantics for action status strings.

    The default configuration preserves the original executed/blocked/failed
    contract. Supplying a custom ActionStatusRegistry lets research runtimes use
    status strings such as partially_executed or deferred while keeping unknown
    statuses rejected by default.
    """

    status_registry: ActionStatusRegistryProtocol = field(default_factory=_default_status_registry)
    open_statuses: bool = False

    def validate_status(self, status: str) -> str:
        if not isinstance(status, str) or not status:
            msg = "Action status must be a non-empty string."
            raise ConfigurationError(msg)
        if self.open_statuses:
            if status in {"executed", "blocked", "failed"} or _CUSTOM_STATUS_RE.fullmatch(status):
                return status
            msg = (
                f"Open ActionResult.status {status!r} must use a registered base status "
                "or a namespaced custom/plugin/experimental:<name> status."
            )
            raise ConfigurationError(msg)
        try:
            self.status_registry.get(status)
        except ValueError as exc:
            msg = (
                f"Unknown ActionResult.status {status!r}. Register it in "
                "ActionStatusRegistry or enable open_statuses."
            )
            raise ConfigurationError(msg) from exc
        return status

    def counts_as_executed(self, status: str) -> bool:
        return (
            self.status_registry.counts_as_executed(status)
            if not self.open_statuses
            else status == "executed"
        )

    def counts_as_blocked(self, status: str) -> bool:
        return (
            self.status_registry.counts_as_blocked(status)
            if not self.open_statuses
            else status in {"blocked", "failed"}
        )

    def counts_as_failed(self, status: str) -> bool:
        return (
            self.status_registry.counts_as_failed(status)
            if not self.open_statuses
            else status == "failed"
        )


@dataclass(frozen=True, slots=True)
class EnergyEffect:
    """Declarative ATP effect requested by a custom action handler.

    Handlers never receive the ATPAccount itself. They can only request safe,
    ledger-recorded energy effects through this value object.
    """

    credit: float = 0.0
    debit_extra: float = 0.0
    reason: str = "custom_energy_effect"

    def __post_init__(self) -> None:
        object.__setattr__(self, "credit", finite_float("EnergyEffect.credit", self.credit, non_negative=True))
        object.__setattr__(self, "debit_extra", finite_float("EnergyEffect.debit_extra", self.debit_extra, non_negative=True))
        if not self.reason:
            msg = "EnergyEffect.reason must not be empty."
            raise ConfigurationError(msg)


def apply_energy_effect_to_atp(
    *,
    energy: EnergyEffect,
    credit: Callable[..., int],
    debit: Callable[..., int | None],
    tick: int,
    entity_id: str,
    codon_bits: str,
    action_name: str,
    status: ActionStatus,
    reason: str,
    world_delta: dict[str, JsonValue],
    ledger_ids: list[int],
    insufficient_reason: str = "insufficient_atp_for_energy_effect",
) -> tuple[ActionStatus, str]:
    """Apply an ``EnergyEffect`` through caller-provided ATP ledger functions.

    The helper centralizes the safe credit/debit semantics used by both
    ``WhiteBoxAgent`` and ``GenesisOrganism`` without exposing ATP accounts to
    action handlers. ``credit`` must return a ledger id. ``debit`` must return a
    ledger id or ``None`` when the requested debit cannot be paid.
    """

    if not isinstance(energy, EnergyEffect):
        msg = "ActionResult.energy must be an EnergyEffect instance."
        raise ConfigurationError(msg)
    world_delta["energy_effect_applied"] = True
    world_delta["energy_effect_credit"] = energy.credit
    world_delta["energy_effect_debit_extra"] = energy.debit_extra
    world_delta["energy_effect_reason"] = energy.reason
    world_delta["energy_effect_blocked"] = False
    if energy.credit > 0:
        credit_id = credit(
            energy.credit,
            tick=tick,
            entity_id=entity_id,
            codon=codon_bits,
            action=action_name,
            reason=energy.reason,
        )
        ledger_ids.append(credit_id)
        world_delta["atp_credit"] = energy.credit
    if energy.debit_extra > 0:
        debit_id = debit(
            energy.debit_extra,
            tick=tick,
            entity_id=entity_id,
            codon=codon_bits,
            action=action_name,
            reason=energy.reason,
        )
        world_delta["atp_debit_extra"] = energy.debit_extra
        if debit_id is None:
            world_delta["energy_effect_blocked"] = True
            return "blocked", insufficient_reason
        ledger_ids.append(debit_id)
    return status, reason


@dataclass(frozen=True, slots=True)
class ActionResult:
    """Declarative result returned by an action handler.

    Handlers return intent/effects. The agent core remains responsible for ATP
    accounting, TraceEvent creation, and applying default world mutations.
    """

    __hash__: ClassVar[None] = None  # type: ignore[assignment]
    VALID_STATUSES: ClassVar[tuple[str, ...]] = ("executed", "blocked", "failed")

    status: ActionStatus
    reason: str
    position_after: Position | None = None
    world_delta: dict[str, JsonValue] | None = None
    energy: EnergyEffect | None = None
    status_registry: ActionStatusRegistryProtocol | None = field(
        default=None, kw_only=True, compare=False, repr=False
    )
    open_statuses: bool = field(default=False, kw_only=True, compare=False, repr=False)

    def __post_init__(self) -> None:
        if not isinstance(self.status, str) or not self.status:
            msg = "ActionResult.status must be a non-empty string."
            raise ConfigurationError(msg)
        if self.status not in self.VALID_STATUSES:
            if self.open_statuses:
                if not _CUSTOM_STATUS_RE.fullmatch(self.status):
                    msg = (
                        f"Open ActionResult.status {self.status!r} must use a "
                        "custom/plugin/experimental:<name> namespace."
                    )
                    raise ConfigurationError(msg)
            elif self.status_registry is not None:
                try:
                    self.status_registry.get(self.status)
                except ValueError as exc:
                    msg = (
                        f"Unknown ActionResult.status {self.status!r}; "
                        "register it before returning this result."
                    )
                    raise ConfigurationError(msg) from exc
            else:
                expected = ", ".join(self.VALID_STATUSES)
                msg = (
                    f"Invalid ActionResult.status {self.status!r}. Expected one of: {expected}. "
                    "For custom statuses pass status_registry=... or open_statuses=True."
                )
                raise ConfigurationError(msg)
        if not self.reason:
            msg = "ActionResult.reason must not be empty."
            raise ConfigurationError(msg)

    @classmethod
    def executed(
        cls,
        *,
        reason: str,
        position_after: Position | None = None,
        world_delta: dict[str, JsonValue] | None = None,
        energy: EnergyEffect | None = None,
    ) -> ActionResult:
        """Create a successful action result without spelling the status string."""

        return cls(
            status="executed",
            reason=reason,
            position_after=position_after,
            world_delta=world_delta,
            energy=energy,
        )

    @classmethod
    def blocked(
        cls,
        *,
        reason: str,
        position_after: Position | None = None,
        world_delta: dict[str, JsonValue] | None = None,
        energy: EnergyEffect | None = None,
    ) -> ActionResult:
        """Create a blocked action result without spelling the status string."""

        return cls(
            status="blocked",
            reason=reason,
            position_after=position_after,
            world_delta=world_delta,
            energy=energy,
        )

    @classmethod
    def failed(
        cls,
        *,
        reason: str,
        position_after: Position | None = None,
        world_delta: dict[str, JsonValue] | None = None,
        energy: EnergyEffect | None = None,
    ) -> ActionResult:
        """Create a failed action result without spelling the status string."""

        return cls(
            status="failed",
            reason=reason,
            position_after=position_after,
            world_delta=world_delta,
            energy=energy,
        )

    @classmethod
    def custom(
        cls,
        status: str,
        *,
        reason: str,
        status_registry: ActionStatusRegistryProtocol,
        position_after: Position | None = None,
        world_delta: dict[str, JsonValue] | None = None,
        energy: EnergyEffect | None = None,
    ) -> ActionResult:
        """Create an ActionResult with a registered custom status string."""

        return cls(
            status=status,
            reason=reason,
            position_after=position_after,
            world_delta=world_delta,
            energy=energy,
            status_registry=status_registry,
        )


@dataclass(frozen=True, slots=True)
class WorldView:
    """Read-only view over World2D for custom action handlers."""

    __hash__: ClassVar[None] = None  # type: ignore[assignment]

    _world: World2D = field(repr=False)

    def in_bounds(self, position: Position) -> bool:
        """Return whether ``position`` is inside the grid."""

        return self._world.in_bounds(position)

    def is_wall(self, position: Position) -> bool:
        """Return whether ``position`` contains a wall."""

        return self._world.is_wall(position)

    def resource_amount(self, position: Position) -> float:
        """Return resource ATP at ``position`` without mutating the world."""

        return self._world.resource_amount(position)

    def nearby_resource(self, position: Position) -> bool:
        """Return whether a resource exists in the Moore neighborhood."""

        return self._world.nearby_resource(position)

    def nearby_wall(self, position: Position) -> bool:
        """Return whether a wall exists in the Moore neighborhood."""

        return self._world.nearby_wall(position)

    def get_custom_cell(self, position: Position) -> str | None:
        """Return a custom cell marker, if present."""

        return self._world.get_custom_cell(position)

    def objects_at(self, position: Position) -> tuple[WorldObject, ...]:
        """Return immutable object metadata at ``position``."""

        return self._world.objects_at(position)


@dataclass(frozen=True, slots=True)
class ActionContext:
    """Frozen context object passed to action handlers.

    Prefer ``ctx.view`` for read-only world inspection. The context object itself
    is frozen, but ``ctx.world`` remains a mutable World2D for backward
    compatibility and advanced deterministic experiments. Handlers that mutate
    ``ctx.world`` directly must report the mutation in ActionResult.world_delta.
    """

    __hash__: ClassVar[None] = None  # type: ignore[assignment]

    agent_id: str
    position: Position
    codon_bits: str
    action_name: str
    step_index: int
    world: World2D
    blocked_positions: tuple[Position, ...] = ()

    @property
    def view(self) -> WorldView:
        """Return a read-only world view for safe custom handlers."""

        return WorldView(self.world)


class ActionHandler(Protocol):
    """Structural protocol for custom action handlers.

    Callables do not need to inherit from a base class. They only need to accept
    an ActionContext and return an ActionResult.
    """

    def __call__(self, ctx: ActionContext) -> ActionResult: ...


@dataclass(frozen=True, slots=True)
class ActionRegistry:
    """Immutable-style registry from action names to handlers."""

    __hash__: ClassVar[None] = None  # type: ignore[assignment]

    _handlers: Mapping[str, ActionHandler] = field(default_factory=dict, repr=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "_handlers", MappingProxyType(dict(self._handlers)))

    def get(self, name: str) -> ActionHandler | None:
        """Return a handler by action name, or None if unsupported."""

        return self._handlers.get(name)

    def names(self) -> tuple[str, ...]:
        """Return registered action names in deterministic order."""

        return tuple(sorted(self._handlers))

    def extend(self, name: str, handler: ActionHandler) -> ActionRegistry:
        """Return a new registry with an additional handler."""

        self._validate_name(name)
        if name in self._handlers:
            msg = f"Action handler {name!r} already exists. Use replace()."
            raise ConfigurationError(msg)
        return ActionRegistry({**self._handlers, name: handler})

    def replace(self, name: str, handler: ActionHandler) -> ActionRegistry:
        """Return a new registry replacing an existing handler."""

        self._validate_name(name)
        if name not in self._handlers:
            msg = f"Cannot replace unknown action handler {name!r}. Use extend()."
            raise ConfigurationError(msg)
        return ActionRegistry({**self._handlers, name: handler})

    @staticmethod
    def _validate_name(name: str) -> None:
        if re.fullmatch(r"[A-Z][A-Z0-9]*(_[A-Z0-9]+)*", name) is None:
            msg = (
                f"Invalid action name {name!r}. Use uppercase names like 'REST' or 'MOVE_EAST' "
                "with single underscores only between non-empty segments."
            )
            raise ConfigurationError(msg)


def wait_handler(ctx: ActionContext) -> ActionResult:
    """Default WAIT handler."""

    return ActionResult.executed(
        reason="waited",
        position_after=ctx.position,
        world_delta={"effect": "waited"},
    )


def sense_resource_handler(ctx: ActionContext) -> ActionResult:
    """Default SENSE_RESOURCE handler."""

    return ActionResult.executed(
        reason="sensed_resource",
        position_after=ctx.position,
        world_delta={"nearby_resource": ctx.view.nearby_resource(ctx.position)},
    )


def sense_danger_handler(ctx: ActionContext) -> ActionResult:
    """Default SENSE_DANGER handler."""

    danger = _nearest_danger_position(ctx)
    return ActionResult.executed(
        reason="sensed_danger",
        position_after=ctx.position,
        world_delta={
            "nearby_wall": ctx.view.nearby_wall(ctx.position),
            "danger": None if danger is None else list(danger),
        },
    )


def _movement_handler(ctx: ActionContext, action_name: str) -> ActionResult:
    from codontrace.world import World2D

    dx, dy = World2D.movement_delta(action_name)
    attempted_target = (ctx.position[0] + dx, ctx.position[1] + dy)
    target = attempted_target
    if not ctx.world.in_bounds(target):
        if ctx.world.boundary == "wrap":
            target = (target[0] % ctx.world.width, target[1] % ctx.world.height)
        else:
            return ActionResult.blocked(
                reason="out_of_bounds",
                position_after=ctx.position,
                world_delta={"target": list(target), "movement": "out_of_bounds"},
            )
    if ctx.world.is_wall(target):
        return ActionResult.blocked(
            reason="wall_blocked",
            position_after=ctx.position,
            world_delta={"target": list(target), "movement": "wall_blocked"},
        )
    if target in ctx.blocked_positions:
        delta: dict[str, JsonValue] = {
            "target": list(target),
            "movement": "occupied_blocked",
            "blocked_by": "agent",
        }
        if target != attempted_target:
            delta["attempted_target"] = list(attempted_target)
            delta["resolved_target"] = list(target)
            delta["boundary"] = "wrap"
        return ActionResult.blocked(
            reason="occupied_blocked",
            position_after=ctx.position,
            world_delta=delta,
        )
    world_delta: dict[str, JsonValue] = {
        "from": list(ctx.position),
        "to": list(target),
        "movement": "moved",
    }
    if target != attempted_target:
        world_delta["target"] = list(attempted_target)
        world_delta["resolved_target"] = list(target)
        world_delta["boundary"] = "wrap"
    return ActionResult.executed(
        reason="moved",
        position_after=target,
        world_delta=world_delta,
    )


def move_north_handler(ctx: ActionContext) -> ActionResult:
    return _movement_handler(ctx, "MOVE_NORTH")


def move_south_handler(ctx: ActionContext) -> ActionResult:
    return _movement_handler(ctx, "MOVE_SOUTH")


def move_east_handler(ctx: ActionContext) -> ActionResult:
    return _movement_handler(ctx, "MOVE_EAST")


def move_west_handler(ctx: ActionContext) -> ActionResult:
    return _movement_handler(ctx, "MOVE_WEST")


def collect_resource_handler(ctx: ActionContext) -> ActionResult:
    """Default COLLECT_RESOURCE handler.

    The handler reads world state but does not mutate it. The agent core removes
    the resource and credits ATP after receiving this result.
    """

    amount = ctx.view.resource_amount(ctx.position)
    inventory_before = {item: 1.0 for item in sorted(_inventory_items(ctx))}
    if amount <= 0:
        return ActionResult.blocked(
            reason="no_resource",
            position_after=ctx.position,
            world_delta={
                "collected_atp": 0.0,
                "resource_credit": 0.0,
                "primitive_action": "collect_resource",
                "action_precondition_allowed": False,
                "missing_inputs": ["resource"],
                "toolchain_failure_reason": "missing_resource",
                "inventory_before": inventory_before,
                "inventory_after": inventory_before,
            },
        )
    _add_inventory_item(ctx, "resource")
    inventory_after = {item: 1.0 for item in sorted(_inventory_items(ctx))}
    return ActionResult.executed(
        reason="resource_collected",
        position_after=ctx.position,
        world_delta={
            "collected_atp": amount,
            "resource_credit": amount,
            "primitive_action": "collect_resource",
            "inventory_item": "resource",
            "action_precondition_allowed": True,
            "world_state_changed": True,
            "inventory_before": inventory_before,
            "inventory_after": inventory_after,
        },
    )


def _nearest_resource_position(ctx: ActionContext) -> Position | None:
    candidates = tuple(sorted(ctx.world.resources))
    if not candidates:
        return None
    return min(candidates, key=lambda pos: (_manhattan(ctx.position, pos), pos[1], pos[0]))


def _nearest_danger_position(ctx: ActionContext) -> Position | None:
    candidates: set[Position] = set(ctx.world.walls)
    for position, marker in ctx.world.custom_cells.items():
        if marker == "I":
            candidates.add(position)
    for position, objects in ctx.world.objects.items():
        for obj in objects:
            if obj.kind.lower() in {"hazard", "ignis", "danger"}:
                candidates.add(position)
    if not candidates:
        return None
    return min(candidates, key=lambda pos: (_manhattan(ctx.position, pos), pos[1], pos[0]))


def _manhattan(left: Position, right: Position) -> int:
    return abs(left[0] - right[0]) + abs(left[1] - right[1])


def _candidate_moves(ctx: ActionContext) -> tuple[Position, ...]:
    candidates = (
        (ctx.position[0], ctx.position[1] - 1),
        (ctx.position[0] - 1, ctx.position[1]),
        (ctx.position[0] + 1, ctx.position[1]),
        (ctx.position[0], ctx.position[1] + 1),
    )
    resolved: list[Position] = []
    for candidate in candidates:
        target = candidate
        if not ctx.world.in_bounds(target):
            if ctx.world.boundary != "wrap":
                continue
            target = (target[0] % ctx.world.width, target[1] % ctx.world.height)
        if ctx.world.is_wall(target) or target in ctx.blocked_positions:
            continue
        resolved.append(target)
    return tuple(dict.fromkeys(resolved))


def sense_food_handler(ctx: ActionContext) -> ActionResult:
    """GENESIS SENSE_FOOD handler for nearest Lumen/resource."""

    target = _nearest_resource_position(ctx)
    return ActionResult.executed(
        reason="sensed_food",
        position_after=ctx.position,
        world_delta={
            "nearby_resource": ctx.view.nearby_resource(ctx.position),
            "target": None if target is None else list(target),
            "target_kind": None if target is None else "Lumen",
        },
    )


def move_toward_handler(ctx: ActionContext) -> ActionResult:
    """GENESIS MOVE_TOWARD handler for deterministic food-directed movement."""

    target = _nearest_resource_position(ctx)
    if target is None:
        return ActionResult.blocked(
            reason="no_food_target",
            position_after=ctx.position,
            world_delta={"movement": "no_food_target"},
        )
    if target in ctx.blocked_positions and _manhattan(ctx.position, target) == 1:
        return ActionResult.blocked(
            reason="occupied_blocked",
            position_after=ctx.position,
            world_delta={"target": list(target), "movement": "occupied_blocked"},
        )
    moves = _candidate_moves(ctx)
    if not moves:
        return ActionResult.blocked(
            reason="no_open_step_toward_food",
            position_after=ctx.position,
            world_delta={"target": list(target), "movement": "blocked"},
        )
    next_position = min(moves, key=lambda pos: (_manhattan(pos, target), pos[1], pos[0]))
    if _manhattan(next_position, target) >= _manhattan(ctx.position, target):
        return ActionResult.blocked(
            reason="no_better_step_toward_food",
            position_after=ctx.position,
            world_delta={"target": list(target), "movement": "not_closer"},
        )
    return ActionResult.executed(
        reason="moved_toward_food",
        position_after=next_position,
        world_delta={"from": list(ctx.position), "to": list(next_position), "target": list(target)},
    )


def move_away_handler(ctx: ActionContext) -> ActionResult:
    """GENESIS MOVE_AWAY handler for deterministic danger avoidance."""

    danger = _nearest_danger_position(ctx)
    if danger is None:
        return ActionResult.blocked(
            reason="no_danger_target",
            position_after=ctx.position,
            world_delta={"movement": "no_danger_target"},
        )
    moves = _candidate_moves(ctx)
    if not moves:
        return ActionResult.blocked(
            reason="no_open_step_away_from_danger",
            position_after=ctx.position,
            world_delta={"danger": list(danger), "movement": "blocked"},
        )
    next_position = max(moves, key=lambda pos: (_manhattan(pos, danger), -pos[1], -pos[0]))
    if _manhattan(next_position, danger) <= _manhattan(ctx.position, danger):
        return ActionResult.blocked(
            reason="no_safer_step_away_from_danger",
            position_after=ctx.position,
            world_delta={"danger": list(danger), "movement": "not_farther"},
        )
    return ActionResult.executed(
        reason="moved_away_from_danger",
        position_after=next_position,
        world_delta={"from": list(ctx.position), "to": list(next_position), "danger": list(danger)},
    )


def eat_lumen_handler(ctx: ActionContext) -> ActionResult:
    """GENESIS EAT_LUMEN handler.

    The handler reads world state only. The agent core performs resource removal
    and runtime ATP crediting after the action is accepted.
    """

    amount = ctx.view.resource_amount(ctx.position)
    inventory_before = {item: 1.0 for item in sorted(_inventory_items(ctx))}
    if amount <= 0:
        return ActionResult.blocked(
            reason="no_lumen",
            position_after=ctx.position,
            world_delta={"lumen_consumed": 0.0, "resource_credit": 0.0},
        )
    return ActionResult.executed(
        reason="lumen_consumed",
        position_after=ctx.position,
        world_delta={
            "lumen_consumed": amount,
            "resource_credit": amount,
            "lumen_interaction": True,
        },
    )


def emit_nexus_handler(ctx: ActionContext) -> ActionResult:
    """GENESIS EMIT_NEXUS handler without Causal Capsule semantics."""

    return ActionResult.executed(
        reason="nexus_emitted",
        position_after=ctx.position,
        world_delta={"signal": "Nexus", "marker": "N"},
    )


_TOOL_CHAIN_ORDER: dict[str, tuple[str, ...]] = {
    "COLLECT_WOOD": (),
    "COLLECT_STONE": (),
    "CRAFT_TOOL": ("COLLECT_WOOD", "COLLECT_STONE"),
    "COLLECT_KEY": (),
    "OPEN_DOOR": ("CRAFT_TOOL", "COLLECT_KEY"),
    "CROSS_WATER": ("CRAFT_TOOL", "OPEN_DOOR"),
    "COLLECT_FOOD": ("CROSS_WATER",),
    "RETURN_HOME": ("COLLECT_FOOD",),
}

_TOOL_CHAIN_OBJECT_KIND: dict[str, str] = {
    "COLLECT_WOOD": "wood",
    "COLLECT_STONE": "stone",
    "COLLECT_KEY": "key",
    "OPEN_DOOR": "door",
    "CROSS_WATER": "water",
    "COLLECT_FOOD": "food",
    "RETURN_HOME": "home",
}

_TOOL_CHAIN_INVENTORY_ITEM: dict[str, str] = {
    "COLLECT_WOOD": "wood",
    "COLLECT_STONE": "stone",
    "CRAFT_TOOL": "tool",
    "COLLECT_KEY": "key",
    "COLLECT_FOOD": "food",
}


def _tool_chain_agent_stages(ctx: ActionContext) -> set[str]:
    stages: set[str] = set()
    for objects in ctx.world.objects.values():
        for item in objects:
            if item.kind not in {"tool_chain_state", "tool_chain_inventory"}:
                continue
            metadata = item.metadata
            if metadata.get("agent_id") != ctx.agent_id:
                continue
            stage = metadata.get("stage")
            if isinstance(stage, str):
                stages.add(stage)
    return stages


def _tool_chain_remove_cell_object(ctx: ActionContext, action: str) -> tuple[bool, str | None]:
    kind = _TOOL_CHAIN_OBJECT_KIND.get(action)
    if kind is None:
        return False, None
    existing = ctx.world.objects_at(ctx.position)
    if not any(item.kind == kind for item in existing):
        # Absence of fixture objects is allowed for legacy/default worlds. The
        # transition is still real because progress/inventory objects are added
        # below; when fixture objects exist, they are consumed deterministically.
        return False, kind
    ctx.world.remove_objects(ctx.position, kind=kind)
    return True, kind


def _record_tool_chain_stage(ctx: ActionContext, action: str) -> dict[str, JsonValue]:
    from codontrace.world import WorldObject

    removed_fixture, fixture_kind = _tool_chain_remove_cell_object(ctx, action)
    existing = list(ctx.world.objects.get(ctx.position, ()))
    existing.append(
        WorldObject(
            kind="tool_chain_state",
            metadata={
                "agent_id": ctx.agent_id,
                "stage": action,
                "tick": ctx.step_index,
            },
        )
    )
    inventory_item = _TOOL_CHAIN_INVENTORY_ITEM.get(action)
    if inventory_item is not None:
        existing.append(
            WorldObject(
                kind="tool_chain_inventory",
                metadata={
                    "agent_id": ctx.agent_id,
                    "stage": action,
                    "item": inventory_item,
                    "tick": ctx.step_index,
                },
            )
        )
    if action == "OPEN_DOOR":
        existing.append(
            WorldObject(
                kind="door_opened",
                metadata={"agent_id": ctx.agent_id, "stage": action, "tick": ctx.step_index},
            )
        )
    if action == "CROSS_WATER":
        existing.append(
            WorldObject(
                kind="water_crossed",
                metadata={"agent_id": ctx.agent_id, "stage": action, "tick": ctx.step_index},
            )
        )
    if action == "RETURN_HOME":
        existing.append(
            WorldObject(
                kind="home_returned",
                metadata={"agent_id": ctx.agent_id, "stage": action, "tick": ctx.step_index},
            )
        )
    ctx.world.objects[ctx.position] = tuple(existing)
    return {
        "tool_chain_fixture_kind": fixture_kind,
        "tool_chain_fixture_removed": removed_fixture,
        "tool_chain_inventory_item": inventory_item,
        "tool_chain_world_state_changed": True,
    }


def _tool_chain_completion(stages: set[str]) -> float:
    ordered = (
        "COLLECT_WOOD",
        "COLLECT_STONE",
        "CRAFT_TOOL",
        "COLLECT_KEY",
        "OPEN_DOOR",
        "CROSS_WATER",
        "COLLECT_FOOD",
        "RETURN_HOME",
    )
    return round(sum(1 for item in ordered if item in stages) / len(ordered), 10)


def tool_chain_action_handler(ctx: ActionContext) -> ActionResult:
    """GENESIS tool-chain task handler with deterministic world-state effects.

    The handler records per-agent task progress into ``World2D.objects`` and
    blocks order-sensitive actions until their prerequisites are present.  The
    trace-level evaluator remains the canonical audit surface, but the action is
    now a real world transition instead of only a post-hoc/proxy counter.
    """

    action = ctx.action_name.upper()
    required = _TOOL_CHAIN_ORDER.get(action)
    if required is None:
        return ActionResult.blocked(
            reason="unknown_tool_chain_action",
            position_after=ctx.position,
            world_delta={"tool_chain_action": action, "tool_chain_stage_event": False},
        )
    stages_before = _tool_chain_agent_stages(ctx)
    missing = tuple(item for item in required if item not in stages_before)
    if missing:
        return ActionResult.blocked(
            reason="tool_chain_prerequisite_missing",
            position_after=ctx.position,
            world_delta={
                "tool_chain_action": action,
                "tool_chain_stage_event": True,
                "tool_chain_order_correct": False,
                "tool_chain_missing_prerequisites": list(missing),
                "tool_chain_completion": _tool_chain_completion(stages_before),
            },
        )
    transition_delta = _record_tool_chain_stage(ctx, action)
    stages_after = set(stages_before)
    stages_after.add(action)
    return ActionResult.executed(
        reason="tool_chain_action",
        position_after=ctx.position,
        world_delta={
            "tool_chain_action": action,
            "tool_chain_stage_event": True,
            "tool_chain_order_correct": True,
            **transition_delta,
            "tool_chain_completion": _tool_chain_completion(stages_after),
        },
    )


def _inventory_items(ctx: ActionContext) -> set[str]:
    items: set[str] = set()
    for objects in ctx.world.objects.values():
        for item in objects:
            if item.kind != "inventory_item":
                continue
            if item.metadata.get("agent_id") != ctx.agent_id:
                continue
            raw = item.metadata.get("item")
            if isinstance(raw, str):
                items.add(raw)
    return items


def _add_inventory_item(ctx: ActionContext, item_name: str) -> None:
    from codontrace.world import WorldObject

    ctx.world.add_object(
        ctx.position,
        WorldObject(
            kind="inventory_item",
            metadata={"agent_id": ctx.agent_id, "item": item_name, "tick": ctx.step_index},
        ),
    )


def collect_resource_primitive_handler(ctx: ActionContext) -> ActionResult:
    """Generic primitive: collect any resource object at the current cell.

    Scenario runners choose object kinds/placement. The library only removes the
    selected object deterministically and records inventory/evidence.
    """

    inventory_before = {item: 1.0 for item in sorted(_inventory_items(ctx))}
    objects = ctx.world.objects_at(ctx.position)
    resource = next(
        (
            obj
            for obj in objects
            if obj.kind.startswith("resource:")
            or obj.kind in {"resource", "wood", "stone", "key", "food"}
        ),
        None,
    )
    if resource is None and ctx.world.resource_amount(ctx.position) <= 0:
        return ActionResult.blocked(
            reason="missing_resource",
            position_after=ctx.position,
            world_delta={
                "primitive_action": "collect_resource",
                "action_precondition_allowed": False,
                "missing_inputs": ["resource"],
                "toolchain_failure_reason": "missing_resource",
                "inventory_before": inventory_before,
                "inventory_after": inventory_before,
            },
        )
    item_name = "resource"
    if resource is not None:
        item_name = str(resource.metadata.get("item", resource.kind.split(":", 1)[-1]))
        ctx.world.remove_objects(ctx.position, kind=resource.kind)
    else:
        amount = ctx.world.resources.get(ctx.position, 0.0)
        if amount > 0:
            ctx.world.resources.pop(ctx.position, None)
    _add_inventory_item(ctx, item_name)
    return ActionResult.executed(
        reason="resource_collected",
        position_after=ctx.position,
        world_delta={
            "primitive_action": "collect_resource",
            "inventory_item": item_name,
            "action_precondition_allowed": True,
            "world_state_changed": True,
        },
    )


def craft_item_primitive_handler(ctx: ActionContext) -> ActionResult:
    inventory_before = {item: 1.0 for item in sorted(_inventory_items(ctx))}
    items = _inventory_items(ctx)
    has_named_inputs = {"wood", "stone"}.issubset(items)
    has_generic_input = "resource" in items
    if not has_named_inputs and not has_generic_input:
        required = tuple(sorted({"wood", "stone"} - items))
        return ActionResult.blocked(
            reason="recipe_inputs_missing",
            position_after=ctx.position,
            world_delta={
                "primitive_action": "craft_item",
                "action_precondition_allowed": False,
                "missing_inputs": list(required) or ["resource"],
                "toolchain_failure_reason": "recipe_inputs_missing",
                "inventory_before": inventory_before,
                "inventory_after": inventory_before,
            },
        )
    _add_inventory_item(ctx, "crafted_item")
    _add_inventory_item(ctx, "tool")
    inventory_after = {item: 1.0 for item in sorted(_inventory_items(ctx))}
    return ActionResult.executed(
        reason="item_crafted",
        position_after=ctx.position,
        world_delta={
            "primitive_action": "craft_item",
            "inventory_item": "crafted_item",
            "action_precondition_allowed": True,
            "precondition_reason": "named_inputs_present" if has_named_inputs else "generic_resource_input_present",
            "world_state_changed": True,
            "inventory_before": inventory_before,
            "inventory_after": inventory_after,
        },
    )


def use_item_primitive_handler(ctx: ActionContext) -> ActionResult:
    items = _inventory_items(ctx)
    if not items:
        return ActionResult.blocked(
            reason="no_item_available",
            position_after=ctx.position,
            world_delta={
                "primitive_action": "use_item",
                "action_precondition_allowed": False,
                "missing_inputs": ["item"],
            },
        )
    return ActionResult.executed(
        reason="item_used",
        position_after=ctx.position,
        world_delta={
            "primitive_action": "use_item",
            "used_item": sorted(items)[0],
            "action_precondition_allowed": True,
        },
    )


def unlock_cell_primitive_handler(ctx: ActionContext) -> ActionResult:
    inventory_before = {item: 1.0 for item in sorted(_inventory_items(ctx))}
    items = _inventory_items(ctx)
    if "key" not in items and "tool" not in items and "crafted_item" not in items:
        return ActionResult.blocked(
            reason="unlock_item_missing",
            position_after=ctx.position,
            world_delta={
                "primitive_action": "unlock_cell",
                "action_precondition_allowed": False,
                "missing_inputs": ["key_or_tool"],
                "toolchain_failure_reason": "missing_required_item",
                "inventory_before": inventory_before,
                "inventory_after": inventory_before,
            },
        )
    from codontrace.world import WorldObject

    ctx.world.add_object(
        ctx.position,
        WorldObject(
            kind="unlocked_cell", metadata={"agent_id": ctx.agent_id, "tick": ctx.step_index}
        ),
    )
    return ActionResult.executed(
        reason="cell_unlocked",
        position_after=ctx.position,
        world_delta={
            "primitive_action": "unlock_cell",
            "action_precondition_allowed": True,
            "world_state_changed": True,
            "inventory_before": inventory_before,
            "inventory_after": inventory_before,
        },
    )


def cross_terrain_primitive_handler(ctx: ActionContext) -> ActionResult:
    inventory_before = {item: 1.0 for item in sorted(_inventory_items(ctx))}
    items = _inventory_items(ctx)
    terrain = ctx.world.get_custom_cell(ctx.position)
    if (
        terrain in {"W", "water"}
        and "tool" not in items
        and "bridge" not in items
        and "crafted_item" not in items
    ):
        return ActionResult.blocked(
            reason="terrain_requirement_missing",
            position_after=ctx.position,
            world_delta={
                "primitive_action": "cross_terrain",
                "action_precondition_allowed": False,
                "missing_inputs": ["tool_or_bridge"],
                "terrain_constraint": terrain,
                "toolchain_failure_reason": "terrain_requirement_missing",
                "inventory_before": inventory_before,
                "inventory_after": inventory_before,
            },
        )
    from codontrace.world import WorldObject

    ctx.world.add_object(
        ctx.position,
        WorldObject(
            kind="terrain_crossed", metadata={"agent_id": ctx.agent_id, "tick": ctx.step_index}
        ),
    )
    return ActionResult.executed(
        reason="terrain_crossed",
        position_after=ctx.position,
        world_delta={
            "primitive_action": "cross_terrain",
            "action_precondition_allowed": True,
            "terrain_constraint": terrain,
            "world_state_changed": True,
            "inventory_before": inventory_before,
            "inventory_after": inventory_before,
        },
    )


def deposit_resource_primitive_handler(ctx: ActionContext) -> ActionResult:
    inventory_before = {item: 1.0 for item in sorted(_inventory_items(ctx))}
    items = _inventory_items(ctx)
    if not items:
        return ActionResult.blocked(
            reason="missing_resource",
            position_after=ctx.position,
            world_delta={
                "primitive_action": "deposit_resource",
                "action_precondition_allowed": False,
                "missing_inputs": ["resource"],
                "toolchain_failure_reason": "missing_resource",
            },
        )
    from codontrace.world import WorldObject

    deposited = sorted(items)[0]
    ctx.world.add_object(
        ctx.position,
        WorldObject(
            kind="deposited_resource",
            metadata={"agent_id": ctx.agent_id, "item": deposited, "tick": ctx.step_index},
        ),
    )
    return ActionResult.executed(
        reason="resource_deposited",
        position_after=ctx.position,
        world_delta={
            "primitive_action": "deposit_resource",
            "deposited_item": deposited,
            "action_precondition_allowed": True,
            "world_state_changed": True,
            "tool_chain_reward_delta": 1.0,
            "fitness_component_delta": 1.0,
            "inventory_before": inventory_before,
            "inventory_after": inventory_before,
        },
    )


def return_to_target_primitive_handler(ctx: ActionContext) -> ActionResult:
    target = ctx.world.get_custom_cell(ctx.position)
    at_target = target in {"H", "home", "target"} or any(
        obj.kind in {"home", "target"} for obj in ctx.world.objects_at(ctx.position)
    )
    return ActionResult(
        status="executed" if at_target else "blocked",
        reason="returned_to_target" if at_target else "target_missing",
        position_after=ctx.position,
        world_delta={
            "primitive_action": "return_to_target",
            "action_precondition_allowed": at_target,
            "target_cell": target,
            "world_state_changed": at_target,
            "tool_chain_reward_delta": 1.0 if at_target else 0.0,
            "fitness_component_delta": 1.0 if at_target else 0.0,
        },
    )


def copy_self_handler(ctx: ActionContext) -> ActionResult:
    """GENESIS COPY_SELF is blocked outside population lifecycle runs."""

    return ActionResult.blocked(
        reason="reproduction_not_enabled",
        position_after=ctx.position,
        world_delta={
            "reproduction": "population_lifecycle_required",
            "enabled": False,
            "reproduction_attempted": True,
            "reproduction_succeeded": False,
            "reproduction_blocked_reason": "reproduction_not_enabled",
            "parent_id": ctx.agent_id,
            "child_id": None,
        },
    )


def default_action_registry_manifest() -> tuple[dict[str, str], ...]:
    """Stable process-independent manifest for built-in action handlers.

    The manifest intentionally avoids handler object reprs, closures, memory
    addresses, and bytecode constants so GENESIS experiment digests are stable
    across Python processes while still identifying the replayable built-in ABI.
    """

    registry = default_action_registry()
    rows: list[dict[str, str]] = []
    for name in registry.names():
        handler = registry.get(name)
        module = str(getattr(handler, "__module__", "unknown"))
        qualname = str(getattr(handler, "__qualname__", name))
        rows.append(
            {
                "name": name,
                "handler_stable_id": f"{module}:{qualname}",
                "handler_provenance": "built_in_replayable",
                "action_abi_version": "action_result_v1",
            }
        )
    return tuple(rows)


def default_action_registry() -> ActionRegistry:
    """Return the immutable default handler registry."""

    return ActionRegistry(
        {
            "WAIT": wait_handler,
            "SENSE_RESOURCE": sense_resource_handler,
            "SENSE_FOOD": sense_food_handler,
            "SENSE_DANGER": sense_danger_handler,
            "MOVE_NORTH": move_north_handler,
            "MOVE_SOUTH": move_south_handler,
            "MOVE_EAST": move_east_handler,
            "MOVE_WEST": move_west_handler,
            "MOVE_TOWARD": move_toward_handler,
            "MOVE_AWAY": move_away_handler,
            "COLLECT_RESOURCE": collect_resource_handler,
            "COLLECT_RESOURCE_OBJECT": collect_resource_primitive_handler,
            "EAT_LUMEN": eat_lumen_handler,
            "EMIT_NEXUS": emit_nexus_handler,
            "COLLECT_WOOD": tool_chain_action_handler,
            "COLLECT_STONE": tool_chain_action_handler,
            "CRAFT_TOOL": tool_chain_action_handler,
            "COLLECT_KEY": tool_chain_action_handler,
            "OPEN_DOOR": tool_chain_action_handler,
            "CROSS_WATER": tool_chain_action_handler,
            "COLLECT_FOOD": tool_chain_action_handler,
            "RETURN_HOME": tool_chain_action_handler,
            "CRAFT_ITEM": craft_item_primitive_handler,
            "USE_ITEM": use_item_primitive_handler,
            "UNLOCK_CELL": unlock_cell_primitive_handler,
            "CROSS_TERRAIN": cross_terrain_primitive_handler,
            "DEPOSIT_RESOURCE": deposit_resource_primitive_handler,
            "RETURN_TO_TARGET": return_to_target_primitive_handler,
            "COPY_SELF": copy_self_handler,
        }
    )
