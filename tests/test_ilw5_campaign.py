"""ILW-5 campaign design harness + confirmatory unlock smoke (fast)."""

from __future__ import annotations

import pytest

from codontrace.genesis.ilw.campaign import (
    build_ablation_cells,
    build_interaction_screening_cells,
    build_s4_scale_cells,
    enumerate_campaign_design,
)
from codontrace.genesis.ilw.prereg import (
    CLAIM_CEILING,
    CONFIRMATORY_HELD_OUT_SEEDS,
    EDGE_KNOCKOUTS,
    INTERACTIONS_TO_ESTIMATE,
    PilotGateError,
    PilotGateStatus,
    PilotHarness,
    SCIENTIFIC_NAME,
)


def test_enumerate_design_no_invented_outcomes():
    design = enumerate_campaign_design()
    assert design["campaign_outcomes_invented"] is False
    assert design["claim_ceiling"] == CLAIM_CEILING == "runtime_observation"
    assert design["scientific_name"] == SCIENTIFIC_NAME
    assert design["cell_counts"]["ablation_per_seed"] == 1 + len(EDGE_KNOCKOUTS)
    assert design["cell_counts"]["interaction_per_seed"] == len(INTERACTIONS_TO_ESTIMATE)
    assert design["cell_counts"]["s4_per_seed"] >= 3 * 3 * 3  # widths × horizons × pop
    assert "Colab" in design["remaining_for_colab"] or "colab" in design["remaining_for_colab"].lower()


def test_ablation_and_interaction_require_held_out_seeds():
    with pytest.raises(PilotGateError):
        build_ablation_cells(seed=3100)
    cells = build_ablation_cells(seed=4100)
    assert cells[0].kind == "baseline"
    assert cells[0].knockouts == ()
    assert any(c.knockouts == ("mutation_off",) for c in cells)
    interactions = build_interaction_screening_cells(seed=4101)
    assert len(interactions) == len(INTERACTIONS_TO_ESTIMATE)
    assert all(c.kind == "interaction" for c in interactions)
    assert all(len(c.knockouts) == 2 for c in interactions)


def test_s4_cells_square_grid_enumeration():
    cells = build_s4_scale_cells(seed=4100, widths=(32, 64), horizons=(128,), pop_caps=(64,))
    assert len(cells) == 2
    assert all(c.scale_label == "S4" for c in cells)
    assert {c.width for c in cells} == {32, 64}


def test_confirmatory_harness_gate():
    locked = PilotHarness()
    with pytest.raises(PilotGateError):
        locked.assert_seed_allowed(4100, role="confirmatory")
    unlocked = PilotHarness(
        gates=PilotGateStatus(
            replay_ok=True,
            conservation_ok=True,
            edge_coverage_ok=True,
            pom_patterns_recorded=True,
            no_claim_promotion=True,
            claim_ceiling_ok=True,
        )
    )
    unlocked.assert_seed_allowed(CONFIRMATORY_HELD_OUT_SEEDS[0], role="confirmatory")


def test_select_partial_campaign_cells_default_subset():
    from codontrace.genesis.ilw.campaign import select_partial_campaign_cells

    cells = select_partial_campaign_cells()
    kinds = {c.kind for c in cells}
    assert kinds == {"baseline", "ablation", "interaction", "scale_s4"}
    # 8 ablation arms × 2 seeds + 4 interactions + 2 S4 slice cells
    assert len(cells) == 8 * 2 + 4 + 2
    assert all(c.seed in CONFIRMATORY_HELD_OUT_SEEDS for c in cells)
    assert {c.seed for c in cells if c.kind in {"baseline", "ablation"}} == {4100, 4101}
    assert all(c.seed == 4100 for c in cells if c.kind == "interaction")
    assert all(c.scale_label == "S4" for c in cells if c.kind == "scale_s4")


def test_partial_payload_honesty_flags_without_execution(tmp_path):
    """Partial runner with max_cells=0 writes design-only honest artifact."""
    from codontrace.genesis.ilw.campaign import run_ilw5_partial
    from codontrace.genesis.ilw.prereg import PilotGateStatus, PilotHarness

    unlocked = PilotHarness(
        gates=PilotGateStatus(
            replay_ok=True,
            conservation_ok=True,
            edge_coverage_ok=True,
            pom_patterns_recorded=True,
            no_claim_promotion=True,
            claim_ceiling_ok=True,
        )
    )
    art = tmp_path / "ilw5_campaign_partial.json"
    payload = run_ilw5_partial(
        harness=unlocked,
        max_cells=0,
        write_artifact=True,
        artifact_path=art,
        resume=False,
    )
    assert payload["campaign_outcomes_invented"] is False
    assert payload["intelligence_claimed"] is False
    assert payload["cce_claimed"] is False
    assert payload["claim_ceiling"] == "runtime_observation"
    assert payload["executed_count"] == 0
    assert payload["planned_count"] == 8 * 2 + 4 + 2
    assert payload["enumerated_total"] == 312
    assert art.is_file()
