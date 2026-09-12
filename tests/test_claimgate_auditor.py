"""Standalone ClaimGate auditor: CLAIMS.md §5 + §8, never loosened."""

from __future__ import annotations

import json
from pathlib import Path

from codontrace.claimgate import audit_bundle, parse_claimgate_bundle, public_level_name
from codontrace.genesis.claim_gate import (
    ClaimRequest,
    ScientificClaimGate,
    evaluate_strong_claim_ladder,
    public_level_for_internal,
)

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "claimgate"


def _load(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def test_public_ladder_names_match_claims_section_5() -> None:
    assert public_level_name(0) == "software_capability"
    assert public_level_name(1) == "runtime_observation"
    assert public_level_name(2) == "candidate_evidence"
    assert public_level_name(3) == "mechanism_support"
    assert public_level_name(4) == "replicated_effect"
    assert public_level_name(5) == "publication_grade"


def test_internal_nine_rungs_map_to_public_levels() -> None:
    assert public_level_for_internal("metadata_only") == 0
    assert public_level_for_internal("instrumented_runtime") == 1
    assert public_level_for_internal("pilot_supported") == 1
    assert public_level_for_internal("control_supported") == 2
    assert public_level_for_internal("ablation_supported") == 3
    assert public_level_for_internal("multi_seed_supported") == 4
    assert public_level_for_internal("heldout_supported") == 4
    assert public_level_for_internal("intervention_supported") == 3
    assert public_level_for_internal("claim_ready_research_alpha") == 5


def test_strong_claim_ladder_exposes_public_level_without_changing_digest() -> None:
    first = evaluate_strong_claim_ladder(
        "digital_evolution_claim",
        {"schema_version": True, "artifact_digest": True, "runtime_records": True},
    )
    second = evaluate_strong_claim_ladder(
        "digital_evolution_claim",
        {"runtime_records": True, "artifact_digest": True, "schema_version": True},
    )
    assert first.achieved_level == "instrumented_runtime"
    assert first.public_level == 1
    assert first.digest == second.digest
    assert "public_level" not in first.to_dict()


def test_software_only_bundle_stays_at_public_level_0() -> None:
    report = audit_bundle(_load("level0_software_only.json"))
    assert report.achieved_level == 0
    assert report.public_name == "software_capability"
    assert "seed_list" in report.missing_for_next
    assert report.digest == audit_bundle(_load("level0_software_only.json")).digest


def test_synthetic_difference_reaches_candidate_evidence_not_publication() -> None:
    report = audit_bundle(_load("level2_difference.json"))
    assert report.achieved_level == 2
    assert report.public_name == "candidate_evidence"
    assert "replay_audit" in report.missing_for_next
    assert "negative_control" in report.missing_for_next


def test_null_comparison_is_runtime_observation_not_mechanism_support() -> None:
    payload = _load("level2_difference.json")
    payload["comparisons"][0]["effect_size"] = 0.0
    payload["comparisons"][0]["ci_low"] = 0.0
    payload["comparisons"][0]["ci_high"] = 0.0
    payload["comparisons"][0]["p"] = 1.0
    report = audit_bundle(payload)
    assert report.achieved_level == 1
    assert report.public_name == "runtime_observation"
    assert "consistent_measured_difference" in report.missing_for_next
    assert "interpretable_null_is_valid_not_mechanism_support" in report.warnings


def test_level_4_requires_ci_and_at_least_16_seeds() -> None:
    payload = _load("level2_difference.json")
    payload["arms"].append({"name": "off_gate", "role": "mechanism_ablation", "n": 3})
    payload["arms"].append({"name": "shuffled", "role": "negative_control", "n": 3})
    payload["replay"] = {
        "verified": True,
        "digests": ["dddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd"],
    }
    report = audit_bundle(payload)
    assert report.achieved_level == 3
    assert "seed_count_ge_16" in report.missing_for_next
    payload["seeds"] = list(range(16))
    payload["arms"][0]["n"] = 16
    report = audit_bundle(payload)
    assert report.achieved_level == 4
    assert "archived_artifact_or_doi" in report.missing_for_next
    payload["doi"] = "10.5281/zenodo.20337435"
    report = audit_bundle(payload)
    assert report.achieved_level == 4
    payload["doi"] = "10.5281/zenodo.99999999"
    report = audit_bundle(payload)
    assert report.achieved_level == 5


def test_forbidden_aliases_stay_blocked_and_do_not_promote() -> None:
    gate = ScientificClaimGate()
    for label in (
        "collective_intelligence",
        "agi",
        "tokyo_type1_passed",
        "avida_replacement",
        "open_ended_intelligence",
    ):
        assert gate.decide(ClaimRequest(label, {})).allowed is False
    payload = _load("level2_difference.json")
    payload["tokyo_type1_passed"] = True
    report = audit_bundle(payload)
    assert report.achieved_level == 1
    assert any(item.startswith("forbidden_alias_present_no_promotion") for item in report.warnings)
    assert "metrics_do_not_auto_grant_oee_or_tokyo_type1" in report.warnings


def test_parse_roundtrip_is_deterministic() -> None:
    raw = _load("level2_difference.json")
    bundle = parse_claimgate_bundle(raw)
    again = parse_claimgate_bundle(bundle.to_dict())
    assert bundle.digest() == again.digest()
    assert audit_bundle(bundle).digest == audit_bundle(again).digest
