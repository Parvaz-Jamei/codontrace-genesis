from __future__ import annotations

from codontrace.genesis import (
    EpisodicMemory,
    EpisodicMemoryConfig,
    GenesisATPState,
    LearningATPConfig,
    MemoryConsolidationResult,
    consolidate_memory,
    decide_learning_update,
)


def test_learning_decision_blocks_below_threshold() -> None:
    memory = EpisodicMemory(EpisodicMemoryConfig(prediction_error_threshold=0.5))
    state = GenesisATPState.from_runtime(1.0, learning_atp=5.0, learning_enabled=True)
    decision = decide_learning_update(memory, 0.2, LearningATPConfig(), state)
    assert not decision.should_update
    assert "prediction_error_below_threshold" in decision.reasons


def test_learning_decision_blocks_insufficient_learning_atp() -> None:
    memory = EpisodicMemory(EpisodicMemoryConfig(prediction_error_threshold=0.1))
    state = GenesisATPState.from_runtime(1.0, learning_atp=0.0, learning_enabled=True)
    decision = decide_learning_update(
        memory, 0.5, LearningATPConfig(prediction_update_cost=1.0), state
    )
    assert not decision.should_update
    assert "insufficient_learning_atp" in decision.reasons


def test_learning_decision_allows_with_error_and_atp() -> None:
    memory = EpisodicMemory(EpisodicMemoryConfig(prediction_error_threshold=0.1))
    state = GenesisATPState.from_runtime(1.0, learning_atp=2.0, learning_enabled=True)
    decision = decide_learning_update(
        memory, 0.5, LearningATPConfig(prediction_update_cost=1.0), state
    )
    assert decision.should_update


def test_memory_consolidation_audit_only_does_not_debit_without_state_change() -> None:
    memory = EpisodicMemory(EpisodicMemoryConfig(prediction_error_threshold=0.1))
    state = GenesisATPState.from_runtime(1.0, learning_atp=2.0, learning_enabled=True)
    result = consolidate_memory(
        memory,
        0.5,
        LearningATPConfig(memory_consolidation_cost=0.5),
        state,
        tick=0,
        organism_id="o",
    )
    assert not result.succeeded
    assert result.mode == "audit_summary_only"
    assert not result.state_changed
    assert result.ledger_entry_id is None
    assert state.learning_available == 2.0
    assert not result.claim_allowed_for_learning_compression
    assert MemoryConsolidationResult.from_dict(result.to_dict()).to_dict() == result.to_dict()
