from codontrace.codon import Codon, CodonTable
from codontrace.genesis.adf_runtime import ADFMacroDefinition, ADFMacroRegistry
from codontrace.genesis.artifacts import validate_phase2_manifest_fields
from codontrace.genesis.engine import GenesisEngine, GenesisExperimentSpec
from codontrace.genesis.liveness import AliveGateConfig
from codontrace.genesis.organism import GenesisOrganism
from codontrace.genesis.population import (
    FitnessConfig,
    MutationConfig,
    PopulationConfigs,
    ReproductionConfig,
)
from codontrace.genesis.ribosome import Ribosome
from codontrace.genesis.selection import EvolutionConfig
from codontrace.genesis.structural_mutation import StructuralMutationConfig
from codontrace.genesis.translation_profile import (
    TranslationPolicy,
    TranslationWeight,
    build_translation_profile,
)
from codontrace.specs import GenomeSpec
from codontrace.trace import Trace
from codontrace.world import World2D


def test_population_reproduction_uses_structural_mutation_config_runtime_path():
    configs = PopulationConfigs(
        reproduction=ReproductionConfig(
            min_runtime_atp=1,
            parent_atp_cost=0,
            offspring_atp_fraction=0.1,
            max_population=4,
        ),
        mutation=MutationConfig(bit_flip_rate=0.0),
        structural_mutation=StructuralMutationConfig(
            bit_flip_rate=0.0,
            codon_insert_rate=1.0,
            codon_delete_rate=0.0,
            codon_duplicate_rate=0.0,
            codon_invert_rate=0.0,
            codon_translocate_rate=0.0,
        ),
        fitness=FitnessConfig(),
        alive_gate=AliveGateConfig(
            min_ticks=1,
            min_executed_actions=0,
            max_blocked_ratio=1.0,
            require_positive_runtime_atp=False,
        ),
        ticks_per_generation=1,
        evolution=EvolutionConfig(max_population=4),
    )
    result = GenesisEngine.from_spec(
        GenesisExperimentSpec(
            genome_bits=("111",),
            tick_count=1,
            initial_runtime_atp=100,
            initial_learning_atp=10,
            population_configs=configs,
            enable_execution_source=True,
        )
    ).run_ticks()

    generation = result.ticks[0].generation_result
    assert generation.births == 1
    assert generation.after_count == 2
    event = generation.traces[0].events[0]
    assert event.world_delta["reproduction_succeeded"] is True
    assert event.world_delta["mutation_digest"] is not None
    assert event.world_delta["child_genome_digest"] is not None


def test_organism_step_expands_adf_macro_runtime_and_preserves_source_map():
    table = CodonTable.genesis_v0().extend(Codon("1000", "ADF_1000", 0.0, "test macro"))
    ribosome = Ribosome(codon_table=table, codon_table_version="test_adf")
    registry = ADFMacroRegistry().register(
        ADFMacroDefinition(
            macro_id="ADF_1000",
            primitive_actions=("WAIT",),
            body_codons=("000",),
        )
    )
    organism = GenesisOrganism.from_bits(
        "org-adf",
        "1000",
        ribosome=ribosome,
        initial_runtime_atp=10,
        adf_macro_registry=registry,
        execution_source_enabled=True,
    )
    trace = Trace()
    event = organism.step(World2D(2, 2), trace)

    assert event.action == "WAIT"
    assert event.world_delta["adf_expanded_actions"] == ["WAIT"]
    assert event.world_delta["adf_expansion_digest"] is not None
    record = event.world_delta["codon_execution_record"]
    assert record["source"]["macro_id"] == "ADF_1000"
    assert organism.adf_macro_registry is not None
    assert organism.adf_macro_registry.usage_counts["ADF_1000"] == 1


def test_translation_profile_changes_runtime_decoding_and_manifest_hash():
    profile = build_translation_profile(
        "profile-a",
        GenomeSpec.binary3().digest(),
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
    event = result.ticks[0].generation_result.traces[0].events[0]

    assert event.action == "EMIT_NEXUS"
    assert event.world_delta["base_action"] == "WAIT"
    assert event.world_delta["translation_profile_digest"] == profile.digest
    assert result.manifest.runtime_hashes["translation_profile_hash"] == profile.digest


def test_engine_exports_contribution_ledgers_and_complete_phase2_manifest_hashes():
    result = GenesisEngine.from_spec(
        GenesisExperimentSpec(
            genome_bits=("000",),
            tick_count=1,
            initial_runtime_atp=10,
            enable_execution_source=True,
        )
    ).run_ticks()

    assert result.evidence_pack.contribution_ledgers
    assert result.evidence_pack.contribution_ledgers[0]["records"]
    validation = validate_phase2_manifest_fields(result.manifest)
    assert validation.passed, validation.to_dict()
    for key in (
        "genome_program_digest",
        "structural_mutation_digest",
        "macro_registry_digest",
        "contribution_ledger_digest",
        "event_graph_digest",
        "translation_profile_hash",
        "semantic_proxy_report_digest",
    ):
        assert result.manifest.runtime_hashes[key]
