"""Phase 10 — Refuse-safe JSON/CSV export for meters, prereg, analytics.

Does not invent proved flags, clinical columns, or ClaimGate allows.
Observation / instrumentation only; digests always included.
"""

from __future__ import annotations

import csv
import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any, TextIO

from codontrace.contracts.banned import BANNED_DOMAIN_TOKENS
from codontrace.errors import ConfigurationError
from codontrace.genesis.canonical import canonical_digest
from codontrace.genesis.host_parasite_metrics import (
    HostParasiteMetricSummary,
    HostParasitePreregSpec,
)
from codontrace.life_loop.hook_meters import HookMeterSnapshot

SCHEMA_METER = "host_parasite_export_meter_v1"
SCHEMA_SUMMARY = "host_parasite_export_metric_summary_v1"
SCHEMA_PREREG = "host_parasite_export_prereg_v1"
SCHEMA_WORLD = "host_parasite_export_world_summary_v1"
SCHEMA_ANALYTICS = "host_parasite_export_analytics_v1"
SCHEMA_CALIBRATION = "host_parasite_export_calibration_v1"

_HONESTY_FALSE_COLUMNS: tuple[str, ...] = (
    "red_queen_proved",
    "intervention_supported",
    "raises_claim_ladder",
    "mutualism_equals_success",
)

_BANNED_EXPORT_FRAGMENTS: frozenset[str] = frozenset(
    {
        "phage",
        "vaccine",
        "clinical",
        "biosafety",
        "bsl",
        "therapy",
        "infection",
        "virulence",
        "crispr",
    }
)


def _as_str(value: object, name: str, *, allow_empty: bool = False) -> str:
    if not isinstance(value, str):
        raise ConfigurationError(f"{name} must be a string.")
    text = value.strip()
    if not text and not allow_empty:
        raise ConfigurationError(f"{name} must be a non-empty string.")
    return text


def _refuse_banned_fragment(text: str, name: str) -> str:
    lowered = text.casefold()
    # Honesty False columns intentionally contain refused claim nouns.
    if text in _HONESTY_FALSE_COLUMNS:
        return text
    for token in BANNED_DOMAIN_TOKENS:
        if token.casefold() in lowered:
            raise ConfigurationError(f"{name} contains a banned fragment.")
    for frag in _BANNED_EXPORT_FRAGMENTS:
        if frag in lowered:
            raise ConfigurationError(
                f"{name} contains refused export fragment {frag!r}."
            )
    return text


def _refuse_proved_true(payload: Mapping[str, Any]) -> None:
    for key, value in payload.items():
        k = str(key).casefold()
        if k.endswith("_proved") or k in {
            "intervention_supported",
            "raises_claim_ladder",
            "mutualism_equals_success",
        }:
            if value is True or str(value).casefold() in {"true", "1", "yes"}:
                raise ConfigurationError(
                    f"export refuses {key}=True (honesty-forced False only)."
                )


def _force_honesty(row: dict[str, Any]) -> dict[str, Any]:
    out = dict(row)
    for col in _HONESTY_FALSE_COLUMNS:
        out[col] = False
    _refuse_proved_true(out)
    return out


def _validate_columns(columns: Sequence[str]) -> tuple[str, ...]:
    cleaned: list[str] = []
    for col in columns:
        name = _refuse_banned_fragment(_as_str(col, "column"), "column")
        if name.casefold().endswith("_proved") and name not in _HONESTY_FALSE_COLUMNS:
            # Only the known honesty False columns may carry a proved suffix.
            if name not in {"red_queen_proved"}:
                raise ConfigurationError(
                    f"export refuses invented proved column {name!r}."
                )
        cleaned.append(name)
    return tuple(cleaned)


