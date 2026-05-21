from codontrace.codon import CodonTable
from codontrace.genesis import ActionWiringMatrix, export_action_wiring_matrix


def test_action_wiring_matrix_is_public_digestible_and_codon_reachable():
    matrix = export_action_wiring_matrix(codon_table=CodonTable.genesis_toolchain_v0())
    assert isinstance(matrix, ActionWiringMatrix)
    assert matrix.schema_version == "action_wiring_matrix_v1"
    assert matrix.registered_count >= matrix.codon_reachable_count >= 1
    rows = {row.action_name: row for row in matrix.records}
    assert rows["COLLECT_RESOURCE"].registered
    assert rows["COLLECT_RESOURCE"].codon_reachable
    assert rows["COLLECT_RESOURCE"].world_effecting
    assert rows["COLLECT_RESOURCE"].changes_energy
    assert "missing_resource" in rows["COLLECT_RESOURCE_OBJECT"].blocked_reasons
    assert rows["COPY_SELF"].claim_relevance == "reproduction_gate"
    assert matrix.digest() == export_action_wiring_matrix(codon_table=CodonTable.genesis_toolchain_v0()).digest()


def test_action_wiring_matrix_exposes_unregistered_codon_without_private_hack():
    from codontrace.codon import Codon, CodonTable
    from codontrace.specs import CodonTableSpec, GenomeSpec

    spec = GenomeSpec(codon_width=3, alphabet=("0", "1"), name="binary3")
    table_spec = CodonTableSpec(genome_spec=spec, table_name="custom", allow_partial_tail=False)
    table = CodonTable((Codon("000", "CUSTOM_ACTION", 1.0, spec=spec),), spec=table_spec)
    matrix = export_action_wiring_matrix(codon_table=table)
    row = {item.action_name: item for item in matrix.records}["CUSTOM_ACTION"]
    assert row.codon_reachable is True
    assert row.registered is False
    assert row.handler_stable_id == ""


def test_action_wiring_records_mark_contract_source_until_runtime_validated():
    matrix = export_action_wiring_matrix(codon_table=CodonTable.genesis_toolchain_v0())
    row = {item.action_name: item for item in matrix.records}["COLLECT_RESOURCE"]
    assert row.effect_source == "contract"
    assert row.runtime_validated is False
    assert row.runtime_validation_digest is None


def test_result_action_wiring_matrix_uses_actual_engine_codon_table():
    from codontrace.genesis import GenesisEngine, GenesisExperimentSpec

    result = GenesisEngine.from_spec(
        GenesisExperimentSpec(
            tick_count=0,
            codon_table=CodonTable.genesis_v0(),
        )
    ).run_ticks()
    reachable = {
        row.action_name
        for row in result.action_wiring_matrix.records
        if row.codon_reachable
    }
    assert "EMIT_NEXUS" in reachable
    assert "SENSE_FOOD" in reachable
    assert "CRAFT_ITEM" not in reachable


def test_result_action_wiring_matrix_uses_custom_action_registry_and_table():
    from codontrace.actions import default_action_registry, wait_handler
    from codontrace.codon import Codon, CodonTable
    from codontrace.genesis import GenesisEngine, GenesisExperimentSpec
    from codontrace.specs import CodonTableSpec, GenomeSpec

    spec = GenomeSpec(codon_width=3, alphabet=("0", "1"), name="binary3")
    table_spec = CodonTableSpec(genome_spec=spec, table_name="custom", allow_partial_tail=False)
    table = CodonTable((Codon("000", "CUSTOM_ACTION", 1.0, spec=spec),), spec=table_spec)
    registry = default_action_registry().extend("CUSTOM_ACTION", wait_handler)

    result = GenesisEngine.from_spec(
        GenesisExperimentSpec(
            tick_count=0,
            genome_bits=("000",),
            codon_table=table,
            action_registry=registry,
        )
    ).run_ticks()
    rows = {row.action_name: row for row in result.action_wiring_matrix.records}
    assert rows["CUSTOM_ACTION"].codon_reachable is True
    assert rows["CUSTOM_ACTION"].registered is True
    assert rows["CUSTOM_ACTION"].profile_name == "engine_run"
