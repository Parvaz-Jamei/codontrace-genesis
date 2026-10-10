"""GenesisEngine orchestrator — population stepping, QD, and result build.

Extracted from ``codontrace.engine`` for debuggability. Public imports stay on
the ``codontrace.engine`` facade. GenerationBoundaryObserver is invoked once
per completed generation in ``run_ticks`` (domain-free; no HP payload).
See ``docs/ENGINE_REPLAY_CONTRACT.md``.
"""

from __future__ import annotations

import enum
import importlib
import json
import math
import warnings
from collections.abc import Mapping, Sequence
from copy import deepcopy
from dataclasses import fields, is_dataclass, replace
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
from codontrace.genesis.behavior import BehaviorDescriptor
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
from codontrace.genesis.qd_descriptors import (
    _DEFAULT_RANGES,
    QDDescriptorRegistry,
    compute_novelty_scores_from_archive,
)
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


KNOWN_DESCRIPTOR_ALIASES: dict[str, str] = {
    "path_entropy": "path_entropy_lite",
    "resource_gain": "resource_interactions",
    "energy_efficiency": "energy_profile",
    "capsules_emitted": "capsule_emit_count",
    "capsules_read": "capsule_read_count",
    "capsules_adopted": "capsule_adoption_count",
    "capsule_usage": "capsule_adoption_count",
    "action_distribution_entropy": "movement_diversity",
    "offspring_count": "reproduction_count",
    "nexus_interaction_count": "nexus_emitted",
    "environmental_footprint": "unique_positions",
    "causal_prediction_accuracy": "causal_prediction_correct",
    "causal_graph_size": "causal_update_count",
    "causal_graph_compactness": "causal_update_count",
    "ADF_usage_count": "tool_chain_stage",
    "ADF_reuse_score": "tool_chain_stage",
    "cooperation_score": "social_interaction_count",
    "free_rider_score": "social_interaction_count",
    "mutation_distance": "survival_ticks",
    "genome_length": "survival_ticks",
}


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
FORK_CHECKPOINT_VERSION = 3
_CHECKPOINT_FORMAT = "codontrace-checkpoint-recipe-v1"
CONTINUATION_RECORD_VERSION = 1
NOISE_COUPLING = "stream_position"
_NOISE_NAMESPACE = "fork-noise-contract"
_CODE_TYPES = (FunctionType, BuiltinFunctionType, MethodDescriptorType, WrapperDescriptorType)


def _is_code(value: Any) -> bool:
    if isinstance(value, FunctionType) and value.__closure__:
        return False
    return isinstance(value, _CODE_TYPES) or isinstance(value, type)


def _refuse_bound_closures(value: Any) -> None:
    """A closure cell is shared by deepcopy. Do not call that isolation."""

    seen: set[int] = set()
    stack: list[Any] = [value]
    while stack:
        item = stack.pop()
        marker = id(item)
        if marker in seen:
            continue
        seen.add(marker)
        if isinstance(item, FunctionType) and item.__closure__:
            msg = "fork isolation refused: a closure would share mutable cells across branches."
            raise ConfigurationError(msg)
        if item is None or isinstance(item, (bool, int, float, str, bytes)) or _is_code(item):
            continue
        if isinstance(item, Mapping):
            stack.extend(item.keys())
            stack.extend(item.values())
            continue
        if isinstance(item, (list, tuple, set, frozenset)):
            stack.extend(item)
            continue
        fields = getattr(item, "__dataclass_fields__", None)
        if isinstance(fields, dict):
            for name in fields:
                try:
                    stack.append(getattr(item, name))
                except Exception:
                    continue
            continue
        namespace = getattr(item, "__dict__", None)
        if isinstance(namespace, dict):
            stack.extend(namespace.values())


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

    _refuse_bound_closures(value)
    clone, _report = _isolated_copy_report(value)
    return clone


def _isolated_copy_report(value: Any) -> tuple[Any, tuple[dict[str, Any], ...]]:
    memo, report = _proxy_memo(value)
    return deepcopy(value, memo), report


def _type_token(cls: type) -> str:
    return f"{cls.__module__}:{cls.__qualname__}"


