"""Journal checkpoints: fuzz equivalence, crash points, recovery, retention and concurrency."""
from __future__ import annotations

import hashlib
import json
import os
import random

import pytest

from codontrace.swarm import SwarmCoordinator, service
from codontrace.swarm.experiments import hello, packet, reading
from codontrace.swarm.protocol import canonical

SEG = 1024


def _digest(state):
    return hashlib.sha256(canonical(state).encode()).hexdigest()


def _ops(seed, n):
    """Random but valid-ish event stream; some ops are expected to be rejected."""
    rng = random.Random(seed)
    nodes = {'a': ['boot1', 0], 'b': ['boot1', 0], 'c': ['boot1', 0]}
    now = 1000
    out = []
    for name in nodes:
        out.append(('ingest', hello('lab', name), now))
    for _ in range(n):
        now += rng.choice([0, 1, 5, 50, 3000, 20000])
        node = rng.choice(sorted(nodes))
        boot, seq = nodes[node]
        r = rng.random()
        if r < 0.55:
            seq += rng.choice([1, 1, 1, 0, -1])
            nodes[node][1] = max(seq, nodes[node][1])
            out.append(('ingest', reading('lab', node, max(seq, 0), now - rng.choice([0, 0, 10, 20000]),
                                          round(rng.uniform(-5, 5), 3)), now))
        elif r < 0.62:
            nodes[node] = [f'boot{rng.randint(1, 4)}', 0]
            m = hello('lab', node); m['boot_id'] = nodes[node][0]
            out.append(('ingest', m, now))
        elif r < 0.72:
            out.append(('command', (node, rng.choice(['sample', 'raw', 'set_rate']), {'channel': 's'}), now))
        elif r < 0.80:
            nodes[node][1] += 1
            out.append(('ingest', packet('lab', node, nodes[node][1], 'reply',
                                         {'command_id': f'cmd-{rng.randint(1, 30)}', 'ok': rng.random() < .5},
                                         boot=nodes[node][0]), now))
        elif r < 0.86:
            out.append(('status', rng.choice(['running', 'running', 'paused', 'stopped']), now))
        elif r < 0.93:
            out.append(('trust', (node + '/s', round(rng.uniform(-5, 5), 2)), now))
        else:
            out.append(('boundary', {'generation': rng.randint(0, 99), 'note': 'x' * rng.randint(0, 300)}, now))
    return out


def _do(swarm, op):
    kind, arg, now = op
    try:
        if kind == 'ingest':
            return ('ok', swarm.ingest(arg, now_ms=now))
        if kind == 'command':
            return ('ok', swarm.command(arg[0], arg[1], arg[2], now_ms=now))
        if kind == 'status':
            return ('ok', swarm.set_status(arg, now_ms=now))
        if kind == 'trust':
            return ('ok', swarm.calibrate(arg[0], arg[1], 'ref', now_ms=now))
        return ('ok', swarm.boundary(arg, now_ms=now))
    except ValueError as error:
        return ('ValueError', str(error))


@pytest.mark.parametrize('seed', range(12))
def test_fuzz_checkpoint_tail_replay_equals_memory_and_full_replay(tmp_path, seed):
    rng = random.Random(1000 + seed)
    path = tmp_path / 'events.jsonl'
    kwargs = {'journal_segment_bytes': SEG}
    if seed % 3 == 1:
        kwargs['journal_retention_bytes'] = 3 * SEG
    if seed % 3 == 2:
        kwargs.update(journal_retention_bytes=2 * SEG, archive_max_bytes=10**9)
    memory = SwarmCoordinator('lab')
    disk = SwarmCoordinator('lab', journal=path, **kwargs)
    for i, op in enumerate(_ops(seed, 220)):
        assert _do(memory, op) == _do(disk, op), (i, op)
        assert disk.snapshot(now_ms=op[2])['journal_health'] == 'ready'
        if rng.random() < 0.08:  # restart from disk: checkpoint + tail
            disk = SwarmCoordinator('lab', journal=path, **kwargs)
            assert disk.snapshot(now_ms=op[2])['state'] == memory.snapshot(now_ms=op[2])['state']
            assert disk.snapshot(now_ms=op[2])['journal_digest'] == memory.snapshot(now_ms=op[2])['journal_digest']
    final = memory.snapshot(now_ms=10**9)
    reopened = SwarmCoordinator('lab', journal=path, **kwargs)
    assert reopened.snapshot(now_ms=10**9)['state'] == final['state']
    assert reopened.snapshot(now_ms=10**9)['checkpoint_health'] == 'ok'
    assert len(list(tmp_path.glob('events.jsonl.part.*'))) + len(list((tmp_path / 'events.jsonl.archive').glob('*'))) >= 3
    full = SwarmCoordinator('lab', journal=path, **kwargs)
    assert full.recover(full_replay=True)['journal_digest'] == final['journal_digest']
    assert _digest(full.snapshot(now_ms=10**9)['state']) == _digest(final['state'])


