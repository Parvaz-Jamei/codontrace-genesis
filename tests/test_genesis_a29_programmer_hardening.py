import json
import os
import subprocess
import sys
import textwrap
from pathlib import Path

from codontrace.genesis.engine import (
    GenesisEngine,
    GenesisEngineConfig,
    GenesisExperimentSpec,
    _action_registry_hash,
)
from codontrace.genesis.population import ReproductionConfig


def _cross_process_digest_payload() -> dict[str, str]:
    code = textwrap.dedent(
        """
        import json
        from codontrace.genesis.engine import (
            GenesisEngine,
            GenesisEngineConfig,
            GenesisExperimentSpec,
            _action_registry_hash,
        )
        from codontrace.genesis.population import ReproductionConfig
        spec = GenesisExperimentSpec(
            genome_bits=("101110000", "111"),
            seed=77,
            tick_count=2,
            population_max=4,
            initial_runtime_atp=20.0,
            reproduction_config=ReproductionConfig(max_population=1),
            engine_config=GenesisEngineConfig(enable_qd=True, qd_mode="selection_pressure"),
        )
        result = GenesisEngine.from_spec(spec).run_ticks()
        print(json.dumps({
            "action_registry_hash": _action_registry_hash(None),
            "spec_digest": spec.digest(),
            "result_digest": result.digest(),
            "manifest_digest": result.manifest.digest(),
            "replay_bundle_digest": result.replay_bundle.digest(),
            "snapshot_digest": result.snapshot.digest(),
            "evidence_manifest_digest": result.evidence_manifest.digest(),
        }, sort_keys=True))
        """
    )
    env = os.environ.copy()
    src_path = str(Path(__file__).resolve().parents[1] / "src")
    existing = env.get("PYTHONPATH")
    env["PYTHONPATH"] = src_path if not existing else src_path + os.pathsep + existing
    out = subprocess.check_output([sys.executable, "-c", code], text=True, env=env)
    return json.loads(out)


def test_engine_native_digests_are_cross_process_stable() -> None:
    first = _cross_process_digest_payload()
    second = _cross_process_digest_payload()
    assert first == second
    assert first["action_registry_hash"] == _action_registry_hash(None)


def test_engine_digest_audit_includes_action_registry_stability() -> None:
    result = GenesisEngine.from_spec(
        GenesisExperimentSpec(genome_bits=("101110000",), seed=3, tick_count=1)
    ).run_ticks()
    audit = {item.digest_name: item for item in result.engine_digest_audit}
    assert "action_registry_hash" in audit
    assert audit["action_registry_hash"].stable is True
    assert not result.digest_instability_reasons


def test_copy_self_trace_and_reproduction_diagnostics_agree_when_capacity_blocks() -> None:
    spec = GenesisExperimentSpec(
        genome_bits=("111",),
        seed=5,
        tick_count=1,
        population_max=1,
        initial_runtime_atp=20.0,
        reproduction_config=ReproductionConfig(max_population=1),
        engine_config=GenesisEngineConfig(enable_qd=False),
    )
    result = GenesisEngine.from_spec(spec).run_ticks()

    copy_events = [row for row in result.energy_accounting_records if row.action == "COPY_SELF"]
    assert copy_events
    assert copy_events[0].blocked_reason == "max_population_reached"

    attempts = [
        row
        for row in result.reproduction_attempt_records
        if row.organism_id == copy_events[0].organism_id
    ]
    assert attempts
    assert attempts[0].reproduction_action_attempted is True
    assert attempts[0].blocked_reason == "max_population_reached"
    assert attempts[0].child_created is False


def test_death_accounting_separates_generation_and_event_attribution() -> None:
    spec = GenesisExperimentSpec(
        genome_bits=("111",),
        seed=5,
        tick_count=1,
        population_max=1,
        initial_runtime_atp=20.0,
        reproduction_config=ReproductionConfig(max_population=1),
        engine_config=GenesisEngineConfig(enable_qd=False),
    )
    result = GenesisEngine.from_spec(spec).run_ticks()
    rows = result.energy_accounting_records
    assert rows
    # Capacity-blocked COPY_SELF is an alive-gate warning/risk, not population removal.
    assert rows[0].organism_dead_after_generation is False
    assert rows[0].actual_death_removed_from_population is False
    assert rows[0].alive_gate_failed_after_generation is True
    assert rows[0].death_risk_after_generation is True
    assert rows[0].death_event is False
    assert rows[0].death_causing_event is False
    assert rows[0].death_attribution_level == "alive_gate_warning"


def test_qd_summary_marks_descriptor_set_when_no_grid_bins_exist() -> None:
    spec = GenesisExperimentSpec(
        genome_bits=("101110000",),
        seed=9,
        tick_count=0,
        engine_config=GenesisEngineConfig(enable_qd=True, qd_mode="archive_only"),
    )
    result = GenesisEngine.from_spec(spec).run_ticks()
    summary = result.qd_archive_summary
    assert summary.total_bins == 0
    assert summary.archive_type == "descriptor_set"
    assert summary.coverage_status == "not_applicable_no_grid"


def test_capsule_utility_has_before_after_fields_when_adoptions_exist() -> None:
    spec = GenesisExperimentSpec(
        genome_bits=("101110000", "101110000"),
        seed=4,
        tick_count=2,
        engine_config=GenesisEngineConfig(ticks_per_generation=1, enable_capsules=True),
    )
    result = GenesisEngine.from_spec(spec).run_ticks()
    # The scenario may have no adoption, but when it does, utility rows must no
    # longer be empty shell records with only after fields.
    for row in result.capsule_utility_records:
        assert hasattr(row, "target_fitness_before")
        assert hasattr(row, "target_behavior_digest_before")
        if row.target_fitness_before is not None and row.target_fitness_after is not None:
            assert row.utility_delta == round(
                row.target_fitness_after - row.target_fitness_before, 10
            )
