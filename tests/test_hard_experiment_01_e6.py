"""Wave E6: HE01 ODD + Morris screening harness.

Exploratory documentation and design only. ClaimGate stays
runtime_observation. Does not rewrite Amd 01/02/03 or results_v5.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from codontrace.errors import ConfigurationError
from codontrace.genesis.claim_gate import ClaimRequest, ScientificClaimGate
from codontrace.genesis.hard_experiment_01 import (
    CALIBRATION_BASAL_COST,
    CALIBRATION_RESOURCE_AMOUNT,
    CLAIM_CEILING,
    SCHEMA_VERSION,
    build_hard_experiment_01_spec,
)
from codontrace.genesis.hard_experiment_01_morris import (
    ANALYSIS_SEEDS,
    DEFAULT_DESIGN_SEED,
    DEFAULT_SMOKE_SEEDS,
    EXPLORATORY_SEEDS,
    FACTOR_LEVELS,
    FACTOR_NAMES,
    MORRIS_DELTA,
    MORRIS_TIER,
    PILOT_SEEDS,
    build_morris_trajectories,
    build_morris_treatment_spec,
    calibration_anchor_knobs,
    compute_morris_screening,
    evaluate_morris_e6_claim,
    flatten_morris_points,
    refuse_confirmatory_seeds,
    run_morris_e6,
)

ROOT = Path(__file__).resolve().parents[1]
ODD_PATH = ROOT / "docs" / "HARD_EXPERIMENT_01_ODD.md"
DESIGN_PATH = ROOT / "docs" / "hard_experiment_01" / "morris_e6_design.md"
HE01_DOC = ROOT / "docs" / "HARD_EXPERIMENT_01.md"

FORBIDDEN_CLAIM_WORDS = (
    "collective_intelligence",
    "proved_collective_intelligence",
    "tokyo_type1_passed",
    "avida_replacement",
    "avida-parity",
    "avida_parity",
)

_ALLOWED_INTELLIGENCE_WINDOWS = (
    "odd ≠ intelligence",
    "odd is not intelligence",
    "≠ intelligence",
    "why_not_intelligence_yet",
)


def test_odd_file_exists_with_grimm_and_genesis_sections() -> None:
    assert ODD_PATH.is_file()
    text = ODD_PATH.read_text(encoding="utf-8")
    assert "## 1. Purpose and patterns" in text
    assert "## 2. Entities, state variables and scales" in text
    assert "## 3. Process overview and scheduling" in text
    assert "## 4. Design concepts" in text
    assert "## 5. Initialization" in text
    assert "## 6. Input data" in text
    assert "## 7. Submodels" in text
    assert "## Assumptions" in text
    assert "## Limitations" in text
    assert "## Claim level" in text
    assert "runtime_observation" in text
    assert "seed_permuted_v3_multiset" in text
    assert "every-cell" in text or "every cell" in text
    assert "max(1, population_size)" in text
    assert "shuffled_better_than_capsules_off" in text
    assert "ODD ≠ intelligence" in text
    assert "does not claim `intervention_supported`" in text
    assert "Grimm" in text
    assert DESIGN_PATH.is_file()


def test_odd_forbidden_claim_words_absent() -> None:
    text = ODD_PATH.read_text(encoding="utf-8")
    lowered = text.lower()
    for word in FORBIDDEN_CLAIM_WORDS:
        assert word not in lowered
    assert re.search(r"\bagi\b", lowered) is None
    for match in re.finditer(r"intelligence", lowered):
        window = lowered[max(0, match.start() - 40) : match.end() + 40]
        assert any(token in window for token in _ALLOWED_INTELLIGENCE_WINDOWS), window
    # Must deny the confirmatory label, not assert it.
    assert "does not claim `intervention_supported`" in text
    assert "claim `intervention_supported`" not in text.replace(
        "does not claim `intervention_supported`", ""
    )


def test_he01_doc_cross_links_wave_e6() -> None:
    text = HE01_DOC.read_text(encoding="utf-8")
    assert "Wave E6" in text
    assert "HARD_EXPERIMENT_01_ODD.md" in text
    assert "morris_e6_design.md" in text


def test_morris_trajectories_have_n_equals_r_times_k_plus_one() -> None:
    for r in (2, 10):
        trajectories = build_morris_trajectories(r=r, design_seed=DEFAULT_DESIGN_SEED)
        points = flatten_morris_points(trajectories)
        assert len(trajectories) == r
        assert len(FACTOR_NAMES) == 4
        assert len(points) == r * (len(FACTOR_NAMES) + 1)
        assert all(len(item.points) == 5 for item in trajectories)
        assert all(len(item.stepped_factors) == 4 for item in trajectories)
        assert {name for item in trajectories for name in item.stepped_factors} == set(FACTOR_NAMES)


def test_morris_trajectories_are_deterministic_for_design_seed() -> None:
    first = build_morris_trajectories(r=10, design_seed=DEFAULT_DESIGN_SEED)
    second = build_morris_trajectories(r=10, design_seed=DEFAULT_DESIGN_SEED)
    other = build_morris_trajectories(r=10, design_seed=DEFAULT_DESIGN_SEED + 1)
    assert [item.to_dict() for item in first] == [item.to_dict() for item in second]
    assert [item.to_dict() for item in first] != [item.to_dict() for item in other]


def test_morris_refuses_analysis_and_pilot_seeds() -> None:
    refuse_confirmatory_seeds(EXPLORATORY_SEEDS)
    refuse_confirmatory_seeds(DEFAULT_SMOKE_SEEDS)
    with pytest.raises(ConfigurationError, match="11-40"):
        refuse_confirmatory_seeds((11, 12))
    with pytest.raises(ConfigurationError, match="1000-1009"):
        refuse_confirmatory_seeds((1000,))
    with pytest.raises(ConfigurationError, match="11-40"):
        run_morris_e6(r=1, seeds=(11, 12), evaluate=False)
    with pytest.raises(ConfigurationError, match="1000-1009"):
        build_morris_treatment_spec(seed=1005, knobs=calibration_anchor_knobs())
    assert frozenset(range(11, 41)) == ANALYSIS_SEEDS
    assert frozenset(range(1000, 1010)) == PILOT_SEEDS
    assert set(EXPLORATORY_SEEDS).isdisjoint(ANALYSIS_SEEDS)
    assert set(EXPLORATORY_SEEDS).isdisjoint(PILOT_SEEDS)


def test_morris_treatment_spec_freezes_coverage_and_respawn() -> None:
    knobs = {
        "read_radius": 3.0,
        "min_source_fitness": 1.0,
        "basal_runtime_atp_cost": 0.6,
        "resource_amount": 3.0,
    }
    spec = build_morris_treatment_spec(seed=2000, knobs=knobs, tick_count=8, population=8)
    assert spec.metadata["food_coverage"] == 1.0
    assert spec.metadata["food_layout"] == "every_cell"
    n = int(spec.world_width) * int(spec.world_height)
    assert len(spec.metadata["food_cells"]) == n
    policy = spec.population_configs.runtime_resource_policy
    assert policy.respawn_draws_per_tick == max(1, 8)
    assert policy.amount == 3.0
    assert spec.population_configs.metabolism.basal_runtime_atp_cost == 0.6
    assert spec.capsule_transfer_config is not None
    assert spec.capsule_transfer_config.read_radius == 3
    assert spec.capsule_transfer_config.min_source_fitness == 1.0
    # Confirmatory builder remains on Amd 03 defaults.
    baseline = build_hard_experiment_01_spec(
        seed=2000, arm="source_bias_on", tick_count=8, population=8
    )
    assert baseline.capsule_transfer_config is not None
    assert baseline.capsule_transfer_config.read_radius == 6
    assert baseline.population_configs.metabolism.basal_runtime_atp_cost == CALIBRATION_BASAL_COST
    assert baseline.population_configs.runtime_resource_policy.amount == CALIBRATION_RESOURCE_AMOUNT
    assert spec.digest() != baseline.digest()


def test_morris_synthetic_screen_ranks_the_moving_factor() -> None:
    def outcome_fn(knobs: dict[str, float], seed: int) -> float:
        del seed
        return 10.0 * float(knobs["basal_runtime_atp_cost"]) + 0.01 * float(
            knobs["resource_amount"]
        )

    result = run_morris_e6(
        r=2,
        design_seed=DEFAULT_DESIGN_SEED,
        seeds=(2000,),
        scale="smoke",
        outcome_fn=outcome_fn,
    )
    assert result.n_evaluations == 2 * (4 + 1)
    assert result.n_evaluations == len(result.outcomes)
    assert all(item is not None for item in result.outcomes)
    by_factor = {row.factor: row for row in result.screening}
    assert set(by_factor) == set(FACTOR_NAMES)
    assert by_factor["basal_runtime_atp_cost"].mu_star > by_factor["read_radius"].mu_star
    assert by_factor["basal_runtime_atp_cost"].mu_star > by_factor["min_source_fitness"].mu_star
    assert result.claim_ceiling == CLAIM_CEILING
    assert result.tier == MORRIS_TIER
    assert result.scale == "smoke"
    assert result.tick_count == 8
    assert result.population == 8
    decision = evaluate_morris_e6_claim(result)
    assert decision.allowed is True
    assert decision.final_claim == CLAIM_CEILING


def test_morris_claimgate_stays_runtime_observation() -> None:
    decision = evaluate_morris_e6_claim({"claim_ceiling": CLAIM_CEILING})
    assert decision.final_claim == CLAIM_CEILING
    with pytest.raises(ConfigurationError, match="intervention_supported"):
        evaluate_morris_e6_claim({"claim_ceiling": "intervention_supported"})
    with pytest.raises(ConfigurationError, match="must not set"):
        evaluate_morris_e6_claim({"claim_ceiling": CLAIM_CEILING, "collective_intelligence": True})
    gate = ScientificClaimGate()
    payload = run_morris_e6(r=1, seeds=(2000,), evaluate=False).to_dict()
    assert payload["claim_ceiling"] == CLAIM_CEILING
    assert payload["claim_gate_unchanged"] is True
    assert gate.decide(ClaimRequest("runtime_observation", {})).allowed is True
    assert gate.decide(ClaimRequest("collective_intelligence", {})).allowed is False
    assert gate.decide(ClaimRequest("intervention_supported", {})).allowed is False
    assert SCHEMA_VERSION == "hard_experiment_01_v5"
    assert calibration_anchor_knobs()["min_source_fitness"] == 1.5
    assert set(FACTOR_LEVELS) == {
        "read_radius",
        "min_source_fitness",
        "basal_runtime_atp_cost",
        "resource_amount",
    }
    assert abs(MORRIS_DELTA - (4 / 6)) < 1e-12


def test_morris_screening_requires_matching_outcome_length() -> None:
    trajectories = build_morris_trajectories(r=1, design_seed=1)
    with pytest.raises(ConfigurationError, match=r"N=r\(k\+1\)"):
        compute_morris_screening(trajectories, (1.0,))


def test_committed_morris_smoke_json_is_exploratory_only() -> None:
    path = ROOT / "docs" / "hard_experiment_01" / "morris_e6_smoke.json"
    assert path.is_file()
    payload = __import__("json").loads(path.read_text(encoding="utf-8"))
    assert payload["schema"] == "hard_experiment_01_morris_e6"
    assert payload["claim_ceiling"] == CLAIM_CEILING
    assert payload["tier"] == MORRIS_TIER
    assert payload["claim_gate_unchanged"] is True
    assert payload["k"] == 4
    assert payload["n_evaluations"] == payload["r"] * (payload["k"] + 1)
    assert payload["seeds"] == [2000]
    assert set(payload["seeds"]).isdisjoint(range(11, 41))
    assert set(payload["seeds"]).isdisjoint(range(1000, 1010))
    assert payload["scale"] == "smoke"
    assert payload["frozen"]["food_coverage"] == 1.0
    assert payload["frozen"]["respawn_draws_per_tick"] == "max(1, population_size)"
    assert {row["factor"] for row in payload["screening"]} == set(FACTOR_NAMES)
