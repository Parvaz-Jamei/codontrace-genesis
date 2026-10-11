"""Bounded decision support: calibration, freshness budgets and shadow comparison.

Established methods, not new theoretical guarantees. No device side effects.
"""
from __future__ import annotations

import hashlib
from dataclasses import asdict
from typing import Any

from codontrace.genesis.shadow_evaluation import paired_shadow
from codontrace.genesis.swarm.active_sampling import schedule_measurements  # noqa: F401  (moved; public name)
from codontrace.life_loop.conformal_bands import split_residual_interval
from codontrace.swarm.policies import Pipeline
from codontrace.swarm.protocol import canonical, identifier, integer, number, object_keys  # noqa: F401  (public names)


def _pairs(values: Any, references: Any) -> tuple[list[float], list[float]]:
    if not isinstance(values, list) or not isinstance(references, list) or not 3 <= len(values) <= 4096 or len(values) != len(references):
        raise ValueError('3..4096 paired observations required')
    return [number(v) for v in values], [number(v) for v in references]


def residual_interval(predictions: list[float], references: list[float], *, estimate: float,
                      training_id: str, calibration_id: str, model_id: str,
                      alpha: float = .1) -> dict[str, Any]:
    """Finite-sample split-residual quantile; coverage needs exchangeable scores.

    Dataset identifiers prevent obvious reuse, but cannot prove independence.
    Never clamp an unavailable quantile into a falsely narrow finite interval.
    """
    identifier(training_id); identifier(calibration_id); identifier(model_id)
    if training_id == calibration_id:
        raise ValueError('training and calibration histories must differ')
    number(alpha, low=.001, high=.5); estimate = number(estimate)
    predictions, references = _pairs(predictions, references)
    # Exact rational rank (life_loop.conformal_bands.split_conformal_rank): float
    # rounding can move ceil((n+1)(1-alpha)) by one.
    interval = split_residual_interval(predictions, references, estimate=estimate, alpha=alpha)
    radius, rank = interval.radius, interval.quantile_rank
    return {'schema': 'genesis_residual_interval_v1', 'estimate': estimate,
            'lower': None if radius is None else estimate-radius,
            'upper': None if radius is None else estimate+radius,
            'radius': radius, 'quantile_rank': rank, 'calibration_count': interval.calibration_count, 'alpha': alpha,
            'status': 'finite_calibration_interval' if radius is not None else 'insufficient_for_finite_interval',
            'training_id': training_id, 'calibration_id': calibration_id, 'model_id': model_id,
            'calibration_sha256': hashlib.sha256(canonical({'predictions': predictions, 'references': references}).encode()).hexdigest(),
            'coverage_assumptions': 'frozen predictor; calibration/test scores exchangeable; no calibration reuse for fitting',
            'coverage_verified': False, 'scope': 'scalar_split_residual_calibration_not_aci_or_time_series_guarantee'}


def capsule_shadow(candidate: Pipeline, baseline: Pipeline, values: list[float], references: list[float], *,
                   training_id: str, evaluation_id: str, phase: str = 'qualification',
                   minimum_gain: float = 0., maximum_regression: float = 0.) -> dict[str, Any]:
    """Paired engineering comparison on one independent, full recorded window.

    Deployment monitoring needs fresh post-adoption windows and acknowledgements.
    This function does not deploy or roll back firmware. No RL/SPIBB safety theorem.
    """
    identifier(training_id);identifier(evaluation_id)
    if training_id==evaluation_id: raise ValueError('evaluation cannot reuse training history')
    if phase not in ('qualification','monitoring'): raise ValueError('unknown shadow phase')
    number(minimum_gain,low=0,high=1e12);number(maximum_regression,low=0,high=1e12)
    values,references=_pairs(values,references)
    shadow=paired_shadow(candidate,baseline,values,references,phase=phase,minimum_gain=minimum_gain,
                         maximum_regression=maximum_regression)
    gain,candidate_mse,baseline_mse,rollback,accepted=(shadow.gain_mse,shadow.candidate_mse,shadow.baseline_mse,
                                                        shadow.rollback_advised,shadow.accepted)
    choice=candidate if shadow.keep_candidate else baseline
    events_a,events_b=list(shadow.candidate_events),list(shadow.baseline_events)
    return {'schema':'genesis_capsule_shadow_v1','phase':phase,'gain_mse':gain,
            'candidate_mse':candidate_mse,'baseline_mse':baseline_mse,
            'qualification_passed':accepted if phase=='qualification' else None,
            'rollback_advised':rollback,'recommended_pipeline':asdict(choice),
            'candidate_digest':candidate.digest,'baseline_digest':baseline.digest,
            'training_id':training_id,'evaluation_id':evaluation_id,'sample_count':len(values),
            'evaluation_sha256':hashlib.sha256(canonical({'values':values,'references':references}).encode()).hexdigest(),
            'raw_event_indices_candidate':events_a,'raw_event_indices_baseline':events_b,
            'command_sent':False,'statistical_safety_guarantee':False,
            'scope':'paired_full_window_shadow_not_continuous_stream_state_or_physical_rollback'}