def test_checkpoint_state_is_state_at_end_of_its_segment(tmp_path):
    path = tmp_path / 'events.jsonl'
    s = SwarmCoordinator('lab', journal=path, journal_segment_bytes=SEG)
    for op in _ops(3, 120):
        _do(s, op)
    cps = sorted(tmp_path.glob('events.jsonl.checkpoint.*.json'))
    assert cps
    for cp in cps:
        payload = json.loads(cp.read_text())
        seg = tmp_path / f"events.jsonl.part.{payload['segment_index']:08d}"
        last = json.loads(seg.read_text().splitlines()[-1])
        assert last['digest'] == payload['chain'] and last['state_digest'] == _digest(payload['state'])
        nxt = tmp_path / f"events.jsonl.part.{payload['segment_index'] + 1:08d}"
        first_next = json.loads((nxt if nxt.exists() else path).read_text().splitlines()[0])
        assert first_next['previous'] == payload['chain']


# --- crash points -------------------------------------------------------------------------

def _fill(path, n=30, **kw):
    s = SwarmCoordinator('lab', journal=path, journal_segment_bytes=SEG, **kw)
    s.ingest(hello('lab', 'a'), now_ms=1000)
    for seq in range(1, n):
        s.ingest(reading('lab', 'a', seq, 1000 + seq, float(seq)), now_ms=1000 + seq)
    return s


def _next_rotation(s, path, start):
    """Append records until the next append will rotate."""
    seq = start
    while s._journal_size < SEG:
        s.ingest(reading('lab', 'a', seq, 1000 + seq, 1.0), now_ms=1000 + seq); seq += 1
    return seq


@pytest.mark.parametrize('stage', ['checkpoint_replace', 'checkpoint_fsync', 'append_open', 'append_fsync'])
def test_crash_points_at_rotation_never_lose_or_double_apply(tmp_path, monkeypatch, stage):
    path = tmp_path / 'events.jsonl'
    s = _fill(path)
    seq = _next_rotation(s, path, 30)
    before = s.snapshot(now_ms=5000)
    real_replace, real_fsync, real_open = os.replace, os.fsync, type(path).open
    calls = {'fsync': 0}

    def bad_replace(a, b):
        if '.checkpoint.' in str(b):
            raise OSError('simulated crash at checkpoint rename')
        return real_replace(a, b)

    def bad_fsync(fd):
        calls['fsync'] += 1
        if stage == 'checkpoint_fsync' and calls['fsync'] == 1:
            raise OSError('simulated checkpoint fsync failure')
        if stage == 'append_fsync' and calls['fsync'] == 3:  # cp file, cp dir, then journal append
            raise OSError('simulated journal fsync failure')
        return real_fsync(fd)

    def bad_open(self, mode='r', *a, **k):
        if stage == 'append_open' and self == path and mode == 'a':
            raise OSError('simulated crash before append')
        return real_open(self, mode, *a, **k)

    if stage == 'checkpoint_replace':
        monkeypatch.setattr(os, 'replace', bad_replace)
    monkeypatch.setattr(os, 'fsync', bad_fsync)
    monkeypatch.setattr(type(path), 'open', bad_open)
    msg = reading('lab', 'a', seq, 1000 + seq, 42.0)
    try:
        s.ingest(msg, now_ms=1000 + seq)
        raised = False
    except OSError:
        raised = True
    monkeypatch.undo()
    assert not list(tmp_path.glob('*.tmp'))
    reopened = SwarmCoordinator('lab', journal=path, journal_segment_bytes=SEG)
    state = reopened.snapshot(now_ms=5000)
    if stage == 'append_fsync':
        # Record reached disk though the call raised: documented adoption on reload.
        assert raised and state['state']['frames']['a/s']['value'] == 42.0
    elif stage == 'append_open':
        assert raised and state['state'] == before['state']
    else:
        assert not raised and state['state']['frames']['a/s']['value'] == 42.0
    # Writes continue after restart.
    reopened.ingest(reading('lab', 'a', seq + 1, 1000 + seq + 1, 7.0), now_ms=1000 + seq + 1)
    after = reopened.snapshot(now_ms=5000)
    full = SwarmCoordinator('lab', journal=path, journal_segment_bytes=SEG)
    full.recover(full_replay=True)
    assert full.snapshot(now_ms=5000)['state'] == after['state']


