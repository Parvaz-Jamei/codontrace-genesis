"""Owner measurement fixes. These lock meters. They do not support a hypothesis."""

from __future__ import annotations

import pytest

from codontrace.errors import ConfigurationError
from codontrace.genesis.campaigns.discovery_q_20260928_idea2 import run_idea2_scored_cell
from codontrace.genesis.campaigns.discovery_q_20260928_idea2_engine import (
    run_idea2_engine_cell,
)
from codontrace.genesis.campaigns.discovery_q_20260928_idea4 import _apply_ops_cell
from codontrace.genesis.campaigns.discovery_q_20260928_idea4_engine import (
    aggregate_idea4_engine_rates,
    run_idea4_engine_cell,
)
from codontrace.genesis.campaigns.discovery_q_20260928_idea5 import run_idea5_smoke
from codontrace.genesis.campaigns.discovery_q_20260928_measurement import (
    GENOTYPE_SET_IS_ABUNDANCE,
    GENOTYPE_SET_IS_PRESENCE_ONLY,
    PHASE_ORDER,
    RQ_ACCEPT_THRESHOLD,
    RQ_SYNTHETIC_SCORE,
    assert_record_not_a_discovery,
    genotype_counts,
    process_cycle_complete,
    red_queen_proved_from_score,
    rq_barrier_holds,
    rq_positive_direction_reaches_threshold,
    same_genotype_counts,
    same_genotype_set,
)
from codontrace.life_loop.contact_atp_ledger import build_engine_scaffold_ledger


def test_p1_paired_population_path_diverges() -> None:
    rows = [
        run_idea4_engine_cell(seed=301, ops_cell=cell, t_intervene=2, t_horizon=5, population=4)
        for cell in ("control", "cut_named_scaffold", "cut_matched_random")
    ]
    pres = {row["pre_intervene_pop_digest"] for row in rows}
    posts = {row["ops_cell"]: row["engine_pop_path_digest"] for row in rows}
    assert len(pres) == 1
    assert posts["control"] != posts["cut_named_scaffold"]
    assert posts["cut_named_scaffold"] == posts["cut_matched_random"]
    assert all(row["hypothesis_supported"] is False for row in rows)
    checkpoints = {tuple(row["checkpoint_organism_ids"]) for row in rows}
    assert len(checkpoints) == 1


def test_p2_survival_is_host_census_not_energy_blend() -> None:
    rows = run_idea2_engine_cell(seed=301, cell="baseline", generations=6, population=4)
    for row in rows:
        assert row["estimand"] == "host_lineages_alive_over_founded"
        assert row["score_role"] == "host_lineage_census"
        assert row["hypothesis_test_eligible"] is False
        assert row["parasite_is_independent_population"] is False
        assert row["births_open_new_lineage"] is False
        assert row["hosts_founded"] == 6
        assert 0.0 <= float(row["survival_to_T"]) <= 1.0
        assert isinstance(row["parasite_end"], int)
        pressure = row["pressure_series_tail"]
        parasites = row["parasite_series_tail"]
        assert pressure and all(isinstance(x, float) for x in pressure)
        assert parasites and parasites[-1] == row["parasite_end"]
        assert pressure != parasites
        assert row["hypothesis_supported"] is False
        assert row["red_queen_proved"] is False
    alive = {row["arm"]: row["host_lineages_alive"] for row in rows}
    assert set(alive) == {"gene", "pattern", "causal"}


def test_p2_survival_varies_across_seeds() -> None:
    a = run_idea2_engine_cell(seed=301, cell="baseline")
    b = run_idea2_engine_cell(seed=305, cell="baseline")
    assert {row["arm"]: row["survival_to_T"] for row in a} != {
        row["arm"]: row["survival_to_T"] for row in b
    }


