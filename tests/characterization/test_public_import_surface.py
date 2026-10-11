"""Import surface: every public name of the modules being refactored stays importable.

The golden list records, per module, ``__all__`` when defined plus every other
public (non-underscore, non-module) top-level attribute. Later phases replace
code with re-export shims; removals fail here, additions are allowed.
``public_signatures.json`` also pins ``inspect.signature`` of every public
function defined in codontrace: a function that is still listed must keep its
parameters (names, kinds, defaults, annotation text).
"""
from __future__ import annotations

import importlib
import inspect
import pkgutil
import types

import pytest

from ._golden import check_json, load_json, updating

ROOTS = ('codontrace.swarm', 'codontrace.visualization')
SINGLE = ('codontrace.claimgate.adapters.esp32_bridge', 'codontrace.engine', 'codontrace.rng',
          'codontrace.life_loop.conformal_bands', 'codontrace.life_loop.farm_orchestrator',
          'codontrace.genesis.qd_search', 'codontrace.genesis.selection', 'codontrace.genesis.artifacts')
GOLDEN = 'public_import_surface.json'
SIGNATURES = 'public_signatures.json'
_TYPING_MODULES = ('typing', 'typing_extensions', 'collections.abc', '_collections_abc', 'types', '__future__')


def _modules() -> list[str]:
    names = list(SINGLE)
    for root in ROOTS:
        package = importlib.import_module(root)
        names.append(root)
        names += [f'{root}.{info.name}' for info in pkgutil.iter_modules(package.__path__)]
    return sorted(names)


def _own(value: object) -> bool:
    """Defined in codontrace (classes, functions) or a module-level constant of any type.

    Callables merely imported from the stdlib or typing (``Path``, ``Any``) are
    not part of the surface; dropping such an import must not fail this test.
    Constants count whatever their type (``re.Pattern``, ``Decimal``,
    ``frozenset``), except typing helper objects.
    """
    if isinstance(value, types.ModuleType):
        return False
    if callable(value):
        return str(getattr(value, '__module__', '')).startswith('codontrace')
    return type(value).__module__ not in _TYPING_MODULES


def _surface(name: str) -> dict[str, list[str]]:
    module = importlib.import_module(name)
    public = sorted(k for k, v in vars(module).items() if not k.startswith('_') and _own(v))
    return {'__all__': sorted(getattr(module, '__all__', [])), 'public': public}


def test_public_surface_golden_is_current_or_subset():
    current = {name: _surface(name) for name in _modules()}
    if updating():
        check_json(GOLDEN, current)
        return
    golden = load_json(GOLDEN)
    missing_modules = sorted(set(golden) - set(current))
    assert not missing_modules, f'modules disappeared: {missing_modules}'
    problems = []
    for name, surface in golden.items():
        if surface['__all__'] != current[name]['__all__'] and not set(surface['__all__']) <= set(current[name]['__all__']):
            problems.append(f"{name}.__all__ lost {sorted(set(surface['__all__']) - set(current[name]['__all__']))}")
        lost = sorted(set(surface['public']) - set(current[name]['public']))
        if lost:
            problems.append(f'{name} lost {lost}')
    assert not problems, '\n'.join(problems)


def _signatures(name: str) -> dict[str, str]:
    module = importlib.import_module(name)
    out = {}
    for key, value in vars(module).items():
        if key.startswith('_') or not inspect.isfunction(value) or not value.__module__.startswith('codontrace'):
            continue
        out[key] = str(inspect.signature(value))
    return dict(sorted(out.items()))


def test_public_function_signatures_are_kept():
    current = {name: _signatures(name) for name in _modules()}
    if updating():
        check_json(SIGNATURES, current)
        return
    golden = load_json(SIGNATURES)
    problems = [f'{module}.{fn}: {sig} -> {current.get(module, {}).get(fn)}'
                for module, functions in golden.items() for fn, sig in functions.items()
                if fn in current.get(module, {}) and current[module][fn] != sig]
    assert not problems, '\n'.join(problems)


@pytest.mark.parametrize('name', sorted(set(SINGLE) | set(ROOTS)))
def test_all_names_resolve(name):
    module = importlib.import_module(name)
    for attr in getattr(module, '__all__', ()):
        assert hasattr(module, attr), f'{name}.{attr}'
