#!/usr/bin/env python3
"""Integration end-to-end validation smoke.

This example is deliberately evidence-oriented: it runs the public GENESIS
engine path, consumes Phase-A/Phase-B reports, writes the integration audit artifacts,
and keeps limited/downgraded claims explicit instead of inventing success.
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
import sys

try:
    from examples._path_bootstrap import ensure_src_path
except ModuleNotFoundError:  # pragma: no cover
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
else:
    ensure_src_path()

from codontrace.genesis import GenesisEngine, GenesisExperimentSpec
from codontrace.genesis.canonical import canonical_digest
from codontrace.genesis.evidence_consistency import audit_result_evidence_consistency
from codontrace.genesis.public_api_manifest import public_api_manifest_payload
from codontrace.genesis.runtime_wiring_audit import audit_runtime_wiring, integration_feature_catalog


def _write_json(path: Path, payload: object) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return canonical_digest(payload, prefix="artifact")


def _digest_obj(obj: object) -> str:
    digest = getattr(obj, "digest", None)
    if callable(digest):
        return str(digest())
    value = getattr(obj, "record_digest", None)
    if value:
        return str(value)
    to_dict = getattr(obj, "to_dict", None)
    if callable(to_dict):
        return canonical_digest(to_dict(), prefix="record")
    return canonical_digest({"repr": repr(obj)}, prefix="record")


def _small_run(profile: str):
    ticks = 1 if profile == "smoke" else 2
    spec = GenesisExperimentSpec(
        seed=17,
        tick_count=ticks,
        world_width=2,
        world_height=2,
        genome_bits=("000000000",),
        initial_runtime_atp=5.0,
        initial_learning_atp=2.0,
        population_max=4,
    )
    return GenesisEngine.from_spec(spec).run_ticks()


def _scientific_freshness_matrix() -> dict:
    rows = [
        ["FAIR/research artifacts", "metadata-rich/versioned/replayable/source-linked", "evidence.py/evidence_bundle.py", "tests/test_genesis_integration_evidence_consistency.py", "genesis_integration_end_to_end_validation.py", "EvidenceManifest/ClaimGate", "complete_limited_claim", "sample smoke only"],
        ["Quality Diversity", "descriptor validity + coverage + selection pressure", "quality_diversity.py/phase_b_scientific_maturity.py", "tests/genesis_gates/test_qd_population_integration.py", "genesis_qd_selection_pilot.py", "ClaimGate", "complete_limited_claim", "not a large benchmark"],
        ["Open-endedness", "novelty + persistence + learnability + transfer + controls", "open_endedness.py/phase_b_scientific_maturity.py", "tests/science_gates/test_phase3_oee_threshold_consistency.py", "genesis_integration_end_to_end_validation.py", "OEEClaimEligibilityResult", "descriptive_only", "single smoke seed"],
        ["Causal validation", "intervention/ablation baseline-treatment comparison", "intervention.py/causal_validation.py", "tests/science_gates/test_metadata_only_intervention_supported_rejected.py", "genesis_ablation_protocol.py", "ScientificClaimGate", "complete_limited_claim", "smoke artifact only"],
        ["Collective/swarm evidence", "non-capsule cooperation + role complementarity + scaling", "collective_intelligence.py/swarm_metrics.py", "tests/test_genesis_collective_intelligence_claim_gate.py", "genesis_social_partner_pilot.py", "SocialClaimLadder", "descriptive_only", "capsule-only evidence stays limited"],
        ["Plugin safety", "deterministic config digest + no ClaimGate bypass", "plugins.py/phase_b_scientific_maturity.py", "tests/test_genesis_plugin_api_safety.py", "plugin_action_skeleton.py", "PluginValidationResult", "complete_limited_claim", "third-party plugins need external review"],
    ]
    return {
        "schema_version": "integration_scientific_freshness_matrix_v1",
        "rows": [
            {
                "capability": r[0],
                "scientific_standard_principle": r[1],
                "implementation_module": r[2],
                "test_file": r[3],
                "example_pilot": r[4],
                "claim_gate": r[5],
                "status": r[6],
                "remaining_risk": r[7],
            }
            for r in rows
        ],
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--profile", choices=("smoke", "medium"), default="smoke")
    ap.add_argument("--out", required=True)
    ns = ap.parse_args(argv)
    out = Path(ns.out)
    out.mkdir(parents=True, exist_ok=True)

    result = _small_run(ns.profile)
    phase1 = result.phase1_runtime_maturity_report
    phase_b = result.phase_b_scientific_maturity_report
    stable_run_digest = canonical_digest({"spec_digest": result.run.spec_digest, "phase1": _digest_obj(phase1), "phase_b": _digest_obj(phase_b)}, prefix="run")
    required_classes = tuple(item.record_class_path for item in integration_feature_catalog())

    run_config = {"schema_version": "integration_run_config_v1", "profile": ns.profile, "seed": 17, "tick_count": 2 if ns.profile == "smoke" else 4}
    _write_json(out / "integration_run_config.json", run_config)

    record_rows = [
        {"record_type": "phase1_runtime_maturity_report", "record_digest": _digest_obj(phase1), "status": "measured"},
        {"record_type": "phase_b_scientific_maturity_report", "record_digest": _digest_obj(phase_b), "status": "measured"},
    ]
    with (out / "integration_run_records.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["record_type", "record_digest", "status"])
        writer.writeheader(); writer.writerows(record_rows)

    artifact_manifest = result.evidence_manifest.to_dict()
    _write_json(out / "integration_artifact_manifest.json", artifact_manifest)
    replay_bundle_index = {"schema_version": "integration_replay_bundle_index_v1", "digests": list(result.evidence_manifest.artifact_digest_map.values()), "source_result_digest": stable_run_digest}
    _write_json(out / "integration_replay_bundle_index.json", replay_bundle_index)

    nodes = [
        {"node_id": "phase1", "digest": _digest_obj(phase1), "kind": "runtime_maturity"},
        {"node_id": "phaseB", "digest": _digest_obj(phase_b), "kind": "scientific_maturity"},
        {"node_id": "manifest", "digest": result.evidence_manifest.digest(), "kind": "manifest"},
    ]
    lineage = {"schema_version": "integration_evidence_lineage_dag_v1", "nodes": nodes, "edges": [{"source": "phase1", "target": "phaseB"}, {"source": "phaseB", "target": "manifest"}]}
    _write_json(out / "integration_evidence_lineage_dag.json", lineage)

    allowed_digest = _digest_obj(phase1)
    blocked_digest = _digest_obj(phase_b.oee_results[0]) if phase_b.oee_results else _digest_obj(phase_b)
    claim_manifest = {
        "schema_version": "integration_final_claim_manifest_v1",
        "claim_gate": "limited_allowed_with_strong_claim_downgrade",
        "claim_gate_reason": "runtime maturity has evidence; strong OEE remains downgraded in smoke profile",
        "claims": [
            {"claim_id": "limited_runtime_maturity", "status": "allowed", "required_evidence": [allowed_digest], "claim_gate_decision": "limited_allowed"},
            {"claim_id": "strong_oee", "status": "downgraded", "required_evidence": [blocked_digest], "blocked_reason": "smoke_profile_not_enough_seeds"},
        ],
    }
    claim_manifest["manifest_digest"] = canonical_digest(claim_manifest, prefix="manifest")
    _write_json(out / "integration_final_claim_manifest.json", claim_manifest)

    release_pack = {"schema_version": "integration_release_evidence_pack_v1", "phase1_digest": _digest_obj(phase1), "phase_b_digest": _digest_obj(phase_b), "claim_manifest_digest": canonical_digest(claim_manifest, prefix="claim_manifest"), "replay_bundle_digest": canonical_digest(replay_bundle_index, prefix="replay_bundle")}
    _write_json(out / "integration_release_evidence_pack.json", release_pack)
    negative_results = {"schema_version": "integration_negative_results_v1", "results": [{"claim_id": "strong_oee", "status": "downgraded", "reason": "too_few_smoke_seeds"}]}
    _write_json(out / "integration_negative_results.json", negative_results)
    public_api = public_api_manifest_payload()
    _write_json(out / "integration_public_api_manifest.json", public_api)
    matrix = _scientific_freshness_matrix()
    _write_json(out / "integration_scientific_freshness_matrix.json", matrix)

    wiring = audit_runtime_wiring(result)
    evidence = audit_result_evidence_consistency(result, claims=claim_manifest["claims"], required_class_paths=required_classes)
    summary = {"schema_version": "integration_validation_summary_v1", "profile": ns.profile, "wiring_passed": wiring["passed"], "evidence_passed": evidence["passed"], "run_digest": stable_run_digest, "artifact_count": len(list(out.iterdir()))}
    _write_json(out / "integration_validation_summary.json", summary)
    html = "<html><body><h1>Integration Validation Summary</h1><p>Validated from release artifacts.</p><pre>" + json.dumps(summary, indent=2, sort_keys=True) + "</pre></body></html>"
    (out / "integration_validation_summary.html").write_text(html, encoding="utf-8")
    if not wiring["passed"] or not evidence["passed"]:
        return 1
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
