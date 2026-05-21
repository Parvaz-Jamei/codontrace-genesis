from __future__ import annotations

from codontrace import (
    ATPAccount,
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


def test_custom_string_action_is_supported() -> None:
    codon = Codon("001", "REST", 0.0, "Recover ATP.")
    assert codon.action_name == "REST"


def test_codon_table_replace_does_not_mutate_original() -> None:
    base = CodonTable.default_minimal()
    custom = base.replace(Codon("001", "REST", 0.0))
    assert base.decode("001").action_name == "SENSE_RESOURCE"
    assert custom.decode("001").action_name == "REST"


def test_zero_cost_custom_handler_executes_without_attempt_cost_ledger_entry() -> None:
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
    event = agent.step(world, trace)
    assert event.action == "REST"
    assert event.reason == "rested"
    assert event.world_delta["rest"] is True
    assert event.ledger_entry_id is None
    assert event.ledger_entry_ids == ()
    assert agent.atp_account.ledger == ()


def test_unsupported_action_is_blocked_not_crash() -> None:
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
    event = agent.step(world, trace)
    assert event.status == "blocked"
    assert event.reason == "unsupported_action"
    assert event.action == "REST"


def test_custom_handler_registered_by_custom_action_name() -> None:
    table = CodonTable.default_minimal().replace(Codon("001", "REST", 0.0))
    registry = default_action_registry().extend("REST", rest_handler)
    agent = WhiteBoxAgent(
        id="a1",
        genome=SemanticGenome.from_codons(["001"]),
        codon_table=table,
        atp_account=ATPAccount(5.0),
        position=(1, 1),
        action_registry=registry,
    )
    trace = Trace()
    event = agent.step(World2D(3, 3), trace)
    assert event.action == "REST"
    assert event.reason == "rested"
