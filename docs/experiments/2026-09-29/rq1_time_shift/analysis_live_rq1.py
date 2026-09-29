"""Derive the RQ-1 live summary from raw/live_run.json only.

Recomputes every seed's interaction contrast from the stored matrices (it does
not trust the stored contrast), then the seed-level means, the run-level cluster
bootstrap intervals, the rotation control and the pre-declared decision.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

REPO = Path(r"E:\مقاله پزشکی شبیه سازی ویروس\codontrace-genesis")
import sys

if str(REPO / "src") not in sys.path:
    sys.path.insert(0, str(REPO / "src"))

from codontrace.genesis.measurements.rq_frequency_clocks import (  # noqa: E402
    run_level_cluster_bootstrap_interval,
)

OUT = Path(__file__).resolve().parent
RAW = OUT / "raw"
TIMES = ("past", "now", "future")
SUPPORT_LABELS = {"contemporary_match", "lagged_match"}


def classify(m):
    vals = [m[h][a] for h in TIMES for a in TIMES]
    if max(vals) - min(vals) <= 1e-9:
        return "flat"
    if all(m[h]["past"] < m[h]["now"] < m[h]["future"] for h in TIMES):
        return "directional_increase"
    if all(m[a][a] > m[h][a] for a in TIMES for h in TIMES if h != a):
        return "contemporary_match"
    if (
        m["now"]["past"] > m["past"]["past"]
        and m["now"]["past"] > m["future"]["past"]
        and m["future"]["now"] > m["past"]["now"]
        and m["future"]["now"] > m["now"]["now"]
        and m["future"]["future"] > m["past"]["future"]
        and m["future"]["future"] > m["now"]["future"]
    ):
        return "lagged_match"
    return "other"


def contrast(m):
    cells = [float(m[h][a]) for h in TIMES for a in TIMES]
    grand = sum(cells) / len(cells)
    row = {h: sum(float(m[h][a]) for a in TIMES) / 3.0 for h in TIMES}
    col = {a: sum(float(m[h][a]) for h in TIMES) / 3.0 for a in TIMES}
    inter = {h: {a: float(m[h][a]) - row[h] - col[a] + grand for a in TIMES} for h in TIMES}
    best = max(((h, a) for h in TIMES for a in TIMES), key=lambda c: inter[c[0]][c[1]])
    vals = [inter[h][a] for h in TIMES for a in TIMES]
    npos = sum(1 for v in vals if v > 1e-15)
    nneg = sum(1 for v in vals if v < -1e-15)
    return {
        "i_contemp": round(inter["now"]["now"], 10),
        "i_lag": round((inter["now"]["past"] + inter["future"]["now"]) / 2.0, 10),
        "i_max_cell": list(best),
        "i_max": round(inter[best[0]][best[1]], 10),
        "n_positive_cells": npos,
        "n_negative_cells": nneg,
        "uniform_increase": bool(npos > 0 and nneg == 0),
    }


def supports(label, c):
    return bool(
        label in SUPPORT_LABELS
        and (c["i_contemp"] > 0.0 or c["i_lag"] > 0.0)
        and not c["uniform_increase"]
        and c["i_max_cell"] in (["now", "now"], ["now", "past"], ["future", "now"])
    )


def main() -> int:
    path = RAW / "live_run.json"
    rep = json.loads(path.read_text(encoding="utf-8"))
    sha = hashlib.sha256(path.read_bytes()).hexdigest()
    per_seed = []
    for rec in rep.get("seeds", []):
        if rec.get("skipped") or not rec.get("arms"):
            continue
        row = {"seed": rec["seed"], "phase": rec.get("phase"), "arms": {}}
        for name, arm in rec["arms"].items():
            m = arm["matrix_population_pressure"]
            c = contrast(m)
            label = classify(m)
            stored = arm["contrast_population"]
            row["arms"][name] = {
                "label": label,
                "contrast": c,
                "supports": supports(label, c),
                "stored_contrast_matches": abs(stored["i_contemp"] - c["i_contemp"]) < 1e-9
                and abs(stored["i_lag"] - c["i_lag"]) < 1e-9,
                "stored_label_matches": stored is not None and arm["label"] == label,
                "slot_diagnostics": arm["slot_diagnostics"],
            }
        per_seed.append(row)

    summary = {"arms": {}}
    for name in ("avirulent", "fixed", "copassaged"):
        vals_c = [
            r["arms"][name]["contrast"]["i_contemp"] for r in per_seed if name in r["arms"]
        ]
        vals_l = [r["arms"][name]["contrast"]["i_lag"] for r in per_seed if name in r["arms"]]
        labels = [r["arms"][name]["label"] for r in per_seed if name in r["arms"]]
        sup = [r["arms"][name]["supports"] for r in per_seed if name in r["arms"]]
        entry = {
            "n_seeds": len(vals_c),
            "labels": labels,
            "n_support": sum(1 for s in sup if s),
            "i_contemp_values": vals_c,
            "i_lag_values": vals_l,
            "i_contemp_mean": (sum(vals_c) / len(vals_c)) if vals_c else None,
            "i_lag_mean": (sum(vals_l) / len(vals_l)) if vals_l else None,
        }
        if len(vals_c) >= 2:
            entry["i_contemp_interval"] = run_level_cluster_bootstrap_interval(vals_c)
            entry["i_lag_interval"] = run_level_cluster_bootstrap_interval(vals_l)
        summary["arms"][name] = entry

    rot_n = rot_support = 0
    for rec in rep.get("seeds", []):
        co = (rec.get("arms") or {}).get("copassaged")
        if not co:
            continue
        for lab in co["rotation_labels"].values():
            rot_n += 1
            rot_support += int(lab in SUPPORT_LABELS)
    summary["rotation_control"] = {
        "n": rot_n,
        "n_support_label": rot_support,
        "fraction": (rot_support / rot_n) if rot_n else None,
    }
    summary["integrity"] = {
        "live_run_sha256": sha,
        "all_stored_contrasts_match_recompute": all(
            a["stored_contrast_matches"] and a["stored_label_matches"]
            for r in per_seed
            for a in r["arms"].values()
        ),
        "calibration_gate_ok": rep.get("calibration_gate_ok"),
        "pilot_gate_ok": rep.get("pilot_gate_ok"),
        "arm_match_at_generation_0_all": all(
            rec.get("arm_match_at_generation_0") for rec in rep.get("seeds", [])
        ),
    }

    co = summary["arms"]["copassaged"]
    frozen = summary["arms"]["fixed"]
    host_only = summary["arms"]["avirulent"]
    interval = co.get("i_contemp_interval") or {}
    labels_all_support = bool(co["labels"]) and all(l in SUPPORT_LABELS for l in co["labels"])
    frozen_also = frozen["n_seeds"] > 0 and frozen["n_support"] >= max(1, frozen["n_seeds"] // 2)
    host_only_zero = all(
        abs(v) < 1e-12 for v in host_only["i_contemp_values"] + host_only["i_lag_values"]
    )
    rotation_clean = rot_support == 0

    if co["n_seeds"] == 0:
        verdict, reason = "BLOCKED_MEASUREMENT", "no live seed completed"
    elif frozen_also:
        verdict, reason = "FALSIFIED_IN_MODEL", "the frozen-antagonist control reproduces the support pattern"
    elif not rotation_clean:
        verdict, reason = "FALSIFIED_IN_MODEL", "the shuffled time-label control reproduces the support label"
    elif co["n_support"] == 0 or not labels_all_support:
        verdict, reason = (
            "INCONCLUSIVE",
            "the coevolve arm does not show the pre-declared support pattern consistently across seeds",
        )
    elif interval and not interval.get("excludes_zero"):
        verdict, reason = "INCONCLUSIVE", "the seed-level interval for I_contemp contains zero"
    else:
        verdict, reason = (
            "INCONCLUSIVE",
            "pilot-level only: pattern present and interval excludes zero, but SUPPORTED_IN_MODEL is reserved for the eight-seed locked confirmatory run, which this budget did not fund",
        )

    out = {
        "schema_version": "rq1_live_analysis_v1",
        "route": rep.get("route"),
        "design": rep.get("design"),
        "per_seed": per_seed,
        "summary": summary,
        "decision": {
            "verdict": verdict,
            "reason": reason,
            "frozen_also_supports": bool(frozen_also),
            "rotation_control_clean": bool(rotation_clean),
            "host_only_is_zero": bool(host_only_zero),
            "coevolve_labels_all_support": bool(labels_all_support),
            "confirmatory_run": False,
        },
        "flags": {
            "hypothesis_supported": False,
            "red_queen_proved": False,
            "population_run": True,
        },
        "exclusions": [
            "the smoke-phase run (logs/live_smoke.txt) is not the recorded run; it "
            "used the full 40-generation configuration because RQ1_SMOKE carried a "
            "trailing space, and its gate comparison wrongly included the arm name",
        ],
    }
    (OUT / "analysis_live.json").write_text(
        json.dumps(out, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8"
    )
    print(json.dumps({"verdict": verdict, "reason": reason, "integrity": summary["integrity"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
