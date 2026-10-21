"""The chain's run-reference and QD-parameter hashes use genesis.canonical; prove the bytes match the old helper."""
from __future__ import annotations

import hashlib
import json

from hypothesis import given, settings
from hypothesis import strategies as st

from codontrace.genesis import qd_parametric, run_refs
from codontrace.genesis.canonical import canonical_json


def _old(payload):
    """The helper both modules used before (verbatim)."""
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(',', ':'),
                                     allow_nan=False).encode()).hexdigest()


_scalars = (st.none() | st.booleans() | st.integers(-2**70, 2**70)
            | st.floats(allow_nan=False, allow_infinity=False) | st.text())
_json = st.recursive(_scalars, lambda inner: st.lists(inner, max_size=5) | st.tuples(inner, inner)
                     | st.dictionaries(st.text(), inner, max_size=5), max_leaves=30)


@settings(max_examples=500, deadline=None)
@given(_json)
def test_bytes_identical_for_string_keyed_json(payload):
    assert canonical_json(payload).encode() == json.dumps(payload, sort_keys=True, separators=(',', ':'),
                                                          allow_nan=False).encode()
    assert run_refs._sha256_json(payload) == _old(payload)
    assert qd_parametric._digest(payload) == _old(payload)


def test_real_payloads_are_identical():
    from codontrace.swarm.coevolution import DEFENDER_SPACE
    from codontrace.swarm.policies import PIPELINE_SPACE
    payloads = [PIPELINE_SPACE.to_dict(), DEFENDER_SPACE.to_dict(), {'x': [1, 2.5, 'é', None, True]}]
    for payload in payloads:
        assert qd_parametric._digest(payload) == _old(payload)
        assert run_refs._sha256_json(payload) == _old(payload)


def test_non_finite_still_raises_value_error():
    import pytest
    for helper in (run_refs._sha256_json, qd_parametric._digest):
        with pytest.raises(ValueError):
            helper({'x': float('nan')})
