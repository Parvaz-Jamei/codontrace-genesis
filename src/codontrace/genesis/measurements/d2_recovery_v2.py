"""D-2 performance endpoint, version 2.

The locked 1.25× rule stays the historical record. This module does not
re-read it as a success, and it does not treat a later definition as
confirmation of that design. Topology and contact flags stay false when the
only pairing is sorted names.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence

PREREG_V1_ID = "FI-RARECLASS-CONTACT-YIELD-V1"
PREREG_V2_ID = "FI-RESOURCE-TRANSFER-V2"
OLD_LOCKED_MULTIPLIER = 1.25


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


def _identified_transfer(event: Mapping[str, object]) -> float | None:
    if event.get("mapping") == "sorted_name_order":
        return None
    source = event.get("source_id")
    recipient = event.get("recipient_id")
    contact = event.get("contact_id")
    if not source or not recipient or contact is None:
        return None
    paid = float(event.get("atp_paid", 0.0))  # type: ignore[arg-type]
    if not math.isfinite(paid) or paid < 0.0:
        raise ValueError("atp_paid must be finite and non-negative")
    return paid


def transfer_yield(events: Sequence[Mapping[str, object]]) -> dict[str, object]:
    """ATP moved from a named source to a named recipient on a contact id.

    Name-order rows are skipped and force ``contact_identified`` false.
    """

    paid = 0.0
    identified = True
    counted = 0
    if not events:
        identified = False
    for event in events:
        amount = _identified_transfer(event)
        if amount is None:
            identified = False
            continue
        paid += amount
        counted += 1
    return {
        "endpoint_id": PREREG_V2_ID,
        "paid_transfer": paid if identified else None,
        "n_identified_contacts": counted,
        "contact_identified": identified and counted > 0,
        "topology_identified": False,
        "confirms_v1_endpoint": False,
        "hypothesis_supported": False,
    }


def positive_control_events(amount: float = 1.0) -> list[dict[str, object]]:
    """A predefined instrument transfer. Reaching it is not a discovery."""

    if amount <= 0.0:
        raise ValueError("the positive control amount must be positive")
    return [
        {
            "kind": "instrument_transfer",
            "source_id": "resource-source",
            "recipient_id": "resource-recipient",
            "contact_id": "positive-control-1",
            "atp_paid": float(amount),
            "predefined": True,
        }
    ]


def negative_control_events(cost: float = 1.0) -> list[dict[str, object]]:
    """Same-cost edge removal, predefined, and independent of the positive contact."""

    if cost < 0.0:
        raise ValueError("the negative-control cost must be non-negative")
    return [
        {
            "kind": "edge_removal",
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
    positive_event = positive_control_events(positive_amount)[0]
    negative_event = negative_control_events(negative_cost)[0]
    positive = transfer_yield([positive_event])
    negative = transfer_yield([negative_event])
    return {
        "positive_paid": positive["paid_transfer"],
        "negative_paid": negative["paid_transfer"],
        "positive_reachable": positive["paid_transfer"] == positive_amount,
        "negative_is_zero_transfer": negative["paid_transfer"] == 0.0,
        "same_cost": float(negative_event["cost"]) == float(positive_event["atp_paid"]),
        "independent_contacts": (
            negative_event["contact_id"] != positive_event["contact_id"]
            and negative_event["independent_of"] == positive_event["contact_id"]
        ),
        "predefined": bool(positive_event["predefined"] and negative_event["predefined"]),
        "confirms_v1_endpoint": False,
    }


def performance_recovery(events: Sequence[Mapping[str, object]]) -> dict[str, object]:
    """Recovery of transferred resource. Not digest return, and not survival."""

    measured = transfer_yield(events)
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
