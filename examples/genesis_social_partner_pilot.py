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


def _event_has_delta(event: dict[str, Any]) -> bool:
    return bool(
        float(event.get("resource_delta_source") or 0.0) != 0.0
        or float(event.get("resource_delta_target") or 0.0) != 0.0
        or float(event.get("fitness_delta_source") or 0.0) != 0.0
        or float(event.get("fitness_delta_target") or 0.0) != 0.0
        or bool(event.get("world_state_delta"))
    )


def run(output_dir: str | Path = "genesis_social_partner_pilot_out") -> dict[str, str]:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    familiar_spec = GenesisRuntimeProfile.social_partner_pilot_world(seed=1)
    unfamiliar_spec = GenesisRuntimeProfile.social_partner_pilot_world(seed=2)
    familiar = GenesisEngine.from_spec(familiar_spec).run_ticks()
    unfamiliar = GenesisEngine.from_spec(unfamiliar_spec).run_ticks()
    familiar_group = [r.to_dict() for r in familiar.partner_interaction_records]
    unfamiliar_group = [r.to_dict() for r in unfamiliar.partner_interaction_records]
    all_events = familiar_group + unfamiliar_group
    non_capsule = [e for e in all_events if not str(e.get("interaction_type", "")).startswith("capsule")]
    capsule = [e for e in all_events if str(e.get("interaction_type", "")).startswith("capsule")]
    pairs = {(e.get("source_organism_id"), e.get("target_organism_id")) for e in non_capsule if e.get("target_organism_id") not in {None, "", "environment"}}
    delta_events = [e for e in non_capsule if _event_has_delta(e)]
    social_interaction_allowed = bool(non_capsule and pairs and delta_events)
    social_intelligence_allowed = False
    summary = {
        "schema_version": "social_partner_summary_v1",
        "non_capsule_social_events": len(non_capsule),
        "capsule_social_events": len(capsule),
        "distinct_partner_pairs": len(pairs),
        "resource_or_fitness_delta_events": len(delta_events),
        "familiar_partner_group": familiar_group,
        "unfamiliar_partner_group": unfamiliar_group,
        "heldout_world_seed": 2,
        "heldout_protocol_digest": _digest({"familiar_seed": 1, "unfamiliar_seed": 2, "protocol": "non_capsule_resource_interaction_v1"}),
        "claim_allowed_for_social_interaction": social_interaction_allowed,
        "claim_allowed_for_social_intelligence": social_intelligence_allowed,
        "claim_gate_reason_social_interaction": "non_capsule_delta_event_observed" if social_interaction_allowed else "claim_denied_no_non_capsule_social_events",
        "claim_gate_reason_social_intelligence": "heldout_partner_protocol_exported_not_social_intelligence_proof",
    }
    manifest = {
        "schema_version": "pilot_manifest_v1",
        "producer_version": RELEASE_LABEL,
        "library_version": getattr(familiar.manifest, "library_version", "unknown"),
        "pilot_name": "genesis_social_partner_pilot",
        "pilot_status": "runtime_effective_social_interaction_pilot" if social_interaction_allowed else "claim_denied_no_non_capsule_social_events",
        "seed": 1,
        "config_digest": familiar_spec.digest(),
        "protocol_digest": summary["heldout_protocol_digest"],
        "artifact_digest": _digest({"summary": summary, "events": all_events}),
        "feature_status": "runtime_effective_in_pilot" if social_interaction_allowed else "claim_denied_pending_evidence",
        "claim_gate": {
            "social_interaction": social_interaction_allowed,
            "social_intelligence": social_intelligence_allowed,
            "reason": summary["claim_gate_reason_social_interaction"],
        },
        "output_files": ["social_partner_summary.json", "social_partner_events.jsonl", "social_partner_manifest.json"],
    }
    summary_path = out / "social_partner_summary.json"
    records_path = out / "social_partner_events.jsonl"
    manifest_path = out / "social_partner_manifest.json"
    _write_json(summary_path, summary)
    records_path.write_text("".join(json.dumps(e, sort_keys=True, allow_nan=False) + "\n" for e in all_events), encoding="utf-8")
    _write_json(manifest_path, manifest)
    _write_json(out / "social_partner.json", {**summary, "manifest": manifest, "claim_status": manifest["pilot_status"]})
    return {"json": str(out / "social_partner.json"), "summary": str(summary_path), "records": str(records_path), "manifest": str(manifest_path), "familiar_manifest_digest": familiar.manifest.digest(), "unfamiliar_manifest_digest": unfamiliar.manifest.digest()}


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Run genesis social partner pilot and export JSON artifacts.")
    parser.add_argument("--output-dir", default="genesis_social_partner_pilot_out")
    args = parser.parse_args()
    print(json.dumps(run(args.output_dir), indent=2, sort_keys=True, allow_nan=False))


if __name__ == "__main__":
    main()
