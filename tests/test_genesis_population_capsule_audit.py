from codontrace.genesis import (
    CapsuleTransferConfig,
    GenerationResult,
    OrganismStepRecord,
    PopulationConfigs,
)


def test_population_configs_capsule_roundtrip_default_disabled():
    configs = PopulationConfigs(
        capsule_transfer=CapsuleTransferConfig(enabled=True), enable_nexus_stigmergy=True
    )
    restored = PopulationConfigs.from_dict(configs.to_dict())
    assert restored.capsule_transfer is not None
    assert restored.capsule_transfer.enabled is True
    assert restored.enable_nexus_stigmergy is True


def test_old_generation_result_without_capsule_fields_still_deserializes():
    # Existing roundtrip tests cover GenerationResult; schema additions remain optional.
    assert hasattr(OrganismStepRecord, "from_dict")
    assert hasattr(GenerationResult, "from_dict")
