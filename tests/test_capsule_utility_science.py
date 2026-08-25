"""Scientific evidence tests for outcome-based capsule utility."""

from __future__ import annotations

from codontrace.genesis.capsule_utility import evaluate_capsule_utility


def test_no_synthetic_task_delta_ever() -> None:
    result = evaluate_capsule_utility(
        raw_source_status="measured",
        adoption_success=True,
        target_behavior_before="before",
        target_behavior_after="after",
        selection_delta=None,
    )
    assert result.utility_task_delta is None
    assert result.utility_status == "state_change_only_not_measured"
    assert result.claim_eligible is False


def test_positive_measured_outcome_is_claim_eligible() -> None:
    result = evaluate_capsule_utility(
        raw_source_status="measured",
        adoption_success=True,
        target_behavior_before="before",
        target_behavior_after="after",
        selection_delta=0.25,
    )
    assert result.utility_status == "positive_utility_measured"
    assert result.utility_delta == 0.25
    assert result.claim_eligible is True


def test_provisional_source_never_claim_eligible() -> None:
    result = evaluate_capsule_utility(
        raw_source_status="provisional",
        adoption_success=True,
        target_behavior_before="before",
        target_behavior_after="after",
        selection_delta=1.0,
    )
    assert result.utility_status == "positive_utility_measured"
    assert result.claim_eligible is False


def test_blocked_adoption_has_blocked_status() -> None:
    result = evaluate_capsule_utility(
        raw_source_status="measured",
        adoption_success=False,
        target_behavior_before=None,
        target_behavior_after=None,
        selection_delta=0.5,
    )
    assert result.utility_status == "blocked"
    assert result.claim_eligible is False


def test_negative_utility_not_claim_eligible() -> None:
    result = evaluate_capsule_utility(
        raw_source_status="measured",
        adoption_success=True,
        target_behavior_before="a",
        target_behavior_after="b",
        selection_delta=-0.4,
    )
    assert result.utility_status == "negative_utility_measured"
    assert result.claim_eligible is False