def meter_snapshot_rows(
    snapshot: HookMeterSnapshot, *, run_id: str = "run0"
) -> list[dict[str, Any]]:
    """Export HookMeterSnapshot as flat refuse-safe rows."""

    if not isinstance(snapshot, HookMeterSnapshot):
        raise ConfigurationError("snapshot must be a HookMeterSnapshot.")
    rid = _refuse_banned_fragment(_as_str(run_id, "run_id"), "run_id")
    rows: list[dict[str, Any]] = []
    base = {
        "schema_version": SCHEMA_METER,
        "run_id": rid,
        "meter_id": snapshot.meter_id,
        "tick": snapshot.tick,
        "digest": snapshot.digest,
    }
    for kind, mapping in (
        ("hook", snapshot.hook_counts),
        ("related_count", snapshot.related_counts),
        ("related_total", snapshot.related_totals),
        ("density", snapshot.densities),
        ("contact_fail_reason", snapshot.contact_fail_reasons),
    ):
        for channel, value in sorted(mapping.items()):
            _refuse_banned_fragment(channel, "channel")
            row = _force_honesty(
                {
                    **base,
                    "channel_kind": kind,
                    "channel": channel,
                    "value": value,
                }
            )
            rows.append(row)
    if not rows:
        rows.append(
            _force_honesty({**base, "channel_kind": "empty", "channel": "none", "value": 0})
        )
    return rows


def metric_summary_row(summary: HostParasiteMetricSummary) -> dict[str, Any]:
    if not isinstance(summary, HostParasiteMetricSummary):
        raise ConfigurationError("summary must be a HostParasiteMetricSummary.")
    body = summary.to_dict()
    row: dict[str, Any] = {
        "schema_version": SCHEMA_SUMMARY,
        "summary_id": body["summary_id"],
        "claim_role": body["claim_role"],
        "meter_digest": body["meter_digest"],
        "prereg_digest": body.get("prereg_digest") or "",
        "science_grade": body["science_grade"],
        "ablation_preset": body["ablation_preset"],
        "digest": body["digest"],
    }
    for mid, value in sorted(dict(body["metrics"]).items()):
        row[f"metric_{mid}"] = value
    return _force_honesty(row)


def prereg_row(prereg: HostParasitePreregSpec) -> dict[str, Any]:
    if not isinstance(prereg, HostParasitePreregSpec):
        raise ConfigurationError("prereg must be a HostParasitePreregSpec.")
    body = prereg.to_dict()
    return _force_honesty(
        {
            "schema_version": SCHEMA_PREREG,
            "prereg_id": body["prereg_id"],
            "phenomenon": body["phenomenon"],
            "metric_ids": ",".join(body["metric_ids"]),
            "dual_null_required": body["dual_null_required"],
            "ci_plan": body["ci_plan"],
            "planned_claim_ceiling": body["planned_claim_ceiling"],
            "refuse_list": ",".join(body["refuse_list"]),
            "digest": body["digest"],
            "seed_plan_digest": body["seed_plan"]["digest"]
            if isinstance(body.get("seed_plan"), Mapping)
            else "",
        }
    )


def world_summary_row(summary: Mapping[str, Any], *, run_id: str = "run0") -> dict[str, Any]:
    if not isinstance(summary, Mapping):
        raise ConfigurationError("summary must be a mapping.")
    rid = _refuse_banned_fragment(_as_str(run_id, "run_id"), "run_id")
    census = summary.get("census") or {}
    if not isinstance(census, Mapping):
        raise ConfigurationError("census must be a mapping.")
    return _force_honesty(
        {
            "schema_version": SCHEMA_WORLD,
            "run_id": rid,
            "profile_id": summary.get("profile_id", ""),
            "profile_digest": summary.get("profile_digest", ""),
            "tick": summary.get("tick", 0),
            "world_digest": summary.get("world_digest", ""),
            "meter_digest": summary.get("meter_digest", ""),
            "census_primary": int(census.get("primary", 0)),
            "census_secondary": int(census.get("secondary", 0)),
            "ablation_preset": summary.get("ablation_preset", ""),
            "schedule_arm": summary.get("schedule_arm", ""),
            "physics_home": summary.get("physics_home", "codontrace.life_loop"),
        }
    )


def analytics_payload_row(
    payload: Mapping[str, Any], *, kind: str, run_id: str = "run0"
) -> dict[str, Any]:
    """Flatten a Phase 9 analytics to_dict payload into one refuse-safe row."""

    if not isinstance(payload, Mapping):
        raise ConfigurationError("payload must be a mapping.")
    kind_s = _refuse_banned_fragment(_as_str(kind, "kind"), "kind")
    rid = _refuse_banned_fragment(_as_str(run_id, "run_id"), "run_id")
    digest = payload.get("digest", "")
    if not digest:
        raise ConfigurationError("analytics payload requires digest.")
    row: dict[str, Any] = {
        "schema_version": SCHEMA_ANALYTICS,
        "run_id": rid,
        "analytics_kind": kind_s,
        "digest": digest,
        "schema_payload": payload.get("schema_version", ""),
    }
    for key in (
        "factorial_id",
        "contrast_id",
        "continuum_physics_source",
        "claim_ceiling",
        "smoke_only",
        "science_grade",
        "identifiability",
        "effect_delta",
        "channel_delta_unlock_minus_freeze",
    ):
        if key in payload:
            row[key] = payload[key]
    return _force_honesty(row)


