"""Configurable fitness signal registry for GENESIS experiments."""

from __future__ import annotations

import hashlib
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable

from codontrace._types import JsonValue
from codontrace._numeric import finite_float, finite_json_dumps
from codontrace.genesis.liveness import AliveGateResult
from codontrace.genesis.status import ActionStatusRegistry
from codontrace.trace import Trace, TraceEvent


@runtime_checkable
class FitnessSignalProtocol(Protocol):
    """Structural contract for extracting a numeric fitness signal."""

    @property
    def name(self) -> str:
        """Stable signal name for registered built-ins when available."""
        ...

    def extract(
        self,
        trace: Trace | Sequence[TraceEvent],
        organism: object | None = None,
        context: Mapping[str, object] | None = None,
    ) -> float:
        """Return one deterministic numeric signal."""


@dataclass(frozen=True, slots=True)
class FitnessSignal:
    """Weighted signal wrapper."""

    name: str
    weight: float
    extractor: (
        FitnessSignalProtocol
        | Callable[
            [Trace | Sequence[TraceEvent], object | None, Mapping[str, object] | None], float
        ]
    )
    serializable: bool = True

    def __post_init__(self) -> None:
        if not self.name:
            msg = "FitnessSignal.name must not be empty."
            raise ValueError(msg)
        object.__setattr__(self, "weight", finite_float("FitnessSignal.weight", self.weight))

    def extract(
        self,
        trace: Trace | Sequence[TraceEvent],
        organism: object | None = None,
        context: Mapping[str, object] | None = None,
    ) -> float:
        if isinstance(self.extractor, FitnessSignalProtocol):
            return float(self.extractor.extract(trace, organism, context))
        return float(self.extractor(trace, organism, context))

    def to_dict(self) -> dict[str, JsonValue]:
        if not self.serializable:
            msg = f"FitnessSignal {self.name!r} is not serializable."
            raise ValueError(msg)
        return {"name": self.name, "weight": self.weight}


@dataclass(frozen=True, slots=True)
class _SurvivalTicksSignal:
    name: str = "survival_ticks"

    def extract(
        self,
        trace: Trace | Sequence[TraceEvent],
        organism: object | None = None,
        context: Mapping[str, object] | None = None,
    ) -> float:
        alive = _alive(context)
        return float(alive.survived_ticks if alive is not None else 0.0)


@dataclass(frozen=True, slots=True)
class _LumenEatenSignal:
    name: str = "lumen_eaten"

    def extract(
        self,
        trace: Trace | Sequence[TraceEvent],
        organism: object | None = None,
        context: Mapping[str, object] | None = None,
    ) -> float:
        events = tuple(trace.events if isinstance(trace, Trace) else trace)
        return float(
            sum(
                1
                for event in events
                if event.action == "EAT_LUMEN"
                and _status_registry(context).counts_as_executed(event.status)
                and event.world_delta.get("lumen_interaction") is True
            )
        )


@dataclass(frozen=True, slots=True)
class _NexusEmittedSignal:
    name: str = "nexus_emitted"

    def extract(
        self,
        trace: Trace | Sequence[TraceEvent],
        organism: object | None = None,
        context: Mapping[str, object] | None = None,
    ) -> float:
        events = tuple(trace.events if isinstance(trace, Trace) else trace)
        return float(
            sum(
                1
                for event in events
                if event.action == "EMIT_NEXUS"
                and _status_registry(context).counts_as_executed(event.status)
            )
        )


@dataclass(frozen=True, slots=True)
class _BlockedActionSignal:
    name: str = "blocked_actions"

    def extract(
        self,
        trace: Trace | Sequence[TraceEvent],
        organism: object | None = None,
        context: Mapping[str, object] | None = None,
    ) -> float:
        alive = _alive(context)
        return float(alive.blocked_actions if alive is not None else 0.0)


@dataclass(frozen=True, slots=True)
class _ReproductionSignal:
    name: str = "reproduction_events"

    def extract(
        self,
        trace: Trace | Sequence[TraceEvent],
        organism: object | None = None,
        context: Mapping[str, object] | None = None,
    ) -> float:
        events = tuple(trace.events if isinstance(trace, Trace) else trace)
        return float(
            sum(1 for event in events if event.world_delta.get("reproduction_succeeded") is True)
        )


