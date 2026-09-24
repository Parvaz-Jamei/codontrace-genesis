"""Domain-free birth-time inheritance of attachment links.

Applies an inherit-attached policy when an offspring is created: modes
``none``, ``copy``, and ``share`` with caller-supplied probability draws.
Emits ``BirthAttachEvent`` from Phase 1 contracts. No discipline vocabulary
and no second tick engine.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Literal

from codontrace._types import JsonValue
from codontrace.contracts.banned import BANNED_DOMAIN_TOKENS
from codontrace.contracts.life_loop_events import BirthAttachEvent
from codontrace.errors import ConfigurationError
from codontrace.genesis.canonical import canonical_digest, require_finite_float
from codontrace.life_loop.attachment import AttachmentBook, AttachmentSlot

SCHEMA_VERSION = "life_loop_inherit_attached_v1"

InheritMode = Literal["none", "copy", "share"]

INHERIT_MODES: frozenset[str] = frozenset({"none", "copy", "share"})

InheritFailReason = Literal[
    "success",
    "skipped_draw",
    "mode_none",
    "parent_slot_missing",
    "offspring_slot_missing",
    "seat_full",
    "already_occupant",
    "self_attach",
    "share_parent_missing",
    "share_offspring_missing",
    "draws_exhausted",
    "banned_fragment",
    "unknown_mode",
    "identical_endpoints",
]

INHERIT_FAIL_REASONS: frozenset[str] = frozenset(
    {
        "success",
        "skipped_draw",
        "mode_none",
        "parent_slot_missing",
        "offspring_slot_missing",
        "seat_full",
        "already_occupant",
        "self_attach",
        "share_parent_missing",
        "share_offspring_missing",
        "draws_exhausted",
        "banned_fragment",
        "unknown_mode",
        "identical_endpoints",
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


def _optional_str(value: object, name: str) -> str | None:
    if value is None:
        return None
    return _as_str(value, name)


def _refuse_banned_fragment(text: str, name: str) -> str:
    lowered = text.casefold()
    for token in BANNED_DOMAIN_TOKENS:
        if token.casefold() in lowered:
            raise ConfigurationError(f"{name} contains a banned fragment.")
    return text


def _as_unit_interval(value: object, name: str) -> float:
    number = float(require_finite_float(name, value))
    if number < 0.0 or number > 1.0:
        raise ConfigurationError(f"{name} must be in [0, 1].")
    return number


def _check_digest(existing: str, computed: str, label: str) -> str:
    if existing and existing != computed:
        raise ConfigurationError(f"{label} digest mismatch.")
    return computed


@dataclass(frozen=True, slots=True)
class InheritAttemptCensus:
    """Fail-reason census with sum-check (attempts == sum of counts)."""

    attempts: int = 0
    counts: Mapping[str, int] = None  # type: ignore[assignment]
    digest: str = ""

    def __post_init__(self) -> None:
        attempts = _as_int(self.attempts, "attempts", minimum=0)
        object.__setattr__(self, "attempts", attempts)
        raw = self.counts if self.counts is not None else {}
        if not isinstance(raw, Mapping):
            raise ConfigurationError("counts must be a mapping.")
        cleaned: dict[str, int] = {}
        for key, value in raw.items():
            reason = _as_str(key, "reason")
            if reason not in INHERIT_FAIL_REASONS:
                raise ConfigurationError(f"unknown inherit reason: {reason}")
            cleaned[reason] = _as_int(value, f"counts[{reason}]", minimum=0)
        object.__setattr__(self, "counts", dict(sorted(cleaned.items())))
        total = sum(cleaned.values())
        if total != attempts:
            raise ConfigurationError("attempt census sum mismatch.")
        computed = canonical_digest(self._body(), prefix="inhcensus")
        object.__setattr__(
            self, "digest", _check_digest(self.digest, computed, "InheritAttemptCensus")
        )

    def _body(self) -> dict[str, JsonValue]:
        return {
            "schema_version": SCHEMA_VERSION,
            "attempts": self.attempts,
            "counts": dict(self.counts),
        }

    def to_dict(self) -> dict[str, JsonValue]:
        return {**self._body(), "digest": self.digest}

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> InheritAttemptCensus:
        raw = data.get("counts", {})
        if not isinstance(raw, Mapping):
            raise ConfigurationError("counts must be a mapping.")
        return cls(
            attempts=_as_int(data.get("attempts", 0), "attempts", minimum=0),
            counts={str(k): int(v) for k, v in raw.items()},
            digest=_as_str(data.get("digest", ""), "digest", allow_empty=True),
        )

    def record(self, reason: str) -> InheritAttemptCensus:
        if reason not in INHERIT_FAIL_REASONS:
            raise ConfigurationError(f"unknown inherit reason: {reason}")
        counts = dict(self.counts)
        counts[reason] = counts.get(reason, 0) + 1
        return InheritAttemptCensus(attempts=self.attempts + 1, counts=counts)


@dataclass(frozen=True, slots=True)
class InheritAttachedPolicy:
    """Immutable birth-time attachment inheritance policy."""

    policy_id: str
    mode: str = "copy"
    probability: float = 1.0
    parent_slot_id: str | None = None
    offspring_slot_id: str | None = None
    label: str | None = None
    digest: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "policy_id",
            _refuse_banned_fragment(_as_str(self.policy_id, "policy_id"), "policy_id"),
        )
        mode = _as_str(self.mode, "mode")
        if mode not in INHERIT_MODES:
            raise ConfigurationError("unknown_mode")
        object.__setattr__(self, "mode", mode)
        object.__setattr__(
            self, "probability", _as_unit_interval(self.probability, "probability")
        )
        parent_slot = _optional_str(self.parent_slot_id, "parent_slot_id")
        if parent_slot is not None:
            parent_slot = _refuse_banned_fragment(parent_slot, "parent_slot_id")
        object.__setattr__(self, "parent_slot_id", parent_slot)
        offspring_slot = _optional_str(self.offspring_slot_id, "offspring_slot_id")
        if offspring_slot is not None:
            offspring_slot = _refuse_banned_fragment(offspring_slot, "offspring_slot_id")
        object.__setattr__(self, "offspring_slot_id", offspring_slot)
        label = _optional_str(self.label, "label")
        if label is not None:
            label = _refuse_banned_fragment(label, "label")
        object.__setattr__(self, "label", label)
        computed = canonical_digest(self._body(), prefix="inhpolicy")
        object.__setattr__(
            self,
            "digest",
            _check_digest(self.digest, computed, "InheritAttachedPolicy"),
        )

    def _body(self) -> dict[str, JsonValue]:
        return {
            "schema_version": SCHEMA_VERSION,
            "policy_id": self.policy_id,
            "mode": self.mode,
            "probability": self.probability,
            "parent_slot_id": self.parent_slot_id,
            "offspring_slot_id": self.offspring_slot_id,
            "label": self.label,
        }

    def to_dict(self) -> dict[str, JsonValue]:
        return {**self._body(), "digest": self.digest}

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> InheritAttachedPolicy:
        return cls(
            policy_id=_as_str(data.get("policy_id"), "policy_id"),
            mode=_as_str(data.get("mode", "copy"), "mode"),
            probability=float(
                require_finite_float("probability", data.get("probability", 1.0))
            ),
            parent_slot_id=_optional_str(data.get("parent_slot_id"), "parent_slot_id"),
            offspring_slot_id=_optional_str(
                data.get("offspring_slot_id"), "offspring_slot_id"
            ),
            label=_optional_str(data.get("label"), "label"),
            digest=_as_str(data.get("digest", ""), "digest", allow_empty=True),
        )


def _default_offspring_slot_id(parent_slot_id: str, offspring_id: str) -> str:
    return f"{parent_slot_id}__{offspring_id}"


def apply_birth_inherit(
    policy: InheritAttachedPolicy,
    book: AttachmentBook,
    *,
    parent_id: str,
    offspring_id: str,
    tick: int,
    draws: Sequence[float] | None = None,
    census: InheritAttemptCensus | None = None,
) -> tuple[
    AttachmentBook,
    tuple[BirthAttachEvent, ...],
    tuple[str, ...],
    InheritAttemptCensus,
]:
    """Apply birth-time attachment inheritance.

    ``draws`` are caller-supplied unit-interval values consumed per occupant
    candidate (policy stays RNG-free). Returns updated book, events, per-attempt
    reasons, and census.
    """

    if not isinstance(policy, InheritAttachedPolicy):
        raise ConfigurationError("policy must be an InheritAttachedPolicy.")
    if not isinstance(book, AttachmentBook):
        raise ConfigurationError("book must be an AttachmentBook.")

    parent = _refuse_banned_fragment(_as_str(parent_id, "parent_id"), "parent_id")
    offspring = _refuse_banned_fragment(
        _as_str(offspring_id, "offspring_id"), "offspring_id"
    )
    tick_i = _as_int(tick, "tick", minimum=0)
    census_state = census if census is not None else InheritAttemptCensus()
    reasons: list[str] = []
    events: list[BirthAttachEvent] = []

    if parent == offspring:
        census_state = census_state.record("identical_endpoints")
        reasons.append("identical_endpoints")
        return book, tuple(events), tuple(reasons), census_state

    if policy.mode == "none":
        slot_id = policy.parent_slot_id or "none"
        events.append(
            BirthAttachEvent(
                parent_id=parent,
                offspring_id=offspring,
                slot_id=slot_id,
                inherited_occupant_id=None,
                tick=tick_i,
            )
        )
        census_state = census_state.record("mode_none")
        reasons.append("mode_none")
        return book, tuple(events), tuple(reasons), census_state

    if policy.parent_slot_id is None:
        census_state = census_state.record("parent_slot_missing")
        reasons.append("parent_slot_missing")
        return book, tuple(events), tuple(reasons), census_state

    try:
        parent_slot = book.get(policy.parent_slot_id)
    except ConfigurationError:
        census_state = census_state.record("parent_slot_missing")
        reasons.append("parent_slot_missing")
        return book, tuple(events), tuple(reasons), census_state

    if parent_slot.owner_id != parent:
        census_state = census_state.record("parent_slot_missing")
        reasons.append("parent_slot_missing")
        return book, tuple(events), tuple(reasons), census_state

    offspring_slot_id = policy.offspring_slot_id or _default_offspring_slot_id(
        parent_slot.slot_id, offspring
    )
    offspring_slot_id = _refuse_banned_fragment(offspring_slot_id, "offspring_slot_id")

    # Ensure offspring slot exists (empty), owned by offspring, same capacity.
    slot_ids = set(book.list_slot_ids())
    if offspring_slot_id not in slot_ids:
        new_slot = AttachmentSlot(
            slot_id=offspring_slot_id,
            owner_id=offspring,
            capacity=parent_slot.capacity,
            label=parent_slot.label,
            tick=book.tick,
        )
        book = book.add_slot(new_slot)
    else:
        existing = book.get(offspring_slot_id)
        if existing.owner_id != offspring:
            census_state = census_state.record("offspring_slot_missing")
            reasons.append("offspring_slot_missing")
            return book, tuple(events), tuple(reasons), census_state

    draw_list = list(draws) if draws is not None else []
    draw_index = 0
    parent_occupants_before = set(parent_slot.occupant_ids)

    if not parent_slot.occupant_ids:
        events.append(
            BirthAttachEvent(
                parent_id=parent,
                offspring_id=offspring,
                slot_id=offspring_slot_id,
                inherited_occupant_id=None,
                tick=tick_i,
            )
        )
        census_state = census_state.record("success")
        reasons.append("success")
        return book, tuple(events), tuple(reasons), census_state

    for occupant in parent_slot.occupant_ids:
        if draw_index >= len(draw_list):
            # When draws omitted and probability == 1.0, treat as always inherit.
            if draws is None and policy.probability >= 1.0 - 1e-15:
                draw_value = 0.0
            elif draws is None and policy.probability <= 0.0:
                draw_value = 1.0
            else:
                census_state = census_state.record("draws_exhausted")
                reasons.append("draws_exhausted")
                continue
        else:
            draw_value = float(
                require_finite_float("draw", draw_list[draw_index])
            )
            draw_index += 1
            if draw_value < 0.0 or draw_value > 1.0:
                raise ConfigurationError("draw must be in [0, 1].")

        if draw_value >= policy.probability:
            census_state = census_state.record("skipped_draw")
            reasons.append("skipped_draw")
            events.append(
                BirthAttachEvent(
                    parent_id=parent,
                    offspring_id=offspring,
                    slot_id=offspring_slot_id,
                    inherited_occupant_id=None,
                    tick=tick_i,
                )
            )
            continue

        try:
            book, _ev = book.attach(offspring_slot_id, occupant)
        except ConfigurationError as exc:
            msg = str(exc)
            if msg in {"seat_full", "already_occupant", "self_attach"}:
                census_state = census_state.record(msg)
                reasons.append(msg)
                continue
            if "banned fragment" in msg:
                census_state = census_state.record("banned_fragment")
                reasons.append("banned_fragment")
                continue
            raise

        events.append(
            BirthAttachEvent(
                parent_id=parent,
                offspring_id=offspring,
                slot_id=offspring_slot_id,
                inherited_occupant_id=occupant,
                tick=tick_i,
            )
        )
        census_state = census_state.record("success")
        reasons.append("success")

    # Enforce mode semantics after attachments.
    parent_after = book.get(parent_slot.slot_id)
    offspring_after = book.get(offspring_slot_id)

    if policy.mode == "copy":
        if set(parent_after.occupant_ids) != parent_occupants_before:
            raise ConfigurationError("copy mode must not alter parent occupancy.")

    if policy.mode == "share":
        # Dual-link: every successfully inherited occupant must remain on parent
        # and appear on offspring.
        for ev in events:
            oid = ev.inherited_occupant_id
            if oid is None:
                continue
            if oid not in parent_after.occupant_ids:
                census_state = census_state.record("share_parent_missing")
                reasons.append("share_parent_missing")
            if oid not in offspring_after.occupant_ids:
                census_state = census_state.record("share_offspring_missing")
                reasons.append("share_offspring_missing")

    return book, tuple(events), tuple(reasons), census_state


__all__ = [
    "INHERIT_FAIL_REASONS",
    "INHERIT_MODES",
    "SCHEMA_VERSION",
    "InheritAttachedPolicy",
    "InheritAttemptCensus",
    "InheritFailReason",
    "InheritMode",
    "apply_birth_inherit",
]
