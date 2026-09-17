"""E2 deme / kin selection knob for HARD_EXPERIMENT_02 (Knoester 2008; Floreano 2007).

2×2 design: selection level {INDIVIDUAL, GERMLINE_GROUP} × founder
relatedness {CLONAL, MIXED}. Default-off. Builds on existing Phase E deme
substrate without changing A–E pins when disabled.

Preregistered ordinal (not a single dz):
GERMLINE×CLONAL > GERMLINE×MIXED ≈ INDIVIDUAL×CLONAL > INDIVIDUAL×MIXED.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import Literal

from codontrace._types import JsonValue
from codontrace.errors import ConfigurationError
from codontrace.genesis.canonical import canonical_digest
from codontrace.genesis.phase_e import DemeConfig, PhaseESubstrateConfig

SelectionLevel = Literal["INDIVIDUAL", "GERMLINE_GROUP"]
FounderRelatedness = Literal["CLONAL", "MIXED"]
ReplicationTrigger = Literal["MEAN_FITNESS", "TASK_COUNT"]

E2_ORDINAL_PREDICTION: tuple[str, ...] = (
    "GERMLINE_CLONAL",
    "GERMLINE_MIXED",
    "INDIVIDUAL_CLONAL",
    "INDIVIDUAL_MIXED",
)


class DemeSelectionCell(StrEnum):
    """Named 2×2 cell for deme × relatedness."""

    GERMLINE_CLONAL = "GERMLINE_CLONAL"
    GERMLINE_MIXED = "GERMLINE_MIXED"
    INDIVIDUAL_CLONAL = "INDIVIDUAL_CLONAL"
    INDIVIDUAL_MIXED = "INDIVIDUAL_MIXED"


@dataclass(frozen=True, slots=True)
class DemeSelectionConfig:
    """Opt-in multilevel / kin-structure selection controls."""

    enabled: bool = False
    level: SelectionLevel = "INDIVIDUAL"
    founder_relatedness: FounderRelatedness = "MIXED"
    replication_trigger: ReplicationTrigger = "MEAN_FITNESS"
    deme_size: int = 4
    deme_count: int = 2
    mean_fitness_threshold: float = 0.0

    def __post_init__(self) -> None:
        if self.level not in {"INDIVIDUAL", "GERMLINE_GROUP"}:
            raise ConfigurationError(
                "DemeSelectionConfig.level must be INDIVIDUAL or GERMLINE_GROUP."
            )
        if self.founder_relatedness not in {"CLONAL", "MIXED"}:
            raise ConfigurationError(
                "DemeSelectionConfig.founder_relatedness must be CLONAL or MIXED."
            )
        if self.replication_trigger not in {"MEAN_FITNESS", "TASK_COUNT"}:
            raise ConfigurationError(
                "DemeSelectionConfig.replication_trigger must be MEAN_FITNESS or TASK_COUNT."
            )
        if self.deme_size <= 0:
            raise ConfigurationError("deme_size must be > 0.")
        if self.deme_count <= 0:
            raise ConfigurationError("deme_count must be > 0.")
        if self.mean_fitness_threshold < 0:
            raise ConfigurationError("mean_fitness_threshold must be >= 0.")

    @property
    def cell(self) -> DemeSelectionCell:
        key = (
            "GERMLINE"
            if self.level == "GERMLINE_GROUP"
            else "INDIVIDUAL"
        )
        return DemeSelectionCell(f"{key}_{self.founder_relatedness}")

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "enabled": self.enabled,
            "level": self.level,
            "founder_relatedness": self.founder_relatedness,
            "replication_trigger": self.replication_trigger,
            "deme_size": self.deme_size,
            "deme_count": self.deme_count,
            "mean_fitness_threshold": self.mean_fitness_threshold,
            "cell": self.cell.value,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, JsonValue]) -> DemeSelectionConfig:
        return cls(
            enabled=bool(data.get("enabled", False)),
            level=str(data.get("level", "INDIVIDUAL")),  # type: ignore[arg-type]
            founder_relatedness=str(data.get("founder_relatedness", "MIXED")),  # type: ignore[arg-type]
            replication_trigger=str(data.get("replication_trigger", "MEAN_FITNESS")),  # type: ignore[arg-type]
            deme_size=int(data.get("deme_size", 4)),
            deme_count=int(data.get("deme_count", 2)),
            mean_fitness_threshold=float(data.get("mean_fitness_threshold", 0.0)),
        )

    def digest(self) -> str:
        return canonical_digest(self.to_dict())

    def to_phase_e_demes(self) -> DemeConfig:
        """Map onto existing Phase E deme substrate (no new Phase letter)."""

        if not self.enabled:
            return DemeConfig()
        germline = self.level == "GERMLINE_GROUP"
        threshold = (
            float(self.mean_fitness_threshold)
            if self.replication_trigger == "MEAN_FITNESS"
            else None
        )
        return DemeConfig(
            enabled=True,
            deme_size=int(self.deme_size),
            messaging_enabled=True,
            replicate_on_mean_fitness=threshold if germline else None,
            replicate_copy_germline=germline,
            send_on_eat=True,
        )

    def to_phase_e(self) -> PhaseESubstrateConfig:
        if not self.enabled:
            return PhaseESubstrateConfig()
        return PhaseESubstrateConfig(enabled=True, demes=self.to_phase_e_demes())


@dataclass(frozen=True, slots=True)
class DemeSelectionRecord:
    """Digest-backed deme replication / structure observation."""

    tick: int
    cell: str
    deme_id: str
    mean_fitness: float
    germline_parent_id: str
    member_count: int
    replicated: bool

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "tick": self.tick,
            "cell": self.cell,
            "deme_id": self.deme_id,
            "mean_fitness": self.mean_fitness,
            "germline_parent_id": self.germline_parent_id,
            "member_count": self.member_count,
            "replicated": self.replicated,
        }

    def digest(self) -> str:
        return canonical_digest(self.to_dict())


def e2_ordinal_rank(cell: str | DemeSelectionCell) -> int:
    """Lower rank is predicted better (0 = GERMLINE_CLONAL)."""

    value = cell.value if isinstance(cell, DemeSelectionCell) else str(cell)
    try:
        return E2_ORDINAL_PREDICTION.index(value)
    except ValueError as exc:
        raise ConfigurationError(f"unknown E2 cell: {value!r}") from exc


def e2_ordinal_respects_prediction(cell_means: Mapping[str, float]) -> bool:
    """Return True when observed cell means respect the preregistered order.

    Missing cells are ignored; ties are allowed between GERMLINE_MIXED and
    INDIVIDUAL_CLONAL (predicted ≈).
    """

    present = [
        (e2_ordinal_rank(name), float(mean), name)
        for name, mean in cell_means.items()
        if name in E2_ORDINAL_PREDICTION
    ]
    if len(present) < 2:
        return False
    present.sort(key=lambda item: item[0])
    for left, right in zip(present, present[1:], strict=False):
        left_rank, left_mean, left_name = left
        right_rank, right_mean, right_name = right
        # Predicted ≈ pair may tie or go either way within epsilon.
        approx_pair = {
            frozenset({"GERMLINE_MIXED", "INDIVIDUAL_CLONAL"}),
        }
        if frozenset({left_name, right_name}) in approx_pair:
            continue
        if left_mean + 1e-12 < right_mean:
            return False
        _ = (left_rank, right_rank)
    return True
