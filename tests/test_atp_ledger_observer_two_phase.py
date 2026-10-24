"""F3/F4: an observer that posts and then raises leaves no postings."""

from __future__ import annotations

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from codontrace.atp_ledger import WorldATPLedger
from codontrace.energy import ATPAccount


class Boom(RuntimeError):
    pass


def _wrap(acct: ATPAccount) -> None:
    inner = acct._observer

    def wrapper(entry):  # posts through the real hook, then fails
        inner(entry)
        raise Boom

    acct._observer = wrapper


def _setup() -> tuple[WorldATPLedger, ATPAccount]:
    led = WorldATPLedger("w")
    led.fund_reservoir(50.0, tick=0)
    acct = ATPAccount(5.0)
    led.attach("a", acct, tick=0)
    return led, acct


@pytest.mark.parametrize("credit", [True, False])
def test_post_then_raise_outside_scope_leaves_no_postings(credit: bool) -> None:
    led, acct = _setup()
    before = (led.state_digest(), acct.current_atp, acct.entry_count())
    _wrap(acct)
    op = acct.credit if credit else acct.debit
    with pytest.raises(Boom):
        op(1.25, tick=1, agent_id="a", codon="F", action="forage", reason="r")
    assert (led.state_digest(), acct.current_atp, acct.entry_count()) == before
    led.check({"a": acct.current_atp})
    led.close_tick(1, {"a": acct.current_atp})


def test_post_then_raise_swallowed_inside_scope_leaves_no_postings() -> None:
    led, acct = _setup()
    before = led.state_digest()
    _wrap(acct)
    with led.transfer_scope("t", tick=1):
        with pytest.raises(Boom):
            acct.debit(1.0, tick=1, agent_id="a", codon="B", action="basal", reason="r")
    assert led.state_digest() == before and acct.current_atp == 5.0


@settings(max_examples=40, deadline=None)
@given(st.lists(st.tuples(st.booleans(), st.floats(0.0, 3.0), st.booleans()), min_size=1, max_size=20))
def test_conservation_under_failing_observers(ops) -> None:
    led, acct = _setup()
    real = acct._observer
    for tick, (gain, amt, fail) in enumerate(ops, start=1):
        if fail:
            _wrap(acct)
        try:
            if gain:
                acct.credit(amt, tick=tick, agent_id="a", codon="F", action="forage", reason="r")
            elif acct.can_pay(amt):
                acct.debit(amt, tick=tick, agent_id="a", codon="B", action="basal", reason="r")
        except Boom:
            pass
        acct._observer = real
        led.close_tick(tick, {"a": acct.current_atp})
