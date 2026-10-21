"""Console authorization treats only loopback peers as local.

Regression for 744f6cf, where ``_from_this_machine`` returned True for any
``ipaddress`` ``is_private`` address, so a LAN client with no token was
authorized for /api/release/update and for operator routes.
"""

from __future__ import annotations

import pytest

from codontrace.console import server

LOOPBACK = ["127.0.0.1", "127.0.0.2", "::1", "::ffff:127.0.0.1", "localhost"]
NOT_THIS_MACHINE = [
    "192.168.1.100",
    "10.0.0.5",
    "172.16.4.2",
    "169.254.10.10",
    "100.64.0.1",
    "fd00::1",
    "fe80::1%eth0",
    "::ffff:192.168.1.100",
    "8.8.8.8",
    "0.0.0.0",
    "",
    "not-an-ip",
]


@pytest.mark.parametrize("address", LOOPBACK)
def test_loopback_is_this_machine(address: str) -> None:
    assert server._from_this_machine(address) is True


@pytest.mark.parametrize("address", NOT_THIS_MACHINE)
def test_private_and_public_peers_are_not_this_machine(address: str) -> None:
    assert server._from_this_machine(address) is False


def _handler(ip: str, headers: dict[str, str] | None = None) -> server.ConsoleHandler:
    handler = server.ConsoleHandler.__new__(server.ConsoleHandler)
    handler.client_address = (ip, 40000)
    handler.headers = headers or {}  # type: ignore[assignment]
    return handler


