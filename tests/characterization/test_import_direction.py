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

import pytest

from ._imports import SRC, chains, graph, resolved_edges, within

ENGINE_CORE = ('codontrace.engine', 'codontrace.engine_spec', 'codontrace.engine_runtime',
               'codontrace.engine_results', 'codontrace.engine_digest', 'codontrace.engine_run_result',
               'codontrace.engine_claims', 'codontrace.rng', 'codontrace.world', 'codontrace.replay',
               'codontrace.contracts', 'codontrace.life_loop', 'codontrace.genesis')
# Modules, transports and UI. ``claimgate.adapters.esp32_bridge`` holds device transports.
MODULES = ('codontrace.swarm', 'codontrace.console', 'codontrace.visualization', 'codontrace.campaigns', 'paho')
ADAPTERS = ('codontrace.claimgate.adapters',)

# Pre-existing exceptions (import-linter ``ignore_imports`` style), present at
# feat/swarm-atlas-v5 @ 03c14b0. They are host-parasite campaign drivers that
# live in genesis/ and attach ClaimGate bundles. The list may only shrink:
# ``test_adapter_exceptions_are_exact`` fails on new and on stale entries.
_HP = 'codontrace.claimgate.adapters.host_parasite'
KNOWN_ADAPTER_EDGES = frozenset({
    ('codontrace.genesis.host_parasite_attach_registry', 'codontrace.claimgate.adapters'),
    ('codontrace.genesis.host_parasite_attach_registry', _HP),
    *((f'codontrace.genesis.{name}', target)
      for name in ('host_parasite_cell_microbe_hard_campaigns', 'host_parasite_diff_campaigns',
                   'host_parasite_sim_fidelity_campaigns', 'host_parasite_wave6_smoke')
      for target in (_HP, _HP + '_prereg')),
})


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


@pytest.mark.xfail(strict=True, reason='pre-existing: genesis.replay_integrity resolves its digest-class registry '
                   'with import_module at import time, which loads codontrace.claimgate.adapters '
                   '(including esp32_bridge). Not visible to the AST scan; tracked for a later phase.')
def test_runtime_engine_import_loads_no_claimgate_adapters():
    loaded = _loaded_after(CORE_IMPORTS)
    assert [m for m in loaded if within(m, ADAPTERS)] == []


def test_swarm_and_visualization_import_without_paho():
    """paho stays lazy: only the MQTT bridge functions import it."""
    loaded = _loaded_after(['codontrace.swarm', 'codontrace.visualization', 'codontrace.swarm.mqtt',
                            'codontrace.claimgate.adapters.esp32_bridge'])
    assert [m for m in loaded if within(m, ('paho',))] == []


def test_visualization_does_not_import_swarm():
    found = chains(('codontrace.visualization',), ('codontrace.swarm',))
    assert not found, _fmt(found)


def test_console_simulation_does_not_import_swarm():
    found = chains(('codontrace.console.simulation',), ('codontrace.swarm',))
    assert not found, _fmt(found)


def test_wire_validation_imports_nothing_from_the_engine():
    assert [t for t in resolved_edges('codontrace.contracts.wire_validation') if within(t, ('codontrace',))] == []
