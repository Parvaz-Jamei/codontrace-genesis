from __future__ import annotations

from codontrace import ATPAccount, CodonTable, SemanticGenome, Trace, WhiteBoxAgent, World2D


def test_agent_executes_action_and_creates_trace_with_ledger_ref() -> None:
    world = World2D.from_ascii("""
...
.A.
...
""")
    agent = WhiteBoxAgent(
        id="a",
        genome=SemanticGenome.from_codons(["101"]),
        codon_table=CodonTable.default_minimal(),
        atp_account=ATPAccount(2.0),
        position=(1, 1),
    )
    trace = Trace()
    event = agent.step(world, trace)
    assert event.status == "executed"
    assert event.reason == "moved"
    assert event.position_after == (2, 1)
    assert event.ledger_entry_id == 0
    assert len(agent.atp_account.ledger) == 1


def test_agent_blocked_action_does_not_mutate_atp() -> None:
    world = World2D.from_ascii("""
...
.A.
...
""")
    agent = WhiteBoxAgent(
        id="a",
        genome=SemanticGenome.from_codons(["101"]),
        codon_table=CodonTable.default_minimal(),
        atp_account=ATPAccount(0.2),
        position=(1, 1),
    )
    trace = Trace()
    event = agent.step(world, trace)
    assert event.status == "blocked"
    assert event.reason == "insufficient_atp"
    assert event.ledger_entry_id is None
    assert agent.atp_account.current_atp == 0.2
    assert agent.atp_account.ledger == ()


def test_wall_blocked_movement_still_records_attempt_cost_policy_a() -> None:
    world = World2D.from_ascii("""
...
.A#
...
""")
    agent = WhiteBoxAgent(
        id="a",
        genome=SemanticGenome.from_codons(["101"]),
        codon_table=CodonTable.default_minimal(),
        atp_account=ATPAccount(2.0),
        position=(1, 1),
    )
    trace = Trace()
    event = agent.step(world, trace)
    assert event.status == "blocked"
    assert event.reason == "wall_blocked"
    assert event.ledger_entry_id == 0
    assert agent.atp_account.current_atp == 1.0
    assert len(event.ledger_entry_ids) == 1
