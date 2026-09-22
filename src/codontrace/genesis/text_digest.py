"""Text-file SHA-256 that follows Git LF identity, not the working-tree bytes."""

from __future__ import annotations

import hashlib
from pathlib import Path


def sha256_text_file(path: str | Path) -> str:
    """SHA-256 after CRLF/CR -> LF.

    Windows checkouts with core.autocrlf=true change working-tree bytes.
    Document pins must match the repository blob (LF), not the checkout.
    Keep hashlib.sha256(Path.read_bytes()) only for true binary artifacts.
    """
    data = Path(path).read_bytes().replace(b"\r\n", b"\n").replace(b"\r", b"\n")
    return hashlib.sha256(data).hexdigest()
