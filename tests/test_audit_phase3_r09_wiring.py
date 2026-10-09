"""Tests for Phase 3 (R09: Deep Core Wiring & Causal Mechanisms) remediation.

Verifies:
1. Generic QD descriptor extraction in GenesisEngine._update_qd and Preflight validation in from_spec.
2. PopulationConfigs vs capsule transfer precedence reconciliation and tracking.
3. Semantic separation and 3-chain taxonomy for the 12 causal mechanism fields in protocol_statuses.
"""

from __future__ import annotations

import warnings

import pytest

from codontrace.errors import ConfigurationError
from codontrace.genesis import (
    CapsuleOutcomeWindow,
    CapsuleTransferConfig,
    GenesisEngine,
    GenesisEngineConfig,
    GenesisExperimentSpec,
    MutationConfig,
    PopulationConfigs,
    QDArchiveConfig,
    QDDescriptorRegistry,
    ReproductionConfig,
    RoleMechanicsPolicy,
    TerritoryMechanicsConfig,
)
from codontrace.genesis.quality_diversity import BehaviorDescriptorSchema


def test_qd_preflight_validation_rejects_unregistered_descriptor() -> None:
    """A schema with an unknown descriptor and no registered extractor must raise ConfigurationError in from_spec."""
    schema = BehaviorDescriptorSchema(
        descriptor_names=("survival_ticks", "unregistered_custom_dimension"),
        bins_per_descriptor={"survival_ticks": 4, "unregistered_custom_dimension": 4},
        min_values={"survival_ticks": 0.0, "unregistered_custom_dimension": 0.0},
        max_values={"survival_ticks": 10.0, "unregistered_custom_dimension": 10.0},
    )
    spec = GenesisExperimentSpec(
        tick_count=1,
        qd_archive_config=QDArchiveConfig(schema=schema),
    )
    with pytest.raises(ConfigurationError, match="cannot be extracted: no extractor registered"):
        GenesisEngine.from_spec(spec)


def test_qd_custom_extractor_registry_in_from_spec_and_runtime() -> None:
    """Registered extractor in QDDescriptorRegistry extracts custom metric in _update_qd without error."""
    schema = BehaviorDescriptorSchema(
        descriptor_names=("survival_ticks", "custom_metabolic_score"),
        bins_per_descriptor={"survival_ticks": 4, "custom_metabolic_score": 4},
        min_values={"survival_ticks": 0.0, "custom_metabolic_score": 0.0},
        max_values={"survival_ticks": 10.0, "custom_metabolic_score": 100.0},
    )
    registry = QDDescriptorRegistry().register(
        "custom_metabolic_score",
        lambda rec: float(getattr(rec, "runtime_atp_after", 5.0) * 2.0),
    )
    spec = GenesisExperimentSpec(
        tick_count=2,
        qd_archive_config=QDArchiveConfig(schema=schema),
        qd_descriptor_registry=registry,
    )
    engine = GenesisEngine.from_spec(spec)
    result = engine.run_ticks()

    assert result is not None
    assert engine.qd_archive is not None
    assert len(engine.qd_archive.elites) > 0
    # Verify elite behavior descriptors contain custom_metabolic_score
    for elite in engine.qd_archive.elites.values():
        assert "custom_metabolic_score" in elite.behavior_descriptor
        assert elite.behavior_descriptor["custom_metabolic_score"] >= 0.0


def test_qd_standard_behavior_fields_and_aliases_extracted() -> None:
    """Non-default standard descriptors (e.g. unique_positions, energy_efficiency) resolve cleanly."""
    schema = BehaviorDescriptorSchema(
        descriptor_names=("unique_positions", "energy_efficiency"),
        bins_per_descriptor={"unique_positions": 5, "energy_efficiency": 5},
        min_values={"unique_positions": 0.0, "energy_efficiency": 0.0},
        max_values={"unique_positions": 50.0, "energy_efficiency": 10.0},
    )
    spec = GenesisExperimentSpec(
        tick_count=2,
        qd_archive_config=QDArchiveConfig(schema=schema),
    )
    engine = GenesisEngine.from_spec(spec)
    result = engine.run_ticks()
    assert result is not None
    assert engine.qd_archive is not None
    for elite in engine.qd_archive.elites.values():
        assert "unique_positions" in elite.behavior_descriptor
        assert "energy_efficiency" in elite.behavior_descriptor


