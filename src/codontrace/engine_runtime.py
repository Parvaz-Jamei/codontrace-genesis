"""GenesisEngine orchestrator — population stepping, QD, and result build.

Extracted from ``codontrace.engine`` for debuggability. Public imports stay on
the ``codontrace.engine`` facade. GenerationBoundaryObserver is invoked once
per completed generation in ``run_ticks`` (domain-free; no HP payload).
See ``docs/ENGINE_REPLAY_CONTRACT.md``.
"""

from __future__ import annotations

import enum
import pickle
from collections.abc import Mapping, Sequence
from copy import deepcopy
from dataclasses import replace
from types import (
    BuiltinFunctionType,
    FunctionType,
    MappingProxyType,
    MethodDescriptorType,
    WrapperDescriptorType,
)
from typing import Any, cast

from codontrace._types import JsonValue
from codontrace.engine_claims import (
    _claim_evidence_flags,
    _contribution_ledgers_from_raw_events,
    _execution_source_digest,
    _phase2_hashes,
    _protocol_statuses,
    _qd_scheduler_manifest_digest,
    _raw_events,
    _scientific_protocol_executed,
    _strong_claim_ladder_records_for_result,
    _summarize_run,
)
from codontrace.engine_digest import (
    _action_registry_hash,
    _adf_vocabulary_hash,
    _codon_table_hash,
    _digest,
    _genome_spec_hash,
    _json_float_value,
    _object_hash,
    _ribosome_hash,
)
from codontrace.engine_results import (
    GenesisRun,
    GenesisSnapshot,
    GenesisTickResult,
)
from codontrace.engine_run_result import GenesisRunResult
from codontrace.engine_spec import (
    GenerationBoundaryObserver,
    GenesisExperimentSpec,
)
from codontrace.errors import ConfigurationError
from codontrace.genesis.api_audit import export_action_wiring_matrix
from codontrace.genesis.artifacts import (
    PopulationSnapshot,
    ReplayBundle,
    ReviewStatus,
    RunArtifactSchema,
    compute_source_digest,
    manifest_from_parts,
)
from codontrace.genesis.canonical import canonical_digest
from codontrace.genesis.capsule import (
    CapsuleTransferConfig,
    NexusStigmergyLayer,
)
from codontrace.genesis.causal_graph import (
    CausalGraph,
    CausalGraphConfig,
)
from codontrace.genesis.claim_gate import (
    ClaimRequest,
    ScientificClaimGate,
)
from codontrace.genesis.memory import (
    EpisodicMemory,
    EpisodicMemoryConfig,
)
from codontrace.genesis.organism import GenesisOrganism
from codontrace.genesis.population import (
    FitnessConfig,
    GenerationResult,
    MutationConfig,
    PopulationConfigs,
    PopulationState,
    ReproductionConfig,
)
from codontrace.genesis.population_runner import PopulationRunner
from codontrace.genesis.qd_descriptors import compute_novelty_scores_from_archive
from codontrace.genesis.quality_diversity import (
    BehaviorDescriptorSchema,
    QDArchive,
    QDArchiveBatchUpdateResult,
    QDArchiveConfig,
    QDArchiveItemUpdateRecord,
    QDElite,
    assign_behavior_bin,
    summarize_qd_archive,
    update_qd_archive,
)
from codontrace.genesis.review import (
    LLMReviewRequest,
    LLMReviewResult,
    validate_review_result,
)
from codontrace.genesis.selection import (
    EvolutionConfig,
    select_population,
)
from codontrace.genesis.substrate import (
    element_grid_to_world2d,
    world2d_to_element_grid,
)
from codontrace.genesis.translation_profile import build_semantic_proxy_report
from codontrace.rng import RNGManager
from codontrace.world import World2D


def _effective_evolution_config(spec: GenesisExperimentSpec) -> EvolutionConfig | None:
    base = spec.evolution_config
    if base is None:
        return None
    qd_mode = spec.engine_config.qd_mode if spec.engine_config.enable_qd else "disabled"
    policy = base.resolved_policy()
    if qd_mode == "selection_pressure" and policy.name == "fitness_proportional":
        return replace(base, selection_policy="novelty_weighted", qd_mode="selection_pressure")
    return replace(base, qd_mode=qd_mode)


def _default_qd_archive() -> QDArchive:
    schema = BehaviorDescriptorSchema(
        descriptor_names=("survival_ticks", "blocked_ratio"),
        bins_per_descriptor={"survival_ticks": 8, "blocked_ratio": 8},
        min_values={"survival_ticks": 0.0, "blocked_ratio": 0.0},
        max_values={"survival_ticks": 16.0, "blocked_ratio": 1.0},
    )
    return QDArchive.empty(QDArchiveConfig(schema=schema))


# --- fork isolation -----------------------------------------------------------
#
# A recoverable checkpoint freezes the state graph at capture. Copying only at
# restore is too late: the payload would still point at the live parent.
# ``copy.deepcopy`` cannot copy a ``mappingproxy``. A proxy is shared only when
# every key and value is deeply immutable (a read-only view of a mutable dict,
# or a frozen dataclass that holds a dict, is not immutable). Any other proxy
# is rebuilt over copied contents so a branch cannot write into the parent.

