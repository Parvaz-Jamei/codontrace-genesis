"""Shared run roots and module run references.

``resolve_run_root(kind)`` (from ``codontrace.contracts.run_roots``, standard
library only) is the one place that decides where runs of a kind live; the
console (``simulation``) and the swarm service (``swarm``) call it, with their
environment overrides unchanged.

``module_run_reference`` is the record a module run (swarm, visualization,
board) writes or returns next to its own files: the engine ``RunManifest`` and
``ReplayBundle`` digests when an engine run is involved, the manifest's
``validate_scientific_manifest`` result (missing hashes are reported, never
filled with placeholders), and a journal head anchor when there is a journal.
Legacy module files are not changed.
"""
from __future__ import annotations

import hashlib
import json
import os
from collections.abc import Mapping
from pathlib import Path
from typing import TYPE_CHECKING, Any

from codontrace.contracts.run_roots import resolve_run_root

if TYPE_CHECKING:
    from codontrace.genesis.artifacts import ReplayBundle, RunManifest

__all__ = ['RUN_KINDS', 'RUN_REFERENCE_SCHEMA', 'module_run_reference', 'resolve_run_root', 'write_run_reference']

RUN_KINDS = ('simulation', 'swarm', 'visualization', 'board')
RUN_REFERENCE_SCHEMA = 'genesis_module_run_ref_v1'


def _sha256_json(payload: Any) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(',', ':'),
                                     allow_nan=False).encode()).hexdigest()


def module_run_reference(kind: str, run_id: str, *, manifest: RunManifest | None = None,
                         replay_bundle: ReplayBundle | None = None,
                         journal_anchor: Mapping[str, Any] | None = None,
                         legacy_files: Mapping[str, str] | None = None,
                         extra: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Reference record (plain JSON). ``legacy_files`` maps names to SHA-256 of module files."""
    if kind not in RUN_KINDS:
        raise ValueError('unknown run kind')
    if not isinstance(run_id, str) or not run_id:
        raise ValueError('run id required')
    ref: dict[str, Any] = {'schema': RUN_REFERENCE_SCHEMA, 'kind': kind, 'run_id': run_id,
                           'run_manifest': None, 'run_manifest_sha256': None, 'replay_bundle_sha256': None,
                           'scientific_manifest_validation': None,
                           'journal_anchor': None if journal_anchor is None else dict(journal_anchor),
                           'legacy_files': dict(sorted((legacy_files or {}).items())),
                           'physical_validation': False}
    if manifest is not None:
        from codontrace.genesis.artifacts import validate_scientific_manifest
        payload = manifest.to_dict()
        ref['run_manifest'] = payload
        ref['run_manifest_sha256'] = _sha256_json(payload)
        ref['scientific_manifest_validation'] = validate_scientific_manifest(manifest).to_dict()
    if replay_bundle is not None:
        ref['replay_bundle_sha256'] = _sha256_json(replay_bundle.to_dict())
    if extra:
        ref['extra'] = dict(extra)
    return ref


def write_run_reference(path: Path, reference: Mapping[str, Any]) -> Path:
    """Atomic write (temp file + rename) of a reference record."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + f'.{os.getpid()}.tmp')
    temp.write_text(json.dumps(dict(reference), indent=2, sort_keys=True, allow_nan=False) + '\n', encoding='utf-8')
    os.replace(temp, path)
    return path
