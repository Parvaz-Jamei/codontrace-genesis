from codontrace.genesis import GenesisEngine, GenesisExperimentSpec
from codontrace.genesis.runtime_profiles import GenesisRuntimeProfile


def test_default_result_passes_strict_consistency_validator():
    result = GenesisEngine.from_spec(GenesisExperimentSpec(tick_count=1, seed=7)).run_ticks()
    validation = result.validate_consistency(strict=True)
    assert validation.passed, validation.issues


def test_social_pilot_result_passes_strict_consistency_validator():
    result = GenesisEngine.from_spec(GenesisRuntimeProfile.social_partner_pilot_world(seed=1, tick_count=3)).run_ticks()
    validation = result.validate_consistency(strict=True)
    assert validation.passed, validation.issues
