"""Read archived JSONL, plain or gzip, and hash published files.

Two hash conventions are never mixed in one column:

* ``sha256_raw`` is the digest of the file bytes as stored.
* ``sha256_lf`` is the digest after CR and CRLF become LF. Binary suffixes
  are still hashed raw inside an LF manifest, and the line says so.

A manifest does not list itself, ``evidence_files.sha256``, ``__pycache__``
or ``*.pyc``.
"""

from __future__ import annotations

import gzip
import hashlib
from collections.abc import Iterator
from pathlib import Path

BINARY_SUFFIXES = {".gz", ".npz", ".png", ".pdf", ".zip", ".tgz", ".whl"}
EXCLUDED_NAMES = {
    "manifest_lf.sha256",
    "manifest_raw.sha256",
    "evidence_files.sha256",
}


def sha256_raw(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def sha256_lf(path: Path) -> str:
    data = path.read_bytes().replace(b"\r\n", b"\n").replace(b"\r", b"\n")
    return hashlib.sha256(data).hexdigest()


def is_binary(path: Path) -> bool:
    return path.suffix.lower() in BINARY_SUFFIXES


def resolve_jsonl(path: Path) -> Path:
    """Return ``path`` or its ``.gz`` / plain sibling, whichever exists."""

    if path.is_file():
        return path
    name = path.name
    if name.endswith(".gz"):
        plain = path.with_name(name[:-3])
        if plain.is_file():
            return plain
    else:
        gzipped = path.with_name(name + ".gz")
        if gzipped.is_file():
            return gzipped
    raise FileNotFoundError(path)


def iter_jsonl_lines(path: Path) -> Iterator[str]:
    resolved = resolve_jsonl(path)
    opener = gzip.open if resolved.name.endswith(".gz") else open
    with opener(resolved, "rt", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                yield line


def iter_published_files(root: Path) -> list[Path]:
    files: list[Path] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        if "__pycache__" in path.parts or path.suffix == ".pyc":
            continue
        if path.name in EXCLUDED_NAMES:
            continue
        files.append(path)
    return files


def _manifest_text(root: Path, *, kind: str) -> str:
    lines = [
        f"# convention: {kind}",
        "# paths are relative to this manifest's directory",
        "# this file, evidence_files.sha256, __pycache__ and *.pyc are excluded",
    ]
    if kind == "sha256_lf":
        lines.append("# text files: SHA-256 after CR/CRLF -> LF; binary suffixes stay raw")
    else:
        lines.append("# every file: SHA-256 of the stored bytes")
    for path in iter_published_files(root):
        if kind == "sha256_raw" or is_binary(path):
            digest = sha256_raw(path)
        else:
            digest = sha256_lf(path)
        lines.append(f"{digest}  {path.relative_to(root).as_posix()}")
    return "\n".join(lines) + "\n"


def write_manifests(root: Path) -> tuple[Path, Path]:
    lf_path = root / "manifest_lf.sha256"
    raw_path = root / "manifest_raw.sha256"
    lf_path.write_text(_manifest_text(root, kind="sha256_lf"), encoding="utf-8", newline="\n")
    raw_path.write_text(_manifest_text(root, kind="sha256_raw"), encoding="utf-8", newline="\n")
    return lf_path, raw_path


def verify_manifest(path: Path) -> list[str]:
    """Return mismatch descriptions. An empty list means the manifest matches."""

    root = path.parent
    kind = "sha256_raw" if path.name.startswith("manifest_raw") else "sha256_lf"
    errors: list[str] = []
    seen: set[str] = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line or line.startswith("#"):
            if line.startswith("# convention:"):
                kind = line.split(":", 1)[1].strip()
            continue
        digest, rel = line.split(None, 1)
        seen.add(rel)
        target = root / rel
        if not target.is_file():
            errors.append(f"missing {rel}")
            continue
        if kind == "sha256_raw" or is_binary(target):
            got = sha256_raw(target)
        else:
            got = sha256_lf(target)
        if got != digest:
            errors.append(f"mismatch {rel}")
    expected = {p.relative_to(root).as_posix() for p in iter_published_files(root)}
    extra = sorted(expected - seen)
    if extra:
        errors.append(f"unlisted {extra[0]}" + (f" (+{len(extra) - 1})" if len(extra) > 1 else ""))
    return errors
