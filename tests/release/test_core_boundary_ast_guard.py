from __future__ import annotations

from pathlib import Path

from tools.check_core_boundary import scan_paths, scan_python_source


def test_ast_boundary_guard_allows_policy_text_and_blocks_real_imports(tmp_path: Path) -> None:
    policy_text = tmp_path / "policy_text.py"
    policy_text.write_text(
        '"""FastAPI, WebSocket, React, Tauri are mentioned here as forbidden policy text."""\n'
        'TOKEN = "uvicorn should not matter inside a string literal"\n',
        encoding="utf-8",
    )
    assert scan_python_source(policy_text) == ()

    bad_import = tmp_path / "bad_import.py"
    bad_import.write_text("from fastapi import FastAPI\n", encoding="utf-8")
    violations = scan_python_source(bad_import)
    assert len(violations) == 1
    assert violations[0].reason == "from-import"
    assert violations[0].module == "fastapi"

    dynamic_import = tmp_path / "dynamic_import.py"
    dynamic_import.write_text(
        "import importlib\napp = importlib.import_module('uvicorn')\n",
        encoding="utf-8",
    )
    assert scan_python_source(dynamic_import)[0].reason == "dynamic import"


def test_core_tree_has_no_ui_or_server_imports() -> None:
    assert scan_paths((Path("src/codontrace"),), root=Path.cwd()) == ()