def test_p3_seed_301_matched_cut_is_exact_mirror() -> None:
    from codontrace.genesis.campaigns.discovery_q_20260928_idea4_engine import (
        build_idea4_engine_spec,
    )
    from codontrace.genesis.engine import GenesisEngine
    from codontrace.life_loop.engine_ledger_coupler import EngineCoupledLedgerObserver

    ledger = build_engine_scaffold_ledger(seed=301)
    holder: dict = {"engine": None}

    def _op(led, generation_index: int) -> None:
        del generation_index
        profile = led.scaffold_cut_profile("SCAF-CONTACT-SRC-PATH-V1")
        holder["profile"] = profile
        holder["matched"] = _apply_ops_cell(led, "cut_matched_random")

    observer = EngineCoupledLedgerObserver(
        engine_holder=holder,
        ledger=ledger,
        schedule={1: [_op]},
        feedback_enabled=False,
    )
    spec = build_idea4_engine_spec(seed=301, tick_count=1, population=4)
    engine = GenesisEngine.from_spec(spec, generation_boundary_observers=(observer,))
    holder["engine"] = engine
    engine.run_ticks()
    matched = holder["matched"]
    assert matched["match_exact"] is True
    assert matched["used_nearest_fallback"] is False
    assert matched["cut_edge_ids"] == ["E6", "E7"]
    assert matched["exclude_from_combo_e"] is False
    assert "E5" not in matched["cut_edge_ids"]


def test_p3_unmatched_arm_is_excluded_from_delta() -> None:
    records = [
        {"idea_id": 4, "ops_cell": "control", "t_tilde": 0.25, "recover": False, "match_exact": None, "lineage_branching_real": False, "innovation_observable": False},
        {"idea_id": 4, "ops_cell": "cut_matched_random", "t_tilde": 0.25, "recover": True, "match_exact": False, "lineage_branching_real": False, "innovation_observable": False},
    ]
    summary = aggregate_idea4_engine_rates(records)
    assert summary["abs_delta_p_vs_control"] == {}
    assert summary["inexact_match_cells_excluded"] == ["cut_matched_random"]
    assert summary["hypothesis_supported"] is False
    assert summary["window_law_tested"] is False


def test_p4_background_birth_does_not_open_the_window() -> None:
    rec = run_idea4_engine_cell(
        seed=301, ops_cell="control", t_intervene=1, t_horizon=5, population=4
    )
    assert rec["n_novel_genomes_after_checkpoint"] >= 1
    assert rec["lost_then_regained"] is False
    assert rec["recover"] is False
    assert rec["rare_yield_rebound"] is False
    summary = aggregate_idea4_engine_rates([rec])
    assert summary["window_test_valid"] is False
    assert summary["window_law_tested"] is False
    assert summary["recovery_window_built"] is False
    assert summary["hypothesis_supported"] is False
    assert rec["recovery_window_built"] is False
    assert rec["recovery_window_missing"] == [
        "real_branching_checkpoint",
        "innovation_arising_in_lineage",
        "control_recovery_opportunity",
    ]


def test_p2_cells_are_not_copies() -> None:
    base = run_idea2_engine_cell(seed=301, cell="baseline", generations=12, population=4)
    decoy = run_idea2_engine_cell(seed=301, cell="pi_deception", generations=12, population=4)
    assert {r["arm"]: r["survival_to_T"] for r in base} != {
        r["arm"]: r["survival_to_T"] for r in decoy
    }


def test_p5_injected_accuracies_are_not_a_result() -> None:
    pack = run_idea5_smoke(seed=42)
    assert pack["shortcut_probe_pass"] is False
    assert pack["shortcut_measured_from_behavior"] is False
    assert pack["hypothesis_supported"] is False
    assert pack["engineering_green"] is True


def test_p6_genotype_set_is_presence_and_rq_magnitude_stays_shut() -> None:
    assert GENOTYPE_SET_IS_PRESENCE_ONLY is True
    assert GENOTYPE_SET_IS_ABUNDANCE is False
    assert same_genotype_set(["g1", "g1", "g2"], ["g2", "g1"])
    assert not same_genotype_counts(["g1", "g1", "g2"], ["g2", "g1"])
    assert genotype_counts(["g1", "g1", "g2"]) == {"g1": 2, "g2": 1}
    assert not same_genotype_set(["g1"], ["g1", "g2"])
    assert rq_barrier_holds(RQ_SYNTHETIC_SCORE)
    assert abs(RQ_SYNTHETIC_SCORE) < RQ_ACCEPT_THRESHOLD
    assert rq_barrier_holds(-0.199) is True
    assert rq_barrier_holds(-0.20) is False
    assert rq_barrier_holds(-0.245) is False
    assert rq_barrier_holds(0.19) is True
    assert rq_barrier_holds(0.20) is False
    assert rq_barrier_holds(0.21) is False
    assert rq_positive_direction_reaches_threshold(-0.245) is False
    assert rq_positive_direction_reaches_threshold(0.20) is True
    assert red_queen_proved_from_score(-0.245) is False
    assert red_queen_proved_from_score(0.20) is False
    assert red_queen_proved_from_score(RQ_SYNTHETIC_SCORE) is False
    stub = {
        "pre_rounds": ["a", "b", "c", "d", "e"],
        "post_build": ["p1", "p2"],
        "test_note": "meter only",
        "result_notes": ["r1", "r2"],
    }
    assert process_cycle_complete(stub) is False
    assert process_cycle_complete(
        {
            "pre_rounds": ["a", "a", "a", "a", "a"],
            "post_build": ["p", "q"],
            "test_note": "x",
            "result_notes": ["r", "s"],
        }
    ) is False


