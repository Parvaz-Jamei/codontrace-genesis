"""Membership: boot sessions, sequence de-duplication and TTL liveness.

A member is identified by ``node_id`` and a ``boot_id`` session. Within one
session sequence numbers must increase; a duplicate or reordered message is
reported without a state change. A new session drops the member's per-channel
state (frames, trust, host channel configuration) and marks its pending
commands ``boot_replaced``. Liveness is ``now - last_seen_ms <= ttl_ms``.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from codontrace.genesis.journal import NotRecorded

__all__ = ['MEMBER_CAPACITY', 'SwarmMember', 'accept_hello', 'drop_session_state', 'is_online', 'require_session',
           'touch']

MEMBER_CAPACITY = 256


def is_online(member: dict[str, Any], now_ms: int, ttl_ms: int) -> bool:
    return bool(now_ms - member['last_seen_ms'] <= ttl_ms)


def drop_session_state(state: dict[str, Any], node_id: str) -> None:
    """Forget per-channel state of a member whose boot session changed."""
    for config_key in list(state.get('channel_configs', {})):
        if config_key.startswith(node_id + '/'):
            del state['channel_configs'][config_key]
    for key in list(state['frames']):
        if key.startswith(node_id + '/'):
            del state['frames'][key]
            state['trust'].pop(key, None)
    for c in state['commands'].values():
        if c['node_id'] == node_id and c['status'] == 'pending':
            c['status'] = 'boot_replaced'


def accept_hello(state: dict[str, Any], node_id: str, boot_id: str, seq: int, payload: dict[str, Any],
                 now_ms: int) -> dict[str, Any]:
    """Register or refresh a member from a hello message."""
    nodes = state['nodes']
    node = nodes.get(node_id)
    if node is None and len(nodes) >= MEMBER_CAPACITY:
        raise ValueError('node capacity reached')
    if node is not None and node['boot_id'] == boot_id:
        if node['channels'] != payload['channels'] or node['operations'] != payload['operations']:
            raise ValueError('capabilities changed within boot session')
        if seq <= node['seq']:
            return NotRecorded(accepted=False, reason='duplicate_or_reordered')
    if node is not None and node['boot_id'] != boot_id:
        drop_session_state(state, node_id)
    nodes[node_id] = {**payload, 'boot_id': boot_id, 'seq': seq, 'last_seen_ms': now_ms}
    return {'accepted': True}


def require_session(node: dict[str, Any] | None, boot_id: str, seq: int) -> dict[str, Any] | None:
    """Check a non-hello message against the member's session.

    Returns ``None`` when the message may proceed, or a ``NotRecorded`` result
    for a duplicate or reordered message. Raises for an unknown session.
    """
    if node is None or boot_id != node['boot_id']:
        raise ValueError('hello required for this boot session')
    if seq <= node['seq']:
        return NotRecorded(accepted=False, reason='duplicate_or_reordered')
    return None


def touch(node: dict[str, Any], seq: int, now_ms: int) -> None:
    node['seq'] = seq
    node['last_seen_ms'] = now_ms


@dataclass(frozen=True, slots=True)
class SwarmMember:
    """Read-only view of one member for inspection and adapters (not journaled)."""

    member_id: str
    session_id: str
    seq: int
    last_seen_ms: int
    online: bool
    channels: tuple[str, ...]
    operations: tuple[str, ...]

    @classmethod
    def from_state(cls, member_id: str, node: dict[str, Any], *, now_ms: int, ttl_ms: int) -> SwarmMember:
        return cls(member_id=member_id, session_id=str(node['boot_id']), seq=int(node['seq']),
                   last_seen_ms=int(node['last_seen_ms']), online=is_online(node, now_ms, ttl_ms),
                   channels=tuple(sorted(node.get('channels', {}))), operations=tuple(node.get('operations', ())))

    def to_dict(self) -> dict[str, Any]:
        return {'member_id': self.member_id, 'session_id': self.session_id, 'seq': self.seq,
                'last_seen_ms': self.last_seen_ms, 'online': self.online, 'channels': list(self.channels),
                'operations': list(self.operations)}
