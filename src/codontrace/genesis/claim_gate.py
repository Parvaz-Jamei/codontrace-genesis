"""Whitelist-based scientific claim gate for GENESIS evidence objects.

Feature objects report evidence.  Only :class:`ScientificClaimGate` assigns,
downgrades, or rejects claim labels.  Unknown claim strings and overclaim
aliases are rejected by default so manifests cannot echo raw user claims as
scientific conclusions.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from codontrace._types import JsonValue
from codontrace.errors import ConfigurationError


def _digest(payload: Mapping[str, JsonValue]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def normalize_claim_label(value: str) -> str:
    """Return canonical claim text for whitelist/alias checks."""

    lowered = value.strip().lower()
    lowered = re.sub(r"[^a-z0-9]+", "_", lowered)
    lowered = re.sub(r"_+", "_", lowered).strip("_")
    return lowered


@dataclass(frozen=True, slots=True)
class ClaimEvidenceRequirement:
    name: str
    required: bool = True

    def to_dict(self) -> dict[str, JsonValue]:
        return {"name": self.name, "required": self.required}


EvidenceRequirement = ClaimEvidenceRequirement


@dataclass(frozen=True, slots=True)
class ClaimRequest:
    claim: str
    evidence_flags: Mapping[str, bool]
    manifest_digest: str | None = None
    evidence_digests: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "claim": self.claim,
            "evidence_flags": dict(
                sorted((str(k), bool(v)) for k, v in self.evidence_flags.items())
            ),
            "manifest_digest": self.manifest_digest,
            "evidence_digests": list(self.evidence_digests),
        }


@dataclass(frozen=True, slots=True)
class ClaimDowngradeReason:
    code: str
    detail: str

    def to_dict(self) -> dict[str, JsonValue]:
        return {"code": self.code, "detail": self.detail}


@dataclass(frozen=True, slots=True)
class ClaimGatePolicy:
    version: str
    allowed_claims: tuple[str, ...]
    forbidden_aliases: tuple[str, ...]
    legacy_alias_map: tuple[tuple[str, str], ...]
    digest: str = ""

    def __post_init__(self) -> None:
        allowed = tuple(sorted({normalize_claim_label(item) for item in self.allowed_claims}))
        forbidden = tuple(sorted({normalize_claim_label(item) for item in self.forbidden_aliases}))
        alias_map = tuple(
            sorted(
                (normalize_claim_label(k), normalize_claim_label(v))
                for k, v in self.legacy_alias_map
            )
        )
        object.__setattr__(self, "allowed_claims", allowed)
        object.__setattr__(self, "forbidden_aliases", forbidden)
        object.__setattr__(self, "legacy_alias_map", alias_map)
        payload = self._payload()
        computed = _digest(payload)
        if self.digest and self.digest != computed:
            raise ConfigurationError("ClaimGatePolicy digest mismatch.")
        object.__setattr__(self, "digest", computed)

    def _payload(self) -> dict[str, JsonValue]:
        return {
            "version": self.version,
            "allowed_claims": list(self.allowed_claims),
            "forbidden_aliases": list(self.forbidden_aliases),
            "legacy_alias_map": [[k, v] for k, v in self.legacy_alias_map],
        }

    def to_dict(self) -> dict[str, JsonValue]:
        return {**self._payload(), "digest": self.digest}


_ALLOWED_CLAIMS: tuple[str, ...] = (
    "foundation_engine",
    "experimental_engine",
    "continuous_fitness_supported",
    "qd_reporting_supported",
    "active_qd_supported",
    "qd_candidate_schema_supported",
    "benchmark_suite_supported",
    "execution_source_map_supported",
    "variable_genome_supported",
    "adf_macro_supported",
    "lineage_attribution_supported",
    "event_association_only",
    "lagged_predictive_support",
    "conditional_predictive_support",
    "intervention_supported",
    "ground_truth_recovered",
    "oee_measurement_only",
    "oee_candidate",
    "adaptive_gp_map_proxy",
    "genetic_birth_claim",
    "digital_evolution_claim",
    "baldwinian_learning_claim",
    "lamarckian_inheritance_claim",
    "ai_guided_evolution_claim",
    "open_ended_claim",
    "variable_genome_runtime_supported",
    "adf_macro_usefulness_supported",
    "contribution_attribution_supported",
    "innovation_protection_supported",
    "event_graph_evidence_supported",
    "intervention_supported_causal_evidence",
    "discovery_witness_candidate",
    "discovery_ablation_supported_candidate",
    "social_partner_generalization_supported",
    "oee_candidate_evidence_supported",
    "collective_intelligence_candidate",
    "swarm_coordination_candidate",
    "adf_single_macro_runtime_effect_observed",
)

_FORBIDDEN_ALIASES: tuple[str, ...] = (
    "semantic_closure",
    "semantic_closure_solved",
    "proved_semantic_closure",
    "solved_semantic_closure",
    "symbol_matter_solved",
    "proved_open_endedness",
    "unbounded_open_endedness",
    "unbounded_open_endedness_proved",
    "proved_unbounded_oee",
    "open_ended_evolution_proved",
    "artificial_life",
    "solved_artificial_life",
    "artificial_life_solved",
    "artificial_life_proved",
    "life_proved",
    "true_causal_discovery",
    "causal_discovery_proved",
    "true_causal_intelligence",
    "causal_intelligence",
    "causal_intelligence_proved",
    "full_genesis_engine",
    "proved_full_genesis",
    "full_genesis_proved",
    "benchmark_superiority",
    "state_of_the_art_proved",
    "agi",
    "consciousness",
    "proof_of_artificial_life",
    "qd_functional_claim",
    "capsule_signal_claim",
    "planning_claim",
    "tool_use_claim",
    "planning_tool_use_claim",
    "generalization_claim",
    "social_intelligence_claim",
    "collective_intelligence",
    "real_collective_intelligence",
    "true_social_intelligence",
)

_LEGACY_ALIAS_MAP: tuple[tuple[str, str], ...] = (
    ("research_alpha_foundation_engine", "foundation_engine"),
    ("qd_supported_search", "active_qd_supported"),
    ("qd_search_supported", "active_qd_supported"),
    ("causal_prediction_supported", "lagged_predictive_support"),
    ("causal_association_supported", "event_association_only"),
    ("causal_intervention_supported", "intervention_supported"),
    ("capsule_transfer_supported", "experimental_engine"),
    ("capsule_transfer_effect_supported", "experimental_engine"),
    ("adf_pattern_candidate", "experimental_engine"),
    ("adf_macro_supported", "adf_macro_supported"),
    ("discovery_candidate", "experimental_engine"),
    ("supported_discovery_candidate", "experimental_engine"),
    ("open_ended_evolution_candidate", "oee_candidate"),
    ("artificial_life_candidate", "artificial_life"),
)

_DEFAULT_REQUIREMENTS: dict[str, tuple[str, ...]] = {
    "foundation_engine": (),
    "experimental_engine": ("manifest", "replay_verification"),
    "continuous_fitness_supported": ("fitness_components", "fitness_config_digest"),
    "qd_reporting_supported": ("qd_candidate_schema", "archive_digest"),
    "active_qd_supported": (
        "qd_candidate_schema",
        "archive_digest",
        "qd_ask_tell",
        "archive_feedback",
        "parent_selection_feedback",
        "parent_selection_feedback_digest",
        "qd_scheduler_digest",
    ),
    "qd_candidate_schema_supported": ("qd_candidate_schema",),
    "benchmark_suite_supported": ("benchmark_suite_v2",),
    "execution_source_map_supported": ("execution_source_map",),
    "variable_genome_supported": ("genome_program_digest", "structural_mutation_record"),
    "adf_macro_supported": ("adf_macro_expansion", "bounded_expansion", "source_map"),
    "lineage_attribution_supported": ("contribution_ledger", "execution_records"),
    "event_association_only": ("event_graph",),
    "lagged_predictive_support": ("predictive_probe", "lag_record"),
    "conditional_predictive_support": ("predictive_probe", "controls"),
    "intervention_supported": (
        "intervention_result_artifact",
        "intervention_result_digest",
        "baseline_digest",
        "treatment_digest",
        "intervention_protocol_digest",
        "effect_size",
        "paired_seed_protocol_digest",
        "claim_gate_decision_digest",
    ),
    "ground_truth_recovered": ("ground_truth_world", "recovery_report", "protocol_executed"),
    "oee_measurement_only": ("oee_metrics",),
    "oee_candidate": (
        "oee_report_artifact",
        "oee_report_digest",
        "oee_protocol_executed",
        "shadow_run_present",
        "min_seed_threshold_met",
        "persistence_window_observed",
        "confidence_intervals_present",
        "stagnation_diversity_status_recorded",
        "claim_gate_decision_digest",
    ),
    "adaptive_gp_map_proxy": (
        "translation_profile",
        "semantic_proxy_report",
        "replay_capture",
        "translation_safety_gates",
    ),
    "genetic_birth_claim": ("births_positive", "mutation_records", "lineage_records"),
    "digital_evolution_claim": (
        "births_positive",
        "heritable_variation",
        "differential_fitness",
    ),
    "baldwinian_learning_claim": (
        "learning_improves_fitness",
        "selection_pressure_recorded",
        "learned_content_not_inherited",
    ),
    "lamarckian_inheritance_claim": (
        "learned_content_inherited",
        "compressed_skill_validation",
        "inheritance_records",
    ),
    "ai_guided_evolution_claim": (
        "external_intervention_records",
        "ai_disabled_baseline",
        "baseline_comparison",
    ),
    "open_ended_claim": (
        "heldout_novel_environment_growth",
        "no_fixed_endpoint_protocol",
        "strong_controls",
    ),
    "variable_genome_runtime_supported": (
        "runtime_effect",
        "genome_program_digest",
        "structural_mutation_record",
        "artifact_digest",
        "replay_verification",
    ),
    "adf_macro_usefulness_supported": (
        "runtime_effect",
        "adf_macro_expansion",
        "adf_usefulness_report_digest",
        "null_control",
        "permutation_control",
        "artifact_digest",
        "replay_verification",
    ),
    "contribution_attribution_supported": (
        "runtime_effect",
        "contribution_ledger",
        "execution_records",
        "micro_ablation_status",
        "artifact_digest",
        "replay_verification",
    ),
    "innovation_protection_supported": (
        "runtime_effect",
        "innovation_registry_digest",
        "bounded_policy",
        "negative_control",
        "artifact_digest",
        "replay_verification",
    ),
    "event_graph_evidence_supported": (
        "event_graph",
        "event_graph_digest",
        "runtime_effect",
        "artifact_digest",
        "replay_verification",
    ),
    "intervention_supported_causal_evidence": (
        "intervention_result_artifact",
        "intervention_result_digest",
        "baseline_digest",
        "treatment_digest",
        "intervention_protocol_digest",
        "effect_size",
        "paired_seed_protocol_digest",
        "artifact_digest",
        "replay_verification",
        "claim_gate_decision_digest",
    ),
    "discovery_witness_candidate": (
        "candidate_detected",
        "d0_baseline",
        "shadow_run",
        "persistence",
        "discovery_witness_digest",
        "artifact_digest",
        "replay_verification",
    ),
    "discovery_ablation_supported_candidate": (
        "candidate_detected",
        "d0_baseline",
        "shadow_run",
        "persistence",
        "ablation_result",
        "qd_novelty_distance",
        "discovery_witness_digest",
        "artifact_digest",
        "replay_verification",
    ),
    "social_partner_generalization_supported": (
        "real_partner_event",
        "familiar_partner_protocol",
        "unfamiliar_partner_protocol",
        "heldout_protocol",
        "leakage_check",
        "social_generalization_digest",
        "artifact_digest",
        "replay_verification",
    ),
    "oee_candidate_evidence_supported": (
        "oee_report_artifact",
        "oee_report_digest",
        "novelty_metric",
        "learnability_metric",
        "persistence_window_observed",
        "ablation_result",
        "multi_seed_protocol",
        "confidence_intervals_present",
        "artifact_digest",
        "replay_verification",
        "claim_gate_decision_digest",
    ),
    "collective_intelligence_candidate": (
        "real_partner_event",
        "non_capsule_cooperation",
        "role_complementarity",
        "collective_coordination",
        "heldout_protocol",
        "familiar_partner_protocol",
        "unfamiliar_partner_protocol",
        "ablation_result",
        "collective_report_digest",
        "replay_verification",
    ),
    "swarm_coordination_candidate": (
        "distributed_task_coverage",
        "decentralized_coordination",
        "shuffled_agent_control",
        "single_agent_baseline",
        "no_communication_baseline",
        "swarm_report_digest",
        "replay_verification",
    ),
    "adf_single_macro_runtime_effect_observed": (
        "runtime_effect",
        "adf_macro_expansion",
        "artifact_digest",
        "replay_verification",
    ),
}



_CLAIM_LADDER_LEVELS: tuple[str, ...] = (
    "metadata_only",
    "instrumented_runtime",
    "pilot_supported",
    "control_supported",
    "ablation_supported",
    "multi_seed_supported",
    "heldout_supported",
    "intervention_supported",
    "claim_ready_research_alpha",
)

_CLAIM_LADDER_REQUIREMENTS: dict[str, tuple[str, ...]] = {
    "metadata_only": (),
    "instrumented_runtime": ("schema_version", "artifact_digest", "runtime_records"),
    "pilot_supported": ("schema_version", "artifact_digest", "runtime_records", "pilot_run"),
    "control_supported": ("runtime_records", "negative_control", "control_digest"),
    "ablation_supported": ("negative_control", "ablation_result", "ablation_digest"),
    "multi_seed_supported": ("multi_seed_protocol", "effect_size", "confidence_interval"),
    "heldout_supported": ("heldout_protocol", "leakage_check", "partner_or_world_shift"),
    "intervention_supported": ("intervention_result", "treatment_digest", "baseline_digest"),
    "claim_ready_research_alpha": (
        "schema_version", "artifact_digest", "runtime_records", "pilot_run",
        "negative_control", "control_digest", "ablation_result", "ablation_digest",
        "multi_seed_protocol", "effect_size", "confidence_interval", "heldout_protocol",
        "leakage_check", "partner_or_world_shift", "intervention_result", "treatment_digest",
        "baseline_digest", "replay_verification", "claim_gate_decision_digest",
    ),
}


@dataclass(frozen=True, slots=True)
class StrongClaimLadderResult:
    """Evidence-to-claim ladder for ambitious GENESIS research-alpha claims.

    A large claim is not rejected because it is large. It is mapped to the
    highest evidence level currently supported by schema, runtime traces,
    controls, ablations, multi-seed statistics, heldout checks, and intervention
    evidence.
    """

    requested_claim: str
    achieved_level: str
    target_level: str
    evidence_flags: tuple[tuple[str, bool], ...]
    missing_for_target: tuple[str, ...]
    satisfied_levels: tuple[str, ...]
    schema_version: str = "strong_claim_ladder_result_v1"
    digest: str = ""

    def __post_init__(self) -> None:
        if self.achieved_level not in _CLAIM_LADDER_LEVELS:
            raise ConfigurationError("invalid achieved_level.")
        if self.target_level not in _CLAIM_LADDER_LEVELS:
            raise ConfigurationError("invalid target_level.")
        flags = tuple(sorted((str(k), bool(v)) for k, v in self.evidence_flags))
        object.__setattr__(self, "evidence_flags", flags)
        object.__setattr__(self, "missing_for_target", tuple(sorted(str(x) for x in self.missing_for_target)))
        object.__setattr__(self, "satisfied_levels", tuple(x for x in _CLAIM_LADDER_LEVELS if x in set(self.satisfied_levels)))
        computed = _digest(self._payload())
        if self.digest and self.digest != computed:
            raise ConfigurationError("StrongClaimLadderResult digest mismatch.")
        object.__setattr__(self, "digest", computed)

    def _payload(self) -> dict[str, JsonValue]:
        return {
            "schema_version": self.schema_version,
            "requested_claim": self.requested_claim,
            "achieved_level": self.achieved_level,
            "target_level": self.target_level,
            "evidence_flags": [[k, v] for k, v in self.evidence_flags],
            "missing_for_target": list(self.missing_for_target),
            "satisfied_levels": list(self.satisfied_levels),
        }

    def to_dict(self) -> dict[str, JsonValue]:
        return {**self._payload(), "digest": self.digest}


def _cumulative_claim_ladder_requirements(level: str) -> tuple[str, ...]:
    """Return all requirements up to and including ``level`` in ladder order.

    The Phase 1 claim ladder is intentionally cumulative: a high-level claim
    cannot skip lower evidence layers such as schema/artifact/runtime records,
    pilot support, controls, ablations, multi-seed statistics, or heldout checks.
    """

    if level not in _CLAIM_LADDER_LEVELS:
        raise ConfigurationError("level is not a recognized claim ladder level.")
    required: list[str] = []
    for candidate in _CLAIM_LADDER_LEVELS:
        for name in _CLAIM_LADDER_REQUIREMENTS[candidate]:
            if name not in required:
                required.append(name)
        if candidate == level:
            break
    return tuple(required)


def evaluate_strong_claim_ladder(
    claim: str,
    evidence_flags: Mapping[str, bool],
    *,
    target_level: str = "claim_ready_research_alpha",
) -> StrongClaimLadderResult:
    """Map evidence to the strongest cumulatively supported GENESIS claim level."""

    if target_level not in _CLAIM_LADDER_LEVELS:
        raise ConfigurationError("target_level is not a recognized claim ladder level.")
    normalized_flags = {str(k): bool(v) for k, v in evidence_flags.items()}
    satisfied: list[str] = []
    achieved = "metadata_only"
    for level in _CLAIM_LADDER_LEVELS:
        required = _cumulative_claim_ladder_requirements(level)
        if all(normalized_flags.get(name, False) for name in required):
            satisfied.append(level)
            achieved = level
        else:
            break
    missing = tuple(
        name for name in _cumulative_claim_ladder_requirements(target_level)
        if not normalized_flags.get(name, False)
    )
    return StrongClaimLadderResult(
        requested_claim=claim,
        achieved_level=achieved,
        target_level=target_level,
        evidence_flags=tuple(normalized_flags.items()),
        missing_for_target=missing,
        satisfied_levels=tuple(satisfied),
    )

def default_claim_gate_policy() -> ClaimGatePolicy:
    return ClaimGatePolicy(
        version="claim_gate_policy_v2",
        allowed_claims=_ALLOWED_CLAIMS,
        forbidden_aliases=_FORBIDDEN_ALIASES,
        legacy_alias_map=_LEGACY_ALIAS_MAP,
    )


@dataclass(frozen=True, slots=True)
class ClaimDecision:
    requested_claim: str
    normalized_requested_claim: str
    allowed: bool
    final_claim: str
    decision: str
    failed_reasons: tuple[str, ...]
    evidence_digests_used: tuple[str, ...]
    policy_version: str
    digest: str = ""

    def __post_init__(self) -> None:
        payload = self._payload()
        computed = _digest(payload)
        if self.digest and self.digest != computed:
            raise ConfigurationError("ClaimDecision digest mismatch.")
        object.__setattr__(self, "digest", computed)

    @property
    def claim(self) -> str:
        return self.requested_claim

    @property
    def level(self) -> str:
        return self.final_claim

    @property
    def reasons(self) -> tuple[ClaimDowngradeReason, ...]:
        return tuple(ClaimDowngradeReason(code, code) for code in self.failed_reasons)

    def _payload(self) -> dict[str, JsonValue]:
        return {
            "requested_claim": self.requested_claim,
            "normalized_requested_claim": self.normalized_requested_claim,
            "allowed": self.allowed,
            "final_claim": self.final_claim,
            "decision": self.decision,
            "failed_reasons": list(self.failed_reasons),
            "evidence_digests_used": list(self.evidence_digests_used),
            "policy_version": self.policy_version,
        }

    def to_dict(self) -> dict[str, JsonValue]:
        return {**self._payload(), "digest": self.digest}


class ScientificClaimGate:
    """Whitelist- and alias-resistant central authority for claims."""

    def __init__(self, policy: ClaimGatePolicy | None = None) -> None:
        self.policy = policy or default_claim_gate_policy()
        self._requirements = dict(_DEFAULT_REQUIREMENTS)
        self._allowed = set(self.policy.allowed_claims)
        self._forbidden = set(self.policy.forbidden_aliases)
        self._aliases = dict(self.policy.legacy_alias_map)

    def decide(self, request: ClaimRequest) -> ClaimDecision:
        normalized = normalize_claim_label(request.claim)
        canonical = self._aliases.get(normalized, normalized)
        evidence_digests = tuple(sorted({str(item) for item in request.evidence_digests if item}))
        if request.manifest_digest:
            evidence_digests = tuple(sorted((*evidence_digests, request.manifest_digest)))
        if canonical in self._forbidden:
            final = "not_claimed" if canonical == "full_genesis_engine" else f"{canonical}_rejected"
            return self._decision(
                request,
                normalized,
                False,
                final,
                "rejected_overclaim_alias",
                ("overclaim_alias_forbidden",),
                evidence_digests,
            )
        if canonical not in self._allowed:
            return self._decision(
                request,
                normalized,
                False,
                "not_claimed",
                "rejected_unknown_claim",
                ("unknown_claim_not_whitelisted",),
                evidence_digests,
            )
        missing = tuple(
            f"missing_{name}"
            for name in self._requirements.get(canonical, ())
            if not request.evidence_flags.get(name, False)
        )
        if missing:
            downgrade = self._downgrade_for(canonical)
            return self._decision(
                request,
                normalized,
                False,
                downgrade,
                "insufficient_evidence",
                missing,
                evidence_digests,
            )
        return self._decision(
            request,
            normalized,
            True,
            canonical,
            "allowed",
            (),
            evidence_digests,
        )

    def _downgrade_for(self, canonical: str) -> str:
        if canonical == "active_qd_supported":
            return "qd_reporting_supported"
        if canonical in {"intervention_supported", "ground_truth_recovered"}:
            return "event_association_only"
        if canonical == "oee_candidate":
            return "oee_measurement_only"
        if canonical == "adaptive_gp_map_proxy":
            return "experimental_engine"
        return "experimental_engine" if canonical != "foundation_engine" else "foundation_engine"

    def _decision(
        self,
        request: ClaimRequest,
        normalized: str,
        allowed: bool,
        final_claim: str,
        decision: str,
        reasons: Sequence[str],
        evidence_digests: Sequence[str],
    ) -> ClaimDecision:
        return ClaimDecision(
            requested_claim=request.claim,
            normalized_requested_claim=normalized,
            allowed=allowed,
            final_claim=final_claim,
            decision=decision,
            failed_reasons=tuple(str(item) for item in reasons),
            evidence_digests_used=tuple(str(item) for item in evidence_digests),
            policy_version=self.policy.version,
        )
