"""JR5 phase 2b: opt-in hermaphrodite selfing with sexes on.

``SexualRecombinationConfig.hermaphrodite_selfing`` lets a hermaphrodite whose
outcross locus reads selfing make a selfed child while sexes stay on. Pinned
values in ``_BASE_ERA`` were produced at 7db2227a (before this change) with
the same inputs as below; with the mode off they must match byte for byte.
All seeds are in the unsealed block 20000+, outside the JR5 prereg sealed
ranges.
"""

from __future__ import annotations

import json
from dataclasses import replace

import pytest

from codontrace.errors import ConfigurationError
from codontrace.genesis.birth import SexualRecombinationConfig
from codontrace.genesis.closed_loop_p5 import ClosedLoopP5Session
from codontrace.genesis.host_parasite_life_plugin import (
    OUTCROSS_OUT_BITS,
    OUTCROSS_SELFING_BITS,
    ClosedLoopHPLifeConfig,
    resolve_copy_self_mode,
)
from codontrace.genesis.mating_types import MatingTypeMap, can_self
from codontrace.genesis.organism import GenesisOrganism
from codontrace.genesis.population import PopulationState, mating_type_census, mating_type_of
from codontrace.genesis.runtime_profiles import LIFE_LOOP_EATER_GENOME
from tests.test_jr5_phase2a_mating_types import (
    _BITS,
    _MAIN_ERA_CONFIG_JSON,
    _SEXES,
    _compact,
    _configs,
    _first_id_of,
    _p5,
    _run,
    _sexes_for,
    _step,
    _without_mating_fields,
)

# The snapshot integrity fix adds a checksum; these pins include that field.
# Removing only the checksum reproduces every previous fixed-sex pin exactly.
# Re-pinned when sex became fixed for life (sexes-on runs store each type and
# the run seed). One step uses the run seed for every draw, so the step pins
# with the stored fields removed still equal ``_BASE_ERA``. The two-tick
# session with the outcross locus changed in dynamics too: at 7db2227a the
# second tick redrew every sex from that tick's seed, which was the bug.
_FIXED_SEX_ERA = {
    "fm20005": "2621b5833eea320c1a9ea61608ae1d38b5d493e40bd789bce7a83bb730ea4029",
    "hm20005": "2b55c2cecce86b7e00a4bc4c6a5f57c5f6f405026710c6425bfbe8ae2eca20cb",
    "fm20008": "f62576680e30db317c975b62d1e93ebfb5a205a2240eb9d59617ee59f28da91c",
    "hm20008": "c03ac6291956b2a5b65d5768cf132eed0fe1629d6a72559d7bd350620a2f0706",
    "fm20013": "e88e8c989f306a3dfbfd68c316d81ff02df1a8bf0c9b995e7c4d8882f3f699e1",
    "hm20013": "0972fc8f45a6fb726932450dcb1dbadebcbff9a123c001e2044bc8f5521e93c4",
    "p5" + OUTCROSS_OUT_BITS: "70cf1b0359c80247c251a26717217da6a1e0edbe78eb03afbe3f69f30dbbaacc",
    "p5" + OUTCROSS_SELFING_BITS: "5c53a186ae56445a74f16270275a55650628e22ffa550dfbf89b7a6276a725bd",
}
_BASE_ERA = {
    "fm20005": "69264a3faa40b848e74232c904e4e14a9b24a730cc6f9320ceb08a19264c0241",
    "hm20005": "ec1bade66aadfcbce2359251c50736ac292bfb9bf057c97a6fad6c7db821af2e",
    "fm20008": "7fd06fbc83d5f10178ed9702e0a09569644824de2674133ea341da30b8b56a3c",
    "hm20008": "7fd06fbc83d5f10178ed9702e0a09569644824de2674133ea341da30b8b56a3c",
    "fm20013": "9b3acd0530a3f2d0a16ebc3920b251632f2d58f3d29cddd0b62e37cc671c6bc6",
    "hm20013": "9b3acd0530a3f2d0a16ebc3920b251632f2d58f3d29cddd0b62e37cc671c6bc6",
    "p5" + OUTCROSS_OUT_BITS: "fbc5bfaad9768c9ef5b539309bd92180ecd31b829906ec3c27cabfba8bf99c3b",
    "p5" + OUTCROSS_SELFING_BITS: "033485164bbee357115684e0ecb1bfbb8508d21a7d91a069629b7b831dcbedcf",
}
_ANDRO = {"mating_type_set": ("hermaphrodite", "male"), "sex_ratio": 0.3}


def _self_arm(bits: str, **overrides: object) -> tuple[ClosedLoopP5Session, SexualRecombinationConfig]:
    probe = ClosedLoopP5Session.boot(seed=20011, outcross_bits=bits)
    cfg = _sexes_for(probe, **{**_ANDRO, "hermaphrodite_selfing": True, **overrides})
    return _p5(bits, cfg), cfg


# (1) mode off: byte-identical to the pre-change base.


def test_switch_off_config_payloads_still_match_main_era() -> None:
    """The new field is omitted when False, so the 2a main-era payloads hold."""

    assert _compact(SexualRecombinationConfig()) == _MAIN_ERA_CONFIG_JSON["default"]
    assert _compact(SexualRecombinationConfig(enabled=True)) == _MAIN_ERA_CONFIG_JSON["enabled"]


@pytest.mark.parametrize("seed", [20005, 20008, 20013])
def test_sexes_on_without_self_mode_matches_base(seed: int) -> None:
    """Sexes on, self mode off: one step has the same dynamics as at 7db2227a
    (stored sex fields removed), and the full digest is the fixed-sex pin."""

    for key, extra in (("fm", {}), ("hm", _ANDRO)):
        population = _step(seed, _configs(**{**_SEXES, **extra})).population
        assert _without_mating_fields(population) == _BASE_ERA[f"{key}{seed}"]
        assert population.digest() == _FIXED_SEX_ERA[f"{key}{seed}"]


@pytest.mark.parametrize("bits", [OUTCROSS_OUT_BITS, OUTCROSS_SELFING_BITS])
def test_locus_runs_without_self_mode_match_base(bits: str) -> None:
    """Both locus states with sexes on and the mode off, two ticks. The selfing
    locus never reaches the chamber, so its dynamics match 7db2227a; the
    outcross locus changes because sexes are no longer redrawn on tick two."""

    probe = ClosedLoopP5Session.boot(seed=20011, outcross_bits=bits)
    session = _p5(bits, _sexes_for(probe, **_ANDRO))
    session.run_ticks(2)
    population = session.runner.population
    assert population.digest() == _FIXED_SEX_ERA["p5" + bits]
    if bits == OUTCROSS_SELFING_BITS:
        assert _without_mating_fields(population) == _BASE_ERA["p5" + bits]
    else:
        assert _without_mating_fields(population) != _BASE_ERA["p5" + bits]


# (2) hermaphrodites self; selfers make no sons.


def test_selfing_hermaphrodites_make_only_hermaphrodite_children() -> None:
    """By construction a selfed child is pinned hermaphrodite, so no male can come
    from selfing. With every founder on the selfing locus there is no outcross,
    so every birth is selfed and males can only be founders."""

    session, cfg = _self_arm(OUTCROSS_SELFING_BITS)
    founders = {o.id for o in session.runner.population.organisms}
    summary = session.run_ticks(3)
    population = session.runner.population
    assert summary["births"] >= 1
    assert summary["recombination_births"] == 0
    born = [o for o in population.organisms if o.id not in founders]
    assert born and all(o.selfed for o in born)
    # Any seed gives the same answer for a selfed organism: the type is pinned.
    for seed in (20011, 20012, 20013, 20999):
        assert {mating_type_of(population, o.id, seed=seed, sexual=cfg) for o in born} == {"hermaphrodite"}
        census = mating_type_census(population, seed=seed, sexual=cfg)
        assert census["hermaphrodite"] >= len(born)
        assert census.get("male", 0) <= len(founders)


