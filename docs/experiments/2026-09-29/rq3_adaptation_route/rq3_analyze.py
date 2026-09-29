"""RQ-3 analyzer: derives every reported number from the raw JSONL of a run.

Usage:
  python rq3_analyze.py runs/<run_id> [runs/<run_id> ...] [--out analysis.json]
  python rq3_analyze.py --compare runs/a runs/b ...
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BOOTSTRAP_SEED = 20260928
BOOTSTRAP_RESAMPLES = 10000


def load_jsonl(path: Path) -> list[dict]:
    if not path.is_file():
        return []
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def pressure_series(population: list[dict]) -> dict[str, list[float]]:
    out: dict[str, list[float]] = {}
    for row in population:
        for cls, value in (row.get("pressure_realised") or {}).items():
            if value is None:
                continue
            out.setdefault(cls, []).append(float(value))
    return out


def rareness_effect(population: list[dict], warmup: int = 5) -> dict[str, object]:
    """Run-level rare-ness effect on growth.

    For each generation boundary g in the window, the class with the below-median
    frequency is the rare class and the above-median class is the common class; the
    effect is the difference in the class' next-boundary growth, averaged over
    boundaries. Units: log count per generation.
    """

    deltas: list[float] = []
    for i in range(warmup, len(population) - 1):
        now = population[i]["host_class_frequencies"]
        nxt = population[i + 1]["host_class_counts"]
        prev = population[i]["host_class_counts"]
        if len(now) < 2:
            continue
        ordered = sorted(now.items(), key=lambda kv: kv[1])
        rare = ordered[0][0]
        common = ordered[-1][0]
        if rare == common:
            continue
        rare_growth = math.log(max(1, nxt.get(rare, 0)) / max(1, prev.get(rare, 0)))
        common_growth = math.log(max(1, nxt.get(common, 0)) / max(1, prev.get(common, 0)))
        deltas.append(rare_growth - common_growth)
    if not deltas:
        return {"n_generations": 0, "mean": None, "values": []}
    return {
        "n_generations": len(deltas),
        "mean": sum(deltas) / len(deltas),
        "values": deltas,
    }


def delayed_pressure_link(
    population: list[dict], lag: int = 4
) -> dict[str, object]:
    """Cross-lag covariance: frequency of the class common at g vs pressure on it at g+lag."""

    pairs: list[tuple[float, float]] = []
    for i in range(len(population) - lag):
        now = population[i]["host_class_frequencies"]
        later = population[i + lag]["pressure_realised"]
        for cls, freq in now.items():
            if cls in later and later[cls] is not None:
                pairs.append((float(freq), float(later[cls])))
    if len(pairs) < 3:
        return {"n_pairs": len(pairs), "cov": None}
    xs = [p[0] for p in pairs]
    ys = [p[1] for p in pairs]
    mx = sum(xs) / len(xs)
    my = sum(ys) / len(ys)
    cov = sum((x - mx) * (y - my) for x, y in pairs) / len(pairs)
    vx = sum((x - mx) ** 2 for x in xs) / len(xs)
    vy = sum((y - my) ** 2 for y in ys) / len(ys)
    corr = cov / math.sqrt(vx * vy) if vx > 0 and vy > 0 else None
    return {"n_pairs": len(pairs), "cov": cov, "corr": corr}


def swap_signal(population: list[dict], lag: int = 4) -> dict[str, object]:
    """Delayed-link cut statistic: swap-signal from recorded realised pressure only.

    S = pi_A(swap) - pi_A(unswapped) is not directly observed in these runs, because
    no paired counterfactual arm exists yet. What is computed here is the observed
    quantity the counterfactual would be compared against: the pressure contrast
    between the class that was common `lag` generations earlier and the class that
    was rare, at the same generation.
    """

    contrasts: list[float] = []
    for i in range(lag, len(population)):
        history = population[i - lag]["host_class_frequencies"]
        now = population[i]["pressure_realised"]
        if len(history) < 2:
            continue
        ordered = sorted(history.items(), key=lambda kv: kv[1])
        rare = ordered[0][0]
        common = ordered[-1][0]
        if common == rare:
            continue
        pc = now.get(common)
        pr = now.get(rare)
        if pc is None or pr is None:
            continue
        contrasts.append(float(pc) - float(pr))
    if not contrasts:
        return {"n_generations": 0, "mean": None}
    return {
        "n_generations": len(contrasts),
        "mean": sum(contrasts) / len(contrasts),
        "values": contrasts,
    }


def cluster_bootstrap(values: list[float]) -> dict[str, object]:
    if len(values) < 2:
        return {"n": len(values), "mean": None, "lo": None, "hi": None}
    rng = random.Random(BOOTSTRAP_SEED)
    n = len(values)
    means = []
    for _ in range(BOOTSTRAP_RESAMPLES):
        sample = [values[rng.randrange(n)] for _ in range(n)]
        means.append(sum(sample) / n)
    means.sort()
    return {
        "n": n,
        "mean": sum(values) / n,
        "lo": means[int(0.025 * BOOTSTRAP_RESAMPLES)],
        "hi": means[int(0.975 * BOOTSTRAP_RESAMPLES)],
        "resamples": BOOTSTRAP_RESAMPLES,
        "bootstrap_seed": BOOTSTRAP_SEED,
    }


def analyze_run(run_dir: Path) -> dict[str, object]:
    manifest_path = run_dir / "run_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    population = load_jsonl(run_dir / "population.jsonl")
    events = load_jsonl(run_dir / "events.jsonl")
    contacts = load_jsonl(run_dir / "contact_events.jsonl")
    ancestry = load_jsonl(run_dir / "ancestry.jsonl")

    checksum_ok = {}
    for name, expected in manifest["checksums"].items():
        checksum_ok[name] = (
            hashlib.sha256((run_dir / name).read_bytes()).hexdigest() == expected
        )

    host_births = sum(1 for row in ancestry if row["event"] == "birth")
    host_deaths = sum(1 for row in ancestry if row["event"] == "death")
    antagonist_ancestry_rows = sum(1 for row in ancestry if row["side"] == "antagonist")
    mutations_logged = sum(
        1
        for row in ancestry
        if row.get("mutation") not in (None, 0, False)
    )
    antagonist_mut_events = sum(
        int(row.get("mutation_events_antagonist") or 0) for row in population
    )
    antagonist_replaced = sum(
        int(row.get("antagonist_replaced") or 0) for row in population
    )
    antagonist_kept = sum(int(row.get("antagonist_kept") or 0) for row in population)

    host_class_change = 0
    for i in range(1, len(population)):
        prev = population[i - 1]["host_class_frequencies"]
        now = population[i]["host_class_frequencies"]
        if prev and now and max(prev, key=prev.get) != max(now, key=now.get):
            host_class_change += 1

    antagonist_change = 0
    for i in range(1, len(population)):
        if (
            population[i - 1]["antagonist_class_frequencies"]
            != population[i]["antagonist_class_frequencies"]
        ):
            antagonist_change += 1

    rareness = rareness_effect(population)
    link = delayed_pressure_link(population)
    swap = swap_signal(population)

    return {
        "run_id": manifest["run_id"],
        "arm": manifest["arm"],
        "seed": manifest["seed"],
        "generations": manifest["generations"],
        "stop_code": manifest["stop_code"],
        "checksums_ok": checksum_ok,
        "census_first": population[0]["census"] if population else None,
        "census_last": population[-1]["census"] if population else None,
        "census_min": min((row["census"] for row in population), default=None),
        "host_classes_first": len(population[0]["host_class_frequencies"])
        if population
        else None,
        "host_classes_last": len(population[-1]["host_class_frequencies"])
        if population
        else None,
        "host_dominance_changes": host_class_change,
        "antagonist_classes_last": len(population[-1]["antagonist_class_counts"])
        if population
        else None,
        "antagonist_composition_changes": antagonist_change,
        "antagonist_pool_size_last": population[-1]["antagonist_n"] if population else None,
        "contacts_total": sum(int(row["contacts"]) for row in population),
        "opportunities_total": sum(int(row["opportunities"] or 0) for row in population),
        "host_birth_events": host_births,
        "host_death_events": host_deaths,
        "host_mutation_events_logged": mutations_logged,
        "antagonist_ancestry_rows": antagonist_ancestry_rows,
        "antagonist_replacement_events": antagonist_replaced,
        "antagonist_kept_events": antagonist_kept,
        "antagonist_mutation_events_per_gen": (
            antagonist_mut_events / len(population) if population else None
        ),
        "rareness_effect": {
            "mean": rareness["mean"],
            "n_generations": rareness["n_generations"],
        },
        "rareness_interval": cluster_bootstrap(rareness["values"]),
        "delayed_pressure_link": link,
        "delayed_pressure_contrast": {
            "mean": swap["mean"],
            "n_generations": swap["n_generations"],
        },
        "delayed_contrast_interval": cluster_bootstrap(swap.get("values") or []),
        "contact_event_rows": len(contacts),
        "event_rows": len(events),
        "raw_rows": {
            "population": len(population),
            "events": len(events),
            "contact_events": len(contacts),
            "ancestry": len(ancestry),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("run_dirs", nargs="+")
    parser.add_argument("--out", default=None)
    args = parser.parse_args()

    results = [analyze_run(Path(p)) for p in args.run_dirs]
    out = {"analysis_version": "rq3-analysis-v1", "runs": results}
    text = json.dumps(out, indent=2, sort_keys=True, default=str)
    if args.out:
        Path(args.out).write_text(text, encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
