"""Phase D multi-generation instinct/behavior evidence tests.

These tests document software capability and runtime observation only. They do
not claim artificial life, intelligence, instinct evolution, or open-endedness.
"""

from __future__ import annotations

import json

from codontrace.errors import ConfigurationError
from codontrace.genesis.birth import ReproductionMode
from codontrace.genesis.claim_gate import ClaimRequest, ScientificClaimGate
from codontrace.genesis.engine import GenesisEngine
from codontrace.genesis.multi_generation import (
    LITERATURE_CHECKLIST,
    GenerationCensus,
    MultiGenerationEvidenceConfig,
    MultiGenerationEvidencePack,
    OrganismCensusRecord,
    build_bedau_activity_surface,
    build_fitness_trajectory,
    build_modes_assessment,
    build_multi_generation_evidence_pack,
    compare_descendant_cohorts,
    describe_modes_persistence_semantics,
    evaluate_instinct_improvement_claim,
    evaluate_oee_measurement_claim,
    evaluate_tokyo_type1_measurement_claim,
    export_multi_generation_evidence_pack,
    filter_persistent_lineages,
    run_mutation_ablation_control,
)
from codontrace.genesis.replay_integrity import build_replay_digest_class_policy
from codontrace.genesis.runtime_profiles import (
    GenesisRuntimeProfile,
    summarize_life_loop_observation,
)
from codontrace.genesis.statistical_protocol import StatisticalProtocolConfig


def _org(
    organism_id: str,
    generation: int,
    *,
    parent_id: str | None = None,
    genome: str = "g",
    fitness: float = 1.0,
    lumen_eaten: int = 0,
    role: str = "unknown",
    unique_positions: int = 1,
) -> OrganismCensusRecord:
    return OrganismCensusRecord(
        organism_id=organism_id,
        generation=generation,
        genome_digest=genome,
        genome_bits="101" if genome.startswith("e") else "000",
        parent_id=parent_id,
        second_parent_id=None,
        fitness=fitness,
        selection_fitness=fitness,
        runtime_atp=2.0,
        lumen_eaten=lumen_eaten,
        action_counts=(("EAT_LUMEN", lumen_eaten),) if lumen_eaten else (("WAIT", 1),),
        role_signature=role,
        unique_positions=unique_positions,
        behavior_key=f"{role}|eat:{lumen_eaten}",
    )


def _census(
    generation: int,
    organisms: tuple[OrganismCensusRecord, ...],
    *,
    births: int = 0,
    deaths: int = 0,
) -> GenerationCensus:
    mean = sum(item.fitness for item in organisms) / len(organisms)
    return GenerationCensus(
        generation=generation,
        mean_fitness=mean,
        max_fitness=max(item.fitness for item in organisms),
        selection_mean_fitness=mean,
        selection_max_fitness=max(item.fitness for item in organisms),
        survival_count=len(organisms),
        births=births,
        deaths=deaths,
        mean_runtime_atp=2.0,
        resource_intake=sum(item.lumen_eaten for item in organisms),
        organisms=organisms,
    )


def test_phase_d_public_api_symbols_are_exported() -> None:
    import codontrace.genesis as g

    for name in (
        "MultiGenerationEvidencePack",
        "build_multi_generation_evidence_pack",
        "ModesAssessment",
        "BedauActivitySurface",
        "evaluate_instinct_improvement_claim",
        "evaluate_oee_measurement_claim",
        "evaluate_tokyo_type1_measurement_claim",
        "TOKYO_TYPE1_MEASUREMENT_CLAIM",
        "export_multi_generation_evidence_pack",
        "describe_modes_persistence_semantics",
        "TokyoType1MeasurementProtocol",
        "build_tokyo_type1_measurement_protocol",
    ):
        assert hasattr(g, name)
        assert name in g.__all__
    spec = GenesisRuntimeProfile.life_loop_world(seed=7, tick_count=12, population=6)
    assert spec.digest() == "7d199ae51345872215dbbb0c45cf8f141aacfb4c31d6537eda6de246c0cb7aac"
    assert spec.metadata["phase_d_instinct_claim_metrics"] == "hooks_only_not_implemented"
    result = GenesisEngine.from_spec(spec).run_ticks()
    observation = summarize_life_loop_observation(result)
    assert observation.phase_d_instinct_metrics == "hooks_only_not_implemented"
    assert observation.claim_ceiling == "runtime_observation"


