"""JR5 phase 2a: sexes on top of ``SexualRecombinationConfig.mating_types_enabled``.

Pinned values in ``_MAIN_ERA`` were produced at 21afb891 (before this change)
with the same inputs as below. With the switch off, every one must match.
"""

from __future__ import annotations

import json
from dataclasses import replace

import pytest

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
    (5, False): "dff3aca53f1e46b81cb724642195e13f9aef98afa2263c836ae8b1fe2be14b48",
    (5, True): "2e2ffef616ce650aec78d4439ea0754ee362dac6d483decdbc0b93d6399689a8",
    (8, False): "c44189b66ee5907451db326cb1e35ad700b89a2b70ade722ac0a1573f80c5fae",
    (8, True): "c19d118d9c18a88f2cafeb807ce80b8c4a21898f75eb3d819cce340a5a2154b0",
    (13, False): "9f49f3f9bbc1102f13b87a33b7d041b7bca60cf8224f35455635622e2be12e1c",
    (13, True): "3e2bf5936c4bac527bd0877c63f2b16863336e36c53a85ddc7e68557afe5e7f5",
}
_MAIN_ERA_LIFE_LOOP_SPEC = "f0ee5d80c1638bc6fef5f64ea6eac1848224a5ca4315900c21c204cc9bebc130"
_MAIN_ERA_LIFE_LOOP_TICKS = [
    "30e4f3f738f29a7f8df6c35101de9dbfece26728a2f6207cb1e688a9ce14ba7a",
    "478fc3dd89ea84eb0a03cbe12bd265b46d84edd25285ad660354eeda770ccd3b",
    "2befddbf62afd440123d51c049c7a64ce571bb8477aabef99c4907467d92350b",
    "e9d3832bb193e048f83377a902a5fe474a86f3d8e6a5515f4a75e7e1f96be1c7",
    "aac1e1193013fef8955e7e352162e0b69087b1442a2d992740f69827cfae1f58",
    "862b19904c9a598ed816b2b1a838c857b4f1aa66d53652d700916d6f16660f90",
    "bc6da5e19eee5528efd325e33ea61197ec0bdd9e64bbff8800d68cec70261932",
    "09fce6801980c4dd641622bea2ca5ab16419b35a37730679bc9f6634a4c9a23f",
]
_MAIN_ERA_LIFE_LOOP_SNAPSHOT = "4b9fc37fc02661f396f04fb108178b6a73b383e8c27644c664afd2f5d0534c6f"
_MAIN_ERA_RNG_DRAWS = [0.2861809988781432, 0.3428930518177439, 0.05947213471238899]

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
        seed=7, tick_count=8, population=6, reproduction_mode=ReproductionMode.SEXUAL_CROSSOVER
    )
    assert spec.digest() == _MAIN_ERA_LIFE_LOOP_SPEC
    result = GenesisEngine.from_spec(spec).run_ticks()
    assert [tick.digest() for tick in result.ticks] == _MAIN_ERA_LIFE_LOOP_TICKS
    assert result.snapshot.digest() == _MAIN_ERA_LIFE_LOOP_SNAPSHOT


# (2) the sex stream does not shift any existing stream.


def test_sex_stream_does_not_shift_existing_streams() -> None:
    root = RNGManager(seed=4242, namespace="genesis/population")
    names = ("birth_chamber", "meiosis/x", "recombination/a/b")
    before = [root.fork(name).random() for name in names]
    assert before == _MAIN_ERA_RNG_DRAWS
    for index in range(50):
        mating_type_stream(4242, f"org-{index}").random()
    assert [root.fork(name).random() for name in names] == before
    assert root.draw_count == 0
    stream = mating_type_stream(4242, "org-1")
    assert stream.namespace == f"{MATING_TYPE_STREAM_NAMESPACE}/org-1"
    assert stream.namespace not in {root.fork(name).namespace for name in names}


