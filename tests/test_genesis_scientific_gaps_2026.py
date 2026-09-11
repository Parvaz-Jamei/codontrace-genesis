"""Scientific-gaps 2026 surfaces (opt-in). ClaimGate stays honest.

These tests document software capability and measurement design only. They do
not claim intelligence, AGI, Tokyo Type 1 passed, OEE, associative learning,
collective intelligence, or Avida replacement.
"""

from __future__ import annotations

import pytest

from codontrace.errors import ConfigurationError
from codontrace.genesis.birth import (
    ReproductionMode,
    SexualRecombinationConfig,
    coerce_reproduction_mode,
    reduce_incipient_to_haploid_gamete,
    split_diploid_homologs,
)
from codontrace.genesis.claim_gate import ClaimRequest, ScientificClaimGate
from codontrace.genesis.engine import GenesisEngine
from codontrace.genesis.empirical_systematics import (
    EmpiricalSystematicsShadowConfig,
    build_empirical_systematics_shadow,
    evaluate_empirical_systematics_shadow_claim,
)
from codontrace.genesis.liveness import AliveGateConfig
from codontrace.genesis.logic9 import (
    LOGIC9_TASKS,
    Logic9ReactionConfig,
    build_logic9_reaction_pack,
    detect_logic9_tasks,
    evaluate_logic9_reaction_claim,
    logic9_outputs,
)
from codontrace.genesis.multi_generation import build_multi_generation_evidence_pack
from codontrace.genesis.organism import GenesisOrganism
from codontrace.genesis.phase_e import (
    CapsuleMemoryConfig,
    DemeConfig,
    PhaseESubstrateConfig,
    RoleDifferentiationConfig,
    attach_phase_e_to_organisms,
    build_phase_e_evidence_pack,
)
from codontrace.genesis.population import (
    MutationConfig,
    OffspringPlacementPolicy,
    PopulationConfigs,
    PopulationState,
    ReproductionConfig,
    step_population,
)
from codontrace.genesis.replay_integrity import build_replay_digest_class_policy
from codontrace.genesis.runtime_profiles import GenesisRuntimeProfile
from codontrace.genesis.tokyo_type1 import (
    build_tokyo_type1_measurement_protocol,
    evaluate_tokyo_type1_pass_claim,
    run_multi_seed_tokyo_measurement_campaign,
)
from codontrace.genesis.benchmark_suite import run_channon_avida_modes_shadow_suite
from codontrace.genesis.collective_deme import (
    build_collective_deme_payoff_pack,
    evaluate_collective_deme_payoff_claim,
)
from codontrace.genesis.learning_payoff import (
    build_learning_causal_payoff_pack,
    evaluate_learning_causal_payoff_claim,
)
from codontrace.rng import RNGManager
from codontrace.world import World2D

LIFE_LOOP_SPEC_DIGEST = "7d199ae51345872215dbbb0c45cf8f141aacfb4c31d6537eda6de246c0cb7aac"


def _nand_completing_genome() -> str:
    channel_a = "10101010"
    channel_b = "11001100"
    interleaved = "".join(left + right for left, right in zip(channel_a, channel_b))
    motif = logic9_outputs(channel_a, channel_b)["NAND"]
    bits = interleaved + motif
    while len(bits) % 3:
        bits += "0"
    return bits


def test_phase_a_life_loop_digest_pin_stays_stable() -> None:
    spec = GenesisRuntimeProfile.life_loop_world(seed=7, tick_count=12, population=6)
    assert spec.digest() == LIFE_LOOP_SPEC_DIGEST


def test_build_multi_generation_evidence_pack_rejects_garbage() -> None:
    with pytest.raises(TypeError, match="run result"):
        build_multi_generation_evidence_pack(None)
    with pytest.raises(TypeError, match="ticks collection"):
        build_multi_generation_evidence_pack("not-a-result")


