from __future__ import annotations

import tarfile
import zipfile
from collections.abc import Callable
from pathlib import Path

import pytest

from codontrace.actions import ActionContext, ActionResult, default_action_registry
from codontrace.errors import ConfigurationError
from codontrace.genesis.adf_runtime import MacroPruningDecision, MacroUtilityRecord
from codontrace.genesis.artifacts import compute_source_digest
from codontrace.genesis.causal_validation import InterventionResult, PredictiveProbeResult
from codontrace.genesis.claim_gate import ClaimRequest, ScientificClaimGate
from codontrace.genesis.engine import GenesisEngine, GenesisEngineConfig, GenesisExperimentSpec
from codontrace.genesis.innovation_protection import InnovationRecord
from codontrace.genesis.qd_search import (
    QDCandidate,
    QDCandidateSearchRunner,
    QDSchedulerState,
    QDSearchConfig,
)
from codontrace.genesis.release_readiness import assert_artifact_has_no_cache_files
from codontrace.genesis.rules import RuleProposal, RuleProposalSource, RuleSetDiff
from codontrace.genesis.statistical_protocol import validate_statistical_claim_inputs
from codontrace.genesis.statistical_report import build_statistical_report
from codontrace.genesis.structural_mutation import StructuralMutationRecord
from codontrace.genesis.translation_profile import TranslationProfile, TranslationWeight


def test_top_level_all_symbols_importable() -> None:
    import codontrace

    missing = [name for name in codontrace.__all__ if not hasattr(codontrace, name)]
    assert missing == []


def test_pyproject_has_single_build_backend_configuration() -> None:
    text = Path("pyproject.toml").read_text(encoding="utf-8")
    assert 'build-backend = "setuptools.build_meta"' in text
    assert "[tool.hatch" not in text


def test_built_artifact_hygiene_checks_zip_and_tarball(tmp_path: Path) -> None:
    clean_zip = tmp_path / "clean.zip"
    with zipfile.ZipFile(clean_zip, "w") as archive:
        archive.writestr("codontrace/__init__.py", "")
    assert_artifact_has_no_cache_files(clean_zip)

    dirty_tar = tmp_path / "dirty.tar.gz"
    dirty_file = tmp_path / "pkg" / "__pycache__" / "x.pyc"
    dirty_file.parent.mkdir(parents=True)
    dirty_file.write_bytes(b"cache")
    with tarfile.open(dirty_tar, "w:gz") as archive:
        archive.add(dirty_file, arcname="pkg/__pycache__/x.pyc")
    with pytest.raises(ConfigurationError):
        assert_artifact_has_no_cache_files(dirty_tar)


def test_default_engine_claim_is_whitelisted_and_legacy_alias_maps() -> None:
    result = GenesisEngine.from_spec(GenesisExperimentSpec(tick_count=0)).run_ticks()
    assert result.manifest.claim_level == "foundation_engine"
    alias = ScientificClaimGate().decide(ClaimRequest("research_alpha_foundation_engine", {}))
    assert alias.allowed
    assert alias.final_claim == "foundation_engine"


def test_replay_critical_objects_reject_direct_bad_digest() -> None:
    with pytest.raises(ConfigurationError):
        TranslationProfile(
            "p",
            "spec",
            (TranslationWeight("000", "WAIT", 1.0, 1, 0),),
            "translation_profile_v1",
            digest="bad",
        )
    with pytest.raises(ConfigurationError):
        StructuralMutationRecord("m", "p", "c", "insert", 0, None, None, "rng", "b", "a", "bad")
    with pytest.raises(ConfigurationError):
        PredictiveProbeResult(
            "x",
            "y",
            "permutation",
            0.1,
            None,
            1,
            (1,),
            (),
            None,
            10,
            "not_predictive",
            digest="bad",
        )
    with pytest.raises(ConfigurationError):
        InterventionResult("s", "b", "t", 0.1, (0.0, 0.2), 8, digest="bad")
    with pytest.raises(ConfigurationError):
        InnovationRecord("i", "kind", 0, 1, "lineage", None, "protected", digest="bad")
    with pytest.raises(ConfigurationError):
        MacroUtilityRecord("m", 1, 1.0, 1, 0.1, None, "provisional", digest="bad")
    with pytest.raises(ConfigurationError):
        MacroPruningDecision("m", "low", 1, "provisional", None, None, "keep", digest="bad")


def test_metadata_only_cannot_grant_intervention_or_oee_claims() -> None:
    gate = ScientificClaimGate()
    intervention = gate.decide(
        ClaimRequest(
            "intervention_supported",
            {"intervention_result": True, "paired_seeds": True, "protocol_executed": True},
        )
    )
    assert not intervention.allowed
    assert intervention.final_claim == "event_association_only"
    oee = gate.decide(
        ClaimRequest(
            "oee_candidate",
            {
                "oee_metrics": True,
                "shadow_run": True,
                "min_seed_threshold": True,
                "persistence_window": True,
                "confidence_intervals": True,
                "protocol_executed": True,
            },
        )
    )
    assert not oee.allowed
    assert oee.final_claim == "oee_measurement_only"


