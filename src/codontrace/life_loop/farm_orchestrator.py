"""INN-05 — FARM fault-injection orchestrator over Ablation + ScheduleLock.

Materials/control-theory FARM model (Faults, Activation, Readouts, Measures)
as a thin plan over existing life_loop primitives — no second engine.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from codontrace._types import JsonValue
from codontrace.contracts.banned import BANNED_DOMAIN_TOKENS
from codontrace.errors import ConfigurationError
from codontrace.genesis.canonical import canonical_digest
from codontrace.life_loop.ablation_template import (
    ABLATION_MODES,
    AblationApplyRecord,
    AblationTemplate,
    apply_ablation,
)
from codontrace.life_loop.populations import PopulationRegistry
from codontrace.life_loop.schedule_lock import (
    LOCK_MODES,
    ScheduleLock,
    ScheduleLockApplyRecord,
    ScheduleLockState,
    apply_schedule_lock,
)

SCHEMA_VERSION = "life_loop_farm_orchestrator_v1"


def _as_str(value: object, name: str, *, allow_empty: bool = False) -> str:
    if not isinstance(value, str):
        raise ConfigurationError(f"{name} must be a string.")
    text = value.strip()
    if not text and not allow_empty:
        raise ConfigurationError(f"{name} must be a non-empty string.")
    return text


def _as_int(value: object, name: str, *, minimum: int | None = None) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ConfigurationError(f"{name} must be an integer.")
    if minimum is not None and value < minimum:
        raise ConfigurationError(f"{name} must be >= {minimum}.")
    return value


def _refuse_banned_fragment(text: str, name: str) -> str:
    lowered = text.casefold()
    for token in BANNED_DOMAIN_TOKENS:
        if token.casefold() in lowered:
            raise ConfigurationError(f"{name} contains a banned fragment.")
    return text


def _check_digest(existing: str, computed: str, label: str) -> str:
    if existing and existing != computed:
        raise ConfigurationError(f"{label} digest mismatch.")
    return computed


@dataclass(frozen=True, slots=True)
class FarmPlan:
    """Immutable FARM plan: which fault + when + which readout keys."""

    plan_id: str
    fault_ablation_mode: str
    activation_lock_mode: str
    activation_tick: int = 0
    readout_keys: tuple[str, ...] = ("coupling_total", "contact_success", "match_pass")
    claim_ceiling: str = "runtime_observation"
    intervention_supported: bool = False
    digest: str = ""

    def __post_init__(self) -> None:
        pid = _refuse_banned_fragment(_as_str(self.plan_id, "plan_id"), "plan_id")
        object.__setattr__(self, "plan_id", pid)
        abl = _as_str(self.fault_ablation_mode, "fault_ablation_mode").casefold()
        if abl not in ABLATION_MODES:
            raise ConfigurationError(
                f"unknown fault_ablation_mode {self.fault_ablation_mode!r}."
            )
        object.__setattr__(self, "fault_ablation_mode", abl)
        lock = _as_str(self.activation_lock_mode, "activation_lock_mode").casefold()
        if lock not in LOCK_MODES:
            raise ConfigurationError(
                f"unknown activation_lock_mode {self.activation_lock_mode!r}."
            )
        object.__setattr__(self, "activation_lock_mode", lock)
        object.__setattr__(
            self,
            "activation_tick",
            _as_int(self.activation_tick, "activation_tick", minimum=0),
        )
        keys: list[str] = []
        for k in self.readout_keys:
            keys.append(
                _refuse_banned_fragment(
                    _as_str(k, "readout_keys.item"), "readout_keys.item"
                )
            )
        object.__setattr__(self, "readout_keys", tuple(keys))
        ceiling = _as_str(self.claim_ceiling, "claim_ceiling").casefold()
        if ceiling not in {"runtime_observation", "candidate_evidence"}:
            raise ConfigurationError(
                "claim_ceiling must be runtime_observation or candidate_evidence."
            )
        object.__setattr__(self, "claim_ceiling", ceiling)
        if self.intervention_supported:
            raise ConfigurationError("refuses intervention_supported=True.")
        object.__setattr__(self, "intervention_supported", False)
        computed = canonical_digest(self._body(), prefix="farm_plan")
        object.__setattr__(
            self, "digest", _check_digest(self.digest, computed, "FarmPlan")
        )

    def _body(self) -> dict[str, JsonValue]:
        return {
            "schema_version": SCHEMA_VERSION,
            "plan_id": self.plan_id,
            "fault_ablation_mode": self.fault_ablation_mode,
            "activation_lock_mode": self.activation_lock_mode,
            "activation_tick": self.activation_tick,
            "readout_keys": list(self.readout_keys),
            "claim_ceiling": self.claim_ceiling,
            "intervention_supported": False,
        }

    def to_dict(self) -> dict[str, JsonValue]:
        return {**self._body(), "digest": self.digest}


@dataclass(frozen=True, slots=True)
class FarmApplyRecord:
    """Result of applying a FarmPlan (Faults+Activation); Measures left to caller."""

    plan_id: str
    ablation_record_digest: str
    schedule_record_digest: str
    state_digest: str
    readout_keys: tuple[str, ...]
    bag_after: Mapping[str, JsonValue]
    intervention_supported: bool = False
    digest: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "plan_id",
            _refuse_banned_fragment(_as_str(self.plan_id, "plan_id"), "plan_id"),
        )
        object.__setattr__(
            self,
            "ablation_record_digest",
            _as_str(self.ablation_record_digest, "ablation_record_digest"),
        )
        object.__setattr__(
            self,
            "schedule_record_digest",
            _as_str(self.schedule_record_digest, "schedule_record_digest"),
        )
        object.__setattr__(
            self, "state_digest", _as_str(self.state_digest, "state_digest")
        )
        keys = tuple(
            _refuse_banned_fragment(_as_str(k, "readout_keys.item"), "readout_keys.item")
            for k in self.readout_keys
        )
        object.__setattr__(self, "readout_keys", keys)
        if not isinstance(self.bag_after, Mapping):
            raise ConfigurationError("bag_after must be a mapping.")
        # freeze as plain dict with JSON-ish values
        frozen = {str(k): self.bag_after[k] for k in sorted(self.bag_after)}
        object.__setattr__(self, "bag_after", frozen)
        if self.intervention_supported:
            raise ConfigurationError("refuses intervention_supported=True.")
        object.__setattr__(self, "intervention_supported", False)
        computed = canonical_digest(self._body(), prefix="farm_apply")
        object.__setattr__(
            self, "digest", _check_digest(self.digest, computed, "FarmApplyRecord")
        )

    def _body(self) -> dict[str, JsonValue]:
        return {
            "schema_version": SCHEMA_VERSION,
            "plan_id": self.plan_id,
            "ablation_record_digest": self.ablation_record_digest,
            "schedule_record_digest": self.schedule_record_digest,
            "state_digest": self.state_digest,
            "readout_keys": list(self.readout_keys),
            "bag_after": dict(self.bag_after),
            "intervention_supported": False,
        }

    def to_dict(self) -> dict[str, JsonValue]:
        return {**self._body(), "digest": self.digest}


def apply_farm(
    plan: FarmPlan,
    *,
    ablation_template: AblationTemplate,
    bag: Mapping[str, Any],
    schedule_lock: ScheduleLock,
    registry: PopulationRegistry,
    live_bags: Mapping[str, Mapping[str, Any]],
    frames: Sequence[Mapping[str, Mapping[str, Any]]] = (),
    prior: ScheduleLockState | None = None,
) -> tuple[
    FarmApplyRecord,
    AblationApplyRecord,
    ScheduleLockApplyRecord,
    ScheduleLockState,
    Mapping[str, Any],
]:
    """Apply Fault (ablation) then Activation (schedule lock).

    Returns farm record, ablation record, schedule record, new lock state, ablated bag.
    Measures (readout aggregation) remain the caller's responsibility.
    """

    if not isinstance(plan, FarmPlan):
        raise ConfigurationError("plan must be a FarmPlan.")
    template = ablation_template
    if template.mode != plan.fault_ablation_mode:
        template = AblationTemplate(
            arm_id=template.arm_id,
            mode=plan.fault_ablation_mode,  # type: ignore[arg-type]
            content_keys=template.content_keys,
            structure_keys=template.structure_keys,
        )
    abl_rec, _census = apply_ablation(template, bag, tick=plan.activation_tick)
    lock = schedule_lock
    if lock.lock_mode != plan.activation_lock_mode:
        lock = ScheduleLock(
            schedule_id=lock.schedule_id,
            lock_mode=plan.activation_lock_mode,  # type: ignore[arg-type]
            population_id=lock.population_id,
            schedule_partition=lock.schedule_partition,
        )
    state_out, sched_rec, _scensus = apply_schedule_lock(
        lock,
        registry,
        live_bags,
        tick=plan.activation_tick,
        frames=frames,
        prior=prior,
    )
    record = FarmApplyRecord(
        plan_id=plan.plan_id,
        ablation_record_digest=abl_rec.digest,
        schedule_record_digest=sched_rec.digest,
        state_digest=state_out.digest,
        readout_keys=plan.readout_keys,
        bag_after=dict(abl_rec.bag),
    )
    return record, abl_rec, sched_rec, state_out, dict(abl_rec.bag)
