import pytest

from codontrace.codon import CodonTable
from codontrace.errors import ConfigurationError
from codontrace.genesis.adf_runtime import (
    ADFMacroDefinition,
    ADFMacroRegistry,
    build_adf_usefulness_control_report,
)
from codontrace.genesis.artifacts import (
    PHASE2_MANIFEST_FIELDS,
    manifest_from_parts,
    validate_phase2_manifest_fields,
)
from codontrace.genesis.contribution_ledger import build_micro_ablation_attribution_record
from codontrace.genesis.engine import GenesisEngine, GenesisEngineConfig, GenesisExperimentSpec
from codontrace.genesis.structural_mutation import StructuralMutationConfig
from codontrace.genesis.translation_profile import (
    TranslationPolicy,
    TranslationWeight,
    build_translation_profile,
)


def _manifest_with(runtime_hashes, protocol_statuses):
    return manifest_from_parts(
        run_id="r",
        seed=1,
        config={},
        codon_table_hash="ct",
        genome_spec_hash="gs",
        initial_population_hash="pop",
        tick_count=0,
        replay_digest="replay",
        runtime_hashes=runtime_hashes,
        protocol_statuses=protocol_statuses,
    )


def test_phase2_manifest_rejects_measured_status_without_hash():
    manifest = _manifest_with(
        {},
        {f"phase2.{name}.status": "measured" for name in PHASE2_MANIFEST_FIELDS},
    )

    result = validate_phase2_manifest_fields(manifest)

    assert not result.passed
    assert "genome_program_digest" in result.missing_hashes


def test_phase2_manifest_rejects_placeholder_hash_for_measured_status():
    manifest = _manifest_with(
        {name: "placeholder" for name in PHASE2_MANIFEST_FIELDS},
        {f"phase2.{name}.status": "measured" for name in PHASE2_MANIFEST_FIELDS},
    )

    result = validate_phase2_manifest_fields(manifest)

    assert not result.passed
    assert "genome_program_digest" in result.placeholder_hashes


def test_runtime_claim_gate_digest_matches_manifest_claim_gate_digest():
    result = GenesisEngine.from_spec(GenesisExperimentSpec(tick_count=1, seed=123)).run_ticks()

    assert result.manifest.claim_gate_decision_digest
    assert (
        result.manifest.runtime_hashes["claim_gate_decision_digest"]
        == result.manifest.claim_gate_decision_digest
    )
    assert (
        result.manifest.runtime_hashes["phase2_claim_decision_digest"]
        == result.manifest.claim_gate_decision_digest
    )


def test_engine_built_semantic_proxy_report_marks_status_active():
    profile = build_translation_profile(
        "profile-a",
        "spec",
        (TranslationWeight("000", "EMIT_NEXUS", 1.0, 1, 0),),
    )
    result = GenesisEngine.from_spec(
        GenesisExperimentSpec(
            genome_bits=("000",),
            tick_count=1,
            initial_runtime_atp=10,
            translation_profile=profile,
            translation_policy=TranslationPolicy(),
            enable_execution_source=True,
        )
    ).run_ticks()

    assert result.manifest.runtime_hashes["semantic_proxy_report_digest"]
    assert result.manifest.protocol_statuses[
        "phase2.semantic_proxy_report_digest.status"
    ] in {"measured", "provisional"}
    assert result.manifest.protocol_statuses["translation_protocol_executed"] == "true"
    assert result.manifest.protocol_statuses["semantic_proxy_status"] == "active"


@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf")])
def test_adf_usefulness_report_rejects_non_finite_values(value):
    registry = ADFMacroRegistry().register(ADFMacroDefinition("ADF_ONE", ("WAIT",)))
    registry, _ = registry.expand("ADF_ONE")
    with pytest.raises(ConfigurationError):
        build_adf_usefulness_control_report(
            registry,
            "ADF_ONE",
            task_delta=value,
            null_macro_delta=0.0,
            permutation_control_delta=0.0,
        )


@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf")])
def test_structural_mutation_config_rejects_non_finite_rates(value):
    with pytest.raises(ConfigurationError):
        StructuralMutationConfig(codon_insert_rate=value)


@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf")])
def test_micro_ablation_rejects_non_finite_metrics(value):
    with pytest.raises(ConfigurationError):
        build_micro_ablation_attribution_record(
            "target",
            "macro",
            original_metric=value,
            ablated_metric=0.0,
            contribution_ledger_digest="digest",
        )


