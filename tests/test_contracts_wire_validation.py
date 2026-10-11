"""contracts.wire_validation is byte- and error-identical to the validators it replaced.

The reference implementations below are verbatim copies of the functions that
lived in ``codontrace.swarm.protocol`` up to v0.3.0b30. Journals, checkpoints
and their hash links depend on ``wire_canonical`` bytes, so any divergence is a
format change.
"""
from __future__ import annotations

import json
import math
import re
from collections.abc import Mapping
from typing import Any

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from codontrace.contracts import wire_validation as wv
from codontrace.swarm import protocol


def ref_identifier(value: Any) -> str:
    if not isinstance(value, str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,63}', value):
        raise ValueError('invalid identifier')
    return value


def ref_number(value: Any, *, low: float = -1e12, high: float = 1e12) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError('finite number required')
    if not low <= value <= high:
        raise ValueError('number outside supported range')
    if not math.isfinite(value):
        raise ValueError('finite number required')
    return float(value)


def ref_integer(value: Any, *, high: int = 2**53 - 1) -> int:
    if type(value) is not int or not 0 <= value <= high:
        raise ValueError('bounded nonnegative integer required')
    return value


def ref_text(value: Any, maximum: int = 96) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > maximum:
        raise ValueError('bounded nonempty string required')
    return value


def ref_object_keys(value: Any, required: set[str], optional: set[str] | None = None) -> dict[str, Any]:
    if not isinstance(value, Mapping) or not required <= value.keys() or value.keys() - required - (optional or set()):
        raise ValueError('missing or unknown fields')
    return dict(value)


def ref_canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False)


def outcome(fn, *args, **kwargs):
    try:
        result = fn(*args, **kwargs)
    except Exception as exc:  # compare type and message, never swallow silently
        return ('raise', type(exc), str(exc))
    return ('ok', type(result), result if not (isinstance(result, float) and math.isnan(result)) else 'nan')


scalars = (st.none() | st.booleans() | st.integers(min_value=-(2**80), max_value=2**80)
           | st.floats(allow_nan=True, allow_infinity=True) | st.text(max_size=80)
           | st.sampled_from(['a', 'A0', 'node-1', 'x' * 64, 'x' * 65, '_a', '-a', '0_', ' a', 'ä1', '', '  ', 'a\n']))
json_values = st.recursive(
    st.none() | st.booleans() | st.integers(min_value=-(2**70), max_value=2**70)
    | st.floats(allow_nan=False, allow_infinity=False) | st.text(),
    lambda inner: st.lists(inner, max_size=5) | st.dictionaries(st.text(max_size=8), inner, max_size=5),
    max_leaves=25)


def test_protocol_names_are_the_shared_objects():
    assert protocol.identifier is wv.identifier
    assert protocol.number is wv.finite_number
    assert protocol.integer is wv.bounded_int
    assert protocol.text is wv.bounded_text
    assert protocol.object_keys is wv.exact_keys
    assert protocol.canonical is wv.wire_canonical


@settings(max_examples=400, deadline=None)
@given(scalars)
def test_scalar_validators_match_reference(value):
    assert outcome(wv.identifier, value) == outcome(ref_identifier, value)
    assert outcome(wv.finite_number, value) == outcome(ref_number, value)
    assert outcome(wv.finite_number, value, low=0, high=1) == outcome(ref_number, value, low=0, high=1)
    assert outcome(wv.bounded_int, value) == outcome(ref_integer, value)
    assert outcome(wv.bounded_int, value, high=10) == outcome(ref_integer, value, high=10)
    assert outcome(wv.bounded_text, value) == outcome(ref_text, value)
    assert outcome(wv.bounded_text, value, 3) == outcome(ref_text, value, 3)


@settings(max_examples=200, deadline=None)
@given(st.dictionaries(st.sampled_from(['a', 'b', 'c', 'd']), st.integers(), max_size=4) | scalars)
def test_exact_keys_matches_reference(value):
    for required, optional in (({'a'}, None), ({'a', 'b'}, {'c'}), (set(), {'d'})):
        assert outcome(wv.exact_keys, value, required, optional) == outcome(ref_object_keys, value, required, optional)


@settings(max_examples=400, deadline=None)
@given(json_values)
def test_wire_canonical_is_byte_identical(value):
    assert wv.wire_canonical(value).encode() == ref_canonical(value).encode()


@pytest.mark.parametrize('value', [
    {'\U0001F600': 1, '\uFFFD': 2, 'é': 3, 'Z': 4, 'a': 5},
    [2**63, -(2**64), 2**200, 1e-7, 1e21, 0.1, -0.0, 1.0],
    {'nested': {'b': [1, {'z': None, 'y': True}], 'a': 'line\nbreak\u2028'}},
])
def test_wire_canonical_edge_cases(value):
    assert wv.wire_canonical(value) == ref_canonical(value)


@pytest.mark.parametrize('bad', [math.nan, math.inf, -math.inf, {'x': [math.nan]}])
def test_wire_canonical_rejects_non_finite(bad):
    with pytest.raises(ValueError):
        wv.wire_canonical(bad)
    with pytest.raises(ValueError):
        ref_canonical(bad)


def test_hostile_integers_do_not_overflow():
    assert outcome(wv.finite_number, 10**400) == ('raise', ValueError, 'number outside supported range')
