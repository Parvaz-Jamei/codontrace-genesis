"""Discovery/D0/ablation runner contracts for GENESIS evidence workflows.

These are lightweight contract objects. They identify candidates and evidence
needs; they do not prove discovery, open-endedness, or artificial life.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field

from codontrace._types import JsonValue


@dataclass(frozen=True, slots=True)
class DiscoveryCandidateQueue:
    candidates: tuple[dict[str, JsonValue], ...] = ()

    def push(self, candidate: Mapping[str, JsonValue]) -> DiscoveryCandidateQueue:
        return DiscoveryCandidateQueue((*self.candidates, dict(candidate)))

    def to_dict(self) -> dict[str, JsonValue]:
        return {"candidates": [dict(item) for item in self.candidates]}


@dataclass(frozen=True, slots=True)
class DiscoveryDetectionResult:
    candidate_digest: str
    status: str
    novelty_score: float
    persistence_ticks: int
    reason: str

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "candidate_digest": self.candidate_digest,
            "status": self.status,
            "novelty_score": self.novelty_score,
            "persistence_ticks": self.persistence_ticks,
            "reason": self.reason,
        }

    def digest(self) -> str:
        return _digest(self.to_dict())


@dataclass(frozen=True, slots=True)
class MultiSeedProtocol:
    seeds: tuple[int, ...]
    min_replicates: int = 3

    def to_dict(self) -> dict[str, JsonValue]:
        return {"seeds": list(self.seeds), "min_replicates": self.min_replicates}

    def digest(self) -> str:
        return _digest(self.to_dict())


@dataclass(frozen=True, slots=True)
class DiscoveryReviewPack:
    detection_result: DiscoveryDetectionResult
    multi_seed_protocol: MultiSeedProtocol
    manifest_digest: str | None = None

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "detection_result": self.detection_result.to_dict(),
            "multi_seed_protocol": self.multi_seed_protocol.to_dict(),
            "manifest_digest": self.manifest_digest,
        }


@dataclass(frozen=True, slots=True)
class D0BaselineRunner:
    baseline_config: dict[str, JsonValue]

    @classmethod
    def from_config(cls, config: Mapping[str, JsonValue]) -> D0BaselineRunner:
        return cls(baseline_config=dict(config))

    def digest(self) -> str:
        return _digest(self.baseline_config)


@dataclass(frozen=True, slots=True)
class PersistenceChecker:
    min_ticks: int = 3

    def check(self, observations: Sequence[object]) -> int:
        return min(len(observations), self.min_ticks)


@dataclass(frozen=True, slots=True)
class DiscoveryDetector:
    novelty_threshold: float = 0.1
    persistence_checker: PersistenceChecker = field(default_factory=PersistenceChecker)

    def evaluate(
        self,
        candidate: Mapping[str, JsonValue],
        *,
        d0_digest: str | None = None,
        observations: Sequence[object] = (),
    ) -> DiscoveryDetectionResult:
        digest = _digest(dict(candidate))
        novelty = _numeric(candidate.get("novelty_score"), 0.0)
        persistence = self.persistence_checker.check(observations)
        if d0_digest is None:
            status = "review_needed"
            reason = "candidate_without_d0_is_not_proof"
        elif novelty < self.novelty_threshold:
            status = "insufficient_evidence"
            reason = "novelty_below_threshold"
        elif persistence < self.persistence_checker.min_ticks:
            status = "review_needed"
            reason = "persistence_not_established"
        else:
            status = "review_needed"
            reason = "candidate_requires_ablation_and_external_review"
        return DiscoveryDetectionResult(digest, status, round(novelty, 10), persistence, reason)


@dataclass(frozen=True, slots=True)
class AblationRunner:
    base_config: dict[str, JsonValue]

    def make_diff(self, disabled_component: str) -> dict[str, JsonValue]:
        return {"disable": disabled_component, "base_config_digest": _digest(self.base_config)}


@dataclass(frozen=True, slots=True)
class DiscoveryCandidateFromQD:
    organism_id: str
    novelty_score: float
    archive_digest: str
    metadata: dict[str, JsonValue] = field(default_factory=dict)

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "organism_id": self.organism_id,
            "novelty_score": self.novelty_score,
            "archive_digest": self.archive_digest,
            "metadata": dict(sorted(self.metadata.items())),
        }


def _digest(payload: Mapping[str, JsonValue]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _numeric(value: object, default: float) -> float:
    if isinstance(value, bool) or not isinstance(value, int | float):
        return default
    return float(value)