def _resolve_type(token: str) -> type:
    module_name, separator, qualname = token.partition(":")
    if separator != ":" or not qualname or "<" in qualname:
        msg = "checkpoint type token is not a package type."
        raise ConfigurationError(msg)
    if module_name != "codontrace" and not module_name.startswith("codontrace."):
        msg = "checkpoint type is outside this package."
        raise ConfigurationError(msg)
    module = importlib.import_module(module_name)
    found: Any = module
    for part in qualname.split("."):
        found = getattr(found, part)
    if not isinstance(found, type):
        msg = "checkpoint type token does not name a type."
        raise ConfigurationError(msg)
    return found


def _encode_recipe(value: Any) -> dict[str, Any]:
    """Versioned rebuild recipe. Shared mutable objects keep their identity.

    Loading rebuilds package objects and named package functions. It does not
    run a caller-supplied callable. That is the point of refusing an executable
    memory dump: a checkpoint is a recipe for this package, not a program.
    """

    store: list[Any] = []
    memo: dict[int, int] = {}

    def intern(node_id: int) -> int:
        index = len(store)
        memo[node_id] = index
        store.append(None)
        return index

    def encode(item: Any) -> Any:
        if item is None:
            return item
        if isinstance(item, enum.Enum):
            return {"$enum": _type_token(type(item)), "name": item.name}
        if isinstance(item, (bool, str)):
            return item
        if isinstance(item, int):
            return item
        if isinstance(item, float):
            if math.isnan(item):
                return {"$float": "nan"}
            if math.isinf(item):
                return {"$float": "inf" if item > 0 else "-inf"}
            return item
        if isinstance(item, bytes):
            return {"$bytes": list(item)}
        if isinstance(item, FunctionType):
            if (
                not item.__module__.startswith("codontrace.")
                or "<" in item.__qualname__
            ):
                msg = "checkpoint cannot name a function outside this package."
                raise ConfigurationError(msg)
            return {"$fn": f"{item.__module__}:{item.__qualname__}"}
        if isinstance(item, (tuple, MappingProxyType, frozenset)):
            if isinstance(item, MappingProxyType):
                pairs = [[encode(key), encode(val)] for key, val in item.items()]
                return {"$proxy": pairs}
            if isinstance(item, frozenset):
                return {"$frozenset": [encode(part) for part in item]}
            return {"$tuple": [encode(part) for part in item]}
        seen = memo.get(id(item))
        if seen is not None:
            return {"$ref": seen}
        if isinstance(item, list):
            index = intern(id(item))
            store[index] = {"$list": [encode(part) for part in item]}
            return {"$ref": index}
        if isinstance(item, dict):
            index = intern(id(item))
            store[index] = {"$dict": [[encode(key), encode(val)] for key, val in item.items()]}
            return {"$ref": index}
        if isinstance(item, set):
            index = intern(id(item))
            store[index] = {"$set": [encode(part) for part in item]}
            return {"$ref": index}
        if is_dataclass(item) and not isinstance(item, type):
            index = intern(id(item))
            body = {field.name: encode(getattr(item, field.name)) for field in fields(item)}
            store[index] = {"$dc": _type_token(type(item)), "fields": body}
            return {"$ref": index}
        state = getattr(item, "__dict__", None)
        if isinstance(state, dict):
            index = intern(id(item))
            body = {str(key): encode(val) for key, val in state.items()}
            store[index] = {"$obj": _type_token(type(item)), "fields": body}
            return {"$ref": index}
        msg = f"checkpoint cannot record {type(item).__name__}."
        raise ConfigurationError(msg)

    root = encode(value)
    return {"$format": _CHECKPOINT_FORMAT, "objects": store, "root": root}


