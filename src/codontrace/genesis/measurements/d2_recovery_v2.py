"""D-2 transfer validation V2 and time-bound recovery V4.

The locked 1.25× rule stays the historical record. This module does not
re-read it as a success, and it does not treat a later definition as
confirmation of that design. Topology and contact flags stay false when the
only pairing is sorted names.

A scientific contact is a pair of engine ATP ledger rows: one source debit
and one recipient credit. At the ledger's 1e-10 rounding, source debit =
recipient credit + non-negative loss, and ``atp_paid`` is that source debit.
Names alone are not a contact. Instrument rows stay instrument-only.
``FI-RESOURCE-RECOVERY-V4-TIME-BOUND`` retains the V3 baseline-normalized
fractions and additionally binds every sampled boundary to its run, tick,
recipient and ledger cursor.
It does not confirm the locked 1.25× rule, and a transfer with no drop is
not that return.
"""

from __future__ import annotations

import math
from collections.abc import Collection, Mapping, Sequence
from typing import Literal, cast

from codontrace.dynvalues import same_float, same_int
from codontrace.energy import ATPAccount, ATPLedgerEntry
from codontrace.errors import ConfigurationError
from codontrace.genesis.canonical import canonical_digest
from codontrace.genesis.organism import GenesisOrganism

PREREG_V1_ID = "FI-RARECLASS-CONTACT-YIELD-V1"
PREREG_V2_ID = "FI-RESOURCE-TRANSFER-V2"
OLD_LOCKED_MULTIPLIER = 1.25
CONTACT_VALIDATION_ID = "D2-CONTACT-LEDGER-V2"
ENGINE_LEDGER_EVIDENCE = "engine_ledger"
_LEDGER_PLACES = 10


def _transfer_binding(event: Mapping[str, object]) -> str:
    """Bind both ledger rows to one transfer, its history and its participants."""
    body = {key: event[key] for key in ("run_id", "contact_id", "tick", "source_id", "recipient_id")}
    body.update(atp_paid=_non_negative(event.get("atp_paid"), "atp_paid"),
                loss=_non_negative(event.get("loss", 0.0), "loss"))
    return canonical_digest(body, prefix="d2_transfer_v2")


def execute_runtime_transfer(
    source: ATPAccount, recipient: ATPAccount, *, run_id: str, contact_id: str,
    source_id: str, recipient_id: str, tick: int, amount: float, loss: float = 0.0,
    self_transfer_justification: str | None = None,
) -> dict[str, object]:
    """Record an explicit intervention transfer; this is not spontaneous ecology.

    Validates the complete operation before mutating either account. Both rows
    carry the same content binding. A replay is rejected against the ledgers.
    """
    event: dict[str, object] = {
        "evidence": ENGINE_LEDGER_EVIDENCE, "run_id": run_id, "contact_id": contact_id,
        "source_id": source_id, "recipient_id": recipient_id, "tick": tick,
        "atp_paid": float(_non_negative(amount, "amount")),
        "loss": float(_non_negative(loss, "loss")),
    }
    for name in ("run_id", "contact_id", "source_id", "recipient_id"):
        _text(event, name)
    if isinstance(tick, bool) or not isinstance(tick, int) or tick < 0:
        raise ConfigurationError("transfer tick must be a non-negative integer")
    if (source is recipient) != (source_id == recipient_id):
        raise ConfigurationError("account identity does not match the transfer participants")
    if source_id == recipient_id:
        if not isinstance(self_transfer_justification, str) or not self_transfer_justification.strip():
            raise ConfigurationError("self-transfer requires an explicit justification")
        event["self_transfer_justification"] = self_transfer_justification
    paid, dissipated = same_float(event["atp_paid"]), same_float(event["loss"])
    if paid <= 0.0 or dissipated > paid or not source.can_pay(paid):
        raise ConfigurationError("source cannot fund a positive transfer with this loss")
    binding = _transfer_binding(event)
    if any(row.reason == binding for row in (*source.ledger, *recipient.ledger)):
        raise ConfigurationError("replay of a transfer binding")
    for account in (source, recipient):
        if account.ledger and tick < account.ledger[-1].tick:
            raise ConfigurationError("transfer precedes the account history")
    if not math.isfinite(recipient.current_atp + paid - dissipated):
        raise ConfigurationError("recipient balance would be non-finite")
    source_entry = source.debit(paid, tick=tick, agent_id=source_id, codon="d2",
                                action="d2_transfer_v2", reason=binding)
    recipient_entry = recipient.credit(paid - dissipated, tick=tick, agent_id=recipient_id,
                                       codon="d2", action="d2_transfer_v2", reason=binding)
    event.update(source_entry_id=source_entry, recipient_entry_id=recipient_entry)
    return event


