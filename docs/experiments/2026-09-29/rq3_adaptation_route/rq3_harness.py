"""RQ-3 stage-0 harness: live arms, raw JSONL, manifest, replay (read-only w.r.t. the repo).

Writes only under test-runs/rq3/. Import path is set to the repository src tree; no file
in the repository is created, modified or deleted by this script.

Usage:
  python rq3_harness.py --stage hand          # hand-computed contact/pressure cases
  python rq3_harness.py --stage time --seed 21001 --gens 1
  python rq3_harness.py --stage arm  --seed 21001 --gens 80 --arm coevolve
  python rq3_harness.py --stage replay --run-dir runs/<run_id>
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import sys
import time
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[3]
RUNS = ROOT / "runs"
SCHEMA_VERSION = "rq3-manifest-v1"
# Round number per the Lead's operating directive v2.1: the 50k cap is per round.
ROUND = 1

sys.path.insert(0, str(REPO / "src"))

from codontrace.genesis.closed_loop_hp_arm01 import (  # noqa: E402
    ARM_AVIRULENT,
    ARM_COPASSAGED,
    ARM_FIXED,
    _window,
)
from codontrace.genesis.closed_loop_hp_arm01_structural_rq import (  # noqa: E402
    StructuralRQArm,
    _population_unique_id_guard,
    graded_affinity,
    host_realised_pressure_from_contacts,
    joint_match_class,
)
from codontrace.genesis.organism import GenesisOrganism  # noqa: E402
from codontrace.rng import RNGManager  # noqa: E402

ARM_LABELS = {
    "coevolve": ARM_COPASSAGED,
    "fixed": ARM_FIXED,
    "absent": ARM_AVIRULENT,
}
ARMS = ("coevolve", "fixed", "absent")


# ----------------------------------------------------------------------------- helpers


def sha_json(obj: object) -> str:
    return hashlib.sha256(
        json.dumps(obj, sort_keys=True, separators=(",", ":"), default=str).encode()
    ).hexdigest()


def git_probe() -> dict[str, object]:
    """Read git metadata by file inspection only (no git binary, no writes)."""

    head = REPO / ".git" / "HEAD"
    out: dict[str, object] = {"repo_head_file": None, "commit": None, "dirty": None}
    try:
        raw = head.read_text(encoding="utf-8").strip()
        out["repo_head_file"] = raw
        if raw.startswith("ref:"):
            ref = raw.split(" ", 1)[1].strip()
            ref_file = REPO / ".git" / ref
            if ref_file.is_file():
                out["commit"] = ref_file.read_text(encoding="utf-8").strip()
        else:
            out["commit"] = raw
    except OSError as exc:  # pragma: no cover
        out["repo_head_file"] = f"unreadable: {exc}"
    # Dirty flag: any index file newer than the last commit metadata is not decisive,
    # so it is reported as unknown unless a comparison is available.
    out["dirty"] = "unknown (no git binary on PATH; not inferred from mtimes)"
    return out


def mem_rss_mb() -> float | None:
    try:
        import ctypes

        class PROCESS_MEMORY_COUNTERS(ctypes.Structure):
            _fields_ = [
                ("cb", ctypes.c_ulong),
                ("PageFaultCount", ctypes.c_ulong),
                ("PeakWorkingSetSize", ctypes.c_size_t),
                ("WorkingSetSize", ctypes.c_size_t),
                ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
                ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                ("PagefileUsage", ctypes.c_size_t),
                ("PeakPagefileUsage", ctypes.c_size_t),
            ]

        counters = PROCESS_MEMORY_COUNTERS()
        counters.cb = ctypes.sizeof(PROCESS_MEMORY_COUNTERS)
        ctypes.windll.psapi.GetProcessMemoryInfo(  # type: ignore[attr-defined]
            ctypes.windll.kernel32.GetCurrentProcess(), ctypes.byref(counters)
        )
        return round(counters.WorkingSetSize / (1024 * 1024), 1)
    except Exception:  # pragma: no cover
        return None


def organism_window(org: GenesisOrganism) -> str:
    return _window(org)


def phenotype_roles(arm: StructuralRQArm) -> list[dict[str, object]]:
    hosts = arm._hosts()
    return [
        {
            "organism_id": org.id,
            "genotype_window": organism_window(org),
            "host_class": joint_match_class(organism_window(org)),
            "atp_runtime": round(float(org.atp_state.runtime_available), 6),
        }
        for org in hosts
    ]


# ----------------------------------------------------------------------------- stages


def stage_hand() -> dict[str, object]:
    """Two hand-computed cases from the program's stage-0 record."""

    affinity = {
        "000000|000001": graded_affinity("000000", "000001"),
        "000000|000011": graded_affinity("000000", "000011"),
        "111100|000001": graded_affinity("111100", "000001"),
        "111100|000011": graded_affinity("111100", "000011"),
    }
    pressure_a = host_realised_pressure_from_contacts(
        host_affinity_sums={"A": 5 / 6 + 4 / 6},
        host_contact_counts={"A": 2},
        host_min_available={"A": 1000.0},
    )
    pressure_b = host_realised_pressure_from_contacts(
        host_affinity_sums={"B": 1 / 6 + 1 / 6},
        host_contact_counts={"B": 2},
        host_min_available={"B": 1000.0},
    )
    flat_a = host_realised_pressure_from_contacts(
        host_affinity_sums={"A": 0.5 + 0.5},
        host_contact_counts={"A": 2},
        host_min_available={"A": 1000.0},
    )
    flat_b = host_realised_pressure_from_contacts(
        host_affinity_sums={"B": 0.5 + 0.5},
        host_contact_counts={"B": 2},
        host_min_available={"B": 1000.0},
    )
    trunc_a = host_realised_pressure_from_contacts(
        host_affinity_sums={"A": 0.5},
        host_contact_counts={"A": 1},
        host_min_available={"A": 10.0},
    )
    trunc_b = host_realised_pressure_from_contacts(
        host_affinity_sums={"B": 0.5},
        host_contact_counts={"B": 1},
        host_min_available={"B": 0.5 / 1.2 * 0.6},
    )
    return {
        "affinity": affinity,
        "pi_A_hand": pressure_a,
        "pi_B_hand": pressure_b,
        "pi_flat": {"A": flat_a, "B": flat_b},
        "pi_truncated": {"A": trunc_a, "B": trunc_b},
        "expected": {
            "pi_A": 0.9,
            "pi_B": 0.1,
            "difference": 0.8,
            "flat_difference": 0.0,
            "truncation_intended_difference": 0.0,
        },
    }


