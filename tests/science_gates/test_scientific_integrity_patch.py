"""Adversarial scientific-validity regressions, including valid positive controls."""

from dataclasses import replace

import pytest

from codontrace.energy import ATPAccount
from codontrace.errors import ConfigurationError
from codontrace.genesis.causal_validation import (
    CausalInterventionRunPair,
    InterventionSpec,
    build_causal_evidence_report,
    build_intervention_result,
)
from codontrace.genesis.evidence_validation import EvidenceValidationContext
from codontrace.genesis.measurements.d2_recovery_v2 import (
    assess_recovery,
    capture_recovery_boundary,
    execute_runtime_transfer,
    transfer_yield,
)


def _pair(index: int, *, intervention: str = "probe", history: str | None = None):
    spec = InterventionSpec(
        intervention, "factor", "b", "t", "family", baseline_settings={"factor": 0}, treatment_settings={"factor": 1}
    )
    return CausalInterventionRunPair(
        spec, "b", "t", 0, 1 + index / 100, history_id=history or f"h{index}", seed=index, run_id=f"r{index}"
    )


def test_one_history_cannot_become_sixteen_units_by_intervention_aliases():
    pairs = [replace(_pair(i, intervention=f"alias{i}", history="same"), seed=1, run_id="same") for i in range(16)]
    report = build_causal_evidence_report(pairs)
    assert report.independent_count < 16
    assert not report.claim_eligible
    assert not report.effect.statistical_support
    assert report.failure_status == "mixed_interventions_require_separate_reports"


def test_run_aliases_do_not_change_the_independent_history_count():
    base = _pair(1)
    report = build_causal_evidence_report([replace(base, run_id=f"alias{i}") for i in range(16)])
    assert report.independent_count == 1
    assert not report.claim_eligible


def test_different_estimands_on_independent_histories_are_not_pooled():
    report = build_causal_evidence_report([_pair(i, intervention=f"different{i}") for i in range(16)])
    assert not report.effect.interval_defined
    assert not report.claim_eligible


@pytest.mark.parametrize("baseline,treatment", [([], []), ([0], [1]), ([0, 0], [1, 1])])
def test_anonymous_arrays_never_grant_intervention_support(baseline, treatment):
    result = build_intervention_result("probe", baseline, treatment)
    assert result.confidence_interval is None
    assert not result.claim_eligible
    assert not EvidenceValidationContext(intervention_results=(result,)).has_validated_intervention_result()


def test_unequal_arrays_and_mismatched_pairs_are_rejected():
    with pytest.raises(ConfigurationError, match="equal paired lengths"):
        build_intervention_result("probe", [0, 0], [1])
    with pytest.raises(ConfigurationError, match="do not match"):
        build_intervention_result("other", [0], [1.01], run_pairs=[_pair(1)])


def test_audited_positive_intervention_is_still_supported():
    pairs = [_pair(i) for i in range(16)]
    result = build_intervention_result(
        "probe", [p.baseline_metric for p in pairs], [p.treatment_metric for p in pairs], run_pairs=pairs
    )
    assert result.claim_eligible
    assert result.confidence_interval[0] > 0
    assert EvidenceValidationContext(intervention_results=(result,)).has_validated_intervention_result()
    forged = replace(result, effect_size=99, digest="")
    assert not forged.claim_eligible


def test_claim_eligible_binds_scenario_and_reconstructed_array_digests():
    """A supported result stays bound to the intervention and the metric arrays.

    Assignment is not a label that can be swapped after the contrast is signed,
    and the array digests are the constructor's digest of those metrics.
    """

    pairs = [_pair(i) for i in range(16)]
    result = build_intervention_result(
        "probe", [p.baseline_metric for p in pairs], [p.treatment_metric for p in pairs], run_pairs=pairs
    )
    assert result.claim_eligible
    assert result.scenario_id == "probe"
    assert {pair.spec.intervention_id for pair in result.causal_report.run_pairs} == {"probe"}

    wrong_scenario = replace(result, scenario_id="other-probe", digest="")
    assert not wrong_scenario.claim_eligible

    wrong_baseline = replace(result, baseline_digest="0" * 64, digest="")
    assert not wrong_baseline.claim_eligible

    wrong_treatment = replace(result, treatment_digest="1" * 64, digest="")
    assert not wrong_treatment.claim_eligible


