"""P4: codontrace.contracts.channels and swarm.adapters.fdc behave exactly like the old swarm.sensors.

``tests/_ref_swarm_sensors.py`` is a verbatim copy of ``swarm/sensors.py`` before the move.
Results, error types and messages, and descriptor digests must match it.
"""
from __future__ import annotations

import ast
import hashlib
from pathlib import Path

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

import tests._ref_swarm_sensors as ref
from codontrace.contracts import channels
from codontrace.contracts.channels import ChannelDescriptor, Normalization
from codontrace.swarm import sensors
from codontrace.swarm.adapters import fdc
from codontrace.swarm.protocol import canonical

ROOT = Path(__file__).resolve().parents[1]


def outcome(fn, *args, **kwargs):
    try:
        return ('ok', fn(*args, **kwargs))
    except Exception as error:  # noqa: BLE001 - the comparison includes the type and message
        return ('error', type(error).__name__, str(error))


def test_shim_names_are_the_moved_objects():
    assert sensors.descriptor is channels.validate_descriptor
    assert sensors.normalize is channels.normalize_sample
    assert sensors.typed_value is channels.typed_value
    assert sensors.scalar_frame is channels.scalar_frame
    assert sensors.TYPES is channels.VALUE_TYPES and sensors.MODELS is channels.MEASUREMENT_MODELS
    assert sensors.fdc_sample is fdc.fdc_sample
    assert channels.VALUE_TYPES == ref.TYPES and channels.MEASUREMENT_MODELS == ref.MODELS
    assert not hasattr(sensors, '__all__')  # star-import behaviour unchanged


scalar = st.one_of(st.none(), st.booleans(), st.integers(-10, 300), st.floats(allow_nan=True, allow_infinity=True),
                   st.sampled_from(['', ' ', 'degC', 'Hz', 'cfg1', 'x' * 97, 'bad id', 'raw']))
numbers = st.one_of(st.integers(-5, 5), st.floats(-10, 10, allow_nan=False), st.just(0), st.booleans())
pairs = st.one_of(st.lists(numbers, min_size=0, max_size=3), scalar)
knots = st.one_of(st.lists(st.lists(numbers, min_size=2, max_size=2), min_size=0, max_size=5), scalar)
normalizations = st.one_of(
    st.fixed_dictionaries({'method': st.sampled_from(['affine', 'table', 'log']), 'output_unit': st.sampled_from(['K', 'degC', '']),
                           'evidence_id': st.sampled_from(['bench1', 'bad id'])},
                          optional={'scale': numbers, 'offset': numbers, 'knots': knots}),
    scalar)
descriptors = st.fixed_dictionaries(
    {'value_type': st.sampled_from(sorted(ref.TYPES) + ['matrix']),
     'measurement_model': st.sampled_from(sorted(ref.MODELS) + ['guess']),
     'feature_id': st.sampled_from(['room', 'bad id', '']), 'source_unit': st.sampled_from(['degC', 'Hz', '']),
     'config_id': st.sampled_from(['cfg1', '-x'])},
    optional={'axes': st.one_of(st.lists(st.sampled_from(['x', 'y', 'z', 'bad id']), max_size=4), scalar),
              'length': st.one_of(st.integers(-1, 300), scalar), 'normalization': normalizations, 'range': pairs,
              'rate_hz': pairs, 'model_id': st.sampled_from(['m1', '']), 'vendor': st.sampled_from(['acme', '']),
              'device_model': st.sampled_from(['d1']), 'coordinate_frame': st.sampled_from(['body']),
              'sample_period_us': st.one_of(st.integers(-1, 10), scalar), 'extra': scalar})


@settings(max_examples=1500, deadline=None)
@given(descriptors)
def test_validate_descriptor_matches_reference(raw):
    got, want = outcome(channels.validate_descriptor, raw), outcome(ref.descriptor, raw)
    assert got == want
    if got[0] == 'ok':
        d = got[1]
        expected_digest = hashlib.sha256(canonical(d).encode()).hexdigest()
        assert channels.descriptor_digest(d) == expected_digest
        typed = ChannelDescriptor.from_dict(raw)
        assert typed.to_dict() == d and typed.digest() == expected_digest
        assert ChannelDescriptor.from_dict(typed.to_dict()) == typed


