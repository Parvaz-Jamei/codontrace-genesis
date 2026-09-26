"""Engine submodule split keeps historical imports and Phase A–E digest pins."""

from __future__ import annotations

import codontrace.engine as engine_facade
import codontrace.genesis.engine as genesis_engine_facade
from codontrace.engine import (
    GenerationBoundaryObserver,
    GenesisEngine,
    GenesisEngineConfig,
    GenesisExperimentSpec,
    GenesisRun,
    GenesisRunResult,
    GenesisRunSummary,
    GenesisSnapshot,
    GenesisTickResult,
    _action_registry_hash,
    _digest,
    _execution_source_digest,
    _phase2_hashes,
    apply_human_review,
    attach_review_result,
)
from codontrace.engine_claims import (
    _execution_source_digest as claims_execution_source_digest,
)
from codontrace.engine_claims import _phase2_hashes as claims_phase2_hashes
from codontrace.engine_claims import apply_human_review as claims_apply_human_review
from codontrace.engine_claims import attach_review_result as claims_attach_review_result
from codontrace.engine_digest import _action_registry_hash as digest_action_registry_hash
from codontrace.engine_digest import _digest as module_digest
from codontrace.engine_results import GenesisRun as ResultGenesisRun
from codontrace.engine_results import GenesisSnapshot as ResultGenesisSnapshot
from codontrace.engine_results import GenesisTickResult as ResultGenesisTickResult
from codontrace.engine_run_result import GenesisRunResult as ModuleGenesisRunResult
from codontrace.engine_runtime import GenesisEngine as RuntimeGenesisEngine
from codontrace.engine_spec import (
    GenerationBoundaryObserver as SpecGenerationBoundaryObserver,
)
from codontrace.engine_spec import GenesisEngineConfig as SpecGenesisEngineConfig
from codontrace.engine_spec import GenesisExperimentSpec as SpecGenesisExperimentSpec
from codontrace.genesis.engine import GenesisEngine as GenesisEngineReexport
from codontrace.genesis.engine import GenerationBoundaryObserver as GenesisObserverReexport
from codontrace.genesis.engine import _action_registry_hash as genesis_action_registry_hash
from codontrace.genesis.runtime_profiles import GenesisRuntimeProfile

LIFE_LOOP_SPEC_DIGEST = "7d199ae51345872215dbbb0c45cf8f141aacfb4c31d6537eda6de246c0cb7aac"
LIFE_LOOP_SNAPSHOT_DIGEST = "76a5e62cb0123b20a089adde25acd1cfb6dc460bdfab52f33ee460533d76f43a"

# P0a facade freeze — names that must remain importable from codontrace.engine
FACADE_REQUIRED = (
    "ConsistencyValidationResult",
    "GenerationBoundaryObserver",
    "GenesisEngine",
    "GenesisEngineConfig",
    "GenesisExperimentSpec",
    "GenesisRun",
    "GenesisRunResult",
    "GenesisRunSummary",
    "GenesisSnapshot",
    "GenesisTickResult",
    "apply_human_review",
    "attach_review_result",
    "_action_registry_hash",
    "_digest",
    "_execution_source_digest",
    "_phase2_hashes",
)


def test_engine_facade_all_lists_stable_public_names() -> None:
    assert hasattr(engine_facade, "__all__")
    for name in FACADE_REQUIRED:
        assert name in engine_facade.__all__, name
        assert hasattr(engine_facade, name), name
    for name in (
        "GenerationBoundaryObserver",
        "GenesisEngine",
        "GenesisEngineConfig",
        "GenesisExperimentSpec",
        "GenesisRun",
        "GenesisRunResult",
        "GenesisRunSummary",
        "GenesisSnapshot",
        "GenesisTickResult",
        "apply_human_review",
        "attach_review_result",
        "_action_registry_hash",
        "_execution_source_digest",
        "_phase2_hashes",
    ):
        assert name in genesis_engine_facade.__all__, name


def test_engine_helpers_and_types_reexport_from_new_modules() -> None:
    assert GenesisTickResult is ResultGenesisTickResult
    assert GenesisSnapshot is ResultGenesisSnapshot
    assert GenesisRun is ResultGenesisRun
    assert _digest is module_digest
    assert _action_registry_hash is digest_action_registry_hash
    assert _action_registry_hash is genesis_action_registry_hash
    assert GenesisEngine is GenesisEngineReexport
    assert GenesisEngine is RuntimeGenesisEngine
    assert GenesisRunResult is ModuleGenesisRunResult
    assert GenesisExperimentSpec is SpecGenesisExperimentSpec
    assert GenesisEngineConfig is SpecGenesisEngineConfig
    assert GenerationBoundaryObserver is SpecGenerationBoundaryObserver
    assert GenerationBoundaryObserver is GenesisObserverReexport
    assert attach_review_result is claims_attach_review_result
    assert apply_human_review is claims_apply_human_review
    assert _execution_source_digest is claims_execution_source_digest
    assert _phase2_hashes is claims_phase2_hashes
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
    assert isinstance(result, GenesisRunResult)
    assert isinstance(result.summary(), GenesisRunSummary)


def test_generation_boundary_observer_called_once_per_completed_generation() -> None:
    """P0c / cross:wave8 — domain-free observer fires once per completed gen."""

    seen: list[int] = []

    def _counter(*, generation_index: int) -> None:
        seen.append(int(generation_index))

    observer: GenerationBoundaryObserver = _counter
    spec = GenesisRuntimeProfile.life_loop_world(seed=7, tick_count=5, population=4)
    engine = GenesisEngine.from_spec(spec, generation_boundary_observers=(observer,))
    result = engine.run_ticks()
    assert len(result.ticks) == 5
    assert len(seen) == 5
    assert seen == sorted(seen)
    assert all(idx >= 1 for idx in seen)
    # Observer must not alter pinned life-loop digests when unused on pin path.
    pin_spec = GenesisRuntimeProfile.life_loop_world(seed=7, tick_count=12, population=6)
    pin = GenesisEngine.from_spec(pin_spec).run_ticks()
    assert pin_spec.digest() == LIFE_LOOP_SPEC_DIGEST
    assert pin.snapshot.digest() == LIFE_LOOP_SNAPSHOT_DIGEST
