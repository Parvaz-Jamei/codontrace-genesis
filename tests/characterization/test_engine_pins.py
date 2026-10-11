"""Characterization: engine replay-contract pins in one place.

See docs/ENGINE_REPLAY_CONTRACT.md and docs/validation/LIFE_LOOP_DIGEST_HISTORY.md.
Probe: ``GenesisRuntimeProfile.life_loop_world(seed=7, tick_count=12, population=6)``.

* ``SPEC_DIGEST`` is the spec pin ``7d199ae5…``.
* ``HISTORICAL_SNAPSHOT_DIGEST`` (``76a5e62c…``) is the pre-aadc970 trajectory,
  reproduced with the documented counterfactual that uses the profile's
  population configs verbatim (never done in production runs).
* ``DEFAULT_SNAPSHOT_DIGEST`` (``e9d404a0…``) is today's default trajectory.
* ``*_TICKS_DIGEST`` pins the ordered per-tick digests.
* ``*_CORE_DIGEST`` pins ``GenesisRunResult._core_payload()`` (run, ticks,
  manifest, snapshot, evidence pack, replay bundle, wiring matrix).
* ``DEFAULT_RESULT_DIGEST`` pins the full ``GenesisRunResult.digest()`` once
  (it also covers the maturity reports and costs about 7 s, so only the
  default trajectory is pinned at that level).

The manifest carries ``source_digest``, a hash of the checkout itself
(``compute_source_digest``: src/codontrace, docs, pyproject.toml, README.md),
so core and result pins are computed with the ``neutral_source_digest``
fixture. They then change only when run behaviour changes, not on every
source edit. Snapshot, tick and spec digests never include it.

These values are never loosened. A change needs a pin review under
ENGINE_REPLAY_CONTRACT.md.
"""
from __future__ import annotations

import pytest

from codontrace.engine import GenesisEngine
from codontrace.engine_digest import _digest
from codontrace.genesis.runtime_profiles import GenesisRuntimeProfile

SPEC_DIGEST = '7d199ae51345872215dbbb0c45cf8f141aacfb4c31d6537eda6de246c0cb7aac'
HISTORICAL_SNAPSHOT_DIGEST = '76a5e62cb0123b20a089adde25acd1cfb6dc460bdfab52f33ee460533d76f43a'
DEFAULT_SNAPSHOT_DIGEST = 'e9d404a0a50c5ac323a94306d582bd27596a752ecab00bd9406834947d27db78'
HISTORICAL_TICKS_DIGEST = '941cb8e416c2de2f8a1dbc9801a71ae6cc5d5b7ae7941828d47d124bce576eec'
DEFAULT_TICKS_DIGEST = '92a50b978c24668e856b054f165e54cebc3569fcdddbc554a7fe9bf6a474c7cc'
HISTORICAL_CORE_DIGEST = '5ce138b678b41d33b9c4cb1e8a1b6bec43e7d29384d942534344660a13ce968c'
DEFAULT_CORE_DIGEST = '4889a879e60e0cc04c180fc42d75a54efd9284c0b1aa42035e5cedd28fe5e6ef'
DEFAULT_RESULT_DIGEST = 'c3bd98eb09f2515778fd44671fff9c9631125098070f3da9b7c13ca28014cdd7'


def _spec():
    return GenesisRuntimeProfile.life_loop_world(seed=7, tick_count=12, population=6)


def _run(*, historical: bool):
    spec = _spec()
    engine = GenesisEngine.from_spec(spec)
    if historical:
        engine.runner.configs = spec.population_configs  # documented counterfactual, see module docstring
    return engine.run_ticks()


def _ticks_digest(result) -> str:
    return _digest([t.digest() for t in result.ticks])


def test_spec_digest_pin():
    assert _spec().digest() == SPEC_DIGEST


@pytest.mark.parametrize(('historical', 'snapshot_pin', 'ticks_pin', 'core_pin'), [
    (False, DEFAULT_SNAPSHOT_DIGEST, DEFAULT_TICKS_DIGEST, DEFAULT_CORE_DIGEST),
    (True, HISTORICAL_SNAPSHOT_DIGEST, HISTORICAL_TICKS_DIGEST, HISTORICAL_CORE_DIGEST),
], ids=['default', 'historical'])
def test_run_digest_pins_and_independent_replay(historical, snapshot_pin, ticks_pin, core_pin, neutral_source_digest):
    first = _run(historical=historical)
    assert first.snapshot.digest() == snapshot_pin
    assert _ticks_digest(first) == ticks_pin
    assert _digest(first._core_payload()) == core_pin
    replay = _run(historical=historical)  # independent re-execution, not the same object
    assert [t.digest() for t in replay.ticks] == [t.digest() for t in first.ticks]
    assert _digest(replay._core_payload()) == _digest(first._core_payload())


def test_full_result_digest_pin(neutral_source_digest):
    assert _run(historical=False).digest() == DEFAULT_RESULT_DIGEST


def test_source_identity_is_neutralized(neutral_source_digest):
    from codontrace.genesis.artifacts import compute_source_digest
    result = GenesisEngine.from_spec(
        GenesisRuntimeProfile.life_loop_world(seed=7, tick_count=1, population=2)).run_ticks()
    assert result.manifest.source_digest == compute_source_digest(str(neutral_source_digest))


def test_profile_not_aliased_by_runs():
    before = _spec().to_dict()
    _run(historical=True)
    assert _spec().to_dict() == before and _spec().digest() == SPEC_DIGEST
