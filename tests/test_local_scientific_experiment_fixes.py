"""Behavioral checks against observed model/control/inference defects."""
import pytest

from codontrace.experiments.models import AssessmentStatus, ExecutionTrack
from codontrace.experiments.t01_oee import T01OEERunner
from codontrace.experiments.t02_mls_price import T02MLSPriceRunner
from codontrace.experiments.t03_mutualism import SymbioticPair, T03MutualismRunner
from codontrace.experiments.t04_contingency import T04ContingencyRunner
from codontrace.experiments.t05_red_queen import T05RedQueenRunner


@pytest.mark.parametrize("runner", [T01OEERunner, T02MLSPriceRunner, T03MutualismRunner, T04ContingencyRunner, T05RedQueenRunner])
def test_positive_budget_and_reference_boundary(runner):
    with pytest.raises(ValueError):
        runner(seed=1, generations=0)
    with pytest.raises(ValueError):
        runner(seed=1, track=ExecutionTrack.ENGINE)

@pytest.mark.parametrize("arm,fixed", [("FIXED_HOST", "hosts"), ("FIXED_PARASITE", "parasites")])
def test_frozen_population_really_preserves_entire_population(arm, fixed):
    r = T05RedQueenRunner(13, arm=arm, generations=20)
    r.initialize_populations()
    before = tuple(vars(x).copy() for x in getattr(r, fixed))
    for g in range(1, 21):
        r.step_generation(g)
    assert tuple(vars(x).copy() for x in getattr(r, fixed)) == before


def test_time_shift_assay_is_measured_and_bounded():
    r = T05RedQueenRunner(13, generations=70)
    result = r.run()
    evidence = result.summary_metrics["time_shift"]
    matrix = evidence["matrix"]
    assert len(matrix) == len(evidence["row_labels"]) <= 33
    for i, h_generation in enumerate(evidence["row_labels"]):
        for j, p_generation in enumerate(evidence["column_labels"]):
            h, p = r.archive[h_generation][0], r.archive[p_generation][1]
            expected = sum(r.evaluate_interaction(a,b)[1] for a in h for b in p) / (len(h)*len(p))
            assert matrix[i][j] == expected
    assert result.total_ticks == 0
    assert result.scientific_assessment == AssessmentStatus.INCONCLUSIVE


def test_extinction_is_not_silently_rescued(monkeypatch):
    import codontrace.experiments.t05_red_queen as module
    monkeypatch.setattr(module, "sha_prng_float", lambda *args: 1.0)
    r = T05RedQueenRunner(3, generations=30)
    result = r.run()
    assert result.status == "EXTINCT"
    assert result.completed_generations == 1
    assert r.hosts == r.parasites == []


def test_price_identity_describes_actual_next_generation():
    for seed in range(8):
        r = T02MLSPriceRunner(seed, num_demes=5, deme_capacity=7, generations=10, high_migration=True)
        r.initialize_population()
        for generation in range(1,11):
            parent_mean = sum(p.altruism_trait for p in r.population) / len(r.population)
            r.step_generation(generation)
            actual_delta = sum(p.altruism_trait for p in r.population) / len(r.population) - parent_mean
            assert len(r.population) == 35
            assert abs(actual_delta - r.price_history[-1].delta_z_observed) < 1e-12
            assert abs(r.price_history[-1].identity_residual) < 1e-12


def test_short_window_means_use_actual_sample_count():
    r = T02MLSPriceRunner(12, generations=3)
    result = r.run()
    assert result.summary_metrics["late_between_group_covariance"] == pytest.approx(sum(a.between_group_term for a in r.price_history)/3)


def test_pair_assay_keeps_covariance_and_shuffle_keeps_marginals():
    r = T03MutualismRunner(1, population_size=2, generations=1)
    r.population = [SymbioticPair(0,0,0.,0.), SymbioticPair(1,1,1.,1.)]
    a = r.run_4_assays(1)
    actual = [r.evaluate_pair_payoffs(p.host_cooperation,p.symbiont_cooperation) for p in r.population]
    assert a.payoff_with_partner == pytest.approx(tuple(sum(p[i] for p in actual)/2 for i in range(2)))
    # Either identity permutation or swap; no artificial 0.8 factor allowed.
    swap = [r.evaluate_pair_payoffs(0.,1.), r.evaluate_pair_payoffs(1.,0.)]
    valid = [a.payoff_with_partner, tuple(sum(p[i] for p in swap)/2 for i in range(2))]
    assert any(a.payoff_scrambled_partner == pytest.approx(v) for v in valid)


def test_final_assay_is_current_and_streaming_works():
    r = T03MutualismRunner(2, generations=502, population_size=8)
    seen = []
    result = r.run(on_generation=lambda record: seen.append(record.generation))
    assert result.summary_metrics["final_assay_generation"] == 502
    assert seen == list(range(1,503))


def test_archive_reproductive_feedback_and_descriptor_fitness_match():
    qd = T01OEERunner(42, generations=25)
    no_qd = T01OEERunner(42, arm="REAL_SELECTION_NO_QD", generations=25)
    qd.run(); no_qd.run()
    assert qd.qd_archive
    assert [p.genome for p in qd.population] != [p.genome for p in no_qd.population]
    random = T01OEERunner(42, arm="QD_RANDOM_DESCRIPTOR", generations=1)
    selected = T01OEERunner(42, generations=1)
    random.initialize_population(); selected.initialize_population()
    # Selection before reproductive archive intervention uses identical ecological fitness.
    random_record = random.step_generation(1)
    selected_record = selected.step_generation(1)
    assert random_record.population_size == selected_record.population_size
    assert random_record.primary_metric_value == selected_record.primary_metric_value


