from __future__ import annotations

import pytest

from codontrace.genesis.birth import (
    ADFInheritanceRecord,
    AIBirthInterventionRecord,
    ChildGenomeResult,
    InheritancePolicy,
    InterventionScope,
    LearningInheritanceRecord,
    SkillCompressionRecord,
    SkillInheritanceMode,
)
from codontrace.genesis.death import DeathMonitoringConfig
from codontrace.genesis.diagnostics import (
    DeathReasonRecord,
    EnergyAccountingRecord,
    ExportEnvelope,
    ReproductionAttemptRecord,
)
from codontrace.genesis.engine import GenesisEngine, GenesisEngineConfig, GenesisExperimentSpec
from codontrace.genesis.liveness import AliveGateResult
from codontrace.genesis.memory import EpisodicEvent, EpisodicMemory
from codontrace.genesis.organism import GenesisOrganism
from codontrace.genesis.population import (
    MutationConfig,
    PopulationConfigs,
    ReproductionConfig,
    reproduce,
)
from codontrace.trace import TraceEvent


def _capacity_block_result(*, death_monitoring: DeathMonitoringConfig | None = None):
    reproduction = ReproductionConfig(max_population=1, min_runtime_atp=1.0, parent_atp_cost=1.0)
    spec = GenesisExperimentSpec(
        genome_bits=("111",),
        seed=101,
        tick_count=3,
        population_max=1,
        initial_runtime_atp=100.0,
        population_configs=PopulationConfigs(
            reproduction=reproduction,
            mutation=MutationConfig(bit_flip_rate=0.0),
            death_monitoring=death_monitoring or DeathMonitoringConfig(),
            qd_mode="disabled",
        ),
        engine_config=GenesisEngineConfig(enable_qd=False),
    )
    return GenesisEngine.from_spec(spec).run_ticks()


def test_capacity_block_is_not_actual_death() -> None:
    result = _capacity_block_result()
    assert sum(tick.generation_result.deaths for tick in result.ticks) == 0
    assert len(result.ticks[-1].generation_result.population.organisms) == 1
    assert result.death_reason_records
    for record in result.death_reason_records:
        assert record.death_event is False
        assert record.actual_death_removed_from_population is False
        assert record.alive_gate_failure_event is True
        assert record.death_risk_event is True
    for record in result.energy_accounting_records:
        assert record.organism_dead_after_generation is False
        assert record.actual_death_removed_from_population is False
        assert record.alive_gate_failed_after_generation is True


def test_fatal_alive_reason_config_can_remove_organism() -> None:
    result = _capacity_block_result(
        death_monitoring=DeathMonitoringConfig(
            fatal_alive_reasons=("blocked_ratio_exceeded",),
        )
    )
    assert sum(tick.generation_result.deaths for tick in result.ticks) == 1
    assert len(result.ticks[-1].generation_result.population.organisms) == 0
    record = result.death_reason_records[0]
    assert record.actual_death_removed_from_population is True
    assert record.death_event is True
    assert record.fatal_policy_matched is True
    assert record.fatal_policy_reason == "fatal_alive_reason:blocked_ratio_exceeded"


def test_nonfatal_blocked_reproduction_capacity_summary() -> None:
    result = _capacity_block_result()
    attempts = result.reproduction_attempt_records
    assert attempts
    assert attempts[0].blocked_reason == "max_population_reached"
    assert attempts[0].child_created is False
    assert all(record.death_event is False for record in result.death_reason_records)


def test_death_monitoring_config_digest_is_in_records() -> None:
    config = DeathMonitoringConfig(fatal_alive_reasons=("negative_runtime_atp",))
    result = _capacity_block_result(death_monitoring=config)
    digests = {record.death_policy_digest for record in result.death_reason_records}
    assert digests == {config.digest()}


def test_diagnostic_records_reject_invalid_states() -> None:
    with pytest.raises(ValueError):
        EnergyAccountingRecord(
            organism_id="o",
            tick=-1,
            action="move",
            runtime_atp_before=1,
            runtime_atp_after=1,
            action_cost=-3,
            blocked=False,
            blocked_reason="should_not",
        )
    with pytest.raises(ValueError):
        DeathReasonRecord(
            organism_id="o",
            tick=0,
            death_event=False,
            actual_death_removed_from_population=False,
            death_reason="starvation",
            runtime_atp_after=-1,
            blocked_actions=-5,
            death_policy_digest="digest",
        )
    with pytest.raises(ValueError):
        ReproductionAttemptRecord(
            organism_id="o",
            tick=0,
            reproduction_action_attempted=True,
            reproduction_allowed=True,
            blocked_reason="none",
            runtime_atp=1,
            child_created=True,
            child_id=None,
            lineage_id=None,
        )
    with pytest.raises(ValueError):
        ExportEnvelope(schema_version="x", feature_status="garbage", status_reason="bad")


