"""Bounded decision support: calibration, freshness budgets and shadow comparison.

Established methods, not new theoretical guarantees. No device side effects.
"""
from __future__ import annotations

import hashlib
import math
import statistics
from dataclasses import asdict
from fractions import Fraction
from typing import Any

from codontrace.swarm.policies import Pipeline
from codontrace.swarm.protocol import canonical, identifier, integer, number, object_keys


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
    scores = sorted(abs(p-r) for p, r in zip(predictions, references, strict=True))
    # Exact rational arithmetic: float rounding can move ceil((n+1)(1-alpha)) by one.
    rank = math.ceil((len(scores)+1)*(1-Fraction(str(alpha))))
    radius = scores[rank-1] if rank <= len(scores) else None
    return {'schema': 'genesis_residual_interval_v1', 'estimate': estimate,
            'lower': None if radius is None else estimate-radius,
            'upper': None if radius is None else estimate+radius,
            'radius': radius, 'quantile_rank': rank, 'calibration_count': len(scores), 'alpha': alpha,
            'status': 'finite_calibration_interval' if radius is not None else 'insufficient_for_finite_interval',
            'training_id': training_id, 'calibration_id': calibration_id, 'model_id': model_id,
            'calibration_sha256': hashlib.sha256(canonical({'predictions': predictions, 'references': references}).encode()).hexdigest(),
            'coverage_assumptions': 'frozen predictor; calibration/test scores exchangeable; no calibration reuse for fitting',
            'coverage_verified': False, 'scope': 'scalar_split_residual_calibration_not_aci_or_time_series_guarantee'}


def schedule_measurements(candidates: list[dict[str, Any]], *, now_ms: int,
                          byte_budget: int, request_budget: int = 8) -> dict[str, Any]:
    """Greedy estimated-error reduction per byte with group redundancy discount.

    Scalar random-walk proxy: noise + q*age; successful fresh reading arrives
    with age=latency. Group utility is max, not a sum of correlated sensors.
    A user-declared group is not an estimated covariance model. No optimality claim.
    """
    integer(now_ms); integer(byte_budget, high=16*1024*1024); integer(request_budget, high=32)
    if not isinstance(candidates, list) or len(candidates)>256:
        raise ValueError('bounded candidate list required')
    rows=[];seen=set()
    for raw in candidates:
        row=object_keys(raw, {'key','group','sample_ms','noise_variance','process_variance_per_ms',
                             'latency_ms','success_probability','payload_bytes','evidence_id'})
        key=row['key']
        if not isinstance(key,str) or len(key.split('/')) not in (1,2):
            raise ValueError('candidate key must identify a node/channel')
        for part in key.split('/'): identifier(part)
        identifier(row['group']);identifier(row['evidence_id'])
        if key in seen: raise ValueError('duplicate candidate identity')
        seen.add(key);sample=integer(row['sample_ms'])
        if sample>now_ms: raise ValueError('scheduling requires synchronized nonfuture timestamps')
        noise=number(row['noise_variance'],low=0,high=1e6)
        q=number(row['process_variance_per_ms'],low=0,high=1e6)
        latency=integer(row['latency_ms'],high=3600000);cost=integer(row['payload_bytes'],high=65536)
        if not cost: raise ValueError('positive estimated payload cost required')
        probability=number(row['success_probability'],low=0,high=1)
        age=now_ms-sample
        if age>3600000: raise ValueError('candidate age exceeds modeled one-hour horizon')
        gain=probability*max(0.,q*(age-latency))
        rows.append({**row,'age_ms':age,'current_variance_proxy':noise+q*age,
                     'refreshed_variance_proxy':noise+q*latency,'expected_gain_proxy':gain})
    selected: list[dict[str, Any]]=[];remaining=list(rows);group_best: dict[Any, float]={};spent=0
    while len(selected)<request_budget:
        scored=[]
        for row in remaining:
            gain=max(0.,row['expected_gain_proxy']-group_best.get(row['group'],0.))
            if row['payload_bytes']<=byte_budget-spent and gain>0:
                scored.append((gain/row['payload_bytes'],gain,row))
        if not scored: break
        _,gain,row=min(scored,key=lambda item:(-item[0],-item[1],item[2]['key']))
        selected.append({**row,'marginal_gain_proxy':gain})
        spent+=row['payload_bytes'];group_best[row['group']]=row['expected_gain_proxy'];remaining.remove(row)
    return {'schema':'genesis_freshness_schedule_v1','selected':selected,'candidates':rows,
            'estimated_payload_bytes':spent,'byte_budget':byte_budget,
            'expected_group_gain_proxy':sum(group_best.values()),'command_sent':False,
            'scope':'advisory_greedy_random_walk_proxy_with_declared_redundancy_groups',
            'limitations':'costs/probabilities/q supplied by caller; no actual wire-byte, energy, covariance or optimality guarantee'}


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
    a,events_a=candidate.process(values);b,events_b=baseline.process(values)
    candidate_mse=statistics.mean((v-r)**2 for v,r in zip(a,references,strict=True))
    baseline_mse=statistics.mean((v-r)**2 for v,r in zip(b,references,strict=True))
    gain=baseline_mse-candidate_mse
    rollback=phase=='monitoring' and gain < -maximum_regression
    accepted=phase=='qualification' and gain>minimum_gain
    choice=candidate if accepted or (phase=='monitoring' and not rollback) else baseline
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
