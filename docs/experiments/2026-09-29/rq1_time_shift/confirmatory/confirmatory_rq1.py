"""RQ-1 CONFIRMATORY pack — locked design, 8 unseen seeds x 2 regimes x 200 gens.

Runs against the isolated extraction (commit 6187ff4). Resumable: a completed
seed is written to raw/seed_<n>.json and skipped on re-run.

Locked design, nothing re-tunable:
  seeds        5701..5708 (unseen)
  generations  200 (never shortened)
  regimes      copassaged (coevolve) and fixed (frozen antagonist)
  arms         contemporary = I(now,now); lagged = mean(I(now,past),I(future,now))
               of the coevolve matrix; frozen = same scalars on the fixed regime
  slots        past=90, now=100, future=110 (lag 10)
  contact      equal exposure, contact_mode=full_matrix, kappa=1.2, reserve infinite
  estimator    host-time x antagonist-time interaction contrast
  controls     frozen arm exactly 0; six shuffled antagonist time labels
  interval     95% paired t interval (causal_validation._paired_interval)
  flags        hypothesis_supported=false, red_queen_proved=false until complete

Per-generation JSONL is written from the arm's generation-boundary observer, so
it is flushed as the run advances; a summary snapshot is written every 10
generations and the buffers are flushed every 25.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import time
import traceback
from pathlib import Path

from rq1_design import assert_meter_pins  # noqa: E402

HERE = Path(__file__).resolve().parent
OUT = HERE
RAW = HERE / "raw"
EXTRACTION = HERE
CONFIG_DIGEST = (
    "rq1_confirmatory:d44a70140eeef5876ea68c838ca442de38f5e05cfeaeabd71bab2be38479c807"
)

SCHEMA = "rq1_confirmatory_v1"
COMMIT = "6187ff4"
SEEDS = (5701, 5702, 5703, 5704, 5705, 5706, 5707, 5708)
GENERATIONS = 200
TIMES = ("past", "now", "future")
SLOTS = {"past": 90, "now": 100, "future": 110}
REGIMES = {"copassaged": "coevolve", "fixed": "frozen"}
KAPPA = 1.2
SUPPORT_LABELS = {"contemporary_match", "lagged_match"}
SUMMARY_EVERY = 10

LOCKED_CONFIG = {
    "test": "RQ-1",
    "commit": COMMIT,
    "seeds": list(SEEDS),
    "generations": GENERATIONS,
    "times": list(TIMES),
    "slots": SLOTS,
    "regimes": REGIMES,
    "kappa": KAPPA,
    "contact_mode": "full_matrix",
    "arms": ["contemporary", "lagged", "frozen"],
    "estimator": "host_time_x_antagonist_time_interaction_contrast",
    "controls": ["frozen_exactly_zero", "shuffled_time_labels_6_permutations"],
    "interval": "causal_validation._paired_interval (95% paired t)",
    "flags_locked_false": ["hypothesis_supported", "red_queen_proved"],
}


def class_to_window(cls: str) -> str:
    return str(cls).replace("|", "")


def pressure_cell(host_freq: dict, ant_classes: list) -> float:
    if not host_freq or not ant_classes:
        return 0.0
    res = realised_conditional_host_pressure(
        {c: class_to_window(c) for c in host_freq},
        {c: class_to_window(c) for c in ant_classes},
        contact_mode="full_matrix",
        virulence=8.0,
        steal_fraction=0.15,
    )
    p = res["pressure"]
    return float(sum(w * float(p[c]) for c, w in host_freq.items()))


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


def initial_state(arm_name: str, seed: int) -> dict:
    arm = StructuralRQArm.boot_structural(arm=arm_name, seed=seed)
    genomes = sorted(
        str(org.genome.digest())
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


class _Emitter:
    """Writes per-generation raw JSONL and the 10-generation summary snapshots."""

    def __init__(self, seed: int, regime: str, passage: str) -> None:
        self.seed = seed
        self.regime = regime
        self.passage = passage
        self.run_id = f"rq1-conf-s{seed}-{regime}"
        self.events = (RAW / f"events_seed{seed}.jsonl").open("a", encoding="utf-8")
        self.population = (RAW / f"population_seed{seed}.jsonl").open("a", encoding="utf-8")
        self.summary = (RAW / f"summary_seed{seed}.jsonl").open("a", encoding="utf-8")

    def __call__(self, *, generation_index: int, arm) -> None:
        gen = int(generation_index)
        snap = arm.window_snapshot(gen)
        self.events.write(
            json.dumps(
                {
                    "schema_version": SCHEMA,
                    "run_id": self.run_id,
                    "seed": self.seed,
                    "regime": self.regime,
                    "passage": self.passage,
                    "generation": gen,
                    "event_id": f"{self.run_id}-g{gen}",
                    "organism_id": None,
                    "parent_id": None,
                    "genotype_digest": None,
                    "antagonist_digest": None,
                    "contact_edge_id": None,
                    "opportunity": snap["parasite_n"],
                    "matched": len(snap["host_realised_pressure"]),
                    "intended_debit": None,
                    "realised_debit": None,
                    "atp_before": None,
                    "atp_after": None,
                    "birth": None,
                    "death": None,
                    "mutation": None,
                    "intervention_id": None,
                    "null_reason": (
                        "cross-time assay is computed outside the arm at the three "
                        "pre-declared slots; this record is the generation aggregate"
                    ),
                    "census": snap["census"],
                    "host_classes": len(snap["joint_freq"]),
                    "antagonist_classes": len(snap["parasite_class_hist"]),
                },
                sort_keys=True,
            )
            + "\n"
        )
        self.population.write(
            json.dumps(
                {
                    "schema_version": SCHEMA,
                    "run_id": self.run_id,
                    "seed": self.seed,
                    "regime": self.regime,
                    "generation": gen,
                    "census": snap["census"],
                    "host_joint_class_frequencies": dict(snap["joint_freq"]),
                    "host_joint_richness": snap["joint_richness"],
                    "dominant_host_class": snap["dominant_joint"],
                    "antagonist_class_frequencies": dict(snap["parasite_class_hist"]),
                    "antagonist_n": snap["parasite_n"],
                    "model_realised_pressure": dict(snap["host_realised_pressure"]),
                },
                sort_keys=True,
            )
            + "\n"
        )
        if gen % SUMMARY_EVERY == 0:
            self.summary.write(
                json.dumps(
                    {
                        "generation": gen,
                        "census": snap["census"],
                        "host_classes": len(snap["joint_freq"]),
                        "antagonist_classes": len(snap["parasite_class_hist"]),
                        "antagonist_n": snap["parasite_n"],
                        "dominant_host_class": snap["dominant_joint"],
                    },
                    sort_keys=True,
                )
                + "\n"
            )
            self.summary.flush()
        if gen % 25 == 0:
            self.events.flush()
            self.population.flush()

    def close(self) -> None:
        for handle in (self.events, self.population, self.summary):
            handle.flush()
            handle.close()


def run_seed(seed: int) -> dict:
    started = time.perf_counter()
    # A seed is only started when raw/seed_<seed>.json is absent, so any JSONL
    # left by an interrupted attempt is a partial prefix. Truncate it once here
    # so the two regimes append into a clean, single-run stream.
    for name in (
        f"events_seed{seed}.jsonl",
        f"population_seed{seed}.jsonl",
        f"summary_seed{seed}.jsonl",
    ):
        (RAW / name).write_text("", encoding="utf-8")
    rec: dict = {
        "schema_version": SCHEMA,
        "seed": seed,
        "generations": GENERATIONS,
        "slots": dict(SLOTS),
        "config_digest": CONFIG_DIGEST,
        "commit": COMMIT,
        "regimes": {},
        "errors": [],
    }
    init = [initial_state(name, seed) for name in REGIMES]
    rec["arm_initial_state"] = init
    rec["arm_match_at_generation_0"] = (
        len({(i["census"], i["genome_digest"], i["parasite_windows_sha"]) for i in init}) == 1
    )

    for regime, passage in REGIMES.items():
        emitter = _Emitter(seed, regime, passage)
        try:
            arm = StructuralRQArm.boot_structural(arm=regime, seed=seed)
            arm.collect_realised_host_pressure = True
            emitter_arm = arm

            def _bridge(*, generation_index: int, _e=emitter, _a=emitter_arm) -> None:
                _e(generation_index=generation_index, arm=_a)

            arm.generation_boundary_observer = _bridge
            t0 = time.perf_counter()
            arm.run_generations(GENERATIONS)
            wall = time.perf_counter() - t0
            snaps = {slot: arm.window_snapshot(SLOTS[slot]) for slot in TIMES}
            matrix = {}
            for ti in TIMES:
                matrix[ti] = {}
                hf = {str(k): float(v) for k, v in snaps[ti]["joint_freq"].items()}
                for tj in TIMES:
                    matrix[ti][tj] = round(
                        pressure_cell(
                            hf, [str(k) for k in snaps[tj]["parasite_class_hist"]]
                        ),
                        10,
                    )
            c = contrast(matrix)
            rec["regimes"][regime] = {
                "passage": passage,
                "wall_s": round(wall, 3),
                "matrix": matrix,
                "contrast": c,
                "label": classify_time_shift_matrix(matrix),
                "rotation_labels": {
                    name: classify_time_shift_matrix(rotate_antagonist_labels(matrix))
                    for name in TIMES
                },
                "slot_diagnostics": {
                    slot: {
                        "census": snaps[slot]["census"],
                        "antagonist_n": snaps[slot]["parasite_n"],
                        "host_classes": len(snaps[slot]["joint_freq"]),
                        "antagonist_classes": len(snaps[slot]["parasite_class_hist"]),
                        "host_richness": snaps[slot]["joint_richness"],
                        "dominant_host": snaps[slot]["dominant_joint"],
                    }
                    for slot in TIMES
                },
                "gates": {
                    "variation": all(
                        len(snaps[s]["joint_freq"]) >= 2
                        and len(snaps[s]["parasite_class_hist"]) >= 2
                        for s in TIMES
                    ),
                    "non_zero": all(snaps[s]["census"] > 0 for s in TIMES),
                },
            }
        except Exception:  # noqa: BLE001
            rec["errors"].append({"regime": regime, "traceback": traceback.format_exc()})
        finally:
            emitter.close()
    rec["wall_s"] = round(time.perf_counter() - started, 3)
    co = rec["regimes"].get("copassaged", {})
    fx = rec["regimes"].get("fixed", {})
    rec["seed_gates_ok"] = bool(
        rec["arm_match_at_generation_0"]
        and not rec["errors"]
        and co.get("gates", {}).get("variation")
        and co.get("gates", {}).get("non_zero")
        and fx.get("gates", {}).get("variation")
    )
    if fx:
        fvals = [float(fx["matrix"][h][a]) for h in TIMES for a in TIMES]
        rec["frozen_is_zero"] = bool(
            max(fvals) - min(fvals) <= 1e-12
            and abs(float(fx["contrast"]["i_contemp"])) < 1e-12
            and abs(float(fx["contrast"]["i_lag"])) < 1e-12
        )
    else:
        rec["frozen_is_zero"] = False
    rec["hypothesis_supported"] = False
    rec["red_queen_proved"] = False
    (RAW / f"seed_{seed}.json").write_text(
        json.dumps(rec, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8"
    )
    return rec


def _install(argv: list[str] | None = None) -> None:
    """Bind the runner to an explicit checkout. A missing path or a commit mismatch stops."""

    global OUT, RAW, EXTRACTION
    global canonical_digest, _paired_interval, classify_time_shift_matrix
    global rotate_antagonist_labels, StructuralRQArm, realised_conditional_host_pressure
    parser = argparse.ArgumentParser(description="RQ-1 confirmatory runner")
    parser.add_argument("--reference-checkout", required=True)
    parser.add_argument("--expect-commit", default=COMMIT)
    parser.add_argument("--output", required=True)
    args = parser.parse_args(argv)
    checkout = Path(args.reference_checkout).resolve()
    out = Path(args.output).resolve()
    if out == HERE:
        raise SystemExit(
            "refusing to write into the historical confirmatory directory; pass a fresh --output"
        )
    if not checkout.is_dir():
        raise SystemExit(f"reference checkout does not exist: {checkout}")
    proc = subprocess.run(
        ["git", "-C", str(checkout), "rev-parse", "HEAD"],
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        raise SystemExit(proc.stderr.strip() or "git rev-parse failed on the reference checkout")
    head = proc.stdout.strip()
    if not head.startswith(args.expect_commit):
        raise SystemExit(
            f"commit mismatch: HEAD {head} does not match {args.expect_commit}; "
            "refusing to run the live tip under the pinned label"
        )
    assert_meter_pins(checkout)
    src = checkout / "src"
    if not (src / "codontrace").is_dir():
        raise SystemExit(f"codontrace package missing under {src}")
    sys.path.insert(0, str(src))
    from codontrace.genesis.campaigns.discovery_program_20260929_stage0 import (
        classify_time_shift_matrix as _classify,
    )
    from codontrace.genesis.campaigns.discovery_program_20260929_stage0 import (
        rotate_antagonist_labels as _rotate,
    )
    from codontrace.genesis.canonical import canonical_digest as _digest
    from codontrace.genesis.causal_validation import _paired_interval as _interval
    from codontrace.genesis.closed_loop_hp_arm01_structural_rq import (
        StructuralRQArm as _arm,
    )
    from codontrace.genesis.measurements.rq_frequency_clocks import (
        realised_conditional_host_pressure as _pressure,
    )

    digest = _digest(LOCKED_CONFIG, prefix="rq1_confirmatory")
    if digest != CONFIG_DIGEST:
        raise SystemExit(f"config digest mismatch: {digest}")
    canonical_digest = _digest
    _paired_interval = _interval
    classify_time_shift_matrix = _classify
    rotate_antagonist_labels = _rotate
    StructuralRQArm = _arm
    realised_conditional_host_pressure = _pressure
    EXTRACTION = checkout
    OUT = out
    RAW = out / "raw"
    RAW.mkdir(parents=True, exist_ok=True)


def main() -> int:
    _install()
    started = time.perf_counter()
    completed = []
    for seed in SEEDS:
        path = RAW / f"seed_{seed}.json"
        if path.exists():
            completed.append(seed)
            continue
        try:
            rec = run_seed(seed)
            completed.append(seed)
            print(
                json.dumps(
                    {
                        "seed": seed,
                        "done": True,
                        "wall_s": rec["wall_s"],
                        "frozen_is_zero": rec["frozen_is_zero"],
                        "gates_ok": rec["seed_gates_ok"],
                    }
                ),
                flush=True,
            )
        except Exception:  # noqa: BLE001
            (OUT / "errors.log").write_text(traceback.format_exc(), encoding="utf-8")
            break
    manifest = {
        "schema_version": "rq1_confirmatory_manifest_v1",
        "round": 3,
        "commit": COMMIT,
        "commit_source": "git archive of 6187ff4 at test-runs/verify/full6187ff4",
        "provenance": {
            "pin": COMMIT,
            "seeds_5701_5702": COMMIT,
            "seeds_from_5703": COMMIT,
            "engine_changes_after_pin": [
                "40138c9 RNG migration",
                "913f18e from_fork restoration",
                "02cc725 docs-only",
            ],
            "comparability": (
                "Every seed runs against the same pinned extraction "
                "(test-runs/verify/full6187ff4), so all seeds share exactly one "
                "engine revision. The post-6187ff4 changes are absent from this "
                "pin; they touch the RNG migration and from_fork restoration "
                "paths, which the RQ-1 arm run does not use. The two groups are "
                "therefore comparable by construction, not by assumption."
            ),
        },
        "extraction_path": str(EXTRACTION),
        "extraction_pyproject_sha256": hashlib.sha256(
            (EXTRACTION / "pyproject.toml").read_bytes()
        ).hexdigest(),
        "config_digest": CONFIG_DIGEST,
        "locked_config": LOCKED_CONFIG,
        "seeds_locked": list(SEEDS),
        "seeds_completed": completed,
        "seeds_remaining": [s for s in SEEDS if s not in completed],
        "rng_derivation": (
            "StructuralRQArm.boot_structural(seed) + "
            "RNGManager(seed, namespace=f'hp-struct-rq-{arm}') + "
            "rng.fork(f'passage/{tick}')"
        ),
        "generations": GENERATIONS,
        "pack_wall_s": round(time.perf_counter() - started, 3),
        "python": sys.version,
        "env": {
            "PYTHONUTF8": os.environ.get("PYTHONUTF8"),
            "PYTHONIOENCODING": os.environ.get("PYTHONIOENCODING"),
        },
        "hypothesis_supported": False,
        "red_queen_proved": False,
        "status": "complete" if len(completed) == len(SEEDS) else "partial",
    }
    (OUT / "run_manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"status": manifest["status"], "completed": completed}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