class ArmRun:
    """Stepwise wrapper around StructuralRQArm that emits raw records per generation."""

    def __init__(self, arm_label: str, seed: int) -> None:
        self.arm_label = arm_label
        self.seed = int(seed)
        self.arm = StructuralRQArm.boot_structural(arm=ARM_LABELS[arm_label], seed=seed)
        self.arm.collect_realised_host_pressure = True
        self.rng = RNGManager(seed=self.seed, namespace=f"hp-struct-rq-{self.arm.arm}")
        self.known_ids = set(self.arm.roles)
        self.run_id = f"rq3-{arm_label}-s{self.seed}-{int(time.time())}"
        self.events: list[dict[str, object]] = []
        self.population: list[dict[str, object]] = []
        self.summaries: list[dict[str, object]] = []
        self.contact_events: list[dict[str, object]] = []
        self.ancestry: list[dict[str, object]] = []
        self.wall_by_generation: list[float] = []

    def _diff_births(self, result, generation: int) -> list[tuple[str, str]]:
        lineage = {rec.organism_id: rec for rec in result.population.lineage}
        born: list[tuple[str, str]] = []
        for org in result.population.organisms:
            if org.id in self.known_ids:
                continue
            rec = lineage.get(org.id)
            parent = getattr(rec, "parent_id", None) if rec is not None else None
            born.append((parent or "ROOT", org.id))
        return born

    def step(self, generation: int) -> None:
        t0 = time.perf_counter()
        self.arm._apply_passage_refill()
        before_ids = {org.id for org in self.arm.runner.population.organisms}
        result = self.arm.runner.step_generation(
            seed=self.seed + self.arm.tick_index + 1
        )
        born = self._diff_births(result, generation)
        self.arm._record_births(result)
        after_ids = {org.id for org in self.arm.runner.population.organisms}
        dead = sorted(before_ids - after_ids)
        debit_count, matched = self.arm._apply_hp_env_contact()

        # Contact evidence for this generation, keyed by host class.
        evidenced: dict[str, dict[str, object]] = {}
        if self.arm.host_realised_pressure_series:
            aff = dict(
                (cls, (s, c))
                for cls, s, c in self.arm.host_contact_affinity_series[-1]
            )
            avail = dict((cls, a) for cls, a in self.arm.host_contact_available_series[-1])
            realised = dict(
                (cls, (v, c)) for cls, v, c in self.arm.host_realised_pressure_series[-1]
            )
            for cls in sorted(set(aff) | set(realised)):
                aff_sum, contacts = aff.get(cls, (0.0, 0))
                available = avail.get(cls, None)
                value, _ = realised.get(cls, (None, contacts))
                intended = 1.2 * float(aff_sum) / contacts if contacts else None
                evidenced[cls] = {
                    "opportunity": int(contacts),
                    "affinity_sum": round(float(aff_sum), 9),
                    "intended_pi": None if intended is None else round(intended, 9),
                    "realised_pi": None if value is None else round(float(value), 9),
                    "min_available_atp": available,
                    "class_count": None,
                }

        self.arm._passage_update(
            matched, rng=self.rng.fork(f"passage/{self.arm.tick_index}")
        )
        self.arm._census()
        self.arm.tick_index += 1

        host_counts = Counter(
            joint_match_class(organism_window(org)) for org in self.arm._hosts()
        )
        para_counts = Counter(self.arm.parasite_windows)
        host_total = sum(host_counts.values()) or 1
        para_total = sum(para_counts.values()) or 1

        for cls, payload in evidenced.items():
            payload["class_count"] = int(host_counts.get(cls, 0))
            self.contact_events.append(
                {
                    "run_id": self.run_id,
                    "seed": self.seed,
                    "arm": self.arm_label,
                    "generation": generation,
                    "event_id": f"contact-{self.arm_label}-{self.seed}-{generation}-{cls}",
                    "host_class": cls,
                    "opportunity": payload["opportunity"],
                    "matched": payload["opportunity"] > 0,
                    "intended_debit": payload["intended_pi"],
                    "realised_debit": payload["realised_pi"],
                    "min_available_atp": payload["min_available_atp"],
                }
            )

        for parent, child in born:
            self.ancestry.append(
                {
                    "run_id": self.run_id,
                    "seed": self.seed,
                    "arm": self.arm_label,
                    "generation": generation,
                    "event_id": f"birth-{self.arm_label}-{self.seed}-{generation}-{child}",
                    "organism_id": child,
                    "parent_id": parent,
                    "side": "host",
                    "event": "birth",
                    "genotype_digest": None,
                    "antagonist_digest": None,
                    "mutation": None,
                    "intervention_id": None,
                }
            )
        for organism_id in dead:
            self.ancestry.append(
                {
                    "run_id": self.run_id,
                    "seed": self.seed,
                    "arm": self.arm_label,
                    "generation": generation,
                    "event_id": f"death-{self.arm_label}-{self.seed}-{generation}-{organism_id}",
                    "organism_id": organism_id,
                    "parent_id": None,
                    "side": "host",
                    "event": "death",
                    "genotype_digest": None,
                    "antagonist_digest": None,
                    "mutation": None,
                    "intervention_id": None,
                }
            )

        for cls, count in sorted(host_counts.items()):
            self.events.append(
                {
                    "run_id": self.run_id,
                    "seed": self.seed,
                    "arm": self.arm_label,
                    "generation": generation,
                    "event_id": f"hostclass-{self.arm_label}-{self.seed}-{generation}-{cls}",
                    "organism_id": None,
                    "parent_id": None,
                    "genotype_digest": cls,
                    "antagonist_digest": None,
                    "contact_edge_id": None,
                    "opportunity": evidenced.get(cls, {}).get("opportunity"),
                    "matched": None,
                    "intended_debit": evidenced.get(cls, {}).get("intended_pi"),
                    "realised_debit": evidenced.get(cls, {}).get("realised_pi"),
                    "atp_before": None,
                    "atp_after": None,
                    "birth": None,
                    "death": None,
                    "mutation": None,
                    "intervention_id": None,
                    "host_class_frequency": count / host_total,
                    "antagonist_class_frequency": None,
                }
            )

        self.population.append(
            {
                "run_id": self.run_id,
                "seed": self.seed,
                "arm": self.arm_label,
                "generation": generation,
                "census": len(self.arm._hosts()),
                "host_class_counts": dict(host_counts),
                "host_class_frequencies": {
                    k: v / host_total for k, v in sorted(host_counts.items())
                },
                "antagonist_class_counts": dict(para_counts),
                "antagonist_class_frequencies": {
                    k: v / para_total for k, v in sorted(para_counts.items())
                },
                "antagonist_n": len(self.arm.parasite_windows),
                "contacts": int(debit_count),
                "opportunities": int(sum(p["opportunity"] for p in evidenced.values())),
                "pressure_realised": {
                    k: p["realised_pi"] for k, p in sorted(evidenced.items())
                },
                "pressure_intended": {
                    k: p["intended_pi"] for k, p in sorted(evidenced.items())
                },
                "births": len(born),
                "deaths": len(dead),
                "mutation_events_host": None,
                "mutation_events_antagonist": int(self.arm.turnover_mut_events[-1]),
                "antagonist_kept": int(self.arm.turnover_kept[-1]),
                "antagonist_replaced": int(self.arm.turnover_replaced[-1]),
            }
        )

        if generation % 10 == 0 or generation == 1:
            self.summaries.append(
                {
                    "generation": generation,
                    "census": len(self.arm._hosts()),
                    "host_classes": len(host_counts),
                    "antagonist_classes": len(para_counts),
                    "contacts": int(debit_count),
                    "wall_s": round(time.perf_counter() - t0, 4),
                }
            )
        self.wall_by_generation.append(time.perf_counter() - t0)

    def result(self) -> dict[str, object]:
        return {
            "run_id": self.run_id,
            "arm": self.arm_label,
            "seed": self.seed,
            "generations": len(self.population),
            "events": self.events,
            "contact_events": self.contact_events,
            "ancestry": self.ancestry,
            "population": self.population,
            "summaries": self.summaries,
            "wall_total_s": round(sum(self.wall_by_generation), 4),
            "wall_per_generation_s": [
                round(v, 6) for v in self.wall_by_generation
            ],
            "final_census": self.population[-1]["census"] if self.population else 0,
        }


