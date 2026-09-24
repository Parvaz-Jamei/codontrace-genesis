"""Domain-free ablation template for the life-loop.

Content-null vs structure-null axes (and dual) apply to opaque state bags.
Emits ``AblationArmEvent`` from Phase 1 contracts. Shareable with HE02-style
controls via an axis map helper — no discipline vocabulary and no second
tick engine.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Literal

from codontrace._types import JsonValue
from codontrace.contracts.banned import BANNED_DOMAIN_TOKENS
from codontrace.contracts.life_loop_events import AblationArmEvent
from codontrace.errors import ConfigurationError
from codontrace.genesis.canonical import canonical_digest

SCHEMA_VERSION = "life_loop_ablation_template_v1"

AblationMode = Literal["none", "content_null", "structure_null", "dual_null"]

ABLATION_MODES: frozenset[str] = frozenset(
    {"none", "content_null", "structure_null", "dual_null"}
)

# HE02-shaped baseline names → ablation mode (no HE02 import).
HE02_AXIS_MAP: dict[str, AblationMode] = {
    "content_null": "content_null",
    "channel_off": "structure_null",
    "capsules_shuffled": "content_null",
    "none": "none",
    "dual_null": "dual_null",
    "structure_null": "structure_null",
}

AblationFailReason = Literal[
    "success",
    "unknown_mode",
    "keys_required",
    "key_overlap",
    "banned_fragment",
    "unknown_axis",
    "bag_not_mapping",
]

ABLATION_FAIL_REASONS: frozenset[str] = frozenset(
    {
        "success",
        "unknown_mode",
        "keys_required",
        "key_overlap",
        "banned_fragment",
        "unknown_axis",
        "bag_not_mapping",
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


def _canonical_keys(keys: Sequence[str], name: str) -> tuple[str, ...]:
    cleaned: list[str] = []
    seen: set[str] = set()
    for raw in keys:
        key = _refuse_banned_fragment(_as_str(raw, name), name)
        if key in seen:
            raise ConfigurationError(f"duplicate {name} {key!r}.")
        seen.add(key)
        cleaned.append(key)
    return tuple(sorted(cleaned))


def mode_axes(mode: str) -> tuple[bool, bool]:
    """Return (content_null, structure_null) for a named mode."""

    key = _as_str(mode, "mode").casefold()
    if key not in ABLATION_MODES:
        raise ConfigurationError(f"unknown ablation mode {mode!r}.")
    content = key in {"content_null", "dual_null"}
    structure = key in {"structure_null", "dual_null"}
    return content, structure


def he02_axis_mode(arm_name: str) -> AblationMode:
    """Map an HE02-shaped baseline name to an AblationMode (no HE02 import)."""

    name = _refuse_banned_fragment(_as_str(arm_name, "arm_name"), "arm_name")
    mapped = HE02_AXIS_MAP.get(name.casefold())
    if mapped is None:
        raise ConfigurationError(f"unknown HE02-shaped axis {arm_name!r}.")
    return mapped


@dataclass(frozen=True, slots=True)
class AblationAttemptCensus:
    """Attempt ledger: attempts == sum(counts.values())."""

    attempts: int = 0
    counts: Mapping[str, int] | None = None
    digest: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "attempts", _as_int(self.attempts, "attempts", minimum=0))
        raw = self.counts if self.counts is not None else {}
        if not isinstance(raw, Mapping):
            raise ConfigurationError("counts must be a mapping.")
        cleaned: dict[str, int] = {}
        for key, value in raw.items():
            reason = _as_str(key, "reason")
            if reason not in ABLATION_FAIL_REASONS:
                raise ConfigurationError(f"unknown ablation fail reason {reason!r}.")
            cleaned[reason] = _as_int(value, "count", minimum=0)
        object.__setattr__(self, "counts", cleaned)
        total = sum(cleaned.values())
        if total != self.attempts:
            raise ConfigurationError("attempts must equal sum of reason counts.")
        computed = canonical_digest(
            {"attempts": self.attempts, "counts": dict(sorted(cleaned.items()))},
            prefix="ablation_census",
        )
        object.__setattr__(
            self, "digest", _check_digest(self.digest, computed, "AblationAttemptCensus")
        )

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "attempts": self.attempts,
            "counts": dict(sorted((self.counts or {}).items())),
            "digest": self.digest,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> AblationAttemptCensus:
        return cls(
            attempts=_as_int(data.get("attempts", 0), "attempts", minimum=0),
            counts=data.get("counts") or {},
            digest=_as_str(data.get("digest", ""), "digest", allow_empty=True),
        )

    def record(self, reason: str) -> AblationAttemptCensus:
        if reason not in ABLATION_FAIL_REASONS:
            raise ConfigurationError(f"unknown ablation fail reason {reason!r}.")
        counts = dict(self.counts or {})
        counts[reason] = counts.get(reason, 0) + 1
        return AblationAttemptCensus(attempts=self.attempts + 1, counts=counts)


@dataclass(frozen=True, slots=True)
class AblationTemplate:
    """Immutable content × structure ablation template."""

    arm_id: str
    mode: AblationMode = "none"
    content_keys: tuple[str, ...] = ()
    structure_keys: tuple[str, ...] = ()
    digest: str = ""

    def __post_init__(self) -> None:
        arm = _refuse_banned_fragment(_as_str(self.arm_id, "arm_id"), "arm_id")
        object.__setattr__(self, "arm_id", arm)
        mode = _as_str(self.mode, "mode").casefold()
        if mode not in ABLATION_MODES:
            raise ConfigurationError(f"unknown ablation mode {self.mode!r}.")
        object.__setattr__(self, "mode", mode)
        content_keys = _canonical_keys(self.content_keys, "content_key")
        structure_keys = _canonical_keys(self.structure_keys, "structure_key")
        overlap = set(content_keys) & set(structure_keys)
        if overlap:
            raise ConfigurationError("content_keys and structure_keys must not overlap.")
        content_null, structure_null = mode_axes(mode)
        if content_null and not content_keys:
            raise ConfigurationError("content_null axis requires content_keys.")
        if structure_null and not structure_keys:
            raise ConfigurationError("structure_null axis requires structure_keys.")
        object.__setattr__(self, "content_keys", content_keys)
        object.__setattr__(self, "structure_keys", structure_keys)
        computed = canonical_digest(self._body(), prefix="ablation_template")
        object.__setattr__(
            self, "digest", _check_digest(self.digest, computed, "AblationTemplate")
        )

    @property
    def content_null(self) -> bool:
        return mode_axes(self.mode)[0]

    @property
    def structure_null(self) -> bool:
        return mode_axes(self.mode)[1]

    def _body(self) -> dict[str, JsonValue]:
        return {
            "schema_version": SCHEMA_VERSION,
            "arm_id": self.arm_id,
            "mode": self.mode,
            "content_keys": list(self.content_keys),
            "structure_keys": list(self.structure_keys),
        }

    def to_dict(self) -> dict[str, JsonValue]:
        return {**self._body(), "digest": self.digest}

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> AblationTemplate:
        content_raw = data.get("content_keys", ())
        structure_raw = data.get("structure_keys", ())
        if not isinstance(content_raw, (list, tuple)):
            raise ConfigurationError("content_keys must be a list or tuple.")
        if not isinstance(structure_raw, (list, tuple)):
            raise ConfigurationError("structure_keys must be a list or tuple.")
        return cls(
            arm_id=_as_str(data.get("arm_id"), "arm_id"),
            mode=_as_str(data.get("mode", "none"), "mode"),  # type: ignore[arg-type]
            content_keys=tuple(str(item) for item in content_raw),
            structure_keys=tuple(str(item) for item in structure_raw),
            digest=_as_str(data.get("digest", ""), "digest", allow_empty=True),
        )

    @classmethod
    def from_he02_arm(
        cls,
        arm_name: str,
        *,
        arm_id: str | None = None,
        content_keys: Sequence[str] = (),
        structure_keys: Sequence[str] = (),
    ) -> AblationTemplate:
        mode = he02_axis_mode(arm_name)
        return cls(
            arm_id=arm_id or arm_name,
            mode=mode,
            content_keys=tuple(content_keys),
            structure_keys=tuple(structure_keys),
        )


@dataclass(frozen=True, slots=True)
class AblationApplyRecord:
    """Digest-stable record of one ablation application."""

    arm_id: str
    mode: str
    reason: AblationFailReason
    tick: int
    before_digest: str
    after_digest: str
    event: AblationArmEvent | None
    bag: Mapping[str, JsonValue]
    digest: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "arm_id", _as_str(self.arm_id, "arm_id"))
        object.__setattr__(self, "mode", _as_str(self.mode, "mode"))
        reason = _as_str(self.reason, "reason")
        if reason not in ABLATION_FAIL_REASONS:
            raise ConfigurationError(f"unknown ablation fail reason {reason!r}.")
        object.__setattr__(self, "reason", reason)
        object.__setattr__(self, "tick", _as_int(self.tick, "tick", minimum=0))
        object.__setattr__(self, "before_digest", _as_str(self.before_digest, "before_digest"))
        object.__setattr__(self, "after_digest", _as_str(self.after_digest, "after_digest"))
        if not isinstance(self.bag, Mapping):
            raise ConfigurationError("bag must be a mapping.")
        object.__setattr__(self, "bag", dict(self.bag))
        computed = canonical_digest(
            {
                "arm_id": self.arm_id,
                "mode": self.mode,
                "reason": self.reason,
                "tick": self.tick,
                "before_digest": self.before_digest,
                "after_digest": self.after_digest,
                "event_digest": None if self.event is None else self.event.digest,
                "bag": dict(sorted(self.bag.items())),
            },
            prefix="ablation_apply",
        )
        object.__setattr__(
            self, "digest", _check_digest(self.digest, computed, "AblationApplyRecord")
        )

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "arm_id": self.arm_id,
            "mode": self.mode,
            "reason": self.reason,
            "tick": self.tick,
            "before_digest": self.before_digest,
            "after_digest": self.after_digest,
            "event": None if self.event is None else self.event.to_dict(),
            "bag": dict(sorted(self.bag.items())),
            "digest": self.digest,
        }


def _bag_digest(bag: Mapping[str, Any]) -> str:
    return canonical_digest(dict(sorted(bag.items())), prefix="state_bag")


def apply_ablation(
    template: AblationTemplate,
    bag: Mapping[str, Any],
    *,
    tick: int = 0,
    census: AblationAttemptCensus | None = None,
) -> tuple[AblationApplyRecord, AblationAttemptCensus]:
    """Apply content/structure nulls to an opaque state bag.

    Returns an application record (with optional AblationArmEvent on success)
    and an updated attempt census. Does not execute a world tick.
    """

    if not isinstance(template, AblationTemplate):
        raise ConfigurationError("template must be an AblationTemplate.")
    census_state = census if census is not None else AblationAttemptCensus()
    tick_i = _as_int(tick, "tick", minimum=0)

    if not isinstance(bag, Mapping):
        census_state = census_state.record("bag_not_mapping")
        empty: dict[str, JsonValue] = {}
        record = AblationApplyRecord(
            arm_id=template.arm_id,
            mode=template.mode,
            reason="bag_not_mapping",
            tick=tick_i,
            before_digest=_bag_digest({}),
            after_digest=_bag_digest({}),
            event=None,
            bag=empty,
        )
        return record, census_state

    before = {str(k): bag[k] for k in bag}
    before_digest = _bag_digest(before)
    after = dict(before)

    content_null, structure_null = mode_axes(template.mode)
    if content_null:
        for key in template.content_keys:
            after[key] = None
    if structure_null:
        for key in template.structure_keys:
            after[key] = None

    after_digest = _bag_digest(after)
    event = AblationArmEvent(
        arm_id=template.arm_id,
        content_null=content_null,
        structure_null=structure_null,
        tick=tick_i,
    )
    census_state = census_state.record("success")
    record = AblationApplyRecord(
        arm_id=template.arm_id,
        mode=template.mode,
        reason="success",
        tick=tick_i,
        before_digest=before_digest,
        after_digest=after_digest,
        event=event,
        bag=after,
    )
    return record, census_state


__all__ = [
    "ABLATION_FAIL_REASONS",
    "ABLATION_MODES",
    "HE02_AXIS_MAP",
    "SCHEMA_VERSION",
    "AblationApplyRecord",
    "AblationAttemptCensus",
    "AblationFailReason",
    "AblationMode",
    "AblationTemplate",
    "apply_ablation",
    "he02_axis_mode",
    "mode_axes",
]
