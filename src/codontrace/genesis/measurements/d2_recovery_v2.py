"""D-2 performance endpoint, version 2.

The locked 1.25× rule stays the historical record. This module does not
re-read it as a success, and it does not treat a later definition as
confirmation of that design. Topology and contact flags stay false when the
only pairing is sorted names.

A scientific contact is a pair of engine ATP ledger rows: one source debit
and one recipient credit. At the ledger's 1e-10 rounding, source debit =
recipient credit + non-negative loss, and ``atp_paid`` is that source debit.
Names alone are not a contact. Instrument rows stay instrument-only.
"""

from __future__ import annotations

import math
from collections.abc import Collection, Mapping, Sequence

from codontrace.energy import ATPLedgerEntry
from codontrace.errors import ConfigurationError

PREREG_V1_ID = "FI-RARECLASS-CONTACT-YIELD-V1"
PREREG_V2_ID = "FI-RESOURCE-TRANSFER-V2"
OLD_LOCKED_MULTIPLIER = 1.25
CONTACT_VALIDATION_ID = "D2-CONTACT-LEDGER-V1"
ENGINE_LEDGER_EVIDENCE = "engine_ledger"
_LEDGER_PLACES = 10


def historical_endpoint_barrier() -> dict[str, object]:
    """The old positive control never reached the locked rule.

    Zeros on the arms therefore do not reject an intervention effect. They
    show that the instrument could not move.
    """

    return {
        "endpoint_id": PREREG_V1_ID,
        "locked_rule": "yield >= 1.25x baseline for >= 3 consecutive boundaries",
        "positive_control_reached": False,
        "reading": "measurement_barrier",
        "arm_zeros_reject_an_effect": False,
        "successor": PREREG_V2_ID,
        "successor_confirms_v1": False,
        "hypothesis_supported": False,
    }


def name_order_mapping(names: Sequence[str]) -> dict[str, object]:
    """Pair sorted names. That is not an engine contact."""

    ordered = sorted(str(name) for name in names)
    pair_count = len(ordered) // 2
    pairs = [(ordered[index], ordered[index + 1]) for index in range(0, pair_count * 2, 2)]
    return {
        "method": "sorted_name_order",
        "pairs": pairs,
        "unpaired": ordered[pair_count * 2 :],
        "topology_identified": False,
        "contact_identified": False,
    }


def _is_name_order(event: Mapping[str, object]) -> bool:
    return event.get("mapping") == "sorted_name_order"


def _is_instrument(event: Mapping[str, object]) -> bool:
    """A predefined fixture. It cannot wear the engine-ledger label."""

    if event.get("evidence") == ENGINE_LEDGER_EVIDENCE:
        return False
    if event.get("kind") in {"instrument_transfer", "edge_removal"}:
        return True
    return event.get("evidence") == "instrument" or event.get("predefined") is True


def _is_contact_claim(event: Mapping[str, object]) -> bool:
    if _is_name_order(event) or _is_instrument(event):
        return False
    return any(
        key in event
        for key in ("source_id", "recipient_id", "contact_id", "evidence", "atp_paid", "source_entry_id")
    )


def _text(event: Mapping[str, object], key: str) -> str:
    value = event.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ConfigurationError(f"{key} must be a non-empty string")
    return value


def _entry_id(event: Mapping[str, object], key: str) -> int:
    value = event.get(key)
    if isinstance(value, bool) or not isinstance(value, int):
        raise ConfigurationError(f"{key} must name a ledger entry")
    return value


