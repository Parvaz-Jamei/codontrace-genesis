"""Active quality-diversity search loop helpers.

The existing QD archive can characterize runs. This module adds a minimal active
search loop: sample parents, emit offspring, evaluate quality/descriptor, update
an archive, and feed archive/novelty information back into parent selection.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from enum import Enum

from codontrace._types import JsonValue
from codontrace.errors import ConfigurationError
from codontrace._numeric import finite_float, finite_json_dumps
from codontrace.rng import RNGManager


class QDDescriptorFamily(str, Enum):
    MOVEMENT = "movement"
    ENERGY = "energy"
    REPRODUCTION = "reproduction"
    CAUSAL = "causal"
    CAPSULE = "capsule"
    GENOME = "genome"
    ENVIRONMENT = "environment"
    SOCIAL = "social"


@dataclass(frozen=True, slots=True)
class QDDescriptorConfig:
    descriptor_names: tuple[str, ...]
    bins_per_descriptor: dict[str, int] = field(default_factory=dict)
    min_values: dict[str, float] = field(default_factory=dict)
    max_values: dict[str, float] = field(default_factory=dict)
    families: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.descriptor_names:
            raise ConfigurationError("QDDescriptorConfig.descriptor_names must not be empty.")
        clean_bins: dict[str, int] = {}
        clean_min: dict[str, float] = {}
        clean_max: dict[str, float] = {}
        for name in self.descriptor_names:
            bins = self.bins_per_descriptor.get(name, 8)
            if isinstance(bins, bool) or not isinstance(bins, int) or bins <= 0:
                raise ConfigurationError("bins_per_descriptor values must be positive.")
            min_value = finite_float(f"QDDescriptorConfig.min_values[{name}]", self.min_values.get(name, 0.0))
            max_value = finite_float(f"QDDescriptorConfig.max_values[{name}]", self.max_values.get(name, 1.0))
            if max_value <= min_value:
                raise ConfigurationError(f"max_values[{name!r}] must be greater than min_values.")
            clean_bins[name] = bins
            clean_min[name] = min_value
            clean_max[name] = max_value
        object.__setattr__(self, "bins_per_descriptor", clean_bins)
        object.__setattr__(self, "min_values", clean_min)
        object.__setattr__(self, "max_values", clean_max)
        object.__setattr__(self, "families", dict(self.families))

    @classmethod
    def default(cls) -> QDDescriptorConfig:
        return cls(
            descriptor_names=("unique_positions", "energy_efficiency"),
            bins_per_descriptor={"unique_positions": 8, "energy_efficiency": 8},
            min_values={"unique_positions": 0.0, "energy_efficiency": 0.0},
            max_values={"unique_positions": 16.0, "energy_efficiency": 1.0},
            families={
                "unique_positions": QDDescriptorFamily.MOVEMENT.value,
                "energy_efficiency": QDDescriptorFamily.ENERGY.value,
            },
        )

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "descriptor_names": list(self.descriptor_names),
            "bins_per_descriptor": dict(sorted(self.bins_per_descriptor.items())),
            "min_values": dict(sorted(self.min_values.items())),
            "max_values": dict(sorted(self.max_values.items())),
            "families": dict(sorted(self.families.items())),
        }

    def digest(self) -> str:
        return _digest(self.to_dict())


@dataclass(frozen=True, slots=True)
class QDSearchConfig:
    descriptor_config: QDDescriptorConfig = field(default_factory=QDDescriptorConfig.default)
    generations: int = 3
    offspring_per_generation: int = 4
    novelty_weight: float = 0.0
    seed: int = 1
    qd_selection_enabled: bool = True

    def __post_init__(self) -> None:
        if self.generations < 0 or self.offspring_per_generation <= 0:
            raise ConfigurationError("QDSearchConfig generations/offspring_per_generation invalid.")
        object.__setattr__(self, "novelty_weight", finite_float("novelty_weight", self.novelty_weight, non_negative=True))

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "descriptor_config": self.descriptor_config.to_dict(),
            "generations": self.generations,
            "offspring_per_generation": self.offspring_per_generation,
            "novelty_weight": self.novelty_weight,
            "seed": self.seed,
            "qd_selection_enabled": self.qd_selection_enabled,
        }

    def digest(self) -> str:
        return _digest(self.to_dict())


@dataclass(frozen=True, slots=True)
class QDSearchCandidate:
    genome: str
    quality: float
    descriptors: dict[str, float]
    parent_genome: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "quality", finite_float("QDSearchCandidate.quality", self.quality))
        clean: dict[str, float] = {}
        for name, value in self.descriptors.items():
            clean[str(name)] = finite_float(f"QDSearchCandidate.descriptors[{name}]", value)  # type: ignore[assignment]
        object.__setattr__(self, "descriptors", clean)

    def bin_key(self, config: QDDescriptorConfig) -> tuple[int, ...]:
        bins: list[int] = []
        for name in config.descriptor_names:
            value = self.descriptors.get(name, 0.0)
            min_value = config.min_values.get(name, 0.0)
            max_value = config.max_values.get(name, 1.0)
            count = config.bins_per_descriptor.get(name, 8)
            if max_value <= min_value:
                bins.append(0)
                continue
            scaled = (value - min_value) / (max_value - min_value)
            bins.append(max(0, min(count - 1, int(scaled * count))))
        return tuple(bins)

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "genome": self.genome,
            "quality": self.quality,
            "descriptors": dict(sorted(self.descriptors.items())),
            "parent_genome": self.parent_genome,
        }


@dataclass(frozen=True, slots=True)
class QDSearchArchive:
    elites: dict[tuple[int, ...], QDSearchCandidate] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "elites", dict(self.elites))

    def update(
        self, candidate: QDSearchCandidate, config: QDDescriptorConfig
    ) -> tuple[QDSearchArchive, bool]:
        # Re-check at the archive boundary because this is an evidence-bearing update.
        finite_float("QDSearchArchive.candidate.quality", candidate.quality)
        for name, value in candidate.descriptors.items():
            finite_float(f"QDSearchArchive.candidate.descriptors[{name}]", value)
        key = candidate.bin_key(config)
        current = self.elites.get(key)
        if current is not None and current.quality > candidate.quality:
            return self, False
        next_elites = dict(self.elites)
        next_elites[key] = candidate
        return QDSearchArchive(next_elites), current is None

    def sample_parent(self, rng: RNGManager, novelty_weight: float) -> str | None:
        if not self.elites:
            return None
        ranked = sorted(
            self.elites.items(),
            key=lambda item: (item[1].quality + novelty_weight * sum(item[0]), item[1].genome),
            reverse=True,
        )
        if novelty_weight > 0:
            return ranked[0][1].genome
        return ranked[rng.randrange(len(ranked))][1].genome

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "elites": [
                {"bin": list(key), "candidate": value.to_dict()}
                for key, value in sorted(self.elites.items())
            ]
        }

    def digest(self) -> str:
        return _digest(self.to_dict())


class QDEmitter:
    def emit(self, parent: str, rng: RNGManager) -> str:  # pragma: no cover - protocol-like base
        raise NotImplementedError


class RandomEmitter(QDEmitter):
    def emit(self, parent: str, rng: RNGManager) -> str:
        length = max(1, len(parent))
        return "".join(rng.choice("01") for _ in range(length))


class MutationEmitter(QDEmitter):
    def emit(self, parent: str, rng: RNGManager) -> str:
        if not parent:
            return "0"
        index = rng.randrange(len(parent))
        flipped = "1" if parent[index] == "0" else "0"
        return parent[:index] + flipped + parent[index + 1 :]


class ArchiveSamplingEmitter(MutationEmitter):
    alias_of = "MutationEmitter"
    behavior_status = "alias_no_extra_behavior"
    claim_eligible_for_archive_sampling_bias = False
    emitter_behavior_status = "alias_no_extra_behavior"


class NoveltyBiasedEmitter(MutationEmitter):
    alias_of = "MutationEmitter"
    behavior_status = "alias_no_extra_behavior"
    claim_eligible_for_novelty_bias = False
    emitter_behavior_status = "alias_no_extra_behavior"


@dataclass(frozen=True, slots=True)
class QDParentSelection:
    parent_genome: str
    source: str
    novelty_weight: float
    parent_candidate_id: str | None = None
    parent_candidate_digest: str | None = None
    provenance_status: str = "not_applicable"

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "parent_genome": self.parent_genome,
            "source": self.source,
            "novelty_weight": self.novelty_weight,
            "parent_candidate_id": self.parent_candidate_id,
            "parent_candidate_digest": self.parent_candidate_digest,
            "provenance_status": self.provenance_status,
        }


@dataclass(frozen=True, slots=True)
class QDSearchStepResult:
    generation: int
    emitted_count: int
    inserted_count: int
    archive_digest: str
    parent_selections: tuple[QDParentSelection, ...]

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "generation": self.generation,
            "emitted_count": self.emitted_count,
            "inserted_count": self.inserted_count,
            "archive_digest": self.archive_digest,
            "parent_selections": [item.to_dict() for item in self.parent_selections],
        }


@dataclass(frozen=True, slots=True)
class QDSearchRunResult:
    config: QDSearchConfig
    steps: tuple[QDSearchStepResult, ...]
    archive: QDSearchArchive

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "config": self.config.to_dict(),
            "steps": [item.to_dict() for item in self.steps],
            "archive": self.archive.to_dict(),
        }

    def digest(self) -> str:
        return _digest(self.to_dict())


class QDSearchRunner:
    def __init__(
        self,
        config: QDSearchConfig,
        evaluator: Callable[[str], tuple[float, Mapping[str, float]]],
        emitter: QDEmitter | None = None,
    ) -> None:
        self.config = config
        self.evaluator = evaluator
        self.emitter = emitter or MutationEmitter()

    def run(self, initial_genomes: Sequence[str]) -> QDSearchRunResult:
        if not initial_genomes:
            raise ConfigurationError("QDSearchRunner requires at least one initial genome.")
        rng = RNGManager(seed=self.config.seed, namespace="qd_search")
        archive = QDSearchArchive()
        steps: list[QDSearchStepResult] = []
        parents = list(initial_genomes)
        for generation in range(self.config.generations):
            selections: list[QDParentSelection] = []
            inserted = 0
            for index in range(self.config.offspring_per_generation):
                archive_parent = (
                    archive.sample_parent(rng, self.config.novelty_weight)
                    if self.config.qd_selection_enabled
                    else None
                )
                if archive_parent is None:
                    parent = parents[(generation + index) % len(parents)]
                    source = "initial_population"
                else:
                    parent = archive_parent
                    source = "archive_novelty" if self.config.novelty_weight > 0 else "archive"
                genome = self.emitter.emit(parent, rng)
                quality, descriptors_raw = self.evaluator(genome)
                candidate = QDSearchCandidate(
                    genome,
                    float(quality),
                    {k: float(v) for k, v in descriptors_raw.items()},
                    parent,
                )
                archive, was_inserted = archive.update(candidate, self.config.descriptor_config)
                inserted += int(was_inserted)
                selections.append(QDParentSelection(parent, source, self.config.novelty_weight))
                parents.append(genome)
            steps.append(
                QDSearchStepResult(
                    generation,
                    self.config.offspring_per_generation,
                    inserted,
                    archive.digest(),
                    tuple(selections),
                )
            )
        return QDSearchRunResult(self.config, tuple(steps), archive)


class QDCandidateSearchRunner:
    """Canonical active-QD runner that preserves QDCandidate replay metadata.

    ``QDSearchRunner`` remains available for string-genome compatibility, but new
    replay-critical integrations should use this candidate-level path so genome,
    macro, translation, and mutation digests are carried through emitted children.
    """

    def __init__(
        self,
        config: QDSearchConfig,
        evaluator: Callable[[QDCandidate], tuple[float, Mapping[str, float]]],
        emitter: QDEmitter | None = None,
    ) -> None:
        self.config = config
        self.evaluator = evaluator
        self.emitter = emitter or MutationEmitter()

    def run(self, initial_candidates: Sequence[QDCandidate]) -> QDSearchRunResult:
        if not initial_candidates:
            raise ConfigurationError("QDCandidateSearchRunner requires at least one candidate.")
        if any(candidate.genome_bits is None for candidate in initial_candidates):
            raise ConfigurationError("QDCandidateSearchRunner requires inline genome_bits.")
        rng = RNGManager(seed=self.config.seed, namespace="qd_candidate_search")
        archive = QDSearchArchive()
        steps: list[QDSearchStepResult] = []
        parents = list(initial_candidates)
        genome_to_candidate: dict[str, QDCandidate] = {
            candidate.genome_bits or "": candidate for candidate in initial_candidates if candidate.genome_bits
        }
        for generation in range(self.config.generations):
            selections: list[QDParentSelection] = []
            inserted = 0
            for index in range(self.config.offspring_per_generation):
                fallback_parent = parents[(generation + index) % len(parents)]
                parent = fallback_parent
                parent_bits = parent.genome_bits or "0"
                provenance_status = "resolved_candidate"
                archive_parent_bits = (
                    archive.sample_parent(rng, self.config.novelty_weight)
                    if self.config.qd_selection_enabled
                    else None
                )
                if archive_parent_bits is not None:
                    source = "archive_novelty" if self.config.novelty_weight > 0 else "archive"
                    parent_bits = archive_parent_bits
                    resolved_parent = genome_to_candidate.get(archive_parent_bits)
                    if resolved_parent is not None:
                        parent = resolved_parent
                        provenance_status = "resolved_candidate"
                    else:
                        parent = QDCandidate.from_genome_bits(
                            archive_parent_bits,
                            candidate_id="opaque_archive_parent",
                            parent_ids=(),
                            lineage_tags=("archive_parent_unresolved",),
                            metadata={"provenance_status": "opaque_archive_parent"},
                        )
                        provenance_status = "opaque_archive_parent"
                else:
                    source = "initial_or_emitted_candidate"
                child_bits = self.emitter.emit(parent_bits, rng)
                child = QDCandidate.from_genome_bits(
                    child_bits,
                    candidate_id=f"{parent.candidate_id}/candidate-child-{generation}-{index}",
                    parent_ids=(parent.candidate_id,),
                    genome_program_digest=parent.genome_program_digest,
                    macro_registry_digest=parent.macro_registry_digest,
                    translation_profile_digest=parent.translation_profile_digest,
                    mutation_record_digest=_digest(
                        {
                            "parent_candidate_digest": parent.digest(),
                            "parent_candidate_id": parent.candidate_id,
                            "parent_genome_digest": parent.genome_digest,
                            "parent_provenance_status": provenance_status,
                            "child_bits": child_bits,
                            "generation": generation,
                            "index": index,
                        }
                    ),
                    lineage_tags=(*parent.lineage_tags, "qd_candidate_child"),
                    metadata={"parent_provenance_status": provenance_status},
                )
                quality, descriptors_raw = self.evaluator(child)
                archive_candidate = QDSearchCandidate(
                    child_bits,
                    float(quality),
                    {k: float(v) for k, v in descriptors_raw.items()},
                    parent_bits,
                )
                archive, was_inserted = archive.update(
                    archive_candidate, self.config.descriptor_config
                )
                inserted += int(was_inserted)
                selections.append(
                    QDParentSelection(
                        parent_bits,
                        source,
                        self.config.novelty_weight,
                        parent_candidate_id=parent.candidate_id,
                        parent_candidate_digest=parent.digest(),
                        provenance_status=provenance_status,
                    )
                )
                parents.append(child)
                genome_to_candidate[child_bits] = child
            steps.append(
                QDSearchStepResult(
                    generation,
                    self.config.offspring_per_generation,
                    inserted,
                    archive.digest(),
                    tuple(selections),
                )
            )
        return QDSearchRunResult(self.config, tuple(steps), archive)


def _digest(payload: Mapping[str, JsonValue]) -> str:
    encoded = finite_json_dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class QDCandidate:
    """Genome-program-level QD candidate, not a plain genome string."""

    candidate_id: str
    genome_digest: str
    genome_bits: str | None
    genome_program_digest: str | None
    macro_registry_digest: str | None
    translation_profile_digest: str | None
    parent_ids: tuple[str, ...]
    mutation_record_digest: str | None
    lineage_tags: tuple[str, ...]
    genome_reference_status: str = (
        "missing"  # verified_inline | opaque_external_reference | missing | invalid_digest
    )
    metadata: tuple[tuple[str, JsonValue], ...] = ()

    def __post_init__(self) -> None:
        if not self.candidate_id:
            raise ConfigurationError("QDCandidate requires candidate_id.")
        status = self.genome_reference_status
        if self.genome_bits is not None:
            computed = hashlib.sha256(self.genome_bits.encode("utf-8")).hexdigest()
            if self.genome_digest != computed:
                raise ConfigurationError(
                    "QDCandidate genome_digest mismatch for inline genome_bits."
                )
            status = "verified_inline"
        elif self.genome_digest:
            status = "opaque_external_reference"
        else:
            status = "missing"
        if status not in {
            "verified_inline",
            "opaque_external_reference",
            "missing",
            "invalid_digest",
        }:
            raise ConfigurationError("Unsupported QDCandidate.genome_reference_status.")
        object.__setattr__(self, "genome_reference_status", status)
        object.__setattr__(self, "metadata", tuple(sorted((str(k), v) for k, v in self.metadata)))

    @classmethod
    def from_genome_bits(
        cls,
        genome_bits: str,
        *,
        candidate_id: str | None = None,
        parent_ids: Sequence[str] = (),
        genome_program_digest: str | None = None,
        macro_registry_digest: str | None = None,
        translation_profile_digest: str | None = None,
        mutation_record_digest: str | None = None,
        lineage_tags: Sequence[str] = (),
        metadata: Mapping[str, JsonValue] | None = None,
    ) -> QDCandidate:
        digest = hashlib.sha256(genome_bits.encode("utf-8")).hexdigest()
        cid = candidate_id or f"qd:{digest[:16]}"
        return cls(
            candidate_id=cid,
            genome_digest=digest,
            genome_bits=genome_bits,
            genome_program_digest=genome_program_digest,
            macro_registry_digest=macro_registry_digest,
            translation_profile_digest=translation_profile_digest,
            parent_ids=tuple(parent_ids),
            mutation_record_digest=mutation_record_digest,
            lineage_tags=tuple(lineage_tags),
            genome_reference_status="verified_inline",
            metadata=tuple(sorted((metadata or {}).items())),
        )

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "candidate_id": self.candidate_id,
            "genome_digest": self.genome_digest,
            "genome_bits": self.genome_bits,
            "genome_program_digest": self.genome_program_digest,
            "macro_registry_digest": self.macro_registry_digest,
            "translation_profile_digest": self.translation_profile_digest,
            "parent_ids": list(self.parent_ids),
            "mutation_record_digest": self.mutation_record_digest,
            "lineage_tags": list(self.lineage_tags),
            "genome_reference_status": self.genome_reference_status,
            "metadata": [[k, v] for k, v in self.metadata],
        }

    def digest(self) -> str:
        return _digest(self.to_dict())

    @classmethod
    def from_dict(cls, data: Mapping[str, JsonValue]) -> QDCandidate:
        meta_raw = data.get("metadata", [])
        if not isinstance(meta_raw, list):
            raise ConfigurationError("QDCandidate.metadata must be a list.")
        metadata: list[tuple[str, JsonValue]] = []
        for item in meta_raw:
            if not isinstance(item, list) or len(item) != 2 or not isinstance(item[0], str):
                raise ConfigurationError("QDCandidate.metadata entries must be [key, value].")
            metadata.append((item[0], item[1]))
        return cls(
            candidate_id=str(data["candidate_id"]),
            genome_digest=str(data["genome_digest"]),
            genome_bits=None if data.get("genome_bits") is None else str(data.get("genome_bits")),
            genome_program_digest=None
            if data.get("genome_program_digest") is None
            else str(data.get("genome_program_digest")),
            macro_registry_digest=None
            if data.get("macro_registry_digest") is None
            else str(data.get("macro_registry_digest")),
            translation_profile_digest=None
            if data.get("translation_profile_digest") is None
            else str(data.get("translation_profile_digest")),
            parent_ids=_string_tuple(data.get("parent_ids")),
            mutation_record_digest=None
            if data.get("mutation_record_digest") is None
            else str(data.get("mutation_record_digest")),
            lineage_tags=_string_tuple(data.get("lineage_tags")),
            genome_reference_status=str(data.get("genome_reference_status", "missing")),
            metadata=tuple(metadata),
        )


@dataclass(frozen=True, slots=True)
class QDAskResult:
    candidates: tuple[QDCandidate, ...]
    emitter_name: str
    scheduler_state_digest_before: str
    scheduler_state_digest_after: str
    rng_state_digest_before: str
    rng_state_digest_after: str

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "candidates": [candidate.to_dict() for candidate in self.candidates],
            "emitter_name": self.emitter_name,
            "scheduler_state_digest_before": self.scheduler_state_digest_before,
            "scheduler_state_digest_after": self.scheduler_state_digest_after,
            "rng_state_digest_before": self.rng_state_digest_before,
            "rng_state_digest_after": self.rng_state_digest_after,
        }

    def digest(self) -> str:
        return _digest(self.to_dict())


@dataclass(frozen=True, slots=True)
class QDEvaluateResult:
    candidate_id: str
    objective: float
    descriptor: tuple[float, ...]
    fitness_breakdown_digest: str
    valid: bool
    failure_reason: str | None = None

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "candidate_id": self.candidate_id,
            "objective": self.objective,
            "descriptor": list(self.descriptor),
            "fitness_breakdown_digest": self.fitness_breakdown_digest,
            "valid": self.valid,
            "failure_reason": self.failure_reason,
        }

    def digest(self) -> str:
        return _digest(self.to_dict())


@dataclass(frozen=True, slots=True)
class QDTellResult:
    archive_digest_before: str
    archive_digest_after: str
    inserted: int
    improved: int
    rejected: int
    coverage: float
    qd_score: float
    valid_evaluation_count: int = 0
    invalid_evaluation_count: int = 0
    archive_update_status: str = "not_observed"

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "archive_digest_before": self.archive_digest_before,
            "archive_digest_after": self.archive_digest_after,
            "inserted": self.inserted,
            "improved": self.improved,
            "rejected": self.rejected,
            "coverage": self.coverage,
            "qd_score": self.qd_score,
            "valid_evaluation_count": self.valid_evaluation_count,
            "invalid_evaluation_count": self.invalid_evaluation_count,
            "archive_update_status": self.archive_update_status,
        }

    def digest(self) -> str:
        return _digest(self.to_dict())


@dataclass(frozen=True, slots=True)
class QDSchedulerState:
    archive_digest: str
    emitter_state_digest: str
    descriptor_schema_digest: str
    generation: int
    selection_feedback_policy: str = "none"
    parent_selection_feedback_digest: str | None = None
    rng_state_digest: str | None = None
    digest: str = ""

    def __post_init__(self) -> None:
        payload = self._payload()
        computed = _digest(payload)
        if self.digest and self.digest != computed:
            raise ConfigurationError("QDSchedulerState digest mismatch.")
        object.__setattr__(self, "digest", computed)

    def _payload(self) -> dict[str, JsonValue]:
        return {
            "archive_digest": self.archive_digest,
            "emitter_state_digest": self.emitter_state_digest,
            "descriptor_schema_digest": self.descriptor_schema_digest,
            "generation": self.generation,
            "selection_feedback_policy": self.selection_feedback_policy,
            "parent_selection_feedback_digest": self.parent_selection_feedback_digest,
            "rng_state_digest": self.rng_state_digest,
        }

    def to_dict(self) -> dict[str, JsonValue]:
        return {**self._payload(), "digest": self.digest}

    @classmethod
    def from_dict(cls, data: Mapping[str, JsonValue]) -> QDSchedulerState:
        state = cls(
            archive_digest=str(data.get("archive_digest", "")),
            emitter_state_digest=str(data.get("emitter_state_digest", "")),
            descriptor_schema_digest=str(data.get("descriptor_schema_digest", "")),
            generation=_json_int(data.get("generation", 0), "generation"),
            selection_feedback_policy=str(data.get("selection_feedback_policy", "none")),
            parent_selection_feedback_digest=None
            if data.get("parent_selection_feedback_digest") is None
            else str(data.get("parent_selection_feedback_digest")),
            rng_state_digest=None
            if data.get("rng_state_digest") is None
            else str(data.get("rng_state_digest")),
        )
        if state.digest != data.get("digest"):
            raise ConfigurationError("QDSchedulerState digest mismatch.")
        return state


def _string_tuple(value: JsonValue | None) -> tuple[str, ...]:
    if not isinstance(value, list):
        return ()
    return tuple(str(v) for v in value if isinstance(v, str))


def _json_int(value: JsonValue | None, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ConfigurationError(f"{field} must be an integer")
    return value


def qd_candidate_from_dict(data: Mapping[str, JsonValue]) -> QDCandidate:
    return QDCandidate.from_dict(data)


def validate_qd_candidate_digest(
    data: Mapping[str, JsonValue], expected_digest: str
) -> QDCandidate:
    candidate = QDCandidate.from_dict(data)
    if candidate.digest() != expected_digest:
        raise ConfigurationError("QDCandidate digest mismatch.")
    return candidate


def ask_qd_candidates(
    parents: Sequence[QDCandidate],
    *,
    rng: RNGManager,
    count: int,
    emitter_name: str = "mutation_emitter",
) -> QDAskResult:
    """Emit QDCandidate objects using the Phase-1 ask contract."""

    if not parents:
        raise ConfigurationError("ask_qd_candidates requires at least one parent candidate.")
    before_rng = rng.state_digest()
    before_sched = _digest(
        {"parents": [p.digest() for p in parents], "count": count, "emitter": emitter_name}
    )
    emitted: list[QDCandidate] = []
    for index in range(count):
        parent = rng.choice(parents)
        bits = parent.genome_bits or "0"
        if bits:
            pos = rng.randrange(len(bits))
            flipped = "1" if bits[pos] == "0" else "0"
            child_bits = bits[:pos] + flipped + bits[pos + 1 :]
        else:
            child_bits = "0"
        emitted.append(
            QDCandidate.from_genome_bits(
                child_bits,
                candidate_id=(
                    f"{parent.candidate_id}/child-{index}-"
                    f"{hashlib.sha256(child_bits.encode()).hexdigest()[:8]}"
                ),
                parent_ids=(parent.candidate_id,),
                genome_program_digest=parent.genome_program_digest,
                macro_registry_digest=parent.macro_registry_digest,
                translation_profile_digest=parent.translation_profile_digest,
                mutation_record_digest=_digest(
                    {"parent": parent.digest(), "child_bits": child_bits, "index": index}
                ),
                lineage_tags=(*parent.lineage_tags, "qd_child"),
            )
        )
    after_sched = _digest({"before": before_sched, "candidates": [c.digest() for c in emitted]})
    return QDAskResult(
        candidates=tuple(emitted),
        emitter_name=emitter_name,
        scheduler_state_digest_before=before_sched,
        scheduler_state_digest_after=after_sched,
        rng_state_digest_before=before_rng,
        rng_state_digest_after=rng.state_digest(),
    )


def tell_qd_results(
    archive_before_digest: str,
    archive_after_digest: str,
    evaluations: Sequence[QDEvaluateResult],
    *,
    coverage: float,
    qd_score: float,
    archive_update: object | None = None,
) -> QDTellResult:
    valid_count = sum(1 for item in evaluations if item.valid)
    invalid_count = sum(1 for item in evaluations if not item.valid)
    inserted = improved = rejected = 0
    update_status = "not_observed"
    if archive_update is not None:
        inserted = int(getattr(archive_update, "inserted_count", getattr(archive_update, "inserted", 0)))
        improved = int(getattr(archive_update, "replaced_count", getattr(archive_update, "replaced", 0)))
        rejected = int(getattr(archive_update, "rejected_count", getattr(archive_update, "rejected", 0))) + invalid_count
        update_status = "measured"
    else:
        rejected = invalid_count
    return QDTellResult(
        archive_digest_before=archive_before_digest,
        archive_digest_after=archive_after_digest,
        inserted=inserted,
        improved=improved,
        rejected=rejected,
        coverage=round(float(coverage), 10),
        qd_score=round(float(qd_score), 10),
        valid_evaluation_count=valid_count,
        invalid_evaluation_count=invalid_count,
        archive_update_status=update_status,
    )