def write_run(run: ArmRun, payload: dict[str, object], stop_code: str) -> str:
    run_dir = RUNS / run.run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    def dump_jsonl(name: str, rows: list[dict[str, object]]) -> str:
        path = run_dir / name
        with path.open("w", encoding="utf-8", newline="\n") as handle:
            for row in rows:
                handle.write(json.dumps(row, sort_keys=True, default=str) + "\n")
                handle.flush()
        data = path.read_bytes()
        return hashlib.sha256(data).hexdigest()

    checksums = {
        "events.jsonl": dump_jsonl("events.jsonl", run.events),
        "population.jsonl": dump_jsonl("population.jsonl", run.population),
        "contact_events.jsonl": dump_jsonl("contact_events.jsonl", run.contact_events),
        "ancestry.jsonl": dump_jsonl("ancestry.jsonl", run.ancestry),
    }
    summary_path = run_dir / "summary.json"
    summary_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, default=str), encoding="utf-8"
    )
    checksums["summary.json"] = hashlib.sha256(summary_path.read_bytes()).hexdigest()

    manifest = {
        "schema_version": SCHEMA_VERSION,
        "round": ROUND,
        "run_id": run.run_id,
        "arm": run.arm_label,
        "seed": run.seed,
        "generations": len(run.population),
        "stop_code": stop_code,
        "repo": git_probe(),
        "python": sys.version,
        "platform": platform.platform(),
        "pid": os.getpid(),
        "rng_streams": {
            "engine_seed_expression": "seed + tick_index + 1",
            "passage_namespace": f"hp-struct-rq-{ARM_LABELS[run.arm_label]}",
            "passage_fork": "passage/{tick_index}",
            "namespace_note": (
                "each external RNGManager is constructed with (seed, namespace); "
                "arms share the seed and differ by namespace/arm"
            ),
        },
        "parameters": {
            "antagonist_keep_fraction": run.arm.parasite_keep_fraction,
            "antagonist_mutation": run.arm.parasite_mutation,
            "host_bit_flip_rate": run.arm.host_bit_flip_rate,
            "virulence": run.arm.virulence,
            "steal_fraction": run.arm.hp_env.steal_fraction,
            "soft_carrying_capacity": run.arm.soft_carrying_capacity,
            "resource_bolus_amount": run.arm.resource_bolus_amount,
            "founders": len(run.arm.runner.population.organisms),
            "antagonist_pool_size": len(run.arm.parasite_windows),
        },
        "memory_rss_mb": mem_rss_mb(),
        "wall_s": run.result()["wall_total_s"],
        "parent_snapshot": None,
        "checksums": checksums,
        "replay_command": (
            f"python rq3_harness.py --stage replay --run-dir runs/{run.run_id}"
        ),
    }
    (run_dir / "run_manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True, default=str), encoding="utf-8"
    )
    return run.run_id


