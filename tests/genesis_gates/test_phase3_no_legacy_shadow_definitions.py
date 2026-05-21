from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _class_counts(path: str) -> dict[str, int]:
    tree = ast.parse((ROOT / path).read_text(), filename=path)
    counts: dict[str, int] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            counts[node.name] = counts.get(node.name, 0) + 1
    return counts


def test_phase3_campaign_has_no_legacy_shadow_contract_definitions() -> None:
    counts = _class_counts("src/codontrace/genesis/campaign.py")
    for name in (
        "Phase3RunRecord",
        "Phase3CampaignManifest",
        "Phase3CampaignResult",
        "Phase3ExperimentLedger",
    ):
        assert counts.get(name) == 1


def test_phase3_final_release_has_no_legacy_shadow_contract_definitions() -> None:
    counts = _class_counts("src/codontrace/genesis/final_release_manifest.py")
    for name in (
        "FinalClaimManifest",
        "ReleaseEvidencePack",
        "FinalClaimValidationResult",
    ):
        assert counts.get(name) == 1


def test_phase3_oee_and_statistical_contracts_have_no_legacy_shadow_definitions() -> None:
    oee_counts = _class_counts("src/codontrace/genesis/open_endedness.py")
    for name in ("OEECandidateMetrics", "LearnabilityReport"):
        assert oee_counts.get(name) == 1

    stat_counts = _class_counts("src/codontrace/genesis/statistical_protocol.py")
    for name in ("StatisticalTestPolicy", "PairedComparisonResult"):
        assert stat_counts.get(name) == 1