def test_fitness_trajectory_is_digest_backed_and_replay_stable() -> None:
    spec = GenesisRuntimeProfile.life_loop_world(seed=7, tick_count=12, population=6)
    first = GenesisEngine.from_spec(spec).run_ticks()
    second = GenesisEngine.from_spec(spec).run_ticks()
    pack_a = build_multi_generation_evidence_pack(first, spec=spec)
    pack_b = build_multi_generation_evidence_pack(second, spec=spec)
    assert pack_a.digest == pack_b.digest
    assert len(pack_a.fitness_trajectory.points) == 12
    point = pack_a.fitness_trajectory.points[0]
    assert point.survival_count >= 1
    assert point.mean_runtime_atp >= 0.0
    assert pack_a.fitness_trajectory.digest()
    assert pack_a.claim_ceiling == "runtime_observation"
    assert pack_a.cohort_comparison is not None
    assert pack_a.cohort_comparison.env_seed == 7


def test_persistence_filter_keeps_only_lineages_with_living_descendants() -> None:
    censuses = (
        _census(0, (_org("A", 0, genome="e1", fitness=1.0), _org("B", 0, genome="w1", fitness=0.2))),
        _census(1, (_org("A1", 1, parent_id="A", genome="e2", fitness=1.5),), births=1, deaths=1),
        _census(2, (_org("A2", 2, parent_id="A1", genome="e3", fitness=2.0),), births=1),
    )
    filt = filter_persistent_lineages(censuses, generation=0, window_t=2)
    assert "A" in filt.persistent_organism_ids
    assert "B" not in filt.persistent_organism_ids
    assert filt.alive_at_horizon == 1
    assert filt.persistence_window_t == 2
    assert filt.horizon_observed is True
    assert filt.to_dict()["empirical_systematics_shadow_run"] is False
    assert "coalescence_window_organism_id_graph_not_full_phylogeny" in filt.to_dict()["limitations"]
    modes = build_modes_assessment(censuses, MultiGenerationEvidenceConfig(persistence_window_generations=2))
    assert modes.points
    assert modes.points[0].persistent_count == 1
    assert modes.persistence_window_t == 2
    assert modes.to_dict()["oee_proved"] is False


def test_persistence_filter_coalescence_window_drops_lineages_that_die_before_horizon() -> None:
    """Longer t is a stricter coalescence window (Empirical MODES subtlety)."""

    censuses = (
        _census(
            0,
            (
                _org("A", 0, genome="e1", fitness=1.0),
                _org("B", 0, genome="w1", fitness=0.2),
                _org("C", 0, genome="e9", fitness=0.5),
            ),
        ),
        _census(
            1,
            (
                _org("A1", 1, parent_id="A", genome="e2", fitness=1.5),
                _org("B1", 1, parent_id="B", genome="w2", fitness=0.3),
            ),
            births=2,
            deaths=1,
        ),
        _census(2, (_org("A2", 2, parent_id="A1", genome="e3", fitness=2.0),), births=1, deaths=1),
    )
    short = filter_persistent_lineages(censuses, generation=0, persistence_window_t=1)
    long = filter_persistent_lineages(censuses, generation=0, window_t=2, persistence_window_t=2)
    assert set(short.persistent_organism_ids) == {"A", "B"}
    assert set(long.persistent_organism_ids) == {"A"}
    assert "C" not in short.persistent_organism_ids
    survivor = (
        _census(0, (_org("S", 0, genome="stay"),)),
        _census(1, (_org("S", 1, genome="stay"),)),
        _census(2, (_org("S", 2, genome="stay"),)),
    )
    self_alive = filter_persistent_lineages(survivor, generation=0, persistence_window_t=2)
    assert self_alive.persistent_organism_ids == ("S",)
    assert self_alive.self_survival_counts_as_lineage_continuation is True
    missing_horizon = filter_persistent_lineages(censuses, generation=0, persistence_window_t=3)
    assert missing_horizon.persistent_organism_ids == ()
    assert missing_horizon.horizon_observed is False
    semantics = describe_modes_persistence_semantics()
    assert semantics["empirical_systematics_shadow_run"] is False
    assert semantics["oee_proved"] is False
    config = MultiGenerationEvidenceConfig(persistence_window_generations=2)
    assert config.persistence_window_t == 2


