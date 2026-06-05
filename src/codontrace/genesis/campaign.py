"""Active evolutionary campaign data contracts and conservative execution helpers."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, replace
from enum import Enum
from typing import Protocol, runtime_checkable

from codontrace._types import JsonValue


@runtime_checkable
class _Digestible(Protocol):
    def digest(self) -> str: ...


@runtime_checkable
class _DictSerializable(Protocol):
    def to_dict(self) -> dict[str, JsonValue]: ...


class EvolutionPhase(str, Enum):
    TRAIN = "train"
    ELITE_SELECTION = "elite_selection"
    ELITE_REPLAY = "elite_replay"
    HELDOUT_EVALUATION = "heldout_evaluation"
    CROSS_PARTNER_EVALUATION = "cross_partner_evaluation"
    REPORT = "report"


@dataclass(frozen=True, slots=True)
class EvolutionCampaignConfig:
    seed: int
    phases: tuple[EvolutionPhase | str, ...] = (EvolutionPhase.TRAIN,)
    heldout_isolation: bool = True
    elite_count: int = 4
    schema_version: str = "evolution_campaign_config_v2"

    def __post_init__(self) -> None:
        object.__setattr__(self, "phases", tuple(_evolution_phase(item) for item in self.phases))
        if self.elite_count <= 0:
            raise ValueError("elite_count must be positive")

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "schema_version": self.schema_version,
            "seed": self.seed,
            "phases": [_evolution_phase(item).value for item in self.phases],
            "heldout_isolation": self.heldout_isolation,
            "elite_count": self.elite_count,
        }

    def digest(self) -> str:
        return _digest(self.to_dict())


@dataclass(frozen=True, slots=True)
class EliteLineage:
    organism_id: str
    lineage_digest: str
    replay_digest: str
    fitness_score: float
    behavior_digest: str = ""

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "organism_id": self.organism_id,
            "lineage_digest": self.lineage_digest,
            "replay_digest": self.replay_digest,
            "fitness_score": self.fitness_score,
            "behavior_digest": self.behavior_digest,
        }

    def digest(self) -> str:
        return _digest(self.to_dict())


@dataclass(frozen=True, slots=True)
class EliteSelectionResult:
    phase: EvolutionPhase | str
    elites: tuple[EliteLineage, ...]
    selection_digest: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "phase", _evolution_phase(self.phase))
        if not self.selection_digest:
            object.__setattr__(
                self, "selection_digest", _digest({"elites": [e.digest() for e in self.elites]})
            )

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "phase": _evolution_phase(self.phase).value,
            "elites": [elite.to_dict() for elite in self.elites],
            "selection_digest": self.selection_digest,
        }

    def digest(self) -> str:
        return _digest(self.to_dict())


@dataclass(frozen=True, slots=True)
class EliteReplayResult:
    replay_digest: str
    elite_digests: tuple[str, ...]
    deterministic: bool = True
    schema_version: str = "elite_replay_result_v1"

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "schema_version": self.schema_version,
            "replay_digest": self.replay_digest,
            "elite_digests": list(self.elite_digests),
            "deterministic": self.deterministic,
        }

    def digest(self) -> str:
        return _digest(self.to_dict())


@dataclass(frozen=True, slots=True)
class HeldoutEvaluationResult:
    evaluation_digest: str
    train_digest: str
    heldout_digest: str
    score: float
    leakage_guard_passed: bool = True
    status: str = "measured"

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "evaluation_digest": self.evaluation_digest,
            "train_digest": self.train_digest,
            "heldout_digest": self.heldout_digest,
            "score": self.score,
            "leakage_guard_passed": self.leakage_guard_passed,
            "status": self.status,
        }

    def digest(self) -> str:
        return _digest(self.to_dict())


@dataclass(frozen=True, slots=True)
class CrossPartnerEvaluationResult(HeldoutEvaluationResult):
    partner_mode: str = "unfamiliar_partner"

    def to_dict(self) -> dict[str, JsonValue]:
        data = HeldoutEvaluationResult.to_dict(self)
        data["partner_mode"] = self.partner_mode
        return data


@dataclass(frozen=True, slots=True)
class EvolutionCampaignResult:
    elite_lineages: tuple[EliteLineage, ...] = ()
    heldout_results: tuple[HeldoutEvaluationResult, ...] = ()
    cross_partner_results: tuple[CrossPartnerEvaluationResult, ...] = ()
    elite_replay_results: tuple[EliteReplayResult, ...] = ()
    campaign_manifest: dict[str, JsonValue] | None = None
    schema_version: str = "evolution_campaign_result_v1"

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "schema_version": self.schema_version,
            "elite_lineages": [item.to_dict() for item in self.elite_lineages],
            "heldout_results": [item.to_dict() for item in self.heldout_results],
            "cross_partner_results": [item.to_dict() for item in self.cross_partner_results],
            "elite_replay_results": [item.to_dict() for item in self.elite_replay_results],
            "campaign_manifest": dict(sorted((self.campaign_manifest or {}).items())),
        }

    def digest(self) -> str:
        return _digest(self.to_dict())


@dataclass(frozen=True, slots=True)
class EvolutionCampaign:
    config: EvolutionCampaignConfig
    train_digest: str = ""
    elite_selection: EliteSelectionResult | None = None
    elite_replay: EliteReplayResult | None = None
    heldout_evaluation: HeldoutEvaluationResult | None = None
    cross_partner_evaluation: CrossPartnerEvaluationResult | None = None

    @property
    def result(self) -> EvolutionCampaignResult:
        elite_lineages = () if self.elite_selection is None else self.elite_selection.elites
        return EvolutionCampaignResult(
            elite_lineages=elite_lineages,
            heldout_results=() if self.heldout_evaluation is None else (self.heldout_evaluation,),
            cross_partner_results=()
            if self.cross_partner_evaluation is None
            else (self.cross_partner_evaluation,),
            elite_replay_results=() if self.elite_replay is None else (self.elite_replay,),
            campaign_manifest={
                "config_digest": self.config.digest(),
                "train_digest": self.train_digest,
                "campaign_digest": self.digest(),
            },
        )

    def run_train(self, train_result: object | None = None) -> EvolutionCampaign:
        return replace(
            self,
            train_digest=_object_digest(train_result)
            if train_result is not None
            else self.train_digest,
        )

    def select_elites(
        self, train_result: object | None = None, *, elite_count: int | None = None
    ) -> EvolutionCampaign:
        train_digest = (
            _object_digest(train_result) if train_result is not None else self.train_digest
        )
        records = tuple(getattr(train_result, "selection_fitness_records", ()) or ())
        descriptors = tuple(getattr(train_result, "behavior_descriptors", ()) or ())
        ranked: list[tuple[float, str, str]] = []
        for record in records:
            organism_id = str(getattr(record, "organism_id", ""))
            if not organism_id:
                continue
            ranked.append(
                (
                    float(getattr(record, "selection_score", 0.0)),
                    organism_id,
                    _object_digest(record),
                )
            )
        if not ranked:
            for index, descriptor in enumerate(descriptors):
                ranked.append((0.0, f"descriptor_{index}", _object_digest(descriptor)))
        ranked = sorted(ranked, key=lambda item: (-item[0], item[1]))[
            : (elite_count or self.config.elite_count)
        ]
        elites = tuple(
            EliteLineage(
                organism_id=organism_id,
                lineage_digest=_digest({"train_digest": train_digest, "organism_id": organism_id}),
                replay_digest=evidence_digest,
                fitness_score=score,
                behavior_digest=evidence_digest,
            )
            for score, organism_id, evidence_digest in ranked
        )
        return replace(
            self,
            train_digest=train_digest,
            elite_selection=EliteSelectionResult(EvolutionPhase.ELITE_SELECTION, elites),
        )

    def replay_elites(self) -> EvolutionCampaign:
        elites = () if self.elite_selection is None else self.elite_selection.elites
        elite_digests = tuple(elite.digest() for elite in elites)
        replay = EliteReplayResult(
            replay_digest=_digest(
                {"elite_digests": list(elite_digests), "train_digest": self.train_digest}
            ),
            elite_digests=elite_digests,
            deterministic=True,
        )
        return replace(self, elite_replay=replay)

    def evaluate_heldout(
        self, heldout_result: object, train_result: object | None = None
    ) -> EvolutionCampaign:
        train_digest = (
            _object_digest(train_result) if train_result is not None else self.train_digest
        )
        heldout_digest = _object_digest(heldout_result)
        leakage_guard = bool(
            self.config.heldout_isolation and train_digest and train_digest != heldout_digest
        )
        score = _mean_selection_score(heldout_result)
        evaluation = HeldoutEvaluationResult(
            evaluation_digest=_digest(
                {"train_digest": train_digest, "heldout_digest": heldout_digest, "score": score}
            ),
            train_digest=train_digest,
            heldout_digest=heldout_digest,
            score=score,
            leakage_guard_passed=leakage_guard,
            status="measured" if leakage_guard else "provisional",
        )
        return replace(self, train_digest=train_digest, heldout_evaluation=evaluation)

    def evaluate_cross_partner(
        self,
        partner_result: object,
        train_result: object | None = None,
        *,
        partner_mode: str = "unfamiliar_partner",
    ) -> EvolutionCampaign:
        train_digest = (
            _object_digest(train_result) if train_result is not None else self.train_digest
        )
        partner_digest = _object_digest(partner_result)
        score = _mean_selection_score(partner_result)
        evaluation = CrossPartnerEvaluationResult(
            evaluation_digest=_digest(
                {
                    "train_digest": train_digest,
                    "partner_digest": partner_digest,
                    "score": score,
                    "partner_mode": partner_mode,
                }
            ),
            train_digest=train_digest,
            heldout_digest=partner_digest,
            score=score,
            leakage_guard_passed=bool(train_digest and train_digest != partner_digest),
            status="measured" if train_digest and train_digest != partner_digest else "provisional",
            partner_mode=partner_mode,
        )
        return replace(self, train_digest=train_digest, cross_partner_evaluation=evaluation)

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "config": self.config.to_dict(),
            "train_digest": self.train_digest,
            "elite_selection": None
            if self.elite_selection is None
            else self.elite_selection.to_dict(),
            "elite_replay": None if self.elite_replay is None else self.elite_replay.to_dict(),
            "heldout_evaluation": None
            if self.heldout_evaluation is None
            else self.heldout_evaluation.to_dict(),
            "cross_partner_evaluation": None
            if self.cross_partner_evaluation is None
            else self.cross_partner_evaluation.to_dict(),
        }

    def digest(self) -> str:
        return _digest(self.to_dict())


def _evolution_phase(value: EvolutionPhase | str) -> EvolutionPhase:
    if isinstance(value, EvolutionPhase):
        return value
    return EvolutionPhase(str(value))


def _object_digest(value: object | None) -> str:
    if value is None:
        return ""
    if isinstance(value, _Digestible):
        return value.digest()
    if isinstance(value, _DictSerializable):
        return _digest(value.to_dict())
    return _digest({"repr": repr(value)})


def _mean_selection_score(value: object) -> float:
    records = tuple(getattr(value, "selection_fitness_records", ()) or ())
    if not records:
        return 0.0
    return round(
        sum(float(getattr(record, "selection_score", 0.0)) for record in records) / len(records), 10
    )


def _digest(payload: dict[str, JsonValue]) -> str:
    from codontrace.genesis.canonical import canonical_digest

    return canonical_digest(payload)

# Phase 3 release-grade campaign primitives.
from codontrace.genesis.canonical import canonical_digest as _phase3_digest, require_finite_float as _phase3_finite

@dataclass(frozen=True, slots=True)
class Phase3MetricSpec:
    metric_id: str
    objective: str
    direction: str = "maximize"
    preregistered: bool = True
    schema_version: str = "phase3_metric_spec_v1"
    def __post_init__(self) -> None:
        if not self.metric_id or not self.objective:
            raise ValueError("Phase3MetricSpec requires metric_id and objective")
        if self.direction not in {"maximize", "minimize", "two_sided"}:
            raise ValueError("direction must be maximize/minimize/two_sided")
    def to_dict(self) -> dict[str, JsonValue]:
        return {"schema_version": self.schema_version, "metric_id": self.metric_id, "objective": self.objective, "direction": self.direction, "preregistered": self.preregistered}
    def digest(self) -> str:
        return _phase3_digest(self.to_dict())

@dataclass(frozen=True, slots=True)
class Phase3SeedPlan:
    seeds: tuple[int, ...]
    paired: bool = True
    deterministic_policy: str = "explicit_seed_tuple_v1"
    schema_version: str = "phase3_seed_plan_v1"
    def __post_init__(self) -> None:
        object.__setattr__(self, "seeds", tuple(int(s) for s in self.seeds))
        if len(self.seeds) != len(set(self.seeds)):
            raise ValueError("Phase3SeedPlan seeds must be unique")
        if not self.seeds:
            raise ValueError("Phase3SeedPlan requires at least one seed")
        if self.deterministic_policy != "explicit_seed_tuple_v1":
            raise ValueError("nondeterministic seed policy rejected")
    def to_dict(self) -> dict[str, JsonValue]:
        return {"schema_version": self.schema_version, "seeds": list(self.seeds), "paired": self.paired, "deterministic_policy": self.deterministic_policy}
    def digest(self) -> str:
        return _phase3_digest(self.to_dict())

@dataclass(frozen=True, slots=True)
class Phase3ControlPlan:
    positive_controls: tuple[str, ...] = ()
    negative_controls: tuple[str, ...] = ()
    ablations: tuple[str, ...] = ()
    heldout_required: bool = False
    schema_version: str = "phase3_control_plan_v1"
    def to_dict(self) -> dict[str, JsonValue]:
        return {"schema_version": self.schema_version, "positive_controls": list(self.positive_controls), "negative_controls": list(self.negative_controls), "ablations": list(self.ablations), "heldout_required": self.heldout_required}
    def digest(self) -> str:
        return _phase3_digest(self.to_dict())

@dataclass(frozen=True, slots=True)
class Phase3ScenarioSpec:
    scenario_family: str
    scenario_id: str
    config_digest: str
    world_digest: str
    feature_flags: tuple[str, ...] = ()
    control_flags: tuple[str, ...] = ()
    claim_ceiling: str = "instrumented_runtime"
    schema_version: str = "phase3_scenario_spec_v1"
    def __post_init__(self) -> None:
        if not self.scenario_family or not self.scenario_id or not self.config_digest or not self.world_digest:
            raise ValueError("Phase3ScenarioSpec requires family/id/config/world digests")
        object.__setattr__(self, "feature_flags", tuple(sorted(self.feature_flags)))
        object.__setattr__(self, "control_flags", tuple(sorted(self.control_flags)))
    def to_dict(self) -> dict[str, JsonValue]:
        return {"schema_version": self.schema_version, "scenario_family": self.scenario_family, "scenario_id": self.scenario_id, "config_digest": self.config_digest, "world_digest": self.world_digest, "feature_flags": list(self.feature_flags), "control_flags": list(self.control_flags), "claim_ceiling": self.claim_ceiling}
    def digest(self) -> str:
        return _phase3_digest(self.to_dict())

@dataclass(frozen=True, slots=True)
class Phase3CampaignSpec:
    campaign_id: str
    release_label: str
    seed_plan: Phase3SeedPlan
    control_plan: Phase3ControlPlan
    scenarios: tuple[Phase3ScenarioSpec, ...]
    preregistered_metrics: tuple[Phase3MetricSpec, ...]
    library_version: str = "0.3.0b1"
    schema_version: str = "phase3_campaign_spec_v1"
    def __post_init__(self) -> None:
        if not self.campaign_id or not self.release_label:
            raise ValueError("Phase3CampaignSpec requires campaign_id and release_label")
        if not self.scenarios:
            raise ValueError("Phase3CampaignSpec requires scenarios")
        if not self.preregistered_metrics:
            raise ValueError("Phase3CampaignSpec requires preregistered metrics")
    def to_dict(self) -> dict[str, JsonValue]:
        return {"schema_version": self.schema_version, "library_version": self.library_version, "release_label": self.release_label, "campaign_id": self.campaign_id, "seed_plan": self.seed_plan.to_dict(), "control_plan": self.control_plan.to_dict(), "scenarios": [s.to_dict() for s in self.scenarios], "preregistered_metrics": [m.to_dict() for m in self.preregistered_metrics]}
    def digest(self) -> str:
        return _phase3_digest(self.to_dict())

# Phase 3 P0/P1 strict final evidence-chain data contracts.
# Campaign primitives remain library-level and reject final/measured evidence objects backed by placeholder digests.
from codontrace.errors import ConfigurationError as _Phase3ConfigurationError
from codontrace.genesis.canonical import (
    PHASE3_CLAIM_GRADE_STATUSES as _CLAIM_ELIGIBLE_PHASE3_STATUSES,
    canonical_digest as _strict_digest,
    is_real_evidence_digest as _is_real_evidence_digest,
    require_phase3_status as _require_phase3_status,
    require_real_evidence_digest as _require_real_evidence_digest,
)

def _strict_status_reasons_for_digests(**digests: str) -> tuple[str, ...]:
    reasons: list[str] = []
    for name, value in digests.items():
        if not _is_real_evidence_digest(value):
            reasons.append(f"invalid_{name}")
    return tuple(reasons)


@dataclass(frozen=True, slots=True)
class Phase3RunRecord:
    run_id: str
    scenario_id: str
    seed: int
    manifest_digest: str
    replay_bundle_digest: str
    status: str = "measured"
    status_reason: str = ""
    schema_version: str = "phase3_run_record_v2"

    def __post_init__(self) -> None:
        if not self.run_id or not self.scenario_id:
            raise _Phase3ConfigurationError("Phase3RunRecord requires run_id and scenario_id.")
        _require_phase3_status("Phase3RunRecord.status", self.status)
        if self.status in _CLAIM_ELIGIBLE_PHASE3_STATUSES:
            _require_real_evidence_digest("manifest_digest", self.manifest_digest)
            _require_real_evidence_digest("replay_bundle_digest", self.replay_bundle_digest)
        elif not self.status_reason and (
            not _is_real_evidence_digest(self.manifest_digest)
            or not _is_real_evidence_digest(self.replay_bundle_digest)
        ):
            object.__setattr__(self, "status_reason", "non_claimable_digest_placeholder")

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "schema_version": self.schema_version,
            "run_id": self.run_id,
            "scenario_id": self.scenario_id,
            "seed": self.seed,
            "manifest_digest": self.manifest_digest,
            "replay_bundle_digest": self.replay_bundle_digest,
            "status": self.status,
            "status_reason": self.status_reason,
        }

    def digest(self) -> str:
        return _strict_digest(self.to_dict())


@dataclass(frozen=True, slots=True)
class Phase3CampaignManifest:
    campaign_spec_digest: str
    run_records_digest: str
    summary_digest: str
    claim_manifest_digest: str
    replay_bundle_digest: str
    release_label: str
    status: str = "provisional"
    rejection_reasons: tuple[str, ...] = ()
    schema_version: str = "phase3_campaign_manifest_v2"

    def __post_init__(self) -> None:
        _require_phase3_status("Phase3CampaignManifest.status", self.status)
        reasons = tuple(sorted(set(self.rejection_reasons)))
        reasons += _strict_status_reasons_for_digests(
            campaign_spec_digest=self.campaign_spec_digest,
            run_records_digest=self.run_records_digest,
            summary_digest=self.summary_digest,
        )
        if self.status in _CLAIM_ELIGIBLE_PHASE3_STATUSES:
            reasons += _strict_status_reasons_for_digests(
                claim_manifest_digest=self.claim_manifest_digest,
                replay_bundle_digest=self.replay_bundle_digest,
            )
            if reasons:
                raise _Phase3ConfigurationError(
                    "final Phase3CampaignManifest requires real digests: "
                    + ",".join(tuple(sorted(set(reasons))))
                )
        object.__setattr__(self, "rejection_reasons", tuple(sorted(set(reasons))))

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "schema_version": self.schema_version,
            "release_label": self.release_label,
            "campaign_spec_digest": self.campaign_spec_digest,
            "run_records_digest": self.run_records_digest,
            "summary_digest": self.summary_digest,
            "claim_manifest_digest": self.claim_manifest_digest,
            "replay_bundle_digest": self.replay_bundle_digest,
            "status": self.status,
            "rejection_reasons": list(self.rejection_reasons),
        }

    def digest(self) -> str:
        return _strict_digest(self.to_dict())


@dataclass(frozen=True, slots=True)
class Phase3CampaignResult:
    spec: Phase3CampaignSpec
    run_records: tuple[Phase3RunRecord, ...] = ()
    status: str = "empty_but_available"
    claim_manifest_digest: str = "not_run:claim_manifest"
    replay_bundle_digest: str = "not_run:replay_bundle"
    rejection_reasons: tuple[str, ...] = ()
    schema_version: str = "phase3_campaign_result_v2"

    def __post_init__(self) -> None:
        _require_phase3_status("Phase3CampaignResult.status", self.status)
        run_records = tuple(self.run_records)
        reasons = list(self.rejection_reasons)
        if self.status in _CLAIM_ELIGIBLE_PHASE3_STATUSES:
            if not run_records:
                reasons.append("missing_run_records")
            if not _is_real_evidence_digest(self.claim_manifest_digest):
                reasons.append("claim_manifest_missing")
            if not _is_real_evidence_digest(self.replay_bundle_digest):
                reasons.append("replay_bundle_missing")
            for record in run_records:
                if (
                    record.status not in _CLAIM_ELIGIBLE_PHASE3_STATUSES
                    or not _is_real_evidence_digest(record.manifest_digest)
                    or not _is_real_evidence_digest(record.replay_bundle_digest)
                ):
                    reasons.append(f"non_claimable_run_record:{record.run_id}")
            if reasons:
                raise _Phase3ConfigurationError(
                    "claim-grade Phase3CampaignResult has incomplete evidence: "
                    + ",".join(tuple(sorted(set(reasons))))
                )
        elif not reasons and (
            not _is_real_evidence_digest(self.claim_manifest_digest)
            or not _is_real_evidence_digest(self.replay_bundle_digest)
        ):
            reasons.append("non_claimable_final_digest_placeholder")
        object.__setattr__(self, "run_records", run_records)
        object.__setattr__(self, "rejection_reasons", tuple(sorted(set(reasons))))

    @property
    def manifest(self) -> Phase3CampaignManifest:
        run_digest = _strict_digest({"runs": [r.digest() for r in self.run_records]})
        summary_digest = _strict_digest(
            {
                "status": self.status,
                "run_count": len(self.run_records),
                "rejection_reasons": list(self.rejection_reasons),
            }
        )
        return Phase3CampaignManifest(
            self.spec.digest(),
            run_digest,
            summary_digest,
            self.claim_manifest_digest,
            self.replay_bundle_digest,
            self.spec.release_label,
            status=self.status,
            rejection_reasons=self.rejection_reasons,
        )

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "schema_version": self.schema_version,
            "spec": self.spec.to_dict(),
            "run_records": [r.to_dict() for r in self.run_records],
            "status": self.status,
            "claim_manifest_digest": self.claim_manifest_digest,
            "replay_bundle_digest": self.replay_bundle_digest,
            "rejection_reasons": list(self.rejection_reasons),
            "manifest": self.manifest.to_dict(),
        }

    def digest(self) -> str:
        return _strict_digest(self.to_dict())


@dataclass(frozen=True, slots=True)
class Phase3ExperimentLedger:
    campaign_digest: str
    run_record_digests: tuple[str, ...]
    evidence_lineage_digest: str
    claim_manifest_digest: str
    schema_version: str = "phase3_experiment_ledger_v2"

    def __post_init__(self) -> None:
        object.__setattr__(self, "run_record_digests", tuple(sorted(self.run_record_digests)))
        _require_real_evidence_digest("campaign_digest", self.campaign_digest)
        _require_real_evidence_digest("evidence_lineage_digest", self.evidence_lineage_digest)
        _require_real_evidence_digest("claim_manifest_digest", self.claim_manifest_digest)
        if not self.run_record_digests:
            raise _Phase3ConfigurationError("Phase3ExperimentLedger requires at least one run record digest.")
        for index, digest in enumerate(self.run_record_digests):
            _require_real_evidence_digest(f"run_record_digests[{index}]", digest)

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "schema_version": self.schema_version,
            "campaign_digest": self.campaign_digest,
            "run_record_digests": list(self.run_record_digests),
            "evidence_lineage_digest": self.evidence_lineage_digest,
            "claim_manifest_digest": self.claim_manifest_digest,
        }

    def digest(self) -> str:
        return _strict_digest(self.to_dict())
