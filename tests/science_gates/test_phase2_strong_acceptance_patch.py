from codontrace.codon import CodonTable
from codontrace.genesis.adf_runtime import (
    ADFExecutionPolicy,
    ADFMacroDefinition,
    ADFMacroRegistry,
    build_adf_usefulness_control_report,
)
from codontrace.genesis.artifacts import PHASE2_MANIFEST_FIELDS, validate_phase2_manifest_fields
from codontrace.genesis.claim_gate import ClaimRequest, ScientificClaimGate
from codontrace.genesis.contribution_ledger import (
    build_contribution_ledger,
    build_micro_ablation_attribution_record,
    contribution_from_execution_record,
)
from codontrace.genesis.engine import GenesisEngine, GenesisExperimentSpec
from codontrace.genesis.ribosome import BrainTokenSource, CodonExecutionRecord
from codontrace.genesis.structural_mutation import (
    StructuralMutationConfig,
    build_genome_program,
    mutate_genome_program,
    structural_mutation_record_from_dict,
)
from codontrace.rng import RNGManager


def test_phase2_structural_mutation_record_has_v2_runtime_provenance():
    parent = build_genome_program("000001", codon_width=3)
    child, record = mutate_genome_program(
        parent,
        StructuralMutationConfig(codon_insert_rate=1.0),
        RNGManager(seed=13, namespace="phase2_mutation"),
        kind="insert",
        payload_codon="111",
    )

    assert child.structural_mutation_digest == record.digest
    assert record.schema_version == "structural_mutation_record_v2"
    assert record.mutation_kind == "insert"
    assert record.codon_width == 3
    assert record.token_range is not None
    assert record.before_tokens_digest != record.after_tokens_digest
    assert record.validity_status == "valid"
    assert record.effect_status == "lineage_recorded"
    assert structural_mutation_record_from_dict(record.to_dict()).digest == record.digest


def test_phase2_adf_usefulness_requires_controls_not_compression_alone():
    registry = ADFMacroRegistry().register(
        ADFMacroDefinition(
            macro_id="ADF_FORAGE",
            primitive_actions=("MOVE_EAST", "EAT_LUMEN"),
            body_codons=("000", "001"),
        )
    )
    registry, expansion = registry.expand("ADF_FORAGE", ADFExecutionPolicy())
    assert expansion.executed
    registry, _ = registry.expand("ADF_FORAGE", ADFExecutionPolicy())

    weak = build_adf_usefulness_control_report(
        registry,
        "ADF_FORAGE",
        task_delta=0.1,
        runtime_cost_delta=0.0,
        learning_cost_delta=0.0,
        null_macro_delta=1.0,
        permutation_control_delta=1.0,
        source_map_digest=expansion.digest(),
    )
    strong = build_adf_usefulness_control_report(
        registry,
        "ADF_FORAGE",
        task_delta=3.0,
        runtime_cost_delta=0.2,
        learning_cost_delta=0.1,
        null_macro_delta=0.0,
        permutation_control_delta=0.1,
        source_map_digest=expansion.digest(),
    )

    assert weak.utility_status == "provisional"
    assert not weak.claim_eligible
    assert strong.utility_status == "control_supported"
    assert strong.claim_eligible
    assert strong.digest != weak.digest


def _execution_record() -> CodonExecutionRecord:
    return CodonExecutionRecord(
        "org",
        1,
        0,
        BrainTokenSource(0, "000"),
        "EAT_LUMEN",
        "executed",
        1.0,
        4.0,
        "ctx",
        "trace-0",
    )


def test_phase2_micro_ablation_attribution_not_run_does_not_claim_support():
    contribution = contribution_from_execution_record(_execution_record(), generation=1)
    ledger = build_contribution_ledger("org", 1, (contribution,))
    not_run = build_micro_ablation_attribution_record(
        "codon:0", "codon", contribution_ledger_digest=ledger.digest
    )
    measured = build_micro_ablation_attribution_record(
        "codon:0",
        "codon",
        original_metric=5.0,
        ablated_metric=2.0,
        contribution_ledger_digest=ledger.digest,
    )

    assert not_run.status == "not_run"
    assert not_run.confidence_status == "not_run"
    assert measured.status == "measured"
    assert measured.confidence_status == "ablation_supported"
    assert measured.micro_ablation_delta == 3.0


def test_phase2_manifest_contains_directive_runtime_hash_surfaces():
    result = GenesisEngine.from_spec(
        GenesisExperimentSpec(
            genome_bits=("000",),
            tick_count=1,
            initial_runtime_atp=10,
            enable_execution_source=True,
            codon_table=CodonTable.genesis_v0(),
        )
    ).run_ticks()

    validation = validate_phase2_manifest_fields(result.manifest)
    assert validation.passed, validation.to_dict()
    for key in (
        "adf_macro_registry_digest",
        "adf_usefulness_report_digest",
        "translation_profile_digest",
        "causal_intervention_result_digest",
        "discovery_witness_digest",
        "benchmark_scenario_digest",
        "social_generalization_digest",
        "phase2_claim_decision_digest",
    ):
        assert key in PHASE2_MANIFEST_FIELDS
        assert result.manifest.runtime_hashes[key]


def test_phase2_claim_labels_are_evidence_gated_and_not_metadata_only():
    gate = ScientificClaimGate()
    rejected = gate.decide(
        ClaimRequest(
            "adf_macro_usefulness_supported",
            {
                "runtime_effect": True,
                "adf_macro_expansion": True,
                "adf_usefulness_report_digest": True,
                "artifact_digest": True,
                "replay_verification": True,
            },
        )
    )
    allowed = gate.decide(
        ClaimRequest(
            "adf_macro_usefulness_supported",
            {
                "runtime_effect": True,
                "adf_macro_expansion": True,
                "adf_usefulness_report_digest": True,
                "null_control": True,
                "permutation_control": True,
                "artifact_digest": True,
                "replay_verification": True,
            },
        )
    )

    assert not rejected.allowed
    assert any("null_control" in reason for reason in rejected.failed_reasons)
    assert allowed.allowed
    assert allowed.final_claim == "adf_macro_usefulness_supported"


def test_phase2_manifest_exports_status_for_every_hash_surface():
    from codontrace.genesis.artifacts import phase2_manifest_field_statuses

    result = GenesisEngine.from_spec(
        GenesisExperimentSpec(
            genome_bits=("000",),
            tick_count=1,
            initial_runtime_atp=10,
            enable_execution_source=True,
            codon_table=CodonTable.genesis_v0(),
        )
    ).run_ticks()
    statuses = phase2_manifest_field_statuses(result.manifest)

    assert set(statuses) == set(PHASE2_MANIFEST_FIELDS)
    assert statuses["genome_program_digest"] == "measured"
    assert statuses["event_graph_digest"] == "measured"
    assert statuses["adf_macro_registry_digest"] == "disabled_by_config"
    assert statuses["intervention_result_digest"] == "not_run"
    assert statuses["phase2_claim_decision_digest"] == "measured"
    assert validate_phase2_manifest_fields(result.manifest).passed


def test_phase2_public_exports_include_manifest_status_bridge():
    import codontrace.genesis as genesis

    assert hasattr(genesis, "phase2_manifest_field_statuses")
    assert hasattr(genesis, "validate_phase2_manifest_fields")
