"""The import-linter contracts in .importlinter hold, and they bite.

The second test rewrites the configuration to forbid an edge that does exist.
That shows `lint-imports` actually reports a broken contract and is not
passing vacuously.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
_LOCAL = Path(sys.executable).with_name("lint-imports")
LINT = str(_LOCAL) if _LOCAL.exists() else shutil.which("lint-imports")
pytestmark = pytest.mark.skipif(LINT is None, reason="import-linter is not installed (dev extra)")


def _run(config: Path) -> subprocess.CompletedProcess[str]:
    assert LINT is not None
    env = {**os.environ, "PYTHONPATH": str(ROOT / "src")}
    return subprocess.run([LINT, "--no-cache", "--config", str(config)], cwd=ROOT, env=env,
                          capture_output=True, text=True, check=False)


def test_contracts_are_kept() -> None:
    out = _run(ROOT / ".importlinter")
    assert out.returncode == 0, out.stdout + out.stderr
    assert "0 broken" in out.stdout


def test_a_real_violation_is_reported(tmp_path: Path) -> None:
    cfg = tmp_path / "broken.ini"
    cfg.write_text(
        "[importlinter]\nroot_package = codontrace\n\n"
        "[importlinter:contract:x]\nname = genesis must not import rng (false on purpose)\n"
        "type = forbidden\nsource_modules =\n    codontrace.genesis.population\n"
        "forbidden_modules =\n    codontrace.rng\n",
        encoding="utf-8",
    )
    out = _run(cfg)
    assert out.returncode != 0 and "BROKEN" in out.stdout