def test_single_action_adf_macro_without_compression_is_not_claim_eligible():
    registry = ADFMacroRegistry().register(ADFMacroDefinition("ADF_ONE", ("WAIT",)))
    registry, _ = registry.expand("ADF_ONE")
    registry, _ = registry.expand("ADF_ONE")

    report = build_adf_usefulness_control_report(
        registry,
        "ADF_ONE",
        task_delta=10.0,
        null_macro_delta=0.0,
        permutation_control_delta=0.0,
        source_map_digest="source",
    )

    assert report.compression_ratio == 0.0
    assert not report.claim_eligible


def test_multi_action_adf_macro_with_controls_source_map_and_reuse_can_be_claim_eligible():
    registry = ADFMacroRegistry().register(
        ADFMacroDefinition("ADF_TWO", ("SENSE_FOOD", "MOVE_TOWARD", "EAT_LUMEN"))
    )
    registry, _ = registry.expand("ADF_TWO")
    registry, _ = registry.expand("ADF_TWO")

    report = build_adf_usefulness_control_report(
        registry,
        "ADF_TWO",
        task_delta=10.0,
        runtime_cost_delta=1.0,
        learning_cost_delta=1.0,
        null_macro_delta=0.0,
        permutation_control_delta=0.0,
        source_map_digest="source",
    )

    assert report.compression_ratio > 0.0
    assert report.claim_eligible


@pytest.mark.parametrize(
    "claim_label",
    [
        "variable_genome_runtime_supported",
        "adf_macro_usefulness_supported",
        "contribution_attribution_supported",
        "event_graph_evidence_supported",
        "intervention_supported_causal_evidence",
        "discovery_witness_candidate",
        "social_partner_generalization_supported",
        "oee_candidate_evidence_supported",
        "adaptive_gp_map_proxy",
    ],
)
def test_engine_level_phase2_claims_reject_metadata_only_or_missing_evidence(claim_label):
    result = GenesisEngine.from_spec(
        GenesisExperimentSpec(
            tick_count=0,
            engine_config=GenesisEngineConfig(claim_level=claim_label),
            metadata={"digest_pointer_only": "not_evidence"},
        )
    ).run_ticks()

    assert result.manifest.claim_gate_decision is not None
    assert not result.manifest.claim_gate_allowed
    assert result.manifest.claim_level != claim_label


def test_engine_level_event_graph_claim_uses_runtime_manifest_status_and_replay_digest():
    first = GenesisEngine.from_spec(
        GenesisExperimentSpec(
            genome_bits=("000",),
            seed=77,
            tick_count=1,
            engine_config=GenesisEngineConfig(claim_level="event_graph_evidence_supported"),
            codon_table=CodonTable.genesis_v0(),
        )
    ).run_ticks()
    second = GenesisEngine.from_spec(
        GenesisExperimentSpec(
            genome_bits=("000",),
            seed=77,
            tick_count=1,
            engine_config=GenesisEngineConfig(claim_level="event_graph_evidence_supported"),
            codon_table=CodonTable.genesis_v0(),
        )
    ).run_ticks()

    assert first.manifest.claim_gate_decision is not None
    assert first.manifest.claim_gate_allowed
    assert first.manifest.runtime_hashes["event_graph_digest"] == second.manifest.runtime_hashes[
        "event_graph_digest"
    ]
    assert first.manifest.protocol_statuses["phase2.event_graph_digest.status"] == "measured"


def test_engine_level_adaptive_gp_map_proxy_uses_semantic_report_evidence_path():
    profile = build_translation_profile(
        "profile-b",
        "spec",
        (TranslationWeight("000", "EMIT_NEXUS", 1.0, 1, 0),),
    )
    result = GenesisEngine.from_spec(
        GenesisExperimentSpec(
            genome_bits=("000",),
            tick_count=1,
            initial_runtime_atp=10,
            translation_profile=profile,
            translation_policy=TranslationPolicy(),
            enable_execution_source=True,
            engine_config=GenesisEngineConfig(claim_level="adaptive_gp_map_proxy"),
        )
    ).run_ticks()

    assert result.manifest.claim_gate_decision is not None
    assert result.manifest.claim_gate_allowed
    assert result.manifest.claim_level == "adaptive_gp_map_proxy"
    assert result.manifest.protocol_statuses["semantic_proxy_status"] == "active"

