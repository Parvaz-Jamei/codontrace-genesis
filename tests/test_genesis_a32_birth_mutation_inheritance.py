from __future__ import annotations

from codontrace.genesis.birth import (
    InheritancePolicy,
    SkillInheritanceMode,
)
from codontrace.genesis.claim_gate import ClaimRequest, ScientificClaimGate
from codontrace.genesis.engine import GenesisEngine, GenesisEngineConfig, GenesisExperimentSpec
from codontrace.genesis.organism import GenesisOrganism
from codontrace.genesis.population import MutationConfig, ReproductionConfig
from codontrace.trace import Trace
from codontrace.world import World2D


def _birth_result(
    *,
    inheritance_policy: InheritancePolicy = InheritancePolicy.DARWINIAN_GENETIC_ONLY,
    skill_mode: SkillInheritanceMode = SkillInheritanceMode.CAPACITY_ONLY,
    enable_lamarckian: bool = False,
) -> object:
    spec = GenesisExperimentSpec(
        genome_bits=("111",),
        seed=32,
        tick_count=1,
        population_max=4,
        initial_runtime_atp=20.0,
        reproduction_config=ReproductionConfig(
            max_population=4,
            min_runtime_atp=1.0,
            parent_atp_cost=1.0,
            inheritance_policy=inheritance_policy,
            skill_inheritance_mode=skill_mode,
            enable_skill_compression=enable_lamarckian,
            enable_lamarckian_learning_inheritance=enable_lamarckian,
        ),
        mutation_config=MutationConfig(bit_flip_rate=1.0),
        engine_config=GenesisEngineConfig(enable_qd=False),
    )
    return GenesisEngine.from_spec(spec).run_ticks()


def test_copy_self_birth_creates_child_under_valid_gate() -> None:
    result = _birth_result()
    assert sum(tick.generation_result.births for tick in result.ticks) > 0
    assert result.birth_event_records
    assert result.birth_event_records[0].child_created is True
    assert result.child_genome_records
    child = result.child_genome_records[0]
    assert child.child_genome_digest != child.parent_genome_digest
    assert child.mutation_count >= 0
    assert result.lineage_growth_records[0].lineage_growth_delta > 0


def test_copy_self_direct_handler_still_blocked_without_population_lifecycle() -> None:
    organism = GenesisOrganism.from_bits("org", "111", initial_runtime_atp=20.0)
    trace = Trace()
    event = organism.step(World2D(width=2, height=2), trace)
    assert event.action == "COPY_SELF"
    assert event.status == "blocked"
    assert event.reason == "reproduction_not_enabled"


def test_birth_blocks_when_max_population_reached() -> None:
    spec = GenesisExperimentSpec(
        genome_bits=("111",),
        seed=33,
        tick_count=1,
        population_max=1,
        initial_runtime_atp=20.0,
        reproduction_config=ReproductionConfig(max_population=1, min_runtime_atp=1.0),
        engine_config=GenesisEngineConfig(enable_qd=False),
    )
    result = GenesisEngine.from_spec(spec).run_ticks()
    assert result.birth_event_records
    assert result.birth_event_records[0].child_created is False
    assert result.birth_event_records[0].blocked_reason == "max_population_reached"
    assert result.reproduction_attempt_records[0].reproduction_action_attempted is True
    assert result.reproduction_attempt_records[0].blocked_reason == "max_population_reached"


def test_deferred_copy_self_does_not_count_as_blocked_for_reproduction_gate() -> None:
    result = _birth_result()
    record = result.ticks[0].generation_result.organism_records[0]
    assert record.reproduction_result is not None
    gate = record.reproduction_result.reproduction_gate_result
    assert gate is not None
    assert gate.allowed is True
    assert "alive_gate_not_passed" not in gate.reasons