def test_bedau_activity_surface_tracks_novelty_diversity_and_activity() -> None:
    censuses = (
        _census(0, (_org("A", 0, genome="e1", role="forager"),)),
        _census(1, (_org("A1", 1, parent_id="A", genome="e1", role="forager"), _org("C", 1, genome="e2", role="scout"))),
        _census(2, (_org("C1", 2, parent_id="C", genome="e2", role="scout"),)),
    )
    surface = build_bedau_activity_surface(
        censuses,
        MultiGenerationEvidenceConfig(persistence_window_generations=1),
        persistence_filtered=False,
    )
    assert surface.points[0].novelty == 1
    assert surface.points[1].novelty == 1
    assert surface.points[1].diversity == 2
    assert surface.points[-1].cumulative_activity >= surface.points[0].activity
    assert "bedau_evolutionary_activity" in surface.literature_refs


def test_descendant_cohort_comparison_is_runtime_observation_only() -> None:
    censuses = (
        _census(0, (_org("A", 0, genome="e1", fitness=1.0, lumen_eaten=0),)),
        _census(1, (_org("A1", 1, parent_id="A", genome="e2", fitness=2.0, lumen_eaten=2),)),
    )
    comparison = compare_descendant_cohorts(
        censuses,
        MultiGenerationEvidenceConfig(),
        env_seed=7,
    )
    assert comparison is not None
    assert comparison.descendant_outperforms_ancestors is True
    assert comparison.fitness_delta > 0
    assert comparison.claim_ceiling == "runtime_observation"
    assert comparison.comparison_kind == "same_run"


def test_evidence_pack_json_export_and_claim_gate_honesty() -> None:
    spec = GenesisRuntimeProfile.life_loop_world(seed=7, tick_count=8, population=6)
    result = GenesisEngine.from_spec(spec).run_ticks()
    pack = build_multi_generation_evidence_pack(result, spec=spec)
    payload = export_multi_generation_evidence_pack(pack)
    assert payload["digest"] == pack.digest
    assert payload["oee_proved"] is False
    assert payload["open_ended_intelligence"] is False
    assert payload["instinct_evolution_proved"] is False
    parsed = json.loads(pack.to_json())
    assert parsed["digest"] == pack.digest
    assert parsed["schema_version"] == "multi_generation_evidence_pack_v1"
    literature_keys = {item[0] for item in LITERATURE_CHECKLIST}
    assert literature_keys == {item[0] for item in parsed["literature_checklist"]}
    assert pack.oee_metrics_report is not None
    assert pack.oee_metrics_report.claim_level in {"measurement_only", "insufficient"}
    instinct = evaluate_instinct_improvement_claim(pack)
    assert instinct.allowed is False
    assert instinct.final_claim == "runtime_observation"
    oee = evaluate_oee_measurement_claim(pack)
    assert oee.final_claim == "oee_measurement_only"
    tokyo = evaluate_tokyo_type1_measurement_claim(pack)
    assert tokyo.final_claim == "oee_measurement_only"
    assert tokyo.requested_claim == "tokyo_type1_measurement_only"
    blocked = ScientificClaimGate().decide(ClaimRequest("open_ended_intelligence", {}))
    assert blocked.allowed is False
    proved = ScientificClaimGate().decide(ClaimRequest("proved_instinct_evolution", {}))
    assert proved.allowed is False


