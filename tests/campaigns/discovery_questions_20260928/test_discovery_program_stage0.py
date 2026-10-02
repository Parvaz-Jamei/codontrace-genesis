"""Stage-0 checks for the 2026-09-29 discovery program.

A passing instrument fixture is not a population result and not a discovery.
"""

from __future__ import annotations

from pathlib import Path

from codontrace.genesis.campaigns.discovery_program_20260929_stage0 import (
    PROGRAM_TESTS,
    STAGE0_PILOTS,
    classify_time_shift_matrix,
    example_flat_affinity,
    example_histogram_blind,
    example_truncation,
    live_program_decisions,
    rq1_hand_instrument,
    rq3_hand_channel,
    stage0_report,
)
from codontrace.genesis.campaigns.discovery_q_20260928_idea2_engine import (
    run_idea2_engine_cell,
)
from codontrace.genesis.campaigns.discovery_q_20260928_idea4_engine import (
    run_idea4_engine_cell,
)
from codontrace.genesis.campaigns.discovery_q_20260928_measurement import (
    RQ_SYNTHETIC_SCORE,
)

SRC = (
    Path(__file__).resolve().parents[3]
    / "src"
    / "codontrace"
    / "genesis"
    / "campaigns"
    / "discovery_program_20260929_stage0.py"
)


def test_eight_program_tests_are_named_and_not_population_runs() -> None:
    assert len(PROGRAM_TESTS) == 8
    assert STAGE0_PILOTS == ("RQ-1", "RQ-3", "D-2")


def test_hand_examples_match_the_contact_rule_not_the_withdrawn_difference() -> None:
    blind = example_histogram_blind()
    assert blind["affinity_b_against_000011"] == 0.0
    assert blind["pi_a"] == 0.9
    assert blind["pi_b"] == 0.1
    assert blind["difference"] == 0.8
    assert blind["difference"] != 0.7
    assert blind["histogram_difference"] == 0.0
    flat = example_flat_affinity()
    assert flat["pi"] == 0.6
    assert flat["difference"] == 0.0
    trunc = example_truncation()
    assert trunc["intended"] == 0.6
    assert trunc["intended_difference"] == 0.0
    assert trunc["realised_difference"] == 0.1
    assert trunc["pi_realised_b"] <= 0.5


def test_time_shift_fixtures_separate_pattern_from_nulls() -> None:
    pack = rq1_hand_instrument()
    assert pack["instrument_positive_case"] is True
    assert pack["coevolve_label"] == "contemporary_match"
    assert pack["lagged_label"] == "lagged_match"
    assert pack["frozen_label"] == "flat"
    assert pack["directional_label"] == "directional_increase"
    assert pack["shuffled_label"] not in {"contemporary_match", "lagged_match"}
    assert pack["decision"] == "BLOCKED_MEASUREMENT"
    assert pack["hypothesis_supported"] is False
    assert pack["red_queen_proved"] is False
    assert pack["population_run"] is False
    assert classify_time_shift_matrix(
        {host: {ant: 0.4 for ant in ("past", "now", "future")} for host in ("past", "now", "future")}
    ) == "flat"


def test_delayed_channel_hand_matrix_is_not_a_live_claim() -> None:
    pack = rq3_hand_channel()
    assert pack["pi_common"] == 0.9
    assert pack["pi_rare"] == 0.3
    assert pack["s"] == -0.6
    assert pack["frozen_s"] == 0.0
    assert pack["preregistered_direction"] is True
    assert pack["frozen_reaches_floor"] is False
    assert pack["instrument_positive_case"] is True
    assert pack["decision"] == "BLOCKED_MEASUREMENT"
    assert pack["hypothesis_supported"] is False
    assert pack["red_queen_proved"] is False


def test_ready_flags_still_cannot_support_a_claim() -> None:
    idea2 = {
        "parasite_is_genotype_population": True,
        "hypothesis_test_eligible": True,
    }
    idea4 = {
        "checkpoint_fork_complete": True,
        "parent_child_ids_recorded": True,
        "topology_effect_identified": True,
        "endpoint_map_is_contact_physics": True,
    }
    decisions = live_program_decisions(idea2, idea4)
    assert "SUPPORTED_IN_MODEL" not in decisions["decisions"].values()
    assert decisions["hypothesis_supported"] is False
    assert decisions["red_queen_proved"] is False
    assert decisions["decisions"]["RQ-1"] == "INCONCLUSIVE"
    assert decisions["decisions"]["D-2"] == "INCONCLUSIVE"
    assert decisions["decisions"]["D-3"] == "BLOCKED_MEASUREMENT"
    assert decisions["synthetic_barrier_holds"] is True
    assert decisions["synthetic_score"] == RQ_SYNTHETIC_SCORE
    assert decisions["model_claim_inputs_sufficient"] is False


def test_live_short_cells_stay_blocked_and_replay() -> None:
    idea2 = run_idea2_engine_cell(seed=301, cell="baseline", generations=4, population=4)[0]
    idea4 = run_idea4_engine_cell(
        seed=301, ops_cell="control", t_intervene=1, t_horizon=5, population=4
    )
    report = stage0_report(idea2, idea4)
    assert report["population_runs"] == 0
    assert report["n_program_tests"] == 8
    assert report["instrument_positive_case"] is True
    assert report["histogram_difference"] == 0.8
    assert report["hand_digest"] == report["hand_digest_replay"]
    assert report["hypothesis_supported"] is False
    assert report["red_queen_proved"] is False
    assert report["synthetic_score"] == -0.148
    for name in ("RQ-1", "RQ-3", "D-1"):
        assert report["decisions"][name] == "INCONCLUSIVE"
    assert report["decisions"]["D-2"] == "BLOCKED_MEASUREMENT"
    assert idea2["parasite_is_genotype_population"] is True
    assert idea2["hypothesis_test_eligible"] is False
    assert idea2["hypothesis_supported"] is False
    assert idea4["topology_effect_identified"] is False
    assert idea4["endpoint_map_is_contact_physics"] is False
    assert idea4["checkpoint_fork_complete"] is True
    assert idea4["hypothesis_supported"] is False
    births = int(idea4["n_births_after_checkpoint"])
    if births > 0:
        assert idea4["parent_child_ids_recorded"] is True
    else:
        assert idea4["parent_child_ids_recorded"] is False
    text = SRC.read_text(encoding="utf-8")
    assert "import random" not in text
    assert "pickle" not in text
