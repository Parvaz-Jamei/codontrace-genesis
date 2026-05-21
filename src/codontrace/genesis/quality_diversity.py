"""Quality-Diversity archive hooks for GENESIS experiments.

This module provides dependency-free MAP-Elites-like archive data structures,
validation helpers, deterministic update helpers, and summaries. It does not
implement a search loop, plotting, file output, report generation, or any proof
of open-ended discovery.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import cast

from codontrace._types import JsonValue
from codontrace.errors import ConfigurationError
from codontrace._numeric import finite_float, finite_json_dumps


@dataclass(frozen=True, slots=True)
class BehaviorDescriptorSchema:
    """Configurable descriptor dimensions and binning contract."""

    descriptor_names: tuple[str, ...]
    bins_per_descriptor: dict[str, int]
    min_values: dict[str, float]
    max_values: dict[str, float]
    out_of_range_policy: str = "clip"

    def __post_init__(self) -> None:
        if not self.descriptor_names:
            msg = "BehaviorDescriptorSchema.descriptor_names must not be empty."
            raise ConfigurationError(msg)
        if self.out_of_range_policy not in {"clip", "reject"}:
            msg = "out_of_range_policy must be 'clip' or 'reject'."
            raise ConfigurationError(msg)
        if len(set(self.descriptor_names)) != len(self.descriptor_names):
            msg = "BehaviorDescriptorSchema.descriptor_names must be unique."
            raise ConfigurationError(msg)
        clean_min: dict[str, float] = {}
        clean_max: dict[str, float] = {}
        clean_bins: dict[str, int] = {}
        for name in self.descriptor_names:
            bins = self.bins_per_descriptor.get(name, 0)
            if isinstance(bins, bool) or not isinstance(bins, int) or bins <= 0:
                msg = f"bins_per_descriptor[{name!r}] must be positive."
                raise ConfigurationError(msg)
            min_value = finite_float(f"min_values[{name!r}]", self.min_values.get(name, 0.0))
            max_value = finite_float(f"max_values[{name!r}]", self.max_values.get(name, 0.0))
            if max_value <= min_value:
                msg = f"max_values[{name!r}] must be greater than min_values."
                raise ConfigurationError(msg)
            clean_bins[name] = bins
            clean_min[name] = min_value
            clean_max[name] = max_value
        object.__setattr__(self, "bins_per_descriptor", clean_bins)
        object.__setattr__(self, "min_values", clean_min)
        object.__setattr__(self, "max_values", clean_max)

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "descriptor_names": list(self.descriptor_names),
            "bins_per_descriptor": dict(sorted(self.bins_per_descriptor.items())),
            "min_values": dict(sorted(self.min_values.items())),
            "max_values": dict(sorted(self.max_values.items())),
            "out_of_range_policy": self.out_of_range_policy,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, JsonValue]) -> BehaviorDescriptorSchema:
        return cls(
            descriptor_names=_str_tuple(data, "descriptor_names"),
            bins_per_descriptor=_int_map(data.get("bins_per_descriptor"), "bins_per_descriptor"),
            min_values=_float_map(data.get("min_values"), "min_values"),
            max_values=_float_map(data.get("max_values"), "max_values"),
            out_of_range_policy=_str(data, "out_of_range_policy", "clip"),
        )

    def digest(self) -> str:
        return _digest(self.to_dict())


@dataclass(frozen=True, slots=True)
class BehaviorBin:
    """One discretized behavior cell."""

    indices: tuple[int, ...]

    def __post_init__(self) -> None:
        if not self.indices:
            msg = "BehaviorBin.indices must not be empty."
            raise ConfigurationError(msg)
        if any(
            isinstance(item, bool) or not isinstance(item, int) or item < 0 for item in self.indices
        ):
            msg = "BehaviorBin.indices must be non-negative integers."
            raise ConfigurationError(msg)

    def to_dict(self) -> dict[str, JsonValue]:
        return {"indices": list(self.indices)}

    @classmethod
    def from_dict(cls, data: Mapping[str, JsonValue]) -> BehaviorBin:
        return cls(indices=_int_tuple(data, "indices"))

    def key(self) -> tuple[int, ...]:
        return self.indices

    def digest(self) -> str:
        return _digest(self.to_dict())


@dataclass(frozen=True, slots=True)
class QDElite:
    """Best candidate stored for one behavior bin."""

    organism_id: str
    fitness: float
    behavior_descriptor: dict[str, float]
    behavior_bin: BehaviorBin
    genome_digest: str
    trace_digest: str
    metadata: dict[str, JsonValue] = field(default_factory=dict)
    behavior_digest: str = ""

    def __post_init__(self) -> None:
        if not self.organism_id:
            msg = "QDElite.organism_id must not be empty."
            raise ConfigurationError(msg)
        object.__setattr__(self, "fitness", finite_float("QDElite.fitness", self.fitness))
        copied_descriptor = dict(self.behavior_descriptor)
        copied_metadata = dict(self.metadata)
        _validate_descriptor(copied_descriptor)
        object.__setattr__(self, "behavior_descriptor", copied_descriptor)
        object.__setattr__(self, "metadata", copied_metadata)
        if not self.behavior_digest:
            object.__setattr__(
                self,
                "behavior_digest",
                _digest({"behavior_descriptor": dict(sorted(copied_descriptor.items()))}),
            )

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "organism_id": self.organism_id,
            "fitness": self.fitness,
            "behavior_descriptor": dict(sorted(self.behavior_descriptor.items())),
            "behavior_bin": self.behavior_bin.to_dict(),
            "genome_digest": self.genome_digest,
            "trace_digest": self.trace_digest,
            "behavior_digest": self.behavior_digest,
            "metadata": dict(sorted(self.metadata.items())),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, JsonValue]) -> QDElite:
        raw_bin = data.get("behavior_bin")
        if not isinstance(raw_bin, Mapping):
            msg = "QDElite.behavior_bin must be an object."
            raise ConfigurationError(msg)
        return cls(
            organism_id=_str(data, "organism_id"),
            fitness=_float(data, "fitness", 0.0),
            behavior_descriptor=_float_map(data.get("behavior_descriptor"), "behavior_descriptor"),
            behavior_bin=BehaviorBin.from_dict(raw_bin),
            genome_digest=_str(data, "genome_digest"),
            trace_digest=_str(data, "trace_digest"),
            metadata=_metadata(data.get("metadata", {})),
            behavior_digest=_str(data, "behavior_digest", ""),
        )

    def digest(self) -> str:
        return _digest(self.to_dict())


@dataclass(frozen=True, slots=True)
class QDArchivePolicy:
    """Replacement and audit policy for an immutable QD archive."""

    replacement_policy: str = "higher_fitness"
    allow_equal_fitness_replace: bool = False
    track_rejected_candidates: bool = True
    max_elites: int | None = None
    max_rejected_records: int = 100
    require_behavior_digest: bool = True
    require_trace_digest: bool = True

    def __post_init__(self) -> None:
        if self.replacement_policy not in {
            "higher_fitness",
            "novelty_then_fitness",
            "first_wins",
            "latest_wins",
        }:
            msg = "Unsupported QDArchivePolicy.replacement_policy."
            raise ConfigurationError(msg)
        if self.max_elites is not None and self.max_elites <= 0:
            msg = "QDArchivePolicy.max_elites must be positive or None."
            raise ConfigurationError(msg)
        if self.max_rejected_records < 0:
            msg = "QDArchivePolicy.max_rejected_records must be >= 0."
            raise ConfigurationError(msg)

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "replacement_policy": self.replacement_policy,
            "allow_equal_fitness_replace": self.allow_equal_fitness_replace,
            "track_rejected_candidates": self.track_rejected_candidates,
            "max_elites": self.max_elites,
            "max_rejected_records": self.max_rejected_records,
            "require_behavior_digest": self.require_behavior_digest,
            "require_trace_digest": self.require_trace_digest,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, JsonValue]) -> QDArchivePolicy:
        return cls(
            replacement_policy=_str(data, "replacement_policy", "higher_fitness"),
            allow_equal_fitness_replace=_bool(data, "allow_equal_fitness_replace", False),
            track_rejected_candidates=_bool(data, "track_rejected_candidates", True),
            max_elites=_optional_int(data.get("max_elites"), "max_elites"),
            max_rejected_records=_int(data, "max_rejected_records", 100),
            require_behavior_digest=_bool(data, "require_behavior_digest", True),
            require_trace_digest=_bool(data, "require_trace_digest", True),
        )

    def digest(self) -> str:
        return _digest(self.to_dict())


@dataclass(frozen=True, slots=True)
class QDArchiveConfig:
    """Archive configuration; no search loop is included."""

    schema: BehaviorDescriptorSchema
    keep_one_elite_per_bin: bool = True
    policy: QDArchivePolicy = field(default_factory=QDArchivePolicy)
    archive_id: str = "qd:default"
    archive_metadata: dict[str, JsonValue] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.archive_id:
            msg = "QDArchiveConfig.archive_id must not be empty."
            raise ConfigurationError(msg)
        if not self.keep_one_elite_per_bin:
            msg = (
                "QDArchiveConfig.keep_one_elite_per_bin=False is reserved; "
                "multi-elite bins are not implemented in this alpha."
            )
            raise ConfigurationError(msg)
        object.__setattr__(self, "archive_metadata", dict(self.archive_metadata))

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "schema": self.schema.to_dict(),
            "keep_one_elite_per_bin": self.keep_one_elite_per_bin,
            "policy": self.policy.to_dict(),
            "archive_id": self.archive_id,
            "archive_metadata": dict(sorted(self.archive_metadata.items())),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, JsonValue]) -> QDArchiveConfig:
        raw_schema = data.get("schema")
        if not isinstance(raw_schema, Mapping):
            msg = "QDArchiveConfig.schema must be an object."
            raise ConfigurationError(msg)
        raw_policy = data.get("policy", {})
        if raw_policy is None:
            raw_policy = {}
        if not isinstance(raw_policy, Mapping):
            msg = "QDArchiveConfig.policy must be an object."
            raise ConfigurationError(msg)
        return cls(
            schema=BehaviorDescriptorSchema.from_dict(raw_schema),
            keep_one_elite_per_bin=_bool(data, "keep_one_elite_per_bin", True),
            policy=QDArchivePolicy.from_dict(raw_policy),
            archive_id=_str(data, "archive_id", "qd:default"),
            archive_metadata=_metadata(data.get("archive_metadata", {})),
        )

    def digest(self) -> str:
        return _digest(self.to_dict())


@dataclass(frozen=True, slots=True)
class QDArchiveRejectedCandidate:
    """Auditable rejection record for a candidate not stored as an elite."""

    candidate_digest: str
    behavior_bin: BehaviorBin
    fitness: float
    reason: str
    existing_elite_digest: str | None = None
    metadata: dict[str, JsonValue] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "metadata", dict(self.metadata))

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "candidate_digest": self.candidate_digest,
            "behavior_bin": self.behavior_bin.to_dict(),
            "fitness": self.fitness,
            "reason": self.reason,
            "existing_elite_digest": self.existing_elite_digest,
            "metadata": dict(sorted(self.metadata.items())),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, JsonValue]) -> QDArchiveRejectedCandidate:
        raw_bin = data.get("behavior_bin")
        if not isinstance(raw_bin, Mapping):
            msg = "QDArchiveRejectedCandidate.behavior_bin must be an object."
            raise ConfigurationError(msg)
        return cls(
            candidate_digest=_str(data, "candidate_digest"),
            behavior_bin=BehaviorBin.from_dict(raw_bin),
            fitness=_float(data, "fitness", 0.0),
            reason=_str(data, "reason"),
            existing_elite_digest=_optional_str(
                data.get("existing_elite_digest"), "existing_elite_digest"
            ),
            metadata=_metadata(data.get("metadata", {})),
        )

    def digest(self) -> str:
        return _digest(self.to_dict())


@dataclass(frozen=True, slots=True)
class QDArchive:
    """Immutable QD archive snapshot."""

    config: QDArchiveConfig
    elites: dict[tuple[int, ...], QDElite] = field(default_factory=dict)
    rejected: tuple[QDArchiveRejectedCandidate, ...] = ()
    replacement_count: int = 0

    @classmethod
    def empty(cls, config: QDArchiveConfig) -> QDArchive:
        return cls(config=config, elites={}, rejected=(), replacement_count=0)

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "config": self.config.to_dict(),
            "elites": [elite.to_dict() for _, elite in sorted(self.elites.items())],
            "rejected": [item.to_dict() for item in self.rejected],
            "replacement_count": self.replacement_count,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, JsonValue]) -> QDArchive:
        raw_config = data.get("config")
        raw_elites = data.get("elites", [])
        raw_rejected = data.get("rejected", [])
        if not isinstance(raw_config, Mapping):
            msg = "QDArchive.config must be an object."
            raise ConfigurationError(msg)
        if not isinstance(raw_elites, list):
            msg = "QDArchive.elites must be a list."
            raise ConfigurationError(msg)
        if not isinstance(raw_rejected, list):
            msg = "QDArchive.rejected must be a list."
            raise ConfigurationError(msg)
        elites: dict[tuple[int, ...], QDElite] = {}
        for item in raw_elites:
            if not isinstance(item, Mapping):
                msg = "QDArchive elite entries must be objects."
                raise ConfigurationError(msg)
            elite = QDElite.from_dict(item)
            elites[elite.behavior_bin.key()] = elite
        rejected = tuple(
            QDArchiveRejectedCandidate.from_dict(_mapping(item, "rejected"))
            for item in raw_rejected
        )
        return cls(
            config=QDArchiveConfig.from_dict(raw_config),
            elites=elites,
            rejected=rejected,
            replacement_count=_int(data, "replacement_count", 0),
        )

    def digest(self) -> str:
        return _digest(self.to_dict())


@dataclass(frozen=True, slots=True)
class QDArchiveUpdateResult:
    """Result of adding, replacing, or rejecting one candidate elite."""

    archive: QDArchive
    inserted: bool
    replaced: bool
    behavior_bin: BehaviorBin
    reason: str
    rejected: bool = False
    candidate_digest: str = ""
    previous_elite_digest: str | None = None

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "archive": self.archive.to_dict(),
            "inserted": self.inserted,
            "replaced": self.replaced,
            "behavior_bin": self.behavior_bin.to_dict(),
            "reason": self.reason,
            "rejected": self.rejected,
            "candidate_digest": self.candidate_digest,
            "previous_elite_digest": self.previous_elite_digest,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, JsonValue]) -> QDArchiveUpdateResult:
        raw_archive = data.get("archive")
        raw_bin = data.get("behavior_bin")
        if not isinstance(raw_archive, Mapping):
            msg = "QDArchiveUpdateResult.archive must be an object."
            raise ConfigurationError(msg)
        if not isinstance(raw_bin, Mapping):
            msg = "QDArchiveUpdateResult.behavior_bin must be an object."
            raise ConfigurationError(msg)
        return cls(
            archive=QDArchive.from_dict(raw_archive),
            inserted=_bool(data, "inserted", False),
            replaced=_bool(data, "replaced", False),
            behavior_bin=BehaviorBin.from_dict(raw_bin),
            reason=_str(data, "reason"),
            rejected=_bool(data, "rejected", False),
            candidate_digest=_str(data, "candidate_digest", ""),
            previous_elite_digest=_optional_str(
                data.get("previous_elite_digest"), "previous_elite_digest"
            ),
        )

    def digest(self) -> str:
        return _digest(self.to_dict())


@dataclass(frozen=True, slots=True)
class QDArchiveSummary:
    """Deterministic summary metrics for a QD archive."""

    archive_digest: str
    filled_bins: int
    coverage: float
    best_fitness: float | None
    mean_fitness: float | None
    qd_score: float
    total_bins: int = 0
    rejected_count: int = 0
    replacement_count: int = 0
    archive_id: str = ""
    descriptor_names: tuple[str, ...] = ()
    coverage_percent: float = 0.0
    best_elite_digest: str | None = None
    mode: str = "archive_only"
    archive_type: str = "map_elites_grid"
    coverage_status: str = "measured"

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "archive_digest": self.archive_digest,
            "filled_bins": self.filled_bins,
            "coverage": self.coverage,
            "best_fitness": self.best_fitness,
            "mean_fitness": self.mean_fitness,
            "qd_score": self.qd_score,
            "total_bins": self.total_bins,
            "rejected_count": self.rejected_count,
            "replacement_count": self.replacement_count,
            "archive_id": self.archive_id,
            "descriptor_names": list(self.descriptor_names),
            "coverage_percent": self.coverage_percent,
            "best_elite_digest": self.best_elite_digest,
            "mode": self.mode,
            "archive_type": self.archive_type,
            "coverage_status": self.coverage_status,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, JsonValue]) -> QDArchiveSummary:
        return cls(
            archive_digest=_str(data, "archive_digest"),
            filled_bins=_int(data, "filled_bins", 0),
            coverage=_float(data, "coverage", 0.0),
            best_fitness=_optional_float(data.get("best_fitness"), "best_fitness"),
            mean_fitness=_optional_float(data.get("mean_fitness"), "mean_fitness"),
            qd_score=_float(data, "qd_score", 0.0),
            total_bins=_int(data, "total_bins", 0),
            rejected_count=_int(data, "rejected_count", 0),
            replacement_count=_int(data, "replacement_count", 0),
            archive_id=_str(data, "archive_id", ""),
            descriptor_names=_str_tuple(data, "descriptor_names"),
            coverage_percent=_float(data, "coverage_percent", 0.0),
            best_elite_digest=_optional_str(data.get("best_elite_digest"), "best_elite_digest"),
            mode=_str(data, "mode", "archive_only"),
            archive_type=_str(data, "archive_type", "map_elites_grid"),
            coverage_status=_str(data, "coverage_status", "measured"),
        )

    def digest(self) -> str:
        return _digest(self.to_dict())


@dataclass(frozen=True, slots=True)
class QDArchiveItemUpdateRecord:
    """Compact per-candidate audit record for batch archive updates."""

    candidate_digest: str
    behavior_bin: BehaviorBin
    inserted: bool
    replaced: bool
    rejected: bool
    reason: str
    previous_elite_digest: str | None
    new_elite_digest: str | None
    archive_digest_after: str

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "candidate_digest": self.candidate_digest,
            "behavior_bin": self.behavior_bin.to_dict(),
            "inserted": self.inserted,
            "replaced": self.replaced,
            "rejected": self.rejected,
            "reason": self.reason,
            "previous_elite_digest": self.previous_elite_digest,
            "new_elite_digest": self.new_elite_digest,
            "archive_digest_after": self.archive_digest_after,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, JsonValue]) -> QDArchiveItemUpdateRecord:
        raw_bin = data.get("behavior_bin")
        if not isinstance(raw_bin, Mapping):
            msg = "QDArchiveItemUpdateRecord.behavior_bin must be an object."
            raise ConfigurationError(msg)
        return cls(
            candidate_digest=_str(data, "candidate_digest"),
            behavior_bin=BehaviorBin.from_dict(raw_bin),
            inserted=_bool(data, "inserted", False),
            replaced=_bool(data, "replaced", False),
            rejected=_bool(data, "rejected", False),
            reason=_str(data, "reason"),
            previous_elite_digest=_optional_str(
                data.get("previous_elite_digest"), "previous_elite_digest"
            ),
            new_elite_digest=_optional_str(data.get("new_elite_digest"), "new_elite_digest"),
            archive_digest_after=_str(data, "archive_digest_after"),
        )

    @classmethod
    def from_update_result(cls, result: QDArchiveUpdateResult) -> QDArchiveItemUpdateRecord:
        stored = result.archive.elites.get(result.behavior_bin.key())
        return cls(
            candidate_digest=result.candidate_digest,
            behavior_bin=result.behavior_bin,
            inserted=result.inserted,
            replaced=result.replaced,
            rejected=result.rejected,
            reason=result.reason,
            previous_elite_digest=result.previous_elite_digest,
            new_elite_digest=stored.digest()
            if stored is not None and not result.rejected
            else None,
            archive_digest_after=result.archive.digest(),
        )

    def digest(self) -> str:
        return _digest(self.to_dict())


@dataclass(frozen=True, slots=True)
class QDArchiveBatchUpdateResult:
    """Deterministic compact audit summary for a batch of archive updates."""

    archive_before_digest: str
    archive_after_digest: str
    candidates_seen: int
    inserted_count: int
    replaced_count: int
    rejected_count: int
    update_records: tuple[QDArchiveItemUpdateRecord, ...]
    summary: QDArchiveSummary

    @property
    def update_results(self) -> tuple[QDArchiveItemUpdateRecord, ...]:
        """Backward-readable compact records; batch results no longer embed archives."""
        return self.update_records

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "archive_before_digest": self.archive_before_digest,
            "archive_after_digest": self.archive_after_digest,
            "candidates_seen": self.candidates_seen,
            "inserted_count": self.inserted_count,
            "replaced_count": self.replaced_count,
            "rejected_count": self.rejected_count,
            "update_records": [item.to_dict() for item in self.update_records],
            "summary": self.summary.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, JsonValue]) -> QDArchiveBatchUpdateResult:
        raw_records = data.get("update_records", data.get("update_results", []))
        raw_summary = data.get("summary")
        if not isinstance(raw_records, list):
            msg = "QDArchiveBatchUpdateResult.update_records must be a list."
            raise ConfigurationError(msg)
        if not isinstance(raw_summary, Mapping):
            msg = "QDArchiveBatchUpdateResult.summary must be an object."
            raise ConfigurationError(msg)
        records: list[QDArchiveItemUpdateRecord] = []
        for item in raw_records:
            mapping = _mapping(item, "update_record")
            if "archive" in mapping:
                records.append(
                    QDArchiveItemUpdateRecord.from_update_result(
                        QDArchiveUpdateResult.from_dict(mapping)
                    )
                )
            else:
                records.append(QDArchiveItemUpdateRecord.from_dict(mapping))
        return cls(
            archive_before_digest=_str(data, "archive_before_digest"),
            archive_after_digest=_str(data, "archive_after_digest"),
            candidates_seen=_int(data, "candidates_seen", 0),
            inserted_count=_int(data, "inserted_count", 0),
            replaced_count=_int(data, "replaced_count", 0),
            rejected_count=_int(data, "rejected_count", 0),
            update_records=tuple(records),
            summary=QDArchiveSummary.from_dict(raw_summary),
        )

    def digest(self) -> str:
        return _digest(self.to_dict())


def validate_descriptor_against_schema(
    descriptor: Mapping[str, float], schema: BehaviorDescriptorSchema
) -> tuple[str, ...]:
    """Return deterministic validation reasons for a descriptor/schema pair."""

    reasons: list[str] = []
    for name in schema.descriptor_names:
        raw_value = descriptor.get(name)
        if isinstance(raw_value, bool) or not isinstance(raw_value, int | float):
            reasons.append(f"{name}:missing_or_non_numeric")
            continue
        value = float(raw_value)
        if value < schema.min_values[name] or value > schema.max_values[name]:
            reasons.append(f"{name}:out_of_range")
    extra = sorted(set(str(key) for key in descriptor) - set(schema.descriptor_names))
    reasons.extend(f"{name}:extra_descriptor" for name in extra)
    return tuple(reasons)


def normalize_descriptor(
    descriptor: Mapping[str, float], schema: BehaviorDescriptorSchema
) -> dict[str, float]:
    """Normalize descriptor values into [0, 1] according to schema bounds."""

    normalized: dict[str, float] = {}
    for name in schema.descriptor_names:
        raw_value = descriptor.get(name)
        if isinstance(raw_value, bool) or not isinstance(raw_value, int | float):
            msg = f"Descriptor {name!r} must be numeric."
            raise ConfigurationError(msg)
        min_value = schema.min_values[name]
        max_value = schema.max_values[name]
        value = float(raw_value)
        if value < min_value or value > max_value:
            if schema.out_of_range_policy == "reject":
                msg = f"Descriptor {name!r} is outside schema range."
                raise ConfigurationError(msg)
            value = max(min_value, min(max_value, value))
        normalized[name] = round((value - min_value) / (max_value - min_value), 10)
    return normalized


def descriptor_distance(
    a: Mapping[str, float],
    b: Mapping[str, float],
    schema: BehaviorDescriptorSchema,
    metric: str = "normalized_l1",
) -> float:
    """Pure-Python descriptor distance for archive and witness audits."""

    norm_a = normalize_descriptor(a, schema)
    norm_b = normalize_descriptor(b, schema)
    if metric != "normalized_l1":
        msg = "descriptor_distance currently supports metric='normalized_l1'."
        raise ConfigurationError(msg)
    total = sum(abs(norm_a[name] - norm_b[name]) for name in schema.descriptor_names)
    return round(total / max(1, len(schema.descriptor_names)), 10)


def assign_behavior_bin(
    descriptor: Mapping[str, float], schema: BehaviorDescriptorSchema
) -> BehaviorBin:
    """Assign a descriptor to a deterministic behavior bin."""

    indices: list[int] = []
    for name in schema.descriptor_names:
        raw_value = descriptor.get(name)
        if isinstance(raw_value, bool) or not isinstance(raw_value, int | float):
            msg = f"Descriptor {name!r} must be numeric."
            raise ConfigurationError(msg)
        min_value = schema.min_values[name]
        max_value = schema.max_values[name]
        bins = schema.bins_per_descriptor[name]
        value = float(raw_value)
        if value < min_value or value > max_value:
            if schema.out_of_range_policy == "reject":
                msg = f"Descriptor {name!r} is outside schema range."
                raise ConfigurationError(msg)
            value = max(min_value, min(max_value, value))
        span = max_value - min_value
        relative = (value - min_value) / span
        index = min(bins - 1, max(0, int(relative * bins)))
        indices.append(index)
    return BehaviorBin(tuple(indices))


def update_qd_archive(archive: QDArchive, candidate: QDElite) -> QDArchiveUpdateResult:
    """Insert, replace, or reject one candidate according to archive policy."""

    policy = archive.config.policy
    candidate_digest = candidate.digest()
    if policy.require_behavior_digest and not candidate.behavior_digest:
        return _reject(archive, candidate, "behavior_digest_missing", None)
    if policy.require_trace_digest and not candidate.trace_digest:
        return _reject(archive, candidate, "trace_digest_missing", None)
    key = candidate.behavior_bin.key()
    existing = archive.elites.get(key)
    if (
        existing is None
        and policy.max_elites is not None
        and len(archive.elites) >= policy.max_elites
    ):
        return _reject(archive, candidate, "max_elites_reached", None)
    should_store = False
    reason = "inserted"
    if existing is None:
        should_store = True
    elif policy.replacement_policy == "latest_wins":
        should_store = True
        reason = "replaced_latest_wins"
    elif policy.replacement_policy == "first_wins":
        reason = "first_wins_existing_elite"
    elif policy.replacement_policy == "higher_fitness":
        should_store = candidate.fitness > existing.fitness or (
            policy.allow_equal_fitness_replace and candidate.fitness == existing.fitness
        )
        reason = "replaced_lower_fitness" if should_store else "lower_or_equal_fitness"
    elif policy.replacement_policy == "novelty_then_fitness":
        candidate_novelty = _metadata_float(candidate.metadata, "novelty", 0.0)
        existing_novelty = _metadata_float(existing.metadata, "novelty", 0.0)
        should_store = candidate_novelty > existing_novelty or (
            candidate_novelty == existing_novelty
            and (
                candidate.fitness > existing.fitness
                or (policy.allow_equal_fitness_replace and candidate.fitness == existing.fitness)
            )
        )
        reason = "replaced_novelty_then_fitness" if should_store else "not_more_novel_or_fit"
    if not should_store:
        return _reject(archive, candidate, reason, existing)
    updated = dict(archive.elites)
    updated[key] = candidate
    new_archive = QDArchive(
        archive.config,
        updated,
        archive.rejected,
        archive.replacement_count + (1 if existing is not None else 0),
    )
    return QDArchiveUpdateResult(
        new_archive,
        inserted=existing is None,
        replaced=existing is not None,
        behavior_bin=candidate.behavior_bin,
        reason=reason,
        rejected=False,
        candidate_digest=candidate_digest,
        previous_elite_digest=existing.digest() if existing is not None else None,
    )


def update_qd_archive_many(
    archive: QDArchive, candidates: Sequence[QDElite]
) -> QDArchiveBatchUpdateResult:
    """Apply candidates in provided order and return deterministic audit data."""

    before = archive.digest()
    current = archive
    records: list[QDArchiveItemUpdateRecord] = []
    inserted = replaced = rejected = 0
    for candidate in candidates:
        result = update_qd_archive(current, candidate)
        current = result.archive
        records.append(QDArchiveItemUpdateRecord.from_update_result(result))
        inserted += int(result.inserted)
        replaced += int(result.replaced)
        rejected += int(result.rejected)
    summary = summarize_qd_archive(current)
    return QDArchiveBatchUpdateResult(
        archive_before_digest=before,
        archive_after_digest=current.digest(),
        candidates_seen=len(candidates),
        inserted_count=inserted,
        replaced_count=replaced,
        rejected_count=rejected,
        update_records=tuple(records),
        summary=summary,
    )


def summarize_qd_archive(archive: QDArchive) -> QDArchiveSummary:
    """Summarize archive coverage and fitness without plotting or files."""

    total_bins = 1
    for name in archive.config.schema.descriptor_names:
        total_bins *= archive.config.schema.bins_per_descriptor[name]
    fitness_values = [elite.fitness for elite in archive.elites.values()]
    filled = len(fitness_values)
    qd_score = round(sum(fitness_values), 10)
    best_elite = max(archive.elites.values(), key=lambda item: item.fitness, default=None)
    coverage = round(filled / total_bins, 10) if total_bins else 0.0
    return QDArchiveSummary(
        archive_digest=archive.digest(),
        filled_bins=filled,
        coverage=coverage,
        best_fitness=max(fitness_values) if fitness_values else None,
        mean_fitness=round(sum(fitness_values) / filled, 10) if filled else None,
        qd_score=qd_score,
        total_bins=total_bins,
        rejected_count=len(archive.rejected),
        replacement_count=archive.replacement_count,
        archive_id=archive.config.archive_id,
        descriptor_names=archive.config.schema.descriptor_names,
        coverage_percent=round(coverage * 100.0, 10),
        best_elite_digest=best_elite.digest() if best_elite is not None else None,
        archive_type="map_elites_grid" if total_bins > 0 else "descriptor_set",
        coverage_status="measured" if total_bins > 0 else "not_applicable_no_grid",
    )


def _reject(
    archive: QDArchive, candidate: QDElite, reason: str, existing: QDElite | None
) -> QDArchiveUpdateResult:
    rejected = archive.rejected
    policy = archive.config.policy
    candidate_digest = candidate.digest()
    if policy.track_rejected_candidates and policy.max_rejected_records > 0:
        record = QDArchiveRejectedCandidate(
            candidate_digest=candidate_digest,
            behavior_bin=candidate.behavior_bin,
            fitness=candidate.fitness,
            reason=reason,
            existing_elite_digest=existing.digest() if existing is not None else None,
            metadata={"organism_id": candidate.organism_id},
        )
        rejected = (*archive.rejected, record)[-policy.max_rejected_records :]
    new_archive = QDArchive(
        archive.config, dict(archive.elites), rejected, archive.replacement_count
    )
    return QDArchiveUpdateResult(
        archive=new_archive,
        inserted=False,
        replaced=False,
        behavior_bin=candidate.behavior_bin,
        reason=reason,
        rejected=True,
        candidate_digest=candidate_digest,
        previous_elite_digest=existing.digest() if existing is not None else None,
    )


def _digest(payload: Mapping[str, JsonValue]) -> str:
    encoded = finite_json_dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _mapping(value: object, name: str) -> Mapping[str, JsonValue]:
    if not isinstance(value, Mapping):
        msg = f"{name} must be an object."
        raise ConfigurationError(msg)
    return value


def _str(data: Mapping[str, JsonValue], key: str, default: str | None = None) -> str:
    value = data.get(key, default)
    if not isinstance(value, str):
        msg = f"{key} must be a string."
        raise ConfigurationError(msg)
    return value


def _optional_str(value: object, key: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        msg = f"{key} must be a string or null."
        raise ConfigurationError(msg)
    return value


def _bool(data: Mapping[str, JsonValue], key: str, default: bool) -> bool:
    value = data.get(key, default)
    if not isinstance(value, bool):
        msg = f"{key} must be a boolean."
        raise ConfigurationError(msg)
    return value


def _int(data: Mapping[str, JsonValue], key: str, default: int) -> int:
    value = data.get(key, default)
    if isinstance(value, bool) or not isinstance(value, int):
        msg = f"{key} must be an integer."
        raise ConfigurationError(msg)
    return value


def _optional_int(value: object, key: str) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int):
        msg = f"{key} must be an integer or null."
        raise ConfigurationError(msg)
    return value


def _float(data: Mapping[str, JsonValue], key: str, default: float) -> float:
    value = data.get(key, default)
    if isinstance(value, bool) or not isinstance(value, int | float):
        msg = f"{key} must be numeric."
        raise ConfigurationError(msg)
    return finite_float(key, value)  # type: ignore[return-value]


def _optional_float(value: object, key: str) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int | float):
        msg = f"{key} must be numeric or null."
        raise ConfigurationError(msg)
    return finite_float(key, value)  # type: ignore[return-value]


def _str_tuple(data: Mapping[str, JsonValue], key: str) -> tuple[str, ...]:
    raw = data.get(key, [])
    if not isinstance(raw, list) or not all(isinstance(item, str) for item in raw):
        msg = f"{key} must be a list of strings."
        raise ConfigurationError(msg)
    return tuple(str(item) for item in raw)


def _int_tuple(data: Mapping[str, JsonValue], key: str) -> tuple[int, ...]:
    raw = data.get(key, [])
    if not isinstance(raw, list) or not all(
        isinstance(item, int) and not isinstance(item, bool) for item in raw
    ):
        msg = f"{key} must be a list of integers."
        raise ConfigurationError(msg)
    return tuple(cast(list[int], raw))


def _int_map(value: object, name: str) -> dict[str, int]:
    if not isinstance(value, Mapping):
        msg = f"{name} must be an object."
        raise ConfigurationError(msg)
    out: dict[str, int] = {}
    for key, raw in value.items():
        if not isinstance(key, str) or isinstance(raw, bool) or not isinstance(raw, int):
            msg = f"{name} entries must be string -> integer."
            raise ConfigurationError(msg)
        out[key] = raw
    return out


def _float_map(value: object, name: str) -> dict[str, float]:
    if not isinstance(value, Mapping):
        msg = f"{name} must be an object."
        raise ConfigurationError(msg)
    out: dict[str, float] = {}
    for key, raw in value.items():
        if not isinstance(key, str) or isinstance(raw, bool) or not isinstance(raw, int | float):
            msg = f"{name} entries must be string -> numeric."
            raise ConfigurationError(msg)
        out[key] = finite_float(f"{name}[{key}]", raw)  # type: ignore[assignment]
    return out


def _metadata(value: object) -> dict[str, JsonValue]:
    if not isinstance(value, Mapping):
        msg = "metadata must be an object."
        raise ConfigurationError(msg)
    return {str(key): raw for key, raw in value.items()}


def _metadata_float(metadata: Mapping[str, JsonValue], key: str, default: float) -> float:
    value = metadata.get(key, default)
    if isinstance(value, bool) or not isinstance(value, int | float):
        return default
    return finite_float(key, value)  # type: ignore[return-value]


def _validate_descriptor(value: Mapping[str, float]) -> None:
    for key, raw in value.items():
        if not isinstance(key, str) or isinstance(raw, bool) or not isinstance(raw, int | float):
            msg = "Behavior descriptors must be string -> numeric."
            raise ConfigurationError(msg)
        finite_float(f"behavior_descriptor[{key}]", raw)


@dataclass(frozen=True, slots=True)
class QDSearchConfig:
    """Lightweight QD-to-selection/discovery integration config."""

    enabled: bool = True
    novelty_weight: float = 1.0
    emit_discovery_candidates: bool = True

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "enabled": self.enabled,
            "novelty_weight": self.novelty_weight,
            "emit_discovery_candidates": self.emit_discovery_candidates,
        }

    def digest(self) -> str:
        return _digest(self.to_dict())


@dataclass(frozen=True, slots=True)
class NoveltyScore:
    """Auditable novelty score for selection/QD summaries."""

    organism_id: str
    score: float
    basis: str = "descriptor_distance"

    def to_dict(self) -> dict[str, JsonValue]:
        return {"organism_id": self.organism_id, "score": self.score, "basis": self.basis}


@dataclass(frozen=True, slots=True)
class EliteRecord:
    """Stable public alias for a QD elite record."""

    elite: QDElite

    def to_dict(self) -> dict[str, JsonValue]:
        return self.elite.to_dict()

    def digest(self) -> str:
        return self.elite.digest()


@dataclass(frozen=True, slots=True)
class DiscoveryCandidateFromQD:
    """Candidate emitted from QD for later discovery review; not proof."""

    organism_id: str
    archive_digest: str
    novelty_score: float
    status: str = "review_needed"

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "organism_id": self.organism_id,
            "archive_digest": self.archive_digest,
            "novelty_score": self.novelty_score,
            "status": self.status,
        }


@dataclass(frozen=True, slots=True)
class QDUpdateResult:
    """Small QD population integration summary."""

    archive_digest_before: str
    archive_digest_after: str
    inserted: int
    replaced: int
    rejected: int
    discovery_candidates: tuple[DiscoveryCandidateFromQD, ...] = ()

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "archive_digest_before": self.archive_digest_before,
            "archive_digest_after": self.archive_digest_after,
            "inserted": self.inserted,
            "replaced": self.replaced,
            "rejected": self.rejected,
            "discovery_candidates": [item.to_dict() for item in self.discovery_candidates],
        }

# Phase 2 multi-objective QD / Pareto archive primitives.
@dataclass(frozen=True, slots=True)
class ParetoObjectiveVector:
    task_score: float
    survival_viability: float
    energy_efficiency: float
    novelty: float
    cooperation_coordination: float
    complexity_cost: float
    schema_version: str = "pareto_objective_vector_v1"

    def __post_init__(self) -> None:
        from codontrace.genesis.canonical import require_finite_float
        for attr in (
            "task_score", "survival_viability", "energy_efficiency",
            "novelty", "cooperation_coordination", "complexity_cost",
        ):
            object.__setattr__(self, attr, round(require_finite_float(attr, getattr(self, attr)), 10))

    def dominates(self, other: "ParetoObjectiveVector") -> bool:
        own = (self.task_score, self.survival_viability, self.energy_efficiency, self.novelty, self.cooperation_coordination, -self.complexity_cost)
        their = (other.task_score, other.survival_viability, other.energy_efficiency, other.novelty, other.cooperation_coordination, -other.complexity_cost)
        return all(a >= b for a, b in zip(own, their, strict=True)) and any(a > b for a, b in zip(own, their, strict=True))

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "schema_version": self.schema_version,
            "task_score": self.task_score,
            "survival_viability": self.survival_viability,
            "energy_efficiency": self.energy_efficiency,
            "novelty": self.novelty,
            "cooperation_coordination": self.cooperation_coordination,
            "complexity_cost": self.complexity_cost,
        }

    def digest(self) -> str:
        from codontrace.genesis.canonical import canonical_digest
        return canonical_digest(self.to_dict())


@dataclass(frozen=True, slots=True)
class ParetoEliteRecord:
    elite_id: str
    descriptor_key: tuple[int, ...]
    objectives: ParetoObjectiveVector
    artifact_digest: str
    schema_version: str = "pareto_elite_record_v1"

    def __post_init__(self) -> None:
        object.__setattr__(self, "descriptor_key", tuple(int(x) for x in self.descriptor_key))
        if not self.elite_id or not self.artifact_digest:
            raise ValueError("ParetoEliteRecord requires elite_id and artifact_digest")

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "schema_version": self.schema_version,
            "elite_id": self.elite_id,
            "descriptor_key": list(self.descriptor_key),
            "objectives": self.objectives.to_dict(),
            "artifact_digest": self.artifact_digest,
        }

    def digest(self) -> str:
        from codontrace.genesis.canonical import canonical_digest
        return canonical_digest(self.to_dict())


@dataclass(frozen=True, slots=True)
class MultiObjectiveQDArchive:
    elites: tuple[ParetoEliteRecord, ...] = ()
    schema_version: str = "multi_objective_qd_archive_v1"

    def insert(self, elite: ParetoEliteRecord) -> "MultiObjectiveQDArchive":
        kept = []
        for item in self.elites:
            if elite.objectives.dominates(item.objectives) and elite.descriptor_key == item.descriptor_key:
                continue
            if item.objectives.dominates(elite.objectives) and elite.descriptor_key == item.descriptor_key:
                return self
            kept.append(item)
        kept.append(elite)
        return MultiObjectiveQDArchive(tuple(sorted(kept, key=lambda e: (e.descriptor_key, e.elite_id))))

    def to_dict(self) -> dict[str, JsonValue]:
        return {"schema_version": self.schema_version, "elites": [item.to_dict() for item in self.elites]}

    def digest(self) -> str:
        from codontrace.genesis.canonical import canonical_digest
        return canonical_digest(self.to_dict())


@dataclass(frozen=True, slots=True)
class QDTradeoffReport:
    archive_digest: str
    elite_count: int
    objective_names: tuple[str, ...]
    claim_status: str = "measured"
    schema_version: str = "qd_tradeoff_report_v1"

    def to_dict(self) -> dict[str, JsonValue]:
        return {"schema_version": self.schema_version, "archive_digest": self.archive_digest, "elite_count": self.elite_count, "objective_names": list(self.objective_names), "claim_status": self.claim_status}

    def digest(self) -> str:
        from codontrace.genesis.canonical import canonical_digest
        return canonical_digest(self.to_dict())


def build_qd_tradeoff_report(archive: MultiObjectiveQDArchive) -> QDTradeoffReport:
    return QDTradeoffReport(
        archive_digest=archive.digest(),
        elite_count=len(archive.elites),
        objective_names=("task_score", "survival_viability", "energy_efficiency", "novelty", "cooperation_coordination", "complexity_cost"),
        claim_status="measured" if archive.elites else "empty_but_available",
    )

# Phase 3 QD reporting surfaces.
@dataclass(frozen=True, slots=True)
class QDScoreReport:
    archive_digest: str
    qd_score: float
    elite_count: int
    selection_pressure_mode: str
    qd_changed_selection: bool
    schema_version: str = "qd_score_report_v1"
    def __post_init__(self) -> None:
        from codontrace.genesis.canonical import require_finite_float
        object.__setattr__(self, "qd_score", require_finite_float("qd_score", self.qd_score))
    @property
    def functional_claim_eligible(self) -> bool:
        return self.selection_pressure_mode == "selection_pressure" and self.qd_changed_selection
    def to_dict(self) -> dict[str, JsonValue]:
        return {"schema_version": self.schema_version, "archive_digest": self.archive_digest, "qd_score": self.qd_score, "elite_count": self.elite_count, "selection_pressure_mode": self.selection_pressure_mode, "qd_changed_selection": self.qd_changed_selection, "functional_claim_eligible": self.functional_claim_eligible}
    def digest(self) -> str:
        from codontrace.genesis.canonical import canonical_digest
        return canonical_digest(self.to_dict())

@dataclass(frozen=True, slots=True)
class CoverageReport:
    archive_digest: str
    occupied_bins: int
    total_bins: int
    descriptor_schema_version: str
    schema_version: str = "coverage_report_v1"
    def __post_init__(self) -> None:
        if self.total_bins <= 0 or self.occupied_bins < 0 or self.occupied_bins > self.total_bins:
            raise ValueError("invalid coverage bins")
        if not self.descriptor_schema_version:
            raise ValueError("descriptor schema version required")
    @property
    def coverage(self) -> float:
        return round(self.occupied_bins / self.total_bins, 10)
    def to_dict(self) -> dict[str, JsonValue]:
        return {"schema_version": self.schema_version, "archive_digest": self.archive_digest, "occupied_bins": self.occupied_bins, "total_bins": self.total_bins, "descriptor_schema_version": self.descriptor_schema_version, "coverage": self.coverage}
    def digest(self) -> str:
        from codontrace.genesis.canonical import canonical_digest
        return canonical_digest(self.to_dict())

@dataclass(frozen=True, slots=True)
class EliteReplacementAudit:
    archive_digest_before: str
    archive_digest_after: str
    replaced_elites: int
    rejected_candidates: int
    reason: str = "measured"
    schema_version: str = "elite_replacement_audit_v1"
    def to_dict(self) -> dict[str, JsonValue]:
        return {"schema_version": self.schema_version, "archive_digest_before": self.archive_digest_before, "archive_digest_after": self.archive_digest_after, "replaced_elites": self.replaced_elites, "rejected_candidates": self.rejected_candidates, "reason": self.reason}
    def digest(self) -> str:
        from codontrace.genesis.canonical import canonical_digest
        return canonical_digest(self.to_dict())

DescriptorDriftReport = CoverageReport
ParetoArchive = MultiObjectiveQDArchive
ParetoFrontReport = QDTradeoffReport
EmitterAudit = EliteReplacementAudit