def capture_recovery_boundary(account: ATPAccount, *, run_id: str, recipient_id: str,
                              tick: int) -> dict[str, object]:
    """A balance sample anchored to an append-only recipient ledger cursor."""
    if not run_id.strip() or not recipient_id.strip():
        raise ConfigurationError("boundary requires history and recipient ids")
    if isinstance(tick, bool) or not isinstance(tick, int) or tick < 0:
        raise ConfigurationError("boundary tick must be a non-negative integer")
    if account.ledger and tick < account.ledger[-1].tick:
        raise ConfigurationError("boundary precedes its ledger")
    return {"run_id": run_id, "recipient_id": recipient_id, "tick": tick,
            "value": account.current_atp, "ledger_entry_count": len(account.ledger)}

#: Locked before any live control in this module is scored.
#: Ingrisch and Bahn 2018, Trends Ecol. Evol. 33:251–259,
#: https://doi.org/10.1016/j.tree.2018.01.013 : recovery is a return toward
#: the pre-disturbance baseline after an impact. A transfer with no impact
#: is not recovery. These fractions do not confirm the historical 1.25× rule.
PREREG_V3_ID = "FI-RESOURCE-RECOVERY-V3"
PREREG_V4_ID = "FI-RESOURCE-RECOVERY-V4-TIME-BOUND"
RECOVERY_DROP_FRACTION = 0.5
RECOVERY_RESTORE_FRACTION = 0.8
RECOVERY_WINDOW_BOUNDARIES = 2
RECOVERY_PERSISTENCE_BOUNDARIES = 1


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
    if same_int(source_row["tick"]) != same_int(recipient_row["tick"]):
        raise ConfigurationError("source debit and recipient credit are not one contact")
    _stated_balance(event, "source_before", source_row.get("balance_before"), "balance_before")
    _stated_balance(event, "source_after", source_row.get("balance_after"), "balance_after")
    _stated_balance(event, "recipient_before", recipient_row.get("balance_before"), "balance_before")
    _stated_balance(event, "recipient_after", recipient_row.get("balance_after"), "balance_after")
    source_debit = same_float(source_row["amount"])
    recipient_credit = same_float(recipient_row["amount"])
    loss = _non_negative(event.get("loss", 0.0), "loss")
    paid = _non_negative(event.get("atp_paid"), "atp_paid")
    if not _same(paid, source_debit):
        raise ConfigurationError("atp_paid does not match the source debit")
    if not _same(source_debit, recipient_credit + loss):
        raise ConfigurationError("source debit, recipient credit, and loss do not reconcile")
    _text(event, "run_id")
    tick = event.get("tick")
    if isinstance(tick, bool) or not isinstance(tick, int) or tick < 0 or tick != source_row["tick"]:
        raise ConfigurationError("transfer tick does not match the ledger")
    binding = _transfer_binding(event)
    if any(row.get("action") != "d2_transfer_v2" or row.get("reason") != binding
           for row in (source_row, recipient_row)):
        raise ConfigurationError("ledger rows are not bound to this transfer")
    used_entries.add(source_key)
    used_entries.add(recipient_key)
    return paid


