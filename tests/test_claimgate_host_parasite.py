"""Host–parasite DomainProfile port: thin adapter; engine not forked."""

from __future__ import annotations

import pytest

from codontrace.claimgate import HOST_PARASITE, PROFILES, audit_bundle, bundle_from_declared_scores
from codontrace.claimgate.adapters.host_parasite import (
    BLOCKED_HOST_PARASITE_CLAIMS,
    assert_claim_allowed,
    bundle_from_host_parasite_cou,
)
from codontrace.errors import ConfigurationError


def test_host_parasite_profile_is_registered() -> None:
    assert "host_parasite" in PROFILES
    assert PROFILES["host_parasite"] is HOST_PARASITE
    assert HOST_PARASITE.name == "host_parasite"
    assert HOST_PARASITE.extra_defaults["infection_physics"] == "not_implemented"
    assert HOST_PARASITE.extra_defaults["clinical_scope"] == "blocked"
    assert HOST_PARASITE.extra_defaults["certification"] == "none"


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
    ],
)
def test_assert_claim_allowed_fails_closed_on_clinical_aliases(alias: str) -> None:
    with pytest.raises(ConfigurationError, match="blocked"):
        assert_claim_allowed(alias)


def test_assert_claim_allowed_passes_runtime_observation() -> None:
    assert assert_claim_allowed("runtime_observation") == "runtime_observation"
    assert assert_claim_allowed("  Runtime_Observation  ") == "runtime_observation"


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
