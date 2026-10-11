"""Which channels to sample next.

``plan_oldest_first`` is capability-aware oldest-first allocation (a channel
never sampled counts as older than the TTL); it is not claimed to maximize
information gain. ``measurement_candidates`` filters host channel models to
fresh, online, sample-capable, unit-matched scalar channels with no pending
request, for a separate scheduler.
"""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from codontrace.contracts.channels import scalar_frame
from codontrace.contracts.wire_validation import exact_keys, identifier
from codontrace.genesis.swarm.commands import pending_for

__all__ = ['CHANNEL_MODEL_FIELDS', 'measurement_candidates', 'plan_oldest_first']

CHANNEL_MODEL_FIELDS = frozenset({'group', 'noise_variance', 'process_variance_per_ms', 'latency_ms',
                                  'success_probability', 'payload_bytes', 'evidence_id'})


def plan_oldest_first(view: Mapping[str, Any], quantity: str, unit: str, *, now_ms: int, ttl_ms: int,
                      budget: int) -> list[tuple[str, str]]:
    candidates = []
    for node_id, node in view['nodes'].items():
        if not node['online'] or 'sample' not in node['operations']:
            continue
        for channel, config in node['channels'].items():
            if (config.get('quantity') != quantity or config.get('unit') != unit or
                    config.get('descriptor', {}).get('value_type', 'scalar') != 'scalar'):
                continue
            if pending_for(view['commands'], node_id, channel):
                continue
            frame = view['frames'].get(node_id + '/' + channel)
            age = ttl_ms+1 if frame is None else now_ms - frame['sample_ms']
            candidates.append((-age, node_id, channel))
    return [(node_id, channel) for _, node_id, channel in sorted(candidates)[:budget]]


def measurement_candidates(view: Mapping[str, Any], models: Any, quantity: str, unit: str, *,
                           now_ms: int) -> tuple[list[dict[str, Any]], list[str]]:
    """Return ``(candidates, excluded_keys)``; raises on malformed models."""
    if not isinstance(models, dict) or len(models) > 256:
        raise ValueError('bounded channel model dictionary required')
    candidates: list[dict[str, Any]] = []
    excluded: list[str] = []
    for key, model in models.items():
        if not isinstance(key, str) or len(key.split('/')) != 2:
            raise ValueError('model key must be node/channel')
        node_id, channel = key.split('/')
        identifier(node_id)
        identifier(channel)
        node = view['nodes'].get(node_id)
        if node is None or channel not in node['channels']:
            raise ValueError('model channel has not been advertised')
        exact_keys(model, set(CHANNEL_MODEL_FIELDS))
        frame = view['frames'].get(key)
        eligible = (node['online'] and 'sample' in node['operations'] and frame is not None
                    and frame['sample_ms'] <= now_ms
                    and node['channels'][channel].get('quantity') == quantity
                    and node['channels'][channel].get('unit') == unit
                    and scalar_frame(frame)
                    and not pending_for(view['commands'], node_id, channel))
        if eligible:
            candidates.append({**model, 'key': key, 'sample_ms': frame['sample_ms']})
        else:
            excluded.append(key)
    return candidates, excluded
