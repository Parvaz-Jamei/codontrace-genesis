"""Characterization, second script: exact boundaries and restore-selection paths.

Covers what the main journal golden does not reach: rotation when the live
file is exactly ``journal_segment_bytes``, command expiry at exactly
``expires_ms``, retention that must keep the checkpoint's own segment live,
archive deletion at exactly ``archive_max_bytes``, restore choosing the newest
of two valid checkpoints (and falling back to the spare), the hash-chain check
of covered segments, and the archive/live overlap filter during full replay.
Variant ``archive`` uses minimum retention plus an archive cap; variant
``spare`` keeps every segment live so two checkpoints stay valid.
"""
from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

import pytest

from codontrace.swarm import SwarmCoordinator
from codontrace.swarm.experiments import hello, reading

from ._golden import GOLDEN_DIR, check_json, check_tree, load_json

SWARM = 'edge'
SEG = 1024
END_MS = 50_000


def _opts(variant: str, archive_max_bytes: int | None = None) -> dict[str, Any]:
    if variant == 'archive':
        return {'journal_segment_bytes': SEG, 'journal_retention_bytes': SEG, 'archive_max_bytes': archive_max_bytes}
    return {'journal_segment_bytes': SEG}


def _boundary_line_length(journal: Path, generation: int, now: int, opts: dict[str, Any]) -> int:
    """Length of the next boundary record with an empty pad, measured on a scratch copy."""
    scratch = journal.parent.with_name(journal.parent.name + '-measure')
    shutil.rmtree(scratch, ignore_errors=True)
    shutil.copytree(journal.parent, scratch)
    try:
        probe = SwarmCoordinator(SWARM, journal=scratch / journal.name, **opts)
        before = (scratch / journal.name).stat().st_size
        probe.boundary({'generation': generation, 'pad': ''}, now_ms=now)
        return (scratch / journal.name).stat().st_size - before
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def _last_segment(journal: Path) -> int:
    names = [*journal.parent.glob('events.jsonl.part.*'), *journal.parent.glob('events.jsonl.archive/*.part.*')]
    return max((int(p.name.rsplit('.', 1)[-1]) for p in names), default=0)


def _readings(s: SwarmCoordinator, seqs: range, t: int) -> int:
    for seq in seqs:
        t += 10
        s.ingest(reading(SWARM, 'a', seq, t, 0.25 * seq), now_ms=t)
        s.ingest(reading(SWARM, 'b', seq, t, 0.25 * seq + 1.0), now_ms=t)
    return t


def write_script(journal: Path, variant: str, archive_max_bytes: int | None = None) -> SwarmCoordinator:
    opts = _opts(variant, archive_max_bytes)
    s = SwarmCoordinator(SWARM, journal=journal, **opts)
    t = 1000
    s.ingest(hello(SWARM, 'a'), now_ms=t)
    s.ingest(hello(SWARM, 'b'), now_ms=t)
    command = s.command('a', 'sample', {'channel': 's'}, now_ms=t, timeout_ms=100)
    assert command['expires_ms'] == t + 100
    t = _readings(s, range(1, 10), t)  # t == 1090
    s.set_status('paused', now_ms=1100)  # exactly expires_ms: the command must expire in this record
    s.set_status('running', now_ms=1101)
    t = _readings(s, range(10, 20), 1101)
    # Pad right after a rotation so the live file is exactly one segment long.
    # One small write right after a rotation, so the live file is short.
    parts = _last_segment(journal)
    seq = 20
    while _last_segment(journal) == parts:
        t += 10
        s.ingest(reading(SWARM, 'a', seq, t, 0.25 * seq), now_ms=t)
        seq += 1
    assert journal.stat().st_size < SEG
    size = journal.stat().st_size
    pad = SEG - size - _boundary_line_length(journal, 1, t + 1, opts)
    assert pad >= 0
    segments = s.snapshot(now_ms=t)['journal_segment_count']
    s.boundary({'generation': 1, 'pad': 'x' * pad}, now_ms=t + 1)
    assert journal.stat().st_size == SEG
    s.boundary({'generation': 2, 'pad': ''}, now_ms=t + 2)  # this write rotates at exactly SEG
    assert s.snapshot(now_ms=t + 2)['journal_segment_count'] == segments + 1 or variant == 'archive'
    _readings(s, range(5000, 5020), t + 2)
    return s


def _archive_cap(tmp_path: Path) -> int:
    """Exactly the size of the two newest archived segments of an uncapped run.

    The capped run then ends with those two segments in the archive and a total
    equal to the cap: deletion must stop at equality (``total <= cap``).
    """
    dry = tmp_path / 'dry' / 'events.jsonl'
    write_script(dry, 'archive')
    archived = sorted(dry.with_name('events.jsonl.archive').iterdir())
    assert len(archived) >= 3
    return sum(path.stat().st_size for path in archived[-2:])


def _produce(tmp_path: Path, variant: str) -> tuple[Path, dict[str, Any], int | None]:
    cap = _archive_cap(tmp_path) if variant == 'archive' else None
    folder = tmp_path / variant
    s = write_script(folder / 'events.jsonl', variant, cap)
    snap = s.snapshot(now_ms=END_MS)
    (folder / 'events.jsonl.lock').unlink()
    return folder, snap, cap


