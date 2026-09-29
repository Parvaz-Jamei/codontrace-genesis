"""Derive the RQ-1 summary from raw files only.

Inputs (read-only): raw/*.json, raw/*.jsonl
Outputs: analysis.json, effect_table.json

No live simulation is re-run here and no parameter is tuned. The decision is a
function of the recorded preconditions and of the pre-registered decision rule.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent
RAW = OUT / "raw"

SCHEMA_VERSION = "rq1_analysis_v1"
DECISION_CODES = (
    "SUPPORTED_IN_MODEL",
    "FALSIFIED_IN_MODEL",
    "INCONCLUSIVE",
    "BLOCKED_MEASUREMENT",
)
TIMES = ("past", "now", "future")


def load(name: str):
    path = RAW / name
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical_digest(payload) -> str:
    body = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return "sha256:" + hashlib.sha256(body.encode("utf-8")).hexdigest()


def interaction_contrast(matrix: dict[str, dict[str, float]]) -> dict:
    cells = [float(matrix[h][a]) for h in TIMES for a in TIMES]
    grand = sum(cells) / len(cells)
    row_mean = {h: sum(float(matrix[h][a]) for a in TIMES) / 3.0 for h in TIMES}
    col_mean = {a: sum(float(matrix[h][a]) for h in TIMES) / 3.0 for a in TIMES}
    inter = {
        h: {a: float(matrix[h][a]) - row_mean[h] - col_mean[a] + grand for a in TIMES}
        for h in TIMES
    }
    vals = [inter[h][a] for h in TIMES for a in TIMES]
    best = max(((h, a) for h in TIMES for a in TIMES), key=lambda c: inter[c[0]][c[1]])
    n_pos = sum(1 for v in vals if v > 1e-12)
    n_neg = sum(1 for v in vals if v < -1e-12)
    return {
        "i_contemp": round(inter["now"]["now"], 10),
        "i_lag": round((inter["now"]["past"] + inter["future"]["now"]) / 2.0, 10),
        "i_max": {"cell": list(best), "value": round(inter[best[0]][best[1]], 10)},
        "n_positive_cells": n_pos,
        "n_negative_cells": n_neg,
        "uniform_increase": bool(n_pos > 0 and n_neg == 0),
        "interaction": {h: {a: round(inter[h][a], 10) for a in TIMES} for h in TIMES},
    }


def classify(matrix: dict[str, dict[str, float]]) -> str:
    m = {h: {a: float(matrix[h][a]) for a in TIMES} for h in TIMES}
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


def main() -> int:
    raw_names = [
        "probe_run.json",
        "probe_source_scan.json",
        "probe_engine_antagonist.json",
        "probe_live_generations.json",
        "probe_checkpoint_fork.json",
        "probe_cross_time_matrix.json",
        "probe_measurement_kernel.json",
        "probe_meter_reachability.json",
        "probe_determinism.json",
        "stage0_fixtures.json",
        "events.jsonl",
        "population.jsonl",
        "stage0_fixture_events.jsonl",
    ]
    sources = {}
    for name in raw_names:
        path = RAW / name
        sources[name] = {
            "exists": path.exists(),
            "sha256": sha256(path) if path.exists() else None,
            "bytes": path.stat().st_size if path.exists() else None,
        }

    run = load("probe_run.json") or {}
    scan = load("probe_source_scan.json") or {}
    antagonist = load("probe_engine_antagonist.json") or {}
    fork = load("probe_checkpoint_fork.json") or {}
    world = load("probe_cross_time_matrix.json") or {}
    kernel = load("probe_measurement_kernel.json") or {}
    reach = load("probe_meter_reachability.json") or {}
    det = load("probe_determinism.json") or {}
    fixtures = load("stage0_fixtures.json") or {}

    # ---- preconditions -----------------------------------------------------
    cells = antagonist.get("cells", [])
    any_genotype_antagonist = any(
        c.get("parasite_is_genotype_population") is True for c in cells
    )
    any_independent_antagonist = any(
        c.get("parasite_is_independent_population") is True for c in cells
    )
    fork_complete = any(
        c.get("checkpoint_fork_complete") is True for c in fork.get("idea4_cells", [])
    )
    parent_child = any(
        c.get("parent_child_ids_recorded") is True
        for c in fork.get("idea4_cells", [])
    )
    engine_tokens = {
        k: v.get("token_counts", {})
        for k, v in (scan.get("files") or {}).items()
        if "engine_runtime" in k or "engine.py" in k
    }
    engine_has_antagonist_token = any(
        counts.get("parasite", 0) or counts.get("antagonist", 0) or counts.get("host_parasite", 0)
        for counts in engine_tokens.values()
    )

    # ---- live matrices the model can give ----------------------------------
    live_matrix_rows = []
    for hist in world.get("histories", []):
        for kind in ("matrix_allele_exact", "matrix_affinity_pi"):
            m = hist.get(kind)
            if not isinstance(m, dict):
                continue
            live_matrix_rows.append(
                {
                    "seed": hist.get("seed"),
                    "matrix_kind": kind,
                    "label": classify(m),
                    "contrast": interaction_contrast(m),
                    "admissible_as_pi_realised": kind == "matrix_affinity_pi"
                    and False,  # window definition is imposed by this probe
                    "reason": (
                        "allele-exact match rate is the time-shift witness's own "
                        "currency; it is not ATP pressure and carries no contact cost"
                        if kind == "matrix_allele_exact"
                        else "pi_realised computed on compact[:6] windows invented by "
                        "this probe; the live model has no recognition window and no "
                        "graded-affinity ATP debit, so this is not the model's pressure"
                    ),
                }
            )

    missing_preconditions = []
    if not any_genotype_antagonist:
        missing_preconditions.append(
            "No dated history contains an antagonist genotype population: the live "
            "GenesisEngine runs zero antagonists (source token count 0), the Idea-2 "
            "census antagonist is a capped scalar counter "
            "(parasite_is_genotype_population=false on every arm), and the abstract "
            "HostParasiteWorld is not wired into the engine."
        )
    if not engine_has_antagonist_token:
        missing_preconditions.append(
            "GenesisEngine has no host-antagonist contact route, so no contact "
            "opportunity, no intended/realised debit and no pi_realised can be "
            "observed."
        )
    if not fork_complete or not parent_child:
        missing_preconditions.append(
            "No full-state checkpoint fork exists: RunCheckpoint carries only "
            "digests (no restorable state), checkpoint_fork_complete=false and "
            "parent_child_ids_recorded=false, so the frozen-antagonist, host-only "
            "and shuffled-label arms cannot start from one fork point with "
            "independent labelled RNG streams."
        )

    eligible_histories = 0
    if not missing_preconditions:
        eligible_histories = 8

    # ---- instrument (stage 0) ---------------------------------------------
    fx = fixtures.get("fixtures", [])
    instrument_rows = [
        {
            "fixture": r["fixture"],
            "label": r["repo_label"],
            "i_contemp": r["contrast"]["i_contemp"],
            "i_lag": r["contrast"]["i_lag"],
            "i_max_cell": r["contrast"]["i_max"]["cell"],
            "i_max_value": r["contrast"]["i_max"]["value"],
            "n_positive_cells": r["contrast"]["n_positive_cells"],
            "n_negative_cells": r["contrast"]["n_negative_cells"],
            "uniform_increase": r["contrast"]["uniform_increase"],
            "supports_fluctuating_selection": r["supports_fluctuating_selection"],
        }
        for r in fx
    ]
    randomisation = fixtures.get("randomisation_control", {})
    rotation = fixtures.get("rotation_control", {})

    stage0_ok = (
        (fixtures.get("repo_stage0", {}) or {}).get("rq1_hand_instrument", {}).get(
            "instrument_positive_case"
        )
        is True
        and randomisation.get("n_support_label") == 1
        and rotation.get("repo_rotated_label") not in {"contemporary_match", "lagged_match"}
        and all(
            (r["label"] in {"contemporary_match", "lagged_match"})
            == r["supports_fluctuating_selection"]
            for r in instrument_rows
        )
        and all((kernel.get("two_host_classes", {}) or {}).get(k) is False for k in ("histogram_used", "class_frequency_used"))
    )

    # ---- decision ----------------------------------------------------------
    if eligible_histories == 0 and missing_preconditions:
        decision = "BLOCKED_MEASUREMENT"
        decision_reason = (
            "The RQ-1 assay requires a dated history whose host and antagonist are "
            "genotype populations contacting under a realised-pressure law, plus a "
            "full-state fork for the frozen/host-only/shuffled arms. Neither exists "
            "on the live model. The stage-0 meter passes, but a passing instrument "
            "is not a result about a live population, so no effect can be estimated."
        )
    else:
        decision = "INCONCLUSIVE"
        decision_reason = "Not reached."

    effect_rows = []
    for r in instrument_rows:
        effect_rows.append(
            {
                "unit": "pre_registered_fixture_matrix",
                "arm": r["fixture"],
                "primary_outcome": "host_time_x_antagonist_time_interaction_contrast",
                "i_contemp": r["i_contemp"],
                "i_lag": r["i_lag"],
                "label": r["label"],
                "interval": {
                    "method": "time_label_randomisation_over_6_permutations",
                    "n_support_label": randomisation.get("n_support_label"),
                    "n_permutations": randomisation.get("n_permutations"),
                    "fraction": randomisation.get("fraction_support_label"),
                },
                "supports": r["supports_fluctuating_selection"],
            }
        )
    effect_rows.append(
        {
            "unit": "independent_population_history",
            "arm": "live_model",
            "primary_outcome": "host_time_x_antagonist_time_interaction_contrast",
            "i_contemp": None,
            "i_lag": None,
            "label": None,
            "interval": {
                "method": "run_level_cluster_bootstrap",
                "point": None,
                "lo": None,
                "hi": None,
                "n_runs": 0,
                "excludes_zero": None,
                "note": "undefined: zero eligible independent population histories",
            },
            "supports": None,
            "exclusion_reason": "missing preconditions listed in analysis.json",
        }
    )

    effect_table = {
        "schema_version": "rq1_effect_table_v1",
        "primary_outcome": (
            "interaction contrast I(h,a) = pi(h,a) - row_mean(h) - col_mean(a) + "
            "grand_mean of the host-time x antagonist-time realised-pressure matrix"
        ),
        "thresholds": {
            "scientific_effect_threshold": None,
            "note": "The program's 0.20 and -0.148 locks were not changed and are not used as RQ-1 acceptance thresholds.",
        },
        "rows": effect_rows,
        "paired_seed_level_effect": {
            "defined": False,
            "n_paired_seeds": 0,
            "reason": "no independent population history and no fork point",
        },
        "extinction_or_censoring_rate": {
            "defined": False,
            "reason": "no live RQ-1 run",
        },
    }

    analysis = {
        "schema_version": SCHEMA_VERSION,
        "repo_head": run.get("repo_head"),
        "sources": sources,
        "preconditions": {
            "antagonist_is_genotype_population": bool(any_genotype_antagonist),
            "antagonist_is_independent_population": bool(any_independent_antagonist),
            "engine_has_antagonist_token": bool(engine_has_antagonist_token),
            "checkpoint_fork_complete": bool(fork_complete),
            "parent_child_ids_recorded": bool(parent_child),
            "run_checkpoint_fields": fork.get("run_checkpoint_fields"),
            "run_checkpoint_carries_restorable_state": fork.get(
                "run_checkpoint_carries_restorable_state"
            ),
            "host_parasite_world_fork_methods": fork.get("host_parasite_world_methods"),
            "eligible_independent_population_histories": eligible_histories,
            "missing": missing_preconditions,
        },
        "stage0_instrument": {
            "passed": bool(stage0_ok),
            "fixtures": instrument_rows,
            "rotation_control_label": rotation.get("repo_rotated_label"),
            "rotation_control_i_contemp": (rotation.get("repo_rotated_contrast") or {}).get(
                "i_contemp"
            ),
            "randomisation_control": {
                "n_permutations": randomisation.get("n_permutations"),
                "n_support_label": randomisation.get("n_support_label"),
                "fraction_support_label": randomisation.get("fraction_support_label"),
            },
            "kernel_hand_cases": kernel,
            "label_reachability_under_affinity_law": (reach.get("reachable") or {}),
            "replay_identical": {
                "engine": det.get("engine_replay_identical"),
                "world": det.get("world_replay_identical"),
                "kernel": det.get("kernel_replay_identical"),
            },
            "note": (
                "A passing instrument fixture is not a population result. The "
                "contemporary and lagged fixtures receive support labels and a "
                "positive interaction contrast; the arms-race fixture is a main "
                "effect with a near-zero interaction; the frozen and host-only "
                "fixtures are flat; 5 of 6 time-label permutations destroy the "
                "support label."
            ),
        },
        "live_model_attempt": {
            "matrices_obtained": live_matrix_rows,
            "admissible_pi_realised_matrices": 0,
            "note": (
                "A 3x3 cross-time matrix can be computed from one HostParasiteWorld "
                "history, but neither variant is the model's pi_realised: the "
                "allele-exact matrix is a match rate, and the affinity matrix needs a "
                "recognition window this model does not define. Reporting either as "
                "the RQ-1 primary would be measurement outrunning the model."
            ),
        },
        "effect_and_interval_table": effect_table,
        "exclusions": [
            {
                "item": "live engine cells, seeds 301/302",
                "reason": "host-lineage census without an antagonist; not RQ-1 data",
            },
            {
                "item": "Idea-2 antagonist counter",
                "reason": "scalar counter, not a genotype population",
            },
            {
                "item": "HostParasiteWorld allele-exact matrix",
                "reason": "match rate, not ATP pressure",
            },
            {
                "item": "HostParasiteWorld compact[:6] affinity matrix",
                "reason": "recognition window invented by this probe, not a model definition",
            },
        ],
        "flags": {
            "hypothesis_supported": False,
            "red_queen_proved": False,
            "arms_race_proved": False,
            "population_run": False,
            "instrument_positive_case": bool(stage0_ok),
        },
        "decision": decision,
        "decision_reason": decision_reason,
    }
    if decision not in DECISION_CODES:
        raise SystemExit("decision not in the program's code set")

    analysis_body = {k: v for k, v in analysis.items()}
    analysis["analysis_digest"] = canonical_digest(analysis_body)

    (OUT / "analysis.json").write_text(
        json.dumps(analysis, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (OUT / "effect_table.json").write_text(
        json.dumps(effect_table, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "decision": decision,
                "stage0_passed": stage0_ok,
                "missing_preconditions": len(missing_preconditions),
                "admissible_pi_realised_matrices": 0,
                "analysis_digest": analysis["analysis_digest"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