def test_selfed_type_is_pinned_even_when_the_draw_says_male() -> None:
    """With sex_ratio 1.0 every drawn type is male; a selfed organism must still
    read hermaphrodite, because selfing fixes the type (no sons from selfers)."""

    cfg = SexualRecombinationConfig(
        enabled=True,
        sex_ratio=1.0,
        hermaphrodite_selfing=True,
        **{**_SEXES, "mating_type_set": ("hermaphrodite", "male")},  # type: ignore[arg-type]
    )
    org = replace(GenesisOrganism.from_bits("x0", _BITS[0], position=(0, 0)), selfed=True)
    population = PopulationState(0, 0, (org,), (), ())
    assert mating_type_of(population, "x0", seed=20005, sexual=cfg) == "hermaphrodite"
    types = MatingTypeMap(20005, cfg)
    types.pin("x0", "hermaphrodite")
    assert types.assign("x0") == "hermaphrodite"
    assert types.assign("x1") == "male"


# (3) males and females never self.


def test_can_self_table() -> None:
    """Only a hermaphrodite in self mode may self; the mode off bars everyone."""

    on = SexualRecombinationConfig(
        enabled=True, hermaphrodite_selfing=True, **{**_SEXES, "mating_type_set": ("hermaphrodite",)}
    )  # type: ignore[arg-type]
    off = replace(on, hermaphrodite_selfing=False)
    assert can_self("hermaphrodite", on)
    assert not can_self("male", on)
    assert not can_self("female", on)
    assert not can_self("hermaphrodite", off)


def test_males_on_selfing_locus_never_self_in_self_mode() -> None:
    """sex_ratio 1.0 makes every founder male; males cannot self, so a selfing
    locus with no hermaphrodite partner gives zero births."""

    session, _ = _self_arm(OUTCROSS_SELFING_BITS, sex_ratio=1.0)
    assert session.run_ticks(2)["births"] == 0


def test_selfed_births_all_have_hermaphrodite_parents() -> None:
    """Every selfed birth must come from a parent that is a hermaphrodite, read
    in the step before the birth. Self-fertilisation fuses two gametes of one
    parent, so a selfed birth is a lineage record whose second parent is the
    parent itself."""

    session, cfg = _self_arm(OUTCROSS_SELFING_BITS)
    selfed_parents: list[str] = []
    for _ in range(3):
        step_seed = session.seed + session.tick_index
        before = session.runner.population
        types = {o.id: mating_type_of(before, o.id, seed=step_seed, sexual=cfg) for o in before.organisms}
        known = {rec.organism_id for rec in before.lineage}
        session.run_ticks(1)
        for rec in session.runner.population.lineage:
            if rec.organism_id not in known and rec.parent_id and rec.second_parent_id == rec.parent_id:
                selfed_parents.append(types[rec.parent_id])
    assert selfed_parents
    assert set(selfed_parents) == {"hermaphrodite"}


def test_separate_sexes_never_self_on_selfing_locus() -> None:
    """{female, male} cannot enable the mode, and with the mode off a selfing locus
    in a sexual lineage gives no birth (2a rule, unchanged)."""

    probe = ClosedLoopP5Session.boot(seed=20011, outcross_bits=OUTCROSS_SELFING_BITS)
    assert _p5(OUTCROSS_SELFING_BITS, _sexes_for(probe)).run_ticks(2)["births"] == 0


# (4) asexual_lineage guard still holds.


def test_unmated_female_still_gets_no_uniparental_child_in_self_mode() -> None:
    """Self mode on, {hermaphrodite, male}, sex_ratio 1.0: the lone organism is
    male, and a male cannot self, so it gets no child. A lone female under
    {female, male} also gets none (2a guard). Expected 0 from the rule itself."""

    configs = _configs(
        max_birth_wait_ticks=0,
        hermaphrodite_selfing=True,
        sex_ratio=1.0,
        **{**_SEXES, "mating_type_set": ("hermaphrodite", "male")},
    )
    male = _first_id_of("male", 20005, configs.effective_sexual_config)
    org = GenesisOrganism.from_bits(male, _BITS[0], initial_runtime_atp=40.0, position=(1, 1))
    _, births = _run(20005, configs, (org,), 4)
    assert births == 0
    female_cfg = _configs(max_birth_wait_ticks=0, **_SEXES)
    female = _first_id_of("female", 20005, female_cfg.effective_sexual_config)
    lone = GenesisOrganism.from_bits(female, _BITS[0], initial_runtime_atp=40.0, position=(1, 1))
    assert _run(20005, female_cfg, (lone,), 4)[1] == 0


def test_chamber_timeout_still_never_falls_back_in_self_mode() -> None:
    """Self mode only opens the selfing-locus path. A hermaphrodite that entered
    the chamber (outcross locus, or no locus) and found no mate is still refused
    a fallback copy on timeout, as in 2a."""

    configs = _configs(
        max_birth_wait_ticks=0, hermaphrodite_selfing=True, **{**_SEXES, "mating_type_set": ("hermaphrodite",)}
    )
    org = GenesisOrganism.from_bits("h0", _BITS[0], initial_runtime_atp=40.0, position=(1, 1))
    assert _run(20005, configs, (org,), 4)[1] == 0


# (5) outcross and self arms share one engine mode and one ledger.


def test_outcross_and_self_arms_share_mode_and_ledger() -> None:
    """The arms differ only in the locus bits, so their sexual configs are
    identical. The outcross arm recombines and pays the mating fee; the self arm
    pays no fee. Both record their births as lineage records with the same
    fields."""

    self_session, self_cfg = _self_arm(OUTCROSS_SELFING_BITS)
    out_session, out_cfg = _self_arm(OUTCROSS_OUT_BITS)
    assert self_cfg.to_dict() == out_cfg.to_dict()
    self_summary = self_session.run_ticks(3)
    out_summary = out_session.run_ticks(3)
    assert set(self_summary) == set(out_summary)
    assert out_summary["recombination_births"] >= 1
    assert out_summary["outcross_debit_events"] >= 1
    assert self_summary["recombination_births"] == 0
    assert self_summary["outcross_debit_events"] == 0
    assert not any(o.selfed for o in out_session.runner.population.organisms)
    self_lineage = self_session.runner.population.lineage
    out_lineage = out_session.runner.population.lineage
    assert self_lineage and out_lineage
    assert {type(rec) for rec in self_lineage} == {type(rec) for rec in out_lineage}


# (6) serialization and validation.


def test_round_trip_and_default_omission() -> None:
    """The field is written only when True (same rule as the 2a fields)."""

    base = SexualRecombinationConfig(enabled=True, **{**_SEXES, "mating_type_set": ("hermaphrodite", "male")})  # type: ignore[arg-type]
    assert "hermaphrodite_selfing" not in base.to_dict()
    cfg = replace(base, hermaphrodite_selfing=True)
    payload = cfg.to_dict()
    assert payload["hermaphrodite_selfing"] is True
    assert SexualRecombinationConfig.from_dict(json.loads(json.dumps(payload))) == cfg
    org = replace(GenesisOrganism.from_bits("s0", _BITS[0], position=(1, 1)), selfed=True)
    state = PopulationState(0, 0, (org,), (), ())
    assert state.to_dict()["organisms"][0]["selfed"] is True  # type: ignore[index,call-overload]
    assert "selfed" not in json.dumps(_step(20005, _configs()).population.to_dict())


@pytest.mark.parametrize(
    "overrides",
    [
        {},
        {"mating_types_enabled": False, "mating_type_set": (), "sex_assignment": "none"},
        {"mating_type_set": ("female", "male")},
    ],
)
def test_self_mode_requires_a_set_with_hermaphrodite(overrides: dict[str, object]) -> None:
    """Selfing needs both gamete roles in one body, so only a set holding
    hermaphrodite can enable it; the first case is sexes off entirely."""

    payload: dict[str, object] = {"enabled": True, "hermaphrodite_selfing": True}
    if overrides:
        payload.update({**_SEXES, **overrides})
    with pytest.raises(ValueError, match="hermaphrodite_selfing"):
        SexualRecombinationConfig(**payload)  # type: ignore[arg-type]


# (7) like-for-like: same offspring count and ATP rule per reproduction.


