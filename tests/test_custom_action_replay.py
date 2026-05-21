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
    default_action_registry,
)
from codontrace.actions import ActionContext, ActionResult


def rest_handler(ctx: ActionContext) -> ActionResult:
    return ActionResult(
        status="executed",
        reason="rested",
        position_after=ctx.position,
        world_delta={"rest": True},
    )


def test_explanation_for_custom_action_uses_registry() -> None:
    table = CodonTable.default_minimal().replace(Codon("001", "REST", 0.0))
    registry = default_action_registry().extend("REST", rest_handler)
    world = World2D.from_ascii("""
...
.A.
...
""")
    agent = WhiteBoxAgent(
        id="a1",
        genome=SemanticGenome.from_codons(["001"]),
        codon_table=table,
        atp_account=ATPAccount(5.0),
        position=(1, 1),
        action_registry=registry,
    )
    trace = Trace()
    agent.step(world, trace)
    explanation = CausalReplay.explain_last_action(
        trace,
        world_before_or_snapshot=world.clone(),
        codon_table=table,
        action_registry=registry,
    )
    assert "REST" in explanation.summary
    assert any(result.reason == "rested" for result in explanation.perturbation_results)


def test_explanation_for_custom_action_without_registry_does_not_crash() -> None:
    table = CodonTable.default_minimal().replace(Codon("001", "REST", 0.0))
    world = World2D(3, 3)
    agent = WhiteBoxAgent(
        id="a1",
        genome=SemanticGenome.from_codons(["001"]),
        codon_table=table,
        atp_account=ATPAccount(5.0),
        position=(1, 1),
    )
    trace = Trace()
    agent.step(world, trace)
    explanation = CausalReplay.explain_last_action(
        trace,
        world_before_or_snapshot=world.clone(),
        codon_table=table,
    )
    assert "REST" in explanation.summary
    assert "registry_missing" in explanation.summary or "unsupported_action" in explanation.summary
