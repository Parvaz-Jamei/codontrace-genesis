"""Regression test suite for Coder 3 issues: R04, R05, R15, R17, R18, R19.

Verifies:
- R04: Fail-closed error handling when execution.json is corrupted or exit=0 with failures.
- R05: ZIP export traversal via symlinks strictly blocked and audited in omittedFiles.
- R15: Release ZIP builder prunes .git, node_modules, output, simulation_runs, and cache dirs.
- R17: Cooperative pause mechanism uses PAUSE marker rather than STOP and synchronizes workers.
- R18: Remote updates on /api/release/update require independent authorization token guards.
- R19: Chat turn falls back gracefully to deterministic domain analyst when LLM is offline.
"""

from __future__ import annotations

import json
import zipfile
from pathlib import Path

import pytest

from codontrace.console import chat, runs, server
from tools import build_clean_release_zip

# ============================================================================
# R04 Tests: Corrupted execution.json or exit 0 with failures fail-closed
# ============================================================================

def test_r04_watch_run_process_corrupted_json_fails_closed(tmp_path: Path):
    """When execution.json is corrupted JSON and process exits with 0, run status must be FAILED."""
    run_dir = tmp_path / "run_test_r04_corrupt"
    run_dir.mkdir()
    engine_dir = run_dir / "output"
    engine_dir.mkdir()

    # Create corrupted execution.json
    (engine_dir / "execution.json").write_text("{this is corrupt json!!", encoding="utf-8")
    status_file = run_dir / "status.json"
    status_file.write_text(json.dumps({"status": "RUNNING", "capabilities": {"pause": True, "resume": True}}), encoding="utf-8")

    class DummyProc:
        def wait(self):
            return 0

    runs._watch_run_process("run_test_r04_corrupt", DummyProc(), run_dir, engine_dir)

    status_data = json.loads(status_file.read_text(encoding="utf-8"))
    assert status_data["status"] == "FAILED", f"Expected FAILED, got {status_data['status']}"
    assert "Corrupted execution report" in status_data.get("errorReason", "")


def test_r04_watch_run_process_failures_in_report_fails_closed(tmp_path: Path):
    """When execution.json has complete=False and validation_failures with exit 0, status must be FAILED."""
    run_dir = tmp_path / "run_test_r04_failures"
    run_dir.mkdir()
    engine_dir = run_dir / "output"
    engine_dir.mkdir()

    report = {
        "complete": False,
        "runId": "run_test_r04_failures",
        "validation_failures": [{"seed": 42, "reason": "replay mismatch detected"}],
    }
    (engine_dir / "execution.json").write_text(json.dumps(report), encoding="utf-8")
    status_file = run_dir / "status.json"
    status_file.write_text(json.dumps({"status": "RUNNING", "capabilities": {"pause": True, "resume": True}}), encoding="utf-8")

    class DummyProc:
        def wait(self):
            return 0

    runs._watch_run_process("run_test_r04_failures", DummyProc(), run_dir, engine_dir)

    status_data = json.loads(status_file.read_text(encoding="utf-8"))
    assert status_data["status"] == "FAILED"
    assert "replay mismatch detected" in status_data.get("errorReason", "")


# ============================================================================
# R05 Tests: Symlink traversal prevention in generate_run_zip_file
# ============================================================================

def test_r05_zip_export_blocks_symlink_traversal(tmp_path: Path, monkeypatch):
    """Symlink pointing to an external file outside the run directory must be omitted from ZIP."""
    runs_dir = tmp_path / "runs"
    runs_dir.mkdir()
    monkeypatch.setenv("CODONTRACE_RUNS_DIR", str(runs_dir))

    run_dir = runs_dir / "run_symlink_probe"
    run_dir.mkdir()
    (run_dir / "status.json").write_text(json.dumps({"status": "COMPLETED"}), encoding="utf-8")
    (run_dir / "data.txt").write_text("internal run data", encoding="utf-8")

    # Create sentinel file OUTSIDE the run directory
    sentinel = tmp_path / "external_sentinel.txt"
    sentinel.write_text("SENSITIVE HOST DATA DO NOT EXPORT", encoding="utf-8")

    # Create symlink inside run directory pointing to the external sentinel
    symlink_path = run_dir / "link_to_external.txt"
    try:
        symlink_path.symlink_to(sentinel)
    except (OSError, NotImplementedError):
        pytest.skip("Symlink creation not supported in this environment")

    zip_path, manifest = runs.generate_run_zip_file("run_symlink_probe")
    assert zip_path is not None
    assert manifest is not None

    try:
        with zipfile.ZipFile(zip_path, "r") as zf:
            namelist = zf.namelist()
            assert "data.txt" in namelist
            assert "link_to_external.txt" not in namelist

        # Verify omitted files manifest record
        omitted = manifest.get("omittedFiles", [])
        assert any(item["path"] == "link_to_external.txt" for item in omitted)
        assert any("Symlink traversal outside run boundary rejected" in item["reason"] for item in omitted)
    finally:
        zip_path.unlink(missing_ok=True)


