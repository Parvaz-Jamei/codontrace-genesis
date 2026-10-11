"""Characterization: engine replay-contract pins in one place.

See docs/ENGINE_REPLAY_CONTRACT.md and docs/validation/LIFE_LOOP_DIGEST_HISTORY.md.
Probe: ``GenesisRuntimeProfile.life_loop_world(seed=7, tick_count=12, population=6)``.

* ``SPEC_DIGEST`` is the spec pin ``7d199ae5…``.
* ``HISTORICAL_SNAPSHOT_DIGEST`` (``76a5e62c…``) is the pre-aadc970 trajectory,
  reproduced with the documented counterfactual that uses the profile's
  population configs verbatim (never done in production runs).
* ``DEFAULT_SNAPSHOT_DIGEST`` (``e9d404a0…``) is today's default trajectory.
* The two ``*_RESULT_DIGEST`` values are new characterization pins of the full
  ``GenesisRunResult.digest()``; they contain no package version or host data.

These values are never loosened. A change needs a pin review under
ENGINE_REPLAY_CONTRACT.md.
"""
from __future__ import annotations

import pytest

from codontrace.engine import GenesisEngine
from codontrace.genesis.runtime_profiles import GenesisRuntimeProfile

SPEC_DIGEST = '7d199ae51345872215dbbb0c45cf8f141aacfb4c31d6537eda6de246c0cb7aac'
HISTORICAL_SNAPSHOT_DIGEST = '76a5e62cb0123b20a089adde25acd1cfb6dc460bdfab52f33ee460533d76f43a'
HISTORICAL_RESULT_DIGEST = '59d04908b93a4a51d3626db86b2d98e94f404beb991e4f36a354a86db29829e6'
DEFAULT_SNAPSHOT_DIGEST = 'e9d404a0a50c5ac323a94306d582bd27596a752ecab00bd9406834947d27db78'
DEFAULT_RESULT_DIGEST = '0d7e79f71595e100ddf8418a9891d2073e0e913e3d7bd51e34bf34dfc27c7508'


def _spec():
    return GenesisRuntimeProfile.life_loop_world(seed=7, tick_count=12, population=6)


def _run(*, historical: bool):
    spec = _spec()
    engine = GenesisEngine.from_spec(spec)
    if historical:
        engine.runner.configs = spec.population_configs  # documented counterfactual, see module docstring
    return engine.run_ticks()


def test_spec_digest_pin():
    assert _spec().digest() == SPEC_DIGEST


@pytest.mark.parametrize(('historical', 'snapshot_pin', 'result_pin'), [
    (False, DEFAULT_SNAPSHOT_DIGEST, DEFAULT_RESULT_DIGEST),
    (True, HISTORICAL_SNAPSHOT_DIGEST, HISTORICAL_RESULT_DIGEST),
], ids=['default', 'historical'])
def test_run_digest_pins_and_independent_replay(historical, snapshot_pin, result_pin):
    first = _run(historical=historical)
    assert first.snapshot.digest() == snapshot_pin
    assert first.digest() == result_pin
    replay = _run(historical=historical)  # independent re-execution, not the same object
    assert replay.digest() == first.digest()
    assert [t.digest() for t in replay.ticks] == [t.digest() for t in first.ticks]


def test_profile_not_aliased_by_runs():
    before = _spec().to_dict()
    _run(historical=True)
    assert _spec().to_dict() == before and _spec().digest() == SPEC_DIGEST