def test_selfing_and_outcrossing_mothers_get_the_same_budget() -> None:
    """A fair self vs outcross contrast differs only in who supplies the second
    genome, not in fecundity or provisioning. In both arms one reproduction
    gives the mother exactly one child, and the child gets
    offspring_atp_fraction x the mother's residual after parent_atp_cost.
    The same hermaphrodite (org_b1, seed 20011) starts both arms with the same
    ATP and runs the same program, so its child ATP must be equal. The
    outcrossing mother is then lower by exactly outcross_runtime_atp, the
    mating effort paid only to outcross; selfing gets no matching bonus."""

    self_session, _ = _self_arm(OUTCROSS_SELFING_BITS)
    out_session, _ = _self_arm(OUTCROSS_OUT_BITS)
    fraction = self_session.runner.configs.reproduction.offspring_atp_fraction
    fee = out_session.runner.configs.closed_loop_hp_life.outcross_runtime_atp
    results = {}
    for name, session in (("self", self_session), ("out", out_session)):
        population = session.runner.step_generation(seed=session.seed).population
        by_id = {o.id: o for o in population.organisms}
        kids = [rec for rec in population.lineage if rec.parent_id == "org_b1"]
        assert len(kids) == 1, name
        child = by_id[kids[0].organism_id].atp_state.runtime_available
        mother = by_id["org_b1"].atp_state.runtime_available
        results[name] = (child, mother)
    self_child, self_mother = results["self"]
    out_child, out_mother = results["out"]
    assert self_child == pytest.approx(out_child, abs=1e-9)
    # Selfer keeps (1 - fraction) of the residual, the child gets fraction of it.
    assert self_child == pytest.approx(self_mother * fraction / (1.0 - fraction), abs=1e-9)
    assert self_mother - out_mother == pytest.approx(fee, abs=1e-9)


def test_self_mode_refuses_a_selfing_atp_bonus() -> None:
    """A selfing birth endowment would add ATP only to selfed children, an extra
    fitness term the outcross arm lacks, so the two cannot be combined."""

    session, cfg = _self_arm(OUTCROSS_SELFING_BITS)
    configs = session.runner.configs
    assert isinstance(configs.closed_loop_hp_life, ClosedLoopHPLifeConfig)
    life = replace(configs.closed_loop_hp_life, selfing_birth_atp_endowment=5.0)
    with pytest.raises(ConfigurationError, match="selfing_birth_atp_endowment"):
        replace(configs, closed_loop_hp_life=life, sexual_recombination=cfg)
    # Without self mode the endowment is still allowed (existing behaviour).
    replace(configs, closed_loop_hp_life=life, sexual_recombination=replace(cfg, hermaphrodite_selfing=False))


# (8) sex is fixed for life.


@pytest.mark.parametrize("bits", [OUTCROSS_OUT_BITS, OUTCROSS_SELFING_BITS])
def test_no_organism_ever_changes_sex_over_many_ticks(bits: str) -> None:
    """Sex is set once, at founding or birth, from the run seed and the
    organism id. The session steps with seed + tick index, so any draw keyed to
    the step seed would flip types between ticks. Expected: every organism
    seen keeps one type for all 12 ticks, and the stored type agrees with
    mating_type_of for any seed argument."""

    session, cfg = _self_arm(bits)
    seen: dict[str, str] = {}
    for _ in range(12):
        session.run_ticks(1)
        population = session.runner.population
        assert population.mating_seed == 20011
        for organism in population.organisms:
            assert organism.mating_type is not None
            assert seen.setdefault(organism.id, organism.mating_type) == organism.mating_type
            for probe_seed in (1, 20011 + session.tick_index):
                assert mating_type_of(population, organism.id, seed=probe_seed, sexual=cfg) == organism.mating_type
    assert len(seen) > 4


def test_founder_male_never_selfs() -> None:
    """Self mode on, every founder on the selfing locus. A male cannot self
    (both gamete roles are needed in one body), and its sex can no longer be
    redrawn as hermaphrodite on a later tick. Expected: no lineage record over
    12 ticks has a founder male as its parent."""

    session, _ = _self_arm(OUTCROSS_SELFING_BITS)
    session.run_ticks(1)
    males = {o.id for o in session.runner.population.organisms if o.mating_type == "male" and not o.selfed}
    assert males
    session.run_ticks(11)
    parents = {rec.parent_id for rec in session.runner.population.lineage if rec.parent_id}
    assert parents and not parents & males


def test_mating_seed_and_type_round_trip_and_are_absent_when_sexes_off() -> None:
    """The run seed and stored types are state, so they survive save and load;
    with sexes off neither is written, keeping default digests unchanged."""

    session, _ = _self_arm(OUTCROSS_OUT_BITS)
    session.run_ticks(2)
    population = session.runner.population
    restored = PopulationState.from_dict(json.loads(json.dumps(population.to_dict())))
    assert restored.mating_seed == 20011
    assert [(o.id, o.mating_type) for o in restored.organisms] == [(o.id, o.mating_type) for o in population.organisms]
    off = json.dumps(_step(20005, _configs()).population.to_dict())
    assert "mating_seed" not in off and "mating_type" not in off


# (9) no delayed selfing.


def test_unmated_outcrossing_hermaphrodite_is_refused_a_selfed_child() -> None:
    """Self mode on. A lone hermaphrodite whose locus reads outcross enters the
    chamber, finds no mate, and its wait expires. Selfing is decided only by
    the locus at reproduction, not as a fallback after a failed search, so the
    expected births are 0 (and no child is marked selfed)."""

    life = ClosedLoopHPLifeConfig(outcross_enabled=True)
    herm = {**_SEXES, "mating_type_set": ("hermaphrodite",)}
    configs = replace(_configs(max_birth_wait_ticks=0, hermaphrodite_selfing=True, **herm), closed_loop_hp_life=life)
    bits = LIFE_LOOP_EATER_GENOME + "100000" + OUTCROSS_OUT_BITS
    assert resolve_copy_self_mode(bits, life) == "chamber"
    org = GenesisOrganism.from_bits("h0", bits, initial_runtime_atp=40.0, position=(1, 1))
    state, births = _run(20005, configs, (org,), 4)
    assert births == 0
    assert not any(o.selfed for o in state.organisms)
    # Control: the same organism on the selfing locus does self.
    self_bits = LIFE_LOOP_EATER_GENOME + "100000" + OUTCROSS_SELFING_BITS
    selfer = GenesisOrganism.from_bits("h0", self_bits, initial_runtime_atp=40.0, position=(1, 1))
    _, self_births = _run(20005, configs, (selfer,), 4)
    assert self_births >= 1


@pytest.mark.parametrize("mating_set", [("hermaphrodite",), ("hermaphrodite", "male")])
def test_outcross_locus_hermaphrodite_never_selfs_in_self_mode(mating_set: tuple[str, ...]) -> None:
    """The self and outcross arms run the identical engine config and differ
    only in the locus (000 vs 001), so the mating system is the single
    manipulated factor. For that to hold, hermaphrodite_selfing=True must not
    by itself make a locus-001 hermaphrodite self. Expected: over 6 ticks no
    organism is marked selfed and every birth has two parents."""

    session, _ = _self_arm(OUTCROSS_OUT_BITS, mating_type_set=mating_set)
    founders = {o.id for o in session.runner.population.organisms}
    summary = session.run_ticks(6)
    population = session.runner.population
    assert summary["births"] >= 1
    assert not any(o.selfed for o in population.organisms)
    born = [rec for rec in population.lineage if rec.organism_id not in founders]
    assert born and all(rec.second_parent_id is not None for rec in born)


# Sex fixed for life: a parent ever seen as male never selfs.


def test_parent_ever_seen_as_male_is_never_a_selfer() -> None:
    """Self-fertilisation needs both gamete roles in one body, which a male
    lacks, and a sex is fixed for life. Over 12 ticks of the self arm we record
    every id ever read as male. Expected: none of them is ever selfed, read as
    another type later, or the parent of a selfed birth (second parent equal
    to parent)."""

    session, _ = _self_arm(OUTCROSS_SELFING_BITS)
    ever_male: set[str] = set()
    for _ in range(12):
        session.run_ticks(1)
        for organism in session.runner.population.organisms:
            if organism.mating_type == "male":
                ever_male.add(organism.id)
            elif organism.id in ever_male:
                raise AssertionError(f"{organism.id} changed sex from male")
    population = session.runner.population
    assert ever_male
    assert not any(o.selfed for o in population.organisms if o.id in ever_male)
    selfers = {rec.parent_id for rec in population.lineage if rec.parent_id and rec.second_parent_id == rec.parent_id}
    assert selfers and not selfers & ever_male


# Mutation-killing tests for the selfed pin and the selfed restore.


