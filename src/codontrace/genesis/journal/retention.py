"""Pure retention planning: which closed segments to archive and which archived ones to delete."""
from __future__ import annotations

from collections.abc import Sequence

__all__ = ['archived_to_delete', 'segments_to_archive']


def segments_to_archive(rows: Sequence[tuple[int, int]], live_bytes: int, retention_bytes: int,
                        covered: int) -> list[int]:
    """Oldest-first closed segments ``(index, size)`` to move to the archive.

    Stops once live bytes fit ``retention_bytes`` and never reaches the
    checkpoint's own segment ``covered`` (its tail binds the checkpoint).
    """
    out = []
    for index, size in rows:
        if live_bytes <= retention_bytes or index >= covered:
            break
        out.append(index)
        live_bytes -= size
    return out


def archived_to_delete(rows: Sequence[tuple[int, int]], archive_max_bytes: int) -> list[int]:
    """Oldest-first archived segments to delete until the total is at most ``archive_max_bytes``."""
    total = sum(size for _, size in rows)
    out = []
    for index, size in rows:
        if total <= archive_max_bytes:
            break
        total -= size
        out.append(index)
    return out
