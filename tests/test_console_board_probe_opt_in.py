"""The lab-board LLM probe is opt-in (CODONTRACE_BOARD_IP), off by default."""

from __future__ import annotations

from typing import Any

import pytest

from codontrace.console import chat


@pytest.fixture(autouse=True)
def _clean(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in ("CODONTRACE_BOARD_IP", "CODONTRACE_LLM_ENDPOINT", "CODONTRACE_LLM_URL"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setattr(chat, "_RUNTIME_ENDPOINT", None)
    monkeypatch.setattr(chat, "_STATUS_CACHE", {})


def test_default_probes_loopback_only() -> None:
    endpoints = chat._default_endpoints()
    assert endpoints == list(chat.DEFAULT_ENDPOINTS)
    assert all(e.startswith("http://127.0.0.1:") for e in endpoints)
    assert not any("10.225.130.20" in e for e in endpoints)


def test_check_llm_status_never_contacts_board_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    probed: list[str] = []

    def _probe(ep: str) -> dict[str, Any] | None:
        probed.append(ep)
        return None

    monkeypatch.setattr(chat, "_probe_single_endpoint", _probe)
    chat.check_llm_status()
    assert probed and all("127.0.0.1" in e for e in probed)


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("10.225.130.20", "http://10.225.130.20:8088/v1/chat/completions"),
        ("lab-board.local", "http://lab-board.local:8088/v1/chat/completions"),
        ("fd00::20", "http://[fd00::20]:8088/v1/chat/completions"),
    ],
)
def test_board_probe_when_opted_in(value: str, expected: str, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CODONTRACE_BOARD_IP", value)
    assert chat._default_endpoints()[1] == expected


@pytest.mark.parametrize("value", ["evil.example/x?", "a b", "http://x", "-bad", "x" * 300])
def test_invalid_board_value_is_ignored(value: str, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CODONTRACE_BOARD_IP", value)
    assert chat._default_endpoints() == list(chat.DEFAULT_ENDPOINTS)