_ABSENT = "absent"
_DEEP_COPIED = "deepcopy"
_SHARED_REFERENCE = "shared_reference"
FORK_CHECKPOINT_VERSION = 2
NOISE_COUPLING = "stream_position"
_CODE_TYPES = (FunctionType, BuiltinFunctionType, MethodDescriptorType, WrapperDescriptorType)


def _is_code(value: Any) -> bool:
    return isinstance(value, _CODE_TYPES) or isinstance(value, type)


def _deeply_immutable(value: Any, seen: set[int]) -> bool:
    """True only when sharing ``value`` cannot let one branch mutate another."""

    if value is None or isinstance(value, (bool, int, float, str, bytes)):
        return True
    if isinstance(value, enum.Enum) or _is_code(value):
        return True
    marker = id(value)
    if marker in seen:
        return True
    if isinstance(value, tuple):
        seen.add(marker)
        return all(_deeply_immutable(item, seen) for item in value)
    if isinstance(value, frozenset):
        seen.add(marker)
        return all(_deeply_immutable(item, seen) for item in value)
    if isinstance(value, MappingProxyType):
        seen.add(marker)
        return all(
            _deeply_immutable(key, seen) and _deeply_immutable(item, seen)
            for key, item in value.items()
        )
    params = getattr(value, "__dataclass_params__", None)
    fields = getattr(value, "__dataclass_fields__", None)
    if params is not None and bool(getattr(params, "frozen", False)) and isinstance(fields, dict):
        seen.add(marker)
        for name in fields:
            try:
                item = getattr(value, name)
            except Exception:
                return False
            if not _deeply_immutable(item, seen):
                return False
        return True
    return False


def _walk(value: Any, seen: set[int], proxies: list[Any]) -> None:
    marker = id(value)
    if marker in seen or _is_code(value) or isinstance(value, enum.Enum):
        return
    seen.add(marker)
    if isinstance(value, MappingProxyType):
        for key, item in value.items():
            _walk(key, seen, proxies)
            _walk(item, seen, proxies)
        proxies.append(value)
        return
    if isinstance(value, Mapping):
        for key, item in value.items():
            _walk(key, seen, proxies)
            _walk(item, seen, proxies)
        return
    if isinstance(value, (list, tuple, set, frozenset)):
        for item in value:
            _walk(item, seen, proxies)
        return
    fields = getattr(value, "__dataclass_fields__", None)
    if isinstance(fields, dict):
        for name in fields:
            try:
                _walk(getattr(value, name), seen, proxies)
            except Exception:
                continue
        return
    namespace = getattr(value, "__dict__", None)
    if isinstance(namespace, dict):
        for item in namespace.values():
            _walk(item, seen, proxies)


def _proxy_memo(value: Any) -> tuple[dict[int, Any], tuple[dict[str, Any], ...]]:
    proxies: list[Any] = []
    _walk(value, set(), proxies)
    memo: dict[int, Any] = {}
    report: list[dict[str, Any]] = []
    for proxy in proxies:
        value_types = sorted({type(item).__name__ for item in proxy.values()})
        if _deeply_immutable(proxy, set()):
            memo[id(proxy)] = proxy
            report.append(
                {
                    "disposition": "shared_immutable",
                    "size": len(proxy),
                    "value_types": value_types,
                }
            )
            continue
        material: dict[Any, Any] = {}
        for key, item in proxy.items():
            material[_clone_member(key, memo)] = _clone_member(item, memo)
        memo[id(proxy)] = MappingProxyType(material)
        report.append(
            {
                "disposition": "rebuilt_mutable_values",
                "size": len(proxy),
                "value_types": value_types,
            }
        )
    return memo, tuple(report)


def _clone_member(value: Any, memo: dict[int, Any]) -> Any:
    if id(value) in memo:
        return memo[id(value)]
    if isinstance(value, MappingProxyType):
        if _deeply_immutable(value, set()):
            memo[id(value)] = value
            return value
        material = {
            _clone_member(key, memo): _clone_member(item, memo) for key, item in value.items()
        }
        rebuilt = MappingProxyType(material)
        memo[id(value)] = rebuilt
        return rebuilt
    if _deeply_immutable(value, set()):
        return value
    return deepcopy(value, memo)


def _isolated_copy(value: Any) -> Any:
    """Deep-copy one fork object. Immutable proxies may be shared; nothing mutable is."""

    clone, _report = _isolated_copy_report(value)
    return clone


def _isolated_copy_report(value: Any) -> tuple[Any, tuple[dict[str, Any], ...]]:
    memo, report = _proxy_memo(value)
    return deepcopy(value, memo), report


class _ProxyCarrier:
    """Pickle stand-in for a mappingproxy. The proxy itself cannot be pickled."""

    def __init__(self, items: tuple[tuple[Any, Any], ...]) -> None:
        self.items = items

    def __reduce__(self) -> tuple[Any, tuple[Any, ...]]:
        return (_restore_proxy, (self.items,))


def _restore_proxy(items: tuple[tuple[Any, Any], ...]) -> MappingProxyType:
    return MappingProxyType(dict(items))


def _pack_member(value: Any, memo: dict[int, Any]) -> Any:
    if isinstance(value, MappingProxyType):
        return memo[id(value)]
    if _deeply_immutable(value, set()):
        return value
    return deepcopy(value, memo)


