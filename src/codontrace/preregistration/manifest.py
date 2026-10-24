"""Section 1: hash a preregistration plan into one canonical digest."""

from __future__ import annotations

import hashlib
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

from codontrace.errors import ConfigurationError
from codontrace.genesis.canonical import canonical_json

__all__ = ["PlanManifest", "hash_plan"]


@dataclass(frozen=True)
class PlanManifest:
    """``files`` maps a POSIX path relative to ``root`` to its SHA-256."""

    files: tuple[tuple[str, str], ...]
    title: str = ""

    def canonical_bytes(self) -> bytes:
        payload = {
            "schema": "codontrace_prereg_manifest_v1",
            "title": self.title,
            "files": [{"path": p, "sha256": h} for p, h in self.files],
        }
        return canonical_json(payload).encode("utf-8")

    @property
    def digest(self) -> str:
        """SHA-256 of the canonical manifest bytes; this is what gets timestamped."""
        return hashlib.sha256(self.canonical_bytes()).hexdigest()

    def to_dict(self) -> dict[str, object]:
        return {"title": self.title, "files": [list(f) for f in self.files], "digest": self.digest}

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> PlanManifest:
        files = data.get("files")
        if not isinstance(files, list):
            raise ConfigurationError("manifest.files must be a list")
        m = cls(tuple((str(p), str(h)) for p, h in files), str(data.get("title", "")))
        if "digest" in data and data["digest"] != m.digest:
            raise ConfigurationError("manifest digest does not match its files")
        return m


def hash_plan(paths: Iterable[str | Path], *, root: str | Path, title: str = "") -> PlanManifest:
    base = Path(root).resolve()
    out: list[tuple[str, str]] = []
    for p in paths:
        full = Path(p) if Path(p).is_absolute() else base / p
        full = full.resolve()
        try:
            rel = full.relative_to(base).as_posix()
        except ValueError as exc:
            raise ConfigurationError(f"{full} is outside {base}") from exc
        if not full.is_file():
            raise ConfigurationError(f"plan file not found: {rel}")
        out.append((rel, hashlib.sha256(full.read_bytes()).hexdigest()))
    if not out:
        raise ConfigurationError("a plan needs at least one file")
    if len({p for p, _ in out}) != len(out):
        raise ConfigurationError("duplicate plan file")
    return PlanManifest(tuple(sorted(out)), title)