def test_birth_inheritance_records_reject_inconsistent_states() -> None:
    with pytest.raises(ValueError):
        ChildGenomeResult(
            child_id="c",
            parent_id="p",
            parent_genome_digest="pg",
            child_genome_digest="cg",
            mutation_digest="md",
            mutation_count=0,
            genome_bits="111",
            validity_status="BOGUS",
        )
    with pytest.raises(ValueError):
        LearningInheritanceRecord(
            parent_id="p",
            child_id="c",
            tick=0,
            inheritance_policy=InheritancePolicy.DARWINIAN_GENETIC_ONLY.value,
            learning_capacity_inherited=True,
            learned_content_inherited=False,
            inheritance_type="genetic_only",
            child_received_skill_digest="childskill",
        )
    with pytest.raises(ValueError):
        SkillCompressionRecord(
            parent_id="p",
            child_id="c",
            tick=0,
            mode=SkillInheritanceMode.COMPRESSED_SKILL.value,
            validation_status="not_requested",
            compressed_skill_digest="skill",
        )
    with pytest.raises(ValueError):
        ADFInheritanceRecord(
            parent_id="p",
            child_id="c",
            tick=0,
            parent_adf_digest="parent",
            child_adf_digest="child",
            adf_inheritance_mode="reset",
            adf_skill_imported=True,
        )
    with pytest.raises(ValueError):
        AIBirthInterventionRecord(
            intervention_id="",
            controller_name="",
            controller_version="",
            input_evidence_digest="",
            decision_digest="",
            applied=True,
            rejected_reason=None,
            scope=InterventionScope.CHILD_ONLY.value,
            event="before_birth_gate",
        )


def test_export_table_schemas_and_empty_envelopes_are_public() -> None:
    result = _capacity_block_result()
    schemas = result.export_table_schemas
    assert "ai_birth_intervention_records" in schemas
    assert schemas["ai_birth_intervention_records"] == (
        "schema_version",
        "feature_status",
        "status_reason",
    )
    envelope = result.export_records("ai_birth_intervention_records")
    assert envelope.feature_status == "empty_but_available"
    assert envelope.status_reason == "no_matching_events_observed"
    missing = result.export_records("missing_table")
    assert missing.feature_status == "unavailable"


def _learning_parent() -> GenesisOrganism:
    parent = GenesisOrganism.from_bits(
        "parent",
        "111",
        initial_runtime_atp=40.0,
        initial_learning_atp=5.0,
        learning_enabled=True,
    )
    memory = EpisodicMemory(parent.memory_config)
    event = TraceEvent(
        step=0,
        agent_id="parent",
        codon="111",
        action="skill_probe",
        atp_before=40.0,
        atp_after=40.0,
        position_before=(0, 0),
        position_after=(0, 0),
        status="executed",
        reason="success",
        world_delta={"reward:skill_probe": 1.0},
    )
    memory.append(
        EpisodicEvent(
            tick=0,
            organism_id="parent",
            action="skill_probe",
            status="executed",
            position_before=(0, 0),
            position_after=(0, 0),
            atp_runtime_before=40.0,
            atp_runtime_after=40.0,
            atp_learning_before=5.0,
            atp_learning_after=5.0,
            world_digest_before="world",
            trace_event_digest="trace-event-digest",
            observation={"signal": "skill_probe"},
            outcome={"reason": "success", "world_delta": {"reward:skill_probe": 1.0}},
        )
    )
    parent.episodic_memory = memory
    return parent


def _alive() -> AliveGateResult:
    return AliveGateResult(
        passed=True,
        survived_ticks=1,
        executed_actions=1,
        blocked_actions=0,
        blocked_ratio=0.0,
        final_runtime_atp=40.0,
        lumen_interactions=0,
        reproduction_events=1,
        reasons=(),
    )


def test_lamarckian_positive_probe_validates_skill_transfer() -> None:
    result = reproduce(
        _learning_parent(),
        ReproductionConfig(
            min_runtime_atp=1.0,
            parent_atp_cost=1.0,
            inheritance_policy=InheritancePolicy.LAMARCKIAN_COMPRESSED_LEARNING,
            skill_inheritance_mode=SkillInheritanceMode.COMPRESSED_SKILL,
            enable_skill_compression=True,
            enable_lamarckian_learning_inheritance=True,
        ),
        MutationConfig(bit_flip_rate=0.0),
        alive_result=_alive(),
        generation=0,
        birth_tick=1,
        seed=1,
    )
    assert result.learning_inheritance_record is not None
    assert result.learning_inheritance_record.learned_content_inherited is True
    assert result.learning_inheritance_record.child_received_skill_digest is not None
    assert result.skill_compression_record is not None
    assert result.skill_compression_record.validation_status == "validated"
    assert result.skill_compression_record.inherited is True