def test_successful_birth_reproduction_records_do_not_crash() -> None:
    result = _birth_result()
    rows = result.reproduction_attempt_records
    assert rows[0].child_created is True
    assert rows[0].child_id is not None
    assert rows[0].lineage_id is not None
    assert result.birth_event_records[0].birth_event_id


def test_birth_exports_mutation_plan_and_result() -> None:
    result = _birth_result()
    assert result.mutation_plan_records
    assert result.mutation_result_records
    assert result.mutation_result_records[0].plan_id == result.mutation_plan_records[0].plan_id
    assert result.mutation_result_records[0].child_genome_digest


def test_baldwinian_mode_does_not_copy_learned_content_to_child() -> None:
    result = _birth_result(inheritance_policy=InheritancePolicy.BALDWINIAN)
    record = result.learning_inheritance_records[0]
    assert record.inheritance_policy == "baldwinian"
    assert record.baldwinian_selection_pressure is True
    assert record.learned_content_inherited is False
    assert record.child_received_skill_digest is None


def test_lamarckian_mode_requires_explicit_policy_and_records_skill_candidate() -> None:
    result = _birth_result(
        inheritance_policy=InheritancePolicy.LAMARCKIAN_COMPRESSED_LEARNING,
        skill_mode=SkillInheritanceMode.COMPRESSED_SKILL,
        enable_lamarckian=True,
    )
    record = result.learning_inheritance_records[0]
    assert record.learned_content_inherited is False
    assert record.compressed_skill_digest is not None
    assert record.child_received_skill_digest is None


def test_skill_compression_requires_positive_replay_validated_delta() -> None:
    result = _birth_result(
        inheritance_policy=InheritancePolicy.LAMARCKIAN_COMPRESSED_LEARNING,
        skill_mode=SkillInheritanceMode.COMPRESSED_SKILL,
        enable_lamarckian=True,
    )
    skill = result.skill_compression_records[0]
    assert skill.validation_status == "rejected"
    assert skill.rejected_reason == "no_valid_learning_evidence"
    assert skill.fitness_delta_positive is False
    assert skill.energy_efficiency_positive is False
    assert skill.replay_successful is False
    assert skill.inherited is False


def test_adf_inheritance_records_parent_and_child_digests() -> None:
    result = _birth_result()
    record = result.adf_inheritance_records[0]
    assert record.adf_inheritance_mode == "inherit_capacity"
    assert record.parent_id
    assert record.child_id is not None


def test_external_birth_intervention_disabled_is_explicitly_empty() -> None:
    result = _birth_result()
    assert result.ai_birth_intervention_records == ()
    assert "ai_birth_intervention_records" in result.evidence_manifest.artifact_digest_map


def test_external_birth_intervention_enabled_is_logged_without_hidden_controller() -> None:
    spec = GenesisExperimentSpec(
        genome_bits=("111",),
        seed=132,
        tick_count=1,
        population_max=4,
        initial_runtime_atp=20.0,
        reproduction_config=ReproductionConfig(
            max_population=4,
            min_runtime_atp=1.0,
            parent_atp_cost=1.0,
            enable_ai_birth_intervention=True,
        ),
        mutation_config=MutationConfig(bit_flip_rate=0.0),
        engine_config=GenesisEngineConfig(enable_qd=False),
    )
    result = GenesisEngine.from_spec(spec).run_ticks()
    records = result.ai_birth_intervention_records
    assert records
    assert {record.applied for record in records} == {False}
    assert {record.rejected_reason for record in records} == {"external_controller_not_configured"}
    assert result.digest() == GenesisEngine.from_spec(spec).run_ticks().digest()


def test_ai_intervention_disabled_has_identical_baseline_replay() -> None:
    first = _birth_result().digest()
    second = _birth_result().digest()
    assert first == second


def test_births_zero_blocks_evolution_claim() -> None:
    decision = ScientificClaimGate().decide(
        ClaimRequest(
            claim="digital_evolution_claim",
            evidence_flags={
                "births_positive": False,
                "heritable_variation": True,
                "differential_fitness": True,
            },
        )
    )
    assert decision.allowed is False
    assert "missing_births_positive" in decision.failed_reasons