def _phase_trail() -> dict:
    """Schema example only. This is not a campaign audit."""

    return {
        "pre_rounds": ["r1", "r2", "r3", "r4", "r5"],
        "post_build": ["post-1", "post-2"],
        "test_note": "meters only",
        "result_notes": ["read-1", "read-2"],
        "search_record": {
            "date": "2026-09-29T01:00:00",
            "references": ["10.1111/jeb.13981"],
        },
        "labor_split": {
            "lead": "measurement",
            "roles": {"measurement": "meters", "records": "trail"},
        },
        "independent_critique": ["critique is not a copy of the five rounds"],
        "phase_order": list(PHASE_ORDER),
        "retry_slots": [
            {"used": False, "date": "2026-09-29T06:00:00"},
            {"used": False, "date": "2026-09-29T07:00:00"},
        ],
        "dated_events": [
            {"date": "2026-09-29T01:00:00", "phase": "search"},
            {"date": "2026-09-29T02:00:00", "phase": "pre_build_rounds"},
            {"date": "2026-09-29T03:00:00", "phase": "build"},
            {"date": "2026-09-29T04:00:00", "phase": "post_build_critiques"},
            {"date": "2026-09-29T05:00:00", "phase": "test"},
            {"date": "2026-09-29T06:00:00", "phase": "result_readings"},
        ],
    }


def test_process_schema_checks_order_and_is_not_an_audit() -> None:
    trail = _phase_trail()
    assert process_cycle_complete(trail) is True
    copied = _phase_trail()
    copied["independent_critique"] = list(copied["pre_rounds"])
    assert process_cycle_complete(copied) is False
    disordered = _phase_trail()
    disordered["dated_events"] = list(reversed(disordered["dated_events"]))
    assert process_cycle_complete(disordered) is False
    missing_search = _phase_trail()
    missing_search["search_record"] = {"date": "2026-09-29T01:00:00", "references": []}
    assert process_cycle_complete(missing_search) is False
    unpadded = _phase_trail()
    unpadded["search_record"] = {
        "date": "2026-9-29",
        "references": ["10.1111/jeb.13981"],
    }
    unpadded["dated_events"][0]["date"] = "2026-9-29"
    assert process_cycle_complete(unpadded) is False


def test_p2_harness_score_is_not_the_hypothesis_test() -> None:
    rows = run_idea2_scored_cell(seed=201, cell="baseline", generations=4)
    assert rows
    for row in rows:
        assert row["score_role"] == "observer_arm_score"
        assert row["estimand"] == "observer_arm_score"
        assert row["hypothesis_test_eligible"] is False
        assert row["hypothesis_supported"] is False
        assert row["red_queen_proved"] is False


def test_p3_four_quantities_match_and_stay_a_planted_mirror() -> None:
    published_atp_301 = 1.8868976316601382
    for seed in (301, 302, 303):
        row = run_idea4_engine_cell(
            seed=seed,
            ops_cell="cut_matched_random",
            t_intervene=2,
            t_horizon=5,
            population=4,
        )
        report = row["match_report"]
        assert report["n_edges_cut_scaffold"] == report["n_edges_cut_matched"] == 2
        assert report["n_edges_cut_equal"] is True
        assert report["degree_sum_scaffold"] == report["degree_sum_matched"]
        assert report["contact_weight_sum_scaffold"] == pytest.approx(
            report["contact_weight_sum_matched"]
        )
        assert report["atp_lost_scaffold"] == pytest.approx(report["atp_lost_matched"])
        assert report["atp_lost_scaffold"] == pytest.approx(
            report["contact_weight_sum_scaffold"]
        )
        assert report["contact_weight_is_atp_yield"] is True
        assert report["scaffold_cut_edge_ids"] == ["E0", "E1"]
        assert report["matched_cut_edge_ids"] == ["E6", "E7"]
        assert row["match_exact"] is True
        assert row["exclude_from_combo_e"] is False
        assert row["match_is_planted_mirror"] is True
        assert row["hypothesis_supported"] is False
        assert row["window_law_tested"] is False
        if seed == 301:
            assert report["atp_lost_scaffold"] == pytest.approx(published_atp_301)


