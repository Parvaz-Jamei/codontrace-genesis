"""Replay-critical digest helpers for the unified GENESIS engine.

These functions are the hashing surface used by ``GenesisExperimentSpec``
and engine result objects. Extracted from ``codontrace.engine`` so the
replay contract has a named module boundary. Behavior must stay byte-stable:
changing separators, key order, or float encoding here breaks Phase A–E
digest pins.

See ``docs/ENGINE_REPLAY_CONTRACT.md``.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from typing import Any, Protocol, cast, runtime_checkable

from codontrace._numeric import finite_json_dumps
from codontrace._types import JsonValue
from codontrace.actions import (
    ActionRegistry,
    ActionRuntimeConfig,
    default_action_registry,
    default_action_registry_manifest,
)
from codontrace.codon import CodonTable
from codontrace.genesis.ribosome import Ribosome
from codontrace.specs import GenomeSpec


@runtime_checkable
class _JsonDictSerializable(Protocol):
    def to_dict(self) -> dict[str, JsonValue]: ...


def _digest(payload: Mapping[str, JsonValue]) -> str:
    encoded = finite_json_dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _jsonish_for_digest(item: object) -> JsonValue:
    if isinstance(item, _JsonDictSerializable):
        return item.to_dict()
    if isinstance(item, Mapping):
        return cast(JsonValue, dict(item))
    if isinstance(item, tuple | list):
        return cast(JsonValue, [_jsonish_for_digest(value) for value in item])
    if isinstance(item, str | int | float | bool) or item is None:
        return cast(JsonValue, item)
    return str(item)


def _digest_sequence(items: Sequence[object]) -> str:
    return _digest({"items": [_jsonish_for_digest(item) for item in items]})


def _codon_table_hash(table: CodonTable) -> str:
    payload = {
        "table_name": table.spec.table_name,
        "allow_partial_tail": table.spec.allow_partial_tail,
        "genome_spec": table.spec.genome_spec.to_dict(),
        "codons": [
            {
                "bits": codon.bits,
                "action": codon.action_name,
                "cost": codon.cost,
                "description": codon.description,
            }
            for codon in table.actions()
        ],
    }
    return _digest(cast(dict[str, JsonValue], payload))


def _genome_spec_hash(spec: GenomeSpec) -> str:
    return _digest(spec.to_dict())


def _ribosome_hash(ribosome: Ribosome) -> str:
    return _digest(
        {
            "codon_table_hash": _codon_table_hash(ribosome.codon_table),
            "codon_table_version": ribosome.codon_table_version,
            "min_vitae": ribosome.min_vitae,
        }
    )


def _handler_identity_digest(handler: object) -> str:
    code = getattr(handler, "__code__", None)
    closure = getattr(handler, "__closure__", None)
    if code is None and callable(handler):
        call_method = handler.__call__
        code = getattr(call_method, "__code__", None)
        closure = getattr(call_method, "__closure__", None)
    closure_values: list[str] = []
    if closure:
        for cell in closure:
            try:
                closure_values.append(repr(cell.cell_contents))
            except ValueError:
                closure_values.append("<empty>")
    payload: dict[str, JsonValue] = {
        "module": str(getattr(handler, "__module__", "unknown")),
        "qualname": str(getattr(handler, "__qualname__", repr(handler))),
        "handler_version": getattr(handler, "__codontrace_version__", None),
        "handler_provenance": getattr(handler, "__codontrace_provenance__", None),
        "action_abi_digest": "action_result_v1",
        "bytecode_sha256": None if code is None else hashlib.sha256(code.co_code).hexdigest(),
        "constants_sha256": None
        if code is None
        else hashlib.sha256(repr(code.co_consts).encode("utf-8")).hexdigest(),
        "closure_sha256": hashlib.sha256(
            json.dumps(closure_values, sort_keys=True, allow_nan=False).encode("utf-8")
        ).hexdigest(),
    }
    return _digest(payload)


def _stable_default_action_registry_hash() -> str:
    return _digest(
        {
            "registry_version": "action_registry_digest_v3_stable_manifest",
            "actions": cast(JsonValue, list(default_action_registry_manifest())),
        }
    )


def _action_registry_hash(registry: ActionRegistry | None) -> str | None:
    resolved = default_action_registry() if registry is None else registry
    default_manifest = {item["name"]: item for item in default_action_registry_manifest()}
    default_names = set(default_manifest)
    if tuple(resolved.names()) == tuple(sorted(default_names)):
        return _stable_default_action_registry_hash()
    entries: list[dict[str, JsonValue]] = []
    for name in resolved.names():
        handler = resolved.get(name)
        if name in default_manifest:
            manifest: dict[str, JsonValue] = dict(default_manifest[name])
            manifest["handler_digest"] = _digest(
                {"built_in_action": name, "handler_stable_id": manifest["handler_stable_id"]}
            )
            manifest["replay_status"] = "built_in_replayable"
            entries.append(manifest)
            continue
        stable_id = None
        if handler is not None:
            module = getattr(handler, "__module__", "unknown")
            qualname = getattr(handler, "__qualname__", type(handler).__qualname__)
            stable_id = f"{module}:{qualname}"
        handler_version = getattr(handler, "__codontrace_version__", None)
        handler_provenance = getattr(
            handler, "__codontrace_provenance__", "non_replayable_external_handler"
        )
        entries.append(
            {
                "name": name,
                "handler_stable_id": stable_id,
                "handler_digest": None if handler is None else _handler_identity_digest(handler),
                "handler_version": handler_version if isinstance(handler_version, str) else None,
                "handler_provenance": handler_provenance
                if isinstance(handler_provenance, str)
                else "non_replayable_external_handler",
                "action_abi_version": "action_result_v1",
                "replay_status": "non_replayable_external_handler",
            }
        )
    return _digest(
        {
            "registry_version": "action_registry_digest_v3_stable_manifest",
            "actions": cast(JsonValue, entries),
        }
    )


def _status_registry_digest(value: ActionRuntimeConfig | None) -> str | None:
    if value is None:
        return None
    registry = value.status_registry
    return registry.digest() if hasattr(registry, "digest") else _object_hash(registry)


def _object_hash(value: object | None) -> str | None:
    if value is None:
        return None
    obj = cast(Any, value)
    if hasattr(obj, "digest"):
        return str(obj.digest())
    if hasattr(obj, "to_dict"):
        return _digest(cast(dict[str, JsonValue], obj.to_dict()))
    return _digest({"repr": repr(value)})


def _adf_vocabulary_hash(table: CodonTable) -> str:
    adf_codons = [
        {"bits": codon.bits, "action": codon.action_name, "cost": codon.cost}
        for codon in table.actions()
        if codon.action_name.startswith("ADF_")
    ]
    return _digest({"adf_codons": cast(JsonValue, adf_codons)})


def _json_float_value(value: JsonValue | None) -> float:
    if isinstance(value, bool) or not isinstance(value, int | float):
        return 0.0
    return float(value)


def _json_str_tuple(value: object) -> tuple[str, ...]:
    if not isinstance(value, Sequence) or isinstance(value, str | bytes):
        return ()
    return tuple(str(item) for item in value if isinstance(item, str))
