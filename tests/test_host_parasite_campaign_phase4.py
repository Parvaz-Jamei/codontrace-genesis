"""Phase 4: multi-seed campaign digests + fail-closed ClaimGate factory."""

from __future__ import annotations

import pytest

from codontrace.claimgate import audit_bundle
from codontrace.claimgate.adapters.host_parasite import (
    attach_host_parasite_campaign,
    bundle_from_host_parasite_campaign,
    bundle_from_host_parasite_cou,
)
from codontrace.errors import ConfigurationError
from codontrace.genesis.host_parasite_campaign import (
    CAMPAIGN_ARMS,
    run_host_parasite_campaign,
)


def test_campaign_arms_cover_required_set() -> None:
    assert CAMPAIGN_ARMS == frozenset(
        {
            "intact",
            "content_null",
            "structure_null",
            "dual_null",
            "abiotic_only",
            "freeze_replay_parasites",
        }
    )


def test_campaign_deterministic_digests() -> None:
    a = run_host_parasite_campaign(seeds=(11, 22, 33), request_claim_ceiling="candidate_evidence")
    b = run_host_parasite_campaign(seeds=(11, 22, 33), request_claim_ceiling="candidate_evidence")
    da = a.to_dict()
    db = b.to_dict()
    assert da["campaign_digest"] == db["campaign_digest"]
    assert da["arm_digests"] == db["arm_digests"]
    assert len(da["arm_digests"]) == len(CAMPAIGN_ARMS)
    assert len(set(da["arm_digests"].values())) == len(CAMPAIGN_ARMS)


def test_campaign_seed_order_changes_digest() -> None:
    a = run_host_parasite_campaign(seeds=(1, 2), request_claim_ceiling="runtime_observation")
    b = run_host_parasite_campaign(seeds=(2, 1), request_claim_ceiling="runtime_observation")
    assert a.to_dict()["campaign_digest"] != b.to_dict()["campaign_digest"]


def test_intact_differs_from_null_and_abiotic() -> None:
    result = run_host_parasite_campaign(
        seeds=(7, 8),
        request_claim_ceiling="candidate_evidence",
        steal_fraction=0.8,
    )
    by_arm = {arm.arm: arm for arm in result.arm_results}
    assert by_arm["intact"].mean_score < by_arm["abiotic_only"].mean_score
    assert by_arm["intact"].mean_score < by_arm["content_null"].mean_score
    assert by_arm["structure_null"].injected_fraction == 0.0
    assert by_arm["intact"].injected_fraction == 1.0
    assert by_arm["freeze_replay_parasites"].injected_fraction == 1.0
    assert result.falsification_rules_passed is True
    assert result.claim_ceiling == "candidate_evidence"
    assert result.red_queen_proved is False


def test_steal_zero_still_falsifies_via_injection() -> None:
    result = run_host_parasite_campaign(
        seeds=(3, 4),
        steal_fraction=0.0,
        request_claim_ceiling="candidate_evidence",
    )
    assert result.falsification_rules_passed is True
    by_arm = {arm.arm: arm for arm in result.arm_results}
    assert by_arm["intact"].mean_score == by_arm["abiotic_only"].mean_score == 1.0
    assert by_arm["structure_null"].injected_fraction != by_arm["intact"].injected_fraction


def test_refuse_ceiling_above_candidate_on_run() -> None:
    with pytest.raises(ConfigurationError, match="candidate_evidence"):
        run_host_parasite_campaign(
            seeds=(1,),
            request_claim_ceiling="mechanism_support",
        )


def test_refuse_candidate_without_contrast_arms() -> None:
    with pytest.raises(ConfigurationError, match="falsification"):
        run_host_parasite_campaign(
            seeds=(1, 2),
            arms=("intact",),
            request_claim_ceiling="candidate_evidence",
        )


def test_bundle_factory_attaches_digests_without_raising_ladder() -> None:
    campaign = run_host_parasite_campaign(
        seeds=(9, 10),
        request_claim_ceiling="candidate_evidence",
    )
    bundle = bundle_from_host_parasite_campaign(
        campaign,
        question_of_interest="Does freeze/replay change digital retained-CPU vs abiotic?",
        context_of_use="Digital HostParasiteEnv campaign only. No clinic. No Red Queen proof.",
        claimed="candidate_evidence",
    )
    before = "candidate_evidence"
    assert bundle.extra["requested_claim"] == before
    payload = bundle.extra["host_parasite_campaign"]
    assert payload["campaign_digest"] == campaign.to_dict()["campaign_digest"]
    assert payload["arm_digests"] == campaign.to_dict()["arm_digests"]
    assert payload["red_queen_proved"] is False
    assert payload["grants_intervention_supported"] is False
    assert payload["raises_claim_ladder"] is False
    audit = audit_bundle(bundle)
    assert audit.achieved_level <= 2


