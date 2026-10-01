"""The class-balanced assay and the abundance-weighted pressure are different estimands."""

from __future__ import annotations

import pytest

from codontrace.genesis.measurements.rq_frequency_clocks import (
    CLASS_BALANCED_ASSAY,
    FREQUENCY_WEIGHTED_PRESSURE,
    algebraic_frozen_zero,
    class_balanced_assay,
    confirmatory_seed_disagreement,
    frequency_weighted_abundance_pressure,
    rq_path_components,
    separate_pressure_accounts,
)

HOSTS = {"h": "000000"}
PARASITES = {"common": "000000", "rare": "111111"}
FLAT = {"h": {"common": 1.0, "rare": 0.0}}


def test_same_support_different_frequencies_splits_the_two_metrics() -> None:
    even = {"common": 1, "rare": 1}
    skewed = {"common": 3, "rare": 1}
    balanced_even = class_balanced_assay(HOSTS, PARASITES, affinity=FLAT)
    balanced_skewed = class_balanced_assay(
        HOSTS, PARASITES, affinity=FLAT, parasite_class_counts=skewed
    )
    weighted_even = frequency_weighted_abundance_pressure(
        HOSTS, PARASITES, even, affinity=FLAT
    )
    weighted_skewed = frequency_weighted_abundance_pressure(
        HOSTS, PARASITES, skewed, affinity=FLAT
    )

    assert balanced_even["estimand"] == CLASS_BALANCED_ASSAY
    assert weighted_skewed["estimand"] == FREQUENCY_WEIGHTED_PRESSURE
    assert balanced_even["pressure"] == balanced_skewed["pressure"] == {"h": 0.6}
    assert weighted_even["pressure"] == {"h": 0.6}
    assert weighted_skewed["pressure"] == {"h": 0.9}
    assert balanced_even["equals_living_history_atp"] is False
    assert weighted_skewed["equals_living_history_atp"] is False
    assert balanced_even["red_queen_proved"] is False


def test_accounts_stay_separate_and_infinite_reserve_is_not_paid_atp() -> None:
    open_reserve = separate_pressure_accounts(
        affinity=1.0, kappa=1.2, reserve=None, contact_opportunities=7, lineage_growth=2
    )
    capped = separate_pressure_accounts(
        affinity=1.0, kappa=1.2, reserve=0.4, contact_opportunities=7, lineage_growth=2
    )
    observed = separate_pressure_accounts(
        affinity=1.0,
        kappa=1.2,
        reserve=0.4,
        contact_opportunities=7,
        lineage_growth=2,
        paid_atp=0.25,
    )
    assert open_reserve["intended_pressure"] == 1.2
    assert open_reserve["capacity_capped_assay"] is None
    assert open_reserve["paid_pressure"] is None
    assert open_reserve["capacity_cap_is_paid_atp"] is False
    assert capped["capacity_capped_assay"] == 0.4
    assert capped["paid_pressure"] is None
    assert observed["paid_pressure"] == 0.25
    assert observed["paid_is_observed_atp"] is True
    assert len({
        capped["intended_pressure"],
        capped["capacity_capped_assay"],
        capped["contact_opportunity"],
        capped["lineage_growth"],
    }) == 4
    with pytest.raises(ValueError):
        separate_pressure_accounts(
            affinity=1.0, kappa=1.2, reserve=0.4, contact_opportunities=1, lineage_growth=0, paid_atp=0.5
        )


def test_a_frozen_zero_from_a_zero_debit_is_only_algebraic() -> None:
    report = algebraic_frozen_zero(debit_multiplier=0.0, pressure=0.0)
    assert report["frozen_exactly_zero"] is True
    assert report["algebraic_control"] is True
    assert report["biological_validity"] is False
    assert report["causal_validity"] is False


def test_path_components_do_not_imply_one_another() -> None:
    lag_only = rq_path_components(
        lag_contrast=-0.2,
        rarity_delta=-1.0,
        host_delta=0.0,
        parasite_delta=0.0,
        pressure_with_path=0.0,
        pressure_path_cut=1.0,
        sham_pressure=0.0,
    )
    assert lag_only["lag_condition"] is True
    assert lag_only["rarity_advantage"] is False
    assert lag_only["reciprocal_feedback"] is False
    assert lag_only["path_cut_control"] is False
    assert lag_only["hypothesis_supported"] is False


def test_confirmatory_n_is_seeds_not_generations() -> None:
    report = confirmatory_seed_disagreement(
        {5701: 0.1, 5702: 0.4, 5703: -0.2}, generation_rows=30
    )
    assert report["n_confirmatory_seeds"] == 3
    assert report["n_generation_rows"] == 30
    assert report["n_used_for_inference"] == 3
    assert report["between_seed_range"] == pytest.approx(0.6)
    assert report["generations_are_independent_replicates"] is False


def test_weighted_pressure_is_a_composition_and_infinity_stays_labelled() -> None:
    unit = frequency_weighted_abundance_pressure(
        HOSTS, PARASITES, {"common": 3, "rare": 1}, affinity=FLAT
    )
    census = frequency_weighted_abundance_pressure(
        HOSTS, PARASITES, {"common": 30, "rare": 10}, affinity=FLAT
    )
    infinite = frequency_weighted_abundance_pressure(
        HOSTS,
        PARASITES,
        {"common": 3, "rare": 1},
        affinity=FLAT,
        host_capacity_units=float("inf"),
    )
    assert unit["pressure"] == census["pressure"] == {"h": 0.9}
    assert unit["scale_invariant_composition"] is True
    assert infinite["reserve_reading"] == "infinity_standardised_assay"
    assert infinite["equals_living_history_atp"] is False


def test_a_zero_that_is_not_a_zero_debit_is_not_called_algebraic() -> None:
    report = algebraic_frozen_zero(debit_multiplier=1.0, pressure=0.0)
    assert report["frozen_exactly_zero"] is True
    assert report["algebraic_control"] is False
    assert report["causal_validity"] is False


def test_weighted_pressure_rejects_a_different_support() -> None:
    with pytest.raises(ValueError):
        frequency_weighted_abundance_pressure(HOSTS, PARASITES, {"common": 1}, affinity=FLAT)
    with pytest.raises(ValueError):
        frequency_weighted_abundance_pressure(
            HOSTS, PARASITES, {"common": 1}, affinity=FLAT
        )
