"""Phase C dynamic / fluctuating environment tests.

These tests document software capability and runtime observation only. They do
not claim artificial life, intelligence, phenotypic plasticity, or that CodonTrace
replaces Avida.
"""

from __future__ import annotations

from dataclasses import replace

from codontrace.genesis.birth import ReproductionMode
from codontrace.genesis.engine import GenesisEngine
from codontrace.genesis.environment import (
    EnvironmentConfig,
    EnvironmentRegime,
    EnvironmentSchedule,
    EnvironmentState,
    ResourceSpec,
    apply_chemostat_step,
    decay_local_patches,
    diffuse_local_patches,
    environment_trajectory_digest,
    snapshots_from_generation_results,
    step_environment,
    summarize_dynamic_environment_observation,
    verify_environment_trajectory_replay,
)
from codontrace.genesis.organism import GenesisOrganism
from codontrace.genesis.population import PopulationConfigs, PopulationState, step_population
from codontrace.genesis.runtime_profiles import (
    LIFE_LOOP_FOOD_CELLS,
    GenesisRuntimeProfile,
    summarize_life_loop_observation,
)
from codontrace.trace import (
    WORLD_EVENT_ENVIRONMENT_HAZARD_CHANGED,
    WORLD_EVENT_ENVIRONMENT_INFLOW,
    WORLD_EVENT_ENVIRONMENT_OUTFLOW,
    WORLD_EVENT_ENVIRONMENT_PERIODIC_TOGGLE,
    WORLD_EVENT_ENVIRONMENT_REGIME_SWITCH,
    WorldEvent,
)
from codontrace.world import World2D


def test_default_configs_omit_environment_and_life_loop_stays_phase_a() -> None:
    assert "environment" not in PopulationConfigs().to_dict()
    restored = PopulationConfigs.from_dict(PopulationConfigs().to_dict())
    assert restored.environment.enabled is False
    spec = GenesisRuntimeProfile.life_loop_world(seed=3, tick_count=4, population=6)
    assert spec.metadata["phase_c_fluctuating_environment"] == "deferred"
    assert spec.population_configs is not None
    assert "environment" not in spec.population_configs.to_dict()
    assert spec.population_configs.environment.enabled is False


def test_asexual_life_loop_digest_still_matches_phase_a_baseline() -> None:
    spec = GenesisRuntimeProfile.life_loop_world(seed=7, tick_count=12, population=6)
    result = GenesisEngine.from_spec(spec).run_ticks()
    replay = GenesisEngine.from_spec(spec).run_ticks()
    assert (
        spec.digest()
        == "7d199ae51345872215dbbb0c45cf8f141aacfb4c31d6537eda6de246c0cb7aac"
    )
    assert result.digest() == replay.digest()
    assert result.snapshot.digest() == (
        "76a5e62cb0123b20a089adde25acd1cfb6dc460bdfab52f33ee460533d76f43a"
    )


def test_chemostat_matches_avida_resource_line_unused_outflow_then_inflow() -> None:
    # Ofria & Wilke 2004 / Cooper–Ofria: unused fraction flows out, then inflow.
    amount, removed, added = apply_chemostat_step(100.0, inflow=10.0, outflow=0.01, consumed=20.0)
    assert added == 10.0
    assert abs(removed - 0.8) < 1e-12
    assert abs(amount - 89.2) < 1e-12
    unlimited, rem_u, add_u = apply_chemostat_step(
        100.0, inflow=10.0, outflow=0.01, consumed=20.0, unlimited=True
    )
    assert unlimited == 100.0
    assert rem_u == 0.0
    assert add_u == 0.0


def test_resource_spec_roundtrip_and_config_digest_stable() -> None:
    spec = ResourceSpec(name="lumen", initial=12.0, inflow=2.0, outflow=0.01)
    restored = ResourceSpec.from_dict(spec.to_dict())
    assert restored == spec
    config = EnvironmentConfig.fluctuating_chemostat(
        initial=12.0, inflow=2.0, outflow=0.01, patch_cells=LIFE_LOOP_FOOD_CELLS
    )
    assert config.enabled is True
    assert config.digest() == EnvironmentConfig.from_dict(config.to_dict()).digest()
    assert config.schedule.regimes[0].name == "high_food"
    assert config.schedule.regimes[1].name == "low_food"


def test_periodic_schedule_toggles_two_regimes_like_avida_ed() -> None:
    schedule = EnvironmentSchedule(
        kind="periodic",
        period_ticks=4,
        regimes=(
            EnvironmentRegime(name="high_food"),
            EnvironmentRegime(name="low_food", hazard_intensity=1.0),
        ),
    )
    assert schedule.regime_at(0).name == "high_food"  # type: ignore[union-attr]
    assert schedule.regime_at(3).name == "high_food"  # type: ignore[union-attr]
    assert schedule.regime_at(4).name == "low_food"  # type: ignore[union-attr]
    assert schedule.is_switch_tick(4) is True
    assert schedule.is_switch_tick(3) is False
    static = EnvironmentSchedule(kind="periodic", period_ticks=0, regimes=schedule.regimes)
    assert static.is_periodic is False
    assert static.regime_at(9).name == "high_food"  # type: ignore[union-attr]


