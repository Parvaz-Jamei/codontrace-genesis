"""Console-facing service. Authentication is owned by the HTTP/MQTT transport."""
from __future__ import annotations

import os
import threading
import time
from pathlib import Path
from typing import Any

from codontrace.swarm.policies import Pipeline, PolicyArchive, transfer_decision
from codontrace.swarm.protocol import identifier, object_keys
from codontrace.swarm.runtime import SwarmCoordinator

_LOCK = threading.RLock()
_SWARMS: dict[str, SwarmCoordinator] = {}

# Pure computations on caller-supplied data: no swarm state, no storage.
STATELESS_ACTIONS = frozenset({'fdc_decode', 'pipeline_fit', 'information_level', 'processing_contrast',
                               'twin_fit', 'coevolve', 'uncertainty_interval', 'freshness_schedule',
                               'capsule_shadow', 'capsule_validate'})
# Reads of recorded state: an unknown swarm id is answered from empty state
# without creating its folder, journal or lock file.
READ_ONLY_ACTIONS = frozenset({'snapshot', 'fusion', 'diagnosis', 'freshness_plan'})
WRITE_ACTIONS = frozenset({'journal_recover', 'configure_channel', 'ingest', 'command', 'status', 'plan', 'calibrate'})


def _root() -> Path:
    root = Path(os.environ.get('CODONTRACE_SWARM_DIR', str(Path.home() / '.local' / 'share' / 'codontrace' / 'swarm_runs'))).expanduser()
    if not root.is_absolute():
        raise ValueError('CODONTRACE_SWARM_DIR must be absolute; storage must not depend on CWD')
    return root.resolve()


def coordinator(swarm_id: str, *, create: bool = True) -> SwarmCoordinator | None:
    """Cached coordinator; with ``create=False`` an unrecorded swarm returns None."""
    identifier(swarm_id)
    with _LOCK:
        if swarm_id not in _SWARMS:
            folder = _root() / swarm_id
            if not create and not folder.is_dir():
                return None
            if len(_SWARMS) >= 32:
                raise ValueError('swarm session capacity reached')
            _SWARMS[swarm_id] = SwarmCoordinator(swarm_id, journal=folder / 'events.jsonl')
        return _SWARMS[swarm_id]


