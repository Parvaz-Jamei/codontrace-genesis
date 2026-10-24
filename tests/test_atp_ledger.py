"""Closed world ATP ledger: exact conservation, bypass detection, hash chain."""

from __future__ import annotations

import copy
import pickle
from fractions import Fraction

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from codontrace.atp_ledger import (
    CLEARING,
    RESERVOIR,
    ATPConservationError,
    WorldATPLedger,
    verify_ledger_chain,
)
from codontrace.energy import ATPAccount

amounts = st.floats(min_value=0.0, max_value=1e6, allow_nan=False, allow_infinity=False)
ops = st.lists(
    st.tuples(st.sampled_from(["debit", "credit", "couple", "birth", "death", "tick"]),
              st.integers(0, 7), st.integers(0, 7), amounts, st.floats(0.0, 1.0)),
    max_size=60,
)


def _world(n: int, init: float):
    led = WorldATPLedger("t")
    led.fund_reservoir(n * init, tick=0)
    accts = {}
    for i in range(n):
        accts[f"a{i}"] = ATPAccount(init)
        led.attach(f"a{i}", accts[f"a{i}"], tick=0)
    led.close_tick(0, {k: a.current_atp for k, a in accts.items()})
    return led, accts


@settings(max_examples=150, deadline=None)
@given(n=st.integers(1, 6), init=amounts, program=ops)
def test_random_programs_conserve_exactly(n, init, program):
    led, accts = _world(n, init)
    tick, born = 1, 0
    for op, i, j, amt, frac in program:
        ids = sorted(accts)
        if not ids:
            break
        a, b = ids[i % len(ids)], ids[j % len(ids)]
        if op == "debit":
            accts[a].debit(min(amt, accts[a].current_atp), tick=tick, agent_id=a, codon="X", action="basal", reason="r")
        elif op == "credit":
            accts[a].credit(amt, tick=tick, agent_id=a, codon="X", action="forage", reason="r")
        elif op == "couple" and a != b:
            pay = min(amt, accts[a].current_atp)
            with led.transfer_scope("coupling", tick=tick):
                if accts[a].debit(pay, tick=tick, agent_id=a, codon="C", action="c", reason="r") is not None:
                    accts[b].credit(min(pay * (1 - frac), pay),
                                    tick=tick, agent_id=b, codon="C", action="c", reason="r")
        elif op == "birth":
            born += 1
            cid = f"c{born}"
            accts[cid] = ATPAccount(amt)
            led.attach(cid, accts[cid], tick=tick)
        elif op == "death" and len(accts) > 1:
            led.detach(a, accts.pop(a), tick=tick)
        else:
            led.close_tick(tick, {k: x.current_atp for k, x in accts.items()})
            tick += 1
    head = led.close_tick(tick, {k: x.current_atp for k, x in accts.items()})
    t = led.totals()
    assert t["agents"] + t["reservoir"] + t["clearing"] == t["sources_in"] - t["sinks_out"]
    assert t["agents"] == sum((Fraction(x.current_atp) for x in accts.values()), Fraction(0))
    assert verify_ledger_chain(led.journal_records()) == head


@settings(max_examples=100, deadline=None)
@given(start=amounts, deltas=st.lists(st.floats(-50, 50, allow_nan=False), max_size=40))
def test_scalar_adjust_matches_engine_float_arithmetic(start, deltas):
    led = WorldATPLedger()
    led.open_agent("o", start, tick=0)
    x = start
    for k, d in enumerate(deltas):
        legacy = x + d
        x = led.adjust("o", x, d, tick=k, source="source:reward", sink="sink:cost")
        assert x == legacy  # byte-identical float path
        led.close_tick(k, {"o": x})


def test_bypass_is_detected():
    led, accts = _world(2, 5.0)
    accts["a0"].current_atp = 9.0  # write outside the ledger
    with pytest.raises(ATPConservationError, match="bypass"):
        led.close_tick(1, {k: a.current_atp for k, a in accts.items()})


def test_unledgered_agent_and_ghost_detected():
    led, accts = _world(2, 5.0)
    with pytest.raises(ATPConservationError, match="mismatch"):
        led.close_tick(1, {"a0": 5.0, "a1": 5.0, "zz": 0.0})
    with pytest.raises(ATPConservationError, match="mismatch"):
        led.close_tick(1, {"a0": 5.0})


def test_transfer_creation_raises_and_loss_is_booked():
    led, accts = _world(2, 5.0)
    with led.transfer_scope("coupling", tick=1):
        accts["a0"].debit(2.0, tick=1, agent_id="a0", codon="C", action="c", reason="r")
        accts["a1"].credit(1.5, tick=1, agent_id="a1", codon="C", action="c", reason="r")
    assert led.balance("sink:coupling_loss") == Fraction(1, 2)
    assert led.balance(CLEARING) == 0
    with pytest.raises(ATPConservationError, match="created"):
        with led.transfer_scope("coupling", tick=1):
            accts["a1"].credit(1.0, tick=1, agent_id="a1", codon="C", action="c", reason="r")


def test_rounding_residue_is_booked_not_hidden():
    led = WorldATPLedger()
    a = ATPAccount(1.303216892061755)
    led.attach("a", a, tick=0)
    a.debit(1.303216892061755 - 1e-12, tick=1, agent_id="a", codon="X", action="basal", reason="r")
    assert led.balance("source:rounding") + led.balance("sink:rounding") != 0
    led.close_tick(1, {"a": a.current_atp})


def test_reservoir_shortfall_is_explicit_inflow_and_death_recycles():
    led, accts = _world(1, 3.0)
    assert led.balance(RESERVOIR) == 0
    child = ATPAccount(4.0)
    led.attach("c", child, tick=1)
    assert led.balance("source:inflow") == -4
    led.detach("c", child, tick=1)
    assert led.balance(RESERVOIR) == 4
    led.close_tick(1, {"a0": 3.0})


def test_chain_tamper_detected_and_copy_pickle_safe():
    led, accts = _world(2, 1.0)
    accts["a0"].debit(0.25, tick=1, agent_id="a0", codon="B", action="basal", reason="r")
    led.close_tick(1, {k: a.current_atp for k, a in accts.items()})
    recs = [copy.deepcopy(r) for r in led.journal_records()]
    assert verify_ledger_chain(recs) == led.head
    recs[1]["args"]["postings"][0]["amount"] = "1/8"
    with pytest.raises(ATPConservationError):
        verify_ledger_chain(recs)
    clone = copy.deepcopy((led, accts))
    clone[1]["a0"].debit(0.25, tick=2, agent_id="a0", codon="B", action="basal", reason="r")
    clone[0].close_tick(2, {k: a.current_atp for k, a in clone[1].items()})
    led.close_tick(2, {k: a.current_atp for k, a in accts.items()})  # original untouched
    pickle.loads(pickle.dumps((led, accts)))


def test_observer_does_not_change_account_digest():
    plain, hooked = ATPAccount(5.0), ATPAccount(5.0)
    WorldATPLedger().attach("x", hooked, tick=0)
    for acct in (plain, hooked):
        acct.debit(1.25, tick=1, agent_id="x", codon="B", action="basal", reason="r")
        acct.credit(0.5, tick=1, agent_id="x", codon="F", action="forage", reason="r")
    assert plain.ledger_digest() == hooked.ledger_digest()
    assert plain.to_dict() == hooked.to_dict() and plain == hooked
