"""Characterization: engine replay-contract pins in one place.

See docs/ENGINE_REPLAY_CONTRACT.md and docs/validation/LIFE_LOOP_DIGEST_HISTORY.md.
Probe: ``GenesisRuntimeProfile.life_loop_world(seed=7, tick_count=12, population=6)``.

* ``SPEC_DIGEST`` is the spec pin ``7d199ae5…``.
* ``HISTORICAL_SNAPSHOT_DIGEST`` (``76a5e62c…``) is the pre-aadc970 trajectory,
  reproduced with the documented counterfactual that uses the profile's
  population configs verbatim (never done in production runs).
* ``DEFAULT_SNAPSHOT_DIGEST`` (``e9d404a0…``) is today's default trajectory.
* The two ``*_RESULT_DIGEST`` values are characterization pins of the full
  ``GenesisRunResult.digest()``, computed with a neutral source identity
  (``neutral_source_digest`` fixture): the real manifest ``source_digest``
  hashes the checkout itself, so it changes with every source edit.

These values are never loosened. A change needs a pin review under
ENGINE_REPLAY_CONTRACT.md.
"""
from __future__ import annotations

import pytest

from codontrace.engine import GenesisEngine
from codontrace.genesis.runtime_profiles import GenesisRuntimeProfile

SPEC_DIGEST = '7d199ae51345872215dbbb0c45cf8f141aacfb4c31d6537eda6de246c0cb7aac'
HISTORICAL_SNAPSHOT_DIGEST = '76a5e62cb0123b20a089adde25acd1cfb6dc460bdfab52f33ee460533d76f43a'
HISTORICAL_RESULT_DIGEST = '5c52a107779aa9166897dfbd81a41e9bf026c2f63592c12f82a062842786c766'
DEFAULT_SNAPSHOT_DIGEST = 'e9d404a0a50c5ac323a94306d582bd27596a752ecab00bd9406834947d27db78'
DEFAULT_RESULT_DIGEST = 'c3bd98eb09f2515778fd44671fff9c9631125098070f3da9b7c13ca28014cdd7'


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
def test_run_digest_pins_and_independent_replay(historical, snapshot_pin, result_pin, neutral_source_digest):
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


def test_result_digest_source_identity_is_neutralized(neutral_source_digest):
    from codontrace.genesis.artifacts import compute_source_digest
    result = GenesisEngine.from_spec(
        GenesisRuntimeProfile.life_loop_world(seed=7, tick_count=1, population=2)).run_ticks()
    assert result.manifest.source_digest == compute_source_digest(str(neutral_source_digest))
