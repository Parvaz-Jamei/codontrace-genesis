from __future__ import annotations

import pytest

from codontrace.errors import ConfigurationError
from codontrace.genesis.atp import GenesisATPState
from codontrace.genesis.learning import LearningATPConfig, consolidate_memory
from codontrace.genesis.memory import EpisodicEvent, EpisodicMemory, EpisodicMemoryConfig, MemoryWriteResult
from codontrace.genesis.selection import (
    AgeLayeredSelection,
    EvolutionSelectionResult,
    NoveltyWeightedSelection,
    QDParentFeedback,
    QDSelectionFeedback,
)


def _event(tick: int, action: str = "WAIT", organism_id: str = "org") -> EpisodicEvent:
    return EpisodicEvent(
        tick=tick,
        organism_id=organism_id,
        action=action,
        status="executed",
        position_before=(0, 0),
        position_after=(0, 0),
        atp_runtime_before=10.0,
        atp_runtime_after=10.0,
        atp_learning_before=10.0,
        atp_learning_after=10.0,
        world_digest_before="world",
        trace_event_digest=f"trace-{tick}-{action}",
        observation={},
        outcome={},
    )


class _Candidate:
    def __init__(self, organism_id: str) -> None:
        self.organism_id = organism_id


def _candidate(organism_id: str) -> _Candidate:
    return _Candidate(organism_id)


def _stable_candidate_id(candidate: object) -> str:
    return str(getattr(candidate, "organism_id"))


def test_qd_selection_feedback_to_dict_and_digest_do_not_crash() -> None:
    feedback = QDSelectionFeedback(
        generation=1,
        archive_digest_before="before",
        archive_digest_after="after",
        descriptor_digest="descriptor",
        fitness_scores_digest="fitness",
        novelty_scores_digest="novelty",
        selected_survivor_ids=("b",),
        selected_parent_ids=("b",),
        selection_changed_by_qd=True,
        fallback_reason=None,
        qd_fallback_reason="selection_applied",
        qd_mode="selection_pressure",
    )
    payload = feedback.to_dict()
    assert payload["selection_changed_by_qd"] is True
    assert payload["qd_changed_selection"] is True
    assert isinstance(feedback.digest(), str)
    assert len(feedback.digest()) == 64


def test_qd_parent_feedback_inherits_qd_changed_selection_alias() -> None:
    feedback = QDParentFeedback(
        generation=1,
        archive_digest_before="before",
        archive_digest_after="after",
        descriptor_digest="descriptor",
        fitness_scores_digest="fitness",
        novelty_scores_digest="novelty",
        selected_survivor_ids=("b",),
        selected_parent_ids=("b",),
        selection_changed_by_qd=True,
        qd_mode="selection_pressure",
    )
    assert feedback.qd_changed_selection is True
    assert feedback.to_dict()["qd_changed_selection"] is True


def test_memory_write_reports_ring_buffer_eviction() -> None:
    memory = EpisodicMemory(EpisodicMemoryConfig(capacity=2, max_events_per_tick=10))
    atp = GenesisATPState.from_runtime(10.0, learning_atp=10.0, learning_enabled=True)

    e1 = _event(1, "A1")
    e2 = _event(2, "A2")
    e3 = _event(3, "A3")

    memory.write_event(e1, atp, cost=0.1)
    memory.write_event(e2, atp, cost=0.1)
    result = memory.write_event(e3, atp, cost=0.1)

    assert result.written is True
    assert result.blocked_reason is None
    assert result.write_status == "written_with_eviction"
    assert result.evicted_count == 1
    assert result.evicted_event_digests == (e1.digest(),)
    assert [event.action for event in memory.events] == ["A2", "A3"]


def test_memory_write_no_eviction_reports_zero_evictions() -> None:
    memory = EpisodicMemory(EpisodicMemoryConfig(capacity=3, max_events_per_tick=10))
    atp = GenesisATPState.from_runtime(10.0, learning_atp=10.0, learning_enabled=True)
    result = memory.write_event(_event(1, "A1"), atp, cost=0.1)
    assert result.written is True
    assert result.write_status == "written"
    assert result.evicted_count == 0
    assert result.evicted_event_digests == ()


def test_memory_write_result_from_dict_is_backward_compatible() -> None:
    result = MemoryWriteResult.from_dict(
        {
            "written": True,
            "blocked_reason": None,
            "memory_size_before": 0,
            "memory_size_after": 1,
            "learning_ledger_entry_id": None,
            "memory_digest_before": "before",
            "memory_digest_after": "after",
        }
    )
    assert result.write_status == "written"
    assert result.evicted_count == 0
    assert result.evicted_event_digests == ()