def test_baldwinian_and_lamarckian_claims_are_distinct() -> None:
    gate = ScientificClaimGate()
    baldwin = gate.decide(
        ClaimRequest(
            claim="baldwinian_learning_claim",
            evidence_flags={
                "learning_improves_fitness": True,
                "selection_pressure_recorded": True,
                "learned_content_not_inherited": True,
            },
        )
    )
    lamarck_missing = gate.decide(
        ClaimRequest(
            claim="lamarckian_inheritance_claim",
            evidence_flags={
                "learned_content_inherited": True,
                "compressed_skill_validation": False,
                "inheritance_records": True,
            },
        )
    )
    assert baldwin.allowed is True
    assert lamarck_missing.allowed is False
    assert "missing_compressed_skill_validation" in lamarck_missing.failed_reasons


def test_ai_guided_claim_requires_intervention_and_baseline() -> None:
    decision = ScientificClaimGate().decide(
        ClaimRequest(
            claim="ai_guided_evolution_claim",
            evidence_flags={
                "external_intervention_records": True,
                "ai_disabled_baseline": False,
                "baseline_comparison": True,
            },
        )
    )
    assert decision.allowed is False
    assert "missing_ai_disabled_baseline" in decision.failed_reasons

import pytest

from codontrace.genesis.birth import (
    AIBirthInterventionRecord,
    BirthEvent,
    BirthIntent,
    BirthRequest,
    ChildAdmissionResult,
    ExternalBirthInterventionAPI,
    LearningInheritanceRecord,
    ReproductionGateResult,
    SkillCompressionRecord,
    WorldLawPatch,
    build_mutation_plan,
)
from codontrace.genesis.population import OffspringPlacementPolicy
from codontrace.genesis.selection import EvolutionConfig, select_population


def test_birth_intent_and_request_reject_invalid_identity_fields() -> None:
    with pytest.raises(ValueError):
        BirthIntent(organism_id="", tick=0)
    with pytest.raises(ValueError):
        BirthIntent(organism_id="p", tick=-1)
    with pytest.raises(ValueError):
        BirthRequest(
            request_id="",
            parent_id="p",
            tick=0,
            parent_genome_digest="g",
            policy_digest="policy",
            intent_digest="intent",
        )
    with pytest.raises(ValueError):
        BirthRequest(
            request_id="r",
            parent_id="p",
            tick=0,
            parent_genome_digest="",
            policy_digest="policy",
            intent_digest="intent",
        )


def test_skill_compression_record_rejects_invalid_mode() -> None:
    with pytest.raises(ValueError):
        SkillCompressionRecord(parent_id="p", child_id="c", tick=1, mode="FAKE_MODE")


def test_skill_compression_validated_requires_positive_replay_delta() -> None:
    with pytest.raises(ValueError):
        SkillCompressionRecord(
            parent_id="p",
            child_id="c",
            tick=1,
            mode="compressed_skill",
            validation_status="validated",
            compressed_skill_digest="skill",
            successful_behavior_trace_digest="trace",
            fitness_delta_positive=False,
            energy_efficiency_positive=True,
            replay_successful=True,
            inherited=True,
        )


def test_birth_event_rejects_child_id_when_child_not_created() -> None:
    with pytest.raises(ValueError):
        BirthEvent(
            birth_event_id="b",
            tick=1,
            parent_id="p",
            child_id="c",
            parent_lineage_id="p",
            child_lineage_id=None,
            parent_generation=0,
            child_generation=None,
            parent_genome_digest="pg",
            child_genome_digest=None,
            mutation_digest=None,
            mutation_count=0,
            mutation_operator_names=(),
            birth_cost_runtime_atp=0.0,
            birth_cost_learning_atp=0.0,
            child_initial_runtime_atp=None,
            child_initial_learning_atp=None,
            placement_cell=None,
            birth_policy_digest="policy",
            reproduction_gate_digest="gate",
            child_created=False,
            blocked_reason="blocked",
        )