def test_bundle_refuses_mechanism_support_ceiling() -> None:
    campaign = run_host_parasite_campaign(
        seeds=(1, 2),
        request_claim_ceiling="candidate_evidence",
    )
    with pytest.raises(ConfigurationError, match="candidate_evidence"):
        bundle_from_host_parasite_campaign(
            campaign,
            question_of_interest="q",
            context_of_use="Digital only.",
            claimed="mechanism_support",
        )


def test_attach_refuses_silent_overwrite() -> None:
    campaign = run_host_parasite_campaign(
        seeds=(5,),
        arms=("intact", "abiotic_only", "content_null"),
        request_claim_ceiling="runtime_observation",
    )
    bundle = bundle_from_host_parasite_campaign(
        campaign,
        question_of_interest="q",
        context_of_use="Digital only.",
        claimed="runtime_observation",
    )
    with pytest.raises(ConfigurationError, match="already attached"):
        attach_host_parasite_campaign(bundle, campaign)


def test_attach_refuses_missing_requested_claim() -> None:
    campaign = run_host_parasite_campaign(
        seeds=(5,),
        arms=("intact", "abiotic_only"),
        request_claim_ceiling="runtime_observation",
    )
    bundle = bundle_from_host_parasite_cou(
        question_of_interest="q",
        context_of_use="Digital only.",
        model_influence=1,
        decision_consequence=1,
        treatment_scores=(0.2,),
        control_scores=(1.0,),
    )
    # Simulate a corrupted / menu-only attach surface with no requested_claim.
    from dataclasses import replace

    broken = replace(bundle, extra={k: v for k, v in (bundle.extra or {}).items() if k != "requested_claim"})
    with pytest.raises(ConfigurationError, match="requested_claim"):
        attach_host_parasite_campaign(broken, campaign)


def test_attach_refuses_candidate_without_falsification() -> None:
    # Runtime campaign intentionally lacks contrast → falsification false,
    # then try to attach onto a candidate_evidence-labelled bundle.
    campaign = run_host_parasite_campaign(
        seeds=(1,),
        arms=("intact",),
        request_claim_ceiling="runtime_observation",
    )
    assert campaign.falsification_rules_passed is False
    bundle = bundle_from_host_parasite_cou(
        question_of_interest="q",
        context_of_use="Digital only.",
        model_influence=1,
        decision_consequence=1,
        treatment_scores=(0.2, 0.3),
        control_scores=(0.9, 0.8),
        claimed="candidate_evidence",
    )
    with pytest.raises(ConfigurationError, match="falsification"):
        attach_host_parasite_campaign(bundle, campaign)


def test_duplicate_seed_and_unknown_arm_fail_closed() -> None:
    with pytest.raises(ConfigurationError, match="duplicate"):
        run_host_parasite_campaign(seeds=(1, 1))
    with pytest.raises(ConfigurationError, match="arms"):
        run_host_parasite_campaign(seeds=(1,), arms=("clinical_null",))


def test_engine_not_imported_by_campaign_module() -> None:
    import inspect

    import codontrace.genesis.host_parasite_campaign as mod

    src = inspect.getsource(mod)
    assert "engine" not in src.lower() or "engine.py" in src
    assert "does not modify ``engine.py``" in src or "does not modify" in src
    assert "from codontrace.genesis.engine" not in src
    assert "from codontrace.engine" not in src


def test_bundle_refuses_candidate_when_campaign_ceiling_is_runtime() -> None:
    campaign = run_host_parasite_campaign(
        seeds=(1, 2),
        request_claim_ceiling="runtime_observation",
    )
    assert campaign.falsification_rules_passed is True
    assert campaign.claim_ceiling == "runtime_observation"
    with pytest.raises(ConfigurationError, match="claim_ceiling"):
        bundle_from_host_parasite_campaign(
            campaign,
            question_of_interest="q",
            context_of_use="Digital only.",
            claimed="candidate_evidence",
        )


def test_public_surfaces_have_no_toy_wording() -> None:
    import inspect

    import codontrace.genesis.host_parasite_campaign as camp
    import codontrace.genesis.host_parasite_env as env

    for mod in (camp, env):
        src = inspect.getsource(mod)
        assert "toy" not in src.lower()
