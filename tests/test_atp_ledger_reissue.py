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
    mirrors = led.reissue_accounts(new, tick=1, reason="host_hold")
    led.close_tick(1, mirrors)
    assert led.balance("sink:host_hold") == 4 + 2.5  # old h and dropped g
    assert led.balance("source:host_hold") == -(7 + 1)  # new h and new n
    assert led.agent_balance("h") == 5 and led.agent_balance("n") == 0.75