class FitnessSignalRegistry:
    """Immutable registry of built-in or user-supplied fitness signals."""

    def __init__(self, signals: tuple[FitnessSignal, ...] = ()) -> None:
        mapping: dict[str, FitnessSignal] = {}
        for signal in signals:
            if signal.name in mapping:
                msg = f"Duplicate fitness signal {signal.name!r}."
                raise ValueError(msg)
            mapping[signal.name] = signal
        self._signals = mapping

    @classmethod
    def genesis_v0(cls) -> FitnessSignalRegistry:
        return cls(
            (
                FitnessSignal("survival_ticks", 1.0, _SurvivalTicksSignal()),
                FitnessSignal("lumen_eaten", 2.0, _LumenEatenSignal()),
                FitnessSignal("nexus_emitted", 1.0, _NexusEmittedSignal()),
                FitnessSignal("blocked_actions", -0.5, _BlockedActionSignal()),
                FitnessSignal("reproduction_events", 8.0, _ReproductionSignal()),
            )
        )

    def add_signal(
        self,
        name: str,
        extractor: FitnessSignalProtocol
        | Callable[
            [Trace | Sequence[TraceEvent], object | None, Mapping[str, object] | None], float
        ],
        *,
        weight: float = 1.0,
        serializable: bool = False,
    ) -> FitnessSignalRegistry:
        if name in self._signals:
            msg = f"Fitness signal {name!r} is already registered."
            raise ValueError(msg)
        return FitnessSignalRegistry(
            (*self._signals.values(), FitnessSignal(name, weight, extractor, serializable))
        )

    def signals(self) -> tuple[FitnessSignal, ...]:
        return tuple(self._signals[key] for key in sorted(self._signals))

    def score(
        self,
        trace: Trace | Sequence[TraceEvent],
        organism: object | None = None,
        context: Mapping[str, object] | None = None,
    ) -> float:
        return round(
            sum(
                signal.extract(trace, organism, context) * signal.weight
                for signal in self.signals()
            ),
            10,
        )

    def to_dict(self) -> dict[str, JsonValue]:
        return {"signals": [signal.to_dict() for signal in self.signals()]}

    @classmethod
    def from_dict(cls, data: dict[str, JsonValue]) -> FitnessSignalRegistry:
        base = {signal.name: signal for signal in cls.genesis_v0().signals()}
        raw = data.get("signals")
        if not isinstance(raw, list):
            msg = "FitnessSignalRegistry.signals must be a list."
            raise ValueError(msg)
        signals: list[FitnessSignal] = []
        for item in raw:
            if not isinstance(item, dict):
                msg = "FitnessSignal entries must be objects."
                raise ValueError(msg)
            name = item.get("name")
            weight = item.get("weight")
            if (
                not isinstance(name, str)
                or isinstance(weight, bool)
                or not isinstance(weight, int | float)
            ):
                msg = "FitnessSignal entries require name and numeric weight."
                raise ValueError(msg)
            if name not in base:
                msg = f"Unknown serializable fitness signal {name!r}."
                raise ValueError(msg)
            signals.append(FitnessSignal(name, finite_float("FitnessSignal.weight", weight), base[name].extractor))
        return cls(tuple(signals))

    def digest(self) -> str:
        payload = finite_json_dumps(self.to_dict(), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _alive(context: Mapping[str, object] | None) -> AliveGateResult | None:
    if context is None:
        return None
    value = context.get("alive_result")
    return value if isinstance(value, AliveGateResult) else None


def _status_registry(context: Mapping[str, object] | None) -> ActionStatusRegistry:
    if context is not None:
        value = context.get("status_registry")
        if isinstance(value, ActionStatusRegistry):
            return value
    return ActionStatusRegistry.genesis_v0()


@dataclass(frozen=True, slots=True)
class FitnessComponentValue:
    """One normalized, direction-aware continuous fitness component."""

    name: str
    raw: float
    normalized: float
    weight: float
    polarity: str  # reward | penalty
    weighted: float
    normalizer: str
    status: str  # available | missing | clipped | invalid

    def __post_init__(self) -> None:
        for field_name in ("raw", "normalized", "weight", "weighted"):
            object.__setattr__(self, field_name, finite_float(f"FitnessComponentValue.{field_name}", getattr(self, field_name)))
        if self.polarity not in {"reward", "penalty"}:
            msg = "FitnessComponentValue.polarity must be 'reward' or 'penalty'."
            raise ValueError(msg)
        if self.status not in {"available", "missing", "clipped", "invalid"}:
            msg = "Unsupported FitnessComponentValue.status."
            raise ValueError(msg)

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "name": self.name,
            "raw": self.raw,
            "normalized": self.normalized,
            "weight": self.weight,
            "polarity": self.polarity,
            "weighted": self.weighted,
            "normalizer": self.normalizer,
            "status": self.status,
        }

    def digest(self) -> str:
        return _digest(self.to_dict())


