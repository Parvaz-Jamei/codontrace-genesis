"""Domain-free hook meters for the life-loop.

Accumulates digest-stable counters for Phase 1 HOOK_NAMES and related
life-loop tallies (attachment occupancy, coupling totals, contact
fail-reason histogram, per-population densities). Observation only —
no tick physics, no discipline vocabulary, no claim-ladder imports.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

from codontrace._types import JsonValue
from codontrace.contracts.banned import BANNED_DOMAIN_TOKENS
from codontrace.contracts.life_loop_events import HOOK_NAMES
from codontrace.errors import ConfigurationError
from codontrace.genesis.canonical import canonical_digest, require_finite_float

SCHEMA_VERSION = "life_loop_hook_meters_v1"

RELATED_TALLY_KEYS: frozenset[str] = frozenset(
    {
        "attach_occupancy",
        "attach_capacity",
        "coupling_total",
        "coupling_loss_total",
        "contact_success",
        "contact_fail",
        "birth_count",
        "death_count",
    }
)


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


def _as_nonneg_float(value: object, name: str) -> float:
    number = float(require_finite_float(name, value))
    if number < 0.0:
        raise ConfigurationError(f"{name} must be >= 0.")
    return number


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


def _sorted_int_map(raw: Mapping[str, object], name: str) -> dict[str, int]:
    if not isinstance(raw, Mapping):
        raise ConfigurationError(f"{name} must be a mapping.")
    out: dict[str, int] = {}
    for key, value in raw.items():
        k = _refuse_banned_fragment(_as_str(key, f"{name}.key"), f"{name}.key")
        out[k] = _as_int(value, f"{name}[{k}]", minimum=0)
    return dict(sorted(out.items()))


def _sorted_float_map(raw: Mapping[str, object], name: str) -> dict[str, float]:
    if not isinstance(raw, Mapping):
        raise ConfigurationError(f"{name} must be a mapping.")
    out: dict[str, float] = {}
    for key, value in raw.items():
        k = _refuse_banned_fragment(_as_str(key, f"{name}.key"), f"{name}.key")
        out[k] = _as_nonneg_float(value, f"{name}[{k}]")
    return dict(sorted(out.items()))


@dataclass(frozen=True, slots=True)
class HookMeterSnapshot:
    """Immutable digest-stable view of hook / related tallies."""

    meter_id: str
    tick: int
    hook_counts: Mapping[str, int]
    related_counts: Mapping[str, int]
    related_totals: Mapping[str, float]
    densities: Mapping[str, int]
    contact_fail_reasons: Mapping[str, int]
    digest: str = ""

    def __post_init__(self) -> None:
        mid = _refuse_banned_fragment(_as_str(self.meter_id, "meter_id"), "meter_id")
        object.__setattr__(self, "meter_id", mid)
        object.__setattr__(self, "tick", _as_int(self.tick, "tick", minimum=0))
        hooks = _sorted_int_map(dict(self.hook_counts), "hook_counts")
        for name in hooks:
            if name not in HOOK_NAMES:
                raise ConfigurationError(f"unknown hook name: {name!r}")
        # Ensure all HOOK_NAMES present (zeros allowed).
        full_hooks = {h: int(hooks.get(h, 0)) for h in sorted(HOOK_NAMES)}
        object.__setattr__(self, "hook_counts", full_hooks)
        related = _sorted_int_map(dict(self.related_counts), "related_counts")
        for key in related:
            if key not in RELATED_TALLY_KEYS:
                raise ConfigurationError(f"unknown related tally: {key!r}")
        object.__setattr__(self, "related_counts", related)
        totals = _sorted_float_map(dict(self.related_totals), "related_totals")
        for key in totals:
            if key not in RELATED_TALLY_KEYS:
                raise ConfigurationError(f"unknown related total: {key!r}")
        object.__setattr__(self, "related_totals", totals)
        object.__setattr__(
            self, "densities", _sorted_int_map(dict(self.densities), "densities")
        )
        object.__setattr__(
            self,
            "contact_fail_reasons",
            _sorted_int_map(dict(self.contact_fail_reasons), "contact_fail_reasons"),
        )
        computed = canonical_digest(self._body(), prefix="hookmeter")
        object.__setattr__(
            self, "digest", _check_digest(self.digest, computed, "HookMeterSnapshot")
        )

    def _body(self) -> dict[str, JsonValue]:
        return {
            "schema_version": SCHEMA_VERSION,
            "meter_id": self.meter_id,
            "tick": self.tick,
            "hook_counts": dict(self.hook_counts),
            "related_counts": dict(self.related_counts),
            "related_totals": dict(self.related_totals),
            "densities": dict(self.densities),
            "contact_fail_reasons": dict(self.contact_fail_reasons),
        }

    def to_dict(self) -> dict[str, JsonValue]:
        return {**self._body(), "digest": self.digest}

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> HookMeterSnapshot:
        return cls(
            meter_id=_as_str(data.get("meter_id"), "meter_id"),
            tick=_as_int(data.get("tick"), "tick", minimum=0),
            hook_counts=dict(data.get("hook_counts") or {}),
            related_counts=dict(data.get("related_counts") or {}),
            related_totals=dict(data.get("related_totals") or {}),
            densities=dict(data.get("densities") or {}),
            contact_fail_reasons=dict(data.get("contact_fail_reasons") or {}),
            digest=_as_str(data.get("digest", ""), "digest", allow_empty=True),
        )


@dataclass(slots=True)
class HookMeter:
    """Mutable accumulator; snapshots are immutable and digest-stable."""

    meter_id: str
    tick: int = 0
    _hook_counts: dict[str, int] = field(init=False, repr=False)
    _related_counts: dict[str, int] = field(init=False, repr=False)
    _related_totals: dict[str, float] = field(init=False, repr=False)
    _densities: dict[str, int] = field(init=False, repr=False)
    _contact_fail_reasons: dict[str, int] = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self.meter_id = _refuse_banned_fragment(
            _as_str(self.meter_id, "meter_id"), "meter_id"
        )
        self.tick = _as_int(self.tick, "tick", minimum=0)
        self._hook_counts = {h: 0 for h in sorted(HOOK_NAMES)}
        self._related_counts = {}
        self._related_totals = {}
        self._densities = {}
        self._contact_fail_reasons = {}

    def set_tick(self, tick: int) -> None:
        self.tick = _as_int(tick, "tick", minimum=0)

    def record_hook(self, hook_name: str, *, count: int = 1) -> None:
        name = _as_str(hook_name, "hook_name")
        if name not in HOOK_NAMES:
            raise ConfigurationError(f"unknown hook name: {name!r}")
        n = _as_int(count, "count", minimum=0)
        self._hook_counts[name] = self._hook_counts.get(name, 0) + n

    def record_related_count(self, key: str, *, count: int = 1) -> None:
        k = _as_str(key, "key")
        if k not in RELATED_TALLY_KEYS:
            raise ConfigurationError(f"unknown related tally: {k!r}")
        n = _as_int(count, "count", minimum=0)
        self._related_counts[k] = self._related_counts.get(k, 0) + n

    def record_related_total(self, key: str, amount: float) -> None:
        k = _as_str(key, "key")
        if k not in RELATED_TALLY_KEYS:
            raise ConfigurationError(f"unknown related total: {k!r}")
        amt = _as_nonneg_float(amount, "amount")
        self._related_totals[k] = self._related_totals.get(k, 0.0) + amt

    def set_densities(self, densities: Mapping[str, int]) -> None:
        self._densities = _sorted_int_map(dict(densities), "densities")

    def record_contact_outcome(self, reason: str, *, success: bool) -> None:
        r = _refuse_banned_fragment(_as_str(reason, "reason"), "reason")
        self._contact_fail_reasons[r] = self._contact_fail_reasons.get(r, 0) + 1
        if success:
            self.record_related_count("contact_success")
            self.record_hook("on_contact")
        else:
            self.record_related_count("contact_fail")

    def set_attachment_stats(self, *, occupancy: int, capacity: int) -> None:
        occ = _as_int(occupancy, "occupancy", minimum=0)
        cap = _as_int(capacity, "capacity", minimum=0)
        self._related_counts["attach_occupancy"] = occ
        self._related_counts["attach_capacity"] = cap

    def snapshot(self) -> HookMeterSnapshot:
        return HookMeterSnapshot(
            meter_id=self.meter_id,
            tick=self.tick,
            hook_counts=dict(self._hook_counts),
            related_counts=dict(self._related_counts),
            related_totals=dict(self._related_totals),
            densities=dict(self._densities),
            contact_fail_reasons=dict(self._contact_fail_reasons),
        )


def merge_fail_reason_histogram(
    reasons: Sequence[str],
) -> dict[str, int]:
    """Utility: build a sorted fail-reason histogram from reason labels."""

    hist: dict[str, int] = {}
    for item in reasons:
        r = _refuse_banned_fragment(_as_str(item, "reason"), "reason")
        hist[r] = hist.get(r, 0) + 1
    return dict(sorted(hist.items()))


__all__ = [
    "HOOK_NAMES",
    "RELATED_TALLY_KEYS",
    "SCHEMA_VERSION",
    "HookMeter",
    "HookMeterSnapshot",
    "merge_fail_reason_histogram",
]