def test_no_unconditional_or_parameter_only_supported_claims():
    assert T04ContingencyRunner(12, generations=2).run().scientific_assessment == AssessmentStatus.INCONCLUSIVE
    assert T05RedQueenRunner(12, arm="NO_SELECTION", generations=2).run().scientific_assessment == AssessmentStatus.INCONCLUSIVE
    r = T01OEERunner(12, generations=3)
    first = r.run().to_dict()
    assert r.run().to_dict() == first


def test_time_shift_sensor_detects_constructed_positive_temporal_change():
    r = T05RedQueenRunner(1, generations=1)
    r.archive = {0: ((0,), (1,)), 1: ((0xFFFFFFFF,), (0,))}
    evidence = r._assay_time_shifts()
    assert evidence["host_recent_margin"] == pytest.approx(30/32)
    assert evidence["parasite_recent_margin"] == pytest.approx(1/32)


def test_frozen_host_time_shift_has_zero_host_adaptation():
    r = T05RedQueenRunner(13, arm="FIXED_HOST", generations=70)
    result = r.run()
    assert result.summary_metrics["time_shift"]["host_recent_margin"] == 0.0


def test_callback_can_release_metric_buffer_without_losing_summary():
    for runner in (T01OEERunner, T02MLSPriceRunner, T03MutualismRunner, T04ContingencyRunner, T05RedQueenRunner):
        r = runner(14, generations=3)
        result = r.run(on_generation=lambda record: r.metrics_history.clear())
        assert result.completed_generations == getattr(r, "planned_work_units", 3)
        assert result.total_ticks == 0


def test_qd_archive_intervention_reaches_actual_offspring(monkeypatch):
    import codontrace.experiments.t01_oee as module
    def controlled_float(seed, key, stream):
        if stream == "survival":
            return 0.0 if key == 1000 else 1.0
        if stream == "archive_parent":
            return 0.0
        return 1.0  # No mutation
    monkeypatch.setattr(module, "sha_prng_float", controlled_float)
    r = T01OEERunner(2, population_size=2, generations=1)
    r.initialize_population()
    r.qd_archive[0] = (0xA5, 100)  # Synthetic positive intervention, not scientific data.
    r.step_generation(1)
    assert r.population[-1].genome == 0xA5


def test_history_snapshot_is_immutable_and_restore_does_not_refound():
    r = T04ContingencyRunner(3, generations=3, replay_branches=2)
    r.initialize_population(3)
    r.step_generation(1,3)
    snapshot = r.snapshot(3,1)
    before = snapshot.digest()
    r.population[0].genome ^= 1
    r.discovered_phenotypes.add(999)
    assert snapshot.digest() == before
    r.restore_snapshot(snapshot)
    assert r.snapshot(3,1).digest() == before


def test_historical_fork_uses_same_snapshots_and_matched_future_streams():
    r = T04ContingencyRunner(4, generations=6, replay_branches=3, replay_generations=4,
                              snapshot_generations=(0,3,6))
    seen = []
    result = r.run(on_generation=lambda record: seen.append(record.generation))
    evidence = result.summary_metrics
    assert evidence["exact_replay_passed"]
    assert len(evidence["snapshots"]) == 6
    assert len(evidence["branches"]) == 24
    assert seen == list(range(1, r.planned_work_units+1))
    for snapshot_index in range(6):
        branches = [b for b in evidence["branches"] if b["snapshot_index"] == snapshot_index]
        assert len({b["snapshot_sha256"] for b in branches}) == 1
        assert branches[0]["final_state_sha256"] == branches[-1]["final_state_sha256"]
        assert branches[0]["future_seed"] == branches[-1]["future_seed"]
        assert len({b["future_seed"] for b in branches}) == 3
    assert result.scientific_assessment == AssessmentStatus.INCONCLUSIVE
    assert len({b["future_seed"] for b in evidence["branches"] if b["branch_index"] == 0}) == 1


def test_unbiased_stream_preserves_legacy_and_rejects_out_of_range():
    from codontrace.experiments.math_utils import sha_prng_int, sha_prng_int_unbiased
    legacy = sha_prng_int(1,2,"x",0,10)
    assert legacy == sha_prng_int(1,2,"x",0,10)
    values = [sha_prng_int_unbiased(2,i,"v2test",-3,7) for i in range(100)]
    assert set(values) == set(range(-3,8))
    assert values == [sha_prng_int_unbiased(2,i,"v2test",-3,7) for i in range(100)]
    with pytest.raises(ValueError):
        sha_prng_int_unbiased(1,2,"x",0,1<<257)


def test_unbiased_sampler_rejects_high_tail_instead_of_modulo(monkeypatch):
    from types import SimpleNamespace

    import codontrace.experiments.math_utils as module
    draws = [b"\xff" * 32, b"\x00" * 32]
    calls = []
    def digest(data):
        calls.append(data)
        value = draws.pop(0)
        return SimpleNamespace(digest=lambda: value)
    monkeypatch.setattr(module.hashlib, "sha256", digest)
    assert module.sha_prng_int_unbiased(4,2,"tail",0,2) == 0
    assert len(calls) == 2
    assert calls[0] != calls[1]