def test_selfed_hermaphrodite_pairs_with_a_male_before_its_type_is_stored() -> None:
    """A selfed organism is a hermaphrodite by construction, so the chamber must
    read it as one even before its type is stored at the end of the step. With
    sex_ratio 1.0 every drawn type is male, so if the chamber drew the selfed
    organism's type (the pin removed) it would read male and male x male is
    refused. Expected: the first step pairs the two and places both products
    (2 births); later steps add none in this small setup (the males are
    short of ATP and their copies pair with nobody in time). Value measured on this branch; the review saw 4 births
    before sex was fixed (sexes were redrawn each step) and the mutant
    without the pin gives 0."""

    configs = _configs(**{**_SEXES, "mating_type_set": ("hermaphrodite", "male"), "sex_ratio": 1.0})
    selfed = GenesisOrganism.from_bits("o0", _BITS[0], initial_runtime_atp=20.0, position=(1, 0))
    selfed.selfed = True
    male = GenesisOrganism.from_bits("o1", _BITS[1], initial_runtime_atp=20.0, position=(1, 1))
    _, births = _run(20005, configs, (selfed, male), 4)
    assert births == 2


def test_selfed_flag_survives_a_full_population_round_trip() -> None:
    """Being selfed is state (it fixes the type as hermaphrodite), so save and
    load must keep it. Expected: the restored organism is selfed and the
    restored population serializes to the same payload."""

    organism = GenesisOrganism.from_bits("o0", _BITS[0], initial_runtime_atp=20.0, position=(1, 0))
    organism.selfed = True
    population = PopulationState(0, 0, (organism,), (), ())
    restored = PopulationState.from_dict(json.loads(json.dumps(population.to_dict())))
    assert restored.organisms[0].selfed is True
    assert restored.to_dict() == population.to_dict()


# Strict booleans on restore.


@pytest.mark.parametrize("value", ["false", "true", 1, 0, None])
def test_non_boolean_selfing_values_are_refused_on_restore(value: object) -> None:
    """JSON booleans only: bool("false") is True, so a lax parse would turn the
    string "false" into an active selfing mode or a selfed organism."""

    payload = SexualRecombinationConfig(enabled=True).to_dict()
    payload["hermaphrodite_selfing"] = value  # type: ignore[assignment]
    with pytest.raises(ConfigurationError):
        SexualRecombinationConfig.from_dict(payload)
    organism = GenesisOrganism.from_bits("o0", _BITS[0], initial_runtime_atp=20.0, position=(1, 0))
    state = PopulationState(0, 0, (organism,), (), ()).to_dict()
    state["organisms"][0]["selfed"] = value  # type: ignore[index,assignment]
    with pytest.raises(ConfigurationError):
        PopulationState.from_dict(state)


# Outcross mating fee as its own ledger term.


def test_outcross_mating_fee_is_its_own_ledger_term() -> None:
    """The outcross arm pays a fixed mating fee per outcross copy
    (outcross_runtime_atp, default 1.0 ATP, a config value) on top of any cost
    of sons. Booked as its own term, the fee equals 1.0 times the number of
    fee rows; the self arm pays none. Expected values follow from the default
    fee of 1.0."""

    out_session, _ = _self_arm(OUTCROSS_OUT_BITS)
    self_session, _ = _self_arm(OUTCROSS_SELFING_BITS)
    out_session.run_ticks(3)
    self_session.run_ticks(3)
    out_fee = out_session.mating_fee_ledger()
    assert out_fee["term"] == "outcross_mating_fee"
    assert out_fee["ledger_reason"] == "outcross_runtime_cost"
    assert out_fee["events"] == out_session.summary()["outcross_debit_events"] >= 1
    assert out_fee["atp"] == pytest.approx(1.0 * out_fee["events"])
    assert self_session.mating_fee_ledger()["events"] == 0
    assert self_session.mating_fee_ledger()["atp"] == 0.0


# Selfing is self-fertilisation through the gamete path.


def test_haploid_selfed_child_fuses_two_identical_gametes() -> None:
    """Without diploid_meiosis the genome is haploid, so both gametes of a
    selfer equal its genome and their crossover returns the same bits:
    selfing transmits the genome unchanged (no segregation to expose).
    Expected: each selfed lineage record names the parent as both parents,
    carries a crossover digest, and (mutation rate 0) the parent genome."""

    session, _ = _self_arm(OUTCROSS_SELFING_BITS)
    founders = {o.id: o.genome.digest() for o in session.runner.population.organisms}
    session.run_ticks(6)
    population = session.runner.population
    digests = {**founders, **{rec.organism_id: rec.genome_digest for rec in population.lineage}}
    selfed = [rec for rec in population.lineage if rec.parent_id and rec.second_parent_id == rec.parent_id]
    assert selfed
    for rec in selfed:
        assert rec.recombination_digest is not None
        if rec.mutation_count == 0:
            assert rec.genome_digest == digests[rec.parent_id]


def test_diploid_selfing_makes_two_independent_meiotic_gametes() -> None:
    """With diploid_meiosis each gamete is a homolog-crossover product, as in
    outcrossing, so two gametes from one heterozygous parent can differ and a
    selfed child need not equal either homolog (segregation). The genome
    below has different even and odd codons, so its homologs differ. Expected:
    across 20 draws the fused child takes more than one value, and every
    record names two distinct gametes of the same parent."""

    from codontrace.genesis.population import RNGManager, _self_fertilisation_record

    cfg = SexualRecombinationConfig(enabled=True, recombination_prob=1.0, diploid_meiosis=True)
    parent = GenesisOrganism.from_bits("o0", "000111000111000111000111", initial_runtime_atp=1.0, position=(0, 0))
    children = set()
    for seed in range(20):
        record = _self_fertilisation_record(parent, cfg, RNGManager(seed))
        assert record is not None
        assert {record.parent_a_id, record.parent_b_id} == {"o0:gamete_a", "o0:gamete_b"}
        children.add(record.child_genome_bits)
    assert len(children) > 1


# Cost of sons as its own ledger term.


@pytest.mark.parametrize("diploid", [False, True])
def test_son_cost_is_its_own_term_in_both_arms(diploid: bool) -> None:
    """A son cannot bear offspring, so the ATP given to sons is the cost of
    males. Selfed progeny are all hermaphrodite and male-sired progeny are
    sons at sex_ratio, so the JR5 self arm, set (hermaphrodite,), makes no
    sons and the outcross arm, set (hermaphrodite, male), does. Expected: self
    arm term 0; outcross arm term equals the summed initial ATP of its male
    newborns; both terms are separate from the mating fee term. Both arms
    run with and without diploid_meiosis (JR5 runs it on)."""

    self_session, _ = _self_arm(OUTCROSS_SELFING_BITS, mating_type_set=("hermaphrodite",), diploid_meiosis=diploid)
    out_session, _ = _self_arm(OUTCROSS_OUT_BITS, mating_type_set=("hermaphrodite", "male"), diploid_meiosis=diploid)
    seen = {o.id for o in out_session.runner.population.organisms}
    son_atp: list[float] = []
    self_session.run_ticks(3)
    for _ in range(3):
        out_session.run_ticks(1)
        for o in out_session.runner.population.organisms:
            if o.id not in seen:
                seen.add(o.id)
                if o.mating_type == "male":
                    son_atp.append(o.atp_state.runtime.to_dict()["initial_atp"])  # type: ignore[arg-type]
    self_cost = self_session.son_cost_ledger()
    assert self_cost["term"] == "son_allocation"
    assert self_cost["offspring"] >= 1 and self_cost["sons"] == 0 and self_cost["atp"] == 0.0
    out_cost = out_session.son_cost_ledger()
    assert out_cost["sons"] == len(son_atp) >= 1
    assert out_cost["atp"] == pytest.approx(sum(son_atp))
    assert 0.0 < out_cost["son_fraction"] < 1.0
    assert out_session.mating_fee_ledger()["term"] != out_cost["term"]


# Census, and the E1 fit input it provides.


