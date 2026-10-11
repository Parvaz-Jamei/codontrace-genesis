"""Journal checkpoints, storage-free reads, recorder lineage cursor and FDC FIN_SEL."""
from __future__ import annotations

import json

import pytest

from codontrace.genesis.engine import GenesisEngine
from codontrace.genesis.runtime_profiles import GenesisRuntimeProfile
from codontrace.swarm import SwarmCoordinator, service
from codontrace.swarm.experiments import hello, reading
from codontrace.swarm.sensors import fdc_sample
from codontrace.visualization import SimulationRecorder

SEGMENT = 1024


def _fill(path, records=40, **kwargs):
    swarm = SwarmCoordinator('lab', journal=path, journal_segment_bytes=SEGMENT, **kwargs)
    swarm.ingest(hello('lab', 'a'), now_ms=1000)
    for seq in range(1, records):
        swarm.ingest(reading('lab', 'a', seq, 1000 + seq, float(seq)), now_ms=1000 + seq)
    return swarm


def _replayed(monkeypatch):
    seen = []
    original = SwarmCoordinator._replay_file

    def spy(self, path):
        seen.append(path.name)
        return original(self, path)

    monkeypatch.setattr(SwarmCoordinator, '_replay_file', spy)
    return seen


# --- 1. journal checkpoints and retention -------------------------------------------------

def test_startup_replays_only_records_after_latest_checkpoint(tmp_path, monkeypatch):
    path = tmp_path / 'events.jsonl'
    writer = _fill(path)
    segments = sorted(tmp_path.glob('events.jsonl.part.*'))
    checkpoints = sorted(tmp_path.glob('events.jsonl.checkpoint.*.json'))
    assert len(segments) >= 4
    assert [c.name for c in checkpoints] == [f'events.jsonl.checkpoint.{i:08d}.json' for i in (len(segments) - 1, len(segments))]
    expected = writer.snapshot(now_ms=2000)
    seen = _replayed(monkeypatch)
    clone = SwarmCoordinator('lab', journal=path, journal_segment_bytes=SEGMENT)
    assert seen == ['events.jsonl']  # covered segments are hash-checked, not re-applied
    assert clone.snapshot(now_ms=2000) == expected
    assert expected['journal_checkpoint_index'] == len(segments)
    assert expected['checkpoint_health'] == 'ok'
    # Snapshot-plus-tail equals a full replay of the whole chain.
    full = SwarmCoordinator('lab', journal=path, journal_segment_bytes=SEGMENT)
    result = full.recover(full_replay=True)
    assert result['state_changed'] is False and result['journal_digest'] == expected['journal_digest']
    assert full.snapshot(now_ms=2000)['state'] == expected['state']


def test_corrupt_or_unbound_checkpoint_falls_back_without_skipping_history(tmp_path, monkeypatch):
    path = tmp_path / 'events.jsonl'
    expected = _fill(path).snapshot(now_ms=2000)
    newest, older = sorted(tmp_path.glob('events.jsonl.checkpoint.*.json'), reverse=True)
    newest.write_text(newest.read_text().replace('"command_counter":0', '"command_counter":7', 1))
    seen = _replayed(monkeypatch)
    clone = SwarmCoordinator('lab', journal=path, journal_segment_bytes=SEGMENT)
    assert seen == [sorted(tmp_path.glob('events.jsonl.part.*'))[-1].name, 'events.jsonl']
    assert clone.snapshot(now_ms=2000)['state'] == expected['state']
    # Make the older one disagree with its segment too: full replay, same state.
    payload = json.loads(older.read_text())
    payload['chain'] = 'f' * 64
    older.write_text(json.dumps(payload))
    for f in tmp_path.glob('events.jsonl.checkpoint.*.json'):
        if f != older:
            f.unlink()
    seen.clear()
    again = SwarmCoordinator('lab', journal=path, journal_segment_bytes=SEGMENT)
    assert seen[0] == 'events.jsonl.part.00000001'
    assert again.snapshot(now_ms=2000)['state'] == expected['state']
    # A fresh checkpoint was rebuilt after full replay.
    assert again.snapshot(now_ms=2000)['journal_checkpoint_index'] == len(sorted(tmp_path.glob('events.jsonl.part.*')))


def test_journal_without_checkpoints_still_restores_and_gains_one(tmp_path):
    path = tmp_path / 'events.jsonl'
    expected = _fill(path).snapshot(now_ms=2000)
    for f in tmp_path.glob('events.jsonl.checkpoint.*.json'):
        f.unlink()
    clone = SwarmCoordinator('lab', journal=path, journal_segment_bytes=SEGMENT)
    assert clone.snapshot(now_ms=2000)['state'] == expected['state']
    assert list(tmp_path.glob('events.jsonl.checkpoint.*.json'))


