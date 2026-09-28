"""Owner measurement fixes. These lock meters. They do not support a hypothesis."""

from __future__ import annotations

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
    RQ_ACCEPT_THRESHOLD,
    RQ_SYNTHETIC_SCORE,
    process_cycle_complete,
    rq_barrier_holds,
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
        assert row["hosts_founded"] == 6
        assert 0.0 <= float(row["survival_to_T"]) <= 1.0
        assert isinstance(row["parasite_end"], int)
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
    assert summary["hypothesis_supported"] is False


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


def test_p6_genotype_set_ignores_class_size_and_rq_stays_shut() -> None:
    assert same_genotype_set(["g1", "g1", "g2"], ["g2", "g1"])
    assert not same_genotype_set(["g1"], ["g1", "g2"])
    assert rq_barrier_holds(RQ_SYNTHETIC_SCORE)
    assert RQ_SYNTHETIC_SCORE < RQ_ACCEPT_THRESHOLD
    assert process_cycle_complete(
        {
            "pre_rounds": ["a", "b", "c", "d", "e"],
            "post_build": ["p1", "p2"],
            "test_note": "meter only",
            "result_notes": ["r1", "r2"],
        }
    )
    assert process_cycle_complete({"pre_rounds": ["a", "a", "a", "a", "a"], "post_build": ["p", "q"], "test_note": "x", "result_notes": ["r", "s"]}) is False


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