VALID = [
    {'value_type': 'scalar', 'measurement_model': 'direct', 'feature_id': 'room', 'source_unit': 'degC', 'config_id': 'c1'},
    {'value_type': 'scalar', 'measurement_model': 'direct', 'feature_id': 'room', 'source_unit': 'degC', 'config_id': 'c1',
     'range': [-40, 125], 'normalization': {'method': 'affine', 'output_unit': 'K', 'evidence_id': 'b1',
                                            'scale': 1, 'offset': 273.15}},
    {'value_type': 'scalar', 'measurement_model': 'derived', 'model_id': 'm', 'feature_id': 'f', 'source_unit': 'V',
     'config_id': 'c1', 'normalization': {'method': 'table', 'output_unit': 'degC', 'evidence_id': 'b1',
                                          'knots': [[0, -10], [1.5, 20], [3.3, 80]]}},
    {'value_type': 'vector', 'measurement_model': 'raw', 'feature_id': 'imu', 'source_unit': 'g', 'config_id': 'c1',
     'axes': ['x', 'y', 'z'], 'range': [-2, 2]},
    {'value_type': 'waveform', 'measurement_model': 'raw', 'feature_id': 'mic', 'source_unit': 'arb', 'config_id': 'c1',
     'length': 4, 'sample_period_us': 125,
     'normalization': {'method': 'affine', 'output_unit': 'Pa', 'evidence_id': 'b1', 'scale': -0.5, 'offset': 0}},
    {'value_type': 'boolean', 'measurement_model': 'direct', 'feature_id': 'door', 'source_unit': 'state', 'config_id': 'c1'},
    {'value_type': 'category', 'measurement_model': 'proxy', 'model_id': 'm', 'feature_id': 'mode', 'source_unit': 'label',
     'config_id': 'c1'},
]
UNITS = {0: 'degC', 1: 'K', 2: 'degC', 3: 'g', 4: 'Pa', 5: 'state', 6: 'label'}
DESCRIPTOR_KEYS = sorted({k for d in VALID for k in d} | {'rate_hz', 'vendor', 'coordinate_frame', 'device_model'})


def _mutate(index, key, value, drop):
    d = {k: (dict(v) if isinstance(v, dict) else v) for k, v in VALID[index].items()}
    if key is not None:
        if drop:
            d.pop(key, None)
        else:
            d[key] = value
    return d


near_valid = st.builds(_mutate, st.integers(0, len(VALID) - 1), st.one_of(st.none(), st.sampled_from(DESCRIPTOR_KEYS)),
                       st.one_of(scalar, numbers, pairs, normalizations, st.lists(st.sampled_from(['x', 'y']), max_size=3)),
                       st.booleans())


@settings(max_examples=1500, deadline=None)
@given(near_valid)
def test_validate_descriptor_matches_reference_near_valid(raw):
    test_validate_descriptor_matches_reference.hypothesis.inner_test(raw)
values = st.one_of(st.none(), st.booleans(), st.floats(-100, 400, allow_nan=False), st.integers(-5, 5),
                   st.floats(-1, 3.3), st.lists(st.floats(-3, 3, allow_nan=False), min_size=2, max_size=5),
                   st.lists(st.floats(-1, 1), min_size=3, max_size=4), st.sampled_from(['on', 'x' * 129]))


@settings(max_examples=1500, deadline=None)
@given(st.integers(0, len(VALID) - 1), values, st.sampled_from([True, True, True, False]),
       st.sampled_from(['ok', 'ok', 'ok', 'fault']), st.sampled_from(['c1', 'c1', 'c1', 'c2']),
       st.one_of(st.none(), st.none(), st.none(), st.sampled_from(['degC', 'V', 'g'])),
       st.one_of(st.none(), st.none(), st.fixed_dictionaries({'standard': st.floats(0, 2), 'unit': st.sampled_from(['degC', 'V']),
                                                   'evidence_id': st.just('u1')})))
def test_normalize_sample_matches_reference(index, value, valid, status, config_id, source_unit, uncertainty):
    channel = {'quantity': 'q', 'unit': UNITS[index], 'descriptor': VALID[index]}
    payload = {'value': value, 'valid': valid, 'status': status, 'config_id': config_id}
    if source_unit is not None:
        payload['source_unit'] = source_unit
    if uncertainty is not None:
        payload['uncertainty'] = uncertainty
    assert outcome(channels.normalize_sample, payload, channel) == outcome(ref.normalize, payload, channel)
    assert outcome(channels.typed_value, value, VALID[index]) == outcome(ref.typed_value, value, VALID[index])


