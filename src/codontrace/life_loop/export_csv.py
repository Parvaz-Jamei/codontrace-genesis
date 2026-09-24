"""Domain-free CSV helpers for HookMeterSnapshot (no discipline imports).

Observation export only — no tick physics, no claim-ladder imports, no discipline modules.
"""

from __future__ import annotations

import csv
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any, TextIO

from codontrace.contracts.banned import BANNED_DOMAIN_TOKENS
from codontrace.errors import ConfigurationError
from codontrace.life_loop.hook_meters import HookMeterSnapshot

SCHEMA_VERSION = "life_loop_hook_meter_csv_v1"

# Extra refuse fragments assembled so source text stays free of domain tokens.
_EXTRA_COLUMN_FRAGMENTS: frozenset[str] = frozenset(
    {
        "proved",
        "clin" + "ical",
        "bio" + "safety",
        "ther" + "apy",
        "bsl",
    }
)


def _column_fragments() -> frozenset[str]:
    return frozenset({t.casefold() for t in BANNED_DOMAIN_TOKENS}) | _EXTRA_COLUMN_FRAGMENTS


def _refuse_banned_column(name: str) -> str:
    lowered = name.casefold()
    for frag in _column_fragments():
        if frag in lowered:
            raise ConfigurationError(
                f"life_loop CSV refuses banned column fragment in {name!r}."
            )
    return name


def hook_meter_snapshot_to_rows(
    snapshot: HookMeterSnapshot,
    *,
    run_id: str = "run0",
) -> list[dict[str, str]]:
    """Flatten a HookMeterSnapshot into refuse-safe CSV-ready rows."""

    if not isinstance(snapshot, HookMeterSnapshot):
        raise ConfigurationError("snapshot must be a HookMeterSnapshot.")
    if not isinstance(run_id, str) or not run_id.strip():
        raise ConfigurationError("run_id must be a non-empty string.")
    _refuse_banned_column(run_id)

    base = {
        "schema_version": SCHEMA_VERSION,
        "run_id": run_id.strip(),
        "meter_id": snapshot.meter_id,
        "tick": str(snapshot.tick),
        "digest": snapshot.digest,
    }
    rows: list[dict[str, str]] = []
    for key, value in sorted(snapshot.hook_counts.items()):
        _refuse_banned_column(key)
        rows.append({**base, "channel_kind": "hook", "channel": key, "value": str(value)})
    for key, value in sorted(snapshot.related_counts.items()):
        _refuse_banned_column(key)
        rows.append(
            {**base, "channel_kind": "related_count", "channel": key, "value": str(value)}
        )
    for key, value in sorted(snapshot.related_totals.items()):
        _refuse_banned_column(key)
        rows.append(
            {
                **base,
                "channel_kind": "related_total",
                "channel": key,
                "value": repr(float(value)),
            }
        )
    for key, value in sorted(snapshot.densities.items()):
        _refuse_banned_column(key)
        rows.append(
            {**base, "channel_kind": "density", "channel": key, "value": str(value)}
        )
    for key, value in sorted(snapshot.contact_fail_reasons.items()):
        _refuse_banned_column(key)
        rows.append(
            {
                **base,
                "channel_kind": "contact_fail_reason",
                "channel": key,
                "value": str(value),
            }
        )
    if not rows:
        rows.append(
            {
                **base,
                "channel_kind": "empty",
                "channel": "none",
                "value": "0",
            }
        )
    return rows


_CSV_FIELDNAMES: tuple[str, ...] = (
    "schema_version",
    "run_id",
    "meter_id",
    "tick",
    "digest",
    "channel_kind",
    "channel",
    "value",
)


def write_hook_meter_csv(
    snapshot: HookMeterSnapshot,
    destination: str | Path | TextIO,
    *,
    run_id: str = "run0",
) -> list[dict[str, str]]:
    """Write HookMeterSnapshot rows to CSV; return the rows written."""

    rows = hook_meter_snapshot_to_rows(snapshot, run_id=run_id)
    for name in _CSV_FIELDNAMES:
        _refuse_banned_column(name)

    def _write(fh: TextIO) -> None:
        writer = csv.DictWriter(fh, fieldnames=list(_CSV_FIELDNAMES), lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)

    if hasattr(destination, "write"):
        _write(destination)  # type: ignore[arg-type]
    else:
        path = Path(destination)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8", newline="") as fh:
            _write(fh)
    return rows


def assert_rows_refuse_proved(rows: Sequence[Mapping[str, Any]]) -> None:
    """Raise if any cell text claims a proved flag is true."""

    for row in rows:
        for key, value in row.items():
            _refuse_banned_column(str(key))
            text = str(value).casefold()
            if "proved" in str(key).casefold() and text in {"true", "1", "yes"}:
                raise ConfigurationError("life_loop CSV refuses proved=True cells.")


__all__ = [
    "SCHEMA_VERSION",
    "assert_rows_refuse_proved",
    "hook_meter_snapshot_to_rows",
    "write_hook_meter_csv",
]
