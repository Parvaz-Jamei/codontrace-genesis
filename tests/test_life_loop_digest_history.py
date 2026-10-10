"""Lock both sides of the audited capsule-reconciliation behavior migration."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from codontrace.genesis.engine import GenesisEngine
from codontrace.genesis.runtime_profiles import GenesisRuntimeProfile

EVIDENCE = Path(__file__).resolve().parents[1] / 'docs/validation/life_loop_digest_history'
PARENT = 'ab81af94a28d29f1c7dfc38956ad3abd314c0350'
FIRST_CHANGED = 'aadc97062a1a3e03840bc85afb66414e613d559b'


def _historical_payload(commit: str) -> dict:
    return json.loads((EVIDENCE / f'{commit}.json').read_text())


def test_capsule_reconciliation_matches_first_changed_full_trajectory() -> None:
    """Assert all 12 raw generations, not just an easy-to-repin final digest."""
    spec = GenesisRuntimeProfile.life_loop_world(seed=7, tick_count=12, population=6)
    engine = GenesisEngine.from_spec(spec)
    assert engine.config_reconciliation['requested_capsules_enabled'] is True
    assert engine.config_reconciliation['effective_capsules_enabled'] is True
    assert engine.config_reconciliation['reconciliation_applied'] is True
    result = engine.run_ticks()
    expected = _historical_payload(FIRST_CHANGED)
    assert [tick.to_dict() for tick in result.ticks] == expected['ticks']
    assert result.snapshot.to_dict() == expected['snapshot']
    assert result.snapshot.digest() == expected['digest']


def test_legacy_counterfactual_matches_parent_full_trajectory() -> None:
    """Reproduce historical dispatch, isolated to this audit, with the same spec."""
    spec = GenesisRuntimeProfile.life_loop_world(seed=7, tick_count=12, population=6)
    engine = GenesisEngine.from_spec(spec)
    # Pre-aadc970 used population_configs verbatim; this is NOT a public mode.
    engine.runner.configs = spec.population_configs
    result = engine.run_ticks()
    expected = _historical_payload(PARENT)
    assert [tick.to_dict() for tick in result.ticks] == expected['ticks']
    assert result.snapshot.to_dict() == expected['snapshot']
    assert result.snapshot.digest() == expected['digest']


def test_first_tick_energy_difference_is_capsule_read_cost() -> None:
    spec = GenesisRuntimeProfile.life_loop_world(seed=7, tick_count=12, population=6)
    current = GenesisEngine.from_spec(spec)
    legacy = GenesisEngine.from_spec(spec)
    # Identical initial state and identity; no RNG or organism-ID changes.
    assert current.snapshot().to_dict() == legacy.snapshot().to_dict()
    legacy.runner.configs = spec.population_configs
    capsule_config = current.runner.configs.capsule_transfer
    assert capsule_config is not None
    new = current.run_ticks(1).ticks[0].generation_result
    old = legacy.run_ticks(1).ticks[0].generation_result
    assert len(new.organism_records) == len(old.organism_records) == 6
    for before, after in zip(old.organism_records, new.organism_records, strict=True):
        assert before.organism_id == after.organism_id
        assert before.runtime_atp_after - after.runtime_atp_after == pytest.approx(
            capsule_config.read_cost_runtime_atp
        )
