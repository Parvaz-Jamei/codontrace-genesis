from __future__ import annotations

from codontrace.genesis import DualATPBudget, GenesisATPState, LearningATPConfig


def test_runtime_and_learning_ledgers_are_separate() -> None:
    state = GenesisATPState.from_runtime(5.0, learning_atp=2.0, learning_enabled=True)
    runtime_before = state.runtime.ledger_digest()
    learning_before = state.learning.ledger_digest() if state.learning else ""

    state.debit_runtime(1.0, tick=0, organism_id="o", codon="000", action="WAIT")

    assert state.runtime_available == 4.0
    assert state.learning_available == 2.0
    assert state.runtime.ledger_digest() != runtime_before
    assert state.learning is not None
    assert state.learning.ledger_digest() == learning_before


def test_learning_debit_does_not_affect_runtime_and_cannot_go_negative() -> None:
    state = GenesisATPState.from_runtime(5.0, learning_atp=0.2, learning_enabled=True)
    blocked = state.debit_learning(0.5, tick=0, organism_id="o", reason="memory")
    assert blocked is None
    assert state.learning_available == 0.2
    assert state.runtime_available == 5.0

    entry = state.debit_learning(0.1, tick=1, organism_id="o", reason="memory")
    assert entry == 0
    assert state.learning_available == 0.1
    assert state.runtime_available == 5.0


def test_vitae_to_learning_transfer_records_learning_credit() -> None:
    state = GenesisATPState.from_runtime(1.0, learning_enabled=True)
    entry = state.transfer_vitae_to_learning(2.0, tick=2, organism_id="o", conversion_rate=0.5)
    assert entry == 0
    assert state.learning_available == 1.0


def test_dual_atp_budget_roundtrip() -> None:
    budget = DualATPBudget(runtime_available=3.0, learning_available=1.5, learning_enabled=True)
    assert DualATPBudget.from_dict(budget.to_dict()) == budget


def test_learning_atp_config_roundtrip() -> None:
    config = LearningATPConfig(memory_write_cost=0.2, prediction_update_cost=0.3)
    assert LearningATPConfig.from_dict(config.to_dict()) == config