def test_reproduction_mode_none_is_consistently_asexual() -> None:
    assert coerce_reproduction_mode(None) is ReproductionMode.ASEXUAL
    config = ReproductionConfig(reproduction_mode=None)  # type: ignore[arg-type]
    assert config.reproduction_mode is ReproductionMode.ASEXUAL
    assert "reproduction_mode" not in config.to_dict()
    spec = GenesisRuntimeProfile.life_loop_world(reproduction_mode=None)  # type: ignore[arg-type]
    assert spec.population_configs is not None
    assert spec.population_configs.reproduction.reproduction_mode is ReproductionMode.ASEXUAL


def test_empirical_systematics_shadow_is_opt_in_and_never_passes_type1() -> None:
    spec = GenesisRuntimeProfile.life_loop_world(seed=7, tick_count=8, population=6)
    result = GenesisEngine.from_spec(spec).run_ticks()
    with pytest.raises(ConfigurationError, match="enabled=True"):
        build_empirical_systematics_shadow(result)
    shadow = build_empirical_systematics_shadow(
        result,
        EmpiricalSystematicsShadowConfig(enabled=True, seed=7, persistence_window_t=2),
    )
    assert shadow.empirical_systematics_shadow_run is True
    assert len(shadow.shadow_digest) == 64
    assert shadow.tokyo_type1_passed is False
    protocol = build_tokyo_type1_measurement_protocol(
        build_multi_generation_evidence_pack(result, spec=spec),
        shadow_digest=shadow.shadow_digest,
        empirical_systematics_shadow_run=True,
    )
    assert protocol.empirical_systematics_shadow_run is True
    assert protocol.shadow_normalization_status == "empirical_systematics_shadow_recorded_not_cpp_port"
    assert protocol.tokyo_type1_passed is False
    assert evaluate_tokyo_type1_pass_claim(protocol).allowed is False
    measured = evaluate_empirical_systematics_shadow_claim(shadow)
    assert measured.final_claim != "tokyo_type1_passed"
    policy = build_replay_digest_class_policy(
        "codontrace.genesis.empirical_systematics.EmpiricalSystematicsShadowRun"
    )
    assert policy.replay_critical is True


def test_multi_seed_tokyo_campaign_requires_two_seeds_and_blocks_pass() -> None:
    with pytest.raises(ConfigurationError, match="at least two seeds"):
        run_multi_seed_tokyo_measurement_campaign(seeds=(7,))
    campaign = run_multi_seed_tokyo_measurement_campaign(
        seeds=(3, 7),
        tick_count=6,
        population=4,
        empirical_systematics_shadow=True,
    )
    assert campaign.protocol.seed_count >= 2
    assert campaign.tokyo_type1_passed is False
    assert campaign.claim_ceiling == "tokyo_type1_measurement_only"
    assert campaign.empirical_systematics_shadow_run is True
    assert evaluate_tokyo_type1_pass_claim(campaign.protocol).allowed is False
    blocked = ScientificClaimGate().decide(ClaimRequest("tokyo_type1_passed", {}))
    assert blocked.allowed is False


def test_logic9_reaction_coupling_is_opt_in_digest_backed() -> None:
    bits = _nand_completing_genome()
    assert "NAND" in detect_logic9_tasks(bits)
    assert detect_logic9_tasks("101000000") == ()
    world = World2D(4, 4)
    world.place_resource((0, 0), 4.0)
    organism = GenesisOrganism.from_bits("org-0", bits, initial_runtime_atp=12.0, position=(0, 0))
    configs = PopulationConfigs(
        logic9=Logic9ReactionConfig(enabled=True, consume_amount=1.0, atp_bonus=0.5),
        alive_gate=AliveGateConfig(min_ticks=0, require_positive_runtime_atp=False),
        mutation=MutationConfig(bit_flip_rate=0.0),
    )
    off = PopulationConfigs(
        alive_gate=AliveGateConfig(min_ticks=0, require_positive_runtime_atp=False),
        mutation=MutationConfig(bit_flip_rate=0.0),
    )
    assert "logic9" not in off.to_dict()
    born = step_population(PopulationState(0, 0, (organism,), (), ()), world, configs, seed=3)
    assert born.logic9_events
    assert any(item.task == "NAND" and item.consumed > 0 for item in born.logic9_events)
    pack = build_logic9_reaction_pack(
        type("Run", (), {"ticks": (), "spec": type("S", (), {"genome_bits": (bits,)})()})(),
        Logic9ReactionConfig(enabled=False),
    )
    assert pack.events == ()
    enabled_pack = build_logic9_reaction_pack(
        type(
            "Run",
            (),
            {
                "ticks": (
                    type(
                        "Tick",
                        (),
                        {
                            "index": 0,
                            "generation_result": born,
                        },
                    )(),
                )
            },
        )(),
        Logic9ReactionConfig(enabled=True, population_size=1, mutation_bit_flip_rate=0.05),
    )
    assert enabled_pack.claim_ceiling == "runtime_observation"
    assert enabled_pack.total_consumed > 0
    assert evaluate_logic9_reaction_claim(enabled_pack).final_claim == "runtime_observation"
    assert ScientificClaimGate().decide(ClaimRequest("avida_replacement", {})).allowed is False
    assert set(LOGIC9_TASKS) == {
        "NOT",
        "NAND",
        "AND",
        "ORN",
        "OR",
        "ANDN",
        "NOR",
        "XOR",
        "EQU",
    }


