"""Checkout-local import bootstrap for standalone examples.

The public examples are intentionally kept at the repository root so they can be
read and run directly from a source checkout.  Editable installs and pytest set
``src`` on ``PYTHONPATH``, but a clean checkout subprocess does not.  This helper
adds the local ``src`` directory only when the package is not already importable,
which keeps installed-package behavior unchanged while making the official pilots
reproducible from a fresh unpacked archive.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


def ensure_src_path() -> None:
    """Make ``codontrace`` importable for direct example-script execution.

    The function is intentionally conservative: if ``codontrace`` is already
    importable (normal installed/editable usage), it does nothing.  Otherwise it
    prepends the repository-local ``src`` directory when this file lives in the
    top-level ``examples`` directory of a source checkout.
    """

    if importlib.util.find_spec("codontrace") is not None:
        return
    root = Path(__file__).resolve().parents[1]
    src = root / "src"
    if src.exists() and (src / "codontrace").is_dir():
        sys.path.insert(0, str(src))
