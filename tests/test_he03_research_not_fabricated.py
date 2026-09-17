"""Phase 2: HE03 research artifact must not be invented."""

from codontrace.genesis.he03_status import he03_phase2_status
from codontrace.genesis.hard_experiment_03 import CLAIM_CEILING


def test_he03_research_results_are_absent() -> None:
    status = he03_phase2_status()
    assert status["research_results_present"] is False
    assert status["fabricated"] is False
    assert status["intervention_supported"] is False
    assert status["claim_ceiling"] == "runtime_observation"
    assert CLAIM_CEILING == "runtime_observation"


def test_he03_prereg_is_present() -> None:
    status = he03_phase2_status()
    assert status["prereg_present"] is True
