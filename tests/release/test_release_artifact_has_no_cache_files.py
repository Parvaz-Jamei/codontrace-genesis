from __future__ import annotations

import zipfile
from pathlib import Path


def test_release_artifact_has_no_cache_files(tmp_path: Path) -> None:
    artifact = tmp_path / "source.zip"
    with zipfile.ZipFile(artifact, "w") as zf:
        zf.writestr("codontrace/src/codontrace/__init__.py", "")
        zf.writestr("codontrace/docs/readme.md", "")
    with zipfile.ZipFile(artifact) as zf:
        names = zf.namelist()
    forbidden = (
        "__pycache__",
        ".pytest_cache",
        ".mypy_cache",
        ".ruff_cache",
        ".pyc",
        "build/",
        "dist/",
    )
    assert not any(any(part in name for part in forbidden) for name in names)
