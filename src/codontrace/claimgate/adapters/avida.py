"""Avida `.dat` skeleton adapter.

Format notes (avidaR / PrintData wiki, coordinator search 2026-09-12):

- Files are whitespace-separated.
- Column names live in comment lines ``# N: column name``.
- Each run directory is treated as one seed.
- Arm mapping is user-supplied.
- The primary series is a fitness-like column (``ave_fitness`` first),
  never the leading ``update`` clock column.
- Directories that share a ClaimGate role are aggregated into one arm.

This is a skeleton. It does **not** claim full Avida support,
literature compatibility, or audited published `.dat` campaign parity.
Do not cite this adapter as evidence until a real published `.dat`
run is ingested and reviewed.
"""

from __future__ import annotations

import hashlib
import re
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

_HEADER_RE = re.compile(r"^#\s*(\d+)\s*:\s*(.+?)\s*$")
PRODUCT_NAME = "Avida (ClaimGate skeleton)"
PREFERRED_METRICS: tuple[str, ...] = (
    "ave_fitness",
    "average_fitness",
    "mean_fitness",
    "fitness",
)
SKIP_METRICS = frozenset({"update", "updates", "time", "timestep", "generation"})


def parse_avida_dat(text: str) -> tuple[tuple[str, ...], tuple[tuple[float, ...], ...]]:
    """Parse a whitespace-separated Avida `.dat` with ``# N:`` headers."""

    names: dict[int, str] = {}
    rows: list[tuple[float, ...]] = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        header = _HEADER_RE.match(line)
        if header:
            names[int(header.group(1))] = header.group(2).strip()
            continue
        if line.startswith("#"):
            continue
        parts = line.split()
        try:
            rows.append(tuple(float(item) for item in parts))
        except ValueError as exc:
            raise ConfigurationError("Avida .dat data rows must be numeric.") from exc
    if not names:
        raise ConfigurationError("Avida .dat requires '# N: column name' headers.")
    columns = tuple(names[index] for index in sorted(names))
    width = max((len(row) for row in rows), default=len(columns))
    if width < len(columns):
        raise ConfigurationError("Avida .dat rows have fewer columns than headers.")
    return columns, tuple(rows)


def _read_run_directory(path: Path) -> tuple[dict[str, list[float]], list[ClaimgateArtifact]]:
    metrics: dict[str, list[float]] = {}
    artifacts: list[ClaimgateArtifact] = []
    files = sorted(path.glob("*.dat"))
    if not files:
        raise ConfigurationError(f"Avida run directory has no .dat files: {path}")
    for file_path in files:
        columns, rows = parse_avida_dat(file_path.read_text(encoding="utf-8"))
        artifacts.append(
            ClaimgateArtifact(
                path=str(file_path.as_posix()),
                sha256=hashlib.sha256(file_path.read_bytes()).hexdigest(),
            )
        )
        for index, name in enumerate(columns):
            series = [row[index] for row in rows if index < len(row)]
            if series:
                metrics.setdefault(name, []).extend(series)
    return metrics, artifacts


def _pick_metric(metrics: Mapping[str, list[float]]) -> tuple[str, list[float]]:
    for name in PREFERRED_METRICS:
        series = metrics.get(name)
        if series:
            return name, series
    for name, series in metrics.items():
        if name.lower() not in SKIP_METRICS and series:
            return name, series
    raise ConfigurationError("Avida .dat has no fitness-like column (expected ave_fitness).")


def bundle_from_avida_runs(
    run_dirs: Sequence[Path | str],
    arm_map: Mapping[str, str],
    *,
    software_version: str = "unknown",
    commit: str = "",
    config_digest: str | None = None,
) -> ClaimgateBundle:
    """Skeleton bundle: one directory per seed; ``arm_map`` is required.

    ``arm_map`` keys are directory names (or paths) and values are ClaimGate
    arm roles. Folders that share a role are one arm. Full Avida / avida.cfg
    support is **not** claimed.
    """

    if not run_dirs:
        raise ConfigurationError("Avida adapter requires at least one run directory.")
    if not arm_map:
        raise ConfigurationError("Avida arm mapping is user-supplied and required.")
    seeds: list[int] = []
    artifacts: list[ClaimgateArtifact] = []
    values_by_role: dict[str, list[float]] = {}
    counts_by_role: dict[str, int] = {}
    metric_name = "ave_fitness"
    for index, raw in enumerate(run_dirs, start=1):
        path = Path(raw)
        if not path.is_dir():
            raise ConfigurationError(f"Avida run path is not a directory: {path}")
        role = arm_map.get(path.name) or arm_map.get(str(path)) or arm_map.get(path.as_posix())
        if role not in ARM_ROLES:
            raise ConfigurationError(
                "Avida arm_map must assign each run folder a ClaimGate role."
            )
        metrics, found = _read_run_directory(path)
        artifacts.extend(found)
        seeds.append(index)
        name, series = _pick_metric(metrics)
        metric_name = name
        if not series:
            raise ConfigurationError(f"Avida run directory has an empty metric series: {path}")
        values_by_role.setdefault(role, []).append(series[-1])
        counts_by_role[role] = counts_by_role.get(role, 0) + 1
    digest_source = {
        "adapter": "avida_skeleton",
        "runs": [str(Path(item)) for item in run_dirs],
        "arm_map": dict(sorted(arm_map.items())),
    }
    resolved_digest = config_digest or canonical_digest(digest_source)
    arms = tuple(
        ClaimgateArm(name=role, role=role, n=counts_by_role[role])
        for role in counts_by_role
    )
    bundle = ClaimgateBundle(
        software=ClaimgateSoftware(
            name=PRODUCT_NAME, version=software_version, commit=commit
        ),
        seeds=tuple(seeds),
        config_digest=resolved_digest,
        arms=arms,
        outcomes=(
            ClaimgateOutcome(
                metric=metric_name,
                values_by_arm={role: tuple(values) for role, values in values_by_role.items()},
            ),
        ),
        comparisons=(),
        replay=ClaimgateReplay(verified=False, digests=()),
        artifacts=tuple(artifacts),
        limitations=(
            "avida_dat_skeleton_only",
            "run_directory_equals_one_seed",
            "arm_mapping_is_user_supplied",
            "not_full_avida_support",
            "not_avida_replacement",
        ),
        extra={
            "adapter": "avida_skeleton",
            "full_avida_support": False,
            "tokyo_type1_passed": False,
            "avida_replacement": False,
        },
    )
    return parse_claimgate_bundle(bundle)