def invoke(action: str, args: Any, *, now_ms: int | None = None) -> dict[str, Any]:
    args = dict(args) if isinstance(args, dict) else None
    if args is None:
        raise ValueError('swarm args must be an object')
    now = int(time.time() * 1000) if now_ms is None else now_ms
    sid = identifier(args.get('swarm_id'))
    if action not in STATELESS_ACTIONS | READ_ONLY_ACTIONS | WRITE_ACTIONS:
        raise ValueError('unknown swarm action')
    recorded = True
    if action in STATELESS_ACTIONS:
        swarm = None
    elif action in READ_ONLY_ACTIONS:
        swarm = coordinator(sid, create=False)
        if swarm is None:
            recorded = False
            swarm = SwarmCoordinator(sid)  # empty, in memory, never cached
    else:
        swarm = coordinator(sid)
    if action == 'journal_recover':
        object_keys(args, {'swarm_id'}, {'full_replay'})
        result = swarm.recover(full_replay=args.get('full_replay', False))
    elif action == 'snapshot':
        object_keys(args, {'swarm_id'})
        result = swarm.snapshot(now_ms=now)
    elif action == 'configure_channel':
        object_keys(args, {'swarm_id', 'key', 'changes'})
        result = swarm._transaction('configure_channel', {'key': args['key'], 'changes': args['changes']}, now)
    elif action == 'fdc_decode':
        from codontrace.swarm.sensors import fdc_sample
        object_keys(args, {'swarm_id', 'reading', 'variant', 'config_id'})
        channel, payload = fdc_sample(args['reading'], variant=args['variant'], config_id=args['config_id'])
        result = {'channel': channel, 'payload': payload, 'device_command_sent': False, 'scope': 'adapter_preview_not_ingestion'}
    elif action == 'ingest':
        object_keys(args, {'swarm_id', 'message'})
        result = swarm.ingest(args['message'], now_ms=now)
    elif action == 'command':
        object_keys(args, {'swarm_id', 'node_id', 'operation', 'params'}, {'timeout_ms'})
        result = swarm.command(args['node_id'], args['operation'], args['params'], now_ms=now,
                               timeout_ms=args.get('timeout_ms', 5000))
    elif action == 'status':
        object_keys(args, {'swarm_id', 'status'})
        result = swarm.set_status(args['status'], now_ms=now)
    elif action in ('fusion', 'diagnosis', 'plan'):
        optional = {'mode'} if action == 'fusion' else {'reference', 'tolerance'} if action == 'diagnosis' else {'budget'}
        object_keys(args, {'swarm_id', 'quantity', 'unit'}, optional)
        if action == 'fusion':
            result = swarm.fuse(args['quantity'], args['unit'], now_ms=now, mode=args.get('mode', 'median'))
        elif action == 'diagnosis':
            result = swarm.diagnose(args['quantity'], args['unit'], now_ms=now,
                                    reference=args.get('reference'), tolerance=args.get('tolerance', 2))
        else:
            result = swarm.plan(args['quantity'], args['unit'], now_ms=now, budget=args.get('budget', 2))
    elif action == 'calibrate':
        object_keys(args, {'swarm_id', 'key', 'reference', 'reference_id'}, {'scale'})
        result = swarm.calibrate(args['key'], args['reference'], args['reference_id'], now_ms=now,
                                 scale=args.get('scale', 1))
    elif action == 'pipeline_fit':
        object_keys(args, {'swarm_id', 'values', 'references', 'seed'}, {'rounds'})
        archive = PolicyArchive(args['seed'])
        best = archive.fit(args['values'], args['references'], rounds=args.get('rounds', 8))
        result = {'best': archive.entries[best.digest], 'archive': list(archive.entries.values()),
                  'rng': archive.rng.snapshot(), 'scope': 'training_data_only'}
    elif action == 'information_level':
        from codontrace.swarm.research import information_level
        object_keys(args, {'swarm_id', 'options', 'byte_budget', 'maximum_mse'})
        result = information_level(args['options'], byte_budget=args['byte_budget'], maximum_mse=args['maximum_mse'])
    elif action == 'processing_contrast':
        from codontrace.swarm.research import processing_contrast
        object_keys(args, {'swarm_id', 'frame', 'reference'}, {'tolerance'})
        result = processing_contrast(args['frame'], reference=args['reference'], tolerance=args.get('tolerance', 2))
    elif action == 'twin_fit':
        from dataclasses import asdict

        from codontrace.swarm.research import SensorTwin
        object_keys(args, {'swarm_id', 'references', 'observations'})
        result = asdict(SensorTwin.fit(args['references'], args['observations']))
    elif action == 'coevolve':
        from codontrace.swarm.coevolution import coevolve
        object_keys(args, {'swarm_id', 'references', 'seed'}, {'rounds', 'disturbance_budget'})
        result = coevolve(args['references'], seed=args['seed'], rounds=args.get('rounds', 8),
                          disturbance_budget=args.get('disturbance_budget', 1))
    elif action == 'uncertainty_interval':
        from codontrace.swarm.decision_support import residual_interval
        object_keys(args, {'swarm_id','predictions','references','estimate','training_id','calibration_id','model_id'}, {'alpha'})
        result = residual_interval(args['predictions'], args['references'], estimate=args['estimate'],
            training_id=args['training_id'], calibration_id=args['calibration_id'], model_id=args['model_id'], alpha=args.get('alpha', .1))
    elif action == 'freshness_schedule':
        from codontrace.swarm.decision_support import schedule_measurements
        object_keys(args, {'swarm_id','candidates','byte_budget'}, {'request_budget'})
        result = schedule_measurements(args['candidates'], now_ms=now, byte_budget=args['byte_budget'], request_budget=args.get('request_budget', 8))
    elif action == 'freshness_plan':
        object_keys(args, {'swarm_id','models','quantity','unit','byte_budget'}, {'request_budget'})
        result = swarm.freshness_plan(args['models'],args['quantity'],args['unit'],now_ms=now,
                                     byte_budget=args['byte_budget'],request_budget=args.get('request_budget',8))
    elif action == 'capsule_shadow':
        from codontrace.swarm.decision_support import capsule_shadow
        object_keys(args, {'swarm_id','candidate','baseline','values','references','training_id','evaluation_id'},
                    {'phase','minimum_gain','maximum_regression'})
        result = capsule_shadow(Pipeline(**args['candidate']), Pipeline(**args['baseline']), args['values'], args['references'],
            training_id=args['training_id'], evaluation_id=args['evaluation_id'], phase=args.get('phase','qualification'),
            minimum_gain=args.get('minimum_gain',0), maximum_regression=args.get('maximum_regression',0))
    elif action == 'capsule_validate':
        object_keys(args, {'swarm_id', 'candidate', 'baseline', 'values', 'references'}, {'minimum_gain'})
        result = transfer_decision(Pipeline(**args['candidate']), Pipeline(**args['baseline']),
                                   args['values'], args['references'], minimum_gain=args.get('minimum_gain', 0))
    else:
        raise ValueError('unknown swarm action')
    return {'ok': True, 'swarm_id': sid, 'action': action, 'result': result, 'swarm_recorded': recorded}