def calibration_report_rows(report: Mapping[str, Any]) -> list[dict[str, Any]]:
    if not isinstance(report, Mapping):
        raise ConfigurationError("report must be a mapping.")
    outcomes = report.get("outcomes") or []
    if not isinstance(outcomes, Sequence) or isinstance(outcomes, (str, bytes)):
        raise ConfigurationError("outcomes must be a sequence.")
    rows: list[dict[str, Any]] = []
    base = {
        "schema_version": SCHEMA_CALIBRATION,
        "report_id": report.get("report_id", ""),
        "report_digest": report.get("digest", ""),
    }
    for item in outcomes:
        if not isinstance(item, Mapping):
            raise ConfigurationError("each outcome must be a mapping.")
        rows.append(
            _force_honesty(
                {
                    **base,
                    "target_id": item.get("target_id", ""),
                    "outcome": item.get("outcome", ""),
                    "reason": item.get("reason", ""),
                    "observed_digest": item.get("observed_digest", ""),
                    "literature_note": item.get("literature_note", ""),
                }
            )
        )
    if not rows:
        rows.append(
            _force_honesty(
                {
                    **base,
                    "target_id": "none",
                    "outcome": "deferred",
                    "reason": "empty_report",
                    "observed_digest": "",
                    "literature_note": "",
                }
            )
        )
    return rows


def write_json(payload: Mapping[str, Any] | Sequence[Any], destination: str | Path | TextIO) -> str:
    """Write canonical JSON; return digest of the written body."""

    text = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    digest = canonical_digest(payload if isinstance(payload, Mapping) else {"rows": list(payload)}, prefix="hp_export_json")
    if hasattr(destination, "write"):
        destination.write(text)  # type: ignore[union-attr]
        if not text.endswith("\n"):
            destination.write("\n")  # type: ignore[union-attr]
    else:
        path = Path(destination)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text + "\n", encoding="utf-8")
    return digest


def write_csv_rows(
    rows: Sequence[Mapping[str, Any]],
    destination: str | Path | TextIO,
    *,
    fieldnames: Sequence[str] | None = None,
) -> tuple[str, ...]:
    """Write rows as CSV; validate columns; return fieldnames used."""

    if not rows:
        raise ConfigurationError("rows must be non-empty.")
    for row in rows:
        _refuse_proved_true(row)
    if fieldnames is None:
        keys: list[str] = []
        seen: set[str] = set()
        for row in rows:
            for key in row:
                if key not in seen:
                    seen.add(key)
                    keys.append(str(key))
        # Stable: honesty columns last if present.
        fieldnames = tuple(keys)
    cols = _validate_columns(fieldnames)

    def _write(fh: TextIO) -> None:
        writer = csv.DictWriter(fh, fieldnames=list(cols), extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        for row in rows:
            safe = {c: row.get(c, "") for c in cols}
            for col in _HONESTY_FALSE_COLUMNS:
                if col in safe:
                    safe[col] = False
            _refuse_proved_true(safe)
            writer.writerow(safe)

    if hasattr(destination, "write"):
        _write(destination)  # type: ignore[arg-type]
    else:
        path = Path(destination)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8", newline="") as fh:
            _write(fh)
    return cols


__all__ = [
    "SCHEMA_ANALYTICS",
    "SCHEMA_CALIBRATION",
    "SCHEMA_METER",
    "SCHEMA_PREREG",
    "SCHEMA_SUMMARY",
    "SCHEMA_WORLD",
    "analytics_payload_row",
    "calibration_report_rows",
    "meter_snapshot_rows",
    "metric_summary_row",
    "prereg_row",
    "world_summary_row",
    "write_csv_rows",
    "write_json",
]
