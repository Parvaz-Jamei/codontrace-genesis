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


def test_preview_serves_page_and_host_and_rejects_traversal(monkeypatch) -> None:
    monkeypatch.setenv("CODONTRACE_LLM_ENDPOINT", "http://127.0.0.1:59999/v1/chat/completions")
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


def test_console_serves_chat_runs_scripts_and_gates(monkeypatch) -> None:
    monkeypatch.setenv("CODONTRACE_LLM_ENDPOINT", "http://127.0.0.1:59999/v1/chat/completions")
    httpd = server.make_server("127.0.0.1", 0)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    host, port = httpd.server_address[:2]
    base = f"http://{host}:{port}"
    try:
        with urllib.request.urlopen(base + "/api/chat/status", timeout=5) as r:
            assert r.status == 200
            data = json.loads(r.read().decode("utf-8"))
            assert "mounted" in data
        with urllib.request.urlopen(base + "/api/runs", timeout=5) as r:
            assert r.status == 200
            runs = json.loads(r.read().decode("utf-8"))
            assert isinstance(runs, list)
        with urllib.request.urlopen(base + "/api/scripts", timeout=5) as r:
            assert r.status == 200
            scripts = json.loads(r.read().decode("utf-8"))
            assert isinstance(scripts, list)
        with urllib.request.urlopen(base + "/api/gates", timeout=5) as r:
            assert r.status == 200
            gates = json.loads(r.read().decode("utf-8"))
            assert isinstance(gates, list)
        chat_req = urllib.request.Request(
            base + "/api/chat",
            data=json.dumps({"text": "test", "lang": "en"}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(chat_req, timeout=35) as r:
            assert r.status == 200
            resp = json.loads(r.read().decode("utf-8"))
            assert "reply" in resp
        with urllib.request.urlopen(base + "/api/models", timeout=5) as r:
            assert r.status == 200
            models = json.loads(r.read().decode("utf-8"))
            assert isinstance(models, list)
        ep_req = urllib.request.Request(
            base + "/api/chat/endpoint",
            data=json.dumps({"endpoint": "http://127.0.0.1:8088/v1/chat/completions"}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(ep_req, timeout=5) as r:
            assert r.status == 200
            ep_resp = json.loads(r.read().decode("utf-8"))
            assert "mounted" in ep_resp
        action_req = urllib.request.Request(
            base + "/api/runs/action",
            data=json.dumps({"runId": "nonexistent_run", "action": "stop"}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(action_req, timeout=5) as r:
            assert r.status == 200
            act_resp = json.loads(r.read().decode("utf-8"))
            assert act_resp["ok"] is False  # nonexistent run
    finally:
        httpd.shutdown()
        httpd.server_close()
        thread.join(timeout=5)


def test_console_phase1_security_origin_and_cors(monkeypatch) -> None:
    monkeypatch.setenv("CODONTRACE_LLM_ENDPOINT", "http://127.0.0.1:59999/v1/chat/completions")
    httpd = server.make_server("127.0.0.1", 0)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    host, port = httpd.server_address[:2]
    base = f"http://{host}:{port}"
    try:
        # Untrusted Origin POST must receive 403 Forbidden
        evil_req = urllib.request.Request(
            base + "/api/chat",
            data=json.dumps({"text": "hello"}).encode("utf-8"),
            headers={"Content-Type": "application/json", "Origin": "https://untrusted.evil.com"},
            method="POST",
        )
        try:
            urllib.request.urlopen(evil_req, timeout=5)
            raise AssertionError("untrusted origin was allowed for mutation")
        except urllib.error.HTTPError as exc:
            assert exc.code == 403

        # Untrusted Origin in preflight OPTIONS must receive 403
        preflight_evil = urllib.request.Request(
            base + "/api/runs/action",
            headers={"Origin": "https://untrusted.evil.com"},
            method="OPTIONS",
        )
        try:
            urllib.request.urlopen(preflight_evil, timeout=5)
            raise AssertionError("untrusted origin was allowed in preflight")
        except urllib.error.HTTPError as exc:
            assert exc.code == 403

        # Allowed Origin receives matching Access-Control-Allow-Origin
        trusted_req = urllib.request.Request(
            base + "/api/chat",
            data=json.dumps({"text": "hello"}).encode("utf-8"),
            headers={"Content-Type": "application/json", "Origin": f"http://127.0.0.1:{port}"},
            method="POST",
        )
        with urllib.request.urlopen(trusted_req, timeout=35) as r:
            assert r.status == 200
            assert r.headers.get("Access-Control-Allow-Origin") == f"http://127.0.0.1:{port}"
    finally:
        httpd.shutdown()
        httpd.server_close()
        thread.join(timeout=5)


def test_console_phase1_traversal_and_containment(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("CODONTRACE_RUNS_DIR", str(tmp_path / "runs"))
    monkeypatch.setenv("CODONTRACE_SCRIPTS_DIR", str(tmp_path / "scripts"))
    httpd = server.make_server("127.0.0.1", 0)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    host, port = httpd.server_address[:2]
    base = f"http://{host}:{port}"
    try:
        # Path traversal in run details
        for bad_id in ("../sibling", "..%2Fsibling", "something/../../etc", "bad\\id"):
            req = urllib.request.Request(base + f"/api/runs/{bad_id}")
            try:
                urllib.request.urlopen(req, timeout=5)
                raise AssertionError(f"traversal allowed: {bad_id}")
            except urllib.error.HTTPError as exc:
                assert exc.code in (400, 404)

        # Path traversal in run zip
        req_zip = urllib.request.Request(base + "/api/runs/..%2Fsibling/zip")
        try:
            urllib.request.urlopen(req_zip, timeout=5)
            raise AssertionError("traversal allowed in zip")
        except urllib.error.HTTPError as exc:
            assert exc.code in (400, 404)

        # Path traversal in action
        act_req = urllib.request.Request(
            base + "/api/runs/action",
            data=json.dumps({"runId": "../escaped_dir", "action": "stop"}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            urllib.request.urlopen(act_req, timeout=5)
            raise AssertionError("traversal allowed in action")
        except urllib.error.HTTPError as exc:
            assert exc.code == 400

        # Path traversal in script upload
        upload_req = urllib.request.Request(
            base + "/api/scripts/upload",
            data=json.dumps({"name": "../escape.py", "content": "print(1)"}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            urllib.request.urlopen(upload_req, timeout=5)
            raise AssertionError("traversal allowed in script upload")
        except urllib.error.HTTPError as exc:
            assert exc.code == 400
    finally:
        httpd.shutdown()
        httpd.server_close()
        thread.join(timeout=5)


def test_console_phase1_validation_and_collision(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("CODONTRACE_RUNS_DIR", str(tmp_path / "runs"))
    httpd = server.make_server("127.0.0.1", 0)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    host, port = httpd.server_address[:2]
    base = f"http://{host}:{port}"
    try:
        # Sending JSON array instead of dict returns 400 without crashing (fixing E07)
        arr_req = urllib.request.Request(
            base + "/api/chat",
            data=b"[]",
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            urllib.request.urlopen(arr_req, timeout=5)
            raise AssertionError("JSON array accepted")
        except urllib.error.HTTPError as exc:
            assert exc.code == 400
            err_data = json.loads(exc.read().decode("utf-8"))
            assert "Expected JSON object" in err_data["error"]

        # Invalid generations / workers rejected with 400
        bad_launch = urllib.request.Request(
            base + "/api/runs/launch",
            data=json.dumps({"generations": -5, "workers": 2}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            urllib.request.urlopen(bad_launch, timeout=5)
            raise AssertionError("invalid generations accepted")
        except urllib.error.HTTPError as exc:
            assert exc.code == 400

        # Script upload exceeding 200 KB rejected with 413
        oversized = "a = 1\n" * 40000  # > 200 KB
        big_upload = urllib.request.Request(
            base + "/api/scripts/upload",
            data=json.dumps({"name": "big.py", "content": oversized}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            urllib.request.urlopen(big_upload, timeout=5)
            raise AssertionError("oversized script accepted")
        except urllib.error.HTTPError as exc:
            assert exc.code in (400, 413)

        # Zero collision: two simultaneous launches with identical title get distinct IDs
        launch1 = urllib.request.Request(
            base + "/api/runs/launch",
            data=json.dumps({"title": "identical_title", "generations": 1, "workers": 1}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        launch2 = urllib.request.Request(
            base + "/api/runs/launch",
            data=json.dumps({"title": "identical_title", "generations": 1, "workers": 1}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(launch1, timeout=5) as r1, urllib.request.urlopen(launch2, timeout=5) as r2:
            assert r1.status == 200
            assert r2.status == 200
            d1 = json.loads(r1.read().decode("utf-8"))
            d2 = json.loads(r2.read().decode("utf-8"))
            assert d1["runId"] != d2["runId"]
            assert d1["ok"] is True and d2["ok"] is True
    finally:
        httpd.shutdown()
        httpd.server_close()
        thread.join(timeout=5)


def test_console_phase1_process_safety_and_atomic_writes(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("CODONTRACE_RUNS_DIR", str(tmp_path / "runs"))
    from codontrace.console import runs

    # Atomic write verification
    json_path = tmp_path / "atomic" / "status.json"
    data = {"status": "TEST", "val": 42}
    runs.write_atomic_json(json_path, data)
    assert json_path.is_file()
    assert json.loads(json_path.read_text(encoding="utf-8")) == data

    # Attempting to delete an active run returns 409 Conflict
    class FakeProc:
        pid = 99999
        def poll(self):
            return None  # Still running

    fake_run_dir = tmp_path / "runs" / "run_fake_active"
    fake_run_dir.mkdir(parents=True)
    (fake_run_dir / "status.json").write_text(json.dumps({"status": "RUNNING"}), encoding="utf-8")

    with runs._RUN_LOCK:
        runs._RUN_PROCESSES["run_fake_active"] = FakeProc()  # type: ignore[assignment]

    try:
        res = runs.manage_run_action("run_fake_active", "delete")
        assert res["ok"] is False
        assert res.get("status_code") == 409
        assert "actively running" in res.get("error", "").lower()
        assert fake_run_dir.is_dir()  # Must not be deleted!
    finally:
        with runs._RUN_LOCK:
            runs._RUN_PROCESSES.pop("run_fake_active", None)



