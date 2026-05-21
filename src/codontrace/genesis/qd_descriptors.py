"""User-defined QD descriptor schemas and novelty feedback helpers."""

from __future__ import annotations

import hashlib
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import cast

from codontrace._types import JsonValue
from codontrace._numeric import finite_float, finite_json_dumps
from codontrace.errors import ConfigurationError
from codontrace.genesis.quality_diversity import (
    BehaviorDescriptorSchema,
    QDArchive,
    descriptor_distance,
)
from codontrace.genesis.selection import EvolutionConfig, select_population

_DEFAULT_RANGES: dict[str, tuple[float, float, int]] = {
    "survival_ticks": (0.0, 100.0, 10),
    "blocked_ratio": (0.0, 1.0, 10),
    "resource_gain": (0.0, 100.0, 10),
    "energy_efficiency": (0.0, 10.0, 10),
    "path_entropy": (0.0, 10.0, 10),
    "unique_positions": (0.0, 100.0, 10),
    "capsules_emitted": (0.0, 50.0, 10),
    "capsules_read": (0.0, 50.0, 10),
    "capsules_adopted": (0.0, 50.0, 10),
    "causal_prediction_accuracy": (0.0, 1.0, 10),
    "causal_graph_size": (0.0, 100.0, 10),
    "causal_graph_compactness": (0.0, 1.0, 10),
    "lineage_depth": (0.0, 100.0, 10),
    "offspring_count": (0.0, 100.0, 10),
    "genome_length": (0.0, 512.0, 16),
    "ADF_usage_count": (0.0, 100.0, 10),
    "ADF_reuse_score": (0.0, 1.0, 10),
    "nexus_interaction_count": (0.0, 100.0, 10),
    "environmental_footprint": (0.0, 100.0, 10),
    "cooperation_score": (0.0, 1.0, 10),
    "free_rider_score": (0.0, 1.0, 10),
    "mutation_distance": (0.0, 100.0, 10),
}


@dataclass(frozen=True, slots=True)
class QDDescriptorFamily:
    name: str
    descriptors: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.name or not self.descriptors:
            raise ConfigurationError("QDDescriptorFamily requires name and descriptors.")

    def to_dict(self) -> dict[str, JsonValue]:
        return {"name": self.name, "descriptors": list(self.descriptors)}


@dataclass(frozen=True, slots=True)
class QDDescriptorConfig:
    descriptor_names: tuple[str, ...] = ("survival_ticks", "blocked_ratio")
    custom_ranges: dict[str, tuple[float, float, int]] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.descriptor_names:
            raise ConfigurationError("descriptor_names must not be empty.")
        object.__setattr__(self, "custom_ranges", dict(self.custom_ranges))

    def to_schema(self) -> BehaviorDescriptorSchema:
        bins: dict[str, int] = {}
        min_values: dict[str, float] = {}
        max_values: dict[str, float] = {}
        for name in self.descriptor_names:
            low, high, bin_count = self.custom_ranges.get(
                name, _DEFAULT_RANGES.get(name, (0.0, 1.0, 10))
            )
            low = finite_float(f"QDDescriptorConfig.custom_ranges[{name}].low", low)
            high = finite_float(f"QDDescriptorConfig.custom_ranges[{name}].high", high)
            if isinstance(bin_count, bool) or not isinstance(bin_count, int) or high <= low or bin_count <= 0:
                raise ConfigurationError(f"Invalid QD range for descriptor {name!r}.")
            min_values[name] = low
            max_values[name] = high
            bins[name] = int(bin_count)
        return BehaviorDescriptorSchema(self.descriptor_names, bins, min_values, max_values)

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "descriptor_names": list(self.descriptor_names),
            "custom_ranges": {k: [v[0], v[1], v[2]] for k, v in sorted(self.custom_ranges.items())},
        }

    def digest(self) -> str:
        return _digest(self.to_dict())


@dataclass(frozen=True, slots=True)
class QDSelectionFeedbackConfig:
    enabled: bool = False
    novelty_weight: float = 1.0
    archive_digest_required: bool = True

    def __post_init__(self) -> None:
        object.__setattr__(self, "novelty_weight", finite_float("QDSelectionFeedbackConfig.novelty_weight", self.novelty_weight, non_negative=True))

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "enabled": self.enabled,
            "novelty_weight": self.novelty_weight,
            "archive_digest_required": self.archive_digest_required,
        }


