"""Phase 3: intervention falsification, multilevel gate, ARD/FSD labels."""

from __future__ import annotations

import pytest

from codontrace.claimgate import audit_bundle
from codontrace.claimgate.adapters.host_parasite import (
    assert_transition_claim_allowed,
    attach_phase3_honesty,
    bundle_from_host_parasite_cou,
    declared_dynamics_labels,
    multilevel_transition_worksheet,
    run_intervention_falsification,
)
from codontrace.errors import ConfigurationError


def _bundle():
    return bundle_from_host_parasite_cou(
        question_of_interest="Does a digital remove-parasites arm falsify coevolution scores?",
        context_of_use="Digital HostParasiteEnv only. No clinic. No Red Queen proof.",
        model_influence=2,
        decision_consequence=2,
        treatment_scores=(0.4, 0.41, 0.39),
        control_scores=(0.2, 0.21, 0.19),
    )


def test_remove_parasites_falsification_passes_and_stays_runtime() -> None:
    result = run_intervention_falsification(
        kind="remove_parasites",
        host_tasks=("nand", "and"),
        parasite_tasks=("and",),
        payload=(1, 2, 3),
        steal_fraction=0.8,
    )
    assert result.passed is True
    assert result.intervention_score > result.control_score
    assert result.claim_ceiling == "runtime_observation"
    assert result.to_dict()["grants_intervention_supported"] is False


@pytest.mark.parametrize(
    "kind",
    [
        "content_null_payload",
        "structure_null_overlap",
        "steal_fraction_ablation",
        "abiotic_only_arm",
    ],
)
def test_falsification_kinds_change_scores(kind: str) -> None:
    result = run_intervention_falsification(
        kind=kind,
        host_tasks=("and", "or"),
        parasite_tasks=("and",),
        payload=(9, 8),
    )
    assert result.passed is True
    assert result.score_delta != 0.0


def test_falsification_rejects_clinical_kind() -> None:
    with pytest.raises(ConfigurationError, match="kind"):
        run_intervention_falsification(
            kind="vaccine_trial",
            host_tasks=("and",),
            parasite_tasks=("and",),
        )


def test_multilevel_worksheet_blocks_transition_strings() -> None:
    sheet = multilevel_transition_worksheet()
    assert sheet.transition_claim_allowed is False
    assert sheet.readiness_documented is False
    assert "price_partition_is_not_causal" in sheet.open_gaps
    with pytest.raises(ConfigurationError):
        assert_transition_claim_allowed("major_transition_proved", sheet)
    with pytest.raises(ConfigurationError, match="blocked"):
        assert_transition_claim_allowed("major_transition", sheet)


def test_multilevel_worksheet_can_clear_gaps_without_proving() -> None:
    sheet = multilevel_transition_worksheet(
        within_host_conflict_measured=True,
        between_host_export_measured=True,
        fitness_reorganization_documented=True,
        price_partition_only=False,
    )
    assert sheet.readiness_documented is True
    assert sheet.transition_claim_allowed is False
    assert assert_transition_claim_allowed("runtime_observation", sheet) == "runtime_observation"
    # Cleared readiness still cannot unlock transition language.
    with pytest.raises(ConfigurationError, match="blocked"):
        assert_transition_claim_allowed("major_transition_proved", sheet)
    with pytest.raises(ConfigurationError, match="blocked"):
        assert_transition_claim_allowed("major_transition", sheet)


def test_falsification_requires_control_overlap() -> None:
    with pytest.raises(ConfigurationError, match="task overlap"):
        run_intervention_falsification(
            kind="remove_parasites",
            host_tasks=("nand",),
            parasite_tasks=("xor",),
            payload=(1,),
        )


def test_ard_fsd_labels_never_prove_red_queen() -> None:
    labels = declared_dynamics_labels("ard_candidate")
    assert labels.red_queen_proved is False
    assert "not proved" in labels.note.lower() or "not proved" in labels.note
    fsd = declared_dynamics_labels("fsd_candidate")
    assert fsd.red_queen_proved is False
    mixed = declared_dynamics_labels("ard_fsd_mixed_candidate")
    assert mixed.to_dict()["raises_claim_ladder"] is False
    with pytest.raises(ConfigurationError):
        declared_dynamics_labels("red_queen_proved")


def test_attach_phase3_honesty_does_not_raise_ladder() -> None:
    bundle = _bundle()
    before = audit_bundle(bundle).achieved_level
    result = run_intervention_falsification(
        kind="content_null_payload",
        host_tasks=("and",),
        parasite_tasks=("and",),
        payload=(1,),
    )
    sheet = multilevel_transition_worksheet()
    dynamics = declared_dynamics_labels("fsd_candidate")
    enriched = attach_phase3_honesty(
        bundle,
        falsification=result,
        worksheet=sheet,
        dynamics=dynamics,
    )
    after = audit_bundle(enriched).achieved_level
    assert after == before
    extra = enriched.extra or {}
    assert extra["intervention_falsification"]["grants_intervention_supported"] is False
    assert extra["dynamics_labels"]["red_queen_proved"] is False
    assert extra["multilevel_transition_worksheet"]["raises_claim_ladder"] is False


def test_attach_phase3_refuses_overwrite_and_wrong_domain() -> None:
    from codontrace.claimgate.adapters.biomedical import bundle_from_biomedical_cou

    bio = bundle_from_biomedical_cou(
        question_of_interest="q",
        context_of_use="c",
        model_influence=1,
        decision_consequence=1,
        treatment_scores=(0.1,),
        control_scores=(0.0,),
    )
    with pytest.raises(ConfigurationError, match="host_parasite"):
        attach_phase3_honesty(bio, dynamics=declared_dynamics_labels())
    bundle = _bundle()
    once = attach_phase3_honesty(bundle, dynamics=declared_dynamics_labels("ard_candidate"))
    with pytest.raises(ConfigurationError, match="already attached"):
        attach_phase3_honesty(once, dynamics=declared_dynamics_labels("fsd_candidate"))


def test_attach_phase3_rejects_noop() -> None:
    with pytest.raises(ConfigurationError, match="requires"):
        attach_phase3_honesty(_bundle())


def test_soft_transition_request_blocks_readiness() -> None:
    sheet = multilevel_transition_worksheet(
        within_host_conflict_measured=True,
        between_host_export_measured=True,
        fitness_reorganization_documented=True,
        price_partition_only=False,
        requested_transition_claim="major_transition",
    )
    assert sheet.readiness_documented is False
    assert any(gap.startswith("blocked_claim:") for gap in sheet.open_gaps)