@dataclass(frozen=True, slots=True)
class FitnessScorerConfig:
    """Experiment-defined normalized fitness formula.

    Negative weights are rejected; use ``polarity='penalty'`` to express a
    component that should reduce total score. This keeps the formula auditable.
    """

    weights: tuple[tuple[str, float], ...]
    normalization_policy: str = "clip_0_1"
    missing_policy: str = "zero"  # zero | null | fail
    version: str = "fitness_scorer_v2"

    def __post_init__(self) -> None:
        if self.normalization_policy != "clip_0_1":
            msg = "Only clip_0_1 normalization is implemented in Phase 1."
            raise ValueError(msg)
        if self.missing_policy not in {"zero", "null", "fail"}:
            msg = "missing_policy must be zero, null, or fail."
            raise ValueError(msg)
        seen: set[str] = set()
        for name, weight in self.weights:
            if not name:
                msg = "FitnessScorerConfig component names must not be empty."
                raise ValueError(msg)
            if name in seen:
                msg = f"Duplicate fitness component {name!r}."
                raise ValueError(msg)
            seen.add(name)
            finite_float(f"FitnessScorerConfig.weights[{name}]", weight, non_negative=True)

    @classmethod
    def phase1_default(cls) -> FitnessScorerConfig:
        return cls(
            weights=(
                ("alive_score", 1.0),
                ("survival_ticks_score", 1.0),
                ("atp_efficiency_score", 0.5),
                ("resource_gain_score", 1.0),
                ("action_success_score", 0.5),
                ("reproduction_score", 1.0),
                ("novelty_score", 0.5),
                ("qd_score", 0.5),
                ("genome_complexity_penalty", 0.25),
                ("blocked_penalty", 0.5),
            )
        )

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "weights": [[name, weight] for name, weight in self.weights],
            "normalization_policy": self.normalization_policy,
            "missing_policy": self.missing_policy,
            "version": self.version,
        }

    def digest(self) -> str:
        return _digest(self.to_dict())


@dataclass(frozen=True, slots=True)
class FitnessComponentWeights:
    """Policy-configurable component weights for runner-defined landscapes."""

    weights: tuple[tuple[str, float], ...] = ()
    schema_version: str = "fitness_component_weights_v1"

    def __post_init__(self) -> None:
        clean: list[tuple[str, float]] = []
        for name, weight in self.weights:
            if not name:
                raise ValueError("FitnessComponentWeights names must not be empty.")
            clean.append((name, finite_float(f"FitnessComponentWeights[{name}]", weight)))
        object.__setattr__(self, "weights", tuple(clean))

    def to_dict(self) -> dict[str, JsonValue]:
        return {"schema_version": self.schema_version, "weights": [[k, v] for k, v in self.weights]}

    def digest(self) -> str:
        return _digest(self.to_dict())


