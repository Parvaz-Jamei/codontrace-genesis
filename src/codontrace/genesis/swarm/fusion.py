"""Descriptive fusion of fresh scalar frames: median, mean or trust-weighted mean.

Frames are first restricted to fresh, online, positive-quality scalar frames
of one quantity and unit, then to a window of ``max_span_ms`` before the
newest sample. Frames with different measurement semantics (feature id,
measurement model, model id) are not fused. Spread is reported as the median
absolute deviation about the median (MAD; Leys et al. 2013,
doi:10.1016/j.jesp.2013.03.013), unscaled. The estimate is descriptive: no
confidence interval is claimed.
"""
from __future__ import annotations

import statistics
from collections.abc import Mapping
from typing import Any

from codontrace.contracts.channels import scalar_frame

__all__ = ['FUSION_MODES', 'fresh_scalar_frames', 'median_absolute_deviation', 'robust_fuse']

FUSION_MODES = ('median', 'mean', 'calibrated')


def fresh_scalar_frames(view: Mapping[str, Any], quantity: str, unit: str, *, now_ms: int, ttl_ms: int,
                        max_skew_ms: int) -> dict[str, dict[str, Any]]:
    """Frames eligible for fusion from a state view whose members carry ``online``."""
    return {k: f for k, f in view['frames'].items()
            if scalar_frame(f) and f['quantity'] == quantity and f['unit'] == unit and
            -max_skew_ms <= now_ms-f['sample_ms'] <= ttl_ms and
            view['nodes'][f['node_id']]['online'] and f.get('quality', 1) > 0}


def median_absolute_deviation(values: list[float]) -> float:
    center = statistics.median(values)
    return statistics.median(abs(v - center) for v in values)


def robust_fuse(frames: Mapping[str, dict[str, Any]], trust: Mapping[str, Any], quantity: str, unit: str, *,
                mode: str = 'median', max_span_ms: int = 1000) -> dict[str, Any]:
    if mode not in FUSION_MODES:
        raise ValueError('unknown fusion mode')
    if not frames:
        return {'value': None, 'count': 0, 'status': 'insufficient_data', 'unit': unit}
    latest = max(f['sample_ms'] for f in frames.values())
    frames = {k: f for k, f in frames.items() if latest-f['sample_ms'] <= max_span_ms}
    semantics = {(f.get('sensor_descriptor', {}).get('feature_id'), f.get('sensor_descriptor', {}).get('measurement_model'),
                  f.get('sensor_descriptor', {}).get('model_id')) for f in frames.values()}
    if len(semantics) > 1:
        return {'value': None, 'count': len(frames), 'status': 'incompatible_measurement_semantics', 'unit': unit}
    values = [f['value'] for f in frames.values()]
    center = statistics.median(values)
    if mode == 'mean':
        center = statistics.mean(values)
    if mode == 'calibrated':
        weights = {k: trust.get(k, {'weight': 1.0})['weight'] * f.get('quality', 1) for k, f in frames.items()}
        total = sum(weights.values())
        if total == 0:
            return {'value': None, 'count': len(frames), 'status': 'zero_weight', 'unit': unit}
        center = sum(frames[k]['value'] * w for k, w in weights.items()) / total
    return {'value': center, 'count': len(frames), 'status': 'descriptive_estimate',
            'quantity': quantity, 'unit': unit, 'mode': mode,
            'disagreement_mad': median_absolute_deviation(values),
            'contributors': sorted(frames), 'confidence_interval': None}
