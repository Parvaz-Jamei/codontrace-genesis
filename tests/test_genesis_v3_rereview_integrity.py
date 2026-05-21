from __future__ import annotations

import json
from pathlib import Path


def test_release_docs_do_not_reference_obsolete_artifact_names() -> None:
    root = Path(__file__).resolve().parents[1]
    docs = [
        root / "README.md",
        root / "CHANGELOG.md",
        root / "PATCH_SUMMARY.md",
        root / "RELEASE_EVIDENCE.md",
        root / "docs" / "FEATURE_WIRING_MATRIX.md",
    ]
    obsolete = (
        "codontrace-v0.3.0a1-deadcode-wiring-scientific-final-audited-clean.zip",
        "codontrace-v0.3.0a1-final-runtime-wiring.zip",
        "codontrace-v0.3.0a1-scientific-runtime-fixes.zip",
        "codontrace-v0.3.0a1-pilot-strengthened-v2.zip",
    )
    for doc in docs:
        text = doc.read_text(encoding="utf-8")
        for old in obsolete:
            assert old not in text, f"{doc} still references obsolete artifact {old}"


def test_feature_wiring_matrix_keeps_social_interaction_and_intelligence_separate() -> None:
    root = Path(__file__).resolve().parents[1]
    matrix = (root / "docs" / "FEATURE_WIRING_MATRIX.md").read_text(encoding="utf-8")
    assert "Social interaction" in matrix
    assert "Social intelligence" in matrix
    assert "social intelligence remains denied" in matrix.lower() or "heldout" in matrix.lower()


def test_release_evidence_lists_all_official_pilot_outputs() -> None:
    root = Path(__file__).resolve().parents[1]
    evidence = (root / "RELEASE_EVIDENCE.md").read_text(encoding="utf-8")
    for required in (
        "genesis_evolution_pilot.json",
        "qd_selection_pilot.json",
        "toolchain_pilot_summary.json",
        "capsule_utility_summary.json",
        "memory_delayed_reward.json",
        "social_partner_summary.json",
    ):
        assert required in evidence


def test_replayable_pilot_manifests_in_committed_artifacts_are_json_and_claim_gated() -> None:
    root = Path(__file__).resolve().parents[1]
    artifacts = root / "artifacts"
    # The source archive may include only a minimal placeholder artifacts tree. This
    # test validates committed manifests when present and otherwise relies on the
    # official pilot CLI tests for generated artifacts.
    for manifest in artifacts.rglob("*_manifest.json"):
        payload = json.loads(manifest.read_text(encoding="utf-8"))
        assert "manifest_digest" in payload or "artifact_digest" in payload or "protocol_digest" in payload
        assert "claim_gate" in payload or "claim_gate_reason" in payload or "feature_status" in payload
