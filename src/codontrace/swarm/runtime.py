"""Transactional host coordinator, measured data only; no board firmware."""
from __future__ import annotations

import copy
import os  # noqa: F401  (tests patch codontrace.swarm.runtime.os.fsync)
import statistics
from pathlib import Path
from typing import Any

from codontrace.genesis.journal import (  # noqa: F401  (public names)
    CHECKPOINTS_KEPT,
    MAX_CHECKPOINT_BYTES,
    HashChainedJournal,
    NotRecorded,
)
from codontrace.genesis.journal import (
    JournalBusyError as JournalBusyError,
)
from codontrace.swarm.policies import Pipeline, diagnose
from codontrace.swarm.protocol import VERSION2, canonical, decode, identifier, integer, number, object_keys, text  # noqa: F401  (canonical is a public name)
from codontrace.swarm.sensors import descriptor, normalize, scalar_frame

CHECKPOINT_SCHEMA = 'genesis_swarm_checkpoint_v1'
_NotRecorded = NotRecorded  # historical name


class SwarmCoordinator(HashChainedJournal):
    """One isolated sensor swarm; centralized orchestration, not decentralized proof.

    A hash-chained write-ahead journal replays host decisions, not physical reality.
    All times are host UTC milliseconds; sample clocks must be synchronized.

    Journal layout: closed segments ``<journal>.part.NNNNNNNN`` plus the active
    file. Each rotation writes a hashed state checkpoint bound to the last record
    of the closed segment; startup restores the newest checkpoint verified against
    the current journal and replays only later records, falling back to older
    checkpoints or to a full replay that includes ``<journal>.archive/``
    (checkpoints are a rebuildable cache, never authoritative history). With
    ``journal_retention_bytes`` set, closed segments already covered by a verified
    checkpoint move to the archive; archived segments are deleted only when
    ``archive_max_bytes`` is set and exceeded.

    Integrity scope: SHA-256 links are unkeyed, so they detect corruption and
    accidental edits, not a deliberate rewrite by someone with write access.
    Startup checks every live record's link; archived segments are only checked
    by full replay. Removal of trailing records or of the whole active file is a
    consistent shorter history and is not detected without an external anchor.

    One instance per journal per process is expected. Another instance (or
    process) that appended in the meantime makes this instance refuse writes with
    'journal changed externally'; ``recover()`` reloads it from disk.

    Storage, restore, checkpoints, retention and locking come from
    ``codontrace.genesis.journal.HashChainedJournal``; this class is the swarm
    state machine (``_apply``) plus its record header and wire decoding.
    """
    _checkpoint_schema = CHECKPOINT_SCHEMA
    _journal_label = 'swarm'
    def __init__(self, swarm_id: str, *, journal: Path | None = None, ttl_ms: int = 10000,
                 max_skew_ms: int = 2000, journal_segment_bytes: int = 4*1024*1024,
                 journal_retention_bytes: int | None = None, archive_max_bytes: int | None = None,
                 lock_timeout_s: float = 2.0, restore: bool = True) -> None:
        self.swarm_id = identifier(swarm_id)
        self.ttl_ms = integer(ttl_ms, high=3600000)
        if ttl_ms < 1:
            raise ValueError('positive TTL required')
        self.max_skew_ms = integer(max_skew_ms, high=60000)
        self._init_journal(journal, segment_bytes=journal_segment_bytes, retention_bytes=journal_retention_bytes,
                           archive_max_bytes=archive_max_bytes, lock_timeout_s=lock_timeout_s, restore=restore)

    def _record_header(self) -> dict[str, Any]:
        """Fields repeated in every journal record and checkpoint (replay depends on them)."""
        return {'swarm_id': self.swarm_id, 'ttl_ms': self.ttl_ms, 'max_skew_ms': self.max_skew_ms}

    @staticmethod
    def _empty_state() -> dict[str, Any]:
        return {'nodes': {}, 'frames': {}, 'commands': {}, 'command_counter': 0,
                'trust': {}, 'history': [], 'engine_boundaries': [], 'status': 'running', 'now_ms': 0}

    def _apply(self, action: str, args: dict[str, Any], now: int) -> Any:
        if now < self._state['now_ms']:
            raise ValueError('host clock moved backwards')
        self._state['now_ms'] = now
        nodes = self._state['nodes']
        for command in self._state['commands'].values():
            if command['status'] == 'pending' and command['expires_ms'] <= now:
                command['status'] = 'expired'
        if action == 'ingest':
            m = decode(args['message'])
            if m['swarm_id'] != self.swarm_id:
                raise ValueError('cross-swarm message rejected')
            node_id = m['node_id']; p = m['payload']; node = nodes.get(node_id)
            if m['kind'] == 'hello':
                if node is None and len(nodes) >= 256:
                    raise ValueError('node capacity reached')
                if node is not None and node['boot_id'] == m['boot_id']:
                    if node['channels'] != p['channels'] or node['operations'] != p['operations']:
                        raise ValueError('capabilities changed within boot session')
                    if m['seq'] <= node['seq']:
                        return _NotRecorded(accepted=False, reason='duplicate_or_reordered')
                if node is not None and node['boot_id'] != m['boot_id']:
                    for config_key in list(self._state.get('channel_configs', {})):
                        if config_key.startswith(node_id + '/'):
                            del self._state['channel_configs'][config_key]
                    for key in list(self._state['frames']):
                        if key.startswith(node_id + '/'):
                            del self._state['frames'][key]
                            self._state['trust'].pop(key, None)
                    for c in self._state['commands'].values():
                        if c['node_id'] == node_id and c['status'] == 'pending':
                            c['status'] = 'boot_replaced'
                nodes[node_id] = {**p, 'boot_id': m['boot_id'], 'seq': m['seq'], 'last_seen_ms': now}
                return {'accepted': True}
            if node is None or m['boot_id'] != node['boot_id']:
                raise ValueError('hello required for this boot session')
            if m['seq'] <= node['seq']:
                return _NotRecorded(accepted=False, reason='duplicate_or_reordered')
            if m['kind'] == 'reading':
                if self._state['status'] != 'running':
                    raise ValueError('swarm is paused or stopped')
                if p['channel'] not in node['channels']:
                    raise ValueError('undeclared channel')
                channel_config = node['channels'][p['channel']]
                if ('descriptor' in channel_config) != (m['schema'] == VERSION2):
                    raise ValueError('reading schema differs from advertised channel')
                if p['sample_ms'] > now + self.max_skew_ms or now - p['sample_ms'] > self.ttl_ms:
                    raise ValueError('stale sample or clock skew')
                key = node_id + '/' + p['channel']
                if m['schema'] == VERSION2:
                    channel_config = {**channel_config, 'descriptor': self._state.get('channel_configs', {}).get(key, channel_config['descriptor'])}
                    p = normalize(p, channel_config)
                    if 'reference' in p and p.get('reference_unit') != channel_config['unit']:
                        raise ValueError('reference must explicitly use normalized channel unit')
                    if 'reference' in p and channel_config['descriptor']['value_type'] != 'scalar':
                        raise ValueError('scalar reference not supported for non-scalar channel')
                previous = self._state['frames'].get(key)
                if previous and p['sample_ms'] < previous['sample_ms']:
                    raise ValueError('sample clock reordered')
                if previous and (previous['processing_version'] != p['processing_version'] or previous.get('descriptor_digest') != p.get('descriptor_digest')):
                    self._state['trust'].pop(key, None)
                self._state['frames'][key] = {**p, **node['channels'][p['channel']],
                                              'node_id': node_id, 'boot_id': m['boot_id'], 'received_ms': now, 'seq': m['seq']}
                self._state['history'].append(self._state['frames'][key])
                self._state['history'] = self._state['history'][-512:]
            elif m['kind'] == 'reply':
                c = self._state['commands'].get(p['command_id'])
                if c is None or c['node_id'] != node_id or c['boot_id'] != m['boot_id']:
                    raise ValueError('reply identity mismatch')
                if c['status'] != 'pending':
                    raise ValueError('reply to non-pending command')
                c['status'] = 'acknowledged' if p['ok'] else 'rejected'
                c['reply'] = p
            node['seq'] = m['seq']; node['last_seen_ms'] = now
            return {'accepted': True}
        if action == 'command':
            if self._state['status'] != 'running':
                raise ValueError('commands require a running swarm')
            node_id = identifier(args['node_id']); node = nodes.get(node_id)
            op = args['operation']
            if node is None or now - node['last_seen_ms'] > self.ttl_ms:
                raise ValueError('node unavailable')
            if op not in node['operations']:
                raise ValueError('operation not advertised by node')
            params = self._command_params(op, args['params'], node)
            lifetime = integer(args['timeout_ms'], high=60000)
            if lifetime < 1:
                raise ValueError('positive timeout required')
            if sum(c['status'] == 'pending' for c in self._state['commands'].values()) >= 256:
                raise ValueError('pending command capacity reached')
            if len(self._state['commands']) >= 1024:
                oldest = next((k for k, c in self._state['commands'].items() if c['status'] != 'pending'), None)
                if oldest is not None:
                    del self._state['commands'][oldest]
            self._state['command_counter'] += 1
            command_id = 'cmd-' + str(self._state['command_counter'])
            c = {'schema': 'genesis_swarm_command_v1', 'swarm_id': self.swarm_id, 'node_id': node_id,
                 'boot_id': node['boot_id'], 'command_id': command_id, 'operation': op, 'params': params,
                 'created_ms': now, 'expires_ms': now + lifetime, 'status': 'pending'}
            self._state['commands'][command_id] = c
            return c
        if action == 'status':
            status = args['status']
            if status not in ('running', 'paused', 'stopped'):
                raise ValueError('invalid swarm status')
            self._state['status'] = status
            if status != 'running':
                for c in self._state['commands'].values():
                    if c['status'] == 'pending':
                        c['status'] = 'cancelled'
            return {'status': status}
        if action == 'trust':
            key = args['key']; frame = self._state['frames'].get(key)
            if frame is None or not scalar_frame(frame) or now-frame['sample_ms'] > self.ttl_ms:
                raise ValueError('fresh frame required')
            reference = number(args['reference']); scale = number(args['scale'], low=0.001, high=1e6)
            reliability = 1 / (1 + abs(frame['value'] - reference) / scale)
            old = self._state['trust'].get(key, {'weight': 1.0, 'samples': 0})
            self._state['trust'][key] = {'weight': 0.8 * old['weight'] + 0.2 * reliability,
                                         'samples': old['samples'] + 1, 'reference_id': args['reference_id']}
            return self._state['trust'][key]
        if action == 'configure_channel':
            key = args['key']
            if not isinstance(key, str) or len(key.split('/')) != 2: raise ValueError('node/channel key required')
            node_id, channel_id = key.split('/');identifier(node_id);identifier(channel_id)
            node = nodes.get(node_id)
            if node is None or channel_id not in node['channels']: raise ValueError('unknown channel')
            channel = node['channels'][channel_id]
            if 'descriptor' not in channel: raise ValueError('typed v2 channel required')
            changes = object_keys(args['changes'], set(), {'normalization', 'range'})
            d = dict(self._state.get('channel_configs', {}).get(key, channel['descriptor']))
            for field, value in changes.items():
                if value is None: d.pop(field, None)
                else: d[field] = value
            d = descriptor(d)
            if d.get('normalization', {}).get('output_unit', d['source_unit']) != channel['unit']:
                raise ValueError('configured normalization must preserve declared output unit')
            self._state.setdefault('channel_configs', {})[key] = d
            self._state['frames'].pop(key, None); self._state['trust'].pop(key, None)
            return {'key': key, 'descriptor': d, 'host_configuration_applied': True, 'device_command_sent': False}
        if action == 'boundary':
            row = args['row']
            self._state['engine_boundaries'].append(row)
            self._state['engine_boundaries'] = self._state['engine_boundaries'][-128:]
            return row
        raise ValueError('unknown swarm action')

    @staticmethod
    def _command_params(op: str, params: Any, node: dict[str, Any]) -> dict[str, Any]:
        if op in ('sample', 'raw', 'features', 'result'):
            p = object_keys(params, {'channel'})
            if p['channel'] not in node['channels']:
                raise ValueError('undeclared channel')
        elif op == 'set_rate':
            p = object_keys(params, {'channel', 'hz'})
            if p['channel'] not in node['channels']:
                raise ValueError('undeclared channel')
            number(p['hz'], low=0.01, high=10000)
            limits = node['channels'][p['channel']].get('descriptor', {}).get('rate_hz')
            if limits is not None and not limits[0] <= p['hz'] <= limits[1]:
                raise ValueError('rate outside advertised sensor capability')
        elif op in ('pipeline', 'capsule'):
            p = object_keys(params, {'channel', 'pipeline'}, {'source_digest'})
            if p['channel'] not in node['channels']:
                raise ValueError('undeclared channel')
            if node['channels'][p['channel']].get('descriptor', {}).get('value_type', 'scalar') != 'scalar':
                raise ValueError('scalar pipeline requires scalar channel')
            config = object_keys(p['pipeline'], {'alpha', 'clip', 'event_threshold'})
            Pipeline(**config)
            if 'source_digest' in p and (not isinstance(p['source_digest'], str) or len(p['source_digest']) != 64 or any(c not in '0123456789abcdef' for c in p['source_digest'])):
                raise ValueError('invalid source digest')
        else:
            raise ValueError('unsupported command')
        return p

    def ingest(self, message: Any, *, now_ms: int, lock_timeout_s: float | None = None,
               in_process_timeout_s: float | None = None) -> dict[str, Any]:
        """Journal one device message.

        ``lock_timeout_s`` optionally bounds only the wait for the cross-process
        journal file lock; ``in_process_timeout_s`` bounds the wait for this
        coordinator's own lock (held by other threads of this process while they
        write, fsync, checkpoint or recover). Either raises ``JournalBusyError``
        (scope ``'file'`` or ``'in_process'``) when exceeded. Note: in f4bf8c6
        ``lock_timeout_s`` bounded both waits; since 55e5b8b it bounds only the
        file lock, so a slow same-process writer does not make callers drop data.
        """
        return self._transaction('ingest', {'message': decode(message)}, now_ms, lock_timeout_s=lock_timeout_s,
                                 in_process_timeout_s=in_process_timeout_s)

    def command(self, node_id: str, operation: str, params: dict[str, Any], *, now_ms: int,
                timeout_ms: int = 5000) -> dict[str, Any]:
        return self._transaction('command', {'node_id': node_id, 'operation': operation,
                                             'params': params, 'timeout_ms': timeout_ms}, now_ms)

    def set_status(self, status: str, *, now_ms: int) -> dict[str, Any]:
        return self._transaction('status', {'status': status}, now_ms)

    def calibrate(self, key: str, reference: float, reference_id: str, *, now_ms: int,
                  scale: float = 1.0) -> dict[str, Any]:
        identifier(reference_id)
        return self._transaction('trust', {'key': key, 'reference': reference,
                                           'reference_id': reference_id, 'scale': scale}, now_ms)

    def snapshot(self, *, now_ms: int, lock_timeout_s: float | None = None) -> dict[str, Any]:
        """Copy of the state. ``lock_timeout_s`` optionally bounds the wait for this
        coordinator's lock (``JournalBusyError``, scope ``'in_process'``)."""
        integer(now_ms)
        with self._in_process_lock(lock_timeout_s):
            state = copy.deepcopy(self._state)
            for node in state['nodes'].values():
                node['online'] = now_ms - node['last_seen_ms'] <= self.ttl_ms
            for c in state['commands'].values():
                if c['status'] == 'pending' and c['expires_ms'] <= now_ms:
                    c['status'] = 'expired'
            return {'schema': 'genesis_swarm_snapshot_v1', 'swarm_id': self.swarm_id,
                    'coordination_mode': 'genesis_orchestrated_sensor_swarm', 'physical_validation': False,
                    'state': state, 'journal_digest': self._chain, **self.journal_health()}

    def frames(self, quantity: str, unit: str, *, now_ms: int) -> dict[str, dict[str, Any]]:
        text(quantity); text(unit)
        snapshot = self.snapshot(now_ms=now_ms)['state']
        return {k: f for k, f in snapshot['frames'].items()
                if scalar_frame(f) and f['quantity'] == quantity and f['unit'] == unit and
                -self.max_skew_ms <= now_ms-f['sample_ms'] <= self.ttl_ms and
                snapshot['nodes'][f['node_id']]['online'] and f.get('quality', 1) > 0}

    def fuse(self, quantity: str, unit: str, *, now_ms: int, mode: str = 'median', max_span_ms: int = 1000) -> dict[str, Any]:
        integer(max_span_ms, high=3600000)
        if mode not in ('median', 'mean', 'calibrated'):
            raise ValueError('unknown fusion mode')
        # Hold one lock across frames and learned weights: no mixed snapshots.
        with self._lock:
            frames = self.frames(quantity, unit, now_ms=now_ms)
            if not frames:
                return {'value': None, 'count': 0, 'status': 'insufficient_data', 'unit': unit}
            latest = max(f['sample_ms'] for f in frames.values())
            frames = {k: f for k, f in frames.items() if latest-f['sample_ms'] <= max_span_ms}
            semantics = {(f.get('sensor_descriptor', {}).get('feature_id'), f.get('sensor_descriptor', {}).get('measurement_model'),
                          f.get('sensor_descriptor', {}).get('model_id')) for f in frames.values()}
            if len(semantics) > 1:
                return {'value': None, 'count': len(frames), 'status': 'incompatible_measurement_semantics', 'unit': unit}
            values = [f['value'] for f in frames.values()]
            center = statistics.median(values)
            if mode == 'mean':
                center = statistics.mean(values)
            if mode == 'calibrated':
                weights = {k: self._state['trust'].get(k, {'weight': 1.0})['weight'] * f.get('quality', 1)
                           for k, f in frames.items()}
                total = sum(weights.values())
                if total == 0:
                    return {'value': None, 'count': len(frames), 'status': 'zero_weight', 'unit': unit}
                center = sum(frames[k]['value'] * w for k, w in weights.items()) / total
            return {'value': center, 'count': len(frames), 'status': 'descriptive_estimate',
                    'quantity': quantity, 'unit': unit, 'mode': mode,
                    'disagreement_mad': statistics.median(abs(v-statistics.median(values)) for v in values),
                    'contributors': sorted(frames), 'confidence_interval': None}

    def diagnose(self, quantity: str, unit: str, *, now_ms: int,
                 reference: float | None = None, tolerance: float = 2.0) -> dict[str, Any]:
        frames = self.frames(quantity, unit, now_ms=now_ms)
        return diagnose({k: f['value'] for k, f in frames.items()}, reference=reference, tolerance=tolerance)

    def plan(self, quantity: str, unit: str, *, now_ms: int, budget: int = 2) -> list[dict[str, Any]]:
        text(quantity); text(unit); integer(budget, high=32)
        with self._lock:
            snapshot = self.snapshot(now_ms=now_ms)['state']
            candidates = []
            for node_id, node in snapshot['nodes'].items():
                if not node['online'] or 'sample' not in node['operations']:
                    continue
                for channel, config in node['channels'].items():
                    if config.get('quantity') != quantity or config.get('unit') != unit or config.get('descriptor', {}).get('value_type', 'scalar') != 'scalar':
                        continue
                    if any(c['status'] == 'pending' and c['node_id'] == node_id and
                           c['params'].get('channel') == channel for c in snapshot['commands'].values()):
                        continue
                    frame = snapshot['frames'].get(node_id + '/' + channel)
                    age = self.ttl_ms+1 if frame is None else now_ms - frame['sample_ms']
                    candidates.append((-age, node_id, channel))
            # Capability-aware oldest-first allocation, not claimed optimal information gain.
            return [self.command(node_id, 'sample', {'channel': channel}, now_ms=now_ms)
                    for _, node_id, channel in sorted(candidates)[:budget]]

    def boundary(self, row: dict[str, Any], *, now_ms: int) -> dict[str, Any]:
        return self._transaction('boundary', {'row': row}, now_ms)

    def freshness_plan(self, models: dict[str, Any], quantity: str, unit: str, *, now_ms: int,
                       byte_budget: int, request_budget: int = 8) -> dict[str, Any]:
        """Read actual node capabilities/sample times; model costs remain estimates.

        Advisory only: dispatch via the existing authenticated command route.
        A stale/offline, wrong-unit or already-pending channel is not selected.
        """
        from codontrace.swarm.decision_support import schedule_measurements
        text(quantity); text(unit)
        if not isinstance(models,dict) or len(models)>256:
            raise ValueError('bounded channel model dictionary required')
        with self._lock:
            snapshot=self.snapshot(now_ms=now_ms)
            state=snapshot['state'];candidates=[];excluded=[]
            for key,model in models.items():
                if not isinstance(key,str) or len(key.split('/'))!=2:
                    raise ValueError('model key must be node/channel')
                node_id,channel=key.split('/');identifier(node_id);identifier(channel)
                node=state['nodes'].get(node_id)
                if node is None or channel not in node['channels']:
                    raise ValueError('model channel has not been advertised')
                object_keys(model,{'group','noise_variance','process_variance_per_ms','latency_ms',
                                   'success_probability','payload_bytes','evidence_id'})
                frame=state['frames'].get(key)
                eligible=(node['online'] and 'sample' in node['operations'] and frame is not None
                          and frame['sample_ms']<=now_ms
                          and node['channels'][channel].get('quantity')==quantity and node['channels'][channel].get('unit')==unit
                          and scalar_frame(frame)
                          and not any(c['status']=='pending' and c['node_id']==node_id and c['params'].get('channel')==channel
                                      for c in state['commands'].values()))
                if eligible:
                    candidates.append({**model,'key':key,'sample_ms':frame['sample_ms']})
                else: excluded.append(key)
            result=schedule_measurements(candidates,now_ms=now_ms,byte_budget=byte_budget,request_budget=request_budget)
            result.update(swarm_id=self.swarm_id,quantity=quantity,unit=unit,excluded_channels=excluded,
                          journal_digest=snapshot['journal_digest'],swarm_status=state['status'])
            return result
