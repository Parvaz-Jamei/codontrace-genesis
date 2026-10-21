"""Command lifecycle: pending -> acknowledged | rejected | expired | cancelled | boot_replaced.

Commands expire when ``expires_ms <= now``. At most 256 pending commands; the
table keeps at most 1024 entries by dropping the oldest finished one.
"""
from __future__ import annotations

from typing import Any

__all__ = ['COMMAND_SCHEMA', 'MAX_COMMANDS', 'MAX_PENDING', 'apply_reply', 'cancel_pending', 'create_command',
           'expire_pending', 'pending_for']

COMMAND_SCHEMA = 'genesis_swarm_command_v1'
MAX_PENDING = 256
MAX_COMMANDS = 1024


def expire_pending(commands: dict[str, dict[str, Any]], now_ms: int) -> None:
    for command in commands.values():
        if command['status'] == 'pending' and command['expires_ms'] <= now_ms:
            command['status'] = 'expired'


def cancel_pending(commands: dict[str, dict[str, Any]]) -> None:
    for c in commands.values():
        if c['status'] == 'pending':
            c['status'] = 'cancelled'


def pending_for(commands: dict[str, dict[str, Any]], node_id: str, channel: str) -> bool:
    return any(c['status'] == 'pending' and c['node_id'] == node_id and c['params'].get('channel') == channel
               for c in commands.values())


def create_command(state: dict[str, Any], *, swarm_id: str, node_id: str, boot_id: str, operation: str,
                   params: dict[str, Any], lifetime_ms: int, now_ms: int) -> dict[str, Any]:
    if lifetime_ms < 1:
        raise ValueError('positive timeout required')
    commands = state['commands']
    if sum(c['status'] == 'pending' for c in commands.values()) >= MAX_PENDING:
        raise ValueError('pending command capacity reached')
    if len(commands) >= MAX_COMMANDS:
        oldest = next((k for k, c in commands.items() if c['status'] != 'pending'), None)
        if oldest is not None:
            del commands[oldest]
    state['command_counter'] += 1
    command_id = 'cmd-' + str(state['command_counter'])
    c = {'schema': COMMAND_SCHEMA, 'swarm_id': swarm_id, 'node_id': node_id,
         'boot_id': boot_id, 'command_id': command_id, 'operation': operation, 'params': params,
         'created_ms': now_ms, 'expires_ms': now_ms + lifetime_ms, 'status': 'pending'}
    commands[command_id] = c
    return c


def apply_reply(commands: dict[str, dict[str, Any]], node_id: str, boot_id: str, payload: dict[str, Any]) -> None:
    c = commands.get(payload['command_id'])
    if c is None or c['node_id'] != node_id or c['boot_id'] != boot_id:
        raise ValueError('reply identity mismatch')
    if c['status'] != 'pending':
        raise ValueError('reply to non-pending command')
    c['status'] = 'acknowledged' if payload['ok'] else 'rejected'
    c['reply'] = payload
