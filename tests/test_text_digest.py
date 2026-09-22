"""Text digests follow Git LF identity, not working-tree CRLF."""

from __future__ import annotations

import hashlib
from pathlib import Path

from codontrace.genesis.text_digest import sha256_text_file


def test_crlf_and_lf_files_share_digest(tmp_path: Path) -> None:
    lf = tmp_path / "lf.md"
    crlf = tmp_path / "crlf.md"
    body = "# pin\nsecond line\n"
    lf.write_bytes(body.encode("utf-8"))
    crlf.write_bytes(body.replace("\n", "\r\n").encode("utf-8"))
    assert sha256_text_file(lf) == sha256_text_file(crlf)
    assert sha256_text_file(lf) == hashlib.sha256(body.encode("utf-8")).hexdigest()
    assert sha256_text_file(crlf) != hashlib.sha256(crlf.read_bytes()).hexdigest()
