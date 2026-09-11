"""Phase E capsule/memory/role/collective substrate tests.

These tests document software capability and runtime observation only. They do
not claim associative learning, evolved plasticity, collective intelligence,
or that CodonTrace replaces Avida.
"""

from __future__ import annotations

from dataclasses import replace

from codontrace.genesis.birth import ReproductionMode
from codontrace.genesis.claim_gate import ClaimRequest, ScientificClaimGate
from codontrace.genesis.engine import GenesisEngine
from codontrace.genesis.environment import EnvironmentConfig
from codontrace.genesis.liveness import AliveGateConfig, AliveGateResult
from codontrace.genesis.multi_generation import build_multi_generation_evidence_pack
from codontrace.genesis.organism import GenesisOrganism
from codontrace.genesis.phase_e import (
    GHALAMBOR_CLUNE_CONDITIONS,
    LITERATURE_CHECKLIST,
    AvidaParityProtocolSpec,
    CapsuleMemoryConfig,
    Deme,
    DemeConfig,
    DemeState,
    MessageKind,
    PhaseESubstrateConfig,
    PlasticityCondition,
    PlasticityProtocolSpec,
    RoleDifferentiationConfig,
    RoleKind,
    attach_phase_e_to_organisms,
    build_phase_e_evidence_pack,
    evaluate_phase_e_claim,
    export_phenotype_transcriptome,
    read_environment_cue,
    retrieve_message,
    role_for_kind,
    send_message,
)
from codontrace.genesis.population import (
    PopulationConfigs,
    PopulationState,
    can_reproduce,
    step_population,
)
from codontrace.genesis.replay_integrity import build_replay_digest_class_policy
from codontrace.genesis.runtime_profiles import GenesisRuntimeProfile
from codontrace.world import World2D


LIFE_LOOP_SPEC_DIGEST = "7d199ae51345872215dbbb0c45cf8f141aacfb4c31d6537eda6de246c0cb7aac"
LIFE_LOOP_SNAPSHOT_DIGEST = "76a5e62cb0123b20a089adde25acd1cfb6dc460bdfab52f33ee460533d76f43a"


def test_default_configs_omit_phase_e_and_life_loop_stays_phase_a() -> None:
    assert "phase_e" not in PopulationConfigs().to_dict()
    restored = PopulationConfigs.from_dict(PopulationConfigs().to_dict())
    assert restored.phase_e.enabled is False
    spec = GenesisRuntimeProfile.life_loop_world(seed=3, tick_count=4, population=6)
    assert spec.metadata.get("phase_e_capsule_memory_collective") is None
    assert spec.population_configs is not None
    assert "phase_e" not in spec.population_configs.to_dict()


def test_asexual_life_loop_digest_still_matches_phase_a_baseline() -> None:
    spec = GenesisRuntimeProfile.life_loop_world(seed=7, tick_count=12, population=6)
    result = GenesisEngine.from_spec(spec).run_ticks()
    replay = GenesisEngine.from_spec(spec).run_ticks()
    assert spec.digest() == LIFE_LOOP_SPEC_DIGEST
    assert result.digest() == replay.digest()
    assert result.snapshot.digest() == LIFE_LOOP_SNAPSHOT_DIGEST


def test_phase_d_pack_digest_stable_on_default_life_loop() -> None:
    spec = GenesisRuntimeProfile.life_loop_world(seed=7, tick_count=12, population=6)
    assert spec.digest() == LIFE_LOOP_SPEC_DIGEST
    result = GenesisEngine.from_spec(spec).run_ticks()
    pack = build_multi_generation_evidence_pack(result, spec=spec)
    assert pack.digest
    assert pack.claim_ceiling == "runtime_observation"


