"""Version 2 of the D-2 performance endpoint. It does not confirm the 1.25× rule."""

from __future__ import annotations

from codontrace.genesis.measurements.d2_recovery_v2 import (
    controls_match,
    historical_endpoint_barrier,
    name_order_mapping,
    performance_recovery,
    positive_control_events,
    replicate_unit,
    transfer_yield,
)


def test_positive_control_is_reachable_and_the_negative_control_pays_nothing() -> None:
    report = controls_match(positive_amount=1.0, negative_cost=1.0)
    assert report["positive_reachable"] is True
    assert report["positive_paid"] == 1.0
    assert report["negative_is_zero_transfer"] is True
    assert report["same_cost"] is True
    assert report["independent_contacts"] is True
    assert report["confirms_v1_endpoint"] is False


def test_name_order_is_not_an_identified_contact() -> None:
    mapping = name_order_mapping(["b", "a", "c"])
    assert mapping["pairs"] == [("a", "b")]
    assert mapping["unpaired"] == ["c"]
    assert mapping["topology_identified"] is False
    assert mapping["contact_identified"] is False
    events = [{"mapping": "sorted_name_order", "source_id": "a", "recipient_id": "b", "atp_paid": 5.0}]
    measured = transfer_yield(events)
    assert measured["contact_identified"] is False
    assert measured["paid_transfer"] is None
    assert measured["topology_identified"] is False


def test_old_barrier_is_not_confirmed_by_the_new_endpoint() -> None:
    barrier = historical_endpoint_barrier()
    assert barrier["positive_control_reached"] is False
    assert barrier["arm_zeros_reject_an_effect"] is False
    assert barrier["successor_confirms_v1"] is False
    recovered = performance_recovery(positive_control_events(1.0))
    assert recovered["performance_recovered"] is True
    assert recovered["digest_returned"] is None
    assert recovered["population_survived"] is None
    assert recovered["performance_equals_digest_return"] is False
    alive_without_transfer = performance_recovery(
        [{"digest_returned": True, "n_alive": 4, "mapping": "sorted_name_order", "atp_paid": 3.0}]
    )
    assert alive_without_transfer["performance_recovered"] is False
    assert alive_without_transfer["digest_returned"] is True
    assert alive_without_transfer["population_survived"] is True
    assert recovered["confirms_v1_endpoint"] is False


def test_two_seeds_at_three_checkpoints_are_two_histories() -> None:
    rows = [
        {"seed": seed, "checkpoint": checkpoint}
        for seed in (5501, 5502)
        for checkpoint in (10, 20, 30)
    ]
    report = replicate_unit(rows)
    assert report["n_seed_checkpoint_pairs"] == 6
    assert report["n_independent_histories"] == 2
    assert report["pairs_are_independent"] is False
    assert report["replicate_unit"] == "seed"