@pytest.mark.parametrize("diploid", [False, True])
def test_census_reports_sexes_modes_and_sons_in_both_arms(diploid: bool) -> None:
    """Selfed progeny are all hermaphrodite and outcrossed progeny include sons
    at sex_ratio, so the census of the self arm, set (hermaphrodite,), has no
    males and only selfed births, while the outcross arm, set
    (hermaphrodite, male), has males and outcrossed births. Expected: one row
    per generation from 0 to 4, counts sum to the census, and the summed sons
    and son ATP equal the son_allocation term."""

    for bits, types, mode in (
        (OUTCROSS_SELFING_BITS, ("hermaphrodite",), "selfed"),
        (OUTCROSS_OUT_BITS, ("hermaphrodite", "male"), "outcrossed"),
    ):
        session, _ = _self_arm(bits, mating_type_set=types, diploid_meiosis=diploid)
        session.run_ticks(4)
        rows = session.census()
        assert [row["generation"] for row in rows] == [0, 1, 2, 3, 4]
        assert all(sum(row["counts"].values()) == row["census"] for row in rows)
        assert set().union(*(row["counts"] for row in rows)) <= set(types)
        assert sum(row[mode] for row in rows) == sum(row["births"] for row in rows) >= 1
        cost = session.son_cost_ledger()
        assert sum(row["sons_born"] for row in rows) == cost["sons"]
        assert sum(row["son_atp"] for row in rows) == pytest.approx(cost["atp"])
        assert (cost["sons"] == 0) == (types == ("hermaphrodite",))


def test_census_male_share_and_m_are_defined_per_generation() -> None:
    """Two sex-ratio quantities: male_share_population is males over the census
    (standing ratio); m is sons over births of outcrossing parents, the prereg
    m (sex allocation of outcrossed offspring; selfed progeny are never sons).
    Expected: both recomputed from the row's own counts, m is None in rows with
    no outcrossed births, and in the outcross arm, where every birth is
    outcrossed, m equals sons_born over births."""

    for bits, types in (
        (OUTCROSS_OUT_BITS, ("hermaphrodite", "male")),
        (OUTCROSS_SELFING_BITS, ("hermaphrodite",)),
    ):
        session, _ = _self_arm(bits, mating_type_set=types)
        session.run_ticks(4)
        for row in session.census():
            assert "sex_ratio_male" not in row
            assert row["male_share_population"] == row["counts"].get("male", 0) / row["census"]
            if not row["outcrossed"]:
                assert row["m"] is None
            elif row["outcrossed"] == row["births"]:
                assert row["m"] == row["sons_born"] / row["births"]


def test_enabling_sexes_mid_run_is_refused() -> None:
    """The mating seed is captured at the first sexes-on step; enabling sexes
    after generation 0 would key sexes to a later step, so it is refused.
    Expected: ConfigurationError when a population past generation 0 with no
    mating seed is stepped with mating types on; generation 0 is accepted."""

    session, _ = _self_arm(OUTCROSS_OUT_BITS)
    runner = session.runner
    late = replace(runner.population, generation=3, mating_seed=None)
    from codontrace.genesis.population import step_population

    with pytest.raises(ConfigurationError, match="generation 0"):
        step_population(late, runner.world, runner.configs, seed=5)
    step_population(replace(late, generation=0), runner.world, runner.configs, seed=5)


def test_census_counts_the_asexual_founder_lineage() -> None:
    """E1 tracks the asexual share; the census counts asexual-lineage
    organisms under "asexual". Expected: one founder marked asexual is counted
    at generation 0, and e1_counts returns generation, asexual count and
    census per row."""

    session, _ = _self_arm(OUTCROSS_OUT_BITS)
    session.runner.population.organisms[0].asexual_lineage = True
    session.run_ticks(2)
    generations, asexual, census = session.e1_counts("asexual")
    assert generations == [0, 1, 2]
    assert asexual[0] == 1 and all(a >= 1 for a in asexual)
    assert census == [row["census"] for row in session.census()]


# Regression pins, not the prereg E1 estimand: the bias-reduced binomial
# logit of tests/_jr5_e1_fit.py fitted to the male count of a 4-founder run
# with no asexual lineage. Both current pins use outcross fee 0.0
# (outcross_runtime_atp=0.0, the prereg confirmatory setting). The prereg E1 fit (asexual count, 0.2 asexual
# founders) is pinned separately as _E1_PREREG_ASEXUAL below.
# Re-pin history, each step checked by rerunning the fit at the commits named:
# - Outcross arm: (0.79900229, -0.09470521) on the 2b tip 8be79b12 with the
#   old setup (outcross fee 1.0). Merging the gamete-fusion fix moved it to
#   (0.38787177, -0.00003415) on that setup; the setup change to outcross fee
#   0.0 then gave (0.80725957, -0.32454182). The selfing fix did not move it.
# - Self arm: only this pin moved with the selfing fix, from (-3.8506,-0.1356)
#   to (-3.9159,-0.1605), because genome length went from 9 to 18 bits (before
#   the fix a selfed child was the parent's even homolog alone, so the genome
#   halved). The self arm has zero males, so its intercept sits at the
#   bias-reduced lower bound. Selfing pays no outcross fee, so the fee
#   setting does not enter this arm.
_E1_MALE_OUTCROSS_DIPLOID = (0.80725957, -0.32454182)
_E1_MALE_SELF_DIPLOID = (-3.91594154, -0.16053908)
# The prereg E1 estimand: asexual count out of census against generation,
# obligate-outcross host arm with an asexual founder fraction of 0.2 and no
# parasite (this session has no host-parasite world clock), outcross fee 0.0.
# Computed with the
# same estimator on this branch.
_E1_PREREG_ASEXUAL = (-1.23889801, 0.05642555)


def _prereg_e1_arm(bits: str, types: tuple[str, ...]) -> ClosedLoopP5Session:
    session = ClosedLoopP5Session.boot(seed=20011, outcross_bits=bits, outcross_runtime_atp=0.0)
    cfg = _sexes_for(
        session,
        **{**_ANDRO, "hermaphrodite_selfing": True, "mating_type_set": types, "diploid_meiosis": True},
    )
    session.runner.configs = replace(session.runner.configs, sexual_recombination=cfg)
    return session


def test_e1_fit_on_the_census_is_pinned() -> None:
    """The census feeds the E1 fit: count out of census against generation,
    bias-reduced logit (likelihood plus half the log determinant of the
    Fisher information). Regression pin, not the prereg estimand (see the
    comment above the pins). Input: outcross fee 0.0,
    diploid_meiosis on, seed 20011, 6 generations; male counts of the outcross
    arm, set (hermaphrodite, male), and of the self arm, set (hermaphrodite,).
    Expected: the pinned intercept and slope (computed with this estimator on
    this branch after gamete fusion and the selfing fix); genome length stays 18 bits; the plain
    fit differs on the outcross arm, and on the self arm's all-zero male count,
    where the plain estimate does not exist, the bias-reduced one is finite
    (the reason the prereg uses it)."""

    np = pytest.importorskip("numpy")
    from tests._jr5_e1_fit import fit_logit

    for bits, types, pin in (
        (OUTCROSS_OUT_BITS, ("hermaphrodite", "male"), _E1_MALE_OUTCROSS_DIPLOID),
        (OUTCROSS_SELFING_BITS, ("hermaphrodite",), _E1_MALE_SELF_DIPLOID),
    ):
        session = _prereg_e1_arm(bits, types)
        assert session.runner.configs.closed_loop_hp_life.outcross_runtime_atp == 0.0
        session.run_ticks(6)
        assert {len(o.genome.to_compact()) for o in session.runner.population.organisms} == {18}
        generations, males, census = session.e1_counts("male")
        assert generations == [0, 1, 2, 3, 4, 5, 6]
        x = np.array(generations, dtype=float)
        k = np.array(males, dtype=float)
        n = np.array(census, dtype=float)
        beta = fit_logit(k, n, x, bias_reduced=True)
        assert beta == pytest.approx(pin, abs=1e-7)
        if types == ("hermaphrodite",):
            assert k.sum() == 0 and np.all(np.isfinite(beta))
        else:
            assert not np.allclose(fit_logit(k, n, x, bias_reduced=False), beta, atol=1e-6)


