"""F7: every ATP owner books into a closed world ledger, outputs byte-identical."""

from __future__ import annotations

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from codontrace import AgentFactory, InitializationConfig, Simulation, SimulationConfig, World2D
from codontrace.atp_ledger import (
    ATPConservationError,
    ScalarATPBook,
    WorldATPLedger,
    verify_ledger_chain,
)
from codontrace.experiments.t02_mls_price import T02MLSPriceRunner
from codontrace.experiments.t03_mutualism import T03MutualismRunner
from codontrace.experiments.t05_red_queen import T05RedQueenRunner
from codontrace.genesis.closed_loop_p6 import run_match_arm
from codontrace.genesis.engine import GenesisEngine
from codontrace.genesis.runtime_profiles import GenesisRuntimeProfile
from codontrace.life_loop.energy_coupling import EnergyCoupling


def _closed(led: WorldATPLedger) -> None:
    led.check()
    assert verify_ledger_chain(led.journal_records(), led.journal_base()) == led.head
    t = led.totals()
    assert t["sources_in"] == t["sinks_out"] + t["agents"] + t["reservoir"]


@settings(max_examples=3, deadline=None)
@given(seed=st.integers(0, 2**16), ticks=st.integers(1, 6))
def test_genesis_engine_ledger_property(seed: int, ticks: int) -> None:
    eng = GenesisEngine.from_spec(
        GenesisRuntimeProfile.life_loop_world(seed=seed, tick_count=ticks, population=6))
    eng.run_ticks()
    led = eng.runner.atp_ledger
    assert led.ticks_checked >= ticks
    _closed(led)


def test_genesis_engine_digest_unchanged_by_ledger() -> None:
    a = GenesisEngine.from_spec(GenesisRuntimeProfile.life_loop_world(seed=7, tick_count=4, population=6))
    b = GenesisEngine.from_spec(GenesisRuntimeProfile.life_loop_world(seed=7, tick_count=4, population=6))
    ra, rb = a.run_ticks(), b.run_ticks()
    assert ra.digest() == rb.digest()
    assert a.runner.atp_ledger.head == b.runner.atp_ledger.head


def test_population_runner_detects_bypass() -> None:
    eng = GenesisEngine.from_spec(GenesisRuntimeProfile.life_loop_world(seed=3, tick_count=2, population=6))
    eng.run_ticks()
    runner = eng.runner
    org = runner.population.organisms[0]
    org.atp_state.runtime.current_atp += 1.0  # write around the entry log
    with pytest.raises((ATPConservationError, ValueError)):
        runner.settle_atp()


def _sim(seed: int, steps: int, ledger: WorldATPLedger | None = None):
    world = World2D(5, 5)
    agents = AgentFactory.create_many(world=world, config=InitializationConfig(count=3, seed=seed,
                                                                               placement_strategy="grid"))
    return agents, Simulation.run(world=world, agents=agents,
                                  config=SimulationConfig(steps=steps, seed=seed), atp_ledger=ledger)


@settings(max_examples=8, deadline=None)
@given(seed=st.integers(0, 2**16), steps=st.integers(0, 10))
def test_simulation_ledger_property(seed: int, steps: int) -> None:
    led = WorldATPLedger("sim")
    agents, res = _sim(seed, steps, led)
    _, plain = _sim(seed, steps)
    assert (res.trace_digest, res.world_digest) == (plain.trace_digest, plain.world_digest)
    _closed(led)
    assert led.ticks_checked == steps + 1
    for a in agents:
        assert led.balance(f"agent:{a.id}") == a.atp_account.current_atp


def test_p6_custom_loop_wired() -> None:
    rec = run_match_arm(mating="outcross", passage="coevolve", generations=3)
    assert rec.generations == 3


@pytest.mark.parametrize(("runner", "kw"), [(T02MLSPriceRunner, {}), (T03MutualismRunner, {}),
                                           (T05RedQueenRunner, {})])
def test_scalar_runners_closed(runner, kw) -> None:
    r = runner(5, generations=12, **kw)
    r.run()
    _closed(r.atp_book.ledger)
    assert r.atp_book.ledger.ticks_checked >= 12


def test_t03_bypass_detected() -> None:
    r = T03MutualismRunner(5, generations=3)
    r.initialize_population()
    r.step_generation(1)
    r.population[0].host_atp += 0.5
    with pytest.raises(ATPConservationError):
        r.step_generation(2)


@settings(max_examples=40, deadline=None)
@given(st.lists(st.tuples(st.sampled_from("bdsm"), st.floats(0, 50, allow_nan=False)), max_size=30))
def test_scalar_book_conservation(ops) -> None:
    class Ind:
        def __init__(self, atp: float) -> None:
            self.atp = atp

    book = ScalarATPBook("prop")
    pop = [Ind(10.0)]
    book.settle(pop, tick=-1)
    for tick, (op, x) in enumerate(ops):
        if op == "b":
            pop.append(Ind(x))
        elif op == "d" and pop:
            pop.pop(0)
        elif op == "s" and pop:
            pop[-1].atp = book.assign(pop[-1], "atp", x, tick=tick, source="source:x", sink="sink:x")
        elif op == "m" and pop:
            new = Ind(pop[0].atp)
            book.carry(new, pop[0])
            pop[0] = new
        book.settle(pop, tick=tick)
    _closed(book.ledger)


@settings(max_examples=60, deadline=None)
@given(src=st.floats(0, 100), tgt=st.floats(0, 100), amt=st.floats(0, 100), loss=st.floats(0, 1))
def test_energy_coupling_ledger(src: float, tgt: float, amt: float, loss: float) -> None:
    led = WorldATPLedger("ec")
    led.open_agent("a", src, tick=0, funded_from="source:x")
    led.open_agent("b", tgt, tick=0, funded_from="source:x")
    c = EnergyCoupling(coupling_id="c", source_id="a", target_id="b", amount=amt, loss_fraction=loss)
    plain = c.apply({"a": src, "b": tgt}, tick=1, allow_partial=True)
    booked = c.apply({"a": src, "b": tgt}, tick=1, allow_partial=True, atp_ledger=led)
    assert repr(plain) == repr(booked)
    led.close_tick(1, booked[0])
    _closed(led)
