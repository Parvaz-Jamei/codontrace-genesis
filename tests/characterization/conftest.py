from __future__ import annotations

import pytest


@pytest.fixture
def neutral_source_digest(tmp_path_factory, monkeypatch):
    """Make ``RunManifest.source_digest`` independent of the checkout.

    ``compute_source_digest()`` hashes every file under ``src/codontrace/``,
    ``docs/``, ``pyproject.toml`` and ``README.md``, and that digest flows
    into ``GenesisRunResult.digest()``. Any edit, even a docstring or a
    release version bump, would move a result pin. Pointing
    ``CODONTRACE_SOURCE_ROOT`` at an empty directory keeps the source identity
    constant, so result pins characterize run behaviour only. Snapshot and
    tick digests never include it.
    """
    root = tmp_path_factory.mktemp('empty_source_root')
    monkeypatch.setenv('CODONTRACE_SOURCE_ROOT', str(root))
    return root
