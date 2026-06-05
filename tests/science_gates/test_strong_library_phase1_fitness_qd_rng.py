from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

from codontrace.genesis.fitness import (
    FitnessScorerConfig,
    build_fitness_component_value,
    evaluate_fitness_breakdown,
)
from codontrace.genesis.qd_search import (
    QDCandidate,
    QDEvaluateResult,
    ask_qd_candidates,
    tell_qd_results,
    validate_qd_candidate_digest,
)
from codontrace.rng import NumpyGeneratorBackend, RNGManager, RNGManagerBackend


def test_rng_backend_replay_stability_same_backend_and_no_cross_backend_claim() -> None:
    left = RNGManagerBackend(seed=11, namespace="phase1")
    right = RNGManagerBackend(seed=11, namespace="phase1")
    assert [left.randrange(100) for _ in range(5)] == [right.randrange(100) for _ in range(5)]
    assert left.backend_kind == "rng_manager"
    assert left.state_digest() == right.state_digest()

    if importlib.util.find_spec("numpy") is not None:
        np_left = NumpyGeneratorBackend(seed=11, namespace="phase1")
        np_right = NumpyGeneratorBackend(seed=11, namespace="phase1")
        assert [np_left.randrange(100) for _ in range(5)] == [
            np_right.randrange(100) for _ in range(5)
        ]
        assert np_left.backend_kind == "numpy_generator"
        assert np_left.state_digest() == np_right.state_digest()
        assert (
            np_left.snapshot(include_state=True)["backend_kind"]
            != left.snapshot(include_state=True)["backend_kind"]
        )


def test_core_imports_without_optional_dependency_modules_loaded() -> None:
    import codontrace
    import codontrace.genesis

    assert codontrace.__version__ == "0.3.0b1"
    # Core import must not import optional scientific backends as a side effect.
    assert "ribs" not in sys.modules


def test_optional_extras_use_ribs_package_name() -> None:
    pyproject = Path("pyproject.toml").read_text(encoding="utf-8")
    assert '"ribs>=0.10,<1"' in pyproject
    assert "pyribs" not in pyproject
    assert "science = [" in pyproject and "research = [" in pyproject


def test_fitness_components_raw_normalized_weighted_polarity_and_penalties() -> None:
    reward = build_fitness_component_value(name="survival_ticks_score", raw=50, weight=2.0)
    penalty = build_fitness_component_value(name="blocked_penalty", raw=0.5, weight=3.0)
    assert reward.polarity == "reward"
    assert reward.weighted == 1.0
    assert penalty.polarity == "penalty"
    assert penalty.weighted == -1.5

    config = FitnessScorerConfig(weights=(("survival_ticks_score", 1.0), ("blocked_penalty", 1.0)))
    low = evaluate_fitness_breakdown(
        {"survival_ticks_score": 10, "blocked_penalty": 0.9}, config=config
    )
    high = evaluate_fitness_breakdown(
        {"survival_ticks_score": 10, "blocked_penalty": 0.0}, config=config
    )
    assert high.total > low.total
    assert low.config_digest == config.digest()
    with pytest.raises(ValueError):
        FitnessScorerConfig(weights=(("survival_ticks_score", -1.0),))


def test_qd_candidate_and_ask_evaluate_tell_contracts_are_candidate_objects() -> None:
    parent = QDCandidate.from_genome_bits(
        "000111",
        candidate_id="parent",
        genome_program_digest="gp1",
        macro_registry_digest="macro1",
        translation_profile_digest="translation1",
    )
    restored = validate_qd_candidate_digest(parent.to_dict(), parent.digest())
    assert restored.genome_program_digest == "gp1"
    rng = RNGManager(seed=5, namespace="qd")
    ask = ask_qd_candidates((parent,), rng=rng, count=2)
    assert len(ask.candidates) == 2
    assert all(isinstance(candidate, QDCandidate) for candidate in ask.candidates)
    assert ask.rng_state_digest_before != ask.rng_state_digest_after
    evaluation = QDEvaluateResult(
        candidate_id=ask.candidates[0].candidate_id,
        objective=1.0,
        descriptor=(0.5, 0.25),
        fitness_breakdown_digest="fit",
        valid=True,
    )
    tell = tell_qd_results("before", "after", (evaluation,), coverage=0.1, qd_score=1.5)
    assert tell.inserted == 0 and tell.improved == 0 and tell.rejected == 0
    assert tell.valid_evaluation_count == 1
    assert tell.archive_update_status == "not_observed"