def transfer_yield(
    events: Sequence[Mapping[str, object]],
    ledger: Sequence[ATPLedgerEntry | Mapping[str, object]] | None = None,
    *,
    used_contact_ids: Collection[str] | None = None,
    used_ledger_entries: Collection[tuple[str, int]] | None = None,
) -> dict[str, object]:
    """ATP moved on an engine ledger contact.

    Name-order rows are not contacts and force ``contact_identified`` false.
    Instrument rows are counted apart and are never engine contacts. A claim
    that is duplicate, replayed, unknown, a bare self-transfer, or
    inconsistent with the ledger is rejected.
    """

    index = _index_ledger(ledger)
    already = set(used_contact_ids or ())
    used_entries: set[tuple[str, int]] = set(used_ledger_entries or ())
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
        "consumed_ledger_entries": tuple(sorted(used_entries - set(used_ledger_entries or ()))) if identified else (),
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
        "instrument_positive_amount": same_float(positive_event["atp_paid"]),
        "instrument_negative_paid": same_float(negative_event["atp_paid"]),
        "positive_reachable": same_float(positive_event["atp_paid"]) == same_float(positive_amount),
        "negative_is_zero_transfer": same_float(negative_event["atp_paid"]) == 0.0,
        "positive_is_engine_contact": positive["contact_identified"],
        "negative_is_engine_contact": negative["contact_identified"],
        "contact_identified": False,
        "same_cost": same_float(negative_event["cost"]) == same_float(positive_event["atp_paid"]),
        "independent_contacts": (
            negative_event["contact_id"] != positive_event["contact_id"]
            and negative_event["independent_of"] == positive_event["contact_id"]
        ),
        "predefined": bool(positive_event["predefined"] and negative_event["predefined"]),
        "confirms_v1_endpoint": False,
    }


def _grid(value: float, *, up: bool) -> float:
    """Snap onto the ledger's 1e-10 grid without crossing the locked fraction."""

    scaled = value * 10**_LEDGER_PLACES
    snapped = math.ceil(scaled - 1e-9) if up else math.floor(scaled + 1e-9)
    return cast(float, snapped / 10**_LEDGER_PLACES)


def _boundaries(boundaries: Sequence[object]) -> list[float]:
    values: list[float] = []
    for value in boundaries:
        if isinstance(value, bool) or not isinstance(value, int | float):
            raise ConfigurationError("a recovery boundary must be finite")
        number = float(value)
        if not math.isfinite(number):
            raise ConfigurationError("a recovery boundary must be finite")
        values.append(number)
    if not values:
        raise ConfigurationError("recovery needs a baseline boundary")
    if values[0] <= 0.0:
        raise ConfigurationError("baseline must be finite and positive")
    return values


def _recipient_credit(events: Sequence[Mapping[str, object]], recipient_id: str) -> float:
    total = 0.0
    for event in events:
        if event.get("evidence") != ENGINE_LEDGER_EVIDENCE or event.get("recipient_id") != recipient_id:
            continue
        paid = _non_negative(event.get("atp_paid"), "atp_paid")
        loss = _non_negative(event.get("loss", 0.0), "loss")
        total += paid - loss
    return total


