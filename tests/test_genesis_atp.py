from __future__ import annotations

from codontrace.genesis import GenesisATPState


def test_runtime_atp_never_goes_below_zero() -> None:
    state = GenesisATPState.from_runtime(1.0)
    assert (
        state.debit_runtime(2.0, tick=0, organism_id="g", codon="111", action="COPY_SELF") is None
    )
    assert state.runtime_available == 1.0


def test_zero_cost_debit_remains_noop() -> None:
    state = GenesisATPState.from_runtime(1.0)
    assert state.debit_runtime(0.0, tick=0, organism_id="g", codon="000", action="WAIT") is None
    assert len(state.runtime.ledger) == 0


def test_learning_budget_exists_but_is_not_consumed() -> None:
    state = GenesisATPState.from_runtime(2.0, learning_enabled=True, learning_atp=5.0)
    before = state.learning_available
    assert state.debit_runtime(1.0, tick=0, organism_id="g", codon="000", action="WAIT") == 0
    assert state.learning_available == before


def test_ledger_digest_is_deterministic() -> None:
    left = GenesisATPState.from_runtime(2.0, learning_enabled=True, learning_atp=1.0)
    right = GenesisATPState.from_runtime(2.0, learning_enabled=True, learning_atp=1.0)
    left.debit_runtime(0.5, tick=0, organism_id="g", codon="000", action="WAIT")
    right.debit_runtime(0.5, tick=0, organism_id="g", codon="000", action="WAIT")
    assert left.ledger_digest() == right.ledger_digest()
