from __future__ import annotations

from codontrace import (
    ATPAccount,
    CausalReplay,
    CodonTable,
    SemanticGenome,
    Trace,
    WhiteBoxAgent,
    World2D,
)


def test_explanation_contains_core_facts_and_perturbations() -> None:
    world = World2D.from_ascii("""
...
.A.
...
""")
    snapshot = world.clone()
    agent = WhiteBoxAgent(
        id="a",
        genome=SemanticGenome.from_codons(["101"]),
        codon_table=CodonTable.default_minimal(),
        atp_account=ATPAccount(5.0),
        position=(1, 1),
    )
    trace = Trace()
    agent.step(world, trace)
    explanation = CausalReplay.explain_last_action(trace, snapshot)
    assert "codon 101" in explanation.summary
    assert "MOVE_EAST" in explanation.summary
    assert "ATP" in explanation.summary
    assert "Counterfactual" not in explanation.summary
    assert explanation.perturbation_results
    assert any(result.name == "low_atp" for result in explanation.perturbation_results)


def test_explanation_reports_action_cost_resource_credit_and_net_atp() -> None:
    world = World2D.from_ascii("""
...
.A.
...
""")
    world.place_resource((1, 1), amount=2.0)
    snapshot = world.clone()
    agent = WhiteBoxAgent(
        id="a",
        genome=SemanticGenome.from_codons(["111"]),
        codon_table=CodonTable.default_minimal(),
        atp_account=ATPAccount(5.0),
        position=(1, 1),
    )
    trace = Trace()
    agent.step(world, trace)
    explanation = CausalReplay.explain_last_action(trace, snapshot)
    assert "action cost" in explanation.summary
    assert "resource credit" in explanation.summary
    assert "net ATP" in explanation.summary
    assert "ledger entry ids" in explanation.summary


def test_explanation_uses_custom_codon_table_cost() -> None:
    from codontrace import Action, Codon

    custom_table = CodonTable((Codon("101", Action.MOVE_EAST, 2.5, "custom east"),))
    world = World2D.from_ascii("""
...
.A.
...
""")
    snapshot = world.clone()
    agent = WhiteBoxAgent(
        id="a",
        genome=SemanticGenome.from_codons(["101"]),
        codon_table=custom_table,
        atp_account=ATPAccount(5.0),
        position=(1, 1),
    )
    trace = Trace()
    agent.step(world, trace)
    explanation = CausalReplay.explain_last_action(trace, snapshot, codon_table=custom_table)
    assert "action cost was 2.5" in explanation.summary
