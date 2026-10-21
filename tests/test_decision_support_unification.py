"""P8: residual intervals, shadow evaluation, active sampling and the
disturbance family moved into engine sections; the swarm wrappers must give
identical results (frozen reference copies of the pre-move code below)."""
from __future__ import annotations

import hashlib
import json
import math
import statistics
from dataclasses import asdict
from fractions import Fraction

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from codontrace.genesis.shadow_evaluation import paired_mse_gain, paired_shadow
from codontrace.genesis.swarm import active_sampling
from codontrace.life_loop.conformal_bands import (
    conformal_risk_band,
    split_conformal_rank,
    split_residual_interval,
)
from codontrace.life_loop.disturbance import DisturbanceFamily, apply_disturbance
from codontrace.rng import RNGManager
from codontrace.swarm import decision_support
from codontrace.swarm.decision_support import capsule_shadow, residual_interval
from codontrace.swarm.policies import Pipeline, transfer_decision
from codontrace.swarm.protocol import canonical, number
from codontrace.swarm.research import perturb


def _exact(value):
    return json.dumps(value, sort_keys=True)


def _ref_residual(predictions, references, estimate, alpha):
    scores = sorted(abs(p-r) for p, r in zip(predictions, references, strict=True))
    rank = math.ceil((len(scores)+1)*(1-Fraction(str(alpha))))
    radius = scores[rank-1] if rank <= len(scores) else None
    return {'schema': 'genesis_residual_interval_v1', 'estimate': estimate,
            'lower': None if radius is None else estimate-radius,
            'upper': None if radius is None else estimate+radius,
            'radius': radius, 'quantile_rank': rank, 'calibration_count': len(scores), 'alpha': alpha,
            'status': 'finite_calibration_interval' if radius is not None else 'insufficient_for_finite_interval',
            'training_id': 't', 'calibration_id': 'c', 'model_id': 'm',
            'calibration_sha256': hashlib.sha256(canonical({'predictions': predictions,
                                                            'references': references}).encode()).hexdigest(),
            'coverage_assumptions': 'frozen predictor; calibration/test scores exchangeable; no calibration reuse for fitting',
            'coverage_verified': False, 'scope': 'scalar_split_residual_calibration_not_aci_or_time_series_guarantee'}


values_st = st.one_of(st.integers(-1000, 1000), st.floats(-1e6, 1e6, allow_nan=False, allow_infinity=False))


@settings(max_examples=300, deadline=None)
@given(st.lists(st.tuples(values_st, values_st), min_size=3, max_size=60), values_st,
       st.sampled_from([0.001, 0.01, 0.05, 0.1, 0.2, 0.25, 1/3, 0.5]))
def test_residual_interval_is_identical_key_for_key(pairs, estimate, alpha):
    predictions = [p for p, _ in pairs]; references = [r for _, r in pairs]
    got = residual_interval(predictions, references, estimate=estimate, training_id='t', calibration_id='c',
                            model_id='m', alpha=alpha)
    want = _ref_residual([number(v) for v in predictions], [number(v) for v in references], number(estimate), alpha)
    assert list(got) == list(want) and _exact(got) == _exact(want)


@pytest.mark.parametrize(('n', 'rank'), [(9, 9), (10, 10), (19, 18)])
def test_exact_rank_edge_cases_at_alpha_0_1(n, rank):
    assert split_conformal_rank(n, 0.1) == rank
    scores = list(range(1, n + 1))
    interval = split_residual_interval([float(s) for s in scores], [0.0] * n, estimate=0.0, alpha=0.1)
    assert interval.quantile_rank == rank and interval.radius == float(rank)


def test_exact_rank_where_float_arithmetic_is_off_by_one():
    assert math.ceil((99 + 1) * (1 - 0.45)) == 56
    assert split_conformal_rank(99, 0.45) == 55
    got = residual_interval([float(i) for i in range(99)], [0.0] * 99, estimate=0.0, training_id='t',
                            calibration_id='c', model_id='m', alpha=0.45)
    assert got['quantile_rank'] == 55 and got['radius'] == 54.0


def test_split_interval_without_finite_quantile_is_not_clamped():
    interval = split_residual_interval([1.0, 2.0, 3.0], [0.0, 0.0, 0.0], estimate=5.0, alpha=0.1)
    assert interval.quantile_rank == 4 and interval.radius is None and interval.lower is None
    assert interval.to_dict()['upper'] is None and interval.digest().startswith('split_residual:')
    with pytest.raises(ValueError):
        split_residual_interval([1.0], [0.0, 1.0], estimate=0.0)
    with pytest.raises(ValueError):
        split_conformal_rank(5, 0)


def test_conformal_risk_band_digests_are_unchanged():
    # Values computed on the pre-P8 code (refactor/engine-integration-p7 @ 9c4637a).
    cases = [
        (dict(result_id='r1', point_prediction=1.5, calibration_residuals=[0.1, -0.4, 0.25, 0.9, -0.05]),
         'conf_band:aee4e9e058821d41ab8fa6d6f3348dd43d102d9940ada83ebeaca6b45317b5cb'),
        (dict(result_id='r2', point_prediction=-3.0, calibration_residuals=[i / 7 for i in range(19)], alpha=0.1,
              max_width=1.0), 'conf_band:475bcd50af0856b06a332d40397515f2334b3276f14c072586120868c75dc63f'),
        (dict(result_id='r3', point_prediction=0.0, calibration_residuals=[2.0] * 10, alpha=0.2,
              claim_ceiling='candidate_evidence'),
         'conf_band:6bd3f67439e220c629bf4f300455a23d72b5d9adfa5eb2f9216ce5b26acbba21'),
    ]
    for kwargs, digest in cases:
        assert conformal_risk_band(**kwargs).digest == digest


