"""Typed observation-channel descriptors and explicit sample normalization.

Domain-free channel contract, the analogue of Gymnasium spaces or
ros2_control state interfaces: a descriptor states the value type
(scalar/vector/waveform/boolean/category), how the value relates to the
measured quantity (direct/derived/proxy/raw), its source unit, bounds and an
optional explicit normalization (affine or monotone table). Receipt support is
separate from filter/inference support. No implicit unit conversion, no
extrapolation, and no calibration claimed from caller metadata.

The dict functions are the validated wire form used by journals;
``ChannelDescriptor`` and ``Normalization`` are typed views over the same
data whose ``to_dict()`` returns that form and whose ``digest()`` equals
``descriptor_digest``.
"""
from __future__ import annotations

import hashlib
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from codontrace.contracts.wire_validation import bounded_int as integer
from codontrace.contracts.wire_validation import bounded_text as text
from codontrace.contracts.wire_validation import exact_keys as object_keys
from codontrace.contracts.wire_validation import finite_number as number
from codontrace.contracts.wire_validation import identifier, wire_canonical

__all__ = ['MEASUREMENT_MODELS', 'NORMALIZATION_METHODS', 'VALUE_TYPES', 'ChannelDescriptor', 'Normalization',
           'descriptor_digest', 'normalize_sample', 'scalar_frame', 'typed_value', 'validate_descriptor']

VALUE_TYPES = frozenset({'scalar', 'vector', 'waveform', 'boolean', 'category'})
MEASUREMENT_MODELS = frozenset({'direct', 'derived', 'proxy', 'raw'})
NORMALIZATION_METHODS = frozenset({'affine', 'table'})


def descriptor_digest(d: Mapping[str, Any]) -> str:
    """SHA-256 hex of the canonical wire form of a validated descriptor."""
    return hashlib.sha256(wire_canonical(d).encode()).hexdigest()


def validate_descriptor(raw: Any) -> dict[str, Any]:
    """Validate a channel descriptor mapping; returns a shallow copy with the same values."""
    d = object_keys(raw, {'value_type', 'measurement_model', 'feature_id', 'source_unit', 'config_id'},
                    {'axes', 'length', 'normalization', 'range', 'rate_hz', 'model_id', 'vendor', 'device_model', 'coordinate_frame', 'sample_period_us'})
    if d['value_type'] not in VALUE_TYPES or d['measurement_model'] not in MEASUREMENT_MODELS:
        raise ValueError('unsupported value type or measurement model')
    for key in ('feature_id', 'config_id'): identifier(d[key])
    for key in ('source_unit', 'model_id', 'vendor', 'device_model', 'coordinate_frame'):
        if key in d: text(d[key])
    if d['measurement_model'] in ('derived', 'proxy') and 'model_id' not in d:
        raise ValueError('derived/proxy sensor requires model provenance')
    if d['value_type'] == 'vector':
        axes = d.get('axes')
        if not isinstance(axes, list) or not 1 <= len(axes) <= 16 or len(set(axes)) != len(axes):
            raise ValueError('1..16 unique vector axes required')
        for axis in axes: identifier(axis)
    elif 'axes' in d: raise ValueError('axes require vector data')
    if d['value_type'] == 'waveform':
        if not integer(d.get('length'), high=256) >= 1: raise ValueError('bounded waveform length required')
    elif 'length' in d: raise ValueError('length requires waveform data')
    if 'sample_period_us' in d:
        if d['value_type'] != 'waveform' or integer(d['sample_period_us'], high=3600000000) < 1:
            raise ValueError('positive waveform sample period required')
    numeric = d['value_type'] in ('scalar', 'vector', 'waveform')
    for key in ('range', 'rate_hz'):
        if key in d:
            pair = d[key]
            if not isinstance(pair, list) or len(pair) != 2: raise ValueError('two range limits required')
            lo, hi = (number(v) for v in pair)
            if lo > hi or (key == 'rate_hz' and (lo <= 0 or hi > 10000)):
                raise ValueError('invalid descriptor limits')
            if key == 'range' and not numeric: raise ValueError('numeric range on nonnumeric data')
    if 'normalization' in d:
        if not numeric: raise ValueError('normalization requires numeric data')
        n = object_keys(d['normalization'], {'method', 'output_unit', 'evidence_id'}, {'scale', 'offset', 'knots'})
        text(n['output_unit']);identifier(n['evidence_id'])
        if n['method'] == 'affine':
            if set(n) != {'method', 'output_unit', 'evidence_id', 'scale', 'offset'}: raise ValueError('affine coefficients required')
            if number(n['scale']) == 0: raise ValueError('nonzero normalization scale required')
            number(n['offset'])
        elif n['method'] == 'table':
            if set(n) != {'method', 'output_unit', 'evidence_id', 'knots'}: raise ValueError('table knots required')
            knots = n['knots']
            if not isinstance(knots, list) or not 2 <= len(knots) <= 64: raise ValueError('2..64 table knots required')
            previous = None
            for point in knots:
                if not isinstance(point, list) or len(point) != 2: raise ValueError('paired knots required')
                x, _ = (number(v) for v in point)
                if previous is not None and x <= previous: raise ValueError('table input coordinates must increase')
                previous = x
        else: raise ValueError('unknown normalization method')
    return d