def test_birth_event_success_requires_child_fields_and_placement() -> None:
    with pytest.raises(ValueError):
        BirthEvent(
            birth_event_id="b",
            tick=1,
            parent_id="p",
            child_id="c",
            parent_lineage_id="p",
            child_lineage_id="c",
            parent_generation=0,
            child_generation=1,
            parent_genome_digest="pg",
            child_genome_digest="cg",
            mutation_digest="md",
            mutation_count=0,
            mutation_operator_names=(),
            birth_cost_runtime_atp=1.0,
            birth_cost_learning_atp=0.0,
            child_initial_runtime_atp=1.0,
            child_initial_learning_atp=0.0,
            placement_cell=None,
            birth_policy_digest="policy",
            reproduction_gate_digest="gate",
            child_created=True,
        )


def test_world_law_patch_claim_eligible_requires_claim_gate_digest() -> None:
    with pytest.raises(ValueError):
        WorldLawPatch(
            old_digest="old",
            new_digest="new",
            scope="child_only",
            activation_tick_or_world="1",
            reason="test",
            claim_eligible=True,
        )


def test_reproduction_gate_allowed_requires_known_or_deferred_placement_stage() -> None:
    with pytest.raises(ValueError):
        ReproductionGateResult(
            parent_id="p",
            tick=1,
            allowed=True,
            reasons=(),
            parent_alive_before_copy_self=True,
            parent_runtime_atp_before_copy_self=10.0,
            parent_learning_atp_before_copy_self=0.0,
            capacity_available=True,
            copy_self_action_detected=True,
            reproduction_enabled=True,
            min_runtime_atp_met=True,
            parent_cost_payable=True,
            offspring_fraction_valid=True,
            child_placement_available=None,
            placement_gate_evaluated=False,
            placement_resolution_stage="gate",
            placement_policy="adjacent_free",
        )


def test_child_admission_requires_placement_when_admitted() -> None:
    with pytest.raises(ValueError):
        ChildAdmissionResult(child_id="c", admitted=True, placement_cell=None)


def test_learning_inheritance_rejects_lamarckian_without_skill_digest() -> None:
    with pytest.raises(ValueError):
        LearningInheritanceRecord(
            parent_id="p",
            child_id="c",
            tick=1,
            inheritance_policy="lamarckian_compressed_learning",
            learning_capacity_inherited=True,
            learned_content_inherited=True,
            inheritance_type="lamarckian_compressed",
            source_lifetime_evidence_digest="evidence",
            compressed_skill_digest=None,
            child_received_skill_digest="skill",
        )


def test_ai_birth_intervention_record_rejects_applied_with_rejected_reason() -> None:
    with pytest.raises(ValueError):
        AIBirthInterventionRecord(
            intervention_id="i",
            controller_name="controller",
            controller_version="1",
            input_evidence_digest="input",
            decision_digest="decision",
            applied=True,
            rejected_reason="nope",
            scope="child_only",
            event="before_birth_gate",
        )


def test_external_birth_intervention_api_rejects_forbidden_scope() -> None:
    with pytest.raises(ValueError):
        ExternalBirthInterventionAPI(allowed_scopes=("retroactive_hidden_global_change",))


