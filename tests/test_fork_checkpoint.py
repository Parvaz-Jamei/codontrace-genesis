"""Time-fixed checkpoints, independent branches, and the noise-coupling contract."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from codontrace.engine import GenesisEngine, GenesisExperimentSpec
from codontrace.engine_runtime import (
    checkpoint_bytes,
    event_keyed_draws,
    stream_position_draws,
)
from codontrace.errors import ConfigurationError

SPEC = GenesisExperimentSpec(tick_count=0, seed=31)


def _engine() -> GenesisEngine:
    engine = GenesisEngine.from_spec(SPEC)
    engine.run_ticks(3)
    return engine


def test_capture_then_parent_mutation_restores_the_frozen_state() -> None:
    engine = _engine()
    before = engine.runner.population.digest()
    atp = engine.runner.population.organisms[0].atp_state.runtime_available
    payload = engine.capture_fork()
    frozen = payload["state_digest"]
    organism = engine.runner.population.organisms[0]
    organism.atp_state.credit_runtime(
        7.5, tick=3, organism_id=organism.id, codon="000", action="probe", reason="phase3"
    )
    restored = GenesisEngine.from_fork(SPEC, payload)
    assert payload["live_objects"]["population"] is not engine.runner.population
    assert restored.runner.population.digest() == before
    assert restored.runner.population.organisms[0].atp_state.runtime_available == atp
    assert restored._state_digest() == frozen
    assert payload["state_digest"] == frozen
    assert restored.fork_state_exact is True


def test_restore_order_does_not_change_the_result() -> None:
    payload = _engine().capture_fork()
    first_then_second = GenesisEngine.from_fork(SPEC, payload)
    _second = GenesisEngine.from_fork(SPEC, payload)
    second_then_first = GenesisEngine.from_fork(SPEC, payload)
    _first = GenesisEngine.from_fork(SPEC, payload)
    first_then_second.run_ticks(1)
    second_then_first.run_ticks(1)
    assert first_then_second.runner.population.digest() == second_then_first.runner.population.digest()
    assert first_then_second._state_digest() == second_then_first._state_digest()


def test_batch_and_stepwise_continuation_match() -> None:
    payload = _engine().capture_fork()
    batch = GenesisEngine.from_fork(SPEC, payload)
    batch.run_ticks(2)
    stepwise = GenesisEngine.from_fork(SPEC, payload)
    stepwise.run_ticks(1)
    stepwise.run_ticks(1)
    assert batch._state_digest() == stepwise._state_digest()


def test_branch_mutation_does_not_touch_the_other_branch_parent_or_payload() -> None:
    parent = _engine()
    payload = parent.capture_fork()
    parent_digest = parent.runner.population.digest()
    payload_digest = payload["live_objects"]["population"].digest()
    branch_a = GenesisEngine.from_fork(SPEC, payload)
    branch_b = GenesisEngine.from_fork(SPEC, payload)
    organism = branch_a.runner.population.organisms[0]
    organism.atp_state.credit_runtime(
        7.5, tick=3, organism_id=organism.id, codon="000", action="probe", reason="phase3"
    )
    definition = branch_a.element_grid.registry.require("Ig")
    definition.properties["probe"] = 1
    assert parent.runner.population.digest() == parent_digest
    assert payload["live_objects"]["population"].digest() == payload_digest
    assert branch_b.runner.population.digest() == parent_digest
    assert "probe" not in parent.element_grid.registry.require("Ig").properties
    assert "probe" not in payload["live_objects"]["element_grid"].registry.require("Ig").properties
    assert "probe" not in branch_b.element_grid.registry.require("Ig").properties
    dispositions = {item["disposition"] for item in payload["proxy_contract"]}
    assert "shared_immutable" in dispositions
    assert "rebuilt_mutable_values" in dispositions


def test_spec_mismatch_is_refused_without_an_explicit_reason() -> None:
    payload = _engine().capture_fork()
    other = GenesisExperimentSpec(tick_count=0, seed=32)
    with pytest.raises(ConfigurationError):
        GenesisEngine.from_fork(other, payload)
    with pytest.raises(ConfigurationError):
        GenesisEngine.from_fork(other, payload, allow_spec_change=True)
    changed = GenesisEngine.from_fork(
        other, payload, allow_spec_change=True, spec_change_reason="intentional arm spec"
    )
    assert changed.fork_state_exact is False
    assert changed.fork_provenance["spec_change_reason"] == "intentional arm spec"


def test_audit_is_not_a_checkpoint_and_noise_follows_stream_position() -> None:
    engine = _engine()
    audit = engine.fork_audit_payload()
    json.dumps(audit)
    assert audit["record_role"] == "serialisable_audit"
    assert audit["restorable"] is False
    assert audit["noise_coupling"] == "stream_position"
    with pytest.raises(ConfigurationError):
        GenesisEngine.from_fork(SPEC, audit)
    payload = engine.capture_fork()
    assert payload["rng_derivation"]["next_tick_seed"] == 31 + 3
    plain = stream_position_draws(31, 3, ("contact", "birth"))
    inserted = stream_position_draws(31, 3, ("contact", "unrelated", "birth"))
    assert plain[0] == inserted[0]
    assert plain[1][0] == inserted[2][0] == "birth"
    assert plain[1][1] != inserted[2][1]
    keyed_plain = event_keyed_draws(31, 3, ("contact", "birth"))
    keyed_inserted = event_keyed_draws(31, 3, ("contact", "unrelated", "birth"))
    assert keyed_plain[1][1] == keyed_inserted[2][1]


def test_checkpoint_resumes_in_a_fresh_process(tmp_path) -> None:
    payload = _engine().capture_fork()
    blob = tmp_path / "checkpoint.pkl"
    blob.write_bytes(checkpoint_bytes(payload))
    script = tmp_path / "resume.py"
    script.write_text(
        "import sys\n"
        "from codontrace.engine import GenesisEngine, GenesisExperimentSpec\n"
        "from codontrace.engine_runtime import checkpoint_from_bytes\n"
        "payload = checkpoint_from_bytes(open(sys.argv[1], 'rb').read())\n"
        "spec = GenesisExperimentSpec(tick_count=0, seed=int(payload['seed']))\n"
        "engine = GenesisEngine.from_fork(spec, payload)\n"
        "print(engine._state_digest())\n"
        "print(engine.fork_state_exact)\n",
        encoding="utf-8",
    )
    env = dict(os.environ)
    root = Path(__file__).resolve().parents[1]
    env["PYTHONPATH"] = str(root / "src") + os.pathsep + env.get("PYTHONPATH", "")
    proc = subprocess.run(
        [sys.executable, str(script), str(blob)],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )
    assert proc.returncode == 0, proc.stderr
    lines = proc.stdout.splitlines()
    assert lines[0] == payload["state_digest"]
    assert lines[1] == "True"


def test_rng_snapshot_matches_the_tick_and_a_tampered_one_is_refused() -> None:
    payload = _engine().capture_fork()
    assert payload["rng"]["seed"] == 31 + 3
    assert payload["rng"]["namespace"] == "fork-noise-contract"
    assert payload["rng_derivation"]["next_tick_seed"] == payload["rng"]["seed"]
    payload["rng"] = dict(payload["rng"])
    payload["rng"]["seed"] = 31
    with pytest.raises(ConfigurationError, match="rng snapshot"):
        GenesisEngine.from_fork(SPEC, payload)


def test_branch_does_not_share_spec_metadata_or_drop_the_feedback_flag() -> None:
    parent = _engine()
    parent._qd_parent_feedback_applied = True
    payload = parent.capture_fork()
    branch = GenesisEngine.from_fork(SPEC, payload)
    assert branch.runner.configs.to_dict() == parent.runner.configs.to_dict()
    assert branch._qd_parent_feedback_applied is True
    assert branch.fork_state_exact is True
    branch.spec.metadata["arm"] = "A"
    assert "arm" not in parent.spec.metadata