def typed_value(value: Any, d: dict[str, Any]) -> Any:
    """Check one raw value against the descriptor's value type and shape."""
    kind = d['value_type']
    if kind == 'scalar': return number(value)
    if kind in ('vector', 'waveform'):
        length = len(d['axes']) if kind == 'vector' else d['length']
        if not isinstance(value, list) or len(value) != length: raise ValueError('sensor shape mismatch')
        return [number(v) for v in value]
    if kind == 'boolean':
        if type(value) is not bool: raise ValueError('boolean sensor requires boolean value')
        return value
    return text(value, 128)


def normalize_sample(payload: dict[str, Any], channel: dict[str, Any]) -> dict[str, Any]:
    """Type-check, normalize and range-check one sample against ``channel['descriptor']``.

    Adds ``source_value``, ``descriptor_digest`` and ``sensor_descriptor``. A unit
    change needs an explicit normalization; table normalization never extrapolates.
    """
    d = validate_descriptor(channel['descriptor']); p = dict(payload)
    source_unit = p.get('source_unit', d['source_unit'])
    if source_unit != d['source_unit']: raise ValueError('source unit differs from advertised descriptor')
    if p['config_id'] != d['config_id']: raise ValueError('sensor configuration mismatch')
    p['source_value'] = p['value']; p['source_unit'] = source_unit
    p['descriptor_digest'] = descriptor_digest(d)
    p['sensor_descriptor'] = d
    n = d.get('normalization')
    if (n['output_unit'] if n else source_unit) != channel['unit']:
        raise ValueError('explicit normalization required for unit conversion')
    if not p['valid']:
        if p['value'] is not None: raise ValueError('invalid sensor must carry null value')
        p['quality'] = 0.
        return p
    if p['status'] != 'ok': raise ValueError('valid sample requires ok status')
    value = typed_value(p['value'], d)
    def transform(v: float) -> float:
        if n is None: return v
        if n['method'] == 'affine': return number(n['scale'] * v + n['offset'])
        points = n['knots']
        if not points[0][0] <= v <= points[-1][0]: raise ValueError('calibration table extrapolation forbidden')
        for (a, b), (c, e) in zip(points, points[1:], strict=False):
            if a <= v <= c: return number(b + (e-b)*(v-a)/(c-a))
        raise ValueError('calibration table has no interval')
    if d['value_type'] == 'scalar': value = transform(value)
    elif d['value_type'] in ('vector', 'waveform'): value = [transform(v) for v in value]
    if 'range' in d:
        numbers = value if isinstance(value, list) else [value]
        if any(not d['range'][0] <= v <= d['range'][1] for v in numbers):
            raise ValueError('normalized sensor value outside configured range')
    p['value'] = value
    if 'uncertainty' in p:
        u = object_keys(p['uncertainty'], {'standard', 'unit', 'evidence_id'})
        number(u['standard'], low=0);text(u['unit']);identifier(u['evidence_id'])
        if u['unit'] != source_unit or d['value_type'] != 'scalar': raise ValueError('scalar source-unit uncertainty required')
        if n and n['method'] != 'affine': raise ValueError('nonlinear uncertainty needs an explicit propagation model')
        p['uncertainty'] = {**u, 'standard': number(u['standard'] * abs(n['scale'] if n else 1), low=0), 'unit': channel['unit']}
    return p


def scalar_frame(frame: dict[str, Any]) -> bool:
    """True for a valid scalar numeric sample (frames without a descriptor count as scalar)."""
    d = frame.get('sensor_descriptor', {'value_type': 'scalar'})
    return d['value_type'] == 'scalar' and frame.get('valid', True) and type(frame.get('value')) in (int, float)


Number = int | float


