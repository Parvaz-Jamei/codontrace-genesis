"""Bounded, read-only scientific tools over local run artifacts.

Numerics run on the host; LLMs select tools, never execute arbitrary code.
A plot is descriptive data, not a hypothesis verdict. No evolution-engine imports.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import statistics
import subprocess
from pathlib import Path
from typing import Any

from codontrace.console.runs import get_run_details, get_safe_run_dir, list_simulation_runs, runs_directory
from codontrace.rng import RNGManager

MAX_BYTES = 8 * 1024 * 1024
MAX_RECORDS = 20000
MAX_SIBLINGS = 64


def _schema(**properties: Any) -> dict[str, Any]:
    return {"type": "object", "properties": properties, "additionalProperties": False}


from .chart_builder import KINDS, PALETTES, build_chart

COMMON = {
    "run_id": {"type": "string", "description": "Selected run ID; never a filesystem path."},
    "metric": {"type": "string", "description": "Numeric metric key; omitted selects primary metric."},
    "seed_from": {"type": "integer", "minimum": 0},
    "seed_to": {"type": "integer", "minimum": 0},
    "generation_from": {"type": "integer", "minimum": 0},
    "generation_to": {"type": "integer", "minimum": 0},
    "arm": {"type": "string", "description": "Exact recorded arm label."},
    "max_points": {"type": "integer", "minimum": 8, "maximum": 2000, "default": 400},
}

DEFINITIONS = (
    (
        "scientific_plot",
        "Scientific chart studio",
        "Two modes: raw (default, no options) plots selected run as recorded; tool permits bounded filters/style. No arbitrary code, smoothing or inferred verdict. inspect_run lists metric keys.",
        _schema(
            **COMMON,
            mode={"type": "string", "enum": ["raw", "tool"], "default": "raw"},
            chart={"type": "string", "enum": list(KINDS), "default": "auto"},
            palette={"type": "string", "enum": list(PALETTES)},
            x_scale={"type": "string", "enum": ["linear", "log"]},
            y_scale={"type": "string", "enum": ["linear", "log"]},
            bins={"type": "integer", "minimum": 4, "maximum": 80},
            **{
                k: {"type": "string"}
                for k in (
                    "x_metric",
                    "size_metric",
                    "lower_metric",
                    "upper_metric",
                    "metrics",
                    "title",
                    "x_label",
                    "y_label",
                )
            },
        ),
    ),
    (
        "inspect_run",
        "Inspect selected run",
        "Read status, evidence and metric inventory in every lifecycle state.",
        _schema(run_id=COMMON["run_id"]),
    ),
    (
        "list_projects",
        "Local projects",
        "List registered local simulations only when explicitly requested; no filesystem or process secrets.",
        _schema(),
    ),
    (
        "board_processes",
        "Board processes",
        "Opt-in process names/PID/load only; no command arguments or unrelated files.",
        _schema(),
    ),
    (
        "metric_series",
        "Scientific time series",
        "Plot recorded fitness, loss, reward or any numeric metric; keeps extrema when downsampling.",
        _schema(**COMMON),
    ),
    (
        "seed_comparison",
        "Compare seeds and arms",
        "Compare the last observed value per seed/arm within this campaign; excludes synthetic rows.",
        _schema(**COMMON),
    ),
    (
        "time_shift_heatmap",
        "Host–parasite time shift",
        "Show measured archived host/parasite assays with real generation labels; no fabricated cells.",
        _schema(run_id=COMMON["run_id"]),
    ),
    (
        "price_decomposition",
        "Price decomposition",
        "Plot realized between/within selection, transmission and regulation terms when recorded.",
        _schema(**COMMON),
    ),
    (
        "diversity_curve",
        "Diversity and learning",
        "Plot recorded Shannon diversity or archive coverage; does not infer diversity from survival.",
        _schema(**COMMON),
    ),
    (
        "effect_summary",
        "Seed-level uncertainty",
        "Descriptive bootstrap intervals across independent seed endpoints, separately for each arm; not a confirmation test.",
        _schema(**COMMON),
    ),
    (
        "mathematical_summary",
        "Mathematical output",
        "Return precise equations and definitions with selected-run evidence scope.",
        _schema(run_id=COMMON["run_id"]),
    ),
    (
        "reproducibility_code",
        "Recompute locally",
        "Show a read-only Python snippet for raw JSONL; it is displayed, never executed by the chat.",
        _schema(run_id=COMMON["run_id"]),
    ),
    (
        "confusion_matrix",
        "AI confusion matrix",
        "Show an actual recorded classifier confusion matrix if one exists; never infer it from a score.",
        _schema(run_id=COMMON["run_id"]),
    ),
    (
        "pareto_front",
        "AI efficiency tradeoff",
        "Scatter recorded quality versus resource cost; requires both paired observations.",
        _schema(
            run_id=COMMON["run_id"],
            x_metric={"type": "string"},
            y_metric={"type": "string"},
            max_points=COMMON["max_points"],
        ),
    ),
)


def tool_catalog() -> list[dict[str, Any]]:
    return [
        {
            "name": n,
            "title": title,
            "description": desc,
            "parameters": params,
            "read_only": True,
            "requires_project_opt_in": n in {"list_projects", "board_processes"},
        }
        for n, title, desc, params in DEFINITIONS
    ]


def llm_tool_schemas(allow_cross_project: bool = False) -> list[dict[str, Any]]:
    return [
        {
            "type": "function",
            "function": {"name": row["name"], "description": row["description"], "parameters": row["parameters"]},
        }
        for row in tool_catalog()
        if allow_cross_project or not row["requires_project_opt_in"]
    ]


def _finite(value: Any) -> bool:
    return not isinstance(value, bool) and isinstance(value, (int, float)) and math.isfinite(value)


def _safe_file(folder: Path, relative: str) -> Path:
    path = (folder / relative).resolve()
    if not path.is_relative_to(folder.resolve()):
        raise ValueError("artifact points outside selected run")
    return path


def _metric_map(record: dict[str, Any]) -> dict[str, Any]:
    values = dict(record)
    for key in ("metrics", "secondary_metrics", "summary_metrics"):
        nested = record.get(key)
        if isinstance(nested, dict):
            values.update(nested)
    name = record.get("primary_metric_name")
    if isinstance(name, str):
        values[name] = record.get("primary_metric_value")
    return values


def _read_rows(
    folder: Path, *, byte_limit: int = MAX_BYTES, record_limit: int = MAX_RECORDS
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    rows: list[dict[str, Any]] = []
    evidence = []
    for relative in ("metrics.jsonl", "output/metrics.jsonl"):
        path = _safe_file(folder, relative)
        if not path.is_file():
            continue
        with path.open("rb") as f:
            size = os.fstat(f.fileno()).st_size
            start = max(0, size - byte_limit)
            f.seek(start)
            raw = f.read(byte_limit)
        if start:
            boundary = raw.find(b"\n")
            raw = raw[boundary + 1 :] if boundary >= 0 else b""
        malformed = 0
        local = []
        for line in raw.splitlines():
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except (ValueError, UnicodeDecodeError):
                malformed += 1
                continue
            if isinstance(row, dict):
                local.append(row)
            else:
                malformed += 1
        rows.extend(local[-record_limit:])
        evidence.append(
            {
                "path": relative,
                "snapshot_bytes": len(raw),
                "snapshot_sha256": hashlib.sha256(raw).hexdigest(),
                "truncated": bool(start or len(local) > record_limit),
                "malformed_rows": malformed,
                "records_read": len(local[-record_limit:]),
                "byte_budget": byte_limit,
                "record_budget": record_limit,
            }
        )
        # Root is authoritative; do not double-count a mirrored output stream.
        break
    return rows, evidence


def _context(run_id: str) -> tuple[dict[str, Any], Path, dict[str, Any]]:
    if not isinstance(run_id, str) or len(run_id) > 200:
        raise ValueError("valid run_id is required")
    folder = get_safe_run_dir(run_id, must_exist=True)
    if folder is None:
        raise ValueError("selected run not found")
    details = get_run_details(run_id)
    if details is None:
        raise ValueError("selected run not found")
    manifest = details.get("manifest") or {}
    provenance = {
        "run_id": run_id,
        "source_sha": manifest.get("source_sha") or manifest.get("sourceSha") or "UNKNOWN",
        "status": details.get("status"),
        "session_id": (details.get("snapshot") or {}).get("session_id"),
        "revision": (details.get("snapshot") or {}).get("revision"),
        "scope": details.get("executionBoundary"),
        "hypothesis_assessment": details.get("hypothesis_assessment"),
        "descriptive_only": True,
    }
    return details, folder, provenance


def _scope_key(manifest: dict[str, Any]) -> tuple[Any, Any]:
    params = manifest.get("params") or {}
    return (
        manifest.get("campaign_id") or params.get("campaign_id"),
        params.get("experiment") or manifest.get("experiment_id"),
    )


def _campaign_rows(
    details: dict[str, Any], folder: Path, *, include_campaign: bool = True
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    selected = details.get("manifest") or {}
    key = _scope_key(selected)
    candidates = [(folder, selected)]
    if include_campaign and key[0] is not None:
        # Bounded discovery only of the same explicitly identified campaign/experiment.
        for item in sorted(runs_directory().iterdir(), key=lambda p: p.name)[:1000]:
            if item.name == folder.name or not item.is_dir():
                continue
            safe = get_safe_run_dir(item.name, must_exist=True)
            if safe is None:
                continue
            for name in ("run_manifest.json", "manifest.json"):
                path = _safe_file(safe, name)
                if not path.is_file() or path.stat().st_size > 262144:
                    continue
                try:
                    manifest = json.loads(path.read_text(encoding="utf-8"))
                except (ValueError, OSError):
                    continue
                if isinstance(manifest, dict) and _scope_key(manifest) == key:
                    candidates.append((safe, manifest))
                break
            if len(candidates) >= MAX_SIBLINGS:
                break
    rows = []
    evidence = []
    for path, manifest in candidates:
        # One bounded aggregate budget, rather than 64 independent 8-MiB loads.
        local, sources = _read_rows(
            path, byte_limit=MAX_BYTES // len(candidates), record_limit=max(1, MAX_RECORDS // len(candidates))
        )
        params = manifest.get("params") or {}
        seed = params.get("seed", manifest.get("seed"))
        if seed is None and isinstance(params.get("seeds"), list) and len(params["seeds"]) == 1:
            seed = params["seeds"][0]
        arm = params.get("arm", manifest.get("arm", "DEFAULT"))
        for row in local:
            row = dict(row)
            row.setdefault("seed", seed)
            row.setdefault("arm", arm)
            row["_source_run_id"] = path.name
            rows.append(row)
        for src in sources:
            src["run_id"] = path.name
        evidence.extend(sources)
    return rows, evidence


def _downsample(points: list[list[float]], maximum: int) -> list[list[float]]:
    if len(points) <= maximum:
        return points
    # Endpoint + extrema in each chronological bucket, for plotting only.
    output = [points[0]]
    buckets = max(1, (maximum - 2) // 2)
    for b in range(buckets):
        first = 1 + (len(points) - 2) * b // buckets
        last = 1 + (len(points) - 2) * (b + 1) // buckets
        window = points[first:last]
        if not window:
            continue
        low = min(range(len(window)), key=lambda i: window[i][1])
        high = max(range(len(window)), key=lambda i: window[i][1])
        output.extend(window[i] for i in sorted(set((low, high))))
    output.append(points[-1])
    return output


def _numeric_series(
    rows: list[dict[str, Any]], metric: str | None, maximum: int
) -> tuple[list[dict[str, Any]], str, str]:
    groups: dict[str, list[list[float]]] = {}
    chosen = metric
    if chosen is None:
        chosen = next((r["primary_metric_name"] for r in rows if isinstance(r.get("primary_metric_name"), str)), None)
    if not chosen:
        raise ValueError("metric required: no primary metric recorded")
    eligible = [r for r in rows if r.get("synthetic") is not True and _finite(_metric_map(r).get(chosen))]
    axis = (
        "generation"
        if eligible and all(_finite(r.get("generation")) for r in eligible)
        else "tick"
        if eligible and all(_finite(r.get("tick")) for r in eligible)
        else "record_index"
    )
    for index, r in enumerate(eligible):
        x = r.get(axis, index)
        value = _metric_map(r)[chosen]
        label = f"seed {r.get('seed', '?')} · {r.get('arm', 'DEFAULT')} · {r.get('_source_run_id', 'selected')}"
        groups.setdefault(label, []).append([float(x), float(value)])
    if not groups:
        raise ValueError(f"metric '{chosen}' not recorded as finite numeric data")
    series = [
        {"name": name, "points": _downsample(sorted(points, key=lambda p: p[0]), maximum), "raw_points": len(points)}
        for name, points in groups.items()
    ]
    return series, chosen, axis


def _filter(rows: list[dict[str, Any]], args: dict[str, Any]) -> list[dict[str, Any]]:
    lo = args.get("seed_from")
    hi = args.get("seed_to")
    if lo is not None and hi is not None and lo > hi:
        raise ValueError("seed_from must be <= seed_to")
    gl, gh = args.get("generation_from"), args.get("generation_to")
    if gl is not None and gh is not None and gl > gh:
        raise ValueError("generation_from must be <= generation_to")
    rows = [
        r
        for r in rows
        if (args.get("arm") is None or r.get("arm") == args["arm"])
        and (
            (gl is None and gh is None)
            or (
                _finite(r.get("generation"))
                and (gl is None or r["generation"] >= gl)
                and (gh is None or r["generation"] <= gh)
            )
        )
    ]
    return [
        r
        for r in rows
        if (lo is None and hi is None)
        or (isinstance(r.get("seed"), int) and (lo is None or r["seed"] >= lo) and (hi is None or r["seed"] <= hi))
    ]


def _validate(name: str, args: dict[str, Any]) -> None:
    row = next((r for r in tool_catalog() if r["name"] == name), None)
    if row is None:
        raise ValueError("unknown scientific tool")
    properties = row["parameters"]["properties"]
    if any(k not in properties for k in args):
        raise ValueError("unknown tool parameter")
    for key, value in args.items():
        spec = properties[key]
        if "enum" in spec and value not in spec["enum"]:
            raise ValueError(f"invalid {key}")
        if spec["type"] == "integer":
            if (
                isinstance(value, bool)
                or not isinstance(value, int)
                or value < spec.get("minimum", 0)
                or value > spec.get("maximum", 2**31 - 1)
            ):
                raise ValueError(f"invalid {key}")
        elif not isinstance(value, str) or not value.strip() or len(value) > 200:
            raise ValueError(f"invalid {key}")


def invoke_tool(
    name: str,
    args: dict[str, Any] | None = None,
    *,
    selected_run_id: str | None = None,
    allow_cross_project: bool = False,
) -> dict[str, Any]:
    artifacts: list[dict[str, Any]] = []
    try:
        if not isinstance(args, (dict, type(None))):
            raise ValueError("tool args must be an object")
        args = dict(args or {})
        _validate(name, args)
        if name in {"list_projects", "board_processes"}:
            if allow_cross_project is not True:
                raise ValueError("explicit request to inspect other local projects/processes is required")
            if name == "list_projects":
                projects = list_simulation_runs()[:1000]
                artifacts = [
                    {
                        "kind": "table",
                        "columns": ["run_id", "title", "status", "pct"],
                        "rows": [[r.get("id"), r.get("title"), r.get("status"), r.get("pct")] for r in projects],
                        "provenance": {"scope": "registered_local_simulations", "descriptive_only": True},
                    }
                ]
            else:
                if os.name == "nt":
                    raise ValueError(
                        "process listing is unavailable on this platform; simulation registry remains available"
                    )
                try:
                    out = subprocess.check_output(
                        ["ps", "-eo", "pid,comm,pcpu,pmem", "--no-headers"], text=True, timeout=2
                    )
                except (OSError, subprocess.SubprocessError) as exc:
                    raise ValueError("OS process metadata unavailable") from exc
                records = [line.split(None, 3) for line in out.splitlines()[:200]]
                artifacts = [
                    {
                        "kind": "table",
                        "columns": ["PID", "process", "CPU %", "RAM %"],
                        "rows": records,
                        "provenance": {"scope": "opt_in_process_metadata", "no_command_arguments": True},
                    }
                ]
            return {
                "ok": True,
                "tool": name,
                "run_id": None,
                "artifacts": artifacts,
                "summary": "Local metadata; unregistered programs are not inferred to be simulation projects.",
            }
        run_id = args.get("run_id") or selected_run_id
        if selected_run_id and run_id != selected_run_id:
            raise ValueError("tool scope is the selected run; select another run explicitly")
        details, folder, provenance = _context(run_id)
        execution = details.get("execution") or {}
        summary = execution.get("summary") or {}
        nested = summary.get("summary_metrics") or {}
        if name == "inspect_run":
            rows, sources = _read_rows(folder)
            provenance["sources"] = sources
            keys = sorted({key for r in rows for key, v in _metric_map(r).items() if _finite(v)})
            artifacts = [
                {
                    "kind": "table",
                    "columns": ["field", "value"],
                    "rows": [
                        ["status", details.get("status")],
                        ["progress", details.get("pct")],
                        ["available_metrics", ", ".join(keys)],
                        ["verdict", (details.get("hypothesis_assessment") or {}).get("verdict")],
                    ],
                    "provenance": provenance,
                }
            ]
        elif name in {"time_shift_heatmap", "confusion_matrix"}:
            raw = (
                (nested.get("time_shift") or summary.get("time_shift") or details.get("diagnostics"))
                if name == "time_shift_heatmap"
                else (
                    nested.get("confusion_matrix")
                    or summary.get("confusion_matrix")
                    or execution.get("confusion_matrix")
                )
            )
            if isinstance(raw, list):
                raw = {"matrix": raw}
            if not isinstance(raw, dict):
                raise ValueError("no measured matrix recorded for this run")
            matrix = raw.get("matrix") or raw.get("time_shift_matrix")
            if (
                not isinstance(matrix, list)
                or not matrix
                or len(matrix) > 256
                or any(
                    not isinstance(r, list) or not r or len(r) > 256 or any(not _finite(v) for v in r) for r in matrix
                )
                or len({len(r) for r in matrix}) != 1
            ):
                raise ValueError("matrix missing, nonfinite or malformed")
            labels = raw.get("labels") or raw.get("archive_generations")
            row_labels = raw.get("row_labels") or raw.get("host_generations") or labels
            col_labels = raw.get("column_labels") or raw.get("parasite_generations") or labels
            if (
                row_labels is None
                or col_labels is None
                or len(row_labels) != len(matrix)
                or len(col_labels) != len(matrix[0])
            ):
                raise ValueError("matrix requires measured row and column labels")
            artifacts = [
                {
                    "kind": "chart",
                    "spec": {
                        "chart_type": "heatmap",
                        "title": "Measured time-shift assays"
                        if name == "time_shift_heatmap"
                        else "Recorded confusion matrix",
                        "x_label": "parasite generation" if name == "time_shift_heatmap" else "predicted class",
                        "y_label": "host generation" if name == "time_shift_heatmap" else "actual class",
                        "matrix": matrix,
                        "row_labels": row_labels,
                        "column_labels": col_labels,
                        "series": [],
                    },
                    "provenance": provenance,
                }
            ]
        elif name == "mathematical_summary":
            artifacts = [
                {
                    "kind": "math",
                    "latex": r"\Delta\bar z=\frac{\operatorname{Cov}(w,z)}{\bar w}+\frac{\operatorname{E}[w\Delta z]}{\bar w}",
                    "provenance": provenance,
                    "description": "Price identity over actual retained offspring; a separate regulation term is required if measuring before culling.",
                },
                {
                    "kind": "math",
                    "latex": r"I(E)=-\log_2 F(E)",
                    "description": "Functional information requires a specified sampling space and independently measured success threshold. These are definitions, not a claim about this run.",
                    "provenance": provenance,
                },
            ]
        elif name == "reproducibility_code":
            code = (
                "import json\nfrom pathlib import Path\n\n"
                "# Run from the selected exported run directory; read-only.\n"
                'rows = [json.loads(line) for line in Path("metrics.jsonl").read_text().splitlines() if line.strip()]\n'
                'rows = [r for r in rows if not r.get("synthetic", False)]\n'
                'print("observations:", len(rows))\nprint(rows[-1] if rows else "No measurements")\n'
            )
            artifacts = [{"kind": "code", "language": "python", "text": code, "provenance": provenance}]
        else:
            compare = (
                name in {"seed_comparison", "effect_summary"}
                or args.get("seed_from") is not None
                or args.get("seed_to") is not None
            )
            rows, sources = _campaign_rows(details, folder, include_campaign=compare)
            rows = _filter(rows, args)
            provenance["sources"] = sources
            provenance["scope_campaign"] = _scope_key(details.get("manifest") or {})
            maximum = args.get("max_points", 400)
            metric = args.get("metric")
            if name == "diversity_curve" and metric is None:
                metric = next(
                    (
                        k
                        for k in (
                            "shannon_diversity",
                            "shannon_entropy",
                            "genetic_diversity",
                            "archive_coverage",
                            "discovered_phenotypes",
                        )
                        if any(_finite(_metric_map(r).get(k)) for r in rows)
                    ),
                    None,
                )
                if metric is None:
                    raise ValueError("no actual diversity/coverage measurement recorded")
            if name == "scientific_plot":
                spec, chart_notes = build_chart(rows, args, _metric_map, _finite, _numeric_series)
                provenance.update(chart_notes)
                artifacts = [{"kind": "chart", "spec": spec, "provenance": provenance}]
            elif name == "price_decomposition":
                terms = (
                    "between_group_term",
                    "within_group_term",
                    "transmission_bias",
                    "regulation_term",
                    "identity_residual",
                    "realized_identity_residual",
                )
                all_series = []
                axis = "generation"
                for key in terms:
                    try:
                        series, _, axis = _numeric_series(rows, key, maximum)
                    except ValueError:
                        continue
                    for s in series:
                        s["name"] = key + " · " + s["name"]
                    all_series.extend(series)
                if not all_series:
                    raise ValueError("no recorded Price decomposition terms")
                artifacts = [
                    {
                        "kind": "chart",
                        "spec": {
                            "chart_type": "line",
                            "title": "Recorded Price decomposition",
                            "x_label": axis,
                            "y_label": "trait change / residual",
                            "series": all_series,
                        },
                        "provenance": provenance,
                    }
                ]
            elif name == "pareto_front":
                x = args.get("x_metric", "energy_used")
                y = args.get("y_metric", "fitness")
                points = []
                for r in rows:
                    values = _metric_map(r)
                    if r.get("synthetic") is not True and _finite(values.get(x)) and _finite(values.get(y)):
                        points.append([float(values[x]), float(values[y])])
                if not points:
                    raise ValueError("both paired cost and quality metrics must be recorded")
                artifacts = [
                    {
                        "kind": "chart",
                        "spec": {
                            "chart_type": "scatter",
                            "title": "Recorded resource–quality tradeoff (no dominance inference)",
                            "x_label": x,
                            "y_label": y,
                            "series": [
                                {
                                    "name": "paired observations",
                                    "points": _downsample(points, maximum),
                                    "raw_points": len(points),
                                }
                            ],
                        },
                        "provenance": provenance,
                    }
                ]
            elif name in {"seed_comparison", "effect_summary"}:
                metric = metric or next(
                    (r.get("primary_metric_name") for r in rows if isinstance(r.get("primary_metric_name"), str)), None
                )
                endpoints = {}
                seed_sources = {}
                for r in rows:
                    val = _metric_map(r).get(metric)
                    if r.get("synthetic") is True or not _finite(val) or not isinstance(r.get("seed"), int):
                        continue
                    key = (r["seed"], str(r.get("arm", "DEFAULT")))
                    timepoint = r.get("generation", r.get("tick", 0))
                    source = r.get("_source_run_id")
                    if key in seed_sources and seed_sources[key] != source:
                        raise ValueError(
                            "duplicate seed/arm across runs: select a campaign with unique replicates before estimating uncertainty"
                        )
                    seed_sources[key] = source
                    if key not in endpoints or timepoint >= endpoints[key][0]:
                        endpoints[key] = (timepoint, float(val))
                if not endpoints:
                    raise ValueError("no seed-labelled measurements for this metric")
                if name == "seed_comparison":
                    byarm = {}
                    for (seed, arm), (_, val) in sorted(endpoints.items()):
                        byarm.setdefault(arm, []).append([seed, val])
                    artifacts = [
                        {
                            "kind": "chart",
                            "spec": {
                                "chart_type": "scatter",
                                "title": "Last observed endpoint per seed and arm",
                                "x_label": "seed ID (independent runs)",
                                "y_label": metric,
                                "series": [{"name": a, "points": v} for a, v in byarm.items()],
                            },
                            "provenance": provenance,
                        }
                    ]
                else:
                    byarm = {}
                    for (_, arm), (_, value) in endpoints.items():
                        byarm.setdefault(arm, []).append(value)
                    output = []
                    provenance["bootstrap_method"] = "seed-endpoint-percentile-rngmanager-v2"
                    provenance["rng_streams"] = {}
                    for arm, values in sorted(byarm.items()):
                        rng = RNGManager(seed=20261010, namespace="science.effect_summary." + arm)
                        lo = hi = None
                        if len(values) >= 2:
                            bootstrap = sorted(
                                statistics.fmean([rng.choice(values) for _ in values]) for _ in range(1000)
                            )
                            lo = bootstrap[24]
                            hi = bootstrap[974]
                        provenance["rng_streams"][arm] = rng.snapshot()
                        output.append([arm, len(values), statistics.fmean(values), lo, hi])
                    artifacts = [
                        {
                            "kind": "table",
                            "columns": [
                                "arm",
                                "independent seeds",
                                "mean last-observed endpoint",
                                "descriptive bootstrap 2.5%",
                                "descriptive bootstrap 97.5%",
                            ],
                            "rows": output,
                            "provenance": provenance,
                        }
                    ]
                    provenance["uncertainty_notice"] = (
                        "Descriptive seed bootstrap, 1000 resamples, PRNG seed 20261010. Partial endpoints, shared history and dependence require separate confirmatory analysis; no p-value or verdict computed."
                    )
            else:
                series, metric, axis = _numeric_series(rows, metric, maximum)
                artifacts = [
                    {
                        "kind": "chart",
                        "spec": {
                            "chart_type": "line",
                            "title": "Recorded " + metric,
                            "x_label": axis,
                            "y_label": metric,
                            "series": series,
                        },
                        "provenance": provenance,
                    }
                ]
        return {
            "ok": True,
            "tool": name,
            "run_id": run_id,
            "artifacts": artifacts,
            "summary": "Read-only descriptive output from recorded artifacts; run status does not block analysis.",
        }
    except (ValueError, OSError, TypeError, KeyError) as exc:
        return {
            "ok": False,
            "tool": name,
            "run_id": selected_run_id or (args or {}).get("run_id") if isinstance(args, (dict, type(None))) else None,
            "artifacts": [],
            "summary": str(exc),
            "error": str(exc),
        }
