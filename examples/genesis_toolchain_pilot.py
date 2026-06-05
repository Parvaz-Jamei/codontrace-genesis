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


def run(output_dir: str | Path = "genesis_toolchain_pilot_out") -> dict[str, str]:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    spec = GenesisRuntimeProfile.toolchain_pilot_world()
    engine = GenesisEngine.from_spec(spec)
    result = engine.run_ticks()
    records = [r.to_dict() if hasattr(r, "to_dict") else dict(r) for r in result.tool_chain_records]
    successful = [r for r in records if r.get("allowed") is True and r.get("status") == "executed"]
    blocked = [r for r in records if r.get("allowed") is not True]
    reward_total = round(sum(float(r.get("reward_delta") or 0.0) for r in records), 10)
    state_or_inventory = [
        r
        for r in successful
        if r.get("world_state_before_digest") != r.get("world_state_after_digest")
        or r.get("inventory_before") != r.get("inventory_after")
        or float(r.get("reward_delta") or 0.0) != 0.0
    ]
    successful_chain_actions = [str(r.get("action")) for r in successful]
    has_collection = "COLLECT_RESOURCE" in successful_chain_actions
    has_state_change = bool(state_or_inventory)
    has_reward = reward_total > 0.0
    chain_success = bool(has_collection and has_state_change and has_reward and len(successful) >= 3)
    claim_allowed = chain_success
    claim_reason = "toolchain_success_path_observed" if claim_allowed else "no_successful_toolchain_path"
    summary = {
        "schema_version": "toolchain_pilot_summary_v1",
        "pilot_status": "runtime_effective_toolchain_pilot" if chain_success else "toolchain_pilot_no_success_path",
        "chain_success": chain_success,
        "total_tool_actions": len(records),
        "successful_tool_actions": len(successful),
        "blocked_tool_actions": len(blocked),
        "tool_reward_total": reward_total,
        "successful_chain_actions": successful_chain_actions,
        "claim_allowed_for_tool_use": claim_allowed,
        "claim_gate_reason": claim_reason,
        "manifest_digest": result.manifest.digest(),
    }
    manifest = {
        "schema_version": "pilot_manifest_v1",
        "producer_version": RELEASE_LABEL,
        "library_version": getattr(result.manifest, "library_version", "unknown"),
        "pilot_name": "genesis_toolchain_pilot",
        "pilot_status": summary["pilot_status"],
        "seed": 1,
        "config_digest": spec.digest(),
        "protocol_digest": _digest({"pilot": "toolchain", "expected": "collection_state_change_reward"}),
        "artifact_digest": _digest({"summary": summary, "records": records}),
        "feature_status": "runtime_effective_in_pilot" if chain_success else "claim_denied_pending_evidence",
        "claim_gate": {"tool_use": claim_allowed, "reason": claim_reason},
        "output_files": ["toolchain_pilot_summary.json", "toolchain_pilot_records.jsonl", "toolchain_pilot_manifest.json"],
    }
    summary_path = out / "toolchain_pilot_summary.json"
    records_path = out / "toolchain_pilot_records.jsonl"
    manifest_path = out / "toolchain_pilot_manifest.json"
    _write_json(summary_path, summary)
    records_path.write_text("".join(json.dumps(r, sort_keys=True, allow_nan=False) + "\n" for r in records), encoding="utf-8")
    _write_json(manifest_path, manifest)
    # Backward-compatible aggregate file for older smoke tests.
    _write_json(out / "toolchain_pilot.json", {"summary": summary, "records": records, "manifest": manifest, "record_count": len(records), "chain_success": chain_success, "claim_allowed_for_tool_use": claim_allowed, "status": summary["pilot_status"]})
    return {"json": str(out / "toolchain_pilot.json"), "summary": str(summary_path), "records": str(records_path), "manifest": str(manifest_path), "manifest_digest": result.manifest.digest()}


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Run genesis toolchain pilot and export JSON artifacts.")
    parser.add_argument("--output-dir", default="genesis_toolchain_pilot_out")
    args = parser.parse_args()
    print(json.dumps(run(args.output_dir), indent=2, sort_keys=True, allow_nan=False))


if __name__ == "__main__":
    main()
