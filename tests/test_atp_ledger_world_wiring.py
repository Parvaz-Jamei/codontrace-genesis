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


# Default-profile digests at origin/main 89ecd78 (run() result + snapshot).
LONG_PINS = {
    "0_60": "7b4ac61cfcf115c188d69fc02748a4fda6ceb5575d0d018c7019a72f5b22e5b7",
    "0_200": "81a2b9295829ae97416f5971de3dbe6689a92f86fcd883960bc7b5268229caca",
    "1_60": "13beaa3b1a2b18038679b2ad9e131ac1203f58f983c627a12e4b39d071c77ce6",
    "1_200": "fc4795406db4f5ee60bd716dfb6f080c542fdefcc71099e6736a5e84ad0a3667",
    "2_60": "2c970bbd3d2e1535a2f5e869f19485ee6d20002f268794f9258cac1dc1bff82a",
    "2_200": "db195ff467f7392c6a507dffe56af77598449100415edce2979e46cb4a4b34fe",
    "3_60": "c7ead7ec6408865840844081a0d009073cab152fed7e5fd0ef90c6796208daef",
    "3_200": "280bf8b0cdeae0df543af6d03f8de34db2f15d9fd8066fc7488075cb5891098f",
    "7_60": "071fe73cf3392e068cf4631944b43b82a3d531518ae5c0b6e6fe1be122ec02c4",
    "7_200": "431098a009d1f85b084c922bd1571cb03077c1241b7d9ab9dcc0664bead0d6a4",
    "42_60": "bfd1799a9a64430f758f7e8a36b32a56c0f985e2ca063ca24ddcfade9b2621f8",
    "42_200": "ab9ce45972d6b1ea866bbb63a6429ae752defbf3fb4a67f0ce1fda3ef71e784d",
    "99_60": "1d8afa7b5e67fee1aa3f190d7182c8d41f5e5877ddc7ab3ea1a94bb834874275",
    "99_200": "2e393f03464971522565b0e8d3b05ff534fd103f8845070667334f1aa4fb9174"
}


@pytest.mark.parametrize("key", sorted(LONG_PINS))
def test_hp_long_horizon_byte_identical_to_main(key: str) -> None:
    seed, ticks = (int(x) for x in key.split("_"))
    w = HostParasiteWorld(HostParasiteProfile(profile_id="d", seed=seed))
    result = w.run(ticks)
    assert _h([result, w.life_loop_snapshot()]) == LONG_PINS[key]
    assert w.atp_ledger.ticks_checked == ticks


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


@settings(max_examples=30, deadline=None)
@given(
    seed=st.integers(0, 10_000),
    amt=st.floats(0.0, 2.0),
    loss=st.floats(0.0, 1.0),
    birth=st.floats(0.0, 1.0),
    death=st.floats(0.0, 0.5),
    basal=st.floats(0.0, 0.5),
    ticks=st.integers(1, 25),
    energy=st.floats(0.0, 20.0),
)
def test_hp_conservation_property(seed, amt, loss, birth, death, basal, ticks, energy) -> None:
    w = HostParasiteWorld(HostParasiteProfile(
        profile_id="prop", seed=seed, initial_energy=energy, coupling_amount=amt, coupling_loss_fraction=loss,
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
