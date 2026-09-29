"""Static hygiene: no file under src/ may start with a UTF-8 BOM.

A BOM passes Python's own compile step but makes `ast.parse` fail, which reddens the
"Enforce core boundary with AST import guard" CI step for every job. This guard makes
that failure impossible to reintroduce silently.
"""

from __future__ import annotations

from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SRC = REPO / "src"
BOM = b"\xef\xbb\xbf"


def test_no_utf8_bom_under_src() -> None:
    offenders = [
        path.relative_to(REPO).as_posix()
        for path in sorted(SRC.rglob("*"))
        if path.is_file() and path.read_bytes().startswith(BOM)
    ]
    assert offenders == [], f"UTF-8 BOM found in: {offenders}"