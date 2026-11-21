"""JR5 discrete uniform census: brood of b, semelparous cap, census re-endowment, explicit kill.

All of it is opt-in. The tests use only the smoke seed and pooled counts
(births, mothers, refusals); nothing here reads an asexual share by
generation or anything a w could be fitted from.
"""

from __future__ import annotations

import collections
import dataclasses
from typing import Any

import pytest

from codontrace.campaigns import jr5_realised_w_pilot as P
from codontrace.genesis.closed_loop_hp_arm01 import (
    ARM_FIXED,
    FOUNDER_PROGRAM,
    JR5_KILL_NAMESPACE,
    LifeLoopEcologyArm,
)
from codontrace.genesis.liveness import AliveGateResult
from codontrace.genesis.organism import GenesisOrganism
from codontrace.genesis.population import (
    SEMELPAROUS_EVENT_CAP,
    ReproductionConfig,
    brood_shares,
    can_reproduce,
)
from codontrace.rng import RNGManager
from tests.test_jr5_realised_w_pilot import SMOKE_SEED, discrete_design, no_engine_boot_on_registered_seeds, spec

__all__ = ["no_engine_boot_on_registered_seeds", "spec"]

B = 6
N = 20


def brood_design(**change: Any) -> P.PopulationDesign:
    """The discrete design with b = 6, a cap of one event, soft K (1 + b) N and re-endowment."""

    fields: dict[str, Any] = {
        "soft_k_multiple": float(1 + B),
        "brood_size": B,
        "max_reproduction_events_per_lifetime": 1,
        "census_reendowment": True,
    }
    fields.update(change)
    return discrete_design(**fields)


@pytest.fixture(scope="module")
def first_step(spec: P.RealisedWPilotSpec) -> dict[str, Any]:
    """Generation 0 -> 1 without the census: founders, births and the newborns themselves."""

    arm = P.build_population(spec, brood_design(), SMOKE_SEED, N)
    founders = {o.id: o for o in arm.runner.population.organisms}
    males = {o.id for o in founders.values() if o.mating_type == "male"}
    arm.run_generations(1)
    runner = arm.runner
    births = [r for r in runner.population.lineage if r.parent_id is not None and r.organism_id not in founders]
    alive = {o.id: o for o in runner.population.organisms}
    return {
        "founders": founders,
        "males": males,
        "births": births,
        "alive": alive,
        "refusals": runner.capacity_refusals[-1],
    }


def test_each_mother_bears_exactly_b_children(first_step: dict[str, Any]) -> None:
    """Basis: a reproduction event makes b children (brood of b, one event per life).
    So births = b x mothers, every mother has exactly b children and births <= b N.
    Pooled counts only."""

    per_mother = collections.Counter(r.parent_id for r in first_step["births"])
    assert per_mother, "no births in the first generation"
    assert set(per_mother.values()) == {B}
    assert len(first_step["births"]) == B * len(per_mother) <= B * N
    assert first_step["refusals"] == 0


def test_generation_zero_births_are_b_times_asexual_plus_paired_non_males(first_step: dict[str, Any]) -> None:
    """Basis: at generation 0 every mother is an asexual founder or a paired non-male
    (males sire only). Expected births = b x (asexual mothers + paired non-male mothers),
    and no male founder is a mother. Pooled over the population."""

    founders = first_step["founders"]
    mothers = {r.parent_id for r in first_step["births"]}
    sexual_mothers = {r.parent_id for r in first_step["births"] if r.second_parent_id is not None}
    asexual_mothers = mothers - sexual_mothers
    assert mothers <= set(founders)
    assert not mothers & first_step["males"]
    assert all(founders[m].asexual_lineage for m in asexual_mothers)
    assert len(first_step["births"]) == B * (len(asexual_mothers) + len(sexual_mothers))