class QDDescriptorRegistry:
    """Registry for user-defined descriptor extractors."""

    def __init__(self) -> None:
        self._extractors: dict[str, Callable[[object], float]] = {}

    def register(self, name: str, extractor: Callable[[object], float]) -> QDDescriptorRegistry:
        if not name:
            raise ConfigurationError("descriptor name must not be empty.")
        self._extractors[name] = extractor
        return self

    def describe(self, subject: object, descriptor_names: Sequence[str]) -> dict[str, float]:
        values: dict[str, float] = {}
        for name in descriptor_names:
            extractor = self._extractors.get(name)
            value = getattr(subject, name, 0.0) if extractor is None else extractor(subject)
            values[name] = finite_float(f"descriptor[{name}]", value)  # type: ignore[assignment]
        return values

    def digest(self) -> str:
        return _digest({"descriptors": cast(JsonValue, list(sorted(self._extractors)))})


def compute_novelty_scores_from_archive(
    candidates: Sequence[object],
    descriptors: Mapping[str, Mapping[str, float]],
    archive: QDArchive,
) -> dict[str, float]:
    elites = tuple(archive.elites.values())
    if not elites:
        return {_stable_id(candidate): 1.0 for candidate in candidates}
    scores: dict[str, float] = {}
    for candidate in candidates:
        oid = _stable_id(candidate)
        descriptor = dict(descriptors.get(oid, {}))
        if not descriptor:
            scores[oid] = 0.0
            continue
        distances = [
            descriptor_distance(descriptor, elite.behavior_descriptor, archive.config.schema)
            for elite in elites
        ]
        scores[oid] = round(min(distances), 10) if distances else 1.0
    return scores


def select_population_with_qd_feedback(
    candidates: Sequence[object],
    *,
    fitness_scores: Mapping[str, float],
    behavior_descriptors: Mapping[str, Mapping[str, float]],
    archive: QDArchive,
    max_population: int,
    evolution_config: EvolutionConfig,
) -> tuple[tuple[object, ...], object, dict[str, float]]:
    novelty_scores = compute_novelty_scores_from_archive(candidates, behavior_descriptors, archive)
    selected, result = select_population(
        candidates,
        fitness_scores=fitness_scores,
        max_population=max_population,
        config=evolution_config,
        novelty_scores=novelty_scores,
    )
    return selected, result, novelty_scores


def _stable_id(item: object) -> str:
    value = getattr(item, "id", None) or getattr(item, "organism_id", None)
    return str(value) if value else repr(item)


def _digest(payload: Mapping[str, JsonValue]) -> str:
    encoded = finite_json_dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class DescriptorValue:
    """One QD descriptor value with explicit missing/unavailable status."""

    name: str
    value: float | None
    status: str  # available | missing_zeroed | missing_null | unavailable_phase

    def __post_init__(self) -> None:
        if self.value is not None:
            object.__setattr__(self, "value", finite_float("DescriptorValue.value", self.value))
        if self.status not in {"available", "missing_zeroed", "missing_null", "unavailable_phase"}:
            raise ConfigurationError("Unsupported DescriptorValue.status.")

    def to_dict(self) -> dict[str, JsonValue]:
        return {"name": self.name, "value": self.value, "status": self.status}


@dataclass(frozen=True, slots=True)
class DescriptorSpec:
    """One dimension in a user-defined behavior descriptor schema."""

    name: str
    source: str
    range_min: float
    range_max: float
    bins: int
    normalize: bool = True

    def __post_init__(self) -> None:
        if not self.name or not self.source:
            raise ConfigurationError("DescriptorSpec requires name and source.")
        object.__setattr__(self, "range_min", finite_float("DescriptorSpec.range_min", self.range_min))
        object.__setattr__(self, "range_max", finite_float("DescriptorSpec.range_max", self.range_max))
        if self.range_max <= self.range_min:
            raise ConfigurationError("DescriptorSpec.range_max must be greater than range_min.")
        if self.bins <= 0:
            raise ConfigurationError("DescriptorSpec.bins must be positive.")

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "name": self.name,
            "source": self.source,
            "range_min": self.range_min,
            "range_max": self.range_max,
            "bins": self.bins,
            "normalize": self.normalize,
        }


