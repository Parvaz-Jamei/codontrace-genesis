"""Engine-level tool-chain task state and scoring helpers."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable
from dataclasses import dataclass

from codontrace._types import JsonValue
from codontrace.trace import Trace, TraceEvent

TOOL_CHAIN_ACTIONS = (
    "collect_resource",
    "craft_item",
    "use_item",
    "unlock_cell",
    "cross_terrain",
    "deposit_resource",
    "return_to_target",
    "collect_wood",
    "collect_stone",
    "craft_tool",
    "collect_key",
    "open_door",
    "cross_water",
    "collect_food",
    "return_home",
)
_ORDER = {name.upper(): index + 1 for index, name in enumerate(TOOL_CHAIN_ACTIONS)}


@dataclass(frozen=True, slots=True)
class ToolActionSpec:
    """Primitive tool/action contract; runners define scenarios with these specs."""

    action: str
    resource_kind: str | None = None
    required_inputs: tuple[str, ...] = ()
    output_item: str | None = None
    target_cell: tuple[int, int] | None = None
    terrain_constraint: str | None = None
    reward_component: str = "tool_chain_score"
    failure_reason: str = "precondition_failed"
    schema_version: str = "tool_action_spec_v1"

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "schema_version": self.schema_version,
            "action": self.action,
            "resource_kind": self.resource_kind,
            "required_inputs": list(self.required_inputs),
            "output_item": self.output_item,
            "target_cell": None if self.target_cell is None else list(self.target_cell),
            "terrain_constraint": self.terrain_constraint,
            "reward_component": self.reward_component,
            "failure_reason": self.failure_reason,
        }

    def digest(self) -> str:
        return _digest(self.to_dict())


@dataclass(frozen=True, slots=True)
class ToolChainRecord:
    """Per-action tool primitive audit record with state/reward evidence."""

    organism_id: str
    tick: int
    action: str
    allowed: bool
    blocked_reason: str | None
    state_digest: str
    inventory_before: dict[str, JsonValue] | None = None
    inventory_after: dict[str, JsonValue] | None = None
    world_delta: dict[str, JsonValue] | None = None
    reward_delta: float = 0.0
    status: str = "measured"
    precondition_passed: bool = False
    precondition_reason: str | None = None
    world_state_before_digest: str | None = None
    world_state_after_digest: str | None = None
    fitness_component_delta: float = 0.0
    effect_digest: str = ""
    schema_version: str = "tool_chain_record_v2"

    def _payload(self) -> dict[str, JsonValue]:
        return {
            "schema_version": self.schema_version,
            "organism_id": self.organism_id,
            "tick": self.tick,
            "action": self.action,
            "allowed": self.allowed,
            "status": self.status,
            "blocked_reason": self.blocked_reason,
            "precondition_passed": self.precondition_passed,
            "precondition_reason": self.precondition_reason,
            "inventory_before": {} if self.inventory_before is None else dict(self.inventory_before),
            "inventory_after": {} if self.inventory_after is None else dict(self.inventory_after),
            "world_state_before_digest": self.world_state_before_digest,
            "world_state_after_digest": self.world_state_after_digest,
            "world_delta": {} if self.world_delta is None else dict(self.world_delta),
            "reward_delta": self.reward_delta,
            "fitness_component_delta": self.fitness_component_delta,
            "state_digest": self.state_digest,
            "effect_digest": self.effect_digest,
        }

    def to_dict(self) -> dict[str, JsonValue]:
        payload = self._payload()
        payload["record_digest"] = self.digest()
        return payload

    def digest(self) -> str:
        return _digest(self._payload())


@dataclass(frozen=True, slots=True)
class ToolChainState:
    wood_collected: bool = False
    stone_collected: bool = False
    tool_created: bool = False
    key_collected: bool = False
    door_opened: bool = False
    water_crossed: bool = False
    food_collected: bool = False
    home_returned: bool = False
    stage: int = 0
    order_correct: bool = True
    completion: float = 0.0
    schema_version: str = "tool_chain_state_v1"

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "schema_version": self.schema_version,
            "wood_collected": self.wood_collected,
            "stone_collected": self.stone_collected,
            "tool_created": self.tool_created,
            "key_collected": self.key_collected,
            "door_opened": self.door_opened,
            "water_crossed": self.water_crossed,
            "food_collected": self.food_collected,
            "home_returned": self.home_returned,
            "stage": self.stage,
            "order_correct": self.order_correct,
            "completion": self.completion,
        }

    @property
    def tool_chain_score(self) -> float:
        return round(self.completion + (1.0 if self.order_correct else 0.0), 10)

    def digest(self) -> str:
        return _digest(self.to_dict())


def evaluate_tool_chain_state(trace: Trace | Iterable[TraceEvent]) -> ToolChainState:
    events = tuple(trace.events if isinstance(trace, Trace) else trace)
    max_stage = 0
    order_correct = True
    wood = stone = tool = key = door = water = food = home = False
    for event in events:
        action = event.action.upper()
        if action not in _ORDER:
            continue
        if event.status != "executed" or event.world_delta.get("tool_chain_order_correct") is False:
            order_correct = False
            continue
        stage = _ORDER[action]
        if stage < max_stage:
            order_correct = False
        max_stage = max(max_stage, stage)
        if action == "COLLECT_WOOD":
            wood = True
        elif action == "COLLECT_STONE":
            stone = True
        elif action == "CRAFT_TOOL":
            if wood and stone:
                tool = True
            else:
                order_correct = False
        elif action == "COLLECT_KEY":
            key = True
        elif action == "OPEN_DOOR":
            if tool and key:
                door = True
            else:
                order_correct = False
        elif action == "CROSS_WATER":
            if tool and door:
                water = True
            else:
                order_correct = False
        elif action == "COLLECT_FOOD":
            if water:
                food = True
            else:
                order_correct = False
        elif action == "RETURN_HOME":
            if food:
                home = True
            else:
                order_correct = False
    passed = (wood, stone, tool, key, door, water, food, home)
    completion = round(sum(1 for item in passed if item) / len(passed), 10)
    return ToolChainState(
        wood_collected=wood,
        stone_collected=stone,
        tool_created=tool,
        key_collected=key,
        door_opened=door,
        water_crossed=water,
        food_collected=food,
        home_returned=home,
        stage=max_stage,
        order_correct=order_correct,
        completion=completion,
    )


def tool_chain_records_from_trace(trace: Trace | Iterable[TraceEvent]) -> tuple[ToolChainRecord, ...]:
    """Return event-level tool-chain records with explicit evidence invariants."""

    events = tuple(trace.events if isinstance(trace, Trace) else trace)
    rows: list[ToolChainRecord] = []
    running_events: list[TraceEvent] = []
    running_inventory: dict[str, float] = {}
    for event in events:
        action = event.action.upper()
        primitive = str(event.world_delta.get("primitive_action", "")).lower()
        if action.lower() not in TOOL_CHAIN_ACTIONS and action not in _ORDER and primitive not in TOOL_CHAIN_ACTIONS:
            continue
        before_inventory = dict(sorted(running_inventory.items()))
        explicit_before = event.world_delta.get("inventory_before")
        if isinstance(explicit_before, dict):
            before_inventory = {str(key): float(value) for key, value in explicit_before.items() if isinstance(value, int | float) and not isinstance(value, bool)}
        item = event.world_delta.get("inventory_item")
        deposited_item = event.world_delta.get("deposited_item")
        if event.status == "executed" and isinstance(item, str):
            running_inventory[item] = round(running_inventory.get(item, 0.0) + 1.0, 10)
        if event.status == "executed" and isinstance(deposited_item, str):
            # Depositing changes the world but does not erase the audit trail of held items.
            running_inventory[deposited_item] = running_inventory.get(deposited_item, 0.0)
        after_inventory = dict(sorted(running_inventory.items()))
        explicit_after = event.world_delta.get("inventory_after")
        if isinstance(explicit_after, dict):
            after_inventory = {str(key): float(value) for key, value in explicit_after.items() if isinstance(value, int | float) and not isinstance(value, bool)}
        running_events.append(event)
        state = evaluate_tool_chain_state(running_events)
        reward_delta = _numeric_delta(event.world_delta.get("tool_chain_reward_delta"))
        fitness_delta = _numeric_delta(event.world_delta.get("fitness_component_delta"))
        precondition_passed = event.world_delta.get("action_precondition_allowed") is True or (
            event.status == "executed" and event.world_delta.get("tool_chain_order_correct", True) is not False
        )
        state_changed = bool(event.world_delta.get("world_state_changed") or event.world_delta.get("tool_chain_world_state_changed"))
        inventory_changed = before_inventory != after_inventory
        evidenceful_success = event.status == "executed" and precondition_passed and (
            state_changed or inventory_changed or reward_delta != 0.0 or fitness_delta != 0.0
        )
        allowed = evidenceful_success
        reason = None if allowed else _toolchain_blocked_reason(event)
        world_before = event.world_digest_before
        world_after = event.world_delta.get("world_digest_after")
        if not isinstance(world_after, str):
            world_after = world_before
        effect_digest = _digest({
            "action": event.action,
            "status": event.status,
            "reason": event.reason,
            "world_delta": dict(event.world_delta),
            "inventory_before": before_inventory,
            "inventory_after": after_inventory,
            "reward_delta": reward_delta,
            "fitness_component_delta": fitness_delta,
        })
        rows.append(
            ToolChainRecord(
                organism_id=event.agent_id,
                tick=event.step,
                action=event.action,
                allowed=allowed,
                blocked_reason=reason,
                state_digest=state.digest(),
                inventory_before=before_inventory,
                inventory_after=after_inventory,
                world_delta=dict(event.world_delta),
                reward_delta=reward_delta,
                status=event.status,
                precondition_passed=precondition_passed,
                precondition_reason=str(event.world_delta.get("precondition_reason") or event.reason or ""),
                world_state_before_digest=world_before,
                world_state_after_digest=world_after,
                fitness_component_delta=fitness_delta,
                effect_digest=effect_digest,
            )
        )
    if not rows and events:
        first = events[0]
        state = evaluate_tool_chain_state(events)
        rows.append(
            ToolChainRecord(
                organism_id=first.agent_id,
                tick=first.step,
                action="NO_TOOLCHAIN_ACTION",
                allowed=False,
                blocked_reason="no_toolchain_action_observed",
                state_digest=state.digest(),
                inventory_before={},
                inventory_after={},
                world_delta={},
                reward_delta=0.0,
                status="empty_but_available",
                precondition_passed=False,
                precondition_reason="no_toolchain_action_observed",
                world_state_before_digest=first.world_digest_before,
                world_state_after_digest=first.world_digest_before,
                fitness_component_delta=0.0,
                effect_digest=_digest({"status": "empty_but_available"}),
            )
        )
    return tuple(rows)


def _numeric_delta(value: JsonValue | None) -> float:
    return float(value) if isinstance(value, int | float) and not isinstance(value, bool) else 0.0


def _toolchain_blocked_reason(event: TraceEvent) -> str:
    explicit = event.world_delta.get("toolchain_failure_reason")
    if isinstance(explicit, str) and explicit:
        return explicit
    if event.reason in {"resource_missing", "no_resource", "missing_resource"}:
        return "missing_resource"
    if event.reason in {"craft_inputs_missing", "recipe_inputs_missing"}:
        return "recipe_inputs_missing"
    if event.reason in {"unlock_item_missing"}:
        return "missing_required_item"
    if event.reason in {"terrain_constraint_failed", "terrain_requirement_missing"}:
        return "terrain_requirement_missing"
    if event.reason in {"deposit_resource_missing"}:
        return "missing_resource"
    if event.reason in {"target_missing"}:
        return "wrong_target"
    return event.reason or "unknown"


def _digest(payload: dict[str, JsonValue]) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    ).hexdigest()
