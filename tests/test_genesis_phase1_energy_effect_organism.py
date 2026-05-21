from __future__ import annotations

from codontrace.actions import ActionContext, ActionResult, EnergyEffect, default_action_registry
from codontrace.codon import Codon
from codontrace.genesis import GenesisOrganism, Ribosome
from codontrace.trace import Trace
from codontrace.world import World2D


def _organism_for_custom_action(handler, *, atp: float = 1.0, cost: float = 0.0) -> GenesisOrganism:
    table = Ribosome.genesis_v0().codon_table.replace(Codon("000", "CUSTOM_ENERGY", cost))
    organism = GenesisOrganism.from_bits(
        "org", "000", initial_runtime_atp=atp, ribosome=Ribosome(table)
    )
    organism.action_registry = default_action_registry().extend("CUSTOM_ENERGY", handler)
    return organism


def test_energy_effect_credit_updates_genesis_runtime_atp_and_trace() -> None:
    def handler(ctx: ActionContext) -> ActionResult:
        return ActionResult.executed(
            reason="charged",
            position_after=ctx.position,
            energy=EnergyEffect(credit=0.5, reason="custom_credit"),
        )

    organism = _organism_for_custom_action(handler)
    event = organism.step(World2D(2, 2), Trace())

    assert organism.atp_state.runtime_available == 1.5
    assert event.ledger_entry_ids == (0,)
    assert event.world_delta["energy_effect_applied"] is True
    assert event.world_delta["energy_effect_credit"] == 0.5


def test_energy_effect_extra_debit_updates_genesis_runtime_atp_and_trace() -> None:
    def handler(ctx: ActionContext) -> ActionResult:
        return ActionResult.executed(
            reason="spent",
            position_after=ctx.position,
            energy=EnergyEffect(debit_extra=0.25, reason="custom_debit"),
        )

    organism = _organism_for_custom_action(handler)
    event = organism.step(World2D(2, 2), Trace())

    assert organism.atp_state.runtime_available == 0.75
    assert event.ledger_entry_ids == (0,)
    assert event.world_delta["energy_effect_debit_extra"] == 0.25
    assert event.world_delta["energy_effect_blocked"] is False


def test_energy_effect_extra_debit_blocks_when_runtime_atp_is_insufficient() -> None:
    def handler(ctx: ActionContext) -> ActionResult:
        return ActionResult.executed(
            reason="overspent",
            position_after=ctx.position,
            energy=EnergyEffect(debit_extra=2.0, reason="custom_debit"),
        )

    organism = _organism_for_custom_action(handler, atp=1.0)
    event = organism.step(World2D(2, 2), Trace())

    assert event.status == "blocked"
    assert event.reason == "insufficient_runtime_atp_for_energy_effect"
    assert event.world_delta["energy_effect_blocked"] is True
    assert organism.atp_state.runtime_available == 1.0
