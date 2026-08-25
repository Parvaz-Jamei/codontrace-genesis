"""Scientific evidence tests for memory delayed-reward classification."""

from __future__ import annotations

from codontrace.genesis.memory_evidence import classify_memory_delayed_evidence
from codontrace.genesis.memory import MemoryUseEvidence


def test_write_then_reward_is_temporal_correlation_not_causal() -> None:
    result = classify_memory_delayed_evidence(
        memory_written=True,
        memory_read=False,
        reward_observed=True,
        runtime_correct_flag=False,
    )
    assert result.evidence_status == "temporal_correlation"
    assert result.causal_status == "correlational_only"
    assert result.correct_delayed_action is False
    assert result.claim_eligible is False


def test_read_linked_reward_is_mechanism_candidate_not_claim() -> None:
    result = classify_memory_delayed_evidence(
        memory_written=True,
        memory_read=True,
        reward_observed=True,
        runtime_correct_flag=False,
    )
    assert result.evidence_status == "read_linked"
    assert result.correct_delayed_action is True
    assert result.causal_status == "mechanism_candidate"
    assert result.claim_eligible is False


def test_ablation_control_enables_claim_eligible_causal_support() -> None:
    result = classify_memory_delayed_evidence(
        memory_written=True,
        memory_read=True,
        reward_observed=True,
        runtime_correct_flag=True,
        control_digest="ablation:no_memory:seed1",
    )
    assert result.causal_status == "causal_support"
    assert result.claim_eligible is True


def test_memory_use_evidence_record_carries_evidence_ladder() -> None:
    record = MemoryUseEvidence(
        signal_seen_tick=0,
        memory_written_tick=0,
        memory_read_tick=None,
        decision_tick=3,
        reward_tick=3,
        correct_delayed_action=False,
        evidence_status="temporal_correlation",
        causal_status="correlational_only",
        claim_eligible=False,
        reward_after_action=1.0,
    )
    payload = record.to_dict()
    assert payload["evidence_status"] == "temporal_correlation"
    assert payload["causal_status"] == "correlational_only"
    assert payload["claim_eligible"] is False
    assert payload["correct_delayed_action"] is False
    assert record.digest() == MemoryUseEvidence(
        signal_seen_tick=0,
        memory_written_tick=0,
        memory_read_tick=None,
        decision_tick=3,
        reward_tick=3,
        correct_delayed_action=False,
        evidence_status="temporal_correlation",
        causal_status="correlational_only",
        claim_eligible=False,
        reward_after_action=1.0,
    ).digest()
