"""Readings and host-side channel configuration.

A reading must come from an advertised channel, match the channel's typed or
untyped advertisement, and fall inside ``[now - ttl_ms, now + max_skew_ms]``.
Typed channels are normalized through ``contracts.channels`` with any
host-applied configuration. Frames keep the newest sample per channel; the
shared history keeps the last 512 frames.
"""
from __future__ import annotations

from typing import Any

from codontrace.contracts.channels import normalize_sample, validate_descriptor
from codontrace.contracts.wire_validation import exact_keys, identifier

__all__ = ['HISTORY_LIMIT', 'accept_reading', 'configure_channel']

HISTORY_LIMIT = 512


def accept_reading(state: dict[str, Any], node_id: str, node: dict[str, Any], *, boot_id: str, seq: int,
                   payload: dict[str, Any], typed: bool, now_ms: int, ttl_ms: int, max_skew_ms: int) -> None:
    p = payload
    if state['status'] != 'running':
        raise ValueError('swarm is paused or stopped')
    if p['channel'] not in node['channels']:
        raise ValueError('undeclared channel')
    channel_config = node['channels'][p['channel']]
    if ('descriptor' in channel_config) != typed:
        raise ValueError('reading schema differs from advertised channel')
    if p['sample_ms'] > now_ms + max_skew_ms or now_ms - p['sample_ms'] > ttl_ms:
        raise ValueError('stale sample or clock skew')
    key = node_id + '/' + p['channel']
    if typed:
        channel_config = {**channel_config,
                          'descriptor': state.get('channel_configs', {}).get(key, channel_config['descriptor'])}
        p = normalize_sample(p, channel_config)
        if 'reference' in p and p.get('reference_unit') != channel_config['unit']:
            raise ValueError('reference must explicitly use normalized channel unit')
        if 'reference' in p and channel_config['descriptor']['value_type'] != 'scalar':
            raise ValueError('scalar reference not supported for non-scalar channel')
    previous = state['frames'].get(key)
    if previous and p['sample_ms'] < previous['sample_ms']:
        raise ValueError('sample clock reordered')
    if previous and (previous['processing_version'] != p['processing_version'] or
                     previous.get('descriptor_digest') != p.get('descriptor_digest')):
        state['trust'].pop(key, None)
    state['frames'][key] = {**p, **node['channels'][p['channel']],
                            'node_id': node_id, 'boot_id': boot_id, 'received_ms': now_ms, 'seq': seq}
    state['history'].append(state['frames'][key])
    state['history'] = state['history'][-HISTORY_LIMIT:]


def configure_channel(state: dict[str, Any], key: Any, changes: Any) -> dict[str, Any]:
    """Host-side normalization/range override for a typed channel (no device command)."""
    nodes = state['nodes']
    if not isinstance(key, str) or len(key.split('/')) != 2:
        raise ValueError('node/channel key required')
    node_id, channel_id = key.split('/')
    identifier(node_id)
    identifier(channel_id)
    node = nodes.get(node_id)
    if node is None or channel_id not in node['channels']:
        raise ValueError('unknown channel')
    channel = node['channels'][channel_id]
    if 'descriptor' not in channel:
        raise ValueError('typed v2 channel required')
    changes = exact_keys(changes, set(), {'normalization', 'range'})
    d = dict(state.get('channel_configs', {}).get(key, channel['descriptor']))
    for field, value in changes.items():
        if value is None:
            d.pop(field, None)
        else:
            d[field] = value
    d = validate_descriptor(d)
    if d.get('normalization', {}).get('output_unit', d['source_unit']) != channel['unit']:
        raise ValueError('configured normalization must preserve declared output unit')
    state.setdefault('channel_configs', {})[key] = d
    state['frames'].pop(key, None)
    state['trust'].pop(key, None)
    return {'key': key, 'descriptor': d, 'host_configuration_applied': True, 'device_command_sent': False}
