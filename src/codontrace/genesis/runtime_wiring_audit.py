"""Integration runtime wiring audit primitives.

The audit is intentionally conservative: a feature is complete only when it has
an importable producer path, replay policy coverage, and a manifest/result route.
It does not synthesize scientific success; unsupported paths remain provisional
or blocked with explicit reasons.
"""

from __future__ import annotations

from dataclasses import dataclass
from importlib import import_module
from typing import Any

from codontrace._types import JsonValue
from codontrace.genesis.canonical import canonical_digest, is_real_evidence_digest
from codontrace.genesis.replay_integrity import replay_digest_class_policies


@dataclass(frozen=True, slots=True)
class RuntimeWiringFeature:
    feature_name: str
    record_class_path: str
    runtime_producer: str
    result_key: str
    manifest_key: str
    claim_relevant: bool
    positive_test: str
    negative_test: str
    record_digest: str = ""

    def __post_init__(self) -> None:
        if not self.record_digest:
            object.__setattr__(self, "record_digest", canonical_digest({
                "feature_name": self.feature_name,
                "record_class_path": self.record_class_path,
                "runtime_producer": self.runtime_producer,
                "result_key": self.result_key,
                "manifest_key": self.manifest_key,
                "claim_relevant": self.claim_relevant,
                "positive_test": self.positive_test,
                "negative_test": self.negative_test,
            }, prefix="integration_wiring_feature"))

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "feature_name": self.feature_name,
            "record_class_path": self.record_class_path,
            "runtime_producer": self.runtime_producer,
            "result_key": self.result_key,
            "manifest_key": self.manifest_key,
            "claim_relevant": self.claim_relevant,
            "positive_test": self.positive_test,
            "negative_test": self.negative_test,
            "record_digest": self.record_digest,
        }

    def digest(self) -> str:
        return self.record_digest


def integration_feature_catalog() -> tuple[RuntimeWiringFeature, ...]:
    return (
        RuntimeWiringFeature("mutation_operator_maturity", "codontrace.genesis.phase1_runtime_maturity.MutationOperatorAuditRecord", "GenesisRunResult.phase1_runtime_maturity_report", "phase1_runtime_maturity_report", "phase1_runtime_maturity_report", True, "tests/test_genesis_mutation_operator_maturity.py", "tests/test_genesis_mutation_operator_maturity.py"),
        RuntimeWiringFeature("birth_reproduction_gate", "codontrace.genesis.phase1_runtime_maturity.ReproductionGateAuditRecord", "GenesisRunResult.phase1_runtime_maturity_report", "phase1_runtime_maturity_report", "phase1_runtime_maturity_report", True, "tests/test_genesis_a32_birth_mutation_inheritance.py", "tests/test_genesis_a32_birth_mutation_inheritance.py"),
        RuntimeWiringFeature("role_detection_runtime", "codontrace.genesis.phase1_runtime_maturity.RuntimeRoleEvidenceRecord", "GenesisRunResult.phase1_runtime_maturity_report", "phase1_runtime_maturity_report", "phase1_runtime_maturity_report", True, "tests/test_genesis_role_detection_runtime.py", "tests/test_genesis_role_detection_runtime.py"),
        RuntimeWiringFeature("discovery_detector", "codontrace.genesis.phase_b_scientific_maturity.DiscoveryEvent", "GenesisRunResult.phase_b_scientific_maturity_report", "phase_b_scientific_maturity_report", "phase_b_scientific_maturity_report", True, "tests/science_gates/test_discovery_gate_requires_d0_shadow_persistence_ablation.py", "tests/science_gates/test_discovery_gate_requires_d0_shadow_persistence_ablation.py"),
        RuntimeWiringFeature("ablation_witness", "codontrace.genesis.phase_b_scientific_maturity.AblationWitness", "GenesisRunResult.phase_b_scientific_maturity_report", "phase_b_ablation_witnesses", "phase_b_ablation_witnesses", True, "tests/science_gates/test_causal_intervention_protocol.py", "tests/science_gates/test_metadata_only_intervention_supported_rejected.py"),
        RuntimeWiringFeature("heldout_generalization", "codontrace.genesis.phase_b_scientific_maturity.HeldoutEvaluationResult", "GenesisRunResult.phase_b_scientific_maturity_report", "phase_b_heldout_evaluations", "phase_b_heldout_evaluations", True, "tests/test_genesis_generalization_snapshots.py", "tests/test_genesis_social_heldout_distinctness.py"),
        RuntimeWiringFeature("collective_swarm_ladder", "codontrace.genesis.phase_b_scientific_maturity.CollectiveSwarmEvidenceLadder", "GenesisRunResult.phase_b_scientific_maturity_report", "phase_b_collective_swarm_ladders", "phase_b_collective_swarm_ladders", True, "tests/test_genesis_collective_intelligence_claim_gate.py", "tests/test_genesis_collective_intelligence_claim_gate.py"),
        RuntimeWiringFeature("oee_metrics", "codontrace.genesis.phase_b_scientific_maturity.OEEClaimEligibilityResult", "GenesisRunResult.phase_b_scientific_maturity_report", "phase_b_oee_results", "phase_b_oee_results", True, "tests/science_gates/test_oee_candidate_requires_validated_oee_report_artifact.py", "tests/science_gates/test_metadata_only_oee_candidate_rejected.py"),
        RuntimeWiringFeature("curriculum_environment", "codontrace.genesis.phase_b_scientific_maturity.CurriculumEnvironmentRecord", "GenesisRunResult.phase_b_scientific_maturity_report", "phase_b_curriculum_records", "phase_b_curriculum_records", True, "tests/test_genesis_curriculum_environment_coevolution.py", "tests/test_genesis_curriculum_environment_coevolution.py"),
        RuntimeWiringFeature("scale_ladder", "codontrace.genesis.phase_b_scientific_maturity.ScaleBenchmarkReport", "GenesisRunResult.phase_b_scientific_maturity_report", "phase_b_scale_reports", "phase_b_scale_reports", True, "tests/test_genesis_scale_ladder_benchmark.py", "tests/test_genesis_scale_ladder_benchmark.py"),
        RuntimeWiringFeature("statistical_protocol", "codontrace.genesis.phase_b_scientific_maturity.StatisticalClaimValidationResult", "GenesisRunResult.phase_b_scientific_maturity_report", "phase_b_statistical_results", "phase_b_statistical_results", True, "tests/science_gates/test_phase3_digest_and_release_pack_strictness.py", "tests/science_gates/test_phase3_final_acceptance_blockers.py"),
        RuntimeWiringFeature("release_evidence_pack", "codontrace.genesis.phase_b_scientific_maturity.ReleaseEvidencePackSample", "GenesisRunResult.phase_b_scientific_maturity_report", "phase_b_release_packs", "phase_b_release_packs", True, "tests/science_gates/test_phase3_final_acceptance_blockers.py", "tests/science_gates/test_phase3_digest_and_release_pack_strictness.py"),
        RuntimeWiringFeature("plugin_extension_safety", "codontrace.genesis.phase_b_scientific_maturity.PluginValidationResult", "GenesisRunResult.phase_b_scientific_maturity_report", "phase_b_plugin_validations", "phase_b_plugin_validations", True, "tests/test_genesis_plugin_api_safety.py", "tests/test_genesis_plugin_api_safety.py"),
    )


