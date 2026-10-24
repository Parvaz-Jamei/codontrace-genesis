"""F13: creation can not be booked as "rounding".

Each test injects a creation of eps in 1e-300 .. 0.5 at one point of the
coupling path and requires a raise. An addition smaller than half an ulp of
the value is absorbed by the float itself (nothing is created), so the
injection is at least one ulp: ``v + eps`` or, if that rounds back to ``v``,
the next double above ``v``.
"""

from __future__ import annotations

import math
from fractions import Fraction

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from codontrace.atp_ledger import ATPConservationError, WorldATPLedger, coupling_rounding_units, float_error
from codontrace.energy import ATPAccount, ATPLedgerEntry
from codontrace.genesis.host_parasite_world import HostParasiteProfile, HostParasiteWorld
from codontrace.life_loop import energy_coupling as ec

EPS = [1e-300, 1e-15, 1e-12, 1e-6, 0.5]


def _bump(v: float, eps: float) -> float:
    w = v + eps
    return w if w != v else math.nextafter(v, math.inf)


def _profile() -> HostParasiteProfile:
    return HostParasiteProfile(profile_id="f13", seed=3, coupling_amount=0.3, coupling_loss_fraction=0.25,
                               birth_probability_primary=0.3, birth_probability_secondary=0.3,
                               death_probability_primary=0.1, death_probability_secondary=0.1,
                               basal_energy_cost=0.05)


def test_uninjected_run_is_clean() -> None:
    HostParasiteWorld(_profile()).run(40)


@pytest.mark.parametrize("eps", EPS)
def test_injection_into_engine_new_balances_raises(monkeypatch: pytest.MonkeyPatch, eps: float) -> None:
    orig = ec.EnergyCoupling.apply

    def apply(self, balances, **kw):  # type: ignore[no-untyped-def]
        new, *rest = orig(self, balances, **kw)
        new = dict(new)
        new[self.target_id] = _bump(float(new[self.target_id]), eps)
        return (new, *rest)

    monkeypatch.setattr(ec.EnergyCoupling, "apply", apply)
    with pytest.raises(ATPConservationError):
        HostParasiteWorld(_profile()).run(40)


@pytest.mark.parametrize("eps", EPS)
def test_injection_into_gained_leg_raises(eps: float) -> None:
    sb, tb, req, lf = 4.0, 1.3, 0.3, 0.25
    loss = req * lf
    acc = req - loss
    sa, ta = sb - req, tb + acc
    paid, gained = sb - sa, ta - tb
    coupling_rounding_units(sb, sa, tb, ta, req, acc, loss, paid=paid, gained=gained)
    with pytest.raises(ATPConservationError):
        coupling_rounding_units(sb, sa, tb, ta, req, acc, loss, paid=paid, gained=_bump(gained, eps))
    with pytest.raises(ATPConservationError):
        coupling_rounding_units(sb, sa, tb, _bump(ta, eps), req, acc, loss, paid=paid, gained=gained)


@pytest.mark.parametrize("eps", EPS)
def test_injection_into_account_entry_raises(eps: float) -> None:
    led = WorldATPLedger("w")
    acct = ATPAccount(5.0)
    led.attach("a", acct, tick=0)
    good = ATPLedgerEntry(entry_id=0, tick=1, agent_id="a", codon="F", action="forage", kind="credit",
                          amount=1.0, balance_before=5.0, balance_after=6.0, reason="r")
    led._book_entry("a", good)
    bad = ATPLedgerEntry(entry_id=1, tick=1, agent_id="a", codon="F", action="forage", kind="credit",
                         amount=1.0, balance_before=6.0, balance_after=_bump(7.0, eps + 1e-10), reason="r")
    with pytest.raises(ATPConservationError):
        led._book_entry("a", bad)


@settings(max_examples=300, deadline=None)
@given(a=st.floats(-1e300, 1e300), b=st.floats(-1e300, 1e300))
def test_bound_is_exactly_half_an_ulp(a: float, b: float) -> None:
    r = a + b
    if not math.isfinite(r):
        return
    float_error(r, a, b)  # a correctly rounded sum is always accepted
    exact = Fraction(a) + Fraction(b)
    for cand in (math.nextafter(r, math.inf), math.nextafter(r, -math.inf), _bump(r, 0.5)):
        if not math.isfinite(cand):
            continue
        ok = 2 * abs(exact - Fraction(cand)) <= Fraction(math.ulp(cand))
        if ok:
            float_error(cand, a, b)
        else:
            with pytest.raises(ATPConservationError):
                float_error(cand, a, b)
