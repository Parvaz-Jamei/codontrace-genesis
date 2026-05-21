"""Scientific discovery gate with D0, shadow, persistence, ablation, and replay checks."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass

from codontrace._types import JsonValue
from codontrace.genesis.canonical import require_finite_float


@dataclass(frozen=True, slots=True)
class DiscoveryGateConfig:
    require_d0: bool = True
    require_shadow: bool = True
    require_persistence: bool = True
    require_ablation: bool = True
    require_replay_verification: bool = True
    required_persistence_ticks: int = 3

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "require_d0": self.require_d0,
            "require_shadow": self.require_shadow,
            "require_persistence": self.require_persistence,
            "require_ablation": self.require_ablation,
            "require_replay_verification": self.require_replay_verification,
            "required_persistence_ticks": self.required_persistence_ticks,
        }


@dataclass(frozen=True, slots=True)
class D0CalibrationRun:
    baseline_digest: str
    distance_to_candidate: float
    passed: bool = True

    def __post_init__(self) -> None:
        object.__setattr__(self, "distance_to_candidate", require_finite_float("distance_to_candidate", self.distance_to_candidate, non_negative=True))

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "baseline_digest": self.baseline_digest,
            "distance_to_candidate": self.distance_to_candidate,
            "passed": self.passed,
        }


@dataclass(frozen=True, slots=True)
class ShadowRunResult:
    shadow_digest: str
    candidate_survives_shadow: bool

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "shadow_digest": self.shadow_digest,
            "candidate_survives_shadow": self.candidate_survives_shadow,
        }


@dataclass(frozen=True, slots=True)
class PersistenceResult:
    persisted_ticks: int
    required_ticks: int

    @property
    def passed(self) -> bool:
        return self.persisted_ticks >= self.required_ticks

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "persisted_ticks": self.persisted_ticks,
            "required_ticks": self.required_ticks,
            "passed": self.passed,
        }


@dataclass(frozen=True, slots=True)
class LineagePersistenceResult:
    lineage_depth: int
    offspring_count: int

    @property
    def passed(self) -> bool:
        return self.lineage_depth > 0 or self.offspring_count > 0

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "lineage_depth": self.lineage_depth,
            "offspring_count": self.offspring_count,
            "passed": self.passed,
        }


@dataclass(frozen=True, slots=True)
class AblationMatrixResult:
    matrix_digest: str
    completed: bool
    ablated_factors: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "matrix_digest": self.matrix_digest,
            "completed": self.completed,
            "ablated_factors": list(self.ablated_factors),
        }


@dataclass(frozen=True, slots=True)
class DiscoveryClaimDecision:
    level: str
    reasons: tuple[str, ...]

    def to_dict(self) -> dict[str, JsonValue]:
        return {"level": self.level, "reasons": list(self.reasons)}


@dataclass(frozen=True, slots=True)
class DiscoveryGateResult:
    candidate_id: str
    decision: DiscoveryClaimDecision
    d0: D0CalibrationRun | None = None
    shadow: ShadowRunResult | None = None
    persistence: PersistenceResult | None = None
    lineage_persistence: LineagePersistenceResult | None = None
    ablation: AblationMatrixResult | None = None
    replay_verified: bool = False
    qd_novelty_checked: bool = False
    review_status: str = "not_reviewed"
    manifest_digest: str | None = None

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "candidate_id": self.candidate_id,
            "decision": self.decision.to_dict(),
            "d0": None if self.d0 is None else self.d0.to_dict(),
            "shadow": None if self.shadow is None else self.shadow.to_dict(),
            "persistence": None if self.persistence is None else self.persistence.to_dict(),
            "lineage_persistence": None
            if self.lineage_persistence is None
            else self.lineage_persistence.to_dict(),
            "ablation": None if self.ablation is None else self.ablation.to_dict(),
            "replay_verified": self.replay_verified,
            "qd_novelty_checked": self.qd_novelty_checked,
            "review_status": self.review_status,
            "manifest_digest": self.manifest_digest,
        }

    def digest(self) -> str:
        return _digest(self.to_dict())


class DiscoveryGate:
    """Downgrade discovery claims unless required evidence is present."""

    def __init__(self, config: DiscoveryGateConfig | None = None) -> None:
        self.config = config or DiscoveryGateConfig()

    def evaluate(
        self,
        *,
        candidate_id: str,
        d0: D0CalibrationRun | None = None,
        shadow: ShadowRunResult | None = None,
        persistence: PersistenceResult | None = None,
        lineage_persistence: LineagePersistenceResult | None = None,
        ablation: AblationMatrixResult | None = None,
        replay_verified: bool = False,
        qd_novelty_checked: bool = False,
        review_status: str = "not_reviewed",
        manifest_digest: str | None = None,
    ) -> DiscoveryGateResult:
        reasons: list[str] = []
        if self.config.require_d0 and (d0 is None or not d0.passed):
            reasons.append("missing_or_failed_d0_baseline")
        if self.config.require_shadow and (shadow is None or not shadow.candidate_survives_shadow):
            reasons.append("missing_or_failed_shadow_run")
        if self.config.require_persistence and (persistence is None or not persistence.passed):
            reasons.append("missing_or_failed_persistence")
        if lineage_persistence is not None and not lineage_persistence.passed:
            reasons.append("failed_lineage_persistence")
        if self.config.require_ablation and (ablation is None or not ablation.completed):
            reasons.append("missing_or_failed_ablation_matrix")
        if self.config.require_replay_verification and not replay_verified:
            reasons.append("missing_replay_verification")
        if not qd_novelty_checked:
            reasons.append("missing_qd_novelty_check")
        if review_status not in {
            "reviewed",
            "accepted",
            "human_accept",
            "human_accepted",
            "not_required",
        }:
            reasons.append("review_needed")
        if not reasons:
            level = "supported_candidate"
        elif "missing_or_failed_d0_baseline" in reasons:
            level = "candidate_only"
        else:
            level = "review_needed"
        return DiscoveryGateResult(
            candidate_id=candidate_id,
            decision=DiscoveryClaimDecision(level, tuple(reasons)),
            d0=d0,
            shadow=shadow,
            persistence=persistence,
            lineage_persistence=lineage_persistence,
            ablation=ablation,
            replay_verified=replay_verified,
            qd_novelty_checked=qd_novelty_checked,
            review_status=review_status,
            manifest_digest=manifest_digest,
        )


def _digest(payload: Mapping[str, JsonValue]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()