@dataclass(frozen=True, slots=True)
class DescriptorSchema:
    """Factory-built descriptor schema for replay-critical QD runs."""

    schema_id: str
    descriptors: tuple[DescriptorSpec, ...]
    distance_metric: str = "euclidean"
    digest: str = ""

    def __post_init__(self) -> None:
        if not self.schema_id:
            raise ConfigurationError("DescriptorSchema.schema_id must not be empty.")
        if not self.descriptors:
            raise ConfigurationError("DescriptorSchema.descriptors must not be empty.")
        if self.distance_metric != "euclidean":
            raise ConfigurationError("Only euclidean descriptor distance is supported in Phase 1.")
        names = [item.name for item in self.descriptors]
        if len(names) != len(set(names)):
            raise ConfigurationError("DescriptorSchema descriptor names must be unique.")
        expected = _digest(
            _descriptor_schema_payload(self.schema_id, self.descriptors, self.distance_metric)
        )
        if self.digest and self.digest != expected:
            raise ConfigurationError("DescriptorSchema digest mismatch.")
        object.__setattr__(self, "digest", expected)

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "schema_id": self.schema_id,
            "descriptors": [item.to_dict() for item in self.descriptors],
            "distance_metric": self.distance_metric,
            "digest": self.digest,
        }

    def to_behavior_schema(self) -> BehaviorDescriptorSchema:
        return BehaviorDescriptorSchema(
            descriptor_names=tuple(item.name for item in self.descriptors),
            bins_per_descriptor={item.name: item.bins for item in self.descriptors},
            min_values={item.name: item.range_min for item in self.descriptors},
            max_values={item.name: item.range_max for item in self.descriptors},
        )


def build_descriptor_schema(
    schema_id: str,
    descriptors: Sequence[DescriptorSpec],
    *,
    distance_metric: str = "euclidean",
) -> DescriptorSchema:
    """Factory that computes the schema digest rather than trusting callers."""

    return DescriptorSchema(
        schema_id=schema_id, descriptors=tuple(descriptors), distance_metric=distance_metric
    )


def descriptor_schema_from_dict(data: Mapping[str, JsonValue]) -> DescriptorSchema:
    raw = data.get("descriptors")
    if not isinstance(raw, list):
        raise ConfigurationError("DescriptorSchema.descriptors must be a list.")
    specs: list[DescriptorSpec] = []
    for item in raw:
        if not isinstance(item, Mapping):
            raise ConfigurationError("DescriptorSpec entries must be objects.")
        name = item.get("name")
        source = item.get("source")
        range_min = item.get("range_min")
        range_max = item.get("range_max")
        bins = item.get("bins")
        normalize = item.get("normalize", True)
        if not isinstance(name, str) or not isinstance(source, str):
            raise ConfigurationError("DescriptorSpec.name/source must be strings.")
        if isinstance(range_min, bool) or not isinstance(range_min, int | float):
            raise ConfigurationError("DescriptorSpec.range_min must be numeric.")
        if isinstance(range_max, bool) or not isinstance(range_max, int | float):
            raise ConfigurationError("DescriptorSpec.range_max must be numeric.")
        if isinstance(bins, bool) or not isinstance(bins, int):
            raise ConfigurationError("DescriptorSpec.bins must be an integer.")
        if not isinstance(normalize, bool):
            raise ConfigurationError("DescriptorSpec.normalize must be boolean.")
        specs.append(
            DescriptorSpec(
                name=name,
                source=source,
                range_min=float(range_min),
                range_max=float(range_max),
                bins=bins,
                normalize=normalize,
            )
        )
    schema_id = data.get("schema_id")
    distance_metric = data.get("distance_metric", "euclidean")
    digest = data.get("digest", "")
    if not isinstance(schema_id, str) or not isinstance(distance_metric, str):
        raise ConfigurationError("DescriptorSchema.schema_id/distance_metric must be strings.")
    if not isinstance(digest, str):
        raise ConfigurationError("DescriptorSchema.digest must be a string.")
    return DescriptorSchema(
        schema_id=schema_id,
        descriptors=tuple(specs),
        distance_metric=distance_metric,
        digest=digest,
    )


def default_phase1_descriptor_schema() -> DescriptorSchema:
    """Return the Phase 1 default multi-family QD descriptor schema."""

    specs = (
        DescriptorSpec("survival_ticks", "runtime", 0.0, 100.0, 10),
        DescriptorSpec("energy_efficiency", "runtime", 0.0, 1.0, 10),
        DescriptorSpec("resource_gain", "runtime", 0.0, 100.0, 10),
        DescriptorSpec("blocked_ratio", "runtime", 0.0, 1.0, 10),
        DescriptorSpec("capsule_usage", "capsule", 0.0, 100.0, 10),
        DescriptorSpec("lineage_depth", "lineage", 0.0, 100.0, 10),
        DescriptorSpec("genome_length", "genome", 0.0, 512.0, 16),
        DescriptorSpec("unique_positions", "movement", 0.0, 100.0, 10),
        DescriptorSpec("action_distribution_entropy", "behavior", 0.0, 10.0, 10),
    )
    return build_descriptor_schema("phase1_default_qd_descriptors", specs)


def _descriptor_schema_payload(
    schema_id: str, descriptors: Sequence[DescriptorSpec], distance_metric: str
) -> dict[str, JsonValue]:
    return {
        "schema_id": schema_id,
        "descriptors": [item.to_dict() for item in descriptors],
        "distance_metric": distance_metric,
    }