def test_r05_zip_export_blocks_external_resolution_mocked(tmp_path: Path, monkeypatch):
    """Ensure that any file whose canonical resolve() lies outside run boundary is omitted."""
    runs_dir = tmp_path / "runs"
    runs_dir.mkdir()
    monkeypatch.setenv("CODONTRACE_RUNS_DIR", str(runs_dir))

    run_dir = runs_dir / "run_external_probe"
    run_dir.mkdir()
    (run_dir / "status.json").write_text(json.dumps({"status": "COMPLETED"}), encoding="utf-8")
    (run_dir / "inside.txt").write_text("inside data", encoding="utf-8")
    (run_dir / "fake_outside.txt").write_text("fake outside", encoding="utf-8")

    outside_path = (tmp_path / "secret_outside.txt").resolve()

    original_resolve = Path.resolve
    def mock_resolve(self, strict=False):
        if self.name == "fake_outside.txt":
            return outside_path
        return original_resolve(self, strict=strict)

    monkeypatch.setattr(Path, "resolve", mock_resolve)

    zip_path, manifest = runs.generate_run_zip_file("run_external_probe")
    assert zip_path is not None
    assert manifest is not None

    try:
        with zipfile.ZipFile(zip_path, "r") as zf:
            namelist = zf.namelist()
            assert "inside.txt" in namelist
            assert "fake_outside.txt" not in namelist

        omitted = manifest.get("omittedFiles", [])
        assert any(item["path"] == "fake_outside.txt" for item in omitted)
        assert any("Symlink traversal outside run boundary rejected" in item["reason"] for item in omitted)
    finally:
        zip_path.unlink(missing_ok=True)


# ============================================================================
# R15 Tests: Release ZIP builder prunes development and output artifacts
# ============================================================================

def test_r15_build_clean_release_zip_prunes_unwanted_dirs(tmp_path: Path):
    """build_clean_release_zip must prune .git, node_modules, output, and cache directories."""
    src_root = tmp_path / "repo_root"
    src_root.mkdir()

    # Valid distribution contents
    (src_root / "pyproject.toml").write_text("[project]\nname='test'\n", encoding="utf-8")
    (src_root / "src" / "codontrace" / "genesis").mkdir(parents=True)
    (src_root / "src" / "codontrace" / "__init__.py").write_text("", encoding="utf-8")
    (src_root / "src" / "codontrace" / "genesis" / "__init__.py").write_text("", encoding="utf-8")
    (src_root / "tests").mkdir()
    (src_root / "tests" / "test_dummy.py").write_text("def test_dummy(): pass\n", encoding="utf-8")
    (src_root / "examples").mkdir()
    (src_root / "examples" / "demo.py").write_text("print('demo')\n", encoding="utf-8")

    # Unwanted directories that MUST be pruned
    (src_root / ".git").mkdir()
    (src_root / ".git" / "objects").mkdir()
    (src_root / ".git" / "objects" / "sentinel.blob").write_bytes(b"git_data")

    (src_root / "node_modules" / "some_pkg").mkdir(parents=True)
    (src_root / "node_modules" / "some_pkg" / "index.js").write_text("module.exports = {};\n", encoding="utf-8")

    (src_root / "output" / "large_run").mkdir(parents=True)
    (src_root / "output" / "large_run" / "sim.dat").write_bytes(b"large_output_bytes")

    (src_root / "simulation_runs" / "run_01").mkdir(parents=True)
    (src_root / "simulation_runs" / "run_01" / "log.txt").write_text("run log", encoding="utf-8")

    (src_root / "src" / "__pycache__").mkdir()
    (src_root / "src" / "__pycache__" / "cached.pyc").write_bytes(b"pyc")

    out_zip = tmp_path / "clean_release.zip"
    result_path = build_clean_release_zip.build(src_root, out_zip)
    assert result_path.is_file()

    with zipfile.ZipFile(result_path, "r") as zf:
        names = zf.namelist()
        assert "pyproject.toml" in names
        assert "src/codontrace/__init__.py" in names
        assert not any(".git" in n for n in names)
        assert not any("node_modules" in n for n in names)
        assert not any(n.startswith("output/") for n in names)
        assert not any(n.startswith("simulation_runs/") for n in names)
        assert not any("__pycache__" in n for n in names)
        assert not any(n.endswith(".pyc") for n in names)


# ============================================================================
# R17 Tests: Cooperative pause mechanism
# ============================================================================

