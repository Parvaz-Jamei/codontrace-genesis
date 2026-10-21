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
