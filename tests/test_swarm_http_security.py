"""Swarm/simulation HTTP routes on a real non-loopback address: auth, input validation, storage."""
from __future__ import annotations

import json
import os
import socket
import threading
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import pytest

from codontrace.swarm import service
from codontrace.swarm.experiments import hello, reading


def _lan_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('10.255.255.255', 1))
        ip = s.getsockname()[0]
    except OSError:
        ip = None
    finally:
        s.close()
    return ip if ip and not ip.startswith('127.') else None


IP = _lan_ip()
pytestmark = pytest.mark.skipif(IP is None, reason='no non-loopback interface')

OP = 'operator-secret'
NODE = 'node-a-secret'


@pytest.fixture
def remote(tmp_path, monkeypatch):
    from codontrace.console.server import make_server
    monkeypatch.setenv('CODONTRACE_SWARM_DIR', str(tmp_path / 'swarm'))
    monkeypatch.setenv('CODONTRACE_RUNS_DIR', str(tmp_path / 'runs'))
    monkeypatch.setenv('CODONTRACE_SWARM_NODE_TOKENS', json.dumps({'lab/a': NODE}))
    monkeypatch.delenv('CODONTRACE_API_TOKEN', raising=False)
    service._SWARMS.clear()
    server = make_server(IP, 0)
    t = threading.Thread(target=server.serve_forever, daemon=True); t.start()
    try:
        yield f'http://{IP}:{server.server_address[1]}', tmp_path, monkeypatch
    finally:
        server.shutdown(); server.server_close(); t.join(timeout=2); service._SWARMS.clear()


def req(url, body=None, token=None, method=None, raw=None):
    headers = {'Content-Type': 'application/json'}
    if token:
        headers['Authorization'] = 'Bearer ' + token
    data = raw if raw is not None else (None if body is None else json.dumps(body).encode())
    try:
        with urlopen(Request(url, data=data, headers=headers, method=method), timeout=20) as r:
            return r.status, r.read()
    except HTTPError as e:
        return e.code, e.read()
    except (URLError, ConnectionError) as e:  # dropped connection == server crash path
        return 599, str(e).encode()


SWARM_ACTIONS = sorted(service.STATELESS_ACTIONS | service.READ_ONLY_ACTIONS | service.WRITE_ACTIONS)


@pytest.mark.parametrize('action', SWARM_ACTIONS + ['no_such'])
@pytest.mark.parametrize('token', [None, NODE, 'wrong'])
def test_remote_swarm_actions_need_operator_token(remote, action, token):
    base, tmp, mp = remote
    args = {'swarm_id': 'lab'}
    if action == 'ingest':
        args['message'] = hello('lab', 'b')  # node token is for lab/a, not lab/b
    status, _ = req(base + '/api/swarm', {'action': action, 'args': args}, token)
    assert status == 403
    assert not (tmp / 'swarm').exists()


@pytest.mark.parametrize('token', [None, NODE])
def test_remote_get_routes_need_operator_token(remote, token):
    base, tmp, mp = remote
    for path in ('/api/swarm?swarm_id=lab', '/api/runs/run/simulation', '/api/science/tools'):
        assert req(base + path, token=token)[0] == 403
    status, _ = req(base + '/api/science/tools', {'tool': 'swarm_inspect', 'args': {'swarm_id': 'lab'}}, token)
    assert status == 403


def test_node_token_only_ingests_its_own_node(remote):
    base, tmp, mp = remote
    s, body = req(base + '/api/swarm', {'action': 'ingest', 'args': {'swarm_id': 'lab', 'message': hello('lab', 'a')}}, NODE)
    assert s == 200, body
    s, _ = req(base + '/api/swarm', {'action': 'ingest', 'args': {'swarm_id': 'lab', 'message': reading('lab', 'a', 1, 1, 1.0)}}, NODE)
    assert s == 400  # stale sample -> 4xx, not 5xx
    # message as a string carrying another node
    s, _ = req(base + '/api/swarm', {'action': 'ingest', 'args': {'swarm_id': 'lab', 'message': json.dumps(hello('lab', 'b'))}}, NODE)
    assert s == 403
    # smuggling: cross-swarm message under lab/a token
    s, _ = req(base + '/api/swarm', {'action': 'ingest', 'args': {'swarm_id': 'lab', 'message': hello('other', 'a')}}, NODE)
    assert s == 400
    for action in ('snapshot', 'command', 'status', 'journal_recover', 'plan'):
        s, _ = req(base + '/api/swarm', {'action': action, 'args': {'swarm_id': 'lab'}}, NODE)
        assert s == 403, action


