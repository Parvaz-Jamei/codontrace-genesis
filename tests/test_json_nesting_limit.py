"""Deeply nested JSON is a 4xx, never a RecursionError or a dropped socket.

On Python 3.11 ``json.loads(b'[' * 5000 + b']' * 5000)`` raised
RecursionError, which _parse_json_dict did not catch, so the console closed
the connection (tests/test_swarm_http_security.py::test_malformed_input_is_4xx).
"""

from __future__ import annotations

import pytest

from codontrace.console import server
from codontrace.contracts.wire_validation import MAX_JSON_DEPTH, json_depth_within
from codontrace.swarm.protocol import decode


def _nested(depth: int) -> bytes:
    return b"[" * depth + b"]" * depth


def test_depth_scan_boundary() -> None:
    assert json_depth_within(_nested(MAX_JSON_DEPTH))
    assert not json_depth_within(_nested(MAX_JSON_DEPTH + 1))
    assert json_depth_within(b'{"a": {"b": [1, 2, {"c": []}]}}', limit=5)
    assert not json_depth_within(b'{"a": {"b": [1, 2, {"c": []}]}}', limit=4)


def test_brackets_inside_strings_do_not_count() -> None:
    text = '{"s": "' + "[" * 500 + '\\"' + "{" * 500 + '"}'
    assert json_depth_within(text, limit=1)
    assert json_depth_within(text.encode(), limit=1)


@pytest.mark.parametrize("depth", [MAX_JSON_DEPTH + 1, 5000, 200_000])
def test_console_parser_rejects_deep_body(depth: int) -> None:
    body = b'{"m": ' + _nested(depth) + b"}"
    obj, err = server._parse_json_dict(body)
    assert obj is None
    assert err is not None and "nesting" in err


def test_console_parser_accepts_ordinary_body() -> None:
    assert server._parse_json_dict(b'{"action": "snapshot", "args": {"swarm_id": "lab"}}') == (
        {"action": "snapshot", "args": {"swarm_id": "lab"}},
        None,
    )


def test_console_parser_recursionerror_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(server, "json_depth_within", lambda raw: True)

    def _boom(*_a: object, **_k: object) -> object:
        raise RecursionError("maximum recursion depth exceeded")

    monkeypatch.setattr(server.json, "loads", _boom)
    obj, err = server._parse_json_dict(b'{"a": 1}')
    assert obj is None and err == "Invalid JSON: nesting too deep"


@pytest.mark.parametrize("depth", [MAX_JSON_DEPTH + 1, 5000])
def test_swarm_decode_rejects_deep_text(depth: int) -> None:
    raw = b'{"schema": "genesis_swarm_v2", "payload": ' + _nested(depth) + b"}"
    with pytest.raises(ValueError, match="nesting"):
        decode(raw)


def test_swarm_decode_rejects_deep_mapping() -> None:
    deep: list[object] = []
    cur = deep
    for _ in range(100_000):
        nxt: list[object] = []
        cur.append(nxt)
        cur = nxt
    with pytest.raises(ValueError, match="nesting"):
        decode({"schema": "genesis_swarm_v2", "payload": deep})


@pytest.mark.parametrize("address", [None, 0, b"127.0.0.1", ("127.0.0.1",)])
def test_non_string_peer_is_not_this_machine(address: object) -> None:
    assert server._from_this_machine(address) is False  # type: ignore[arg-type]


def test_update_without_client_address_is_forbidden(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("CODONTRACE_UPDATE_TOKEN", raising=False)
    handler = server.ConsoleHandler.__new__(server.ConsoleHandler)
    handler.client_address = None  # type: ignore[assignment]
    handler.headers = {}  # type: ignore[assignment]
    ok, status, _ = handler._check_update_authorization({})
    assert (ok, status) == (False, 403)


def test_depth_scan_limit_minus_one_and_mixed_boundary() -> None:
    assert json_depth_within(_nested(MAX_JSON_DEPTH - 1))
    mixed = b'{"a": ' * (MAX_JSON_DEPTH - 1) + b"[]" + b"}" * (MAX_JSON_DEPTH - 1)
    assert json_depth_within(mixed)
    assert not json_depth_within(b"[" + mixed + b"]")


@pytest.mark.parametrize("depth", [MAX_JSON_DEPTH - 1, MAX_JSON_DEPTH])
def test_console_parser_accepts_up_to_the_limit(depth: int) -> None:
    body = b'{"m": ' + _nested(depth - 1) + b"}"  # object + inner arrays = depth
    obj, err = server._parse_json_dict(body)
    assert err is None and isinstance(obj, dict)


def test_loads_bounded_boundary_and_error_type() -> None:
    import json

    from codontrace.contracts.wire_validation import loads_bounded

    assert loads_bounded(_nested(MAX_JSON_DEPTH - 1)) is not None
    assert loads_bounded(_nested(MAX_JSON_DEPTH).decode()) is not None
    for raw in (_nested(MAX_JSON_DEPTH + 1), _nested(100_000).decode()):
        with pytest.raises(json.JSONDecodeError, match="nesting deeper than 64"):
            loads_bounded(raw)
    with pytest.raises(TypeError):
        loads_bounded(5)  # type: ignore[arg-type]


def test_network_json_callers_reject_deep_responses(monkeypatch: pytest.MonkeyPatch) -> None:
    import io

    from codontrace.console import providers, release

    deep = _nested(100_000)

    class _Resp(io.BytesIO):
        status = 200

        def __enter__(self) -> _Resp:
            return self

        def __exit__(self, *_a: object) -> None:
            return None

    monkeypatch.setattr(release.urllib.request, "urlopen", lambda *a, **k: _Resp(deep))
    tag, url, err = release._latest_release()
    assert (tag, url) == (None, None) and err is not None and "nesting" in err

    monkeypatch.setattr(providers, "_credential", lambda provider: ("k", True, None))
    monkeypatch.setattr(providers, "_CACHE", {})
    monkeypatch.setattr(providers, "open_request", lambda *a, **k: _Resp(deep))
    name = next(iter(providers.PROVIDERS))
    providers.refresh(name)  # must not raise RecursionError
    assert providers._CACHE[name]["error"] == "provider_catalog_invalid"
    assert providers._CACHE[name]["models"] == []


@pytest.mark.parametrize("depth, rejected", [(MAX_JSON_DEPTH - 1, False), (MAX_JSON_DEPTH, False), (MAX_JSON_DEPTH + 1, True)])
def test_http_nesting_boundary(depth: int, rejected: bool) -> None:
    import http.client
    import json
    import threading

    srv = server.make_server("127.0.0.1", 0)
    thread = threading.Thread(target=srv.serve_forever, daemon=True)
    thread.start()
    try:
        body = b'{"action": "snapshot", "args": ' + b'{"a": ' * (depth - 2) + b"{}" + b"}" * (depth - 2) + b"}"
        assert json_depth_within(body, depth) and not json_depth_within(body, depth - 1)
        conn = http.client.HTTPConnection("127.0.0.1", srv.server_address[1], timeout=30)
        conn.request("POST", "/api/swarm", body=body, headers={"Content-Type": "application/json"})
        resp = conn.getresponse()
        payload = json.loads(resp.read() or b"{}")
        conn.close()
        assert resp.status < 500
        nesting = "nesting" in str(payload.get("error", ""))
        assert nesting is rejected
        if rejected:
            assert resp.status == 400
    finally:
        srv.shutdown()
        srv.server_close()
