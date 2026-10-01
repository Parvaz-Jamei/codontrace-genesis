"""Archive reader and manifest conventions."""

from __future__ import annotations

import gzip
import json
from pathlib import Path

from codontrace.genesis.archive_io import (
    iter_jsonl_lines,
    resolve_jsonl,
    verify_manifest,
    write_manifests,
)


def test_reads_plain_and_gzip_jsonl(tmp_path: Path) -> None:
    plain = tmp_path / "events.jsonl"
    plain.write_text('{"seed": 1}\n\n{"seed": 2}\n', encoding="utf-8")
    gz = tmp_path / "population.jsonl.gz"
    with gzip.open(gz, "wt", encoding="utf-8") as handle:
        handle.write('{"generation": 90}\n')

    assert resolve_jsonl(tmp_path / "events.jsonl") == plain
    assert resolve_jsonl(tmp_path / "population.jsonl").name.endswith(".gz")
    assert [json.loads(line)["seed"] for line in iter_jsonl_lines(plain)] == [1, 2]
    assert json.loads(next(iter_jsonl_lines(tmp_path / "population.jsonl")))["generation"] == 90


def test_manifest_skips_self_cache_and_matches_lf_checkout(tmp_path: Path) -> None:
    (tmp_path / "note.md").write_bytes(b"alpha\r\nbeta\n")
    (tmp_path / "raw.jsonl.gz").write_bytes(gzip.compress(b'{"ok": 1}\n'))
    cache = tmp_path / "__pycache__"
    cache.mkdir()
    (cache / "note.pyc").write_bytes(b"\x00pyc")
    (tmp_path / "evidence_files.sha256").write_text("stale\n", encoding="utf-8")

    lf_path, raw_path = write_manifests(tmp_path)
    text = lf_path.read_text(encoding="utf-8")
    body = [line for line in text.splitlines() if line and not line.startswith("#")]
    assert all(not line.endswith("evidence_files.sha256") for line in body)
    assert all("__pycache__" not in line and not line.endswith(".pyc") for line in body)
    assert all("manifest_lf.sha256" not in line for line in body)
    assert verify_manifest(lf_path) == []
    assert verify_manifest(raw_path) == []
    # LF and raw conventions differ when the source has CR.
    lf_note = next(line for line in text.splitlines() if line.endswith("note.md"))
    raw_note = next(
        line for line in raw_path.read_text(encoding="utf-8").splitlines() if line.endswith("note.md")
    )
    assert lf_note.split()[0] != raw_note.split()[0]
