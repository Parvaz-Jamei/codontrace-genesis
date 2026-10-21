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
    assert len(rows) == 20
    for row in rows:
        assert row.stability_status == 'provisional' and row.claim_ready_allowed is False
        assert import_public_symbol(row) is not None
