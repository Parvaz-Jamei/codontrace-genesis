from __future__ import annotations

from pathlib import Path


def test_manifest_includes_research_release_assets() -> None:
    root = Path(__file__).resolve().parents[2]
    manifest = root / "MANIFEST.in"
    assert manifest.exists()
    text = manifest.read_text(encoding="utf-8")
    for required in (
        "recursive-include docs *.md",
        "recursive-include examples *.py",
        "recursive-include tests *.py",
        "include RELEASE_EVIDENCE.md",
        "include CITATION.cff",
    ):
        assert required in text


def test_mypy_optional_numpy_override_is_documented() -> None:
    root = Path(__file__).resolve().parents[2]
    pyproject = (root / "pyproject.toml").read_text(encoding="utf-8")
    assert 'module = ["numpy", "numpy.*"]' in pyproject
    assert "ignore_missing_imports = true" in pyproject
