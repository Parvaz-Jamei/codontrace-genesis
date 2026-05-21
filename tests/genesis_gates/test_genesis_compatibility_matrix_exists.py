from __future__ import annotations

from pathlib import Path


def test_genesis_compatibility_matrix_exists_and_controls_claims() -> None:
    root = Path(__file__).resolve().parents[2]
    matrix = root / "GENESIS_COMPATIBILITY_MATRIX.md"
    assert matrix.exists()
    text = matrix.read_text(encoding="utf-8")
    assert "Full GENESIS Engine claim" in text
    assert "not yet a proof of artificial life" in text
    assert "research-alpha foundation engine" in text