def stage_replay(run_dir: Path) -> dict[str, object]:
    """Recompute the summary from raw only and compare checksums."""

    manifest = json.loads((run_dir / "run_manifest.json").read_text(encoding="utf-8"))
    problems: list[str] = []
    for name, expected in manifest["checksums"].items():
        actual = hashlib.sha256((run_dir / name).read_bytes()).hexdigest()
        if actual != expected:
            problems.append(f"{name}: checksum mismatch")
    population = [
        json.loads(line)
        for line in (run_dir / "population.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    derived = {
        "generations": len(population),
        "final_census": population[-1]["census"] if population else 0,
        "total_contacts": sum(int(row["contacts"]) for row in population),
        "final_antagonist_classes": len(population[-1]["antagonist_class_counts"])
        if population
        else 0,
    }
    stored = json.loads((run_dir / "summary.json").read_text(encoding="utf-8"))
    for key, value in derived.items():
        if stored.get(key) != value:
            problems.append(f"{key}: stored={stored.get(key)} derived={value}")
    return {"derived": derived, "problems": problems, "reproduced": not problems}


def stage_time(seed: int, gens: int) -> dict[str, object]:
    payloads = {}
    for label in ARMS:
        run = ArmRun(label, seed)
        t0 = time.perf_counter()
        for generation in range(1, gens + 1):
            run.step(generation)
        wall = time.perf_counter() - t0
        payloads[label] = {
            "wall_s": round(wall, 3),
            "wall_per_generation_s": round(wall / max(1, gens), 4),
            "final_census": run.population[-1]["census"] if run.population else 0,
            "contacts": run.population[-1]["contacts"] if run.population else 0,
            "rss_mb": mem_rss_mb(),
        }
    return payloads


def stage_arm(seed: int, gens: int, arm: str) -> dict[str, object]:
    stop_code = "COMPLETE"
    run = ArmRun(arm, seed)
    # The repository's own guard remaps duplicate digest-based ids; the arms call it
    # inside run_generations, and this stepwise harness must do the same or the
    # PopulationState uniqueness invariant fires on some seeds.
    with _population_unique_id_guard():
        for generation in range(1, gens + 1):
            run.step(generation)
            if mem_rss_mb() is not None and mem_rss_mb() > 3500:
                stop_code = "STOP_MEMORY_SOFT_LIMIT"
                break
            if not run.population[-1]["host_class_counts"]:
                stop_code = "STOP_ZERO_FREQUENCY"
                break
    payload = run.result()
    write_run(run, payload, stop_code)
    return {"run_id": run.run_id, "stop_code": stop_code, "generations": payload["generations"]}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", required=True, choices=["hand", "time", "arm", "replay"])
    parser.add_argument("--seed", type=int, default=21001)
    parser.add_argument("--gens", type=int, default=1)
    parser.add_argument("--arm", default="coevolve", choices=list(ARMS))
    parser.add_argument("--run-dir", default=None)
    args = parser.parse_args()

    if args.stage == "hand":
        out = stage_hand()
    elif args.stage == "time":
        out = stage_time(args.seed, args.gens)
    elif args.stage == "arm":
        out = stage_arm(args.seed, args.gens, args.arm)
    else:
        out = stage_replay(Path(args.run_dir))
    print(json.dumps(out, indent=2, sort_keys=True, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
