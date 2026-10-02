"""Version 2 of the D-2 performance endpoint. It does not confirm the 1.25× rule."""

from __future__ import annotations

import pytest

from codontrace.energy import ATPAccount
from codontrace.engine import GenesisEngine, GenesisExperimentSpec
from codontrace.errors import ConfigurationError
from codontrace.genesis.measurements.d2_recovery_v2 import (
    RECOVERY_DROP_FRACTION,
    RECOVERY_RESTORE_FRACTION,
    apply_locked_recovery_arm,
    assess_recovery,
    controls_match,
    historical_endpoint_barrier,
    name_order_mapping,
    performance_recovery,
    positive_control_events,
    replicate_unit,
    transfer_yield,
)

WITNESS = {
    "source_id": "invented",
    "recipient_id": "invented",
    "contact_id": "fake",
    "atp_paid": 10,
}


def test_positive_control_is_an_instrument_not_an_engine_contact() -> None:
    report = controls_match(positive_amount=1.0, negative_cost=1.0)
    assert report["positive_reachable"] is True
    assert report["instrument_positive_amount"] == 1.0
    assert report["positive_paid"] is None
    assert report["positive_is_engine_contact"] is False
    assert report["negative_is_zero_transfer"] is True
    assert report["instrument_negative_paid"] == 0.0
    assert report["negative_paid"] is None
    assert report["negative_is_engine_contact"] is False
    assert report["contact_identified"] is False
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
    assert recovered["performance_recovered"] is False
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


def test_invented_duplicate_contact_is_rejected() -> None:
    pair = [dict(WITNESS), dict(WITNESS)]
    with pytest.raises(ConfigurationError, match="duplicate contact id fake") as caught:
        transfer_yield(pair)
    assert "not an engine ledger record" in str(caught.value)
    with pytest.raises(ConfigurationError, match="not an engine ledger record"):
        transfer_yield([dict(WITNESS)])
    with pytest.raises(ConfigurationError, match="duplicate contact id fake"):
        performance_recovery(pair)


def _live_transfer() -> tuple[dict[str, object], list[object], float]:
    engine = GenesisEngine.from_spec(
        GenesisExperimentSpec(tick_count=0, seed=31, genome_bits=("101110000", "110000101"))
    )
    engine.run_ticks(1)
    organisms = list(engine.runner.population.organisms)
    assert len(organisms) >= 2
    source, recipient = organisms[0], organisms[1]
    assert source.id != recipient.id
    available = float(source.atp_state.runtime_available)
    paid = round(min(1.0, available), 10)
    assert paid > 0.0
    tick = 1
    source_entry = source.atp_state.debit_runtime(
        paid,
        tick=tick,
        organism_id=source.id,
        codon="d2",
        action="resource_transfer",
        reason="d2_contact",
    )
    recipient_entry = recipient.atp_state.credit_runtime(
        paid,
        tick=tick,
        organism_id=recipient.id,
        codon="d2",
        action="resource_transfer",
        reason="d2_contact",
    )
    assert isinstance(source_entry, int)
    assert isinstance(recipient_entry, int)
    source_row = source.atp_state.runtime.ledger[source_entry]
    recipient_row = recipient.atp_state.runtime.ledger[recipient_entry]
    event = {
        "evidence": "engine_ledger",
        "contact_id": "live-transfer-1",
        "source_id": source.id,
        "recipient_id": recipient.id,
        "source_entry_id": source_entry,
        "recipient_entry_id": recipient_entry,
        "atp_paid": paid,
        "loss": 0.0,
        "source_before": source_row.balance_before,
        "source_after": source_row.balance_after,
        "recipient_before": recipient_row.balance_before,
        "recipient_after": recipient_row.balance_after,
    }
    ledger = list(source.atp_state.runtime.ledger) + list(recipient.atp_state.runtime.ledger)
    return event, ledger, paid


