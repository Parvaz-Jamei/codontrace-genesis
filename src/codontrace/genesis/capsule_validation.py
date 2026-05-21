"""Capsule transfer validation protocols.

Emit/read/adopt counters are not proof of knowledge transfer. These helpers add
controlled ON/OFF, adoption-blocked, before/after, stale/false-capsule, and
locality reports that can be linked to evidence artifacts and claim gates.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import Enum

from codontrace._types import JsonValue


class CapsuleClaimDecision(str, Enum):
    ADOPTION_RECORDED_NO_TRANSFER_EFFECT = "adoption_recorded_no_transfer_effect"
    TRANSFER_EFFECT_SUPPORTED = "capsule_transfer_effect_supported"
    FALSE_CAPSULE_REJECTED = "false_capsule_rejected"
    LOCALITY_SUPPORTED = "locality_supported"


@dataclass(frozen=True, slots=True)
class CapsuleUsefulnessMetric:
    name: str
    before: float
    after: float

    @property
    def delta(self) -> float:
        return round(self.after - self.before, 10)

    def to_dict(self) -> dict[str, JsonValue]:
        return {"name": self.name, "before": self.before, "after": self.after, "delta": self.delta}


@dataclass(frozen=True, slots=True)
class CapsuleTransferAblation:
    name: str
    on_metric: float
    off_metric: float
    metric_name: str = "fitness"

    @property
    def delta(self) -> float:
        return round(self.on_metric - self.off_metric, 10)

    @property
    def supported(self) -> bool:
        return self.delta > 0

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "name": self.name,
            "metric_name": self.metric_name,
            "on_metric": self.on_metric,
            "off_metric": self.off_metric,
            "delta": self.delta,
            "supported": self.supported,
        }


@dataclass(frozen=True, slots=True)
class CapsuleAdoptionOutcome:
    adopted: bool
    useful: bool
    reason: str
    distance: int | None = None

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "adopted": self.adopted,
            "useful": self.useful,
            "reason": self.reason,
            "distance": self.distance,
        }


@dataclass(frozen=True, slots=True)
class CapsuleTransferEffectReport:
    ablation: CapsuleTransferAblation | None = None
    before_after: CapsuleUsefulnessMetric | None = None
    false_capsule_rejected: bool = False
    locality_respected: bool = False
    adoption_success_rate: float = 0.0
    decision: CapsuleClaimDecision = CapsuleClaimDecision.ADOPTION_RECORDED_NO_TRANSFER_EFFECT
    limitations: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "ablation": None if self.ablation is None else self.ablation.to_dict(),
            "before_after": None if self.before_after is None else self.before_after.to_dict(),
            "false_capsule_rejected": self.false_capsule_rejected,
            "locality_respected": self.locality_respected,
            "adoption_success_rate": self.adoption_success_rate,
            "decision": self.decision.value,
            "limitations": list(self.limitations),
        }

    def digest(self) -> str:
        return _digest(self.to_dict())


@dataclass(frozen=True, slots=True)
class CapsuleTransferExperiment:
    experiment_id: str
    metric_name: str = "fitness"
    metadata: dict[str, JsonValue] = field(default_factory=dict)

    def on_off_ablation(self, *, on_metric: float, off_metric: float) -> CapsuleTransferAblation:
        return CapsuleTransferAblation(
            f"{self.experiment_id}:capsule_on_vs_off", on_metric, off_metric, self.metric_name
        )

    def evaluate(
        self,
        *,
        ablation: CapsuleTransferAblation | None = None,
        before_after: CapsuleUsefulnessMetric | None = None,
        false_capsule_rejected: bool = False,
        locality_respected: bool = False,
        adoption_success_rate: float = 0.0,
    ) -> CapsuleTransferEffectReport:
        limitations: list[str] = []
        supported = (ablation is not None and ablation.supported) or (
            before_after is not None and before_after.delta > 0
        )
        if supported:
            decision = CapsuleClaimDecision.TRANSFER_EFFECT_SUPPORTED
        elif false_capsule_rejected:
            decision = CapsuleClaimDecision.FALSE_CAPSULE_REJECTED
        elif locality_respected:
            decision = CapsuleClaimDecision.LOCALITY_SUPPORTED
        else:
            decision = CapsuleClaimDecision.ADOPTION_RECORDED_NO_TRANSFER_EFFECT
            limitations.append("capsule_adoption_without_effect_is_not_transfer_proof")
        return CapsuleTransferEffectReport(
            ablation,
            before_after,
            false_capsule_rejected,
            locality_respected,
            adoption_success_rate,
            decision,
            tuple(limitations),
        )

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "experiment_id": self.experiment_id,
            "metric_name": self.metric_name,
            "metadata": dict(sorted(self.metadata.items())),
        }

    def digest(self) -> str:
        return _digest(self.to_dict())


def _digest(payload: Mapping[str, JsonValue]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()

# ---------------------------------------------------------------------------
# Causal capsule/packet hardening primitives (P0)
# ---------------------------------------------------------------------------
# These objects intentionally extend the existing Capsule validation layer.
# They do not introduce a parallel Packet runtime.  ``Packet*`` names are kept
# only as user-facing aliases because the library's canonical communication
# primitive is ``Capsule``.

from codontrace.genesis.canonical import canonical_digest, require_finite_float


@dataclass(frozen=True, slots=True)
class CapsuleAblationPolicy:
    """Fine-grained causal controls for capsule/packet mechanisms.

    A capsule can be transferred while individual causal channels are disabled.
    This lets experiments isolate whether observed gains came from transfer,
    source-fitness weighting, utility scoring, memory linkage, or behavior
    updates.  The policy is deterministic and digest-backed so it can be used in
    paired counterfactual runs without relying on runner-only metadata.
    """

    enable_capsule_transfer: bool = True
    enable_capsule_utility_scoring: bool = True
    enable_source_fitness_weighting: bool = True
    enable_signal_memory_link: bool = True
    enable_capsule_behavior_update: bool = True
    policy_id: str = "capsule_ablation_policy"
    schema_version: str = "capsule_ablation_policy_v1"

    # Backward/user-facing packet terminology supported as properties only.
    @property
    def enable_packet_transfer(self) -> bool:
        return self.enable_capsule_transfer

    @property
    def enable_packet_utility(self) -> bool:
        return self.enable_capsule_utility_scoring

    @property
    def enable_packet_source_fitness(self) -> bool:
        return self.enable_source_fitness_weighting

    @property
    def enable_packet_behavior_update(self) -> bool:
        return self.enable_capsule_behavior_update

    @property
    def disabled_controls(self) -> tuple[str, ...]:
        controls: list[str] = []
        if not self.enable_capsule_transfer:
            controls.append("disable_capsule_transfer")
        if not self.enable_capsule_utility_scoring:
            controls.append("disable_capsule_utility_scoring")
        if not self.enable_source_fitness_weighting:
            controls.append("disable_source_fitness_weighting")
        if not self.enable_signal_memory_link:
            controls.append("disable_signal_memory_link")
        if not self.enable_capsule_behavior_update:
            controls.append("disable_capsule_behavior_update")
        return tuple(controls)

    @property
    def claim_eligible(self) -> bool:
        # A policy is not evidence by itself; it becomes claim-relevant only when
        # paired with an outcome/intervention artifact.
        return False

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "schema_version": self.schema_version,
            "policy_id": self.policy_id,
            "enable_capsule_transfer": self.enable_capsule_transfer,
            "enable_capsule_utility_scoring": self.enable_capsule_utility_scoring,
            "enable_source_fitness_weighting": self.enable_source_fitness_weighting,
            "enable_signal_memory_link": self.enable_signal_memory_link,
            "enable_capsule_behavior_update": self.enable_capsule_behavior_update,
            "disabled_controls": list(self.disabled_controls),
            "claim_eligible": self.claim_eligible,
        }

    def digest(self) -> str:
        return canonical_digest(self.to_dict(), prefix="capsule_ablation_policy")


PacketAblationPolicy = CapsuleAblationPolicy


@dataclass(frozen=True, slots=True)
class CapsuleOutcomeWindow:
    """Deterministic delayed-outcome window for capsule effects."""

    window_ticks: int = 5
    track_survival: bool = True
    track_fitness_delta: bool = True
    track_reproduction_delta: bool = True
    track_memory_reuse: bool = True
    track_role_change: bool = True
    schema_version: str = "capsule_outcome_window_v1"

    def __post_init__(self) -> None:
        if self.window_ticks <= 0:
            raise ValueError("window_ticks must be positive")

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "schema_version": self.schema_version,
            "window_ticks": self.window_ticks,
            "track_survival": self.track_survival,
            "track_fitness_delta": self.track_fitness_delta,
            "track_reproduction_delta": self.track_reproduction_delta,
            "track_memory_reuse": self.track_memory_reuse,
            "track_role_change": self.track_role_change,
        }

    def digest(self) -> str:
        return canonical_digest(self.to_dict(), prefix="capsule_outcome_window")


PacketOutcomeWindow = CapsuleOutcomeWindow


@dataclass(frozen=True, slots=True)
class CapsuleDelayedOutcomeRecord:
    """Measured delayed utility after a capsule/signal is observed."""

    capsule_id: str
    target_organism_id: str
    signal_seen_tick: int
    outcome_start_tick: int
    outcome_end_tick: int
    window_digest: str
    policy_digest: str
    survival_delta: float = 0.0
    fitness_delta: float = 0.0
    reproduction_delta: float = 0.0
    memory_reuse_delta: float = 0.0
    role_changed: bool = False
    compared_control_digest: str | None = None
    blocked_reason: str | None = None
    schema_version: str = "capsule_delayed_outcome_record_v1"
    record_digest: str = ""

    def __post_init__(self) -> None:
        if not self.capsule_id or not self.target_organism_id:
            raise ValueError("capsule_id and target_organism_id are required")
        if self.signal_seen_tick < 0 or self.outcome_start_tick < self.signal_seen_tick or self.outcome_end_tick < self.outcome_start_tick:
            raise ValueError("outcome ticks must be ordered and non-negative")
        for attr in ("survival_delta", "fitness_delta", "reproduction_delta", "memory_reuse_delta"):
            object.__setattr__(self, attr, round(require_finite_float(attr, getattr(self, attr)), 10))
        if not self.record_digest:
            object.__setattr__(self, "record_digest", canonical_digest(self._payload(), prefix="capsule_outcome"))

    @property
    def claim_eligible(self) -> bool:
        return (
            not self.blocked_reason
            and bool(self.compared_control_digest)
            and (
                self.survival_delta > 0.0
                or self.fitness_delta > 0.0
                or self.reproduction_delta > 0.0
                or self.memory_reuse_delta > 0.0
                or self.role_changed
            )
        )

    def _payload(self) -> dict[str, JsonValue]:
        return {
            "schema_version": self.schema_version,
            "capsule_id": self.capsule_id,
            "target_organism_id": self.target_organism_id,
            "signal_seen_tick": self.signal_seen_tick,
            "outcome_start_tick": self.outcome_start_tick,
            "outcome_end_tick": self.outcome_end_tick,
            "window_digest": self.window_digest,
            "policy_digest": self.policy_digest,
            "survival_delta": self.survival_delta,
            "fitness_delta": self.fitness_delta,
            "reproduction_delta": self.reproduction_delta,
            "memory_reuse_delta": self.memory_reuse_delta,
            "role_changed": self.role_changed,
            "compared_control_digest": self.compared_control_digest,
            "blocked_reason": self.blocked_reason,
            "claim_eligible": self.claim_eligible,
        }

    def to_dict(self) -> dict[str, JsonValue]:
        return {**self._payload(), "record_digest": self.record_digest}

    def digest(self) -> str:
        return self.record_digest


PacketDelayedOutcomeRecord = CapsuleDelayedOutcomeRecord
