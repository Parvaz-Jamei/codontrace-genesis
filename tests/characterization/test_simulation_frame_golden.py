"""Characterization: SimulationRecorder frame bytes for a small fixed run.

Pins the published ``genesis_simulation_frame_v1`` files (exact serializer
bytes) for ``life_loop_world(seed=7, tick_count=4, population=4)``. The full
lineage scan (``lineage_cursor=False``) must produce the same bytes as the
incremental cursor.
"""
from __future__ import annotations

from codontrace.engine import GenesisEngine
from codontrace.engine_digest import _digest
from codontrace.genesis.runtime_profiles import GenesisRuntimeProfile
from codontrace.visualization import SimulationRecorder

from ._golden import check_json, check_tree


def _record(root, **kw):
    engine = GenesisEngine.from_spec(GenesisRuntimeProfile.life_loop_world(seed=7, tick_count=4, population=4))
    recorder = SimulationRecorder(root, **kw).attach(engine)
    result = engine.run_ticks()
    return recorder.finalize(), result


def test_recorder_frames_match_golden_bytes(tmp_path, neutral_source_digest):
    final, result = _record(tmp_path / 'run')
    frames = tmp_path / 'run' / 'simulation' / 'seed_7'
    assert len(list(frames.glob('frame_*.json'))) == 5  # initial + 4 generations
    check_tree('simulation_frames_seed7', frames)
    check_json('simulation_frames_seed7_run.json', {'final_frame_generation': final['generation'],
                                                     # Core payload, not result.digest(): see test_engine_pins.
                                                     'core_digest': _digest(result._core_payload()),
                                                     'tick_digests': [t.digest() for t in result.ticks],
                                                     'snapshot_digest': result.snapshot.digest()})


def test_full_scan_frames_equal_cursor_frames(tmp_path):
    _record(tmp_path / 'cursor')
    _record(tmp_path / 'full', lineage_cursor=False)
    a = tmp_path / 'cursor' / 'simulation' / 'seed_7'
    b = tmp_path / 'full' / 'simulation' / 'seed_7'
    assert {p.name: p.read_bytes() for p in a.iterdir()} == {p.name: p.read_bytes() for p in b.iterdir()}


def test_synthetic_two_parent_frames_golden():
    """Hand-written population records that reach every link kind and interval edge.

    The seed-7 run has no two-parent births, so this pins ``two_parent_birth``
    links, historical sources (parent only in the previous frame), and births and
    deaths exactly at the interval end (``previous_tick < t <= tick``).
    """
    from codontrace.visualization.frames import frame_from_population

    world = {'width': 8, 'height': 8}

    def agent(aid, x, y, atp=None):
        return {'organism_id': aid, 'position': [x, y], 'runtime_atp': atp, 'genome_digest': 'g-' + aid}

    first = frame_from_population({'generation': 0, 'tick': 0, 'agents': [agent('p', 1, 1, 2.5), agent('q', 2, 2),
                                                                         agent('r', 3, 3, 1.0)],
                                   'lineage': [{'organism_id': i} for i in 'pqr']}, world, run_id='synthetic', seed=1)
    lineage = [{'organism_id': 'p', 'death_tick': 5}, {'organism_id': 'q'}, {'organism_id': 'r', 'death_tick': 6},
               {'organism_id': 'c1', 'parent_id': 'p', 'second_parent_id': 'q', 'birth_tick': 5},
               {'organism_id': 'c2', 'parent_id': 'q', 'second_parent_id': 'q', 'birth_tick': 1},
               {'organism_id': 'c3', 'parent_id': 'r', 'birth_tick': 6}]
    second = frame_from_population({'generation': 1, 'tick': 5, 'agents': [agent('q', 2, 3), agent('r', 3, 3),
                                                                          agent('c1', 4, 4, 0.5), agent('c2', 5, 5)],
                                    'lineage': lineage}, world, run_id='synthetic', seed=1,
                                   summary={'births': 2, 'deaths': 1, 'after_count': 4}, previous=first)
    assert second['metrics']['two_parent_births'] == 1
    check_json('simulation_frames_synthetic.json', [first, second])