def test_consolidate_memory_writes_state_changing_summary_event_and_debits_learning_atp() -> None:
    memory = EpisodicMemory(EpisodicMemoryConfig(capacity=8, max_events_per_tick=10))
    atp = GenesisATPState.from_runtime(10.0, learning_atp=10.0, learning_enabled=True)
    memory.write_event(_event(1, "SENSE_FOOD"), atp, cost=0.0)

    before_digest = memory.digest()
    before_learning = atp.learning_available
    config = LearningATPConfig(
        learning_enabled=True,
        prediction_update_cost=0.5,
        memory_consolidation_cost=0.5,
    )

    result = consolidate_memory(memory, 1.0, config, atp, tick=5, organism_id="org")

    assert result.attempted is True
    assert result.succeeded is True
    assert result.state_changed is True
    assert result.mode == "state_changing_consolidation"
    assert result.claim_allowed_for_learning_compression is True
    assert result.consumed_learning_atp == 0.5
    assert atp.learning_available == before_learning - 0.5
    assert result.memory_digest_before == before_digest
    assert result.memory_digest_after == memory.digest()
    assert result.memory_digest_after != before_digest
    assert result.consolidation_event_digest is not None
    assert any(event.action == "MEMORY_CONSOLIDATION" for event in memory.events)


def test_consolidate_memory_does_not_debit_when_consolidation_event_cannot_be_written() -> None:
    memory = EpisodicMemory(EpisodicMemoryConfig(capacity=8, max_events_per_tick=1))
    atp = GenesisATPState.from_runtime(10.0, learning_atp=10.0, learning_enabled=True)
    memory.write_event(_event(5, "SENSE_FOOD"), atp, cost=0.0)
    before_learning = atp.learning_available

    config = LearningATPConfig(
        learning_enabled=True,
        prediction_update_cost=0.5,
        memory_consolidation_cost=0.5,
    )
    result = consolidate_memory(memory, 1.0, config, atp, tick=5, organism_id="org")

    assert result.succeeded is False
    assert result.state_changed is False
    assert result.claim_allowed_for_learning_compression is False
    assert atp.learning_available == before_learning


def test_novelty_weighted_selection_rejects_zero_zero_weights() -> None:
    with pytest.raises(ConfigurationError):
        NoveltyWeightedSelection(fitness_weight=0.0, novelty_weight=0.0)


def test_novelty_weighted_selection_rejects_negative_weights() -> None:
    with pytest.raises(ConfigurationError):
        NoveltyWeightedSelection(fitness_weight=-1.0, novelty_weight=1.0)
    with pytest.raises(ConfigurationError):
        NoveltyWeightedSelection(fitness_weight=1.0, novelty_weight=-1.0)


def test_novelty_weighted_selection_allows_pure_fitness_or_pure_novelty() -> None:
    NoveltyWeightedSelection(fitness_weight=1.0, novelty_weight=0.0)
    NoveltyWeightedSelection(fitness_weight=0.0, novelty_weight=1.0)


def test_age_layered_selection_rejects_negative_age_weight() -> None:
    with pytest.raises(ConfigurationError):
        AgeLayeredSelection(age_weight=-0.1)


def test_age_layered_selection_prefers_younger_when_fitness_equal() -> None:
    old = _candidate("old")
    young = _candidate("young")
    selected = AgeLayeredSelection(age_weight=0.1).select(
        [old, young],
        fitness_scores={"old": 1.0, "young": 1.0},
        ages={"old": 10, "young": 1},
        max_population=1,
    )
    assert _stable_candidate_id(selected[0]) == "young"


def test_evolution_selection_result_preserves_explicit_empty_parent_ids() -> None:
    result = EvolutionSelectionResult(
        before_count=2,
        after_count=1,
        selected_ids=("survivor",),
        dropped_ids=("dropped",),
        policy_name="test",
        config_digest="digest",
        selected_parent_ids=(),
        selected_survivor_ids=("survivor",),
    )
    assert result.selected_parent_ids == ()
    assert result.to_dict()["selected_parent_ids"] == []


def test_evolution_selection_result_legacy_missing_parent_ids_falls_back_to_selected_ids() -> None:
    payload = {
        "before_count": 2,
        "after_count": 1,
        "selected_ids": ["survivor"],
        "dropped_ids": ["dropped"],
        "policy_name": "test",
        "config_digest": "digest",
    }
    result = EvolutionSelectionResult.from_dict(payload)
    assert result.selected_parent_ids == ("survivor",)
    assert result.selected_survivor_ids == ("survivor",)
