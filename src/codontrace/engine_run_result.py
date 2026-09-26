"""GenesisRunResult — heavy evidence / maturity / export surface.

Extracted from ``codontrace.engine`` so the result type can be debugged
without loading the full orchestrator blob. Replay digests must stay
byte-stable. See ``docs/ENGINE_REPLAY_CONTRACT.md``.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field, replace
from typing import Any, cast


from codontrace._types import JsonValue
from codontrace.codon import CodonTable
from codontrace.engine_digest import (
    _action_registry_hash,
    _digest,
    _digest_sequence,
    _json_str_tuple,
    _jsonish_for_digest,
    _stable_default_action_registry_hash,
)
from codontrace.engine_results import (
    ConsistencyValidationResult,
    GenesisRun,
    GenesisRunSummary,
    GenesisSnapshot,
    GenesisTickResult,
)
from codontrace.genesis.api_audit import (
    ActionWiringMatrix,
    export_action_wiring_matrix,
)
from codontrace.genesis.artifacts import (
    ReplayBundle,
    ReviewStatus,
    RunArtifactSchema,
    RunManifest,
)
from codontrace.genesis.birth import (
    ADFInheritanceRecord,
    AIBirthInterventionRecord,
    BirthEvent,
    ChildAdmissionResult,
    ChildGenomeResult,
    LearningInheritanceRecord,
    MutationAuditResult,
    MutationPlan,
    SkillCompressionRecord,
)
from codontrace.genesis.claim_gate import StrongClaimLadderResult
from codontrace.genesis.diagnostics import (
    ActionCostRecord,
    ActionPreconditionRecord,
    ActionRewardRecord,
    BaselineComparisonRecord,
    CapsuleCostRecord,
    CapsuleUtilityRecord,
    DeathReasonRecord,
    DigestInstabilityReason,
    EnergyAccountingRecord,
    EngineDigestAuditRecord,
    ExportEnvelope,
    FeatureStatus,
    InventoryState,
    LineageGrowthRecord,
    OutputCompletenessRecord,
    PostCapsuleBehaviorRecord,
    ReproductionAttemptRecord,
    ReproductionGateRecord,
    SurvivalBaselineRecord,
)
from codontrace.genesis.evidence import EvidenceManifest
from codontrace.genesis.frames import (
    EngineFrame,
    engine_frame_from_generation,
)
from codontrace.genesis.memory import (
    DelayedRewardTrace,
    MemoryUseEvidence,
)
from codontrace.genesis.quality_diversity import QDArchiveSummary
from codontrace.genesis.review import (
    ExternalReviewRecord,
    HumanReviewDecision,
    LLMReviewResult,
)
from codontrace.genesis.role import (
    RoleAssignment,
    RoleContribution,
    infer_role_from_record,
)


@dataclass(frozen=True, slots=True)
class GenesisRunResult:
    """Result returned by GenesisEngine.run_ticks."""

    run: GenesisRun
    ticks: tuple[GenesisTickResult, ...]
    manifest: RunManifest
    snapshot: GenesisSnapshot
    evidence_pack: RunArtifactSchema
    replay_bundle: ReplayBundle
    action_wiring_matrix: ActionWiringMatrix = field(
        default_factory=lambda: export_action_wiring_matrix(
            codon_table=CodonTable.genesis_v0(),
            profile_name="legacy_result_default",
        )
    )
    strong_claim_ladder_records: tuple[StrongClaimLadderResult, ...] = field(default_factory=tuple)
    external_review_record: ExternalReviewRecord | None = None

    def summary(self) -> GenesisRunSummary:
        return GenesisRunSummary(
            experiment=self.evidence_pack.summary,
            tick_digests=tuple(item.digest() for item in self.ticks),
            manifest_digest=self.manifest.digest(),
        )

    def _core_payload(self) -> dict[str, JsonValue]:
        return {
            "run": self.run.to_dict(),
            "ticks": [item.to_dict() for item in self.ticks],
            "manifest": self.manifest.to_dict(),
            "snapshot": self.snapshot.to_dict(),
            "evidence_pack": self.evidence_pack.to_dict(),
            "replay_bundle": self.replay_bundle.to_dict(),
            "action_wiring_matrix": self.action_wiring_matrix.to_dict(),
            "strong_claim_ladder_records": [item.to_dict() for item in self.strong_claim_ladder_records],
            "external_review_record": None
            if self.external_review_record is None
            else self.external_review_record.to_dict(),
        }

    def to_dict(self) -> dict[str, JsonValue]:
        payload = self._core_payload()
        phase1_report = self.phase1_runtime_maturity_report
        phase_b_report = self.phase_b_scientific_maturity_report
        payload.update(
            {
                "export_status_records": [item.to_dict() for item in self.export_status_records],
                "output_completeness_records": [item.to_dict() for item in self.output_completeness_records],
                "phase1_runtime_maturity_report": phase1_report.to_dict(),
                "phase1_runtime_maturity_matrix": [item.to_dict() for item in phase1_report.feature_statuses],
                "phase_b_scientific_maturity_report": phase_b_report.to_dict(),
                "phase_b_scientific_maturity_matrix": [item.to_dict() for item in phase_b_report.feature_statuses],
                "evidence_manifest": self.evidence_manifest.to_dict(),
            }
        )
        return payload

    def digest(self) -> str:
        return _digest(self.to_dict())

    def validate_consistency(self, strict: bool = True) -> ConsistencyValidationResult:
        """Validate internal evidence wiring without re-running the simulation.

        The check is intentionally conservative: it verifies digest/status
        consistency, social descriptor counts, run-specific action wiring, and
        Phase 2 measured/provisional hash rules.
        """

        from codontrace.genesis.artifacts import validate_phase2_manifest_fields
        from codontrace.genesis.canonical import reject_nan_inf_payload

        issues: list[str] = []
        if self.manifest.claim_gate_decision_digest:
            for key in ("claim_gate_decision_digest", "phase2_claim_decision_digest"):
                if self.manifest.runtime_hashes.get(key) != self.manifest.claim_gate_decision_digest:
                    issues.append(f"manifest_{key}_mismatch")
        validation = validate_phase2_manifest_fields(self.manifest)
        if not validation.passed:
            issues.extend(f"phase2_manifest_missing:{item}" for item in validation.missing_hashes)
            issues.extend(f"phase2_manifest_placeholder:{item}" for item in validation.placeholder_hashes)
        total_social = len(self.social_interaction_records)
        total_partner = len(self.partner_interaction_records)
        descriptor_social = sum(int(getattr(item, "social_interaction_count", 0)) for item in self.behavior_descriptors)
        descriptor_partner = sum(int(getattr(item, "partner_interaction_count", 0)) for item in self.behavior_descriptors)
        if total_social and descriptor_social <= 0:
            issues.append("social_descriptor_counts_do_not_match_records")
        if total_partner and descriptor_partner <= 0:
            issues.append("partner_descriptor_counts_do_not_match_records")
        if self.action_wiring_matrix.profile_name == "legacy_result_default":
            issues.append("action_wiring_matrix_not_run_specific")
        for row in self.action_wiring_matrix.records:
            if getattr(row, "effect_source", "contract") == "contract" and getattr(row, "runtime_validated", False):
                issues.append("contract_action_wiring_marked_runtime_validated")
                break
        try:
            reject_nan_inf_payload(self.to_dict())
        except Exception as exc:
            issues.append(f"non_finite_or_noncanonical_result_payload:{type(exc).__name__}")
        if not strict:
            issues = [item for item in issues if not item.startswith("phase2_manifest_missing:")]
        return ConsistencyValidationResult(not issues, tuple(sorted(set(issues))))

    @property
    def phase1_runtime_maturity_report(self) -> object:
        """Digest-backed Phase-1 runtime maturity report derived from this run.

        The report is computed from already-executed runtime records. It does
        not alter the run, does not make claims by itself, and keeps ClaimGate
        as the central authority for claim decisions.
        """

        from codontrace.genesis.phase1_runtime_maturity import (
            build_phase1_runtime_maturity_report,
        )

        return build_phase1_runtime_maturity_report(self)

    @property
    def phase1_runtime_maturity_matrix(self) -> tuple[dict[str, JsonValue], ...]:
        """Public matrix for Phase-1 feature wiring/status review."""

        report = self.phase1_runtime_maturity_report
        return tuple(item.to_dict() for item in report.feature_statuses)

    @property
    def phase_b_scientific_maturity_report(self) -> object:
        """Final Phase-B scientific-evidence report derived from executed runtime records.

        This consumes Phase-A evidence and downgrades unsupported claims instead
        of manufacturing discovery/generalization/swarm/OEE success.
        """

        from codontrace.genesis.phase_b_scientific_maturity import (
            build_phase_b_scientific_maturity_report,
        )

        return build_phase_b_scientific_maturity_report(self)

    @property
    def phase_b_scientific_maturity_matrix(self) -> tuple[dict[str, JsonValue], ...]:
        report = self.phase_b_scientific_maturity_report
        return tuple(item.to_dict() for item in report.feature_statuses)

    @property
    def behavior_descriptors(self) -> tuple[object, ...]:
        return tuple(
            record.behavior_descriptor
            for tick in self.ticks
            for record in tick.generation_result.organism_records
            if record.behavior_descriptor is not None
        )

    @property
    def descriptors(self) -> tuple[object, ...]:
        """Backward-compatible alias for behavior_descriptors."""

        return self.behavior_descriptors

    @property
    def qd_selection_audit(self) -> tuple[object, ...]:
        return tuple(
            tick.generation_result.selection_result
            for tick in self.ticks
            if tick.generation_result.selection_result is not None
        )

    @property
    def capsule_adoption_records(self) -> tuple[object, ...]:
        return tuple(
            item
            for tick in self.ticks
            for record in tick.generation_result.organism_records
            for item in record.capsule_adoption_records
        )

    @property
    def capsule_shuffle_records(self) -> tuple[object, ...]:
        return tuple(
            item
            for tick in self.ticks
            for record in tick.generation_result.organism_records
            for item in record.capsule_shuffle_records
        )

    @property
    def fitness_breakdown_records(self) -> tuple[object, ...]:
        return tuple(
            record.fitness_breakdown or record.fitness_result.fitness_breakdown
            for tick in self.ticks
            for record in tick.generation_result.organism_records
            if (record.fitness_breakdown or record.fitness_result.fitness_breakdown) is not None
        )

    @property
    def fitness_breakdowns(self) -> tuple[object, ...]:
        """Backward-compatible alias for fitness_breakdown_records."""

        return self.fitness_breakdown_records

    @property
    def qd_parent_feedback_audit(self) -> tuple[object, ...]:
        return tuple(
            record
            for record in self.qd_selection_audit
            if getattr(record, "policy_name", "") == "novelty_weighted"
        )

    @property
    def qd_archive_summary(self) -> QDArchiveSummary:
        summaries = [tick.qd_update.summary for tick in self.ticks if tick.qd_update is not None]
        if summaries:
            latest = summaries[-1]
            return replace(
                latest,
                mode=(
                    getattr(self.qd_selection_audit[0], "qd_mode", latest.mode)
                    if self.qd_selection_audit
                    else latest.mode
                ),
                archive_type=("map_elites_grid" if latest.total_bins > 0 else "descriptor_set"),
                coverage_status=("measured" if latest.total_bins > 0 else "not_applicable_no_grid"),
            )
        return QDArchiveSummary(
            archive_digest=self.snapshot.qd_archive_digest or "",
            filled_bins=0,
            coverage=0.0,
            best_fitness=None,
            mean_fitness=None,
            qd_score=0.0,
            total_bins=0,
            archive_id="engine_result_qd_archive",
            mode=(
                getattr(self.qd_selection_audit[0], "qd_mode", "archive_only")
                if self.qd_selection_audit
                else "archive_only"
            ),
            archive_type="descriptor_set",
            coverage_status="not_applicable_no_grid",
        )

    @property
    def capsule_source_fitness_records(self) -> tuple[dict[str, JsonValue], ...]:
        rows: list[dict[str, JsonValue]] = []
        for record in self.capsule_adoption_records:
            rows.append(
                {
                    "schema_version": "capsule_source_fitness_v1",
                    "capsule_id": getattr(record, "capsule_id", ""),
                    "source_organism_id": getattr(record, "source_organism_id", ""),
                    "source_fitness": getattr(record, "source_fitness", 0.0),
                    "source_fitness_status": getattr(
                        getattr(record, "source_fitness_status", "unavailable"),
                        "value",
                        str(getattr(record, "source_fitness_status", "unavailable")),
                    ),
                    "source_fitness_unavailable_is_not_zero": getattr(
                        getattr(record, "source_fitness_status", ""),
                        "value",
                        str(getattr(record, "source_fitness_status", "")),
                    )
                    == "unavailable",
                    "source_fitness_numeric_for_threshold": None
                    if getattr(
                        getattr(record, "source_fitness_status", ""),
                        "value",
                        str(getattr(record, "source_fitness_status", "")),
                    )
                    == "unavailable"
                    else getattr(record, "source_fitness", 0.0),
                }
            )
        return tuple(rows)

    @property
    def selection_fitness_records(self) -> tuple[object, ...]:
        return tuple(
            record.selection_fitness_score or record.fitness_result.selection_fitness_score
            for tick in self.ticks
            for record in tick.generation_result.organism_records
            if (record.selection_fitness_score or record.fitness_result.selection_fitness_score)
            is not None
        )

    @property
    def _all_death_classification_records(self) -> tuple[object, ...]:
        return tuple(
            record.death_classification
            for tick in self.ticks
            for record in tick.generation_result.organism_records
            if record.death_classification is not None
        )

    @property
    def _death_monitoring_disabled(self) -> bool:
        classifications = self._all_death_classification_records
        return bool(classifications) and all(
            not bool(getattr(item, "death_monitoring_enabled", True))
            for item in classifications
        )

    @property
    def _death_record_emission_suppressed(self) -> bool:
        classifications = self._all_death_classification_records
        return bool(classifications) and all(
            bool(getattr(item, "death_monitoring_enabled", True))
            and not bool(getattr(item, "emit_record", True))
            for item in classifications
        )

    @property
    def energy_accounting_records(self) -> tuple[EnergyAccountingRecord, ...]:
        rows: list[EnergyAccountingRecord] = []
        for tick in self.ticks:
            classification_by_id = {
                record.organism_id: record.death_classification
                for record in tick.generation_result.organism_records
                if record.death_classification is not None
            }
            last_event_key_by_agent: dict[str, tuple[int, int]] = {}
            for trace_index, trace in enumerate(tick.generation_result.traces):
                for event_index, event in enumerate(trace.events):
                    last_event_key_by_agent[event.agent_id] = (trace_index, event_index)
            for trace_index, trace in enumerate(tick.generation_result.traces):
                for event_index, event in enumerate(trace.events):
                    energy_delta = round(event.atp_after - event.atp_before, 10)
                    classification = classification_by_id.get(event.agent_id)
                    link_enabled = bool(
                        classification is not None
                        and getattr(classification, "death_monitoring_enabled", True)
                        and getattr(classification, "emit_energy_link", True)
                    )
                    actual_death = bool(
                        link_enabled and classification.actual_death_removed_from_population
                    )
                    last_for_agent = last_event_key_by_agent.get(event.agent_id) == (
                        trace_index,
                        event_index,
                    )
                    event_caused_death = bool(actual_death and last_for_agent)
                    attribution = (
                        "event_level"
                        if event_caused_death and event.atp_after <= 0.0
                        else (
                            classification.death_attribution_level
                            if (
                                classification is not None
                                and link_enabled
                                and (
                                    actual_death
                                    or classification.death_risk_event
                                    or classification.alive_gate_failed
                                )
                            )
                            else "not_applicable"
                        )
                    )
                    reason = None
                    if link_enabled and classification is not None:
                        capacity_reasons = {
                            "max_population_reached",
                            "population_capacity_reached",
                            "offspring_no_free_space",
                        }
                        reason = (
                            classification.removal_reason
                            if classification.actual_death_removed_from_population
                            else (
                                "capacity_block_nonfatal"
                                if classification.death_risk_event
                                and any(
                                    item in capacity_reasons
                                    for item in classification.blocked_action_reasons
                                )
                                else (
                                    "alive_gate_failure_nonfatal"
                                    if classification.death_risk_event
                                    else None
                                )
                            )
                        )
                    rows.append(
                        EnergyAccountingRecord(
                            organism_id=event.agent_id,
                            tick=tick.index,
                            engine_tick=tick.index,
                            population_tick=getattr(classification, "population_tick", None)
                            if classification is not None
                            else None,
                            event_step=event.step,
                            action=event.action,
                            runtime_atp_before=event.atp_before,
                            runtime_atp_after=event.atp_after,
                            action_cost=round(max(0.0, -energy_delta), 10),
                            action_reward=round(max(0.0, energy_delta), 10),
                            blocked=event.status == "blocked",
                            blocked_reason=event.reason if event.status == "blocked" else None,
                            death_event=event_caused_death,
                            death_reason=reason,
                            fitness_delta=None,
                            fitness_delta_status="not_measured",
                            fitness_delta_source=None,
                            energy_delta=energy_delta,
                            organism_dead_after_generation=actual_death,
                            death_causing_event=event_caused_death,
                            death_attribution_level=attribution,
                            actual_death_removed_from_population=actual_death,
                            alive_gate_failed_after_generation=bool(
                                link_enabled
                                and classification is not None
                                and classification.alive_gate_failed
                            ),
                            death_risk_after_generation=bool(
                                link_enabled
                                and classification is not None
                                and classification.death_risk_event
                            ),
                            selected_out_by_evolution=False,
                            death_policy_digest=None
                            if not link_enabled or classification is None
                            else classification.death_policy_digest,
                        )
                    )
        return tuple(sorted(rows, key=lambda item: (item.tick, item.organism_id, item.action)))

    @property
    def death_classification_records(self) -> tuple[object, ...]:
        rows: list[object] = []
        for tick in self.ticks:
            for record in tick.generation_result.organism_records:
                classification = record.death_classification
                if classification is None:
                    continue
                if not bool(getattr(classification, "emit_record", True)):
                    continue
                if not bool(getattr(classification, "death_monitoring_enabled", True)):
                    continue
                rows.append(
                    replace(
                        classification,
                        tick=tick.index,
                        engine_tick=tick.index,
                        population_tick=getattr(classification, "population_tick", None)
                        if getattr(classification, "population_tick", None) is not None
                        else getattr(classification, "tick", tick.index),
                    )
                )
        return tuple(rows)

    @property
    def death_reason_records(self) -> tuple[DeathReasonRecord, ...]:
        rows: list[DeathReasonRecord] = []
        for tick in self.ticks:
            for record in tick.generation_result.organism_records:
                classification = record.death_classification
                if classification is None:
                    continue
                if not bool(getattr(classification, "death_monitoring_enabled", True)):
                    continue
                if not bool(getattr(classification, "emit_record", True)):
                    continue
                actual_death = classification.actual_death_removed_from_population
                alive_failed = classification.alive_gate_failed
                risk = classification.death_risk_event
                fatal = classification.fatal_policy_matched
                fatal_reason = classification.fatal_policy_reason
                policy_digest = classification.death_policy_digest
                attribution = classification.death_attribution_level
                runtime_before = classification.runtime_atp_before
                capacity_reasons = {
                    "max_population_reached",
                    "population_capacity_reached",
                    "offspring_no_free_space",
                }
                reason = (
                    classification.removal_reason
                    if actual_death
                    else (
                        "capacity_block_nonfatal"
                        if risk
                        and any(item in capacity_reasons for item in classification.blocked_action_reasons)
                        else ("alive_gate_failure_nonfatal" if risk else "not_applicable")
                    )
                )
                rows.append(
                    DeathReasonRecord(
                        organism_id=record.organism_id,
                        tick=tick.index,
                        engine_tick=tick.index,
                        population_tick=getattr(classification, "population_tick", None)
                        if getattr(classification, "population_tick", None) is not None
                        else classification.tick,
                        event_step=None,
                        death_event=actual_death,
                        death_reason=reason or "not_applicable",
                        alive_gate_reasons=record.alive_result.reasons,
                        runtime_atp_before=runtime_before,
                        runtime_atp_after=record.runtime_atp_after,
                        blocked_actions=record.alive_result.blocked_actions,
                        actual_death_removed_from_population=actual_death,
                        alive_gate_failure_event=alive_failed,
                        death_risk_event=risk,
                        death_causing_event=actual_death,
                        death_attribution_level=attribution,
                        fatal_policy_matched=fatal,
                        fatal_policy_reason=fatal_reason,
                        death_policy_digest=policy_digest,
                    )
                )
        return tuple(rows)

    @property
    def action_cost_records(self) -> tuple[ActionCostRecord, ...]:
        return tuple(
            ActionCostRecord(
                organism_id=item.organism_id,
                tick=item.tick,
                action=item.action,
                action_cost=item.action_cost,
                blocked=item.blocked,
                blocked_reason=item.blocked_reason,
            )
            for item in self.energy_accounting_records
        )

    @property
    def action_reward_records(self) -> tuple[ActionRewardRecord, ...]:
        return tuple(
            ActionRewardRecord(
                organism_id=item.organism_id,
                tick=item.tick,
                action=item.action,
                action_reward=item.action_reward,
                reward_reason="runtime_atp_delta_positive"
                if item.action_reward > 0
                else "no_positive_reward",
            )
            for item in self.energy_accounting_records
        )

    @property
    def survival_baseline_records(self) -> tuple[SurvivalBaselineRecord, ...]:
        total_cost = round(sum(item.action_cost for item in self.energy_accounting_records), 10)
        survived_ticks = max(
            (
                record.alive_result.survived_ticks
                for tick in self.ticks
                for record in tick.generation_result.organism_records
            ),
            default=0,
        )
        final_atp = max(
            (
                record.runtime_atp_after
                for tick in self.ticks
                for record in tick.generation_result.organism_records
            ),
            default=0.0,
        )
        return (
            SurvivalBaselineRecord(
                baseline_type="observed_wait_or_neutral_proxy",
                tick=len(self.ticks),
                survived_ticks=survived_ticks,
                final_runtime_atp=final_atp,
                action_cost_total=total_cost,
                explanation=(
                    "Baseline is diagnostic only; it does not weaken controls "
                    "or rescue active organisms."
                ),
            ),
        )

    @property
    def baseline_comparison_records(self) -> tuple[BaselineComparisonRecord, ...]:
        from codontrace.engine_claims import _mean_float

        baseline = self.survival_baseline_records[0] if self.survival_baseline_records else None
        mean_survival = _mean_float(
            record.alive_result.survived_ticks
            for tick in self.ticks
            for record in tick.generation_result.organism_records
        )
        mean_energy = _mean_float(
            record.runtime_atp_after
            for tick in self.ticks
            for record in tick.generation_result.organism_records
        )
        mean_task = _mean_float(
            getattr(item, "selection_score", 0.0) for item in self.selection_fitness_records
        )
        if baseline is None:
            return ()
        return (
            BaselineComparisonRecord(
                baseline_type=baseline.baseline_type,
                survival_advantage=round(baseline.survived_ticks - mean_survival, 10),
                energy_advantage=round(baseline.final_runtime_atp - mean_energy, 10),
                action_cost_advantage=round(-baseline.action_cost_total, 10),
                task_score_advantage=round(0.0 - mean_task, 10),
                explanation=(
                    "Positive values mean the neutral/wait proxy is outperforming "
                    "observed active behavior on that axis."
                ),
            ),
        )

    @property
    def reproduction_attempt_records(self) -> tuple[ReproductionAttemptRecord, ...]:
        rows: list[ReproductionAttemptRecord] = []
        _capacity = max((tick.generation_result.before_count for tick in self.ticks), default=None)
        copy_self_by_tick_org: dict[tuple[int, str], object] = {}
        for tick in self.ticks:
            for trace in tick.generation_result.traces:
                for raw_event in trace.events:
                    event = cast(Any, raw_event)
                    if (
                        event.action == "COPY_SELF"
                        or event.world_delta.get("reproduction_attempted") is True
                    ):
                        copy_self_by_tick_org[(tick.index, event.agent_id)] = event
        for tick in self.ticks:
            for record in tick.generation_result.organism_records:
                result = record.reproduction_result
                event = copy_self_by_tick_org.get((tick.index, record.organism_id))
                attempted = bool(result.attempted) if result is not None else event is not None
                succeeded = bool(result.succeeded) if result is not None else False
                reasons = tuple(result.decision.reasons) if result is not None else ()
                if not reasons and event is not None:
                    raw_reason = getattr(event, "world_delta", {}).get(
                        "reproduction_blocked_reason"
                    ) or getattr(event, "reason", None)
                    reasons = (str(raw_reason),) if raw_reason else ("action_not_executed",)
                if not reasons:
                    reasons = ("no_reproduction_action",)
                child = None if result is None else result.child
                lineage = None if result is None else result.lineage
                gate = None if result is None else result.reproduction_gate_result
                rows.append(
                    ReproductionAttemptRecord(
                        organism_id=record.organism_id,
                        tick=tick.index,
                        reproduction_action_attempted=attempted,
                        reproduction_allowed=bool(result.decision.allowed)
                        if result is not None
                        else False,
                        blocked_reason="none"
                        if succeeded
                        else (reasons[0] if reasons else "unknown"),
                        runtime_atp=record.runtime_atp_after,
                        min_runtime_atp_required=None
                        if gate is None
                        else gate.min_runtime_atp_required,
                        parent_atp_cost=None if gate is None else gate.parent_atp_cost,
                        offspring_atp_fraction=None if gate is None else gate.offspring_atp_fraction,
                        available_space=(
                            None
                            if gate is None
                            else bool(gate.capacity_available and gate.child_placement_available is not False)
                        ),
                        population_capacity=None if gate is None else gate.population_capacity,
                        mutation_applied=result.mutation is not None
                        if result is not None
                        else False,
                        child_created=succeeded,
                        child_id=None if child is None else child.id,
                        lineage_id=None if lineage is None else lineage.organism_id,
                    )
                )
        return tuple(rows)

    @property
    def reproduction_gate_records(self) -> tuple[ReproductionGateRecord, ...]:
        return tuple(
            ReproductionGateRecord(
                organism_id=item.organism_id,
                tick=item.tick,
                allowed=item.reproduction_allowed,
                blocked_reason=item.blocked_reason,
                runtime_atp=item.runtime_atp,
                min_runtime_atp_required=item.min_runtime_atp_required,
                parent_atp_cost=item.parent_atp_cost,
                offspring_atp_fraction=item.offspring_atp_fraction,
                population_capacity=item.population_capacity,
                available_space=item.available_space,
            )
            for item in self.reproduction_attempt_records
        )

    @property
    def lineage_growth_records(self) -> tuple[LineageGrowthRecord, ...]:
        return tuple(
            LineageGrowthRecord(
                tick=tick.index,
                births=tick.generation_result.births,
                deaths=tick.generation_result.deaths,
                before_count=tick.generation_result.before_count,
                after_count=tick.generation_result.after_count,
                lineage_growth_delta=tick.generation_result.after_count
                - tick.generation_result.before_count,
            )
            for tick in self.ticks
        )

    @property
    def birth_event_records(self) -> tuple[BirthEvent, ...]:
        return tuple(
            item.birth_event
            for tick in self.ticks
            for record in tick.generation_result.organism_records
            if (item := record.reproduction_result) is not None and item.birth_event is not None
        )

    @property
    def mutation_plan_records(self) -> tuple[MutationPlan, ...]:
        return tuple(
            item.mutation_plan
            for tick in self.ticks
            for record in tick.generation_result.organism_records
            if (item := record.reproduction_result) is not None and item.mutation_plan is not None
        )

    @property
    def mutation_result_records(self) -> tuple[MutationAuditResult, ...]:
        return tuple(
            item.mutation_audit_result
            for tick in self.ticks
            for record in tick.generation_result.organism_records
            if (item := record.reproduction_result) is not None
            and item.mutation_audit_result is not None
        )

    @property
    def child_genome_records(self) -> tuple[ChildGenomeResult, ...]:
        return tuple(
            item.child_genome_result
            for tick in self.ticks
            for record in tick.generation_result.organism_records
            if (item := record.reproduction_result) is not None
            and item.child_genome_result is not None
        )

    @property
    def child_admission_records(self) -> tuple[ChildAdmissionResult, ...]:
        return tuple(
            item.child_admission_result
            for tick in self.ticks
            for record in tick.generation_result.organism_records
            if (item := record.reproduction_result) is not None
            and item.child_admission_result is not None
        )

    @property
    def learning_inheritance_records(self) -> tuple[LearningInheritanceRecord, ...]:
        return tuple(
            item.learning_inheritance_record
            for tick in self.ticks
            for record in tick.generation_result.organism_records
            if (item := record.reproduction_result) is not None
            and item.learning_inheritance_record is not None
        )

    @property
    def skill_compression_records(self) -> tuple[SkillCompressionRecord, ...]:
        return tuple(
            item.skill_compression_record
            for tick in self.ticks
            for record in tick.generation_result.organism_records
            if (item := record.reproduction_result) is not None
            and item.skill_compression_record is not None
        )

    @property
    def adf_inheritance_records(self) -> tuple[ADFInheritanceRecord, ...]:
        return tuple(
            item.adf_inheritance_record
            for tick in self.ticks
            for record in tick.generation_result.organism_records
            if (item := record.reproduction_result) is not None
            and item.adf_inheritance_record is not None
        )

    @property
    def ai_birth_intervention_records(self) -> tuple[AIBirthInterventionRecord, ...]:
        return tuple(
            intervention
            for tick in self.ticks
            for record in tick.generation_result.organism_records
            if (item := record.reproduction_result) is not None
            for intervention in item.ai_birth_intervention_records
        )

    @property
    def capsule_transfer_metrics(self) -> tuple[object, ...]:
        return tuple(
            item
            for tick in self.ticks
            for record in tick.generation_result.organism_records
            for item in record.capsule_transfer_metrics
        )

    @property
    def capsule_cost_records(self) -> tuple[CapsuleCostRecord, ...]:
        rows: list[CapsuleCostRecord] = []
        for record in self.capsule_adoption_records:
            runtime_after = getattr(record, "runtime_atp_after", None)
            learning_after = getattr(record, "learning_atp_after", None)
            runtime_before = getattr(record, "runtime_atp_before", 0.0)
            learning_before = getattr(record, "learning_atp_before", 0.0)
            rows.append(
                CapsuleCostRecord(
                    capsule_id=getattr(record, "capsule_id", ""),
                    source_organism_id=getattr(record, "source_organism_id", ""),
                    target_organism_id=getattr(record, "target_organism_id", ""),
                    adoption_runtime_cost=round(max(0.0, runtime_before - runtime_after), 10)
                    if runtime_after is not None
                    else 0.0,
                    adoption_learning_cost=round(max(0.0, learning_before - learning_after), 10)
                    if learning_after is not None
                    else 0.0,
                )
            )
        return tuple(rows)

    @property
    def capsule_utility_records(self) -> tuple[CapsuleUtilityRecord, ...]:
        by_org_timeline: dict[str, list[tuple[int, float | None, str | None]]] = {}
        for tick in self.ticks:
            for record in tick.generation_result.organism_records:
                score = (
                    record.selection_fitness_score or record.fitness_result.selection_fitness_score
                )
                behavior_digest = (
                    record.behavior_descriptor.digest()
                    if record.behavior_descriptor is not None
                    else None
                )
                by_org_timeline.setdefault(record.organism_id, []).append(
                    (tick.index, None if score is None else score.selection_score, behavior_digest)
                )
        metric_by_key: dict[tuple[str, str], object] = {}
        for metric in self.capsule_transfer_metrics:
            metric_by_key[(
                str(getattr(metric, "source_capsule_id", "")),
                str(getattr(metric, "target_organism_id", "")),
            )] = metric
        rows: list[CapsuleUtilityRecord] = []
        for cap_record in self.capsule_adoption_records:
            target = getattr(cap_record, "target_organism_id", "")
            capsule_id = getattr(cap_record, "capsule_id", "")
            adoption_tick = int(getattr(cap_record, "adoption_attempt_tick", 0))
            timeline = sorted(by_org_timeline.get(target, ()), key=lambda item: item[0])
            before = next(
                ((score, beh) for tick, score, beh in reversed(timeline) if tick <= adoption_tick),
                (None, None),
            )
            after = next(
                ((score, beh) for tick, score, beh in timeline if tick >= adoption_tick), before
            )
            target_fitness_before, target_behavior_before = before
            target_fitness_after, target_behavior_after = after
            metric = metric_by_key.get((str(capsule_id), str(target)))
            metric_pre_graph = getattr(metric, "pre_graph_digest", None) if metric is not None else None
            metric_post_graph = getattr(metric, "post_graph_digest", None) if metric is not None else None
            if isinstance(metric_pre_graph, str) and isinstance(metric_post_graph, str) and metric_pre_graph and metric_post_graph:
                target_behavior_before = metric_pre_graph
                target_behavior_after = metric_post_graph
            selection_delta = (
                None
                if target_fitness_before is None or target_fitness_after is None
                else round(target_fitness_after - target_fitness_before, 10)
            )
            raw_source_status = getattr(
                getattr(cap_record, "source_fitness_status", "unavailable"),
                "value",
                str(getattr(cap_record, "source_fitness_status", "unavailable")),
            )
            # Outcome-based capsule utility via pure scientific evaluator.
            # Single source of truth: codontrace.genesis.capsule_utility
            from codontrace.genesis.capsule_utility import evaluate_capsule_utility

            adoption_success = bool(getattr(cap_record, "adoption_success", False))
            evaluation = evaluate_capsule_utility(
                raw_source_status=raw_source_status,
                adoption_success=adoption_success,
                target_behavior_before=target_behavior_before,
                target_behavior_after=target_behavior_after,
                selection_delta=selection_delta,
            )
            status = evaluation.source_fitness_status
            state_changed = evaluation.state_changed
            _allowed_source = evaluation.allowed_source
            _selection_delta_measured = evaluation.selection_delta_measured
            utility_selection_delta = evaluation.utility_selection_delta
            utility_raw_fitness_delta = evaluation.utility_raw_fitness_delta
            utility_task_delta = evaluation.utility_task_delta
            utility_delta = evaluation.utility_delta
            utility_status = evaluation.utility_status
            claim_eligible = evaluation.claim_eligible
            protocol_payload = evaluation.protocol_payload(
                capsule_id=str(capsule_id),
                target_organism_id=str(target),
                behavior_digest_before=target_behavior_before,
                behavior_digest_after=target_behavior_after,
                selection_fitness_before=target_fitness_before,
                selection_fitness_after=target_fitness_after,
            )
            protocol_digest = _digest(protocol_payload)
            rows.append(
                CapsuleUtilityRecord(
                    capsule_id=str(capsule_id),
                    source_organism_id=getattr(cap_record, "source_organism_id", ""),
                    target_organism_id=target,
                    source_fitness=getattr(cap_record, "source_fitness", 0.0),
                    source_fitness_status=status,
                    source_fitness_status_original=raw_source_status,
                    confidence=getattr(cap_record, "confidence", 0.0),
                    emitted_tick=getattr(cap_record, "emitted_tick", 0),
                    read_tick=getattr(cap_record, "read_tick", 0),
                    adoption_tick=adoption_tick,
                    adoption_success=adoption_success,
                    blocked_reason=getattr(cap_record, "blocked_reason", None),
                    target_fitness_before=target_fitness_before,
                    target_fitness_after=target_fitness_after,
                    target_selection_fitness_before=target_fitness_before,
                    target_selection_fitness_after=target_fitness_after,
                    utility_delta=utility_delta,
                    utility_selection_delta=utility_selection_delta,
                    utility_raw_fitness_delta=utility_raw_fitness_delta,
                    utility_task_delta=utility_task_delta,
                    target_behavior_digest_before=target_behavior_before,
                    target_behavior_digest_after=target_behavior_after,
                    state_changed=state_changed,
                    adoption_semantics="behavioral_adoption" if adoption_success else "blocked_or_rejected",
                    utility_status=utility_status,
                    utility_protocol_digest=protocol_digest,
                    claim_eligible=claim_eligible,
                    capsule_status="claim_eligible_measured_utility" if claim_eligible else "transferred_not_useful",
                )
            )
        return tuple(rows)

    @property
    def post_capsule_behavior_records(self) -> tuple[PostCapsuleBehaviorRecord, ...]:
        return tuple(
            PostCapsuleBehaviorRecord(
                capsule_id=item.capsule_id,
                target_organism_id=item.target_organism_id,
                behavior_digest_before=item.target_behavior_digest_before,
                behavior_digest_after=item.target_behavior_digest_after,
                changed=(
                    item.target_behavior_digest_before is not None
                    and item.target_behavior_digest_before != item.target_behavior_digest_after
                ),
            )
            for item in self.capsule_utility_records
        )

    @property
    def inventory_records(self) -> tuple[InventoryState, ...]:
        rows: list[InventoryState] = []
        for tick in self.ticks:
            for trace in tick.generation_result.traces:
                items: dict[str, float] = {}
                position = None
                organism_id = ""
                for raw_event in trace.events:
                    event = cast(Any, raw_event)
                    organism_id = event.agent_id
                    position = event.position_after
                    item = event.world_delta.get("inventory_item")
                    if isinstance(item, str):
                        items[item] = items.get(item, 0.0) + 1.0
                if organism_id:
                    rows.append(
                        InventoryState(
                            organism_id=organism_id,
                            tick=tick.index,
                            items=tuple(sorted(items.items())),
                            position=position,
                        )
                    )
        return tuple(rows)

    @property
    def action_precondition_records(self) -> tuple[ActionPreconditionRecord, ...]:
        rows: list[ActionPreconditionRecord] = []
        for tick in self.ticks:
            for trace in tick.generation_result.traces:
                for raw_event in trace.events:
                    event = cast(Any, raw_event)
                    if (
                        "action_precondition_allowed" in event.world_delta
                        or "missing_inputs" in event.world_delta
                    ):
                        rows.append(
                            ActionPreconditionRecord(
                                organism_id=event.agent_id,
                                tick=event.step,
                                action=event.action,
                                allowed=event.world_delta.get("action_precondition_allowed")
                                is True,
                                missing_inputs=_json_str_tuple(
                                    event.world_delta.get("missing_inputs", [])
                                ),
                                blocked_reason=event.reason if event.status == "blocked" else None,
                            )
                        )
        return tuple(rows)

    @property
    def social_interaction_records(self) -> tuple[object, ...]:
        return tuple(
            item
            for tick in self.ticks
            for record in tick.generation_result.organism_records
            for item in record.social_interaction_records
        )

    @property
    def partner_interaction_records(self) -> tuple[object, ...]:
        return tuple(
            item
            for item in self.social_interaction_records
            if str(getattr(item, "target_organism_id", ""))
            and str(getattr(item, "target_organism_id", "")) != "environment"
        )

    @property
    def role_timeline_records(self) -> tuple[RoleAssignment, ...]:
        return tuple(
            infer_role_from_record(record, tick.index)
            for tick in self.ticks
            for record in tick.generation_result.organism_records
        )

    @property
    def role_records(self) -> tuple[RoleAssignment, ...]:
        """Backward-compatible alias for role_timeline_records."""

        return self.role_timeline_records

    @property
    def role_contribution_records(self) -> tuple[RoleContribution, ...]:
        return tuple(
            RoleContribution(
                organism_id=item.organism_id,
                role=item.role,
                contribution_to_group_score=item.contribution_to_group_score,
                role_persistence=item.role_persistence,
                evidence_digest=item.digest(),
            )
            for item in self.role_timeline_records
        )

    @property
    def memory_use_records(self) -> tuple[MemoryUseEvidence, ...]:
        """Instrument memory write/read/reward chains without inventing causality.

        Scientific policy (CLAIMS.md + ALife delayed-reward practice):
        - Write then later reward is *temporal correlation*, not causal success.
        - ``correct_delayed_action`` requires an explicit memory_read (or trusted
          runtime flag with a read) before the rewarded decision.
        - ``claim_eligible`` requires a control/ablation digest; the engine never
          fabricates one from correlation alone.
        """

        from codontrace.genesis.memory_evidence import classify_memory_delayed_evidence

        rows: list[MemoryUseEvidence] = []

        def _append_evidence(
            *,
            signal_seen_tick: int,
            memory_written_tick: int | None,
            memory_read_tick: int | None,
            decision_tick: int,
            reward_tick: int | None,
            memory_required: bool,
            memory_key: str | None,
            action_after_memory: str | None,
            reward_after_action: float | None,
            runtime_correct_flag: bool,
            control_digest: str | None = None,
        ) -> None:
            classification = classify_memory_delayed_evidence(
                memory_written=memory_written_tick is not None,
                memory_read=memory_read_tick is not None,
                reward_observed=reward_tick is not None and reward_after_action is not None,
                runtime_correct_flag=runtime_correct_flag,
                control_digest=control_digest,
                memory_enabled=True,
            )
            rows.append(
                MemoryUseEvidence(
                    signal_seen_tick=signal_seen_tick,
                    memory_written_tick=memory_written_tick,
                    memory_read_tick=memory_read_tick,
                    decision_tick=decision_tick,
                    reward_tick=reward_tick,
                    correct_delayed_action=classification.correct_delayed_action,
                    memory_enabled=True,
                    memory_required=memory_required,
                    memory_key=memory_key,
                    action_after_memory=action_after_memory,
                    reward_after_action=reward_after_action,
                    evidence_status=classification.evidence_status,
                    causal_status=classification.causal_status,
                    control_digest=control_digest,
                    claim_eligible=classification.claim_eligible,
                )
            )

        for tick in self.ticks:
            for trace in tick.generation_result.traces:
                events = tuple(trace.events)
                for event in events:
                    write_flag = (
                        event.world_delta.get("memory_write") is True
                        or event.world_delta.get("memory_write_succeeded") is True
                    )
                    read_flag = event.world_delta.get("memory_read") is True
                    correct_flag = event.world_delta.get("correct_delayed_action") is True
                    if write_flag or read_flag:
                        reward_value = None
                        reward_tick = None
                        if correct_flag:
                            reward_tick = event.step
                            reward_value = float(
                                event.world_delta.get("resource_credit", 0.0)
                                or event.world_delta.get("lumen_consumed", 0.0)
                                or 0.0
                            )
                        _append_evidence(
                            signal_seen_tick=event.step,
                            memory_written_tick=event.step if write_flag else None,
                            memory_read_tick=event.step if read_flag else None,
                            decision_tick=event.step,
                            reward_tick=reward_tick,
                            memory_required=event.world_delta.get("memory_required") is True,
                            memory_key=str(event.world_delta.get("memory_key", "runtime_signal")),
                            action_after_memory=event.action if read_flag else None,
                            reward_after_action=reward_value,
                            runtime_correct_flag=correct_flag,
                            control_digest=(
                                str(event.world_delta["memory_control_digest"])
                                if isinstance(event.world_delta.get("memory_control_digest"), str)
                                else None
                            ),
                        )
                # Temporal correlation pilot: write followed by later resource reward.
                # Classified as temporal_correlation unless an explicit memory_read
                # sits between write and reward. Never invents correct_delayed_action.
                first_write = next(
                    (event for event in events if event.world_delta.get("memory_write_succeeded") is True),
                    None,
                )
                if first_write is None:
                    continue
                explicit_read = next(
                    (
                        event
                        for event in events
                        if event.step > first_write.step
                        and event.world_delta.get("memory_read") is True
                    ),
                    None,
                )
                reward_event = next(
                    (
                        event
                        for event in events
                        if event.step > first_write.step
                        and event.action in {"EAT_LUMEN", "COLLECT_RESOURCE"}
                        and (
                            event.world_delta.get("lumen_interaction") is True
                            or event.world_delta.get("resource_credit", 0.0)
                        )
                    ),
                    None,
                )
                if reward_event is not None:
                    read_tick = explicit_read.step if explicit_read is not None else None
                    if explicit_read is not None and explicit_read.step > reward_event.step:
                        read_tick = None
                    _append_evidence(
                        signal_seen_tick=first_write.step,
                        memory_written_tick=first_write.step,
                        memory_read_tick=read_tick,
                        decision_tick=reward_event.step,
                        reward_tick=reward_event.step,
                        memory_required=True,
                        memory_key=str(first_write.world_delta.get("memory_key", "runtime_signal")),
                        action_after_memory=reward_event.action,
                        reward_after_action=float(
                            reward_event.world_delta.get("resource_credit", 0.0)
                            or reward_event.world_delta.get("lumen_consumed", 0.0)
                            or 0.0
                        ),
                        runtime_correct_flag=False,
                        control_digest=(
                            str(reward_event.world_delta["memory_control_digest"])
                            if isinstance(reward_event.world_delta.get("memory_control_digest"), str)
                            else None
                        ),
                    )
        # Cross-tick agent timeline: same classification rules, no invented success.
        events_by_agent: dict[str, list[object]] = {}
        for tick in self.ticks:
            for trace in tick.generation_result.traces:
                for event in trace.events:
                    events_by_agent.setdefault(event.agent_id, []).append(event)
        for events in events_by_agent.values():
            ordered = sorted(events, key=lambda event: event.step)
            first_write = next(
                (event for event in ordered if event.world_delta.get("memory_write_succeeded") is True),
                None,
            )
            if first_write is None:
                continue
            explicit_read = next(
                (
                    event
                    for event in ordered
                    if event.step > first_write.step
                    and event.world_delta.get("memory_read") is True
                ),
                None,
            )
            reward_event = next(
                (
                    event
                    for event in ordered
                    if event.step > first_write.step
                    and event.action in {"EAT_LUMEN", "COLLECT_RESOURCE"}
                    and (
                        event.world_delta.get("lumen_interaction") is True
                        or event.world_delta.get("resource_credit", 0.0)
                    )
                ),
                None,
            )
            if reward_event is None:
                continue
            read_tick = explicit_read.step if explicit_read is not None else None
            if explicit_read is not None and explicit_read.step > reward_event.step:
                read_tick = None
            candidate_kwargs = dict(
                signal_seen_tick=first_write.step,
                memory_written_tick=first_write.step,
                memory_read_tick=read_tick,
                decision_tick=reward_event.step,
                reward_tick=reward_event.step,
                memory_required=True,
                memory_key=str(first_write.world_delta.get("memory_key", "runtime_signal")),
                action_after_memory=reward_event.action,
                reward_after_action=float(
                    reward_event.world_delta.get("resource_credit", 0.0)
                    or reward_event.world_delta.get("lumen_consumed", 0.0)
                    or 0.0
                ),
                runtime_correct_flag=False,
                control_digest=(
                    str(reward_event.world_delta["memory_control_digest"])
                    if isinstance(reward_event.world_delta.get("memory_control_digest"), str)
                    else None
                ),
            )
            before = len(rows)
            _append_evidence(**candidate_kwargs)
            if len(rows) > before:
                # Drop duplicate digests introduced by per-trace + cross-tick paths.
                if any(existing.digest() == rows[-1].digest() for existing in rows[:-1]):
                    rows.pop()
        return tuple(rows)

    @property
    def delayed_reward_records(self) -> tuple[DelayedRewardTrace, ...]:
        """Delayed-reward surface derived from classified memory evidence.

        Includes temporal_correlation rows for instrumentation, but only
        read_linked/causal_support rows can carry correct_delayed_action=True.
        """

        rows: list[DelayedRewardTrace] = []
        for item in self.memory_use_records:
            if item.correct_delayed_action or item.memory_required or item.reward_tick is not None:
                rows.append(
                    DelayedRewardTrace(
                        signal_seen_tick=item.signal_seen_tick,
                        memory_written_tick=item.memory_written_tick,
                        memory_read_tick=item.memory_read_tick,
                        decision_tick=item.decision_tick,
                        reward_tick=item.reward_tick,
                        correct_delayed_action=item.correct_delayed_action,
                        memory_enabled=item.memory_enabled,
                        memory_required=item.memory_required,
                        memory_key=item.memory_key,
                        action_after_memory=item.action_after_memory,
                        reward_after_action=item.reward_after_action,
                        evidence_status=getattr(item, "evidence_status", "not_classified"),
                        causal_status=getattr(item, "causal_status", "correlational_only"),
                        control_digest=getattr(item, "control_digest", None),
                        claim_eligible=getattr(item, "claim_eligible", False),
                    )
                )
        return tuple(rows)

    @property
    def tool_chain_records(self) -> tuple[object, ...]:
        from codontrace.genesis.toolchain import tool_chain_records_from_trace

        rows = []
        for tick in self.ticks:
            for trace in tick.generation_result.traces:
                rows.extend(tool_chain_records_from_trace(trace))
        return tuple(rows)

    @property
    def resource_policy_records(self) -> tuple[object, ...]:
        return tuple(
            item
            for tick in self.ticks
            for item in tick.generation_result.resource_policy_records
        )

    @property
    def generalization_records(self) -> tuple[object, ...]:
        """Emit heldout generalization evidence only from real protocols.

        Scientific policy (CLAIMS.md + QD/heldout practice):
        - First-vs-last tick digests are *not* a heldout evaluation.
        - Without an explicit heldout partner/world protocol, status is
          ``protocol_not_run`` and claim_eligible is always false.
        - When real heldout partner evaluation records exist on the run, they
          are forwarded as measured generalization evidence.
        """

        from codontrace.genesis.generalization import GeneralizationResult

        if not self.ticks:
            return ()

        measured: list[object] = []
        # Prefer explicit heldout partner evaluation records when present.
        for tick in self.ticks:
            gen_result = tick.generation_result
            for attr in ("heldout_partner_evaluation_records", "heldout_evaluation_records"):
                for item in getattr(gen_result, attr, ()) or ():
                    measured.append(item)
        if measured:
            return tuple(measured)

        # No real heldout protocol was run. Do not invent a proxy score from
        # first/last tick digests or average fitness.
        return (
            GeneralizationResult(
                evaluation_id=f"engine_heldout_protocol_not_run_{self.run.run_id}",
                train_digest="not_run:train",
                heldout_digest="not_run:heldout",
                score=0.0,
                claim_eligible=False,
                status="protocol_not_run",
            ),
        )

    @property
    def engine_frames(self) -> tuple[EngineFrame, ...]:
        return tuple(
            engine_frame_from_generation(tick.index, tick.generation_result) for tick in self.ticks
        )

    @property
    def engine_digest_audit(self) -> tuple[EngineDigestAuditRecord, ...]:
        default_registry_hash = _action_registry_hash(None)
        expected_default_registry_hash = _stable_default_action_registry_hash()
        registry_stable = default_registry_hash == expected_default_registry_hash
        items = [
            EngineDigestAuditRecord(
                digest_name="action_registry_hash",
                stable=registry_stable,
                mismatch_reason=None
                if registry_stable
                else "default_action_registry_hash_mismatch",
                nondeterministic_field=None if registry_stable else "action_registry_hash",
                suggested_fix=None
                if registry_stable
                else "Use the built-in action manifest instead of runtime handler introspection.",
                digest=default_registry_hash,
            ),
            EngineDigestAuditRecord(
                digest_name="result_core_payload_digest",
                stable=True,
                digest=_digest(self._core_payload()),
            ),
            EngineDigestAuditRecord(
                digest_name="manifest_digest",
                stable=True,
                digest=self.manifest.digest(),
            ),
            EngineDigestAuditRecord(
                digest_name="snapshot_digest",
                stable=True,
                digest=self.snapshot.digest(),
            ),
            EngineDigestAuditRecord(
                digest_name="replay_bundle_digest",
                stable=True,
                digest=self.replay_bundle.digest(),
            ),
        ]
        return tuple(items)

    @property
    def digest_instability_reasons(self) -> tuple[DigestInstabilityReason, ...]:
        return tuple(
            DigestInstabilityReason(
                digest_name=item.digest_name,
                stable=item.stable,
                mismatch_reason=item.mismatch_reason,
                nondeterministic_field=item.nondeterministic_field,
                suggested_fix=item.suggested_fix,
            )
            for item in self.engine_digest_audit
            if not item.stable
        )

    @property
    def actual_death_count(self) -> int:
        return sum(1 for item in self.death_reason_records if item.actual_death_removed_from_population)

    @property
    def _actual_death_keys(self) -> frozenset[tuple[str, int]]:
        return frozenset(
            (item.organism_id, item.tick)
            for item in self.death_reason_records
            if item.actual_death_removed_from_population
        )

    @property
    def blocked_reproduction_capacity_count(self) -> int:
        """Count reproduction attempts blocked by population capacity.

        This is an attempt/export diagnostic and intentionally includes attempts
        even when a configurable death policy later removes the same organism in
        that tick. Use ``nonfatal_capacity_block_count`` when the caller needs
        capacity blocks that remained non-fatal.
        """

        return sum(
            1
            for item in self.reproduction_attempt_records
            if item.blocked_reason in {"max_population_reached", "population_capacity_reached"}
            and not item.child_created
        )

    @property
    def nonfatal_capacity_block_count(self) -> int:
        actual_death_keys = self._actual_death_keys
        return sum(
            1
            for item in self.reproduction_attempt_records
            if item.blocked_reason in {"max_population_reached", "population_capacity_reached"}
            and not item.child_created
            and (item.organism_id, item.tick) not in actual_death_keys
        )

    @property
    def death_energy_summary_records(self) -> tuple[dict[str, JsonValue], ...]:
        if self._death_monitoring_disabled:
            return (
                {
                    "schema_version": "death_energy_summary_v1",
                    "death_monitoring_enabled": False,
                    "feature_status": "disabled_by_config",
                    "status_reason": "death_monitoring_disabled",
                    "actual_death_count": None,
                    "nonfatal_capacity_block_count": None,
                    "blocked_reproduction_capacity_count": None,
                    "death_risk_count": None,
                },
            )
        return (
            {
                "schema_version": "death_energy_summary_v1",
                "death_monitoring_enabled": True,
                "feature_status": "measured",
                "status_reason": "records_present",
                "actual_death_count": self.actual_death_count,
                "nonfatal_capacity_block_count": self.nonfatal_capacity_block_count,
                "blocked_reproduction_capacity_count": self.blocked_reproduction_capacity_count,
                "death_risk_count": sum(1 for item in self.death_reason_records if item.death_risk_event),
            },
        )

    @property
    def export_status_records(self) -> tuple[ExportEnvelope, ...]:
        exports: tuple[tuple[str, tuple[object, ...]], ...] = (
            ("behavior_descriptors", self.behavior_descriptors),
            ("action_wiring_matrix", (self.action_wiring_matrix,)),
            ("strong_claim_ladder_records", self.strong_claim_ladder_records),
            ("qd_selection_audit", self.qd_selection_audit),
            ("qd_parent_feedback_audit", self.qd_parent_feedback_audit),
            ("qd_archive_summary", (self.qd_archive_summary,)),
            ("capsule_adoption_records", self.capsule_adoption_records),
            ("capsule_source_fitness_records", self.capsule_source_fitness_records),
            ("capsule_shuffle_records", self.capsule_shuffle_records),
            ("fitness_breakdown_records", self.fitness_breakdown_records),
            ("selection_fitness_records", self.selection_fitness_records),
            ("memory_use_records", self.memory_use_records),
            ("delayed_reward_records", self.delayed_reward_records),
            ("social_interaction_records", self.social_interaction_records),
            ("partner_interaction_records", self.partner_interaction_records),
            ("role_timeline_records", self.role_timeline_records),
            ("role_contribution_records", self.role_contribution_records),
            ("tool_chain_records", self.tool_chain_records),
            ("resource_policy_records", self.resource_policy_records),
            ("generalization_records", self.generalization_records),
            ("engine_frames", self.engine_frames),
            ("energy_accounting_records", self.energy_accounting_records),
            ("death_reason_records", self.death_reason_records),
            ("death_classification_records", self.death_classification_records),
            ("death_energy_summary_records", self.death_energy_summary_records),
            ("action_cost_records", self.action_cost_records),
            ("action_reward_records", self.action_reward_records),
            ("survival_baseline_records", self.survival_baseline_records),
            ("baseline_comparison_records", self.baseline_comparison_records),
            ("reproduction_attempt_records", self.reproduction_attempt_records),
            ("reproduction_gate_records", self.reproduction_gate_records),
            ("lineage_growth_records", self.lineage_growth_records),
            ("birth_event_records", self.birth_event_records),
            ("mutation_plan_records", self.mutation_plan_records),
            ("mutation_result_records", self.mutation_result_records),
            ("child_genome_records", self.child_genome_records),
            ("learning_inheritance_records", self.learning_inheritance_records),
            ("skill_compression_records", self.skill_compression_records),
            ("adf_inheritance_records", self.adf_inheritance_records),
            ("ai_birth_intervention_records", self.ai_birth_intervention_records),
            ("child_admission_records", self.child_admission_records),
            ("capsule_cost_records", self.capsule_cost_records),
            ("capsule_utility_records", self.capsule_utility_records),
            ("post_capsule_behavior_records", self.post_capsule_behavior_records),
            ("inventory_records", self.inventory_records),
            ("action_precondition_records", self.action_precondition_records),
            ("exportable_population_snapshot", (self.exportable_population_snapshot,)),
            ("exportable_lineage_snapshots", self.exportable_lineage_snapshots),
            ("evaluation_protocol_digest", (self.evaluation_protocol_digest_record,)),
            ("engine_digest_audit", self.engine_digest_audit),
            ("phase1_runtime_maturity_report", (self.phase1_runtime_maturity_report,)),
            ("phase1_runtime_maturity_matrix", self.phase1_runtime_maturity_report.feature_statuses),
            ("phase_b_scientific_maturity_report", (self.phase_b_scientific_maturity_report,)),
            ("phase_b_scientific_maturity_matrix", self.phase_b_scientific_maturity_report.feature_statuses),
            ("phase_b_discovery_events", self.phase_b_scientific_maturity_report.discovery_events),
            ("phase_b_ablation_witnesses", self.phase_b_scientific_maturity_report.ablation_witnesses),
            ("phase_b_heldout_evaluations", self.phase_b_scientific_maturity_report.heldout_evaluations),
            ("phase_b_collective_swarm_ladders", self.phase_b_scientific_maturity_report.collective_swarm_ladders),
            ("phase_b_oee_results", self.phase_b_scientific_maturity_report.oee_results),
            ("phase_b_curriculum_records", self.phase_b_scientific_maturity_report.curriculum_records),
            ("phase_b_scale_reports", self.phase_b_scientific_maturity_report.scale_reports),
            ("phase_b_statistical_results", self.phase_b_scientific_maturity_report.statistical_results),
            ("phase_b_plugin_validations", self.phase_b_scientific_maturity_report.plugin_validations),
            ("phase_b_release_packs", self.phase_b_scientific_maturity_report.release_packs),
            ("digest_instability_reasons", self.digest_instability_reasons),
        )
        rows: list[ExportEnvelope] = []
        for name, records in exports:
            if name in {"death_reason_records", "death_classification_records"} and self._death_monitoring_disabled:
                status: FeatureStatus = "disabled_by_config"
                reason = "death_monitoring_disabled"
            elif name == "death_energy_summary_records" and self._death_monitoring_disabled:
                status = "disabled_by_config"
                reason = "death_monitoring_disabled"
            elif name == "action_wiring_matrix" and records:
                matrix = records[0]
                matrix_records = tuple(getattr(matrix, "records", ()))
                if matrix_records and all(bool(getattr(row, "runtime_validated", False)) for row in matrix_records):
                    status = "measured"
                    reason = "all_action_wiring_rows_runtime_validated"
                else:
                    status = "provisional"
                    reason = "contract_only_action_wiring_not_runtime_smoke_validated"
            elif records:
                status = "measured"
                reason = "records_present"
            elif name in {"death_reason_records", "death_classification_records"} and self._death_record_emission_suppressed:
                status = "empty_but_available"
                reason = "no_death_or_risk_events_observed"
            else:
                status = "empty_but_available"
                reason = "no_matching_events_observed"
            rows.append(
                ExportEnvelope(
                    schema_version=f"{name}_export_v1",
                    feature_status=status,
                    status_reason=reason,
                    records=tuple(_jsonish_for_digest(item) for item in records),
                )
            )
        return tuple(rows)

    @property
    def export_envelopes_by_name(self) -> dict[str, ExportEnvelope]:
        return {item.schema_version.removesuffix("_export_v1"): item for item in self.export_status_records}

    @property
    def export_table_schemas(self) -> dict[str, tuple[str, ...]]:
        schemas: dict[str, tuple[str, ...]] = {}
        for name, envelope in self.export_envelopes_by_name.items():
            if envelope.records and isinstance(envelope.records[0], dict):
                schemas[name] = tuple(str(key) for key in envelope.records[0].keys())
            else:
                schemas[name] = ("schema_version", "feature_status", "status_reason")
        return schemas

    def export_records(self, name: str) -> ExportEnvelope:
        envelopes = self.export_envelopes_by_name
        if name not in envelopes:
            return ExportEnvelope(
                schema_version=f"{name}_export_v1",
                feature_status="unavailable",
                status_reason="unknown_export_name",
                records=(),
            )
        return envelopes[name]

    @property
    def output_completeness_records(self) -> tuple[OutputCompletenessRecord, ...]:
        return tuple(
            OutputCompletenessRecord(
                artifact_name=item.schema_version.removesuffix("_export_v1"),
                schema_version="output_completeness_record_v1",
                feature_status=item.feature_status,
                record_count=len(item.records),
                measured_after_final_write=True,
                self_size_reliable=True,
                status_reason=item.status_reason,
            )
            for item in self.export_status_records
        )

    @property
    def exportable_population_snapshot(self) -> object:
        return self.snapshot.population

    @property
    def exportable_lineage_snapshots(self) -> tuple[dict[str, JsonValue], ...]:
        return tuple(
            {
                "schema_version": "lineage_snapshot_v1",
                "tick": tick.index,
                "population_digest": tick.generation_result.population.digest(),
                "lineage_digest": _digest(
                    {
                        "lineage": [
                            item.to_dict() for item in tick.generation_result.population.lineage
                        ]
                    }
                ),
            }
            for tick in self.ticks
        )


    @property
    def evaluation_protocol_digest_record(self) -> dict[str, JsonValue]:
        return {
            "schema_version": "evaluation_protocol_digest_v1",
            "digest": self.evaluation_protocol_digest,
            "run_id": self.run.run_id,
            "spec_digest": self.run.spec_digest,
        }

    @property
    def evaluation_protocol_digest(self) -> str:
        return _digest(
            {
                "schema_version": "replayable_evaluation_protocol_v1",
                "run_id": self.run.run_id,
                "spec_digest": self.run.spec_digest,
                "train_heldout_separation": "runner_defined",
                "library_role": "snapshot_replay_evaluation_primitive",
            }
        )

    @property
    def evidence_manifest(self) -> EvidenceManifest:
        artifact_map = {
            "behavior_descriptors": _digest_sequence(self.behavior_descriptors),
            "action_wiring_matrix": _digest_sequence((self.action_wiring_matrix,)),
            "strong_claim_ladder_records": _digest_sequence(self.strong_claim_ladder_records),
            "qd_selection_audit": _digest_sequence(self.qd_selection_audit),
            "qd_parent_feedback_audit": _digest_sequence(self.qd_parent_feedback_audit),
            "qd_archive_summary": _digest_sequence((self.qd_archive_summary,)),
            "capsule_adoption_records": _digest_sequence(self.capsule_adoption_records),
            "capsule_source_fitness_records": _digest_sequence(self.capsule_source_fitness_records),
            "capsule_shuffle_records": _digest_sequence(self.capsule_shuffle_records),
            "fitness_breakdown_records": _digest_sequence(self.fitness_breakdown_records),
            "selection_fitness_records": _digest_sequence(self.selection_fitness_records),
            "memory_use_records": _digest_sequence(self.memory_use_records),
            "delayed_reward_records": _digest_sequence(self.delayed_reward_records),
            "social_interaction_records": _digest_sequence(self.social_interaction_records),
            "partner_interaction_records": _digest_sequence(self.partner_interaction_records),
            "role_timeline_records": _digest_sequence(self.role_timeline_records),
            "role_contribution_records": _digest_sequence(self.role_contribution_records),
            "tool_chain_records": _digest_sequence(self.tool_chain_records),
            "resource_policy_records": _digest_sequence(self.resource_policy_records),
            "generalization_records": _digest_sequence(self.generalization_records),
            "engine_frames": _digest_sequence(self.engine_frames),
            "energy_accounting_records": _digest_sequence(self.energy_accounting_records),
            "death_reason_records": _digest_sequence(self.death_reason_records),
            "action_cost_records": _digest_sequence(self.action_cost_records),
            "action_reward_records": _digest_sequence(self.action_reward_records),
            "survival_baseline_records": _digest_sequence(self.survival_baseline_records),
            "baseline_comparison_records": _digest_sequence(self.baseline_comparison_records),
            "reproduction_attempt_records": _digest_sequence(self.reproduction_attempt_records),
            "reproduction_gate_records": _digest_sequence(self.reproduction_gate_records),
            "lineage_growth_records": _digest_sequence(self.lineage_growth_records),
            "birth_event_records": _digest_sequence(self.birth_event_records),
            "mutation_plan_records": _digest_sequence(self.mutation_plan_records),
            "mutation_result_records": _digest_sequence(self.mutation_result_records),
            "child_genome_records": _digest_sequence(self.child_genome_records),
            "learning_inheritance_records": _digest_sequence(self.learning_inheritance_records),
            "skill_compression_records": _digest_sequence(self.skill_compression_records),
            "adf_inheritance_records": _digest_sequence(self.adf_inheritance_records),
            "ai_birth_intervention_records": _digest_sequence(self.ai_birth_intervention_records),
            "capsule_cost_records": _digest_sequence(self.capsule_cost_records),
            "capsule_utility_records": _digest_sequence(self.capsule_utility_records),
            "post_capsule_behavior_records": _digest_sequence(self.post_capsule_behavior_records),
            "inventory_records": _digest_sequence(self.inventory_records),
            "action_precondition_records": _digest_sequence(self.action_precondition_records),
            "export_status_records": _digest_sequence(self.export_status_records),
            "output_completeness_records": _digest_sequence(self.output_completeness_records),
            "exportable_population_snapshot": _digest_sequence(
                (self.exportable_population_snapshot,)
            ),
            "exportable_lineage_snapshots": _digest_sequence(self.exportable_lineage_snapshots),
            "evaluation_protocol_digest": _digest_sequence((self.evaluation_protocol_digest,)),
            "engine_digest_audit": _digest_sequence(self.engine_digest_audit),
            "digest_instability_reasons": _digest_sequence(self.digest_instability_reasons),
        }
        for envelope in self.export_status_records:
            export_name = envelope.schema_version.removesuffix("_export_v1")
            artifact_map.setdefault(export_name, _digest_sequence(envelope.records))
        phase1_report = self.phase1_runtime_maturity_report
        phase_b_report = self.phase_b_scientific_maturity_report
        artifact_map.update(phase1_report.artifact_digest_map)
        artifact_map.update(phase_b_report.artifact_digest_map)
        feature_status = {
            item.schema_version.removesuffix("_export_v1"): item.feature_status
            for item in self.export_status_records
        }
        feature_status.update(phase1_report.manifest_feature_status)
        feature_status.update(phase_b_report.manifest_feature_status)
        feature_status["phase1_runtime_maturity_report"] = "measured"
        feature_status["phase_b_scientific_maturity_report"] = "measured"
        return EvidenceManifest(
            schema_version="genesis_evidence_manifest_v2",
            producer_version="GenesisRunResult.properties",
            library_version="0.3.0b4.dev0",
            config_digest=self.run.spec_digest,
            source_digest=self.manifest.source_digest or "",
            protocol_digest=self.manifest.digest(),
            artifact_digests=tuple(artifact_map[key] for key in sorted(artifact_map)),
            artifact_digest_map=artifact_map,
            feature_status=feature_status,
        )

    def with_review_result(self, review: LLMReviewResult) -> GenesisRunResult:
        record = ExternalReviewRecord.from_result(review, validated=True)
        status = ReviewStatus(
            status="reviewed_accepted" if review.claim_review.allowed else "reviewed_flagged",
            reviewer=review.reviewer_id,
            decision_digest=record.result_digest,
        )
        manifest = replace(self.manifest, review_status=status)
        evidence_pack = replace(self.evidence_pack, manifest=manifest)
        replay_bundle = replace(self.replay_bundle, manifest=manifest)
        return replace(
            self,
            manifest=manifest,
            evidence_pack=evidence_pack,
            replay_bundle=replay_bundle,
            external_review_record=record,
        )

    def with_human_review(self, decision: HumanReviewDecision) -> GenesisRunResult:
        record = self.external_review_record
        if record is not None:
            record = replace(record, human_decision=decision)
        status = ReviewStatus(
            status=f"human_{decision.decision}",
            reviewer=decision.reviewer,
            decision_digest=decision.digest(),
        )
        manifest = replace(self.manifest, review_status=status)
        evidence_pack = replace(self.evidence_pack, manifest=manifest)
        replay_bundle = replace(self.replay_bundle, manifest=manifest)
        return replace(
            self,
            manifest=manifest,
            evidence_pack=evidence_pack,
            replay_bundle=replay_bundle,
            external_review_record=record,
        )


__all__ = [
    "GenesisRunResult",
]
