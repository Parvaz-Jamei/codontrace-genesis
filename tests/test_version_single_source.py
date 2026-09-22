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
    assert codontrace.__version__ == expected


def test_init_does_not_hardcode_pep440_identity() -> None:
    text = Path("src/codontrace/__init__.py").read_text(encoding="utf-8")
    assert "__version__ = package_version()" in text
    assert '__version__ = "0.' not in text


def test_readme_and_citation_do_not_advertise_stale_dev1() -> None:
    expected = _pyproject_version()
    readme = Path("README.md").read_text(encoding="utf-8")
    citation = Path("CITATION.cff").read_text(encoding="utf-8")
    assert "0.3.0b4.dev1" not in readme
    assert f'version: "{expected}"' in citation
    assert expected in readme
    assert "DomainProfile" in readme
    assert "SaMD" in readme
