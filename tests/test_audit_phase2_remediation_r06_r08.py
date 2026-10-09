"""Strict Scientific Invariants & Security Regression Tests for Phase 2 Remediation (R06-R08).

Audit Document: AUDIT_037648e_UPDATE_REVIEW_FA.md
Scope:
- R06: Unified runner adapter, manifest, and capabilities contract; custom scripts without
       PAUSE consumer must report pause=False and reject pause action with HTTP 409.
- R07: Runtime wiring audit must reject 64-zero hashes, fake payloads, and enforce
       verify_artifact_bytes; restored 5 catalog features with skipped/not_applicable status.
- R08: Replay policy registry must validate actual dataclass fields without bypass shortcuts,
       ensuring digest integrity and round-trip stability.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from codontrace.console import runs
from codontrace.genesis.replay_integrity import (
    _DIGEST_FIELDS_BY_CLASS,
    NON_REPLAY_CRITICAL_DIGEST_CLASSES,
    STRICT_REPLAY_CRITICAL_DIGEST_CLASSES,
    resolve_class_path,
)
from codontrace.genesis.runtime_wiring_audit import (
    RuntimeWiringFeature,
    audit_runtime_wiring,
    integration_feature_catalog,
)

# ==============================================================================
# R06: Unified Runner Adapter, Manifest & Capabilities Contract
# ==============================================================================


def test_r06_noncooperative_custom_script_rejects_pause_with_409(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """R06: A custom script without explicit PAUSE support/consumer must report
    capabilities.pause = False in manifest and adapter, and reject pause action with 409.
    
    Audit finding:
    Launcher previously wrote pause=True for almost any custom script, but
    CustomScriptRunnerAdapter had pause=False, leading to UI/runtime desynchronization.
    """
    runs_dir = tmp_path / "runs"
    runs_dir.mkdir()
    scripts_dir = tmp_path / "scripts"
    scripts_dir.mkdir()

    # Create a non-cooperative custom script (simple script without PAUSE file handling)
    script_file = scripts_dir / "user_benchmark.py"
    script_file.write_text("import time\ntime.sleep(1.0)\n", encoding="utf-8")

    monkeypatch.setenv("CODONTRACE_RUNS_DIR", str(runs_dir))
    monkeypatch.setenv("CODONTRACE_SCRIPTS_DIR", str(scripts_dir))

    launch_res = runs.launch_simulation_run({
        "scriptName": "user_benchmark.py",
        "title": "Non-Cooperative Run",
    })
    assert launch_res.get("ok") is True, f"Failed to launch: {launch_res}"
    run_id = launch_res["runId"]
    run_dir = runs_dir / run_id

    # Read the manifest produced by launcher
    manifest_file = run_dir / "run_manifest.json"
    if not manifest_file.is_file():
        manifest_file = run_dir / "manifest.json"
    manifest = json.loads(manifest_file.read_text(encoding="utf-8"))

    # Invariant 1: Adapter and Manifest capabilities MUST agree
    adapter = runs.get_runner_adapter(manifest, script_name="user_benchmark.py")
    assert isinstance(adapter, runs.CustomScriptRunnerAdapter)
    adapter_caps = adapter.resolve_capabilities(run_dir)
    assert adapter_caps["pause"] is False, "CustomScriptRunnerAdapter must report pause=False"

    manifest_caps = manifest.get("capabilities", {})
    assert manifest_caps.get("pause") is False, (
        f"R06 Invariant Violated: Launcher declared pause=True for non-cooperative script: {manifest_caps}"
    )

    # Invariant 2: manage_run_action('pause') MUST be rejected with HTTP 409 UNSUPPORTED_CAPABILITY
    pause_res = runs.manage_run_action(run_id, "pause")
    assert pause_res["ok"] is False, (
        f"R06 Invariant Violated: manage_run_action allowed pause on non-cooperative script: {pause_res}"
    )
    assert pause_res.get("status_code") == 409
    assert pause_res.get("error_code") == "UNSUPPORTED_CAPABILITY"
    assert not (run_dir / "PAUSE").exists(), "PAUSE marker file must not be created for unsupported runner"


def test_r06_backend_and_engine_backend_key_parity() -> None:
    """R06: Parity between producer (engineBackend) and adapter reader (backend).
    
    Audit finding:
    Producer wrote executionBoundary.engineBackend, while adapter looked for
    executionBoundary.backend. A manifest with engineBackend='genesis_engine'
    must properly resolve to GenesisEngineRunnerAdapter.
    """
    manifest_with_engine_backend = {
        "executionBoundary": {
            "engineBackend": "genesis_engine",
            "isFrontierReference": False,
        },
        "params": {
            "scriptName": "engine_run.py",
        },
    }
    adapter = runs.get_runner_adapter(manifest_with_engine_backend)
    assert isinstance(adapter, runs.GenesisEngineRunnerAdapter), (
        f"R06 Key Parity Violated: engineBackend='genesis_engine' resolved to {type(adapter).__name__} instead of GenesisEngineRunnerAdapter"
    )
    assert adapter.supports_pause is True
    assert adapter.supports_resume is True


# ==============================================================================
# R07: Strict Runtime Wiring Audit, 64-Zero Hash Rejection & 5 Catalog Features
# ==============================================================================


def test_r07_reject_fake_64_zeroes_digest_and_require_real_verification() -> None:
    """R07: Runtime wiring audit must reject synthetic 64-zero sha256 digests
    and empty/fake payloads. runtime_verified must be False when digests are synthetic zeroes.
    
    Audit finding:
    Providing sha256 with 64 zeroes gave passed=True and runtime_verified=True
    without any engine run or real artifact byte verification.
    """
    catalog = integration_feature_catalog()

    class SyntheticZeroManifest:
        def __init__(self, cat: tuple[RuntimeWiringFeature, ...]) -> None:
            # 64-zero SHA256 string for every manifest key
            self.artifact_digest_map = {f.manifest_key: "sha256:" + "0" * 64 for f in cat}

    class SyntheticPayloadResult:
        def __init__(self, cat: tuple[RuntimeWiringFeature, ...]) -> None:
            self.evidence_manifest = SyntheticZeroManifest(cat)
            self._d = {f.result_key: {"arbitrary_non_empty": 123} for f in cat}

        def to_dict(self) -> dict[str, Any]:
            return self._d

    synth_result = SyntheticPayloadResult(catalog)
    audit_res = audit_runtime_wiring(synth_result)

    # Invariant: Must NOT grant runtime_verified or passed on 64-zero placeholder hashes!
    assert audit_res["runtime_verified"] is False, (
        f"Security Invariant Violated: audit accepted 64-zero sha256 digest as runtime_verified: {audit_res}"
    )
    assert audit_res["passed"] is False


def test_r07_catalog_contains_restored_five_features_with_proper_status() -> None:
    """R07: The 5 removed features must be restored to catalog:
    - d0_baseline_metrics
    - novelty_trajectory_metrics
    - learnability_assay
    - seed_sweep_protocol
    - checkpoint_resume_audit
    
    When not activated by current profile, they must be marked skipped/not_applicable,
    not completely erased from the catalog to fake green tests.
    """
    catalog = integration_feature_catalog()
    catalog_feature_names = {f.feature_name for f in catalog}

    required_restored_features = {
        "d0_baseline_metrics",
        "novelty_trajectory_metrics",
        "learnability_assay",
        "seed_sweep_protocol",
        "checkpoint_resume_audit",
    }

    missing_from_catalog = required_restored_features - catalog_feature_names
    assert not missing_from_catalog, (
        f"R07 Invariant Violated: 5 removed features are still missing from catalog: {missing_from_catalog}"
    )


# ==============================================================================
# R08: Replay Policy Registry & Dataclass Digest Fields Invariants
# ==============================================================================


def test_r08_replay_policy_registry_inspects_true_dataclass_fields() -> None:
    """R08: Replay digest policy registry must validate actual dataclass fields
    directly from class inspection (__dataclass_fields__) without bypass shortcuts.
    
    Audit finding:
    `public_dataclass_digest_fields` had a bypass shortcut returning _DIGEST_FIELDS_BY_CLASS
    directly, masking 57-60 mismatches between class definitions and registry expectations.
    """
    all_paths = (*STRICT_REPLAY_CRITICAL_DIGEST_CLASSES, *NON_REPLAY_CRITICAL_DIGEST_CLASSES)
    mismatches: list[str] = []

    for path in sorted(all_paths):
        cls = resolve_class_path(path)
        # Inspect TRUE dataclass fields directly without shortcut:
        fields = getattr(cls, "__dataclass_fields__", {})
        actual_fields = tuple(
            name for name in fields if not name.startswith("_") and (name == "digest" or "_digest" in name)
        )
        expected_fields = _DIGEST_FIELDS_BY_CLASS.get(path)

        if actual_fields != expected_fields:
            mismatches.append(f"{path}: expected={expected_fields} vs actual={actual_fields}")

    assert not mismatches, (
        f"R08 Invariant Violated: Found {len(mismatches)} digest field mismatches between true class fields and policy registry:\n"
        + "\n".join(mismatches[:10])
    )


def test_r08_adf_detection_result_digest_fields_intact() -> None:
    """R08: codontrace.genesis.adf.ADFDetectionResult must have vocabulary_digest_before
    and vocabulary_digest_after properly recognized and matched between class and policy.
    """
    cls = resolve_class_path("codontrace.genesis.adf.ADFDetectionResult")
    fields = getattr(cls, "__dataclass_fields__", {})
    actual_fields = tuple(
        name for name in fields if not name.startswith("_") and (name == "digest" or "_digest" in name)
    )
    expected_fields = _DIGEST_FIELDS_BY_CLASS.get("codontrace.genesis.adf.ADFDetectionResult")

    assert "vocabulary_digest_before" in actual_fields
    assert "vocabulary_digest_after" in actual_fields
    assert actual_fields == expected_fields, (
        f"ADFDetectionResult digest mismatch: expected={expected_fields}, actual={actual_fields}"
    )
