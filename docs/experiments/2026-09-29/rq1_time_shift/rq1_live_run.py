"""RQ-1 live run on the structural RQ arm (no repository change required).

Route
-----
`StructuralRQArm` is a live life-loop host/antagonist coevolutionary arm:
host match windows are genomes under a bit-flip mutation regime, the antagonist
is a stock of 64 recognition windows that is partially kept and partially
re-drawn from this generation's *matched* windows and mutated (heritable,
mutating, selected), and the arm archives, per generation, the host joint match
classes with counts and the antagonist class counts.

Assay (built outside evolution, exactly as RQ-1 states)
------------------------------------------------------
From one dated history take three host snapshots (t-lag, t, t+lag) and three
antagonist snapshots of the *same* history.  For every (host time, antagonist
time) cell, contact every host class present at the host time with every
antagonist class present at the antagonist time under **equal exposure**
(`contact_mode="full_matrix"`, one opportunity per class pair, equal kappa and
equal reserve), and take the realised pressure

    pi(h, a) = kappa * A(h, a)          (capped variant reported separately)

    pi_cell(ti, tj) = sum_h w_h(ti) * mean_a pi(h, a)      [population pressure]
    pi_dom (ti, tj) = mean_a pi(dominant host class at ti, a)   [secondary]

Primary outcome: the host-time x antagonist-time interaction contrast
    I(ti, tj) = pi(ti, tj) - row_mean(ti) - col_mean(tj) + grand
with I_contemp = I(now, now) and I_lag = mean(I(now, past), I(future, now)).

Arms: copassaged (coevolve), fixed (frozen antagonist), avirulent (host-only).
Control: the six permutations of the antagonist time labels.

Budget (pre-declared, ceilings only): measured 1.6 s/generation/arm; each seed
runs 3 arms x 40 generations ~ 3.2 min (< 8 min per test), the pack is two
calibration seeds plus four pilot seeds ~ 19 min (< 45 min).
"""

from __future__ import annotations

import hashlib
import json
import sys
import time
import traceback
from pathlib import Path

REPO = Path(r"E:\مقاله پزشکی شبیه سازی ویروس\codontrace-genesis")
if str(REPO / "src") not in sys.path:
    sys.path.insert(0, str(REPO / "src"))

from codontrace.genesis.campaigns.discovery_program_20260929_stage0 import (  # noqa: E402
    classify_time_shift_matrix,
    rotate_antagonist_labels,
)
from codontrace.genesis.closed_loop_hp_arm01_structural_rq import (  # noqa: E402
    ECOLOGY_ARMS,
    StructuralRQArm,
)
from codontrace.genesis.measurements.rq_frequency_clocks import (  # noqa: E402
    realised_conditional_host_pressure,
    run_level_cluster_bootstrap_interval,
)

OUT = Path(__file__).resolve().parent
RAW = OUT / "raw"
RAW.mkdir(parents=True, exist_ok=True)

SCHEMA_VERSION = "rq1_live_run_v1"
TIMES = ("past", "now", "future")
SLOTS = {"past": 20, "now": 30, "future": 40}
GENERATIONS = 40
CALIBRATION_SEEDS = (5501, 5502)
PILOT_SEEDS = (5601, 5602, 5603, 5604)
RESERVED_SEEDS = (5701, 5702, 5703, 5704, 5705, 5706, 5707, 5708)
KAPPA = 1.2
CAP_ATP = 1.2
SUPPORT_LABELS = {"contemporary_match", "lagged_match"}
ARM_PASSAGE = {"avirulent": "absent", "fixed": "frozen", "copassaged": "coevolve"}

import os  # noqa: E402

if os.environ.get("RQ1_SMOKE", "").strip() == "1":
    GENERATIONS = 12
    SLOTS = {"past": 4, "now": 8, "future": 12}
    CALIBRATION_SEEDS = (5501,)
    PILOT_SEEDS = ()


def class_to_window(cls: str) -> str:
    return str(cls).replace("|", "")


def pressure_cell(
    host_freq: dict[str, float],
    antagonist_classes: list[str],
    *,
    cap: float | None,
) -> float:
    """Frequency-weighted realised pressure on the host population at one time."""

    if not host_freq or not antagonist_classes:
        return 0.0
    host_windows = {c: class_to_window(c) for c in host_freq}
    ant_windows = {c: class_to_window(c) for c in antagonist_classes}
    res = realised_conditional_host_pressure(
        host_windows,
        ant_windows,
        contact_mode="full_matrix",
        virulence=8.0,
        steal_fraction=0.15,
        host_capacity_units=cap,
    )
    pressure = res["pressure"]
    return float(sum(w * float(pressure[c]) for c, w in host_freq.items()))


