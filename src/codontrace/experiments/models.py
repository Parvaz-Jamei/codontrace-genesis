"""Core data models, tracks, and invariants for Genesis Scientific Experiments (T01-T12)."""

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from typing import Any


class ExecutionTrack(str, enum.Enum):
    """Explicit boundary separation of experiment execution tracks."""
    REFERENCE = "REFERENCE"      # Standalone analytical/mathematical benchmark models
    ENGINE = "ENGINE"            # Full Genesis virtual machine codon dispatch & life cycle
    INTEGRATED = "INTEGRATED"    # Coupled engine + ledger + behavioral feedback loops


class AssessmentStatus(str, enum.Enum):
    """Allowed scientific assessment statuses per specification."""
    SUPPORTED_IN_THIS_MODEL = "SUPPORTED_IN_THIS_MODEL"
    NOT_SUPPORTED = "NOT_SUPPORTED"
    INCONCLUSIVE = "INCONCLUSIVE"
    INVALID_MEASUREMENT = "INVALID_MEASUREMENT"
    UNASSESSED = "UNASSESSED"


# Mandatory epistemic invariants
RED_QUEEN_PROVED: bool = False
MAJOR_TRANSITION_PROVED: bool = False
OPEN_ENDED_INTELLIGENCE_PROVED: bool = False


@dataclass(frozen=True, slots=True)
class ExperimentManifest:
    """Rigorous manifest recording environment, seeds, and execution boundary."""
    experiment_id: str
    track: ExecutionTrack
    backend_class: str
    source_sha: str
    seed: int
    generations: int
    population_size: int
    worker_affinity: int | None
    platform_info: dict[str, Any]
    epistemic_invariants: dict[str, bool] = field(
        default_factory=lambda: {
            "red_queen_proved": RED_QUEEN_PROVED,
            "major_transition_proved": MAJOR_TRANSITION_PROVED,
            "open_ended_intelligence_proved": OPEN_ENDED_INTELLIGENCE_PROVED,
        }
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "experiment_id": self.experiment_id,
            "track": self.track.value,
            "backend_class": self.backend_class,
            "source_sha": self.source_sha,
            "seed": self.seed,
            "generations": self.generations,
            "population_size": self.population_size,
            "worker_affinity": self.worker_affinity,
            "platform_info": self.platform_info,
            "epistemic_invariants": self.epistemic_invariants,
        }


@dataclass(frozen=True, slots=True)
class MetricRecord:
    """Single generation metric record logged to metrics.jsonl."""
    generation: int
    tick: int
    population_size: int
    primary_metric_name: str
    primary_metric_value: float
    secondary_metrics: dict[str, float]
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "generation": self.generation,
            "tick": self.tick,
            "population_size": self.population_size,
            "primary_metric_name": self.primary_metric_name,
            "primary_metric_value": self.primary_metric_value,
            "secondary_metrics": self.secondary_metrics,
            "details": self.details,
        }


@dataclass(frozen=True, slots=True)
class CompletionSummary:
    """Final experiment completion summary per spec."""
    experiment_id: str
    track: ExecutionTrack
    seed: int
    completed_generations: int
    total_ticks: int
    status: str
    stop_reason: str
    scientific_assessment: AssessmentStatus
    primary_endpoint_value: float
    summary_metrics: dict[str, Any]
    red_queen_proved: bool = RED_QUEEN_PROVED
    major_transition_proved: bool = MAJOR_TRANSITION_PROVED

    def to_dict(self) -> dict[str, Any]:
        return {
            "experiment_id": self.experiment_id,
            "track": self.track.value,
            "seed": self.seed,
            "completed_generations": self.completed_generations,
            "total_ticks": self.total_ticks,
            "status": self.status,
            "stop_reason": self.stop_reason,
            "scientific_assessment": self.scientific_assessment.value,
            "primary_endpoint_value": self.primary_endpoint_value,
            "summary_metrics": self.summary_metrics,
            "red_queen_proved": self.red_queen_proved,
            "major_transition_proved": self.major_transition_proved,
        }