def test_capsule_memory_changes_action_and_ablation_digest() -> None:
    on_spec = replace(
        GenesisRuntimeProfile.phase_e_substrate_world(
            seed=7, tick_count=6, population=2, enable_capsule_memory=True
        ),
        genome_bits=("000000000", "000000000"),
    )
    off_spec = replace(
        GenesisRuntimeProfile.phase_e_substrate_world(
            seed=7,
            tick_count=6,
            population=2,
            enable_capsule_memory=False,
            seed_preferred_action="",
        ),
        genome_bits=("000000000", "000000000"),
    )
    on_result = GenesisEngine.from_spec(on_spec).run_ticks()
    off_result = GenesisEngine.from_spec(off_spec).run_ticks()
    replay = GenesisEngine.from_spec(on_spec).run_ticks()
    on_pack = build_phase_e_evidence_pack(on_result)
    off_pack = build_phase_e_evidence_pack(off_result)
    assert on_result.digest() == replay.digest()
    assert on_result.digest() != off_result.digest()
    assert on_pack.observation.capsule_substitutions > 0 or on_pack.observation.capsule_reads > 0
    assert on_pack.observation.atp_bonus_total >= 0.0
    assert off_pack.observation.capsule_substitutions == 0
    eat_on = _eat_count(on_result)
    eat_off = _eat_count(off_result)
    assert eat_on > eat_off


def test_default_phase_e_substrate_world_records_capsule_activity_and_ablation_differs() -> None:
    on_spec = GenesisRuntimeProfile.phase_e_substrate_world(
        seed=7, tick_count=8, population=6, enable_capsule_memory=True
    )
    off_spec = GenesisRuntimeProfile.phase_e_substrate_world(
        seed=7,
        tick_count=8,
        population=6,
        enable_capsule_memory=False,
        seed_preferred_action="",
    )
    on_result = GenesisEngine.from_spec(on_spec).run_ticks()
    off_result = GenesisEngine.from_spec(off_spec).run_ticks()
    on_pack = build_phase_e_evidence_pack(on_result)
    off_pack = build_phase_e_evidence_pack(off_result)
    assert on_result.digest() != off_result.digest()
    assert on_pack.observation.capsule_writes > 0
    assert on_pack.observation.capsule_reads > 0
    assert on_pack.observation.capsule_substitutions > 0
    assert off_pack.observation.capsule_writes == 0
    assert off_pack.observation.capsule_reads == 0
    assert off_pack.observation.capsule_substitutions == 0
    assert on_pack.claim_ceiling == "runtime_observation"
    assert on_pack.to_dict()["collective_intelligence_proved"] is False


def test_lineage_capsule_inheritance_flag_roundtrips() -> None:
    config = PhaseESubstrateConfig.capsule_memory_preset(inherit_lineage=True)
    assert config.capsule_memory.inherit_lineage is True
    restored = PhaseESubstrateConfig.from_dict(config.to_dict())
    assert restored.digest() == config.digest()
    assert restored.capsule_memory.inherit_lineage is True


def test_role_gate_blocks_soma_reproduction() -> None:
    soma = GenesisOrganism.from_bits("soma", "111000000", initial_runtime_atp=20.0)
    germline = GenesisOrganism.from_bits("germ", "111000000", initial_runtime_atp=20.0)
    config = PhaseESubstrateConfig(
        enabled=True,
        roles=RoleDifferentiationConfig(enabled=True, gate_reproduction=True),
    )
    soma.phase_e_state = attach_phase_e_to_organisms((soma,), config)[0].phase_e_state
    germline.phase_e_state = attach_phase_e_to_organisms((germline,), config)[0].phase_e_state
    assert soma.phase_e_state is not None
    soma.phase_e_state.role = role_for_kind(RoleKind.SOMA)
    soma.phase_e_state.gate_reproduction = True
    assert germline.phase_e_state is not None
    germline.phase_e_state.role = role_for_kind(RoleKind.GERMLINE)
    germline.phase_e_state.gate_reproduction = True
    alive = AliveGateResult(
        passed=True,
        survived_ticks=1,
        executed_actions=1,
        blocked_actions=0,
        blocked_ratio=0.0,
        final_runtime_atp=20.0,
        lumen_interactions=1,
        reproduction_events=0,
        reasons=(),
    )
    from codontrace.genesis.population import ReproductionConfig

    rec = ReproductionConfig(min_runtime_atp=8.0, parent_atp_cost=1.0)
    soma_decision = can_reproduce(soma, alive, rec)
    germ_decision = can_reproduce(germline, alive, rec)
    assert soma_decision.allowed is False
    assert "not_propagule_eligible" in soma_decision.reasons
    assert germ_decision.allowed is True


