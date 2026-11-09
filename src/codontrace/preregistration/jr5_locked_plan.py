"""JR5 locked-plan pin: plan digest excludes DEVIATIONS.md; the log is checked separately.

The gate and verdict adapter pin ``hash_plan`` over every ``record.json``
manifest file except ``DEVIATIONS.md``. That digest is stable when a
deviation is only logged. The log is verified on its own and is append-only
in code, in the way a transparency log is checked against a trusted
checkpoint (tree size and root hash, RFC 9162 section 2.1.4): the code pins
checkpoints of the log, each the byte length and sha256 of the log text up to
the end of an accepted entry. The current log must start with every pinned
checkpoint, so an accepted entry cannot be edited, reordered or removed.
Text after the last checkpoint must be whole appended entries. The first
entry must be the lock-start entry (its old digest and its full text are
pinned), every entry has exactly one record-digest line at the start of a
line, entries chain, and the last entry names the recomputed plan digest.
``record.json`` must still match fresh file hashes (including
``DEVIATIONS.md``), so a stale record or an edit to a locked file is refused.

Entries appended after the last checkpoint are not protected until a reviewed
change adds a checkpoint for them; this is the window between checkpoints
that any checkpointed log has.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping, Sequence
from pathlib import Path

from codontrace.errors import ConfigurationError
from codontrace.preregistration.manifest import PlanManifest, hash_plan

__all__ = [
    "ACCEPTED_LOG_CHECKPOINTS",
    "DEVIATIONS_RELPATH",
    "DIGEST_LINE",
    "LOCK_START_DIGEST",
    "LOCK_START_ENTRY_SHA256",
    "deviations_log_entries",
    "plan_digest_from_files",
    "verify_deviations_log",
    "verify_jr5_record_at_root",
    "verify_jr5_record_bytes",
]

DEVIATIONS_RELPATH = "docs/prereg/jr5/DEVIATIONS.md"
DIGEST_LINE = re.compile(r"^- Record digest: `([0-9a-f]{64})` -> `([0-9a-f]{64})`$", re.M)
ENTRY_HEADING = re.compile(r"^## ", re.M)
_APPENDED_TAIL = re.compile(rb"\A\n*(?:## |\Z)")

# Record digest at the lock (phase 1 merged to main as 7d7ab8a): the old
# digest of the first log entry.
LOCK_START_DIGEST = "633aa9c84336e946fc7d8e3e2178acc658caeed791f5a484bbe7d0814264b757"
# sha256 of the first entry's UTF-8 text, from its "## " heading up to the
# next heading.
LOCK_START_ENTRY_SHA256 = "be3db2e183e371f013ea52cd1581a72f508d4dc035d7213734372f8fe27f2f67"
# (byte length, sha256) of the log text up to the end of an accepted entry,
# oldest first. A new checkpoint is added only by a reviewed change.
ACCEPTED_LOG_CHECKPOINTS: tuple[tuple[int, str], ...] = (
    # As merged to main in a01c950 (PR 136): three entries.
    (5452, "9b4f42ff11605453e3ccd8e546f1965a949f3fa46a42034bb286b4062820146a"),
    # Through the 2026-11-09 entry on the commit that made selfing two meioses plus fusion.
    (9117, "cf202b488e356206f6a19da7eeded08d43618b802c2f04adf815ff2b1abac98c"),
)


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


def deviations_log_entries(text: str) -> list[str]:
    """Each entry's text, from its ``## `` heading at a line start up to the next one."""

    starts = [match.start() for match in ENTRY_HEADING.finditer(text)]
    return [text[a:b] for a, b in zip(starts, [*starts[1:], len(text)], strict=True)]


def verify_deviations_log(text: str, *, expected_plan_digest: str) -> None:
    """Refuse a log that is not the pinned accepted log plus well-formed appended entries."""

    if not isinstance(text, str) or not text:
        raise ConfigurationError("DEVIATIONS.md must be non-empty text.")
    entries = deviations_log_entries(text)
    if not entries:
        raise ConfigurationError("DEVIATIONS.md must contain at least one dated entry.")
    pairs: list[tuple[str, str]] = []
    for entry in entries:
        found = DIGEST_LINE.findall(entry)
        if len(found) != 1:
            raise ConfigurationError("each DEVIATIONS.md entry must have exactly one record-digest line.")
        pairs.append(found[0])
    if pairs[0][0] != LOCK_START_DIGEST:
        raise ConfigurationError("DEVIATIONS.md first entry does not start at the lock digest.")
    if hashlib.sha256(entries[0].encode("utf-8")).hexdigest() != LOCK_START_ENTRY_SHA256:
        raise ConfigurationError("DEVIATIONS.md first entry is not the pinned lock-start entry.")
    raw = text.encode("utf-8")
    for size, digest in ACCEPTED_LOG_CHECKPOINTS:
        if len(raw) < size or hashlib.sha256(raw[:size]).hexdigest() != digest:
            raise ConfigurationError(
                "DEVIATIONS.md does not start with the accepted log; an accepted entry was edited or removed."
            )
    if ACCEPTED_LOG_CHECKPOINTS and not _APPENDED_TAIL.match(raw[ACCEPTED_LOG_CHECKPOINTS[-1][0] :]):
        raise ConfigurationError("DEVIATIONS.md text after the accepted log must be whole appended entries.")
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
