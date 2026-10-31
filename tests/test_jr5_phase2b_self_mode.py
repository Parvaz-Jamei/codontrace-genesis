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

# Re-pinned when sex became fixed for life (sexes-on runs store each type and
# the run seed). One step uses the run seed for every draw, so the step pins
# with the stored fields removed still equal ``_BASE_ERA``. The two-tick
# session with the outcross locus changed in dynamics too: at 7db2227a the
# second tick redrew every sex from that tick's seed, which was the bug.
_FIXED_SEX_ERA = {
    "fm20005": "acea93875ee9a3c9dfc707c79e8404b3abbc0f6c0df6616fa67a741c8ad2f12c",
    "hm20005": "2d42e01d9459155cf37e68ba92fa66bb2ff11ff089586713e0220133535d01ad",
    "fm20008": "0c31c0f76a62810be2fc737b36072e49d9e1341b615605695e2b13c6f9958578",
    "hm20008": "351fa482d2b0c92d4e8918394d2ddfb1adcf7814a56b35774d2174acc30f80fa",
    "fm20013": "211e7024dd499bad7450c668daf26575d351690afe16d80c9ea443524ffc7746",
    "hm20013": "8d7ee0376f24ad5647a38a2dd08f01b993f361a38e94c4105f80d2a4cee789bf",
    "p5" + OUTCROSS_OUT_BITS: "69a818e96003b6bf2425eaca64e67793f47fa9b92fbf8db6447bdac112f9e8eb",
    "p5" + OUTCROSS_SELFING_BITS: "a6bf00e0399acec8c5e447eabd3653c18d2431aaac704409f7e22f264db2e112",
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
    """Every uniparental birth must come from a parent that was a hermaphrodite
    in the step that made it. The session steps with seed + tick index, so the
    type is read with that step's seed (selfed organisms are pinned anyway)."""

    session, cfg = _self_arm(OUTCROSS_SELFING_BITS)
    selfed_parents: list[str] = []
    for _ in range(3):
        step_seed = session.seed + session.tick_index
        before = session.runner.population
        types = {o.id: mating_type_of(before, o.id, seed=step_seed, sexual=cfg) for o in before.organisms}
        known = {rec.organism_id for rec in before.lineage}
        session.run_ticks(1)
        for rec in session.runner.population.lineage:
            if rec.organism_id not in known and rec.second_parent_id is None and rec.parent_id:
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
