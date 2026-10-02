"""Pedigree time-order and a checkpoint that stays the captured state.

Witnesses are hand censuses, not a fitted model. A birth whose parent is
missing, is itself, or appears in the same census is not a recorded link.
No birth is not a success. A frozen checkpoint matches its own digest after
the parent continues, and that success does not lift a claim.

Lenski, Ofria, Pennock and Adami 2003, Nature 423:139–144,
doi:10.1038/nature01568.
Ofria and Wilke 2004, Artificial Life 10:191–229,
doi:10.1162/106454604773563612.
Sandve, Nekrutenko, Taylor and Hovig 2013, PLoS Comput Biol 9:e1003285,
doi:10.1371/journal.pcbi.1003285.
Hurlbert 1984, Ecological Monographs 54:187–211, doi:10.2307/1942661.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from codontrace.errors import ConfigurationError
from codontrace.genesis import GenesisEngine, GenesisRuntimeProfile
from codontrace.genesis.campaigns.discovery_q_20260928_idea2_engine import (
    run_idea2_engine_cell,
)
from codontrace.genesis.campaigns.discovery_q_20260928_idea4_engine import (
    _lineage_after_checkpoint,
    run_idea4_engine_cell,
)
from codontrace.life_loop.engine_ledger_coupler import _population_census

SOURCE = Path(
    "src/codontrace/genesis/campaigns/discovery_q_20260928_idea4_engine.py"
)
DOIS = (
    "doi:10.1038/nature01568",
    "doi:10.1162/106454604773563612",
    "doi:10.1371/journal.pcbi.1003285",
    "doi:10.2307/1942661",
)


def _row(organism_id: str, genome: str, parent_id: str = "") -> dict[str, str]:
    return {"id": organism_id, "genome": genome, "parent_id": parent_id}


def test_citations_stay_on_the_implementation() -> None:
    text = SOURCE.read_text(encoding="utf-8")
    for doi in DOIS:
        assert doi in text
    assert "hypothesis_supported=False" in text
    assert "red_queen_proved=False" in text


def test_parent_must_already_exist_and_absence_is_not_success() -> None:
    linked = [
        [_row("A", "gA")],
        [_row("A", "gA")],
        [_row("A", "gA"), _row("B", "gB", "A")],
    ]
    ok = _lineage_after_checkpoint(linked, t_intervene=2)
    assert ok["n_births_after_checkpoint"] == 1
    assert ok["parent_child_ids_recorded"] is True
    assert ok["innovation_observable"] is True

    dead_parent = [
        [_row("A", "gA"), _row("D", "gD")],
        [_row("A", "gA")],
        [_row("A", "gA"), _row("B", "gB", "D")],
    ]
    assert _lineage_after_checkpoint(dead_parent, t_intervene=2)["parent_child_ids_recorded"] is True

    same_frame = [
        [_row("A", "gA")],
        [_row("A", "gA")],
        [_row("A", "gA"), _row("C", "gC"), _row("B", "gB", "C")],
    ]
    refused = _lineage_after_checkpoint(same_frame, t_intervene=2)
    assert refused["n_births_after_checkpoint"] == 2
    assert refused["parent_child_ids_recorded"] is False

    for parent in ("", "B"):
        orphan = [
            [_row("A", "gA")],
            [_row("A", "gA")],
            [_row("A", "gA"), _row("B", "gB", parent)],
        ]
        assert _lineage_after_checkpoint(orphan, t_intervene=2)["parent_child_ids_recorded"] is False

    quiet = [[_row("A", "gA")], [_row("A", "gA")], [_row("A", "gA")]]
    none = _lineage_after_checkpoint(quiet, t_intervene=2)
    assert none["n_births_after_checkpoint"] == 0
    assert none["parent_child_ids_recorded"] is False
    assert none["lineage_branching_real"] is False


def test_a_broken_parent_link_does_not_erase_a_regained_genome() -> None:
    history = [
        [_row("A", "gA")],
        [_row("A", "gA")],
        [_row("Z", "gZ")],
        [_row("A", "gA"), _row("B", "gB", "")],
    ]
    report = _lineage_after_checkpoint(history, t_intervene=2)
    assert report["lost_then_regained"] is True
    assert report["n_regained_genomes"] == 1
    assert report["parent_child_ids_recorded"] is False


def test_live_census_matches_the_lineage_record() -> None:
    spec = GenesisRuntimeProfile.life_loop_world(seed=7, tick_count=8, population=6)
    engine = GenesisEngine.from_spec(spec)
    engine.run_ticks()
    rows = _population_census(engine)
    assert rows
    parents = {
        str(record.organism_id): "" if record.parent_id is None else str(record.parent_id)
        for record in engine.runner.population.lineage
    }
    for row in rows:
        assert set(row) == {"id", "genome", "parent_id"}
        assert row["parent_id"] == parents.get(row["id"], "")
        assert row["parent_id"] != row["id"]


def test_idea4_freeze_does_not_promote_a_claim_or_split_one_run() -> None:
    rows = [
        run_idea4_engine_cell(seed=seed, ops_cell="control", t_intervene=2, t_horizon=5, population=4)
        for seed in (301, 302)
    ]
    assert rows[0]["run_id"] != rows[1]["run_id"]
    for row in rows:
        assert row["n_unit"] == "run"
        assert row["checkpoint_fork_complete"] is True
        assert row["hypothesis_supported"] is False
        assert row["red_queen_proved"] is False
        assert row["topology_effect_identified"] is False
        assert row["endpoint_map_is_contact_physics"] is False
        assert row["lineage_recovery_established"] is False
        births = int(row["n_births_after_checkpoint"])
        assert row["parent_child_ids_recorded"] is (births > 0)
        assert int(births) >= 0
        assert row["n_unit"] == "run"


def test_idea2_roster_is_a_population_and_not_a_claim() -> None:
    rows = run_idea2_engine_cell(seed=301, cell="baseline", generations=4, population=4)
    assert rows
    for row in rows:
        assert row["parasite_is_genotype_population"] is True
        assert row["parasite_is_independent_population"] is True
        assert row["hypothesis_test_eligible"] is False
        assert row["hypothesis_supported"] is False
        assert row["red_queen_proved"] is False
        assert len(row["parasite_ids"]) == len(set(row["parasite_ids"]))


def test_blank_ids_and_a_later_parent_cannot_pass() -> None:
    blank = [
        [_row("A", "gA")],
        [_row("A", "gA")],
        [_row("A", "gA"), _row("", "gB", "A"), _row("  B", "gC", "A")],
    ]
    hidden = _lineage_after_checkpoint(blank, t_intervene=2)
    assert hidden["n_births_after_checkpoint"] == 2
    assert hidden["parent_child_ids_recorded"] is False

    padded_parent = [
        [_row("A", "gA")],
        [_row("A", "gA")],
        [_row("A", "gA"), _row("B", "gB", " A")],
    ]
    assert (
        _lineage_after_checkpoint(padded_parent, t_intervene=2)["parent_child_ids_recorded"]
        is False
    )

    future_parent = [
        [_row("A", "gA")],
        [_row("A", "gA")],
        [_row("A", "gA"), _row("B", "gB", "C")],
        [_row("A", "gA"), _row("B", "gB", "C"), _row("C", "gC", "A")],
    ]
    late = _lineage_after_checkpoint(future_parent, t_intervene=2)
    assert late["n_births_after_checkpoint"] == 2
    assert late["parent_child_ids_recorded"] is False


def test_a_boolean_horizon_is_refused() -> None:
    with pytest.raises(ConfigurationError, match="boolean"):
        run_idea4_engine_cell(
            seed=301, ops_cell="control", t_intervene=True, t_horizon=5, population=4
        )
