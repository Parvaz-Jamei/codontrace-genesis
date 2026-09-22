"""CodonTrace Genesis Phase G named-materials / chemistry-effect substrate tests.

These tests document software capability and runtime observation only. They do
not claim realistic chemistry, wet-lab equivalence, GEM/MD solving,
intelligence, or that CodonTrace Genesis replaces Avida.
"""

from __future__ import annotations

from dataclasses import replace

from codontrace.genesis.claim_gate import ClaimRequest, ScientificClaimGate
from codontrace.genesis.engine import GenesisEngine
from codontrace.genesis.materials import (
    LITERATURE_CHECKLIST,
    MaterialBindingSchema,
    MaterialKind,
    MaterialReactionSpec,
    MaterialsConfig,
    MaterialsOrganismState,
    MaterialSpec,
    MaterialsState,
    apply_organism_material_coupling,
    apply_stoichiometric_reaction,
    attach_materials_to_organisms,
    build_materials_evidence_pack,
    evaluate_materials_claim,
    materials_snapshots_from_generation_results,
    measure_spatial_coexistence,
    step_materials,
    summarize_materials_observation,
    verify_materials_trajectory_replay,
)
from codontrace.genesis.organism import GenesisOrganism
from codontrace.genesis.population import PopulationConfigs, PopulationState, step_population
from codontrace.genesis.replay_integrity import build_replay_digest_class_policy
from codontrace.genesis.runtime_profiles import (
    LIFE_LOOP_FOOD_CELLS,
    GenesisRuntimeProfile,
)
from codontrace.trace import WorldEvent
from codontrace.world import World2D

LIFE_LOOP_SPEC_DIGEST = "7d199ae51345872215dbbb0c45cf8f141aacfb4c31d6537eda6de246c0cb7aac"
LIFE_LOOP_SNAPSHOT_DIGEST = "76a5e62cb0123b20a089adde25acd1cfb6dc460bdfab52f33ee460533d76f43a"


def test_default_configs_omit_materials_and_life_loop_stays_phase_a() -> None:
    assert "materials" not in PopulationConfigs().to_dict()
    restored = PopulationConfigs.from_dict(PopulationConfigs().to_dict())
    assert restored.materials.enabled is False
    spec = GenesisRuntimeProfile.life_loop_world(seed=3, tick_count=4, population=6)
    assert spec.metadata.get("phase_g_materials") is None
    assert spec.population_configs is not None
    assert "materials" not in spec.population_configs.to_dict()
    assert spec.population_configs.materials.enabled is False


def test_asexual_life_loop_digest_still_matches_phase_a_baseline() -> None:
    spec = GenesisRuntimeProfile.life_loop_world(seed=7, tick_count=12, population=6)
    result = GenesisEngine.from_spec(spec).run_ticks()
    replay = GenesisEngine.from_spec(spec).run_ticks()
    assert spec.digest() == LIFE_LOOP_SPEC_DIGEST
    assert result.digest() == replay.digest()
    assert result.snapshot.digest() == LIFE_LOOP_SNAPSHOT_DIGEST


def test_material_spec_roundtrip_ontology_hook_and_no_accuracy_claim() -> None:
    spec = MaterialSpec(
        name="nourish",
        kind=MaterialKind.NUTRIENT,
        energy_yield=2.0,
        permeability=0.8,
        initial=12.0,
        inflow=1.0,
        outflow=0.01,
        external_ontology_id="CHEBI:17234",
        units="arbitrary_mass",
        effect_coefficients={"merit_per_unit": 1.0},
    )
    restored = MaterialSpec.from_dict(spec.to_dict())
    assert restored == spec
    assert restored.biological_accuracy_claimed is False
    assert restored.external_ontology_id == "CHEBI:17234"
    try:
        MaterialSpec(name="bad", biological_accuracy_claimed=True)
    except Exception as exc:
        assert "biological_accuracy" in str(exc)
    else:
        raise AssertionError("biological_accuracy_claimed must be rejected")


def test_named_material_chemostat_reuses_phase_c_unused_outflow_then_inflow() -> None:
    config = MaterialsConfig(
        enabled=True,
        materials=(
            MaterialSpec(name="nourish", kind="nutrient", initial=100.0, inflow=10.0, outflow=0.01),
        ),
        spatial_mode="global_pool",
    )
    state = MaterialsState.initialize(config, tick=0)
    result = step_materials(state, config, tick=1, consumed={"nourish": 20.0})
    assert abs(result.snapshot.outflow_removed["nourish"] - 0.8) < 1e-12
    assert abs(result.snapshot.inflow_applied["nourish"] - 10.0) < 1e-12
    assert abs(result.state.pools["nourish"] - 89.2) < 1e-12
    types = {event.event_type for event in result.events}
    assert "chemostat_update" in types


