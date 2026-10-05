"""The preview console stays outside the evolution engine."""

from __future__ import annotations

import ast
import json
import sys
import threading
import urllib.error
import urllib.request
from pathlib import Path

from codontrace.console import server

REPO = Path(__file__).resolve().parents[1]
SERVER = REPO / "src" / "codontrace" / "console" / "server.py"


def test_server_source_does_not_import_the_engine() -> None:
    tree = ast.parse(SERVER.read_text(encoding="utf-8"))
    banned = {"codontrace.engine", "codontrace.genesis", "codontrace.rng", "engine", "genesis"}
    found: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            found.append(module)
            found.extend(alias.name for alias in node.names)
    assert not any(
        name in banned or name.startswith("codontrace.engine") or name.startswith("codontrace.genesis")
        for name in found
    )
    text = SERVER.read_text(encoding="utf-8")
    assert "exec(" not in text
    assert "eval(" not in text


def test_workers_stay_between_one_and_four() -> None:
    assert server.recommended_workers(0) == 1
    assert server.recommended_workers(1) == 1
    assert server.recommended_workers(3) == 3
    assert server.recommended_workers(16) == 4


def test_temperature_parse_matches_the_sensor_file() -> None:
    assert server.parse_temp_c("45000") == 45.0
    assert server.parse_temp_c("37.5") == 37.5
    assert server.parse_temp_c("nope") is None
    if sys.platform != "linux":
        assert server.read_temp_c() is None


def test_host_profile_is_a_measurement_not_a_claim() -> None:
    profile = server.host_profile()
    assert profile["source"] == "host"
    assert profile["platform"] == server.sys.platform
    workers = profile["recommendedWorkers"]
    assert isinstance(workers, int)
    assert 1 <= workers <= 4
    assert "red_queen_proved" not in profile
    assert isinstance(profile["packageVersion"], str)
    assert profile["packageVersion"]
    if profile["platform"] == "win32":
        assert profile["load1"] == 0.0
        assert profile["tempC"] is None


def test_preview_serves_page_and_host_and_rejects_traversal() -> None:
    assert (server.STATIC_ROOT / "index.html").is_file()
    httpd = server.make_server("127.0.0.1", 0)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    host, port = httpd.server_address[:2]
    base = f"http://{host}:{port}"
    try:
        with urllib.request.urlopen(base + "/", timeout=5) as page:
            body = page.read()
            assert page.status == 200
            assert b"CodonTrace Genesis Console" in body or b'id="root"' in body or b"root" in body
        with urllib.request.urlopen(base + "/api/host", timeout=5) as host_page:
            payload = json.loads(host_page.read().decode("utf-8"))
        assert payload["source"] == "host"
        assert payload["recommendedWorkers"] <= 4
        try:
            urllib.request.urlopen(base + "/%2e%2e/%2e%2e/pyproject.toml", timeout=5)
        except urllib.error.HTTPError as exc:
            assert exc.code == 404
        else:
            raise AssertionError("path traversal was served")
    finally:
        httpd.shutdown()
        httpd.server_close()
        thread.join(timeout=5)
