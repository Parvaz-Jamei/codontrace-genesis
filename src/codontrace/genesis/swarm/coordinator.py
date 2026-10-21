"""SwarmCoordinatorCore: the pure coordination state machine.

No transport, no storage, no wire schema. ``apply(state, action, args, now)``
mutates a plain JSON state dict and returns the action result; a caller that
wants durability journals the actions (``codontrace.genesis.journal``), a
caller that does not uses ``transact`` on the core's own state. Message
decoding and operation-specific command parameters are injected, so module
vocabularies (wire schemas, device operations) stay outside this package.

Actions: ``ingest`` (hello / reading / reply), ``command``, ``status``,
``trust``, ``configure_channel``, ``boundary``. All times are host
milliseconds and must not move backwards. Each action first expires due
pending commands.
"""
from __future__ import annotations

import copy
import json
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any

from codontrace.contracts.channels import scalar_frame
from codontrace.contracts.wire_validation import bounded_int, finite_number, identifier, wire_canonical
from codontrace.genesis.journal import NotRecorded
from codontrace.genesis.swarm import active_sampling, commands, fusion, membership, readings, trust
from codontrace.genesis.swarm.diagnosis import peer_disagreement

__all__ = ['ACTIONS', 'BOUNDARY_LIMIT', 'STATUSES', 'CommandParams', 'Decoder', 'SwarmConfig', 'SwarmCoordinatorCore']

ACTIONS = ('ingest', 'command', 'status', 'trust', 'configure_channel', 'boundary')
STATUSES = ('running', 'paused', 'stopped')
BOUNDARY_LIMIT = 128

Decoder = Callable[[Any], dict[str, Any]]
CommandParams = Callable[[str, Any, dict[str, Any]], dict[str, Any]]


def _plain_decoder(message: Any) -> dict[str, Any]:
    """Accept an already decoded message: schema, swarm_id, node_id, boot_id, seq, kind, payload."""
    if not isinstance(message, Mapping) or not {'schema', 'swarm_id', 'node_id', 'boot_id', 'seq', 'kind',
                                                 'payload'} <= message.keys():
        raise ValueError('decoded message required')
    return dict(message)