def test_crash_between_retention_moves_keeps_history(tmp_path, monkeypatch):
    path = tmp_path / 'events.jsonl'
    s = _fill(path, n=40)
    expected = s.snapshot(now_ms=5000)
    real = os.replace
    moved = {'n': 0}

    def flaky(a, b):
        if '.archive' in str(b):
            moved['n'] += 1
            if moved['n'] == 2:
                raise OSError('simulated crash mid-retention')
        return real(a, b)

    monkeypatch.setattr(os, 'replace', flaky)
    s2 = SwarmCoordinator('lab', journal=path, journal_segment_bytes=SEG, journal_retention_bytes=SEG)
    seq = _next_rotation(s2, path, 100)
    s2.ingest(reading('lab', 'a', seq, 1000 + seq, 9.0), now_ms=1000 + seq)
    monkeypatch.undo()
    final = s2.snapshot(now_ms=5000)
    assert final['journal_health'] == 'ready'
    clone = SwarmCoordinator('lab', journal=path, journal_segment_bytes=SEG)
    assert clone.snapshot(now_ms=5000)['state'] == final['state']
    assert clone.recover(full_replay=True)['journal_digest'] == final['journal_digest']
    assert expected['journal_digest'] != final['journal_digest']


# --- regressions ----------------------------------------------------------------------------

def test_recover_with_pending_checkpoint_and_retention_keeps_writing(tmp_path, monkeypatch):
    """recover() writes the pending checkpoint (which may archive segments) before it
    adopts the on-disk layout, so the next write is accepted."""
    path = tmp_path / 'events.jsonl'
    kw = dict(journal_segment_bytes=SEG, journal_retention_bytes=SEG)
    # Disable checkpoints while filling, so the newest closed segment has none.
    real = SwarmCoordinator._write_checkpoint
    monkeypatch.setattr(SwarmCoordinator, '_write_checkpoint', lambda self, *a: None)
    s = SwarmCoordinator('lab', journal=path, **kw)
    s.ingest(hello('lab', 'a'), now_ms=1000)
    for seq in range(1, 40):
        s.ingest(reading('lab', 'a', seq, 1000 + seq, float(seq)), now_ms=1000 + seq)
    monkeypatch.setattr(SwarmCoordinator, '_write_checkpoint', real)
    s.recover()  # restores by full replay, then writes checkpoint + archives segments
    assert (tmp_path / 'events.jsonl.archive').is_dir()
    assert s.ingest(reading('lab', 'a', 41, 1041, 1.0), now_ms=1041)['accepted'] is True
    assert s.snapshot(now_ms=1041)['retention_health'] == 'ok'
    full = SwarmCoordinator('lab', journal=path, **kw)
    assert full.recover(full_replay=True)['journal_digest'] == s.snapshot(now_ms=1041)['journal_digest']


def test_archived_swarm_without_checkpoint_opens_and_recovers_via_service(tmp_path, monkeypatch):
    """After retention archived segments, corrupt checkpoints make startup fall back to
    a full replay including the archive; journal_recover full replay works too."""
    monkeypatch.setenv('CODONTRACE_SWARM_DIR', str(tmp_path)); service._SWARMS.clear()
    folder = tmp_path / 'lab'; folder.mkdir()
    _fill(folder / 'events.jsonl', n=60, journal_retention_bytes=2 * SEG)
    assert (folder / 'events.jsonl.archive').is_dir()
    for cp in folder.glob('events.jsonl.checkpoint.*.json'):
        cp.write_text('{}')  # e.g. torn/corrupted cache file
    try:
        # Default-sized segments in the service, but layout is still valid for it.
        expected = SwarmCoordinator('lab', journal=folder / 'events.jsonl', journal_segment_bytes=SEG).snapshot(now_ms=10**7)
        result = service.invoke('journal_recover', {'swarm_id': 'lab', 'full_replay': True}, now_ms=10**7)
        assert result['ok'] and result['result']['journal_digest'] == expected['journal_digest']
        snap = service.invoke('snapshot', {'swarm_id': 'lab'}, now_ms=10**7)['result']
        assert snap['state'] == expected['state'] and snap['journal_health'] == 'ready'
    finally:
        service._SWARMS.clear()


