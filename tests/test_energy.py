from __future__ import annotations

from codontrace import ATPAccount


def test_atp_account_records_immutable_ledger_entries() -> None:
    account = ATPAccount(initial_atp=3.0)
    debit_id = account.debit(
        1.0,
        tick=1,
        agent_id="a",
        codon="101",
        action="MOVE_EAST",
        reason="action_cost",
    )
    credit_id = account.credit(
        2.0,
        tick=1,
        agent_id="a",
        codon="111",
        action="COLLECT_RESOURCE",
        reason="resource_collected",
    )
    assert debit_id == 0
    assert credit_id == 1
    assert account.current_atp == 4.0
    assert len(account.ledger) == 2
    assert account.ledger[0].balance_before == 3.0
    assert account.ledger[0].balance_after == 2.0


def test_atp_account_never_goes_negative_and_blocked_has_no_entry() -> None:
    account = ATPAccount(initial_atp=0.5)
    assert (
        account.debit(
            1.0,
            tick=0,
            agent_id="a",
            codon="101",
            action="MOVE_EAST",
            reason="action_cost",
        )
        is None
    )
    assert account.current_atp == 0.5
    assert account.ledger == ()


def test_ledger_digest_changes_with_ledger_content() -> None:
    a = ATPAccount(5.0)
    b = ATPAccount(5.0)
    a.debit(1.0, tick=0, agent_id="a", codon="101", action="MOVE_EAST", reason="action_cost")
    b.debit(0.1, tick=0, agent_id="a", codon="000", action="WAIT", reason="action_cost")
    assert a.snapshot()["ledger_digest"] != b.snapshot()["ledger_digest"]
