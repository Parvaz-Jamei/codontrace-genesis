"""Three-arm frequency clocks: ecology arms, clocks, ClaimGate refuse.

Anchored to sealed confirmatory 101–108 honest FAIL at tip 610f46f and to
Pearl-pair taxonomy on closed-loop/pearl-pair-spc. Does not promote
red_queen_proved. Does not loosen ClaimGate.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from codontrace.claimgate.adapters.host_parasite import assert_claim_allowed
from codontrace.errors import ConfigurationError
from codontrace.genesis.closed_loop_hp_arm01 import (
    ARM_AVIRULENT,
    ARM_COPASSAGED,
    ARM_FIXED,
    ARM_TO_PASSAGE,
    CLAIM_CEILING_CANDIDATE,
    CLAIM_CEILING_OBSERVATION,
    REQUIRED_CLOCKS,
    assert_ecology_arm_taxonomy,
    ecology_arm_to_passage,
    handling_ablation_digests,
    max_allowed_claim_ceiling,
    passage_to_ecology_arm,
    required_clocks_complete,
    run_three_arm_frequency_campaign,
    slowinski_selfing_invasion_contrast,
)
from codontrace.genesis.closed_loop_pearl_spc import (
    PASSAGE_ABSENT,
    PASSAGE_COEVOLVE,
    PASSAGE_COSTLESS,
    PASSAGE_FROZEN,
)
from codontrace.genesis.host_parasite_env import HostParasiteEnv

_REPO = Path(__file__).resolve().parents[2]


def test_claimgate_still_refuses_red_queen_proved() -> None:
    with pytest.raises(ConfigurationError, match="blocked"):
        assert_claim_allowed("red_queen_proved")
    report = run_three_arm_frequency_campaign(
        virulence=8.0, generations=4, seed=101
    )
    assert report.red_queen_proved is False
    assert report.biological_red_queen_proved is False
    assert report.claim_ceiling == CLAIM_CEILING_OBSERVATION


def test_ecology_arm_taxonomy_maps_without_costless_alias() -> None:
    meanings = assert_ecology_arm_taxonomy()
    assert meanings[ARM_AVIRULENT] != meanings[ARM_FIXED]
    assert meanings[ARM_FIXED] != meanings[ARM_COPASSAGED]
    assert ecology_arm_to_passage(ARM_AVIRULENT) == PASSAGE_ABSENT
    assert ecology_arm_to_passage(ARM_FIXED) == PASSAGE_FROZEN
    assert ecology_arm_to_passage(ARM_COPASSAGED) == PASSAGE_COEVOLVE
    assert PASSAGE_COSTLESS not in ARM_TO_PASSAGE.values()
    assert passage_to_ecology_arm(PASSAGE_ABSENT) == ARM_AVIRULENT
    with pytest.raises(ConfigurationError, match="costless|zero_debit"):
        ecology_arm_to_passage("costless")
    with pytest.raises(ConfigurationError, match="Pearl debit knockout"):
        passage_to_ecology_arm(PASSAGE_COSTLESS)
    with pytest.raises(ConfigurationError, match="aliases are forbidden"):
        assert_ecology_arm_taxonomy(refuse_aliases=False)


def test_frequency_clocks_are_required_and_digest_backed() -> None:
    report = run_three_arm_frequency_campaign(
        virulence=8.0, generations=4, seed=101
    )
    assert report.clocks_complete is True
    assert required_clocks_complete(report.clocks) is True
    assert set(report.clocks) == set(REQUIRED_CLOCKS)
    for name, clock in report.clocks.items():
        assert clock.name == name
        assert len(clock.digest) == 64
        assert clock.series
        assert clock.to_dict()["writes_red_queen_flag"] is False
    assert report.treatment_control_present is True
    assert report.max_allowed_ceiling == CLAIM_CEILING_CANDIDATE
    # Contrast may honestly fail on a short seed; ceiling stays observational
    # unless the Slowinski accept path actually holds.
    if not report.slowinski_contrast_holds:
        assert report.claim_ceiling == CLAIM_CEILING_OBSERVATION
    assert report.digest
    assert len(report.digest) == 64


def test_slowinski_contrast_fail_closed_and_honest() -> None:
    assert (
        slowinski_selfing_invasion_contrast(
            selfing_freq_avirulent=None,
            selfing_freq_fixed=0.8,
            selfing_freq_copassaged=0.1,
        )
        is False
    )
    assert (
        slowinski_selfing_invasion_contrast(
            selfing_freq_avirulent=0.9,
            selfing_freq_fixed=0.8,
            selfing_freq_copassaged=0.1,
        )
        is True
    )
    assert (
        slowinski_selfing_invasion_contrast(
            selfing_freq_avirulent=0.2,
            selfing_freq_fixed=0.2,
            selfing_freq_copassaged=0.5,
        )
        is False
    )
    assert max_allowed_claim_ceiling(
        clocks_complete=False, treatment_control_present=True
    ) == CLAIM_CEILING_OBSERVATION
    assert max_allowed_claim_ceiling(
        clocks_complete=True, treatment_control_present=False
    ) == CLAIM_CEILING_OBSERVATION
    assert max_allowed_claim_ceiling(
        clocks_complete=True, treatment_control_present=True
    ) == CLAIM_CEILING_CANDIDATE


def test_pearl_measurement_requires_clocks_and_stays_non_promoting() -> None:
    report = run_three_arm_frequency_campaign(
        virulence=8.0,
        generations=4,
        seed=101,
        attach_pearl_measurement=True,
    )
    assert report.pearl_measurement_attached is True
    assert report.red_queen_proved is False
    assert report.biological_red_queen_proved is False
    assert report.clocks_complete is True


def test_handling_time_ablation_digest_pair() -> None:
    off = HostParasiteEnv(steal_fraction=0.8, handling_time=0.0)
    on = HostParasiteEnv(steal_fraction=0.8, handling_time=2.0)
    for env in (off, on):
        env.add_host("H0", ["not", "nand"])
        env.add_host("H1", ["not", "nand"])
    # First inject succeeds on both.
    a0 = off.try_horizontal_inject(
        host_id="H0", parasite_id="P0", parasite_tasks=["not"], payload=(1,)
    )
    a1 = on.try_horizontal_inject(
        host_id="H0", parasite_id="P0", parasite_tasks=["not"], payload=(1,)
    )
    assert a0.injected is True
    assert a1.injected is True
    # Second inject: off can take H1; on is handling-busy.
    b0 = off.try_horizontal_inject(
        host_id="H1", parasite_id="P1", parasite_tasks=["not"], payload=(2,)
    )
    b1 = on.try_horizontal_inject(
        host_id="H1", parasite_id="P1", parasite_tasks=["not"], payload=(2,)
    )
    assert b0.injected is True
    assert b1.injected is False
    assert b1.reason == "handling_busy"
    # Steal magnitude also differs under handling_time.
    assert off.host_retained_cpu("H0") != on.host_retained_cpu("H0")
    pair = handling_ablation_digests(
        handling_off=off.snapshot(), handling_on=on.snapshot()
    )
    assert pair["digests_distinct"] is True
    assert pair["red_queen_proved"] is False
    assert pair["claim_ceiling"] == CLAIM_CEILING_OBSERVATION
    with pytest.raises(ConfigurationError, match="handling_time"):
        HostParasiteEnv(handling_time=-0.1)


def test_engine_has_no_infection_tokens() -> None:
    engine = (_REPO / "src" / "codontrace" / "engine.py").read_text(encoding="utf-8").lower()
    for token in ("outcross", "infection", "parasite", "red_queen", "matching_allele"):
        assert token not in engine
