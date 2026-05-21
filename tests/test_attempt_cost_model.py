from __future__ import annotations

from codontrace import ATPAccount, CodonTable, SemanticGenome, Trace, WhiteBoxAgent, World2D


def _agent(codon: str, *, atp: float, position: tuple[int, int]) -> WhiteBoxAgent:
    return WhiteBoxAgent(
        id="agent-1",
        genome=SemanticGenome.from_codons([codon]),
        codon_table=CodonTable.default_minimal(),
        atp_account=ATPAccount(atp),
        position=position,
    )


def test_collect_without_resource_still_debits_attempt_cost() -> None:
    world = World2D(3, 3)
    agent = _agent("111", atp=5.0, position=(1, 1))
    event = agent.step(world, Trace())

    assert event.status == "blocked"
    assert event.reason == "no_resource"
    assert agent.atp_account.current_atp == 4.2
    assert len(agent.atp_account.ledger) == 1


def test_move_into_wall_still_debits_attempt_cost() -> None:
    world = World2D.from_ascii(".A#")
    agent = _agent("101", atp=5.0, position=(1, 0))
    event = agent.step(world, Trace())

    assert event.status == "blocked"
    assert event.reason == "wall_blocked"
    assert agent.atp_account.current_atp == 4.0
    assert len(agent.atp_account.ledger) == 1


def test_insufficient_atp_costs_nothing_and_creates_no_ledger_entry() -> None:
    world = World2D(3, 3)
    agent = _agent("101", atp=0.5, position=(1, 1))
    event = agent.step(world, Trace())

    assert event.status == "blocked"
    assert event.reason == "insufficient_atp"
    assert agent.atp_account.current_atp == 0.5
    assert event.ledger_entry_ids == ()
    assert len(agent.atp_account.ledger) == 0