def test_siblings_have_their_own_meiosis_and_sex_draw(first_step: dict[str, Any]) -> None:
    """Basis: each child of a brood has its own RNG fork .../brood/<k>, so siblings
    get distinct ids (-b0..-b5), their own sex, and, in outcrossed broods of
    heterozygous parents, their own recombinant genome. Over all broods of the step
    at least one brood has siblings of both sexes and at least one outcrossed brood
    has siblings with different genomes (all-equal would mean one shared draw)."""

    broods: dict[str, list[Any]] = collections.defaultdict(list)
    for r in first_step["births"]:
        broods[str(r.parent_id)].append(r)
    alive = first_step["alive"]
    mixed_sex = False
    mixed_genome = False
    for records in broods.values():
        suffixes = sorted(r.organism_id.rsplit("-", 1)[-1] for r in records)
        assert suffixes == [f"b{k}" for k in range(B)]
        kids = [alive[r.organism_id] for r in records if r.organism_id in alive]
        if len({k.mating_type for k in kids}) > 1:
            mixed_sex = True
        if records[0].second_parent_id is not None and len({r.genome_digest for r in records}) > 1:
            mixed_genome = True
    assert mixed_sex
    assert mixed_genome


def test_brood_shares_split_the_endowment_exactly() -> None:
    """Basis: E is split E/b with exact conservation: b - 1 shares of round(E/b, 10)
    and the remainder to the last child, so the shares sum to E."""

    assert brood_shares(48.0, 6) == (8.0,) * 6
    shares = brood_shares(10.0, 3)
    assert shares[:2] == (3.3333333333, 3.3333333333)
    assert sum(shares) == 10.0
    assert brood_shares(7.5, 1) == (7.5,)


def test_siblings_start_with_equal_shares_of_one_endowment(first_step: dict[str, Any]) -> None:
    """Basis: the children of one event share the mother's endowment E as E/b: in k
    order b - 1 equal shares of round(E/b, 10) and the remainder last, which differs
    from them only by the 10-digit rounding (at most b x 0.5e-10)."""

    broods: dict[str, list[GenesisOrganism]] = collections.defaultdict(list)
    for oid, org in sorted(first_step["alive"].items()):
        if oid not in first_step["founders"]:
            broods[oid.rsplit("-", 1)[0]].append(org)
    assert broods
    for kids in broods.values():
        kids.sort(key=lambda o: int(o.id.rsplit("-b", 1)[1]))
        initial = tuple(o.atp_state.runtime.initial_atp for o in kids)
        if len(initial) == B:
            assert len(set(initial[:-1])) == 1
            assert initial[0] == round(initial[0], 10)
            assert abs(initial[-1] - initial[0]) <= B * 0.5e-10 + 1e-12


def test_the_cap_refuses_a_second_copy() -> None:
    """Basis: with max_reproduction_events_per_lifetime = 1 an organism that has
    reproduced once is refused (semelparous_event_cap); without the cap it is not."""

    org = GenesisOrganism.from_bits("o0", "111000000", initial_runtime_atp=40.0)
    gate = AliveGateResult(
        passed=True,
        survived_ticks=1,
        executed_actions=1,
        blocked_actions=0,
        blocked_ratio=0.0,
        final_runtime_atp=40.0,
        lumen_interactions=0,
        reproduction_events=0,
        reasons=(),
    )
    capped = ReproductionConfig(min_runtime_atp=1.0, max_reproduction_events_per_lifetime=1)
    assert SEMELPAROUS_EVENT_CAP not in can_reproduce(org, gate, capped).reasons
    org.reproduction_events = 1
    assert SEMELPAROUS_EVENT_CAP in can_reproduce(org, gate, capped).reasons
    assert SEMELPAROUS_EVENT_CAP not in can_reproduce(org, gate, ReproductionConfig(min_runtime_atp=1.0)).reasons


def test_census_reendows_recruits_and_the_ledger_closes(spec: P.RealisedWPilotSpec) -> None:
    """Basis: after thinning, every kept recruit starts with birth_atp = 48.0 runtime
    ATP; the endowment is booked from source:jr5_census_endowment and the remainder to
    sink:jr5_census_thinning. Expected: N recruits at 48.0, the source grew by exactly
    48 N, and the world ledger residual is within 1e-9."""

    design = brood_design()
    arm = P.build_population(spec, design, SMOKE_SEED, N)
    ledger = arm.runner.atp_ledger
    before = ledger.balance(P.CENSUS_ENDOWMENT_SOURCE)
    step = P._discrete_step(arm, 1, N, SMOKE_SEED, endowment_atp=design.birth_atp)
    kept = arm.runner.population.organisms
    assert step["births"] > N
    assert len(kept) == N
    assert {o.atp_state.runtime_available for o in kept} == {48.0}
    assert -(ledger.balance(P.CENSUS_ENDOWMENT_SOURCE) - before) == 48 * N
    assert abs(P._ledger_residual(arm)) <= 1e-9