def test_live_engine_transfer_matches_the_atp_ledger() -> None:
    event, ledger, paid = _live_transfer()
    measured = transfer_yield([event], ledger)
    assert measured["contact_identified"] is True
    assert measured["paid_transfer"] == paid
    assert measured["n_identified_contacts"] == 1
    assert measured["hypothesis_supported"] is False
    assert measured["confirms_v1_endpoint"] is False
    assert measured["validation"] == "D2-CONTACT-LEDGER-V1"


def test_live_transfer_rejects_duplicates_replay_unknown_ids_and_imbalance() -> None:
    event, ledger, paid = _live_transfer()
    with pytest.raises(ConfigurationError, match="duplicate contact id live-transfer-1"):
        transfer_yield([event, dict(event)], ledger)
    with pytest.raises(ConfigurationError, match="replay of contact id live-transfer-1"):
        transfer_yield([event], ledger, used_contact_ids={"live-transfer-1"})
    unknown = dict(event, source_id="no-such-source", recipient_id="no-such-recipient")
    with pytest.raises(ConfigurationError, match="unknown id no-such-source"):
        transfer_yield([unknown], ledger)
    unbalanced = dict(event, atp_paid=paid + 1.0)
    with pytest.raises(ConfigurationError, match="does not match the source debit"):
        transfer_yield([unbalanced], ledger)
    other = dict(event, contact_id="live-transfer-2")
    with pytest.raises(ConfigurationError, match="replay of a ledger entry"):
        transfer_yield([event, other], ledger)
    leaked = dict(event, loss=0.25)
    with pytest.raises(ConfigurationError, match="do not reconcile"):
        transfer_yield([leaked], ledger)


def test_self_transfer_needs_an_explicit_justification() -> None:
    account = ATPAccount(20.0)
    debit_id = account.debit(4.0, tick=2, agent_id="same", codon="d2", action="transfer", reason="self")
    credit_id = account.credit(4.0, tick=2, agent_id="same", codon="d2", action="transfer", reason="self")
    assert debit_id is not None
    event = {
        "evidence": "engine_ledger",
        "contact_id": "self-1",
        "source_id": "same",
        "recipient_id": "same",
        "source_entry_id": debit_id,
        "recipient_entry_id": credit_id,
        "atp_paid": 4.0,
        "loss": 0.0,
    }
    with pytest.raises(ConfigurationError, match="self-transfer"):
        transfer_yield([event], account.ledger)
    justified = dict(event, self_transfer_justification="internal reallocation defined by the model")
    measured = transfer_yield([justified], account.ledger)
    assert measured["contact_identified"] is True
    assert measured["paid_transfer"] == 4.0


def test_dissipated_loss_is_accepted_only_when_the_books_balance() -> None:
    source = ATPAccount(30.0)
    recipient = ATPAccount(5.0)
    debit_id = source.debit(10.0, tick=4, agent_id="src", codon="d2", action="transfer", reason="loss")
    credit_id = recipient.credit(7.0, tick=4, agent_id="dst", codon="d2", action="transfer", reason="loss")
    assert debit_id is not None
    event = {
        "evidence": "engine_ledger",
        "contact_id": "lossy-1",
        "source_id": "src",
        "recipient_id": "dst",
        "source_entry_id": debit_id,
        "recipient_entry_id": credit_id,
        "atp_paid": 10.0,
        "loss": 3.0,
    }
    ledger = list(source.ledger) + list(recipient.ledger)
    measured = transfer_yield([event], ledger)
    assert measured["contact_identified"] is True
    assert measured["paid_transfer"] == 10.0
    forged = {
        "entry_id": 0,
        "tick": 4,
        "agent_id": "src",
        "kind": "debit",
        "amount": 10.0,
        "balance_before": 30.0,
        "balance_after": 28.0,
        "codon": "d2",
        "action": "transfer",
        "reason": "forged",
    }
    with pytest.raises(ConfigurationError, match="does not conserve ATP"):
        transfer_yield([event], [forged, recipient.ledger[0]])