def test_learning_causal_payoff_has_ablation_and_keeps_instinct_gated() -> None:
    pack = build_learning_causal_payoff_pack(seeds=(7, 11), tick_count=6, population=4)
    assert pack.seed_count >= 2
    assert pack.ablation_present is True
    assert pack.substitutions_on >= pack.substitutions_off
    assert pack.claim_ceiling == "runtime_observation"
    assert pack.instinct_improved_status == "gated_requires_phase_d_claim_gate"
    decision = evaluate_learning_causal_payoff_claim(pack)
    assert decision.final_claim == "runtime_observation"
    blocked = ScientificClaimGate().decide(ClaimRequest("associative_learning_proved", {}))
    assert blocked.allowed is False
    instinct = ScientificClaimGate().decide(ClaimRequest("instinct_improved", {}))
    assert instinct.allowed is False


def test_collective_deme_payoff_ledger_and_blocked_intelligence() -> None:
    world = World2D(6, 4)
    world.place_resource((0, 0), 6.0)
    organisms = [
        GenesisOrganism.from_bits(f"org-{i}", "101000000", initial_runtime_atp=14.0, position=(i, 0))
        for i in range(2)
    ]
    config = PhaseESubstrateConfig(
        enabled=True,
        capsule_memory=CapsuleMemoryConfig(enabled=False),
        roles=RoleDifferentiationConfig(
            enabled=True, assignment="round_robin", gate_reproduction=False
        ),
        demes=DemeConfig(
            enabled=True,
            deme_size=2,
            replicate_on_mean_fitness=0.0,
            replicate_copy_germline=True,
        ),
    )
    organisms = list(attach_phase_e_to_organisms(organisms, config))
    population = PopulationState(generation=0, tick=0, organisms=tuple(organisms), lineage=(), fitness=())
    configs = PopulationConfigs(
        phase_e=config,
        alive_gate=AliveGateConfig(min_ticks=0, require_positive_runtime_atp=False),
    )
    result = step_population(population, world, configs, seed=3)
    assert result.deme_state is not None
    assert result.deme_state.replication_events
    target_ids = {event.target_deme_id for event in result.deme_state.replication_events}
    assert target_ids <= {deme.deme_id for deme in result.deme_state.demes}
    fake_run = type("Run", (), {"ticks": (type("Tick", (), {"generation_result": result})(),)})()
    pack = build_collective_deme_payoff_pack(fake_run)
    assert pack.replication_count >= 1
    assert pack.ledgers
    assert pack.claim_ceiling == "runtime_observation"
    assert evaluate_collective_deme_payoff_claim(pack).final_claim == "runtime_observation"
    assert ScientificClaimGate().decide(ClaimRequest("collective_intelligence", {})).allowed is False
    on_spec = GenesisRuntimeProfile.phase_e_substrate_world(
        seed=3, tick_count=4, population=4, enable_demes=True
    )
    on_pack = build_phase_e_evidence_pack(GenesisEngine.from_spec(on_spec).run_ticks())
    assert on_pack.to_dict()["collective_intelligence_proved"] is False


