"""Console-facing service. Authentication is owned by the HTTP/MQTT transport."""
from __future__ import annotations

import os
import threading
import time
from collections import OrderedDict
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Literal, overload

from codontrace.swarm.policies import Pipeline, PolicyArchive, transfer_decision
from codontrace.swarm.protocol import identifier, object_keys
from codontrace.swarm.runtime import SwarmCoordinator

_LOCK = threading.RLock()
# Least-recently-used first. Only fully restored coordinators are cached; they are
# reopened from their journal on demand after eviction.
_SWARMS: OrderedDict[str, SwarmCoordinator] = OrderedDict()
_LEASES: dict[str, int] = {}   # in-flight service requests
_PINS: dict[str, int] = {}     # long-lived holders (MQTT bridge, engine links)
_OPENING: dict[str, list[Any]] = {}  # per-swarm [lock, users] so opening happens outside _LOCK
MAX_CACHED_SWARMS = 32


class SwarmCapacityError(ValueError):
    """Every cached coordinator is in use; nothing can be evicted."""


class SwarmRecoveryRequired(ValueError):
    """Recorded history exists but is not loaded; only journal_recover is served."""

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


def _evict_idle() -> None:
    """Drop least-recently-used coordinators nobody is using (caller holds _LOCK).

    Skipped: swarms pinned by a long-lived holder, leased by an in-flight request,
    whose lock is held, or that need journal recovery (their flag would be lost).
    """
    for sid in list(_SWARMS):
        if len(_SWARMS) < MAX_CACHED_SWARMS:
            return
        swarm = _SWARMS[sid]
        if _PINS.get(sid) or _LEASES.get(sid) or swarm._write_failed or not swarm._lock.acquire(blocking=False):
            continue
        try:
            del _SWARMS[sid]
        finally:
            swarm._lock.release()
    if len(_SWARMS) >= MAX_CACHED_SWARMS:
        raise SwarmCapacityError('swarm session capacity reached; all cached swarms are busy')


@contextmanager
def _opening(swarm_id: str) -> Iterator[None]:
    """Per-swarm open lock: one opener per swarm, other swarms are never blocked."""
    with _LOCK:
        entry = _OPENING.setdefault(swarm_id, [threading.Lock(), 0])
        entry[1] += 1
    try:
        with entry[0]:
            yield
    finally:
        with _LOCK:
            entry[1] -= 1
            if not entry[1]:
                del _OPENING[swarm_id]


def _insert(swarm_id: str, swarm: SwarmCoordinator, pin: bool) -> SwarmCoordinator:
    with _LOCK:
        _evict_idle()
        _SWARMS[swarm_id] = swarm
        if pin:
            _PINS[swarm_id] = _PINS.get(swarm_id, 0) + 1
        return swarm


@overload
def _cached(swarm_id: str, *, create: Literal[True], pin: bool = False) -> SwarmCoordinator: ...
@overload
def _cached(swarm_id: str, *, create: bool, pin: bool = False) -> SwarmCoordinator | None: ...
def _cached(swarm_id: str, *, create: bool, pin: bool = False) -> SwarmCoordinator | None:
    identifier(swarm_id)
    with _LOCK:
        if swarm_id in _SWARMS:
            _SWARMS.move_to_end(swarm_id)
            if pin:
                _PINS[swarm_id] = _PINS.get(swarm_id, 0) + 1
            return _SWARMS[swarm_id]
    folder = _root() / swarm_id
    if not create and not folder.is_dir():
        return None
    with _opening(swarm_id):
        with _LOCK:
            if swarm_id in _SWARMS:  # opened by another thread meanwhile
                _SWARMS.move_to_end(swarm_id)
                if pin:
                    _PINS[swarm_id] = _PINS.get(swarm_id, 0) + 1
                return _SWARMS[swarm_id]
            if len(_SWARMS) >= MAX_CACHED_SWARMS:
                _evict_idle()  # fail fast before a possibly long open
        try:
            # Lock wait and replay happen outside _LOCK.
            swarm = SwarmCoordinator(swarm_id, journal=folder / 'events.jsonl')
        except ValueError as error:
            raise SwarmRecoveryRequired(f'recovery_required: {error}; run journal_recover') from error
        return _insert(swarm_id, swarm, pin)


@overload
def coordinator(swarm_id: str, *, create: Literal[True] = True) -> SwarmCoordinator: ...
@overload
def coordinator(swarm_id: str, *, create: bool) -> SwarmCoordinator | None: ...
def coordinator(swarm_id: str, *, create: bool = True) -> SwarmCoordinator | None:
    """Long-lived coordinator handle shared with the service cache.

    The returned coordinator is pinned (never evicted) so a holder such as the
    MQTT bridge and HTTP requests always use the same instance. Call
    ``release(swarm_id)`` when done. With ``create=False`` an unrecorded swarm
    returns None and nothing is pinned.
    """
    return _cached(swarm_id, create=create, pin=True)


def release(swarm_id: str) -> None:
    """Drop one pin taken by ``coordinator()``; the swarm becomes evictable when idle."""
    with _LOCK:
        if not _PINS.get(swarm_id):
            raise ValueError('swarm is not pinned')
        _PINS[swarm_id] -= 1
        if not _PINS[swarm_id]:
            del _PINS[swarm_id]


@contextmanager
def _lease(swarm_id: str) -> Iterator[None]:
    with _LOCK:
        _LEASES[swarm_id] = _LEASES.get(swarm_id, 0) + 1
    try:
        yield
    finally:
        with _LOCK:
            _LEASES[swarm_id] -= 1
            if not _LEASES[swarm_id]:
                del _LEASES[swarm_id]


