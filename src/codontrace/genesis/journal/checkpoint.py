"""Hashed state checkpoints bound to the last record of a closed journal segment.

A checkpoint is a rebuildable cache, never authoritative history. Its payload
is ``{schema, <record header>, segment_index, chain, state, state_digest}``
plus a ``digest`` of that payload, serialized with the frozen wire canonical
JSON so existing checkpoints stay byte-identical.
"""
from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from typing import Any

from codontrace.contracts.wire_validation import wire_canonical

__all__ = ['CHECKPOINTS_KEPT', 'MAX_CHECKPOINT_BYTES', 'checkpoint_body', 'state_digest', 'verify_checkpoint_text']

CHECKPOINTS_KEPT = 2
MAX_CHECKPOINT_BYTES = 256 * 1024 * 1024


def state_digest(state: Any) -> str:
    return hashlib.sha256(wire_canonical(state).encode()).hexdigest()


def checkpoint_body(schema: str, header: Mapping[str, Any], index: int, chain: str, state: Any) -> str:
    """Canonical checkpoint file text (no trailing newline)."""
    payload = {'schema': schema, **header, 'segment_index': index, 'chain': chain,
               'state': state, 'state_digest': state_digest(state)}
    return wire_canonical({**payload, 'digest': hashlib.sha256(wire_canonical(payload).encode()).hexdigest()})


def verify_checkpoint_text(text: str, *, schema: str, header: Mapping[str, Any], index: int) -> dict[str, Any]:
    """Self-check one checkpoint's digest, identity and state digest; return the payload.

    Raises ``ValueError``. Binding to the closed segment's final record is the
    journal's job (it needs the segment file).
    """
    payload = json.loads(text)
    if not isinstance(payload, dict):
        raise ValueError('checkpoint must be an object')
    digest = payload.pop('digest', None)
    if hashlib.sha256(wire_canonical(payload).encode()).hexdigest() != digest:
        raise ValueError('checkpoint digest mismatch')
    if (payload.get('schema') != schema or any(payload.get(key) != value for key, value in header.items())
            or payload.get('segment_index') != index):
        raise ValueError('checkpoint identity or configuration mismatch')
    if state_digest(payload['state']) != payload.get('state_digest'):
        raise ValueError('checkpoint state digest mismatch')
    return payload
