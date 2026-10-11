"""Typed, bounded sensor descriptors and explicit host-side normalization.

Receipt support is separate from filter/inference support. No driver execution,
implicit physical conversion, or claimed calibration from caller metadata.
"""
from __future__ import annotations

import hashlib
from typing import Any

from codontrace.swarm.protocol import canonical, identifier, integer, number, object_keys, text

TYPES = frozenset({'scalar', 'vector', 'waveform', 'boolean', 'category'})
MODELS = frozenset({'direct', 'derived', 'proxy', 'raw'})


def descriptor(raw: Any) -> dict[str, Any]:
    d = object_keys(raw, {'value_type', 'measurement_model', 'feature_id', 'source_unit', 'config_id'},
                    {'axes', 'length', 'normalization', 'range', 'rate_hz', 'model_id', 'vendor', 'device_model', 'coordinate_frame', 'sample_period_us'})
    if d['value_type'] not in TYPES or d['measurement_model'] not in MODELS:
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


def normalize(payload: dict[str, Any], channel: dict[str, Any]) -> dict[str, Any]:
    d = descriptor(channel['descriptor']); p = dict(payload)
    source_unit = p.get('source_unit', d['source_unit'])
    if source_unit != d['source_unit']: raise ValueError('source unit differs from advertised descriptor')
    if p['config_id'] != d['config_id']: raise ValueError('sensor configuration mismatch')
    p['source_value'] = p['value']; p['source_unit'] = source_unit
    p['descriptor_digest'] = hashlib.sha256(canonical(d).encode()).hexdigest()
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
    d = frame.get('sensor_descriptor', {'value_type': 'scalar'})
    return d['value_type'] == 'scalar' and frame.get('valid', True) and type(frame.get('value')) in (int, float)


def fdc_sample(reading: dict[str, Any], *, variant: str, config_id: str) -> tuple[dict[str, Any], dict[str, Any]]:
    """Map host-provided FDCxCapSense reading fields; not a firmware driver.

    Original registers/configuration stay in metadata. Never reconstruct missing
    clock/LC data or turn a library error's zero placeholder into a valid value.
    """
    identifier(config_id)
    if variant not in ('FDC1004', 'FDC1004-Q1', 'FDC2212', 'FDC2214', 'FDC2112', 'FDC2114'):
        raise ValueError('unknown FDC variant')
    common = {'channel', 'status'}
    direct = variant.startswith('FDC1004')
    keys = {'raw24', 'capacitancePf', 'capdacCode', 'capdacEnabled', 'diagnosticFlags'} if direct else {'rawCode', 'frequencyHz', 'frefHz', 'finSelMultiplier', 'frefDivider', 'dataReady'}
    row = object_keys(reading, common | keys)
    integer(row['channel'], high=1 if variant.endswith('12') else 3);text(row['status'])
    if row['status'] not in {'Ok', 'I2cError', 'Timeout', 'InvalidArgument', 'DeviceNotFound', 'InvalidDeviceId', 'MeasurementNotReady', 'NotSupported'}:
        raise ValueError('unknown FDC status')
    valid = row['status'] == 'Ok'; metadata = {'variant': variant, 'library': 'FDCxCapSense', **row}
    if direct:
        if type(row['raw24']) is not int or not -(2**23) <= row['raw24'] < 2**23: raise ValueError('signed 24-bit FDC reading required')
        integer(row['capdacCode'], high=31);integer(row['diagnosticFlags'],high=65535)
        if type(row['capdacEnabled']) is not bool: raise ValueError('CAPDAC flag must be boolean')
        value = number(row['capacitancePf']) if valid else None
        channel = {'quantity': 'capacitance', 'unit': 'F', 'descriptor': {
            'value_type': 'scalar', 'measurement_model': 'direct', 'feature_id': 'fdc-electrode',
            'source_unit': 'pF', 'config_id': config_id, 'vendor': 'Texas Instruments', 'device_model': variant,
            'normalization': {'method': 'affine', 'scale': 1e-12, 'offset': 0., 'output_unit': 'F', 'evidence_id': 'SI-prefix'}}}
    else:
        integer(row['rawCode'],high=(2**12-1 if variant.startswith('FDC211') else 2**28-1))
        # CHx_FIN_SEL: b01 = divide by 1, b10 = divide by 2; b11 is reserved (FDC2x1x datasheet,
        # CLOCK_DIVIDERS_CHx). FDCxCapSense reports the multiplier (1 or 2), 0 when unread.
        number(row['frequencyHz']);number(row['frefHz'],low=0);integer(row['finSelMultiplier'],high=2);integer(row['frefDivider'],high=1023)
        if type(row['dataReady']) is not bool: raise ValueError('dataReady must be boolean')
        if variant.startswith('FDC211') and valid: raise ValueError('FDC211x frequency conversion is not supported in FDCxCapSense 0.6.13')
        valid = valid and row['dataReady']
        if valid and (row['frefHz'] <= 0 or row['frequencyHz'] <= 0 or row['finSelMultiplier'] not in (1,2) or row['frefDivider'] < 1):
            raise ValueError('valid resonant frequency requires clock/multiplier metadata')
        value = number(row['frequencyHz']) if valid else None
        channel = {'quantity': 'frequency', 'unit': 'Hz', 'descriptor': {'value_type': 'scalar',
            'measurement_model': 'derived', 'model_id': 'FDC2x1x-reference-clock', 'feature_id': 'fdc-electrode',
            'source_unit': 'Hz', 'config_id': config_id, 'vendor': 'Texas Instruments', 'device_model': variant}}
    return channel, {'value': value, 'valid': valid, 'status': 'ok' if valid else row['status'] if row['status'] != 'Ok' else 'not_ready',
                     'config_id': config_id, 'metadata': metadata}
