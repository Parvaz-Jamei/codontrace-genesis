"""Bounded descriptive chart transforms. No inference, mutation or arbitrary expressions."""

from __future__ import annotations

import math
import statistics
from typing import Any

KINDS = (
    "auto",
    "line",
    "step",
    "area",
    "scatter",
    "bubble",
    "bar",
    "histogram",
    "ecdf",
    "box",
    "violin",
    "density",
    "correlation",
    "errorbar",
)
PALETTES = ("accessible", "cool", "warm", "mono")


def quantile(values: list[float], q: float) -> float:
    values = sorted(values)
    x = (len(values) - 1) * q
    lo = int(x)
    return values[lo] + (values[min(lo + 1, len(values) - 1)] - values[lo]) * (x - lo)


def build_chart(
    rows: list[dict[str, Any]], args: dict[str, Any], metric_map: Any, finite: Any, numeric_series: Any
) -> tuple[dict[str, Any], dict[str, Any]]:
    mode = args.get("mode", "raw")
    if mode == "raw" and any(k not in {"run_id", "mode"} for k in args):
        raise ValueError("raw mode accepts only run_id and mode; choose tool mode for filters or styling")
    kind = args.get("chart", "auto")
    metric = args.get("metric") or next(
        (r.get("primary_metric_name") for r in rows if isinstance(r.get("primary_metric_name"), str)), None
    )
    if kind == "correlation" and not metric:
        metric = next((k.strip() for k in args.get("metrics", "").split(",") if k.strip()), None)
    if not metric:
        raise ValueError("metric required; inspect_run lists recorded metrics")
    rows = [
        r
        for r in rows
        if r.get("synthetic") is not True and (kind == "correlation" or finite(metric_map(r).get(metric)))
    ]
    if not rows:
        raise ValueError("no finite measured observations after filtering")
    maximum = args.get("max_points", 400)
    if kind == "correlation":
        metric = next(
            (
                k.strip()
                for k in args.get("metrics", "").split(",")
                if any(finite(metric_map(r).get(k.strip())) for r in rows)
            ),
            metric,
        )
    series, metric, axis = numeric_series(rows, metric, maximum)
    notes: dict[str, Any] = {
        "mode": mode,
        "settings": dict(args),
        "descriptive_only": True,
        "input_records": len(rows),
        "raw_unchanged": True,
        "sampling": "bounded source snapshot; extrema-preserving display reduction only for time-series",
        "independence_notice": "Repeated generations are not independent replicates; distributions describe recorded observations.",
    }
    spec: dict[str, Any] = {
        "chart_type": "line" if kind == "auto" else kind,
        "title": args.get("title", "Recorded " + metric),
        "x_label": axis,
        "y_label": metric,
        "series": series,
        "palette": args.get("palette", "accessible"),
        "x_scale": args.get("x_scale", "linear"),
        "y_scale": args.get("y_scale", "linear"),
    }
    groups: dict[str, list[float]] = {}
    for r in rows:
        label = f"seed {r.get('seed', '?')} · {r.get('arm', 'DEFAULT')} · {r.get('_source_run_id', 'selected')}"
        if finite(metric_map(r).get(metric)):
            groups.setdefault(label, []).append(float(metric_map(r)[metric]))
    if len(groups) > 12:
        raise ValueError("more than 12 series; narrow seed/arm filters rather than silently hiding groups")
    if kind in {"scatter", "bubble", "errorbar"}:
        xkey = args.get("x_metric")
        sizekey = args.get("size_metric")
        lower = args.get("lower_metric")
        upper = args.get("upper_metric")
        if kind == "bubble" and not sizekey:
            raise ValueError("bubble requires size_metric from recorded data")
        if kind == "errorbar" and not (lower and upper):
            raise ValueError("errorbar requires recorded lower_metric and upper_metric; no CI invented")
        paired: dict[str, list[list[float]]] = {}
        for i, r in enumerate(rows):
            m = metric_map(r)
            x = m.get(xkey) if xkey else r.get(axis, i)
            if not finite(x):
                continue
            point = [float(x), float(m[metric])]
            if kind == "bubble":
                if not finite(m.get(sizekey)) or m[sizekey] < 0:
                    continue
                point.append(float(m[sizekey]))
            if kind == "errorbar":
                if not (finite(m.get(lower)) and finite(m.get(upper)) and m[lower] <= m[metric] <= m[upper]):
                    continue
                point += [float(m[lower]), float(m[upper])]
            label = f"seed {r.get('seed', '?')} · {r.get('arm', 'DEFAULT')} · {r.get('_source_run_id', 'selected')}"
            paired.setdefault(label, []).append(point)
        if not paired:
            raise ValueError("no valid paired observations for requested chart")
        # Deterministic evenly spaced display indices, not extrema sampling of paired values.
        spec["series"] = [
            {
                "name": n,
                "points": [
                    p[i]
                    for i in sorted(
                        {round(j * (len(p) - 1) / (min(len(p), maximum) - 1)) for j in range(min(len(p), maximum))}
                    )
                ]
                if len(p) > 1
                else p,
            }
            for n, p in paired.items()
        ]
        spec["x_label"] = xkey or axis
        notes["sampling"] = "paired observations; deterministic evenly spaced display indices"
    elif kind in {"histogram", "ecdf", "box", "violin", "density"}:
        values = [v for group in groups.values() for v in group]
        lo, hi = min(values), max(values)
        if lo == hi:
            lo, hi = lo - 0.5, hi + 0.5
        output = []
        boxes = []
        bins = args.get("bins", 20)
        for index, (label, vs) in enumerate(groups.items()):
            vs = sorted(vs)
            if kind == "histogram":
                width = (hi - lo) / bins
                counts = [0] * bins
                for v in vs:
                    counts[min(bins - 1, max(0, int((v - lo) / width)))] += 1
                points = [[lo + (i + 0.5) * width, float(c)] for i, c in enumerate(counts)]
                spec["bin_width"] = width
            elif kind == "ecdf":
                # Includes both sides of each retained jump; no smoothing.
                points = [[v, (i + 1) / len(vs)] for i, v in enumerate(vs)]
                if len(points) > maximum:
                    points = [points[round(i * (len(points) - 1) / (maximum - 1))] for i in range(maximum)]
                    notes["ecdf_display_reduced"] = True
            elif kind == "box":
                q1, med, q3 = (quantile(vs, q) for q in (0.25, 0.5, 0.75))
                iqr = q3 - q1
                inliers = [v for v in vs if q1 - 1.5 * iqr <= v <= q3 + 1.5 * iqr]
                boxes.append(
                    {
                        "name": label,
                        "index": index,
                        "q1": q1,
                        "median": med,
                        "q3": q3,
                        "low": min(inliers),
                        "high": max(inliers),
                        "n": len(vs),
                        "outliers": [v for v in vs if v < min(inliers) or v > max(inliers)][:maximum],
                    }
                )
                points = [[float(index), med]]
            else:
                if len(vs) < 3 or statistics.pstdev(vs) == 0:
                    raise ValueError(
                        "KDE needs at least three nonconstant measured observations per group; choose ECDF or box"
                    )
                # Silverman normal-reference bandwidth, stated explicitly; no automatic biological inference.
                bw = 1.06 * statistics.stdev(vs) * len(vs) ** (-0.2)
                grid = [lo - 3 * bw + (hi - lo + 6 * bw) * i / 79 for i in range(80)]
                points = [
                    [x, sum(math.exp(-0.5 * ((x - v) / bw) ** 2) for v in vs) / (len(vs) * bw * math.sqrt(2 * math.pi))]
                    for x in grid
                ]
                notes.setdefault("kde", []).append(
                    {
                        "series": label,
                        "bandwidth": bw,
                        "kernel": "Gaussian",
                        "rule": "1.06 * sample SD * n^(-1/5)",
                        "n": len(vs),
                    }
                )
            output.append({"name": label, "points": points})
        spec["series"] = output
        if boxes:
            spec["boxes"] = boxes
        spec["x_label"] = "group" if kind == "box" else metric
        spec["y_label"] = (
            metric
            if kind == "box"
            else "count"
            if kind == "histogram"
            else "empirical cumulative probability"
            if kind == "ecdf"
            else "estimated density (KDE)"
        )
        if kind == "violin":
            notes["violin_width"] = "each KDE normalized to equal peak width; area/width is not sample size"
        notes["distribution_basis"] = (
            "all finite observations in bounded filtered snapshot, before display downsampling"
        )
    elif kind == "correlation":
        keys = [k.strip() for k in args.get("metrics", metric).split(",") if k.strip()]
        if not 2 <= len(keys) <= 12 or len(set(keys)) != len(keys):
            raise ValueError("correlation requires 2–12 unique comma-separated metrics")
        matrix, counts = [], []
        for a in keys:
            line, ns = [], []
            for b in keys:
                pairs = [
                    (metric_map(r).get(a), metric_map(r).get(b))
                    for r in rows
                    if finite(metric_map(r).get(a)) and finite(metric_map(r).get(b))
                ]
                n = len(pairs)
                ns.append(n)
                if n < 3:
                    line.append(None)
                    continue
                xa = [p[0] for p in pairs]
                xb = [p[1] for p in pairs]
                ma, mb = statistics.mean(xa), statistics.mean(xb)
                denominator = math.sqrt(sum((x - ma) ** 2 for x in xa) * sum((x - mb) ** 2 for x in xb))
                line.append(sum((x - ma) * (y - mb) for x, y in pairs) / denominator if denominator else None)
            matrix.append(line)
            counts.append(ns)
        if not any(v is not None for line in matrix for v in line):
            raise ValueError("no nonconstant metric pairs with at least three observations")
        spec.update(
            chart_type="heatmap",
            matrix=matrix,
            row_labels=keys,
            column_labels=keys,
            x_label="metric",
            y_label="metric",
            color_min=-1,
            color_max=1,
        )
        notes.update(
            pair_counts=counts, correlation="pairwise complete Pearson r; descriptive, not causal; no p-values"
        )
    if spec["x_scale"] == "log" or spec["y_scale"] == "log":
        if kind in {"box", "violin", "correlation", "histogram", "area", "bar"}:
            raise ValueError("log scale unsupported for this geometry; use linear")
        for s in spec["series"]:
            for p in s["points"]:
                if (
                    spec["x_scale"] == "log"
                    and p[0] <= 0
                    or spec["y_scale"] == "log"
                    and any(v <= 0 for v in ([p[1]] + p[2:] if kind == "errorbar" else [p[1]]))
                ):
                    raise ValueError("log scale requires strictly positive plotted coordinates; no silent dropping")
    spec["x_label"] = args.get("x_label", spec["x_label"])
    spec["y_label"] = args.get("y_label", spec["y_label"])
    notes["display_points"] = sum(len(s["points"]) for s in spec["series"])
    return spec, notes