@dataclass(frozen=True, slots=True)
class Normalization:
    """Explicit affine (``scale * v + offset``) or table (piecewise-linear) normalization."""

    method: str
    output_unit: str
    evidence_id: str
    scale: Number | None = None
    offset: Number | None = None
    knots: tuple[tuple[Number, Number], ...] | None = None

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {'method': self.method, 'output_unit': self.output_unit, 'evidence_id': self.evidence_id}
        if self.method == 'affine':
            out['scale'] = self.scale
            out['offset'] = self.offset
        else:
            out['knots'] = [list(point) for point in self.knots or ()]
        return out

    @classmethod
    def from_dict(cls, raw: Any) -> Normalization:
        """Validate through a minimal numeric descriptor, so rules match ``validate_descriptor``."""
        validate_descriptor({'value_type': 'scalar', 'measurement_model': 'raw', 'feature_id': 'x', 'source_unit': 'x',
                             'config_id': 'x', 'normalization': raw})
        return cls._from_valid(raw)

    @classmethod
    def _from_valid(cls, n: Mapping[str, Any]) -> Normalization:
        if n['method'] == 'affine':
            return cls(n['method'], n['output_unit'], n['evidence_id'], scale=n['scale'], offset=n['offset'])
        return cls(n['method'], n['output_unit'], n['evidence_id'],
                   knots=tuple((point[0], point[1]) for point in n['knots']))

    def apply(self, value: float) -> float:
        """Normalize one source value; same arithmetic and errors as ``normalize_sample``."""
        if self.method == 'affine':
            return number(self.scale * value + self.offset)  # type: ignore[operator]
        points = self.knots or ()
        if not points[0][0] <= value <= points[-1][0]:
            raise ValueError('calibration table extrapolation forbidden')
        for (a, b), (c, e) in zip(points, points[1:], strict=False):
            if a <= value <= c:
                return number(b + (e - b) * (value - a) / (c - a))
        raise ValueError('calibration table has no interval')


_OPTIONAL_TEXT = ('model_id', 'vendor', 'device_model', 'coordinate_frame')


@dataclass(frozen=True, slots=True)
class ChannelDescriptor:
    """Typed, validated view of a channel descriptor. Build with ``from_dict``."""

    value_type: str
    measurement_model: str
    feature_id: str
    source_unit: str
    config_id: str
    axes: tuple[str, ...] | None = None
    length: int | None = None
    value_range: tuple[Number, Number] | None = None
    rate_hz: tuple[Number, Number] | None = None
    normalization: Normalization | None = None
    model_id: str | None = None
    vendor: str | None = None
    device_model: str | None = None
    coordinate_frame: str | None = None
    sample_period_us: int | None = None

    @classmethod
    def from_dict(cls, raw: Any) -> ChannelDescriptor:
        d = validate_descriptor(raw)
        return cls(
            value_type=d['value_type'], measurement_model=d['measurement_model'], feature_id=d['feature_id'],
            source_unit=d['source_unit'], config_id=d['config_id'],
            axes=tuple(d['axes']) if 'axes' in d else None,
            length=d.get('length'),
            value_range=(d['range'][0], d['range'][1]) if 'range' in d else None,
            rate_hz=(d['rate_hz'][0], d['rate_hz'][1]) if 'rate_hz' in d else None,
            normalization=Normalization._from_valid(d['normalization']) if 'normalization' in d else None,
            sample_period_us=d.get('sample_period_us'),
            **{key: d.get(key) for key in _OPTIONAL_TEXT},
        )

    def to_dict(self) -> dict[str, Any]:
        """The wire form; ``validate_descriptor(x.to_dict()) == x.to_dict()``."""
        out: dict[str, Any] = {'value_type': self.value_type, 'measurement_model': self.measurement_model,
                               'feature_id': self.feature_id, 'source_unit': self.source_unit,
                               'config_id': self.config_id}
        if self.axes is not None:
            out['axes'] = list(self.axes)
        if self.length is not None:
            out['length'] = self.length
        if self.value_range is not None:
            out['range'] = list(self.value_range)
        if self.rate_hz is not None:
            out['rate_hz'] = list(self.rate_hz)
        if self.normalization is not None:
            out['normalization'] = self.normalization.to_dict()
        for key in _OPTIONAL_TEXT:
            value = getattr(self, key)
            if value is not None:
                out[key] = value
        if self.sample_period_us is not None:
            out['sample_period_us'] = self.sample_period_us
        return out

    def digest(self) -> str:
        return descriptor_digest(self.to_dict())

    @property
    def numeric(self) -> bool:
        return self.value_type in ('scalar', 'vector', 'waveform')

    @property
    def shape(self) -> tuple[int, ...]:
        """``()`` for single values, ``(n,)`` for vectors and waveforms."""
        if self.value_type == 'vector':
            return (len(self.axes or ()),)
        if self.value_type == 'waveform':
            return (int(self.length or 0),)
        return ()