def test_founder_coding_prefix_check() -> None:
    """Basis: every founder carries the same coding prefix on each homolog; a founder
    with a different first codon is refused at boot."""

    tail = "001000111"
    good = [GenesisOrganism.from_bits(f"f{i}", FOUNDER_PROGRAM + tail) for i in range(3)]
    P.check_founder_coding_prefixes(good, len(FOUNDER_PROGRAM))
    flipped = ("0" if FOUNDER_PROGRAM[0] == "1" else "1") + FOUNDER_PROGRAM[1:]
    bad = [*good, GenesisOrganism.from_bits("f9", flipped + tail)]
    with pytest.raises(P.PilotInvariantError, match="coding prefix"):
        P.check_founder_coding_prefixes(bad, len(FOUNDER_PROGRAM))


def test_brood_options_are_discrete_only_and_need_room() -> None:
    """Basis: brood, cap and re-endowment are part of the discrete census model, and
    soft K must be at least (1 + b) N so capacity never picks the offspring."""

    from tests.test_jr5_realised_w_pilot import smoke_design

    with pytest.raises(P.ConfigurationError, match="discrete"):
        dataclasses.replace(smoke_design(), brood_size=B)
    with pytest.raises(P.ConfigurationError, match="1 \\+ brood_size"):
        brood_design(soft_k_multiple=float(B))


def test_default_design_records_are_unchanged() -> None:
    """Basis: the opt-in fields are left out of to_record at their defaults, so a design
    that does not set them keeps the digest it had before they existed."""

    from tests.test_jr5_realised_w_pilot import smoke_design

    design = smoke_design()
    record = design.to_record()
    for name in ("brood_size", "max_reproduction_events_per_lifetime", "census_reendowment"):
        assert name not in record
    assert brood_design().to_record()["brood_size"] == B


@pytest.mark.parametrize("s", [1.0, 0.25])
def test_jr5_kill_zeroes_and_removes_killed_hosts(s: float) -> None:
    """Basis: a matched host is killed iff u < s, u from RNGManager(seed, "jr5-kill")
    fork g<generation>/h<host id>; a kill debits all runtime ATP (jr5_kill). Expected:
    each matched host's outcome equals that draw, killed hosts hold ATP 0.0 and are
    absent from the population and its census, survivors of the draw keep their ATP."""

    arm = LifeLoopEcologyArm.boot(arm=ARM_FIXED, seed=SMOKE_SEED, kill_probability=s)
    killed_total = 0
    contacts = 0
    for _ in range(2):
        arm.run_generations(1)
        generation = int(arm.runner.population.generation)
        alive = {o.id for o in arm.runner.population.organisms}
        for host_id, killed, atp_after in arm.kill_outcomes_by_generation[-1]:
            u = RNGManager(seed=SMOKE_SEED, namespace=JR5_KILL_NAMESPACE).fork(f"g{generation}/h{host_id}").random()
            assert killed == (u < s)
            contacts += 1
            if killed:
                killed_total += 1
                assert atp_after == 0.0
                assert host_id not in alive
            else:
                assert atp_after > 0.0
    assert contacts > 0
    if s == 1.0:
        assert killed_total == contacts
    assert abs(arm.runner.atp_ledger.balance("sink:jr5_kill")) > 0 or killed_total == 0


def test_kill_probability_is_validated() -> None:
    """Basis: s is a probability; anything outside [0, 1] is refused at boot."""

    with pytest.raises(Exception, match="kill_probability"):
        LifeLoopEcologyArm.boot(arm=ARM_FIXED, seed=SMOKE_SEED, kill_probability=1.5)
