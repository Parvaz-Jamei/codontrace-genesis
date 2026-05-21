from __future__ import annotations

import csv
from pathlib import Path

import pytest

from codontrace.actions import ActionResult, default_action_registry
from codontrace.errors import ConfigurationError
from codontrace.genesis.death import DeathClassificationRecord, DeathMonitoringConfig
from codontrace.genesis.diagnostics import EnergyAccountingRecord, write_export_csvs
from codontrace.genesis.engine import GenesisEngine, GenesisEngineConfig, GenesisExperimentSpec
from codontrace.genesis.example_smoke import ExampleSmokeCase, describe_example_smoke_cases
from codontrace.genesis.population import MutationConfig, PopulationConfigs, ReproductionConfig
from codontrace.genesis.qd_search import (
    QDCandidate,
    QDCandidateSearchRunner,
    QDEvaluateResult,
    QDSearchConfig,
    tell_qd_results,
)
from codontrace.genesis.substrate_runtime import GenesisWorldState, SubstrateActionBridge
from codontrace.world import World2D


def _capacity_block_result(*, death_monitoring: DeathMonitoringConfig | None = None):
    reproduction = ReproductionConfig(max_population=1, min_runtime_atp=1.0, parent_atp_cost=1.0)
    spec = GenesisExperimentSpec(
        genome_bits=("111",),
        seed=101,
        tick_count=2,
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


def _csv_data_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def test_write_export_csvs_row_counts_match_manifest_for_all_measured_exports(tmp_path: Path) -> None:
    result = _capacity_block_result()
    manifest = write_export_csvs(result, tmp_path)
    assert manifest.files
    for item in manifest.files:
        rows = _csv_data_rows(Path(item.path))
        assert len(rows) == item.row_count
        if item.feature_status == "measured":
            assert item.row_count > 0
            assert rows


def test_evaluation_protocol_digest_export_writes_digest_row(tmp_path: Path) -> None:
    result = _capacity_block_result()
    write_export_csvs(result, tmp_path)
    rows = _csv_data_rows(tmp_path / "evaluation_protocol_digest.csv")
    assert len(rows) == 1
    row = rows[0]
    assert row["schema_version"] == "evaluation_protocol_digest_v1"
    assert row["digest"] == result.evaluation_protocol_digest
    assert row["run_id"] == result.run.run_id
    assert row["spec_digest"] == result.run.spec_digest


def test_death_energy_reproduction_records_share_documented_time_contract() -> None:
    result = _capacity_block_result()
    death_cls = result.death_classification_records[0]
    death_reason = result.death_reason_records[0]
    repro = result.reproduction_attempt_records[0]
    energy = result.energy_accounting_records[0]

    assert death_reason.engine_tick == repro.tick == energy.engine_tick
    assert death_cls.engine_tick == death_reason.engine_tick
    assert death_cls.population_tick is not None
    assert death_cls.population_tick >= death_cls.engine_tick
    assert energy.event_step == 0


def test_tell_qd_results_does_not_report_inserted_without_archive_update() -> None:
    evaluation = QDEvaluateResult(
        candidate_id="candidate",
        objective=1.0,
        descriptor=(0.1, 0.2),
        fitness_breakdown_digest="fit",
        valid=True,
    )
    tell = tell_qd_results("before", "after", (evaluation,), coverage=0.1, qd_score=1.0)
    assert tell.inserted == 0
    assert tell.improved == 0
    assert tell.rejected == 0
    assert tell.valid_evaluation_count == 1
    assert tell.archive_update_status == "not_observed"


def test_energy_fitness_delta_is_not_fake_zero_when_unmeasured() -> None:
    result = _capacity_block_result()
    rec = result.energy_accounting_records[0]
    assert rec.fitness_delta is None
    assert rec.fitness_delta_status == "not_measured"
    assert rec.fitness_delta_source is None


def test_death_energy_summary_disabled_when_death_monitoring_disabled() -> None:
    result = _capacity_block_result(death_monitoring=DeathMonitoringConfig(enabled=False))
    envelope = result.export_envelopes_by_name["death_energy_summary_records"]
    assert envelope.feature_status == "disabled_by_config"
    row = envelope.records[0]
    assert isinstance(row, dict)
    assert row["death_monitoring_enabled"] is False
    assert row["actual_death_count"] is None


@pytest.mark.parametrize(
    "payload",
    [
        {"enabled": "false"},
        {"emit_energy_link_records": "yes"},
        {"fatal_alive_reasons": [None]},
        {"remove_on_runtime_atp_lte": "0"},
        {"fatal_alive_reasons": ["x", "x"]},
    ],
)
def test_death_monitoring_config_from_dict_rejects_lossy_coercion(payload: dict[str, object]) -> None:
    with pytest.raises(ConfigurationError):
        DeathMonitoringConfig.from_dict(payload)  # type: ignore[arg-type]


def test_capacity_block_reason_has_single_documented_export_semantics() -> None:
    result = _capacity_block_result()
    reasons = {record.death_reason for record in result.death_reason_records}
    assert reasons == {"capacity_block_nonfatal"}
    assert result.death_energy_summary_records[0]["nonfatal_capacity_block_count"] >= 1


def test_qd_candidate_archive_parent_provenance_matches_emitted_parent() -> None:
    parents = (
        QDCandidate.from_genome_bits("0000", candidate_id="p0"),
        QDCandidate.from_genome_bits("1111", candidate_id="p1"),
    )

    def evaluator(candidate: QDCandidate) -> tuple[float, dict[str, float]]:
        ones = float((candidate.genome_bits or "").count("1"))
        return ones, {"unique_positions": ones, "energy_efficiency": 1.0}

    runner = QDCandidateSearchRunner(
        QDSearchConfig(generations=2, offspring_per_generation=1, novelty_weight=1.0, seed=7),
        evaluator=evaluator,
    )
    result = runner.run(parents)
    second_selection = result.steps[1].parent_selections[0]
    assert second_selection.source == "archive_novelty"
    assert second_selection.provenance_status == "resolved_candidate"
    assert second_selection.parent_candidate_id is not None
    assert second_selection.parent_candidate_id != "p1"
    assert second_selection.parent_candidate_digest is not None


def test_example_smoke_contract_not_reported_as_successful_execution() -> None:
    result = describe_example_smoke_cases((ExampleSmokeCase("case", "examples/x.py"),))[0]
    assert result.attempted is False
    assert result.executed is False
    assert result.succeeded is False
    assert result.execution_status == "contract_only_not_executed"
    assert result.success_status == "not_attempted"


def test_open_action_status_requires_namespace() -> None:
    with pytest.raises(ConfigurationError):
        ActionResult("open_statuses", "typo", open_statuses=True)
    assert ActionResult("custom:my_status", "ok", open_statuses=True).status == "custom:my_status"


def test_collect_resource_object_is_explicit_registry_action() -> None:
    registry = default_action_registry()
    assert "COLLECT_RESOURCE_OBJECT" in registry.names()


def test_substrate_bridge_is_explicitly_audit_only() -> None:
    state = GenesisWorldState(world=World2D(2, 2), element_grid=None)
    _, audit = SubstrateActionBridge().apply_action(state, "EAT_LUMEN", (0, 0))
    assert audit["feature_status"] == "provisional_audit_only"
    assert audit["claim_allowed"] is False
    assert audit["resource_bridge_status"] == "audit_only_not_integrated"


def test_energy_record_requires_measured_fitness_delta_value_and_source() -> None:
    with pytest.raises(ValueError):
        EnergyAccountingRecord(
            organism_id="o",
            tick=0,
            action="x",
            runtime_atp_before=1.0,
            runtime_atp_after=1.0,
            fitness_delta_status="measured",
            fitness_delta=None,
        )


def test_death_monitoring_config_constructor_rejects_lossy_values() -> None:
    with pytest.raises(ConfigurationError):
        DeathMonitoringConfig(enabled="false")  # type: ignore[arg-type]
    with pytest.raises(ConfigurationError):
        DeathMonitoringConfig(fatal_alive_reasons=(None,))  # type: ignore[arg-type]
    with pytest.raises(ConfigurationError):
        DeathMonitoringConfig(fatal_alive_reasons=("x", "x"))


def test_death_classification_from_dict_rejects_lossy_coercion() -> None:
    payload = {
        "organism_id": "org",
        "tick": 0,
        "actual_death_removed_from_population": False,
        "alive_gate_failed": "true",
        "alive_gate_reasons": [],
        "death_risk_event": False,
        "fatal_policy_matched": False,
        "runtime_atp_before": 1.0,
        "runtime_atp_after": 1.0,
        "blocked_actions": 0,
        "blocked_action_reasons": [],
        "death_policy_digest": "digest",
    }
    with pytest.raises(ConfigurationError):
        DeathClassificationRecord.from_dict(payload)  # type: ignore[arg-type]


def test_energy_capacity_block_reason_matches_death_export_semantics() -> None:
    result = _capacity_block_result()
    energy_reasons = {
        record.death_reason for record in result.energy_accounting_records if record.death_risk_after_generation
    }
    assert energy_reasons == {"capacity_block_nonfatal"}
    assert {record.death_reason for record in result.death_reason_records} == {
        "capacity_block_nonfatal"
    }
