"""Small GENESIS evolution pilot.

This example is deliberately descriptive: it builds a real resource/birth/QD pilot
and exports audit columns, but it does not claim artificial life or open-endedness.
"""

from __future__ import annotations

try:
    from ._path_bootstrap import ensure_src_path
except ImportError:  # direct script or runpy execution outside the examples package
    import sys as _sys
    from pathlib import Path as _Path

    _EXAMPLES_DIR = _Path(__file__).resolve().parent
    if str(_EXAMPLES_DIR) not in _sys.path:
        _sys.path.insert(0, str(_EXAMPLES_DIR))
    from _path_bootstrap import ensure_src_path

ensure_src_path()

from codontrace.genesis import RELEASE_LABEL
import csv
import hashlib
import json
from pathlib import Path

from codontrace.genesis.engine import GenesisEngine
from codontrace.genesis.runtime_profiles import GenesisRuntimeProfile



def _digest(payload: object) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")).hexdigest()


REQUIRED_COLUMNS = (
    "generation",
    "population",
    "births",
    "deaths",
    "best_raw_fitness",
    "best_selection_fitness",
    "mean_raw_fitness",
    "mean_selection_fitness",
    "viability_gate_failures",
    "lumen_eaten",
    "resource_pressure",
    "blocked_actions",
    "reproduction_attempts",
    "reproduction_successes",
    "qd_changed_selection",
    "capsule_utility_mean",
    "top_action_histogram",
    "top_genome_digest",
)


def run(output_dir: str | Path = "genesis_evolution_pilot_out", *, seed: int = 1, tick_count: int = 50) -> dict[str, str]:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    result = GenesisEngine.from_spec(GenesisRuntimeProfile.evolution_pilot_world(seed=seed, tick_count=tick_count)).run_ticks()
    rows = []
    for tick in result.ticks:
        gen = tick.generation_result
        action_counts: dict[str, int] = {}
        lumen = 0.0
        blocked = 0
        for trace in gen.traces:
            for event in trace.events:
                action_counts[event.action] = action_counts.get(event.action, 0) + 1
                if isinstance(event.world_delta.get("lumen_consumed"), (int, float)):
                    lumen += float(event.world_delta["lumen_consumed"])
                if event.status == "blocked":
                    blocked += 1
        capsule_utils = [item.utility_delta for item in result.capsule_utility_records if item.utility_delta is not None]
        rows.append({
            "generation": gen.population.generation,
            "population": gen.after_count,
            "births": gen.births,
            "deaths": gen.deaths,
            "best_raw_fitness": gen.raw_best_fitness,
            "best_selection_fitness": gen.selection_best_fitness,
            "mean_raw_fitness": gen.raw_mean_fitness,
            "mean_selection_fitness": gen.selection_mean_fitness,
            "viability_gate_failures": gen.viability_gate_failures,
            "lumen_eaten": round(lumen, 10),
            "resource_pressure": sum(1 for item in gen.resource_policy_records if item.event_type in {"resource_pressure", "resource_regenerated"}),
            "blocked_actions": blocked,
            "reproduction_attempts": gen.reproduction_attempts,
            "reproduction_successes": gen.births,
            "qd_changed_selection": bool(gen.selection_result and gen.selection_result.qd_changed_selection),
            "capsule_utility_mean": round(sum(capsule_utils) / len(capsule_utils), 10) if capsule_utils else 0.0,
            "top_action_histogram": json.dumps(dict(sorted(action_counts.items())), sort_keys=True),
            "top_genome_digest": gen.population.organisms[0].genome.digest() if gen.population.organisms else "",
        })
    csv_path = out / "genesis_evolution_pilot.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=REQUIRED_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    total_births = sum(int(row["reproduction_successes"]) for row in rows)
    any_qd_changed = any(bool(row["qd_changed_selection"]) for row in rows)
    pilot_status = (
        "runtime_effective_evolution_pilot"
        if total_births > 0
        else "no_successful_births_not_evolution_evidence"
    )
    qd_status = "selection_applied" if any_qd_changed else "qd_selection_not_demonstrated"
    summary = {
        "pilot_status": pilot_status,
        "total_births": total_births,
        "any_qd_changed_selection": any_qd_changed,
        "qd_status": qd_status,
    }
    payload = {"rows": rows, "summary": summary, "manifest": result.manifest.to_dict()}
    json_path = out / "genesis_evolution_pilot.json"
    manifest = {
        "schema_version": "pilot_manifest_v1",
        "producer_version": RELEASE_LABEL,
        "library_version": getattr(result.manifest, "library_version", "0.3.0a1"),
        "pilot_name": "genesis_evolution_pilot",
        "pilot_status": pilot_status,
        "seed": seed,
        "config_digest": GenesisRuntimeProfile.evolution_pilot_world(seed=seed, tick_count=tick_count).digest(),
        "protocol_digest": _digest({"pilot": "evolution", "requires": "births_resource_selection_records", "tick_count": tick_count}),
        "artifact_digest": _digest(payload),
        "feature_status": "claim_eligible_limited" if total_births > 0 else "claim_denied_pending_evidence",
        "claim_gate": {"evolution_pilot": total_births > 0, "reason": pilot_status},
        "output_files": ["genesis_evolution_pilot.csv", "genesis_evolution_pilot.json", "genesis_evolution_pilot_manifest.json"],
    }
    manifest_path = out / "genesis_evolution_pilot_manifest.json"
    json_path.write_text(json.dumps(payload, sort_keys=True, indent=2, allow_nan=False), encoding="utf-8")
    manifest_path.write_text(json.dumps(manifest, sort_keys=True, indent=2, allow_nan=False), encoding="utf-8")
    return {"csv": str(csv_path), "json": str(json_path), "manifest": str(manifest_path), "manifest_digest": result.manifest.digest()}


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Run the GENESIS evolution pilot and export CSV/JSON artifacts.")
    parser.add_argument("--output-dir", default="genesis_evolution_pilot_out")
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument("--tick-count", type=int, default=50)
    args = parser.parse_args()
    print(json.dumps(run(args.output_dir, seed=args.seed, tick_count=args.tick_count), indent=2, sort_keys=True, allow_nan=False))


if __name__ == "__main__":
    main()
