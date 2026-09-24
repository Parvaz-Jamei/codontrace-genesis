"""Domain-free contact transfer for the life-loop.

Applies a contact policy between two individuals: candidate filtering,
MatchRule gating, atomic payload package transfer, and optional seat
attach via AttachmentBook. Emits ``ContactEvent`` from Phase 1 contracts.
No discipline vocabulary and no second tick engine.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Literal

from codontrace._types import JsonValue
from codontrace.contracts.banned import BANNED_DOMAIN_TOKENS
from codontrace.contracts.life_loop_events import ContactEvent
from codontrace.errors import ConfigurationError
from codontrace.genesis.canonical import canonical_digest, require_finite_float
from codontrace.life_loop.attachment import AttachmentBook

SCHEMA_VERSION = "life_loop_contact_v1"

TransferMode = Literal["none", "payload_copy", "payload_move", "seat_attach"]
CandidateMode = Literal["well_mixed", "local"]

TRANSFER_MODES: frozenset[str] = frozenset(
    {"none", "payload_copy", "payload_move", "seat_attach"}
)
CANDIDATE_MODES: frozenset[str] = frozenset({"well_mixed", "local"})

ContactFailReason = Literal[
    "success",
    "match_failed",
    "not_in_candidates",
    "identical_endpoints",
    "neighbors_required",
    "payload_missing",
    "payload_incomplete",
    "seat_required",
    "slot_required",
    "not_attached",
    "seat_full",
    "already_occupant",
    "self_attach",
    "unknown_slot",
    "banned_fragment",
    "unknown_mode",
    "non_finite",
]

CONTACT_FAIL_REASONS: frozenset[str] = frozenset(
    {
        "success",
        "match_failed",
        "not_in_candidates",
        "identical_endpoints",
        "neighbors_required",
        "payload_missing",
        "payload_incomplete",
        "seat_required",
        "slot_required",
        "not_attached",
        "seat_full",
        "already_occupant",
        "self_attach",
        "unknown_slot",
        "banned_fragment",
        "unknown_mode",
        "non_finite",
    }
)

MatchRule = Callable[[str, str], bool | float]


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


def _canonical_keys(keys: Sequence[str]) -> tuple[str, ...]:
    cleaned: list[str] = []
    seen: set[str] = set()
    for raw in keys:
        key = _refuse_banned_fragment(_as_str(raw, "payload_key"), "payload_key")
        if key in seen:
            raise ConfigurationError(f"duplicate payload_key {key!r}.")
        seen.add(key)
        cleaned.append(key)
    return tuple(sorted(cleaned))


@dataclass(frozen=True, slots=True)
class ContactAttemptCensus:
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
            if reason not in CONTACT_FAIL_REASONS:
                raise ConfigurationError(f"unknown contact reason: {reason}")
            cleaned[reason] = _as_int(value, f"counts[{reason}]", minimum=0)
        object.__setattr__(self, "counts", dict(sorted(cleaned.items())))
        total = sum(cleaned.values())
        if total != attempts:
            raise ConfigurationError("attempt census sum mismatch.")
        computed = canonical_digest(self._body(), prefix="ctcensus")
        object.__setattr__(
            self, "digest", _check_digest(self.digest, computed, "ContactAttemptCensus")
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
    def from_dict(cls, data: Mapping[str, Any]) -> ContactAttemptCensus:
        raw = data.get("counts", {})
        if not isinstance(raw, Mapping):
            raise ConfigurationError("counts must be a mapping.")
        return cls(
            attempts=_as_int(data.get("attempts", 0), "attempts", minimum=0),
            counts={str(k): int(v) for k, v in raw.items()},
            digest=_as_str(data.get("digest", ""), "digest", allow_empty=True),
        )

    def record(self, reason: str) -> ContactAttemptCensus:
        if reason not in CONTACT_FAIL_REASONS:
            raise ConfigurationError(f"unknown contact reason: {reason}")
        counts = dict(self.counts)
        counts[reason] = counts.get(reason, 0) + 1
        return ContactAttemptCensus(attempts=self.attempts + 1, counts=counts)


@dataclass(frozen=True, slots=True)
class ContactTransferPolicy:
    """Immutable contact-transfer policy (digest-stable)."""

    rule_id: str
    transfer_mode: str = "payload_copy"
    candidate_mode: str = "well_mixed"
    payload_keys: tuple[str, ...] = ()
    target_slot_id: str | None = None
    require_attached: bool = False
    label: str | None = None
    digest: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "rule_id",
            _refuse_banned_fragment(_as_str(self.rule_id, "rule_id"), "rule_id"),
        )
        mode = _as_str(self.transfer_mode, "transfer_mode")
        if mode not in TRANSFER_MODES:
            raise ConfigurationError("unknown_mode")
        object.__setattr__(self, "transfer_mode", mode)
        cand = _as_str(self.candidate_mode, "candidate_mode")
        if cand not in CANDIDATE_MODES:
            raise ConfigurationError("unknown_mode")
        object.__setattr__(self, "candidate_mode", cand)
        object.__setattr__(self, "payload_keys", _canonical_keys(self.payload_keys))
        slot = _optional_str(self.target_slot_id, "target_slot_id")
        if slot is not None:
            slot = _refuse_banned_fragment(slot, "target_slot_id")
        object.__setattr__(self, "target_slot_id", slot)
        if not isinstance(self.require_attached, bool):
            raise ConfigurationError("require_attached must be a bool.")
        label = _optional_str(self.label, "label")
        if label is not None:
            label = _refuse_banned_fragment(label, "label")
        object.__setattr__(self, "label", label)
        computed = canonical_digest(self._body(), prefix="ctpolicy")
        object.__setattr__(
            self, "digest", _check_digest(self.digest, computed, "ContactTransferPolicy")
        )

    def _body(self) -> dict[str, JsonValue]:
        return {
            "schema_version": SCHEMA_VERSION,
            "rule_id": self.rule_id,
            "transfer_mode": self.transfer_mode,
            "candidate_mode": self.candidate_mode,
            "payload_keys": list(self.payload_keys),
            "target_slot_id": self.target_slot_id,
            "require_attached": self.require_attached,
            "label": self.label,
        }

    def to_dict(self) -> dict[str, JsonValue]:
        return {**self._body(), "digest": self.digest}

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> ContactTransferPolicy:
        raw_keys = data.get("payload_keys", ())
        if not isinstance(raw_keys, (list, tuple)):
            raise ConfigurationError("payload_keys must be a list or tuple.")
        return cls(
            rule_id=_as_str(data.get("rule_id"), "rule_id"),
            transfer_mode=_as_str(data.get("transfer_mode", "payload_copy"), "transfer_mode"),
            candidate_mode=_as_str(
                data.get("candidate_mode", "well_mixed"), "candidate_mode"
            ),
            payload_keys=tuple(str(item) for item in raw_keys),
            target_slot_id=_optional_str(data.get("target_slot_id"), "target_slot_id"),
            require_attached=bool(data.get("require_attached", False)),
            label=_optional_str(data.get("label"), "label"),
            digest=_as_str(data.get("digest", ""), "digest", allow_empty=True),
        )


def select_contact_candidates(
    actor_id: str,
    member_ids: Sequence[str],
    *,
    candidate_mode: str,
    neighbors: Mapping[str, Sequence[str]] | None = None,
) -> tuple[str, ...]:
    """Return sorted candidate peer ids for a contact attempt."""

    actor = _refuse_banned_fragment(_as_str(actor_id, "actor_id"), "actor_id")
    mode = _as_str(candidate_mode, "candidate_mode")
    if mode not in CANDIDATE_MODES:
        raise ConfigurationError("unknown_mode")
    members = [
        _refuse_banned_fragment(_as_str(m, "member_id"), "member_id") for m in member_ids
    ]
    member_set = set(members)
    if actor not in member_set:
        # Actor may contact from outside census; still filter peers from members.
        pass
    if mode == "well_mixed":
        return tuple(sorted(m for m in member_set if m != actor))
    if neighbors is None:
        raise ConfigurationError("neighbors_required")
    if not isinstance(neighbors, Mapping):
        raise ConfigurationError("neighbors must be a mapping.")
    local = neighbors.get(actor, ())
    if not isinstance(local, (list, tuple)):
        raise ConfigurationError("neighbors entry must be a list or tuple.")
    local_ids = {
        _refuse_banned_fragment(_as_str(n, "neighbor_id"), "neighbor_id") for n in local
    }
    return tuple(sorted(m for m in local_ids if m in member_set and m != actor))


def _eval_match(match_rule: MatchRule | None, actor_id: str, other_id: str) -> float | None:
    if match_rule is None:
        return 1.0
    result = match_rule(actor_id, other_id)
    if isinstance(result, bool):
        return 1.0 if result else 0.0
    score = float(require_finite_float("match_score", result))
    return score


def apply_contact(
    policy: ContactTransferPolicy,
    *,
    actor_id: str,
    other_id: str,
    tick: int,
    member_ids: Sequence[str],
    payloads: Mapping[str, Mapping[str, JsonValue]] | None = None,
    book: AttachmentBook | None = None,
    neighbors: Mapping[str, Sequence[str]] | None = None,
    match_rule: MatchRule | None = None,
    census: ContactAttemptCensus | None = None,
) -> tuple[
    dict[str, dict[str, JsonValue]],
    AttachmentBook | None,
    ContactEvent | None,
    str,
    ContactAttemptCensus,
]:
    """Apply one contact transfer.

    Returns ``(new_payloads, new_book, event_or_none, reason, census)``.
    On refuse, payloads/book are unchanged and event is None.
    """

    if not isinstance(policy, ContactTransferPolicy):
        raise ConfigurationError("policy must be a ContactTransferPolicy.")
    actor = _refuse_banned_fragment(_as_str(actor_id, "actor_id"), "actor_id")
    other = _refuse_banned_fragment(_as_str(other_id, "other_id"), "other_id")
    tick_i = _as_int(tick, "tick", minimum=0)
    census_state = census if census is not None else ContactAttemptCensus()

    def _fail(reason: str) -> tuple[
        dict[str, dict[str, JsonValue]],
        AttachmentBook | None,
        ContactEvent | None,
        str,
        ContactAttemptCensus,
    ]:
        base_payloads = {
            str(k): dict(v) for k, v in (payloads or {}).items() if isinstance(v, Mapping)
        }
        return base_payloads, book, None, reason, census_state.record(reason)

    if actor == other:
        return _fail("identical_endpoints")

    try:
        candidates = select_contact_candidates(
            actor,
            member_ids,
            candidate_mode=policy.candidate_mode,
            neighbors=neighbors,
        )
    except ConfigurationError as exc:
        msg = str(exc)
        if "neighbors_required" in msg:
            return _fail("neighbors_required")
        if "banned fragment" in msg:
            return _fail("banned_fragment")
        if "unknown_mode" in msg:
            return _fail("unknown_mode")
        raise

    if other not in candidates:
        return _fail("not_in_candidates")

    try:
        score = _eval_match(match_rule, actor, other)
    except ConfigurationError:
        return _fail("non_finite")
    if score is None or score <= 0.0:
        return _fail("match_failed")

    if policy.require_attached:
        if book is None:
            return _fail("seat_required")
        if not book.any_link(actor, other):
            return _fail("not_attached")

    new_payloads: dict[str, dict[str, JsonValue]] = {
        str(k): dict(v) for k, v in (payloads or {}).items() if isinstance(v, Mapping)
    }
    new_book = book

    mode = policy.transfer_mode
    if mode in {"payload_copy", "payload_move"}:
        if not policy.payload_keys:
            # Empty package is a no-op success for payload modes.
            pass
        else:
            sender = new_payloads.get(actor)
            if sender is None:
                return _fail("payload_missing")
            missing = [k for k in policy.payload_keys if k not in sender]
            if missing:
                return _fail("payload_incomplete")
            receiver = dict(new_payloads.get(other, {}))
            for key in policy.payload_keys:
                receiver[key] = sender[key]
            new_payloads[other] = receiver
            if mode == "payload_move":
                remaining = dict(sender)
                for key in policy.payload_keys:
                    remaining.pop(key, None)
                new_payloads[actor] = remaining
            else:
                new_payloads[actor] = dict(sender)

    if mode == "seat_attach":
        if book is None:
            return _fail("seat_required")
        if policy.target_slot_id is None:
            return _fail("slot_required")
        try:
            new_book, _attach_event = book.attach(policy.target_slot_id, actor)
        except ConfigurationError as exc:
            msg = str(exc)
            if msg in {"seat_full", "already_occupant", "self_attach", "unknown_slot"}:
                return _fail(msg)
            if "banned fragment" in msg:
                return _fail("banned_fragment")
            raise

    if mode == "none":
        pass

    event = ContactEvent(
        actor_id=actor,
        other_id=other,
        tick=tick_i,
        rule_id=policy.rule_id,
        score=score,
        transfer_mode=policy.transfer_mode,
    )
    return new_payloads, new_book, event, "success", census_state.record("success")


__all__ = [
    "CANDIDATE_MODES",
    "CONTACT_FAIL_REASONS",
    "SCHEMA_VERSION",
    "TRANSFER_MODES",
    "CandidateMode",
    "ContactAttemptCensus",
    "ContactFailReason",
    "ContactTransferPolicy",
    "MatchRule",
    "TransferMode",
    "apply_contact",
    "select_contact_candidates",
]
