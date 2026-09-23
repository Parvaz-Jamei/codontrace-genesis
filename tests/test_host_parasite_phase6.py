"""Phase 6: factorial, adaptive-origin gate, network digests, preregistration."""

from __future__ import annotations

import pytest

from codontrace.claimgate import audit_bundle
from codontrace.claimgate.adapters.host_parasite import (
    attach_host_parasite_campaign,
    bundle_from_host_parasite_cou,
)
from codontrace.claimgate.adapters.host_parasite_prereg import (
    attach_host_parasite_preregistration,
    host_parasite_preregistration,
    require_preregistration_before_campaign_attach,
)
from codontrace.errors import ConfigurationError
from codontrace.genesis.host_parasite_campaign import run_host_parasite_campaign
from codontrace.genesis.host_parasite_factorial import (
    adaptive_origin_gate,
    run_abiotic_biotic_factorial,
    summarize_interaction_network,
)


def test_factorial_four_cells_with_digests() -> None:
    result = run_abiotic_biotic_factorial(
        seeds=(1, 2),
        request_claim_ceiling="candidate_evidence",
    )
    assert len(result.cells) == 4
    keys = {(cell.abiotic, cell.biotic) for cell in result.cells}
    assert keys == {("low", "absent"), ("low", "present"), ("high", "absent"), ("high", "present")}
    payload = result.to_dict()
    assert payload["red_queen_proved"] is False
    assert "factorial_digest" in payload
    digests = {cell.campaign_digest for cell in result.cells}
    assert len(digests) >= 2


def test_adaptive_origin_gate_is_digital_only() -> None:
    gate = adaptive_origin_gate(allow_exaptation_like_gains=False)
    body = gate.to_dict()
    assert body["wet_claim"] is False
    assert body["raises_claim_ladder"] is False
    assert body["allow_exaptation_like_gains"] is False


def test_interaction_network_digest_deterministic() -> None:
    edges = (
        {"host_id": "H0", "parasite_id": "P0", "strength": 0.8},
        {"host_id": "H1", "parasite_id": "P0", "strength": 0.2},
        {"host_id": "H1", "parasite_id": "P1", "strength": 0.5},
    )
    a = summarize_interaction_network(edges)
    b = summarize_interaction_network(edges)
    assert a.to_dict()["digest"] == b.to_dict()["digest"]
    assert a.edge_count == 3
    assert a.host_count == 2
    assert a.parasite_count == 2
    assert a.strength_heterogeneity > 0.0
    assert a.to_dict()["red_queen_proved"] is False


def test_preregistration_required_before_campaign_attach() -> None:
    campaign = run_host_parasite_campaign(
        seeds=(3,),
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
    with pytest.raises(ConfigurationError, match="preregistration"):
        require_preregistration_before_campaign_attach(bundle)
    with pytest.raises(ConfigurationError, match="preregistration"):
        attach_host_parasite_campaign(bundle, campaign)
    prereg = host_parasite_preregistration(
        question_of_interest="Does abiotic-only differ from intact retained-CPU?",
        context_of_use="Digital factorial only. No clinic.",
        arms=("intact", "abiotic_only"),
        success_metrics=("mean_retained_cpu_diff",),
    )
    ready = attach_host_parasite_preregistration(bundle, prereg)
    before = audit_bundle(ready).achieved_level
    attached = attach_host_parasite_campaign(ready, campaign)
    assert "host_parasite_campaign" in attached.extra
    assert "host_parasite_preregistration" in attached.extra
    assert audit_bundle(attached).achieved_level == before


def test_preregistration_refuses_overwrite_and_empty_forbidden() -> None:
    bundle = bundle_from_host_parasite_cou(
        question_of_interest="q",
        context_of_use="Digital only.",
        model_influence=1,
        decision_consequence=1,
        treatment_scores=(0.2,),
        control_scores=(1.0,),
    )
    prereg = host_parasite_preregistration(
        question_of_interest="q",
        context_of_use="Digital only.",
        arms=("intact",),
        success_metrics=("score",),
        forbidden_claims=("red_queen_proved",),
    )
    once = attach_host_parasite_preregistration(bundle, prereg)
    with pytest.raises(ConfigurationError, match="already attached"):
        attach_host_parasite_preregistration(once, prereg)
    # Empty forbidden list is rejected before merge.
    with pytest.raises(ConfigurationError, match="forbidden_claims"):
        host_parasite_preregistration(
            question_of_interest="q",
            context_of_use="c",
            arms=("intact",),
            success_metrics=("score",),
            forbidden_claims=(),
        )


def test_factorial_refuses_high_ceiling() -> None:
    with pytest.raises(ConfigurationError, match="candidate_evidence"):
        run_abiotic_biotic_factorial(
            seeds=(1,),
            request_claim_ceiling="mechanism_support",
        )


def test_factorial_includes_network_when_provided() -> None:
    result = run_abiotic_biotic_factorial(
        seeds=(1,),
        network_edges=[{"host_id": "H0", "parasite_id": "P0", "strength": 1.0}],
    )
    assert result.network is not None
    assert result.network.edge_count == 1
    assert result.adaptive_origin_gate.allow_exaptation_like_gains is False