def test_seeded_events_advance_regimes_at_listed_ticks() -> None:
    schedule = EnvironmentSchedule(
        kind="seeded_events",
        regimes=(
            EnvironmentRegime(name="niche_a"),
            EnvironmentRegime(name="niche_b"),
        ),
        switch_ticks=(3, 7),
    )
    assert schedule.regime_at(2).name == "niche_a"  # type: ignore[union-attr]
    assert schedule.regime_at(3).name == "niche_b"  # type: ignore[union-attr]
    assert schedule.regime_at(7).name == "niche_a"  # type: ignore[union-attr]


def test_spatial_diffusion_and_decay_are_deterministic() -> None:
    amounts = {(0, 0): 8.0, (1, 0): 0.0}
    first = diffuse_local_patches(amounts, width=2, height=2, rate=0.5)
    second = diffuse_local_patches(amounts, width=2, height=2, rate=0.5)
    assert first == second
    assert first[(0, 0)] < 8.0
    assert first.get((1, 0), 0.0) > 0.0
    decayed = decay_local_patches({(0, 0): 4.0}, rate=0.25)
    assert abs(decayed[(0, 0)] - 3.0) < 1e-12


def test_step_environment_records_chemostat_and_world_events() -> None:
    world = World2D(4, 4)
    world.place_resource((0, 0), 6.0)
    config = EnvironmentConfig(
        enabled=True,
        resources=(ResourceSpec(name="lumen", initial=12.0, inflow=2.0, outflow=0.01),),
        spatial_mode="global_and_local",
        schedule=EnvironmentSchedule(
            kind="periodic",
            period_ticks=1,
            regimes=(
                EnvironmentRegime(name="high_food"),
                EnvironmentRegime(name="low_food", hazard_intensity=1.0),
            ),
        ),
        patch_cells=((0, 0), (1, 0)),
    )
    state = EnvironmentState.initialize(config, tick=0)
    result = step_environment(world, state, config, tick=1, consumed={"lumen": 3.0})
    types = {event.event_type for event in result.events}
    assert "chemostat_update" in types
    assert "periodic_toggle" in types
    assert result.snapshot.pools["lumen"] != 12.0
    world_types = {event.event_type for event in result.world_events}
    assert WORLD_EVENT_ENVIRONMENT_INFLOW in world_types
    assert WORLD_EVENT_ENVIRONMENT_PERIODIC_TOGGLE in world_types
    restored = World2D(4, 4)
    for event in result.world_events:
        restored.apply_world_event(event)


def test_environment_world_events_are_replay_noops_for_global_pool() -> None:
    world = World2D(3, 3)
    digest = world.digest()
    for event_type in (
        WORLD_EVENT_ENVIRONMENT_INFLOW,
        WORLD_EVENT_ENVIRONMENT_OUTFLOW,
        WORLD_EVENT_ENVIRONMENT_REGIME_SWITCH,
        WORLD_EVENT_ENVIRONMENT_PERIODIC_TOGGLE,
        WORLD_EVENT_ENVIRONMENT_HAZARD_CHANGED,
    ):
        world.apply_world_event(
            WorldEvent(schema_version=1, step=0, sequence=0, event_type=event_type)
        )
    assert world.digest() == digest


def test_dynamic_environment_profile_changes_resource_trajectory_under_fixed_seed() -> None:
    spec = GenesisRuntimeProfile.dynamic_environment_world(
        seed=7, tick_count=12, population=6, period_ticks=4
    )
    assert spec.metadata["phase_c_fluctuating_environment"] == "enabled"
    assert spec.metadata["claim_ceiling"] == "runtime_observation"
    assert spec.metadata["claim_allowed_for_plasticity"] is False
    assert spec.metadata["runtime_profile"] == "dynamic_environment_world"
    assert spec.population_configs is not None
    assert spec.population_configs.environment.enabled is True
    assert spec.population_configs.environment.resources[0].outflow == 0.01
    first = GenesisEngine.from_spec(spec).run_ticks()
    second = GenesisEngine.from_spec(spec).run_ticks()
    assert first.digest() == second.digest()
    observation = summarize_dynamic_environment_observation(
        first, config=spec.population_configs.environment
    )
    life = summarize_life_loop_observation(first)
    assert observation.claim_ceiling == "runtime_observation"
    assert observation.plasticity_evolved is False
    assert observation.ticks == 12
    assert observation.regime_switches >= 1
    assert "high_food" in observation.unique_regimes
    assert "low_food" in observation.unique_regimes
    lumen = observation.pool_series["lumen"]
    lo, hi = observation.pool_range["lumen"]
    assert hi > lo
    assert len(set(round(value, 6) for value in lumen)) >= 2
    assert observation.environment_events >= 12
    assert observation.environment_config_digest == spec.population_configs.environment.digest()
    verify = verify_environment_trajectory_replay(
        snapshots_from_generation_results(first.ticks),
        snapshots_from_generation_results(second.ticks),
    )
    assert verify.matched is True
    assert verify.claim_ceiling == "runtime_observation"
    assert life.lumen_eaten_events >= 0
    assert first.ticks[0].generation_result.environment_snapshot is not None
    assert first.ticks[0].generation_result.environment_world_events


