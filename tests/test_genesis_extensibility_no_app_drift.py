from __future__ import annotations

import pathlib


def test_no_runtime_dependencies_or_console_scripts() -> None:
    pyproject = pathlib.Path("pyproject.toml").read_text(encoding="utf-8")
    assert "dependencies = []" in pyproject
    assert "[project.scripts]" not in pyproject
    assert "[project.gui-scripts]" not in pyproject
