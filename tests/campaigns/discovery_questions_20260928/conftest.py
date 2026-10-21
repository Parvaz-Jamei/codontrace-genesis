"""Shared fixtures for the 2026-09-28 discovery campaign tests."""

from __future__ import annotations

from collections.abc import Iterator

import pytest

from codontrace.genesis.engine import GenesisEngine


@pytest.fixture
def legacy_capsule_dispatch(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Historical counterfactual: pre-aadc970 population-config dispatch.

    Before aadc970 (R09 capsule reconciliation) ``GenesisEngine.from_spec``
    used ``spec.population_configs`` verbatim and silently ignored the
    top-level capsule request. This fixture restores only that dispatch,
    the same way tests/test_life_loop_digest_history.py does, so a test can
    show that a pre-migration pin came from the old model condition. It is
    not a public mode; see docs/validation/LIFE_LOOP_DIGEST_HISTORY.md.
    """
    original = GenesisEngine.from_spec.__func__  # type: ignore[attr-defined]

    def _legacy(cls: type[GenesisEngine], spec, **kwargs):  # type: ignore[no-untyped-def]
        engine = original(cls, spec, **kwargs)
        if spec.population_configs is not None:
            engine.runner.configs = spec.population_configs
        return engine

    monkeypatch.setattr(GenesisEngine, "from_spec", classmethod(_legacy))
    yield