def test_prereg_e1_fit_on_the_asexual_count_is_pinned() -> None:
    """Toy regression of the prereg E1 estimator, not registered-instrument
    calibration. Same response and bias-reduced fit as prereg E1
    (asexual count out of census against generation), but on a small toy
    session: N = 10 founders, male fraction m = 0.3, T = 6 generations,
    seed 20011. Registered E1 instead uses N = 200 / 50, m = 0.5 / 0.25,
    and T = 5 / 11. Setup otherwise mirrors the gate: no parasite, obligate
    outcross (outcross locus, set (hermaphrodite, male), outcross fee 0.0,
    diploid_meiosis on) plus an asexual founder fraction of 0.2 (2 of 10
    founders marked asexual lineage). Expected: generation 0 has 2 asexual
    out of 10 (0.2); the asexual line persists; the fit equals the pin
    computed with this estimator on this toy; and it differs from the
    male-count regression pin, a different estimand."""

    np = pytest.importorskip("numpy")
    from tests._jr5_e1_fit import fit_logit

    session = ClosedLoopP5Session.boot(
        seed=20011,
        outcross_bits=OUTCROSS_OUT_BITS,
        outcross_runtime_atp=0.0,
        n_primary=5,
        n_secondary=5,
    )
    cfg = _sexes_for(
        session,
        **{**_ANDRO, "hermaphrodite_selfing": True, "diploid_meiosis": True},
    )
    session.runner.configs = replace(session.runner.configs, sexual_recombination=cfg)
    founders = session.runner.population.organisms
    for organism in founders[: round(0.2 * len(founders))]:
        organism.asexual_lineage = True
    session.run_ticks(6)
    generations, asexual, census = session.e1_counts("asexual")
    assert generations == [0, 1, 2, 3, 4, 5, 6]
    assert asexual[0] / census[0] == 0.2 and min(asexual) >= 1
    beta = fit_logit(
        np.array(asexual, dtype=float),
        np.array(census, dtype=float),
        np.array(generations, dtype=float),
        bias_reduced=True,
    )
    assert beta == pytest.approx(_E1_PREREG_ASEXUAL, abs=1e-7)
    assert not np.allclose(beta, _E1_MALE_OUTCROSS_DIPLOID, atol=1e-3)


def _selfed_child_bits(bits: str, seed: int, recombination_prob: float = 1.0) -> str:
    from codontrace.genesis.population import _self_fertilisation_record
    from codontrace.rng import RNGManager

    parent = GenesisOrganism.from_bits("p", bits, initial_runtime_atp=10.0, position=(0, 0))
    config = SexualRecombinationConfig(
        enabled=True, diploid_meiosis=True, recombination_prob=recombination_prob
    )
    record = _self_fertilisation_record(parent, config, RNGManager(seed).fork("self"))
    assert record is not None
    return record.child_genome_bits


def test_selfed_child_keeps_parent_length_over_generations() -> None:
    """Selfing with diploid meiosis is two meioses in one parent and a fusion
    of the two gametes as the child's homologs, so each gamete carries one copy
    of every locus and the child has the parent's length. Expected: the founder
    length, exactly, in each of 5 selfed generations, for an even and an odd
    codon count.

    Length alone is also kept by a clone, so the second part checks that the
    child is a fusion of two gametes. With recombination_prob 0 there is no
    crossover and each gamete is exactly one parental homolog, picked with
    probability 1/2 by segregation. Parent: even homolog all 000, odd all 111
    (4 loci). Expected: every child homolog equals one parental homolog, and
    over 200 seeds all four (egg, pollen) homolog pairs occur, including the
    two homozygous ones a clone or a single gamete cannot give. Chance that
    one pair is missing by luck is at most 4 * (3/4)**200, below 1e-24."""

    from codontrace.genesis.birth import split_diploid_homologs

    for founder in (LIFE_LOOP_EATER_GENOME + "101000111", "010110001111000101011"):
        bits = founder
        for generation in range(5):
            bits = _selfed_child_bits(bits, 1000 + generation)
            assert len(bits) == len(founder)

    parent = "".join("000" if i % 2 == 0 else "111" for i in range(8))
    homologs = split_diploid_homologs(parent, 3)
    pairs = set()
    for seed in range(200):
        child = _selfed_child_bits(parent, seed, recombination_prob=0.0)
        assert len(child) == len(parent)
        egg, pollen = split_diploid_homologs(child, 3)
        assert egg in homologs and pollen in homologs
        pairs.add((egg, pollen))
    assert pairs == {(x, y) for x in homologs for y in homologs}


def test_selfing_meioses_draw_independent_crossover_gates() -> None:
    """The two meioses of a selfing parent are separate events, so each draws
    its own crossover gate from its own RNGManager stream. With
    recombination_prob p = 0.5 the pair of gates is (True, True), (True,
    False), (False, True) or (False, False) with probability 1/4 each if the
    draws are independent; one shared draw gives only the two equal pairs.
    Over N = 4000 seeds the count of unequal pairs is Binomial(N, 1/2): mean
    2000, SD sqrt(N / 4) = 31.6, tolerance 4 SD = 126.5. The same seed gives
    the same pair (deterministic), and p = 1.0 or 0.0 makes no draw."""

    from codontrace.genesis.population import _selfing_crossover_gates
    from codontrace.rng import RNGManager

    half = SexualRecombinationConfig(enabled=True, diploid_meiosis=True, recombination_prob=0.5)
    n = 4000
    unequal = 0
    for seed in range(n):
        gates = _selfing_crossover_gates(half, RNGManager(seed).fork("self"))
        assert gates == _selfing_crossover_gates(half, RNGManager(seed).fork("self"))
        unequal += gates[0] != gates[1]
    assert abs(unequal - n / 2) < 4 * (n / 4) ** 0.5
    for prob, expected in ((1.0, (True, True)), (0.0, (False, False))):
        cfg = replace(half, recombination_prob=prob)
        assert _selfing_crossover_gates(cfg, RNGManager(1).fork("self")) == expected


def _heterozygous_loci(bits: str) -> int:
    from codontrace.genesis.birth import split_diploid_homologs

    even, odd = split_diploid_homologs(bits, 3)
    loci = min(len(even), len(odd)) // 3
    return sum(even[3 * i : 3 * i + 3] != odd[3 * i : 3 * i + 3] for i in range(loci))


def test_self_fertilisation_passes_an_independent_crossover_gate_to_each_meiosis(
    monkeypatch: object,
) -> None:
    """Each meiosis of a selfing birth draws its own crossover gate.

    `_self_fertilisation_record` with diploid_meiosis calls `meiotic_gamete`
    twice and must pass each call its own gate from `meiosis/a/gate` and
    `meiosis/b/gate`. This test records the `crossover=` argument of each
    `meiotic_gamete` call (re-binding that name in `birth` and `population`).
    The outcross zygote check
    (`test_each_meiosis_of_a_zygote_draws_its_own_crossover_gate`) instead
    hooks `_meiosis_crossover_gate` on the fertilise path; same binomial
    arithmetic, different hook. At recombination_prob p = 0.5 independent
    draws make the two gates differ with probability 2 * p * (1 - p) = 1/2;
    a call-site mutant that reuses one gate for both meioses never differs.
    Over N = 4000 births the count of unequal pairs is Binomial(N, 1/2):
    mean 2000, SD sqrt(N / 4) = 31.6, tolerance 4 SD."""

    from codontrace.genesis import birth as birth_mod
    from codontrace.genesis.population import _self_fertilisation_record
    from codontrace.rng import RNGManager

    gates: list[bool] = []
    real = birth_mod.meiotic_gamete

    def record(bits: str, width: int, rng: object, crossover: bool = True) -> str:
        gates.append(bool(crossover))
        return real(bits, width, rng, crossover=crossover)

    monkeypatch.setattr(birth_mod, "meiotic_gamete", record)
    # population imports meiotic_gamete as a name; re-bind there too
    from codontrace.genesis import population as pop

    monkeypatch.setattr(pop, "meiotic_gamete", record)
    parent = GenesisOrganism.from_bits(
        "p", "000111" * 8, initial_runtime_atp=10.0, position=(0, 0)
    )
    cfg = SexualRecombinationConfig(
        enabled=True, diploid_meiosis=True, recombination_prob=0.5
    )
    n = 4000
    unequal = 0
    for seed in range(n):
        gates.clear()
        record_out = _self_fertilisation_record(parent, cfg, RNGManager(seed).fork("self"))
        assert record_out is not None
        assert len(gates) == 2
        unequal += gates[0] != gates[1]
    assert abs(unequal - n / 2) < 4 * (n / 4) ** 0.5


