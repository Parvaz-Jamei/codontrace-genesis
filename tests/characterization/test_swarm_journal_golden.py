"""Characterization: swarm journal, segment, checkpoint and archive bytes.

A fixed message script (fixed host clock, no wall time, no RNG) is written
through ``SwarmCoordinator`` with small segments and retention so that
rotation, checkpoints and the archive all occur. The produced files must equal
``golden/swarm_journal/`` byte for byte, and that committed fixture must keep
restoring (checkpoint path, explicit full replay, checkpoint-less full replay
across the archive) to the pinned state and journal digest.
"""
from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

from codontrace.swarm import SwarmCoordinator
from codontrace.swarm.experiments import hello, reading

from ._golden import GOLDEN_DIR, check_json, check_tree, load_json

SWARM = 'lab'
SEG = 1024
RETENTION = 2 * SEG
END_MS = 100_000
OPTS = {'journal_segment_bytes': SEG, 'journal_retention_bytes': RETENTION}


def _typed_hello(node: str) -> dict[str, Any]:
    m = hello(SWARM, node)
    m['schema'] = 'genesis_swarm_v2'
    m['payload']['channels'] = {'t': {'quantity': 'temperature', 'unit': 'degC', 'descriptor': {
        'value_type': 'scalar', 'measurement_model': 'direct', 'feature_id': 'room',
        'source_unit': 'degC', 'config_id': 'cfg1'}}}
    return m


def _typed_reading(node: str, seq: int, now: int, value: float) -> dict[str, Any]:
    m = reading(SWARM, node, seq, now, value)
    m['schema'] = 'genesis_swarm_v2'
    m['payload'].update(channel='t', valid=True, status='ok', config_id='cfg1')
    return m


def _reply(node: str, seq: int, command_id: str, ok: bool) -> dict[str, Any]:
    m = reading(SWARM, node, seq, 0, 0.0)
    m['kind'] = 'reply'
    m['payload'] = {'command_id': command_id, 'ok': ok, 'message': 'done' if ok else 'refused'}
    return m


def write_script(journal: Path) -> SwarmCoordinator:
    """Deterministic script touching every journaled action kind."""
    s = SwarmCoordinator(SWARM, journal=journal, **OPTS)
    t = 1000
    s.ingest(hello(SWARM, 'a'), now_ms=t)
    s.ingest(hello(SWARM, 'b'), now_ms=t)
    s.ingest(_typed_hello('c'), now_ms=t)
    for seq in range(1, 9):
        t += 10
        s.ingest(reading(SWARM, 'a', seq, t, 0.5 * seq), now_ms=t)
        s.ingest(reading(SWARM, 'b', seq, t, 0.5 * seq + 0.25), now_ms=t)
        s.ingest(_typed_reading('c', seq, t, 20.0 + seq / 8), now_ms=t)
        s.ingest(reading(SWARM, 'a', seq, t, 99.0), now_ms=t)  # duplicate seq: not journaled
        if seq % 3 == 0:
            s.calibrate('a/s', 0.5 * seq, 'ref-a', now_ms=t, scale=0.5)
    first = s.command('a', 'sample', {'channel': 's'}, now_ms=t, timeout_ms=500)
    s.command('b', 'pipeline', {'channel': 's', 'pipeline': {'alpha': 0.5, 'clip': 2.0, 'event_threshold': 1.0}},
              now_ms=t, timeout_ms=60_000)
    s.ingest(_reply('a', 9, first['command_id'], True), now_ms=t + 1)
    s._transaction('configure_channel', {'key': 'c/t', 'changes': {'range': [0.0, 50.0]}}, t + 2)  # service path
    s.boundary({'generation': 1, 'world_digest': 'f' * 64}, now_ms=t + 3)
    s.set_status('paused', now_ms=t + 4)  # cancels the pending pipeline command
    s.set_status('running', now_ms=t + 5)
    s.ingest(_typed_reading('c', 9, t + 6, 21.5), now_ms=t + 6)
    s.command('b', 'sample', {'channel': 's'}, now_ms=t + 7, timeout_ms=100)  # expires later
    s.boundary({'generation': 2, 'world_digest': 'e' * 64}, now_ms=t + 500)
    return s


def _stable(snapshot: dict[str, Any]) -> dict[str, Any]:
    return {'state': snapshot['state'], 'journal_digest': snapshot['journal_digest']}


def test_journal_files_match_golden_bytes(tmp_path):
    folder = tmp_path / SWARM
    s = write_script(folder / 'events.jsonl')
    snap = s.snapshot(now_ms=END_MS)
    # The script must actually exercise rotation, checkpoints and the archive.
    assert snap['journal_segment_count'] >= 1 and snap['journal_checkpoint_index'] is not None
    assert (folder / 'events.jsonl.archive').is_dir()
    assert snap['checkpoint_health'] == 'ok' and snap['retention_health'] == 'ok'
    (folder / 'events.jsonl.lock').unlink()  # empty lock file: not part of the format
    check_tree('swarm_journal', folder)
    check_json('swarm_journal_snapshot.json', snap)


def _fixture_copy(tmp_path: Path) -> Path:
    folder = tmp_path / SWARM
    shutil.copytree(GOLDEN_DIR / 'swarm_journal', folder)
    return folder / 'events.jsonl'


def test_committed_fixture_restores_via_checkpoint(tmp_path):
    journal = _fixture_copy(tmp_path)
    s = SwarmCoordinator(SWARM, journal=journal, **OPTS)
    assert s.snapshot(now_ms=END_MS) == load_json('swarm_journal_snapshot.json')


def test_committed_fixture_full_replay_matches(tmp_path):
    expected = _stable(load_json('swarm_journal_snapshot.json'))
    journal = _fixture_copy(tmp_path)
    s = SwarmCoordinator(SWARM, journal=journal, **OPTS)
    s.recover(full_replay=True)
    assert _stable(s.snapshot(now_ms=END_MS)) == expected
    for cp in journal.parent.glob('events.jsonl.checkpoint.*.json'):
        cp.unlink()
    # No checkpoint covers the live journal: automatic replay across the archive.
    auto = SwarmCoordinator(SWARM, journal=journal, **OPTS)
    assert _stable(auto.snapshot(now_ms=END_MS)) == expected


def test_restored_fixture_appends_identical_next_record(tmp_path):
    journal = _fixture_copy(tmp_path)
    s = SwarmCoordinator(SWARM, journal=journal, **OPTS)
    before = journal.read_bytes() if journal.exists() else b''
    s.set_status('stopped', now_ms=END_MS)
    after = journal.read_bytes()
    assert after.startswith(before)
    check_json('swarm_journal_next_record.json', {'appended_line': after[len(before):].decode('utf-8')})
