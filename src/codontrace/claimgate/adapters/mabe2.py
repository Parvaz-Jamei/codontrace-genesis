"""MABE2 DataFile CSV skeleton adapter.

Format notes (coordinator search 2026-09-12):

- MABE2 ``DataFile`` uses ``ADD_COLUMN(name, expr)`` then ``WRITE``.
- A ``.csv`` filename is written as CSV.

This is a skeleton. It does **not** claim full MABE2 support,
literature compatibility, or audited published DataFile CSV parity.
Do not cite this adapter as evidence until a real published CSV
export is ingested and reviewed.
"""

from __future__ import annotations

import csv
import hashlib
import io
from collections.abc import Mapping, Sequence
from pathlib import Path

from codontrace.claimgate.schema import (
    ARM_ROLES,
    ClaimgateArm,
    ClaimgateArtifact,
    ClaimgateBundle,
    ClaimgateOutcome,
    ClaimgateReplay,
    ClaimgateSoftware,
    parse_claimgate_bundle,
)
from codontrace.errors import ConfigurationError
from codontrace.genesis.canonical import canonical_digest

PRODUCT_NAME = "MABE2 (ClaimGate skeleton)"


def parse_mabe2_csv(text: str) -> tuple[tuple[str, ...], tuple[tuple[str, ...], ...]]:
    """Parse a MABE2 DataFile CSV export."""

    reader = csv.reader(io.StringIO(text))
    try:
        header = next(reader)
    except StopIteration as exc:
        raise ConfigurationError("MABE2 CSV is empty.") from exc
    columns = tuple(item.strip() for item in header if item.strip())
    if not columns:
        raise ConfigurationError("MABE2 CSV requires a header row.")
    rows: list[tuple[str, ...]] = []
    for raw in reader:
        if not raw or all(not cell.strip() for cell in raw):
            continue
        rows.append(tuple(cell.strip() for cell in raw))
    return columns, tuple(rows)


def bundle_from_mabe2_csv(
    path: Path | str,
    *,
    arm_name: str,
    arm_role: str,
    seeds: Sequence[int],
    metric: str,
    software_version: str = "unknown",
    commit: str = "",
    config_digest: str | None = None,
    extra_arm_map: Mapping[str, str] | None = None,
) -> ClaimgateBundle:
    """Skeleton bundle from one MABE2 DataFile CSV.

    ``extra_arm_map`` is accepted for multi-file campaigns later. Full MABE2
    support is **not** claimed.
    """

    if arm_role not in ARM_ROLES:
        raise ConfigurationError("MABE2 arm_role must be a ClaimGate arm role.")
    if extra_arm_map:
        for role in extra_arm_map.values():
            if role not in ARM_ROLES:
                raise ConfigurationError("MABE2 extra_arm_map roles must be ClaimGate roles.")
    file_path = Path(path)
    if file_path.suffix.lower() != ".csv":
        raise ConfigurationError("MABE2 DataFile CSV adapter expects a .csv filename.")
    if not file_path.is_file():
        raise ConfigurationError(f"MABE2 CSV not found: {file_path}")
    if not seeds:
        raise ConfigurationError("MABE2 adapter requires a user-supplied seed list.")
    columns, rows = parse_mabe2_csv(file_path.read_text(encoding="utf-8"))
    if metric not in columns:
        raise ConfigurationError(f"MABE2 CSV has no column {metric!r}.")
    metric_index = columns.index(metric)
    values: list[float] = []
    for row in rows:
        if metric_index >= len(row):
            continue
        try:
            values.append(float(row[metric_index]))
        except ValueError as exc:
            raise ConfigurationError("MABE2 metric column must be numeric.") from exc
    digest_source = {
        "adapter": "mabe2_skeleton",
        "path": str(file_path),
        "metric": metric,
        "arm": arm_name,
    }
    bundle = ClaimgateBundle(
        software=ClaimgateSoftware(
            name=PRODUCT_NAME, version=software_version, commit=commit
        ),
        seeds=tuple(int(item) for item in seeds),
        config_digest=config_digest or canonical_digest(digest_source),
        arms=(ClaimgateArm(name=arm_name, role=arm_role, n=len(seeds)),),
        outcomes=(
            ClaimgateOutcome(metric=metric, values_by_arm={arm_name: tuple(values)}),
        ),
        comparisons=(),
        replay=ClaimgateReplay(verified=False, digests=()),
        artifacts=(
            ClaimgateArtifact(
                path=str(file_path.as_posix()),
                sha256=hashlib.sha256(file_path.read_bytes()).hexdigest(),
            ),
        ),
        limitations=(
            "mabe2_csv_skeleton_only",
            "datafile_add_column_write_not_executed",
            "not_full_mabe2_support",
            "not_avida_or_mabe_replacement",
        ),
        extra={
            "adapter": "mabe2_skeleton",
            "full_mabe2_support": False,
            "tokyo_type1_passed": False,
            "avida_replacement": False,
        },
    )
    return parse_claimgate_bundle(bundle)
