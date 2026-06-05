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
import hashlib
import json
from pathlib import Path
from typing import Any

from codontrace.genesis.engine import GenesisEngine
from codontrace.genesis.runtime_profiles import GenesisRuntimeProfile


def _write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, sort_keys=True, indent=2, allow_nan=False), encoding="utf-8")


def _digest(payload: Any) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")).hexdigest()


def run(output_dir: str | Path = "genesis_capsule_utility_pilot_out") -> dict[str, str]:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    spec = GenesisRuntimeProfile.capsule_utility_pilot_world()
    engine = GenesisEngine.from_spec(spec)
    result = engine.run_ticks()
    records = [r.to_dict() for r in result.capsule_utility_records]
    positive = [
        r
        for r in records
        if r.get("adoption_success") is True
        and r.get("state_changed") is True
        and float(r.get("utility_delta") or 0.0) > 0.0
        and r.get("utility_protocol_digest")
        and r.get("source_fitness_status") in {"measured", "last_known"}
    ]
    claim_allowed = bool(positive)
    reason = "positive_behavioral_utility_observed" if claim_allowed else "no_positive_behavioral_utility"
    summary = {
        "schema_version": "capsule_utility_pilot_summary_v1",
        "pilot_status": "capsule_positive_utility_observed" if claim_allowed else "capsule_records_emitted_claim_denied",
        "record_count": len(records),
        "positive_utility_records": len(positive),
        "claim_allowed_for_capsule_usefulness": claim_allowed,
        "claim_gate_reason": reason,
        "utility_delta_max": max([float(r.get("utility_delta") or 0.0) for r in records], default=0.0),
        "manifest_digest": result.manifest.digest(),
    }
    manifest = {
        "schema_version": "pilot_manifest_v1",
        "producer_version": RELEASE_LABEL,
        "library_version": getattr(result.manifest, "library_version", "unknown"),
        "pilot_name": "genesis_capsule_utility_pilot",
        "pilot_status": summary["pilot_status"],
        "seed": 1,
        "config_digest": spec.digest(),
        "protocol_digest": _digest({"pilot": "capsule", "protocol": "paired_micro_eval", "requires": "behavior_digest_change_and_positive_delta"}),
        "artifact_digest": _digest({"summary": summary, "records": records}),
        "feature_status": "claim_eligible_limited" if claim_allowed else "claim_denied_pending_evidence",
        "claim_gate": {"capsule_usefulness": claim_allowed, "reason": reason},
        "output_files": ["capsule_utility_summary.json", "capsule_utility_records.jsonl", "capsule_utility_manifest.json"],
    }
    summary_path = out / "capsule_utility_summary.json"
    records_path = out / "capsule_utility_records.jsonl"
    manifest_path = out / "capsule_utility_manifest.json"
    _write_json(summary_path, summary)
    records_path.write_text("".join(json.dumps(r, sort_keys=True, allow_nan=False) + "\n" for r in records), encoding="utf-8")
    _write_json(manifest_path, manifest)
    _write_json(out / "capsule_utility.json", {"summary": summary, "records": records, "manifest": manifest, "claim_allowed_for_capsule_usefulness": claim_allowed, "status": ("claim_eligible_measured_utility" if claim_allowed else "records_emitted_not_usefulness_claim"), "record_count": len(records)})
    return {"json": str(out / "capsule_utility.json"), "summary": str(summary_path), "records": str(records_path), "manifest": str(manifest_path), "manifest_digest": result.manifest.digest()}


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Run genesis capsule utility pilot and export JSON artifacts.")
    parser.add_argument("--output-dir", default="genesis_capsule_utility_pilot_out")
    args = parser.parse_args()
    print(json.dumps(run(args.output_dir), indent=2, sort_keys=True, allow_nan=False))


if __name__ == "__main__":
    main()