def test_tamper_in_covered_live_segment_is_still_detected(tmp_path):
    path = tmp_path / 'events.jsonl'
    _fill(path)
    first = tmp_path / 'events.jsonl.part.00000001'
    first.write_text(first.read_text().replace('"now_ms":1001', '"now_ms":1002', 1))
    with pytest.raises(ValueError, match='integrity'):
        SwarmCoordinator('lab', journal=path, journal_segment_bytes=SEGMENT)


def test_retention_archives_covered_segments_and_keeps_data(tmp_path):
    path = tmp_path / 'events.jsonl'
    writer = _fill(path, records=60, journal_retention_bytes=3 * SEGMENT)
    expected = writer.snapshot(now_ms=3000)
    archive = tmp_path / 'events.jsonl.archive'
    archived = sorted(archive.glob('events.jsonl.part.*'))
    live = sorted(tmp_path.glob('events.jsonl.part.*'))
    assert archived and archived[0].name == 'events.jsonl.part.00000001'
    live_bytes = sum(p.stat().st_size for p in live) + path.stat().st_size
    assert live_bytes <= 3 * SEGMENT + SEGMENT  # cap plus the record being appended
    clone = SwarmCoordinator('lab', journal=path, journal_segment_bytes=SEGMENT, journal_retention_bytes=3 * SEGMENT)
    assert clone.snapshot(now_ms=3000)['state'] == expected['state']
    # Archived history remains fully verifiable.
    assert clone.recover(full_replay=True)['journal_digest'] == expected['journal_digest']
    assert clone.snapshot(now_ms=3000)['state'] == expected['state']
    # Rotation keeps numbering after archiving.
    clone.ingest(reading('lab', 'a', 500, 3000, 1.0), now_ms=3000)
    names = [int(p.name.rsplit('.', 1)[1]) for p in [*archive.glob('events.jsonl.part.*'), *tmp_path.glob('events.jsonl.part.*')]]
    assert sorted(names) == list(range(1, max(names) + 1))


def test_archive_deletion_only_past_explicit_cap(tmp_path):
    path = tmp_path / 'events.jsonl'
    writer = _fill(path, records=60, journal_retention_bytes=2 * SEGMENT, archive_max_bytes=SEGMENT)
    expected = writer.snapshot(now_ms=3000)
    archive = tmp_path / 'events.jsonl.archive'
    assert sum(p.stat().st_size for p in archive.glob('events.jsonl.part.*')) <= SEGMENT
    assert not (archive / 'events.jsonl.part.00000001').exists()
    clone = SwarmCoordinator('lab', journal=path, journal_segment_bytes=SEGMENT)
    assert clone.snapshot(now_ms=3000)['state'] == expected['state']
    with pytest.raises(ValueError, match='deleted'):
        clone.recover(full_replay=True)
    assert clone.snapshot(now_ms=3000)['journal_health'] == 'recovery_required'
    assert clone.recover()['journal_digest'] == expected['journal_digest']


def test_retention_settings_are_validated(tmp_path):
    with pytest.raises(ValueError):
        SwarmCoordinator('lab', journal=tmp_path / 'e', journal_segment_bytes=4096, journal_retention_bytes=1024)
    with pytest.raises(ValueError):
        SwarmCoordinator('lab', journal=tmp_path / 'e', archive_max_bytes=-1)
    with pytest.raises(ValueError):
        SwarmCoordinator('lab').recover(full_replay='yes')


def test_failed_checkpoint_does_not_block_journal_writes(tmp_path, monkeypatch):
    path = tmp_path / 'events.jsonl'
    monkeypatch.setattr(SwarmCoordinator, '_checkpoint_path',
                        lambda self, index: tmp_path / 'missing-dir' / f'c{index}.json')
    writer = _fill(path)
    snap = writer.snapshot(now_ms=2000)
    assert snap['journal_health'] == 'ready' and snap['checkpoint_health'].startswith('checkpoint ')
    monkeypatch.undo()
    assert SwarmCoordinator('lab', journal=path, journal_segment_bytes=SEGMENT).snapshot(now_ms=2000)['state'] == snap['state']


# --- 2. read-only access never creates storage ---------------------------------------------

