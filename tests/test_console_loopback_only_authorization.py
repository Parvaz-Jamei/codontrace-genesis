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


def test_private_peer_is_remote_without_opt_in(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("CODONTRACE_CONSOLE_TRUSTED_NETWORKS", raising=False)
    assert server._from_this_machine("10.225.130.20") is False


def test_trusted_networks_opt_in_is_explicit_and_narrow(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CODONTRACE_CONSOLE_TRUSTED_NETWORKS", "10.225.130.0/24, not-a-net")
    assert server._from_this_machine("10.225.130.20") is True
    assert server._from_this_machine("10.225.131.20") is False
    assert server._from_this_machine("192.168.1.100") is False
    monkeypatch.delenv("CODONTRACE_UPDATE_TOKEN", raising=False)
    ok, status, _ = _handler("10.225.130.20")._check_update_authorization({})
    assert (ok, status) == (True, 200)
    ok, status, _ = _handler(
        "10.225.130.20", {"X-Forwarded-For": "1.2.3.4"}
    )._check_update_authorization({})
    assert (ok, status) == (False, 403)


def test_invalid_trusted_networks_never_widen(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CODONTRACE_CONSOLE_TRUSTED_NETWORKS", "garbage,,10.0.0.0/33")
    assert server._from_this_machine("10.0.0.5") is False


@pytest.mark.parametrize(
    "networks", ["0.0.0.0/0", "::/0", "10.0.0.0/8", "172.16.0.0/12", "192.0.0.0/15", "fd00::/8", "2001:db8::/47"]
)
def test_over_broad_trusted_networks_are_ignored(
    networks: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("CODONTRACE_CONSOLE_TRUSTED_NETWORKS", networks)
    assert server._trusted_networks() == []
    for peer in ("10.1.2.3", "172.16.0.9", "192.0.1.1", "8.8.8.8", "fd00::1", "2001:db8::1"):
        assert server._from_this_machine(peer) is False


def test_prefix_threshold_boundary(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CODONTRACE_CONSOLE_TRUSTED_NETWORKS", "192.168.0.0/16,2001:db8:1::/48")
    assert server._from_this_machine("192.168.77.1") is True
    assert server._from_this_machine("2001:db8:1::5") is True
    assert server._from_this_machine("2001:db8:2::5") is False


def test_trusted_network_is_never_an_allowed_origin(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CODONTRACE_CONSOLE_TRUSTED_NETWORKS", "10.225.130.0/24")
    assert server._from_this_machine("10.225.130.20") is True
    handler = _handler(
        "10.225.130.20", {"Origin": "http://10.225.130.50:8765", "Host": "127.0.0.1:8765"}
    )
    handler.server = type("S", (), {"server_address": ("127.0.0.1", 8765)})()  # type: ignore[assignment]
    assert handler._is_origin_allowed() is False