def test_deme_messaging_buffer_send_retrieve_broadcast_and_block() -> None:
    state = DemeState()
    state.demes = (Deme(deme_id="deme-0", member_ids=("a", "b")),)
    sent = send_message(
        state,
        tick=1,
        sender_id="a",
        deme_id="deme-0",
        payload="EAT_SUCCESS",
        kind=MessageKind.BROADCAST,
        recipient_ids=("a", "b"),
        can_message=True,
        can_forward=True,
    )
    assert sent.blocked is False
    got = retrieve_message(state, deme_id="deme-0")
    assert got is not None
    assert got.payload == "EAT_SUCCESS"
    blocked = send_message(
        state,
        tick=2,
        sender_id="b",
        deme_id="deme-0",
        payload="NOPE",
        kind=MessageKind.BLOCK_PROPAGATION,
        can_message=True,
        can_forward=False,
    )
    assert blocked.blocked is True
    soma_blocked = send_message(
        state,
        tick=3,
        sender_id="b",
        deme_id="deme-0",
        payload="X",
        kind=MessageKind.SEND,
        can_message=False,
    )
    assert soma_blocked.blocked_reason == "role_cannot_message"


def test_deme_replication_trigger_records_event() -> None:
    world = World2D(6, 4)
    world.place_resource((0, 0), 6.0)
    organisms = [
        GenesisOrganism.from_bits(f"org-{i}", "101000000", initial_runtime_atp=14.0, position=(i, 0))
        for i in range(2)
    ]
    config = PhaseESubstrateConfig(
        enabled=True,
        capsule_memory=CapsuleMemoryConfig(enabled=False),
        roles=RoleDifferentiationConfig(enabled=True, assignment="round_robin", gate_reproduction=False),
        demes=DemeConfig(enabled=True, deme_size=2, replicate_on_mean_fitness=0.0),
    )
    organisms = list(attach_phase_e_to_organisms(organisms, config))
    population = PopulationState(generation=0, tick=0, organisms=tuple(organisms), lineage=(), fitness=())
    configs = PopulationConfigs(phase_e=config, alive_gate=AliveGateConfig(min_ticks=0, require_positive_runtime_atp=False))
    result = step_population(population, world, configs, seed=3)
    assert result.deme_state is not None
    assert result.deme_state.replication_events


def test_plasticity_protocol_is_checklist_not_proof() -> None:
    spec = PlasticityProtocolSpec(condition=PlasticityCondition.FLUCTUATING, sense_react_enabled=True)
    assert spec.claim_ceiling == "runtime_observation"
    assert spec.to_dict()["plasticity_evolved"] is False
    names = {name for name, _detail in spec.experimental_design_checklist()}
    assert names == {item.value for item in PlasticityCondition}
    assert len(GHALAMBOR_CLUNE_CONDITIONS) == 4
    cue = read_environment_cue(tick=0, position=(0, 0), world=World2D(2, 2), environment=None)
    roundtrip = PlasticityProtocolSpec.from_dict(spec.to_dict())
    assert roundtrip.digest == spec.digest
    assert cue.source == "phase_c_env_and_local_patches"


def test_avida_parity_protocol_and_ontoavida_export() -> None:
    protocol = AvidaParityProtocolSpec(include_capsule_memory=True, include_multi_generation_evidence=True)
    assert protocol.to_dict()["superiority_claimed"] is False
    assert protocol.to_dict()["avida_replacement"] is False
    spec = replace(
        GenesisRuntimeProfile.phase_e_substrate_world(seed=5, tick_count=4, population=2),
        genome_bits=("000000000", "000000000"),
    )
    result = GenesisEngine.from_spec(spec).run_ticks()
    rows = export_phenotype_transcriptome(result)
    assert rows
    assert rows[0].digest
    assert rows[0].export_kind == (
        "phenotype_plus_instruction_execution_counts_not_biological_transcriptome"
    )
    assert "instruction_execution_counts" in rows[0].to_dict()
    assert rows[0].to_dict()["biological_transcriptome"] is False
    assert "ontoavida_avidar_2023" in rows[0].literature_refs
    pack = build_phase_e_evidence_pack(result, protocol=protocol)
    assert pack.digest == pack.to_dict()["digest"]
    decision = evaluate_phase_e_claim(pack)
    assert decision.final_claim == "runtime_observation"
    blocked = ScientificClaimGate().decide(ClaimRequest("collective_intelligence", {}))
    assert blocked.allowed is False
    plasticity = ScientificClaimGate().decide(ClaimRequest("evolved_plasticity", {}))
    assert plasticity.allowed is False
    replacement = ScientificClaimGate().decide(ClaimRequest("avida_replacement", {}))
    assert replacement.allowed is False