def assess_recovery(
    boundaries: Sequence[object],
    events: Sequence[Mapping[str, object]] = (),
    ledger: Sequence[ATPLedgerEntry | Mapping[str, object]] | None = None,
    *,
    recipient_id: str,
    used_contact_ids: Collection[str] | None = None,
    used_ledger_entries: Collection[tuple[str, int]] | None = None,
) -> dict[str, object]:
    """Score the versioned time-bound V4 rule with the V3 fractions. This does not confirm the 1.25× endpoint.

    Baseline is boundary 0. A drop is a later boundary at or below half of
    that baseline. Restoration is a later boundary, at most two steps after
    the drop, at or above 80% of baseline, that is still there on the next
    boundary. The rise from the drop to that restoration must equal a
    reconciled ledger credit to ``recipient_id``.
    """

    if not isinstance(recipient_id, str) or not recipient_id.strip():
        raise ConfigurationError("recovery scoring needs the recipient id")
    if not boundaries or not all(isinstance(row, Mapping) for row in boundaries):
        return {"endpoint_id": PREREG_V4_ID, "performance_recovered": False,
                "reason": "unbound_boundaries", "transfer_recorded": False,
                "confirms_v1_endpoint": False, "hypothesis_supported": False}
    samples = cast(list[Mapping[str, object]], list(boundaries))
    run_id = _text(samples[0], "run_id")
    recipient_rows = sorted(
        (dict(_entry_view(row)) for row in ledger or () if _entry_view(row).get("agent_id") == recipient_id),
        key=lambda row: same_int(row["entry_id"]),
    )
    _index_ledger(ledger)
    for index, row in enumerate(recipient_rows):
        if row["entry_id"] != index:
            raise ConfigurationError("recovery needs a complete recipient ledger")
        # Legacy engine entries contain action-local and generation-local tick
        # counters. Entry ids establish append order; sampled V4 boundaries
        # separately establish the time of the analysed interval.
        if index and not _same(same_float(row["balance_before"]), same_float(recipient_rows[index - 1]["balance_after"])):
            raise ConfigurationError("recipient ledger history is discontinuous")
    values = _boundaries([row.get("value") for row in samples])
    previous_tick = -1
    previous_count = 0
    for sample in samples:
        if _text(sample, "run_id") != run_id or _text(sample, "recipient_id") != recipient_id:
            raise ConfigurationError("recovery boundaries mix histories or recipients")
        tick, count = sample.get("tick"), sample.get("ledger_entry_count")
        if isinstance(tick, bool) or not isinstance(tick, int) or tick <= previous_tick:
            raise ConfigurationError("recovery ticks must be strictly increasing")
        if isinstance(count, bool) or not isinstance(count, int) or count < previous_count or count > len(recipient_rows):
            raise ConfigurationError("invalid boundary ledger cursor")
        if count != sum(same_int(row["tick"]) <= tick for row in recipient_rows):
            raise ConfigurationError("boundary cursor does not match its tick")
        if recipient_rows:
            expected = recipient_rows[count - 1]["balance_after"] if count else recipient_rows[0]["balance_before"]
            if not _same(same_float(sample["value"]), same_float(expected)):
                raise ConfigurationError("boundary balance does not match its ledger cursor")
        previous_tick, previous_count = tick, count
    baseline = values[0]
    drop_index: int | None = None
    for index, value in enumerate(values):
        if index > 0 and value <= RECOVERY_DROP_FRACTION * baseline:
            drop_index = index
            break
    definition = {
        "drop_fraction_max": RECOVERY_DROP_FRACTION,
        "restore_fraction_min": RECOVERY_RESTORE_FRACTION,
        "window_boundaries": RECOVERY_WINDOW_BOUNDARIES,
        "persistence_boundaries": RECOVERY_PERSISTENCE_BOUNDARIES,
    }
    restore_index: int | None = None
    reason = "no_drop"
    shape = False
    saw_lapse = False
    if drop_index is not None:
        reason = "not_restored"
        last = min(len(values) - 1, drop_index + RECOVERY_WINDOW_BOUNDARIES)
        for index in range(drop_index + 1, last + 1):
            if values[index] < RECOVERY_RESTORE_FRACTION * baseline:
                continue
            end = index + RECOVERY_PERSISTENCE_BOUNDARIES
            held = end < len(values) and all(
                values[point] >= RECOVERY_RESTORE_FRACTION * baseline for point in range(index, end + 1)
            )
            if held:
                restore_index = index
                shape = True
                reason = "restored"
                break
            saw_lapse = True
        if not shape and saw_lapse:
            reason = "not_persistent"
    measured = transfer_yield(events, ledger, used_contact_ids=used_contact_ids,
                              used_ledger_entries=used_ledger_entries)
    if any(event.get("run_id") != run_id for event in events if _is_contact_claim(event)):
        raise ConfigurationError("transfer and recovery belong to different histories")
    credit = 0.0
    if shape and restore_index is not None and drop_index is not None:
        start_count = same_int(samples[drop_index]["ledger_entry_count"])
        end_count = same_int(samples[restore_index]["ledger_entry_count"])
        window_events = [event for event in events if event.get("recipient_id") == recipient_id
                         and isinstance(event.get("recipient_entry_id"), int)
                         and start_count <= same_int(event["recipient_entry_id"]) < end_count
                         and same_int(samples[drop_index]["tick"]) < same_int(event["tick"]) <= same_int(samples[restore_index]["tick"])]
        credit = _recipient_credit(window_events, recipient_id) if measured["contact_identified"] else 0.0
        interval_rows = recipient_rows[start_count:end_count]
        contact_entries = {event["recipient_entry_id"] for event in window_events}
        unexplained = any(row["kind"] == "credit" and row["entry_id"] not in contact_entries
                          for row in interval_rows)
        debit = sum(same_float(row["amount"]) for row in interval_rows if row["kind"] == "debit")
        gain = values[restore_index] - values[drop_index]
        if credit <= 0.0 or not measured["contact_identified"]:
            shape = False
            reason = "no_reconciling_contact"
        elif unexplained:
            shape = False
            reason = "unattributed_credit"
        elif not _same(gain, credit - debit):
            shape = False
            reason = "gain_does_not_match_credit"
    return {
        "endpoint_id": PREREG_V4_ID,
        "definition": definition,
        "baseline": baseline,
        "drop_index": drop_index,
        "restore_index": restore_index if shape else None,
        "recipient_credit": credit if shape else 0.0,
        "performance_recovered": shape,
        "reason": reason,
        "transfer_recorded": bool(measured["contact_identified"]) and same_float(measured["paid_transfer"] or 0.0) > 0.0,
        "consumed_contact_ids": measured["consumed_contact_ids"],
        "consumed_ledger_entries": measured["consumed_ledger_entries"],
        "confirms_v1_endpoint": False,
        "hypothesis_supported": False,
    }


