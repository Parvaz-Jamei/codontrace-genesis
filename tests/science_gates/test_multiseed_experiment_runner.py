from codontrace.genesis import GenesisExperimentSpec
from codontrace.genesis.multiseed import MultiSeedExperimentRunner, MultiSeedRunConfig


def test_multiseed_runner_executes_all_seeds_and_is_deterministic():
    spec = GenesisExperimentSpec(tick_count=2, seed=7)
    config = MultiSeedRunConfig(seeds=(1, 2, 3), tick_count=2, min_seeds_for_scientific_claim=5)
    result_a = MultiSeedExperimentRunner(spec, config).run()
    result_b = MultiSeedExperimentRunner(spec, config).run()

    assert len(result_a.records) == 3
    assert {record.seed for record in result_a.records} == {1, 2, 3}
    assert all(record.manifest_digest for record in result_a.records)
    assert result_a.digest() == result_b.digest()
    assert result_a.summary.seed_count == 3
    assert "best_fitness" in result_a.summary.metric_stats
    assert result_a.summary.claim_gate_status == "claim_limited"


def test_multiseed_summary_allows_enough_seeds():
    spec = GenesisExperimentSpec(tick_count=1)
    config = MultiSeedRunConfig(seeds=(1, 2), tick_count=1, min_seeds_for_scientific_claim=2)
    result = MultiSeedExperimentRunner(spec, config).run()

    assert result.summary.claim_gate_status == "descriptive_multiseed_ready"
    assert "insufficient_seed_count_for_scientific_claim" not in result.summary.limitations
