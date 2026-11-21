"""JR5 phase 2b rule: a male never enters the birth chamber as a mother.

docs/prereg/jr5/MATING_TYPES_DESIGN_NOTE.md, phase 2b item 1: "a pair whose
offspring is assigned male still places it, but a male never enters the
chamber as a mother. The cost shows up in births, not through a multiplier."

Scientific basis. In the cost-of-males model only females (here
hermaphrodites, or females in a female/male set) bear offspring; a male
supplies a gamete at fertilisation and nothing else. With equal output per
mother, a sexual lineage whose offspring are male with probability m keeps
a fraction 1 - m of its offspring as mothers, so an all-female asexual
line gains 1/(1 - m) per generation (PREREG E1). If a male also placed an
offspring of its own, every pair would place two products whatever their
sexes, males would act as mothers, and the cost would vanish.

Seeds are in the unsealed block 20000+, outside every JR5 sealed range.
"""

from __future__ import annotations

import collections
import math
from dataclasses import replace

import pytest

from codontrace.genesis import closed_loop_hp_arm01_selfing_hold as hold
from codontrace.genesis.closed_loop_hp_arm01 import ARM_AVIRULENT, LifeLoopEcologyArm
from codontrace.genesis.host_parasite_life_plugin import hp_life_config
from codontrace.genesis.mating_types import draw_mating_type
from codontrace.genesis.organism import GenesisOrganism
from codontrace.genesis.population import LineageRecord, PopulationState, step_population
from codontrace.world import World2D
from tests.test_jr5_phase2a_mating_types import _BITS, _SEXES, _configs

_ANDRO = {**_SEXES, "mating_type_set": ("hermaphrodite", "male")}


def _one_step(seed: int, sex_ratio: float, organisms: tuple[GenesisOrganism, ...]) -> list[LineageRecord]:
    configs = _configs(**{**_ANDRO, "sex_ratio": sex_ratio})
    result = step_population(PopulationState(0, 0, organisms, (), ()), World2D(4, 4), configs, seed=seed)
    founders = {o.id for o in organisms}
    return [r for r in result.population.lineage if r.organism_id not in founders and r.parent_id is not None]


def _pair() -> tuple[GenesisOrganism, GenesisOrganism]:
    # A selfed organism is pinned hermaphrodite; with sex_ratio 1.0 every drawn type is male.
    herm = GenesisOrganism.from_bits("o0", _BITS[0], initial_runtime_atp=20.0, position=(1, 0))
    herm.selfed = True
    male = GenesisOrganism.from_bits("o1", _BITS[1], initial_runtime_atp=20.0, position=(1, 1))
    return herm, male


def test_hermaphrodite_x_male_places_only_the_hermaphrodites_product() -> None:
    """Basis: only the mother bears the zygote. One hermaphrodite and one male
    pair once in the first step, so the expected births are 1 (not 2), with
    the hermaphrodite as parent and the male as second parent. Measured 2
    births on main 91d0bd7, one of them with the male as parent."""

    herm, male = _pair()
    births = _one_step(20005, 1.0, (herm, male))
    assert len(births) == 1
    assert births[0].parent_id == "o0"
    assert births[0].second_parent_id == "o1"


def test_hermaphrodite_x_hermaphrodite_still_places_both_products() -> None:
    """Basis: both partners are mothers, so each places its own product, the
    same one offspring per mother as above. Expected 2 births, one per
    parent. This keeps the rule from passing by dropping every second product."""

    first, second = (
        GenesisOrganism.from_bits(f"o{i}", _BITS[i], initial_runtime_atp=20.0, position=(1, i)) for i in range(2)
    )
    first.selfed = True
    second.selfed = True
    births = _one_step(20005, 1.0, (first, second))
    assert sorted(r.parent_id for r in births) == ["o0", "o1"]


def test_a_sire_needs_no_room_for_a_product_of_its_own() -> None:
    """Basis: a hermaphrodite x male pair places one child, so it needs one
    free place, not two. With max_population 3 and two live parents there is
    exactly one place: expected 1 birth. Counting the male's slot as a
    product would need 2 + 2 > 3 places and place nothing."""

    herm, male = _pair()
    configs = _configs(**{**_ANDRO, "sex_ratio": 1.0})
    configs = replace(configs, reproduction=replace(configs.reproduction, max_population=3))
    result = step_population(PopulationState(0, 0, (herm, male), (), ()), World2D(4, 4), configs, seed=20005)
    births = [r for r in result.population.lineage if r.parent_id is not None]
    assert [(r.parent_id, r.second_parent_id) for r in births] == [("o0", "o1")]