from codontrace.genesis.evidence_validation import EvidenceValidationContext


def _engine_context(flags):
    return EvidenceValidationContext(
        validated_digests=("sha256:validated-phase2-artifact",),
        replay_capture_digests=("sha256:validated-phase2-replay",),
        validated_evidence_flags=tuple(flags),
    )


_PHASE2_ENGINE_POSITIVE_CASES = {
    "variable_genome_runtime_supported": {
        "flags": (),
        "kwargs": {"structural_mutation_config": StructuralMutationConfig(codon_insert_rate=0.1)},
    },
    "adf_macro_usefulness_supported": {
        "flags": ("adf_usefulness_report_digest", "null_control", "permutation_control"),
        "kwargs": {
            "adf_macro_registry": ADFMacroRegistry().register(
                ADFMacroDefinition("ADF_POS", ("SENSE_FOOD", "MOVE_TOWARD", "EAT_LUMEN"))
            ),
        },
    },
    "contribution_attribution_supported": {
        "flags": ("contribution_ledger", "execution_records", "micro_ablation_status"),
        "kwargs": {"enable_execution_source": True},
    },
    "event_graph_evidence_supported": {
        "flags": (),
        "kwargs": {},
    },
    "intervention_supported_causal_evidence": {
        "flags": (
            "intervention_result_artifact",
            "intervention_result_digest",
            "baseline_digest",
            "treatment_digest",
            "intervention_protocol_digest",
            "effect_size",
            "paired_seed_protocol_digest",
            "claim_gate_decision_digest",
        ),
        "kwargs": {},
    },
    "discovery_witness_candidate": {
        "flags": (
            "candidate_detected",
            "d0_baseline",
            "shadow_run",
            "persistence",
            "discovery_witness_digest",
        ),
        "kwargs": {},
    },
    "social_partner_generalization_supported": {
        "flags": (
            "real_partner_event",
            "familiar_partner_protocol",
            "unfamiliar_partner_protocol",
            "heldout_protocol",
            "leakage_check",
            "social_generalization_digest",
        ),
        "kwargs": {},
    },
    "oee_candidate_evidence_supported": {
        "flags": (
            "oee_report_artifact",
            "oee_report_digest",
            "novelty_metric",
            "learnability_metric",
            "persistence_window_observed",
            "ablation_result",
            "multi_seed_protocol",
            "confidence_intervals_present",
            "claim_gate_decision_digest",
        ),
        "kwargs": {},
    },
}


@pytest.mark.parametrize("claim_label", sorted(_PHASE2_ENGINE_POSITIVE_CASES))
def test_engine_level_phase2_claims_accept_validated_artifact_contexts(claim_label):
    case = _PHASE2_ENGINE_POSITIVE_CASES[claim_label]
    result = GenesisEngine.from_spec(
        GenesisExperimentSpec(
            genome_bits=("000",),
            tick_count=1,
            seed=321,
            codon_table=CodonTable.genesis_v0(),
            evidence_validation_context=_engine_context(case["flags"]),
            engine_config=GenesisEngineConfig(claim_level=claim_label),
            **case["kwargs"],
        )
    ).run_ticks()

    assert result.manifest.claim_gate_decision is not None
    assert result.manifest.claim_gate_allowed
    assert result.manifest.claim_level == claim_label
    assert result.manifest.runtime_hashes["claim_gate_decision_digest"] == result.manifest.claim_gate_decision_digest
    assert result.manifest.runtime_hashes["phase2_claim_decision_digest"] == result.manifest.claim_gate_decision_digest
    assert result.validate_consistency(strict=True).passed


def test_validated_evidence_flags_do_not_unlock_claim_without_artifact_and_replay_digests():
    context = EvidenceValidationContext(
        validated_evidence_flags=(
            "candidate_detected",
            "d0_baseline",
            "shadow_run",
            "persistence",
            "discovery_witness_digest",
            "artifact_digest",
            "replay_verification",
        )
    )
    result = GenesisEngine.from_spec(
        GenesisExperimentSpec(
            genome_bits=("000",),
            tick_count=1,
            evidence_validation_context=context,
            engine_config=GenesisEngineConfig(claim_level="discovery_witness_candidate"),
        )
    ).run_ticks()

    assert not result.manifest.claim_gate_allowed
    assert result.manifest.claim_level != "discovery_witness_candidate"