def _pack_proxies(value: Any) -> Any:
    proxies: list[Any] = []
    _walk(value, set(), proxies)
    memo: dict[int, Any] = {}
    for proxy in proxies:
        items = tuple(
            (_pack_member(key, memo), _pack_member(item, memo)) for key, item in proxy.items()
        )
        memo[id(proxy)] = _ProxyCarrier(items)
    return deepcopy(value, memo)


def checkpoint_bytes(fork: Mapping[str, Any]) -> bytes:
    """Bytes for a fresh process. Not a format for untrusted input.

    The serialisable audit stays JSON and cannot restore a branch. This record
    can, because the frozen objects travel with it and mapping proxies are
    rebuilt on load.
    """

    if fork.get("record_role") != "recoverable_checkpoint":
        msg = "only a recoverable checkpoint can be persisted."
        raise ConfigurationError(msg)
    packed_live = {
        name: None if value is None else _pack_proxies(value)
        for name, value in dict(fork["live_objects"]).items()
    }
    packed = {key: value for key, value in fork.items() if key != "live_objects"}
    packed["live_objects"] = packed_live
    return pickle.dumps(packed)


def checkpoint_from_bytes(blob: bytes) -> dict[str, Any]:
    """Load bytes written by :func:`checkpoint_bytes` in this or another process."""

    loaded = pickle.loads(blob)
    if not isinstance(loaded, dict) or loaded.get("record_role") != "recoverable_checkpoint":
        msg = "checkpoint bytes are not a recoverable fork payload."
        raise ConfigurationError(msg)
    return loaded


def stream_position_draws(
    seed: int, tick: int, events: Sequence[str]
) -> tuple[tuple[str, float], ...]:
    """Draws under the engine's noise contract: one stream per tick, in event order.

    ``run_ticks`` seeds a generation with ``spec.seed + completed_ticks``. The
    same seed does not attach a draw to an event name. An inserted event takes
    a position and every later draw on that stream moves.
    """

    rng = RNGManager(seed=int(seed) + int(tick), namespace="fork-noise-contract")
    return tuple((str(event), float(rng.random())) for event in events)


def event_keyed_draws(
    seed: int, tick: int, events: Sequence[str]
) -> tuple[tuple[str, float], ...]:
    """The coupling this engine does not use: the draw follows the event name."""

    return tuple(
        (
            str(event),
            float(
                RNGManager(
                    seed=int(seed), namespace=f"tick/{int(tick)}/event/{event}"
                ).random()
            ),
        )
        for event in events
    )


def _checkpoint_digest(
    *,
    tick_index: int,
    population: Any,
    world: Any,
    nexus_layer: Any,
    qd_archive: Any,
    element_grid: Any,
) -> str:
    payload = {
        "tick_index": int(tick_index),
        "population": str(population.digest()),
        "world": str(world.digest()),
        "nexus": None if nexus_layer is None else str(nexus_layer.digest()),
        "qd_archive": None if qd_archive is None else str(qd_archive.digest()),
        "element_grid": None if element_grid is None else str(element_grid.digest()),
    }
    return canonical_digest(payload, prefix="fork_checkpoint")


