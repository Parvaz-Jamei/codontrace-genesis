"""GENESIS Foundation organism runner."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import cast

from codontrace._types import JsonValue, Position
from codontrace.actions import (
    ActionContext,
    ActionRegistry,
    ActionResult,
    ActionRuntimeConfig,
    ActionStatus,
    default_action_registry,
)
from codontrace.errors import ConfigurationError, PlacementError
from codontrace.genesis.adf_runtime import ADFExecutionPolicy, ADFMacroRegistry
from codontrace.genesis.atp import GenesisATPState
from codontrace.genesis.causal_graph import CausalGraph
from codontrace.genesis.causal_runtime import (
    CausalPrediction,
    CausalUpdateInput,
    CausalUpdateResult,
    evaluate_prediction,
    predict_next_outcome,
    update_causal_graph_from_step,
)
from codontrace.genesis.learning import LearningATPConfig
from codontrace.genesis.liveness import AliveGateConfig, AliveGateResult, evaluate_alive
from codontrace.genesis.memory import (
    EpisodicEvent,
    EpisodicMemory,
    EpisodicMemoryConfig,
    MemoryWriteResult,
)
from codontrace.genesis.ribosome import (
    BrainTokenSource,
    CodonExecutionRecord,
    CompiledBrain,
    CompiledToken,
    Ribosome,
    TranslationResult,
)
from codontrace.genesis.translation_profile import (
    TranslationPolicy,
    TranslationProfile,
    resolve_translation_action,
)
from codontrace.genome import SemanticGenome
from codontrace.specs import GenomeSpec
from codontrace.trace import Trace, TraceEvent
from codontrace.world import World2D, WorldObject


@dataclass(frozen=True, slots=True)
class BrainStepResult:
    """Runtime contract for one compiled-token execution step."""

    event: TraceEvent
    token_index: int

    @property
    def status(self) -> str:
        return self.event.status

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "event": self.event.to_dict(),
            "token_index": self.token_index,
            "contract": "BrainStep",
        }


@dataclass(frozen=True, slots=True)
class OrganismTickResult:
    """Runtime contract for a bounded organism brain tick.

    In phase 1 this is a bounded sequence of BrainStep executions, not yet the
    full synchronous GENESIS perception-memory-causal loop.
    """

    organism_id: str
    brain_steps: tuple[BrainStepResult, ...]
    trace: Trace
    runtime_atp_before: float
    runtime_atp_after: float
    stopped_reason: str

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "organism_id": self.organism_id,
            "brain_steps": [step.to_dict() for step in self.brain_steps],
            "trace": self.trace.to_bundle(),
            "runtime_atp_before": self.runtime_atp_before,
            "runtime_atp_after": self.runtime_atp_after,
            "stopped_reason": self.stopped_reason,
            "contract": "OrganismTick",
        }


@dataclass(frozen=True, slots=True)
class PopulationTickResult:
    """Runtime contract placeholder for population-level ticks.

    Population stepping remains generation-oriented in phase 1; this value type
    gives UI/replay callers an explicit name for future synchronous population
    ticks without changing ``step_population`` behavior.
    """

    generation: int
    tick: int
    organism_ticks: tuple[OrganismTickResult, ...] = ()
    stopped_reason: str = "not_integrated_in_phase1"
    feature_status: str = "provisional"

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "generation": self.generation,
            "tick": self.tick,
            "organism_ticks": [item.to_dict() for item in self.organism_ticks],
            "stopped_reason": self.stopped_reason,
            "feature_status": self.feature_status,
            "contract": "PopulationTick",
        }


@dataclass(slots=True)
class GenesisOrganism:
    """Small wrapper for the GENESIS Phase 1 execution path.

    The formal path is NexusGenome -> Ribosome -> CompiledBrain -> ATP_runtime
    execution -> TraceEvent. This class is intentionally separate from
    WhiteBoxAgent so the beginner API remains backward compatible.
    """

    id: str
    genome: SemanticGenome
    ribosome: Ribosome
    compiled_brain: CompiledBrain
    atp_state: GenesisATPState
    position: Position
    vitae_store: float = 0.0
    action_registry: ActionRegistry = field(default_factory=default_action_registry)
    action_runtime_config: ActionRuntimeConfig = field(default_factory=ActionRuntimeConfig)
    episodic_memory: EpisodicMemory | None = None
    memory_config: EpisodicMemoryConfig = field(default_factory=EpisodicMemoryConfig)
    learning_config: LearningATPConfig = field(default_factory=LearningATPConfig)
    causal_graph: CausalGraph | None = None
    execution_source_enabled: bool = False
    adf_macro_registry: ADFMacroRegistry | None = None
    adf_execution_policy: ADFExecutionPolicy = field(default_factory=ADFExecutionPolicy)
    translation_profile: TranslationProfile | None = None
    translation_policy: TranslationPolicy = field(default_factory=TranslationPolicy)
    _cursor: int = field(default=0, init=False, repr=False)
    _step_index: int = field(default=0, init=False, repr=False)

    def __post_init__(self) -> None:
        if not self.id:
            msg = "GenesisOrganism.id must not be empty."
            raise ConfigurationError(msg)
        if self.vitae_store < 0:
            msg = "vitae_store cannot be negative."
            raise ConfigurationError(msg)

    @classmethod
    def from_bits(
        cls,
        organism_id: str,
        genome_bits: str,
        *,
        initial_runtime_atp: float = 5.0,
        position: Position = (0, 0),
        ribosome: Ribosome | None = None,
        initial_learning_atp: float = 0.0,
        learning_enabled: bool = False,
        causal_graph: CausalGraph | None = None,
        action_registry: ActionRegistry | None = None,
        action_runtime_config: ActionRuntimeConfig | None = None,
        memory_config: EpisodicMemoryConfig | None = None,
        execution_source_enabled: bool = False,
        adf_macro_registry: ADFMacroRegistry | None = None,
        adf_execution_policy: ADFExecutionPolicy | None = None,
        translation_profile: TranslationProfile | None = None,
        translation_policy: TranslationPolicy | None = None,
    ) -> GenesisOrganism:
        """Create a GENESIS organism from Nexus genome bits."""

        resolved_ribosome = ribosome or Ribosome.genesis_v0()
        translation = resolved_ribosome.translate(genome_bits)
        genome = _genome_from_translation(translation, resolved_ribosome)
        return cls(
            id=organism_id,
            genome=genome,
            ribosome=resolved_ribosome,
            compiled_brain=translation.compiled_brain,
            atp_state=GenesisATPState.from_runtime(
                initial_runtime_atp,
                learning_atp=initial_learning_atp,
                learning_enabled=learning_enabled or initial_learning_atp > 0,
            ),
            position=position,
            causal_graph=causal_graph,
            action_registry=action_registry or default_action_registry(),
            action_runtime_config=action_runtime_config or ActionRuntimeConfig(),
            memory_config=memory_config or EpisodicMemoryConfig(),
            execution_source_enabled=execution_source_enabled,
            adf_macro_registry=adf_macro_registry,
            adf_execution_policy=adf_execution_policy or ADFExecutionPolicy(),
            translation_profile=translation_profile,
            translation_policy=translation_policy or TranslationPolicy(),
        )

    def run(
        self,
        world: World2D,
        *,
        ticks: int,
        alive_config: AliveGateConfig | None = None,
        blocked_positions: Iterable[Position] = (),
    ) -> GenesisRunResult:
        """Run compiled tokens for a fixed number of ticks and evaluate AliveGate."""

        if ticks < 0:
            msg = "ticks cannot be negative."
            raise ConfigurationError(msg)
        self._ensure_position(world, self.position)
        trace = Trace()
        for _ in range(ticks):
            self.step(world, trace, blocked_positions=blocked_positions)
        alive_result = evaluate_alive(
            trace,
            final_runtime_atp=self.atp_state.runtime_available,
            config=alive_config,
        )
        return GenesisRunResult(
            organism_id=self.id,
            compiled_brain=self.compiled_brain,
            trace=trace,
            alive_result=alive_result,
        )

    def step(
        self,
        world: World2D,
        trace: Trace,
        *,
        blocked_positions: Iterable[Position] = (),
    ) -> TraceEvent:
        """Execute one precompiled token with runtime ATP safety.

        This method is the phase-1 ``BrainStep`` contract: one call advances one
        compiled token and remains backward-compatible with earlier releases.
        Use ``step_brain_tick()`` when a caller wants a bounded multi-token
        organism tick.
        """

        self._ensure_position(world, self.position)
        blocked_set = frozenset(blocked_positions)
        token = self.compiled_brain.tokens[self._cursor]
        self._cursor = (self._cursor + 1) % len(self.compiled_brain.tokens)
        atp_before = self.atp_state.runtime_available
        position_before = self.position
        world.agent_position = self.position
        world_digest_before = world.digest()
        base_action = token.action
        resolved_action = resolve_translation_action(
            token.bits,
            base_action,
            self.translation_profile,
            self.translation_policy,
        )
        action_name = resolved_action or base_action
        action_sequence: tuple[str, ...] = (action_name,)
        source_override = token.source
        adf_expansion_digest: str | None = None
        adf_expanded_sources: tuple[BrainTokenSource, ...] = ()
        if self.adf_macro_registry is not None and action_name.startswith("ADF_"):
            next_registry, expansion = self.adf_macro_registry.expand(
                action_name, self.adf_execution_policy
            )
            self.adf_macro_registry = next_registry
            adf_expansion_digest = expansion.digest()
            if expansion.executed and expansion.expanded_actions:
                action_sequence = tuple(expansion.expanded_actions)
                action_name = action_sequence[0]
                adf_expanded_sources = tuple(expansion.expanded_sources)
                source_override = (
                    expansion.expanded_sources[0] if expansion.expanded_sources else token.source
                )
            else:
                action_sequence = ()
        prediction = predict_next_outcome(self.causal_graph, action_name)
        world_delta: dict[str, JsonValue] = {
            "action_cost": token.cost,
            "base_action": base_action,
            "resolved_action": action_name,
            "translation_profile_digest": None
            if self.translation_profile is None
            else self.translation_profile.digest,
            "translation_policy": self.translation_policy.to_dict(),
            "adf_macro_registry_digest": None
            if self.adf_macro_registry is None
            else self.adf_macro_registry.digest(),
            "adf_expansion_digest": adf_expansion_digest,
            "adf_expanded_actions": list(action_sequence),
            "adf_expanded_sources": [source.to_dict() for source in adf_expanded_sources],
            "compiled_token_index": token.index,
            "compiled_brain_digest": self.compiled_brain.digest(),
            "causal_prediction_attempted": prediction.predicted_outcome is not None,
            "causal_prediction_confidence": prediction.confidence,
            "causal_prediction_expected": prediction.predicted_outcome,
            "causal_prediction_graph_digest": prediction.graph_digest,
            "causal_prediction_reason": prediction.reason,
        }
        source_token = CompiledToken(
            bits=token.bits,
            action=action_name,
            cost=token.cost,
            index=token.index,
            source=source_override,
        )
        ledger_ids: list[int] = []
        debit_id = self.atp_state.debit_runtime(
            token.cost,
            tick=self._step_index,
            organism_id=self.id,
            codon=token.bits,
            action=base_action,
        )
        if debit_id is None and token.cost > 0:
            event = self._event(
                codon_bits=token.bits,
                action=action_name,
                atp_before=atp_before,
                atp_after=self.atp_state.runtime_available,
                position_before=position_before,
                position_after=self.position,
                world_digest_before=world_digest_before,
                world_delta={
                    **world_delta,
                    "net_atp_delta": round(self.atp_state.runtime_available - atp_before, 10),
                },
                status="blocked",
                reason="insufficient_runtime_atp",
                ledger_entry_ids=(),
            )
            event = self._maybe_attach_execution_source(event, source_token)
            trace.append(event)
            learning_before = self.atp_state.learning_available
            memory_result = self._maybe_write_memory(event)
            if memory_result is not None:
                event = _with_memory_delta(
                    event,
                    memory_result,
                    atp_learning_before=learning_before,
                    atp_learning_after=self.atp_state.learning_available,
                )
                trace._events[-1] = event
            event = self._maybe_update_causal_graph(event, prediction, memory_result)
            trace._events[-1] = event
            return event
        if debit_id is not None:
            ledger_ids.append(debit_id)

        handler = None if not action_sequence else self.action_registry.get(action_name)
        if handler is None:
            result = ActionResult.blocked(
                reason="unsupported_action" if action_sequence else "invalid_adf_macro",
                position_after=self.position,
                world_delta={"action_name": action_name, "base_action": base_action},
            )
        else:
            result = handler(
                ActionContext(
                    agent_id=self.id,
                    position=self.position,
                    codon_bits=token.bits,
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
            and position_after in blocked_set
            and position_after != self.position
        ):
            status = "blocked"
            reason = "occupied_blocked"
            world_delta.update({"target": list(position_after), "movement": "occupied_blocked"})
            position_after = self.position
        if result.energy is not None:
            status, reason = self._apply_energy_effect(
                energy=result.energy,
                status=status,
                reason=reason,
                world_delta=world_delta,
                ledger_ids=ledger_ids,
                codon_bits=token.bits,
                action_name=action_name,
            )
        if (
            self.action_runtime_config.counts_as_executed(status)
            and position_after != self.position
        ):
            self._ensure_position(world, position_after)
            self.position = position_after
            world.agent_position = position_after
        self._apply_genesis_effects(
            world=world,
            action=action_name,
            reason=reason,
            ledger_ids=ledger_ids,
            codon_bits=token.bits,
            world_delta=world_delta,
        )
        primitive_statuses: list[dict[str, JsonValue]] = []
        primitive_event_digests: list[str] = []
        for primitive_index, primitive_action in enumerate(action_sequence[1:], start=1):
            primitive_ledger_start = len(ledger_ids)
            primitive_position_before = self.position
            primitive_atp_before = self.atp_state.runtime_available
            primitive_world_digest_before = world.digest()
            primitive_handler = self.action_registry.get(primitive_action)
            if primitive_handler is None:
                primitive_status: ActionStatus = "blocked"
                primitive_reason = "unsupported_action"
                primitive_position = self.position
                primitive_delta: dict[str, JsonValue] = {"action_name": primitive_action}
            else:
                primitive_result = primitive_handler(
                    ActionContext(
                        agent_id=self.id,
                        position=self.position,
                        codon_bits=token.bits,
                        action_name=primitive_action,
                        step_index=self._step_index,
                        world=world,
                        blocked_positions=tuple(sorted(blocked_set)),
                    )
                )
                primitive_status = self.action_runtime_config.validate_status(primitive_result.status)
                primitive_reason = primitive_result.reason
                primitive_position = primitive_result.position_after or self.position
                primitive_delta = dict(primitive_result.world_delta or {})
                if (
                    self.action_runtime_config.counts_as_executed(primitive_status)
                    and primitive_position in blocked_set
                    and primitive_position != self.position
                ):
                    primitive_status = "blocked"
                    primitive_reason = "occupied_blocked"
                    primitive_delta.update({"target": list(primitive_position), "movement": "occupied_blocked"})
                    primitive_position = self.position
                if primitive_result.energy is not None:
                    primitive_status, primitive_reason = self._apply_energy_effect(
                        energy=primitive_result.energy,
                        status=primitive_status,
                        reason=primitive_reason,
                        world_delta=primitive_delta,
                        ledger_ids=ledger_ids,
                        codon_bits=token.bits,
                        action_name=primitive_action,
                    )
            if (
                self.action_runtime_config.counts_as_executed(primitive_status)
                and primitive_position != self.position
            ):
                self._ensure_position(world, primitive_position)
                self.position = primitive_position
                world.agent_position = primitive_position
            self._apply_genesis_effects(
                world=world,
                action=primitive_action,
                reason=primitive_reason,
                ledger_ids=ledger_ids,
                codon_bits=token.bits,
                world_delta=primitive_delta,
            )
            primitive_atp_after = self.atp_state.runtime_available
            primitive_ledger_ids = tuple(ledger_ids[primitive_ledger_start:])
            primitive_event_payload: dict[str, JsonValue] = {
                "primitive_index": primitive_index,
                "action": primitive_action,
                "status": primitive_status,
                "reason": primitive_reason,
                "position_before": [primitive_position_before[0], primitive_position_before[1]],
                "position_after": [self.position[0], self.position[1]],
                "atp_before": primitive_atp_before,
                "atp_after": primitive_atp_after,
                "world_digest_before": primitive_world_digest_before,
                "world_digest_after": world.digest(),
                "world_delta": cast(JsonValue, dict(sorted(primitive_delta.items()))),
                "ledger_entry_ids": list(primitive_ledger_ids),
            }
            primitive_digest = _stable_payload_digest(primitive_event_payload)
            primitive_event_digests.append(primitive_digest)
            energy_credit = max(0.0, round(primitive_atp_after - primitive_atp_before, 10))
            energy_debit_extra = max(0.0, round(primitive_atp_before - primitive_atp_after, 10))
            world_delta[f"adf_primitive_{primitive_index}_delta"] = cast(JsonValue, primitive_delta)
            world_delta[f"adf_primitive_{primitive_index}_action"] = primitive_action
            world_delta[f"adf_primitive_{primitive_index}_status"] = primitive_status
            world_delta[f"adf_primitive_{primitive_index}_reason"] = primitive_reason
            world_delta[f"adf_primitive_{primitive_index}_position_before"] = [primitive_position_before[0], primitive_position_before[1]]
            world_delta[f"adf_primitive_{primitive_index}_position_after"] = [self.position[0], self.position[1]]
            world_delta[f"adf_primitive_{primitive_index}_energy_credit"] = energy_credit
            world_delta[f"adf_primitive_{primitive_index}_energy_debit_extra"] = energy_debit_extra
            world_delta[f"adf_primitive_{primitive_index}_ledger_entry_ids"] = list(primitive_ledger_ids)
            world_delta[f"adf_primitive_{primitive_index}_effect_digest"] = primitive_digest
            primitive_statuses.append(
                {
                    "action": primitive_action,
                    "status": primitive_status,
                    "reason": primitive_reason,
                    "event_digest": primitive_digest,
                    "energy_credit": energy_credit,
                    "energy_debit_extra": energy_debit_extra,
                    "ledger_entry_ids": list(primitive_ledger_ids),
                }
            )
        if primitive_statuses:
            failed = [i for i, row in enumerate(primitive_statuses, start=1) if self.action_runtime_config.counts_as_failed(str(row.get("status", "")))]
            blocked = [i for i, row in enumerate(primitive_statuses, start=1) if self.action_runtime_config.counts_as_blocked(str(row.get("status", "")))]
            if failed:
                idx = failed[0]
                status = "failed"
                reason = f"adf_primitive_failed:{idx}:{primitive_statuses[idx - 1].get('reason', 'unknown')}"
            elif blocked:
                idx = blocked[0]
                status = "blocked"
                reason = f"adf_primitive_blocked:{idx}:{primitive_statuses[idx - 1].get('reason', 'unknown')}"
            else:
                reason = "adf_all_primitives_executed"
            world_delta["adf_primitive_statuses"] = cast(JsonValue, primitive_statuses)
            world_delta["adf_aggregate_status"] = status
            world_delta["adf_aggregate_reason"] = reason
            world_delta["adf_primitive_event_digests"] = cast(JsonValue, primitive_event_digests)
            world_delta["adf_primitive_commit_digest"] = _stable_payload_digest({"primitive_statuses": cast(JsonValue, primitive_statuses)})
            world_delta["adf_primitive_count"] = len(primitive_statuses)
            world_delta["adf_primitive_failed_count"] = len(failed)
            world_delta["adf_primitive_blocked_count"] = len(blocked)
        world_delta["net_atp_delta"] = round(self.atp_state.runtime_available - atp_before, 10)
        world_delta["world_digest_after"] = world.digest()
        event = self._event(
            codon_bits=token.bits,
            action=action_name,
            atp_before=atp_before,
            atp_after=self.atp_state.runtime_available,
            position_before=position_before,
            position_after=self.position,
            world_digest_before=world_digest_before,
            world_delta=world_delta,
            status=status,
            reason=reason,
            ledger_entry_ids=tuple(ledger_ids),
        )
        event = self._maybe_attach_execution_source(event, source_token)
        trace.append(event)
        learning_before = self.atp_state.learning_available
        memory_result = self._maybe_write_memory(event)
        if memory_result is not None:
            event = _with_memory_delta(
                event,
                memory_result,
                atp_learning_before=learning_before,
                atp_learning_after=self.atp_state.learning_available,
            )
            trace._events[-1] = event
        event = self._maybe_update_causal_graph(event, prediction, memory_result)
        trace._events[-1] = event
        return event

    def step_brain_tick(
        self,
        world: World2D,
        trace: Trace | None = None,
        *,
        max_tokens: int | None = None,
        max_runtime_atp: float | None = None,
        blocked_positions: Iterable[Position] = (),
    ) -> OrganismTickResult:
        """Execute a bounded multi-token organism brain tick.

        ``max_tokens=None`` means one full pass over the currently compiled
        brain. ``max_runtime_atp`` is a spending guard checked against the next
        token's declared cost before it is attempted. The full synchronous
        GENESIS tick loop remains a phase-2 integration target.
        """

        if max_tokens is not None and max_tokens < 0:
            msg = "max_tokens cannot be negative."
            raise ConfigurationError(msg)
        if max_runtime_atp is not None and max_runtime_atp < 0:
            msg = "max_runtime_atp cannot be negative."
            raise ConfigurationError(msg)
        resolved_trace = trace or Trace()
        token_limit = len(self.compiled_brain.tokens) if max_tokens is None else max_tokens
        runtime_before = self.atp_state.runtime_available
        spent = 0.0
        steps: list[BrainStepResult] = []
        stopped_reason = "max_tokens_reached"
        for _ in range(token_limit):
            token = self.compiled_brain.tokens[self._cursor]
            if max_runtime_atp is not None and spent + token.cost > max_runtime_atp:
                stopped_reason = "max_runtime_atp_reached"
                break
            token_index = token.index
            before_step = self.atp_state.runtime_available
            event = self.step(world, resolved_trace, blocked_positions=blocked_positions)
            spent += max(0.0, before_step - self.atp_state.runtime_available)
            steps.append(BrainStepResult(event=event, token_index=token_index))
        else:
            if token_limit == 0:
                stopped_reason = "max_tokens_zero"
        return OrganismTickResult(
            organism_id=self.id,
            brain_steps=tuple(steps),
            trace=resolved_trace,
            runtime_atp_before=runtime_before,
            runtime_atp_after=self.atp_state.runtime_available,
            stopped_reason=stopped_reason,
        )

    def _maybe_attach_execution_source(self, event: TraceEvent, token: object) -> TraceEvent:
        """Attach CodonExecutionRecord payloads when source-map tracing is enabled.

        ADF expansion is replay-critical source attribution: every primitive
        action expanded from a macro receives its own ``CodonExecutionRecord``
        in ``world_delta["codon_execution_records"]``. Non-ADF tokens keep the
        original single-record compatibility field.
        """

        if not self.execution_source_enabled:
            return event
        source = getattr(token, "source", None)
        delta = dict(event.world_delta)
        adf_records = self._adf_execution_records(event, token, source)
        if adf_records:
            delta["codon_execution_records"] = cast(
                JsonValue, [record.to_dict() for record in adf_records]
            )
            delta["codon_execution_record_digests"] = cast(
                JsonValue, [record.digest() for record in adf_records]
            )
            return TraceEvent(
                step=event.step,
                agent_id=event.agent_id,
                codon=event.codon,
                action=event.action,
                atp_before=event.atp_before,
                atp_after=event.atp_after,
                position_before=event.position_before,
                position_after=event.position_after,
                world_delta=delta,
                status=event.status,
                reason=event.reason,
                ledger_entry_ids=event.ledger_entry_ids,
                genome_digest=event.genome_digest,
                world_digest_before=event.world_digest_before,
                cause_refs=event.cause_refs,
                config_hash=event.config_hash,
            )
        if source is None:
            return event
        record = self._build_execution_record(
            event,
            token,
            source,
            resolved_action=event.action,
            action_status=event.status,
            primitive_index=None,
        )
        delta["codon_execution_record"] = record.to_dict()
        delta["codon_execution_record_digest"] = record.digest()
        return TraceEvent(
            step=event.step,
            agent_id=event.agent_id,
            codon=event.codon,
            action=event.action,
            atp_before=event.atp_before,
            atp_after=event.atp_after,
            position_before=event.position_before,
            position_after=event.position_after,
            world_delta=delta,
            status=event.status,
            reason=event.reason,
            ledger_entry_ids=event.ledger_entry_ids,
            genome_digest=event.genome_digest,
            world_digest_before=event.world_digest_before,
            cause_refs=event.cause_refs,
            config_hash=event.config_hash,
        )

    def _adf_execution_records(
        self, event: TraceEvent, token: object, fallback_source: object
    ) -> tuple[CodonExecutionRecord, ...]:
        actions_raw = event.world_delta.get("adf_expanded_actions")
        sources_raw = event.world_delta.get("adf_expanded_sources")
        if not isinstance(actions_raw, list) or not isinstance(sources_raw, list):
            return ()
        if len(actions_raw) <= 1 or len(sources_raw) != len(actions_raw):
            return ()
        primitive_statuses = event.world_delta.get("adf_primitive_statuses")
        statuses = primitive_statuses if isinstance(primitive_statuses, list) else []
        records: list[CodonExecutionRecord] = []
        for index, action_raw in enumerate(actions_raw):
            source_raw = sources_raw[index]
            if isinstance(source_raw, dict):
                source = BrainTokenSource.from_dict(source_raw)
            elif isinstance(fallback_source, BrainTokenSource):
                source = fallback_source
            else:
                continue
            status = event.status
            if index > 0 and index - 1 < len(statuses):
                status_raw = statuses[index - 1]
                if isinstance(status_raw, dict):
                    status = str(status_raw.get("status", status))
            records.append(
                self._build_execution_record(
                    event,
                    token,
                    source,
                    resolved_action=str(action_raw),
                    action_status=status,
                    primitive_index=index,
                )
            )
        return tuple(records)

    def _build_execution_record(
        self,
        event: TraceEvent,
        token: object,
        source: BrainTokenSource,
        *,
        resolved_action: str,
        action_status: str,
        primitive_index: int | None,
    ) -> CodonExecutionRecord:
        context_payload: dict[str, JsonValue] = {
            "world_digest_before": event.world_digest_before,
            "position_before": list(event.position_before),
            "position_after": list(event.position_after),
            "compiled_brain_digest": self.compiled_brain.digest(),
            "resolved_action": resolved_action,
        }
        if primitive_index is not None:
            context_payload["primitive_index"] = primitive_index
            context_payload["adf_expansion_digest"] = event.world_delta.get("adf_expansion_digest")
        import hashlib
        import json

        context_digest = hashlib.sha256(
            json.dumps(context_payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
        base_ref = event_digest(event)
        trace_event_ref = (
            base_ref if primitive_index is None else f"{base_ref}#primitive-{primitive_index}"
        )
        return CodonExecutionRecord(
            organism_id=self.id,
            tick=event.step,
            token_index=int(getattr(token, "index", 0)),
            source=source,
            resolved_action=resolved_action,
            action_status=action_status,
            atp_before=event.atp_before,
            atp_after=event.atp_after,
            context_digest=context_digest,
            trace_event_ref=trace_event_ref,
        )

    def _maybe_write_memory(self, event: TraceEvent) -> MemoryWriteResult | None:
        if self.episodic_memory is None:
            return None
        learning_before = self.atp_state.learning_available
        episodic_event = EpisodicEvent(
            tick=event.step,
            organism_id=self.id,
            action=event.action,
            status=event.status,
            position_before=event.position_before,
            position_after=event.position_after,
            atp_runtime_before=event.atp_before,
            atp_runtime_after=event.atp_after,
            atp_learning_before=learning_before,
            atp_learning_after=learning_before,
            world_digest_before=event.world_digest_before,
            trace_event_digest=event_digest(event),
            observation={
                "codon": event.codon,
                "genome_digest": event.genome_digest,
            },
            outcome={
                "reason": event.reason,
                "world_delta": dict(event.world_delta),
            },
        )
        result = self.episodic_memory.write_event(
            episodic_event,
            self.atp_state,
            cost=self.learning_config.memory_write_cost
            if self.learning_config.learning_enabled
            else 0.0,
        )
        if result.written and self.episodic_memory.events:
            written = self.episodic_memory.events[-1]
            updated = EpisodicEvent(
                tick=written.tick,
                organism_id=written.organism_id,
                action=written.action,
                status=written.status,
                position_before=written.position_before,
                position_after=written.position_after,
                atp_runtime_before=written.atp_runtime_before,
                atp_runtime_after=written.atp_runtime_after,
                atp_learning_before=learning_before,
                atp_learning_after=self.atp_state.learning_available,
                world_digest_before=written.world_digest_before,
                trace_event_digest=written.trace_event_digest,
                observation=written.observation,
                outcome=written.outcome,
            )
            self.episodic_memory._events[-1] = updated
        return result

    def _maybe_update_causal_graph(
        self,
        event: TraceEvent,
        prediction: CausalPrediction,
        memory_result: MemoryWriteResult | None,
    ) -> TraceEvent:
        """Attach one step to the optional CausalGraph and audit the result."""

        memory_event_id = None
        if (
            memory_result is not None
            and memory_result.written
            and self.episodic_memory is not None
            and self.episodic_memory.events
        ):
            memory_event_id = self.episodic_memory.events[-1].digest()
        update_input = CausalUpdateInput(
            organism_id=self.id,
            tick=event.step,
            action=event.action,
            action_status=event.status,
            blocked_reason=event.reason if event.status == "blocked" else None,
            energy_delta=round(event.atp_after - event.atp_before, 10),
            resource_delta=_numeric_world_delta(
                event.world_delta, "resource_credit", fallback_key="collected_atp"
            ),
            position_before=event.position_before,
            position_after=event.position_after,
            memory_event_id=memory_event_id,
        )
        result = update_causal_graph_from_step(
            self.causal_graph,
            update_input,
            atp_learning_state=self.atp_state,
            config=None if self.causal_graph is None else self.causal_graph.config,
        )
        evaluation = evaluate_prediction(prediction, event.status)
        return _with_causal_delta(event, result, prediction, evaluation)

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
            raise ConfigurationError(msg)

        def _credit(
            amount: float, *, tick: int, entity_id: str, codon: str, action: str, reason: str
        ) -> int:
            return self.atp_state.credit_runtime(
                amount,
                tick=tick,
                organism_id=entity_id,
                codon=codon,
                action=action,
                reason=reason,
            )

        def _debit(
            amount: float, *, tick: int, entity_id: str, codon: str, action: str, reason: str
        ) -> int | None:
            return self.atp_state.debit_runtime(
                amount,
                tick=tick,
                organism_id=entity_id,
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
            insufficient_reason="insufficient_runtime_atp_for_energy_effect",
        )

    def _apply_genesis_effects(
        self,
        *,
        world: World2D,
        action: str,
        reason: str,
        ledger_ids: list[int],
        codon_bits: str,
        world_delta: dict[str, JsonValue],
    ) -> None:
        if action == "EAT_LUMEN" and reason == "lumen_consumed":
            collected = world.collect_resource(self.position)
            credit_value = world_delta.get("resource_credit", collected)
            credit = float(credit_value) if isinstance(credit_value, int | float) else collected
            if credit > 0:
                credit_id = self.atp_state.credit_runtime(
                    credit,
                    tick=self._step_index,
                    organism_id=self.id,
                    codon=codon_bits,
                    action=action,
                    reason="lumen_consumed",
                )
                ledger_ids.append(credit_id)
                world_delta["collected_atp"] = collected
                world_delta["resource_credit"] = credit
                world_delta["lumen_interaction"] = True
        if action == "EMIT_NEXUS" and reason == "nexus_emitted":
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
        position_after: Position,
        world_digest_before: str,
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

    @staticmethod
    def _ensure_position(world: World2D, position: Position) -> None:
        if not world.in_bounds(position):
            msg = f"Position {position!r} is outside the world."
            raise PlacementError(msg)
        if world.is_wall(position):
            msg = f"Position {position!r} is inside a wall."
            raise PlacementError(msg)


def _genome_from_translation(translation: TranslationResult, ribosome: Ribosome) -> SemanticGenome:
    """Build a digestable genome view from the actual decoded token bits."""

    decoded_codons = tuple(token.bits for token in translation.compiled_brain.tokens)
    decoded_bits = "".join(decoded_codons)
    widths = {len(codon) for codon in decoded_codons}
    base_spec = ribosome.codon_table.spec.genome_spec
    if len(widths) == 1:
        width = next(iter(widths))
        spec = (
            base_spec
            if base_spec.codon_width == width
            else GenomeSpec(codon_width=width, alphabet=base_spec.alphabet, name=f"binary{width}")
        )
        return SemanticGenome.from_compact(decoded_bits, spec=spec)
    # SemanticGenome is fixed-width by design. For mixed-width ADF programs we
    # keep a stable compact representation without truncating back to binary3;
    # the executable contract remains the CompiledBrain produced by the ribosome.
    variable_spec = GenomeSpec(
        codon_width=1,
        alphabet=base_spec.alphabet,
        name=f"{base_spec.name}_variable_decoded",
    )
    return SemanticGenome.from_compact(decoded_bits, spec=variable_spec)


def _with_memory_delta(
    event: TraceEvent,
    result: MemoryWriteResult,
    *,
    atp_learning_before: float,
    atp_learning_after: float,
) -> TraceEvent:
    """Return a TraceEvent whose world_delta exposes memory-write audit data."""

    delta = dict(event.world_delta)
    delta.update(
        {
            "memory_write_attempted": True,
            "memory_write_succeeded": result.written,
            "memory_write_blocked_reason": result.blocked_reason,
            "memory_size_before": result.memory_size_before,
            "memory_size_after": result.memory_size_after,
            "memory_digest_before": result.memory_digest_before,
            "memory_digest_after": result.memory_digest_after,
            "learning_ledger_entry_id": result.learning_ledger_entry_id,
            "atp_learning_before": round(atp_learning_before, 10),
            "atp_learning_after": round(atp_learning_after, 10),
        }
    )
    return TraceEvent(
        step=event.step,
        agent_id=event.agent_id,
        codon=event.codon,
        action=event.action,
        atp_before=event.atp_before,
        atp_after=event.atp_after,
        position_before=event.position_before,
        position_after=event.position_after,
        world_delta=delta,
        status=event.status,
        reason=event.reason,
        ledger_entry_ids=event.ledger_entry_ids,
        genome_digest=event.genome_digest,
        world_digest_before=event.world_digest_before,
        cause_refs=event.cause_refs,
        config_hash=event.config_hash,
    )


def _with_causal_delta(
    event: TraceEvent,
    result: CausalUpdateResult,
    prediction: CausalPrediction,
    evaluation: object,
) -> TraceEvent:
    """Return a TraceEvent with causal runtime audit fields in world_delta."""

    delta = dict(event.world_delta)
    eval_dict = evaluation.to_dict() if hasattr(evaluation, "to_dict") else {}
    delta.update(
        {
            "causal_graph_update_attempted": result.attempted,
            "causal_graph_update_succeeded": result.success,
            "causal_graph_update_reason": result.reason,
            "causal_graph_digest_before": result.digest_before,
            "causal_graph_digest_after": result.digest_after,
            "causal_graph_nodes_before": result.nodes_before,
            "causal_graph_nodes_after": result.nodes_after,
            "causal_graph_edges_before": result.edges_before,
            "causal_graph_edges_after": result.edges_after,
            "causal_graph_learning_cost": result.cost_atp_learning,
            "causal_graph_learning_ledger_entry_id": result.learning_ledger_entry_id,
            "atp_learning_spent_causal": result.cost_atp_learning if result.success else 0.0,
            "causal_prediction_attempted": bool(eval_dict.get("predicted", False)),
            "causal_prediction_correct": eval_dict.get("correct"),
            "causal_prediction_observed": eval_dict.get("observed"),
            "causal_prediction_expected": prediction.predicted_outcome,
            "causal_prediction_confidence": prediction.confidence,
        }
    )
    return TraceEvent(
        step=event.step,
        agent_id=event.agent_id,
        codon=event.codon,
        action=event.action,
        atp_before=event.atp_before,
        atp_after=event.atp_after,
        position_before=event.position_before,
        position_after=event.position_after,
        world_delta=delta,
        status=event.status,
        reason=event.reason,
        ledger_entry_ids=event.ledger_entry_ids,
        genome_digest=event.genome_digest,
        world_digest_before=event.world_digest_before,
        cause_refs=event.cause_refs,
        config_hash=event.config_hash,
    )


def _numeric_world_delta(
    delta: dict[str, JsonValue], key: str, *, fallback_key: str | None = None
) -> float | None:
    value = delta.get(key)
    if not isinstance(value, int | float) and fallback_key is not None:
        value = delta.get(fallback_key)
    if isinstance(value, bool) or not isinstance(value, int | float):
        return None
    return float(value)


@dataclass(frozen=True, slots=True)
class GenesisRunResult:
    """Result returned by GenesisOrganism.run()."""

    organism_id: str
    compiled_brain: CompiledBrain
    trace: Trace
    alive_result: AliveGateResult

    def to_dict(self) -> dict[str, JsonValue]:
        """Return a JSON-friendly run result."""

        return {
            "organism_id": self.organism_id,
            "compiled_brain": self.compiled_brain.to_dict(),
            "trace": self.trace.to_bundle(),
            "alive_result": self.alive_result.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, JsonValue]) -> GenesisRunResult:
        compiled_raw = data.get("compiled_brain")
        trace_raw = data.get("trace")
        alive_raw = data.get("alive_result")
        if not isinstance(compiled_raw, dict):
            msg = "GenesisRunResult.compiled_brain must be an object."
            raise ConfigurationError(msg)
        if not isinstance(trace_raw, dict):
            msg = "GenesisRunResult.trace must be an object."
            raise ConfigurationError(msg)
        if not isinstance(alive_raw, dict):
            msg = "GenesisRunResult.alive_result must be an object."
            raise ConfigurationError(msg)
        return cls(
            organism_id=_required_str(data, "organism_id"),
            compiled_brain=CompiledBrain.from_dict(compiled_raw),
            trace=Trace.from_bundle(trace_raw),
            alive_result=AliveGateResult.from_dict(alive_raw),
        )


def _stable_payload_digest(payload: object) -> str:
    import hashlib
    import json

    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def event_digest(event: TraceEvent) -> str:
    """Return a stable digest for one trace event."""

    return _stable_payload_digest(event.to_dict())


def _required_str(data: dict[str, JsonValue], key: str) -> str:
    value = data.get(key)
    if not isinstance(value, str):
        msg = f"{key} must be a string."
        raise ConfigurationError(msg)
    return value
