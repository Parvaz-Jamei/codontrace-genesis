"""Execution and artifact schema definitions for Genesis."""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from codontrace._types import JsonValue

SCHEMA_VERSION = "genesis_execution_v1"


@dataclass(frozen=True, slots=True)
class RunState:
    run_id: str
    status: str
    start_time: str
    end_time: str | None
    
    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "run_id": self.run_id,
            "status": self.status,
            "start_time": self.start_time,
            "end_time": self.end_time,
        }


@dataclass(frozen=True, slots=True)
class FeatureExecutionRecord:
    feature_name: str
    executed: bool
    result: str | None
    
    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "feature_name": self.feature_name,
            "executed": self.executed,
            "result": self.result,
        }


@dataclass(frozen=True, slots=True)
class MetricRecord:
    metric_name: str
    value: float
    unit: str | None

    def __post_init__(self) -> None:
        if not isinstance(self.value, (int, float)) or not math.isfinite(self.value):
            raise ValueError(f"MetricRecord '{self.metric_name}' value must be a finite float, got {self.value}")
    
    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "metric_name": self.metric_name,
            "value": self.value,
            "unit": self.unit,
        }


@dataclass(frozen=True, slots=True)
class HypothesisAssessment:
    hypothesis_id: str
    conclusion: str
    confidence: float
    evidence_digests: tuple[str, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.confidence, (int, float)) or not math.isfinite(self.confidence):
            raise ValueError(f"HypothesisAssessment confidence must be finite, got {self.confidence}")
        if not (0.0 <= self.confidence <= 1.0):
            raise ValueError(f"HypothesisAssessment confidence must be between 0.0 and 1.0, got {self.confidence}")
        for d in self.evidence_digests:
            if not d or any(d.startswith(p) for p in ("fake", "placeholder", "not_run:")):
                raise ValueError(f"HypothesisAssessment contains invalid or fake evidence digest: {d}")
    
    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "hypothesis_id": self.hypothesis_id,
            "conclusion": self.conclusion,
            "confidence": self.confidence,
            "evidence_digests": list(self.evidence_digests),
        }


@dataclass(frozen=True, slots=True)
class ArtifactManifest:
    artifacts: tuple[Mapping[str, Any], ...]
    version: str = SCHEMA_VERSION
    
    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "version": self.version,
            "artifacts": [dict(a) for a in self.artifacts],
        }