def test_channon_avida_modes_shadow_suite_pins_windows_and_tokyo_json() -> None:
    suite = run_channon_avida_modes_shadow_suite(
        seed=7, tick_count=6, population=4, windows=(1, 2), include_empirical_shadow=True
    )
    assert suite.windows == (1, 2)
    assert len(suite.points) == 2
    assert suite.points[0].persistence_window_t == 1
    assert suite.points[1].tokyo_json
    assert '"tokyo_type1_passed":false' in suite.points[0].tokyo_json.replace(" ", "")
    assert suite.tokyo_type1_passed is False
    assert suite.empirical_systematics_shadow_run is True
    assert suite.claim_ceiling == "tokyo_type1_measurement_only"


def test_diploid_meiosis_and_two_fold_cost_are_opt_in() -> None:
    homolog_a, homolog_b = split_diploid_homologs("111000111000", codon_width=3)
    assert homolog_a
    assert homolog_b
    from codontrace.genesis.birth import IncipientOffspring

    slot = IncipientOffspring(
        slot_id="s",
        parent_id="p",
        genome_bits="111000111000",
        genome_digest="x",
        entered_tick=0,
        parent_position=(0, 0),
        offspring_runtime_atp=4.0,
        parent_generation=0,
        codon_width=3,
    )
    # digest is validated only as non-empty
    gamete = reduce_incipient_to_haploid_gamete(slot, RNGManager(0).fork("meiosis/test"))
    assert gamete.genome_bits
    world = World2D(4, 4)
    parent_a = GenesisOrganism.from_bits(
        "a", "111000111000", initial_runtime_atp=20.0, position=(0, 0)
    )
    parent_b = GenesisOrganism.from_bits(
        "b", "111111000111", initial_runtime_atp=20.0, position=(0, 1)
    )
    configs = PopulationConfigs(
        reproduction=ReproductionConfig(
            min_runtime_atp=1.0,
            parent_atp_cost=1.0,
            max_population=8,
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
        sexual_recombination=SexualRecombinationConfig(
            enabled=True,
            diploid_meiosis=True,
            two_fold_cost_sex=True,
            chamber_capacity=8,
        ),
    )
    born = step_population(
        PopulationState(0, 0, (parent_a, parent_b), (), ()),
        world,
        configs,
        seed=8,
    )
    assert born.births == 1
    spec = GenesisRuntimeProfile.life_loop_world(
        seed=3,
        tick_count=4,
        population=4,
        reproduction_mode=ReproductionMode.SEXUAL_CROSSOVER,
        two_fold_cost_sex=True,
        diploid_meiosis=True,
    )
    assert spec.metadata["two_fold_cost_sex"] is True
    assert spec.metadata["phase_b1_diploid_meiosis"] == "enabled"
    default_sexual = GenesisRuntimeProfile.life_loop_world(
        seed=7, tick_count=12, population=6, reproduction_mode=ReproductionMode.SEXUAL_CROSSOVER
    )
    assert default_sexual.metadata["phase_b1_diploid_meiosis"] == "deferred"
    assert default_sexual.metadata["two_fold_cost_sex"] is False
    restored = SexualRecombinationConfig.from_dict(
        SexualRecombinationConfig(enabled=True).to_dict()
    )
    assert restored.diploid_meiosis is False
    assert "diploid_meiosis" not in SexualRecombinationConfig(enabled=True).to_dict()


def test_scientific_gaps_public_api_and_claimgate() -> None:
    import codontrace.genesis as g

    for name in (
        "build_empirical_systematics_shadow",
        "run_multi_seed_tokyo_measurement_campaign",
        "build_logic9_reaction_pack",
        "build_learning_causal_payoff_pack",
        "build_collective_deme_payoff_pack",
        "run_channon_avida_modes_shadow_suite",
        "LOGIC9_TASKS",
    ):
        assert hasattr(g, name)
        assert name in g.__all__
    gate = ScientificClaimGate()
    for label in (
        "tokyo_type1_passed",
        "agi",
        "collective_intelligence",
        "associative_learning_proved",
        "avida_replacement",
        "open_ended_intelligence",
    ):
        assert gate.decide(ClaimRequest(label, {})).allowed is False