@dataclass(frozen=True, slots=True)
class FitnessLandscapeConfig:
    """Layered fitness policy; library computes components, runner chooses meaning."""

    viability_enabled: bool = True
    task_components_enabled: bool = True
    selection_score_enabled: bool = True
    reporting_score_enabled: bool = True
    component_weights: FitnessComponentWeights = field(default_factory=FitnessComponentWeights)
    schema_version: str = "fitness_landscape_config_v1"

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "schema_version": self.schema_version,
            "viability_enabled": self.viability_enabled,
            "task_components_enabled": self.task_components_enabled,
            "selection_score_enabled": self.selection_score_enabled,
            "reporting_score_enabled": self.reporting_score_enabled,
            "component_weights": self.component_weights.to_dict(),
        }

    def digest(self) -> str:
        return _digest(self.to_dict())


@dataclass(frozen=True, slots=True)
class FitnessAuditRecord:
    organism_id: str
    tick: int
    selection_score_before_gate: float
    selection_score_after_gate: float
    viability_gate: float
    viability_gate_reason: str
    weighted_component_sum: float
    dominant_component: str | None = None
    zero_score_reason: str | None = None
    schema_version: str = "fitness_audit_record_v1"

    def __post_init__(self) -> None:
        for field_name in ("selection_score_before_gate", "selection_score_after_gate", "viability_gate", "weighted_component_sum"):
            object.__setattr__(self, field_name, finite_float(f"FitnessAuditRecord.{field_name}", getattr(self, field_name)))

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "schema_version": self.schema_version,
            "organism_id": self.organism_id,
            "tick": self.tick,
            "selection_score_before_gate": self.selection_score_before_gate,
            "selection_score_after_gate": self.selection_score_after_gate,
            "viability_gate": self.viability_gate,
            "viability_gate_reason": self.viability_gate_reason,
            "weighted_component_sum": self.weighted_component_sum,
            "dominant_component": self.dominant_component,
            "zero_score_reason": self.zero_score_reason,
        }

    def digest(self) -> str:
        return _digest(self.to_dict())


@dataclass(frozen=True, slots=True)
class FitnessComponent:
    """Backward-compatible simple fitness component."""

    name: str
    value: float
    weight: float = 1.0
    reason: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "value", finite_float("FitnessComponent.value", self.value))
        object.__setattr__(self, "weight", finite_float("FitnessComponent.weight", self.weight))

    @property
    def contribution(self) -> float:
        return round(self.value * self.weight, 10)

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "name": self.name,
            "value": self.value,
            "weight": self.weight,
            "contribution": self.contribution,
            "reason": self.reason,
        }


@dataclass(frozen=True, slots=True)
class FitnessBreakdown:
    """Auditable deterministic fitness score breakdown.

    This is backward-compatible with the earlier ``components,total`` shape but
    can now also carry normalized component values and scorer metadata.
    """

    components: tuple[FitnessComponent | FitnessComponentValue, ...]
    total: float | None = None
    organism_id: str = ""
    tick: int = 0
    config_digest: str = ""
    formula_version: str = "fitness_scorer_v2"
    caveat: str = "experiment_defined_fitness_not_universal_life_score"

    def __post_init__(self) -> None:
        if self.total is None:
            total = 0.0
            for item in self.components:
                if isinstance(item, FitnessComponentValue):
                    total += item.weighted
                else:
                    total += item.contribution
            object.__setattr__(self, "total", finite_float("FitnessBreakdown.total", round(total, 10)))
        else:
            object.__setattr__(self, "total", finite_float("FitnessBreakdown.total", self.total))
        if not self.config_digest:
            object.__setattr__(
                self,
                "config_digest",
                _digest(
                    {
                        "formula_version": self.formula_version,
                        "components": [c.to_dict() for c in self.components],
                    }
                ),
            )

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "organism_id": self.organism_id,
            "tick": self.tick,
            "components": [item.to_dict() for item in self.components],
            "total": self.total,
            "config_digest": self.config_digest,
            "formula_version": self.formula_version,
            "caveat": self.caveat,
        }

    def digest(self) -> str:
        return _digest(self.to_dict())