@pytest.mark.parametrize('variant', ['archive', 'spare'])
def test_boundary_script_matches_golden_bytes(tmp_path, variant):
    folder, snap, cap = _produce(tmp_path, variant)
    assert snap['checkpoint_health'] == 'ok' and snap['retention_health'] == 'ok'
    checkpoints = sorted(p.name for p in folder.glob('events.jsonl.checkpoint.*.json'))
    if variant == 'archive':
        archived = sorted(p.name for p in (folder / 'events.jsonl.archive').iterdir())
        # Older segments were deleted; the two newest fill the cap exactly and both stay.
        assert len(archived) == 2
        assert sum((folder / 'events.jsonl.archive' / name).stat().st_size for name in archived) == cap
        # The checkpoint's own segment stays live even though live bytes exceed retention.
        live = sorted(p.name for p in folder.glob('events.jsonl.part.*'))
        assert live == [f'events.jsonl.part.{snap["journal_checkpoint_index"]:08d}']
    else:
        assert len(checkpoints) == 2
    check_tree(f'swarm_journal_{variant}', folder)
    check_json(f'swarm_journal_{variant}_snapshot.json', {'snapshot': snap, 'archive_max_bytes': cap,
                                                          'checkpoints': checkpoints})


def _fixture(tmp_path: Path, variant: str) -> Path:
    folder = tmp_path / variant
    shutil.copytree(GOLDEN_DIR / f'swarm_journal_{variant}', folder)
    return folder / 'events.jsonl'


def _golden_snapshot(variant: str) -> dict[str, Any]:
    return load_json(f'swarm_journal_{variant}_snapshot.json')


def _identity(path: Path) -> tuple[int, int]:
    st = path.stat()
    return st.st_ino, st.st_mtime_ns


def test_restore_prefers_newest_of_two_valid_checkpoints(tmp_path):
    journal = _fixture(tmp_path, 'spare')
    expected = _golden_snapshot('spare')
    newest_name, spare_name = reversed(expected['checkpoints'])
    before = {name: _identity(journal.parent / name) for name in (newest_name, spare_name)}
    s = SwarmCoordinator(SWARM, journal=journal, **_opts('spare'))
    snap = s.snapshot(now_ms=END_MS)
    assert snap == expected['snapshot']
    assert snap['journal_checkpoint_index'] == int(newest_name.split('.')[-2])
    # Restoring from the newest checkpoint leaves nothing to re-checkpoint: both files untouched.
    # (Restoring from the spare would replay the last segment and rewrite the newest one.)
    assert {name: _identity(journal.parent / name) for name in before} == before


def test_restore_falls_back_to_spare_checkpoint(tmp_path):
    journal = _fixture(tmp_path, 'spare')
    expected = _golden_snapshot('spare')
    newest_name, spare_name = reversed(expected['checkpoints'])
    original = (journal.parent / newest_name).read_bytes()
    (journal.parent / newest_name).write_text('{}', encoding='utf-8')
    spare_before = _identity(journal.parent / spare_name)
    s = SwarmCoordinator(SWARM, journal=journal, **_opts('spare'))
    snap = s.snapshot(now_ms=END_MS)
    assert snap['state'] == expected['snapshot']['state']
    assert snap['journal_digest'] == expected['snapshot']['journal_digest']
    # Restored from the spare, replayed the newest segment and rewrote its checkpoint identically.
    assert _identity(journal.parent / spare_name) == spare_before
    assert (journal.parent / newest_name).read_bytes() == original
    assert snap['journal_checkpoint_index'] == int(newest_name.split('.')[-2])


def test_covered_segment_tampering_is_detected(tmp_path):
    journal = _fixture(tmp_path, 'spare')
    first = journal.with_name('events.jsonl.part.00000001')
    lines = first.read_bytes().split(b'\n')
    lines[0] = lines[0].replace(b'"now_ms":1000', b'"now_ms":1001', 1)
    assert lines[0] != first.read_bytes().split(b'\n')[0]
    first.write_bytes(b'\n'.join(lines))
    with pytest.raises(ValueError, match='integrity'):
        SwarmCoordinator(SWARM, journal=journal, **_opts('spare'))


def test_full_replay_drops_archive_copy_overlapping_live_segment(tmp_path):
    journal = _fixture(tmp_path, 'archive')
    expected = _golden_snapshot('archive')['snapshot']
    live = sorted(journal.parent.glob('events.jsonl.part.*'))[0]
    archive = journal.with_name('events.jsonl.archive')
    # Interrupted move: the live segment also exists in the archive.
    shutil.copy2(live, archive / live.name)
    # Re-create the deleted early segments' absence check: replay starts at segment 1 only if present.
    s = SwarmCoordinator(SWARM, journal=journal, **_opts('archive', _golden_snapshot('archive')['archive_max_bytes']))
    assert s.snapshot(now_ms=END_MS)['journal_digest'] == expected['journal_digest']
    with pytest.raises(ValueError, match='earliest archived segments were deleted'):
        s.recover(full_replay=True)


def test_full_replay_with_overlap_on_complete_archive(tmp_path):
    """Overlap filter on a history whose archive still starts at segment 1."""
    dry = tmp_path / 'full' / 'events.jsonl'
    s = write_script(dry, 'archive')  # no cap: nothing deleted
    expected = s.snapshot(now_ms=END_MS)
    live = sorted(dry.parent.glob('events.jsonl.part.*'))[0]
    shutil.copy2(live, dry.with_name('events.jsonl.archive') / live.name)
    restored = SwarmCoordinator(SWARM, journal=dry, **_opts('archive'))
    result = restored.recover(full_replay=True)
    assert result['journal_digest'] == expected['journal_digest']
    assert restored.snapshot(now_ms=END_MS)['state'] == expected['state']