def test_instinct_improved_stays_candidate_without_pretending_publication_grade() -> None:
    gate = ScientificClaimGate()
    allowed = gate.decide(
        ClaimRequest(
            "instinct_improved",
            {
                "metric_delta_observed": True,
                "same_env_seed_paired_comparison": True,
                "multi_seed_protocol": True,
                "ablation_or_control_present": True,
                "persistence_filter_applied": True,
            },
        )
    )
    assert allowed.allowed is True
    assert allowed.final_claim == "instinct_improved"
    pack = build_multi_generation_evidence_pack(
        GenesisEngine.from_spec(
            GenesisRuntimeProfile.life_loop_world(seed=3, tick_count=6, population=4)
        ).run_ticks(),
        MultiGenerationEvidenceConfig(claim_ceiling="candidate_evidence"),
        multi_seed_protocol=StatisticalProtocolConfig(min_seeds=5),
        ablation_control=None,
    )
    assert pack.claim_ceiling == "runtime_observation"
    assert pack.instinct_improved_status != "instinct_evolution_proved"


def test_optional_sexual_and_dynamic_env_runs_still_export_packs() -> None:
    sexual = GenesisRuntimeProfile.life_loop_world(
        seed=7,
        tick_count=8,
        population=6,
        reproduction_mode=ReproductionMode.SEXUAL_CROSSOVER,
    )
    env = GenesisRuntimeProfile.dynamic_environment_world(seed=7, tick_count=8, population=6)
    sexual_pack = build_multi_generation_evidence_pack(
        GenesisEngine.from_spec(sexual).run_ticks(), spec=sexual
    )
    env_pack = build_multi_generation_evidence_pack(
        GenesisEngine.from_spec(env).run_ticks(), spec=env
    )
    assert sexual_pack.fitness_trajectory.points
    assert env_pack.bedau_surface is not None
    assert sexual.metadata["phase_d_instinct_claim_metrics"] == "hooks_only_not_implemented"
    assert env.metadata["phase_d_instinct_claim_metrics"] == "hooks_only_not_implemented"


def test_ablation_control_hook_runs_no_mutation_control() -> None:
    spec = GenesisRuntimeProfile.life_loop_world(seed=5, tick_count=6, population=4)
    treatment = GenesisEngine.from_spec(spec).run_ticks()
    control = run_mutation_ablation_control(spec, treatment)
    assert control.control_kind == "no_mutation"
    assert control.treatment_run_digest
    assert control.control_run_digest
    assert control.claim_ceiling == "runtime_observation"
    pack = build_multi_generation_evidence_pack(
        treatment, spec=spec, ablation_control=control
    )
    assert pack.ablation_control is not None
    decision = evaluate_instinct_improvement_claim(pack)
    assert decision.final_claim == "runtime_observation"


def test_pack_constructor_rejects_proof_claims() -> None:
    spec = GenesisRuntimeProfile.life_loop_world(seed=1, tick_count=4, population=3)
    result = GenesisEngine.from_spec(spec).run_ticks()
    trajectory = build_fitness_trajectory(
        (
            _census(0, (_org("A", 0, genome="e1"),)),
            _census(1, (_org("A1", 1, parent_id="A", genome="e1", fitness=2.0),)),
        ),
        run_digest=result.digest(),
        seed=1,
    )
    from codontrace.genesis.multi_generation import InstinctBehaviorTrajectory

    instinct = InstinctBehaviorTrajectory(summaries=())
    try:
        MultiGenerationEvidencePack(
            fitness_trajectory=trajectory,
            instinct_trajectory=instinct,
            cohort_comparison=None,
            modes_assessment=None,
            bedau_surface=None,
            oee_metrics_report=None,
            hallmark_observation=None,
            ablation_control=None,
            config=MultiGenerationEvidenceConfig(),
            run_digest=result.digest(),
            seed=1,
            instinct_improved_status="proved_instinct_evolution",
        )
    except ConfigurationError as exc:
        assert "never claim" in str(exc).lower()
    else:
        raise AssertionError("proof status should be rejected")


def test_phase_d_pack_is_replay_critical_with_validated_digest() -> None:
    policy = build_replay_digest_class_policy(
        "codontrace.genesis.multi_generation.MultiGenerationEvidencePack"
    )
    assert policy.replay_critical is True
    assert "digest" in policy.digest_fields
    organism_policy = build_replay_digest_class_policy(
        "codontrace.genesis.multi_generation.OrganismCensusRecord"
    )
    assert organism_policy.replay_critical is False
    assert organism_policy.evidence_role == "reference_or_summary_only_not_scientific_evidence"
