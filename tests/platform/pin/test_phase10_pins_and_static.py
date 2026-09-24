"""Phase 10 pin: BAIC pins + static audits for calib/export modules."""

from __future__ import annotations

import ast
import hashlib
from pathlib import Path

import pytest

from codontrace.genesis.host_parasite_world import _BAIC_PINS, assert_baic_pins_untouched

REPO = Path(__file__).resolve().parents[3]
ENGINE = REPO / "src" / "codontrace" / "engine.py"
CALIB = REPO / "src" / "codontrace" / "genesis" / "host_parasite_calibration.py"
EXPORT = REPO / "src" / "codontrace" / "genesis" / "host_parasite_export.py"
DESIGN = REPO / "docs" / "design_notes" / "ENGINE_PACKAGE_SPLIT_DESIGN.md"

_BANNED_MARKERS = ("HostParasiteEnv", "codontrace.engine", "Infection")


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _assert_no_banned_imports(path: Path) -> None:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    text = path.read_text(encoding="utf-8")
    for marker in _BANNED_MARKERS:
        if marker == "Infection":
            # Allow the word only inside comments/docstrings carefully — require no class Infection
            assert "class Infection" not in text
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert marker not in alias.name
            if isinstance(node, ast.ImportFrom) and node.module:
                assert marker not in node.module
                if marker == "HostParasiteEnv":
                    assert "host_parasite_env" not in node.module


@pytest.mark.pin
def test_baic_pins_byte_identical() -> None:
    assert_baic_pins_untouched()
    for rel, expected in _BAIC_PINS:
        assert _sha(REPO / rel) == expected


@pytest.mark.pin
def test_engine_py_untouched_vs_phase9_tip_presence() -> None:
    # Phase 10 must not mass-refactor engine.py; file must exist and DESIGN note present.
    assert ENGINE.is_file()
    assert DESIGN.is_file()
    body = DESIGN.read_text(encoding="utf-8")
    assert "Do not execute" in body or "do not execute" in body.casefold()
    assert "owner" in body.casefold()


@pytest.mark.pin
def test_calib_export_static_imports() -> None:
    _assert_no_banned_imports(CALIB)
    _assert_no_banned_imports(EXPORT)
    calib_text = CALIB.read_text(encoding="utf-8")
    assert "host_parasite_env" not in calib_text
    assert "from codontrace.engine" not in calib_text
