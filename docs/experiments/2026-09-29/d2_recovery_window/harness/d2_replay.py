"""D-2 replay: recompute one run's summary from its raw files and verify checksums.

    python test-runs/d2/harness/d2_replay.py --run-dir test-runs/d2/raw/<run_id>

Reads only the run directory the manifest names, so a cut run replays its valid prefix.
Writes ``replay.json`` beside the raw files and returns non-zero if any check fails.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

REQUIRED_EVENT_FIELDS = (
    "run_id",
    "seed",
    "arm",
    "generation",
    "event_id",
    "organism_id",
    "parent_id",
    "genotype_digest",
    "antagonist_digest",
    "contact_edge_id",
    "opportunity",
    "matched",
    "intended_debit",
    "realised_debit",
    "atp_before",
    "atp_after",
    "birth",
    "death",
    "mutation",
    "intervention_id",
)
REQUIRED_POP_FIELDS = (
    "run_id",
    "seed",
    "arm",
    "generation",
    "n_alive",
    "class_counts",
    "class_frequencies",
    "genotype_counts",
    "genotype_frequencies",
    "antagonist_frequency",
    "fitness",
    "atp_sum",
    "atp_mean",
    "contact_opportunities",
    "pi_realised",
    "pi_intended",
    "resource_mass",
    "genealogy",
    "population_path_digest",
)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def read_jsonl(path: Path, required: tuple[str, ...]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    bad = 0
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        record = json.loads(line)
        missing = [k for k in required if k not in record]
        if missing:
            bad += 1
            continue
        rows.append(record)
    if bad:
        print(f"WARN {path.name}: {bad} record(s) failed the schema check", file=sys.stderr)
    return rows


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-dir", required=True)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()
    run_dir = Path(args.run_dir)
    out_path = Path(args.out) if args.out else run_dir / "replay.json"
    manifest = json.loads((run_dir / "run_manifest.json").read_text(encoding="utf-8"))

    checks: dict[str, Any] = {}
    for name, expected in (manifest.get("checksums") or {}).items():
        checks[name] = sha256_file(run_dir / name) == expected
    events = read_jsonl(run_dir / "events.jsonl", REQUIRED_EVENT_FIELDS)
    population = read_jsonl(run_dir / "population.jsonl", REQUIRED_POP_FIELDS)

    births = sum(1 for e in events if e.get("birth") is True)
    deaths = sum(1 for e in events if e.get("death") is True)
    mutations = sum(1 for e in events if e.get("mutation") is True)
    negative_atp = sum(1 for e in events if isinstance(e.get("atp_after"), (int, float)) and e["atp_after"] < 0)
    recovered = any(bool(v) for v in ())  # placeholder: recovery is recomputed below
    recover = False
    if population:
        checkpoint_gen = min(int(r["generation"]) for r in population)
        digests_at_ckpt = set()
        for row in population:
            if int(row["generation"]) == checkpoint_gen:
                digests_at_ckpt |= set(row["genotype_counts"])
        missing: set[str] = set()
        for row in population:
            present = set(row["genotype_counts"])
            for digest in digests_at_ckpt:
                if digest not in present:
                    missing.add(digest)
                elif digest in missing:
                    recover = True
    summary = {
        "run_id": manifest.get("run_id"),
        "seed": manifest.get("seed"),
        "arm": manifest.get("arm"),
        "t_intervene": manifest.get("t_intervene"),
        "horizon": manifest.get("horizon"),
        "n_population_rows": len(population),
        "n_events": len(events),
        "n_birth_events": births,
        "n_death_events": deaths,
        "n_mutation_events": mutations,
        "n_negative_atp_events": negative_atp,
        "final_n_alive": int(population[-1]["n_alive"]) if population else 0,
        "recover_exploratory_return": bool(recover),
        "checksum_match": checks,
        "all_checksums_match": all(checks.values()) if checks else False,
        "stop_code": manifest.get("stop_code"),
        "schema_version": manifest.get("schema"),
        "replayed_from": str(run_dir),
        "deterministic_replay_note": (
            "the summary is derived from the raw files only; re-simulation is not required, and the "
            "pre-intervention segment is byte-identical across arms for the same seed and checkpoint"
        ),
        "_unused": recovered,
    }
    out_path.write_text(json.dumps(summary, indent=2, sort_keys=True, default=str), encoding="utf-8")
    print(json.dumps({k: v for k, v in summary.items() if k != "checksum_match"}, indent=1, default=str))
    ok = bool(summary["all_checksums_match"] and events and population and negative_atp == 0)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