def test_heterozygosity_halves_per_selfed_generation_through_step_population() -> None:
    """Complete selfing over several generations, run with
    PopulationRunner.step_generation (which calls step_population). Male-free
    self arm, set (hermaphrodite,), selfing locus, diploid_meiosis on, no
    mutation, 10 founders, seeds 0-19, 16 steps each.

    Derivation: at a locus heterozygous in the parent each gamete carries
    either homolog with probability 1/2, independently of the other gamete,
    so the child is heterozygous there with probability 1/2; a homozygous
    locus stays homozygous. So E[H_child | parent] = H_parent / 2 and, by
    iterating, H_t = H_0 * 0.5**t after t selfed generations.

    The engine selects on genotype (a homozygous child runs a different
    program and may breed less), so the H of all depth-t organisms is not an
    unselected sample. The test therefore checks the transmission step at each
    selfing depth t (generations from a founder, read from the lineage): the
    ratio R_t of heterozygous loci in depth-t children over those in their
    parents is 1/2, and the chain H_t / H_0 = R_1 * ... * R_t equals 0.5**t.
    Tolerance: per locus the child is Bernoulli(1/2), variance 1/4. Loci in
    one genome are linked (a gamete's leading homolog is one draw), so the
    worst case treats a parent's m heterozygous loci as one draw, variance
    m**2 / 4. With M = sum of m, the SD of R_t is at most
    sqrt(sum m**2) / (2 * M); the bound is 4 SD. Depths 1 and 2 have enough
    births to test; the chain's bound adds the two 4-SD bounds."""

    births: dict[int, list[tuple[int, int]]] = {}
    for seed in range(20):
        session = ClosedLoopP5Session.boot(
            seed=seed,
            outcross_bits=OUTCROSS_SELFING_BITS,
            outcross_runtime_atp=0.0,
            n_primary=5,
            n_secondary=5,
            max_population=200,
            world_size=16,
        )
        cfg = _sexes_for(
            session,
            mating_type_set=("hermaphrodite",),
            hermaphrodite_selfing=True,
            diploid_meiosis=True,
        )
        runner = session.runner
        runner.configs = replace(runner.configs, sexual_recombination=cfg)
        genome = {o.id: o.genome.to_compact() for o in runner.population.organisms}
        depth = dict.fromkeys(genome, 0)
        for step in range(16):
            runner.step_generation(seed=seed * 1000 + step)
            live = {o.id: o.genome.to_compact() for o in runner.population.organisms}
            for rec in runner.population.lineage:
                child, parent = rec.organism_id, rec.parent_id
                if child in genome or child not in live or parent not in genome:
                    continue
                assert rec.second_parent_id in (None, parent)
                genome[child] = live[child]
                depth[child] = depth[parent] + 1
                births.setdefault(depth[child], []).append(
                    (_heterozygous_loci(genome[child]), _heterozygous_loci(genome[parent]))
                )

    chain, bound = 1.0, 0.0
    for t in (1, 2):
        rows = births[t]
        total = sum(m for _, m in rows)
        assert total >= 100
        ratio = sum(k for k, _ in rows) / total
        sd = sum(m * m for _, m in rows) ** 0.5 / (2 * total)
        assert abs(ratio - 0.5) < 4 * sd
        chain *= ratio
        bound += 4 * sd
        assert abs(chain - 0.5**t) < bound


