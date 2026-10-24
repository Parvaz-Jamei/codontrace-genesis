"""F15: an explicit hold that rebuilds accounts under the same id."""

from __future__ import annotations

import pytest

from codontrace.atp_ledger import ATPConservationError, WorldATPLedger
from codontrace.energy import ATPAccount


def _acct(start: float, debit: float) -> ATPAccount:
    a = ATPAccount(start)
    a.debit(debit, tick=1, agent_id="h", codon="B", action="basal", reason="r")
    return a


def test_silent_rewrite_still_raises() -> None:
    led = WorldATPLedger("w")
    led.close_tick(0, led.sync_accounts({"h": _acct(5.0, 1.0)}, tick=0))
    with pytest.raises(ATPConservationError, match="rewritten"):
        led.sync_accounts({"h": _acct(7.0, 2.0)}, tick=1)


def test_reissue_books_explicit_flows_and_conserves() -> None:
    led = WorldATPLedger("w")
    led.close_tick(0, led.sync_accounts({"h": _acct(5.0, 1.0), "g": _acct(3.0, 0.5)}, tick=0))
    new = {"h": _acct(7.0, 2.0), "n": _acct(1.0, 0.25)}  # h rebuilt, g dropped, n added
    mirrors = led.reissue_accounts(new, tick=1, reason="host_hold", declared={"h": 5.0, "n": 0.75})
    led.close_tick(1, mirrors)
    assert led.balance("sink:host_hold") == 4 + 2.5  # old h and dropped g
    assert led.balance("source:host_hold") == -(7 + 1)  # new h and new n
    assert led.agent_balance("h") == 5 and led.agent_balance("n") == 0.75



def _booked() -> WorldATPLedger:
    led = WorldATPLedger("w")
    led.close_tick(0, led.sync_accounts({"h": _acct(5.0, 1.0)}, tick=0))
    return led


def test_reissue_with_changed_balance_raises() -> None:
    led = _booked()
    before = led.state_digest()
    rebuilt = _acct(1e6, 1.0)  # declared snapshot says 9, account holds ~1e6
    with pytest.raises(ATPConservationError, match="declared"):
        led.reissue_accounts({"h": rebuilt}, tick=1, reason="host_hold", declared={"h": 8.0})
    assert led.state_digest() == before


def test_reissue_of_undeclared_id_or_reason_raises() -> None:
    led = _booked()
    with pytest.raises(ATPConservationError, match="not declared"):
        led.reissue_accounts({"h": _acct(7.0, 2.0)}, tick=1, reason="host_hold", declared={})
    with pytest.raises(ATPConservationError, match="undeclared reissue boundary"):
        led.reissue_accounts({"h": _acct(7.0, 2.0)}, tick=1, reason="anything", declared={"h": 5.0})


def test_phase3_hold_books_exactly_what_it_declares() -> None:
    from codontrace.genesis.rq_mechanism_v2_phase3 import (
        BRANCH_LOCKED,
        _parasite_founders,
        build_host_seats,
        build_phase3_arm,
    )

    seats = build_host_seats("000000", "111111", common="A")
    arm = build_phase3_arm(3, BRANCH_LOCKED, seats, _parasite_founders())
    arm.run_generations(2)  # honest hold: books cleanly
    led = arm.runner.atp_ledger
    assert led.balance("source:host_hold") < 0  # the declared refill inflow is visible

    hold = arm.host_composition_hold
    assert hold is not None

    def lying_hold(target):  # type: ignore[no-untyped-def]
        hold(target)
        key = sorted(target.host_hold_atp)[0]
        target.host_hold_atp = dict(target.host_hold_atp, **{key: target.host_hold_atp[key] + 1.0})

    arm.host_composition_hold = lying_hold
    with pytest.raises(ATPConservationError, match="declared"):
        arm.run_generations(1)
