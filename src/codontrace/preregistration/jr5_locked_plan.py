"""JR5 locked-plan pin: plan digest excludes DEVIATIONS.md; the log is checked separately.

The gate and verdict adapter pin ``hash_plan`` over every ``record.json``
manifest file except ``DEVIATIONS.md``. That digest is stable when a
deviation is only logged. The append-only log is verified on its own:
entries chain from the lock, and the last entry's new digest equals the
recomputed plan digest. ``record.json`` must still match fresh file hashes
(including ``DEVIATIONS.md``), so a stale record or an edit to a locked file
is refused.
"""

from __future__ import annotations

import json
import re
from collections.abc import Mapping, Sequence
from pathlib import Path

from codontrace.errors import ConfigurationError
from codontrace.preregistration.manifest import PlanManifest, hash_plan

__all__ = [
    "DEVIATIONS_RELPATH",
    "DIGEST_LINE",
    "plan_digest_from_files",
    "verify_deviations_log",
    "verify_jr5_record_at_root",
    "verify_jr5_record_bytes",
]

DEVIATIONS_RELPATH = "docs/prereg/jr5/DEVIATIONS.md"
DIGEST_LINE = re.compile(r"^- Record digest: `([0-9a-f]{64})` -> `([0-9a-f]{64})`$", re.M)


def _mapping(value: object, what: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise ConfigurationError(f"{what} must be a mapping.")
    return value


def plan_digest_from_files(files: Sequence[tuple[str, str]], title: str) -> str:
    """Canonical digest of the manifest file list with DEVIATIONS.md removed."""

    locked = tuple((path, digest) for path, digest in files if path != DEVIATIONS_RELPATH)
    if not locked:
        raise ConfigurationError("JR5 plan has no locked files.")
    if len(locked) != len(files) - 1 or DEVIATIONS_RELPATH not in {path for path, _ in files}:
        raise ConfigurationError("JR5 record must list DEVIATIONS.md exactly once among the plan files.")
    return PlanManifest(locked, title).digest


def verify_deviations_log(text: str, *, expected_plan_digest: str) -> None:
    """Refuse a broken chain or a last entry that does not name the plan digest."""

    if not isinstance(text, str) or not text:
        raise ConfigurationError("DEVIATIONS.md must be non-empty text.")
    entries = text.split("\n## ")[1:]
    if not entries:
        raise ConfigurationError("DEVIATIONS.md must contain at least one dated entry.")
    pairs: list[tuple[str, str]] = []
    for entry in entries:
        found = DIGEST_LINE.findall(entry)
        if len(found) != 1:
            raise ConfigurationError("each DEVIATIONS.md entry must have exactly one record-digest line.")
        pairs.append(found[0])
    for (_, new), (old, _) in zip(pairs, pairs[1:], strict=False):
        if old != new:
            raise ConfigurationError("DEVIATIONS.md digest lines do not chain.")
    if pairs[-1][1] != expected_plan_digest:
        raise ConfigurationError("DEVIATIONS.md last entry does not name the locked plan digest.")


def _parse_record_manifest(record_raw: bytes) -> tuple[PlanManifest, str]:
    try:
        record = json.loads(record_raw.decode("utf-8"))
    except (UnicodeError, ValueError) as exc:
        raise ConfigurationError("record must contain valid UTF-8 JSON.") from exc
    body = _mapping(record, "record")
    manifest = _mapping(body.get("manifest"), "record.manifest")
    title = manifest.get("title")
    files = manifest.get("files")
    if not isinstance(title, str):
        raise ConfigurationError("record manifest title must be a string.")
    if not isinstance(files, list):
        raise ConfigurationError("record manifest files must be a list.")
    pairs: list[tuple[str, str]] = []
    for entry in files:
        if not isinstance(entry, list) or len(entry) != 2 or not all(isinstance(x, str) for x in entry):
            raise ConfigurationError("record manifest files must be path/digest pairs.")
        pairs.append((entry[0], entry[1]))
    if len({path for path, _ in pairs}) != len(pairs):
        raise ConfigurationError("record manifest must not repeat a path.")
    verified = PlanManifest(tuple(pairs), title)
    declared = manifest.get("digest")
    if declared != verified.digest:
        raise ConfigurationError("record manifest content does not match its declared digest.")
    return verified, verified.digest


def verify_jr5_record_bytes(
    record_raw: bytes,
    *,
    locked_plan_digest: str,
    deviations_text: str | None = None,
) -> tuple[PlanManifest, str]:
    """Check the declared record and the plan-digest pin; optionally the log text."""

    manifest, _full = _parse_record_manifest(record_raw)
    plan = plan_digest_from_files(manifest.files, manifest.title)
    if plan != locked_plan_digest:
        raise ConfigurationError("record plan digest does not match the code-pinned prereg lock.")
    if deviations_text is not None:
        verify_deviations_log(deviations_text, expected_plan_digest=plan)
    return manifest, plan


def verify_jr5_record_at_root(
    root: str | Path,
    *,
    locked_plan_digest: str,
) -> tuple[PlanManifest, str]:
    """Re-hash every listed file under ``root``, pin the plan digest, and check the log."""

    base = Path(root)
    try:
        record_raw = (base / "docs/prereg/jr5/record.json").read_bytes()
        deviations_text = (base / DEVIATIONS_RELPATH).read_text(encoding="utf-8")
    except OSError as exc:
        raise ConfigurationError(f"JR5 prereg files not readable under {base}.") from exc
    manifest, plan = verify_jr5_record_bytes(
        record_raw, locked_plan_digest=locked_plan_digest, deviations_text=deviations_text
    )
    fresh = hash_plan([path for path, _ in manifest.files], root=base, title=manifest.title)
    if fresh.files != manifest.files or fresh.digest != manifest.digest:
        raise ConfigurationError("record.json does not match the fresh hashes of its plan files.")
    # Plan from disk must equal the pin (locked files only).
    disk_plan = hash_plan(
        [path for path, _ in manifest.files if path != DEVIATIONS_RELPATH],
        root=base,
        title=manifest.title,
    )
    if disk_plan.digest != locked_plan_digest or disk_plan.digest != plan:
        raise ConfigurationError("fresh plan digest does not match the code-pinned prereg lock.")
    return manifest, plan