def test_validated_intervention_and_oee_artifacts_can_grant_claims() -> None:
    gate = ScientificClaimGate()
    intervention = gate.decide(
        ClaimRequest(
            "intervention_supported",
            {
                "intervention_result_artifact": True,
                "intervention_result_digest": True,
                "baseline_digest": True,
                "treatment_digest": True,
                "intervention_protocol_digest": True,
                "effect_size": True,
                "paired_seed_protocol_digest": True,
                "claim_gate_decision_digest": True,
            },
        )
    )
    assert intervention.allowed
    oee = gate.decide(
        ClaimRequest(
            "oee_candidate",
            {
                "oee_report_artifact": True,
                "oee_report_digest": True,
                "oee_protocol_executed": True,
                "shadow_run_present": True,
                "min_seed_threshold_met": True,
                "persistence_window_observed": True,
                "confidence_intervals_present": True,
                "stagnation_diversity_status_recorded": True,
                "claim_gate_decision_digest": True,
            },
        )
    )
    assert oee.allowed


def test_default_run_has_split_protocol_fields_false() -> None:
    result = GenesisEngine.from_spec(GenesisExperimentSpec(tick_count=0)).run_ticks()
    statuses = result.manifest.protocol_statuses
    assert result.manifest.scientific_protocol_executed is False
    assert statuses["predictive_probe_executed"] == "false"
    assert statuses["intervention_protocol_executed"] == "false"
    assert statuses["oee_protocol_executed"] == "false"
    assert statuses["translation_protocol_executed"] == "false"
    assert statuses["innovation_protocol_active"] == "false"
    assert statuses["scientific_validation_protocol_executed"] == "false"


def test_engine_manifest_source_digest_tracks_source_and_ignores_generated_metadata(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    src = tmp_path / "src" / "codontrace"
    src.mkdir(parents=True)
    tracked = src / "tracked.py"
    tracked.write_text("x = 1\n")
    monkeypatch.setenv("CODONTRACE_SOURCE_ROOT", str(tmp_path))
    first = (
        GenesisEngine.from_spec(GenesisExperimentSpec(tick_count=0))
        .run_ticks()
        .manifest.source_digest
    )
    egg = tmp_path / "src" / "codontrace.egg-info"
    egg.mkdir()
    (egg / "PKG-INFO").write_text("generated")
    assert (
        GenesisEngine.from_spec(GenesisExperimentSpec(tick_count=0))
        .run_ticks()
        .manifest.source_digest
        == first
    )
    tracked.write_text("x = 2\n")
    assert (
        GenesisEngine.from_spec(GenesisExperimentSpec(tick_count=0))
        .run_ticks()
        .manifest.source_digest
        != first
    )
    assert compute_source_digest(str(tmp_path)) != ""


def test_qd_candidate_runner_and_active_scheduler_digest_include_feedback_state() -> None:
    parent = QDCandidate.from_genome_bits(
        "000111",
        genome_program_digest="program",
        macro_registry_digest="macro",
        translation_profile_digest="translation",
    )
    runner = QDCandidateSearchRunner(
        QDSearchConfig(generations=1, offspring_per_generation=1),
        lambda candidate: (
            1.0,
            {
                "unique_positions": float(len(candidate.genome_bits or "")),
                "energy_efficiency": 1.0,
            },
        ),
    )
    result = runner.run((parent,))
    assert result.steps[0].parent_selections
    state_a = QDSchedulerState("a", "e", "s", 1, "reporting_only", None, "rng")
    state_b = QDSchedulerState("a", "e", "s", 1, "archive_parent_feedback", "parent", "rng")
    assert state_a.digest != state_b.digest


def test_custom_closure_handler_identity_changes_and_is_non_replayable() -> None:
    def make_handler(reason: str) -> Callable[[ActionContext], ActionResult]:
        def handler(ctx: ActionContext) -> ActionResult:
            return ActionResult.executed(reason=reason, position_after=ctx.position)

        return handler

    spec_a = GenesisExperimentSpec(
        action_registry=default_action_registry().extend("CUSTOM_A", make_handler("a")),
        tick_count=0,
    )
    spec_b = GenesisExperimentSpec(
        action_registry=default_action_registry().extend("CUSTOM_A", make_handler("b")),
        tick_count=0,
    )
    assert spec_a.to_dict()["action_registry_hash"] != spec_b.to_dict()["action_registry_hash"]
    result = GenesisEngine.from_spec(
        GenesisExperimentSpec(
            action_registry=default_action_registry().extend("CUSTOM_A", make_handler("a")),
            engine_config=GenesisEngineConfig(claim_level="experimental_engine"),
            tick_count=0,
        )
    ).run_ticks()
    assert result.manifest.claim_gate_allowed is False


def test_statistical_claims_are_policy_driven_not_pvalue_only() -> None:
    report = build_statistical_report({"fitness": list(range(7))})
    assert report.claim_status == "descriptive_only"
    assert report.protocol_digest
    assert report.statistical_policy_version == "statistical_test_policy_v1"
    ok, reason = validate_statistical_claim_inputs(
        p_value=0.01,
        effect_size=None,
        confidence_interval=None,
        replay_artifact_digest="replay",
        protocol_digest="protocol",
        claim_gate_decision_digest="claim",
    )
    assert not ok
    assert reason == "missing_effect_size"


def test_rule_proposal_and_diff_are_deep_immutable() -> None:
    nested = {"target": "metadata", "key": "x", "value": {"inner": [1, 2]}}
    proposal = RuleProposal(
        "p", RuleProposalSource.HUMAN, RuleSetDiff(add=(nested,)), metadata={"m": {"n": [1]}}
    )
    before = proposal.digest()
    nested["value"] = {"inner": [9]}
    assert proposal.digest() == before
    with pytest.raises(TypeError):
        proposal.diff.add[0]["key"] = "changed"  # type: ignore[index]
    with pytest.raises(TypeError):
        proposal.metadata["m"] = "changed"  # type: ignore[index]
