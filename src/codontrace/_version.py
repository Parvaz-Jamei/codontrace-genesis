"""Single runtime version source.

Canonical PEP 440 identity lives in pyproject.toml [project].version.
Installed trees read importlib.metadata; editable/source trees parse pyproject.
"""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

_PACKAGE_NAME = "codontrace"


def package_version() -> str:
    try:
        return version(_PACKAGE_NAME)
    except PackageNotFoundError:
        pass
    pyproject = Path(__file__).resolve().parents[2] / "pyproject.toml"
    if pyproject.is_file():
        for raw in pyproject.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if line.startswith("#") or not line.startswith("version ="):
                continue
            value = line.split("=", 1)[1].strip().strip('"').strip("'")
            if value:
                return value
    raise RuntimeError("cannot resolve codontrace version from metadata or pyproject.toml")


__version__ = package_version()
