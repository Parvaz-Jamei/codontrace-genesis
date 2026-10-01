"""Confirmatory RQ-1 analysis, derived only from the raw JSONL and per-seed files.

Recomputes each seed's 3x3 matrix from raw/population_seed<N>.jsonl (slots 90,
100, 110), checks it against raw/seed_<N>.json, then computes the locked
estimands, the 95% paired t intervals, the frozen and shuffled-label controls,
the exclusions and exactly one verdict label.

Never re-tunes a seed, threshold, arm or estimator.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
REPO = HERE
for _candidate in (HERE, *HERE.parents):
    if (_candidate / "src" / "codontrace").is_dir():
        REPO = _candidate
        break
SRC = REPO / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import rq1_design as mod

from codontrace.genesis.archive_io import iter_jsonl_lines

OUT_DIR = HERE
RAW = HERE / "raw"


def _t_critical(df: int, conf: float = 0.95) -> tuple[float, str]:
    """Exact Student-t 0.975 quantile; falls back to the repo table if scipy is absent."""

    try:
        from scipy.stats import t as _student_t

        return float(_student_t.ppf(0.5 + conf / 2.0, int(df))), "scipy.stats.t.ppf"
    except Exception:  # noqa: BLE001
        from codontrace.genesis.causal_validation import _T975_BY_DF

        return float(_T975_BY_DF.get(int(df), 1.96)), "causal_validation._T975_BY_DF"


def exact_paired_interval(deltas, *, conf: float = 0.95):
    """The same paired-t interval as causal_validation but with the exact quantile.

    Returns (lo, hi, critical). Used only to quantify the endpoint shift caused
    by the repo's three-decimal lookup table; the locked verdict uses the repo
    function.
    """

    vals = [float(v) for v in deltas]
    if len(vals) < 2:
        return (0.0, 0.0, 0.0)
    mean = sum(vals) / len(vals)
    var = sum((v - mean) ** 2 for v in vals) / (len(vals) - 1)
    if var <= 0.0:
        return (0.0, 0.0, 0.0)
    se = (var / len(vals)) ** 0.5
    crit, _src = _t_critical(len(vals) - 1, conf)
    return (round(mean - crit * se, 10), round(mean + crit * se, 10), crit)


def t_star_comparison() -> dict:
    """Repo lookup table vs the exact quantile, and the endpoint shift at n=8."""

    from codontrace.genesis.causal_validation import _T975_BY_DF

    rows = []
    for df in (1, 2, 3, 4, 5, 6, 7):
        exact, src = _t_critical(df)
        table = float(_T975_BY_DF[df])
        rows.append(
            {
                "df": df,
                "repo_table": table,
                "exact": exact,
                "exact_minus_table": exact - table,
                "source": src,
            }
        )
    return {
        "note": (
            "causal_validation._paired_interval uses the three-decimal lookup "
            "_T975_BY_DF; the exact quantile is reported for the archived copy. "
            "df=1 is the 12.706 -> 12.7062047361747 case."
        ),
        "rows": rows,
        "confirmatory_df": 7,
        "confirmatory_repo_table": float(_T975_BY_DF[7]),
        "confirmatory_exact": _t_critical(7)[0],
    }

TIMES = mod.TIMES
SLOTS = mod.SLOTS
SEEDS = mod.SEEDS
SUPPORT_LABELS = mod.SUPPORT_LABELS


def load_population(seed: int) -> dict:
    path = RAW / f"population_seed{seed}.jsonl"
    rows: dict[tuple[str, int], dict] = {}
    try:
        lines = iter_jsonl_lines(path)
    except FileNotFoundError:
        return rows
    for line in lines:
        record = json.loads(line)
        rows[(record["regime"], int(record["generation"]))] = record
    return rows


def matrix_from_raw(pop: dict, regime: str) -> dict | None:
    snaps = {}
    for slot in TIMES:
        row = pop.get((regime, SLOTS[slot]))
        if row is None:
            return None
        snaps[slot] = row
    m = {}
    for ti in TIMES:
        m[ti] = {}
        hf = {str(k): float(v) for k, v in snaps[ti]["host_joint_class_frequencies"].items()}
        for tj in TIMES:
            ant = [str(k) for k in snaps[tj]["antagonist_class_frequencies"]]
            m[ti][tj] = round(mod.pressure_cell(hf, ant), 10)
    return m


def main() -> int:
    mod.bind_meter(REPO)
    seed_files = [
        (s, RAW / f"seed_{s}.json") for s in SEEDS if (RAW / f"seed_{s}.json").exists()
    ]
    completed = [s for s, p in seed_files]
    report: dict = {
        "schema_version": "rq1_confirmatory_analysis_v1",
        "commit": mod.COMMIT,
        "config_digest": mod.CONFIG_DIGEST,
        "generations": mod.GENERATIONS,
        "slots": SLOTS,
        "seeds_locked": list(SEEDS),
        "seeds_completed": completed,
        "seeds_remaining": [s for s in SEEDS if s not in completed],
        "status": "complete" if len(completed) == len(SEEDS) else "partial",
        "per_seed": [],
        "integrity": {},
        "errors": [],
    }
    report["archive_inventory"] = mod.archive_inventory(RAW)
    report["archive_complete"] = all(
        row["events"] and row["population"] and row["summary"] and row["seed_json"]
        for row in report["archive_inventory"]
    )
    if not report["archive_complete"]:
        report["status"] = "incomplete_archive"
    if not completed:
        report["decision"] = {
            "verdict": "BLOCKED_MEASUREMENT",
            "reason": "no confirmatory seed produced raw data",
        }
        (OUT_DIR / "analysis_confirmatory.json").write_text(
            json.dumps(report, indent=2, sort_keys=True, default=str) + "\n",
            encoding="utf-8",
        )
        print(json.dumps(report["decision"], indent=2))
        return 0

    raw_recompute_matches = True
    gates_ok_all = True
    frozen_exactly_zero = True
    per_seed = []
    for seed, path in seed_files:
        rec = json.loads(path.read_text(encoding="utf-8"))
        pop = load_population(seed)
        entry: dict = {"seed": seed, "regimes": {}, "errors": rec.get("errors", [])}
        gates_ok_all = gates_ok_all and bool(rec.get("seed_gates_ok"))
        for regime in ("copassaged", "fixed"):
            stored = (rec.get("regimes") or {}).get(regime)
            if not stored:
                entry["regimes"][regime] = None
                continue
            recomputed = matrix_from_raw(pop, regime)
            match = recomputed is not None and all(
                abs(recomputed[h][a] - float(stored["matrix"][h][a])) < 1e-12
                for h in TIMES
                for a in TIMES
            )
            raw_recompute_matches = raw_recompute_matches and match
            c = mod.contrast(stored["matrix"])
            if regime == "fixed":
                fvals = [float(stored["matrix"][h][a]) for h in TIMES for a in TIMES]
                frozen_exactly_zero = frozen_exactly_zero and (
                    max(fvals) - min(fvals) <= 1e-12
                    and abs(float(c["i_contemp"])) < 1e-12
                    and abs(float(c["i_lag"])) < 1e-12
                )
            entry["regimes"][regime] = {
                "matrix": stored["matrix"],
                "contrast": c,
                "label": mod.classify_time_shift_matrix(stored["matrix"]),
                "rotation_labels": stored["rotation_labels"],
                "recomputed_from_raw_matches": bool(match),
                "slot_diagnostics": stored["slot_diagnostics"],
                "wall_s": stored.get("wall_s"),
            }
        co = entry["regimes"]["copassaged"]
        fx = entry["regimes"]["fixed"]
        entry["contemporary"] = co["contrast"]["i_contemp"] if co else None
        entry["lagged"] = co["contrast"]["i_lag"] if co else None
        entry["frozen_contemporary"] = fx["contrast"]["i_contemp"] if fx else None
        entry["frozen_lagged"] = fx["contrast"]["i_lag"] if fx else None
        entry["coevolve_label"] = co["label"] if co else None
        per_seed.append(entry)
    report["per_seed"] = per_seed

    contemp = [e["contemporary"] for e in per_seed if e["contemporary"] is not None]
    lagged = [e["lagged"] for e in per_seed if e["lagged"] is not None]
    frozen_c = [e["frozen_contemporary"] for e in per_seed if e["frozen_contemporary"] is not None]
    frozen_l = [e["frozen_lagged"] for e in per_seed if e["frozen_lagged"] is not None]

    labels = [e["coevolve_label"] for e in per_seed]
    n_support_label = sum(1 for lab in labels if lab in SUPPORT_LABELS)
    rot_labels = [
        lab
        for e in per_seed
        for lab in (e["regimes"]["copassaged"] or {}).get("rotation_labels", {}).values()
    ]
    rot_support = sum(1 for lab in rot_labels if lab in SUPPORT_LABELS)

    d_contemp = [c - f for c, f in zip(contemp, frozen_c, strict=False)]
    d_lag = [lag - frozen for lag, frozen in zip(lagged, frozen_l, strict=False)]
    d_contemp_lag = [con - lag for con, lag in zip(contemp, lagged, strict=False)]

    def interval(vals):
        lo, hi = mod._paired_interval(vals)
        ex_lo, ex_hi, crit = exact_paired_interval(vals)
        return {
            "n_pairs": len(vals),
            "mean": (sum(vals) / len(vals)) if vals else None,
            "lo": lo,
            "hi": hi,
            "excludes_zero": bool(vals) and (lo > 0.0 or hi < 0.0),
            "method": "causal_validation._paired_interval (95% paired t)",
            "exact_t_lo": ex_lo,
            "exact_t_hi": ex_hi,
            "exact_t_critical": crit,
            "exact_minus_repo_lo": (ex_lo - lo) if vals else None,
            "exact_minus_repo_hi": (ex_hi - hi) if vals else None,
        }

    t_star = t_star_comparison()

    stats = {
        "contemporary": {
            "values": contemp,
            "mean": (sum(contemp) / len(contemp)) if contemp else None,
            "interval_vs_frozen": interval(d_contemp),
        },
        "lagged": {
            "values": lagged,
            "mean": (sum(lagged) / len(lagged)) if lagged else None,
            "interval_vs_frozen": interval(d_lag),
        },
        "frozen": {
            "contemporary_values": frozen_c,
            "lagged_values": frozen_l,
            "exactly_zero": frozen_exactly_zero,
        },
        "paired_contemporary_vs_lagged": interval(d_contemp_lag),
        "labels": labels,
        "n_support_label": n_support_label,
        "rotation_control": {
            "n": len(rot_labels),
            "n_support_label": rot_support,
            "fraction": (rot_support / len(rot_labels)) if rot_labels else None,
        },
    }
    report["statistics"] = stats
    report["interval_exact_quantile"] = {
        "t_star": t_star,
        "intervals": {
            "contemporary_vs_frozen": stats["contemporary"]["interval_vs_frozen"],
            "lagged_vs_frozen": stats["lagged"]["interval_vs_frozen"],
            "contemporary_vs_lagged": stats["paired_contemporary_vs_lagged"],
        },
        "confirmatory_endpoint_shift": {
            k: {
                "exact_minus_repo_lo": v.get("exact_minus_repo_lo"),
                "exact_minus_repo_hi": v.get("exact_minus_repo_hi"),
            }
            for k, v in (
                ("contemporary_vs_frozen", stats["contemporary"]["interval_vs_frozen"]),
                ("lagged_vs_frozen", stats["lagged"]["interval_vs_frozen"]),
                ("contemporary_vs_lagged", stats["paired_contemporary_vs_lagged"]),
            )
        },
    }
    report["integrity"] = {
        "raw_recompute_matches_all_seeds": raw_recompute_matches,
        "all_seed_gates_ok": gates_ok_all,
        "frozen_exactly_zero": frozen_exactly_zero,
        "n_seeds_completed": len(completed),
        "n_seeds_locked": len(SEEDS),
    }

    prim = stats["contemporary"]["interval_vs_frozen"]
    lag = stats["lagged"]["interval_vs_frozen"]
    rotation_clean = rot_support == 0
    all_support_labels = n_support_label == len(completed)
    sign_present = (stats["contemporary"]["mean"] or 0.0) > 0.0 or (
        stats["lagged"]["mean"] or 0.0
    ) > 0.0

    if not rotation_clean or not frozen_exactly_zero:
        verdict = "FALSIFIED_IN_MODEL"
        reason = (
            "a locked negative control reproduces the pattern: "
            f"frozen_exactly_zero={frozen_exactly_zero}, "
            f"rotation_support={rot_support}/{len(rot_labels)}"
        )
    elif (
        report["status"] == "complete"
        and gates_ok_all
        and raw_recompute_matches
        and all_support_labels
        and prim["excludes_zero"]
        and (stats["contemporary"]["mean"] or 0.0) > 0.0
    ):
        verdict = "SUPPORTED_IN_MODEL"
        reason = "all eight locked unseen seeds met the pre-declared pattern and controls"
    elif not sign_present and report["status"] == "complete":
        verdict = "FALSIFIED_IN_MODEL"
        reason = "neither the contemporary nor the lagged mean interaction is positive"
    else:
        verdict = "INCONCLUSIVE"
        reason = (
            f"pattern not met at the locked threshold: completed "
            f"{len(completed)}/{len(SEEDS)} seeds, support labels "
            f"{n_support_label}/{len(completed)}, contemporary vs frozen interval "
            f"[{prim['lo']}, {prim['hi']}] excludes_zero={prim['excludes_zero']}, "
            f"lagged vs frozen [{lag['lo']}, {lag['hi']}] "
            f"excludes_zero={lag['excludes_zero']}"
        )

    report["decision"] = {
        "verdict": verdict,
        "reason": reason,
        "hypothesis_supported": False,
        "red_queen_proved": False,
        "confirmatory_complete": report["status"] == "complete",
    }
    report["effect_table"] = [
        {
            "arm": "contemporary",
            "unit": "independent population history (seed)",
            "n": len(contemp),
            "mean": stats["contemporary"]["mean"],
            "interval_vs_frozen": prim,
        },
        {
            "arm": "lagged",
            "unit": "independent population history (seed)",
            "n": len(lagged),
            "mean": stats["lagged"]["mean"],
            "interval_vs_frozen": lag,
        },
        {
            "arm": "frozen",
            "unit": "independent population history (seed)",
            "n": len(frozen_c),
            "mean": 0.0,
            "interval_vs_frozen": {"lo": 0.0, "hi": 0.0, "excludes_zero": False},
            "exactly_zero": frozen_exactly_zero,
        },
        {
            "arm": "contemporary_minus_lagged",
            "unit": "independent population history (seed)",
            "n": len(d_contemp_lag),
            "mean": stats["paired_contemporary_vs_lagged"]["mean"],
            "interval_vs_frozen": stats["paired_contemporary_vs_lagged"],
        },
    ]
    report["exclusions"] = [
        "no seed was dropped on the basis of its result",
        "the confirmatory generation count was not shortened",
        f"seeds not yet complete: {report['seeds_remaining']}"
        if report["seeds_remaining"]
        else "all locked seeds complete",
    ]

    (OUT_DIR / "analysis_confirmatory.json").write_text(
        json.dumps(report, indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
    )
    (OUT_DIR / "effect_table_confirmatory.json").write_text(
        json.dumps(report["effect_table"], indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
    )

    manifest = {
        "schema_version": "rq1_confirmatory_manifest_v1",
        "round": 3,
        "commit": mod.COMMIT,
        "commit_source": "git archive of 6187ff4 at test-runs/verify/full6187ff4",
        "provenance": {
            "pin": mod.COMMIT,
            "seeds_5701_5702": mod.COMMIT,
            "seeds_5703_5708": mod.COMMIT,
            "engine_changes_after_pin": [
                "40138c9 RNG migration",
                "913f18e from_fork restoration",
                "02cc725 docs-only",
            ],
            "comparability": (
                "All eight seeds ran against the same pinned extraction "
                "(test-runs/verify/full6187ff4, commit 6187ff4), so the pack is "
                "single-revision and the two groups are comparable by construction. "
                "The post-6187ff4 commits are absent from the pin and touch the RNG "
                "migration and from_fork restoration paths, which these arm runs do "
                "not use. No mixed-revision claim is made."
            ),
        },
        "config_digest": mod.CONFIG_DIGEST,
        "locked_config": mod.LOCKED_CONFIG,
        "seeds_locked": list(SEEDS),
        "seeds_completed": completed,
        "seeds_remaining": report["seeds_remaining"],
        "status": report["status"],
        "rng_derivation": (
            "StructuralRQArm.boot_structural(seed) + "
            "RNGManager(seed, namespace=f'hp-struct-rq-{arm}') + rng.fork(f'passage/{tick}')"
        ),
        "generations": mod.GENERATIONS,
        "interval_method": "causal_validation._paired_interval (95% paired t)",
        "raw_artifacts": [
            str(p.relative_to(HERE))
            for p in sorted(RAW.glob("*"))
        ],
        "hypothesis_supported": False,
        "red_queen_proved": False,
    }
    (OUT_DIR / "run_manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
    )

    decision_md = f"""# RQ-1 confirmatory decision