def test_population_configs_capsule_transfer_reconciliation() -> None:
    """When population_configs has capsule_transfer=None but engine_config.enable_capsules=True, capsules are retained."""
    pop_cfg = PopulationConfigs(
        reproduction=ReproductionConfig(max_population=8),
        mutation=MutationConfig(bit_flip_rate=0.01),
        capsule_transfer=None,  # omitted in population_configs
    )
    spec = GenesisExperimentSpec(
        tick_count=1,
        population_configs=pop_cfg,
        engine_config=GenesisEngineConfig(enable_capsules=True),
    )
    engine = GenesisEngine.from_spec(spec)

    assert engine.runner.configs.capsule_transfer is not None
    assert engine.runner.configs.capsule_transfer.enabled is True
    assert engine.runner.nexus_layer is not None
    assert engine.config_reconciliation["reconciliation_applied"] is True
    assert engine.config_reconciliation["effective_capsules_enabled"] is True


def test_population_configs_explicit_capsule_disabled_conflict_warning() -> None:
    """When population_configs explicitly disables capsule_transfer while spec requested it, warn and respect setting."""
    pop_cfg = PopulationConfigs(
        reproduction=ReproductionConfig(max_population=8),
        capsule_transfer=CapsuleTransferConfig(enabled=False),  # explicitly disabled
    )
    spec = GenesisExperimentSpec(
        tick_count=1,
        population_configs=pop_cfg,
        engine_config=GenesisEngineConfig(enable_capsules=True),
    )
    with warnings.catch_warnings(record=True) as recorded:
        warnings.simplefilter("always")
        engine = GenesisEngine.from_spec(spec)

    assert any("Conflicting capsule configuration" in str(w.message) for w in recorded)
    assert engine.runner.configs.capsule_transfer.enabled is False
    assert engine.config_reconciliation["effective_capsules_enabled"] is False
    assert len(engine.config_reconciliation["warnings"]) > 0


def test_protocol_statuses_3_chain_taxonomy_and_reasons() -> None:
    """Protocol statuses must expose 3-chain classifications and informative status_reasons."""
    spec = GenesisExperimentSpec(
        tick_count=1,
        role_mechanics_policy=RoleMechanicsPolicy(max_bias_strength=0.2),
        territory_mechanics_config=TerritoryMechanicsConfig(enabled=True, home_cells=("0:0",)),
        capsule_outcome_window=CapsuleOutcomeWindow(window_ticks=5),
    )
    engine = GenesisEngine.from_spec(spec)
    result = engine.run_ticks()
    statuses = result.manifest.protocol_statuses

    # Chain 1: Behavioral Policies
    assert statuses.get("phase2.role_mechanics_policy_digest.chain") == "behavioral_policy"
    assert statuses.get("phase2.role_mechanics_policy_digest.status") == "candidate_evidence"
    assert "active" in statuses.get("phase2.role_mechanics_policy_digest.status_reason", "")

    assert statuses.get("phase2.territory_mechanics_config_digest.chain") == "behavioral_policy"
    assert statuses.get("phase2.territory_mechanics_config_digest.status") == "candidate_evidence"

    assert statuses.get("phase2.capsule_outcome_window_digest.chain") == "behavioral_policy"
    assert statuses.get("phase2.capsule_outcome_window_digest.status") == "candidate_evidence"

    # Disabled by config fields
    assert statuses.get("phase2.heldout_partner_protocol_digest.status") == "disabled_by_config"
    assert statuses.get("phase2.heldout_partner_protocol_digest.status_reason") == "not_configured_in_spec"