def test_heterozygosity_follows_h0_over_two_to_the_t_on_independent_neutral_lineages() -> None:
    """Independent neutral selfing lineages: H_t = H_0 / 2**t for t = 1..4.

    Each lineage is one diploid genome selfed by `_self_fertilisation_record`
    (two meioses then fusion) with no selection, no shared parents across
    lineages, and randomness only from RNGManager. Founder: even homolog all
    000, odd all 111, 16 codons / 8 loci, so H_0 = 1 and length 48. N = 1000
    lineages at each of recombination_prob in {0, 0.5, 1}. Seeds are
    partitioned by arm with stride N * 16 + 16 = 16016 (>= 16000): arm a uses
    40_000 + a * stride + lineage * 16 + t, so the three arms never reuse a
    seed (within an arm, lineage * 16 + t < stride).

    Derivation (Mendelian transmission under complete selfing): at a locus
    heterozygous in the parent each of the two independent gametes carries
    either homolog with probability 1/2, so the child is heterozygous there
    with probability 1/2; a homozygous locus stays homozygous. Hence
    E[H_child | parent] = H_parent / 2, and after t selfed generations
    E[H_t] = H_0 / 2**t. With H_0 = 1 that is mu_t = 2**(-t). Allele
    frequency is unchanged; only genotype frequencies move. The law is for a
    single selfing line; averaging N independent lines estimates that
    expectation.

    Tolerance: each lineage's H is a fraction in [0, 1] with mean mu_t, so
    its variance is at most mu_t * (1 - mu_t) (sharp bound for a [0, 1]
    random variable with fixed mean). Independent lineages make the
    sample-mean variance at most that over N, so the SE bound used here is
    4 * sqrt(mu_t * (1 - mu_t) / N). The looser 0.5 / sqrt(N) bound (any
    [0, 1] variable has variance at most 1/4) cannot reject a forced H = 0
    at t = 4, where mu_4 = 1/16 and |0 - 1/16| < 4 * 0.5 / sqrt(N); the
    mean-dependent bound can. Related births in one selected population
    would not justify that SE. Every child keeps length 48. Reusing one
    meiosis for both gametes forces H = 0 at t = 1, far outside the bound.
    Uniqueness bound (principled): a collapse mutant that replaces every
    contiguous block of K next-parents with one child yields exactly N/K
    distinct genomes in the pool passed forward. At p >= 0.5 independent
    meioses over 8 loci still collide: observed distinctness on this
    fixture bottoms near ~320 by t = 4 at p = 0.5, so an N/2 or N/3
    threshold false-fails. N/4 = 250 is the tightest integer-divisor bound
    that stays below that natural floor with margin, and it rejects every
    systematic collapse of family size K >= 4 (including a K = 10 block).
    Families of size 2 or 3 are not guaranteed to be rejected at p = 0.5
    because natural collisions already sit near those thresholds. At
    recombination_prob = 0 only a few whole-homolog genotypes exist, so
    that uniqueness check is not applied there."""

    n_lineages = 1000
    founder = "000111" * 8
    assert _heterozygous_loci(founder) / (len(founder) // 6) == 1.0
    arm_stride = n_lineages * 16 + 16
    assert arm_stride >= 16_000
    for arm, recombination_prob in enumerate((0.0, 0.5, 1.0)):
        genomes = [founder] * n_lineages
        for t in range(1, 5):
            children = [
                _selfed_child_bits(
                    bits,
                    seed=40_000 + arm * arm_stride + lineage * 16 + t,
                    recombination_prob=recombination_prob,
                )
                for lineage, bits in enumerate(genomes)
            ]
            assert {len(child) for child in children} == {48}
            observed = sum(
                _heterozygous_loci(child) / (len(child) // 6) for child in children
            ) / n_lineages
            expected = 0.5**t
            bound = 4.0 * (expected * (1.0 - expected) / n_lineages) ** 0.5
            assert abs(observed - expected) < bound
            genomes = children
            # After the hand-off: reject a systematic collapse of family
            # size K >= 4 (exactly N/K distinct). Bound N/4 is derived above
            # from the natural distinctness floor at p = 0.5; check the
            # genomes passed forward so the collapse is visible.
            if recombination_prob >= 0.5:
                collapse_block = 4
                assert len(set(genomes)) > n_lineages // collapse_block




def test_uniqueness_bound_rejects_family_size_five() -> None:
    """The N/4 uniqueness bound rejects a K=5 collapse; N/10 would not.

    A pool of N = 1000 genomes with exactly N/5 distinct values models a
    mutant that replaces every contiguous block of 5 next-parents with one
    child. That pool fails `|set| > N/4` and would pass the older
    H3-tied `|set| > N/10`, so the tighter bound is what catches family
    sizes between 5 and 9 inclusive.
    """

    n = 1000
    genomes = [f"g{i // 5}" for i in range(n)]
    assert len(set(genomes)) == n // 5
    assert not (len(set(genomes)) > n // 4)
    assert len(set(genomes)) > n // 10


def test_heterozygosity_arm_seed_blocks_are_disjoint() -> None:
    """The three p-arm seed blocks of the H-decay fixture must not overlap.

    Seeds are `40_000 + arm * stride + lineage * 16 + t` with
    `stride = N * 16 + 16`, N = 1000, arm in {0, 1, 2}, lineage in
    `0..N-1`, t in `1..4`. Within one arm the max offset is
    `(N - 1) * 16 + 4 = 15988 < stride`, so arms abut with a gap of
    `stride - 15988 = 28` and never share a seed. A mutant that shrinks
    the stride below that span (or that keys arms by a colliding function
    of p) reuses seeds across arms and this set-equality fails.
    """

    n_lineages = 1000
    arm_stride = n_lineages * 16 + 16
    assert arm_stride >= 16_000
    blocks: list[set[int]] = []
    for arm in range(3):
        seeds = {
            40_000 + arm * arm_stride + lineage * 16 + t
            for lineage in range(n_lineages)
            for t in range(1, 5)
        }
        blocks.append(seeds)
    assert len(blocks[0]) == n_lineages * 4
    for i in range(3):
        for j in range(i + 1, 3):
            assert blocks[i].isdisjoint(blocks[j])
    # Contiguous span check: arm a occupies [base, base + max_offset]
    max_offset = (n_lineages - 1) * 16 + 4
    assert max_offset < arm_stride
    for arm in range(3):
        base = 40_000 + arm * arm_stride
        assert min(blocks[arm]) == base + 1  # lineage 0, t=1
        assert max(blocks[arm]) == base + max_offset


def test_one_selfed_generation_halves_heterozygosity() -> None:
    """A parent heterozygous at every locus (even homolog all 000, odd all 111,
    8 codons so 4 loci) is selfed once. Each locus of the child is
    heterozygous when the two gametes carry different homologs there; each
    gamete carries either homolog with probability 1/2 independently, so
    P(het) = 1/2 and expected H = 0.5. H per child is a mean of values in
    [0, 1], so its variance is at most 1/4 and 4 standard errors of the mean
    over N = 3000 children are at most 4 * 0.5 / sqrt(3000) = 0.0365."""

    parent = "".join("000" if i % 2 == 0 else "111" for i in range(8))
    n = 3000
    total = 0.0
    for i in range(n):
        child = _selfed_child_bits(parent, i)
        codons = [child[k : k + 3] for k in range(0, len(child), 3)]
        loci = [(codons[k], codons[k + 1]) for k in range(0, 8, 2)]
        total += sum(a != b for a, b in loci) / len(loci)
    assert abs(total / n - 0.5) < 4 * 0.5 / n**0.5


def test_prereg_m_counts_sons_of_outcrossed_births_only() -> None:
    """The prereg m is sons over births of outcrossing parents. Row: 4
    outcrossed births (1 son), 4 selfed births and 2 uniparental births.
    Expected by hand: m = 1/4; sons over all births would give 1/10 and sons
    over sexual births 1/8, so either mutant fails. A row with no outcrossed
    births has m None."""

    from codontrace.genesis.closed_loop_p5 import birth_modes_and_m

    births = [
        ("male", "a", "b"),
        ("hermaphrodite", "a", "c"),
        ("hermaphrodite", "b", "c"),
        ("hermaphrodite", "c", "a"),
        ("hermaphrodite", "s", "s"),
        ("hermaphrodite", "s", "s"),
        ("hermaphrodite", "t", "t"),
        ("hermaphrodite", "t", "t"),
        ("hermaphrodite", "u", None),
        ("male", "u", None),
    ]
    modes, m = birth_modes_and_m(births)
    assert modes == {"selfed": 4, "outcrossed": 4, "uniparental": 2}
    outcross_sons = sum(1 for kind, p, q in births if q is not None and q != p and kind == "male")
    assert m == outcross_sons / modes["outcrossed"] == 0.25
    assert birth_modes_and_m([("hermaphrodite", "s", "s")])[1] is None


def test_generation_zero_guard_rejects_edited_snapshots() -> None:
    """The mating seed must come from the run's first sexes-on step. A
    snapshot cannot dodge this: with no generation key it is rejected at
    from_dict; edited back to generation 0 it still has its tick and lineage;
    with a mating_seed injected into a sexes-off snapshot its organisms have
    no stored type. Expected: ConfigurationError in all three cases, and a
    real sexes-on snapshot round-trips and steps."""

    from codontrace.genesis.population import step_population

    session, _ = _self_arm(OUTCROSS_OUT_BITS)
    on_runner = session.runner
    off = ClosedLoopP5Session.boot(seed=20011, outcross_bits=OUTCROSS_OUT_BITS)
    off.run_ticks(2)
    off_data = dict(off.runner.population.to_dict())
    assert "mating_seed" not in off_data

    missing = {k: v for k, v in off_data.items() if k != "generation"}
    with pytest.raises(ConfigurationError, match="no generation"):
        PopulationState.from_dict(missing)

    edited = PopulationState.from_dict({**off_data, "generation": 0})
    with pytest.raises(ConfigurationError, match="generation 0"):
        step_population(edited, on_runner.world, on_runner.configs, seed=5)

    with pytest.raises(ConfigurationError, match="stored mating"):
        injected = PopulationState.from_dict({**off_data, "mating_seed": 20011})
        step_population(injected, on_runner.world, on_runner.configs, seed=5)

    session.run_ticks(1)
    real = PopulationState.from_dict(session.runner.population.to_dict())
    step_population(real, on_runner.world, on_runner.configs, seed=5)


def test_sexes_on_snapshot_cannot_be_reset_or_reseeded() -> None:
    """Sex is fixed for life and keyed to the run's mating seed. A sexes-on
    snapshot keeps both: each organism's stored type and the seed. Expected:
    (a) a full reset (generation 0, tick 0, no lineage, no mating_seed) still
    has stored types, so stepping it is refused; (b) a seed edited so that
    the draw for some non-selfed organism's id differs from its stored type
    is refused; (c) the real snapshot steps. Seeds 1..50 are tried for (b);
    with two types at sex ratio 0.3 a draw differs from the stored type with
    probability 0.42 per organism, so at least one such seed is found."""

    from codontrace.genesis.mating_types import draw_mating_type
    from codontrace.genesis.population import step_population

    session, cfg = _self_arm(OUTCROSS_OUT_BITS)
    session.run_ticks(1)
    runner = session.runner
    data = dict(runner.population.to_dict())
    assert isinstance(data.get("mating_seed"), int)

    with pytest.raises(ConfigurationError, match="cannot be reset"):
        PopulationState.from_dict(
            {**{k: v for k, v in data.items() if k != "mating_seed"}, "generation": 0, "tick": 0, "lineage": []}
        )

    real = PopulationState.from_dict(data)
    typed = [o for o in real.organisms if o.mating_type is not None and not o.selfed]
    assert typed
    edits = [
        data["mating_seed"] + k
        for k in range(1, 51)
        if any(o.mating_type != draw_mating_type(data["mating_seed"] + k, o.id, cfg) for o in typed)
    ]
    assert edits
    with pytest.raises(ConfigurationError, match="was edited"):
        PopulationState.from_dict({**data, "mating_seed": edits[0]})

    step_population(real, runner.world, runner.configs, seed=5)


def test_snapshot_rejects_seed_edits_even_when_all_stored_types_match() -> None:
    """Sex is fixed at birth, but equal type draws do not identify a seed.

    With finitely many two-valued stored types, different seeds can produce
    the same vector of types yet draw different types for future offspring.
    Expected: changing only the seed is refused even for such a collision;
    deleting the checksum is refused too. An unedited JSON round-trip resumes.
    This is an edit check, not protection against a recomputed checksum.
    """
    from codontrace.genesis.mating_types import draw_mating_type
    from codontrace.genesis.population import step_population

    session, cfg = _self_arm(OUTCROSS_OUT_BITS)
    session.run_ticks(1)
    runner = session.runner
    data = dict(runner.population.to_dict())
    original = data["mating_seed"]
    assert isinstance(original, int)
    typed = [o for o in runner.population.organisms if o.mating_type is not None and not o.selfed and not o.asexual_lineage]
    assert typed
    collision = next(
        seed for seed in range(original + 1, original + 10000)
        if all(o.mating_type == draw_mating_type(seed, o.id, cfg) for o in typed)
    )
    with pytest.raises(ConfigurationError, match="was edited"):
        PopulationState.from_dict({**data, "mating_seed": collision})
    without_digest = {k: v for k, v in data.items() if k != "mating_snapshot_digest"}
    with pytest.raises(ConfigurationError, match="integrity digest"):
        PopulationState.from_dict(without_digest)
    restored = PopulationState.from_dict(json.loads(json.dumps(data)))
    step_population(restored, runner.world, runner.configs, seed=5)
