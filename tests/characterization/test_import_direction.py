"""Layer contract: engine core never depends on modules, transports or UI.

Plan section 3.2: ``codontrace.{engine*, rng, world, replay, contracts,
life_loop, genesis}`` must not import ``codontrace.{swarm, console,
visualization, claimgate.adapters, campaigns}`` or ``paho``. Checked
statically (AST, direct and transitive, see ``_imports``) and at runtime in a
clean interpreter.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from ._imports import SRC, chains, graph, resolved_edges, within

ENGINE_CORE = ('codontrace.engine', 'codontrace.engine_spec', 'codontrace.engine_runtime',
               'codontrace.engine_results', 'codontrace.engine_digest', 'codontrace.engine_run_result',
               'codontrace.engine_claims', 'codontrace.rng', 'codontrace.world', 'codontrace.replay',
               'codontrace.contracts', 'codontrace.life_loop', 'codontrace.genesis')
# Modules, transports and UI. ``claimgate.adapters.esp32_bridge`` holds device transports.
MODULES = ('codontrace.swarm', 'codontrace.console', 'codontrace.visualization', 'codontrace.campaigns',
           'codontrace.causal_inference', 'codontrace.preregistration', 'paho')
ADAPTERS = ('codontrace.claimgate.adapters',)

# Pre-existing exceptions (import-linter ``ignore_imports`` style), present at
# feat/swarm-atlas-v5 @ 03c14b0. They are host-parasite campaign drivers that
# live in genesis/ and attach ClaimGate bundles. The list may only shrink:
# ``test_adapter_exceptions_are_exact`` fails on new and on stale entries.
_HP = 'codontrace.claimgate.adapters.host_parasite'
KNOWN_ADAPTER_EDGES = frozenset({
    ('codontrace.genesis.host_parasite_attach_registry', _HP),
    *((f'codontrace.genesis.{name}', target)
      for name in ('host_parasite_cell_microbe_hard_campaigns', 'host_parasite_diff_campaigns',
                   'host_parasite_sim_fidelity_campaigns', 'host_parasite_wave6_smoke')
      for target in (_HP, _HP + '_prereg')),
})


# Runtime edges seen by ``_runtime_edges`` while importing CORE_IMPORTS: the
# host-parasite drivers. (genesis.replay_integrity used to load esp32_bridge
# through its digest-class registry; STRDisparityResult now lives in
# genesis.transferability.)
# Exact and shrink-only: a new runtime edge (static or dynamic) fails, and so
# does a removed one until this set is updated.
KNOWN_RUNTIME_ADAPTER_EDGES = frozenset({
    *((f'codontrace.genesis.{name}', target)
      for name in ('host_parasite_cell_microbe_hard_campaigns', 'host_parasite_diff_campaigns',
                   'host_parasite_sim_fidelity_campaigns', 'host_parasite_wave6_smoke')
      for target in (_HP, _HP + '_prereg')),
})

# Wrong-direction edges from plan section 1b. P1 moved the validators to
# contracts.wire_validation, so both sets are empty; they stay exact so a new
# edge fails (add to them only with a reviewed, documented reason).
KNOWN_VISUALIZATION_SWARM_EDGES: frozenset[tuple[str, str]] = frozenset()
KNOWN_CONSOLE_PROTOCOL_EDGES: frozenset[tuple[str, str]] = frozenset()


def _fmt(found):
    return '\n'.join(' -> '.join(chain) for chain in found)


def test_engine_core_modules_exist():
    known = graph()
    for name in ENGINE_CORE:
        assert name in known, f'{name} moved; update ENGINE_CORE'
    for name in MODULES[:-1]:
        assert name in known, f'{name} moved; update MODULES'


def test_scanner_detects_lazy_relative_and_dynamic_imports(tmp_path, monkeypatch):
    """Guard the guard: a planted violation in each import form is reported."""
    from . import _imports
    pkg = tmp_path / 'codontrace'
    (pkg / 'core').mkdir(parents=True); (pkg / 'mod').mkdir()
    for p in (pkg, pkg / 'core', pkg / 'mod'):
        (p / '__init__.py').write_text('')
    (pkg / 'mod' / 'x.py').write_text('')
    (pkg / 'core' / 'lazy.py').write_text('def f():\n    import codontrace.mod.x\n')
    (pkg / 'core' / 'rel.py').write_text('from ..mod import x\n')
    (pkg / 'core' / 'dyn.py').write_text('import importlib\nimportlib.import_module("codontrace.mod.x")\n')
    (pkg / 'core' / 'via.py').write_text('from codontrace.core import helper\n')
    (pkg / 'core' / 'helper.py').write_text('from codontrace import mod\n')
    (pkg / 'core' / 'clean.py').write_text('import json\n')
    monkeypatch.setattr(_imports, 'SRC', tmp_path); monkeypatch.setattr(_imports, 'PACKAGE', pkg)
    _imports.graph.cache_clear()
    try:
        found = {c[0]: c for c in _imports.chains(('codontrace.core',), ('codontrace.mod',))}
    finally:
        _imports.graph.cache_clear()
    assert set(found) == {'codontrace.core.lazy', 'codontrace.core.rel', 'codontrace.core.dyn',
                          'codontrace.core.via', 'codontrace.core.helper'}
    assert found['codontrace.core.via'] == ['codontrace.core.via', 'codontrace.core.helper', 'codontrace.mod']


def test_engine_core_does_not_import_modules_transport_or_ui():
    found = chains(ENGINE_CORE, MODULES)
    assert not found, 'engine core reaches a module/transport/UI package:\n' + _fmt(found)


def test_engine_core_does_not_import_claimgate_adapters():
    found = chains(ENGINE_CORE, ADAPTERS, ignored=KNOWN_ADAPTER_EDGES)
    assert not found, 'engine core reaches claimgate.adapters:\n' + _fmt(found)


def test_adapter_exceptions_are_exact():
    actual = {(m, t) for m in graph() if within(m, ENGINE_CORE) for t in resolved_edges(m) if within(t, ADAPTERS)}
    assert actual == set(KNOWN_ADAPTER_EDGES), (
        f'new: {sorted(actual - KNOWN_ADAPTER_EDGES)}; stale (delete them): {sorted(KNOWN_ADAPTER_EDGES - actual)}')


def _loaded_after(imports: list[str]) -> list[str]:
    code = ('import json, sys\n' + ''.join(f'import {m}\n' for m in imports) +
            'print(json.dumps(sorted(sys.modules)))')
    out = subprocess.run([sys.executable, '-c', code], capture_output=True, text=True, check=True,
                         cwd=SRC.parent, env={'PYTHONPATH': str(SRC), 'PATH': '/usr/bin:/bin'})
    return json.loads(out.stdout.strip().splitlines()[-1])


CORE_IMPORTS = ['codontrace.engine', 'codontrace.rng', 'codontrace.world', 'codontrace.replay',
                'codontrace.contracts', 'codontrace.life_loop', 'codontrace.genesis']


def test_runtime_engine_import_loads_no_module_transport_or_ui():
    loaded = _loaded_after(CORE_IMPORTS)
    assert [m for m in loaded if within(m, MODULES)] == []


def _runtime_edges(imports: list[str], targets: tuple[str, ...]) -> set[tuple[str, str]]:
    probe = Path(__file__).with_name('_runtime_edges.py')
    out = subprocess.run([sys.executable, str(probe), json.dumps(ENGINE_CORE), json.dumps(targets), json.dumps(imports)],
                         capture_output=True, text=True, check=True, cwd=SRC.parent,
                         env={'PYTHONPATH': str(SRC), 'PATH': '/usr/bin:/bin'})
    return {tuple(edge) for edge in json.loads(out.stdout.strip().splitlines()[-1])}


def test_runtime_claimgate_adapter_edges_are_exact():
    actual = _runtime_edges(CORE_IMPORTS, ADAPTERS)
    assert actual == set(KNOWN_RUNTIME_ADAPTER_EDGES), (
        f'new: {sorted(actual - KNOWN_RUNTIME_ADAPTER_EDGES)}; stale: {sorted(KNOWN_RUNTIME_ADAPTER_EDGES - actual)}')


def test_runtime_edge_probe_sees_cached_and_dynamic_imports(tmp_path):
    """Guard the guard: imports of already-loaded modules, by name or dynamically, are still recorded."""
    pkg = tmp_path / 'probe_core'
    pkg.mkdir()
    (pkg / '__init__.py').write_text('')
    (pkg / 'a.py').write_text('import json\n')
    (pkg / 'b.py').write_text('import importlib\nimportlib.import_module("j" + "son")\nfrom json import decoder\n')
    probe = Path(__file__).with_name('_runtime_edges.py')
    out = subprocess.run([sys.executable, str(probe), json.dumps(['probe_core']), json.dumps(['json']),
                          json.dumps(['probe_core.a', 'probe_core.b'])], capture_output=True, text=True, check=True,
                         env={'PYTHONPATH': str(tmp_path), 'PATH': '/usr/bin:/bin'})
    edges = {tuple(e) for e in json.loads(out.stdout.strip().splitlines()[-1])}
    assert edges == {('probe_core.a', 'json'), ('probe_core.b', 'json'), ('probe_core.b', 'json.decoder')}


def test_swarm_and_visualization_import_without_paho():
    """paho stays lazy: only the MQTT bridge functions import it."""
    loaded = _loaded_after(['codontrace.swarm', 'codontrace.visualization', 'codontrace.swarm.mqtt',
                            'codontrace.claimgate.adapters.esp32_bridge'])
    assert [m for m in loaded if within(m, ('paho',))] == []


def _direct_edges(sources: tuple[str, ...], targets: tuple[str, ...]) -> set[tuple[str, str]]:
    return {(m, t) for m in graph() if within(m, sources) for t in resolved_edges(m) if within(t, targets)}


def test_visualization_swarm_edges_are_exact():
    actual = _direct_edges(('codontrace.visualization',), ('codontrace.swarm',))
    assert actual == set(KNOWN_VISUALIZATION_SWARM_EDGES), (
        f'new: {sorted(actual - KNOWN_VISUALIZATION_SWARM_EDGES)}; '
        f'stale: {sorted(KNOWN_VISUALIZATION_SWARM_EDGES - actual)}')
    # No other path: with the known edges ignored, visualization reaches no swarm module.
    found = chains(('codontrace.visualization',), ('codontrace.swarm',), ignored=KNOWN_VISUALIZATION_SWARM_EDGES)
    assert not found, _fmt(found)


def test_console_protocol_edges_are_exact():
    """Console -> swarm (service, routes) is fine; console -> swarm.protocol validators is not."""
    actual = _direct_edges(('codontrace.console',), ('codontrace.swarm.protocol',))
    assert actual == set(KNOWN_CONSOLE_PROTOCOL_EDGES), (
        f'new: {sorted(actual - KNOWN_CONSOLE_PROTOCOL_EDGES)}; stale: {sorted(KNOWN_CONSOLE_PROTOCOL_EDGES - actual)}')


def test_console_simulation_does_not_import_swarm():
    found = chains(('codontrace.console.simulation',), ('codontrace.swarm',))
    assert not found, _fmt(found)


def test_wire_validation_imports_nothing_from_the_engine():
    assert [t for t in resolved_edges('codontrace.contracts.wire_validation') if within(t, ('codontrace',))] == []
