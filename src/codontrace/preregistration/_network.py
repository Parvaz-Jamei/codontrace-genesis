"""Opt-in gate and a minimal HTTP transport (stdlib only)."""

from __future__ import annotations

import os
import urllib.request
from collections.abc import Callable, Mapping
from dataclasses import dataclass

from codontrace.errors import ConfigurationError


@dataclass(frozen=True)
class HttpResponse:
    status: int
    body: bytes
    headers: Mapping[str, str]


Transport = Callable[[str, str, bytes | None, Mapping[str, str]], HttpResponse]


def network_allowed(allow_network: bool) -> bool:
    return allow_network or os.environ.get("CODONTRACE_ALLOW_NETWORK") == "1"


def require_network(allow_network: bool, what: str) -> None:
    if not network_allowed(allow_network):
        raise ConfigurationError(
            f"{what} needs the network; pass allow_network=True or set CODONTRACE_ALLOW_NETWORK=1"
        )


def urllib_transport(
    method: str, url: str, body: bytes | None, headers: Mapping[str, str], timeout: float = 30.0
) -> HttpResponse:
    if not url.startswith("https://"):
        raise ConfigurationError("only https URLs are allowed")
    req = urllib.request.Request(url, data=body, method=method, headers=dict(headers))
    with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310 - https enforced above
        return HttpResponse(resp.status, resp.read(), dict(resp.headers.items()))