def _ref_shadow(candidate, baseline, values, references, phase, minimum_gain, maximum_regression):
    a, events_a = candidate.process(values); b, events_b = baseline.process(values)
    candidate_mse = statistics.mean((v-r)**2 for v, r in zip(a, references, strict=True))
    baseline_mse = statistics.mean((v-r)**2 for v, r in zip(b, references, strict=True))
    gain = baseline_mse-candidate_mse
    rollback = phase == 'monitoring' and gain < -maximum_regression
    accepted = phase == 'qualification' and gain > minimum_gain
    choice = candidate if accepted or (phase == 'monitoring' and not rollback) else baseline
    return {'schema': 'genesis_capsule_shadow_v1', 'phase': phase, 'gain_mse': gain,
            'candidate_mse': candidate_mse, 'baseline_mse': baseline_mse,
            'qualification_passed': accepted if phase == 'qualification' else None,
            'rollback_advised': rollback, 'recommended_pipeline': asdict(choice),
            'candidate_digest': candidate.digest, 'baseline_digest': baseline.digest,
            'training_id': 't', 'evaluation_id': 'e', 'sample_count': len(values),
            'evaluation_sha256': hashlib.sha256(canonical({'values': values, 'references': references}).encode()).hexdigest(),
            'raw_event_indices_candidate': events_a, 'raw_event_indices_baseline': events_b,
            'command_sent': False, 'statistical_safety_guarantee': False,
            'scope': 'paired_full_window_shadow_not_continuous_stream_state_or_physical_rollback'}


@pytest.mark.parametrize('phase', ['qualification', 'monitoring'])
@pytest.mark.parametrize('seed', range(6))
def test_capsule_shadow_and_transfer_decision_are_identical(phase, seed):
    rng = RNGManager(seed=seed, namespace='test/shadow')
    refs = [math.sin(i / 4) * 2 for i in range(30)]
    values = [r + (rng.random() - 0.5) * 3 for r in refs]
    candidate = Pipeline(alpha=0.2 + 0.1 * seed, clip=1.0 + seed)
    baseline = Pipeline()
    for gain, regression in ((0.0, 0.0), (0.05, 0.1), (10.0, 10.0)):
        got = capsule_shadow(candidate, baseline, values, refs, training_id='t', evaluation_id='e', phase=phase,
                             minimum_gain=gain, maximum_regression=regression)
        want = _ref_shadow(candidate, baseline, [number(v) for v in values], [number(v) for v in refs], phase,
                           gain, regression)
        assert list(got) == list(want) and _exact(got) == _exact(want)
    a, _ = candidate.process(values); b, _ = baseline.process(values)
    ref_gain = statistics.mean((x-y)**2 - (z-y)**2 for x, z, y in zip(b, a, refs, strict=True))
    assert transfer_decision(candidate, baseline, values, refs)['local_mse_gain'] == ref_gain
    assert paired_mse_gain(candidate, baseline, values, refs) == ref_gain
    assert paired_shadow(candidate, baseline, values, refs, phase=phase).gain_mse == want['gain_mse']


def test_schedule_measurements_moved_not_copied():
    assert decision_support.schedule_measurements is active_sampling.schedule_measurements


def _ref_perturb(values, rng, amplitude, bias, dropout):
    out = []
    for value in values:
        number(value)
        lost = rng.random() < dropout
        noise = (rng.random()*2-1)*amplitude
        out.append(None if lost else value + bias + noise)
    return out


@pytest.mark.parametrize(('amplitude', 'bias', 'dropout'), [(1, 0, 0), (0.5, 2.0, 0.3), (0, -1, 1.0), (3, 0, 0.05)])
def test_perturb_is_identical_including_rng_state(amplitude, bias, dropout):
    values = [i * 0.5 - 3 for i in range(50)]
    a, b = RNGManager(seed=4, namespace='t'), RNGManager(seed=4, namespace='t')
    assert _exact(perturb(values, rng=a, amplitude=amplitude, bias=bias, dropout=dropout)) == \
        _exact(_ref_perturb(values, b, amplitude, bias, dropout))
    assert a.snapshot() == b.snapshot()


def test_perturb_error_path_consumes_the_same_draws():
    a, b = RNGManager(seed=1, namespace='t'), RNGManager(seed=1, namespace='t')
    bad = [1.0, 2.0, math.inf, 3.0]
    with pytest.raises(ValueError, match='number outside supported range'):
        perturb(bad, rng=a, dropout=0.5)
    with pytest.raises(ValueError, match='number outside supported range'):
        _ref_perturb(bad, b, 1, 0, 0.5)
    assert a.snapshot() == b.snapshot()


def test_disturbance_family_is_validated_and_digestible():
    family = DisturbanceFamily(amplitude=0.5, bias=1.0, dropout=0.25)
    assert family.digest() == DisturbanceFamily(0.5, 1.0, 0.25).digest() != DisturbanceFamily().digest()
    out = apply_disturbance([0.0] * 400, family, RNGManager(seed=2, namespace='t'))
    kept = [v for v in out if v is not None]
    assert 0.15 < 1 - len(kept) / 400 < 0.35 and all(0.5 <= v <= 1.5 for v in kept)
    for bad in (dict(amplitude=-1), dict(dropout=1.5), dict(bias=math.nan)):
        with pytest.raises(ValueError):
            DisturbanceFamily(**bad)