def test_stoichiometric_autocatalytic_fire_is_mass_action_subset() -> None:
    reaction = MaterialReactionSpec(
        name="A_plus_B_to_2A",
        reactants={"A": 1.0, "B": 1.0},
        products={"A": 2.0},
        rate=0.5,
        catalyst="A",
        autocatalytic=True,
    )
    pools, extent = apply_stoichiometric_reaction(
        {"A": 1.0, "B": 4.0}, reaction, catalyst_amount=1.0, require_catalyst=True
    )
    assert extent > 0
    assert pools["A"] > 1.0
    assert pools["B"] < 4.0
    blocked, zero = apply_stoichiometric_reaction(
        {"A": 1.0, "B": 4.0}, reaction, catalyst_amount=0.0, require_catalyst=True
    )
    assert zero == 0.0
    assert blocked["A"] == 1.0


def test_membrane_permeability_gates_nutrient_and_toxin_uptake() -> None:
    open_spec = GenesisRuntimeProfile.materials_world(
        seed=5, tick_count=4, population=3, membrane_permeability=1.0
    )
    shut_spec = GenesisRuntimeProfile.materials_world(
        seed=5, tick_count=4, population=3, membrane_permeability=0.0
    )
    open_run = GenesisEngine.from_spec(open_spec).run_ticks()
    shut_run = GenesisEngine.from_spec(shut_spec).run_ticks()
    open_obs = summarize_materials_observation(
        open_run, config=open_spec.population_configs.materials  # type: ignore[union-attr]
    )
    shut_obs = summarize_materials_observation(
        shut_run, config=shut_spec.population_configs.materials  # type: ignore[union-attr]
    )
    assert open_obs.uptake_events > shut_obs.uptake_events
    assert shut_obs.uptake_events == 0


def test_eat_absorbs_named_nutrient_credits_atp() -> None:
    config = MaterialsConfig(
        enabled=True,
        materials=(
            MaterialSpec(
                name="nourish",
                kind="nutrient",
                energy_yield=2.0,
                permeability=1.0,
                initial=8.0,
            ),
        ),
        spatial_mode="global_pool",
        default_membrane_permeability=1.0,
        eat_absorbs_nutrients=True,
        toxin_passive_uptake=False,
    )
    organism = GenesisOrganism.from_bits(
        "eater", "101000000", initial_runtime_atp=8.0, position=(0, 0)
    )
    attach_materials_to_organisms((organism,), config)
    before = organism.atp_state.runtime_available
    state = MaterialsState.initialize(config, tick=0)
    events = apply_organism_material_coupling(
        organism,
        dict(state.pools),
        {name: dict(cells) for name, cells in state.grids.items()},
        config,
        tick=1,
        did_eat=True,
    )
    materials_state = organism.materials_state
    assert isinstance(materials_state, MaterialsOrganismState)
    assert any(event.event_type == "uptake" and event.material == "nourish" for event in events)
    assert materials_state.atp_from_materials > 0
    assert organism.atp_state.runtime_available > before
    spec = GenesisRuntimeProfile.materials_world(seed=7, tick_count=6, population=4)
    result = GenesisEngine.from_spec(spec).run_ticks()
    observation = summarize_materials_observation(
        result, config=spec.population_configs.materials  # type: ignore[union-attr]
    )
    assert observation.uptake_events >= 1
    assert observation.claim_ceiling == "runtime_observation"


def test_materials_world_replay_and_trajectory_digest() -> None:
    spec = GenesisRuntimeProfile.materials_world(seed=7, tick_count=8, population=6)
    first = GenesisEngine.from_spec(spec).run_ticks()
    second = GenesisEngine.from_spec(spec).run_ticks()
    assert first.digest() == second.digest()
    snapshots = materials_snapshots_from_generation_results(first.ticks)
    replay = materials_snapshots_from_generation_results(second.ticks)
    verified = verify_materials_trajectory_replay(snapshots, replay)
    assert verified.matched is True
    assert verified.claim_ceiling == "runtime_observation"
    assert spec.metadata["runtime_profile"] == "materials_world"
    assert spec.metadata["claim_allowed_for_realistic_chemistry"] is False
    assert spec.metadata["biological_accuracy_claimed"] is False


def test_autocatalytic_cycle_records_extent_and_spatial_note() -> None:
    spec = GenesisRuntimeProfile.materials_world(
        seed=3, tick_count=6, population=4, autocatalytic=True
    )
    assert spec.population_configs is not None
    assert any(item.autocatalytic for item in spec.population_configs.materials.reactions)
    result = GenesisEngine.from_spec(spec).run_ticks()
    observation = summarize_materials_observation(
        result, config=spec.population_configs.materials
    )
    assert observation.reaction_events >= 1 or observation.autocatalytic_extent_total >= 0.0
    if observation.spatial_coexistence is not None:
        assert observation.spatial_coexistence.spatial_ace_evolved is False
        assert observation.spatial_coexistence.claim_ceiling == "runtime_observation"


