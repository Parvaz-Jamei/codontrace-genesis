"""P11: engine-integration docs point at real files and modules; experimental API rows import."""
from __future__ import annotations

import importlib
import re
from pathlib import Path

import pytest

from codontrace.genesis.public_api_manifest import build_public_api_manifest, import_public_symbol

ROOT = Path(__file__).resolve().parents[1]
DOCS = ('docs/ENGINE_REPLAY_CONTRACT.md', 'docs/ARCHITECTURE_PORTS.md', 'docs/swarm/ENGINE_SECTIONS.md',
        'docs/swarm/README_FA.md')
_LINK = re.compile(r'\]\(([^)#\s]+)(?:#[^)]*)?\)')
_PATH = re.compile(r'`((?:src|tests|docs)/[^`*]+)`')
_MODULE = re.compile(r'`((?:codontrace\.)?(?:genesis|contracts|life_loop|swarm|replay|engine_spec)\.[A-Za-z0-9_.]+)')


@pytest.mark.parametrize('doc', DOCS)
def test_relative_links_resolve(doc):
    text = (ROOT / doc).read_text(encoding='utf-8')
    missing = [t for t in _LINK.findall(text) if '://' not in t and not (ROOT / doc).parent.joinpath(t).exists()]
    assert missing == []


@pytest.mark.parametrize('doc', DOCS[:3])
def test_named_paths_exist(doc):
    text = (ROOT / doc).read_text(encoding='utf-8')
    assert [p for p in _PATH.findall(text) if not (ROOT / p.rstrip('/')).exists()] == []


def _importable(dotted: str) -> bool:
    name = dotted if dotted.startswith('codontrace.') else f'codontrace.{dotted}'
    parts = name.split('.')
    for cut in range(len(parts), 1, -1):
        try:
            obj = importlib.import_module('.'.join(parts[:cut]))
        except ImportError:
            continue
        for attr in parts[cut:]:
            if not hasattr(obj, attr):
                return False
            obj = getattr(obj, attr)
        return True
    return False


@pytest.mark.parametrize('doc', DOCS[:2])
def test_named_modules_import(doc):
    text = (ROOT / doc).read_text(encoding='utf-8')
    names = {m.rstrip('.') for m in _MODULE.findall(text)}
    assert names and [n for n in sorted(names) if not _importable(n)] == []


def test_experimental_api_rows_import_and_are_not_claim_ready():
    rows = [r for r in build_public_api_manifest() if r.introduced_in == '0.3.0b30-engine-integration']
    assert len(rows) == 30
    for row in rows:
        assert row.stability_status == 'provisional' and row.claim_ready_allowed is False
        assert import_public_symbol(row) is not None


_SECTION_PATH = re.compile(r'`((?:src/codontrace/|swarm/|claimgate/)[A-Za-z0-9_/]+\.py)`')
_SECTION_SYMBOL = re.compile(r'`([A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*)(?:\(\))?`')


def _section_module(path: str) -> str:
    path = path.removeprefix('src/codontrace/').removesuffix('.py')
    return 'codontrace.' + path.replace('/', '.')


def test_engine_sections_table_names_real_modules_and_symbols():
    """Every module path in the ENGINE_SECTIONS table imports, and every symbol
    named in a cell (``SwarmCoordinator.run_reference()``, ``perturb``) exists on
    one of the modules named in that same cell (or, for a cell without a path,
in any module the table names)."""
    text = (ROOT / 'docs/swarm/ENGINE_SECTIONS.md').read_text(encoding='utf-8')
    rows = [line for line in text.splitlines() if line.startswith('| ') and '`' in line]
    assert len(rows) >= 10
    checked, problems = 0, []
    every = sorted({_section_module(p) for p in _SECTION_PATH.findall(text)})
    for row in rows:
        for cell in row.strip('|').split('|')[1:3]:
            modules = [_section_module(p) for p in _SECTION_PATH.findall(cell)]
            for module in modules:
                if not _importable(module):
                    problems.append(module)
            symbols = [s for s in _SECTION_SYMBOL.findall(cell) if '/' not in s and not s.endswith('.py')
                       and not s.isupper() and not s.startswith('codontrace')]
            for symbol in symbols:
                checked += 1
                if not any(_importable(f'{m}.{symbol}') for m in modules or every):
                    problems.append(f'{modules}: {symbol}')
    assert checked >= 5 and problems == []