def apply_locked_recovery_arm(
    source: GenesisOrganism,
    recipient: GenesisOrganism,
    *,
    tick: int,
    arm: Literal["positive", "negative"],
) -> dict[str, object]:
    """Place the locked drop, then either restore it or pay the same cost aside.

    Samples are recipient runtime ATP: baseline, after the drop, after the
    arm, and one persistence sample with no further credit. The positive arm
    credits the recipient from the source. The negative arm debits that same
    amount from the source and does not credit the recipient.
    """

    if arm not in {"positive", "negative"}:
        raise ConfigurationError("recovery arm must be positive or negative")
    if source.id == recipient.id:
        raise ConfigurationError("the recovery control needs two organisms")
    run_id = f"d2-control:{source.id}:{recipient.id}:{tick}:{arm}"
    samples = [capture_recovery_boundary(recipient.atp_state.runtime, run_id=run_id,
               recipient_id=recipient.id, tick=tick)]
    baseline = float(recipient.atp_state.runtime_available)
    if baseline <= 0.0:
        raise ConfigurationError("recovery control baseline must be positive")
    drop_level = _grid(baseline * RECOVERY_DROP_FRACTION, up=False)
    disturbance = round(baseline - drop_level, _LEDGER_PLACES)
    if disturbance <= 0.0 or not recipient.atp_state.can_execute(disturbance):
        raise ConfigurationError("recovery control could not place the locked drop")
    drop_entry = recipient.atp_state.debit_runtime(
        disturbance,
        tick=tick + 1,
        organism_id=recipient.id,
        codon="d2",
        action="recovery_drop",
        reason="v3_drop",
    )
    if drop_entry is None:
        raise ConfigurationError("recovery control could not place the locked drop")
    samples.append(capture_recovery_boundary(recipient.atp_state.runtime, run_id=run_id,
                   recipient_id=recipient.id, tick=tick + 1))
    dropped = float(recipient.atp_state.runtime_available)
    restore_level = _grid(baseline * RECOVERY_RESTORE_FRACTION, up=True)
    credit = round(restore_level - dropped, _LEDGER_PLACES)
    if credit <= 0.0 or not source.atp_state.can_execute(credit):
        raise ConfigurationError("source cannot fund the locked restore")
    events: list[dict[str, object]] = []
    if arm == "positive":
        events.append(execute_runtime_transfer(
            source.atp_state.runtime, recipient.atp_state.runtime,
            run_id=run_id, contact_id="v4-positive-1", source_id=source.id,
            recipient_id=recipient.id, tick=tick + 2, amount=credit,
        ))
    else:
        source.atp_state.debit_runtime(
            credit, tick=tick + 2, organism_id=source.id, codon="d2",
            action="matched_uncredited_cost", reason="v4_negative_matched_cost",
        )
    after = float(recipient.atp_state.runtime_available)
    persisted = after
    samples.extend(capture_recovery_boundary(recipient.atp_state.runtime, run_id=run_id,
                   recipient_id=recipient.id, tick=stage) for stage in (tick + 2, tick + 3))
    boundaries = [baseline, dropped, after, persisted]
    ledger = list(source.atp_state.runtime.ledger) + list(recipient.atp_state.runtime.ledger)
    scored = assess_recovery(samples, events, ledger, recipient_id=recipient.id)
    return {
        "arm": arm,
        "endpoint_id": PREREG_V4_ID,
        "baseline": baseline,
        "boundaries": boundaries,
        "boundary_records": samples,
        "control_only": True,
        "disturbance_cost": disturbance,
        "source_cost": credit,
        "recipient_credit": credit if arm == "positive" else 0.0,
        "performance_recovered": scored["performance_recovered"],
        "reason": scored["reason"],
        "recovery": scored,
        "confirms_v1_endpoint": False,
        "hypothesis_supported": False,
    }