def dominant_cell(
    host_snap: dict, antagonist_classes: list[str], *, cap: float | None
) -> float:
    dom = host_snap.get("dominant_joint")
    if dom is None or not antagonist_classes:
        return 0.0
    res = realised_conditional_host_pressure(
        {str(dom): class_to_window(str(dom))},
        {c: class_to_window(c) for c in antagonist_classes},
        contact_mode="full_matrix",
        virulence=8.0,
        steal_fraction=0.15,
        host_capacity_units=cap,
    )
    return float(res["pressure"][str(dom)])


def interaction_contrast(matrix: dict[str, dict[str, float]]) -> dict:
    cells = [float(matrix[h][a]) for h in TIMES for a in TIMES]
    grand = sum(cells) / len(cells)
    row_mean = {h: sum(float(matrix[h][a]) for a in TIMES) / 3.0 for h in TIMES}
    col_mean = {a: sum(float(matrix[h][a]) for h in TIMES) / 3.0 for a in TIMES}
    inter = {
        h: {a: float(matrix[h][a]) - row_mean[h] - col_mean[a] + grand for a in TIMES}
        for h in TIMES
    }
    best = max(
        ((h, a) for h in TIMES for a in TIMES), key=lambda c: inter[c[0]][c[1]]
    )
    vals = [inter[h][a] for h in TIMES for a in TIMES]
    n_pos = sum(1 for v in vals if v > 1e-15)
    n_neg = sum(1 for v in vals if v < -1e-15)
    return {
        "grand_mean": round(grand, 10),
        "i_contemp": round(inter["now"]["now"], 10),
        "i_lag": round((inter["now"]["past"] + inter["future"]["now"]) / 2.0, 10),
        "i_max": {"cell": list(best), "value": round(inter[best[0]][best[1]], 10)},
        "n_positive_cells": n_pos,
        "n_negative_cells": n_neg,
        "uniform_increase": bool(n_pos > 0 and n_neg == 0),
        "interaction": {h: {a: round(inter[h][a], 10) for a in TIMES} for h in TIMES},
    }


def support_decision(label: str, contrast: dict) -> bool:
    return bool(
        label in SUPPORT_LABELS
        and (contrast["i_contemp"] > 0.0 or contrast["i_lag"] > 0.0)
        and not contrast["uniform_increase"]
        and contrast["i_max"]["cell"] in (["now", "now"], ["now", "past"], ["future", "now"])
    )


def arm_initial_state(arm_name: str, seed: int) -> dict:
    arm = StructuralRQArm.boot_structural(arm=arm_name, seed=seed)
    genomes = sorted(
        str(getattr(org, "genome").digest())
        for org in arm.runner.population.organisms
        if getattr(org, "genome", None) is not None
    )
    return {
        "arm": arm_name,
        "census": len(arm.runner.population.organisms),
        "genome_digest": hashlib.sha256("".join(genomes).encode()).hexdigest(),
        "parasite_windows_sha": hashlib.sha256(
            "|".join(arm.parasite_windows).encode()
        ).hexdigest(),
    }