def test_unknown_swarm_reads_create_no_files(tmp_path, monkeypatch):
    monkeypatch.setenv('CODONTRACE_SWARM_DIR', str(tmp_path)); service._SWARMS.clear()
    try:
        snap = service.invoke('snapshot', {'swarm_id': 'ghost'}, now_ms=1000)
        assert snap['swarm_recorded'] is False and snap['result']['state']['nodes'] == {}
        fused = service.invoke('fusion', {'swarm_id': 'ghost', 'quantity': 'signal', 'unit': 'arb'}, now_ms=1000)
        assert fused['result']['status'] == 'insufficient_data'
        service.invoke('uncertainty_interval', {'swarm_id': 'ghost2', 'predictions': [0, 0, 0], 'references': [1, 2, 3],
                       'estimate': 0, 'training_id': 't', 'calibration_id': 'c', 'model_id': 'm'}, now_ms=1000)
        with pytest.raises(ValueError):
            service.invoke('no_such_action', {'swarm_id': 'ghost3'}, now_ms=1000)
        assert list(tmp_path.iterdir()) == [] and service._SWARMS == {}
        service.invoke('ingest', {'swarm_id': 'real', 'message': hello('real', 'a')}, now_ms=1000)
        assert (tmp_path / 'real' / 'events.jsonl').exists()
        assert service.invoke('snapshot', {'swarm_id': 'real'}, now_ms=1000)['swarm_recorded'] is True
    finally:
        service._SWARMS.clear()


# --- 3. recorder lineage cursor -------------------------------------------------------------

def _record(root, *, cursor, ticks=40):
    engine = GenesisEngine.from_spec(GenesisRuntimeProfile.life_loop_world(seed=11, tick_count=ticks, population=6))
    recorder = SimulationRecorder(root, lineage_cursor=cursor).attach(engine)
    engine.run_ticks(); recorder.finalize()
    files = sorted((root / 'simulation' / 'seed_11').glob('frame_*.json'))
    return recorder, {f.name: f.read_bytes() for f in files}, engine


def test_lineage_cursor_frames_are_byte_identical_to_full_scan(tmp_path):
    fast, frames, engine = _record(tmp_path / 'cursor', cursor=True)
    slow, reference, _ = _record(tmp_path / 'scan', cursor=False)
    assert frames == reference and len(frames) > 2
    lineage = engine.runner.population.lineage
    assert any(r.death_tick is not None for r in lineage) and len(lineage) > 6
    assert any(json.loads(b)['metrics']['births'] for b in frames.values())
    assert fast.lineage_full_scans == 0 and slow.lineage_full_scans == len(frames) - 1


def test_lineage_cursor_falls_back_when_history_is_rewritten(tmp_path):
    rec = SimulationRecorder(tmp_path)

    class R:
        def __init__(self, oid, birth, death=None):
            self.organism_id, self.birth_tick, self.death_tick = oid, birth, death

    rec._reset_cursor((R('a', 0), R('b', 0)))
    assert [r.organism_id for r in rec._interval_lineage((R('a', 0, 2), R('b', 0), R('c', 1)), 0, 2)] == ['a', 'c']
    assert rec.lineage_full_scans == 0 and rec._lineage_open == {1: 'b', 2: 'c'}
    rewritten = (R('x', 3), R('y', 0, 3))
    assert [r.organism_id for r in rec._interval_lineage(rewritten, 2, 3)] == ['x', 'y']
    assert rec.lineage_full_scans == 1


# --- 5. FDC2x1x FIN_SEL ---------------------------------------------------------------------

FDC2214 = {'channel': 0, 'status': 'Ok', 'rawCode': 1, 'frequencyHz': 1e6, 'frefHz': 40e6,
           'finSelMultiplier': 1, 'frefDivider': 1, 'dataReady': True}


@pytest.mark.parametrize('multiplier', [1, 2])
def test_fdc_fin_sel_documented_values_accepted(multiplier):
    _, payload = fdc_sample({**FDC2214, 'finSelMultiplier': multiplier}, variant='FDC2214', config_id='c1')
    assert payload['valid'] is True and payload['metadata']['finSelMultiplier'] == multiplier


@pytest.mark.parametrize('status', ['Ok', 'Timeout'])
def test_fdc_reserved_fin_sel_rejected(status):
    with pytest.raises(ValueError):
        fdc_sample({**FDC2214, 'status': status, 'finSelMultiplier': 3}, variant='FDC2214', config_id='c1')


def test_fdc_valid_reading_needs_divider_and_unread_fin_sel_stays_invalid():
    with pytest.raises(ValueError):
        fdc_sample({**FDC2214, 'frefDivider': 0}, variant='FDC2214', config_id='c1')
    _, payload = fdc_sample({**FDC2214, 'status': 'Timeout', 'finSelMultiplier': 0, 'frefDivider': 0},
                            variant='FDC2214', config_id='c1')
    assert payload['valid'] is False and payload['value'] is None
