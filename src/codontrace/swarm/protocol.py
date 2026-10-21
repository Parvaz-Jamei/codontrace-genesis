"""Board-independent Wi-Fi sensor protocol. Never executes device code."""
from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any

from codontrace.contracts.wire_validation import (
    bounded_int,
    bounded_text,
    exact_keys,
    finite_number,
    json_depth_within,
    wire_canonical,
)
from codontrace.contracts.wire_validation import (
    identifier as identifier,  # re-exported for swarm callers
)

VERSION = 'genesis_swarm_v1'
VERSION2 = 'genesis_swarm_v2'
MAX_BYTES = 65536
# A v2 reading value is at most one array deep: the flat vector/waveform lists of
# contracts.channels.typed_value (CodonTraceSwarm MaxValues = 256).
MAX_VALUE_ITEMS = 256
MAX_CATEGORY_CHARS = 128
OPERATIONS = frozenset({'sample', 'raw', 'features', 'result', 'set_rate', 'pipeline', 'capsule'})


# Generic validators live in codontrace.contracts.wire_validation; these names
# are kept as aliases (same objects) for existing callers and journal formats.
number = finite_number
integer = bounded_int
text = bounded_text
object_keys = exact_keys
canonical = wire_canonical


def reading_value(value: Any) -> Any:
    """Check a valid v2 reading value against the union of the descriptor value types.

    scalar: finite number; vector/waveform: flat list of 1..256 finite numbers;
    boolean: bool; category: text of at most 128 characters. Nesting is limited
    to 1 array level; the per-channel shape is checked later against the descriptor.
    """
    if type(value) is bool:
        return value
    if isinstance(value, str):
        return text(value, MAX_CATEGORY_CHARS)
    if isinstance(value, list):
        if not 1 <= len(value) <= MAX_VALUE_ITEMS:
            raise ValueError('reading value array must contain 1..256 numbers')
        return [number(v) for v in value]
    return number(value)


def decode(raw: bytes | str | Mapping[str, Any]) -> dict[str, Any]:
    def unique(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        out: dict[str, Any] = {}
        for key, value in pairs:
            if key in out:
                raise ValueError('duplicate JSON key')
            out[key] = value
        return out
    def non_finite(token: str) -> Any:
        raise ValueError('finite number required')  # NaN/Infinity are not JSON (RFC 8259 s6)
    if isinstance(raw, (str, bytes)):
        if len(raw.encode() if isinstance(raw, str) else raw) > MAX_BYTES:
            raise ValueError('payload too large')
        if not json_depth_within(raw):
            raise ValueError('JSON nesting too deep')
        raw = json.loads(raw, object_pairs_hook=unique, parse_constant=non_finite)
    try:
        encoded = canonical(raw).encode()
    except RecursionError:
        raise ValueError('JSON nesting too deep') from None
    if len(encoded) > MAX_BYTES:
        raise ValueError('payload too large')
    m = object_keys(raw, {'schema', 'swarm_id', 'node_id', 'boot_id', 'seq', 'kind', 'payload'})
    if m['schema'] not in (VERSION, VERSION2):
        raise ValueError('unsupported schema')
    for key in ('swarm_id', 'node_id', 'boot_id'):
        identifier(m[key])
    integer(m['seq'])
    p = m['payload']
    if m['kind'] == 'hello':
        p = object_keys(p, {'wifi', 'channels', 'operations'})
        if p['wifi'] is not True:
            raise ValueError('Wi-Fi node required')
        if not isinstance(p['channels'], dict) or not 1 <= len(p['channels']) <= 32:
            raise ValueError('1..32 channels required')
        for name, channel in p['channels'].items():
            identifier(name)
            c = object_keys(channel, {'quantity', 'unit', 'descriptor'} if m['schema'] == VERSION2 else {'quantity', 'unit'})
            text(c['quantity']); text(c['unit'])
            if m['schema'] == VERSION2:
                from codontrace.swarm.sensors import descriptor
                d = descriptor(c['descriptor'])
                if (d.get('normalization', {}).get('output_unit', d['source_unit'])) != c['unit']:
                    raise ValueError('channel requires explicit unit normalization')
        if not isinstance(p['operations'], list) or len(p['operations']) > len(OPERATIONS):
            raise ValueError('invalid operations')
        if any(op not in OPERATIONS for op in p['operations']) or len(set(p['operations'])) != len(p['operations']):
            raise ValueError('unsupported or duplicate operation')
    elif m['kind'] == 'reading':
        extra = {'valid', 'status', 'config_id'} if m['schema'] == VERSION2 else set()
        p = object_keys(p, {'channel', 'sample_ms', 'value', 'processing_version'} | extra,
                        {'raw', 'features', 'quality', 'reference', 'energy_j', 'reference_id'} | ({'metadata', 'uncertainty', 'source_unit', 'reference_unit'} if extra else set()))
        identifier(p['channel']); integer(p['sample_ms']); text(p['processing_version'])
        if extra:
            identifier(p['config_id']);text(p['status'])
            if type(p['valid']) is not bool or (not p['valid'] and p['value'] is not None):
                raise ValueError('invalid typed sample validity')
            if p['valid'] and p['status'] != 'ok': raise ValueError('valid sample requires ok status')
            if p['valid']:
                reading_value(p['value'])
            if 'metadata' in p:
                metadata = p['metadata']
                if not isinstance(metadata, dict) or len(metadata) > 32: raise ValueError('bounded metadata object required')
                for key, value in metadata.items():
                    identifier(key)
                    if isinstance(value, str): text(value, 256)
                    elif type(value) is bool or value is None: pass
                    else: number(value)
        else:
            number(p['value'])
        if 'quality' in p:
            number(p['quality'], low=0, high=1)
        if 'reference' in p:
            number(p['reference']); text(p.get('reference_id'))
        elif 'reference_id' in p:
            raise ValueError('reference_id without reference')
        if 'energy_j' in p:
            number(p['energy_j'], low=0, high=1e6)
        if 'raw' in p:
            if not isinstance(p['raw'], list) or not 1 <= len(p['raw']) <= 256:
                raise ValueError('raw window must contain 1..256 numbers')
            for v in p['raw']:
                number(v)
        if 'features' in p:
            if not isinstance(p['features'], dict) or len(p['features']) > 32:
                raise ValueError('invalid features')
            for k, v in p['features'].items():
                identifier(k); number(v)
    elif m['kind'] == 'heartbeat':
        object_keys(p, set())
    elif m['kind'] == 'reply':
        p = object_keys(p, {'command_id', 'ok'}, {'message'})
        identifier(p['command_id'])
        if type(p['ok']) is not bool:
            raise ValueError('reply ok must be boolean')
        if 'message' in p:
            text(p['message'], 256)
    else:
        raise ValueError('unsupported message kind')
    copy: dict[str, Any] = json.loads(canonical(m))  # defensive copy, including nested arrays
    return copy
