from __future__ import annotations

from codontrace import (
    ATPAccount,
    CausalReplay,
    Codon,
    CodonTable,
    SemanticGenome,
    Trace,
    WhiteBoxAgent,
    World2D,
)


def run_one(codon: str, world: World2D, position: tuple[int, int], atp: float = 5.0) -> Trace:
    agent = WhiteBoxAgent(
        id="a",
        genome=SemanticGenome.from_codons([codon]),
        codon_table=CodonTable.default_minimal(),
        atp_account=ATPAccount(atp),
        position=position,
    )
    trace = Trace()
    agent.step(world, trace)
    return trace


def test_explanation_reports_low_atp_counterfactual_for_movement() -> None:
    world = World2D.from_ascii("""
...
.A.
...
""")
    snapshot = world.clone()
    trace = run_one("101", world, (1, 1))
    explanation = CausalReplay.explain_last_action(trace, snapshot)
    assert explanation.perturbation_results
    assert any(
        result.name == "low_atp" and result.reason == "insufficient_atp"
        for result in explanation.perturbation_results
    )
    assert "insufficient_atp" in explanation.summary or any(
        "insufficient_atp" in item for item in explanation.counterfactuals
    )


def test_explanation_reports_inserted_wall_counterfactual_for_movement() -> None:
    world = World2D.from_ascii("""
...
.A.
...
""")
    snapshot = world.clone()
    trace = run_one("101", world, (1, 1))
    explanation = CausalReplay.explain_last_action(trace, snapshot)
    assert any(
        result.name == "wall_inserted" and result.reason == "wall_blocked"
        for result in explanation.perturbation_results
    )
    assert "wall_blocked" in explanation.summary or any(
        "wall_blocked" in item for item in explanation.counterfactuals
    )


def test_explanation_reports_resource_removed_counterfactual_for_collect() -> None:
    world = World2D.from_ascii("""
...
.A.
...
""")
    world.place_resource((1, 1), amount=2.0)
    snapshot = world.clone()
    trace = run_one("111", world, (1, 1))
    explanation = CausalReplay.explain_last_action(trace, snapshot)
    assert any(
        result.name == "resource_removed" and result.reason == "no_resource"
        for result in explanation.perturbation_results
    )
    assert "no_resource" in explanation.summary or any(
        "no_resource" in item for item in explanation.counterfactuals
    )


def test_explanation_uses_custom_codon_table_cost() -> None:
    base = CodonTable.default_minimal().actions()
    table = CodonTable(
        [
            Codon(
                codon.bits,
                codon.action,
                3.5 if codon.bits == "101" else codon.cost,
                codon.description,
            )
            for codon in base
        ]
    )
    world = World2D.from_ascii("""
...
.A.
...
""")
    snapshot = world.clone()
    agent = WhiteBoxAgent(
        id="custom",
        genome=SemanticGenome.from_codons(["101"]),
        codon_table=table,
        atp_account=ATPAccount(5.0),
        position=(1, 1),
    )
    trace = Trace()
    agent.step(world, trace)
    explanation = CausalReplay.explain_last_action(trace, snapshot, codon_table=table)
    assert "action cost was 3.5" in explanation.summary
