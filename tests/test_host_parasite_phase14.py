"""Phase 14: mode-completeness hardening (transmission contrast + menu)."""

from __future__ import annotations

import pytest

from codontrace.claimgate import audit_bundle
from codontrace.claimgate.adapters.host_parasite import (
    DECLARED_INTERVENTION_KINDS,
    attach_transmission_mode_contrast,
    bundle_from_host_parasite_cou,
)
from codontrace.claimgate.adapters.host_parasite_prereg import (
    attach_host_parasite_preregistration,
    host_parasite_preregistration,
)
from codontrace.errors import ConfigurationError
from codontrace.genesis.host_parasite_hgt import ARMS as HGT_ARMS
from codontrace.genesis.host_parasite_mode_contrast import (
    BRAINSTORMED_KEEP_MODES,
    run_transmission_mode_contrast,
)
from codontrace.genesis.host_parasite_zaman import ZAMAN_ARMS


def test_noise_transfer_registered_on_declared_menu() -> None:
    assert "hgt_analogue_noise_transfer" in DECLARED_INTERVENTION_KINDS
    assert "hgt_analogue_noise_transfer" in HGT_ARMS


def test_transmission_mode_contrast_mixed_blends_and_digests_distinct() -> None:
    result = run_transmission_mode_contrast(
        seeds=(1, 2),
        request_claim_ceiling="candidate_evidence",
    )
    assert result.modes_are_distinct is True
    assert result.mixed_blends_horizontal_and_vertical is True
    assert result.red_queen_proved is False
    assert result.virulence_optimized_for_humans is False
    assert result.major_transition_proved is False
    payload = result.to_dict()
    assert len(set(payload["mode_digests"].values())) == 3
    by_mode = {item.mode: item for item in result.arm_outcomes if item.seed == 1}
    assert by_mode["mixed"].blend_observed is True
    assert by_mode["mixed"].horizontal_injected is True
    assert by_mode["mixed"].vertical_transmitted is True
    assert by_mode["horizontal"].vertical_transmitted is False
    assert by_mode["vertical"].horizontal_injected is False
    assert by_mode["vertical"].vertical_transmitted is True


def test_transmission_mode_contrast_deterministic() -> None:
    a = run_transmission_mode_contrast(seeds=(3, 4))
    b = run_transmission_mode_contrast(seeds=(3, 4))
    assert a.to_dict()["campaign_digest"] == b.to_dict()["campaign_digest"]
    with pytest.raises(ConfigurationError, match="candidate_evidence|request_claim_ceiling"):
        run_transmission_mode_contrast(
            seeds=(1,),
            request_claim_ceiling="mechanism_support",
        )


def test_attach_mode_contrast_requires_prereg_and_keeps_ladder() -> None:
    contrast = run_transmission_mode_contrast(
        seeds=(5,),
        request_claim_ceiling="candidate_evidence",
    )
    bundle = bundle_from_host_parasite_cou(
        question_of_interest="Do horizontal, vertical, and mixed modes differ?",
        context_of_use="Digital transmission-mode contrast only.",
        model_influence=1,
        decision_consequence=1,
        treatment_scores=(0.2,),
        control_scores=(1.0,),
    )
    with pytest.raises(ConfigurationError, match="preregistration"):
        attach_transmission_mode_contrast(bundle, contrast)
    prereg = host_parasite_preregistration(
        question_of_interest="Do horizontal, vertical, and mixed modes differ?",
        context_of_use="Digital transmission-mode contrast only.",
        arms=("horizontal", "vertical", "mixed"),
        success_metrics=("mode_digest", "blend_observed"),
    )
    ready = attach_host_parasite_preregistration(bundle, prereg)
    before = audit_bundle(ready).achieved_level
    attached = attach_transmission_mode_contrast(ready, contrast)
    record = attached.extra["transmission_mode_contrast"]
    assert record["modes_are_distinct"] is True
    assert record["mixed_blends_horizontal_and_vertical"] is True
    assert record["virulence_optimized_for_humans"] is False
    assert audit_bundle(attached).achieved_level == before
    with pytest.raises(ConfigurationError, match="already attached"):
        attach_transmission_mode_contrast(attached, contrast)


def test_brainstormed_keep_modes_registry_covers_wave_modes() -> None:
    required = {
        "horizontal",
        "vertical",
        "mixed",
        "well_mixed",
        "local_neighborhood",
        "hgt_analogue_segment_copy",
        "hgt_analogue_noise_transfer",
        "intracellular_seat_constraint",
        "free_living_horizontal_inject",
        "freeze_parasites",
        "replay_parasite_schedule",
        "reciprocal_coevolution",
    }
    assert required <= set(BRAINSTORMED_KEEP_MODES)
    # Zaman three arms still present as shipped surface.
    assert len(ZAMAN_ARMS) >= 3
