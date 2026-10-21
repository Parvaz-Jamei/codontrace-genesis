"""codontrace.genesis.swarm: the pure coordinator core, used without a journal
or transport, its equivalence with the module SwarmCoordinator, and the
population adapter on a real engine population."""
from __future__ import annotations

import ast
import statistics
from pathlib import Path

import pytest

from codontrace.engine import GenesisEngine
from codontrace.genesis.runtime_profiles import GenesisRuntimeProfile
from codontrace.genesis.swarm import (
    SwarmConfig,
    SwarmCoordinatorCore,
    members_from_population,
    members_from_registry,
    robust_fuse,
)
from codontrace.genesis.swarm.population_adapter import hello_messages, reading_messages
from codontrace.genesis.swarm.trust import update_trust
from codontrace.life_loop.populations import PopulationRegistry
from codontrace.swarm.protocol import VERSION2, decode
from codontrace.swarm.runtime import SwarmCoordinator

PKG = Path(__file__).resolve().parents[1] / 'src' / 'codontrace' / 'genesis' / 'swarm'


def _msg(kind, payload, *, node='n1', boot='b1', seq=1, swarm='s1'):
    return {'schema': 'plain', 'swarm_id': swarm, 'node_id': node, 'boot_id': boot, 'seq': seq, 'kind': kind,
            'payload': payload}


HELLO = {'channels': {'t': {'quantity': 'temperature', 'unit': 'C'}}, 'operations': ['sample']}


def _reading(value, sample_ms, *, node='n1', seq=2, boot='b1'):
    return _msg('reading', {'channel': 't', 'value': value, 'sample_ms': sample_ms, 'quantity': 'temperature',
                            'unit': 'C', 'processing_version': 'v1'}, node=node, seq=seq, boot=boot)


def _core(**kw):
    return SwarmCoordinatorCore(SwarmConfig('s1', **kw))


def test_core_runs_without_journal_or_transport():
    core = _core()
    for node in ('n1', 'n2', 'n3'):
        assert core.transact('ingest', {'message': _msg('hello', HELLO, node=node)}, 100) == {'accepted': True}
    for i, node in enumerate(('n1', 'n2', 'n3')):
        core.transact('ingest', {'message': _reading(20.0 + i, 150, node=node)}, 200)
    fused = core.fuse(core.state, 'temperature', 'C', now_ms=300)
    assert fused['value'] == 21.0 and fused['count'] == 3 and fused['disagreement_mad'] == 1.0
    assert core.diagnose(core.state, 'temperature', 'C', now_ms=300, tolerance=0.5)['suspects'] == ['n1/t', 'n3/t']
    assert [m.member_id for m in core.members(core.state, 300) if m.online] == ['n1', 'n2', 'n3']
    assert [m.online for m in core.members(core.state, 200 + 10001)] == [False] * 3


def test_duplicate_is_not_recorded_and_failures_leave_state_unchanged():
    core = _core()
    core.transact('ingest', {'message': _msg('hello', HELLO)}, 100)
    before = core.state
    assert core.transact('ingest', {'message': _msg('hello', HELLO)}, 101) == {
        'accepted': False, 'reason': 'duplicate_or_reordered'}
    assert core.state is before
    with pytest.raises(ValueError, match='host clock moved backwards'):
        core.transact('status', {'status': 'paused'}, 50)
    with pytest.raises(ValueError, match='stale sample or clock skew'):
        core.transact('ingest', {'message': _reading(1.0, 100 + 2001 + 10)}, 100)
    assert core.state is before


def test_command_lifecycle_expiry_cancel_and_boot_replacement():
    core = _core()
    core.transact('ingest', {'message': _msg('hello', HELLO)}, 100)
    c1 = core.transact('command', {'node_id': 'n1', 'operation': 'sample', 'params': {'channel': 't'},
                                   'timeout_ms': 50}, 100)
    assert c1['status'] == 'pending' and c1['expires_ms'] == 150
    assert core.view(core.state, 150)['commands']['cmd-1']['status'] == 'expired'   # inclusive
    assert core.view(core.state, 149)['commands']['cmd-1']['status'] == 'pending'
    core.transact('command', {'node_id': 'n1', 'operation': 'sample', 'params': {'channel': 't'},
                              'timeout_ms': 500}, 120)
    core.transact('ingest', {'message': _msg('hello', HELLO, boot='b2')}, 130)
    # A new boot session replaces both still-pending commands (cmd-1 is due only at 150).
    assert [core.state['commands'][c]['status'] for c in ('cmd-1', 'cmd-2')] == ['boot_replaced'] * 2
    core.transact('command', {'node_id': 'n1', 'operation': 'sample', 'params': {'channel': 't'},
                              'timeout_ms': 500}, 140)
    core.transact('status', {'status': 'paused'}, 141)
    assert core.state['commands']['cmd-3']['status'] == 'cancelled'
    with pytest.raises(ValueError, match='commands require a running swarm'):
        core.transact('command', {'node_id': 'n1', 'operation': 'sample', 'params': {}, 'timeout_ms': 5}, 142)


