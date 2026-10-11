"""GenerationInputProvider seam: record exogenous world events, replay them without the source."""
from __future__ import annotations

import pytest

from codontrace.engine import ExogenousInputRecord, GenerationInputProvider, GenesisEngine
from codontrace.errors import ConfigurationError, PlacementError, ReplayError
from codontrace.genesis.runtime_profiles import GenesisRuntimeProfile
from codontrace.replay import RecordedInputProvider
from codontrace.rng import RNGManager
from codontrace.trace import (
    WORLD_EVENT_AGENT_MOVED,
    WORLD_EVENT_CUSTOM_CELL_SET,
    WORLD_EVENT_RESOURCE_PLACED,
    WorldEvent,
)
from codontrace.world import World2D

TICKS = 5


def _spec():
    return GenesisRuntimeProfile.life_loop_world(seed=7, tick_count=TICKS, population=4)


def _resource(generation: int, sequence: int, position: tuple[int, int], amount: float) -> WorldEvent:
    return WorldEvent(schema_version=1, step=generation, sequence=sequence, event_type=WORLD_EVENT_RESOURCE_PLACED,
                      position=position, amount=amount, source='exogenous', reason='test input',
                      after={'resource': amount})


class SeededSource:
    """A stand-in live source: random placements drawn from RNGManager."""

    def __init__(self, seed: int = 11) -> None:
        self.rng = RNGManager(seed=seed, namespace='test/exogenous-inputs')
        self.calls: list[tuple[int, str]] = []

    def __call__(self, *, generation_index: int, world_view: World2D) -> list[WorldEvent]:
        self.calls.append((generation_index, world_view.digest()))
        if generation_index % 2:
            return []
        count = 1 + self.rng.randrange(2)
        return [_resource(generation_index, i, (self.rng.randrange(world_view.width), self.rng.randrange(world_view.height)),
                          float(1 + self.rng.randrange(4))) for i in range(count)]


def _live():
    source = SeededSource()
    engine = GenesisEngine.from_spec(_spec(), generation_input_provider=source)
    return engine, engine.run_ticks(), source


def test_provider_satisfies_protocol():
    provider: GenerationInputProvider = SeededSource()
    replay: GenerationInputProvider = RecordedInputProvider(())
    assert callable(provider) and callable(replay)


def test_empty_provider_matches_no_provider():
    baseline = GenesisEngine.from_spec(_spec()).run_ticks()
    quiet = GenesisEngine.from_spec(_spec(), generation_input_provider=lambda **_: ())
    result = quiet.run_ticks()
    assert quiet.exogenous_inputs == ()
    assert 'exogenous_inputs' not in result.to_dict()
    assert result.digest() == baseline.digest()
    assert result.snapshot.digest() == baseline.snapshot.digest()


def test_live_inputs_are_recorded_and_change_the_run():
    engine, result, source = _live()
    baseline = GenesisEngine.from_spec(_spec()).run_ticks()
    records = engine.exogenous_inputs
    assert records and all(isinstance(r, ExogenousInputRecord) for r in records)
    assert [r.generation_index for r in records] == [g for g, _ in source.calls if g % 2 == 0]
    assert all(r.world_digest_before != r.world_digest_after for r in records)
    assert result.exogenous_inputs == records
    assert result.to_dict()['exogenous_inputs'] == [r.to_dict() for r in records]
    assert result.digest() != baseline.digest()
    assert result.snapshot.world_digest != baseline.snapshot.world_digest


def test_recorded_replay_reproduces_spec_result_and_world_digests():
    live_engine, live, _ = _live()
    serialised = live.to_dict()['exogenous_inputs']
    replay_engine = GenesisEngine.from_spec(_spec(), generation_input_provider=RecordedInputProvider.from_records(serialised))
    replayed = replay_engine.run_ticks()
    assert replay_engine.spec.digest() == live_engine.spec.digest()
    assert replayed.digest() == live.digest()
    assert replay_engine.world_digest() == live_engine.world_digest()
    assert replayed.snapshot.digest() == live.snapshot.digest()
    assert replay_engine.exogenous_inputs == live_engine.exogenous_inputs


def test_replay_detects_a_diverged_world():
    engine, _, _ = _live()
    first = engine.exogenous_inputs[0]
    forged = ExogenousInputRecord(first.tick_index, first.generation_index, first.events, '0' * 64, first.world_digest_after)
    replay = GenesisEngine.from_spec(_spec(), generation_input_provider=RecordedInputProvider([forged]))
    with pytest.raises(ReplayError):
        replay.run_ticks()
    assert replay.tick_results == ()