def _recover(swarm_id: str, full_replay: Any) -> dict[str, Any]:
    """journal_recover, reachable even when normal opening fails.

    An instance opened without restore is cached only after recovery succeeded,
    so reads never see its empty placeholder state.
    """
    try:
        swarm = _cached(swarm_id, create=True)
    except SwarmRecoveryRequired:
        swarm = None
    if swarm is not None:
        try:
            return swarm.recover(full_replay=full_replay)
        except BaseException:
            # Unpinned: drop it so reads reopen from disk (and refuse if that fails).
            with _LOCK:
                if not _PINS.get(swarm_id) and _SWARMS.get(swarm_id) is swarm:
                    del _SWARMS[swarm_id]
            raise
    with _opening(swarm_id):
        with _LOCK:
            cached = _SWARMS.get(swarm_id)
        if cached is not None:
            return cached.recover(full_replay=full_replay)
        fresh = SwarmCoordinator(swarm_id, journal=_root() / swarm_id / 'events.jsonl', restore=False)
        result = fresh.recover(full_replay=full_replay)  # raises: nothing is cached
        _insert(swarm_id, fresh, False)
        return result


def _readable(swarm: SwarmCoordinator) -> SwarmCoordinator:
    if swarm._write_failed:
        raise SwarmRecoveryRequired('recovery_required: journal failure; run journal_recover')
    return swarm


def invoke(action: str, args: Any, *, now_ms: int | None = None) -> dict[str, Any]:
    args = dict(args) if isinstance(args, dict) else None
    if args is None:
        raise ValueError('swarm args must be an object')
    sid = identifier(args.get('swarm_id'))
    with _lease(sid):
        return _invoke(action, args, sid, now_ms)


def _live(swarm: SwarmCoordinator | None) -> SwarmCoordinator:
    """Every non-stateless action has opened a coordinator; None here is a bug."""
    if swarm is None:
        raise RuntimeError('swarm action reached without a coordinator')
    return swarm


def _invoke(action: str, args: dict[str, Any], sid: str, now_ms: int | None) -> dict[str, Any]:
    now = int(time.time() * 1000) if now_ms is None else now_ms
    if action not in STATELESS_ACTIONS | READ_ONLY_ACTIONS | WRITE_ACTIONS:
        raise ValueError('unknown swarm action')
    recorded = True
    if action in STATELESS_ACTIONS:
        swarm = None
    elif action in READ_ONLY_ACTIONS:
        swarm = _cached(sid, create=False)
        if swarm is None:
            recorded = False
            swarm = SwarmCoordinator(sid)  # empty, in memory, never cached
        else:
            swarm = _readable(swarm)
    elif action == 'journal_recover':
        swarm = None
    else:
        swarm = _cached(sid, create=True)
    result: Any = None
    if action == 'journal_recover':
        object_keys(args, {'swarm_id'}, {'full_replay'})
        result = _recover(sid, args.get('full_replay', False))
    elif action == 'snapshot':
        object_keys(args, {'swarm_id'})
        result = _live(swarm).snapshot(now_ms=now)
    elif action == 'configure_channel':
        object_keys(args, {'swarm_id', 'key', 'changes'})
        result = _live(swarm)._transaction('configure_channel', {'key': args['key'], 'changes': args['changes']}, now)
    elif action == 'fdc_decode':
        from codontrace.swarm.sensors import fdc_sample
        object_keys(args, {'swarm_id', 'reading', 'variant', 'config_id'})
        channel, payload = fdc_sample(args['reading'], variant=args['variant'], config_id=args['config_id'])
        result = {'channel': channel, 'payload': payload, 'device_command_sent': False, 'scope': 'adapter_preview_not_ingestion'}
    elif action == 'ingest':
        object_keys(args, {'swarm_id', 'message'})
        result = _live(swarm).ingest(args['message'], now_ms=now)
    elif action == 'command':
        object_keys(args, {'swarm_id', 'node_id', 'operation', 'params'}, {'timeout_ms'})
        result = _live(swarm).command(args['node_id'], args['operation'], args['params'], now_ms=now,
                               timeout_ms=args.get('timeout_ms', 5000))
    elif action == 'status':
        object_keys(args, {'swarm_id', 'status'})
        result = _live(swarm).set_status(args['status'], now_ms=now)
    elif action in ('fusion', 'diagnosis', 'plan'):
        optional = {'mode'} if action == 'fusion' else {'reference', 'tolerance'} if action == 'diagnosis' else {'budget'}
        object_keys(args, {'swarm_id', 'quantity', 'unit'}, optional)
        if action == 'fusion':
            result = _live(swarm).fuse(args['quantity'], args['unit'], now_ms=now, mode=args.get('mode', 'median'))
        elif action == 'diagnosis':
            result = _live(swarm).diagnose(args['quantity'], args['unit'], now_ms=now,
                                    reference=args.get('reference'), tolerance=args.get('tolerance', 2))
        else:
            result = _live(swarm).plan(args['quantity'], args['unit'], now_ms=now, budget=args.get('budget', 2))
    elif action == 'calibrate':
        object_keys(args, {'swarm_id', 'key', 'reference', 'reference_id'}, {'scale'})
        result = _live(swarm).calibrate(args['key'], args['reference'], args['reference_id'], now_ms=now,
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
        result = _live(swarm).freshness_plan(args['models'],args['quantity'],args['unit'],now_ms=now,
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
