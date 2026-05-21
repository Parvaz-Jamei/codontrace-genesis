from __future__ import annotations

import ast
from pathlib import Path, PurePosixPath, PureWindowsPath

from codontrace.genesis.replay_integrity import (
    STRICT_REPLAY_CRITICAL_DIGEST_CLASSES,
    audit_replay_digest_policy_registry,
    build_replay_digest_class_policy,
    replay_digest_class_policies,
)


def _module_path_from_source(source: Path) -> str:
    return ".".join(source.relative_to("src").with_suffix("").parts)


def test_module_path_from_source_is_cross_platform() -> None:
    posix_source = PurePosixPath("src/codontrace/genesis/artifacts.py")
    windows_source = PureWindowsPath("src/codontrace/genesis/artifacts.py")

    assert (
        ".".join(posix_source.relative_to("src").with_suffix("").parts)
        == "codontrace.genesis.artifacts"
    )
    assert (
        ".".join(windows_source.relative_to("src").with_suffix("").parts)
        == "codontrace.genesis.artifacts"
    )


KNOWN_STRICT_CLASSES = {
    "codontrace.genesis.translation_profile.TranslationProfile",
    "codontrace.genesis.structural_mutation.StructuralMutationRecord",
    "codontrace.genesis.causal_validation.PredictiveProbeResult",
    "codontrace.genesis.causal_validation.InterventionResult",
    "codontrace.genesis.innovation_protection.InnovationRecord",
    "codontrace.genesis.adf_runtime.MacroUtilityRecord",
    "codontrace.genesis.adf_runtime.MacroPruningDecision",
    "codontrace.genesis.qd_search.QDSchedulerState",
    "codontrace.genesis.qd_search.QDCandidate",
    "codontrace.genesis.statistical_protocol.OEEMetricsReport",
}


def _source_digest_dataclass_paths() -> set[str]:
    paths: set[str] = set()
    for source in Path("src/codontrace").rglob("*.py"):
        tree = ast.parse(source.read_text(encoding="utf-8"))
        module = _module_path_from_source(source)
        for node in ast.walk(tree):
            if not isinstance(node, ast.ClassDef):
                continue
            is_dataclass = False
            for decorator in node.decorator_list:
                if isinstance(decorator, ast.Name) and decorator.id == "dataclass":
                    is_dataclass = True
                if isinstance(decorator, ast.Call):
                    fn = decorator.func
                    if isinstance(fn, ast.Name) and fn.id == "dataclass":
                        is_dataclass = True
                    if isinstance(fn, ast.Attribute) and fn.attr == "dataclass":
                        is_dataclass = True
            if not is_dataclass:
                continue
            digest_fields = []
            for item in node.body:
                if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
                    name = item.target.id
                    if name == "digest" or name.endswith("_digest"):
                        digest_fields.append(name)
            if digest_fields:
                paths.add(f"{module}.{node.name}")
    return paths


def test_replay_critical_digest_sweep_all_public_digest_objects() -> None:
    source_paths = _source_digest_dataclass_paths()
    policy_paths = {policy.class_path for policy in replay_digest_class_policies()}
    assert source_paths - policy_paths == set()
    assert policy_paths - source_paths == set()
    assert audit_replay_digest_policy_registry() == ()


def test_digest_policy_marks_non_evidence_reference_classes_explicitly() -> None:
    policy = build_replay_digest_class_policy("codontrace.genesis.artifacts.RunManifest")
    assert policy.replay_role == "non_replay_critical"
    assert policy.evidence_role == "reference_or_summary_only_not_scientific_evidence"
    assert policy.validation_mode == "excluded_from_claim_granting_without_validated_artifact"


def test_known_replay_critical_digest_classes_are_strictly_registered() -> None:
    assert set(STRICT_REPLAY_CRITICAL_DIGEST_CLASSES) >= KNOWN_STRICT_CLASSES
    for path in KNOWN_STRICT_CLASSES:
        policy = build_replay_digest_class_policy(path)
        assert policy.replay_critical
        assert policy.validation_mode == "constructor_or_factory_must_validate_digest"