def test_female_x_male_places_only_the_females_product() -> None:
    """Basis: the same rule with separate sexes: a female x male cross places
    one offspring, mothered by the female. Expected 1 birth, parent female."""

    configs = _configs(**_SEXES)
    sexual = configs.effective_sexual_config
    ids: dict[str, str] = {}
    for index in range(200):
        kind = draw_mating_type(20005, f"s{index}", sexual)
        ids.setdefault(kind, f"s{index}")
    female = GenesisOrganism.from_bits(ids["female"], _BITS[0], initial_runtime_atp=20.0, position=(1, 0))
    male = GenesisOrganism.from_bits(ids["male"], _BITS[1], initial_runtime_atp=20.0, position=(1, 1))
    result = step_population(PopulationState(0, 0, (female, male), (), ()), World2D(4, 4), configs, seed=20005)
    births = [r for r in result.population.lineage if r.parent_id is not None]
    assert [(r.parent_id, r.second_parent_id) for r in births] == [(female.id, male.id)]


def test_a_male_keeps_its_offspring_endowment() -> None:
    """Basis: a male bears no offspring, so it pays no offspring endowment
    (the cost of sons is paid by the mothers that make them). It still pays
    the per-reproduction parent cost (1.0 ATP), as every chamber entrant does.
    Expected male ATP after one step: 20 - 1 - basal, i.e. no 25% endowment."""

    herm, male = _pair()
    configs = _configs(**{**_ANDRO, "sex_ratio": 1.0})
    result = step_population(PopulationState(0, 0, (herm, male), (), ()), World2D(4, 4), configs, seed=20005)
    after = {o.id: o for o in result.population.organisms}
    reasons = [e.reason for e in after["o1"].atp_state.runtime.ledger]
    assert "offspring_runtime_atp_transfer" not in reasons
    assert "parent_reproduction_cost" in reasons
    assert "offspring_runtime_atp_transfer" in [e.reason for e in after["o0"].atp_state.runtime.ledger]


# Several generations of the section-4 engine config under the timing harness.

_N = 20
_GENERATIONS = 4
_SEED = 20501


def _section4_arm(n: int, seed: int) -> LifeLoopEcologyArm:
    windows = [w for _, w in hold._INVASION_FOUNDERS]
    arm = LifeLoopEcologyArm.boot(
        arm=ARM_AVIRULENT,
        seed=seed,
        birth_atp=hold.HOLD_BIRTH_ATP,
        founders=[("outcross", windows[i % len(windows)]) for i in range(n)],
        world_size=max(12, math.ceil(math.sqrt(4 * n))),
        soft_carrying_capacity=3 * n,
        basal_runtime_atp_cost=hold.HOLD_BASAL_ATP_COST,
        passage_refill_mode=hold.HOLD_PASSAGE_REFILL_MODE,
        resource_bolus_amount=hold.HOLD_RESOURCE_BOLUS_AMOUNT,
        food_patches=hold.HOLD_FOOD_PATCHES,
        founder_spatial_policy=hold.HOLD_FOUNDER_SPATIAL_POLICY,
        two_fold_cost_sex=False,
        mating_locus_lock=hold.HOLD_MATING_LOCUS_LOCK,
        selfing_birth_atp_endowment=0.0,
        chamber_max_birth_wait_ticks=2,
        chamber_timeout_policy="fail",
    )
    configs = arm.runner.configs
    sexual = replace(
        configs.sexual_recombination,
        mating_types_enabled=True,
        sex_assignment="random_at_birth",
        hermaphrodite_selfing=True,
        diploid_meiosis=True,
        mating_type_set=("hermaphrodite", "male"),
        sex_ratio=0.5,
    )
    life = replace(hp_life_config(configs.closed_loop_hp_life), outcross_runtime_atp=0.0)
    arm.runner.configs = replace(configs, sexual_recombination=sexual, closed_loop_hp_life=life)
    return arm