@pytest.mark.parametrize("seed", [5, 8, 13])
def test_hermaphrodite_only_sexes_reproduce_the_switch_off_run(seed: int) -> None:
    """All-compatible types: pairing and every draw match the switch-off run."""

    herm = {**_SEXES, "mating_type_set": ("hermaphrodite",)}
    off = _step(seed, _configs())
    on = _step(seed, _configs(**herm))
    assert on.population.digest() == off.population.digest()
    assert on.population.digest() == _MAIN_ERA_STEP_DIGESTS[(seed, False)]


# (3) reproducible per seed; matches the configured ratio.


@pytest.mark.parametrize("ratio", [0.5, 0.25])
def test_sex_assignment_is_reproducible_and_matches_ratio(ratio: float) -> None:
    cfg = SexualRecombinationConfig(enabled=True, sex_ratio=ratio, **_SEXES)  # type: ignore[arg-type]
    n = 4000
    first = [draw_mating_type(4343, f"id-{i}", cfg) for i in range(n)]
    again = [draw_mating_type(4343, f"id-{i}", cfg) for i in reversed(range(n))][::-1]
    assert first == again
    other_seed = [draw_mating_type(4344, f"id-{i}", cfg) for i in range(n)]
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
    assert {draw_mating_type(3, f"x{i}", herm) for i in range(20)} == {"hermaphrodite"}
    andro = replace(herm, mating_type_set=("hermaphrodite", "male"), sex_ratio=0.3)
    assert {draw_mating_type(3, f"x{i}", andro) for i in range(200)} == {"hermaphrodite", "male"}


# (4) only opposite-sex pairs mate.


def test_compatibility_table() -> None:
    assert mating_types_compatible("male", "female")
    assert mating_types_compatible("female", "male")
    assert not mating_types_compatible("male", "male")
    assert not mating_types_compatible("female", "female")
    assert mating_types_compatible("hermaphrodite", "male")
    assert mating_types_compatible("hermaphrodite", "female")
    assert mating_types_compatible("hermaphrodite", "hermaphrodite")


@pytest.mark.parametrize("seed", [5, 8, 13, 21, 34])
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
        result = _step(5, _configs(sex_ratio=ratio, **_SEXES))
        assert not [rec for rec in result.population.lineage if rec.second_parent_id]
        assert not result.population.birth_chamber.is_empty


def test_some_seed_pairs_under_separate_sexes() -> None:
    mated = 0
    for seed in range(1, 30):
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
    session = ClosedLoopP5Session.boot(seed=11, outcross_bits=outcross_bits)
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
    probe = ClosedLoopP5Session.boot(seed=11, outcross_bits=OUTCROSS_OUT_BITS)
    herm = _sexes_for(probe, mating_type_set=("hermaphrodite",))
    summary = _p5(OUTCROSS_OUT_BITS, herm).run_ticks(1)
    baseline = _p5(OUTCROSS_OUT_BITS, None).run_ticks(1)
    assert summary["outcross_debit_events"] >= 1
    assert summary["recombination_births"] == baseline["recombination_births"]
    assert summary["births"] == baseline["births"]


def test_outcross_single_sex_pays_fee_but_cannot_pair() -> None:
    probe = ClosedLoopP5Session.boot(seed=11, outcross_bits=OUTCROSS_OUT_BITS)
    males = _sexes_for(probe, sex_ratio=1.0)
    summary = _p5(OUTCROSS_OUT_BITS, males).run_ticks(1)
    assert summary["outcross_debit_events"] >= 1
    assert summary["recombination_births"] == 0


def test_selfing_locus_bypasses_chamber_with_sexes_on() -> None:
    probe = ClosedLoopP5Session.boot(seed=11, outcross_bits=OUTCROSS_SELFING_BITS)
    sexes = _sexes_for(probe)
    summary = _p5(OUTCROSS_SELFING_BITS, sexes).run_ticks(1)
    baseline = _p5(OUTCROSS_SELFING_BITS, None).run_ticks(1)
    assert summary["outcross_debit_events"] == 0
    assert summary["recombination_births"] == 0
    assert summary["births"] == baseline["births"]
