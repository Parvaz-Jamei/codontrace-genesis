"""F15: an explicit hold that rebuilds accounts under the same id."""

from __future__ import annotations

import pytest

from codontrace.atp_ledger import ATPConservationError, WorldATPLedger
from codontrace.energy import ATPAccount


def _acct(start: float, debit: float) -> ATPAccount:
    a = ATPAccount(start)
    a.debit(debit, tick=1, agent_id="h", codon="B", action="basal", reason="r")
    return a


def test_silent_rewrite_still_raises() -> None:
    led = WorldATPLedger("w")
    led.close_tick(0, led.sync_accounts({"h": _acct(5.0, 1.0)}, tick=0))
    with pytest.raises(ATPConservationError, match="rewritten"):
        led.sync_accounts({"h": _acct(7.0, 2.0)}, tick=1)


def test_reissue_books_explicit_flows_and_conserves() -> None:
    led = WorldATPLedger("w")
    led.close_tick(0, led.sync_accounts({"h": _acct(5.0, 1.0), "g": _acct(3.0, 0.5)}, tick=0))
    new = {"h": _acct(7.0, 2.0), "n": _acct(1.0, 0.25)}  # h rebuilt, g dropped, n added
    mirrors = led.reissue_accounts(new, tick=1, reason="host_hold", declared={"h": 5.0, "n": 0.75})
    led.close_tick(1, mirrors)
    assert led.balance("sink:host_hold") == 4 + 2.5  # old h and dropped g
    assert led.balance("source:host_hold") == -(7 + 1)  # new h and new n
    assert led.agent_balance("h") == 5 and led.agent_balance("n") == 0.75



def _booked() -> WorldATPLedger:
    led = WorldATPLedger("w")
    led.close_tick(0, led.sync_accounts({"h": _acct(5.0, 1.0)}, tick=0))
    return led


def test_reissue_with_changed_balance_raises() -> None:
    led = _booked()
    before = led.state_digest()
    rebuilt = _acct(1e6, 1.0)  # declared snapshot says 9, account holds ~1e6
    with pytest.raises(ATPConservationError, match="declared"):
        led.reissue_accounts({"h": rebuilt}, tick=1, reason="host_hold", declared={"h": 8.0})
    assert led.state_digest() == before


def test_reissue_of_undeclared_id_or_reason_raises() -> None:
    led = _booked()
    with pytest.raises(ATPConservationError, match="not declared"):
        led.reissue_accounts({"h": _acct(7.0, 2.0)}, tick=1, reason="host_hold", declared={})
    with pytest.raises(ATPConservationError, match="undeclared reissue boundary"):
        led.reissue_accounts({"h": _acct(7.0, 2.0)}, tick=1, reason="anything", declared={"h": 5.0})


def test_phase3_hold_books_exactly_what_it_declares() -> None:
    from codontrace.genesis.rq_mechanism_v2_phase3 import (
        BRANCH_LOCKED,
        _parasite_founders,
        build_host_seats,
        build_phase3_arm,
    )

    seats = build_host_seats("000000", "111111", common="A")
    arm = build_phase3_arm(3, BRANCH_LOCKED, seats, _parasite_founders())
    arm.run_generations(2)  # honest hold: books cleanly
    led = arm.runner.atp_ledger
    assert led.balance("source:host_hold") < 0  # the declared refill inflow is visible

    hold = arm.host_composition_hold
    assert hold is not None

    def lying_hold(target):  # type: ignore[no-untyped-def]
        hold(target)
        key = sorted(target.host_hold_atp)[0]
        target.host_hold_atp = dict(target.host_hold_atp, **{key: target.host_hold_atp[key] + 1.0})

    arm.host_composition_hold = lying_hold
    with pytest.raises(ATPConservationError, match="declared"):
        arm.run_generations(1)


# F17: the hold's declaration comes from the profile's birth reserve, not from
# the bodies the hold built, and each hold's net is checked against a figure
# worked out independently from the population before the hold.


def _watch_holds(arm, monkeypatch):  # type: ignore[no-untyped-def]
    """Wrap the hold and the reissue; record expected and booked flows per hold."""
    from codontrace.genesis.atp import organism_atp_accounts
    from codontrace.genesis.closed_loop_hp_arm01_structural_rq import STRUCT_BIRTH_ATP

    led = arm.runner.atp_ledger
    hold = arm.host_composition_hold
    from codontrace.genesis.population_runner import PopulationRunner

    reissue = PopulationRunner._reissue_atp
    rows: list[dict[str, float]] = []
    pending: dict[str, float] = {}

    def watched_hold(target):  # type: ignore[no-untyped-def]
        before = organism_atp_accounts(target.runner.population.organisms)
        hold(target)
        after = organism_atp_accounts(target.runner.population.organisms)
        # A body is reissued when the hold replaced it (its old history is not
        # extended) or installed it fresh; a body that left goes to the sink.
        rebuilt = [k for k, a in after.items() if k not in before or (a is not before[k] and before[k].entry_count())]
        gone = [k for k in before if k not in after]
        pending.clear()
        pending.update(
            n=float(len(rebuilt)),
            source=float(STRUCT_BIRTH_ATP) * len(rebuilt),
            sink=sum(led.agent_balance(k) for k in rebuilt + gone if k in before),
        )

    def watched_reissue(runner, reason, declared):  # type: ignore[no-untyped-def]
        src, snk = led.balance("source:host_hold"), led.balance("sink:host_hold")
        reissue(runner, reason, declared)
        rows.append(dict(pending, booked_source=-(led.balance("source:host_hold") - src),
                         booked_sink=led.balance("sink:host_hold") - snk))

    arm.host_composition_hold = watched_hold
    monkeypatch.setattr(PopulationRunner, "_reissue_atp", watched_reissue)
    return rows