def _decode_recipe(encoded: Mapping[str, Any]) -> Any:
    if encoded.get("$format") != _CHECKPOINT_FORMAT:
        msg = "checkpoint bytes are not a recoverable fork payload."
        raise ConfigurationError(msg)
    objects = encoded.get("objects")
    if not isinstance(objects, list):
        msg = "checkpoint bytes are not a recoverable fork payload."
        raise ConfigurationError(msg)
    shells: list[Any] = []
    for node in objects:
        if not isinstance(node, dict):
            msg = "checkpoint record is not an object recipe."
            raise ConfigurationError(msg)
        if "$list" in node:
            shells.append([])
        elif "$dict" in node:
            shells.append({})
        elif "$set" in node:
            shells.append(set())
        elif "$dc" in node or "$obj" in node:
            shells.append(object.__new__(_resolve_type(str(node.get("$dc") or node.get("$obj")))))
        else:
            msg = "checkpoint record is not an object recipe."
            raise ConfigurationError(msg)

    def resolve(item: Any) -> Any:
        if item is None or isinstance(item, (bool, str, int, float)):
            return item
        if not isinstance(item, dict):
            msg = "checkpoint value is not a recipe."
            raise ConfigurationError(msg)
        if "$ref" in item:
            return shells[int(item["$ref"])]
        if "$float" in item:
            label = str(item["$float"])
            if label == "nan":
                return float("nan")
            if label == "inf":
                return float("inf")
            if label == "-inf":
                return float("-inf")
            msg = "checkpoint float label is not recognised."
            raise ConfigurationError(msg)
        if "$bytes" in item:
            return bytes(int(part) for part in item["$bytes"])
        if "$enum" in item:
            return cast(Any, _resolve_type(str(item["$enum"])))[str(item["name"])]
        if "$fn" in item:
            module_name, _, qualname = str(item["$fn"]).partition(":")
            if not module_name.startswith("codontrace.") or "<" in qualname:
                msg = "checkpoint function is outside this package."
                raise ConfigurationError(msg)
            found: Any = importlib.import_module(module_name)
            for part in qualname.split("."):
                found = getattr(found, part)
            if not isinstance(found, FunctionType):
                msg = "checkpoint function token does not name a function."
                raise ConfigurationError(msg)
            return found
        if "$tuple" in item:
            return tuple(resolve(part) for part in item["$tuple"])
        if "$frozenset" in item:
            return frozenset(resolve(part) for part in item["$frozenset"])
        if "$proxy" in item:
            return MappingProxyType({resolve(key): resolve(val) for key, val in item["$proxy"]})
        msg = "checkpoint value is not a recipe."
        raise ConfigurationError(msg)

    for index, node in enumerate(objects):
        shell = shells[index]
        if "$list" in node:
            shell.extend(resolve(part) for part in node["$list"])
        elif "$dict" in node:
            for key, val in node["$dict"]:
                shell[resolve(key)] = resolve(val)
        elif "$set" in node:
            shell.update(resolve(part) for part in node["$set"])
        else:
            for name, val in node["fields"].items():
                object.__setattr__(shell, str(name), resolve(val))
    return resolve(encoded.get("root"))


def checkpoint_bytes(fork: Mapping[str, Any]) -> bytes:
    """Bytes for a fresh process. Not a format for untrusted input.

    The serialisable audit stays JSON and cannot restore a branch. This record
    can, because it is a versioned rebuild recipe: package objects and named
    package functions only. A caller-supplied callable is refused.
    """

    if fork.get("record_role") != "recoverable_checkpoint":
        msg = "only a recoverable checkpoint can be persisted."
        raise ConfigurationError(msg)
    return json.dumps(_encode_recipe(dict(fork)), allow_nan=False, separators=(",", ":")).encode("utf-8")


