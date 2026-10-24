"""F3/F4: atomic observer + rollback, and copy/pickle detachment."""

from __future__ import annotations

import copy
import pickle

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from codontrace.atp_ledger import CLEARING, ATPConservationError, WorldATPLedger
from codontrace.energy import ATPAccount

amounts = st.floats(min_value=0.0, max_value=50.0, allow_nan=False, allow_infinity=False)


def _world(n: int, start: float) -> tuple[WorldATPLedger, dict[str, ATPAccount]]:
    led = WorldATPLedger()
    led.fund_reservoir(1000.0, tick=0)
    accts = {f"a{i}": ATPAccount(start) for i in range(n)}
    for k, a in accts.items():
        led.attach(k, a, tick=0)
    return led, accts


def _mirrors(accts: dict[str, ATPAccount]) -> dict[str, float]:
    return {k: a.current_atp for k, a in accts.items()}


def test_observer_failure_leaves_account_untouched() -> None:
    led, accts = _world(1, 5.0)
    a = accts["a0"]

    def boom(_entry: object) -> None:
        raise RuntimeError("observer failed")

    a.set_observer(boom)
    with pytest.raises(RuntimeError):
        a.debit(1.0, tick=1, agent_id="a0", codon="B", action="basal", reason="r")
    assert a.current_atp == 5.0 and len(a.ledger) == 0
    a.verify_balance()


def test_unknown_agent_entry_rejected_without_mutation() -> None:
    led, accts = _world(1, 5.0)
    a = accts["a0"]
    led.close_agent("a0", tick=1)  # observer still bound: entry must be refused
    with pytest.raises(ATPConservationError):
        a.credit(1.0, tick=1, agent_id="a0", codon="F", action="forage", reason="r")
    assert a.current_atp == 5.0 and len(a.ledger) == 0
    led.check({})


@settings(max_examples=60, deadline=None)
@given(st.lists(st.tuples(st.integers(0, 2), st.booleans(), amounts), min_size=1, max_size=12),
       st.integers(0, 11))
def test_scope_exception_rolls_back_everything(ops, fail_at) -> None:
    led, accts = _world(3, 20.0)
    before = {k: (a.current_atp, a.ledger_digest()) for k, a in accts.items()}
    head_state = led.state_digest()
    with pytest.raises(RuntimeError), led.transfer_scope("t", tick=1, magnitude=100.0):
        for i, (who, gain, amt) in enumerate(ops):
            if i == fail_at:
                raise RuntimeError("abort")
            acct = accts[f"a{who}"]
            if gain:
                acct.credit(amt, tick=1, agent_id=f"a{who}", codon="X", action="x", reason="r")
            else:
                acct.debit(amt, tick=1, agent_id=f"a{who}", codon="X", action="x", reason="r")
        raise RuntimeError("abort")
    assert led.balance(CLEARING) == 0
    assert {k: (a.current_atp, a.ledger_digest()) for k, a in accts.items()} == before
    assert led.state_digest() == head_state
    led.close_tick(1, _mirrors(accts))
    for a in accts.values():
        a.verify_balance()


def test_copy_and_pickle_of_attached_account_detach() -> None:
    led, accts = _world(1, 5.0)
    a = accts["a0"]
    for clone in (copy.deepcopy(a), copy.copy(a), pickle.loads(pickle.dumps(a))):
        assert clone == a
        clone.debit(1.0, tick=1, agent_id="a0", codon="B", action="basal", reason="r")
        led.check(_mirrors(accts))  # original ledger never sees the clone
    assert len(pickle.dumps(a)) < 1000  # the ledger is not dragged along


@settings(max_examples=30, deadline=None)
@given(st.lists(st.tuples(st.booleans(), st.floats(0.0, 3.0)), max_size=8))
def test_whole_world_copy_stays_closed(ops) -> None:
    led, accts = _world(2, 5.0)
    for clone_led, clone_accts in (copy.deepcopy((led, accts)), pickle.loads(pickle.dumps((led, accts)))):
        for gain, amt in ops:
            acct = clone_accts["a1"]
            if gain:
                acct.credit(amt, tick=1, agent_id="a1", codon="F", action="forage", reason="r")
            else:
                acct.debit(amt, tick=1, agent_id="a1", codon="B", action="basal", reason="r")
        clone_led.close_tick(1, _mirrors(clone_accts))
    led.close_tick(1, _mirrors(accts))
