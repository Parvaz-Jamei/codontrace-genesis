"""Characterization: SimulationRecorder frame bytes for a small fixed run.

Pins the published ``genesis_simulation_frame_v1`` files (exact serializer
bytes) for ``life_loop_world(seed=7, tick_count=4, population=4)``. The full
lineage scan (``lineage_cursor=False``) must produce the same bytes as the
incremental cursor.
"""
from __future__ import annotations

from codontrace.engine import GenesisEngine
from codontrace.genesis.runtime_profiles import GenesisRuntimeProfile
from codontrace.visualization import SimulationRecorder

from ._golden import check_json, check_tree


def _record(root, **kw):
    engine = GenesisEngine.from_spec(GenesisRuntimeProfile.life_loop_world(seed=7, tick_count=4, population=4))
    recorder = SimulationRecorder(root, **kw).attach(engine)
    result = engine.run_ticks()
    return recorder.finalize(), result


def test_recorder_frames_match_golden_bytes(tmp_path):
    final, result = _record(tmp_path / 'run')
    frames = tmp_path / 'run' / 'simulation' / 'seed_7'
    assert len(list(frames.glob('frame_*.json'))) == 5  # initial + 4 generations
    check_tree('simulation_frames_seed7', frames)
    check_json('simulation_frames_seed7_run.json', {'final_frame_generation': final['generation'],
                                                     'result_digest': result.digest(),
                                                     'snapshot_digest': result.snapshot.digest()})


def test_full_scan_frames_equal_cursor_frames(tmp_path):
    _record(tmp_path / 'cursor')
    _record(tmp_path / 'full', lineage_cursor=False)
    a = tmp_path / 'cursor' / 'simulation' / 'seed_7'
    b = tmp_path / 'full' / 'simulation' / 'seed_7'
    assert {p.name: p.read_bytes() for p in a.iterdir()} == {p.name: p.read_bytes() for p in b.iterdir()}
