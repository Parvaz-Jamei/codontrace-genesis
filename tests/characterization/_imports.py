"""Static import graph of ``src/codontrace`` built from the AST (no third-party linter).

Semantics follow import-linter's ``forbidden`` contract: a source package and
all its descendants must not import a forbidden package or any descendant,
directly or through a chain of other in-repo modules. Every ``import`` /
``from … import`` node counts, including imports inside functions and
``TYPE_CHECKING`` blocks, relative imports are resolved, and
``importlib.import_module('literal')`` / ``__import__('literal')`` calls with a
literal string are included. Imports computed from variables cannot be seen
statically; a runtime ``sys.modules`` check complements this scan.
"""
from __future__ import annotations

import ast
from collections import deque
from functools import cache
from pathlib import Path

SRC = Path(__file__).resolve().parents[2] / 'src'
PACKAGE = SRC / 'codontrace'


def module_name(path: Path) -> str:
    parts = list(path.relative_to(SRC).with_suffix('').parts)
    if parts[-1] == '__init__':
        parts = parts[:-1]
    return '.'.join(parts)


def _imports(path: Path) -> set[str]:
    name = module_name(path)
    package = name.split('.') if path.name == '__init__.py' else name.split('.')[:-1]
    found: set[str] = set()
    for node in ast.walk(ast.parse(path.read_text(encoding='utf-8'), filename=str(path))):
        if isinstance(node, ast.Import):
            found.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                base = package[:len(package) - (node.level - 1)]
                target = '.'.join(base + ([node.module] if node.module else []))
            else:
                target = node.module or ''
            found.add(target)
            # ``from pkg import sub`` may import the submodule ``pkg.sub``.
            found.update(f'{target}.{alias.name}' for alias in node.names if alias.name != '*')
        elif isinstance(node, ast.Call) and node.args and isinstance(node.args[0], ast.Constant) \
                and isinstance(node.args[0].value, str):
            func = node.func
            called = func.attr if isinstance(func, ast.Attribute) else getattr(func, 'id', None)
            if called in ('import_module', '__import__'):
                found.add(node.args[0].value)
    return {f for f in found if f}


@cache
def graph() -> dict[str, frozenset[str]]:
    """Module -> raw imported names (internal and external)."""
    return {module_name(p): frozenset(_imports(p)) for p in sorted(PACKAGE.rglob('*.py'))}


def resolve(name: str) -> str | None:
    """Most specific in-repo module for an imported dotted name, else None."""
    known = graph()
    while name not in known:
        if '.' not in name:
            return None
        name = name.rsplit('.', 1)[0]
    return name


def within(name: str, prefixes: tuple[str, ...]) -> bool:
    return any(name == p or name.startswith(p + '.') for p in prefixes)


def resolved_edges(module: str) -> set[str]:
    """Imported names of ``module`` mapped to in-repo modules; external names are kept as written."""
    return {resolve(d) or d for d in graph().get(module, ())} - {module}


def chains(sources: tuple[str, ...], forbidden: tuple[str, ...],
           ignored: frozenset[tuple[str, str]] = frozenset()) -> list[list[str]]:
    """One shortest offending import chain per source module (direct or indirect).

    ``ignored`` holds exact (importer, resolved imported module) edges removed
    from the graph, like import-linter's ``ignore_imports``.
    """
    edges = {m: sorted(t for t in resolved_edges(m) if (m, t) not in ignored) for m in graph()}
    found = []
    for start in sorted(m for m in edges if within(m, sources)):
        parent: dict[str, str | None] = {start: None}
        queue = deque([start])
        while queue:
            current = queue.popleft()
            direct = [t for t in edges.get(current, ()) if within(t, forbidden)]
            if direct:
                chain = [direct[0]]
                node: str | None = current
                while node is not None:
                    chain.append(node); node = parent[node]
                found.append(chain[::-1])
                break
            for nxt in edges.get(current, ()):
                if nxt in edges and nxt not in parent:
                    parent[nxt] = current; queue.append(nxt)
    return found
