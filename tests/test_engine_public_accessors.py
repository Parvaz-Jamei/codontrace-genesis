"""Read-only engine accessors used by observers instead of private lists."""
from __future__ import annotations

import ast
from pathlib import Path

from codontrace.engine import GenesisEngine
from codontrace.genesis.runtime_profiles import GenesisRuntimeProfile

ROOT = Path(__file__).resolve().parents[1]
PRIVATE = {'_tick_results', '_snapshots'}
OWNER = ROOT / 'src' / 'codontrace' / 'engine_runtime.py'


def _engine(ticks: int = 0) -> GenesisEngine:
    engine = GenesisEngine.from_spec(GenesisRuntimeProfile.life_loop_world(seed=7, tick_count=4, population=4))
    if ticks:
        engine.run_ticks(ticks)
    return engine


def test_fresh_engine():
    engine = _engine()
    assert engine.tick_results == ()
    assert engine.latest_snapshot is engine._snapshots[-1]
    assert engine.latest_snapshot.generation == engine.runner.population.generation
    assert engine.world_digest() == engine.snapshot().world_digest == engine.runner.world.digest()


def test_accessors_follow_committed_ticks():
    engine = _engine(3)
    assert isinstance(engine.tick_results, tuple)
    assert engine.tick_results == tuple(engine._tick_results)
    assert len(engine.tick_results) == 3
    assert engine.latest_snapshot is engine._snapshots[-1]
    assert engine.latest_snapshot.generation == engine.runner.population.generation
    assert engine.tick_results[-1].generation_result.world_after_digest == engine.world_digest()


def test_tick_results_is_a_copy():
    engine = _engine(2)
    view = engine.tick_results
    engine.run_ticks(1)
    assert len(view) == 2 and len(engine.tick_results) == 3


def test_accessors_after_fork_restore():
    engine = _engine(2)
    spec = engine.spec
    restored = GenesisEngine.from_fork(spec, engine.capture_fork())
    assert restored.tick_results == ()
    assert restored.latest_snapshot is None
    assert restored.world_digest() == engine.world_digest()
    restored.run_ticks(1)
    assert len(restored.tick_results) == 1
    assert restored.latest_snapshot is not None


def test_accessors_add_nothing_to_digests():
    a, b = _engine(2), _engine(2)
    _ = (b.tick_results, b.latest_snapshot, b.world_digest())
    assert a.run_ticks(0).digest() == b.run_ticks(0).digest()


def _private_uses(path: Path) -> list[tuple[int, str]]:
    tree = ast.parse(path.read_text(encoding='utf-8'), filename=str(path))
    return [(node.lineno, node.attr) for node in ast.walk(tree)
            if isinstance(node, ast.Attribute) and node.attr in PRIVATE]


def test_no_private_engine_lists_outside_engine_runtime():
    found = []
    for base in (ROOT / 'src' / 'codontrace', ROOT / 'scripts'):
        for path in sorted(base.rglob('*.py')):
            if path == OWNER:
                continue
            found += [f'{path.relative_to(ROOT)}:{line} {attr}' for line, attr in _private_uses(path)]
    assert found == []


def test_private_scan_sees_a_planted_use(tmp_path):
    planted = tmp_path / 'x.py'
    planted.write_text('def f(engine):\n    return engine._tick_results, getattr(engine, "y")._snapshots\n')
    assert [attr for _, attr in _private_uses(planted)] == ['_tick_results', '_snapshots']
