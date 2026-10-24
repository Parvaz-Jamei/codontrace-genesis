"""F6: bounded journal (rolling window + checkpoints + streaming sink)."""

from __future__ import annotations

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from codontrace.atp_ledger import ATPConservationError, WorldATPLedger, verify_ledger_chain
from codontrace.energy import ATPAccount


def _run(ops: list[tuple[int, bool, float]], every: int, sink: list | None = None) -> WorldATPLedger:
    led = WorldATPLedger("w", checkpoint_every=every, record_sink=None if sink is None else sink.append)
    led.fund_reservoir(100.0, tick=0)
    accts = {f"a{i}": ATPAccount(5.0) for i in range(3)}
    for k, a in accts.items():
        led.attach(k, a, tick=0)
    for tick, (who, gain, amt) in enumerate(ops, start=1):
        a = accts[f"a{who}"]
        if gain:
            a.credit(amt, tick=tick, agent_id=f"a{who}", codon="F", action="forage", reason="r")
        elif a.can_pay(amt):
            a.debit(amt, tick=tick, agent_id=f"a{who}", codon="B", action="basal", reason="r")
        led.close_tick(tick, {k: v.current_atp for k, v in accts.items()})
    return led


OPS = st.lists(st.tuples(st.integers(0, 2), st.booleans(), st.floats(0.0, 4.0)), min_size=1, max_size=40)


@settings(max_examples=40, deadline=None)
@given(OPS, st.integers(1, 9))
def test_window_is_bounded_and_head_independent_of_checkpointing(ops, every) -> None:
    full_sink: list = []
    ref = _run(ops, 10**9)
    led = _run(ops, every, full_sink)
    assert led.head == ref.head  # checkpointing never changes the replay digest
    # length: exactly the ticks since the last checkpoint, never more
    assert len(led.journal_records()) == len(ops) % every < every
    assert len(full_sink) == len(ops)  # every record streamed exactly once
    # behaviour: the bounded ledger is the same ledger as the unbounded one
    assert led.state_digest() == ref.state_digest()
    assert led.totals() == ref.totals()
    # the retained window verifies on its own from its checkpoint ...
    assert verify_ledger_chain(led.journal_records(), led.journal_base()) == led.head
    # ... and the streamed records verify the whole history from genesis
    assert verify_ledger_chain(full_sink) == led.head == verify_ledger_chain(ref.journal_records())


def test_tampered_checkpoint_rejected() -> None:
    led = _run([(0, True, 1.0)] * 5, 2)
    base = led.journal_base()
    assert base is not None
    base["balances"] = dict(base["balances"], **{"agent:a0": "1/1"})
    with pytest.raises(ATPConservationError):
        verify_ledger_chain(led.journal_records(), base)


def test_window_length_stays_bounded_over_a_long_run() -> None:
    led = _run([(i % 3, i % 2 == 0, 0.5) for i in range(1000)], 16)
    ref = _run([(i % 3, i % 2 == 0, 0.5) for i in range(1000)], 10**9)
    assert len(led.journal_records()) == 1000 % 16
    assert len(ref.journal_records()) == 1000
    assert led.head == ref.head and led.state_digest() == ref.state_digest()