def _non_negative(value: object, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise ConfigurationError(f"{name} must be finite and non-negative")
    number = float(value)
    if not math.isfinite(number) or number < 0.0:
        raise ConfigurationError(f"{name} must be finite and non-negative")
    return number


def _same(left: float, right: float) -> bool:
    return round(left, _LEDGER_PLACES) == round(right, _LEDGER_PLACES)


def _entry_view(entry: ATPLedgerEntry | Mapping[str, object]) -> dict[str, object]:
    if isinstance(entry, ATPLedgerEntry):
        return dict(entry.to_dict())
    if isinstance(entry, Mapping):
        return dict(entry)
    raise ConfigurationError("ledger entry is not an ATP ledger record")


def _checked_entry(view: Mapping[str, object]) -> tuple[str, int]:
    agent = view.get("agent_id")
    entry_id = view.get("entry_id")
    kind = view.get("kind")
    if not isinstance(agent, str) or not agent:
        raise ConfigurationError("unknown id in ledger")
    if isinstance(entry_id, bool) or not isinstance(entry_id, int):
        raise ConfigurationError(f"unknown ledger entry for {agent}")
    if kind not in {"debit", "credit"}:
        raise ConfigurationError(f"ledger entry {agent}:{entry_id} has no debit or credit kind")
    amount = _non_negative(view.get("amount"), "ledger amount")
    before = _non_negative(view.get("balance_before"), "balance_before")
    after = _non_negative(view.get("balance_after"), "balance_after")
    moved = before - amount if kind == "debit" else before + amount
    if not _same(moved, after):
        raise ConfigurationError(f"ledger entry {agent}:{entry_id} does not conserve ATP")
    tick = view.get("tick")
    if isinstance(tick, bool) or not isinstance(tick, int):
        raise ConfigurationError(f"ledger entry {agent}:{entry_id} has no tick")
    return agent, entry_id


def _index_ledger(
    ledger: Sequence[ATPLedgerEntry | Mapping[str, object]] | None,
) -> dict[tuple[str, int], Mapping[str, object]]:
    index: dict[tuple[str, int], Mapping[str, object]] = {}
    if ledger is None:
        return index
    for entry in ledger:
        view = _entry_view(entry)
        key = _checked_entry(view)
        if key in index:
            raise ConfigurationError(f"duplicate ledger entry {key[0]}:{key[1]}")
        index[key] = view
    return index


def _require_row(
    index: Mapping[tuple[str, int], Mapping[str, object]],
    agent: str,
    entry_id: int,
    *,
    kind: str,
) -> Mapping[str, object]:
    view = index.get((agent, entry_id))
    if view is None:
        if any(listed == agent for listed, _entry in index):
            raise ConfigurationError(f"unknown ledger entry {agent}:{entry_id}")
        raise ConfigurationError(f"unknown id {agent}")
    if view.get("kind") != kind:
        role = "source" if kind == "debit" else "recipient"
        raise ConfigurationError(f"{role} ledger entry is not a {kind}")
    return view


def _stated_balance(event: Mapping[str, object], key: str, ledger_value: object, label: str) -> None:
    if key not in event:
        return
    stated = _non_negative(event.get(key), key)
    recorded = _non_negative(ledger_value, label)
    if not _same(stated, recorded):
        raise ConfigurationError(f"{key} does not match the ledger")


def _validate_claim(
    event: Mapping[str, object],
    index: Mapping[tuple[str, int], Mapping[str, object]],
    used_entries: set[tuple[str, int]],
) -> float:
    contact = _text(event, "contact_id")
    if event.get("evidence") != ENGINE_LEDGER_EVIDENCE:
        raise ConfigurationError(f"contact {contact} is not an engine ledger record")
    source = _text(event, "source_id")
    recipient = _text(event, "recipient_id")
    if source == recipient:
        justification = event.get("self_transfer_justification")
        if not isinstance(justification, str) or not justification.strip():
            raise ConfigurationError("self-transfer is not a valid contact")
    source_key = (source, _entry_id(event, "source_entry_id"))
    recipient_key = (recipient, _entry_id(event, "recipient_entry_id"))
    if source_key == recipient_key:
        raise ConfigurationError("source and recipient cannot be the same ledger entry")
    if source_key in used_entries or recipient_key in used_entries:
        raise ConfigurationError(f"replay of a ledger entry on contact {contact}")
    source_row = _require_row(index, source_key[0], source_key[1], kind="debit")
    recipient_row = _require_row(index, recipient_key[0], recipient_key[1], kind="credit")
    if int(source_row["tick"]) != int(recipient_row["tick"]):
        raise ConfigurationError("source debit and recipient credit are not one contact")
    _stated_balance(event, "source_before", source_row.get("balance_before"), "balance_before")
    _stated_balance(event, "source_after", source_row.get("balance_after"), "balance_after")
    _stated_balance(event, "recipient_before", recipient_row.get("balance_before"), "balance_before")
    _stated_balance(event, "recipient_after", recipient_row.get("balance_after"), "balance_after")
    source_debit = float(source_row["amount"])
    recipient_credit = float(recipient_row["amount"])
    loss = _non_negative(event.get("loss", 0.0), "loss")
    paid = _non_negative(event.get("atp_paid"), "atp_paid")
    if not _same(paid, source_debit):
        raise ConfigurationError("atp_paid does not match the source debit")
    if not _same(source_debit, recipient_credit + loss):
        raise ConfigurationError("source debit, recipient credit, and loss do not reconcile")
    used_entries.add(source_key)
    used_entries.add(recipient_key)
    return paid


def transfer_yield(
    events: Sequence[Mapping[str, object]],
    ledger: Sequence[ATPLedgerEntry | Mapping[str, object]] | None = None,
    *,
    used_contact_ids: Collection[str] | None = None,
) -> dict[str, object]:
    """ATP moved on an engine ledger contact.

    Name-order rows are not contacts and force ``contact_identified`` false.
    Instrument rows are counted apart and are never engine contacts. A claim
    that is duplicate, replayed, unknown, a bare self-transfer, or
    inconsistent with the ledger is rejected.
    """

    index = _index_ledger(ledger)
    already = set(used_contact_ids or ())
    used_entries: set[tuple[str, int]] = set()
    paid = 0.0
    counted = 0
    instrument = 0
    blocked = not events
    claims: list[Mapping[str, object]] = []
    for event in events:
        if _is_name_order(event):
            blocked = True
            continue
        if _is_instrument(event):
            if "atp_paid" in event:
                _non_negative(event.get("atp_paid"), "atp_paid")
            instrument += 1
            continue
        if not _is_contact_claim(event):
            blocked = True
            continue
        claims.append(event)
    seen: list[str] = []
    for event in claims:
        contact = _text(event, "contact_id")
        if contact in seen:
            if event.get("evidence") != ENGINE_LEDGER_EVIDENCE:
                raise ConfigurationError(f"duplicate contact id {contact} is not an engine ledger record")
            raise ConfigurationError(f"duplicate contact id {contact}")
        if contact in already:
            raise ConfigurationError(f"replay of contact id {contact}")
        seen.append(contact)
    for event, contact in zip(claims, seen, strict=True):
        if event.get("evidence") != ENGINE_LEDGER_EVIDENCE:
            raise ConfigurationError(f"contact {contact} is not an engine ledger record")
    for event in claims:
        paid += _validate_claim(event, index, used_entries)
        counted += 1
    identified = counted > 0 and not blocked
    return {
        "endpoint_id": PREREG_V2_ID,
        "validation": CONTACT_VALIDATION_ID,
        "paid_transfer": paid if identified else None,
        "n_identified_contacts": counted if identified else 0,
        "contact_identified": identified,
        "instrument_only": instrument > 0 and not identified,
        "n_instrument_events": instrument,
        "topology_identified": False,
        "confirms_v1_endpoint": False,
        "hypothesis_supported": False,
        "consumed_contact_ids": tuple(sorted(seen)) if identified else (),
    }


def positive_control_events(amount: float = 1.0) -> list[dict[str, object]]:
    """A predefined instrument transfer. It is not an engine contact."""

    if amount <= 0.0:
        raise ValueError("the positive control amount must be positive")
    return [
        {
            "kind": "instrument_transfer",
            "evidence": "instrument",
            "source_id": "resource-source",
            "recipient_id": "resource-recipient",
            "contact_id": "positive-control-1",
            "atp_paid": float(amount),
            "predefined": True,
        }
    ]


def negative_control_events(cost: float = 1.0) -> list[dict[str, object]]:
    """Same-cost edge removal. Predefined, and not an engine contact."""

    if cost < 0.0:
        raise ValueError("the negative-control cost must be non-negative")
    return [
        {
            "kind": "edge_removal",
            "evidence": "instrument",
            "cost": float(cost),
            "atp_paid": 0.0,
            "contact_id": "negative-control-1",
            "source_id": "resource-source",
            "recipient_id": "held-apart",
            "predefined": True,
            "independent_of": "positive-control-1",
        }
    ]


def controls_match(*, positive_amount: float, negative_cost: float) -> dict[str, object]:
    """The instrument can state an amount. That statement is not a ledger contact."""

    positive_event = positive_control_events(positive_amount)[0]
    negative_event = negative_control_events(negative_cost)[0]
    positive = transfer_yield([positive_event])
    negative = transfer_yield([negative_event])
    return {
        "positive_paid": positive["paid_transfer"],
        "negative_paid": negative["paid_transfer"],
        "instrument_positive_amount": float(positive_event["atp_paid"]),
        "instrument_negative_paid": float(negative_event["atp_paid"]),
        "positive_reachable": float(positive_event["atp_paid"]) == float(positive_amount),
        "negative_is_zero_transfer": float(negative_event["atp_paid"]) == 0.0,
        "positive_is_engine_contact": positive["contact_identified"],
        "negative_is_engine_contact": negative["contact_identified"],
        "contact_identified": False,
        "same_cost": float(negative_event["cost"]) == float(positive_event["atp_paid"]),
        "independent_contacts": (
            negative_event["contact_id"] != positive_event["contact_id"]
            and negative_event["independent_of"] == positive_event["contact_id"]
        ),
        "predefined": bool(positive_event["predefined"] and negative_event["predefined"]),
        "confirms_v1_endpoint": False,
    }


def performance_recovery(
    events: Sequence[Mapping[str, object]],
    ledger: Sequence[ATPLedgerEntry | Mapping[str, object]] | None = None,
    *,
    used_contact_ids: Collection[str] | None = None,
) -> dict[str, object]:
    """A paid reconciled transfer. Not a return to baseline, and not survival.

    The flag follows contact identification only. A drop, a baseline, and a
    persistence window are not scored here.
    """

    measured = transfer_yield(events, ledger, used_contact_ids=used_contact_ids)
    digest_flags = [event["digest_returned"] for event in events if "digest_returned" in event]
    survivor_flags = [event["n_alive"] for event in events if "n_alive" in event]
    recovered = bool(measured["contact_identified"]) and float(measured["paid_transfer"] or 0.0) > 0.0
    return {
        "endpoint_id": PREREG_V2_ID,
        "performance_recovered": recovered,
        "digest_returned": None if not digest_flags else any(bool(flag) for flag in digest_flags),
        "population_survived": None
        if not survivor_flags
        else all(int(value) > 0 for value in survivor_flags),  # type: ignore[arg-type]
        "performance_equals_digest_return": False,
        "performance_equals_population_survival": False,
        "confirms_v1_endpoint": False,
        "hypothesis_supported": False,
    }


def replicate_unit(rows: Sequence[Mapping[str, object]]) -> dict[str, object]:
    """A seed is one history. Its checkpoints are nested, not extra samples."""

    seeds = {int(row["seed"]) for row in rows}  # type: ignore[arg-type]
    pairs = {(int(row["seed"]), int(row["checkpoint"])) for row in rows}  # type: ignore[arg-type]
    return {
        "n_independent_histories": len(seeds),
        "n_seed_checkpoint_pairs": len(pairs),
        "pairs_are_independent": False,
        "replicate_unit": "seed",
        "checkpoints_nested_within_seed": True,
    }