def test_record_round_trip_and_validation():
    engine, _, _ = _live()
    for record in engine.exogenous_inputs:
        assert ExogenousInputRecord.from_dict(record.to_dict()) == record
        assert ExogenousInputRecord.from_dict(record.to_dict()).digest() == record.digest()
    with pytest.raises(ValueError):
        ExogenousInputRecord.from_dict({**engine.exogenous_inputs[0].to_dict(), 'tick_index': True})
    with pytest.raises(ReplayError):
        RecordedInputProvider([engine.exogenous_inputs[0], engine.exogenous_inputs[0]])


class FailAt:
    def __init__(self, generation: int, events) -> None:
        self.generation, self.events = generation, events

    def __call__(self, *, generation_index: int, world_view: World2D):
        if generation_index < self.generation:
            return [_resource(generation_index, 0, (0, 0), 1.0)]
        if callable(self.events):
            return self.events()
        return self.events


def _boom():
    raise RuntimeError('source offline')


@pytest.mark.parametrize('bad, error', [
    (_boom, RuntimeError),
    ([_resource(9, 0, (1, 1), 2.0), _resource(9, 1, (999, 0), 2.0)], PlacementError),
    ([_resource(9, 0, (1, 1), 2.0), 'not an event'], ConfigurationError),
    ([WorldEvent(schema_version=1, step=0, sequence=0, event_type=WORLD_EVENT_AGENT_MOVED, position=(0, 0))],
     ConfigurationError),
    ([WorldEvent(schema_version=1, step=0, sequence=0, event_type=WORLD_EVENT_CUSTOM_CELL_SET, position=(0, 0))],
     ConfigurationError),
    ([WorldEvent(schema_version=1, step=0, sequence=0, event_type=WORLD_EVENT_RESOURCE_PLACED, position=None)],
     ConfigurationError),
])
def test_failing_inputs_fail_the_generation_before_any_mutation(bad, error):
    engine = GenesisEngine.from_spec(_spec(), generation_input_provider=FailAt(2, bad))
    engine.run_ticks(2)
    world, ticks, inputs = engine.world_digest(), engine.tick_results, engine.exogenous_inputs
    population = engine.latest_snapshot
    with pytest.raises(error):
        engine.run_ticks(1)
    assert engine.world_digest() == world
    assert engine.tick_results == ticks
    assert engine.exogenous_inputs == inputs
    assert engine.latest_snapshot is population


def test_world_view_is_a_disposable_clone():
    def vandal(*, generation_index: int, world_view: World2D):
        world_view.place_resource((0, 0), 50.0)
        world_view.walls.add((1, 1))
        return ()
    baseline = GenesisEngine.from_spec(_spec()).run_ticks()
    engine = GenesisEngine.from_spec(_spec(), generation_input_provider=vandal)
    assert engine.run_ticks().digest() == baseline.digest()


def test_observer_sees_post_step_state_and_inputs_land_between_generations():
    seen: list[tuple[int, str, str]] = []
    source = SeededSource()
    engine = GenesisEngine.from_spec(_spec(), generation_input_provider=source)

    def observer(*, generation_index: int) -> None:
        seen.append((generation_index, engine.world_digest(), engine.tick_results[-1].generation_result.world_after_digest))

    engine.generation_boundary_observers.append(observer)
    engine.run_ticks()
    assert [g for g, _, _ in seen] == [g + 1 for g, _ in source.calls]
    assert all(live == after for _, live, after in seen)
    # The view handed to the provider for generation g+1 is the world the observer saw after g.
    by_generation = {r.generation_index: r for r in engine.exogenous_inputs}
    for (generation, observed, _), (next_generation, offered) in zip(seen, source.calls[1:], strict=False):
        assert next_generation == generation
        assert offered == observed
        if generation in by_generation:
            assert by_generation[generation].world_digest_before == observed


def test_fork_restore_keeps_the_provider_seam():
    engine, _, _ = _live()
    fork_source = GenesisEngine.from_spec(_spec(), generation_input_provider=SeededSource())
    fork_source.run_ticks(2)
    fork = fork_source.capture_fork()
    child = GenesisEngine.from_fork(_spec(), fork, generation_input_provider=RecordedInputProvider(engine.exogenous_inputs))
    assert child.exogenous_inputs == ()
    child.run_ticks(TICKS - 2)
    assert child.world_digest() == engine.world_digest()
    assert child.exogenous_inputs == tuple(r for r in engine.exogenous_inputs if r.tick_index >= 2)
