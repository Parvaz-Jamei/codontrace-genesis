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
from codontrace.genesis.engine import GenesisEngine
from codontrace.genesis.runtime_profiles import GenesisRuntimeProfile


def _digest(payload: object) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")).hexdigest()

def run(output_dir: str | Path = "genesis_memory_delayed_reward_pilot_out") -> dict[str, str]:
    out = Path(output_dir); out.mkdir(parents=True, exist_ok=True)
    result = GenesisEngine.from_spec(GenesisRuntimeProfile.memory_delayed_reward_pilot_world()).run_ticks()
    memory_use_records = [r.to_dict() for r in result.memory_use_records]
    delayed_reward_records = [r.to_dict() for r in result.delayed_reward_records]
    def _has_full_chain(record: dict[str, object]) -> bool:
        return all(
            record.get(key) not in (None, "")
            for key in (
                "signal_seen_tick",
                "memory_written_tick",
                "memory_read_tick",
                "decision_tick",
                "reward_tick",
                "memory_key",
                "action_after_memory",
                "link_digest",
            )
        )

    full_chain = bool(delayed_reward_records) and all(_has_full_chain(item) for item in delayed_reward_records)
    status = (
        "runtime_effective_delayed_reward_chain"
        if full_chain
        else "pilot_fixture_not_strong_memory_claim"
    )
    payload = {
        "memory_use_records": memory_use_records,
        "delayed_reward_records": delayed_reward_records,
        "status": status,
        "claim_allowed_for_strong_memory": full_chain,
    }
    path = out / "memory_delayed_reward.json"
    manifest = {
        "schema_version": "pilot_manifest_v1",
        "producer_version": RELEASE_LABEL,
        "library_version": getattr(result.manifest, "library_version", "unknown"),
        "pilot_name": "genesis_memory_delayed_reward_pilot",
        "pilot_status": status,
        "seed": 1,
        "config_digest": GenesisRuntimeProfile.memory_delayed_reward_pilot_world().digest(),
        "protocol_digest": _digest({"pilot": "memory_delayed_reward", "requires": "signal_write_read_action_reward"}),
        "artifact_digest": _digest(payload),
        "feature_status": "claim_eligible_limited" if full_chain else "claim_denied_pending_evidence",
        "claim_gate": {"strong_memory": full_chain, "reason": status},
        "output_files": ["memory_delayed_reward.json", "memory_delayed_reward_manifest.json"],
    }
    manifest_path = out / "memory_delayed_reward_manifest.json"
    path.write_text(json.dumps(payload, sort_keys=True, indent=2, allow_nan=False), encoding="utf-8")
    manifest_path.write_text(json.dumps(manifest, sort_keys=True, indent=2, allow_nan=False), encoding="utf-8")
    return {"json": str(path), "manifest": str(manifest_path), "manifest_digest": result.manifest.digest()}

def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Run genesis memory delayed reward pilot and export JSON artifacts.")
    parser.add_argument("--output-dir", default="genesis_memory_delayed_reward_pilot_out")
    args = parser.parse_args()
    print(json.dumps(run(args.output_dir), indent=2, sort_keys=True, allow_nan=False))


if __name__ == "__main__":
    main()