def run_seed(seed: int, events: list[dict], population: list[dict]) -> dict:
    started = time.perf_counter()
    record: dict = {
        "schema_version": SCHEMA_VERSION,
        "seed": seed,
        "generations": GENERATIONS,
        "slots": dict(SLOTS),
        "arms": {},
        "errors": [],
    }
    initial = [arm_initial_state(name, seed) for name in ECOLOGY_ARMS]
    record["arm_initial_state"] = initial
    record["arm_match_at_generation_0"] = (
        len(
            {
                (i["census"], i["genome_digest"], i["parasite_windows_sha"])
                for i in initial
            }
        )
        == 1
    )

    for arm_name in ECOLOGY_ARMS:
        t0 = time.perf_counter()
        try:
            arm = StructuralRQArm.boot_structural(arm=arm_name, seed=seed)
            arm.collect_realised_host_pressure = True
            arm.run_generations(GENERATIONS)
        except Exception:  # noqa: BLE001
            record["errors"].append(
                {"arm": arm_name, "traceback": traceback.format_exc()}
            )
            continue
        wall = time.perf_counter() - t0

        snaps = {}
        for slot in TIMES:
            snaps[slot] = arm.window_snapshot(SLOTS[slot])

        matrix: dict[str, dict[str, float]] = {}
        matrix_dom: dict[str, dict[str, float]] = {}
        matrix_capped: dict[str, dict[str, float]] = {}
        for ti in TIMES:
            matrix[ti] = {}
            matrix_dom[ti] = {}
            matrix_capped[ti] = {}
            host_freq = {
                str(k): float(v) for k, v in snaps[ti]["joint_freq"].items()
            }
            for tj in TIMES:
                ant = [str(k) for k in snaps[tj]["parasite_class_hist"]]
                matrix[ti][tj] = round(
                    pressure_cell(host_freq, ant, cap=None), 10
                )
                matrix_dom[ti][tj] = round(
                    dominant_cell(snaps[ti], ant, cap=None), 10
                )
                matrix_capped[ti][tj] = round(
                    pressure_cell(host_freq, ant, cap=CAP_ATP), 10
                )

        contrast = interaction_contrast(matrix)
        contrast_dom = interaction_contrast(matrix_dom)
        label = classify_time_shift_matrix(matrix)
        flipped = {
            name: classify_time_shift_matrix(rotate_antagonist_labels(matrix))
            for name in TIMES
        }
        record["arms"][arm_name] = {
            "passage": arm.passage,
            "wall_s": round(wall, 3),
            "s_per_generation": round(wall / GENERATIONS, 4),
            "matrix_population_pressure": matrix,
            "matrix_dominant_host": matrix_dom,
            "matrix_capped_at_1p2atp": matrix_capped,
            "contrast_population": contrast,
            "contrast_dominant": contrast_dom,
            "label": label,
            "supports": support_decision(label, contrast),
            "rotation_labels": flipped,
            "slot_diagnostics": {
                slot: {
                    "census": snaps[slot]["census"],
                    "parasite_n": snaps[slot]["parasite_n"],
                    "host_classes": len(snaps[slot]["joint_freq"]),
                    "antagonist_classes": len(snaps[slot]["parasite_class_hist"]),
                    "host_richness": snaps[slot]["joint_richness"],
                    "dominant_host": snaps[slot]["dominant_joint"],
                    "model_realised_pressure_classes": len(
                        snaps[slot]["host_realised_pressure"]
                    ),
                }
                for slot in TIMES
            },
            "turnover_tail": {
                "kept": arm.turnover_kept[-5:],
                "replaced": arm.turnover_replaced[-5:],
                "mut_events": arm.turnover_mut_events[-5:],
            },
        }

        for gen in range(1, GENERATIONS + 1):
            snap = arm.window_snapshot(gen)
            run_id = f"rq1-live-s{seed}-{arm_name}"
            events.append(
                {
                    "schema_version": SCHEMA_VERSION,
                    "record_role": "generation_aggregate",
                    "run_id": run_id,
                    "seed": seed,
                    "arm": arm_name,
                    "passage": arm.passage,
                    "generation": gen,
                    "event_id": f"{run_id}-g{gen}",
                    "organism_id": None,
                    "organism_id_null_reason": "arm exposes generation aggregates, not per-contact events",
                    "parent_id": None,
                    "parent_id_null_reason": "no per-contact genealogy exposed by this arm",
                    "genotype_digest": None,
                    "genotype_digest_null_reason": "aggregate record; class tables are in population.jsonl",
                    "antagonist_digest": None,
                    "antagonist_digest_null_reason": "aggregate record; antagonist class table is in population.jsonl",
                    "contact_edge_id": None,
                    "contact_edge_id_null_reason": "the arm reports per-class contact evidence, not edge ids",
                    "opportunity": snap["parasite_n"],
                    "matched": sum(1 for _ in snap["host_realised_pressure"]),
                    "intended_debit": None,
                    "intended_debit_null_reason": "cross-time assay is computed outside the arm and stored in the matrix",
                    "realised_debit": None,
                    "realised_debit_null_reason": "see population.jsonl model_realised_pressure",
                    "atp_before": None,
                    "atp_after": None,
                    "birth": None,
                    "death": None,
                    "mutation": None,
                    "intervention_id": None,
                    "host_classes": len(snap["joint_freq"]),
                    "antagonist_classes": len(snap["parasite_class_hist"]),
                    "census": snap["census"],
                }
            )
            population.append(
                {
                    "schema_version": SCHEMA_VERSION,
                    "record_role": "generation_population",
                    "run_id": run_id,
                    "seed": seed,
                    "arm": arm_name,
                    "passage": arm.passage,
                    "generation": gen,
                    "census": snap["census"],
                    "host_joint_class_counts_and_frequencies": dict(snap["joint_freq"]),
                    "host_joint_richness": snap["joint_richness"],
                    "dominant_host_class": snap["dominant_joint"],
                    "antagonist_class_frequencies": dict(snap["parasite_class_hist"]),
                    "antagonist_n": snap["parasite_n"],
                    "model_realised_pressure": dict(snap["host_realised_pressure"]),
                    "pi_realised_note": (
                        "model_realised_pressure is the arm's same-generation "
                        "realised conditional pressure per host class (ATP per host "
                        "per generation); the cross-time matrix is in live_run.json"
                    ),
                    "fitness": None,
                    "fitness_null_reason": "the arm does not expose a per-class fitness",
                    "genealogy": None,
                    "genealogy_null_reason": "the arm does not expose per-organism genealogy here",
                }
            )

    record["wall_s"] = round(time.perf_counter() - started, 3)
    return record