def test_lamarckian_no_evidence_control_rejects_skill_transfer() -> None:
    parent = GenesisOrganism.from_bits("parent", "111", initial_runtime_atp=40.0)
    result = reproduce(
        parent,
        ReproductionConfig(
            min_runtime_atp=1.0,
            parent_atp_cost=1.0,
            inheritance_policy=InheritancePolicy.LAMARCKIAN_COMPRESSED_LEARNING,
            skill_inheritance_mode=SkillInheritanceMode.COMPRESSED_SKILL,
            enable_skill_compression=True,
            enable_lamarckian_learning_inheritance=True,
        ),
        MutationConfig(bit_flip_rate=0.0),
        alive_result=_alive(),
        generation=0,
        birth_tick=1,
        seed=1,
    )
    assert result.learning_inheritance_record is not None
    assert result.learning_inheritance_record.learned_content_inherited is False
    assert result.learning_inheritance_record.child_received_skill_digest is None
    assert result.skill_compression_record is not None
    assert result.skill_compression_record.validation_status == "rejected"
    assert result.skill_compression_record.rejected_reason == "no_valid_learning_evidence"


def test_death_monitoring_enabled_false_disables_risk_records() -> None:
    result = _capacity_block_result(death_monitoring=DeathMonitoringConfig(enabled=False))
    assert result.death_reason_records == ()
    assert result.death_classification_records == ()
    assert result.export_records("death_reason_records").feature_status == "disabled_by_config"
    assert result.export_records("death_reason_records").status_reason == "death_monitoring_disabled"
    assert all(not record.death_risk_after_generation for record in result.energy_accounting_records)
    assert all(not record.alive_gate_failed_after_generation for record in result.energy_accounting_records)
    assert all(record.death_policy_digest is None for record in result.energy_accounting_records)


def test_emit_record_for_every_organism_tick_false_suppresses_not_applicable_records() -> None:
    result = _capacity_block_result(
        death_monitoring=DeathMonitoringConfig(
            emit_record_for_every_organism_tick=False,
            count_capacity_block_as_risk=False,
        )
    )
    assert result.death_reason_records == ()
    assert result.death_classification_records == ()
    assert result.export_records("death_reason_records").feature_status == "empty_but_available"
    assert (
        result.export_records("death_reason_records").status_reason
        == "no_death_or_risk_events_observed"
    )


def test_emit_energy_link_records_false_removes_death_links_from_energy_records() -> None:
    result = _capacity_block_result(
        death_monitoring=DeathMonitoringConfig(emit_energy_link_records=False)
    )
    assert result.death_reason_records
    assert all(record.death_policy_digest is None for record in result.energy_accounting_records)
    assert all(not record.death_risk_after_generation for record in result.energy_accounting_records)
    assert all(not record.alive_gate_failed_after_generation for record in result.energy_accounting_records)
    assert all(not record.actual_death_removed_from_population for record in result.energy_accounting_records)


def test_energy_record_rejects_death_risk_without_alive_gate_failure() -> None:
    with pytest.raises(ValueError):
        EnergyAccountingRecord(
            organism_id="o",
            tick=0,
            action="x",
            runtime_atp_before=1.0,
            runtime_atp_after=1.0,
            action_cost=0.0,
            blocked=False,
            alive_gate_failed_after_generation=False,
            death_risk_after_generation=True,
        )


def test_capacity_block_reproduction_attempt_exports_config_thresholds() -> None:
    result = _capacity_block_result()
    attempt = result.reproduction_attempt_records[0]
    assert attempt.blocked_reason == "max_population_reached"
    assert attempt.min_runtime_atp_required == 1.0
    assert attempt.parent_atp_cost == 1.0
    assert attempt.offspring_atp_fraction == 0.25
    assert attempt.population_capacity == 1
    assert attempt.available_space is False


def test_capacity_block_has_nonfatal_capacity_summary() -> None:
    result = _capacity_block_result()
    summary = result.death_energy_summary_records[0]
    assert summary["actual_death_count"] == 0
    assert summary["nonfatal_capacity_block_count"] >= 1
    assert summary["blocked_reproduction_capacity_count"] >= 1


def test_fatal_capacity_block_is_not_counted_as_nonfatal_capacity_summary() -> None:
    result = _capacity_block_result(
        death_monitoring=DeathMonitoringConfig(
            fatal_alive_reasons=("blocked_ratio_exceeded",),
        )
    )
    summary = result.death_energy_summary_records[0]
    assert summary["actual_death_count"] == 1
    assert summary["blocked_reproduction_capacity_count"] == 1
    assert summary["nonfatal_capacity_block_count"] == 0


def test_write_export_csvs_never_writes_zero_byte_files(tmp_path) -> None:
    from codontrace.genesis import write_export_csvs

    result = _capacity_block_result(death_monitoring=DeathMonitoringConfig(enabled=False))
    manifest = write_export_csvs(result, tmp_path)
    assert manifest.files
    for file_record in manifest.files:
        assert file_record.size_bytes > 0
        assert file_record.header_digest
        assert file_record.file_digest