def test_token_penalty_is_not_a_contact_structure_effect() -> None:
    control = run_idea4_engine_cell(
        seed=301, ops_cell="control", t_intervene=2, t_horizon=5, population=4
    )
    named = run_idea4_engine_cell(
        seed=301,
        ops_cell="cut_named_scaffold",
        t_intervene=2,
        t_horizon=5,
        population=4,
    )
    token_move = control["intervention_feedback"]
    scaffold_cut = named["intervention_feedback"]
    assert token_move["token_changed"] == 1.0
    assert token_move["n_edge_changes"] == 0.0
    assert token_move["digest_changed"] == 0.0
    assert token_move["burden_token"] > 0.0
    assert token_move["burden"] == pytest.approx(token_move["burden_token"])
    assert token_move["food_from_edge_count"] == pytest.approx(0.0)
    assert token_move["effect_applied"] is True
    assert control["coupler_affects_engine"] is True
    assert scaffold_cut["n_edge_changes"] > 0.0
    assert scaffold_cut["burden_edge_changes"] == pytest.approx(
        scaffold_cut["n_edge_changes"] * 0.35
    )
    assert scaffold_cut["food_from_edge_count"] == pytest.approx(
        scaffold_cut["n_edge_changes"] * 0.15
    )
    parts = (
        scaffold_cut["burden_lost_energy"]
        + scaffold_cut["burden_edge_changes"]
        + scaffold_cut["burden_digest"]
        + scaffold_cut["burden_token"]
    )
    assert scaffold_cut["burden"] == pytest.approx(parts)
    assert control["engine_pop_path_digest"] != named["engine_pop_path_digest"]
    assert control["contact_structure_effect_identified"] is False
    assert named["contact_structure_effect_identified"] is False
    assert named["knowledge_effect_identified"] is False
    assert control["hypothesis_supported"] is False
    assert named["hypothesis_supported"] is False


def test_records_cannot_promote_scaffold_or_idea2() -> None:
    with pytest.raises(ConfigurationError, match="host-parasite"):
        assert_record_not_a_discovery(
            {
                "idea_id": 2,
                "hypothesis_supported": False,
                "red_queen_proved": False,
            }
        )
    with pytest.raises(ConfigurationError, match="scientific result"):
        assert_record_not_a_discovery(
            {
                "idea_id": 5,
                "hypothesis_supported": False,
                "red_queen_proved": False,
                "scientific_result": True,
            }
        )
    with pytest.raises(ConfigurationError, match="scaffold"):
        assert_record_not_a_discovery(
            {
                "idea_id": 5,
                "hypothesis_supported": False,
                "red_queen_proved": False,
                "data_class": "scaffold",
            }
        )


def test_mirror_yields_follow_ecology_scale() -> None:
    from codontrace.genesis.campaigns.discovery_q_20260928_idea4_engine import (
        build_idea4_engine_spec,
    )
    from codontrace.genesis.engine import GenesisEngine

    ledger = build_engine_scaffold_ledger(seed=11)
    holder = {"engine": None}
    from codontrace.life_loop.engine_ledger_coupler import EngineCoupledLedgerObserver

    observer = EngineCoupledLedgerObserver(
        engine_holder=holder,
        ledger=ledger,
        schedule={},
        feedback_enabled=False,
    )
    spec = build_idea4_engine_spec(seed=11, tick_count=1, population=4)
    engine = GenesisEngine.from_spec(spec, generation_boundary_observers=(observer,))
    holder["engine"] = engine
    engine.run_ticks()
    assert ledger.edges["E6"].atp_yield == ledger.edges["E0"].atp_yield
    assert ledger.edges["E7"].atp_yield == ledger.edges["E1"].atp_yield
