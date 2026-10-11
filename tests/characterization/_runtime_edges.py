"""Subprocess probe: record (importer, imported module) pairs during an import, including cached hits.

Run as ``python _runtime_edges.py CORE_JSON TARGET_JSON IMPORTS_JSON``. ``builtins.__import__`` and
``importlib.import_module`` are wrapped, so an import of an already-loaded module is still seen.
Only importers inside CORE and targets inside TARGET (and actually loaded as modules) are reported.
"""
import builtins
import importlib
import importlib.util
import json
import sys

CORE = tuple(json.loads(sys.argv[1]))
TARGET = tuple(json.loads(sys.argv[2]))
IMPORTS = json.loads(sys.argv[3])
seen = set()


def within(name, prefixes):
    return any(name == p or name.startswith(p + '.') for p in prefixes)


def note(caller, names):
    if caller and within(caller, CORE) and not within(caller, TARGET):
        seen.update((caller, n) for n in names if within(n, TARGET))


real_import = builtins.__import__
real_import_module = importlib.import_module


def hooked_import(name, globals=None, locals=None, fromlist=(), level=0):
    caller = (globals or {}).get('__name__', '')
    absolute = name
    if level:
        package = (globals or {}).get('__package__') or ''
        base = package.rsplit('.', level - 1)[0] if level > 1 else package
        absolute = f'{base}.{name}' if name else base
    note(caller, [absolute, *(f'{absolute}.{item}' for item in (fromlist or ()) if item != '*')])
    return real_import(name, globals, locals, fromlist, level)


def hooked_import_module(name, package=None):
    caller = sys._getframe(1).f_globals.get('__name__', '')
    note(caller, [importlib.util.resolve_name(name, package) if name.startswith('.') else name])
    return real_import_module(name, package)


builtins.__import__ = hooked_import
importlib.import_module = hooked_import_module
for module in IMPORTS:
    importlib.import_module(module)
print(json.dumps(sorted(edge for edge in seen if edge[1] in sys.modules)))