def _import_class(path: str) -> type[Any]:
    module_name, name = path.rsplit(".", 1)
    return getattr(import_module(module_name), name)


def audit_runtime_wiring(result: Any | None = None, *, features: tuple[RuntimeWiringFeature, ...] | None = None) -> dict[str, JsonValue]:
    catalog = features or integration_feature_catalog()
    policy_paths = {item.class_path for item in replay_digest_class_policies()}
    result_payload = result.to_dict() if result is not None and hasattr(result, "to_dict") else {}
    manifest_map = {}
    if result is not None and hasattr(result, "evidence_manifest"):
        manifest_map = dict(result.evidence_manifest.artifact_digest_map)
    issues: list[str] = []
    rows: list[dict[str, JsonValue]] = []
    for feature in catalog:
        importable = True
        try:
            _import_class(feature.record_class_path)
        except Exception:
            importable = False
            issues.append(f"record_not_importable:{feature.feature_name}:{feature.record_class_path}")
        replay_policy_registered = feature.record_class_path in policy_paths
        if not replay_policy_registered:
            issues.append(f"missing_replay_policy:{feature.feature_name}")
        result_reachable = not result_payload or feature.result_key in result_payload or feature.result_key in manifest_map
        if not result_reachable:
            issues.append(f"missing_result_key:{feature.feature_name}:{feature.result_key}")
        manifest_reachable = not manifest_map or feature.manifest_key in manifest_map
        if not manifest_reachable:
            issues.append(f"missing_manifest_key:{feature.feature_name}:{feature.manifest_key}")
        digest = manifest_map.get(feature.manifest_key) if manifest_map else feature.digest()
        if digest and isinstance(digest, str) and digest.startswith(("fake", "placeholder", "not_run:")):
            issues.append(f"non_real_manifest_digest:{feature.feature_name}")
        rows.append({**feature.to_dict(), "record_importable": importable, "result_reachable": result_reachable, "manifest_reachable": manifest_reachable, "replay_policy_registered": replay_policy_registered, "audit_digest": feature.digest()})
    return {"schema_version": "integration_runtime_wiring_audit_v1", "passed": not issues, "issues": sorted(set(issues)), "features": rows, "audit_digest": canonical_digest(rows, prefix="integration_wiring")}
