"""Host–parasite DomainProfile port: thin adapter; engine not forked."""

from __future__ import annotations

import pytest

from codontrace.claimgate import HOST_PARASITE, PROFILES, audit_bundle, bundle_from_declared_scores
from codontrace.claimgate.adapters.host_parasite import (
    BLOCKED_HOST_PARASITE_CLAIMS,
    DECLARED_INTERVENTION_KINDS,
    assert_claim_allowed,
    attach_declared_intervention_menu,
    bundle_from_host_parasite_cou,
    declared_cou_risk_labels,
    declared_intervention_menu,
)
from codontrace.errors import ConfigurationError


def _toy_menu_rows() -> tuple[dict[str, str], ...]:
    return (
        {
            "intervention_id": "I1_remove_parasites",
            "kind": "remove_parasites",
            "description": "Drop all parasites while keeping host task set.",
            "expected_digital_effect": "coevolution score collapses toward abiotic-only baseline",
        },
        {
            "intervention_id": "I2_content_null",
            "kind": "content_null_payload",
            "description": "Replace parasite payload with null content; keep seats.",
            "expected_digital_effect": "payload-dependent gain disappears; seat structure remains",
        },
    )


def test_host_parasite_profile_is_registered() -> None:
    assert "host_parasite" in PROFILES
    assert PROFILES["host_parasite"] is HOST_PARASITE
    assert HOST_PARASITE.name == "host_parasite"
    assert HOST_PARASITE.extra_defaults["infection_physics"] == "not_implemented"
    assert HOST_PARASITE.extra_defaults["clinical_scope"] == "blocked"
    assert HOST_PARASITE.extra_defaults["certification"] == "none"
    assert "crispr_identity_proved" in HOST_PARASITE.blocked_claims
    assert "red_queen_proved" in HOST_PARASITE.blocked_claims
    assert "major_transition_proved" in HOST_PARASITE.blocked_claims


def test_host_parasite_wrapper_records_domain_and_stays_unverified() -> None:
    bundle = bundle_from_host_parasite_cou(
        question_of_interest="Does a toy task-overlap score license a coevolution claim?",
        context_of_use="Synthetic digital host–parasite scores only. No wet lab. No clinic.",
        model_influence=2,
        decision_consequence=2,
        treatment_scores=(0.40, 0.38, 0.42),
        control_scores=(0.20, 0.22, 0.19),
        metric="task_overlap_toy",
    )
    extra = bundle.extra or {}
    assert extra["domain"] == "host_parasite"
    assert extra["model_risk"] == 2
    assert extra["infection_physics"] == "not_implemented"
    assert extra["clinical_scope"] == "blocked"
    assert extra["asme_vv40"] == "complement_only"
    assert extra["fda_2023"] == "declared_labels_only"
    assert bundle.replay.verified is False
    report = audit_bundle(bundle)
    assert report.achieved_level <= 2


@pytest.mark.parametrize("alias", sorted(BLOCKED_HOST_PARASITE_CLAIMS))
def test_host_parasite_wrapper_rejects_blocked_aliases(alias: str) -> None:
    with pytest.raises(ConfigurationError):
        bundle_from_host_parasite_cou(
            question_of_interest="q",
            context_of_use="c",
            model_influence=1,
            decision_consequence=1,
            treatment_scores=(0.1,),
            control_scores=(0.0,),
            claimed=alias,
        )


@pytest.mark.parametrize(
    "alias",
    [
        "vaccine_efficacy_proved",
        "antiviral_therapy_validated",
        "clinical_pathogen_model",
        "epidemic_forecast_certified",
        "phage_therapy_cleared",
        "virulence_optimized_for_humans",
        "biosafety_level_certified",
        "crispr_identity_proved",
        "crispr_therapy_validated",
        "red_queen_proved",
        "major_transition_proved",
    ],
)
def test_assert_claim_allowed_fails_closed_on_clinical_aliases(alias: str) -> None:
    with pytest.raises(ConfigurationError, match="blocked"):
        assert_claim_allowed(alias)


def test_assert_claim_allowed_passes_runtime_observation() -> None:
    assert assert_claim_allowed("runtime_observation") == "runtime_observation"
    assert assert_claim_allowed("  Runtime_Observation  ") == "runtime_observation"


def test_assert_claim_allowed_rejects_blank() -> None:
    with pytest.raises(ConfigurationError, match="non-empty"):
        assert_claim_allowed("   ")
    with pytest.raises(ConfigurationError, match="non-empty"):
        assert_claim_allowed("")


def test_host_parasite_profile_blocks_via_generic_declared_scores() -> None:
    with pytest.raises(ConfigurationError):
        bundle_from_declared_scores(
            profile=HOST_PARASITE,
            question_of_interest="q",
            context_of_use="c",
            model_influence=1,
            decision_consequence=1,
            treatment_scores=(0.2,),
            control_scores=(0.1,),
            claimed="phage_therapy_cleared",
        )


def test_host_parasite_is_independent_of_biomedical_domain_label() -> None:
    bundle = bundle_from_host_parasite_cou(
        question_of_interest="q",
        context_of_use="Digital coevolution table; no pathogen clinic.",
        model_influence=1,
        decision_consequence=1,
        treatment_scores=(0.3, 0.31),
        control_scores=(0.1, 0.11),
    )
    extra = bundle.extra or {}
    assert extra["domain"] == "host_parasite"
    assert extra["domain"] != "biomedical"