@dataclass(frozen=True, slots=True)
class TaskFitnessComponent:
    """Named task-sensitive component before normalization."""

    name: str
    raw_value: float
    weight: float = 1.0
    status: str = "measured"  # measured | provisional | unavailable

    def __post_init__(self) -> None:
        object.__setattr__(self, "raw_value", finite_float("TaskFitnessComponent.raw_value", self.raw_value))
        object.__setattr__(self, "weight", finite_float("TaskFitnessComponent.weight", self.weight))
        if self.status not in {"measured", "provisional", "unavailable"}:
            raise ValueError("Unsupported TaskFitnessComponent.status")

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "name": self.name,
            "raw_value": self.raw_value,
            "weight": self.weight,
            "status": self.status,
        }

    def digest(self) -> str:
        return _digest(self.to_dict())


@dataclass(frozen=True, slots=True)
class FitnessLandscapeScore:
    """Collection of task components observed on one landscape/world."""

    organism_id: str
    components: tuple[TaskFitnessComponent, ...]
    landscape_digest: str = ""

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "organism_id": self.organism_id,
            "components": [item.to_dict() for item in self.components],
            "landscape_digest": self.landscape_digest,
        }

    def digest(self) -> str:
        return _digest(self.to_dict())


@dataclass(frozen=True, slots=True)
class SelectionFitnessScore:
    """Selection-facing score separated from raw AliveGate survival."""

    organism_id: str
    viability_gate: float
    weighted_component_sum: float
    selection_score: float
    breakdown_digest: str
    status: str = "measured"
    viability_gate_reason: str = "not_audited"
    alive_gate_digest: str = ""
    selection_score_before_gate: float = 0.0
    selection_score_after_gate: float = 0.0

    def __post_init__(self) -> None:
        for field_name in ("viability_gate", "weighted_component_sum", "selection_score", "selection_score_before_gate", "selection_score_after_gate"):
            object.__setattr__(self, field_name, finite_float(f"SelectionFitnessScore.{field_name}", getattr(self, field_name)))

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "organism_id": self.organism_id,
            "viability_gate": self.viability_gate,
            "weighted_component_sum": self.weighted_component_sum,
            "selection_score": self.selection_score,
            "breakdown_digest": self.breakdown_digest,
            "status": self.status,
            "viability_gate_reason": self.viability_gate_reason,
            "alive_gate_digest": self.alive_gate_digest,
            "selection_score_before_gate": self.selection_score_before_gate,
            "selection_score_after_gate": self.selection_score_after_gate,
        }

    def digest(self) -> str:
        return _digest(self.to_dict())


def task_sensitive_raw_metrics(
    *,
    alive_result: AliveGateResult,
    lumen_eaten: int = 0,
    blocked_actions: int = 0,
    reproduction_events: int = 0,
    memory_write_count: int = 0,
    memory_read_count: int = 0,
    delayed_reward_count: int = 0,
    capsules_emitted: int = 0,
    capsules_read: int = 0,
    capsules_adopted: int = 0,
    social_interaction_count: int = 0,
    cooperation_events: int = 0,
    role_persistence: float = 0.0,
    tool_chain_stage: int = 0,
    generalization_score: float = 0.0,
    novelty_score: float = 0.0,
) -> dict[str, float]:
    """Return the standard task-sensitive raw metric map.

    AliveGate contributes only the viability gate; useful behavior must come from
    task, memory, social, capsule, tool-chain, generalization, novelty, and energy
    components.
    """

    survival = float(alive_result.survived_ticks)
    resource = float(lumen_eaten)
    hazard_avoidance = max(0.0, survival - float(blocked_actions))
    capsule_utility = float(capsules_adopted * 2 + capsules_read + capsules_emitted * 0.25)
    social = float(social_interaction_count)
    homeostasis = max(0.0, float(alive_result.final_runtime_atp))
    energy_efficiency = max(0.0, homeostasis / max(1.0, survival))
    return {
        "viability_score": 1.0 if alive_result.passed else 0.0,
        "survival_score": survival,
        "resource_score": resource,
        "hazard_avoidance_score": hazard_avoidance,
        "memory_score": float(memory_write_count) + 0.5 * float(memory_read_count),
        "delayed_reward_score": float(delayed_reward_count),
        "capsule_utility_score": capsule_utility,
        "social_score": social,
        "cooperation_score": float(cooperation_events),
        "role_specialization_score": float(role_persistence),
        "tool_chain_score": float(tool_chain_stage),
        "homeostasis_score": homeostasis,
        "generalization_score": float(generalization_score),
        "novelty_score": float(novelty_score),
        "energy_efficiency_score": energy_efficiency,
        "reproduction_score": float(reproduction_events),
        "blocked_penalty": float(blocked_actions),
    }


