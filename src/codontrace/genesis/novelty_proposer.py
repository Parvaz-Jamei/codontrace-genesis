"""Novelty proposer Protocol and adapters for open-ended discovery audits.

External proposals cross a Pydantic boundary before becoming CandidateSpec.
RandomProposer and ExternalModelStubProposer are callable without paid APIs.
This module does not claim AGI, collective intelligence, or open-ended proof.
"""

from __future__ import annotations

import hashlib
import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable

from typing import Any

from codontrace._types import JsonValue
from codontrace.errors import ConfigurationError
from codontrace.genesis.discovery_witness import CandidateSpec
from codontrace.rng import RNGManager

try:
    from pydantic import BaseModel, ConfigDict, Field, ValidationError
except ImportError:  # pragma: no cover - optional at install time
    BaseModel = None  # type: ignore[misc, assignment]
    ConfigDict = None  # type: ignore[misc, assignment]
    Field = None  # type: ignore[misc, assignment]
    ValidationError = Exception  # type: ignore[misc, assignment]


@dataclass(frozen=True, slots=True)
class ArchiveSummary:
    """Cheap archive view passed to proposers (bounded; OMNI-EPIC lesson)."""

    archive_digest: str
    filled_bins: int
    coverage: float
    best_fitness: float | None
    mean_fitness: float | None
    descriptor_names: tuple[str, ...] = ()
    elite_genomes: tuple[str, ...] = ()
    metadata: dict[str, JsonValue] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.filled_bins < 0:
            raise ConfigurationError("ArchiveSummary.filled_bins must be >= 0.")
        if isinstance(self.coverage, bool) or not isinstance(self.coverage, int | float):
            raise ConfigurationError("ArchiveSummary.coverage must be numeric.")
        if not math.isfinite(float(self.coverage)):
            raise ConfigurationError("ArchiveSummary.coverage must be finite.")
        object.__setattr__(self, "coverage", float(self.coverage))
        object.__setattr__(self, "metadata", dict(self.metadata))
        object.__setattr__(self, "descriptor_names", tuple(self.descriptor_names))
        object.__setattr__(self, "elite_genomes", tuple(self.elite_genomes))

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "archive_digest": self.archive_digest,
            "filled_bins": self.filled_bins,
            "coverage": self.coverage,
            "best_fitness": self.best_fitness,
            "mean_fitness": self.mean_fitness,
            "descriptor_names": list(self.descriptor_names),
            "elite_genomes": list(self.elite_genomes),
            "metadata": dict(sorted(self.metadata.items())),
        }

    def digest(self) -> str:
        encoded = __import__("json").dumps(
            self.to_dict(), sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()

    def shuffled(self, *, seed: int) -> ArchiveSummary:
        """Permutation of elite genomes / descriptor names (proposer_shuffled_archive)."""

        rng = RNGManager(seed)

        def _permute(items: list[str]) -> list[str]:
            values = list(items)
            for index in range(len(values) - 1, 0, -1):
                swap_at = rng.randrange(0, index + 1)
                values[index], values[swap_at] = values[swap_at], values[index]
            return values

        elites = _permute(list(self.elite_genomes))
        names = _permute(list(self.descriptor_names))
        return ArchiveSummary(
            archive_digest=f"shuffled:{self.archive_digest}",
            filled_bins=self.filled_bins,
            coverage=self.coverage,
            best_fitness=self.best_fitness,
            mean_fitness=self.mean_fitness,
            descriptor_names=tuple(names),
            elite_genomes=tuple(elites),
            metadata={**self.metadata, "shuffled": True, "shuffle_seed": seed},
        )


@runtime_checkable
class NoveltyProposer(Protocol):
    """Protocol for proposing CandidateSpec from an archive summary."""

    def propose(self, archive_summary: ArchiveSummary) -> CandidateSpec: ...


@dataclass(frozen=True, slots=True)
class RandomProposer:
    """Negative / baseline proposer: samples the same parameter space at random."""

    seed: int = 1
    descriptor_names: tuple[str, ...] = ("unique_positions", "energy_efficiency")
    quality_low: float = 0.0
    quality_high: float = 1.0

    def propose(self, archive_summary: ArchiveSummary) -> CandidateSpec:
        rng = RNGManager(self.seed ^ (archive_summary.filled_bins * 1_000_003))
        names = self.descriptor_names or archive_summary.descriptor_names or ("d0",)
        descriptors = {name: rng.random() for name in names}
        quality = self.quality_low + rng.random() * (self.quality_high - self.quality_low)
        genome = f"RAND:{rng.randrange(0, 1_000_000):06d}"
        return CandidateSpec(
            candidate_id=f"random:{self.seed}:{genome}",
            genome=genome,
            descriptors=descriptors,
            quality=round(quality, 10),
            source="proposer_random",
            metadata={"seed": self.seed, "archive_digest": archive_summary.archive_digest},
        )


@dataclass(frozen=True, slots=True)
class ExternalModelStubProposer:
    """Deterministic external-model *stub* — no paid API; tests call it freely.

    Mimics an FM-guided proposer that conditions lightly on archive coverage
    (ASAL lesson: keep substrate cheap; model outside the hot loop).
    """

    seed: int = 42
    model_name: str = "stub-novelty-v0"
    descriptor_names: tuple[str, ...] = ("unique_positions", "energy_efficiency")

    def propose(self, archive_summary: ArchiveSummary) -> CandidateSpec:
        rng = RNGManager(self.seed + archive_summary.filled_bins)
        names = self.descriptor_names or archive_summary.descriptor_names or ("d0",)
        # Stub heuristic: nudge descriptors away from mean coverage proxy.
        bias = min(1.0, max(0.0, 1.0 - archive_summary.coverage))
        descriptors = {
            name: round(min(1.0, rng.random() * 0.5 + bias * 0.5), 10) for name in names
        }
        base = archive_summary.mean_fitness if archive_summary.mean_fitness is not None else 0.2
        quality = round(min(1.0, max(0.0, float(base) + 0.05 + rng.random() * 0.1)), 10)
        genome = f"STUB:{self.model_name}:{rng.randrange(0, 1_000_000):06d}"
        return CandidateSpec(
            candidate_id=f"stub:{self.seed}:{genome}",
            genome=genome,
            descriptors=descriptors,
            quality=quality,
            source="external_model_stub",
            metadata={
                "model_name": self.model_name,
                "seed": self.seed,
                "archive_digest": archive_summary.archive_digest,
                "paid_api": False,
            },
        )


if BaseModel is not None:

    class ExternalCandidateProposalModel(BaseModel):
        """Untrusted-boundary schema for external / ESP32-adjacent payloads."""

        model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

        candidate_id: str = Field(min_length=1)
        genome: str = ""
        descriptors: dict[str, float] = Field(default_factory=dict)
        quality: float = 0.0
        source: str = "external"
        metadata: dict[str, Any] = Field(default_factory=dict)

else:  # pragma: no cover

    class ExternalCandidateProposalModel:  # type: ignore[no-redef]
        """Placeholder when pydantic is not installed."""

        def __init__(self, **kwargs: object) -> None:
            raise ConfigurationError(
                "pydantic is required to parse untrusted external proposals. "
                "Install codontrace[dev] or pydantic>=2."
            )


def parse_external_proposal(raw: Mapping[str, object]) -> CandidateSpec:
    """Validate untrusted mapping via Pydantic, then freeze as CandidateSpec."""

    if BaseModel is None:
        raise ConfigurationError(
            "pydantic is required to parse untrusted external proposals. "
            "Install codontrace[dev] or pydantic>=2."
        )
    try:
        model = ExternalCandidateProposalModel.model_validate(dict(raw))
    except ValidationError as exc:
        raise ConfigurationError(f"external proposal failed validation: {exc}") from exc
    payload = model.model_dump()
    return CandidateSpec(
        candidate_id=str(payload["candidate_id"]),
        genome=str(payload["genome"]),
        descriptors={str(k): float(v) for k, v in dict(payload["descriptors"]).items()},
        quality=float(payload["quality"]),
        source=str(payload["source"]),
        metadata=dict(payload.get("metadata") or {}),
    )


def empty_archive_summary(*, digest: str = "empty") -> ArchiveSummary:
    return ArchiveSummary(
        archive_digest=digest,
        filled_bins=0,
        coverage=0.0,
        best_fitness=None,
        mean_fitness=None,
        descriptor_names=("unique_positions", "energy_efficiency"),
        elite_genomes=(),
    )


def archive_summary_from_qd(
    *,
    archive_digest: str,
    filled_bins: int,
    coverage: float,
    best_fitness: float | None,
    mean_fitness: float | None,
    descriptor_names: Sequence[str] = (),
    elite_genomes: Sequence[str] = (),
) -> ArchiveSummary:
    """Adapter from quality_diversity / qd_search summaries into ArchiveSummary."""

    return ArchiveSummary(
        archive_digest=archive_digest,
        filled_bins=int(filled_bins),
        coverage=float(coverage),
        best_fitness=best_fitness,
        mean_fitness=mean_fitness,
        descriptor_names=tuple(str(item) for item in descriptor_names),
        elite_genomes=tuple(str(item) for item in elite_genomes),
    )


__all__ = [
    "ArchiveSummary",
    "ExternalCandidateProposalModel",
    "ExternalModelStubProposer",
    "NoveltyProposer",
    "RandomProposer",
    "archive_summary_from_qd",
    "empty_archive_summary",
    "parse_external_proposal",
]