def test_plan_is_oldest_first_and_skips_pending():
    core = _core()
    for node in ('n1', 'n2', 'n3'):
        core.transact('ingest', {'message': _msg('hello', HELLO, node=node)}, 100)
    core.transact('ingest', {'message': _reading(1.0, 150, node='n1')}, 200)
    core.transact('ingest', {'message': _reading(1.0, 190, node='n2')}, 200)
    assert core.plan(core.state, 'temperature', 'C', now_ms=300, budget=3) == [('n3', 't'), ('n1', 't'), ('n2', 't')]
    core.transact('command', {'node_id': 'n3', 'operation': 'sample', 'params': {'channel': 't'},
                              'timeout_ms': 500}, 300)
    assert core.plan(core.state, 'temperature', 'C', now_ms=300, budget=3) == [('n1', 't'), ('n2', 't')]


def test_trust_update_matches_documented_formula():
    t = update_trust(None, 10.0, 9.0, 2.0, 'ref')
    assert t == {'weight': 0.8 * 1.0 + 0.2 * (1 / (1 + 0.5)), 'samples': 1, 'reference_id': 'ref'}
    assert update_trust(t, 9.0, 9.0, 2.0, 'ref')['weight'] == 0.8 * t['weight'] + 0.2 * 1.0


def test_robust_fuse_rejects_mixed_semantics_and_zero_weight():
    a = {'value': 1.0, 'sample_ms': 10, 'quality': 0, 'sensor_descriptor': {'feature_id': 'x'}}
    b = {'value': 2.0, 'sample_ms': 10, 'sensor_descriptor': {'feature_id': 'y'}}
    assert robust_fuse({'a': a, 'b': b}, {}, 'q', 'u')['status'] == 'incompatible_measurement_semantics'
    assert robust_fuse({'a': a}, {}, 'q', 'u', mode='calibrated')['status'] == 'zero_weight'
    with pytest.raises(ValueError, match='unknown fusion mode'):
        robust_fuse({}, {}, 'q', 'u', mode='trimmed')


def _wire(kind, payload, seq, boot='b1', node='n1'):
    return {'schema': 'genesis_swarm_v1', 'swarm_id': 's1', 'node_id': node, 'boot_id': boot, 'seq': seq,
            'kind': kind, 'payload': payload}


def test_module_coordinator_and_core_reach_the_same_state():
    """The module composes the core: same actions, same state and results."""
    module = SwarmCoordinator('s1')
    core = SwarmCoordinatorCore(SwarmConfig('s1'), decode=decode, typed_schema=VERSION2,
                                command_params=SwarmCoordinator._command_params)
    hello = {'wifi': True, 'channels': {'t': {'quantity': 'temperature', 'unit': 'C'}}, 'operations': ['sample']}
    script = [('ingest', {'message': decode(_wire('hello', hello, 1))}, 100),
              ('ingest', {'message': decode(_wire('reading', {'channel': 't', 'value': 3.5, 'sample_ms': 120,
                                                              'processing_version': 'v1'}, 2))}, 130),
              ('command', {'node_id': 'n1', 'operation': 'sample', 'params': {'channel': 't'},
                           'timeout_ms': 40}, 140),
              ('trust', {'key': 'n1/t', 'reference': 3.0, 'reference_id': 'r1', 'scale': 1.0}, 150),
              ('boundary', {'row': {'generation': 1}}, 200),
              ('status', {'status': 'paused'}, 210)]
    for action, args, now in script:
        assert module._transaction(action, args, now) == core.transact(action, args, now)
    assert module._state == core.state
    assert module.snapshot(now_ms=220)['state'] == core.view(core.state, 220)


def test_members_from_a_real_engine_population():
    engine = GenesisEngine.from_spec(GenesisRuntimeProfile.life_loop_world(seed=7, tick_count=2, population=4))
    engine.run_ticks()
    population = engine.runner.population
    members = members_from_population(population)
    organisms = [m for m in members if m.kind == 'organism']
    assert [m.member_id for m in organisms] == [o.id for o in population.organisms]
    assert all(m.generation == population.generation and m.energy is not None for m in organisms)
    core = SwarmCoordinatorCore(SwarmConfig('pop'))
    for message in hello_messages(organisms, 'pop'):
        core.transact('ingest', {'message': message}, 1000)
    energy = {m.member_id: m.energy for m in organisms}
    for message in reading_messages(organisms, energy, 'pop', sample_ms=1000):
        core.transact('ingest', {'message': message}, 1000)
    fused = core.fuse(core.state, 'energy', 'atp', now_ms=1000)
    assert fused['count'] == len(organisms)
    assert fused['value'] == statistics.median(energy.values())


def test_members_from_registry():
    registry = PopulationRegistry().create_population('alpha', member_ids=('o2', 'o1'))
    members = members_from_registry(registry)
    assert [(m.member_id, m.kind, m.group_id) for m in members] == [
        ('o1', 'organism', 'alpha'), ('o2', 'organism', 'alpha'), ('alpha', 'population', None)]


def test_genesis_swarm_imports_no_module_or_transport():
    allowed = ('codontrace.contracts', 'codontrace.genesis', 'codontrace.life_loop')
    for path in PKG.glob('*.py'):
        for node in ast.walk(ast.parse(path.read_text(encoding='utf-8'))):
            names = ([a.name for a in node.names] if isinstance(node, ast.Import)
                     else [node.module or ''] if isinstance(node, ast.ImportFrom) and node.level == 0 else [])
            for name in names:
                assert not name.startswith('codontrace') or name.startswith(allowed), (path.name, name)
                assert not name.startswith(('codontrace.genesis.swarm_', 'paho')) or name == \
                    'codontrace.genesis.swarm_metrics', (path.name, name)
