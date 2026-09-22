"""Discovery/D0/ablation runner contracts for GENESIS evidence workflows.

These are lightweight contract objects. They identify candidates and evidence
needs; they do not prove discovery, open-endedness, or artificial life.
"""

from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Literal

from codontrace._types import JsonValue
from codontrace.errors import ConfigurationError
from codontrace.genesis.canonical import canonical_digest
from codontrace.genesis.discovery_witness import (
    CLAIM_CEILING_DISCOVERY_CANDIDATE,
    CLAIM_CEILING_RUNTIME,
    CandidateSpec,
    DiscoveryAuditReport,
    NegativeControlResult,
)
from codontrace.genesis.novelty_proposer import (
    ArchiveSummary,
    RandomProposer,
    empty_archive_summary,
)


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


# --- Open-ended discovery ClaimGate pipeline (waves الف–د) -----------------


DiscoveryPipelineScale = Literal["S1", "S2", "research"]

_PROTOCOL_ID = "open_ended_discovery_claimgate_pipeline_v2"
_SCALE_MARGIN: dict[str, float] = {
    "S1": 0.15,
    "S2": 0.20,
    "research": 0.25,
}
_SCALE_SEEDS: dict[str, int] = {
    "S1": 11,
    "S2": 22,
    "research": 33,
}


def score_candidate(
    candidate: CandidateSpec,
    archive_summary: ArchiveSummary,
    *,
    seed: int = 0,
) -> float:
    """Cheap deterministic novelty/quality score (substrate stays cheap — ASAL)."""

    desc_values = list(candidate.descriptors.values())
    diversity = 0.0
    if desc_values:
        mean = sum(desc_values) / len(desc_values)
        diversity = sum(abs(value - mean) for value in desc_values) / len(desc_values)
    coverage_gap = max(0.0, 1.0 - archive_summary.coverage)
    archive_bonus = 0.05 * math.log1p(max(0, archive_summary.filled_bins))
    # Tiny seed salt keeps scores stable but distinguishes control draws.
    salt = ((seed * 1_000_003) % 997) / 9970.0
    return round(float(candidate.quality) + 0.5 * diversity + 0.2 * coverage_gap + archive_bonus + salt, 10)


def _archive_no_op_candidate() -> CandidateSpec:
    return CandidateSpec(
        candidate_id="archive_no_op",
        genome="",
        descriptors={},
        quality=0.0,
        source="archive_no_op",
        metadata={"neutral": True},
    )


def _build_negative_controls(
    candidate: CandidateSpec,
    archive_summary: ArchiveSummary,
    *,
    scale: str,
    candidate_score: float,
) -> tuple[NegativeControlResult, ...]:
    from codontrace.genesis.novelty_proposer import ExternalModelStubProposer

    seed = _SCALE_SEEDS[scale]
    random_prop = RandomProposer(seed=seed + 101)
    random_candidate = random_prop.propose(archive_summary)
    random_score = score_candidate(random_candidate, archive_summary, seed=seed + 1)

    # Same external-model stub, but archive_summary is shuffled before propose
    # (HE01 / goal §7: does the proposer actually use the archive summary?).
    shuffled = archive_summary.shuffled(seed=seed + 202)
    shuffled_prop = ExternalModelStubProposer(seed=seed + 303)
    shuffled_candidate = shuffled_prop.propose(shuffled)
    shuffled_score = score_candidate(shuffled_candidate, shuffled, seed=seed + 2)

    no_op = _archive_no_op_candidate()
    no_op_score = score_candidate(no_op, archive_summary, seed=seed + 3)

    return (
        NegativeControlResult(
            control_id="proposer_random",
            score=random_score,
            candidate_digest=random_candidate.digest(),
            reasons=("random_proposer_baseline",),
        ),
        NegativeControlResult(
            control_id="proposer_shuffled_archive",
            score=shuffled_score,
            candidate_digest=shuffled_candidate.digest(),
            reasons=(
                "archive_summary_shuffled_before_propose",
                f"delta={round(candidate_score - shuffled_score, 10)}",
            ),
        ),
        NegativeControlResult(
            control_id="archive_no_op",
            score=no_op_score,
            candidate_digest=no_op.digest(),
            reasons=("neutral_archive_admission_probe",),
        ),
    )


