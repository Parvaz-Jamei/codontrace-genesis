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


def test_verify_anchor_tells_pruning_apart_from_truncation(tmp_path):
    journal = tmp_path / 'j.jsonl'
    kw = dict(journal=journal, journal_segment_bytes=1024, journal_retention_bytes=1024, archive_max_bytes=1024)
    s = SwarmCoordinator('s1', **kw)
    s.ingest(_hello(1), now_ms=1)
    s.ingest(_hello(2), now_ms=2)
    early = journal_anchor(s)
    for seq in range(3, 40):
        s.ingest(_hello(seq), now_ms=seq)
    late = journal_anchor(s)
    s.ingest(_hello(40), now_ms=40)
    archive = journal.with_name(journal.name + '.archive')
    kept = sorted(p.name for p in [*archive.glob('j.jsonl.part.*'), *tmp_path.glob('j.jsonl.part.*')])
    assert kept and not kept[0].endswith('.00000001')  # retention deleted the oldest segments
    # Normal pruning: the anchored segment is gone, the kept history is intact.
    assert verify_anchor(s, early)['status'] == 'pruned'
    assert verify_anchor(SwarmCoordinator('s1', **kw), early)['status'] == 'pruned'
    assert verify_anchor(s, late)['status'] == 'earlier_record'
    # Truncation: dropping the live tail is still reported as not_found, not as pruning.
    journal.write_text('', encoding='utf-8')
    journal.unlink()
    for p in tmp_path.glob('j.jsonl.part.*'):
        if p.name > kept[-1] or p.name == kept[-1]:
            p.unlink()
    truncated = SwarmCoordinator('s1', **kw)
    assert verify_anchor(truncated, late)['status'] == 'not_found'


def _pruned_coordinator(journal):
    kw = dict(journal=journal, journal_segment_bytes=1024, journal_retention_bytes=1024, archive_max_bytes=1024)
    s = SwarmCoordinator('s1', **kw)
    s.ingest(_hello(1), now_ms=1)
    s.ingest(_hello(2), now_ms=2)
    early = journal_anchor(s)
    for seq in range(3, 41):
        s.ingest(_hello(seq), now_ms=seq)
    return s, early, kw


def test_verify_anchor_checks_the_head_of_a_pruned_anchor(tmp_path):
    journal = tmp_path / 'j.jsonl'
    s, early, kw = _pruned_coordinator(journal)
    assert verify_anchor(s, early)['status'] == 'pruned'
    ledger = journal.with_name(journal.name + '.pruned')
    assert early['journal_head'] in ledger.read_text(encoding='utf-8')
    # Same segment, same swarm id, fabricated head: the head is checked, not just the index.
    forged = {**early, 'journal_head': 'ab' * 32}
    assert verify_anchor(s, forged)['status'] == 'forged'
    assert verify_anchor(SwarmCoordinator('s1', **kw), forged)['status'] == 'forged'
    # An anchor from another journal of the same swarm id is another history.
    other, foreign, _ = _pruned_coordinator(tmp_path / 'other.jsonl')
    other.ingest(_hello(41), now_ms=41)
    foreign = {**foreign, 'journal_head': other._chain, 'journal_checkpoint_index': early['journal_checkpoint_index']}
    assert foreign['journal_head'] != early['journal_head']
    assert verify_anchor(s, foreign)['status'] == 'forged'
    # Without a ledger entry for the anchored segment the head cannot be checked: not_found, never 'pruned'.
    ledger.unlink()
    assert verify_anchor(SwarmCoordinator('s1', **kw), early)['status'] == 'not_found'


def _oldest_kept(journal):
    archive = journal.with_name(journal.name + '.archive')
    names = [*archive.glob(journal.name + '.part.*'), *journal.parent.glob(journal.name + '.part.*')]
    return min(int(p.name.rsplit('.', 1)[-1]) for p in names)


def test_pruned_needs_an_anchored_segment_strictly_older_than_the_oldest_kept(tmp_path):
    from codontrace.genesis.journal.anchor import _pruned_before
    journal = tmp_path / 'j.jsonl'
    s, early, _ = _pruned_coordinator(journal)
    oldest = _oldest_kept(journal)
    assert oldest > 2
    # Segment one past journal_checkpoint_index: oldest - 1 is gone, oldest is kept.
    assert _pruned_before(s, {**early, 'journal_checkpoint_index': oldest - 2}) is True
    assert _pruned_before(s, {**early, 'journal_checkpoint_index': oldest - 1}) is False
    # A genuine pruned head paired with a kept segment is inconsistent: never 'pruned'.
    misplaced = {**early, 'journal_checkpoint_index': oldest - 1}
    assert verify_anchor(s, misplaced)['status'] == 'not_found'
    assert verify_anchor(s, {**early, 'journal_checkpoint_index': oldest - 2})['status'] == 'pruned'


def test_history_that_starts_at_genesis_is_never_pruned(tmp_path):
    from codontrace.genesis.journal.anchor import _pruned_before
    journal = tmp_path / 'j.jsonl'
    s = SwarmCoordinator('s1', journal=journal, journal_segment_bytes=1024)
    for seq in range(1, 30):
        s.ingest(_hello(seq), now_ms=seq)
    parts = sorted(tmp_path.glob('j.jsonl.part.*'))
    assert len(parts) >= 2
    # Renumber the segments upwards: the oldest kept segment is no longer 1,
    # but its first record still links to the zero digest, so nothing was pruned.
    for path in reversed(parts):
        index = int(path.name.rsplit('.', 1)[-1])
        path.rename(path.with_name(f'j.jsonl.part.{index + 10:08d}'))
    anchor = {**journal_anchor(s), 'journal_checkpoint_index': 0}
    assert _pruned_before(s, anchor) is False


def test_pruned_check_raises_without_a_journal_file_even_under_optimize(tmp_path):
    import subprocess
    import sys

    from codontrace.genesis.journal.anchor import _pruned_before
    with pytest.raises(ValueError, match='journal has no file'):
        _pruned_before(SwarmCoordinator('s1'), {'journal_checkpoint_index': 0})
    # Under -O an assert would be compiled away; the check must still raise.
    code = ("from codontrace.genesis.journal.anchor import _pruned_before\n"
            "from codontrace.swarm.runtime import SwarmCoordinator\n"
            "try:\n    _pruned_before(SwarmCoordinator('s1'), {'journal_checkpoint_index': 0})\n"
            "except ValueError as error:\n    print('raised', error)\n")
    out = subprocess.run([sys.executable, '-O', '-c', code], capture_output=True, text=True, check=True, timeout=120)
    assert out.stdout.startswith('raised journal has no file')
