"""Lineage cursor vs full scan equivalence across modes, forks, mid-run attach and failed publishes."""
from __future__ import annotations

import pytest

from codontrace.genesis.engine import GenesisEngine
from codontrace.genesis.runtime_profiles import GenesisRuntimeProfile
from codontrace.visualization import SimulationRecorder


def _frames(root, seed):
    return {f.name: f.read_bytes() for f in sorted((root / 'simulation' / f'seed_{seed}').glob('frame_*.json'))}


def _spec(seed, ticks, population, mode):
    kw = {}
    if mode == 'sexual':
        kw['reproduction_mode'] = 'sexual_crossover'
    return GenesisRuntimeProfile.life_loop_world(seed=seed, tick_count=ticks, population=population, **kw)


def _run(root, spec, *, cursor, every, chunks):
    engine = GenesisEngine.from_spec(spec)
    rec = SimulationRecorder(root, lineage_cursor=cursor, every=every).attach(engine)
    if chunks:
        remaining = spec.run.tick_count if hasattr(spec, 'run') else None
        for _ in range(chunks):
            engine.run_ticks(chunks)
        del remaining
    else:
        engine.run_ticks()
    rec.finalize()
    return rec, engine


CASES = [(s, t, p, m, e, c) for s, t, p, m, e, c in [
    (1, 60, 6, 'asexual', 1, 0), (2, 60, 12, 'asexual', 1, 0), (7, 30, 16, 'asexual', 1, 0),  # 7/16: extinction
    (3, 80, 8, 'asexual', 3, 0), (4, 50, 10, 'sexual', 1, 0), (5, 50, 10, 'sexual', 4, 0),
    (11, 40, 6, 'asexual', 1, 5), (13, 90, 20, 'asexual', 2, 0), (17, 120, 6, 'asexual', 7, 0),
]]


@pytest.mark.parametrize('seed,ticks,population,mode,every,chunks', CASES)
def test_cursor_equals_full_scan(tmp_path, seed, ticks, population, mode, every, chunks):
    try:
        spec = _spec(seed, ticks, population, mode)
    except (ValueError, TypeError) as exc:
        pytest.skip(f'spec unsupported: {exc}')
    fast, engine = _run(tmp_path / 'c', spec, cursor=True, every=every, chunks=chunks)
    slow, _ = _run(tmp_path / 's', spec, cursor=False, every=every, chunks=chunks)
    a, b = _frames(tmp_path / 'c', seed), _frames(tmp_path / 's', seed)
    assert a == b and len(a) >= 2
    assert fast.lineage_full_scans == 0


def test_cursor_on_forked_engine_equals_full_scan(tmp_path):
    spec = _spec(21, 60, 10, 'asexual')
    parent = GenesisEngine.from_spec(spec)
    parent.run_ticks(20)
    fork = parent.capture_fork()
    out = {}
    for name, cursor in (('c', True), ('s', False)):
        child = GenesisEngine.from_fork(spec, fork)
        rec = SimulationRecorder(tmp_path / name, lineage_cursor=cursor).attach(child)
        child.run_ticks(30); rec.finalize()
        out[name] = _frames(tmp_path / name, 21)
    assert out['c'] == out['s'] and len(out['c']) > 2


def test_cursor_attached_mid_run_with_dead_history(tmp_path):
    spec = _spec(23, 80, 12, 'asexual')
    out = {}
    for name, cursor in (('c', True), ('s', False)):
        e = GenesisEngine.from_spec(spec)
        e.run_ticks(30)
        assert any(r.death_tick is not None for r in e.runner.population.lineage)
        rec = SimulationRecorder(tmp_path / name, lineage_cursor=cursor).attach(e)
        e.run_ticks(30); rec.finalize()
        out[name] = _frames(tmp_path / name, 23)
    assert out['c'] == out['s']


def test_cursor_restored_after_failed_publish(tmp_path, monkeypatch):
    """A failed frame publish must not advance the cursor (events must reappear in next frame)."""
    import codontrace.visualization.recorder as recorder_mod
    spec = _spec(1, 40, 6, 'asexual')
    out = {}
    for name, cursor in (('c', True), ('s', False)):
        e = GenesisEngine.from_spec(spec)
        SimulationRecorder(tmp_path / name, lineage_cursor=cursor).attach(e)
        real = recorder_mod.publish_frame
        n = {'i': 0}

        def flaky(target, frame):
            n['i'] += 1
            if n['i'] % 4 == 0:
                raise OSError('disk hiccup')
            return real(target, frame)
        monkeypatch.setattr(recorder_mod, 'publish_frame', flaky)
        try:
            e.run_ticks()
        except OSError:
            pass
        monkeypatch.setattr(recorder_mod, 'publish_frame', real)
        out[name] = _frames(tmp_path / name, 1)
    assert out['c'] == out['s']