def checkpoint_from_bytes(blob: bytes) -> dict[str, Any]:
    """Load bytes written by :func:`checkpoint_bytes` in this or another process."""

    try:
        encoded = json.loads(blob.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        msg = "checkpoint bytes are not a recoverable fork payload."
        raise ConfigurationError(msg) from exc
    if not isinstance(encoded, dict):
        msg = "checkpoint bytes are not a recoverable fork payload."
        raise ConfigurationError(msg)
    loaded = _decode_recipe(encoded)
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

    rng = RNGManager(seed=int(seed) + int(tick), namespace=_NOISE_NAMESPACE)
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


def _callable_token(fn: object) -> str | None:
    module = getattr(fn, "__module__", None)
    qualname = getattr(fn, "__qualname__", None)
    if not isinstance(module, str) or not isinstance(qualname, str):
        return None
    if not module.startswith("codontrace.") or "<" in qualname:
        return None
    return f"{module}:{qualname}"


def _as_record(value: object) -> object:
    if value is None:
        return None
    to_dict = getattr(value, "to_dict", None)
    if callable(to_dict):
        return to_dict()
    digest = getattr(value, "digest", None)
    if callable(digest):
        return digest()
    return None


def _organism_continuation(organism: object) -> tuple[dict[str, object], bool]:
    """Fields that can change the next tick, beyond the population summary.

    A field with no package record is not hashed. Coverage is then incomplete
    and a checkpoint must not be called exact.
    """

    covered = True
    handlers: dict[str, str] = {}
    registry = getattr(organism, "action_registry", None)
    raw_handlers = getattr(registry, "_handlers", {})
    for name in sorted(raw_handlers):
        token = _callable_token(raw_handlers[name])
        if token is None:
            covered = False
            continue
        handlers[name] = token
    runtime = getattr(organism, "action_runtime_config", None)
    status_registry = getattr(runtime, "status_registry", None)
    status_record = _as_record(status_registry)
    if status_registry is not None and status_record is None:
        covered = False
    profile = getattr(organism, "translation_profile", None)
    profile_record = _as_record(profile)
    if profile is not None and profile_record is None:
        covered = False
    causal = getattr(organism, "causal_graph", None)
    causal_record = _as_record(causal)
    if causal is not None and causal_record is None:
        covered = False
    adf_registry = getattr(organism, "adf_macro_registry", None)
    adf_record = _as_record(adf_registry)
    if adf_registry is not None and adf_record is None:
        covered = False
    ribosome = getattr(organism, "ribosome", None)
    ribosome_record = _as_record(ribosome)
    if ribosome is not None and ribosome_record is None:
        table = getattr(ribosome, "codon_table", None)
        ribosome_record = _as_record(getattr(table, "spec", None))
        if ribosome_record is None:
            covered = False
    nav = getattr(organism, "capsule_nav_target", None)
    record: dict[str, object] = {
        "version": CONTINUATION_RECORD_VERSION,
        "low_energy_ticks": int(getattr(organism, "_low_energy_ticks", 0)),
        "execution_source_enabled": bool(getattr(organism, "execution_source_enabled", False)),
        "action_handlers": handlers,
        "action_open_statuses": bool(getattr(runtime, "open_statuses", False)),
        "action_status_registry": status_record,
        "causal_graph": causal_record,
        "translation_policy": _as_record(getattr(organism, "translation_policy", None)),
        "translation_profile": profile_record,
        "adf_execution_policy": _as_record(getattr(organism, "adf_execution_policy", None)),
        "adf_macro_registry": adf_record,
        "ribosome": ribosome_record,
        "capsule_action_bias": getattr(organism, "capsule_action_bias", None),
        "capsule_nav_target": None if nav is None else [int(nav[0]), int(nav[1])],
        "last_task_class": getattr(organism, "last_task_class", None),
    }
    if record["translation_policy"] is None and getattr(organism, "translation_policy", None) is not None:
        covered = False
    if record["adf_execution_policy"] is None and getattr(organism, "adf_execution_policy", None) is not None:
        covered = False
    return record, covered


def _population_continuation(population: object) -> tuple[dict[str, object], bool]:
    covered = True
    organisms = []
    for organism in getattr(population, "organisms", ()):
        record, organism_covered = _organism_continuation(organism)
        organisms.append(record)
        covered = covered and organism_covered
    return {
        "version": CONTINUATION_RECORD_VERSION,
        "population_summary_digest": str(cast(Any, population).digest()),
        "organisms": organisms,
    }, covered


def _checkpoint_digest(
    *,
    tick_index: int,
    population: Any,
    world: Any,
    nexus_layer: Any,
    qd_archive: Any,
    element_grid: Any,
    configs: Any,
    qd_parent_feedback_applied: bool,
) -> tuple[str, bool]:
    continuation, covered = _population_continuation(population)
    payload = {
        "continuation_version": CONTINUATION_RECORD_VERSION,
        "continuation_covered": covered,
        "tick_index": int(tick_index),
        "population": str(population.digest()),
        "continuation": continuation,
        "world": str(world.digest()),
        "nexus": None if nexus_layer is None else str(nexus_layer.digest()),
        "qd_archive": None if qd_archive is None else str(qd_archive.digest()),
        "element_grid": None if element_grid is None else str(element_grid.digest()),
        "configs": canonical_digest(configs.to_dict(), prefix="configs"),
        "qd_parent_feedback_applied": bool(qd_parent_feedback_applied),
    }
    return canonical_digest(payload, prefix="fork_checkpoint"), covered


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
        qd_descriptor_registry: QDDescriptorRegistry | None = None,
    ) -> None:
        self.spec = spec
        self.runner = runner
        self.run = run
        self.qd_archive = qd_archive
        self.qd_descriptor_registry = qd_descriptor_registry
        self.element_grid = spec.element_grid
        self.review_status = ReviewStatus()
        self.config_reconciliation: dict[str, Any] = {}
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
        qd_descriptor_registry: QDDescriptorRegistry | None = None,
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
        reconciliation_applied = False
        reconciliation_warnings: list[str] = []
        if spec.population_configs is not None:
            configs = spec.population_configs
            if capsule_config is not None:
                if configs.capsule_transfer is None:
                    configs = replace(
                        configs,
                        capsule_transfer=capsule_config,
                        enable_nexus_stigmergy=True,
                    )
                    reconciliation_applied = True
                elif not configs.capsule_transfer.enabled and capsule_config.enabled:
                    w = (
                        "Conflicting capsule configuration: spec requested capsules but "
                        "spec.population_configs.capsule_transfer is explicitly disabled. "
                        "Respecting explicit population_configs setting."
                    )
                    warnings.warn(w, UserWarning, stacklevel=2)
                    reconciliation_warnings.append(w)
            elif (
                configs.capsule_transfer is not None
                and configs.capsule_transfer.enabled
                and not spec.engine_config.enable_capsules
            ):
                w = (
                    "Conflicting capsule configuration: spec.engine_config.enable_capsules is False but "
                    "spec.population_configs.capsule_transfer is enabled. "
                    "Respecting explicit population_configs setting."
                )
                warnings.warn(w, UserWarning, stacklevel=2)
                reconciliation_warnings.append(w)
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
        registry = qd_descriptor_registry or getattr(spec, "qd_descriptor_registry", None)
        qd_archive = (
            QDArchive.empty(spec.qd_archive_config)
            if spec.qd_archive_config is not None
            else (_default_qd_archive() if spec.engine_config.enable_qd else None)
        )
        if qd_archive is not None:
            for desc_name in qd_archive.config.schema.descriptor_names:
                resolvable = (
                    (registry is not None and desc_name in registry._extractors)
                    or desc_name in BehaviorDescriptor.__dataclass_fields__
                    or desc_name in KNOWN_DESCRIPTOR_ALIASES
                    or desc_name in _DEFAULT_RANGES
                )
                if not resolvable:
                    msg = (
                        f"QD descriptor {desc_name!r} defined in schema cannot be extracted: "
                        f"no extractor registered and field not present in BehaviorDescriptor."
                    )
                    raise ConfigurationError(msg)
        run_id = f"genesis-run-{spec.digest()[:16]}"
        engine = cls(
            spec=spec,
            runner=runner,
            run=GenesisRun(run_id=run_id, spec_digest=spec.digest(), seed=spec.seed),
            qd_archive=qd_archive,
            generation_boundary_observers=generation_boundary_observers,
            qd_descriptor_registry=registry,
        )
        engine.config_reconciliation = {
            # Report the resolved top-level request, before population overrides.
            # A non-None population config does not erase the engine default.
            "requested_capsules_enabled": bool(
                capsule_config is not None and capsule_config.enabled
            ),
            "effective_capsules_enabled": bool(
                configs.capsule_transfer is not None and configs.capsule_transfer.enabled
            ),
            "requested_capsule_config": None
            if capsule_config is None
            else capsule_config.to_dict(),
            "effective_capsule_config": None
            if configs.capsule_transfer is None
            else configs.capsule_transfer.to_dict(),
            "reconciliation_applied": reconciliation_applied,
            "warnings": tuple(reconciliation_warnings),
        }
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
        state_digest, continuation_covered = _checkpoint_digest(
            tick_index=tick_index,
            population=live["population"],
            world=live["world"],
            nexus_layer=live.get("nexus_layer"),
            qd_archive=live.get("qd_archive"),
            element_grid=live.get("element_grid"),
            configs=live["configs"],
            qd_parent_feedback_applied=bool(self._qd_parent_feedback_applied),
        )
        generation_seed = int(self.spec.seed) + tick_index
        return {
            "record_role": "recoverable_checkpoint",
            "fork_version": FORK_CHECKPOINT_VERSION,
            "run_id": self.run.run_id,
            "spec_digest": self.spec.digest(),
            "seed": int(self.spec.seed),
            "tick_index": tick_index,
            "state_digest": state_digest,
            "continuation_covered": continuation_covered,
            "population": live["population"].to_dict(),
            "world": live["world"].to_dict(),
            "rng": RNGManager(seed=generation_seed, namespace=_NOISE_NAMESPACE).snapshot(
                include_state=True
            ),
            "rng_derivation": {
                "coupling": NOISE_COUPLING,
                "seed": int(self.spec.seed),
                "next_tick_seed": generation_seed,
                "note": (
                    "per-generation seed = spec.seed + completed_ticks; "
                    "draws inside a generation are ordered on that stream, "
                    "so an inserted event moves every later draw"
                ),
            },
            "noise_coupling": NOISE_COUPLING,
            "qd_parent_feedback_applied": bool(self._qd_parent_feedback_applied),
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
            "configs": self.runner.configs,
            "nexus_layer": self.runner.nexus_layer,
            "qd_archive": self.qd_archive,
            "element_grid": self.element_grid,
        }

    def _state_digest(self) -> str:
        digest, _covered = self._checkpoint_view()
        return digest

    def _continuation_covered(self) -> bool:
        _digest, covered = self._checkpoint_view()
        return covered

    def _checkpoint_view(self) -> tuple[str, bool]:
        tick_index = int(getattr(self, "_tick_offset", 0)) + len(self._tick_results)
        return _checkpoint_digest(
            tick_index=tick_index,
            population=self.runner.population,
            world=self.runner.world,
            nexus_layer=self.runner.nexus_layer,
            qd_archive=self.qd_archive,
            element_grid=self.element_grid,
            configs=self.runner.configs,
            qd_parent_feedback_applied=bool(self._qd_parent_feedback_applied),
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
                "fork_isolation": cast(JsonValue, isolation),
                "fork_state_exact": False,
                "noise_coupling": NOISE_COUPLING,
                "proxy_contract": [],
                "live_payload_is_in_memory_only": True,
                "restorable": False,
            }
        exact = (
            self._continuation_covered()
            and self._state_digest() == fork["state_digest"]
            and all(value in (_DEEP_COPIED, _ABSENT) for value in fork["fork_isolation"].values())
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
        require_exact: bool = False,
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
        if "population" not in source or "world" not in source or "configs" not in source:
            msg = "recoverable checkpoint is missing frozen population, world, or configs."
            raise ConfigurationError(msg)
        generation_seed = int(fork.get("seed", -1)) + int(fork["tick_index"])
        snapshot = fork.get("rng") or {}
        if int(snapshot.get("seed", -1)) != generation_seed or snapshot.get("namespace") != _NOISE_NAMESPACE:
            msg = "checkpoint rng snapshot is not the unused stream at seed + tick_index."
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
        engine.spec = _isolated_copy(spec)
        isolation: dict[str, str] = {}
        taken: dict[str, Any] = {}
        for name in ("population", "world", "configs", "nexus_layer", "qd_archive", "element_grid"):
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
        engine.runner.configs = taken["configs"]
        if "nexus_layer" in taken:
            engine.runner.nexus_layer = taken["nexus_layer"]
        if "qd_archive" in taken:
            engine.qd_archive = taken["qd_archive"]
        if "element_grid" in taken:
            engine.element_grid = taken["element_grid"]
        cast(Any, engine)._tick_offset = int(fork["tick_index"])
        engine._tick_results = []
        engine._snapshots = []
        engine._qd_parent_feedback_applied = bool(fork.get("qd_parent_feedback_applied", False))
        cast(Any, engine).fork_isolation = isolation
        cast(Any, engine).fork_provenance = {
            "checkpoint_version": FORK_CHECKPOINT_VERSION,
            "checkpoint_spec_digest": str(fork.get("spec_digest")),
            "restore_spec_digest": str(spec.digest()),
            "spec_change_reason": spec_change_reason if spec_changed else None,
        }
        cast(Any, engine).fork_state_exact = (
            bool(engine._continuation_covered())
            and not spec_changed
            and engine._state_digest() == str(fork.get("state_digest"))
            and all(value in (_DEEP_COPIED, _ABSENT) for value in isolation.values())
        )
        if require_exact and not cast(Any, engine).fork_state_exact:
            msg = (
                "checkpoint is not an exact continuation state. "
                "A scientific path must not consume it."
            )
            raise ConfigurationError(msg)
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

    def _extract_qd_descriptor_value(
        self,
        name: str,
        record: Any,
        descriptor_dict: Mapping[str, Any],
    ) -> float:
        if self.qd_descriptor_registry is not None and name in self.qd_descriptor_registry._extractors:
            extractor = self.qd_descriptor_registry._extractors[name]
            try:
                return float(extractor(record))
            except Exception:
                if getattr(record, "behavior_descriptor", None) is not None:
                    return float(extractor(record.behavior_descriptor))
                raise

        if name in descriptor_dict:
            val = descriptor_dict[name]
            if isinstance(val, int | float) and not isinstance(val, bool):
                return float(val)

        if name in KNOWN_DESCRIPTOR_ALIASES:
            alias = KNOWN_DESCRIPTOR_ALIASES[name]
            if alias in descriptor_dict:
                val = descriptor_dict[alias]
                if isinstance(val, int | float) and not isinstance(val, bool):
                    return float(val)

        if hasattr(record, name):
            val = getattr(record, name)
            if isinstance(val, int | float) and not isinstance(val, bool):
                return float(val)

        if name in KNOWN_DESCRIPTOR_ALIASES:
            alias = KNOWN_DESCRIPTOR_ALIASES[name]
            if hasattr(record, alias):
                val = getattr(record, alias)
                if isinstance(val, int | float) and not isinstance(val, bool):
                    return float(val)

        if name == "causal_prediction_accuracy":
            attempted = getattr(record, "causal_prediction_attempted", 0)
            correct = getattr(record, "causal_prediction_correct", 0)
            return float(correct / attempted) if attempted > 0 else 0.0

        return 0.0

    def _update_qd(self, generation: GenerationResult) -> QDArchiveBatchUpdateResult | None:
        if self.qd_archive is None:
            return None
        candidates: list[QDElite] = []
        for record in generation.organism_records:
            if record.behavior_descriptor is None:
                continue
            descriptor = record.behavior_descriptor.to_dict()
            reduced = {
                name: _json_float_value(self._extract_qd_descriptor_value(name, record, descriptor))
                for name in self.qd_archive.config.schema.descriptor_names
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
                desc_dict = {
                    key: _json_float_value(value)
                    for key, value in record.behavior_descriptor.to_dict().items()
                    if isinstance(value, int | float) and not isinstance(value, bool)
                }
                for name in self.qd_archive.config.schema.descriptor_names:
                    if name not in desc_dict:
                        desc_dict[name] = _json_float_value(
                            self._extract_qd_descriptor_value(
                                name, record, record.behavior_descriptor.to_dict()
                            )
                        )
                descriptors[record.organism_id] = desc_dict
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