def test_phase_d_metrics_observe_phase_e_behavior_change() -> None:
    on_spec = replace(
        GenesisRuntimeProfile.phase_e_substrate_world(seed=7, tick_count=6, population=2),
        genome_bits=("000000000", "000000000"),
    )
    off_spec = replace(
        GenesisRuntimeProfile.phase_e_substrate_world(
            seed=7, tick_count=6, population=2, enable_capsule_memory=False, seed_preferred_action=""
        ),
        genome_bits=("000000000", "000000000"),
    )
    on_pack = build_multi_generation_evidence_pack(
        GenesisEngine.from_spec(on_spec).run_ticks(), spec=on_spec
    )
    off_pack = build_multi_generation_evidence_pack(
        GenesisEngine.from_spec(off_spec).run_ticks(), spec=off_spec
    )
    assert on_pack.digest != off_pack.digest
    assert on_pack.claim_ceiling == "runtime_observation"


def test_sexual_and_dynamic_env_opt_ins_still_available() -> None:
    sexual = GenesisRuntimeProfile.life_loop_world(
        seed=3, tick_count=4, population=4, reproduction_mode=ReproductionMode.SEXUAL_CROSSOVER
    )
    env = GenesisRuntimeProfile.dynamic_environment_world(seed=3, tick_count=4, population=4)
    mixed = GenesisRuntimeProfile.phase_e_substrate_world(
        seed=3,
        tick_count=4,
        population=4,
        environment=EnvironmentConfig.fluctuating_chemostat(
            initial=4.0,
            inflow=1.0,
            period_ticks=2,
            patch_cells=((0, 0), (1, 0)),
        ),
    )
    assert sexual.metadata["phase_b_sexual_crossover"] == "enabled"
    assert env.metadata["phase_c_fluctuating_environment"] == "enabled"
    assert mixed.metadata["phase_e_capsule_memory_collective"] == "enabled"
    assert mixed.population_configs is not None
    assert mixed.population_configs.environment.enabled is True


def test_phase_e_pack_is_replay_critical_with_validated_digest() -> None:
    policy = build_replay_digest_class_policy("codontrace.genesis.phase_e.PhaseEEvidencePack")
    assert policy.replay_critical
    assert "digest" in policy.digest_fields
    obs_policy = build_replay_digest_class_policy("codontrace.genesis.phase_e.PhaseEObservation")
    assert obs_policy.replay_role == "non_replay_critical"


def test_literature_checklist_covers_required_sources() -> None:
    keys = {name for name, _detail in LITERATURE_CHECKLIST}
    assert "avida_demes_group_selection" in keys
    assert "goldsby_coordination_instructions" in keys
    assert "associative_learning_odometry" in keys
    assert "ontoavida_avidar" in keys
    assert "plasticity_fluctuating_env" in keys


def test_public_exports_include_phase_e_symbols() -> None:
    import codontrace.genesis as g

    for name in (
        "PhaseEEvidencePack",
        "AvidaParityProtocolSpec",
        "PhaseESubstrateConfig",
        "build_phase_e_evidence_pack",
        "read_environment_cue",
    ):
        assert hasattr(g, name)
        assert name in g.__all__


def _eat_count(result: object) -> int:
    total = 0
    for tick in getattr(result, "ticks", ()):
        generation = getattr(tick, "generation_result", None)
        if generation is None:
            continue
        for trace in getattr(generation, "traces", ()):
            for event in getattr(trace, "events", ()):
                if getattr(event, "action", "") == "EAT_LUMEN":
                    total += 1
    return total