def test_niche_maps_switch_spatial_abundance() -> None:
    spec = GenesisRuntimeProfile.dynamic_environment_world(
        seed=5, tick_count=8, population=4, period_ticks=2, niche_maps=True
    )
    result = GenesisEngine.from_spec(spec).run_ticks()
    observation = summarize_dynamic_environment_observation(result)
    assert "niche_a" in observation.unique_regimes
    assert "niche_b" in observation.unique_regimes
    assert observation.regime_switches >= 1


def test_seeded_event_schedule_and_diffusion_hooks_stay_deterministic() -> None:
    spec = GenesisRuntimeProfile.dynamic_environment_world(
        seed=11,
        tick_count=6,
        population=4,
        schedule_kind="seeded_events",
        switch_ticks=(2, 4),
        diffusion_rate=0.25,
        decay_rate=0.0,
    )
    first = GenesisEngine.from_spec(spec).run_ticks()
    second = GenesisEngine.from_spec(spec).run_ticks()
    assert first.digest() == second.digest()
    observation = summarize_dynamic_environment_observation(first)
    assert observation.regime_switches >= 1
    types = {
        event.event_type
        for tick in first.ticks
        for event in tick.generation_result.environment_records
    }
    assert "diffusion" in types


def test_life_loop_still_eats_and_reproduces_under_dynamic_env() -> None:
    spec = GenesisRuntimeProfile.dynamic_environment_world(seed=7, tick_count=12, population=6)
    result = GenesisEngine.from_spec(spec).run_ticks()
    observation = summarize_life_loop_observation(result)
    assert observation.claim_ceiling == "runtime_observation"
    assert observation.lumen_eaten_events >= 1
    assert observation.genesis_alive_full is False


def test_sexual_chamber_still_works_when_environment_enabled() -> None:
    spec = GenesisRuntimeProfile.dynamic_environment_world(
        seed=7,
        tick_count=12,
        population=6,
        reproduction_mode=ReproductionMode.SEXUAL_CROSSOVER,
    )
    assert spec.metadata["phase_b_sexual_crossover"] == "enabled"
    assert spec.metadata["phase_c_fluctuating_environment"] == "enabled"
    result = GenesisEngine.from_spec(spec).run_ticks()
    observation = summarize_life_loop_observation(result)
    assert observation.two_parent_lineage_records >= 0
    env = summarize_dynamic_environment_observation(result)
    assert env.ticks == 12


def test_unlimited_resource_skips_chemostat_turnover() -> None:
    world = World2D(2, 2)
    config = EnvironmentConfig(
        enabled=True,
        resources=(
            ResourceSpec(name="lumen", initial=9.0, inflow=4.0, outflow=0.5, unlimited=True),
        ),
        spatial_mode="global_pool",
        schedule=EnvironmentSchedule(),
    )
    state = EnvironmentState.initialize(config)
    result = step_environment(world, state, config, tick=0, consumed={"lumen": 9.0})
    assert result.state.pools["lumen"] == 9.0


def test_step_population_carries_environment_state_across_ticks() -> None:
    world = World2D(4, 4)
    world.place_resource((0, 0), 6.0)
    eater = GenesisOrganism.from_bits(
        "eater", "101111000", initial_runtime_atp=14.0, position=(0, 0)
    )
    config = EnvironmentConfig(
        enabled=True,
        resources=(ResourceSpec(name="lumen", initial=12.0, inflow=1.0, outflow=0.01),),
        spatial_mode="global_and_local",
        patch_cells=((0, 0), (1, 0)),
        skip_legacy_respawn=True,
        schedule=EnvironmentSchedule(
            kind="static",
            regimes=(EnvironmentRegime(name="high_food"),),
        ),
    )
    configs = replace(PopulationConfigs(), environment=config)
    first = step_population(PopulationState(0, 0, (eater,), (), ()), world, configs, seed=3)
    assert first.population.environment is not None
    assert first.environment_snapshot is not None
    second = step_population(first.population, first.world_after, configs, seed=4)
    assert second.population.environment is not None
    assert second.population.environment.tick == 1
    assert second.environment_snapshot is not None
    assert environment_trajectory_digest(
        (first.environment_snapshot, second.environment_snapshot)
    ) != environment_trajectory_digest((first.environment_snapshot,))
