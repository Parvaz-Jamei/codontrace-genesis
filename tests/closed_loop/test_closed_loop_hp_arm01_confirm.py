"""Locked Slowinski confirmatory prereg: constants, refuse soft-pass, ClaimGate."""

from __future__ import annotations

from pathlib import Path

import pytest

from codontrace.claimgate.adapters.host_parasite import assert_claim_allowed
from codontrace.errors import ConfigurationError
from codontrace.genesis.closed_loop_hp_arm01 import (
    CLAIM_CEILING_OBSERVATION,
    HP_ARM01_ESTIMAND,
    SUBSTRATE_LIFE_LOOP,
)
from codontrace.genesis.closed_loop_hp_arm01_confirm import (
    CONFIRM_GENERATIONS,
    CONFIRM_INTRO_SELFING_FREQ,
    CONFIRM_PASS_BAR,
    CONFIRM_SEEDS,
    CONFIRM_VIRULENCE,
    PREREG_RELATIVE_PATH,
    SEALED_P7_SEEDS,
    assert_confirm_seed_policy,
    assert_locked_horizon,
    locked_design_dict,
    prereg_document_path,
    run_slowinski_confirm_campaign,
    slowinski_confirm_design_digest,
    slowinski_confirm_document_digest,
)


def test_prereg_file_exists_and_digests_stable() -> None:
    path = prereg_document_path()
    assert path.is_file()
    assert PREREG_RELATIVE_PATH in str(path).replace("\\", "/")
    text = path.read_text(encoding="utf-8")
    assert "LOCKED before outcomes" in text
    assert "101–108" in text or "101-108" in text
    assert "doi:10.1126/science.1206360" in text
    assert "doi:10.1111/evo.13048" in text
    d1 = slowinski_confirm_design_digest()
    d2 = slowinski_confirm_document_digest()
    assert d1.startswith("hp_arm01_slowinski_design:")
    assert len(d2) == 64
    assert d1 == slowinski_confirm_design_digest()
    assert d2 == slowinski_confirm_document_digest()
    design = locked_design_dict()
    assert design["estimand"] == HP_ARM01_ESTIMAND
    assert design["substrate"] == SUBSTRATE_LIFE_LOOP
    assert design["generations"] == CONFIRM_GENERATIONS
    assert design["virulence"] == CONFIRM_VIRULENCE
    assert design["intro_selfing_freq"] == CONFIRM_INTRO_SELFING_FREQ
    assert design["pass_bar"] == CONFIRM_PASS_BAR
    assert design["two_fold_cost_sex"] is False
    assert design["seeds"] == list(CONFIRM_SEEDS)


def test_seed_policy_refuses_sealed_p7_and_short_horizon() -> None:
    assert_confirm_seed_policy()
    with pytest.raises(ConfigurationError, match="101"):
        assert_confirm_seed_policy([101, 201])
    with pytest.raises(ConfigurationError, match="unique"):
        assert_confirm_seed_policy([201, 201])
    assert_locked_horizon(generations=CONFIRM_GENERATIONS)
    with pytest.raises(ConfigurationError, match="locked at 48"):
        assert_locked_horizon(generations=4)
    assert set(CONFIRM_SEEDS).isdisjoint(set(SEALED_P7_SEEDS))


def test_claimgate_still_refuses_and_engine_clean() -> None:
    with pytest.raises(ConfigurationError, match="blocked"):
        assert_claim_allowed("red_queen_proved")
    repo = Path(__file__).resolve().parents[2]
    engine = (repo / "src" / "codontrace" / "engine.py").read_text(encoding="utf-8").lower()
    for token in ("outcross", "infection", "parasite", "red_queen", "matching_allele"):
        assert token not in engine


def test_confirm_runner_refuses_retuned_virulence_or_mutation() -> None:
    with pytest.raises(ConfigurationError, match="virulence is locked"):
        run_slowinski_confirm_campaign(virulence=8.0)
    with pytest.raises(ConfigurationError, match="parasite_mutation is locked"):
        run_slowinski_confirm_campaign(parasite_mutation=0.7)
    with pytest.raises(ConfigurationError, match="locked at 48"):
        run_slowinski_confirm_campaign(generations=4)


@pytest.mark.slow
def test_confirm_campaign_smoke_one_seed_locked_horizon() -> None:
    """One locked-horizon seed for CI; full 8-seed run is the evidence package."""

    report = run_slowinski_confirm_campaign(seeds=(201,))
    assert report.generations == CONFIRM_GENERATIONS
    assert report.virulence == CONFIRM_VIRULENCE
    assert report.intro_selfing_freq == CONFIRM_INTRO_SELFING_FREQ
    assert report.two_fold_cost_sex_applied is False
    assert report.red_queen_proved is False
    assert report.biological_red_queen_proved is False
    assert report.claim_ceiling == CLAIM_CEILING_OBSERVATION or report.campaign_pass
    assert len(report.seed_results) == 1
    row = report.seed_results[0]
    assert row.confirmatory_horizon_deferred is False
    assert row.life_loop_bound is True
    assert row.clocks_complete is True
    assert abs(row.intro_selfing_freq - 0.2) < 1e-12
    # Honest FAIL is success of the method; do not require PASS.
    if not report.campaign_pass:
        assert report.claim_ceiling == CLAIM_CEILING_OBSERVATION
        assert "fail_recorded_honestly" in report.notes
