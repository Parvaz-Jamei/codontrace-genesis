"""Pin the fork payload contracts: audit payload serialises, live payload does not."""

from __future__ import annotations

import json

import pytest

try:
    from codontrace.engine import GenesisEngine, GenesisExperimentSpec
except Exception:  # pragma: no cover - import-path fallback
    from codontrace.genesis import GenesisEngine, GenesisExperimentSpec


def _engine():
    engine = GenesisEngine.from_spec(GenesisExperimentSpec(tick_count=0, seed=31))
    engine.run_ticks(3)
    return engine


def test_fork_audit_payload_is_json_serialisable_and_carries_the_flags() -> None:
    audit = _engine().fork_audit_payload(parent_snapshot_id="audit-1")
    encoded = json.dumps(audit)
    assert isinstance(encoded, str)
    assert audit["fork_isolation"] == "shared_reference:population,element_grid"
    assert audit["fork_state_exact"] is True
    assert audit["live_payload_is_in_memory_only"] is True
    assert audit["tick_index"] == 3
    assert audit["parent_snapshot_id"] == "audit-1"
    assert len(str(audit["population_digest"])) > 0
    assert len(str(audit["world_digest"])) > 0


def test_live_fork_payload_is_documented_in_memory_only() -> None:
    live = _engine().capture_fork()
    assert "live_objects" in live
    assert type(live["live_objects"]["population"]).__name__ == "PopulationState"
    with pytest.raises(TypeError):
        json.dumps(live)
    assert "Not JSON-serialisable" in GenesisEngine.capture_fork.__doc__


def test_fork_audit_flags_survive_a_fork_round_trip() -> None:
    engine = _engine()
    spec = GenesisExperimentSpec(tick_count=0, seed=31)
    restored = GenesisEngine.from_fork(spec, engine.capture_fork())
    restored.run_ticks(1)
    audit = restored.fork_audit_payload()
    assert audit["tick_index"] == 4
    assert audit["fork_state_exact"] is True
    assert json.dumps(audit)