def test_documented_limitation_tail_truncation_is_not_detected(tmp_path):
    """Documented scope: the unkeyed chain detects edits, not removal of trailing records
    or of the active file (a consistent shorter history). See README / class docstring."""
    path = tmp_path / 'events.jsonl'
    s = _fill(path)
    full = s.snapshot(now_ms=5000)
    lines = path.read_text().splitlines(keepends=True)
    path.write_text(''.join(lines[:-2]))
    clone = SwarmCoordinator('lab', journal=path, journal_segment_bytes=SEG)
    assert clone.snapshot(now_ms=5000)['journal_digest'] != full['journal_digest']
    path.unlink()
    clone = SwarmCoordinator('lab', journal=path, journal_segment_bytes=SEG)  # silently rolled back
    assert clone.snapshot(now_ms=5000)['journal_health'] == 'ready'


# --- concurrency -----------------------------------------------------------------------------

def _writer(path, node, count, out):
    import time
    ok = 0; errors = 0
    s = None
    while s is None:
        try:
            s = SwarmCoordinator('lab', journal=path, journal_segment_bytes=SEG)
        except OSError:
            time.sleep(0.0005)
    t = 0
    while ok < count and errors < 20000:
        t += 1
        try:
            if ok == 0:
                s.ingest(hello('lab', node), now_ms=10**6 + t)
            else:
                s.ingest(reading('lab', node, ok, 10**6 + t, float(ok)), now_ms=10**6 + t)
            ok += 1
        except (OSError, ValueError):
            errors += 1
            time.sleep(0.0005)
            try:
                s = SwarmCoordinator('lab', journal=path, journal_segment_bytes=SEG)
            except OSError:
                pass
    out.put((node, ok, errors))


def test_two_processes_never_fork_the_chain(tmp_path):
    import multiprocessing as mp
    path = tmp_path / 'events.jsonl'
    SwarmCoordinator('lab', journal=path, journal_segment_bytes=SEG)
    ctx = mp.get_context('fork')
    q = ctx.Queue()
    procs = [ctx.Process(target=_writer, args=(path, n, 60, q)) for n in ('a', 'b')]
    for p in procs: p.start()
    for p in procs: p.join(120)
    results = [q.get(timeout=5) for _ in procs]
    final = SwarmCoordinator('lab', journal=path, journal_segment_bytes=SEG)
    full = SwarmCoordinator('lab', journal=path, journal_segment_bytes=SEG)
    full.recover(full_replay=True)
    assert final.snapshot(now_ms=2 * 10**6)['state'] == full.snapshot(now_ms=2 * 10**6)['state']
    assert all(ok == 60 for _, ok, _ in results), results


def test_stale_high_index_checkpoints_are_pruned_and_reopen_works(tmp_path):
    """Leftover checkpoint files from another history (e.g. after restoring an older
    backup) never evict the checkpoint just written; stale ones are deleted and
    retention trusts only a checkpoint verified against the current journal."""
    path = tmp_path / 'events.jsonl'
    kw = dict(journal_segment_bytes=SEG, journal_retention_bytes=2 * SEG)
    s = _fill(path, n=12)
    any_cp = sorted(tmp_path.glob('events.jsonl.checkpoint.*.json'))[-1]
    for idx in (98, 99):  # stale cache files whose segments are not live: ignored at load
        (tmp_path / f'events.jsonl.checkpoint.{idx:08d}.json').write_bytes(any_cp.read_bytes())
    s = SwarmCoordinator('lab', journal=path, **kw)
    for seq in range(100, 160):
        s.ingest(reading('lab', 'a', seq, 1000 + seq, 1.0), now_ms=1000 + seq)
    assert (tmp_path / 'events.jsonl.archive').is_dir()
    assert not (tmp_path / 'events.jsonl.checkpoint.00000098.json').exists()
    assert not (tmp_path / 'events.jsonl.checkpoint.00000099.json').exists()
    reopened = SwarmCoordinator('lab', journal=path, **kw)
    assert reopened.snapshot(now_ms=5000)['state'] == s.snapshot(now_ms=5000)['state']
    assert reopened.snapshot(now_ms=5000)['checkpoint_health'] == 'ok'


def test_stray_part_file_is_ignored(tmp_path):
    """Files like '<journal>.part.00000001.bak' (editor/backup copies) are ignored."""
    path = tmp_path / 'events.jsonl'
    s = _fill(path)
    (tmp_path / 'events.jsonl.part.00000001.bak').write_bytes((tmp_path / 'events.jsonl.part.00000001').read_bytes())
    (tmp_path / 'events.jsonl.part.x').write_text('junk')
    assert s.ingest(reading('lab', 'a', 500, 1500, 1.0), now_ms=1500)['accepted'] is True
    reopened = SwarmCoordinator('lab', journal=path, journal_segment_bytes=SEG)
    assert reopened.snapshot(now_ms=1500)['state'] == s.snapshot(now_ms=1500)['state']
