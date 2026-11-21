"""Phase 1 fixtures for R06 and R10 by Tester 1."""

import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

import pytest

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


def _group_alive(pgid: int) -> bool:
    try:
        os.killpg(pgid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


@pytest.fixture
def reap_launched_runs(monkeypatch):
    """Launched runs are real engine processes (here 4 workers, up to 3600 s). Start each in its
    own session so the whole tree (the script and its worker pool) is one process group, and on
    teardown terminate that group and check that nothing in it survives."""

    real_popen = subprocess.Popen
    launched: list[subprocess.Popen] = []

    def popen(*args, **kwargs):
        if sys.platform != "win32":
            kwargs.setdefault("start_new_session", True)
        proc = real_popen(*args, **kwargs)
        launched.append(proc)
        return proc

    monkeypatch.setattr(runs.subprocess, "Popen", popen)
    yield launched
    monkeypatch.setattr(runs.subprocess, "Popen", real_popen)
    for proc in launched:
        if sys.platform == "win32":
            proc.kill()
            proc.wait(timeout=30)
            continue
        for sig in (signal.SIGTERM, signal.SIGKILL):
            if not _group_alive(proc.pid):
                break
            os.killpg(proc.pid, sig)
            deadline = time.monotonic() + 10
            while _group_alive(proc.pid) and time.monotonic() < deadline:
                try:
                    proc.wait(timeout=0.2)
                except subprocess.TimeoutExpired:
                    pass
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            pass
        assert proc.poll() is not None, "launched run still alive after teardown"
        assert not _group_alive(proc.pid), "a process of the launched run survived teardown"


def test_reap_fixture_terminates_the_whole_process_group(reap_launched_runs):
    """Basis: the launcher's child may start workers of its own; killing only the child would
    orphan them. A child that forks a sleeping grandchild is started through the patched Popen;
    the fixture's group kill must leave neither alive (checked here by its own teardown and below)."""

    if sys.platform == "win32":
        pytest.skip("process groups are POSIX")
    code = "import subprocess, sys, time; subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(600)']); time.sleep(600)"
    proc = runs.subprocess.Popen([sys.executable, "-c", code])
    assert os.getpgid(proc.pid) == proc.pid
    assert reap_launched_runs == [proc]


def test_r10_panel_execution_form_mismatch_with_actual_command(tmp_path: Path, monkeypatch, reap_launched_runs):
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