def test_unrelated_move_and_food_rows_are_not_a_transfer():
    source, recipient = ATPAccount(20), ATPAccount(5)
    debit = source.debit(3, tick=7, agent_id="s", codon="000", action="MOVE", reason="move")
    credit = recipient.credit(3, tick=7, agent_id="r", codon="000", action="EAT", reason="food")
    event = dict(
        evidence="engine_ledger",
        run_id="history",
        contact_id="invented",
        tick=7,
        source_id="s",
        recipient_id="r",
        source_entry_id=debit,
        recipient_entry_id=credit,
        atp_paid=3,
        loss=0,
    )
    with pytest.raises(ConfigurationError, match="not bound"):
        transfer_yield([event], [*source.ledger, *recipient.ledger])


def _recovery(*, run_id="history", maintenance=0):
    source, recipient = ATPAccount(20), ATPAccount(10)

    def sample(tick):
        return capture_recovery_boundary(recipient, run_id=run_id, recipient_id="r", tick=tick)

    boundaries = [sample(0)]
    recipient.debit(5, tick=1, agent_id="r", codon="d2", action="drop", reason="disturbance")
    boundaries.append(sample(1))
    event = execute_runtime_transfer(
        source,
        recipient,
        run_id=run_id,
        contact_id="contact",
        source_id="s",
        recipient_id="r",
        tick=2,
        amount=3 + maintenance,
    )
    if maintenance:
        recipient.debit(maintenance, tick=2, agent_id="r", codon="d2", action="maintenance", reason="cost")
    boundaries.extend([sample(2), sample(3)])
    return source, recipient, boundaries, event


@pytest.mark.parametrize("maintenance", [0, 0.5])
def test_time_bound_recovery_reconciles_net_credit_and_cost(maintenance):
    source, recipient, boundaries, event = _recovery(maintenance=maintenance)
    report = assess_recovery(boundaries, [event], [*source.ledger, *recipient.ledger], recipient_id="r")
    assert report["performance_recovered"]
    assert not report["hypothesis_supported"]


def test_numeric_trajectory_has_no_history_or_time_evidence():
    source, recipient, _boundaries, event = _recovery()
    report = assess_recovery([10, 5, 8, 8], [event], [*source.ledger, *recipient.ledger], recipient_id="r")
    assert not report["performance_recovered"]
    assert report["reason"] == "unbound_boundaries"


def test_transfer_after_the_window_cannot_explain_earlier_recovery():
    source, recipient = ATPAccount(20), ATPAccount(10)

    def sample(tick):
        return capture_recovery_boundary(recipient, run_id="h", recipient_id="r", tick=tick)

    boundaries = [sample(0)]
    recipient.debit(5, tick=1, agent_id="r", codon="d2", action="drop", reason="drop")
    boundaries.append(sample(1))
    recipient.credit(3, tick=2, agent_id="r", codon="000", action="EAT", reason="food")
    boundaries.extend([sample(2), sample(3)])
    late = execute_runtime_transfer(
        source, recipient, run_id="h", contact_id="late", source_id="s", recipient_id="r", tick=99, amount=3
    )
    report = assess_recovery(boundaries, [late], [*source.ledger, *recipient.ledger], recipient_id="r")
    assert not report["performance_recovered"]


def test_mixed_history_and_changed_balance_samples_are_rejected():
    source, recipient, boundaries, event = _recovery()
    ledger = [*source.ledger, *recipient.ledger]
    mixed = [dict(row) for row in boundaries]
    mixed[-1]["run_id"] = "other"
    with pytest.raises(ConfigurationError, match="mix histories"):
        assess_recovery(mixed, [event], ledger, recipient_id="r")
    altered = [dict(row) for row in boundaries]
    altered[2]["value"] = 99
    with pytest.raises(ConfigurationError, match="does not match"):
        assess_recovery(altered, [event], ledger, recipient_id="r")


def test_replay_state_covers_entries_not_only_contact_names():
    source, recipient, boundaries, event = _recovery()
    ledger = [*source.ledger, *recipient.ledger]
    first = transfer_yield([event], ledger)
    with pytest.raises(ConfigurationError, match="replay of a ledger entry"):
        transfer_yield([dict(event, contact_id="alias")], ledger, used_ledger_entries=first["consumed_ledger_entries"])
    with pytest.raises(ConfigurationError, match="replay of contact"):
        assess_recovery(boundaries, [event], ledger, recipient_id="r", used_contact_ids=first["consumed_contact_ids"])


def test_unfunded_transfer_leaves_both_books_unchanged():
    source, recipient = ATPAccount(1), ATPAccount(2)
    before = source.to_dict(), recipient.to_dict()
    with pytest.raises(ConfigurationError, match="cannot fund"):
        execute_runtime_transfer(
            source, recipient, run_id="h", contact_id="c", source_id="s", recipient_id="r", tick=0, amount=3
        )
    assert (source.to_dict(), recipient.to_dict()) == before
