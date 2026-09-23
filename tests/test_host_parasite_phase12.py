"""Phase 12: HGT-analogue + intracellular vs free-living pack."""

from __future__ import annotations

import pytest

from codontrace.claimgate import audit_bundle
from codontrace.claimgate.adapters.host_parasite import (
    DECLARED_INTERVENTION_KINDS,
    attach_hgt_compartment_campaign,
    bundle_from_host_parasite_cou,
)
from codontrace.claimgate.adapters.host_parasite_prereg import (
    attach_host_parasite_preregistration,
    host_parasite_preregistration,
)
from codontrace.errors import ConfigurationError
from codontrace.genesis.host_parasite_hgt import (
    HYPOTHESIS,
    run_hgt_compartment_campaign,
)


def test_hgt_kinds_registered_on_menu() -> None:
    assert "hgt_analogue_segment_copy" in DECLARED_INTERVENTION_KINDS
    assert "intracellular_seat_constraint" in DECLARED_INTERVENTION_KINDS
    assert "free_living_horizontal_inject" in DECLARED_INTERVENTION_KINDS


def test_hgt_dual_null_can_fail_any_transfer_claim() -> None:
    result = run_hgt_compartment_campaign(
        seeds=(1, 2),
        request_claim_ceiling="candidate_evidence",
    )
    assert result.hypothesis == HYPOTHESIS
    assert result.hypothesis_supported is False
    assert (
        "noise_transfer" in result.failure_reason
        or "intracellular_seat" in result.failure_reason
    )
    assert result.red_queen_proved is False
    assert result.cou_labels == ("microbe", "bacterium_analogue")
    by_arm: dict[str, list[float]] = {}
    seated: dict[str, bool] = {}
    for item in result.arm_outcomes:
        by_arm.setdefault(item.arm, []).append(item.diversity_delta)
        seated[item.arm] = item.seated
        body = item.to_dict()
        assert body["wet_hgt"] is False
        assert body["conjugation"] is False
        assert body["crispr_spacer_acquisition"] is False
        assert item.transfer_digest
    assert (
        sum(by_arm["hgt_analogue_segment_copy"]) / len(by_arm["hgt_analogue_segment_copy"])
        > 0
    )
    assert (
        sum(by_arm["hgt_analogue_noise_transfer"])
        / len(by_arm["hgt_analogue_noise_transfer"])
        <= 0
    )
    assert seated["intracellular_seat_constraint"] is True
    assert seated["free_living_horizontal_inject"] is False
    payload = result.to_dict()
    assert payload["wet_hgt_claimed"] is False
    assert payload["crispr_identity_proved"] is False
    assert payload["domain_profile"] == "host_parasite"
    assert len(set(payload["arm_digests"].values())) == 4
    transfers = {item.arm: item.transfer_digest for item in result.arm_outcomes}
    assert len(set(transfers.values())) == 4
    assert transfers["hgt_analogue_segment_copy"] != transfers["hgt_analogue_noise_transfer"]


def test_hgt_deterministic_and_refuses_high_ceiling() -> None:
    a = run_hgt_compartment_campaign(seeds=(3, 4))
    b = run_hgt_compartment_campaign(seeds=(3, 4))
    assert a.to_dict()["campaign_digest"] == b.to_dict()["campaign_digest"]
    with pytest.raises(ConfigurationError, match="candidate_evidence"):
        run_hgt_compartment_campaign(
            seeds=(1,),
            request_claim_ceiling="mechanism_support",
        )


def test_attach_hgt_requires_prereg_and_refuses_wet_claims() -> None:
    campaign = run_hgt_compartment_campaign(seeds=(5,))
    bundle = bundle_from_host_parasite_cou(
        question_of_interest="Does structured segment copy differ from noise transfer?",
        context_of_use="Digital HGT-analogue only. Wet HGT unclaimed.",
        model_influence=1,
        decision_consequence=1,
        treatment_scores=(0.2,),
        control_scores=(1.0,),
    )
    with pytest.raises(ConfigurationError, match="preregistration"):
        attach_hgt_compartment_campaign(bundle, campaign)
    prereg = host_parasite_preregistration(
        question_of_interest="Does structured segment copy differ from noise transfer?",
        context_of_use="Digital HGT-analogue only. Wet HGT unclaimed.",
        arms=(
            "hgt_analogue_segment_copy",
            "hgt_analogue_noise_transfer",
            "intracellular_seat_constraint",
            "free_living_horizontal_inject",
        ),
        success_metrics=("transfer_digest", "diversity_delta"),
    )
    ready = attach_host_parasite_preregistration(bundle, prereg)
    before = audit_bundle(ready).achieved_level
    attached = attach_hgt_compartment_campaign(ready, campaign)
    assert attached.extra["hgt_compartment_campaign"]["wet_hgt_claimed"] is False
    assert attached.extra["hgt_compartment_campaign"]["crispr_identity_proved"] is False
    assert attached.extra["hgt_compartment_campaign"]["preregistration_digest"] == str(
        prereg.to_dict()["digest"]
    )
    assert audit_bundle(attached).achieved_level == before
    with pytest.raises(ConfigurationError, match="already attached"):
        attach_hgt_compartment_campaign(attached, campaign)
