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

def run(output_dir: str | Path = "genesis_qd_selection_pilot_out") -> dict[str, str]:
    out = Path(output_dir); out.mkdir(parents=True, exist_ok=True)
    result = GenesisEngine.from_spec(GenesisRuntimeProfile.qd_selection_pilot_world()).run_ticks()
    audits = [
        tick.generation_result.selection_result.to_dict()
        for tick in result.ticks
        if tick.generation_result.selection_result is not None
    ]
    changed = any(bool(item.get("qd_changed_selection")) for item in audits)
    status = "selection_applied" if changed else "qd_selection_not_demonstrated"
    payload = {
        "selection_audits": audits,
        "qd_changed_selection": changed,
        "status": status,
        "manifest": result.manifest.to_dict(),
    }
    path = out / "qd_selection_pilot.json"
    manifest = {
        "schema_version": "pilot_manifest_v1",
        "producer_version": RELEASE_LABEL,
        "library_version": getattr(result.manifest, "library_version", "0.3.0a1"),
        "pilot_name": "genesis_qd_selection_pilot",
        "pilot_status": status,
        "seed": 1,
        "config_digest": GenesisRuntimeProfile.qd_selection_pilot_world().digest(),
        "protocol_digest": _digest({"pilot": "qd_selection", "requires": "qd_changed_selection_true"}),
        "artifact_digest": _digest(payload),
        "feature_status": "claim_eligible_limited" if changed else "claim_denied_pending_evidence",
        "claim_gate": {"qd_selection": changed, "reason": status},
        "output_files": ["qd_selection_pilot.json", "qd_selection_pilot_manifest.json"],
    }
    manifest_path = out / "qd_selection_pilot_manifest.json"
    path.write_text(json.dumps(payload, sort_keys=True, indent=2, allow_nan=False), encoding="utf-8")
    manifest_path.write_text(json.dumps(manifest, sort_keys=True, indent=2, allow_nan=False), encoding="utf-8")
    return {"json": str(path), "manifest": str(manifest_path), "manifest_digest": result.manifest.digest()}

def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Run genesis qd selection pilot and export JSON artifacts.")
    parser.add_argument("--output-dir", default="genesis_qd_selection_pilot_out")
    args = parser.parse_args()
    print(json.dumps(run(args.output_dir), indent=2, sort_keys=True, allow_nan=False))


if __name__ == "__main__":
    main()
