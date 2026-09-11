"""Engine submodule split keeps historical imports and Phase A–E digest pins."""

from __future__ import annotations

from codontrace.engine import (
    GenesisEngine,
    GenesisExperimentSpec,
    GenesisRun,
    GenesisSnapshot,
    GenesisTickResult,
    _action_registry_hash,
    _digest,
)
from codontrace.engine_digest import _action_registry_hash as digest_action_registry_hash
from codontrace.engine_digest import _digest as module_digest
from codontrace.engine_results import GenesisRun as ResultGenesisRun
from codontrace.engine_results import GenesisSnapshot as ResultGenesisSnapshot
from codontrace.engine_results import GenesisTickResult as ResultGenesisTickResult
from codontrace.genesis.engine import GenesisEngine as GenesisEngineReexport
from codontrace.genesis.engine import _action_registry_hash as genesis_action_registry_hash
from codontrace.genesis.runtime_profiles import GenesisRuntimeProfile


LIFE_LOOP_SPEC_DIGEST = "7d199ae51345872215dbbb0c45cf8f141aacfb4c31d6537eda6de246c0cb7aac"
LIFE_LOOP_SNAPSHOT_DIGEST = "76a5e62cb0123b20a089adde25acd1cfb6dc460bdfab52f33ee460533d76f43a"


def test_engine_helpers_and_types_reexport_from_new_modules() -> None:
    assert GenesisTickResult is ResultGenesisTickResult
    assert GenesisSnapshot is ResultGenesisSnapshot
    assert GenesisRun is ResultGenesisRun
    assert _digest is module_digest
    assert _action_registry_hash is digest_action_registry_hash
    assert _action_registry_hash is genesis_action_registry_hash
    assert GenesisEngine is GenesisEngineReexport
    assert _action_registry_hash(None)
    assert _digest({"replay_contract": "engine_digest"})


def test_engine_split_does_not_move_default_life_loop_pins() -> None:
    spec = GenesisRuntimeProfile.life_loop_world(seed=7, tick_count=12, population=6)
    assert isinstance(spec, GenesisExperimentSpec)
    result = GenesisEngine.from_spec(spec).run_ticks()
    replay = GenesisEngine.from_spec(spec).run_ticks()
    assert spec.digest() == LIFE_LOOP_SPEC_DIGEST
    assert result.digest() == replay.digest()
    assert result.snapshot.digest() == LIFE_LOOP_SNAPSHOT_DIGEST
    assert isinstance(result.ticks[0], GenesisTickResult)
