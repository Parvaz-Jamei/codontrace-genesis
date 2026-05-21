"""Executable discovery experiment protocol scaffolds.

A discovery witness is not a proof unless it survives baseline, shadow/control,
persistence, lineage, multi-seed, ablation, QD novelty, replay, and review gates.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import Enum

from codontrace._types import JsonValue


class DiscoveryDecision(str, Enum):
    METADATA_ONLY = "metadata_only"
    CANDIDATE = "candidate"
    REPRODUCIBLE_CANDIDATE = "reproducible_candidate"
    SUPPORTED_BY_ABLATION = "supported_by_ablation"
    EXPERIMENTALLY_SUPPORTED_CANDIDATE = "experimentally_supported_candidate"


@dataclass(frozen=True, slots=True)
class DiscoveryExperimentConfig:
    require_d0: bool = True
    require_shadow: bool = True
    require_persistence: bool = True
    require_lineage: bool = True
    require_ablation: bool = True
    require_multiseed: bool = True
    require_replay: bool = True

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "require_d0": self.require_d0,
            "require_shadow": self.require_shadow,
            "require_persistence": self.require_persistence,
            "require_lineage": self.require_lineage,
            "require_ablation": self.require_ablation,
            "require_multiseed": self.require_multiseed,
            "require_replay": self.require_replay,
        }


@dataclass(frozen=True, slots=True)
class D0ExecutableBaseline:
    baseline_id: str
    manifest_digest: str
    metric: float

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "baseline_id": self.baseline_id,
            "manifest_digest": self.manifest_digest,
            "metric": self.metric,
        }


@dataclass(frozen=True, slots=True)
class ShadowRun:
    run_id: str
    manifest_digest: str
    candidate_persists: bool

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "run_id": self.run_id,
            "manifest_digest": self.manifest_digest,
            "candidate_persists": self.candidate_persists,
        }


@dataclass(frozen=True, slots=True)
class PersistenceFilter:
    window: int
    observed_ticks: int

    @property
    def passed(self) -> bool:
        return self.observed_ticks >= self.window

    def to_dict(self) -> dict[str, JsonValue]:
        return {"window": self.window, "observed_ticks": self.observed_ticks, "passed": self.passed}


@dataclass(frozen=True, slots=True)
class LineagePersistenceCheck:
    min_lineage_depth: int
    observed_depth: int

    @property
    def passed(self) -> bool:
        return self.observed_depth >= self.min_lineage_depth

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "min_lineage_depth": self.min_lineage_depth,
            "observed_depth": self.observed_depth,
            "passed": self.passed,
        }


@dataclass(frozen=True, slots=True)
class AblationMatrix:
    rows: tuple[dict[str, JsonValue], ...]

    @property
    def passed(self) -> bool:
        return bool(self.rows) and all(
            bool(row.get("effect_supported", False)) for row in self.rows
        )

    def to_dict(self) -> dict[str, JsonValue]:
        return {"rows": [dict(sorted(row.items())) for row in self.rows], "passed": self.passed}


@dataclass(frozen=True, slots=True)
class DiscoveryEffectSizeReport:
    metric_name: str
    candidate_metric: float
    baseline_metric: float

    @property
    def effect_size(self) -> float:
        return round(self.candidate_metric - self.baseline_metric, 10)

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "metric_name": self.metric_name,
            "candidate_metric": self.candidate_metric,
            "baseline_metric": self.baseline_metric,
            "effect_size": self.effect_size,
        }


@dataclass(frozen=True, slots=True)
class DiscoveryExperimentResult:
    candidate_id: str
    decision: DiscoveryDecision
    missing_gates: tuple[str, ...]
    d0: D0ExecutableBaseline | None = None
    shadow: ShadowRun | None = None
    persistence: PersistenceFilter | None = None
    lineage: LineagePersistenceCheck | None = None
    ablation: AblationMatrix | None = None
    effect_size: DiscoveryEffectSizeReport | None = None
    replay_verified: bool = False

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "candidate_id": self.candidate_id,
            "decision": self.decision.value,
            "missing_gates": list(self.missing_gates),
            "d0": None if self.d0 is None else self.d0.to_dict(),
            "shadow": None if self.shadow is None else self.shadow.to_dict(),
            "persistence": None if self.persistence is None else self.persistence.to_dict(),
            "lineage": None if self.lineage is None else self.lineage.to_dict(),
            "ablation": None if self.ablation is None else self.ablation.to_dict(),
            "effect_size": None if self.effect_size is None else self.effect_size.to_dict(),
            "replay_verified": self.replay_verified,
        }

    def digest(self) -> str:
        return _digest(self.to_dict())


@dataclass(frozen=True, slots=True)
class DiscoveryExperimentProtocol:
    config: DiscoveryExperimentConfig = field(default_factory=DiscoveryExperimentConfig)

    def evaluate(
        self,
        *,
        candidate_id: str,
        d0: D0ExecutableBaseline | None = None,
        shadow: ShadowRun | None = None,
        persistence: PersistenceFilter | None = None,
        lineage: LineagePersistenceCheck | None = None,
        ablation: AblationMatrix | None = None,
        effect_size: DiscoveryEffectSizeReport | None = None,
        multiseed_passed: bool = False,
        replay_verified: bool = False,
        review_approved: bool = False,
    ) -> DiscoveryExperimentResult:
        missing: list[str] = []
        if self.config.require_d0 and d0 is None:
            missing.append("d0_baseline")
        if self.config.require_shadow and (shadow is None or not shadow.candidate_persists):
            missing.append("shadow_run")
        if self.config.require_persistence and (persistence is None or not persistence.passed):
            missing.append("persistence")
        if self.config.require_lineage and (lineage is None or not lineage.passed):
            missing.append("lineage_persistence")
        if self.config.require_ablation and (ablation is None or not ablation.passed):
            missing.append("ablation_matrix")
        if self.config.require_multiseed and not multiseed_passed:
            missing.append("multiseed_repeatability")
        if self.config.require_replay and not replay_verified:
            missing.append("replay_verification")

        if missing:
            decision = (
                DiscoveryDecision.CANDIDATE if d0 is not None else DiscoveryDecision.METADATA_ONLY
            )
        elif ablation is not None and ablation.passed and review_approved:
            decision = DiscoveryDecision.EXPERIMENTALLY_SUPPORTED_CANDIDATE
        elif ablation is not None and ablation.passed:
            decision = DiscoveryDecision.SUPPORTED_BY_ABLATION
        else:
            decision = DiscoveryDecision.REPRODUCIBLE_CANDIDATE
        return DiscoveryExperimentResult(
            candidate_id,
            decision,
            tuple(missing),
            d0,
            shadow,
            persistence,
            lineage,
            ablation,
            effect_size,
            replay_verified,
        )


def _digest(payload: Mapping[str, JsonValue]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()
