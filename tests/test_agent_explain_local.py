from __future__ import annotations

import pytest

from codontrace import (
    ATPAccount,
    CodonTable,
    ReplayError,
    SemanticGenome,
    Trace,
    WhiteBoxAgent,
    World2D,
)


def test_explain_last_action_is_agent_local_with_shared_trace() -> None:
    world = World2D(5, 5)
    trace = Trace()
    table = CodonTable.default_minimal()

    waiter = WhiteBoxAgent(
        id="waiter",
        genome=SemanticGenome.from_codons(["000", "000", "000"]),
        codon_table=table,
        atp_account=ATPAccount(5.0),
        position=(1, 1),
    )
    scanner = WhiteBoxAgent(
        id="scanner",
        genome=SemanticGenome.from_codons(["001", "001", "001"]),
        codon_table=table,
        atp_account=ATPAccount(5.0),
        position=(3, 3),
    )

    waiter.step(world, trace)
    scanner.step(world, trace)

    waiter_explanation = waiter.explain_last_action()
    scanner_explanation = scanner.explain_last_action()

    assert "Action WAIT" in waiter_explanation.summary
    assert "codon 000" in waiter_explanation.summary
    assert "Action SENSE_RESOURCE" in scanner_explanation.summary
    assert "codon 001" in scanner_explanation.summary


def test_explain_last_action_uses_selected_agent_event_even_when_action_matches_global_last() -> (
    None
):
    world = World2D(8, 8)
    trace = Trace()
    table = CodonTable.default_minimal()

    first = WhiteBoxAgent(
        id="first",
        genome=SemanticGenome.from_codons(["111"]),
        codon_table=table,
        atp_account=ATPAccount(0.1),
        position=(2, 2),
    )
    second = WhiteBoxAgent(
        id="second",
        genome=SemanticGenome.from_codons(["111"]),
        codon_table=table,
        atp_account=ATPAccount(0.1),
        position=(6, 6),
    )

    first.step(world, trace)
    second.step(world, trace)

    first_explanation = first.explain_last_action()

    assert "Action COLLECT_RESOURCE" in first_explanation.summary
    assert "codon 111" in first_explanation.summary
    assert "movement (2, 2)->(2, 2)" in first_explanation.summary
    assert "movement (6, 6)->(6, 6)" not in first_explanation.summary


def test_explain_last_action_raises_when_agent_has_no_event_in_shared_trace() -> None:
    world = World2D(5, 5)
    trace = Trace()
    table = CodonTable.default_minimal()

    active = WhiteBoxAgent(
        id="active",
        genome=SemanticGenome.from_codons(["000"]),
        codon_table=table,
        atp_account=ATPAccount(5.0),
        position=(1, 1),
    )
    inactive = WhiteBoxAgent(
        id="inactive",
        genome=SemanticGenome.from_codons(["001"]),
        codon_table=table,
        atp_account=ATPAccount(5.0),
        position=(3, 3),
    )

    active.step(world, trace)
    inactive._trace = trace

    with pytest.raises(ReplayError, match="No traced action is available"):
        inactive.explain_last_action()