MALFORMED = [
    b'[]', b'"x"', b'{"action": ["x"], "args": {}}', b'{"action": "snapshot", "args": []}',
    b'{"action": "snapshot", "args": {"swarm_id": 5}}', b'{"action": "snapshot", "args": {"swarm_id": "../x"}}',
    b'{"action": "ingest", "args": {"swarm_id": "lab", "message": ' + b'['*5000 + b']'*5000 + b'}}',
    b'{"action": "ingest", "args": {"swarm_id": "lab", "message": {"node_id": "a"}}}',
    b'{"action": "ingest", "args": {"swarm_id": "lab", "message": 7}}',
    b'{"action": "fusion", "args": {"swarm_id": "lab", "quantity": [], "unit": {}}}',
    b'{"action": "capsule_shadow", "args": {"swarm_id": "lab", "candidate": [], "baseline": 1, "values": 1, "references": 1, "training_id": 1, "evaluation_id": 1}}',
    b'{"action": "capsule_validate", "args": {"swarm_id": "lab", "candidate": {"alpha": 1e400}, "baseline": {}, "values": [], "references": []}}',
    b'{"action": "pipeline_fit", "args": {"swarm_id": "lab", "values": [1], "references": [1], "seed": -1}}',
    b'{"action": "pipeline_fit", "args": {"swarm_id": "lab", "values": [1,2], "references": [1,2], "seed": 1, "rounds": 100000000}}',
    b'{"action": "coevolve", "args": {"swarm_id": "lab", "references": [1,2,3], "seed": 1, "rounds": 100000000}}',
    b'{"action": "uncertainty_interval", "args": {"swarm_id": "lab", "predictions": [1], "references": [1,2], "estimate": "x", "training_id": "t", "calibration_id": "c", "model_id": "m"}}',
    b'{"action": "freshness_schedule", "args": {"swarm_id": "lab", "candidates": {"a": 1}, "byte_budget": -1}}',
    b'{"action": "freshness_plan", "args": {"swarm_id": "lab", "models": [], "quantity": "q", "unit": "u", "byte_budget": 1}}',
    b'{"action": "information_level", "args": {"swarm_id": "lab", "options": [{}], "byte_budget": 1, "maximum_mse": 1}}',
    b'{"action": "twin_fit", "args": {"swarm_id": "lab", "references": [1], "observations": ["a"]}}',
    b'{"action": "processing_contrast", "args": {"swarm_id": "lab", "frame": 1, "reference": 1}}',
    b'{"action": "fdc_decode", "args": {"swarm_id": "lab", "reading": {"channel": 99}, "variant": "FDC1004", "config_id": "c"}}',
    b'{"action": "configure_channel", "args": {"swarm_id": "lab", "key": "a/s", "changes": []}}',
    b'{"action": "journal_recover", "args": {"swarm_id": "lab", "full_replay": "yes"}}',
    b'{"action": "command", "args": {"swarm_id": "lab", "node_id": "a", "operation": "sample", "params": [], "timeout_ms": 1e300}}',
]


@pytest.mark.parametrize('raw', MALFORMED)
def test_malformed_input_is_4xx(remote, raw):
    base, tmp, mp = remote
    mp.setenv('CODONTRACE_API_TOKEN', OP)
    status, body = req(base + '/api/swarm', raw=raw, token=OP, method='POST')
    assert 400 <= status < 500, (status, body[:300])


