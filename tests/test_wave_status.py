"""Post-phase-3 wave status stays honest."""

from codontrace.genesis.wave_status import wave_status


def test_wave_status_keeps_research_ceiling() -> None:
    status = wave_status()
    assert status["pypi_cut"] is True
    assert status["tag_created_in_this_wave"] is False
    assert status["phase1_wrapper_present"] is True
    assert status["phase2_he03_research_present"] is False
    assert status["claim_ceiling"] == "runtime_observation"
    assert status["intervention_supported"] is False