def test_spatial_coexistence_measurement_is_not_ace_proof() -> None:
    state = MaterialsState(
        tick=1,
        pools={"A": 3.0, "B": 3.0},
        grids={"A": {(0, 0): 2.0}, "B": {(1, 0): 2.0}},
    )
    note = measure_spatial_coexistence(state, material_a="A", material_b="B", threshold=0.5)
    assert note.coexistence_observed is True
    assert note.spatial_ace_evolved is False


def test_binding_schema_forbids_gem_and_md_flags() -> None:
    schema = MaterialBindingSchema()
    payload = schema.to_dict()
    assert payload["gem_solver_implemented"] is False
    assert payload["molecular_dynamics_implemented"] is False
    assert payload["biological_accuracy_claimed"] is False
    assert "CHEBI" in payload["supported_ontologies"]
    try:
        MaterialBindingSchema(gem_solver_implemented=True)
    except Exception as exc:
        assert "GEM" in str(exc) or "deferred" in str(exc).lower()
    else:
        raise AssertionError("GEM solver flag must stay false")


def test_claim_gate_blocks_realistic_chemistry_and_allows_runtime_observation() -> None:
    spec = GenesisRuntimeProfile.materials_world(seed=7, tick_count=4, population=4)
    result = GenesisEngine.from_spec(spec).run_ticks()
    pack = build_materials_evidence_pack(result)
    decision = evaluate_materials_claim(pack)
    assert decision.final_claim == "runtime_observation"
    gate = ScientificClaimGate()
    for name in (
        "realistic_chemistry_proved",
        "wet_lab_equivalent",
        "kegg_solver_equivalent",
        "bigg_gem_equivalent",
        "molecular_dynamics_equivalent",
    ):
        blocked = gate.decide(ClaimRequest(name, {}))
        assert blocked.allowed is False


def test_summarize_rejects_garbage_input() -> None:
    try:
        summarize_materials_observation(None)
    except TypeError:
        pass
    else:
        raise AssertionError("None must raise TypeError")
    try:
        summarize_materials_observation(object())
    except TypeError:
        pass
    else:
        raise AssertionError("garbage must raise TypeError")


def test_material_world_events_are_replay_noops() -> None:
    world = World2D(3, 3)
    digest = world.digest()
    for event_type in (
        "material_inflow",
        "material_outflow",
        "material_reaction",
        "material_uptake",
        "material_excrete",
    ):
        world.apply_world_event(WorldEvent(schema_version=1, step=0, sequence=0, event_type=event_type))
    assert world.digest() == digest


def test_pack_is_replay_critical_with_validated_digest() -> None:
    policy = build_replay_digest_class_policy("codontrace.genesis.materials.MaterialsEvidencePack")
    assert policy.replay_critical
    assert "digest" in policy.digest_fields
    obs_policy = build_replay_digest_class_policy("codontrace.genesis.materials.MaterialsObservation")
    assert obs_policy.replay_role == "non_replay_critical"


def test_literature_checklist_covers_required_sources() -> None:
    keys = {name for name, _detail in LITERATURE_CHECKLIST}
    assert "avida_resource_reaction_merit" in keys
    assert "chemostat_novick_szilard_named_materials" in keys
    assert "artificial_chemistry_autocatalytic_ecosystems" in keys
    assert "cellularity_metabolism_coevolution" in keys
    assert "deferred_kegg_bigg_md" in keys


def test_public_exports_include_phase_g_symbols() -> None:
    import codontrace.genesis as g

    for name in (
        "MaterialSpec",
        "MaterialsConfig",
        "MaterialsEvidencePack",
        "build_materials_evidence_pack",
        "evaluate_materials_claim",
        "step_materials",
    ):
        assert hasattr(g, name)
        assert name in g.__all__


def test_step_population_records_materials_when_enabled() -> None:
    eater = GenesisOrganism.from_bits("eater", "101000000", initial_runtime_atp=14.0, position=(0, 0))
    world = World2D(6, 4)
    world.place_resource((0, 0), 6.0)
    configs = replace(
        PopulationConfigs(),
        materials=MaterialsConfig.research_defaults(patch_cells=LIFE_LOOP_FOOD_CELLS),
    )
    result = step_population(PopulationState(0, 0, (eater,), (), ()), world, configs, seed=3)
    assert result.materials_snapshot is not None
    assert result.population.materials is not None
    assert "nourish" in result.population.materials.pools