def test_adjacent_free_birth_event_records_final_child_placement() -> None:
    spec = GenesisExperimentSpec(
        genome_bits=("111",),
        seed=333,
        tick_count=1,
        world_width=2,
        world_height=1,
        population_max=4,
        initial_runtime_atp=20.0,
        reproduction_config=ReproductionConfig(
            max_population=4,
            min_runtime_atp=1.0,
            parent_atp_cost=1.0,
            offspring_placement=OffspringPlacementPolicy.ADJACENT_FREE,
        ),
        mutation_config=MutationConfig(bit_flip_rate=0.0),
        engine_config=GenesisEngineConfig(enable_qd=False),
    )
    result = GenesisEngine.from_spec(spec).run_ticks()
    assert result.birth_event_records
    event = result.birth_event_records[0]
    assert event.child_created is True
    assert event.placement_cell == (1, 0)
    assert result.child_admission_records[0].placement_cell == (1, 0)
    assert any(agent.position == (1, 0) for agent in result.snapshot.population.agents)


def test_blocked_child_placement_does_not_count_as_birth() -> None:
    spec = GenesisExperimentSpec(
        genome_bits=("111",),
        seed=334,
        tick_count=1,
        world_width=1,
        world_height=1,
        population_max=4,
        initial_runtime_atp=20.0,
        reproduction_config=ReproductionConfig(
            max_population=4,
            min_runtime_atp=1.0,
            parent_atp_cost=1.0,
            offspring_placement=OffspringPlacementPolicy.ADJACENT_FREE,
        ),
        mutation_config=MutationConfig(bit_flip_rate=0.0),
        engine_config=GenesisEngineConfig(enable_qd=False),
    )
    result = GenesisEngine.from_spec(spec).run_ticks()
    assert result.ticks[0].generation_result.births == 0
    assert result.birth_event_records
    event = result.birth_event_records[0]
    assert event.child_created is False
    assert event.child_id is None
    assert event.child_genome_digest is None
    assert event.blocked_reason == "offspring_no_free_space"
    assert result.child_admission_records[0].admitted is False


def test_build_mutation_plan_rejects_negative_rates() -> None:
    with pytest.raises(ValueError):
        build_mutation_plan(
            plan_id="p",
            parent_genome_digest="g",
            bit_flip_rate=-0.1,
            insertion_rate=0.0,
            deletion_rate=0.0,
            rng_state_digest_before="rng",
        )


def test_qd_single_candidate_records_no_selection_pressure_reason() -> None:
    class Candidate:
        id = "only"

    _selected, audit = select_population(
        (Candidate(),),
        fitness_scores={"only": 1.0},
        novelty_scores={"only": 2.0},
        max_population=1,
        config=EvolutionConfig(
            selection_policy="novelty_weighted",
            max_population=1,
            novelty_weight=1.0,
            fitness_weight=1.0,
            qd_mode="selection_pressure",
        ),
        qd_mode="selection_pressure",
    )
    assert audit.selection_changed_by_qd is False
    assert audit.qd_fallback_reason == "single_candidate_no_selection_pressure"
    assert audit.qd_parent_order_changed is False
    assert audit.qd_survivor_set_changed is False


def test_qd_parent_order_change_is_distinct_from_survivor_set_change() -> None:
    class Candidate:
        def __init__(self, id: str) -> None:
            self.id = id

    candidates = (Candidate("a"), Candidate("b"), Candidate("c"))
    _selected, audit = select_population(
        candidates,
        fitness_scores={"a": 3.0, "b": 2.0, "c": 1.0},
        novelty_scores={"a": 0.0, "b": 4.0, "c": 6.0},
        max_population=3,
        config=EvolutionConfig(
            selection_policy="novelty_weighted",
            max_population=3,
            novelty_weight=1.0,
            fitness_weight=1.0,
            qd_mode="selection_pressure",
        ),
        qd_mode="selection_pressure",
    )
    assert audit.qd_parent_order_changed is True
    assert audit.qd_survivor_set_changed is False
    assert audit.selection_changed_by_qd is True


def test_public_aliases_or_patch_summary_names_are_consistent() -> None:
    result = _birth_result()
    assert result.descriptors == result.behavior_descriptors
    assert result.fitness_breakdowns == result.fitness_breakdown_records
    assert result.role_records == result.role_timeline_records