def performance_recovery(
    events: Sequence[Mapping[str, object]],
    ledger: Sequence[ATPLedgerEntry | Mapping[str, object]] | None = None,
    *,
    used_contact_ids: Collection[str] | None = None,
    used_ledger_entries: Collection[tuple[str, int]] | None = None,
    boundaries: Sequence[object] | None = None,
    recipient_id: str | None = None,
) -> dict[str, object]:
    """Name a transfer as a transfer. Recovery requires time-bound V4 evidence.

    Without a baseline series, a paid contact is ``transfer_recorded`` and
    ``performance_recovered`` stays false. Digest return and survival are
    separate flags and are not this endpoint.
    """

    measured = transfer_yield(events, ledger, used_contact_ids=used_contact_ids,
                              used_ledger_entries=used_ledger_entries)
    digest_flags = [event["digest_returned"] for event in events if "digest_returned" in event]
    survivor_flags = [event["n_alive"] for event in events if "n_alive" in event]
    transfer_recorded = bool(measured["contact_identified"]) and same_float(measured["paid_transfer"] or 0.0) > 0.0
    recovery: dict[str, object] | None = None
    recovered = False
    reason = "no_baseline"
    if boundaries is not None:
        if recipient_id is None:
            raise ConfigurationError("recovery scoring needs the recipient id")
        recovery = assess_recovery(boundaries, events, ledger, recipient_id=recipient_id,
                                   used_contact_ids=used_contact_ids, used_ledger_entries=used_ledger_entries)
        recovered = bool(recovery["performance_recovered"])
        reason = str(recovery["reason"])
    return {
        "endpoint_id": PREREG_V2_ID if boundaries is None else PREREG_V4_ID,
        "transfer_recorded": transfer_recorded,
        "performance_recovered": recovered,
        "recovery_reason": reason,
        "recovery": recovery,
        "digest_returned": None if not digest_flags else any(bool(flag) for flag in digest_flags),
        "population_survived": None
        if not survivor_flags
        else all(same_int(value) > 0 for value in survivor_flags),
        "performance_equals_digest_return": False,
        "performance_equals_population_survival": False,
        "confirms_v1_endpoint": False,
        "hypothesis_supported": False,
    }


def replicate_unit(rows: Sequence[Mapping[str, object]]) -> dict[str, object]:
    """A seed is one history. Its checkpoints are nested, not extra samples."""

    seeds = {same_int(row["seed"]) for row in rows}
    pairs = {(same_int(row["seed"]), same_int(row["checkpoint"])) for row in rows}
    return {
        "n_independent_histories": len(seeds),
        "n_seed_checkpoint_pairs": len(pairs),
        "pairs_are_independent": False,
        "replicate_unit": "seed",
        "checkpoints_nested_within_seed": True,
    }