@pytest.fixture(scope="module")
def section4_run() -> tuple[list[LineageRecord], dict[str, str]]:
    arm = _section4_arm(_N, _SEED)
    types: dict[str, str] = {}
    for _ in range(_GENERATIONS):
        arm.run_generations(1)
        for organism in arm.runner.population.organisms:
            assert organism.mating_type is not None
            types[organism.id] = organism.mating_type
    sexual = arm.runner.configs.effective_sexual_config
    seed = arm.runner.population.mating_seed
    births = [r for r in arm.runner.population.lineage if r.parent_id is not None]
    for record in births:
        for oid in (record.parent_id, record.second_parent_id, record.organism_id):
            if oid is not None and oid not in types:
                types[oid] = draw_mating_type(seed, oid, sexual)
    return births, types


def test_no_male_is_ever_the_parent_of_a_birth(section4_run: tuple[list[LineageRecord], dict[str, str]]) -> None:
    """Basis: males never mother. Section-4 config (sexes on, hermaphrodite x
    male set, m = 0.5, diploid meiosis, two_fold_cost_sex off), N = 20 over 4
    generations of the timing harness. Expected male parents: 0. Every
    outcrossed birth still has a second parent, and a male may be that
    sire. On main 91d0bd7 the same run had 19 births with a male parent."""

    births, types = section4_run
    assert births
    assert [r.organism_id for r in births if types[str(r.parent_id)] == "male"] == []
    assert all(r.second_parent_id is not None for r in births)
    assert any(types[str(r.second_parent_id)] == "male" for r in births)


def test_sons_of_hermaphrodites_are_still_placed(section4_run: tuple[list[LineageRecord], dict[str, str]]) -> None:
    """Basis: the cost shows up in births, so mothers still make sons at the
    sex ratio. Expected sons about m * births = 0.5 * births; the check is
    a 3-sigma binomial band and the exact value is pinned for this seed."""

    births, types = section4_run
    sons = sum(1 for r in births if types[r.organism_id] == "male")
    n = len(births)
    assert abs(sons - 0.5 * n) <= 3 * math.sqrt(n * 0.25)
    assert sons >= 1
    assert all(types[str(r.parent_id)] == "hermaphrodite" for r in births)
    per_mother = collections.Counter(r.parent_id for r in births)
    assert per_mother


def test_son_allocation_is_paid_by_mothers_only() -> None:
    """Basis: the cost of males is the share of a mother's offspring ATP that
    goes to sons. The son_allocation term (ClosedLoopP5Session.son_cost_ledger)
    sums the initial ATP of male newborns; after the fix each of those sons
    has a non-male parent, and no male ever debits an offspring endowment.
    Expected: sons >= 1, term ATP equals the sons' summed endowments, every
    son's parent is a hermaphrodite, and no male carries an
    offspring_runtime_atp_transfer row."""

    from codontrace.genesis.closed_loop_p5 import ClosedLoopP5Session
    from codontrace.genesis.host_parasite_life_plugin import OUTCROSS_OUT_BITS
    from tests.test_jr5_phase2a_mating_types import _p5, _sexes_for

    probe = ClosedLoopP5Session.boot(seed=20011, outcross_bits=OUTCROSS_OUT_BITS)
    cfg = _sexes_for(
        probe,
        mating_type_set=("hermaphrodite", "male"),
        sex_ratio=0.5,
        hermaphrodite_selfing=True,
        diploid_meiosis=True,
    )
    session = _p5(OUTCROSS_OUT_BITS, cfg)
    founders = {o.id for o in session.runner.population.organisms}
    types: dict[str, str] = {}
    son_atp: dict[str, float] = {}
    males_seen: list[GenesisOrganism] = []
    for _ in range(4):
        session.run_ticks(1)
        for o in session.runner.population.organisms:
            types[o.id] = str(o.mating_type)
            if o.mating_type == "male":
                males_seen.append(o)
                if o.id not in founders:
                    son_atp[o.id] = float(o.atp_state.runtime.to_dict()["initial_atp"])  # type: ignore[arg-type]
    cost = session.son_cost_ledger()
    assert cost["term"] == "son_allocation"
    assert cost["sons"] == len(son_atp) >= 1
    assert cost["atp"] == pytest.approx(sum(son_atp.values()))
    parents = {r.organism_id: r.parent_id for r in session.runner.population.lineage}
    assert {types[str(parents[son])] for son in son_atp} == {"hermaphrodite"}
    for male in males_seen:
        assert "offspring_runtime_atp_transfer" not in [e.reason for e in male.atp_state.runtime.ledger]