def main() -> int:
    started = time.perf_counter()
    events: list[dict] = []
    population: list[dict] = []
    report: dict = {
        "schema_version": SCHEMA_VERSION,
        "route": "StructuralRQArm (closed_loop_hp_arm01_structural_rq)",
        "design": {
            "slots": dict(SLOTS),
            "generations": GENERATIONS,
            "times": list(TIMES),
            "kappa": KAPPA,
            "cap_atp_secondary": CAP_ATP,
            "primary": "frequency-weighted population realised pressure",
            "secondary": "dominant host class realised pressure",
            "calibration_seeds": list(CALIBRATION_SEEDS),
            "pilot_seeds": list(PILOT_SEEDS),
            "reserved_seeds_not_drawn": list(RESERVED_SEEDS),
            "budget": {
                "measured_s_per_generation_per_arm": 1.6,
                "cap_wall_s_per_test": 480,
                "cap_wall_s_first_pack": 2700,
            },
        },
        "arm_passage_map": ARM_PASSAGE,
        "seeds": [],
        "errors": [],
    }

    calibration_ok = True
    pilot_ok = True
    for phase, seeds in (("calibration", CALIBRATION_SEEDS), ("pilot", PILOT_SEEDS)):
        for seed in seeds:
            if phase == "pilot" and not calibration_ok:
                report["seeds"].append(
                    {
                        "seed": seed,
                        "phase": phase,
                        "skipped": "calibration gate failed; pilot not started",
                    }
                )
                continue
            try:
                rec = run_seed(seed, events, population)
                rec["phase"] = phase
                report["seeds"].append(rec)
                co = rec["arms"].get("copassaged", {})
                diag = co.get("slot_diagnostics", {})
                seed_gate_ok = bool(
                    rec.get("arm_match_at_generation_0")
                    and not rec.get("errors")
                    and diag
                    and all(
                        d["host_classes"] >= 2
                        and d["antagonist_classes"] >= 2
                        and d["parasite_n"] > 0
                        and d["census"] > 0
                        for d in diag.values()
                    )
                )
                rec["seed_gate_ok"] = seed_gate_ok
                if phase == "calibration":
                    calibration_ok = calibration_ok and seed_gate_ok
                    if not calibration_ok and "calibration_gate_failed_at_seed" not in report:
                        report["calibration_gate_failed_at_seed"] = seed
                else:
                    pilot_ok = pilot_ok and seed_gate_ok
            except Exception:  # noqa: BLE001
                report["errors"].append(
                    {"seed": seed, "phase": phase, "traceback": traceback.format_exc()}
                )
                if phase == "calibration":
                    calibration_ok = False
                else:
                    pilot_ok = False
    report["calibration_gate_ok"] = calibration_ok
    report["pilot_gate_ok"] = pilot_ok

    # ---- seed-level summary -------------------------------------------------
    def seed_values(arm_name: str, key: str) -> list[float]:
        out = []
        for rec in report["seeds"]:
            arm = (rec.get("arms") or {}).get(arm_name)
            if arm:
                out.append(float(arm["contrast_population"][key]))
        return out

    summary: dict = {"arms": {}}
    for arm_name in ECOLOGY_ARMS:
        vals_contemp = seed_values(arm_name, "i_contemp")
        vals_lag = seed_values(arm_name, "i_lag")
        labels = [
            (rec.get("arms") or {}).get(arm_name, {}).get("label")
            for rec in report["seeds"]
        ]
        supports = [
            bool((rec.get("arms") or {}).get(arm_name, {}).get("supports"))
            for rec in report["seeds"]
            if (rec.get("arms") or {}).get(arm_name)
        ]
        entry = {
            "n_seeds": len(vals_contemp),
            "labels": labels,
            "n_support": sum(1 for s in supports if s),
            "i_contemp_values": vals_contemp,
            "i_lag_values": vals_lag,
            "i_contemp_mean": (sum(vals_contemp) / len(vals_contemp)) if vals_contemp else None,
            "i_lag_mean": (sum(vals_lag) / len(vals_lag)) if vals_lag else None,
        }
        if len(vals_contemp) >= 2:
            entry["i_contemp_interval"] = run_level_cluster_bootstrap_interval(vals_contemp)
            entry["i_lag_interval"] = run_level_cluster_bootstrap_interval(vals_lag)
        summary["arms"][arm_name] = entry

    # rotation control on the coevolve arm, pooled over seeds
    rot_labels: list[str] = []
    rot_support = 0
    for rec in report["seeds"]:
        arm = (rec.get("arms") or {}).get("copassaged")
        if not arm:
            continue
        for name, lab in arm["rotation_labels"].items():
            rot_labels.append(lab)
            rot_support += int(lab in SUPPORT_LABELS)
    summary["rotation_control"] = {
        "n": len(rot_labels),
        "n_support_label": rot_support,
        "fraction_support_label": (rot_support / len(rot_labels)) if rot_labels else None,
        "labels": rot_labels,
    }

    co = summary["arms"].get("copassaged", {})
    frozen = summary["arms"].get("fixed", {})
    host_only = summary["arms"].get("avirulent", {})
    co_labels_support = all(
        lab in SUPPORT_LABELS for lab in co.get("labels", []) if lab is not None
    ) and bool(co.get("labels"))
    interval = co.get("i_contemp_interval") or {}
    effect_positive = (
        co.get("i_contemp_mean") is not None and co["i_contemp_mean"] > 0.0
    )
    frozen_also = (
        frozen.get("n_support", 0) > 0 and frozen.get("n_seeds", 0) > 0
        and frozen["n_support"] >= max(1, frozen["n_seeds"] // 2)
    )
    host_only_zero = all(
        abs(v) < 1e-12 for v in host_only.get("i_contemp_values", []) + host_only.get("i_lag_values", [])
    )

    if not report["seeds"] or not co.get("n_seeds"):
        verdict = "BLOCKED_MEASUREMENT"
        reason = "no live seed completed"
    elif frozen_also:
        verdict = "FALSIFIED_IN_MODEL"
        reason = "the frozen-antagonist control reproduces the support pattern"
    elif not co_labels_support or not effect_positive:
        verdict = "INCONCLUSIVE"
        reason = (
            "the coevolve arm does not show the pre-declared support pattern "
            "consistently across seeds, or the effect is not positive"
        )
    elif interval and not interval.get("excludes_zero"):
        verdict = "INCONCLUSIVE"
        reason = "the seed-level interval for I_contemp contains zero"
    else:
        verdict = "INCONCLUSIVE"
        reason = (
            "pilot-level only: the support pattern is present and the interval "
            "excludes zero, but the program reserves SUPPORTED_IN_MODEL for the "
            "eight-seed locked confirmatory run, which this budget did not fund"
        )

    summary["decision"] = {
        "verdict": verdict,
        "reason": reason,
        "frozen_also_supports": bool(frozen_also),
        "host_only_is_zero": bool(host_only_zero),
        "coevolve_labels_all_support": bool(co_labels_support),
        "confirmatory_run": False,
    }
    summary["flags"] = {
        "hypothesis_supported": False,
        "red_queen_proved": False,
        "population_run": True,
    }
    report["summary"] = summary
    report["wall_s"] = round(time.perf_counter() - started, 3)

    with (RAW / "live_events.jsonl").open("w", encoding="utf-8") as handle:
        for row in events:
            handle.write(json.dumps(row, sort_keys=True, default=str) + "\n")
        handle.flush()
    with (RAW / "live_population.jsonl").open("w", encoding="utf-8") as handle:
        for row in population:
            handle.write(json.dumps(row, sort_keys=True, default=str) + "\n")
        handle.flush()
    (RAW / "live_run.json").write_text(
        json.dumps(report, indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
    )
    (OUT / "live_summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(summary, indent=2, default=str))
    print("wall_s", report["wall_s"], "events", len(events), "population", len(population))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