@pytest.mark.parametrize("address", [a for a in NOT_THIS_MACHINE if a])
def test_remote_update_without_token_is_forbidden(
    address: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("CODONTRACE_UPDATE_TOKEN", raising=False)
    ok, status, _ = _handler(address)._check_update_authorization({})
    assert (ok, status) == (False, 403)


def test_loopback_update_without_token_is_allowed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("CODONTRACE_UPDATE_TOKEN", raising=False)
    ok, status, _ = _handler("127.0.0.1")._check_update_authorization({})
    assert (ok, status) == (True, 200)


def test_loopback_behind_proxy_header_is_remote(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("CODONTRACE_UPDATE_TOKEN", raising=False)
    ok, status, _ = _handler(
        "127.0.0.1", {"X-Forwarded-For": "192.168.1.100"}
    )._check_update_authorization({})
    assert (ok, status) == (False, 403)


def test_lan_origin_is_not_allowed_by_address_class() -> None:
    handler = _handler(
        "127.0.0.1", {"Origin": "http://192.168.1.50:8765", "Host": "127.0.0.1:8765"}
    )
    handler.server = type("S", (), {"server_address": ("127.0.0.1", 8765)})()  # type: ignore[assignment]
    assert handler._is_origin_allowed() is False


def _trust(monkeypatch: pytest.MonkeyPatch, value: str) -> None:
    monkeypatch.setattr(server, "_TRUSTED", server.parse_trusted_networks(value))


def test_private_peer_is_remote_without_opt_in() -> None:
    assert server._trusted_networks() == ()
    assert server._from_this_machine("10.225.130.20") is False


@pytest.mark.parametrize("address", ["::ffff:7f00:1", "::FFFF:7F00:2", "::ffff:127.0.0.1"])
def test_ipv4_mapped_loopback_in_any_spelling_is_loopback(address: str) -> None:
    assert server._is_loopback(address) is True
    assert server._from_this_machine(address) is True


def test_ipv4_mapped_non_loopback_hex_is_remote() -> None:
    assert server._from_this_machine("::ffff:c0a8:164") is False  # 192.168.1.100


def test_trusted_networks_opt_in_is_explicit_and_narrow(monkeypatch: pytest.MonkeyPatch) -> None:
    _trust(monkeypatch, "10.225.130.0/24, 192.168.5.7")
    assert server._from_this_machine("10.225.130.20") is True
    assert server._from_this_machine("192.168.5.7") is True  # bare address = one host
    assert server._from_this_machine("192.168.5.8") is False
    assert server._from_this_machine("10.225.131.20") is False
    monkeypatch.delenv("CODONTRACE_UPDATE_TOKEN", raising=False)
    ok, status, _ = _handler("10.225.130.20")._check_update_authorization({})
    assert (ok, status) == (True, 200)
    ok, status, _ = _handler(
        "10.225.130.20", {"X-Forwarded-For": "1.2.3.4"}
    )._check_update_authorization({})
    assert (ok, status) == (False, 403)


@pytest.mark.parametrize("entry", ["garbage", "10.0.0.0/33", "10.225.130.5/24", "172.30.0.5/16", "fd00::1/64"])
def test_invalid_or_host_bit_entries_are_errors(entry: str) -> None:
    with pytest.raises(ValueError, match="invalid entry"):
        server.parse_trusted_networks(f"10.225.130.0/24,{entry}")


@pytest.mark.parametrize(
    "networks", ["0.0.0.0/0", "::/0", "10.0.0.0/8", "172.16.0.0/12", "192.0.0.0/15", "fd00::/8", "2001:db8::/47"]
)
def test_over_broad_trusted_networks_are_errors(networks: str) -> None:
    with pytest.raises(ValueError, match="broader than"):
        server.parse_trusted_networks(networks)


def test_empty_items_mean_loopback_only() -> None:
    assert server.parse_trusted_networks(" , ,,") == ()


def test_prefix_threshold_boundary(monkeypatch: pytest.MonkeyPatch) -> None:
    _trust(monkeypatch, "192.168.0.0/16,2001:db8:1::/48")
    assert server._from_this_machine("192.168.77.1") is True
    assert server._from_this_machine("2001:db8:1::5") is True
    assert server._from_this_machine("2001:db8:2::5") is False


def test_env_is_parsed_once_at_startup(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    monkeypatch.setattr(server, "_TRUSTED", ())
    monkeypatch.setenv(server.TRUSTED_NETWORKS_ENV, "10.225.130.0/24")
    srv = server.make_server("127.0.0.1", 0)
    try:
        assert "10.225.130.0/24" in capsys.readouterr().err
        monkeypatch.setenv(server.TRUSTED_NETWORKS_ENV, "192.168.9.0/24")  # changed at runtime
        assert server._from_this_machine("10.225.130.20") is True
        assert server._from_this_machine("192.168.9.1") is False
    finally:
        srv.server_close()


def test_invalid_env_refuses_to_start(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(server, "_TRUSTED", ())
    monkeypatch.setenv(server.TRUSTED_NETWORKS_ENV, "0.0.0.0/0")
    with pytest.raises(ValueError, match="broader than"):
        server.make_server("127.0.0.1", 0)
    assert server._trusted_networks() == ()


def test_trusted_network_is_never_an_allowed_origin(monkeypatch: pytest.MonkeyPatch) -> None:
    _trust(monkeypatch, "10.225.130.0/24")
    assert server._from_this_machine("10.225.130.20") is True
    handler = _handler(
        "10.225.130.20", {"Origin": "http://10.225.130.50:8765", "Host": "127.0.0.1:8765"}
    )
    handler.server = type("S", (), {"server_address": ("127.0.0.1", 8765)})()  # type: ignore[assignment]
    assert handler._is_origin_allowed() is False


def _no_peer_handler(monkeypatch: pytest.MonkeyPatch, path: str, body: bytes) -> tuple[server.ConsoleHandler, list[int]]:
    import io
    handler = server.ConsoleHandler.__new__(server.ConsoleHandler)
    handler.client_address = None  # type: ignore[assignment]
    handler.path = path
    handler.headers = {"Content-Length": str(len(body))}  # type: ignore[assignment]
    handler.rfile = io.BytesIO(body)
    sent: list[int] = []
    monkeypatch.setattr(handler, "_send", lambda status, *a, **k: sent.append(status))
    monkeypatch.setattr(handler, "_is_origin_allowed", lambda: True)
    return handler, sent


def test_inference_without_peer_address_is_403(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("CODONTRACE_API_TOKEN", raising=False)
    handler, sent = _no_peer_handler(monkeypatch, "/api/runs/action", b"")
    assert handler._authorize_inference() is False
    assert sent == [403]


def test_providers_without_peer_address_is_403(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("CODONTRACE_SETTINGS_TOKEN", raising=False)
    handler, sent = _no_peer_handler(monkeypatch, "/api/providers", b'{"provider": "openai"}')
    handler.do_POST()
    assert sent == [403]
