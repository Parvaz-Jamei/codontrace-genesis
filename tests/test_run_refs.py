"""P9: shared run roots, module run references and journal head anchors."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from codontrace.campaigns import board_runner
from codontrace.contracts.run_roots import resolve_run_root
from codontrace.genesis.artifacts import validate_scientific_manifest
from codontrace.genesis.journal import journal_anchor, verify_anchor
from codontrace.genesis.run_refs import RUN_REFERENCE_SCHEMA, module_run_reference
from codontrace.swarm.runtime import SwarmCoordinator


def test_simulation_root_precedence(tmp_path, monkeypatch):
    from codontrace.console.runs import runs_directory
    monkeypatch.delenv('CODONTRACE_RUNS_DIR', raising=False)
    monkeypatch.setenv('HOME', str(tmp_path / 'home'))
    monkeypatch.chdir(tmp_path)
    (tmp_path / 'home').mkdir()
    # Fallback: ./simulation_runs is created.
    assert runs_directory() == resolve_run_root('simulation') == (tmp_path / 'simulation_runs').resolve()
    (tmp_path / 'simulation_runs').rmdir()
    (tmp_path / 'home' / 'simulation_runs').mkdir()
    assert runs_directory() == tmp_path / 'home' / 'simulation_runs'
    (tmp_path / 'simulation_runs').mkdir()
    assert runs_directory() == (tmp_path / 'simulation_runs').resolve()
    monkeypatch.setenv('CODONTRACE_RUNS_DIR', str(tmp_path / 'custom' / 'runs'))
    assert runs_directory() == tmp_path / 'custom' / 'runs' and (tmp_path / 'custom' / 'runs').is_dir()


def test_swarm_root_override_and_absolute_rule(tmp_path, monkeypatch):
    from codontrace.swarm import service
    monkeypatch.setenv('CODONTRACE_SWARM_DIR', str(tmp_path / 's'))
    assert service._root() == resolve_run_root('swarm') == (tmp_path / 's').resolve()
    assert not (tmp_path / 's').exists()
    monkeypatch.setenv('CODONTRACE_SWARM_DIR', 'relative/dir')
    with pytest.raises(ValueError, match='must be absolute'):
        service._root()
    monkeypatch.delenv('CODONTRACE_SWARM_DIR')
    monkeypatch.setenv('HOME', str(tmp_path / 'h'))
    assert resolve_run_root('swarm') == (tmp_path / 'h' / '.local' / 'share' / 'codontrace' / 'swarm_runs').resolve()
    with pytest.raises(ValueError, match='explicit output directory'):
        resolve_run_root('board')


def _legacy_tree(root: Path) -> dict[str, bytes]:
    return {str(p.relative_to(root)): p.read_bytes() for p in sorted(root.rglob('*'))
            if p.is_file() and p.name != board_runner.RUN_REFERENCE_NAME}


def test_board_reference_leaves_legacy_bytes_identical(tmp_path, monkeypatch):
    with_ref, without = tmp_path / 'a', tmp_path / 'b'
    for output in (with_ref, without):
        if output is without:
            monkeypatch.setattr(board_runner, '_write_run_reference', lambda *a, **k: None)
        board_runner.run_uninterrupted(output=output, seed=7, ticks=2, population=4, workers=1)
        mid = output / 'runs' / 'T11' / 'seed_7' / 'arm_uninterrupted' / 'checkpoints' / 'mid.bin'
        board_runner.resume(output=output, checkpoint=mid, seed=7, ticks=2, population=4, workers=1)
    assert _legacy_tree(with_ref) == _legacy_tree(without)
    for arm in ('uninterrupted', 'resume'):
        arm_dir = with_ref / 'runs' / 'T11' / 'seed_7' / f'arm_{arm}'
        ref = json.loads((arm_dir / board_runner.RUN_REFERENCE_NAME).read_text(encoding='utf-8'))
        assert ref['schema'] == RUN_REFERENCE_SCHEMA and ref['kind'] == 'board'
        assert not (without / 'runs' / 'T11' / 'seed_7' / f'arm_{arm}' / board_runner.RUN_REFERENCE_NAME).exists()
        manifest = json.loads((arm_dir / 'artifacts_manifest.json').read_text(encoding='utf-8'))
        assert board_runner.RUN_REFERENCE_NAME not in manifest['files']
        assert ref['legacy_files']['artifacts_manifest.json'] == board_runner._sha256(arm_dir / 'artifacts_manifest.json')
        validation = ref['scientific_manifest_validation']
        assert set(validation) == {'passed', 'missing_hashes', 'placeholder_hashes'}
        assert ref['run_manifest']['seed'] == 7 and len(ref['run_manifest_sha256']) == 64
        assert len(ref['replay_bundle_sha256']) == 64


def test_reference_carries_the_manifest_validation_result():
    from codontrace.engine import GenesisEngine
    from codontrace.genesis.runtime_profiles import GenesisRuntimeProfile
    result = GenesisEngine.from_spec(GenesisRuntimeProfile.life_loop_world(seed=7, tick_count=1, population=2)).run_ticks()
    ref = module_run_reference('visualization', 'r1', manifest=result.manifest, replay_bundle=result.replay_bundle)
    assert ref['scientific_manifest_validation'] == validate_scientific_manifest(result.manifest).to_dict()
    with pytest.raises(ValueError):
        module_run_reference('nope', 'r1')


def _hello(seq):
    return {'schema': 'genesis_swarm_v1', 'swarm_id': 's1', 'node_id': 'n1', 'boot_id': f'b{seq}', 'seq': seq,
            'kind': 'hello', 'payload': {'wifi': True, 'channels': {'t': {'quantity': 'q', 'unit': 'u'}},
                                         'operations': ['sample']}}


def test_swarm_reference_anchor_detects_tail_truncation(tmp_path):
    journal = tmp_path / 'j.jsonl'
    s = SwarmCoordinator('s1', journal=journal)
    for seq in range(1, 4):
        s.ingest(_hello(seq), now_ms=seq)
    ref = s.run_reference()
    anchor = ref['journal_anchor']
    assert ref['kind'] == 'swarm' and anchor['journal_head'] == s._chain and anchor['swarm_id'] == 's1'
    assert verify_anchor(s, anchor)['status'] == 'current_head'
    s.ingest(_hello(4), now_ms=4)
    assert verify_anchor(s, anchor)['status'] == 'earlier_record'
    # Drop the last two records: a valid, shorter chain that no longer contains the anchored head.
    lines = journal.read_text(encoding='utf-8').splitlines(keepends=True)
    journal.write_text(''.join(lines[:-2]), encoding='utf-8')
    truncated = SwarmCoordinator('s1', journal=journal)
    assert verify_anchor(truncated, anchor)['status'] == 'not_found'
    assert journal_anchor(truncated)['journal_head'] != anchor['journal_head']


def test_visualization_reference_is_opt_in_and_beside_the_frames(tmp_path):
    from codontrace.engine import GenesisEngine
    from codontrace.genesis.runtime_profiles import GenesisRuntimeProfile
    from codontrace.visualization import SimulationRecorder
    engine = GenesisEngine.from_spec(GenesisRuntimeProfile.life_loop_world(seed=7, tick_count=2, population=4))
    root = tmp_path / 'atlas'
    recorder = SimulationRecorder(root).attach(engine)
    result = engine.run_ticks()
    before = sorted(str(p.relative_to(root)) for p in root.rglob('*'))
    assert not (tmp_path / 'atlas.run_ref.json').exists()
    path = recorder.write_run_reference(result=result)
    assert path == tmp_path / 'atlas.run_ref.json'
    assert sorted(str(p.relative_to(root)) for p in root.rglob('*')) == before
    ref = json.loads(path.read_text(encoding='utf-8'))
    assert ref['kind'] == 'visualization' and ref['extra']['world_digest'] == engine.world_digest()