**Pack:** RQ-1 confirmatory · **Round:** 3 · **Commit:** `{mod.COMMIT}` (isolated
extraction `test-runs/verify/full6187ff4`, never the live checkout)
**Config digest:** `{mod.CONFIG_DIGEST}`
**Seeds locked:** {list(SEEDS)} · **completed:** {completed}
**Generations per seed:** {mod.GENERATIONS} (never shortened) · **slots:** {SLOTS}
**Regimes:** copassaged (coevolve) and fixed (frozen antagonist)
**Status:** {report['status']}

## Decision

`{verdict}`

{reason}

## Integrity

* analysis derived only from raw JSONL: `raw_recompute_matches_all_seeds =
  {raw_recompute_matches}`
* all completed-seed gates OK: `{gates_ok_all}`
* frozen negative control exactly zero: `{frozen_exactly_zero}`
* shuffled time-label control: {rot_support} of {len(rot_labels)} permutations
  receive a support label
* hypothesis_supported = false · red_queen_proved = false

## Effect table

| arm | n | mean | 95% paired t interval vs frozen |
|---|---|---|---|
| contemporary | {len(contemp)} | {stats['contemporary']['mean']} | [{prim['lo']}, {prim['hi']}] |
| lagged | {len(lagged)} | {stats['lagged']['mean']} | [{lag['lo']}, {lag['hi']}] |
| frozen | {len(frozen_c)} | 0.0 fixed | [0.0, 0.0] |
| contemporary − lagged | {len(d_contemp_lag)} | {stats['paired_contemporary_vs_lagged']['mean']} | [{stats['paired_contemporary_vs_lagged']['lo']}, {stats['paired_contemporary_vs_lagged']['hi']}] |

