"""F8: no tolerance window. Every float rounding is booked exactly; any
creation, even 1e-15 per transfer, raises."""

from __future__ import annotations

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from codontrace.atp_ledger import (
    ATPConservationError,
    WorldATPLedger,
    coupling_rounding_units,
    float_error,
    verify_ledger_chain,
)
from codontrace.energy import ATPAccount
from codontrace.genesis.host_parasite_world import HostParasiteProfile, HostParasiteWorld
from codontrace.life_loop.energy_coupling import EnergyCoupling


def _profile(seed: int = 3) -> HostParasiteProfile:
    return HostParasiteProfile(profile_id="f8", seed=seed, coupling_amount=0.3, coupling_loss_fraction=0.25,
                               birth_probability_primary=0.3, birth_probability_secondary=0.3,
                               death_probability_primary=0.1, death_probability_secondary=0.1,
                               basal_energy_cost=0.05)


def test_float_error_exact() -> None:
    a, b = 0.1, 0.2
    r = a + b
    assert float_error(r, a, b) != 0  # 0.1 + 0.2 rounds
    assert float_error(1.5, 1.0, 0.5) == 0


@pytest.mark.parametrize("inject", [1e-15, 2e-15, 5e-15, 1e-14, 1e-12])
def test_hp_coupling_creation_raises(monkeypatch: pytest.MonkeyPatch, inject: float) -> None:
    orig = ATPAccount.credit

    def credit(self, amount, *a, **k):  # type: ignore[no-untyped-def]
        if k.get("action") == "energy_coupling":
            amount = amount + inject
        return orig(self, amount, *a, **k)

    monkeypatch.setattr(ATPAccount, "credit", credit)
    w = HostParasiteWorld(_profile())
    with pytest.raises(ATPConservationError):
        w.run(40)


def test_scope_negative_residual_raises_and_rolls_back() -> None:
    led = WorldATPLedger("t")
    a, b = ATPAccount(10.0), ATPAccount(1.0)
    led.attach("a", a, tick=0)
    led.attach("b", b, tick=0)
    with pytest.raises(ATPConservationError), led.transfer_scope("x", tick=1):
        a.debit(1.0, tick=1, agent_id="a", codon="", action="x", reason="x")
        b.credit(1.0 + 1e-15, tick=1, agent_id="b", codon="", action="x", reason="x")
    assert (a.current_atp, b.current_atp) == (10.0, 1.0)
    led.check({"a": 10.0, "b": 1.0})


@settings(max_examples=200, deadline=None)
@given(sb=st.floats(0, 1e6), tb=st.floats(0, 1e6), req=st.floats(0, 1e6), lf=st.floats(0, 1))
def test_coupling_identity_exact(sb: float, tb: float, req: float, lf: float) -> None:
    req = min(req, sb)
    loss = req * lf
    acc = req - loss
    sa, ta = max(0.0, sb - req), tb + acc
    paid, gained = sb - sa, ta - tb
    from codontrace.atp_ledger import _u
    assert _u(paid) - _u(gained) == _u(loss) + coupling_rounding_units(
        sb, sa, tb, ta, req, acc, loss, paid=paid, gained=gained)


@settings(max_examples=25, deadline=None)
@given(seed=st.integers(0, 2**16), ticks=st.integers(1, 30))
def test_hp_exact_no_window(seed: int, ticks: int) -> None:
    w = HostParasiteWorld(_profile(seed))
    w.run(ticks)
    w.check_atp_conservation()
    assert verify_ledger_chain(w.atp_ledger.journal_records(), w.atp_ledger.journal_base()) == w.atp_ledger.head


def test_energy_coupling_injected_creation_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    led = WorldATPLedger("ec")
    led.open_agent("a", 5.0, tick=0, funded_from="source:x")
    led.open_agent("b", 1.0, tick=0, funded_from="source:x")
    c = EnergyCoupling(coupling_id="c", source_id="a", target_id="b", amount=0.3, loss_fraction=0.1)
    orig = led.settle

    def settle(aid, cur, new, **k):  # type: ignore[no-untyped-def]
        return orig(aid, cur, new + (1e-15 if aid == "b" else 0.0), **k)

    monkeypatch.setattr(led, "settle", settle)
    with pytest.raises(ATPConservationError):
        c.apply({"a": 5.0, "b": 1.0}, tick=1, atp_ledger=led)