def test_phase3_declaration_is_the_profile_birth_reserve() -> None:
    from codontrace.genesis.closed_loop_hp_arm01_structural_rq import STRUCT_BIRTH_ATP
    from codontrace.genesis.rq_mechanism_v2_phase3 import (
        BRANCH_LOCKED,
        _parasite_founders,
        build_host_seats,
        build_phase3_arm,
    )

    seats = build_host_seats("000000", "111111", common="A")
    arm = build_phase3_arm(3, BRANCH_LOCKED, seats, _parasite_founders())
    assert arm.host_hold_atp == {str(s["host_id"]): float(STRUCT_BIRTH_ATP) for s in seats}


def test_phase3_each_hold_nets_exactly_the_expected_amount(monkeypatch: pytest.MonkeyPatch) -> None:
    from codontrace.genesis.rq_mechanism_v2_phase3 import (
        BRANCH_LOCKED,
        _parasite_founders,
        build_host_seats,
        build_phase3_arm,
    )

    seats = build_host_seats("000000", "111111", common="A")
    arm = build_phase3_arm(3, BRANCH_LOCKED, seats, _parasite_founders())
    rows = _watch_holds(arm, monkeypatch)
    arm.run_generations(10)
    assert len(rows) == 20
    for row in rows:
        assert row["booked_source"] == row["source"]
        assert row["booked_sink"] == row["sink"]
    # Reference run documented in docs/ATP_WORLD_LEDGER.md.
    led = arm.runner.atp_ledger
    assert sum(r["n"] for r in rows) == 1111
    assert -led.balance("source:host_hold") == 1111 * 48 == 53328
    # Host balances are binary floats of decimal amounts, so the exact sink is
    # 50856 plus about 8e-13; both legs above are compared exactly per hold.
    assert round(float(led.balance("sink:host_hold")), 6) == 50856.0
    assert round(float(-led.balance("source:host_hold") - led.balance("sink:host_hold")), 6) == 2472.0


def test_phase3_hold_installing_another_balance_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    import codontrace.genesis.rq_mechanism_v2_phase3 as p3

    seats = p3.build_host_seats("000000", "111111", common="A")
    arm = p3.build_phase3_arm(3, p3.BRANCH_LOCKED, seats, p3._parasite_founders())
    arm.run_generations(1)
    real = p3.GenesisOrganism.from_bits

    def off_by_one(*args, **kwargs):  # type: ignore[no-untyped-def]
        kwargs["initial_runtime_atp"] = float(kwargs["initial_runtime_atp"]) - 1.0
        return real(*args, **kwargs)

    monkeypatch.setattr(p3.GenesisOrganism, "from_bits", off_by_one)
    with pytest.raises(ATPConservationError, match="declared"):
        arm.run_generations(1)


def test_phase5_hold_replaces_a_lost_host_at_the_birth_reserve(monkeypatch: pytest.MonkeyPatch) -> None:
    from dataclasses import replace

    from codontrace.genesis.closed_loop_hp_arm01_structural_rq import STRUCT_BIRTH_ATP
    from codontrace.genesis.rq_mechanism_v2_phase5 import ARM_ADAPTATION_CUT, build_phase5_arm

    arm = build_phase5_arm(ARM_ADAPTATION_CUT, 11)
    arm.run_generations(1)
    rows = _watch_holds(arm, monkeypatch)
    pop = arm.runner.population
    lost = str(pop.organisms[0].id)
    arm.runner.population = replace(pop, organisms=pop.organisms[1:])  # a host is gone
    arm.run_generations(1)
    first = rows[0]
    assert first["n"] >= 1 and first["source"] == float(STRUCT_BIRTH_ATP) * first["n"]
    for row in rows:
        assert row["booked_source"] == row["source"]
        assert row["booked_sink"] == row["sink"]
    assert lost in {str(o.id) for o in arm.runner.population.organisms}


def test_phase5_hold_installing_another_balance_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    from dataclasses import replace

    import codontrace.genesis.rq_mechanism_v2_phase5 as p5

    arm = p5.build_phase5_arm(p5.ARM_ADAPTATION_CUT, 11)
    arm.run_generations(1)
    real = p5.GenesisOrganism.from_bits

    def off_by_one(*args, **kwargs):  # type: ignore[no-untyped-def]
        if float(kwargs.get("initial_runtime_atp", 0.0)) > 0:
            kwargs["initial_runtime_atp"] = float(kwargs["initial_runtime_atp"]) + 1.0
        return real(*args, **kwargs)

    monkeypatch.setattr(p5.GenesisOrganism, "from_bits", off_by_one)
    pop = arm.runner.population
    arm.runner.population = replace(pop, organisms=pop.organisms[1:])
    with pytest.raises((ATPConservationError, p5.ConfigurationError)):
        arm.run_generations(1)