def evaluate_task_sensitive_fitness(
    raw_metrics: Mapping[str, float | None],
    *,
    organism_id: str = "",
    tick: int = 0,
    viability_gate: float | None = None,
) -> tuple[FitnessBreakdown, SelectionFitnessScore]:
    weights = (
        ("survival_score", 0.7),
        ("resource_score", 1.0),
        ("hazard_avoidance_score", 0.7),
        ("memory_score", 0.5),
        ("delayed_reward_score", 1.2),
        ("capsule_utility_score", 0.8),
        ("social_score", 0.6),
        ("cooperation_score", 0.8),
        ("role_specialization_score", 0.5),
        ("tool_chain_score", 1.2),
        ("homeostasis_score", 0.4),
        ("generalization_score", 1.0),
        ("novelty_score", 0.5),
        ("energy_efficiency_score", 0.4),
        ("reproduction_score", 0.6),
        ("blocked_penalty", 0.4),
    )
    config = FitnessScorerConfig(weights=weights, version="task_sensitive_selection_v1")
    breakdown = evaluate_fitness_breakdown(
        raw_metrics, config=config, organism_id=organism_id, tick=tick
    )
    raw_gate = raw_metrics.get("viability_score", 0.0) if viability_gate is None else viability_gate
    gate = finite_float("viability_gate", raw_gate if isinstance(raw_gate, (int, float)) and not isinstance(raw_gate, bool) else 0.0)
    gate = max(0.0, min(1.0, gate))
    weighted_sum = float(breakdown.total or 0.0)
    selection_score = round(gate * weighted_sum, 10)
    if gate <= 0.0:
        gate_reason = "alive_gate_failed"
    elif gate >= 1.0:
        gate_reason = "alive_gate_passed"
    else:
        gate_reason = "partial_viability_gate"
    alive_gate_digest = _digest(
        {
            "organism_id": organism_id,
            "tick": tick,
            "viability_gate": gate,
            "raw_viability_score": raw_metrics.get("viability_score", 0.0),
        }
    )
    score = SelectionFitnessScore(
        organism_id=organism_id,
        viability_gate=gate,
        weighted_component_sum=round(weighted_sum, 10),
        selection_score=selection_score,
        breakdown_digest=breakdown.digest(),
        status="measured",
        viability_gate_reason=gate_reason,
        alive_gate_digest=alive_gate_digest,
        selection_score_before_gate=round(weighted_sum, 10),
        selection_score_after_gate=selection_score,
    )
    return breakdown, score


_PHASE1_POLARITY: dict[str, str] = {
    "viability_score": "reward",
    "survival_score": "reward",
    "resource_score": "reward",
    "hazard_avoidance_score": "reward",
    "memory_score": "reward",
    "delayed_reward_score": "reward",
    "capsule_utility_score": "reward",
    "social_score": "reward",
    "cooperation_score": "reward",
    "role_specialization_score": "reward",
    "tool_chain_score": "reward",
    "homeostasis_score": "reward",
    "generalization_score": "reward",
    "energy_efficiency_score": "reward",
    "alive_score": "reward",
    "survival_ticks_score": "reward",
    "atp_efficiency_score": "reward",
    "resource_gain_score": "reward",
    "action_success_score": "reward",
    "reproduction_score": "reward",
    "novelty_score": "reward",
    "qd_score": "reward",
    "lineage_persistence_score": "reward",
    "genome_complexity_penalty": "penalty",
    "blocked_penalty": "penalty",
    "toxicity_penalty": "penalty",
}

