"""Claim ladder, protocol status, and run-summary helpers for the GENESIS engine.

Extracted from ``codontrace.engine`` so ClaimGate / protocol / digest helper
logic can be reviewed without the orchestrator. Helpers take engine/result
objects as arguments; they must not soft-pass scientific claims.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import TYPE_CHECKING, Any, cast


from codontrace._types import JsonValue
from codontrace.actions import (
    ActionRegistry,
    default_action_registry,
)
from codontrace.engine_digest import (
    _digest,
    _object_hash,
)
from codontrace.engine_results import GenesisTickResult
from codontrace.genesis.artifacts import (
    ExperimentSummary,
    RawEventSchema,
)
from codontrace.genesis.claim_gate import (
    StrongClaimLadderResult,
    evaluate_strong_claim_ladder,
)
from codontrace.genesis.contribution_ledger import (
    CodonContributionRecord,
    ContributionLedger,
    build_contribution_ledger,
    contribution_from_execution_record,
)
from codontrace.genesis.event_graph import EventGraph
from codontrace.genesis.evidence_validation import EvidenceValidationContext
from codontrace.genesis.population import PopulationState
from codontrace.genesis.quality_diversity import (
    QDArchive,
    summarize_qd_archive,
)
from codontrace.genesis.review import (
    HumanReviewDecision,
    LLMReviewResult,
)
from codontrace.genesis.ribosome import CodonExecutionRecord
from codontrace.genesis.structural_mutation import (
    build_genome_program,
    genome_length_distribution,
)

if TYPE_CHECKING:
    from codontrace.engine_run_result import GenesisRunResult
    from codontrace.engine_runtime import GenesisEngine


def _strong_claim_ladder_records_for_result(
    result: GenesisRunResult,
    *,
    claim_gate_decision_digest: str | None,
) -> tuple[StrongClaimLadderResult, ...]:
    """Build Phase 1 claim ladder records from real result surfaces.

    The ladder record is evidence-derived and cumulative.  It does not promote
    a run with placeholder evidence; missing pilot/control/ablation/multi-seed/
    heldout/intervention layers remain false until actual protocols provide
    those artifacts.
    """

    runtime_surfaces = (
        result.behavior_descriptors,
        result.energy_accounting_records,
        result.action_cost_records,
        result.action_reward_records,
        result.reproduction_attempt_records,
        result.qd_selection_audit,
        result.capsule_adoption_records,
        result.memory_use_records,
        result.tool_chain_records,
        result.engine_frames,
    )
    has_runtime_records = any(bool(surface) for surface in runtime_surfaces)
    has_negative_control = bool(
        result.baseline_comparison_records
        or result.capsule_shuffle_records
    )
    evidence_flags = {
        "schema_version": True,
        "artifact_digest": True,
        "runtime_records": has_runtime_records,
        "pilot_run": False,
        "negative_control": has_negative_control,
        "control_digest": has_negative_control,
        "ablation_result": False,
        "ablation_digest": False,
        "multi_seed_protocol": False,
        "effect_size": False,
        "confidence_interval": False,
        "heldout_protocol": False,
        "leakage_check": False,
        "partner_or_world_shift": bool(result.partner_interaction_records),
        "intervention_result": False,
        "treatment_digest": False,
        "baseline_digest": has_negative_control,
        "replay_verification": bool(result.replay_bundle.digest()),
        "claim_gate_decision_digest": bool(claim_gate_decision_digest),
    }
    return (
        evaluate_strong_claim_ladder(
            "genesis_phase1_core_evidence_claim",
            evidence_flags,
            target_level="claim_ready_research_alpha",
        ),
    )


def _mean_float(values: object) -> float:
    if not isinstance(values, Sequence) or isinstance(values, str | bytes):
        return 0.0
    seq = [float(item) for item in values if isinstance(item, (int, float))]
    return round(sum(seq) / len(seq), 10) if seq else 0.0


def _death_reason_from_record(record: object) -> str:
    alive = getattr(record, "alive_result", None)
    if alive is None:
        return "unknown"
    reasons = tuple(getattr(alive, "reasons", ()))
    final_atp = float(getattr(alive, "final_runtime_atp", 0.0))
    blocked_actions = int(getattr(alive, "blocked_actions", 0))
    if final_atp <= 0:
        return "atp_starvation"
    joined = " ".join(str(item) for item in reasons).lower()
    if "reproduction" in joined:
        return "reproduction_cost"
    if "capsule_emission" in joined:
        return "capsule_emission_cost"
    if "capsule_adoption" in joined:
        return "capsule_adoption_cost"
    if "move" in joined or "movement" in joined:
        return "movement_cost"
    if "hazard" in joined or "damage" in joined:
        return "hazard_damage"
    if "invalid" in joined:
        return "invalid_action"
    if "depletion" in joined or "resource" in joined:
        return "environment_depletion"
    if blocked_actions > 0 and not getattr(alive, "passed", True):
        return "blocked_action_accumulation"
    return "unknown"


def _claim_evidence_flags(
    engine: GenesisEngine,
    contribution_ledgers: Sequence[ContributionLedger],
    semantic_report: object | None,
) -> dict[str, bool]:
    active_qd = engine.qd_archive is not None and bool(engine.spec.engine_config.enable_qd)
    qd_selection_pressure = active_qd and engine.spec.engine_config.qd_mode == "selection_pressure"
    qd_feedback = qd_selection_pressure and engine._qd_parent_feedback_applied
    metadata = engine.spec.metadata
    evidence_context = engine.spec.evidence_validation_context or EvidenceValidationContext()
    intervention_flags = dict(evidence_context.intervention_evidence_flags())
    oee_flags = dict(evidence_context.oee_evidence_flags())
    predictive_flags = evidence_context.predictive_evidence_flags()
    semantic_flags = dict(evidence_context.semantic_proxy_evidence_flags())
    semantic_report_present = semantic_report is not None
    semantic_report_replay_captured = bool(getattr(semantic_report, "replay_captured", False))
    if semantic_report_present or evidence_context.has_semantic_proxy_artifact():
        semantic_flags["semantic_proxy_report"] = True
        semantic_flags["semantic_proxy_report_digest"] = True
    else:
        semantic_flags.setdefault("semantic_proxy_report_digest", False)
    semantic_flags["replay_capture"] = bool(
        semantic_report_replay_captured or semantic_flags.get("replay_capture", False)
    )
    claim_gate_decision_digest_available = bool(
        intervention_flags.pop("claim_gate_decision_digest", False)
        or oee_flags.pop("claim_gate_decision_digest", False)
    )
    custom_handlers_replayable = _action_registry_replayable(engine.spec.action_registry)
    has_runtime_ticks = bool(engine._tick_results)
    return {
        "manifest": True,
        "runtime_effect": has_runtime_ticks,
        "artifact_digest": True,
        "replay_verification": custom_handlers_replayable,
        "replayable_action_handlers": custom_handlers_replayable,
        "fitness_components": True,
        "fitness_config_digest": True,
        "qd_candidate_schema": active_qd,
        "archive_digest": active_qd,
        "qd_ask_tell": active_qd,
        "archive_feedback": qd_feedback,
        "parent_selection_feedback": qd_feedback,
        "parent_selection_feedback_digest": qd_feedback,
        "qd_scheduler_digest": active_qd,
        "qd_mode_selection_pressure": qd_selection_pressure,
        "qd_changed_selection": qd_feedback,
        "benchmark_suite_v2": bool(metadata.get("benchmark_scenario_digest"))
        and metadata.get("scenario_runtime_status") in {"measured", "runtime_effective"}
        and metadata.get("claim_allowed", True) is True
        and metadata.get("behavior_digest_equal_baseline_treatment", False) is not True,
        "execution_source_map": engine.spec.enable_execution_source
        and bool(_execution_records_from_raw_events(_raw_events(engine._tick_results))),
        "genome_program_digest": True,
        "births_positive": any(t.generation_result.births > 0 for t in engine._tick_results),
        "heritable_variation": bool(engine.spec.mutation_config is not None and engine.spec.mutation_config.bit_flip_rate > 0.0),
        "differential_fitness": any(
            t.generation_result.selection_best_fitness > t.generation_result.selection_mean_fitness
            for t in engine._tick_results
        ),
        "structural_mutation_record": bool(engine.spec.structural_mutation_config is not None),
        "adf_macro_expansion": engine.spec.adf_macro_registry is not None,
        "bounded_expansion": engine.spec.adf_macro_registry is not None,
        "source_map": engine.spec.enable_execution_source,
        "contribution_ledger": bool(contribution_ledgers)
        or bool(evidence_context.contribution_ledgers),
        "execution_records": bool(
            _execution_records_from_raw_events(_raw_events(engine._tick_results))
        ),
        "event_graph": True,
        "event_graph_digest": has_runtime_ticks,
        **predictive_flags,
        **intervention_flags,
        # Metadata-only ground-truth/recovery digest strings are artifact pointers,
        # not validated scientific evidence.
        "ground_truth_world": False,
        "recovery_report": False,
        **oee_flags,
        "claim_gate_decision_digest": claim_gate_decision_digest_available,
        "translation_profile": engine.spec.translation_profile is not None,
        **semantic_flags,
        **evidence_context.validated_evidence_flag_map(),
        "translation_safety_gates": _translation_safety_gate_passed(engine),
    }


def _qd_scheduler_manifest_digest(
    engine: GenesisEngine, phase2_hashes: Mapping[str, str | None], rng_state_digest: str
) -> str:
    archive_digest = None if engine.qd_archive is None else engine.qd_archive.digest()
    descriptor_schema_digest = (
        None if engine.qd_archive is None else engine.qd_archive.config.schema.digest()
    )
    parent_feedback_digest = (
        _digest({"parent_selection_feedback": True, "ticks": len(engine._tick_results)})
        if engine._qd_parent_feedback_applied
        else None
    )
    return _digest(
        {
            "archive_digest": archive_digest,
            "descriptor_schema_digest": descriptor_schema_digest,
            "emitter_state_digest": phase2_hashes.get("qd_emitter_state_digest", "default_emitter"),
            "scheduler_generation": len(engine._tick_results),
            "selection_feedback_policy": "archive_parent_feedback"
            if engine._qd_parent_feedback_applied
            else "reporting_only",
            "parent_selection_feedback_digest": parent_feedback_digest,
            "rng_state_digest": rng_state_digest,
        }
    )


def _action_registry_replayable(registry: ActionRegistry | None) -> bool:
    if registry is None:
        return True
    builtins = set(default_action_registry().names())
    return all(name in builtins for name in registry.names())


def _translation_safety_gate_passed(engine: GenesisEngine) -> bool:
    profile = engine.spec.translation_profile
    if profile is None:
        return False
    approved = set(
        engine.spec.action_registry.names()
        if engine.spec.action_registry is not None
        else default_action_registry().names()
    )
    return all(weight.action in approved for weight in profile.weights)


def _protocol_statuses(
    engine: GenesisEngine, phase2_hashes: Mapping[str, str | None]
) -> dict[str, str]:
    evidence_context = engine.spec.evidence_validation_context or EvidenceValidationContext()
    predictive_executed = evidence_context.has_predictive_probe_artifact()
    intervention_executed = (
        evidence_context.has_validated_intervention_result()
        and evidence_context.has_intervention_protocol_artifact()
    )
    intervention_result_status = (
        "supported" if evidence_context.has_validated_intervention_result() else "not_run"
    )
    oee_executed = evidence_context.has_oee_candidate_report()
    translation_executed = (
        evidence_context.has_semantic_proxy_artifact()
        or engine.spec.translation_profile is not None
    )
    # A digest for a disabled/not-configured innovation registry is not a validation protocol.
    innovation_active = False
    validation_executed = evidence_context.scientific_validation_protocol_executed()
    statuses = {
        "predictive_probe_status": "executed" if predictive_executed else "not_run",
        "predictive_probe_executed": str(predictive_executed).lower(),
        "intervention_protocol_status": "executed" if intervention_executed else "not_run",
        "intervention_result_status": intervention_result_status,
        "intervention_protocol_executed": str(intervention_executed).lower(),
        "oee_status": "candidate" if oee_executed else "not_run",
        "oee_protocol_executed": str(oee_executed).lower(),
        "translation_protocol_executed": str(translation_executed).lower(),
        "innovation_protocol_active": str(innovation_active).lower(),
        "scientific_feature_active": str(
            engine.spec.translation_profile is not None or innovation_active
        ).lower(),
        "scientific_validation_protocol_executed": str(validation_executed).lower(),
        "innovation_status": "active" if innovation_active else "not_configured",
        "semantic_proxy_status": "active" if translation_executed else "fixed_translation",
    }
    statuses.update(_phase2_manifest_protocol_statuses(engine, phase2_hashes))
    return statuses


def _phase2_manifest_protocol_statuses(
    engine: GenesisEngine, phase2_hashes: Mapping[str, str | None]
) -> dict[str, str]:
    """Status every Phase 2 manifest field next to its deterministic digest.

    The digest/status pair is the compatibility bridge from Phase 1 manifests
    to Phase 2 evidence. Disabled or not-run capabilities still receive stable
    digests for replay, but their status prevents downstream code from treating
    them as measured scientific evidence.
    """

    evidence_context = engine.spec.evidence_validation_context or EvidenceValidationContext()
    has_ticks = bool(engine._tick_results)
    has_mutation_event = any(
        isinstance(event.world_delta.get("mutation_digest"), str)
        for tick in engine._tick_results
        for trace in tick.generation_result.traces
        for event in trace.events
    )
    has_contribution_ledger = bool(phase2_hashes.get("contribution_ledger_digest")) and (
        bool(getattr(evidence_context, "contribution_ledgers", ()))
        or any(_execution_records_from_raw_events(_raw_events(engine._tick_results)))
    )
    benchmark_runtime = (
        "benchmark_scenario_digest" in engine.spec.metadata
        and engine.spec.metadata.get("scenario_runtime_status") in {"measured", "runtime_effective"}
    )
    statuses = {name: "not_run" for name in phase2_hashes}
    for name in ("genome_program_digest",):
        statuses[name] = "measured"
    for name in ("structural_mutation_digest", "structural_mutation_record_digest"):
        statuses[name] = "measured" if has_mutation_event else "not_observed"
    for name in ("adf_macro_registry_digest", "macro_registry_digest"):
        statuses[name] = "measured" if engine.spec.adf_macro_registry is not None else "disabled_by_config"
    for name in ("adf_usefulness_report_digest", "macro_utility_digest"):
        statuses[name] = "provisional" if engine.spec.adf_macro_registry is not None else "not_run"
    for name in ("translation_profile_digest", "translation_profile_hash"):
        statuses[name] = "measured" if engine.spec.translation_profile is not None else "fixed_default"
    statuses["contribution_ledger_digest"] = "measured" if has_contribution_ledger else "not_observed"
    statuses["micro_ablation_attribution_digest"] = "not_run"
    statuses["innovation_registry_digest"] = "not_configured"
    statuses["event_graph_digest"] = "measured" if has_ticks else "empty_but_available"
    statuses["predictive_probe_digest"] = (
        "measured" if evidence_context.has_predictive_probe_artifact() else "not_run"
    )
    intervention_status = (
        "measured"
        if evidence_context.has_validated_intervention_result()
        and evidence_context.has_intervention_protocol_artifact()
        else "not_run"
    )
    for name in (
        "intervention_protocol_digest",
        "intervention_result_digest",
        "causal_intervention_result_digest",
    ):
        statuses[name] = intervention_status
    statuses["discovery_witness_digest"] = "not_run"
    statuses["benchmark_scenario_digest"] = "measured" if benchmark_runtime else "not_configured"
    statuses["statistical_report_digest"] = "provisional" if has_ticks else "empty_but_available"
    statuses["oee_report_digest"] = "not_run"
    statuses["social_generalization_digest"] = "not_run"
    config_status_map = {
        "capsule_ablation_policy_digest": engine.spec.capsule_ablation_policy,
        "capsule_outcome_window_digest": engine.spec.capsule_outcome_window,
        "skill_compression_ablation_policy_digest": engine.spec.skill_compression_ablation_policy,
        "role_mechanics_policy_digest": engine.spec.role_mechanics_policy,
        "territory_mechanics_config_digest": engine.spec.territory_mechanics_config,
        "heldout_partner_protocol_digest": engine.spec.heldout_partner_protocol,
        "source_reputation_memory_digest": engine.spec.source_reputation_memory,
        "collective_task_graph_digest": engine.spec.collective_task_graph,
        "role_ablation_protocol_digest": engine.spec.role_ablation_protocol,
        "multi_agent_contribution_ledger_digest": engine.spec.multi_agent_contribution_ledger,
        "counterfactual_replay_protocol_digest": engine.spec.counterfactual_replay_protocol,
        "oee_extended_metrics_digest": engine.spec.oee_extended_metrics,
    }
    for name, configured_value in config_status_map.items():
        statuses[name] = "configured_digest_only" if configured_value is not None else "disabled_by_config"
    if engine.spec.oee_extended_metrics is not None and engine.spec.oee_extended_metrics.claim_eligible:
        statuses["oee_extended_metrics_digest"] = "candidate_evidence"
    if evidence_context.has_semantic_proxy_artifact() or engine.spec.translation_profile is not None:
        statuses["semantic_proxy_report_digest"] = "measured"
    else:
        statuses["semantic_proxy_report_digest"] = "fixed_default"
    statuses["phase2_claim_decision_digest"] = "measured"
    statuses["claim_gate_decision_digest"] = "measured"
    out = {f"phase2.{name}.status": status for name, status in sorted(statuses.items())}
    for name, status in sorted(statuses.items()):
        if status == "provisional":
            out[f"phase2.{name}.status_reason"] = "deterministic_digest_present_but_control_or_runtime_protocol_incomplete"
    return out


def _scientific_protocol_executed(
    engine: GenesisEngine, phase2_hashes: Mapping[str, str | None]
) -> bool:
    statuses = _protocol_statuses(engine, phase2_hashes)
    return statuses.get("scientific_validation_protocol_executed") == "true"


def _execution_records_from_raw_events(
    raw_events: Sequence[RawEventSchema],
) -> tuple[dict[str, JsonValue], ...]:
    records: list[dict[str, JsonValue]] = []
    for raw in raw_events:
        delta = raw.payload.get("world_delta")
        if isinstance(delta, Mapping):
            rec = delta.get("codon_execution_record")
            if isinstance(rec, Mapping):
                records.append(dict(rec))
            many = delta.get("codon_execution_records")
            if isinstance(many, list):
                records.extend(dict(item) for item in many if isinstance(item, Mapping))
    return tuple(records)


def _execution_source_digest(raw_events: Sequence[RawEventSchema], *, enabled: bool) -> str:
    records = _execution_records_from_raw_events(raw_events)
    return _digest(
        {
            "enable_execution_source": enabled,
            "record_count": len(records),
            "records": cast(JsonValue, records),
        }
    )


def attach_review_result(result: GenesisRunResult, review: LLMReviewResult) -> GenesisRunResult:
    """Return an immutable copy of a run result with review status attached."""

    return result.with_review_result(review)


def apply_human_review(result: GenesisRunResult, decision: HumanReviewDecision) -> GenesisRunResult:
    """Return an immutable copy of a run result with human review status attached."""

    return result.with_human_review(decision)


def _summarize_run(
    run_id: str,
    ticks: Sequence[GenesisTickResult],
    population: PopulationState,
    qd_archive: QDArchive | None,
) -> ExperimentSummary:
    last = ticks[-1].generation_result if ticks else None
    qd_summary = summarize_qd_archive(qd_archive) if qd_archive is not None else None
    return ExperimentSummary(
        run_id=run_id,
        ticks=len(ticks),
        generations=population.generation,
        final_population=len(population.organisms),
        best_fitness=0.0 if last is None else last.best_fitness,
        mean_fitness=0.0 if last is None else last.mean_fitness,
        raw_best_fitness=None if last is None else last.raw_best_fitness,
        raw_mean_fitness=None if last is None else last.raw_mean_fitness,
        selection_best_fitness=None if last is None else last.selection_best_fitness,
        selection_mean_fitness=None if last is None else last.selection_mean_fitness,
        viable_best_fitness=None if last is None else last.viable_best_fitness,
        viable_mean_fitness=None if last is None else last.viable_mean_fitness,
        viability_gate_failures=0 if last is None else last.viability_gate_failures,
        causal_updates=sum(
            item.generation_result.causal_summary.update_successes for item in ticks
        ),
        capsules_emitted=sum(
            item.generation_result.causal_summary.capsules_emitted for item in ticks
        ),
        capsules_adopted=sum(
            item.generation_result.causal_summary.capsules_adopted for item in ticks
        ),
        qd_filled_bins=0 if qd_summary is None else qd_summary.filled_bins,
    )


def _raw_events(ticks: Sequence[GenesisTickResult]) -> tuple[RawEventSchema, ...]:
    events: list[RawEventSchema] = []
    for tick in ticks:
        for trace in tick.generation_result.traces:
            for event in trace.events:
                payload = event.to_dict()
                events.append(RawEventSchema(len(events), _digest(payload), payload))
    return tuple(events)


def _contribution_ledgers_from_raw_events(
    raw_events: Sequence[RawEventSchema],
    generation: int,
) -> tuple[ContributionLedger, ...]:
    """Build contribution ledgers from real CodonExecutionRecord payloads."""

    grouped: dict[str, list[CodonContributionRecord]] = {}
    for raw in raw_events:
        delta = raw.payload.get("world_delta")
        if not isinstance(delta, Mapping):
            continue
        record_raw = delta.get("codon_execution_record")
        if not isinstance(record_raw, Mapping):
            continue
        try:
            execution = CodonExecutionRecord.from_dict(dict(record_raw))
        except Exception:
            continue
        contribution = contribution_from_execution_record(execution, generation=generation)
        grouped.setdefault(execution.organism_id, []).append(contribution)
    return tuple(
        build_contribution_ledger(organism_id, generation, tuple(records))
        for organism_id, records in sorted(grouped.items())
    )


def _event_graph_digest_from_ticks(ticks: Sequence[GenesisTickResult]) -> str:
    graph = EventGraph()
    previous: str | None = None
    for raw in _raw_events(ticks):
        action = str(raw.payload.get("action", "unknown"))
        if previous is not None:
            graph = graph.add_edge(previous, action, lag=1, evidence_count=1)
        previous = action
    return graph.digest()


def _phase2_hashes(
    *,
    engine: GenesisEngine,
    contribution_ledgers: Sequence[ContributionLedger],
    semantic_report_digest: str | None,
) -> dict[str, str | None]:
    organisms = tuple(engine.runner.population.organisms)
    ribosome = engine.spec.resolved_ribosome()
    codon_width = ribosome.codon_table.spec.genome_spec.codon_width
    genome_program_payload = []
    for organism in organisms:
        program = build_genome_program(
            organism.genome.to_compact(),
            codon_width=codon_width,
            macro_registry_digest=None
            if organism.adf_macro_registry is None
            else organism.adf_macro_registry.digest(),
            lineage_tags=(organism.id,),
        )
        genome_program_payload.append(program.to_dict())
    mutation_digests = []
    for tick in engine._tick_results:
        for trace in tick.generation_result.traces:
            for event in trace.events:
                digest = event.world_delta.get("mutation_digest")
                if isinstance(digest, str):
                    mutation_digests.append(digest)
    macro_registry_digest = (
        engine.spec.adf_macro_registry.digest()
        if engine.spec.adf_macro_registry is not None
        else _digest({"macro_registry": "not_enabled"})
    )
    macro_utility_digest = _digest(
        {"macro_registry_digest": macro_registry_digest, "status": "runtime_registry"}
    )
    structural_mutation_digest = (
        _digest({"mutation_digests": cast(JsonValue, sorted(mutation_digests))})
        if mutation_digests
        else _digest({"structural_mutation": "not_observed"})
    )
    contribution_digest = _digest(
        {"ledgers": cast(JsonValue, [ledger.digest for ledger in contribution_ledgers])}
    )
    innovation_digest = _digest(
        {
            "innovation_registry": "not_configured",
            "population_generation": engine.runner.population.generation,
        }
    )
    translation_digest = (
        engine.spec.translation_profile.digest
        if engine.spec.translation_profile is not None
        else _digest({"translation_profile": "fixed_base_table"})
    )
    statistical_digest = _digest(
        {"tick_count": len(engine._tick_results), "population_size": len(organisms)}
    )
    oee_digest = _digest(
        {
            "oee": "measurement_not_run",
            "genome_length_distribution": genome_length_distribution(
                tuple(
                    build_genome_program(o.genome.to_compact(), codon_width=codon_width)
                    for o in organisms
                )
            ),
        }
    )
    return {
        "genome_program_digest": _digest(
            {"genome_programs": cast(JsonValue, genome_program_payload)}
        ),
        "structural_mutation_digest": structural_mutation_digest,
        "structural_mutation_record_digest": structural_mutation_digest,
        "adf_macro_registry_digest": macro_registry_digest,
        "macro_registry_digest": macro_registry_digest,
        "adf_usefulness_report_digest": macro_utility_digest,
        "macro_utility_digest": macro_utility_digest,
        "translation_profile_digest": translation_digest,
        "translation_profile_hash": translation_digest,
        "contribution_ledger_digest": contribution_digest,
        "micro_ablation_attribution_digest": _digest({"micro_ablation": "not_run", "ledger_digest": contribution_digest}),
        "innovation_registry_digest": innovation_digest,
        "event_graph_digest": _event_graph_digest_from_ticks(engine._tick_results),
        "predictive_probe_digest": _digest({"predictive_probe": "not_run"}),
        "intervention_protocol_digest": _digest({"intervention_protocol": "not_run"}),
        "intervention_result_digest": _digest({"intervention_result": "not_run"}),
        "causal_intervention_result_digest": _digest({"intervention_result": "not_run"}),
        "discovery_witness_digest": _digest({"discovery_witness": "not_run", "tick_count": len(engine._tick_results)}),
        "benchmark_scenario_digest": str(engine.spec.metadata.get("benchmark_scenario_digest"))
        if "benchmark_scenario_digest" in engine.spec.metadata
        else _digest({"benchmark_scenario": "not_configured"}),
        "statistical_report_digest": statistical_digest,
        "oee_report_digest": oee_digest,
        "social_generalization_digest": _digest({"social_generalization": "not_run", "population_size": len(organisms)}),
        "capsule_ablation_policy_digest": _object_hash(engine.spec.capsule_ablation_policy)
        or _digest({"capsule_ablation_policy": "disabled_by_config"}),
        "capsule_outcome_window_digest": _object_hash(engine.spec.capsule_outcome_window)
        or _digest({"capsule_outcome_window": "disabled_by_config"}),
        "skill_compression_ablation_policy_digest": _object_hash(engine.spec.skill_compression_ablation_policy)
        or _digest({"skill_compression_ablation_policy": "disabled_by_config"}),
        "role_mechanics_policy_digest": _object_hash(engine.spec.role_mechanics_policy)
        or _digest({"role_mechanics_policy": "disabled_by_config"}),
        "territory_mechanics_config_digest": _object_hash(engine.spec.territory_mechanics_config)
        or _digest({"territory_mechanics_config": "disabled_by_config"}),
        "heldout_partner_protocol_digest": _object_hash(engine.spec.heldout_partner_protocol)
        or _digest({"heldout_partner_protocol": "disabled_by_config"}),
        "source_reputation_memory_digest": _object_hash(engine.spec.source_reputation_memory)
        or _digest({"source_reputation_memory": "disabled_by_config"}),
        "collective_task_graph_digest": _object_hash(engine.spec.collective_task_graph)
        or _digest({"collective_task_graph": "disabled_by_config"}),
        "role_ablation_protocol_digest": _object_hash(engine.spec.role_ablation_protocol)
        or _digest({"role_ablation_protocol": "disabled_by_config"}),
        "multi_agent_contribution_ledger_digest": _object_hash(engine.spec.multi_agent_contribution_ledger)
        or _digest({"multi_agent_contribution_ledger": "disabled_by_config"}),
        "counterfactual_replay_protocol_digest": _object_hash(engine.spec.counterfactual_replay_protocol)
        or _digest({"counterfactual_replay_protocol": "disabled_by_config"}),
        "oee_extended_metrics_digest": _object_hash(engine.spec.oee_extended_metrics)
        or _digest({"oee_extended_metrics": "disabled_by_config"}),
        "semantic_proxy_report_digest": semantic_report_digest
        or _digest({"semantic_proxy": "fixed_translation"}),
    }


__all__ = [
    "attach_review_result",
    "apply_human_review",
    "_execution_source_digest",
    "_phase2_hashes",
    "_mean_float",
    "_raw_events",
    "_summarize_run",
    "_claim_evidence_flags",
    "_protocol_statuses",
    "_strong_claim_ladder_records_for_result",
]