@pytest.mark.parametrize('index', [1, 2, 4])
@settings(max_examples=300, deadline=None)
@given(value=st.floats(-50, 150, allow_nan=False))
def test_normalization_apply_matches_normalize_sample(index, value):
    n = Normalization.from_dict(VALID[index]['normalization'])
    assert n.to_dict() == VALID[index]['normalization']
    descriptor = {k: v for k, v in VALID[index].items() if k not in ('range', 'length', 'sample_period_us')}
    descriptor['value_type'] = 'scalar'
    channel = {'quantity': 'q', 'unit': UNITS[index], 'descriptor': descriptor}
    sample = outcome(channels.normalize_sample, {'value': value, 'valid': True, 'status': 'ok', 'config_id': 'c1'}, channel)
    applied = outcome(n.apply, value)
    assert (applied[0], applied[1:]) == (sample[0], (sample[1]['value'],) if sample[0] == 'ok' else sample[1:])


def test_channel_descriptor_typed_view():
    d = ChannelDescriptor.from_dict(VALID[3])
    assert d.numeric and d.shape == (3,) and d.axes == ('x', 'y', 'z') and d.value_range == (-2, 2)
    w = ChannelDescriptor.from_dict(VALID[4])
    assert w.shape == (4,) and w.normalization == Normalization('affine', 'Pa', 'b1', scale=-0.5, offset=0)
    assert ChannelDescriptor.from_dict(VALID[5]).shape == () and not ChannelDescriptor.from_dict(VALID[5]).numeric
    with pytest.raises(ValueError, match='derived/proxy sensor requires model provenance'):
        ChannelDescriptor.from_dict({**VALID[0], 'measurement_model': 'proxy'})
    with pytest.raises(ValueError):
        Normalization.from_dict({'method': 'affine', 'output_unit': 'K', 'evidence_id': 'b1', 'scale': 0, 'offset': 1})


FDC_ROWS = [
    ('FDC1004', {'channel': 0, 'status': 'Ok', 'raw24': 1234, 'capacitancePf': 3.125, 'capdacCode': 0,
                 'capdacEnabled': False, 'diagnosticFlags': 0}),
    ('FDC1004-Q1', {'channel': 3, 'status': 'Timeout', 'raw24': 0, 'capacitancePf': 0.0, 'capdacCode': 31,
                    'capdacEnabled': True, 'diagnosticFlags': 65535}),
    ('FDC2214', {'channel': 1, 'status': 'Ok', 'rawCode': 1000, 'frequencyHz': 2.5e6, 'frefHz': 4e7,
                 'finSelMultiplier': 2, 'frefDivider': 1, 'dataReady': True}),
    ('FDC2112', {'channel': 1, 'status': 'Ok', 'rawCode': 1000, 'frequencyHz': 2.5e6, 'frefHz': 4e7,
                 'finSelMultiplier': 1, 'frefDivider': 1, 'dataReady': True}),
    ('FDC2114', {'channel': 2, 'status': 'MeasurementNotReady', 'rawCode': 0, 'frequencyHz': 0, 'frefHz': 0,
                 'finSelMultiplier': 0, 'frefDivider': 0, 'dataReady': False}),
]


@settings(max_examples=800, deadline=None)
@given(st.integers(0, len(FDC_ROWS) - 1), st.sampled_from(['', 'raw24', 'status', 'channel', 'frefHz', 'dataReady',
                                                           'capdacEnabled', 'finSelMultiplier', 'extra']),
       st.one_of(st.none(), st.booleans(), st.integers(-2**24, 2**24), st.floats(-1, 1e7, allow_nan=False),
                 st.sampled_from(['Ok', 'I2cError', 'Weird'])),
       st.sampled_from([None, 'FDC1004', 'FDC2214', 'FDC2212', 'FDC9999']), st.sampled_from(['c1', 'bad id']))
def test_fdc_sample_matches_reference(index, key, value, variant_override, config_id):
    variant, row = FDC_ROWS[index]
    row = dict(row)
    if key:
        row[key] = value
    variant = variant_override or variant
    got = outcome(fdc.fdc_sample, row, variant=variant, config_id=config_id)
    assert got == outcome(ref.fdc_sample, row, variant=variant, config_id=config_id)
    if got[0] == 'ok':
        channel, payload = got[1]
        assert outcome(channels.normalize_sample, payload, channel) == outcome(ref.normalize, payload, channel)


def test_contracts_channels_is_domain_free_and_engine_free():
    path = ROOT / 'src' / 'codontrace' / 'contracts' / 'channels.py'
    source = path.read_text(encoding='utf-8')
    assert 'fdc' not in source.lower() and 'texas' not in source.lower()
    imported = {n.module for n in ast.walk(ast.parse(source)) if isinstance(n, ast.ImportFrom)}
    assert {m for m in imported if m and m.startswith('codontrace')} == {'codontrace.contracts.wire_validation'}
