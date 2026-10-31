"""JR5 phase 2a: sexes on top of ``SexualRecombinationConfig.mating_types_enabled``.

Pinned values in ``_MAIN_ERA`` were produced at 21afb891 (before this change)
with the same inputs as below. With the switch off, every one must match.
All seeds here are in the unsealed block 20000+, outside the JR5 prereg
sealed ranges.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import replace

import pytest

from codontrace.errors import ConfigurationError
from codontrace.genesis.birth import ReproductionMode, SexualRecombinationConfig
from codontrace.genesis.closed_loop_p5 import ClosedLoopP5Session
from codontrace.genesis.engine import GenesisEngine
from codontrace.genesis.host_parasite_life_plugin import (
    OUTCROSS_OUT_BITS,
    OUTCROSS_SELFING_BITS,
    ClosedLoopHPLifeConfig,
    resolve_copy_self_mode,
)
from codontrace.genesis.liveness import AliveGateConfig
from codontrace.genesis.mating_types import (
    MATING_TYPE_STREAM_NAMESPACE,
    MatingTypeMap,
    draw_mating_type,
    mating_type_stream,
    mating_types_compatible,
)
from codontrace.genesis.organism import GenesisOrganism
from codontrace.genesis.population import (
    GenerationResult,
    MutationConfig,
    OffspringPlacementPolicy,
    PopulationConfigs,
    PopulationState,
    ReproductionConfig,
    mating_type_census,
    mating_type_of,
    step_population,
)
from codontrace.genesis.runtime_profiles import LIFE_LOOP_EATER_GENOME, GenesisRuntimeProfile
from codontrace.rng import RNGManager
from codontrace.world import World2D

_CFG_KEYS = '{"chamber_capacity":3600,"continuous_regions":true,"corresponding_positions":true,'
_MAIN_ERA_CONFIG_JSON = {
    "default": _CFG_KEYS + '"enabled":false,"lekking":false,"mating_types_enabled":false,"max_birth_wait_ticks":null,'
    '"modular_region_count":0,"pairing_policy":"birth_chamber","recombination_prob":1.0,'
    '"same_length_only":false,"timeout_policy":"asexual_fallback","two_fold_cost_sex":false}',
    "enabled": _CFG_KEYS + '"enabled":true,"lekking":false,"mating_types_enabled":false,"max_birth_wait_ticks":null,'
    '"modular_region_count":0,"pairing_policy":"birth_chamber","recombination_prob":1.0,'
    '"same_length_only":false,"timeout_policy":"asexual_fallback","two_fold_cost_sex":false}',
    "two_fold": _CFG_KEYS + '"enabled":true,"lekking":false,"mating_types_enabled":false,"max_birth_wait_ticks":null,'
    '"modular_region_count":0,"pairing_policy":"birth_chamber","recombination_prob":1.0,'
    '"same_length_only":false,"timeout_policy":"asexual_fallback","two_fold_cost_sex":true}',
    "meiosis": _CFG_KEYS + '"diploid_meiosis":true,"enabled":true,"lekking":false,"mating_types_enabled":false,'
    '"max_birth_wait_ticks":null,"modular_region_count":0,"pairing_policy":"birth_chamber",'
    '"recombination_prob":1.0,"same_length_only":false,"timeout_policy":"asexual_fallback",'
    '"two_fold_cost_sex":false}',
}
_MAIN_ERA_STEP_DIGESTS = {
    (20005, False): "ec1bade66aadfcbce2359251c50736ac292bfb9bf057c97a6fad6c7db821af2e",
    (20005, True): "07425860239a1e7081c58216f85416663db2e31e7f7a4ecf9dea7e861ce70464",
    (20008, False): "7fd06fbc83d5f10178ed9702e0a09569644824de2674133ea341da30b8b56a3c",
    (20008, True): "7533038265b818d43d0aa53792fb07e8601f8cc2b5049963ee6521b88f38431e",
    (20013, False): "9b3acd0530a3f2d0a16ebc3920b251632f2d58f3d29cddd0b62e37cc671c6bc6",
    (20013, True): "dd39537e48fc11bbc0346e31e482989fdb93add0e65b244532f5cf265578fda0",
}
_MAIN_ERA_LIFE_LOOP_SPEC = "15ef97673d0415149a5d8d41f4bb1685a8e78edf9a10e6ff8959e7a24b7080c4"
_MAIN_ERA_LIFE_LOOP_TICKS = [
    "30e4f3f738f29a7f8df6c35101de9dbfece26728a2f6207cb1e688a9ce14ba7a",
    "093b134b84580ccef6b7a3a923b38745fa13a95796647c9c874f3beb0b9bd4d9",
    "eff697b657a87e0dbe1ae8193470661fee30ba4c46926d3e1c572ab069fc3128",
    "fc4894b3b74e6def22d487b9257b0ca822aa477edc4cc497d6e8174458837b43",
    "c4cea36e71c984f6e93f55c431b1fcff33b654059f900353f5da88b527895209",
    "1a0e62678857c825a9120b04478cb5d2eac3af5354016858eafdfa9137251c69",
    "61718b3f5026df4c4cb8ff3ce4e0546bc826a6498a74300291b2f6fd364f889d",
    "8603d1edd6ba71f6f81f43d38f3755e91a25a0d0888ea51e4ec6f6c706c159c1",
]
_MAIN_ERA_LIFE_LOOP_SNAPSHOT = "ddb1be11949dc8585c95aeea1a4d7cce1055ef46590e40747b15387cd19f2439"
_MAIN_ERA_RNG_DRAWS = [0.07288018841626231, 0.020732041539421653, 0.32331505896767]

# sha256 of the sorted-key JSON of the census test population plus one asexual founder.
_MIXED_DIGEST = "d60e113323d9a2d75156d362da5428630c4bf23d97b9abed9879c7677ceeecab"
_BITS = ("111000000", "111111000", "101101101", "110011001")
_SEXES = {
    "mating_types_enabled": True,
    "mating_type_set": ("female", "male"),
    "sex_assignment": "random_at_birth",
}


def _compact(cfg: SexualRecombinationConfig) -> str:
    return json.dumps(cfg.to_dict(), sort_keys=True, separators=(",", ":"))


def _configs(**overrides: object) -> PopulationConfigs:
    payload: dict[str, object] = {
        "enabled": True,
        "recombination_prob": 1.0,
        "chamber_capacity": 8,
        "timeout_policy": "asexual_fallback",
        "pairing_policy": "birth_chamber",
    }
    payload.update(overrides)
    return PopulationConfigs(
        reproduction=ReproductionConfig(
            min_runtime_atp=1.0,
            parent_atp_cost=1.0,
            max_population=12,
            offspring_placement=OffspringPlacementPolicy.SAME_CELL,
            reproduction_mode=ReproductionMode.SEXUAL_CROSSOVER,
        ),
        mutation=MutationConfig(bit_flip_rate=0.0),
        alive_gate=AliveGateConfig(
            min_ticks=1,
            min_executed_actions=0,
            max_blocked_ratio=1.0,
            require_positive_runtime_atp=True,
        ),
        sexual_recombination=SexualRecombinationConfig(**payload),  # type: ignore[arg-type]
    )


def _step(seed: int, configs: PopulationConfigs, bits: tuple[str, ...] = _BITS) -> GenerationResult:
    organisms = tuple(
        GenesisOrganism.from_bits(f"o{i}", b, initial_runtime_atp=20.0, position=(1, i)) for i, b in enumerate(bits)
    )
    return step_population(PopulationState(0, 0, organisms, (), ()), World2D(4, 4), configs, seed=seed)


# (1) switch off: byte-identical to main-era values.


def test_switch_off_config_payloads_are_byte_identical_to_main_era() -> None:
    cases = {
        "default": SexualRecombinationConfig(),
        "enabled": SexualRecombinationConfig(enabled=True),
        "two_fold": SexualRecombinationConfig(enabled=True, two_fold_cost_sex=True),
        "meiosis": SexualRecombinationConfig(enabled=True, diploid_meiosis=True),
    }
    for name, cfg in cases.items():
        assert _compact(cfg) == _MAIN_ERA_CONFIG_JSON[name], name


@pytest.mark.parametrize(("seed", "two_fold"), sorted(_MAIN_ERA_STEP_DIGESTS))
def test_switch_off_chamber_step_digest_matches_main_era(seed: int, two_fold: bool) -> None:
    result = _step(seed, _configs(two_fold_cost_sex=two_fold))
    assert result.population.digest() == _MAIN_ERA_STEP_DIGESTS[(seed, two_fold)]


def test_switch_off_sexual_life_loop_replay_matches_main_era() -> None:
    spec = GenesisRuntimeProfile.life_loop_world(
        seed=20007, tick_count=8, population=6, reproduction_mode=ReproductionMode.SEXUAL_CROSSOVER
    )
    assert spec.digest() == _MAIN_ERA_LIFE_LOOP_SPEC
    result = GenesisEngine.from_spec(spec).run_ticks()
    assert [tick.digest() for tick in result.ticks] == _MAIN_ERA_LIFE_LOOP_TICKS
    assert result.snapshot.digest() == _MAIN_ERA_LIFE_LOOP_SNAPSHOT


# (2) the sex stream does not shift any existing stream.


def test_sex_stream_does_not_shift_existing_streams() -> None:
    root = RNGManager(seed=24242, namespace="genesis/population")
    names = ("birth_chamber", "meiosis/x", "recombination/a/b")
    before = [root.fork(name).random() for name in names]
    assert before == _MAIN_ERA_RNG_DRAWS
    for index in range(50):
        mating_type_stream(24242, f"org-{index}").random()
    assert [root.fork(name).random() for name in names] == before
    assert root.draw_count == 0
    stream = mating_type_stream(24242, "org-1")
    assert stream.namespace == f"{MATING_TYPE_STREAM_NAMESPACE}/org-1"
    assert stream.namespace not in {root.fork(name).namespace for name in names}


@pytest.mark.parametrize("seed", [20005, 20008, 20013])
def test_hermaphrodite_only_sexes_reproduce_the_switch_off_run(seed: int) -> None:
    """All-compatible types: pairing and every draw match the switch-off run."""

    herm = {**_SEXES, "mating_type_set": ("hermaphrodite",)}
    off = _step(seed, _configs())
    on = _step(seed, _configs(**herm))
    assert on.population.digest() == off.population.digest()
    assert on.population.digest() == _MAIN_ERA_STEP_DIGESTS[(seed, False)]


# (3) reproducible per seed; matches the configured ratio.


# Only the 0.25 case catches a mutant that inverts the ratio (male vs female);
# 0.5 is symmetric and kept as a plain sanity check.
@pytest.mark.parametrize("ratio", [0.5, 0.25])
def test_sex_assignment_is_reproducible_and_matches_ratio(ratio: float) -> None:
    cfg = SexualRecombinationConfig(enabled=True, sex_ratio=ratio, **_SEXES)  # type: ignore[arg-type]
    n = 4000
    first = [draw_mating_type(24343, f"id-{i}", cfg) for i in range(n)]
    again = [draw_mating_type(24343, f"id-{i}", cfg) for i in reversed(range(n))][::-1]
    assert first == again
    other_seed = [draw_mating_type(24344, f"id-{i}", cfg) for i in range(n)]
    assert first != other_seed
    males = sum(1 for t in first if t == "male")
    assert set(first) == {"male", "female"}
    sd = (n * ratio * (1.0 - ratio)) ** 0.5
    assert abs(males - n * ratio) < 4.0 * sd


def test_hermaphrodite_sets() -> None:
    herm = SexualRecombinationConfig(
        enabled=True,
        mating_types_enabled=True,
        mating_type_set=("hermaphrodite",),
        sex_assignment="random_at_birth",
    )
    assert {draw_mating_type(20003, f"x{i}", herm) for i in range(20)} == {"hermaphrodite"}
    andro = replace(herm, mating_type_set=("hermaphrodite", "male"), sex_ratio=0.3)
    assert {draw_mating_type(20003, f"x{i}", andro) for i in range(200)} == {"hermaphrodite", "male"}


# (4) only opposite-sex pairs mate.


def test_compatibility_table() -> None:
    assert mating_types_compatible("male", "female")
    assert mating_types_compatible("female", "male")
    assert not mating_types_compatible("male", "male")
    assert not mating_types_compatible("female", "female")
    assert mating_types_compatible("hermaphrodite", "male")
    assert mating_types_compatible("hermaphrodite", "female")
    assert mating_types_compatible("hermaphrodite", "hermaphrodite")


@pytest.mark.parametrize("seed", [20005, 20008, 20013, 20021, 20034])
def test_sexes_on_only_opposite_sex_pairs_mate(seed: int) -> None:
    configs = _configs(**_SEXES)
    result = _step(seed, configs)
    types = MatingTypeMap(seed, configs.effective_sexual_config)
    pairs = [(rec.parent_id, rec.second_parent_id) for rec in result.population.lineage if rec.second_parent_id]
    for a, b in pairs:
        assert b is not None
        assert {types.assign(a), types.assign(b)} == {"male", "female"}


def test_single_sex_population_never_pairs() -> None:
    for ratio in (0.0, 1.0):
        result = _step(20005, _configs(sex_ratio=ratio, **_SEXES))
        assert not [rec for rec in result.population.lineage if rec.second_parent_id]
        assert not result.population.birth_chamber.is_empty


def test_some_seed_pairs_under_separate_sexes() -> None:
    mated = 0
    for seed in range(20001, 20030):
        result = _step(seed, _configs(**_SEXES))
        mated += sum(1 for rec in result.population.lineage if rec.second_parent_id)
    assert mated > 0


def test_two_fold_cost_sex_cannot_be_combined_with_sexes() -> None:
    with pytest.raises(ValueError, match="two_fold_cost_sex"):
        SexualRecombinationConfig(enabled=True, two_fold_cost_sex=True, **_SEXES)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "overrides",
    [
        {"enabled": False},
        {"mating_type_set": ()},
        {"mating_type_set": ("female",)},
        {"mating_type_set": ("female", "hermaphrodite")},
        {"mating_type_set": ("male", "male")},
        {"mating_type_set": ("male", "queen")},
        {"sex_assignment": "none"},
        {"sex_assignment": "inherited_locus"},
        {"sex_assignment": "coin"},
        {"sex_ratio": 1.5},
    ],
)
def test_invalid_sex_configs_raise(overrides: dict[str, object]) -> None:
    payload: dict[str, object] = {"enabled": True, **_SEXES}
    payload.update(overrides)
    with pytest.raises(ValueError):
        SexualRecombinationConfig(**payload)  # type: ignore[arg-type]


# (5) serialization round-trip and default omission.


def test_new_fields_are_omitted_when_default() -> None:
    payload = SexualRecombinationConfig(enabled=True).to_dict()
    for key in ("mating_type_set", "sex_ratio", "sex_assignment"):
        assert key not in payload
    assert payload["mating_types_enabled"] is False


def test_round_trip_with_sexes_on() -> None:
    cfg = SexualRecombinationConfig(enabled=True, sex_ratio=0.25, **_SEXES)  # type: ignore[arg-type]
    payload = cfg.to_dict()
    assert payload["mating_types_enabled"] is True
    assert payload["mating_type_set"] == ["female", "male"]
    assert payload["sex_ratio"] == 0.25
    assert payload["sex_assignment"] == "random_at_birth"
    restored = SexualRecombinationConfig.from_dict(json.loads(json.dumps(payload)))
    assert restored == cfg
    assert _compact(restored) == _compact(cfg)
    assert SexualRecombinationConfig.from_dict(SexualRecombinationConfig().to_dict()) == (SexualRecombinationConfig())
    with pytest.raises(ValueError):
        SexualRecombinationConfig.from_dict({**payload, "mating_type_set": "male"})


# (6) the outcross locus still decides chamber entry.


def _p5(outcross_bits: str, sexual: SexualRecombinationConfig | None) -> ClosedLoopP5Session:
    session = ClosedLoopP5Session.boot(seed=20011, outcross_bits=outcross_bits)
    if sexual is not None:
        session.runner.configs = replace(session.runner.configs, sexual_recombination=sexual)
    return session


def _sexes_for(session: ClosedLoopP5Session, **overrides: object) -> SexualRecombinationConfig:
    base = session.runner.configs.effective_sexual_config
    return replace(base, **{**_SEXES, **overrides})  # type: ignore[arg-type]


def test_outcross_locus_policy_is_reused_unchanged() -> None:
    life = ClosedLoopHPLifeConfig(outcross_enabled=True)
    assert resolve_copy_self_mode(LIFE_LOOP_EATER_GENOME + "100000" + OUTCROSS_OUT_BITS, life) == ("chamber")
    assert resolve_copy_self_mode(LIFE_LOOP_EATER_GENOME + "100000" + OUTCROSS_SELFING_BITS, life) == ("asexual")


def test_outcross_with_hermaphrodites_still_recombines() -> None:
    probe = ClosedLoopP5Session.boot(seed=20011, outcross_bits=OUTCROSS_OUT_BITS)
    herm = _sexes_for(probe, mating_type_set=("hermaphrodite",))
    summary = _p5(OUTCROSS_OUT_BITS, herm).run_ticks(1)
    baseline = _p5(OUTCROSS_OUT_BITS, None).run_ticks(1)
    assert summary["outcross_debit_events"] >= 1
    assert summary["recombination_births"] == baseline["recombination_births"]
    assert summary["births"] == baseline["births"]


def test_outcross_single_sex_pays_fee_but_cannot_pair() -> None:
    probe = ClosedLoopP5Session.boot(seed=20011, outcross_bits=OUTCROSS_OUT_BITS)
    males = _sexes_for(probe, sex_ratio=1.0)
    summary = _p5(OUTCROSS_OUT_BITS, males).run_ticks(1)
    assert summary["outcross_debit_events"] >= 1
    assert summary["recombination_births"] == 0


def test_selfing_locus_in_sexual_lineage_cannot_reproduce() -> None:
    probe = ClosedLoopP5Session.boot(seed=20011, outcross_bits=OUTCROSS_SELFING_BITS)
    summary = _p5(OUTCROSS_SELFING_BITS, _sexes_for(probe)).run_ticks(1)
    baseline = _p5(OUTCROSS_SELFING_BITS, None).run_ticks(1)
    assert baseline["births"] >= 1
    assert summary["outcross_debit_events"] == 0
    assert summary["births"] == 0


def test_selfing_locus_in_asexual_founder_lineage_still_reproduces() -> None:
    probe = ClosedLoopP5Session.boot(seed=20011, outcross_bits=OUTCROSS_SELFING_BITS)
    session = _p5(OUTCROSS_SELFING_BITS, _sexes_for(probe))
    population = session.runner.population
    session.runner.population = replace(
        population,
        organisms=tuple(replace(o, asexual_lineage=True) for o in population.organisms),
    )
    summary = session.run_ticks(1)
    baseline = _p5(OUTCROSS_SELFING_BITS, None).run_ticks(1)
    assert summary["births"] == baseline["births"]
    assert all(o.asexual_lineage for o in session.runner.population.organisms)


# Uniparental reproduction is barred in sexual lineages.


def _first_id_of(kind: str, seed: int, cfg: SexualRecombinationConfig) -> str:
    for index in range(200):
        candidate = f"s{index}"
        if draw_mating_type(seed, candidate, cfg) == kind:
            return candidate
    raise AssertionError(kind)


def _run(
    seed: int, configs: PopulationConfigs, organisms: tuple[GenesisOrganism, ...], steps: int
) -> tuple[PopulationState, int]:
    state = PopulationState(0, 0, organisms, (), ())
    world = World2D(4, 4)
    births = 0
    for _ in range(steps):
        result = step_population(state, world, configs, seed=seed)
        births += result.births
        state, world = result.population, result.world_after
    return state, births


def test_unmated_female_in_sexual_lineage_produces_no_child() -> None:
    configs = _configs(max_birth_wait_ticks=0, **_SEXES)
    female = _first_id_of("female", 20005, configs.effective_sexual_config)
    org = GenesisOrganism.from_bits(female, _BITS[0], initial_runtime_atp=40.0, position=(1, 1))
    state, births = _run(20005, configs, (org,), 4)
    assert births == 0
    assert [o.id for o in state.organisms] == [female]
    # Switch off with the same timeout: the copy falls back and is placed.
    _, births_off = _run(20005, _configs(max_birth_wait_ticks=0), (org,), 4)
    assert births_off >= 1


def test_same_sex_waiters_do_not_fall_back_to_a_copy_on_timeout() -> None:
    """Two males wait in the chamber; when the wait expires neither may copy itself."""

    configs = _configs(max_birth_wait_ticks=0, **_SEXES)
    sexual = configs.effective_sexual_config
    first = _first_id_of("male", 20005, sexual)
    second = next(f"m{i}" for i in range(200) if draw_mating_type(20005, f"m{i}", sexual) == "male")
    orgs = tuple(
        GenesisOrganism.from_bits(oid, _BITS[0], initial_runtime_atp=40.0, position=(1, i))
        for i, oid in enumerate((first, second))
    )
    state = PopulationState(0, 0, orgs, (), ())
    world = World2D(4, 4)
    blocked = births = 0
    for _ in range(4):
        result = step_population(state, world, configs, seed=20005)
        blocked += result.blocked_reproduction
        births += result.births
        state, world = result.population, result.world_after
    assert births == 0
    assert blocked > 0
    # Same organisms with the switch off fall back to a copy after the wait.
    _, births_off = _run(20005, _configs(max_birth_wait_ticks=0), orgs, 4)
    assert births_off >= 1


def test_asexual_founder_lineage_reproduces_and_passes_the_flag_on() -> None:
    configs = _configs(**_SEXES)
    founder = replace(
        GenesisOrganism.from_bits("a0", _BITS[0], initial_runtime_atp=40.0, position=(1, 1)),
        asexual_lineage=True,
    )
    state, births = _run(20005, configs, (founder,), 3)
    assert births >= 1
    assert len(state.organisms) > 1
    assert all(o.asexual_lineage for o in state.organisms)
    assert not [rec for rec in state.lineage if rec.second_parent_id]


def test_asexual_lineage_flag_is_serialized_only_when_set() -> None:
    plain = _step(20005, _configs()).population
    assert "asexual_lineage" not in json.dumps(plain.to_dict())
    founder = replace(GenesisOrganism.from_bits("a0", _BITS[0], position=(1, 1)), asexual_lineage=True)
    flagged = PopulationState(0, 0, (founder,), (), ())
    assert flagged.to_dict()["organisms"][0]["asexual_lineage"] is True  # type: ignore[index,call-overload]


def test_sexes_require_birth_chamber_pairing() -> None:
    with pytest.raises(ValueError, match="birth_chamber"):
        SexualRecombinationConfig(enabled=True, pairing_policy="nearest_mate", **_SEXES)  # type: ignore[arg-type]


# Read-only accessors for the census.


def test_mating_type_of_and_census() -> None:
    configs = _configs(**_SEXES)
    sexual = configs.effective_sexual_config
    result = _step(20013, configs)
    population = result.population
    types = MatingTypeMap(20013, sexual)
    for organism in population.organisms:
        assert mating_type_of(population, organism.id, seed=20013, sexual=sexual) == types.assign(organism.id)
    census = mating_type_census(population, seed=20013, sexual=sexual)
    assert sum(census.values()) == len(population.organisms)
    assert set(census) <= {"male", "female"}
    founder = replace(GenesisOrganism.from_bits("a0", _BITS[0], position=(0, 0)), asexual_lineage=True)
    mixed = replace(population, organisms=(*population.organisms, founder))
    assert mating_type_of(mixed, "a0", seed=20013, sexual=sexual) == "asexual"
    assert mating_type_census(mixed, seed=20013, sexual=sexual)["asexual"] == 1
    assert hashlib.sha256(json.dumps(mixed.to_dict(), sort_keys=True).encode()).hexdigest() == _MIXED_DIGEST
    assert "mating_type" not in json.dumps(population.to_dict())
    with pytest.raises(ConfigurationError):
        mating_type_of(population, "missing", seed=20013, sexual=sexual)
    with pytest.raises(ConfigurationError):
        mating_type_census(population, seed=20013, sexual=SexualRecombinationConfig(enabled=True))