def test_declared_cou_risk_labels_defaults_and_safe_override() -> None:
    labels = declared_cou_risk_labels()
    assert labels["asme_vv40"] == "complement_only"
    assert labels["infection_physics"] == "not_implemented"
    labels2 = declared_cou_risk_labels(infection_physics="optional_env_outside_core")
    assert labels2["infection_physics"] == "optional_env_outside_core"
    with pytest.raises(ConfigurationError):
        declared_cou_risk_labels(certification="fda_cleared")
    with pytest.raises(ConfigurationError):
        declared_cou_risk_labels(clinical_scope="allowed")


def test_bundle_accepts_safe_cou_risk_override() -> None:
    bundle = bundle_from_host_parasite_cou(
        question_of_interest="q",
        context_of_use="Digital table with optional env declared outside core.",
        model_influence=1,
        decision_consequence=1,
        treatment_scores=(0.2,),
        control_scores=(0.1,),
        cou_risk_overrides={"infection_physics": "optional_env_outside_core"},
    )
    assert (bundle.extra or {})["infection_physics"] == "optional_env_outside_core"


def test_declared_intervention_menu_schema_stub() -> None:
    menu = declared_intervention_menu(
        question_of_interest="Does remove-parasites falsify a digital coevolution score?",
        context_of_use="Declared menu only. No campaign executed.",
        interventions=_toy_menu_rows(),
    )
    payload = menu.to_dict()
    assert payload["schema"] == "host_parasite_declared_intervention_menu_v1"
    assert payload["executed"] is False
    assert payload["raises_claim_ladder"] is False
    assert len(payload["interventions"]) == 2
    assert "content_null_payload" in DECLARED_INTERVENTION_KINDS


def test_declared_intervention_menu_rejects_empty_and_blocked_ids() -> None:
    with pytest.raises(ConfigurationError, match="at least one"):
        declared_intervention_menu(
            question_of_interest="q",
            context_of_use="c",
            interventions=(),
        )
    bad = (
        {
            "intervention_id": "phage_therapy_cleared",
            "kind": "remove_parasites",
            "description": "x",
            "expected_digital_effect": "y",
        },
    )
    with pytest.raises(ConfigurationError, match="blocked"):
        declared_intervention_menu(
            question_of_interest="q",
            context_of_use="c",
            interventions=bad,
        )
    dup = (
        _toy_menu_rows()[0],
        dict(_toy_menu_rows()[0]),
    )
    with pytest.raises(ConfigurationError, match="duplicate"):
        declared_intervention_menu(
            question_of_interest="q",
            context_of_use="c",
            interventions=dup,
        )
    weird_kind = (
        {
            "intervention_id": "I9",
            "kind": "clinical_trial",
            "description": "x",
            "expected_digital_effect": "y",
        },
    )
    with pytest.raises(ConfigurationError, match="kind"):
        declared_intervention_menu(
            question_of_interest="q",
            context_of_use="c",
            interventions=weird_kind,
        )


def test_attach_declared_intervention_menu_does_not_raise_ladder() -> None:
    bundle = bundle_from_host_parasite_cou(
        question_of_interest="Does a declared menu change the public grade?",
        context_of_use="Menu attachment must not promote claims.",
        model_influence=2,
        decision_consequence=2,
        treatment_scores=(0.4, 0.41, 0.39),
        control_scores=(0.2, 0.21, 0.19),
    )
    before = audit_bundle(bundle).achieved_level
    enriched = attach_declared_intervention_menu(bundle, interventions=_toy_menu_rows())
    after = audit_bundle(enriched).achieved_level
    assert after == before
    menu = (enriched.extra or {})["declared_intervention_menu"]
    assert menu["raises_claim_ladder"] is False
    assert any("Declared intervention menu" in item for item in enriched.limitations)


def test_intervention_row_and_menu_use_bool_flags() -> None:
    menu = declared_intervention_menu(
        question_of_interest="q",
        context_of_use="c",
        interventions=_toy_menu_rows(),
    )
    payload = menu.to_dict()
    assert payload["executed"] is False
    assert isinstance(payload["executed"], bool)
    row = payload["interventions"][0]
    assert row["executed"] is False
    assert row["raises_claim_ladder"] is False


def test_attach_menu_rejects_non_host_parasite_bundle() -> None:
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
        attach_declared_intervention_menu(bio, interventions=_toy_menu_rows())


def test_unknown_cou_risk_override_keys_fail_closed() -> None:
    with pytest.raises(ConfigurationError, match="unknown keys"):
        bundle_from_host_parasite_cou(
            question_of_interest="q",
            context_of_use="c",
            model_influence=1,
            decision_consequence=1,
            treatment_scores=(0.1,),
            control_scores=(0.0,),
            cou_risk_overrides={"not_a_real_key": "x"},
        )


def test_attach_menu_refuses_silent_overwrite() -> None:
    bundle = bundle_from_host_parasite_cou(
        question_of_interest="q",
        context_of_use="c",
        model_influence=1,
        decision_consequence=1,
        treatment_scores=(0.2,),
        control_scores=(0.1,),
    )
    once = attach_declared_intervention_menu(bundle, interventions=_toy_menu_rows())
    with pytest.raises(ConfigurationError, match="already attached"):
        attach_declared_intervention_menu(once, interventions=_toy_menu_rows()[:1])
