from codontrace.genesis.statistical_report import (
    MinimumSeedPolicy,
    build_statistical_report,
    paired_seed_comparison,
)


def test_statistical_report_ci_and_seed_policy():
    report = build_statistical_report(
        {"fitness": [1.0, 2.0, 3.0]}, min_seed_policy=MinimumSeedPolicy(min_seeds=5)
    )

    assert (
        report.confidence_intervals[0].lower
        <= report.confidence_intervals[0].mean
        <= report.confidence_intervals[0].upper
    )
    assert report.claim_status == "descriptive_only"
    assert "insufficient_seed_count" in report.limitations


def test_paired_seed_comparison_pairs_common_seeds():
    comparison = paired_seed_comparison({1: 1.0, 2: 2.0}, {2: 5.0, 3: 9.0}, "fitness")

    assert comparison.seed_deltas == {2: 3.0}
    assert comparison.mean_delta == 3.0