def _plain_command_params(operation: str, params: Any, member: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(params, Mapping):
        raise ValueError('command parameters must be an object')
    return dict(params)


@dataclass(frozen=True, slots=True)
class SwarmConfig:
    """Coordination parameters that replay depends on."""

    swarm_id: str
    ttl_ms: int = 10000
    max_skew_ms: int = 2000

    def __post_init__(self) -> None:
        identifier(self.swarm_id)
        bounded_int(self.ttl_ms, high=3600000)
        if self.ttl_ms < 1:
            raise ValueError('positive TTL required')
        bounded_int(self.max_skew_ms, high=60000)


class SwarmCoordinatorCore:
    """Pure coordination over a JSON state dict (see module docstring)."""

    def __init__(self, config: SwarmConfig, *, decode: Decoder | None = None, typed_schema: str | None = None,
                 command_params: CommandParams | None = None) -> None:
        self.config = config
        self.decode = decode or _plain_decoder
        self.typed_schema = typed_schema
        self.command_params = command_params or _plain_command_params
        self.state = self.empty_state()

    @staticmethod
    def empty_state() -> dict[str, Any]:
        return {'nodes': {}, 'frames': {}, 'commands': {}, 'command_counter': 0,
                'trust': {}, 'history': [], 'engine_boundaries': [], 'status': 'running', 'now_ms': 0}

    # -- state machine -------------------------------------------------
    def apply(self, state: dict[str, Any], action: str, args: dict[str, Any], now: int) -> Any:
        cfg = self.config
        if now < state['now_ms']:
            raise ValueError('host clock moved backwards')
        state['now_ms'] = now
        nodes = state['nodes']
        commands.expire_pending(state['commands'], now)
        if action == 'ingest':
            m = self.decode(args['message'])
            if m['swarm_id'] != cfg.swarm_id:
                raise ValueError('cross-swarm message rejected')
            node_id = m['node_id']; p = m['payload']
            if m['kind'] == 'hello':
                return membership.accept_hello(state, node_id, m['boot_id'], m['seq'], p, now)
            node = nodes.get(node_id)
            skipped = membership.require_session(node, m['boot_id'], m['seq'])
            if skipped is not None:
                return skipped
            assert node is not None
            if m['kind'] == 'reading':
                readings.accept_reading(state, node_id, node, boot_id=m['boot_id'], seq=m['seq'], payload=p,
                                        typed=m['schema'] == self.typed_schema, now_ms=now, ttl_ms=cfg.ttl_ms,
                                        max_skew_ms=cfg.max_skew_ms)
            elif m['kind'] == 'reply':
                commands.apply_reply(state['commands'], node_id, m['boot_id'], p)
            membership.touch(node, m['seq'], now)
            return {'accepted': True}
        if action == 'command':
            if state['status'] != 'running':
                raise ValueError('commands require a running swarm')
            node_id = identifier(args['node_id']); node = nodes.get(node_id)
            op = args['operation']
            if node is None or not membership.is_online(node, now, cfg.ttl_ms):
                raise ValueError('node unavailable')
            if op not in node['operations']:
                raise ValueError('operation not advertised by node')
            params = self.command_params(op, args['params'], node)
            lifetime = bounded_int(args['timeout_ms'], high=60000)
            return commands.create_command(state, swarm_id=cfg.swarm_id, node_id=node_id, boot_id=node['boot_id'],
                                           operation=op, params=params, lifetime_ms=lifetime, now_ms=now)
        if action == 'status':
            status = args['status']
            if status not in STATUSES:
                raise ValueError('invalid swarm status')
            state['status'] = status
            if status != 'running':
                commands.cancel_pending(state['commands'])
            return {'status': status}
        if action == 'trust':
            key = args['key']; frame = state['frames'].get(key)
            if frame is None or not scalar_frame(frame) or now-frame['sample_ms'] > cfg.ttl_ms:
                raise ValueError('fresh frame required')
            reference = finite_number(args['reference']); scale = finite_number(args['scale'], low=0.001, high=1e6)
            state['trust'][key] = trust.update_trust(state['trust'].get(key), frame['value'], reference, scale,
                                                     args['reference_id'])
            return state['trust'][key]
        if action == 'configure_channel':
            return readings.configure_channel(state, args['key'], args['changes'])
        if action == 'boundary':
            row = args['row']
            state['engine_boundaries'].append(row)
            state['engine_boundaries'] = state['engine_boundaries'][-BOUNDARY_LIMIT:]
            return row
        raise ValueError('unknown swarm action')

    # -- read side -----------------------------------------------------
    def view(self, state: dict[str, Any], now_ms: int) -> dict[str, Any]:
        """Deep copy of ``state`` with member ``online`` flags and due commands shown expired."""
        view = copy.deepcopy(state)
        for node in view['nodes'].values():
            node['online'] = membership.is_online(node, now_ms, self.config.ttl_ms)
        for c in view['commands'].values():
            if c['status'] == 'pending' and c['expires_ms'] <= now_ms:
                c['status'] = 'expired'
        return view

    def members(self, state: dict[str, Any], now_ms: int) -> tuple[membership.SwarmMember, ...]:
        return tuple(membership.SwarmMember.from_state(k, v, now_ms=now_ms, ttl_ms=self.config.ttl_ms)
                     for k, v in sorted(state['nodes'].items()))

    def frames(self, view: dict[str, Any], quantity: str, unit: str, now_ms: int) -> dict[str, dict[str, Any]]:
        return fusion.fresh_scalar_frames(view, quantity, unit, now_ms=now_ms, ttl_ms=self.config.ttl_ms,
                                          max_skew_ms=self.config.max_skew_ms)

    def fuse(self, state: dict[str, Any], quantity: str, unit: str, *, now_ms: int, mode: str = 'median',
             max_span_ms: int = 1000) -> dict[str, Any]:
        bounded_int(max_span_ms, high=3600000)
        if mode not in fusion.FUSION_MODES:
            raise ValueError('unknown fusion mode')
        frames = self.frames(self.view(state, now_ms), quantity, unit, now_ms)
        return fusion.robust_fuse(frames, state['trust'], quantity, unit, mode=mode, max_span_ms=max_span_ms)

    def diagnose(self, state: dict[str, Any], quantity: str, unit: str, *, now_ms: int,
                 reference: float | None = None, tolerance: float = 2.0) -> dict[str, Any]:
        frames = self.frames(self.view(state, now_ms), quantity, unit, now_ms)
        return peer_disagreement({k: f['value'] for k, f in frames.items()}, reference=reference, tolerance=tolerance)

    def plan(self, state: dict[str, Any], quantity: str, unit: str, *, now_ms: int,
             budget: int = 2) -> list[tuple[str, str]]:
        return active_sampling.plan_oldest_first(self.view(state, now_ms), quantity, unit, now_ms=now_ms,
                                                 ttl_ms=self.config.ttl_ms, budget=budget)

    # -- standalone use (no journal) -------------------------------------
    def transact(self, action: str, args: dict[str, Any], now_ms: int) -> Any:
        """Apply to the core's own state atomically: on error the state is unchanged."""
        now_ms = bounded_int(now_ms)
        working = copy.deepcopy(self.state)
        result = self.apply(working, action, json.loads(wire_canonical(args)), now_ms)
        if isinstance(result, NotRecorded):
            return dict(result)
        self.state = working
        return copy.deepcopy(result)