def run_discovery_pipeline(
    candidate: CandidateSpec,
    *,
    scale: DiscoveryPipelineScale = "S1",
    archive_summary: ArchiveSummary | None = None,
) -> DiscoveryAuditReport:
    """Mandatory audit before archive admission (Flageat et al. 2026 trade-off).

    Ceiling rises above ``runtime_observation`` only when the candidate is
    meaningfully better than all three HE01-style discovery negatives.
    """

    if scale not in _SCALE_MARGIN:
        raise ConfigurationError(f"unsupported discovery scale: {scale!r}")
    archive = archive_summary or empty_archive_summary()
    margin = _SCALE_MARGIN[scale]
    seed = _SCALE_SEEDS[scale]
    novelty_score = score_candidate(candidate, archive, seed=seed)
    negatives = _build_negative_controls(
        candidate, archive, scale=scale, candidate_score=novelty_score
    )
    beat_flags = tuple(novelty_score > (control.score + margin) for control in negatives)
    beat_all = all(beat_flags)
    reasons: list[str] = []
    if not beat_flags[0]:
        reasons.append("not_better_than_proposer_random")
    if not beat_flags[1]:
        reasons.append("not_better_than_proposer_shuffled_archive")
    if not beat_flags[2]:
        reasons.append("not_better_than_archive_no_op")
    if beat_all:
        reasons.append("meaningfully_better_than_all_three_negatives")
        accepted = True
        claim_ceiling = CLAIM_CEILING_DISCOVERY_CANDIDATE
    else:
        reasons.append("held_at_runtime_observation")
        accepted = False
        claim_ceiling = CLAIM_CEILING_RUNTIME

    protocol_digest = canonical_digest(
        {
            "protocol_id": _PROTOCOL_ID,
            "scale": scale,
            "margin": margin,
            "negatives": ["proposer_random", "proposer_shuffled_archive", "archive_no_op"],
            "literature": [
                "ASAL_Kumar_et_al_2024_arXiv_2412_17799",
                "Flageat_Janmohamed_Lim_Cully_IEEE_TEVC_2026_arXiv_2409_13315",
                "MAP_Elites_Mouret_Clune_2015",
                "HE01_three_discovery_negatives",
            ],
        }
    )
    replay_digest = canonical_digest(
        {
            "candidate_digest": candidate.digest(),
            "archive_digest": archive.archive_digest,
            "novelty_score": novelty_score,
            "scale": scale,
        }
    )
    return DiscoveryAuditReport(
        candidate_id=candidate.candidate_id,
        candidate_digest=candidate.digest(),
        scale=scale,
        accepted=accepted,
        claim_ceiling=claim_ceiling,
        novelty_score=novelty_score,
        margin=margin,
        negative_controls=negatives,
        beat_all_negatives=beat_all,
        reasons=tuple(reasons),
        replay_digest=replay_digest,
        protocol_digest=protocol_digest,
    )


def hand_crafted_demo_candidates() -> tuple[CandidateSpec, ...]:
    """Three fixed candidates for pipeline unit tests (not from a model)."""

    weak = CandidateSpec(
        candidate_id="hand_weak",
        genome="WAIT",
        descriptors={"unique_positions": 0.1, "energy_efficiency": 0.1},
        quality=0.05,
        source="hand_crafted",
        metadata={"expected": "reject"},
    )
    mid = CandidateSpec(
        candidate_id="hand_mid",
        genome="MOVE:EAT",
        descriptors={"unique_positions": 0.4, "energy_efficiency": 0.35},
        quality=0.35,
        source="hand_crafted",
        metadata={"expected": "reject_or_borderline"},
    )
    # High quality + diverse descriptors — still must beat all three negatives.
    strong = CandidateSpec(
        candidate_id="hand_strong",
        genome="EXPLORE:CACHE:SHARE",
        descriptors={"unique_positions": 0.95, "energy_efficiency": 0.05},
        quality=0.98,
        source="hand_crafted",
        metadata={"expected": "accept_if_beats_negatives"},
    )
    return (weak, mid, strong)
