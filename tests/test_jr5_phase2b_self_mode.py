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
)
from codontrace.genesis.mating_types import MatingTypeMap, can_self
from codontrace.genesis.organism import GenesisOrganism
from codontrace.genesis.population import PopulationState, mating_type_census, mating_type_of
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
)

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
    """Sexes on, self mode off: same digests as at 7db2227a (values pinned there)."""

    assert _step(seed, _configs(**_SEXES)).population.digest() == _BASE_ERA[f"fm{seed}"]
    andro = {**_SEXES, **_ANDRO}
    assert _step(seed, _configs(**andro)).population.digest() == _BASE_ERA[f"hm{seed}"]


@pytest.mark.parametrize("bits", [OUTCROSS_OUT_BITS, OUTCROSS_SELFING_BITS])
def test_locus_runs_without_self_mode_match_base(bits: str) -> None:
    """Both locus states with sexes on and the mode off: digests pinned at 7db2227a."""

    probe = ClosedLoopP5Session.boot(seed=20011, outcross_bits=bits)
    session = _p5(bits, _sexes_for(probe, **_ANDRO))
    session.run_ticks(2)
    assert session.runner.population.digest() == _BASE_ERA["p5" + bits]


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
    pays no fee. Both write lineage into the same kind of ledger."""

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