_PHASE1_NORMALIZERS: dict[str, float] = {
    "viability_score": 1.0,
    "survival_score": 100.0,
    "resource_score": 20.0,
    "hazard_avoidance_score": 100.0,
    "memory_score": 20.0,
    "delayed_reward_score": 10.0,
    "capsule_utility_score": 20.0,
    "social_score": 20.0,
    "cooperation_score": 20.0,
    "role_specialization_score": 1.0,
    "tool_chain_score": 8.0,
    "homeostasis_score": 100.0,
    "generalization_score": 1.0,
    "energy_efficiency_score": 10.0,
    "alive_score": 1.0,
    "survival_ticks_score": 100.0,
    "atp_efficiency_score": 1.0,
    "resource_gain_score": 100.0,
    "action_success_score": 1.0,
    "reproduction_score": 10.0,
    "novelty_score": 1.0,
    "qd_score": 1.0,
    "lineage_persistence_score": 100.0,
    "genome_complexity_penalty": 512.0,
    "blocked_penalty": 1.0,
    "toxicity_penalty": 1.0,
}


def build_fitness_component_value(
    *,
    name: str,
    raw: float | None,
    weight: float,
    polarity: str | None = None,
    normalizer: float | None = None,
    missing_policy: str = "zero",
) -> FitnessComponentValue:
    """Factory for a normalized phase-1 fitness component."""

    weight = finite_float("fitness component weight", weight, non_negative=True)
    resolved_polarity = polarity or _PHASE1_POLARITY.get(name, "reward")
    if resolved_polarity not in {"reward", "penalty"}:
        msg = "unknown fitness component polarity"
        raise ValueError(msg)
    denom = finite_float("fitness normalizer", normalizer if normalizer is not None else _PHASE1_NORMALIZERS.get(name, 1.0))
    if denom <= 0:
        msg = "normalizer must be positive."
        raise ValueError(msg)
    status = "available"
    raw_value = raw
    if raw_value is None:
        if missing_policy == "fail":
            msg = f"missing required fitness component {name!r}."
            raise ValueError(msg)
        status = "missing"
        raw_value = 0.0
    raw_value = finite_float(f"fitness component raw[{name}]", raw_value)
    normalized_unclipped = raw_value / denom
    normalized = max(0.0, min(1.0, normalized_unclipped))
    if normalized != normalized_unclipped and status == "available":
        status = "clipped"
    if resolved_polarity == "reward":
        weighted = abs(weight) * normalized
    elif resolved_polarity == "penalty":
        weighted = -abs(weight) * normalized
    else:  # pragma: no cover - kept for defensive clarity
        raise ValueError("unknown fitness component polarity")
    return FitnessComponentValue(
        name=name,
        raw=round(float(raw_value), 10),
        normalized=round(normalized, 10),
        weight=round(float(weight), 10),
        polarity=resolved_polarity,
        weighted=round(weighted, 10),
        normalizer=f"clip_0_1/{denom:g}",
        status=status,
    )


def evaluate_fitness_breakdown(
    raw_metrics: Mapping[str, float | None],
    *,
    config: FitnessScorerConfig | None = None,
    organism_id: str = "",
    tick: int = 0,
) -> FitnessBreakdown:
    """Evaluate normalized continuous fitness from experiment-defined metrics."""

    resolved = config or FitnessScorerConfig.phase1_default()
    components = tuple(
        build_fitness_component_value(
            name=name,
            raw=raw_metrics.get(name),
            weight=weight,
            missing_policy=resolved.missing_policy,
        )
        for name, weight in resolved.weights
    )
    return FitnessBreakdown(
        organism_id=organism_id,
        tick=tick,
        components=components,
        total=None,
        config_digest=resolved.digest(),
        formula_version=resolved.version,
    )


