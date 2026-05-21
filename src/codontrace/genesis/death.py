"""Death/risk classification primitives for GENESIS population runs.

This module separates actual removal from a population from non-fatal
alive-gate failures. It is deliberately policy-driven and diagnostic-only: it
must not rescue organisms, kill them for reporting convenience, or turn warning
telemetry into a death claim.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Literal

from codontrace._types import JsonValue
from codontrace.errors import ConfigurationError
from codontrace.genesis.liveness import AliveGateResult


def _digest(payload: dict[str, JsonValue]) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


DeathAttributionLevel = Literal[
    "none",
    "alive_gate_warning",
    "policy_fatal",
    "event_level",
    "generation_level",
]


def _require_bool(value: object, field_name: str) -> bool:
    if not isinstance(value, bool):
        raise ConfigurationError(f"{field_name} must be bool.")
    return value


def _require_int(value: object, field_name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ConfigurationError(f"{field_name} must be int.")
    return value


def _require_float(value: object, field_name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise ConfigurationError(f"{field_name} must be number.")
    return float(value)


def _require_float_or_none(value: object, field_name: str) -> float | None:
    if value is None:
        return None
    return _require_float(value, field_name)


def _require_int_or_none(value: object, field_name: str) -> int | None:
    if value is None:
        return None
    return _require_int(value, field_name)


def _require_str(value: object, field_name: str) -> str:
    if not isinstance(value, str) or not value:
        raise ConfigurationError(f"{field_name} must be a non-empty string.")
    return value


def _require_str_or_none(value: object, field_name: str) -> str | None:
    if value is None:
        return None
    return _require_str(value, field_name)


def _require_str_tuple(value: object, field_name: str) -> tuple[str, ...]:
    if not isinstance(value, tuple):
        raise ConfigurationError(f"{field_name} must be a tuple of strings.")
    out: list[str] = []
    for item in value:
        if not isinstance(item, str) or not item:
            raise ConfigurationError(f"{field_name} contains invalid reason.")
        out.append(item)
    if len(out) != len(set(out)):
        raise ConfigurationError(f"{field_name} contains duplicate reasons.")
    return tuple(out)


def _require_reason_tuple(value: object, field_name: str) -> tuple[str, ...]:
    if not isinstance(value, tuple):
        raise ConfigurationError(f"{field_name} must be a tuple of strings.")
    out: list[str] = []
    for item in value:
        if not isinstance(item, str) or not item:
            raise ConfigurationError(f"{field_name} contains invalid reason.")
        out.append(item)
    return tuple(out)


def _strict_str_tuple_from_json(value: object, field_name: str) -> tuple[str, ...]:
    if not isinstance(value, list | tuple):
        raise ConfigurationError(f"{field_name} must be list/tuple of strings.")
    out: list[str] = []
    for item in value:
        if not isinstance(item, str) or not item:
            raise ConfigurationError(f"{field_name} contains invalid reason.")
        out.append(item)
    if len(out) != len(set(out)):
        raise ConfigurationError(f"{field_name} contains duplicate reasons.")
    return tuple(out)


@dataclass(frozen=True, slots=True)
class DeathMonitoringConfig:
    """Configurable death/risk export policy.

    The config controls classification and export semantics. It does not force
    success, force survival, or weaken controls. Actual death means the organism
    should be removed from the population lifecycle under this policy; risk means
    an alive-gate warning that did not remove the organism.
    """

    enabled: bool = True
    remove_on_runtime_atp_lte: float | None = 0.0
    fatal_alive_reasons: tuple[str, ...] = ("negative_runtime_atp",)
    fatal_blocked_reasons: tuple[str, ...] = ()
    fatal_blocked_action_threshold: int | None = None
    enable_max_age_death: bool = False
    max_age_ticks: int | None = None
    count_alive_gate_failure_as_risk: bool = True
    count_capacity_block_as_risk: bool = True
    nonfatal_blocked_reasons: tuple[str, ...] = (
        "max_population_reached",
        "population_capacity_reached",
        "offspring_no_free_space",
    )
    emit_record_for_every_organism_tick: bool = True
    emit_energy_link_records: bool = True
    schema_version: str = "death_monitoring_config_v1"

    def __post_init__(self) -> None:
        _require_bool(self.enabled, "enabled")
        _require_bool(self.enable_max_age_death, "enable_max_age_death")
        _require_bool(self.count_alive_gate_failure_as_risk, "count_alive_gate_failure_as_risk")
        _require_bool(self.count_capacity_block_as_risk, "count_capacity_block_as_risk")
        _require_bool(self.emit_record_for_every_organism_tick, "emit_record_for_every_organism_tick")
        _require_bool(self.emit_energy_link_records, "emit_energy_link_records")
        remove_threshold = _require_float_or_none(
            self.remove_on_runtime_atp_lte, "remove_on_runtime_atp_lte"
        )
        fatal_threshold = _require_int_or_none(
            self.fatal_blocked_action_threshold, "fatal_blocked_action_threshold"
        )
        max_age = _require_int_or_none(self.max_age_ticks, "max_age_ticks")
        _require_str_tuple(self.fatal_alive_reasons, "fatal_alive_reasons")
        _require_str_tuple(self.fatal_blocked_reasons, "fatal_blocked_reasons")
        _require_str_tuple(self.nonfatal_blocked_reasons, "nonfatal_blocked_reasons")
        if remove_threshold is not None and remove_threshold < 0:
            raise ValueError("remove_on_runtime_atp_lte must be non-negative when provided.")
        if fatal_threshold is not None and fatal_threshold < 0:
            raise ValueError("fatal_blocked_action_threshold must be non-negative when provided.")
        if max_age is not None and max_age <= 0:
            raise ValueError("max_age_ticks must be > 0 when provided.")
        if self.enable_max_age_death and max_age is None:
            raise ValueError("enable_max_age_death requires max_age_ticks.")
        if not isinstance(self.schema_version, str) or not self.schema_version:
            raise ValueError("schema_version must be a non-empty string.")

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "schema_version": self.schema_version,
            "enabled": self.enabled,
            "remove_on_runtime_atp_lte": self.remove_on_runtime_atp_lte,
            "fatal_alive_reasons": list(self.fatal_alive_reasons),
            "fatal_blocked_reasons": list(self.fatal_blocked_reasons),
            "fatal_blocked_action_threshold": self.fatal_blocked_action_threshold,
            "enable_max_age_death": self.enable_max_age_death,
            "max_age_ticks": self.max_age_ticks,
            "count_alive_gate_failure_as_risk": self.count_alive_gate_failure_as_risk,
            "count_capacity_block_as_risk": self.count_capacity_block_as_risk,
            "nonfatal_blocked_reasons": list(self.nonfatal_blocked_reasons),
            "emit_record_for_every_organism_tick": self.emit_record_for_every_organism_tick,
            "emit_energy_link_records": self.emit_energy_link_records,
        }

    @classmethod
    def from_dict(cls, data: dict[str, JsonValue]) -> "DeathMonitoringConfig":
        def _strict_bool(name: str, default: bool) -> bool:
            if name not in data:
                return default
            value = data[name]
            if not isinstance(value, bool):
                raise ConfigurationError(f"{name} must be bool.")
            return value

        def _strict_float_or_none(name: str, default: float | None) -> float | None:
            if name not in data:
                return default
            value = data[name]
            if value is None:
                return None
            if isinstance(value, bool) or not isinstance(value, int | float):
                raise ConfigurationError(f"{name} must be number or None.")
            return float(value)

        def _strict_int_or_none(name: str, default: int | None) -> int | None:
            if name not in data:
                return default
            value = data[name]
            if value is None:
                return None
            if isinstance(value, bool) or not isinstance(value, int):
                raise ConfigurationError(f"{name} must be int or None.")
            return int(value)

        def _strict_str_tuple(name: str, default: tuple[str, ...]) -> tuple[str, ...]:
            if name not in data:
                return default
            value = data[name]
            if not isinstance(value, list | tuple):
                raise ConfigurationError(f"{name} must be list/tuple of strings.")
            out: list[str] = []
            for item in value:
                if not isinstance(item, str) or not item:
                    raise ConfigurationError(f"{name} contains invalid reason.")
                out.append(item)
            if len(out) != len(set(out)):
                raise ConfigurationError(f"{name} contains duplicate reasons.")
            return tuple(out)

        schema = data.get("schema_version", "death_monitoring_config_v1")
        if not isinstance(schema, str) or not schema:
            raise ConfigurationError("schema_version must be a non-empty string.")
        return cls(
            enabled=_strict_bool("enabled", True),
            remove_on_runtime_atp_lte=_strict_float_or_none("remove_on_runtime_atp_lte", 0.0),
            fatal_alive_reasons=_strict_str_tuple("fatal_alive_reasons", ("negative_runtime_atp",)),
            fatal_blocked_reasons=_strict_str_tuple("fatal_blocked_reasons", ()),
            fatal_blocked_action_threshold=_strict_int_or_none(
                "fatal_blocked_action_threshold", None
            ),
            enable_max_age_death=_strict_bool("enable_max_age_death", False),
            max_age_ticks=_strict_int_or_none("max_age_ticks", None),
            count_alive_gate_failure_as_risk=_strict_bool(
                "count_alive_gate_failure_as_risk", True
            ),
            count_capacity_block_as_risk=_strict_bool("count_capacity_block_as_risk", True),
            nonfatal_blocked_reasons=_strict_str_tuple(
                "nonfatal_blocked_reasons",
                ("max_population_reached", "population_capacity_reached", "offspring_no_free_space"),
            ),
            emit_record_for_every_organism_tick=_strict_bool(
                "emit_record_for_every_organism_tick", True
            ),
            emit_energy_link_records=_strict_bool("emit_energy_link_records", True),
            schema_version=schema,
        )

    def digest(self) -> str:
        return _digest(self.to_dict())


@dataclass(frozen=True, slots=True)
class DeathClassificationRecord:
    organism_id: str
    tick: int
    actual_death_removed_from_population: bool
    removal_reason: str | None
    alive_gate_failed: bool
    alive_gate_reasons: tuple[str, ...]
    death_risk_event: bool
    fatal_policy_matched: bool
    fatal_policy_reason: str | None
    runtime_atp_before: float
    runtime_atp_after: float
    blocked_actions: int
    blocked_action_reasons: tuple[str, ...] = ()
    lineage_death_tick: int | None = None
    death_policy_digest: str = ""
    death_attribution_level: DeathAttributionLevel = "none"
    death_monitoring_enabled: bool = True
    emit_record: bool = True
    emit_energy_link: bool = True
    engine_tick: int | None = None
    population_tick: int | None = None
    event_step: int | None = None
    schema_version: str = "death_classification_record_v2"

    def __post_init__(self) -> None:
        _require_str(self.organism_id, "organism_id")
        _require_int(self.tick, "tick")
        if self.tick < 0:
            raise ValueError("tick must be non-negative.")
        if self.engine_tick is not None:
            _require_int(self.engine_tick, "engine_tick")
            if self.engine_tick < 0:
                raise ValueError("engine_tick must be non-negative.")
        if self.population_tick is not None:
            _require_int(self.population_tick, "population_tick")
            if self.population_tick < 0:
                raise ValueError("population_tick must be non-negative.")
        if self.event_step is not None:
            _require_int(self.event_step, "event_step")
            if self.event_step < 0:
                raise ValueError("event_step must be non-negative.")
        _require_bool(self.actual_death_removed_from_population, "actual_death_removed_from_population")
        _require_bool(self.alive_gate_failed, "alive_gate_failed")
        _require_bool(self.death_risk_event, "death_risk_event")
        _require_bool(self.fatal_policy_matched, "fatal_policy_matched")
        _require_bool(self.death_monitoring_enabled, "death_monitoring_enabled")
        _require_bool(self.emit_record, "emit_record")
        _require_bool(self.emit_energy_link, "emit_energy_link")
        _require_reason_tuple(self.alive_gate_reasons, "alive_gate_reasons")
        _require_reason_tuple(self.blocked_action_reasons, "blocked_action_reasons")
        _require_float(self.runtime_atp_before, "runtime_atp_before")
        _require_float(self.runtime_atp_after, "runtime_atp_after")
        _require_int(self.blocked_actions, "blocked_actions")
        if self.blocked_actions < 0:
            raise ValueError("blocked_actions must be non-negative.")
        if self.removal_reason is not None:
            _require_str(self.removal_reason, "removal_reason")
        if self.fatal_policy_reason is not None:
            _require_str(self.fatal_policy_reason, "fatal_policy_reason")
        if self.lineage_death_tick is not None:
            _require_int(self.lineage_death_tick, "lineage_death_tick")
        if self.actual_death_removed_from_population:
            if self.removal_reason is None:
                raise ValueError("actual death requires removal_reason.")
            if not self.fatal_policy_matched:
                raise ValueError("actual death requires fatal_policy_matched=True.")
            if self.fatal_policy_reason is None:
                raise ValueError("actual death requires fatal_policy_reason.")
            if self.lineage_death_tick is None:
                raise ValueError("actual death requires lineage_death_tick.")
        else:
            if self.removal_reason is not None:
                raise ValueError("non-death classification must not carry removal_reason.")
        if self.death_risk_event and self.actual_death_removed_from_population:
            raise ValueError("death_risk_event is non-fatal and cannot coincide with actual death.")
        if self.death_risk_event and not self.alive_gate_failed:
            raise ValueError("death risk requires alive_gate_failed=True.")
        if not self.death_monitoring_enabled:
            if self.actual_death_removed_from_population or self.alive_gate_failed or self.death_risk_event:
                raise ValueError("disabled death monitoring must not emit death/risk events.")
            if self.emit_record or self.emit_energy_link:
                raise ValueError("disabled death monitoring must not request record or energy-link emission.")
        if not self.death_policy_digest:
            raise ValueError("death_policy_digest is required.")
        if self.death_attribution_level not in {
            "none",
            "alive_gate_warning",
            "policy_fatal",
            "event_level",
            "generation_level",
        }:
            raise ValueError("invalid death_attribution_level.")

    @property
    def death_event(self) -> bool:
        return self.actual_death_removed_from_population

    @property
    def alive_gate_failure_event(self) -> bool:
        return self.alive_gate_failed

    @property
    def death_causing_event(self) -> bool:
        return self.actual_death_removed_from_population

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "schema_version": self.schema_version,
            "organism_id": self.organism_id,
            "tick": self.tick,
            "actual_death_removed_from_population": self.actual_death_removed_from_population,
            "removal_reason": self.removal_reason,
            "alive_gate_failed": self.alive_gate_failed,
            "alive_gate_failure_event": self.alive_gate_failed,
            "alive_gate_reasons": list(self.alive_gate_reasons),
            "death_risk_event": self.death_risk_event,
            "death_causing_event": self.death_causing_event,
            "death_event": self.death_event,
            "fatal_policy_matched": self.fatal_policy_matched,
            "fatal_policy_reason": self.fatal_policy_reason,
            "runtime_atp_before": self.runtime_atp_before,
            "runtime_atp_after": self.runtime_atp_after,
            "blocked_actions": self.blocked_actions,
            "blocked_action_reasons": list(self.blocked_action_reasons),
            "lineage_death_tick": self.lineage_death_tick,
            "death_policy_digest": self.death_policy_digest,
            "death_attribution_level": self.death_attribution_level,
            "death_monitoring_enabled": self.death_monitoring_enabled,
            "emit_record": self.emit_record,
            "emit_energy_link": self.emit_energy_link,
            "engine_tick": self.engine_tick if self.engine_tick is not None else self.tick,
            "population_tick": self.population_tick,
            "event_step": self.event_step,
        }

    @classmethod
    def from_dict(cls, data: dict[str, JsonValue]) -> "DeathClassificationRecord":
        def _field(name: str, default: object = None) -> object:
            return data[name] if name in data else default

        def _tuple(name: str) -> tuple[str, ...]:
            return _strict_str_tuple_from_json(_field(name, ()), name)

        lineage_raw = _field("lineage_death_tick")
        engine_tick_raw = _field("engine_tick")
        population_tick_raw = _field("population_tick")
        event_step_raw = _field("event_step")
        actual_raw = _field(
            "actual_death_removed_from_population", _field("death_event", False)
        )
        alive_raw = _field("alive_gate_failed", _field("alive_gate_failure_event", False))
        return cls(
            organism_id=_require_str(_field("organism_id", ""), "organism_id"),
            tick=_require_int(_field("tick", 0), "tick"),
            actual_death_removed_from_population=_require_bool(
                actual_raw, "actual_death_removed_from_population"
            ),
            removal_reason=_require_str_or_none(_field("removal_reason"), "removal_reason"),
            alive_gate_failed=_require_bool(alive_raw, "alive_gate_failed"),
            alive_gate_reasons=_tuple("alive_gate_reasons"),
            death_risk_event=_require_bool(_field("death_risk_event", False), "death_risk_event"),
            fatal_policy_matched=_require_bool(
                _field("fatal_policy_matched", False), "fatal_policy_matched"
            ),
            fatal_policy_reason=_require_str_or_none(
                _field("fatal_policy_reason"), "fatal_policy_reason"
            ),
            runtime_atp_before=_require_float(
                _field("runtime_atp_before", 0.0), "runtime_atp_before"
            ),
            runtime_atp_after=_require_float(
                _field("runtime_atp_after", 0.0), "runtime_atp_after"
            ),
            blocked_actions=_require_int(_field("blocked_actions", 0), "blocked_actions"),
            blocked_action_reasons=_tuple("blocked_action_reasons"),
            lineage_death_tick=None
            if lineage_raw is None
            else _require_int(lineage_raw, "lineage_death_tick"),
            death_policy_digest=_require_str(
                _field("death_policy_digest", ""), "death_policy_digest"
            ),
            death_attribution_level=_require_str(
                _field("death_attribution_level", "none"), "death_attribution_level"
            ),  # type: ignore[arg-type]
            death_monitoring_enabled=_require_bool(
                _field("death_monitoring_enabled", True), "death_monitoring_enabled"
            ),
            emit_record=_require_bool(_field("emit_record", True), "emit_record"),
            emit_energy_link=_require_bool(_field("emit_energy_link", True), "emit_energy_link"),
            engine_tick=None
            if engine_tick_raw is None
            else _require_int(engine_tick_raw, "engine_tick"),
            population_tick=None
            if population_tick_raw is None
            else _require_int(population_tick_raw, "population_tick"),
            event_step=None
            if event_step_raw is None
            else _require_int(event_step_raw, "event_step"),
            schema_version=_require_str(
                _field("schema_version", "death_classification_record_v2"), "schema_version"
            ),
        )

    def digest(self) -> str:
        return _digest(self.to_dict())


def classify_death(
    *,
    organism_id: str,
    tick: int,
    runtime_atp_before: float,
    runtime_atp_after: float,
    alive_result: AliveGateResult,
    birth_tick: int | None,
    config: DeathMonitoringConfig,
    blocked_action_reasons: tuple[str, ...] = (),
) -> DeathClassificationRecord:
    """Classify actual population death versus non-fatal risk telemetry."""

    policy_digest = config.digest()
    if not config.enabled:
        return DeathClassificationRecord(
            organism_id=organism_id,
            tick=tick,
            actual_death_removed_from_population=False,
            removal_reason=None,
            alive_gate_failed=False,
            alive_gate_reasons=(),
            death_risk_event=False,
            fatal_policy_matched=False,
            fatal_policy_reason=None,
            runtime_atp_before=runtime_atp_before,
            runtime_atp_after=runtime_atp_after,
            blocked_actions=0,
            blocked_action_reasons=(),
            lineage_death_tick=None,
            death_policy_digest=policy_digest,
            death_attribution_level="none",
            death_monitoring_enabled=False,
            emit_record=False,
            emit_energy_link=False,
            population_tick=tick,
        )

    alive_gate_failed = not alive_result.passed
    fatal_policy_reason: str | None = None

    if config.enabled:
        if (
            config.remove_on_runtime_atp_lte is not None
            and runtime_atp_after <= config.remove_on_runtime_atp_lte
        ):
            fatal_policy_reason = "runtime_atp_lte_threshold"
        for reason in alive_result.reasons:
            if fatal_policy_reason is None and reason in config.fatal_alive_reasons:
                fatal_policy_reason = f"fatal_alive_reason:{reason}"
        for reason in blocked_action_reasons:
            if fatal_policy_reason is None and reason in config.fatal_blocked_reasons:
                fatal_policy_reason = f"fatal_blocked_reason:{reason}"
        if (
            fatal_policy_reason is None
            and config.fatal_blocked_action_threshold is not None
            and alive_result.blocked_actions >= config.fatal_blocked_action_threshold
        ):
            fatal_policy_reason = "fatal_blocked_action_threshold"
        if (
            fatal_policy_reason is None
            and config.enable_max_age_death
            and config.max_age_ticks is not None
            and birth_tick is not None
            and tick - birth_tick >= config.max_age_ticks
        ):
            fatal_policy_reason = "max_age_ticks_exceeded"

    actual_death = fatal_policy_reason is not None
    capacity_only = bool(
        blocked_action_reasons
        and all(reason in config.nonfatal_blocked_reasons for reason in blocked_action_reasons)
    )
    risk_allowed = config.count_alive_gate_failure_as_risk and alive_gate_failed
    if capacity_only and not config.count_capacity_block_as_risk:
        risk_allowed = False
    death_risk_event = bool(risk_allowed and not actual_death)
    attribution: DeathAttributionLevel
    if actual_death:
        attribution = "policy_fatal"
    elif death_risk_event:
        attribution = "alive_gate_warning"
    else:
        attribution = "none"

    emit_record = bool(
        config.emit_record_for_every_organism_tick
        or actual_death
        or death_risk_event
        or fatal_policy_reason is not None
    )

    return DeathClassificationRecord(
        organism_id=organism_id,
        tick=tick,
        actual_death_removed_from_population=actual_death,
        removal_reason=fatal_policy_reason if actual_death else None,
        alive_gate_failed=alive_gate_failed,
        alive_gate_reasons=tuple(alive_result.reasons),
        death_risk_event=death_risk_event,
        fatal_policy_matched=actual_death,
        fatal_policy_reason=fatal_policy_reason,
        runtime_atp_before=runtime_atp_before,
        runtime_atp_after=runtime_atp_after,
        blocked_actions=alive_result.blocked_actions,
        blocked_action_reasons=blocked_action_reasons,
        lineage_death_tick=tick if actual_death else None,
        death_policy_digest=policy_digest,
        death_attribution_level=attribution,
        death_monitoring_enabled=True,
        emit_record=emit_record,
        emit_energy_link=config.emit_energy_link_records,
        population_tick=tick,
    )


__all__ = [
    "DeathAttributionLevel",
    "DeathClassificationRecord",
    "DeathMonitoringConfig",
    "classify_death",
]
