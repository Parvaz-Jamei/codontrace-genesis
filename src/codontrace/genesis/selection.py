"""Deterministic selection and evolution policies for GENESIS population runs.

These helpers provide controlled selection pressure for research-alpha runs. They
are deliberately small, auditable, dependency-free, and do not claim open-ended
evolution or artificial-life discovery.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from enum import Enum
from typing import Protocol, runtime_checkable

from codontrace._types import JsonValue
from codontrace._numeric import finite_float, finite_json_dumps
from codontrace.errors import ConfigurationError


class QDFallbackReason(str, Enum):
    """Stable QD/novelty selection audit reasons."""

    SELECTION_APPLIED = "selection_applied"
    NO_SELECTION_PRESSURE = "no_selection_pressure"
    CAPACITY_NOT_EXCEEDED = "capacity_not_exceeded"
    ARCHIVE_EMPTY = "archive_empty"
    NOVELTY_SCORES_UNAVAILABLE = "novelty_scores_unavailable"
    NOVELTY_SCORES_ZERO = "novelty_scores_zero"
    FITNESS_DOMINATES = "fitness_dominates"
    QD_DISABLED = "qd_disabled"
    QD_ARCHIVE_ONLY_MODE = "qd_archive_only_mode"
    SINGLE_CANDIDATE_NO_SELECTION_PRESSURE = "single_candidate_no_selection_pressure"


@runtime_checkable
class SelectionPolicy(Protocol):
    """Protocol for deterministic capacity selection policies."""

    @property
    def name(self) -> str:
        """Stable policy name."""
        ...

    def select(
        self,
        candidates: Sequence[object],
        *,
        fitness_scores: Mapping[str, float],
        max_population: int,
        novelty_scores: Mapping[str, float] | None = None,
        ages: Mapping[str, int] | None = None,
    ) -> tuple[object, ...]:
        """Return selected candidates without mutating inputs."""
        ...


@dataclass(frozen=True, slots=True)
class FitnessProportionalSelection:
    """Deterministic fitness-weighted ranking.

    The implementation avoids hidden randomness: candidates are ordered by
    positive fitness weight, then by id. This gives fitness pressure while
    keeping replay deterministic.
    """

    name: str = "fitness_proportional"

    def select(
        self,
        candidates: Sequence[object],
        *,
        fitness_scores: Mapping[str, float],
        max_population: int,
        novelty_scores: Mapping[str, float] | None = None,
        ages: Mapping[str, int] | None = None,
    ) -> tuple[object, ...]:
        return _top_by_score(candidates, fitness_scores, max_population)


@dataclass(frozen=True, slots=True)
class TournamentSelection:
    """Deterministic tournament selection using sorted windows."""

    tournament_size: int = 3
    name: str = "tournament"

    def __post_init__(self) -> None:
        if self.tournament_size <= 0:
            msg = "tournament_size must be > 0."
            raise ConfigurationError(msg)

    def select(
        self,
        candidates: Sequence[object],
        *,
        fitness_scores: Mapping[str, float],
        max_population: int,
        novelty_scores: Mapping[str, float] | None = None,
        ages: Mapping[str, int] | None = None,
    ) -> tuple[object, ...]:
        ordered = sorted(candidates, key=lambda item: _stable_id(item))
        winners: list[object] = []
        remaining = list(ordered)
        while remaining and len(winners) < max_population:
            window = remaining[: self.tournament_size]
            winner = _top_by_score(window, fitness_scores, 1)[0]
            winners.append(winner)
            remaining.remove(winner)
        return tuple(winners)


@dataclass(frozen=True, slots=True)
class ElitismSelection:
    """Keep elites first, then fill with fitness-proportional ranking."""

    elitism_count: int = 1
    name: str = "elitism"

    def __post_init__(self) -> None:
        if self.elitism_count < 0:
            msg = "elitism_count must be >= 0."
            raise ConfigurationError(msg)

    def select(
        self,
        candidates: Sequence[object],
        *,
        fitness_scores: Mapping[str, float],
        max_population: int,
        novelty_scores: Mapping[str, float] | None = None,
        ages: Mapping[str, int] | None = None,
    ) -> tuple[object, ...]:
        if max_population <= 0:
            return ()
        elites = list(
            _top_by_score(candidates, fitness_scores, min(self.elitism_count, max_population))
        )
        elite_ids = {_stable_id(item) for item in elites}
        rest = [item for item in candidates if _stable_id(item) not in elite_ids]
        fill = _top_by_score(rest, fitness_scores, max_population - len(elites))
        return tuple(elites + list(fill))


@dataclass(frozen=True, slots=True)
class NoveltyWeightedSelection:
    """Rank by weighted fitness and novelty score."""

    fitness_weight: float = 1.0
    novelty_weight: float = 1.0
    name: str = "novelty_weighted"

    def __post_init__(self) -> None:
        fitness_weight = finite_float(
            "NoveltyWeightedSelection.fitness_weight",
            self.fitness_weight,
            non_negative=True,
        )
        novelty_weight = finite_float(
            "NoveltyWeightedSelection.novelty_weight",
            self.novelty_weight,
            non_negative=True,
        )
        if fitness_weight == 0.0 and novelty_weight == 0.0:
            msg = "At least one of fitness_weight or novelty_weight must be > 0."
            raise ConfigurationError(msg)
        object.__setattr__(self, "fitness_weight", fitness_weight)
        object.__setattr__(self, "novelty_weight", novelty_weight)

    def select(
        self,
        candidates: Sequence[object],
        *,
        fitness_scores: Mapping[str, float],
        max_population: int,
        novelty_scores: Mapping[str, float] | None = None,
        ages: Mapping[str, int] | None = None,
    ) -> tuple[object, ...]:
        novelty_scores = novelty_scores or {}
        combined = {
            _stable_id(item): round(
                self.fitness_weight * float(fitness_scores.get(_stable_id(item), 0.0))
                + self.novelty_weight * float(novelty_scores.get(_stable_id(item), 0.0)),
                10,
            )
            for item in candidates
        }
        return _top_by_score(candidates, combined, max_population)


@dataclass(frozen=True, slots=True)
class AgeLayeredSelection:
    """Prefer younger organisms within comparable fitness bands."""

    age_weight: float = 0.1
    name: str = "age_layered"

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "age_weight",
            finite_float("AgeLayeredSelection.age_weight", self.age_weight, non_negative=True),
        )

    def select(
        self,
        candidates: Sequence[object],
        *,
        fitness_scores: Mapping[str, float],
        max_population: int,
        novelty_scores: Mapping[str, float] | None = None,
        ages: Mapping[str, int] | None = None,
    ) -> tuple[object, ...]:
        ages = ages or {}
        combined = {
            _stable_id(item): round(
                float(fitness_scores.get(_stable_id(item), 0.0))
                - self.age_weight * float(ages.get(_stable_id(item), 0)),
                10,
            )
            for item in candidates
        }
        return _top_by_score(candidates, combined, max_population)


@dataclass(frozen=True, slots=True)
class EvolutionConfig:
    """Capacity-selection configuration for population/engine orchestration."""

    selection_policy: SelectionPolicy | str = field(default_factory=FitnessProportionalSelection)
    elitism_count: int = 1
    tournament_size: int = 3
    novelty_weight: float = 1.0
    fitness_weight: float = 1.0
    max_population: int | None = None
    extinction_policy: str = "none"
    qd_mode: str = "archive_only"

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "fitness_weight",
            finite_float("EvolutionConfig.fitness_weight", self.fitness_weight, non_negative=True),
        )
        object.__setattr__(
            self,
            "novelty_weight",
            finite_float("EvolutionConfig.novelty_weight", self.novelty_weight, non_negative=True),
        )
        if self.elitism_count < 0 or self.tournament_size <= 0:
            msg = "elitism_count must be >= 0 and tournament_size must be > 0."
            raise ConfigurationError(msg)
        if self.max_population is not None and self.max_population <= 0:
            msg = "max_population must be positive or None."
            raise ConfigurationError(msg)
        if self.extinction_policy not in {"none", "drop_lowest_fitness"}:
            msg = "Unsupported extinction_policy."
            raise ConfigurationError(msg)
        if self.qd_mode not in {"archive_only", "selection_pressure", "disabled"}:
            msg = "qd_mode must be archive_only, selection_pressure, or disabled."
            raise ConfigurationError(msg)

    def resolved_policy(self) -> SelectionPolicy:
        policy = self.selection_policy
        if isinstance(policy, str):
            return policy_from_name(
                policy,
                elitism_count=self.elitism_count,
                tournament_size=self.tournament_size,
                novelty_weight=self.novelty_weight,
                fitness_weight=self.fitness_weight,
            )
        return policy

    def to_dict(self) -> dict[str, JsonValue]:
        policy = self.resolved_policy()
        return {
            "selection_policy": policy.name,
            "elitism_count": self.elitism_count,
            "tournament_size": self.tournament_size,
            "novelty_weight": self.novelty_weight,
            "fitness_weight": self.fitness_weight,
            "max_population": self.max_population,
            "extinction_policy": self.extinction_policy,
            "qd_mode": self.qd_mode,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, JsonValue]) -> EvolutionConfig:
        return cls(
            selection_policy=_str(data, "selection_policy", "fitness_proportional"),
            elitism_count=_int(data, "elitism_count", 1),
            tournament_size=_int(data, "tournament_size", 3),
            novelty_weight=_float(data, "novelty_weight", 1.0),
            fitness_weight=_float(data, "fitness_weight", 1.0),
            max_population=None
            if data.get("max_population") is None
            else _int(data, "max_population", 0),
            extinction_policy=_str(data, "extinction_policy", "none"),
            qd_mode=_str(data, "qd_mode", "archive_only"),
        )

    def digest(self) -> str:
        return _digest(self.to_dict())


@dataclass(frozen=True, slots=True)
class EvolutionSelectionResult:
    """Audit result for a capacity-selection operation.

    The original fields remain positional/backward-compatible.  The optional
    digest and QD fields make novelty/QD pressure inspectable without requiring
    callers to read private internals.
    """

    before_count: int
    after_count: int
    selected_ids: tuple[str, ...]
    dropped_ids: tuple[str, ...]
    policy_name: str
    config_digest: str
    selected_parent_ids: tuple[str, ...] | None = None
    selected_survivor_ids: tuple[str, ...] | None = None
    fitness_scores_digest: str = ""
    novelty_scores_digest: str = ""
    descriptor_digest: str = ""
    selection_changed_by_qd: bool = False
    fallback_reason: str | None = None
    qd_fallback_reason: str | None = None
    qd_mode: str = "disabled"
    qd_parent_order_changed: bool = False
    qd_survivor_set_changed: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, "selected_ids", tuple(self.selected_ids))
        object.__setattr__(self, "dropped_ids", tuple(self.dropped_ids))
        if self.selected_parent_ids is None:
            object.__setattr__(self, "selected_parent_ids", self.selected_ids)
        else:
            object.__setattr__(self, "selected_parent_ids", tuple(self.selected_parent_ids))
        if self.selected_survivor_ids is None:
            object.__setattr__(self, "selected_survivor_ids", self.selected_ids)
        else:
            object.__setattr__(self, "selected_survivor_ids", tuple(self.selected_survivor_ids))

    @property
    def qd_changed_selection(self) -> bool:
        """Backward-compatible alias used by benchmark claim guards."""

        return self.selection_changed_by_qd

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "before_count": self.before_count,
            "after_count": self.after_count,
            "selected_ids": list(self.selected_ids),
            "dropped_ids": list(self.dropped_ids),
            "policy_name": self.policy_name,
            "config_digest": self.config_digest,
            "selected_parent_ids": list(self.selected_parent_ids),
            "selected_survivor_ids": list(self.selected_survivor_ids),
            "fitness_scores_digest": self.fitness_scores_digest,
            "novelty_scores_digest": self.novelty_scores_digest,
            "descriptor_digest": self.descriptor_digest,
            "selection_changed_by_qd": self.selection_changed_by_qd,
            "qd_changed_selection": self.qd_changed_selection,
            "fallback_reason": self.fallback_reason,
            "qd_fallback_reason": self.qd_fallback_reason or self.fallback_reason,
            "qd_mode": self.qd_mode,
            "qd_parent_order_changed": self.qd_parent_order_changed,
            "qd_survivor_set_changed": self.qd_survivor_set_changed,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, JsonValue]) -> EvolutionSelectionResult:
        selected_ids = tuple(str(item) for item in _list(data.get("selected_ids")))
        return cls(
            before_count=_int(data, "before_count", 0),
            after_count=_int(data, "after_count", 0),
            selected_ids=selected_ids,
            dropped_ids=tuple(str(item) for item in _list(data.get("dropped_ids"))),
            policy_name=_str(data, "policy_name"),
            config_digest=_str(data, "config_digest"),
            selected_parent_ids=(
                None
                if "selected_parent_ids" not in data
                else tuple(str(item) for item in _list(data.get("selected_parent_ids")))
            ),
            selected_survivor_ids=(
                None
                if "selected_survivor_ids" not in data
                else tuple(str(item) for item in _list(data.get("selected_survivor_ids")))
            ),
            fitness_scores_digest=_str(data, "fitness_scores_digest", ""),
            novelty_scores_digest=_str(data, "novelty_scores_digest", ""),
            descriptor_digest=_str(data, "descriptor_digest", ""),
            selection_changed_by_qd=_bool(data, "selection_changed_by_qd", False),
            fallback_reason=_optional_str(data, "fallback_reason"),
            qd_fallback_reason=_optional_str(data, "qd_fallback_reason"),
            qd_mode=_str(data, "qd_mode", "disabled"),
            qd_parent_order_changed=_bool(data, "qd_parent_order_changed", False),
            qd_survivor_set_changed=_bool(data, "qd_survivor_set_changed", False),
        )

    def digest(self) -> str:
        return _digest(self.to_dict())


@dataclass(frozen=True, slots=True)
class NoveltyScore:
    """Auditable novelty score attached to one candidate."""

    organism_id: str
    score: float
    descriptor_digest: str = ""
    method: str = "mean_pairwise_descriptor_distance_v1"

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "organism_id": self.organism_id,
            "score": self.score,
            "descriptor_digest": self.descriptor_digest,
            "method": self.method,
        }

    def digest(self) -> str:
        return _digest(self.to_dict())


@dataclass(frozen=True, slots=True)
class QDSelectionFeedback:
    """Public QD/novelty feedback for one selection decision."""

    generation: int
    archive_digest_before: str | None
    archive_digest_after: str | None
    descriptor_digest: str
    fitness_scores_digest: str
    novelty_scores_digest: str
    selected_survivor_ids: tuple[str, ...]
    selected_parent_ids: tuple[str, ...]
    selection_changed_by_qd: bool
    fallback_reason: str | None = None
    qd_fallback_reason: str | None = None
    qd_mode: str = "disabled"

    @property
    def qd_changed_selection(self) -> bool:
        """Backward-compatible alias for QD claim/audit guards."""

        return self.selection_changed_by_qd

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "generation": self.generation,
            "archive_digest_before": self.archive_digest_before,
            "archive_digest_after": self.archive_digest_after,
            "descriptor_digest": self.descriptor_digest,
            "fitness_scores_digest": self.fitness_scores_digest,
            "novelty_scores_digest": self.novelty_scores_digest,
            "selected_survivor_ids": list(self.selected_survivor_ids),
            "selected_parent_ids": list(self.selected_parent_ids),
            "selection_changed_by_qd": self.selection_changed_by_qd,
            "qd_changed_selection": self.qd_changed_selection,
            "fallback_reason": self.fallback_reason,
            "qd_fallback_reason": self.qd_fallback_reason or self.fallback_reason,
            "qd_mode": self.qd_mode,
        }

    def digest(self) -> str:
        return _digest(self.to_dict())


@dataclass(frozen=True, slots=True)
class QDParentFeedback(QDSelectionFeedback):
    """Alias class for parent-order feedback produced by active QD pressure."""


QDSelectionAuditRecord = EvolutionSelectionResult


def policy_from_name(
    name: str,
    *,
    elitism_count: int = 1,
    tournament_size: int = 3,
    novelty_weight: float = 1.0,
    fitness_weight: float = 1.0,
) -> SelectionPolicy:
    """Create a built-in selection policy by stable name."""

    if name == "fitness_proportional":
        return FitnessProportionalSelection()
    if name == "tournament":
        return TournamentSelection(tournament_size=tournament_size)
    if name == "elitism":
        return ElitismSelection(elitism_count=elitism_count)
    if name == "novelty_weighted":
        return NoveltyWeightedSelection(
            fitness_weight=fitness_weight, novelty_weight=novelty_weight
        )
    if name == "age_layered":
        return AgeLayeredSelection()
    msg = f"Unsupported selection policy {name!r}."
    raise ConfigurationError(msg)


def select_population(
    candidates: Sequence[object],
    *,
    fitness_scores: Mapping[str, float],
    max_population: int,
    config: EvolutionConfig | None = None,
    novelty_scores: Mapping[str, float] | None = None,
    ages: Mapping[str, int] | None = None,
    qd_mode: str | None = None,
) -> tuple[tuple[object, ...], EvolutionSelectionResult]:
    """Apply deterministic capacity selection and return audit metadata."""

    if max_population <= 0:
        msg = "max_population must be > 0."
        raise ConfigurationError(msg)
    config = config or EvolutionConfig(max_population=max_population)
    effective_capacity = (
        max_population
        if config.max_population is None
        else min(max_population, config.max_population)
    )
    policy = config.resolved_policy()
    resolved_qd_mode = qd_mode if qd_mode is not None else config.qd_mode
    selected = tuple(
        policy.select(
            tuple(candidates),
            fitness_scores=fitness_scores,
            max_population=effective_capacity,
            novelty_scores=novelty_scores,
            ages=ages,
        )
    )
    selected_ids = tuple(_stable_id(item) for item in selected)
    selected_set = set(selected_ids)
    dropped_ids = tuple(
        _stable_id(item) for item in candidates if _stable_id(item) not in selected_set
    )
    fitness_scores_digest = _digest(
        {"fitness_scores": {str(key): float(fitness_scores[key]) for key in sorted(fitness_scores)}}
    )
    resolved_novelty_scores = novelty_scores or {}
    novelty_scores_digest = _digest(
        {
            "novelty_scores": {
                str(key): float(resolved_novelty_scores[key])
                for key in sorted(resolved_novelty_scores)
            }
        }
    )
    fallback_reason: str | None = None
    selection_changed_by_qd = False
    qd_parent_order_changed = False
    qd_survivor_set_changed = False
    if resolved_qd_mode == "archive_only" and policy.name != "novelty_weighted":
        fallback_reason = QDFallbackReason.QD_ARCHIVE_ONLY_MODE.value
    elif policy.name == "novelty_weighted":
        baseline_ids = tuple(
            _stable_id(item)
            for item in _top_by_score(candidates, fitness_scores, effective_capacity)
        )
        qd_parent_order_changed = selected_ids != baseline_ids
        qd_survivor_set_changed = set(selected_ids) != set(baseline_ids)
        selection_changed_by_qd = qd_parent_order_changed
        if len(candidates) <= 1:
            fallback_reason = QDFallbackReason.SINGLE_CANDIDATE_NO_SELECTION_PRESSURE.value
        elif effective_capacity >= len(candidates) and not qd_parent_order_changed:
            fallback_reason = QDFallbackReason.CAPACITY_NOT_EXCEEDED.value
        elif not resolved_novelty_scores:
            fallback_reason = QDFallbackReason.NOVELTY_SCORES_UNAVAILABLE.value
        elif all(float(value) == 0.0 for value in resolved_novelty_scores.values()):
            fallback_reason = QDFallbackReason.NOVELTY_SCORES_ZERO.value
        elif qd_parent_order_changed:
            fallback_reason = QDFallbackReason.SELECTION_APPLIED.value
        else:
            fallback_reason = QDFallbackReason.FITNESS_DOMINATES.value
    else:
        fallback_reason = QDFallbackReason.QD_DISABLED.value
    return selected, EvolutionSelectionResult(
        before_count=len(candidates),
        after_count=len(selected),
        selected_ids=selected_ids,
        dropped_ids=dropped_ids,
        policy_name=policy.name,
        config_digest=config.digest(),
        selected_parent_ids=selected_ids,
        selected_survivor_ids=selected_ids,
        fitness_scores_digest=fitness_scores_digest,
        novelty_scores_digest=novelty_scores_digest,
        descriptor_digest="",
        selection_changed_by_qd=selection_changed_by_qd,
        fallback_reason=fallback_reason,
        qd_fallback_reason=fallback_reason,
        qd_mode=resolved_qd_mode,
        qd_parent_order_changed=qd_parent_order_changed,
        qd_survivor_set_changed=qd_survivor_set_changed,
    )


def _top_by_score(
    candidates: Sequence[object], fitness_scores: Mapping[str, float], max_population: int
) -> tuple[object, ...]:
    if max_population <= 0:
        return ()
    return tuple(
        sorted(
            candidates,
            key=lambda item: (-float(fitness_scores.get(_stable_id(item), 0.0)), _stable_id(item)),
        )[:max_population]
    )


def _stable_id(item: object) -> str:
    value = getattr(item, "id", None)
    if isinstance(value, str) and value:
        return value
    value = getattr(item, "organism_id", None)
    if isinstance(value, str) and value:
        return value
    return repr(item)


def _digest(payload: Mapping[str, JsonValue]) -> str:
    encoded = finite_json_dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _str(data: Mapping[str, JsonValue], key: str, default: str = "") -> str:
    value = data.get(key, default)
    if not isinstance(value, str):
        msg = f"{key} must be a string."
        raise ConfigurationError(msg)
    return value


def _int(data: Mapping[str, JsonValue], key: str, default: int) -> int:
    value = data.get(key, default)
    if isinstance(value, bool) or not isinstance(value, int):
        msg = f"{key} must be an integer."
        raise ConfigurationError(msg)
    return value


def _float(data: Mapping[str, JsonValue], key: str, default: float) -> float:
    value = data.get(key, default)
    if isinstance(value, bool) or not isinstance(value, int | float):
        msg = f"{key} must be numeric."
        raise ConfigurationError(msg)
    return finite_float(key, value)  # type: ignore[return-value]


def _list(value: object) -> list[object]:
    if value is None:
        return []
    if not isinstance(value, list):
        msg = "expected a list."
        raise ConfigurationError(msg)
    return value


def _bool(data: Mapping[str, JsonValue], key: str, default: bool) -> bool:
    value = data.get(key, default)
    if not isinstance(value, bool):
        msg = f"{key} must be a boolean."
        raise ConfigurationError(msg)
    return value


def _optional_str(data: Mapping[str, JsonValue], key: str) -> str | None:
    value = data.get(key)
    if value is None:
        return None
    if not isinstance(value, str):
        msg = f"{key} must be a string or null."
        raise ConfigurationError(msg)
    return value
