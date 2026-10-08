"""Phase 1 fixtures for R06 and R10 by Tester 1."""

import json
from pathlib import Path

from codontrace.console import runs
from codontrace.genesis.organism import GenesisOrganism
from codontrace.genesis.population import (
    LineageRecord,
    create_population_with_unique_ids,
)


def test_r06_lineage_id_collision_connects_correct_history():
    """R06: Lineage after ID collision resolution must connect to the renamed ID.
    
    If twin A and A#1 are created, the LineageRecord for A#1 should be intact,
    and any child of A#1 should correctly point to A#1, not A.
    """
    # Simulate a generation where two identical organisms are born.
    # They will have the same hash ID initially.
    org1 = GenesisOrganism.from_bits("orgA", "111000", position=(0, 0))
    org2 = GenesisOrganism.from_bits("orgA", "111000", position=(0, 1))
    
    # Original lineage records as they would be generated before collision resolution
    lin1 = LineageRecord(
        organism_id="orgA",
        parent_id="parentX",
        generation=1,
        genome_digest="hashA",
        mutation_count=0,
        birth_tick=1,
        death_tick=None,
        reproduction_event_id=None,
        recombination_start_index=0,
        recombination_end_index=0,
    )
    lin2 = LineageRecord(
        organism_id="orgA",
        parent_id="parentY",
        generation=1,
        genome_digest="hashA",
        mutation_count=0,
        birth_tick=1,
        death_tick=None,
        reproduction_event_id=None,
        recombination_start_index=0,
        recombination_end_index=0,
    )
    
    # Resolve collisions
    state = create_population_with_unique_ids(
        generation=1,
        tick=1,
        organisms=(org1, org2),
        lineage=(lin1, lin2),
        fitness=(),
        birth_chamber=None, # type: ignore
    )
    
    # Check that the organisms are renamed correctly
    assert len(state.organisms) == 2
    ids = [o.id for o in state.organisms]
    assert "orgA" in ids
    assert "orgA#1" in ids
    
    # Check that the lineage records point to the correctly renamed organism IDs
    lin_ids = {r.organism_id for r in state.lineage}
    assert "orgA" in lin_ids
    assert "orgA#1" in lin_ids
    
    # Ensure they preserved their distinct parent histories
    lin_dict = {r.organism_id: r for r in state.lineage}
    assert lin_dict["orgA"].parent_ids == ("parentX",)
    assert lin_dict["orgA#1"].parent_ids == ("parentY",)


def test_r10_panel_execution_form_mismatch_with_actual_command(tmp_path: Path, monkeypatch):
    """R10: The execution parameters requested by the panel are not faithfully applied to the command.
    
    The UI form allows selecting `cores` to pin CPU affinity and `track`, but `launch_simulation_run` 
    discards them and does not pass them to `rq_full_engine_parallel.py`.
    """
    runs_dir = tmp_path / "runs"
    runs_dir.mkdir()
    monkeypatch.setenv("CODONTRACE_RUNS_DIR", str(runs_dir))
    
    params = {
        "generations": 200,
        "workers": 4,
        "cores": [0, 1, 2, 3],
        "track": "contracts",
        "seeds": [42],
        "budget": 3600,
        "title": "Test Run",
    }
    
    res = runs.launch_simulation_run(params)
    # Ensure it was successful in creating the run
    assert res.get("ok") is True, res
    run_id = res["runId"]
    
    manifest_file = runs_dir / run_id / "run_manifest.json"
    manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
    cmd = manifest["command"]
    
    # The command should contain the expected parameters
    cmd_str = " ".join(cmd)
    assert "--generations 200" in cmd_str
    assert "--workers 4" in cmd_str
    assert "--max-seconds 3600" in cmd_str
    
    # R10 FIX VERIFICATION: The cores and track parameters are faithfully passed
    assert "contracts" in cmd_str
    assert manifest["params"]["cores"] == [0, 1, 2, 3]
    assert manifest["params"]["track"] == "contracts"