@pytest.mark.parametrize('path', [
    '/api/runs/..%2F..%2Fetc/simulation', '/api/runs/../../etc/simulation', '/api/runs/a/b/simulation',
    '/api/runs/run/simulation?seed=abc', '/api/runs/run/simulation?cursor=-1', '/api/runs/run/simulation?limit=0',
    '/api/runs/run/simulation?limit=100000', '/api/runs/run/simulation?seed=' + '9' * 40,
    '/api/runs/%00/simulation', '/api/swarm?swarm_id=..%2Fx', '/api/swarm?swarm_id=' + 'a' * 500,
])
def test_simulation_and_swarm_get_reject_bad_input(remote, path):
    base, tmp, mp = remote
    mp.setenv('CODONTRACE_API_TOKEN', OP)
    (tmp / 'runs' / 'run' / 'simulation' / 'seed_1').mkdir(parents=True)
    status, body = req(base + path, token=OP)
    assert 400 <= status < 500, (status, body[:300])


def test_symlinked_frames_and_reports_are_rejected(remote):
    base, tmp, mp = remote
    mp.setenv('CODONTRACE_API_TOKEN', OP)
    secret = tmp / 'secret.json'; secret.write_text('{"schema": "genesis_simulation_frame_v1"}')
    seed = tmp / 'runs' / 'run' / 'simulation' / 'seed_1'; seed.mkdir(parents=True)
    os.symlink(secret, seed / 'frame_000000000000.json')
    assert req(base + '/api/runs/run/simulation', token=OP)[0] == 400
    os.unlink(seed / 'frame_000000000000.json')
    os.rmdir(seed); os.symlink(tmp, seed)
    assert req(base + '/api/runs/run/simulation', token=OP)[0] == 400
    (tmp / 'runs' / 'run' / 'swarm_decision_support.json').symlink_to(secret)
    status, body = req(base + '/api/science/tools', {'tool': 'swarm_decision_report', 'args': {'run_id': 'run'}}, OP)
    assert status == 400 and b'secret' not in body


def test_remote_with_token_works_and_reads_create_no_storage(remote):
    base, tmp, mp = remote
    mp.setenv('CODONTRACE_API_TOKEN', OP)
    for action in sorted(service.READ_ONLY_ACTIONS):
        args = {'swarm_id': 'ghost', 'quantity': 'signal', 'unit': 'arb', 'models': {}, 'byte_budget': 10}
        args = {k: v for k, v in args.items() if k == 'swarm_id' or action in ('fusion', 'freshness_plan') and k in ('quantity', 'unit') or action == 'freshness_plan'}
        s, body = req(base + '/api/swarm', {'action': action, 'args': args}, OP)
        assert s in (200, 400), (action, s, body)
    assert req(base + '/api/swarm?swarm_id=ghost', token=OP)[0] == 200
    assert not (tmp / 'swarm').exists()
    s, _ = req(base + '/api/swarm', {'action': 'ingest', 'args': {'swarm_id': 'ghost', 'message': hello('ghost', 'a')}}, OP)
    assert s == 200
    s, body = req(base + '/api/swarm?swarm_id=ghost', token=OP)
    data = json.loads(body)
    assert data['swarm_recorded'] is True and 'a' in data['result']['state']['nodes']


@pytest.mark.parametrize('path', ['/api/runs/launch', '/api/runs/action', '/api/scripts/upload', '/api/scripts/run',
                                  '/api/gates/run', '/api/runs/run/pause', '/api/runs/run/resume', '/api/chat',
                                  '/api/chat/endpoint', '/api/science/tools'])
@pytest.mark.parametrize('token', [None, NODE])
def test_b29_run_control_and_chat_still_need_token_remotely(remote, path, token):
    base, tmp, mp = remote
    status, _ = req(base + path, {'runId': 'run', 'action': 'delete', 'name': 'x.py', 'content': 'print(1)',
                                  'text': 'hi', 'tool': 'swarm_inspect', 'args': {'swarm_id': 'lab'}}, token)
    assert status == 403
    assert not (tmp / 'swarm').exists()
