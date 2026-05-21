from __future__ import annotations

from pathlib import Path

import pytest

from codontrace.errors import ConfigurationError
from codontrace.genesis import (
    BenchmarkScenarioSuite,
    ClaimRequest,
    GenesisEngine,
    GenesisExperimentSpec,
    ScientificClaimGate,
)
from codontrace.genesis.artifacts import compute_source_digest, validate_phase1_manifest_fields
from codontrace.genesis.benchmark_suite import benchmark_v2_specs
from codontrace.genesis.engine import GenesisEngineConfig
from codontrace.genesis.qd_descriptors import (
    DescriptorSpec,
    build_descriptor_schema,
    default_phase1_descriptor_schema,
    descriptor_schema_from_dict,
)


def test_descriptor_schema_uses_factory_and_rejects_digest_mismatch() -> None:
    schema = build_descriptor_schema(
        "custom",
        (DescriptorSpec("unique_positions", "movement", 0.0, 10.0, 5),),
    )
    payload = schema.to_dict()
    assert descriptor_schema_from_dict(payload).digest == schema.digest
    tampered = dict(payload)
    tampered["digest"] = "bad"
    with pytest.raises(ConfigurationError):
        descriptor_schema_from_dict(tampered)
    assert default_phase1_descriptor_schema().digest


def test_benchmark_suite_v2_scenarios_exist_and_generate_specs() -> None:
    expected = {
        "empty_world_sanity",
        "static_resource_world",
        "deceptive_resource_world",
        "novelty_required_maze_world",
        "variable_genome_bloat_trap",
        "adf_usefulness_world",
        "known_resource_gate_world",
        "known_action_delayed_effect_world",
        "capsule_transfer_world",
        "known_capsule_transfer_world",
        "environmental_shift_translation_world",
        "multi_agent_stigmergy_world",
    }
    specs = benchmark_v2_specs()
    assert {spec.scenario_id for spec in specs} == expected
    assert all(spec.digest() for spec in specs)
    assert all(
        spec.build_experiment_spec().metadata["benchmark_scenario"] == spec.scenario_id
        for spec in specs
    )
    suite = BenchmarkScenarioSuite.standard()
    assert suite.suite_id.endswith("v2")
    assert {scenario.scenario_id for scenario in suite.scenarios} == expected


def test_manifest_phase1_fields_and_rng_backend_change_digest() -> None:
    base = GenesisEngine.from_spec(GenesisExperimentSpec(tick_count=1)).run_ticks()
    assert validate_phase1_manifest_fields(base.manifest).passed
    changed = GenesisEngine.from_spec(
        GenesisExperimentSpec(
            tick_count=1,
            engine_config=GenesisEngineConfig(rng_backend_kind="numpy_generator"),
        )
    ).run_ticks()
    assert base.manifest.rng_backend_kind == "rng_manager"
    assert changed.manifest.rng_backend_kind == "numpy_generator"
    assert base.manifest.digest() != changed.manifest.digest()
    assert base.manifest.source_digest
    assert base.manifest.descriptor_schema_hash
    assert base.manifest.claim_gate_decision_digest


def test_source_digest_changes_for_source_and_ignores_cache_files(tmp_path: Path) -> None:
    (tmp_path / "pkg").mkdir()
    source = tmp_path / "pkg" / "a.py"
    source.write_text("x = 1\n")
    before = compute_source_digest(str(tmp_path))
    (tmp_path / "pkg" / "__pycache__").mkdir()
    (tmp_path / "pkg" / "__pycache__" / "a.pyc").write_bytes(b"ignored")
    assert compute_source_digest(str(tmp_path)) == before
    source.write_text("x = 2\n")
    assert compute_source_digest(str(tmp_path)) != before


def test_claim_gate_phase1_labels_and_overclaims() -> None:
    gate = ScientificClaimGate()
    allowed = gate.decide(
        ClaimRequest(
            "continuous_fitness_supported",
            {"fitness_components": True, "fitness_config_digest": True},
        )
    )
    assert allowed.allowed
    qd = gate.decide(
        ClaimRequest(
            "active_qd_supported",
            {
                "qd_candidate_schema": True,
                "qd_ask_tell": True,
                "archive_feedback": True,
                "parent_selection_feedback": True,
                "archive_digest": True,
                "parent_selection_feedback_digest": True,
                "qd_scheduler_digest": True,
            },
        )
    )
    assert qd.allowed
    rejected = gate.decide(ClaimRequest("full_genesis_rejected", {}))
    assert not rejected.allowed
    heavy = gate.decide(ClaimRequest("full_GENESIS_engine", {}))
    assert not heavy.allowed