class GenesisEngine:
    """Unified orchestration wrapper around existing GENESIS primitives."""

    def __init__(
        self,
        *,
        spec: GenesisExperimentSpec,
        runner: PopulationRunner,
        run: GenesisRun,
        qd_archive: QDArchive | None = None,
        generation_boundary_observers: Sequence[GenerationBoundaryObserver] | None = None,
    ) -> None:
        self.spec = spec
        self.runner = runner
        self.run = run
        self.qd_archive = qd_archive
        self.element_grid = spec.element_grid
        self.review_status = ReviewStatus()
        self.generation_boundary_observers: list[GenerationBoundaryObserver] = list(
            generation_boundary_observers or ()
        )
        self._tick_results: list[GenesisTickResult] = []
        self._snapshots: list[PopulationSnapshot] = [
            PopulationSnapshot.from_population(self.runner.population, self.runner.nexus_layer)
        ]
        self._last_result: GenesisRunResult | None = None
        self._qd_parent_feedback_applied = False

    @classmethod
    def from_spec(
        cls,
        spec: GenesisExperimentSpec,
        *,
        generation_boundary_observers: Sequence[GenerationBoundaryObserver] | None = None,
    ) -> GenesisEngine:
        world = (
            element_grid_to_world2d(spec.element_grid)
            if spec.element_grid is not None and spec.substrate_bridge_mode == "element_grid_source"
            else World2D(spec.world_width, spec.world_height)
        )
        ribosome = spec.resolved_ribosome()
        memory_config = spec.memory_config or EpisodicMemoryConfig()
        causal_config = spec.causal_graph_config or CausalGraphConfig()
        action_registry = spec.action_registry
        organisms: list[GenesisOrganism] = []
        for index, bits in enumerate(spec.genome_bits):
            organism = GenesisOrganism.from_bits(
                f"org-{index}",
                bits,
                initial_runtime_atp=spec.initial_runtime_atp,
                initial_learning_atp=spec.initial_learning_atp,
                learning_enabled=spec.engine_config.enable_memory
                or spec.engine_config.enable_causal_graph,
                position=(
                    index % cast(Any, world).width,
                    index // cast(Any, world).width % cast(Any, world).height,
                ),
                ribosome=ribosome,
                causal_graph=CausalGraph(config=causal_config)
                if spec.engine_config.enable_causal_graph
                else None,
                action_registry=action_registry,
                action_runtime_config=spec.action_runtime_config,
                memory_config=memory_config,
                execution_source_enabled=spec.enable_execution_source,
                adf_macro_registry=spec.adf_macro_registry,
                adf_execution_policy=spec.adf_execution_policy,
                translation_profile=spec.translation_profile,
                translation_policy=spec.translation_policy,
            )
            if spec.engine_config.enable_memory:
                organism.episodic_memory = EpisodicMemory(memory_config)
            organisms.append(organism)
        capsule_config = (
            spec.capsule_transfer_config
            if spec.capsule_transfer_config is not None
            else (
                CapsuleTransferConfig(enabled=True) if spec.engine_config.enable_capsules else None
            )
        )
        if spec.population_configs is not None:
            configs = spec.population_configs
        else:
            configs = PopulationConfigs(
                reproduction=spec.reproduction_config
                or ReproductionConfig(max_population=spec.population_max),
                mutation=spec.mutation_config or MutationConfig(bit_flip_rate=0.0),
                structural_mutation=spec.structural_mutation_config,
                fitness=FitnessConfig(),
                ticks_per_generation=spec.engine_config.ticks_per_generation,
                capsule_transfer=capsule_config,
                enable_nexus_stigmergy=spec.engine_config.enable_capsules,
                evolution=_effective_evolution_config(spec),
                qd_mode=spec.engine_config.qd_mode if spec.engine_config.enable_qd else "disabled",
            )
        initial_deme = None
        if configs.phase_e.enabled:
            from codontrace.genesis.phase_e import attach_phase_e_to_organisms, build_deme_state

            organisms = list(attach_phase_e_to_organisms(organisms, configs.phase_e))
            if configs.phase_e.demes.enabled:
                initial_deme = build_deme_state(organisms)
        if configs.materials.enabled:
            from codontrace.genesis.materials import attach_materials_to_organisms

            organisms = list(attach_materials_to_organisms(organisms, configs.materials))
        population = PopulationState(
            generation=0,
            tick=0,
            organisms=tuple(organisms),
            lineage=(),
            fitness=(),
            deme=initial_deme,
        )
        runner = PopulationRunner(
            population=population,
            world=cast(Any, world),
            configs=configs,
            nexus_layer=NexusStigmergyLayer() if spec.engine_config.enable_capsules else None,
        )
        qd_archive = (
            QDArchive.empty(spec.qd_archive_config)
            if spec.qd_archive_config is not None
            else (_default_qd_archive() if spec.engine_config.enable_qd else None)
        )
        run_id = f"genesis-run-{spec.digest()[:16]}"
        engine = cls(
            spec=spec,
            runner=runner,
            run=GenesisRun(run_id=run_id, spec_digest=spec.digest(), seed=spec.seed),
            qd_archive=qd_archive,
            generation_boundary_observers=generation_boundary_observers,
        )
        engine.element_grid = spec.element_grid or world2d_to_element_grid(world)
        return engine

    def run_ticks(self, ticks: int | None = None) -> GenesisRunResult:
        count = self.spec.tick_count if ticks is None else ticks
        if count < 0:
            msg = "ticks must be >= 0."
            raise ValueError(msg)
        base = int(getattr(self, "_tick_offset", 0)) + len(self._tick_results)
        for index in range(count):
            generation = self.runner.step_generation(seed=self.spec.seed + base + index)
            self._apply_qd_parent_feedback(generation)
            qd_update = self._update_qd(generation)
            if self.spec.substrate_bridge_mode == "world2d_mirror":
                self.element_grid = world2d_to_element_grid(self.runner.world)
            tick_result = GenesisTickResult(
                index=base + index, generation_result=generation, qd_update=qd_update
            )
            self._tick_results.append(tick_result)
            self._snapshots.append(
                PopulationSnapshot.from_population(self.runner.population, self.runner.nexus_layer)
            )
            # Domain-free generation-boundary seam (WAVE9 P0c / cross:wave8).
            generation_index = int(self.runner.population.generation)
            for observer in self.generation_boundary_observers:
                observer(generation_index=generation_index)
        self._last_result = self._build_result()
        return self._last_result


    def capture_fork(self, *, parent_snapshot_id: str | None = None) -> dict[str, Any]:
        """Freeze a recoverable checkpoint. The payload does not alias the parent.

        **Not JSON-serialisable.** Live objects are isolated copies taken now.
        :meth:`fork_audit_payload` is the serialisable audit and cannot restore
        this checkpoint. ``fork_version`` is :data:`FORK_CHECKPOINT_VERSION`.
        """

        tick_index = int(getattr(self, "_tick_offset", 0)) + len(self._tick_results)
        live: dict[str, Any] = {}
        isolation: dict[str, str] = {}
        proxy_contract: list[dict[str, Any]] = []
        for name, value in self._fork_live_objects().items():
            if value is None:
                isolation[name] = _ABSENT
                continue
            try:
                clone = _isolated_copy(value)
            except Exception as exc:
                msg = (
                    f"fork isolation refused: cannot freeze {name!r} "
                    f"({type(exc).__name__}: {exc})."
                )
                raise ConfigurationError(msg) from exc
            if clone is value:
                msg = f"fork isolation refused: {name!r} was not copied."
                raise ConfigurationError(msg)
            _memo, report = _proxy_memo(value)
            live[name] = clone
            isolation[name] = _DEEP_COPIED
            for item in report:
                proxy_contract.append({"object": name, **item})
        state_digest = _checkpoint_digest(
            tick_index=tick_index,
            population=live["population"],
            world=live["world"],
            nexus_layer=live.get("nexus_layer"),
            qd_archive=live.get("qd_archive"),
            element_grid=live.get("element_grid"),
        )
        return {
            "record_role": "recoverable_checkpoint",
            "fork_version": FORK_CHECKPOINT_VERSION,
            "run_id": self.run.run_id,
            "spec_digest": self.spec.digest(),
            "seed": int(self.spec.seed),
            "tick_index": tick_index,
            "state_digest": state_digest,
            "population": self.runner.population.to_dict(),
            "world": self.runner.world.to_dict(),
            "rng": RNGManager(seed=self.spec.seed, namespace="engine_fork").snapshot(
                include_state=True
            ),
            "rng_derivation": {
                "coupling": NOISE_COUPLING,
                "seed": int(self.spec.seed),
                "next_tick_seed": int(self.spec.seed) + tick_index,
                "note": (
                    "per-generation seed = spec.seed + completed_ticks; "
                    "draws inside a generation are ordered on that stream, "
                    "so an inserted event moves every later draw"
                ),
            },
            "noise_coupling": NOISE_COUPLING,
            "parent_snapshot_id": parent_snapshot_id,
            "fork_isolation": isolation,
            "proxy_contract": proxy_contract,
            "live_objects": live,
        }

    def _fork_live_objects(self) -> dict[str, Any]:
        """The live objects a fork carries, keyed by the names used in the payload."""

        return {
            "population": self.runner.population,
            "world": self.runner.world,
            "nexus_layer": self.runner.nexus_layer,
            "qd_archive": self.qd_archive,
            "element_grid": self.element_grid,
        }

    def _state_digest(self) -> str:
        tick_index = int(getattr(self, "_tick_offset", 0)) + len(self._tick_results)
        return _checkpoint_digest(
            tick_index=tick_index,
            population=self.runner.population,
            world=self.runner.world,
            nexus_layer=self.runner.nexus_layer,
            qd_archive=self.qd_archive,
            element_grid=self.element_grid,
        )

    def _fork_isolation_map(self) -> dict[str, str]:
        """Actual isolation outcome for this engine's live fork objects."""

        status: dict[str, str] = {}
        for name, value in self._fork_live_objects().items():
            if value is None:
                status[name] = _ABSENT
                continue
            try:
                clone = _isolated_copy(value)
            except Exception:
                status[name] = _SHARED_REFERENCE
                continue
            status[name] = _SHARED_REFERENCE if clone is value else _DEEP_COPIED
        return status

    def fork_audit_payload(
        self, *, parent_snapshot_id: str | None = None
    ) -> dict[str, JsonValue]:
        """Serialisable audit. This record cannot restore a branch.

        ``fork_state_exact`` is true only when a freeze taken now digests to
        the same checkpoint as the live engine. It is not a constant.
        """

        try:
            fork = self.capture_fork(parent_snapshot_id=parent_snapshot_id)
        except ConfigurationError:
            isolation = self._fork_isolation_map()
            return {
                "record_role": "serialisable_audit",
                "fork_version": FORK_CHECKPOINT_VERSION,
                "run_id": self.run.run_id,
                "spec_digest": self.spec.digest(),
                "seed": int(self.spec.seed),
                "tick_index": int(getattr(self, "_tick_offset", 0)) + len(self._tick_results),
                "state_digest": "",
                "population_digest": str(self.runner.population.digest()),
                "world_digest": str(self.runner.world.digest()),
                "parent_snapshot_id": parent_snapshot_id,
                "fork_isolation": isolation,
                "fork_state_exact": False,
                "noise_coupling": NOISE_COUPLING,
                "proxy_contract": [],
                "live_payload_is_in_memory_only": True,
                "restorable": False,
            }
        exact = self._state_digest() == fork["state_digest"] and all(
            value in (_DEEP_COPIED, _ABSENT) for value in fork["fork_isolation"].values()
        )
        return {
            "record_role": "serialisable_audit",
            "fork_version": int(fork["fork_version"]),
            "run_id": str(fork["run_id"]),
            "spec_digest": str(fork["spec_digest"]),
            "seed": int(fork["seed"]),
            "tick_index": int(fork["tick_index"]),
            "state_digest": str(fork["state_digest"]),
            "population_digest": str(self.runner.population.digest()),
            "world_digest": str(self.runner.world.digest()),
            "parent_snapshot_id": fork["parent_snapshot_id"],
            "fork_isolation": dict(fork["fork_isolation"]),
            "fork_state_exact": bool(exact),
            "noise_coupling": str(fork["noise_coupling"]),
            "proxy_contract": list(fork["proxy_contract"]),
            "live_payload_is_in_memory_only": True,
            "restorable": False,
        }

    @classmethod
    def from_fork(
        cls,
        spec: Any,
        fork: Mapping[str, Any],
        *,
        generation_boundary_observers: Sequence[Any] | None = None,
        allow_spec_change: bool = False,
        spec_change_reason: str | None = None,
    ) -> GenesisEngine:
        """Restore a branch from a frozen checkpoint, then copy it again.

        The second copy keeps the stored payload independent of the branch.
        Seed, spec digest and payload version are checked. A different spec is
        refused unless ``allow_spec_change`` is set and a reason is given; that
        restore is recorded and is not exact.
        """

        if fork.get("record_role") == "serialisable_audit":
            msg = "a serialisable audit cannot restore a branch."
            raise ConfigurationError(msg)
        if int(fork.get("fork_version", 0)) != FORK_CHECKPOINT_VERSION:
            msg = f"fork payload must carry fork_version == {FORK_CHECKPOINT_VERSION}."
            raise ValueError(msg)
        source = fork.get("live_objects") or {}
        if "population" not in source or "world" not in source:
            msg = "recoverable checkpoint is missing frozen population or world."
            raise ConfigurationError(msg)
        spec_changed = str(fork.get("spec_digest")) != str(spec.digest()) or int(
            fork.get("seed", -1)
        ) != int(spec.seed)
        if spec_changed:
            if not allow_spec_change:
                msg = (
                    "checkpoint spec digest or seed does not match the restore spec. "
                    "Pass allow_spec_change and spec_change_reason to do this on purpose."
                )
                raise ConfigurationError(msg)
            if not spec_change_reason:
                msg = "an intentional spec change requires spec_change_reason."
                raise ConfigurationError(msg)
        engine = cls.from_spec(spec, generation_boundary_observers=generation_boundary_observers)
        isolation: dict[str, str] = {}
        taken: dict[str, Any] = {}
        for name in ("population", "world", "nexus_layer", "qd_archive", "element_grid"):
            value = source.get(name)
            if value is None:
                isolation[name] = _ABSENT
                continue
            try:
                clone = _isolated_copy(value)
            except Exception as exc:
                msg = (
                    f"fork isolation refused: cannot copy live object {name!r} "
                    f"({type(exc).__name__}: {exc})."
                )
                raise ConfigurationError(msg) from exc
            if clone is value:
                msg = f"fork isolation refused: live object {name!r} was not copied."
                raise ConfigurationError(msg)
            isolation[name] = _DEEP_COPIED
            taken[name] = clone
        engine.runner.population = taken["population"]
        engine.runner.world = taken["world"]
        if "nexus_layer" in taken:
            engine.runner.nexus_layer = taken["nexus_layer"]
        if "qd_archive" in taken:
            engine.qd_archive = taken["qd_archive"]
        if "element_grid" in taken:
            engine.element_grid = taken["element_grid"]
        engine._tick_offset = int(fork["tick_index"])
        engine._tick_results = []
        engine._snapshots = []
        engine.fork_isolation = isolation
        engine.fork_provenance = {
            "checkpoint_version": FORK_CHECKPOINT_VERSION,
            "checkpoint_spec_digest": str(fork.get("spec_digest")),
            "restore_spec_digest": str(spec.digest()),
            "spec_change_reason": spec_change_reason if spec_changed else None,
        }
        engine.fork_state_exact = (
            not spec_changed
            and engine._state_digest() == str(fork.get("state_digest"))
            and all(value in (_DEEP_COPIED, _ABSENT) for value in isolation.values())
        )
        return engine

    def snapshot(self) -> GenesisSnapshot:
        return GenesisSnapshot(
            run_id=self.run.run_id,
            population=PopulationSnapshot.from_population(
                self.runner.population, self.runner.nexus_layer
            ),
            world_digest=self.runner.world.digest(),
            qd_archive_digest=None if self.qd_archive is None else self.qd_archive.digest(),
            element_grid_digest=None if self.element_grid is None else self.element_grid.digest(),
            substrate_bridge_mode=self.spec.substrate_bridge_mode,
        )

    def export_evidence_pack(self) -> RunArtifactSchema:
        if self._last_result is None:
            return self._build_result().evidence_pack
        return self._last_result.evidence_pack

    def export_replay_bundle(self) -> ReplayBundle:
        if self._last_result is None:
            return self._build_result().replay_bundle
        return self._last_result.replay_bundle

    def build_review_request(self) -> LLMReviewRequest:
        return LLMReviewRequest.from_evidence_pack(
            self.export_evidence_pack(), request_id=f"review:{self.run.run_id}"
        )

    def record_review_result(
        self, result: LLMReviewResult, *, reviewer: str | None = None
    ) -> GenesisRunResult:
        """Validate a provider-neutral review result and attach review status to the manifest."""

        request = self.build_review_request()
        validated = validate_review_result(result, request=request)
        self.review_status = ReviewStatus(
            status="accepted" if validated.claim_review.allowed else "flagged",
            reviewer=reviewer or validated.reviewer_id,
            decision_digest=validated.digest(),
        )
        self._last_result = self._build_result()
        return self._last_result

    def _update_qd(self, generation: GenerationResult) -> QDArchiveBatchUpdateResult | None:
        if self.qd_archive is None:
            return None
        candidates: list[QDElite] = []
        for record in generation.organism_records:
            if record.behavior_descriptor is None:
                continue
            descriptor = record.behavior_descriptor.to_dict()
            reduced = {
                "survival_ticks": _json_float_value(descriptor.get("survival_ticks", 0.0)),
                "blocked_ratio": _json_float_value(descriptor.get("blocked_ratio", 0.0)),
            }
            behavior_bin = assign_behavior_bin(reduced, self.qd_archive.config.schema)
            candidates.append(
                QDElite(
                    organism_id=record.organism_id,
                    fitness=record.fitness_result.score,
                    behavior_descriptor=reduced,
                    behavior_bin=behavior_bin,
                    genome_digest=record.genome_digest or "missing_genome_digest",
                    trace_digest=record.trace_digest,
                    metadata={
                        "source": "GenesisEngine",
                        "provenance_status": "verified_genome_digest"
                        if record.genome_digest
                        else "missing_genome_digest",
                    },
                )
            )
        if not candidates:
            return None
        before = self.qd_archive.digest()
        current = self.qd_archive
        records: list[QDArchiveItemUpdateRecord] = []
        inserted = replaced = rejected = 0
        for candidate in candidates:
            update = update_qd_archive(current, candidate)
            current = update.archive
            records.append(QDArchiveItemUpdateRecord.from_update_result(update))
            inserted += int(update.inserted)
            replaced += int(update.replaced)
            rejected += int(update.rejected)
        self.qd_archive = current
        return QDArchiveBatchUpdateResult(
            archive_before_digest=before,
            archive_after_digest=current.digest(),
            candidates_seen=len(candidates),
            inserted_count=inserted,
            replaced_count=replaced,
            rejected_count=rejected,
            update_records=tuple(records),
            summary=summarize_qd_archive(current),
        )

    def _apply_qd_parent_feedback(self, generation: GenerationResult) -> None:
        """Use QD archive novelty to deterministically order/select next-generation parents."""
        if (
            self.qd_archive is None
            or not self.spec.engine_config.enable_qd
            or self.spec.engine_config.qd_mode != "selection_pressure"
        ):
            return
        evolution = _effective_evolution_config(self.spec)
        if evolution is None or evolution.novelty_weight <= 0:
            return
        organisms = tuple(self.runner.population.organisms)
        if len(organisms) <= 1:
            return
        descriptors: dict[str, dict[str, float]] = {}
        fitness_scores: dict[str, float] = {}
        for record in generation.organism_records:
            if record.behavior_descriptor is not None:
                descriptors[record.organism_id] = {
                    key: _json_float_value(value)
                    for key, value in record.behavior_descriptor.to_dict().items()
                    if isinstance(value, int | float) and not isinstance(value, bool)
                }
            fitness_scores[record.organism_id] = record.fitness_result.score
        novelty_scores = compute_novelty_scores_from_archive(
            organisms, descriptors, self.qd_archive
        )
        feedback_config = EvolutionConfig(
            selection_policy="novelty_weighted",
            elitism_count=evolution.elitism_count,
            tournament_size=evolution.tournament_size,
            novelty_weight=evolution.novelty_weight,
            fitness_weight=evolution.fitness_weight,
            max_population=len(organisms),
            extinction_policy=evolution.extinction_policy,
            qd_mode="selection_pressure",
        )
        selected, _selection_result = select_population(
            organisms,
            fitness_scores=fitness_scores,
            novelty_scores=novelty_scores,
            max_population=len(organisms),
            config=feedback_config,
            qd_mode="selection_pressure",
        )
        selected_organisms = tuple(cast(GenesisOrganism, item) for item in selected)
        if tuple(org.id for org in selected_organisms) != tuple(org.id for org in organisms):
            self.runner.population = replace(self.runner.population, organisms=selected_organisms)
            self._qd_parent_feedback_applied = True

    def _build_result(self) -> GenesisRunResult:
        snapshot = self.snapshot()
        generation_digests = tuple(item.generation_result.digest() for item in self._tick_results)
        raw_events = _raw_events(self._tick_results)
        contribution_ledgers = _contribution_ledgers_from_raw_events(
            raw_events, self.runner.population.generation
        )
        semantic_report = (
            None
            if self.spec.translation_profile is None
            else build_semantic_proxy_report(
                self.spec.translation_profile,
                behavior_delta_digest=_digest(
                    {
                        "ticks": len(self._tick_results),
                        "population": self.runner.population.digest(),
                    }
                ),
                lineage_persistence=self.runner.population.generation,
                replay_captured=True,
            )
        )
        phase2_hashes = _phase2_hashes(
            engine=self,
            contribution_ledgers=contribution_ledgers,
            semantic_report_digest=None if semantic_report is None else semantic_report.digest,
        )
        replay_seed_payload: dict[str, JsonValue] = {
            "run": self.run.to_dict(),
            "snapshots": cast(JsonValue, [item.to_dict() for item in self._snapshots]),
            "generation_digests": cast(JsonValue, list(generation_digests)),
            "phase2_hashes": cast(JsonValue, phase2_hashes),
        }
        replay_digest = _digest(replay_seed_payload)
        manifest_rng = RNGManager(seed=self.spec.seed, namespace="engine_manifest")
        seed_schedule_digest = _digest(
            {
                "seed": self.spec.seed,
                "tick_count": len(self._tick_results),
                "schedule": cast(
                    JsonValue,
                    [self.spec.seed + index for index in range(len(self._tick_results))],
                ),
            }
        )
        source_digest = compute_source_digest()
        evidence_flags = _claim_evidence_flags(self, contribution_ledgers, semantic_report)
        evidence_digests = tuple(
            value
            for value in (
                replay_digest,
                snapshot.digest(),
                None if self.qd_archive is None else self.qd_archive.digest(),
                None
                if not contribution_ledgers
                else _digest(
                    {"ledgers": cast(JsonValue, [ledger.digest for ledger in contribution_ledgers])}
                ),
            )
            if value
        )
        claim_decision = ScientificClaimGate().decide(
            ClaimRequest(
                self.spec.engine_config.claim_level,
                evidence_flags,
                manifest_digest=None,
                evidence_digests=evidence_digests,
            )
        )
        claim_gate_decision_digest = claim_decision.digest
        phase2_hashes = {
            **phase2_hashes,
            "claim_gate_decision_digest": claim_gate_decision_digest,
            "phase2_claim_decision_digest": claim_gate_decision_digest,
        }
        ribosome = self.spec.resolved_ribosome()
        codon_table = self.spec.codon_table or ribosome.codon_table
        manifest = manifest_from_parts(
            run_id=self.run.run_id,
            seed=self.run.seed,
            config=self.spec.to_dict(),
            codon_table_hash=_codon_table_hash(codon_table),
            genome_spec_hash=_genome_spec_hash(
                self.spec.genome_spec or codon_table.spec.genome_spec
            ),
            rule_set_hash=_digest({"approved_rule_set": None})
            if self.spec.approved_rule_set is None
            else self.spec.approved_rule_set.digest(),
            adf_vocabulary_hash=_adf_vocabulary_hash(codon_table),
            initial_population_hash=self._snapshots[0].population_digest,
            tick_count=len(self._tick_results),
            replay_digest=replay_digest,
            claim_level=claim_decision.final_claim,
            claim_decision=claim_decision,
            protocol_statuses=_protocol_statuses(self, phase2_hashes),
            manifest_schema_complete=True,
            scientific_protocol_executed=_scientific_protocol_executed(self, phase2_hashes),
            review_status=self.review_status,
            runtime_hashes={
                "action_registry_hash": _action_registry_hash(self.spec.action_registry),
                "ribosome_hash": _ribosome_hash(ribosome),
                "engine_config_hash": _object_hash(self.spec.engine_config),
                "population_config_hash": _object_hash(self.runner.configs),
                "evolution_config_hash": _object_hash(self.spec.evolution_config),
                "capsule_transfer_config_hash": _object_hash(self.runner.configs.capsule_transfer),
                "qd_archive_config_hash": _object_hash(
                    None if self.qd_archive is None else self.qd_archive.config
                ),
                "substrate_bridge_mode": self.spec.substrate_bridge_mode,
                "element_grid_hash": None
                if self.element_grid is None
                else self.element_grid.digest(),
                **phase2_hashes,
            },
            source_digest=source_digest,
            rng_backend_kind=self.spec.engine_config.rng_backend_kind,
            rng_namespace=manifest_rng.namespace,
            rng_draw_count=manifest_rng.draw_count + len(self._tick_results),
            rng_state_digest=manifest_rng.state_digest(),
            seed_schedule_digest=seed_schedule_digest,
            fitness_config_hash=_object_hash(self.runner.configs.fitness),
            descriptor_schema_hash=None
            if self.qd_archive is None
            else self.qd_archive.config.schema.digest(),
            archive_digest=None if self.qd_archive is None else self.qd_archive.digest(),
            qd_scheduler_digest=_qd_scheduler_manifest_digest(
                self, phase2_hashes, manifest_rng.state_digest()
            ),
            benchmark_scenario_digest=str(self.spec.metadata.get("benchmark_scenario_digest"))
            if "benchmark_scenario_digest" in self.spec.metadata
            else None,
            execution_source_digest=_execution_source_digest(
                raw_events, enabled=self.spec.enable_execution_source
            ),
            claim_gate_decision_digest=claim_gate_decision_digest,
        )
        summary = _summarize_run(
            self.run.run_id, self._tick_results, self.runner.population, self.qd_archive
        )
        evidence_pack = RunArtifactSchema(
            manifest=manifest,
            summary=summary,
            snapshot=snapshot.population,
            raw_events=raw_events,
            contribution_ledgers=tuple(ledger.to_dict() for ledger in contribution_ledgers),
        )
        replay_bundle = ReplayBundle(
            manifest=manifest,
            snapshots=tuple(self._snapshots),
            generation_digests=generation_digests,
        )
        action_wiring_matrix = export_action_wiring_matrix(
            action_registry=self.spec.action_registry,
            codon_table=codon_table,
            profile_name="engine_run",
        )
        provisional_result = GenesisRunResult(
            run=self.run,
            ticks=tuple(self._tick_results),
            manifest=manifest,
            snapshot=snapshot,
            evidence_pack=evidence_pack,
            replay_bundle=replay_bundle,
            action_wiring_matrix=action_wiring_matrix,
            strong_claim_ladder_records=(),
        )
        return replace(
            provisional_result,
            strong_claim_ladder_records=_strong_claim_ladder_records_for_result(
                provisional_result,
                claim_gate_decision_digest=claim_gate_decision_digest,
            ),
        )


__all__ = [
    "GenesisEngine",
    "_effective_evolution_config",
    "_default_qd_archive",
]
