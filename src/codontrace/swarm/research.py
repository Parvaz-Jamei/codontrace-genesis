"""Measured processing contrasts, sensor twins and bounded disturbance families."""
from __future__ import annotations

import statistics
from dataclasses import dataclass
from typing import Any

from codontrace.life_loop.disturbance import DisturbanceFamily, apply_disturbance
from codontrace.rng import RNGManager
from codontrace.swarm.protocol import canonical, integer, number, object_keys


def processing_contrast(frame: dict[str, Any], *, reference: float, tolerance: float = 2) -> dict[str, Any]:
    number(reference); number(tolerance, low=0.001)
    if not isinstance(frame, dict):
        raise ValueError('frame object required')
    raw = frame.get('raw')
    if not isinstance(raw, list) or len(raw) < 3:
        return {'status': 'insufficient_raw_data', 'causal_proof': False}
    for v in raw:
        number(v)
    estimate = statistics.median(raw)
    raw_error = abs(estimate-reference); processed_error = abs(number(frame['value'])-reference)
    return {'raw_error': raw_error, 'processed_error': processed_error,
            'status': 'processing_disagreement_candidate' if raw_error <= tolerance < processed_error else
                      'measurement_disagreement_candidate' if raw_error > tolerance else 'within_tolerance',
            'causal_proof': False}


@dataclass(frozen=True)
class SensorTwin:
    slope: float
    intercept: float
    residual_mae: float
    training_count: int

    @classmethod
    def fit(cls, references: list[float], observations: list[float]) -> SensorTwin:
        if not isinstance(references, list) or not isinstance(observations, list) or not 3 <= len(references) <= 4096 or len(references) != len(observations):
            raise ValueError('paired calibration data required')
        for v in references + observations:
            number(v)
        mx = statistics.mean(references); my = statistics.mean(observations)
        denominator = sum((x-mx)**2 for x in references)
        if denominator == 0:
            raise ValueError('reference variation required for identifiable slope')
        slope = sum((x-mx)*(y-my) for x, y in zip(references, observations, strict=True)) / denominator
        intercept = my-slope*mx
        mae = statistics.mean(abs(y-(slope*x+intercept)) for x, y in zip(references, observations, strict=True))
        return cls(slope, intercept, mae, len(references))

    def predict(self, reference: float) -> float:
        return self.slope * number(reference) + self.intercept


def perturb(values: list[float], *, rng: RNGManager, amplitude: float = 1,
            bias: float = 0, dropout: float = 0) -> list[float | None]:
    number(amplitude, low=0, high=1e6); number(bias); number(dropout, low=0, high=1)
    if not isinstance(values, list) or len(values) > 4096:
        raise ValueError('bounded disturbance input required')
    return apply_disturbance(values, DisturbanceFamily(amplitude=amplitude, bias=bias, dropout=dropout), rng,
                             check=number)


def mse(values: list[float], references: list[float]) -> float:
    if not values or len(values) != len(references):
        raise ValueError('nonempty paired observations required')
    for v in values + references:
        number(v)
    return statistics.mean((x-y)**2 for x, y in zip(values, references, strict=True))


def information_level(options: dict[str, Any], *, byte_budget: int, maximum_mse: float) -> dict[str, Any]:
    """Choose a supplied representation under measured validation error/byte limits.

    Validation errors are caller-supplied evidence, not inferred from payload size.
    This estimates JSON payload bytes, not total radio energy or link overhead.
    """
    integer(byte_budget, high=65536); number(maximum_mse, low=0, high=1e12)
    if not isinstance(options, dict) or not options or set(options) - {'raw', 'features', 'result'}:
        raise ValueError('known representation options required')
    rows = []
    for name, option in options.items():
        object_keys(option, {'payload', 'validation_mse', 'validation_id'})
        from codontrace.swarm.protocol import identifier
        identifier(option['validation_id']); number(option['validation_mse'], low=0, high=1e12)
        size = len(canonical(option['payload']).encode())
        rows.append({'operation': name, 'payload_bytes': size, 'validation_mse': option['validation_mse'],
                     'validation_id': option['validation_id'],
                     'eligible': size <= byte_budget and option['validation_mse'] <= maximum_mse})
    eligible = sorted((r for r in rows if r['eligible']), key=lambda r: (r['payload_bytes'], r['operation']))
    return {'selected': eligible[0]['operation'] if eligible else None, 'options': rows,
            'status': 'selected' if eligible else 'no_feasible_representation',
            'scope': 'caller_supplied_validation_and_json_payload_bytes'}