def _json_number(value: JsonValue, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise ValueError(f"{field} must be numeric")
    return finite_float(field, value)  # type: ignore[return-value]


def _json_int(value: JsonValue, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{field} must be an integer")
    return value


def _json_str(value: JsonValue, field: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{field} must be a string")
    return value


def fitness_breakdown_from_dict(data: Mapping[str, JsonValue]) -> FitnessBreakdown:
    """Import a FitnessBreakdown and validate its digest by reconstruction."""

    raw_components = data.get("components")
    if not isinstance(raw_components, list):
        raise ValueError("FitnessBreakdown.components must be a list.")
    components: list[FitnessComponent | FitnessComponentValue] = []
    for item in raw_components:
        if not isinstance(item, Mapping):
            raise ValueError("FitnessBreakdown component entries must be objects.")
        name = _json_str(item.get("name"), "component.name")
        if "raw" in item:
            components.append(
                FitnessComponentValue(
                    name=name,
                    raw=_json_number(item.get("raw"), "component.raw"),
                    normalized=_json_number(item.get("normalized"), "component.normalized"),
                    weight=_json_number(item.get("weight"), "component.weight"),
                    polarity=_json_str(item.get("polarity"), "component.polarity"),
                    weighted=_json_number(item.get("weighted"), "component.weighted"),
                    normalizer=_json_str(item.get("normalizer"), "component.normalizer"),
                    status=_json_str(item.get("status"), "component.status"),
                )
            )
        else:
            components.append(
                FitnessComponent(
                    name=name,
                    value=_json_number(item.get("value"), "component.value"),
                    weight=_json_number(item.get("weight", 1.0), "component.weight"),
                    reason=_json_str(item.get("reason", ""), "component.reason"),
                )
            )
    total_raw = data.get("total")
    obj = FitnessBreakdown(
        components=tuple(components),
        total=None if total_raw is None else _json_number(total_raw, "total"),
        organism_id=_json_str(data.get("organism_id", ""), "organism_id"),
        tick=_json_int(data.get("tick", 0), "tick"),
        config_digest=_json_str(data.get("config_digest", ""), "config_digest"),
        formula_version=_json_str(
            data.get("formula_version", "fitness_scorer_v2"), "formula_version"
        ),
        caveat=_json_str(
            data.get("caveat", "experiment_defined_fitness_not_universal_life_score"), "caveat"
        ),
    )
    expected = _json_str(data.get("digest", obj.digest()), "digest")
    if expected != obj.digest():
        raise ValueError("FitnessBreakdown digest mismatch")
    return obj


@dataclass(frozen=True, slots=True)
class GenesisFitnessV1:
    """GENESIS-aligned scaffold fitness, not an artificial-life proof."""

    survival_weight: float = 1.0
    atp_efficiency_weight: float = 0.1
    reproduction_weight: float = 8.0
    resource_weight: float = 2.0
    causal_prediction_weight: float = 0.5
    capsule_activity_weight: float = 0.25
    genome_length_penalty: float = 0.0

    def evaluate(
        self,
        *,
        trace: Trace | Sequence[TraceEvent],
        alive_result: AliveGateResult,
        genome_length: int = 0,
        causal_prediction_accuracy: float | None = None,
        capsules_emitted: int = 0,
        capsules_read: int = 0,
        capsules_adopted: int = 0,
    ) -> FitnessBreakdown:
        events = tuple(trace.events if isinstance(trace, Trace) else trace)
        lumen_eaten = sum(1 for event in events if event.action == "EAT_LUMEN")
        reproduction = sum(
            1 for event in events if event.world_delta.get("reproduction_succeeded") is True
        )
        mean_atp = sum(event.atp_after for event in events) / len(events) if events else 0.0
        components = [
            FitnessComponent(
                "survival_ticks", float(alive_result.survived_ticks), self.survival_weight
            ),
            FitnessComponent("atp_efficiency", round(mean_atp, 10), self.atp_efficiency_weight),
            FitnessComponent("reproduction_success", float(reproduction), self.reproduction_weight),
            FitnessComponent("resource_gain", float(lumen_eaten), self.resource_weight),
            FitnessComponent(
                "capsule_activity",
                float(capsules_emitted + capsules_read + capsules_adopted),
                self.capsule_activity_weight,
            ),
        ]
        if causal_prediction_accuracy is not None:
            components.append(
                FitnessComponent(
                    "causal_prediction_accuracy",
                    causal_prediction_accuracy,
                    self.causal_prediction_weight,
                )
            )
        if self.genome_length_penalty:
            components.append(
                FitnessComponent(
                    "genome_length_penalty", float(genome_length), -abs(self.genome_length_penalty)
                )
            )
        total = round(sum(item.contribution for item in components), 10)
        return FitnessBreakdown(components=tuple(components), total=total)


def _digest(payload: Mapping[str, JsonValue]) -> str:
    encoded = finite_json_dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()
