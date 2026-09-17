"""Phase 3 notes exist and do not bump PyPI."""

from pathlib import Path


def test_phase3_handoff_is_not_pypi() -> None:
    text = (
        Path(__file__).resolve().parents[1] / "docs/PHASE3_RELEASE_HANDOFF.md"
    ).read_text(encoding="utf-8")
    assert "not a PyPI cut" in text or "not PyPI" in text
    assert "v0.3.0b4.dev0-he02-v1b" in text
    assert "0.3.0b5" not in text.split("does not contain")[0]
