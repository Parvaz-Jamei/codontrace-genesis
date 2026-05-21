from __future__ import annotations

from codontrace import ATPAccount, Codon, CodonTable, SemanticGenome, Trace, WhiteBoxAgent, World2D
from codontrace.actions import ActionContext, ActionResult, EnergyEffect, default_action_registry


def test_custom_action_can_credit_atp_safely() -> None:
    def rest(ctx: ActionContext) -> ActionResult:
        return ActionResult(
            status="executed",
            reason="rested",
            position_after=ctx.position,
            world_delta={"rest": True},
            energy=EnergyEffect(credit=0.5, reason="rest_recovery"),
        )

    table = CodonTable.default_minimal().replace(Codon("001", "REST", 0.0))
    registry = default_action_registry().extend("REST", rest)
    agent = WhiteBoxAgent(
        id="a1",
        genome=SemanticGenome.from_codons(["001"]),
        codon_table=table,
        atp_account=ATPAccount(1.0),
        position=(0, 0),
        action_registry=registry,
    )

    event = agent.step(World2D(2, 2), Trace())

    assert agent.atp_account.current_atp == 1.5
    assert event.world_delta["atp_credit"] == 0.5
    assert event.ledger_entry_ids == (0,)


def test_custom_action_can_extra_debit_atp_safely() -> None:
    def sprint(ctx: ActionContext) -> ActionResult:
        return ActionResult(
            status="executed",
            reason="sprinted",
            position_after=ctx.position,
            energy=EnergyEffect(debit_extra=0.25, reason="sprint_extra"),
        )

    table = CodonTable.default_minimal().replace(Codon("001", "SPRINT", 0.0))
    registry = default_action_registry().extend("SPRINT", sprint)
    agent = WhiteBoxAgent(
        id="a1",
        genome=SemanticGenome.from_codons(["001"]),
        codon_table=table,
        atp_account=ATPAccount(1.0),
        position=(0, 0),
        action_registry=registry,
    )

    event = agent.step(World2D(2, 2), Trace())

    assert agent.atp_account.current_atp == 0.75
    assert event.world_delta["atp_debit_extra"] == 0.25
    assert event.ledger_entry_ids == (0,)


def test_custom_action_energy_effect_ledger_is_complete_and_balanced() -> None:
    def charge_then_spend(ctx: ActionContext) -> ActionResult:
        assert not hasattr(ctx, "atp_account")
        return ActionResult(
            status="executed",
            reason="charged_then_spent",
            position_after=ctx.position,
            world_delta={"composite_effect": True},
            energy=EnergyEffect(credit=0.6, debit_extra=0.3, reason="composite_energy"),
        )

    table = CodonTable.default_minimal().replace(Codon("001", "CHARGE_SPEND", 0.2))
    registry = default_action_registry().extend("CHARGE_SPEND", charge_then_spend)
    agent = WhiteBoxAgent(
        id="a1",
        genome=SemanticGenome.from_codons(["001"]),
        codon_table=table,
        atp_account=ATPAccount(2.0),
        position=(0, 0),
        action_registry=registry,
    )

    event = agent.step(World2D(2, 2), Trace())
    ledger = tuple(agent.atp_account.ledger)

    assert agent.atp_account.current_atp == 2.1
    assert event.atp_after == ledger[-1].balance_after == agent.atp_account.current_atp
    assert event.ledger_entry_ids == tuple(entry.entry_id for entry in ledger)
    assert [(entry.kind, entry.amount, entry.reason) for entry in ledger] == [
        ("debit", 0.2, "action_cost"),
        ("credit", 0.6, "composite_energy"),
        ("debit", 0.3, "composite_energy"),
    ]
    assert event.world_delta["atp_credit"] == 0.6
    assert event.world_delta["atp_debit_extra"] == 0.3
    assert event.world_delta["net_atp_delta"] == 0.1
