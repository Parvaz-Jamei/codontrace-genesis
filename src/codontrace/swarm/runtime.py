"""Transactional host coordinator, measured data only; no board firmware."""
from __future__ import annotations

import os  # noqa: F401  (tests patch codontrace.swarm.runtime.os.fsync)
from pathlib import Path
from typing import Any

from codontrace.genesis.journal import (  # noqa: F401  (public names)
    CHECKPOINTS_KEPT,
    MAX_CHECKPOINT_BYTES,
    HashChainedJournal,
    NotRecorded,
)
from codontrace.genesis.swarm import (
    SwarmConfig,
    SwarmCoordinatorCore,
    measurement_candidates,
    plan_oldest_first,
    robust_fuse,
)
from codontrace.genesis.swarm.fusion import FUSION_MODES
from codontrace.swarm.policies import Pipeline, diagnose
from codontrace.swarm.protocol import (  # noqa: F401  (canonical is a public name)
    VERSION2,
    canonical,
    decode,
    identifier,
    integer,
    number,
    object_keys,
    text,
)
from codontrace.swarm.sensors import descriptor, normalize, scalar_frame  # noqa: F401  (public names)

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
        self._core = SwarmCoordinatorCore(SwarmConfig(self.swarm_id, self.ttl_ms, self.max_skew_ms), decode=decode,
                                          typed_schema=VERSION2, command_params=self._command_params)
        self._init_journal(journal, segment_bytes=journal_segment_bytes, retention_bytes=journal_retention_bytes,
                           archive_max_bytes=archive_max_bytes, lock_timeout_s=lock_timeout_s, restore=restore)

    def _record_header(self) -> dict[str, Any]:
        """Fields repeated in every journal record and checkpoint (replay depends on them)."""
        return {'swarm_id': self.swarm_id, 'ttl_ms': self.ttl_ms, 'max_skew_ms': self.max_skew_ms}

    @staticmethod
    def _empty_state() -> dict[str, Any]:
        return SwarmCoordinatorCore.empty_state()

    def _apply(self, action: str, args: dict[str, Any], now: int) -> Any:
        return self._core.apply(self._state, action, args, now)

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

    def ingest(self, message: Any, *, now_ms: int) -> dict[str, Any]:
        return self._transaction('ingest', {'message': decode(message)}, now_ms)

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

    def snapshot(self, *, now_ms: int) -> dict[str, Any]:
        integer(now_ms)
        with self._lock:
            state = self._core.view(self._state, now_ms)
            return {'schema': 'genesis_swarm_snapshot_v1', 'swarm_id': self.swarm_id,
                    'coordination_mode': 'genesis_orchestrated_sensor_swarm', 'physical_validation': False,
                    'state': state, 'journal_digest': self._chain, **self.journal_health()}

    def run_reference(self) -> dict[str, Any]:
        """Module run reference with the journal head anchor (see genesis.run_refs, genesis.journal.anchor)."""
        from codontrace.genesis.journal.anchor import journal_anchor
        from codontrace.genesis.run_refs import module_run_reference
        return module_run_reference('swarm', self.swarm_id, journal_anchor=journal_anchor(self),
                                    extra={'coordination_mode': 'genesis_orchestrated_sensor_swarm'})

    def frames(self, quantity: str, unit: str, *, now_ms: int) -> dict[str, dict[str, Any]]:
        text(quantity); text(unit)
        snapshot = self.snapshot(now_ms=now_ms)['state']
        return self._core.frames(snapshot, quantity, unit, now_ms)

    def fuse(self, quantity: str, unit: str, *, now_ms: int, mode: str = 'median', max_span_ms: int = 1000) -> dict[str, Any]:
        integer(max_span_ms, high=3600000)
        if mode not in FUSION_MODES:
            raise ValueError('unknown fusion mode')
        # Hold one lock across frames and learned weights: no mixed snapshots.
        with self._lock:
            frames = self.frames(quantity, unit, now_ms=now_ms)
            return robust_fuse(frames, self._state['trust'], quantity, unit, mode=mode, max_span_ms=max_span_ms)

    def diagnose(self, quantity: str, unit: str, *, now_ms: int,
                 reference: float | None = None, tolerance: float = 2.0) -> dict[str, Any]:
        frames = self.frames(quantity, unit, now_ms=now_ms)
        return diagnose({k: f['value'] for k, f in frames.items()}, reference=reference, tolerance=tolerance)

    def plan(self, quantity: str, unit: str, *, now_ms: int, budget: int = 2) -> list[dict[str, Any]]:
        text(quantity); text(unit); integer(budget, high=32)
        with self._lock:
            snapshot = self.snapshot(now_ms=now_ms)['state']
            # Capability-aware oldest-first allocation, not claimed optimal information gain.
            return [self.command(node_id, 'sample', {'channel': channel}, now_ms=now_ms)
                    for node_id, channel in plan_oldest_first(snapshot, quantity, unit, now_ms=now_ms,
                                                              ttl_ms=self.ttl_ms, budget=budget)]

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
        with self._lock:
            snapshot=self.snapshot(now_ms=now_ms)
            state=snapshot['state']
            candidates,excluded=measurement_candidates(state,models,quantity,unit,now_ms=now_ms)
            result=schedule_measurements(candidates,now_ms=now_ms,byte_budget=byte_budget,request_budget=request_budget)
            result.update(swarm_id=self.swarm_id,quantity=quantity,unit=unit,excluded_channels=excluded,
                          journal_digest=snapshot['journal_digest'],swarm_status=state['status'])
            return result