## Exclusions

{chr(10).join('- ' + x for x in report['exclusions'])}

## Note

No seed, threshold, arm, estimator or generation count was changed after any
result. {('Seeds ' + str(report['seeds_remaining']) + ' remain; the pack is resumed by re-running the same locked command.') if report['seeds_remaining'] else 'The locked pack is complete.'}
"""
    (OUT_DIR / "decision.md").write_text(decision_md, encoding="utf-8")
    (OUT_DIR / "exclusions.md").write_text(
        "\n".join(f"- {x}" for x in report["exclusions"]) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {"verdict": verdict, "reason": reason, "integrity": report["integrity"]},
            indent=2,
        )
    )
    print(
        json.dumps(
            {
                "t_star_df7": {
                    "repo_table": t_star["confirmatory_repo_table"],
                    "exact": t_star["confirmatory_exact"],
                },
                "t_star_df1": next(r for r in t_star["rows"] if r["df"] == 1),
                "endpoint_shift": report["interval_exact_quantile"][
                    "confirmatory_endpoint_shift"
                ],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Rebuild the RQ-1 table from archived raw files")
    parser.add_argument("--raw", type=Path, default=None)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--reference-checkout", type=Path, default=None)
    args = parser.parse_args()
    if args.reference_checkout is not None:
        REPO = args.reference_checkout.resolve()
    RAW = (args.raw or (HERE / "raw")).resolve()
    OUT_DIR = args.output.resolve()
    if OUT_DIR in {HERE.resolve(), (HERE / "raw").resolve()}:
        raise SystemExit(
            "refusing to overwrite historical confirmatory files; pass a fresh --output"
        )
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    raise SystemExit(main())
