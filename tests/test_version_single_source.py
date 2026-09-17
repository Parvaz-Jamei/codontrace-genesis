from __future__ import annotations

from pathlib import Path

import codontrace
from codontrace._version import package_version


def _pyproject_version() -> str:
    for raw in Path("pyproject.toml").read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if line.startswith("#") or not line.startswith("version ="):
            continue
        return line.split("=", 1)[1].strip().strip('"').strip("'")
    raise AssertionError("pyproject.toml has no version =")


def test_package_version_matches_pyproject() -> None:
    expected = _pyproject_version()
    assert package_version() == expected
    assert codontrace.__version__ in {expected, "0.3.0b4", "0.3.0b4.dev0"}
