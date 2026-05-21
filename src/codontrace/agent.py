"""White-box ATP-constrained agent."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable
from dataclasses import dataclass, field

from codontrace._types import JsonValue, Position
from codontrace.actions import (
    ActionContext,
    ActionHandler,
    ActionRegistry,
    ActionResult,
    ActionRuntimeConfig,
    ActionStatus,
    default_action_registry,
)
from codontrace.codon import CodonTable
from codontrace.energy import ATPAccount
from codontrace.errors import ConfigurationError, InsufficientATPError, PlacementError, ReplayError
from codontrace.genome import SemanticGenome
from codontrace.replay import CausalReplay, Explanation
from codontrace.trace import Trace, TraceEvent
from codontrace.world import World2D


@dataclass(frozen=True, slots=True)
class RunResult:
    """Beginner-friendly result returned by ``WhiteBoxAgent.run_trial()``."""

    agent: WhiteBoxAgent
    world: World2D
    trace: Trace
    explanation: Explanation | None = None


@dataclass(slots=True)
class WhiteBoxAgent:
    """A deterministic white-box agent that executes genome codons in order.

    The genome cursor wraps around when it reaches the end. Custom action
    handlers are resolved through ActionRegistry, while ATP accounting and trace
    creation always remain in the agent core.
    """

    id: str
    genome: SemanticGenome
    codon_table: CodonTable
    atp_account: ATPAccount
    position: Position
    action_registry: ActionRegistry = field(default_factory=default_action_registry)
    action_runtime_config: ActionRuntimeConfig = field(default_factory=ActionRuntimeConfig)
    profile: str | None = None
    lineage_id: str | None = None
    parent_id: str | None = None
    generation: int = 0
    _cursor: int = field(default=0, init=False, repr=False)
    _step_index: int = field(default=0, init=False, repr=False)
    _trace: Trace | None = field(default=None, init=False, repr=False)

    @classmethod
    def quick(
        cls,
        genome: str | list[str] | tuple[str, ...] | SemanticGenome,
        *,
        initial_atp: float | None = None,
        atp: float | None = None,
        position: Position = (0, 0),
        agent_id: str = "agent-1",
        codon_table: CodonTable | None = None,
        action_registry: ActionRegistry | None = None,
        action_runtime_config: ActionRuntimeConfig | None = None,
    ) -> WhiteBoxAgent:
        """Create a WhiteBoxAgent with sensible defaults for quick experiments.

        ``initial_atp`` is the preferred energy parameter. ``atp`` is retained as
        a backward-compatible alias for earlier alpha examples.
        """

        if initial_atp is not None and atp is not None:
            msg = "Provide either initial_atp or atp, not both."
            raise ConfigurationError(msg)
        resolved_initial_atp = initial_atp if initial_atp is not None else atp
        if resolved_initial_atp is None:
            resolved_initial_atp = 5.0

        if isinstance(genome, SemanticGenome):
            resolved_genome = genome
        elif isinstance(genome, str):
            resolved_genome = SemanticGenome.from_compact(genome)
        else:
            resolved_genome = SemanticGenome.from_codons(tuple(genome))
        return cls(
            id=agent_id,
            genome=resolved_genome,
            codon_table=codon_table or CodonTable.default_minimal(),
            atp_account=ATPAccount(initial_atp=resolved_initial_atp),
            position=position,
            action_registry=action_registry or default_action_registry(),
            action_runtime_config=action_runtime_config or ActionRuntimeConfig(),
        )

    @classmethod
    def from_world(
        cls,
        world: World2D,
        genome: str | list[str] | tuple[str, ...] | SemanticGenome,
        *,
        initial_atp: float = 5.0,
        agent_id: str = "agent-1",
        position: Position | None = None,
        codon_table: CodonTable | None = None,
        action_registry: ActionRegistry | None = None,
        action_runtime_config: ActionRuntimeConfig | None = None,
    ) -> WhiteBoxAgent:
        """Create an agent from a world marker and a compact beginner genome.

        If ``position`` is omitted, the method uses the ``A`` marker parsed by
        ``World2D.from_ascii()``. This is the recommended single-agent entrypoint
        for first-time users.
        """

        resolved_position = position if position is not None else world.agent_position
        if resolved_position is None:
            msg = (
                "World has no agent marker 'A'. Pass position=(x, y) "
                "or include 'A' in the ASCII map."
            )
            raise ConfigurationError(msg)
        if not world.in_bounds(resolved_position):
            msg = f"Agent position {resolved_position!r} is outside the world."
            raise PlacementError(msg)
        if world.is_wall(resolved_position):
            msg = f"Agent position {resolved_position!r} is inside a wall."
            raise PlacementError(msg)

        if isinstance(genome, SemanticGenome):
            resolved_genome = genome
        elif isinstance(genome, str):
            resolved_genome = SemanticGenome.from_compact(genome)
        else:
            resolved_genome = SemanticGenome.from_codons(tuple(genome))

        world.agent_position = resolved_position
        return cls(
            id=agent_id,
            genome=resolved_genome,
            codon_table=codon_table or CodonTable.default_minimal(),
            atp_account=ATPAccount(initial_atp=initial_atp),
            position=resolved_position,
            action_registry=action_registry or default_action_registry(),
            action_runtime_config=action_runtime_config or ActionRuntimeConfig(),
        )

    @property
    def atp_budget(self) -> ATPAccount:
        """Backward-compatible alias for earlier Lite API naming."""

        return self.atp_account

    @property
    def cursor(self) -> int:
        """Return the current genome cursor for snapshot/replay diagnostics."""

        return self._cursor

    @property
    def step_index(self) -> int:
        """Return the next step index for snapshot/replay diagnostics."""

        return self._step_index

    def restore_runtime_state(self, *, cursor: int, step_index: int) -> None:
        """Restore internal runtime counters from a replay snapshot."""

        if not 0 <= cursor < len(self.genome):
            msg = f"cursor {cursor} is outside genome range."
            raise ValueError(msg)
        if step_index < 0:
            msg = "step_index cannot be negative."
            raise ValueError(msg)
        self._cursor = cursor
        self._step_index = step_index

    def step(
        self,
        world: World2D,
        trace: Trace,
        *,
        blocked_positions: Iterable[Position] = (),
    ) -> TraceEvent:
        """Execute one codon and record every attempted action.

        ATP is debited before action handlers run. If ATP is insufficient, the
        handler is not called. Handlers cannot bypass ATPAccount, ATPLedgerEntry,
        or TraceEvent creation.
        """

        self._trace = trace
        blocked_set = frozenset(blocked_positions)
        world.agent_position = self.position
        codon_bits = self.genome.to_codons()[self._cursor]
        self._cursor = (self._cursor + 1) % len(self.genome)
        codon = self.codon_table.decode(codon_bits)
        action_name = codon.action_name
        atp_before = self.atp_account.current_atp
        position_before = self.position
        world_digest_before = world.digest()
        world_delta: dict[str, JsonValue] = {"action_cost": codon.cost}
        ledger_ids: list[int] = []

        debit_id = self.atp_account.debit(
            codon.cost,
            tick=self._step_index,
            agent_id=self.id,
            codon=codon_bits,
            action=action_name,
            reason="action_cost",
        )
        if debit_id is None and codon.cost > 0:
            world_delta["net_atp_delta"] = round(self.atp_account.current_atp - atp_before, 10)
            event = self._event(
                codon_bits=codon_bits,
                action=action_name,
                atp_before=atp_before,
                atp_after=self.atp_account.current_atp,
                position_before=position_before,
                world_digest_before=world_digest_before,
                position_after=self.position,
                world_delta=world_delta,
                status="blocked",
                reason="insufficient_atp",
                ledger_entry_ids=(),
            )
            trace.append(event)
            return event
        if debit_id is not None:
            ledger_ids.append(debit_id)

        handler = self._resolve_handler(action_name=action_name, codon_bits=codon_bits)
        if handler is None:
            result = ActionResult(
                status="blocked",
                reason="unsupported_action",
                position_after=self.position,
                world_delta={"action_name": action_name},
            )
        else:
            result = handler(
                ActionContext(
                    agent_id=self.id,
                    position=self.position,
                    codon_bits=codon_bits,
                    action_name=action_name,
                    step_index=self._step_index,
                    world=world,
                    blocked_positions=tuple(sorted(blocked_set)),
                )
            )

        status: ActionStatus = self.action_runtime_config.validate_status(result.status)
        reason = result.reason
        position_after = result.position_after or self.position
        world_delta.update(result.world_delta or {})
        if (
            self.action_runtime_config.counts_as_executed(status)
            and position_after != self.position
            and position_after in blocked_set
        ):
            status = "blocked"
            reason = "occupied_blocked"
            world_delta.update(
                {
                    "target": list(position_after),
                    "movement": "occupied_blocked",
                    "blocked_by": "agent",
                }
            )
            position_after = self.position
        if result.energy is not None:
            status, reason = self._apply_energy_effect(
                energy=result.energy,
                status=status,
                reason=reason,
                world_delta=world_delta,
                ledger_ids=ledger_ids,
                codon_bits=codon_bits,
                action_name=action_name,
            )
        self._apply_result(
            world=world,
            action_name=action_name,
            position_after=position_after,
            status=status,
            reason=reason,
            world_delta=world_delta,
            ledger_ids=ledger_ids,
            codon_bits=codon_bits,
        )
        world_delta["net_atp_delta"] = round(self.atp_account.current_atp - atp_before, 10)

        event = self._event(
            codon_bits=codon_bits,
            action=action_name,
            atp_before=atp_before,
            atp_after=self.atp_account.current_atp,
            position_before=position_before,
            world_digest_before=world_digest_before,
            position_after=self.position,
            world_delta=world_delta,
            status=status,
            reason=reason,
            ledger_entry_ids=tuple(ledger_ids),
        )
        trace.append(event)
        return event

    def run(self, world: World2D, steps: int) -> Trace:
        """Run the agent for ``steps`` and return a new trace."""

        if steps < 0:
            msg = "steps cannot be negative."
            raise ValueError(msg)
        trace = Trace()
        for _ in range(steps):
            self.step(world, trace)
        return trace

    def run_trial(self, world: World2D, *, steps: int, explain: bool = False) -> RunResult:
        """Run a short single-agent trial and return clean Python objects."""

        trace = self.run(world, steps)
        explanation = self.explain_last_action() if explain and len(trace) > 0 else None
        return RunResult(agent=self, world=world, trace=trace, explanation=explanation)

    def observe(self, world: World2D) -> dict[str, JsonValue]:
        """Return a small deterministic observation."""

        return {
            "position": list(self.position),
            "cell": world.get_cell(self.position),
            "nearby_resource": world.nearby_resource(self.position),
            "nearby_wall": world.nearby_wall(self.position),
            "atp": self.atp_account.current_atp,
        }

    def state_digest(self) -> str:
        """Return a stable digest of agent state used by replay hash gates."""

        payload = {
            "id": self.id,
            "genome": self.genome.to_compact(),
            "position": list(self.position),
            "cursor": self._cursor,
            "step_index": self._step_index,
            "atp": self.atp_account.snapshot(),
            "actions": self.action_registry.names(),
            "profile": self.profile,
            "lineage_id": self.lineage_id,
            "parent_id": self.parent_id,
            "generation": self.generation,
        }
        return hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()

    def explain_last_action(self) -> Explanation:
        """Explain the latest traced action emitted by this agent."""

        if self._trace is None:
            msg = "No trace is available. Run step() or run() first."
            raise ReplayError(msg)

        selected_event = None
        for event in reversed(self._trace.events):
            if event.agent_id == self.id:
                selected_event = event
                break

        if selected_event is None:
            msg = f"No traced action is available for agent {self.id!r}."
            raise ReplayError(msg)

        local_trace = Trace()
        local_trace.append(selected_event)

        return CausalReplay.explain_last_action(
            local_trace,
            codon_table=self.codon_table,
            action_registry=self.action_registry,
        )

    def _resolve_handler(self, *, action_name: str, codon_bits: str) -> ActionHandler | None:
        handler = self.action_registry.get(action_name)
        if handler is not None:
            return handler
        try:
            default_action_name = CodonTable.default_minimal().decode(codon_bits).action_name
        except KeyError:
            return None
        fallback = self.action_registry.get(default_action_name)
        default_fallback = default_action_registry().get(default_action_name)
        if fallback is not None and fallback is not default_fallback:
            return fallback
        return None

    def _apply_energy_effect(
        self,
        *,
        energy: object,
        status: ActionStatus,
        reason: str,
        world_delta: dict[str, JsonValue],
        ledger_ids: list[int],
        codon_bits: str,
        action_name: str,
    ) -> tuple[ActionStatus, str]:
        from codontrace.actions import EnergyEffect, apply_energy_effect_to_atp

        if not isinstance(energy, EnergyEffect):
            msg = "ActionResult.energy must be an EnergyEffect instance."
            raise InsufficientATPError(msg)

        def _credit(
            amount: float, *, tick: int, entity_id: str, codon: str, action: str, reason: str
        ) -> int:
            return self.atp_account.credit(
                amount,
                tick=tick,
                agent_id=entity_id,
                codon=codon,
                action=action,
                reason=reason,
            )

        def _debit(
            amount: float, *, tick: int, entity_id: str, codon: str, action: str, reason: str
        ) -> int | None:
            return self.atp_account.debit(
                amount,
                tick=tick,
                agent_id=entity_id,
                codon=codon,
                action=action,
                reason=reason,
            )

        return apply_energy_effect_to_atp(
            energy=energy,
            credit=_credit,
            debit=_debit,
            tick=self._step_index,
            entity_id=self.id,
            codon_bits=codon_bits,
            action_name=action_name,
            status=status,
            reason=reason,
            world_delta=world_delta,
            ledger_ids=ledger_ids,
        )

    def _apply_result(
        self,
        *,
        world: World2D,
        action_name: str,
        position_after: Position,
        status: ActionStatus,
        reason: str,
        world_delta: dict[str, JsonValue],
        ledger_ids: list[int],
        codon_bits: str,
    ) -> None:
        if (
            self.action_runtime_config.counts_as_executed(status)
            and position_after != self.position
        ):
            if not world.in_bounds(position_after):
                msg = f"Action handler returned out-of-bounds position {position_after!r}."
                raise ValueError(msg)
            if world.is_wall(position_after):
                msg = f"Action handler returned wall position {position_after!r}."
                raise ValueError(msg)
            self.position = position_after
            world.agent_position = position_after
        if action_name in {"COLLECT_RESOURCE", "EAT_LUMEN"} and reason in {
            "resource_collected",
            "lumen_consumed",
        }:
            collected = world.collect_resource(self.position)
            credit_value = world_delta.get("resource_credit", collected)
            credit = float(credit_value) if isinstance(credit_value, int | float) else collected
            if credit > 0:
                credit_id = self.atp_account.credit(
                    credit,
                    tick=self._step_index,
                    agent_id=self.id,
                    codon=codon_bits,
                    action=action_name,
                    reason=reason,
                )
                ledger_ids.append(credit_id)
                world_delta["collected_atp"] = collected
                world_delta["resource_credit"] = credit
                if action_name == "EAT_LUMEN":
                    world_delta["lumen_interaction"] = True
        if action_name == "EMIT_NEXUS" and reason == "nexus_emitted":
            from codontrace.world import WorldObject

            world.add_object(
                self.position,
                WorldObject(kind="Nexus", amount=1.0, metadata={"source": self.id}),
            )
            world_delta["nexus_object_added"] = True

    def _event(
        self,
        *,
        codon_bits: str,
        action: str,
        atp_before: float,
        atp_after: float,
        position_before: Position,
        world_digest_before: str,
        position_after: Position,
        world_delta: dict[str, JsonValue],
        status: ActionStatus,
        reason: str,
        ledger_entry_ids: tuple[int, ...],
    ) -> TraceEvent:
        event = TraceEvent(
            step=self._step_index,
            agent_id=self.id,
            codon=codon_bits,
            action=action,
            atp_before=atp_before,
            atp_after=atp_after,
            position_before=position_before,
            position_after=position_after,
            world_delta=world_delta,
            status=status,
            reason=reason,
            ledger_entry_ids=ledger_entry_ids,
            genome_digest=self.genome.digest(),
            world_digest_before=world_digest_before,
        )
        self._step_index += 1
        return event


Agent = WhiteBoxAgent