def _two_organism_engine() -> GenesisEngine:
    engine = GenesisEngine.from_spec(
        GenesisExperimentSpec(
            tick_count=0,
            seed=31,
            genome_bits=("101110000", "110000101"),
            initial_runtime_atp=40.0,
        )
    )
    engine.run_ticks(1)
    return engine


def test_a_transfer_without_a_drop_is_not_recovery() -> None:
    engine = _two_organism_engine()
    source, recipient = list(engine.runner.population.organisms)[:2]
    before = float(recipient.atp_state.runtime_available)
    paid = 1.0
    assert source.atp_state.can_execute(paid)
    source_entry = source.atp_state.debit_runtime(
        paid, tick=1, organism_id=source.id, codon="d2", action="transfer", reason="no_drop"
    )
    recipient_entry = recipient.atp_state.credit_runtime(
        paid, tick=1, organism_id=recipient.id, codon="d2", action="transfer", reason="no_drop"
    )
    assert isinstance(source_entry, int)
    after = float(recipient.atp_state.runtime_available)
    event = {
        "evidence": "engine_ledger",
        "contact_id": "no-drop-1",
        "source_id": source.id,
        "recipient_id": recipient.id,
        "source_entry_id": source_entry,
        "recipient_entry_id": recipient_entry,
        "atp_paid": paid,
        "loss": 0.0,
    }
    ledger = list(source.atp_state.runtime.ledger) + list(recipient.atp_state.runtime.ledger)
    report = performance_recovery(
        [event],
        ledger,
        boundaries=[before, after, after, after],
        recipient_id=recipient.id,
    )
    assert report["transfer_recorded"] is True
    assert report["performance_recovered"] is False
    assert report["recovery_reason"] == "no_drop"
    assert report["confirms_v1_endpoint"] is False
    assert report["hypothesis_supported"] is False


def test_an_instrument_trajectory_is_not_recovery() -> None:
    report = assess_recovery(
        [10.0, 4.0, 9.0, 9.0],
        positive_control_events(5.0),
        recipient_id="resource-recipient",
    )
    assert report["performance_recovered"] is False
    assert report["reason"] == "no_reconciling_contact"
    assert report["confirms_v1_endpoint"] is False
    assert report["endpoint_id"] == "FI-RESOURCE-RECOVERY-V3"


def test_live_positive_control_recovers_and_the_matched_negative_does_not() -> None:
    positive_engine = _two_organism_engine()
    negative_engine = _two_organism_engine()
    positive_organisms = list(positive_engine.runner.population.organisms)
    negative_organisms = list(negative_engine.runner.population.organisms)
    positive = apply_locked_recovery_arm(positive_organisms[0], positive_organisms[1], tick=1, arm="positive")
    negative = apply_locked_recovery_arm(negative_organisms[0], negative_organisms[1], tick=1, arm="negative")
    assert positive["source_cost"] == negative["source_cost"]
    assert float(positive["source_cost"]) > 0.0
    assert positive["disturbance_cost"] == negative["disturbance_cost"]
    assert positive["recipient_credit"] == positive["source_cost"]
    assert negative["recipient_credit"] == 0.0
    assert positive["performance_recovered"] is True
    assert negative["performance_recovered"] is False
    assert negative["reason"] == "not_restored"
    assert positive["confirms_v1_endpoint"] is False
    assert negative["hypothesis_supported"] is False
    baseline = float(positive["boundaries"][0])  # type: ignore[index]
    assert float(positive["boundaries"][1]) <= RECOVERY_DROP_FRACTION * baseline  # type: ignore[index]
    assert float(positive["boundaries"][2]) >= RECOVERY_RESTORE_FRACTION * baseline  # type: ignore[index]
    assert float(positive["boundaries"][3]) >= RECOVERY_RESTORE_FRACTION * baseline  # type: ignore[index]
    negative_baseline = float(negative["boundaries"][0])  # type: ignore[index]
    assert float(negative["boundaries"][1]) <= RECOVERY_DROP_FRACTION * negative_baseline  # type: ignore[index]
    assert float(negative["boundaries"][2]) <= RECOVERY_DROP_FRACTION * negative_baseline  # type: ignore[index]
