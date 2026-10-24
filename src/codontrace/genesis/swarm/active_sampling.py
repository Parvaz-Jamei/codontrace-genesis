"""Which channels to sample next.

``plan_oldest_first`` is capability-aware oldest-first allocation (a channel
never sampled counts as older than the TTL); it is not claimed to maximize
information gain. ``measurement_candidates`` filters host channel models to
fresh, online, sample-capable, unit-matched scalar channels with no pending
request, for a separate scheduler. ``schedule_measurements`` is that
scheduler: greedy expected-error reduction per byte with a per-group
redundancy discount, the cost-benefit greedy rule of budgeted sensor
selection. No approximation guarantee is claimed here:
the gain proxy is not shown to be submodular for arbitrary inputs.
"""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from codontrace.contracts.channels import scalar_frame
from codontrace.contracts.wire_validation import bounded_int, exact_keys, finite_number, identifier
from codontrace.genesis.swarm.commands import pending_for

__all__ = ['CHANNEL_MODEL_FIELDS', 'measurement_candidates', 'plan_oldest_first', 'schedule_measurements']

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


def schedule_measurements(candidates: list[dict[str, Any]], *, now_ms: int,
                          byte_budget: int, request_budget: int = 8) -> dict[str, Any]:
    """Greedy estimated-error reduction per byte with group redundancy discount.

    Scalar random-walk proxy: noise + q*age; successful fresh reading arrives
    with age=latency. Group utility is max, not a sum of correlated sensors.
    A user-declared group is not an estimated covariance model. No optimality claim.
    """
    bounded_int(now_ms); bounded_int(byte_budget, high=16*1024*1024); bounded_int(request_budget, high=32)
    if not isinstance(candidates, list) or len(candidates)>256:
        raise ValueError('bounded candidate list required')
    rows: list[dict[str, Any]]=[];seen: set[str]=set()
    for raw in candidates:
        row=exact_keys(raw, {'key','group','sample_ms','noise_variance','process_variance_per_ms',
                             'latency_ms','success_probability','payload_bytes','evidence_id'})
        key=row['key']
        if not isinstance(key,str) or len(key.split('/')) not in (1,2):
            raise ValueError('candidate key must identify a node/channel')
        for part in key.split('/'): identifier(part)
        identifier(row['group']);identifier(row['evidence_id'])
        if key in seen: raise ValueError('duplicate candidate identity')
        seen.add(key);sample=bounded_int(row['sample_ms'])
        if sample>now_ms: raise ValueError('scheduling requires synchronized nonfuture timestamps')
        noise=finite_number(row['noise_variance'],low=0,high=1e6)
        q=finite_number(row['process_variance_per_ms'],low=0,high=1e6)
        latency=bounded_int(row['latency_ms'],high=3600000);cost=bounded_int(row['payload_bytes'],high=65536)
        if not cost: raise ValueError('positive estimated payload cost required')
        probability=finite_number(row['success_probability'],low=0,high=1)
        age=now_ms-sample
        if age>3600000: raise ValueError('candidate age exceeds modeled one-hour horizon')
        gain=probability*max(0.,q*(age-latency))
        rows.append({**row,'age_ms':age,'current_variance_proxy':noise+q*age,
                     'refreshed_variance_proxy':noise+q*latency,'expected_gain_proxy':gain})
    selected: list[dict[str, Any]]=[];remaining=list(rows);group_best: dict[str, float]={};spent=0
    while len(selected)<request_budget:
        scored=[]
        for row in remaining:
            gain=max(0.,row['expected_gain_proxy']-group_best.get(row['group'],0.))
            if row['payload_bytes']<=byte_budget-spent and gain>0:
                scored.append((gain/row['payload_bytes'],gain,row))
        if not scored: break
        _,gain,row=min(scored,key=lambda item:(-item[0],-item[1],item[2]['key']))
        selected.append({**row,'marginal_gain_proxy':gain})
        spent+=row['payload_bytes'];group_best[row['group']]=row['expected_gain_proxy'];remaining.remove(row)
    return {'schema':'genesis_freshness_schedule_v1','selected':selected,'candidates':rows,
            'estimated_payload_bytes':spent,'byte_budget':byte_budget,
            'expected_group_gain_proxy':sum(group_best.values()),'command_sent':False,
            'scope':'advisory_greedy_random_walk_proxy_with_declared_redundancy_groups',
            'limitations':'costs/probabilities/q supplied by caller; no actual wire-byte, energy, covariance or optimality guarantee'}
