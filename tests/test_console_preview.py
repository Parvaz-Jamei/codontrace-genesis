"""The preview console stays outside the evolution engine."""

from __future__ import annotations

import ast
import json
import subprocess
import sys
import threading
import urllib.error
import urllib.request
from pathlib import Path

from codontrace.console import release, server

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
    release_text = (REPO / "src" / "codontrace" / "console" / "release.py").read_text(encoding="utf-8")
    assert "git push" not in release_text
    assert "--hard" not in release_text
    assert "--ff-only" in release_text


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
            assert host_page.headers.get("Access-Control-Allow-Origin") == "*"
        assert payload["source"] == "host"
        assert payload["recommendedWorkers"] <= 4
        with urllib.request.urlopen(base + "/api/release", timeout=5) as release_page:
            info = json.loads(release_page.read().decode("utf-8"))
        assert info["currentVersion"]
        assert info["updateAvailable"] in {True, False}
        assert "red_queen_proved" not in info
        preflight = urllib.request.Request(base + "/api/host", method="OPTIONS")
        with urllib.request.urlopen(preflight, timeout=5) as options:
            assert options.status == 204
            assert options.headers.get("Access-Control-Allow-Origin") == "*"
        with urllib.request.urlopen(base + "/gates", timeout=5) as gate_page:
            gate_body = gate_page.read()
            assert gate_page.status == 200
            assert b'id="root"' in gate_body or b"root" in gate_body
        try:
            urllib.request.urlopen(base + "/assets/does-not-exist.js", timeout=5)
        except urllib.error.HTTPError as exc:
            assert exc.code == 404
        else:
            raise AssertionError("a missing script was served as the page")
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


def test_cpu_zone_is_preferred_over_the_gpu_zone(tmp_path: Path) -> None:
    gpu = tmp_path / "thermal_zone0"
    cpu = tmp_path / "thermal_zone2"
    gpu.mkdir()
    cpu.mkdir()
    (gpu / "type").write_text("gpu-thermal\n", encoding="utf-8")
    (gpu / "temp").write_text("30000\n", encoding="utf-8")
    (cpu / "type").write_text("cpu-thermal\n", encoding="utf-8")
    (cpu / "temp").write_text("45000\n", encoding="utf-8")
    assert server.cpu_temp_c(tmp_path) == 45.0


def test_zone_zero_remains_when_no_cpu_zone_is_named(tmp_path: Path) -> None:
    zone = tmp_path / "thermal_zone0"
    zone.mkdir()
    (zone / "type").write_text("soc-thermal\n", encoding="utf-8")
    (zone / "temp").write_text("37000\n", encoding="utf-8")
    assert server.cpu_temp_c(tmp_path) == 37.0


def test_release_ordering_knows_a_newer_beta() -> None:
    assert release.newer_release("v0.3.0b17", "0.3.0b16")
    assert not release.newer_release("0.3.0b16", "0.3.0b17")
    assert not release.newer_release("0.3.0b16", "v0.3.0b16")
    assert release.newer_release("0.3.0", "0.3.0b17")
    assert release.version_key("nope") is None


def _git(cwd: Path, *args: str) -> None:
    subprocess.check_call(
        ["git", "-c", "user.email=console@example.com", "-c", "user.name=console", *args],
        cwd=cwd,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def test_dirty_checkout_is_left_untouched(tmp_path: Path) -> None:
    origin = tmp_path / "origin"
    origin.mkdir()
    _git(origin, "init", "-b", "main")
    (origin / "pyproject.toml").write_text('name = "codontrace"\nversion = "0.3.0b17"\n', encoding="utf-8")
    _git(origin, "add", "pyproject.toml")
    _git(origin, "commit", "-m", "base")
    clone = tmp_path / "clone"
    subprocess.check_call(
        ["git", "clone", str(origin), str(clone)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )
    (clone / "local.txt").write_text("keep\n", encoding="utf-8")
    ok, message = release.pull_checkout(clone)
    assert ok is False
    assert "untouched" in message
    assert (clone / "local.txt").read_text(encoding="utf-8") == "keep\n"


def test_fast_forward_updates_a_clean_checkout(tmp_path: Path) -> None:
    origin = tmp_path / "origin"
    origin.mkdir()
    _git(origin, "init", "-b", "main")
    (origin / "pyproject.toml").write_text('name = "codontrace"\nversion = "0.3.0b17"\n', encoding="utf-8")
    _git(origin, "add", "pyproject.toml")
    _git(origin, "commit", "-m", "base")
    clone = tmp_path / "clone"
    subprocess.check_call(
        ["git", "clone", str(origin), str(clone)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )
    (origin / "note.txt").write_text("next\n", encoding="utf-8")
    _git(origin, "add", "note.txt")
    _git(origin, "commit", "-m", "next")
    ok, _message = release.pull_checkout(clone)
    assert ok is True
    assert (clone / "note.txt").read_text(encoding="utf-8") == "next\n"