def test_r17_cooperative_pause_signal_and_action(tmp_path: Path, monkeypatch):
    """Pause creates PAUSE marker without creating STOP; resume removes PAUSE."""
    runs_dir = tmp_path / "runs"
    runs_dir.mkdir()
    monkeypatch.setenv("CODONTRACE_RUNS_DIR", str(runs_dir))

    run_dir = runs_dir / "run_pause_test"
    run_dir.mkdir()
    engine_dir = run_dir / "output"
    engine_dir.mkdir()
    status_file = run_dir / "status.json"
    status_file.write_text(json.dumps({"status": "RUNNING", "capabilities": {"pause": True, "resume": True}}), encoding="utf-8")

    # 1. Action pause
    res_pause = runs.manage_run_action("run_pause_test", "pause")
    assert res_pause["ok"] is True
    assert (run_dir / "PAUSE").is_file(), "PAUSE marker must exist in run_dir"
    assert (engine_dir / "PAUSE").is_file(), "PAUSE marker must exist in engine_dir"
    assert not (run_dir / "STOP").is_file(), "STOP marker MUST NOT be created for pause"
    assert not (engine_dir / "STOP").is_file(), "STOP marker MUST NOT be created in engine_dir for pause"

    # A marker requests pause; the worker must acknowledge before PAUSED.
    st_data = json.loads(status_file.read_text(encoding="utf-8"))
    assert st_data["status"] == "PAUSING"
    (run_dir / "ack_paused_worker").write_text("ack", encoding="utf-8")
    assert runs.manage_run_action("run_pause_test", "pause")["ok"] is True
    assert json.loads(status_file.read_text())["status"] == "PAUSED"

    # 2. Action resume
    res_resume = runs.manage_run_action("run_pause_test", "resume")
    assert res_resume["ok"] is True
    assert not (run_dir / "PAUSE").is_file(), "PAUSE marker must be removed on resume"
    assert not (engine_dir / "PAUSE").is_file(), "engine_dir PAUSE marker must be removed on resume"

    st_data = json.loads(status_file.read_text(encoding="utf-8"))
    assert st_data["status"] == "RESUMING"


# ============================================================================
# R18 Tests: Independent authorization on /api/release/update
# ============================================================================

def test_r18_remote_update_rejected_without_token(monkeypatch):
    """Remote caller without CODONTRACE_UPDATE_TOKEN must be rejected with 403."""
    handler = server.ConsoleHandler.__new__(server.ConsoleHandler)
    handler.client_address = ("192.168.1.100", 45678)
    handler.headers = {}
    monkeypatch.delenv("CODONTRACE_UPDATE_TOKEN", raising=False)

    authorized, status_code, msg = handler._check_update_authorization({})
    assert authorized is False
    assert status_code == 403
    assert "Remote update requires CODONTRACE_UPDATE_TOKEN authorization" in msg


def test_r18_update_with_configured_token_enforces_bearer(monkeypatch):
    """When CODONTRACE_UPDATE_TOKEN is set, caller must supply matching token."""
    monkeypatch.setenv("CODONTRACE_UPDATE_TOKEN", "secret-admin-token-xyz")
    handler = server.ConsoleHandler.__new__(server.ConsoleHandler)
    handler.client_address = ("127.0.0.1", 12345)

    # 1. Missing token
    handler.headers = {}
    authorized, status_code, msg = handler._check_update_authorization({})
    assert authorized is False
    assert status_code == 401

    # 2. Invalid token
    handler.headers = {"Authorization": "Bearer wrong-token"}
    authorized, status_code, msg = handler._check_update_authorization({})
    assert authorized is False
    assert status_code == 401

    # 3. Valid Bearer token
    handler.headers = {"Authorization": "Bearer secret-admin-token-xyz"}
    authorized, status_code, msg = handler._check_update_authorization({})
    assert authorized is True
    assert status_code == 200

    # 4. Valid X-Update-Token header
    handler.headers = {"X-Update-Token": "secret-admin-token-xyz"}
    authorized, status_code, msg = handler._check_update_authorization({})
    assert authorized is True
    assert status_code == 200


def test_r18_local_update_allowed_when_no_token_configured(monkeypatch):
    """Local caller is allowed when no token is configured."""
    monkeypatch.delenv("CODONTRACE_UPDATE_TOKEN", raising=False)
    handler = server.ConsoleHandler.__new__(server.ConsoleHandler)
    handler.client_address = ("127.0.0.1", 12345)
    handler.headers = {}

    authorized, status_code, msg = handler._check_update_authorization({})
    assert authorized is True
    assert status_code == 200


# ============================================================================
# R19 Tests: LLM fallback contract and Price equation
# ============================================================================

def test_r19_chat_turn_fallback_contract(monkeypatch):
    """When LLM is unmounted/offline, chat_turn returns source=analyst and fallback=True."""
    # Force LLM status unmounted
    monkeypatch.setattr(chat, "check_llm_status", lambda: {
        "mounted": False,
        "endpoint": "http://127.0.0.1:8088/v1/chat/completions",
        "model": None,
        "provider": "none",
        "available_models": [],
    })
    monkeypatch.setattr(chat, "query_llm", lambda *args, **kwargs: None)

    res = chat.chat_turn("What is the Price equation?", lang="en", model="llama-3-8b")
    assert res["source"] == "analyst"
    assert res["mounted"] is False
    assert res["fallback"] is True
    assert "Cov(W_g, z̄_g)" in res["reply"]
    assert "Price Equation Analysis" in res["reply"]


def test_r19_chat_turn_explicit_deterministic_analyst():
    """When explicitly requesting deterministic-analyst, fallback is False."""
    res = chat.chat_turn("Price equation", lang="en", model="deterministic-analyst")
    assert res["source"] == "analyst"
    assert res["fallback"] is False
    assert "Price Equation Analysis" in res["reply"]
