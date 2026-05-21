from codontrace.genesis import GenesisExperimentSpec
from codontrace.genesis.benchmark_suite import BenchmarkScenarioSuite


def test_benchmark_suite_runs_baseline_and_ablation_with_artifacts():
    suite = BenchmarkScenarioSuite.standard()
    small = BenchmarkScenarioSuite(suite.suite_id, suite.scenarios[:2])
    results, report = small.run(GenesisExperimentSpec(tick_count=1))

    assert len(results) == 2
    assert report.scenario_count == 2
    for result in results:
        payload = result.to_dict()
        assert payload["baseline_manifest_digest"]
        assert payload["baseline_replay_digest"]
        assert payload["baseline_evidence_digest"]
        assert payload["ablation_manifest_digest"]
    assert (
        report.digest()
        == BenchmarkScenarioSuite(suite.suite_id, suite.scenarios[:2])
        .run(GenesisExperimentSpec(tick_count=1))[1]
        .digest()
    )
