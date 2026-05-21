"""Replay and perturbation-based explanations for traced decisions."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol

from codontrace._types import JsonValue, Position
from codontrace.actions import ActionContext, ActionHandler, ActionRegistry, default_action_registry
from codontrace.codon import CodonTable
from codontrace.energy import ATPAccount
from codontrace.genome import SemanticGenome
from codontrace.trace import TimelineFrame, Trace, TraceEvent, WorldEvent
from codontrace.world import World2D

if TYPE_CHECKING:
    from codontrace.agent import WhiteBoxAgent


@dataclass(frozen=True, slots=True)
class ReplayResult:
    """Digest bundle returned by deterministic replay runs."""

    trace_digest: str
    world_digest: str
    agent_digest: str


@dataclass(frozen=True, slots=True)
class TimelineReplayResult:
    """Result of replaying world events into viewer-oriented timeline frames."""

    trace_digest: str
    bundle_digest: str
    world_digest: str
    frames_digest: str
    frames: tuple[TimelineFrame, ...] = ()


@dataclass(frozen=True, slots=True)
class ReplaySnapshot:
    """Snapshot of the minimal state needed for deterministic replay."""

    agent_id: str
    genome: SemanticGenome
    codon_table: CodonTable
    action_registry: ActionRegistry
    world: World2D
    atp: float
    atp_snapshot: dict[str, float | int | str]
    atp_state: dict[str, JsonValue]
    position: Position
    cursor: int
    step_index: int

    @classmethod
    def capture(cls, agent: SnapshotAgent, world: World2D) -> ReplaySnapshot:
        """Capture replay state from an agent and world."""

        return cls(
            agent_id=agent.id,
            genome=agent.genome,
            codon_table=agent.codon_table,
            action_registry=agent.action_registry,
            world=world.clone(),
            atp=agent.atp_account.current_atp,
            atp_snapshot=agent.atp_account.snapshot(),
            atp_state=agent.atp_account.to_dict(),
            position=agent.position,
            cursor=agent.cursor,
            step_index=agent.step_index,
        )

    def world_digest(self) -> str:
        """Return the digest of the captured world state."""

        return self.world.digest()

    def ledger_digest(self) -> str:
        """Return the captured ATP ledger digest."""

        value = self.atp_snapshot.get("ledger_digest")
        return str(value)


@dataclass(frozen=True, slots=True)
class PerturbationResult:
    """Result of perturbing one traced decision."""

    name: str
    status: str
    reason: str
    position_after: Position

    def to_dict(self) -> dict[str, str | list[int]]:
        """Return JSON-friendly perturbation output."""

        return {
            "name": self.name,
            "status": self.status,
            "reason": self.reason,
            "position_after": list(self.position_after),
        }


@dataclass(frozen=True, slots=True)
class Explanation:
    """Faithful explanation object for one traced decision."""

    summary: str
    sufficient_causes: tuple[str, ...]
    counterfactuals: tuple[str, ...]
    trace_refs: tuple[int, ...]
    perturbation_results: tuple[PerturbationResult, ...] = ()

    def __str__(self) -> str:
        return self.summary


class ReplayableAgent(Protocol):
    def run(self, world: World2D, steps: int) -> Trace: ...

    def state_digest(self) -> str: ...


class SnapshotAgent(ReplayableAgent, Protocol):
    id: str
    genome: SemanticGenome
    codon_table: CodonTable
    action_registry: ActionRegistry
    atp_account: ATPAccount
    position: Position

    @property
    def cursor(self) -> int: ...

    @property
    def step_index(self) -> int: ...


class CausalReplay:
    """Small deterministic replay/explanation helper."""

    @staticmethod
    def run_deterministic(agent: ReplayableAgent, world: World2D, *, steps: int) -> ReplayResult:
        """Run an agent-like object and return stable trace/world/agent digests."""

        trace = agent.run(world, steps)
        return ReplayResult(
            trace_digest=trace.digest(),
            world_digest=world.digest(),
            agent_digest=agent.state_digest(),
        )

    @staticmethod
    def replay(agent: ReplayableAgent, world: World2D, *, steps: int) -> ReplayResult:
        """Backward-compatible alias for ``run_deterministic``."""

        return CausalReplay.run_deterministic(agent, world, steps=steps)

    @staticmethod
    def replay_from_snapshot(snapshot: ReplaySnapshot, *, steps: int) -> ReplayResult:
        """Replay from a snapshot without mutating the captured world object."""

        from codontrace.agent import WhiteBoxAgent

        world = snapshot.world.clone()
        account = ATPAccount.from_dict(snapshot.atp_state)
        agent = WhiteBoxAgent(
            id=snapshot.agent_id,
            genome=snapshot.genome,
            codon_table=snapshot.codon_table,
            atp_account=account,
            position=snapshot.position,
            action_registry=snapshot.action_registry,
        )
        agent.restore_runtime_state(cursor=snapshot.cursor, step_index=snapshot.step_index)
        trace = agent.run(world, steps)
        return ReplayResult(
            trace_digest=trace.digest(),
            world_digest=world.digest(),
            agent_digest=agent.state_digest(),
        )

    @staticmethod
    def apply_world_events(
        world: World2D,
        events: Iterable[WorldEvent],
        *,
        until_step: int | None = None,
    ) -> World2D:
        """Apply world events deterministically to a clone of ``world``."""

        clone = world.clone()
        for event in sorted(events, key=lambda item: (item.step, item.sequence)):
            if until_step is not None and event.step > until_step:
                break
            clone.apply_world_event(event)
        return clone

    @staticmethod
    def replay_timeline(
        *,
        initial_world: World2D,
        trace: Trace,
        agents: Sequence[WhiteBoxAgent] | None = None,
        emit_frames: bool = False,
        frame_every: int = 1,
    ) -> TimelineReplayResult:
        """Replay world events and optionally emit UI/game-engine timeline frames.

        v1 applies world/environment events deterministically. Agent events are
        preserved in the bundle and may be included in emitted frame event lists;
        full agent re-execution remains the responsibility of replay_from_snapshot
        or higher-level experiment code.
        """

        if frame_every <= 0:
            msg = "frame_every must be positive."
            raise ValueError(msg)
        runtime_world = initial_world.clone()
        frames: list[TimelineFrame] = []
        agent_items = tuple(agents or ())
        for event in sorted(trace.world_events, key=lambda item: (item.step, item.sequence)):
            runtime_world.apply_world_event(event)
            if emit_frames and event.step % frame_every == 0:
                step_events = tuple(item for item in trace.all_events() if item.step == event.step)
                frames.append(
                    runtime_world.to_timeline_frame(
                        agents=agent_items,
                        step=event.step,
                        events=step_events,
                    )
                )
        frames_payload = [frame.to_dict() for frame in frames]
        return TimelineReplayResult(
            trace_digest=trace.digest(),
            bundle_digest=trace.bundle_digest(),
            world_digest=runtime_world.digest(),
            frames_digest=digest_payload(frames_payload),
            frames=tuple(frames),
        )

    @staticmethod
    def perturb(
        event: TraceEvent,
        world_before_or_snapshot: World2D,
        *,
        name: str,
        codon_table: CodonTable | None = None,
        action_registry: ActionRegistry | None = None,
        atp_override: float | None = None,
        remove_resource_at: Position | None = None,
        add_wall_at: Position | None = None,
    ) -> PerturbationResult:
        """Perturb a traced decision and re-evaluate the immediate action effect."""

        table = codon_table or CodonTable.default_minimal()
        registry = action_registry or default_action_registry()
        world = world_before_or_snapshot.clone()
        if remove_resource_at is not None:
            world.resources.pop(remove_resource_at, None)
        if add_wall_at is not None:
            world.walls.add(add_wall_at)
        atp_value = event.atp_before if atp_override is None else atp_override
        return CausalReplay._simulate_event(
            event,
            world,
            name=name,
            atp_value=atp_value,
            codon_table=table,
            action_registry=registry,
        )

    @staticmethod
    def compare(
        baseline: PerturbationResult,
        perturbed: PerturbationResult,
    ) -> dict[str, object]:
        """Compare baseline and perturbed immediate outcomes."""

        changed_fields = []
        if baseline.status != perturbed.status:
            changed_fields.append("status")
        if baseline.reason != perturbed.reason:
            changed_fields.append("reason")
        if baseline.position_after != perturbed.position_after:
            changed_fields.append("position_after")
        return {
            "changed": bool(changed_fields),
            "changed_fields": changed_fields,
            "baseline": baseline.to_dict(),
            "perturbed": perturbed.to_dict(),
            "explanation_passed": bool(changed_fields),
        }

    @staticmethod
    def explain_last_action(
        trace: Trace,
        world_before_or_snapshot: World2D | None = None,
        *,
        codon_table: CodonTable | None = None,
        action_registry: ActionRegistry | None = None,
    ) -> Explanation:
        """Explain the last action using trace facts and optional local perturbations."""

        event = trace.last()
        table = codon_table or CodonTable.default_minimal()
        registry = action_registry or default_action_registry()
        codon = table.decode(event.codon)
        action_cost = _float_from_delta(event, "action_cost", codon.cost)
        resource_credit = _float_from_delta(event, "resource_credit", 0.0)
        net_atp_delta = _float_from_delta(
            event,
            "net_atp_delta",
            round(event.atp_after - event.atp_before, 10),
        )
        perturbations: tuple[PerturbationResult, ...] = ()
        sufficient_causes = (
            f"codon:{event.codon}",
            f"action:{event.action}",
            f"atp_before:{event.atp_before}",
            f"action_cost:{action_cost}",
            f"status:{event.status}",
            f"reason:{event.reason}",
        )
        counterfactuals = _counterfactuals_for(event.action, action_cost)

        if world_before_or_snapshot is not None:
            perturbation_list = [
                CausalReplay.perturb(
                    event,
                    world_before_or_snapshot,
                    name="baseline",
                    codon_table=table,
                    action_registry=registry,
                )
            ]
            low_atp_value = max(action_cost - 0.01, 0.0)
            perturbation_list.append(
                CausalReplay.perturb(
                    event,
                    world_before_or_snapshot,
                    name="low_atp",
                    codon_table=table,
                    action_registry=registry,
                    atp_override=low_atp_value,
                )
            )
            if event.action == "COLLECT_RESOURCE":
                perturbation_list.append(
                    CausalReplay.perturb(
                        event,
                        world_before_or_snapshot,
                        name="resource_removed",
                        codon_table=table,
                        action_registry=registry,
                        remove_resource_at=event.position_before,
                    )
                )
            if event.action.startswith("MOVE_"):
                perturbation_list.append(
                    CausalReplay.perturb(
                        event,
                        world_before_or_snapshot,
                        name="wall_inserted",
                        codon_table=table,
                        action_registry=registry,
                        add_wall_at=event.position_after,
                    )
                )
            perturbations = tuple(perturbation_list)

        perturbation_reasons = ", ".join(
            f"{item.name}:{item.reason}" for item in perturbations if item.name != "baseline"
        )
        ledger_ids = ",".join(str(item) for item in event.ledger_entry_ids) or "none"
        ledger_refs = ",".join(event.ledger_entry_refs) or "none"
        handler_note = ""
        if registry.get(event.action) is None:
            handler_note = (
                " Handler missing for this action; registry_missing may appear in replay."
            )
        summary = (
            f"Action {event.action} was selected because codon {event.codon} decoded to "
            f"{codon.action_name}. ATP before action was {event.atp_before}; action cost was "
            f"{action_cost}; resource credit was {resource_credit}; net ATP delta was "
            f"{net_atp_delta}; ledger entry refs were {ledger_refs}; raw ledger entry ids "
            f"were {ledger_ids}. Status={event.status}; "
            f"reason={event.reason}; movement {event.position_before}->{event.position_after}."
            f"{handler_note}"
        )
        if perturbation_reasons:
            summary = f"{summary} Perturbations: {perturbation_reasons}."
        return Explanation(
            summary=summary,
            sufficient_causes=sufficient_causes,
            counterfactuals=counterfactuals,
            trace_refs=(event.step,),
            perturbation_results=perturbations,
        )

    @staticmethod
    def _simulate_event(
        event: TraceEvent,
        world: World2D,
        *,
        name: str,
        atp_value: float,
        codon_table: CodonTable,
        action_registry: ActionRegistry,
    ) -> PerturbationResult:
        codon = codon_table.decode(event.codon)
        action_name = codon.action_name
        if atp_value < codon.cost:
            return PerturbationResult(
                name=name,
                status="blocked",
                reason="insufficient_atp",
                position_after=event.position_before,
            )
        handler = _resolve_handler(
            action_name=action_name,
            codon_bits=event.codon,
            action_registry=action_registry,
        )
        if handler is None:
            return PerturbationResult(
                name=name,
                status="blocked",
                reason="registry_missing" if action_name != event.action else "unsupported_action",
                position_after=event.position_before,
            )
        result = handler(
            ActionContext(
                agent_id=event.agent_id,
                position=event.position_before,
                codon_bits=event.codon,
                action_name=action_name,
                step_index=event.step,
                world=world,
            )
        )
        return PerturbationResult(
            name=name,
            status=result.status,
            reason=result.reason,
            position_after=result.position_after or event.position_before,
        )


def _counterfactuals_for(action_name: str, action_cost: float) -> tuple[str, ...]:
    items: list[str] = []
    if action_cost > 0:
        items.append(
            f"If ATP were below action cost {action_cost}, the action would be blocked "
            "with reason=insufficient_atp."
        )
    if action_name == "COLLECT_RESOURCE":
        items.append(
            "If the resource were removed, collection would be blocked with reason=no_resource."
        )
    if action_name.startswith("MOVE_"):
        items.append(
            "If a wall occupied the target cell, movement would be blocked "
            "with reason=wall_blocked."
        )
    return tuple(items)


def _float_from_delta(event: TraceEvent, key: str, default: float) -> float:
    value = event.world_delta.get(key)
    if isinstance(value, int | float):
        return float(value)
    return default


def digest_payload(payload: object) -> str:
    """Return a stable digest for small replay payloads."""

    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _resolve_handler(
    *,
    action_name: str,
    codon_bits: str,
    action_registry: ActionRegistry,
) -> ActionHandler | None:
    handler = action_registry.get(action_name)
    if handler is not None:
        return handler
    try:
        default_action_name = CodonTable.default_minimal().decode(codon_bits).action_name
    except KeyError:
        return None
    fallback = action_registry.get(default_action_name)
    default_fallback = default_action_registry().get(default_action_name)
    if fallback is not None and fallback is not default_fallback:
        return fallback
    return None
