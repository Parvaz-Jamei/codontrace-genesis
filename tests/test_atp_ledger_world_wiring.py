"""HostParasiteWorld and assert_single_atp_owner run on the closed world ledger."""

from __future__ import annotations

import hashlib
import json
from fractions import Fraction

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from codontrace.atp_ledger import RESERVOIR, ATPConservationError, WorldATPLedger, verify_ledger_chain
from codontrace.errors import ConfigurationError
from codontrace.genesis.host_parasite_life_plugin import assert_single_atp_owner
from codontrace.genesis.host_parasite_world import HostParasiteProfile, HostParasiteWorld


def _h(x: object) -> str:
    return hashlib.sha256(json.dumps(x, sort_keys=True, default=repr).encode()).hexdigest()


def _busy_profile(seed: int = 3, **kw: float) -> HostParasiteProfile:
    base = dict(coupling_amount=0.3, coupling_loss_fraction=0.25,
                birth_probability_primary=0.3, birth_probability_secondary=0.3,
                death_probability_primary=0.1, death_probability_secondary=0.1,
                basal_energy_cost=0.05)
    base.update(kw)
    return HostParasiteProfile(profile_id="pin", seed=seed, **base)  # type: ignore[arg-type]


def test_hp_outputs_byte_identical_to_pre_ledger_main() -> None:
    # Pins computed at origin/main 89ecd78 (before the ledger) with the same
    # profile; the ledger observes, it never changes engine arithmetic.
    w = HostParasiteWorld(_busy_profile())
    assert _h(w.run(40)) == "b959a5edcb00facb2067f0c1be65b8f6fa1b9a78e851b66d0f640b7ecc0252ca"
    assert _h(w.life_loop_snapshot()) == "85b487a6175eeba09e792671c5994d6c8685238f326551b9706fb58c0743b9ba"


def test_hp_every_tick_checked_and_chained() -> None:
    w = HostParasiteWorld(_busy_profile())
    w.run(25)
    led = w.atp_ledger
    assert led.ticks_checked == 25
    assert verify_ledger_chain(led.journal_records()) == led.head
    t = led.totals()
    agents = sum((Fraction(a.current_atp) for a in w.accounts.values()), Fraction(0))
    assert t["agents"] == agents
    assert agents + t["reservoir"] == t["sources_in"] - t["sinks_out"]
    assert led.balance("sink:coupling_loss") > 0  # loss fraction is booked
    assert led.balance("sink:basal") > 0
    assert sum(w.death_counts.values()) == 0 or led.balance(RESERVOIR) >= 0


def test_hp_bypass_write_fails_next_tick() -> None:
    w = HostParasiteWorld(_busy_profile())
    w.run(2)
    mid = sorted(w.accounts)[0]
    w.accounts[mid].current_atp += 1.0
    with pytest.raises(ATPConservationError, match="bypass"):
        w.tick()


@settings(max_examples=25, deadline=None)
@given(
    seed=st.integers(0, 10_000),
    amt=st.floats(0.0, 2.0),
    loss=st.floats(0.0, 1.0),
    birth=st.floats(0.0, 1.0),
    death=st.floats(0.0, 0.5),
    basal=st.floats(0.0, 0.5),
    ticks=st.integers(1, 15),
)
def test_hp_conservation_property(seed, amt, loss, birth, death, basal, ticks) -> None:
    w = HostParasiteWorld(HostParasiteProfile(
        profile_id="prop", seed=seed, coupling_amount=amt, coupling_loss_fraction=loss,
        birth_probability_primary=birth, birth_probability_secondary=birth,
        death_probability_primary=death, death_probability_secondary=death, basal_energy_cost=basal))
    w.run(ticks)
    w.check_atp_conservation()
    assert w.atp_ledger.ticks_checked == ticks
    assert verify_ledger_chain(w.atp_ledger.journal_records()) == w.atp_ledger.head


class _Org:
    def __init__(self, oid: str, state) -> None:
        self.id = oid
        self.atp_state = state


def test_assert_single_atp_owner_checks_real_balance() -> None:
    from codontrace.genesis.atp import GenesisATPState

    a, b = GenesisATPState.from_runtime(5.0), GenesisATPState.from_runtime(5.0)
    assert_single_atp_owner([_Org("a", a), _Org("b", b)])  # type: ignore[list-item]
    with pytest.raises(ConfigurationError, match="share one ATP account"):
        assert_single_atp_owner([_Org("a", a), _Org("b", a)])  # type: ignore[list-item]
    led = WorldATPLedger()
    led.attach("a", a.runtime, tick=0)
    led.attach("b", b.runtime, tick=0)
    a.debit_runtime(1.0, tick=1, organism_id="a", codon="X", action="act")
    assert_single_atp_owner([_Org("a", a), _Org("b", b)], ledger=led)  # type: ignore[list-item]
    with pytest.raises(ConfigurationError, match="world ATP ledger"):
        assert_single_atp_owner([_Org("a", a)], ledger=led)  # type: ignore[list-item]
    b.runtime.current_atp = 7.0  # write around the ledger
    with pytest.raises(ConfigurationError, match="bypass"):
        assert_single_atp_owner([_Org("a", a), _Org("b", b)])  # type: ignore[list-item]
